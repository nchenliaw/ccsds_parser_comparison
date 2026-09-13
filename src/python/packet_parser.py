import binascii
import struct
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

BITS_PER_BYTE = 8
CRC_SIZE_BYTES = 2
FRAME_SYNC_HEADER = 0xABCD1234
SEQUENCE_FLAGS = 0b11
VERSION_NUMBER = 0
PACKET_TYPE = 0
SECONDARY_HEADER_FLAG = 1

sequence_count = 0


@dataclass
class DebugMetaData:
    packets_parsed: int = 0
    dropped_packets: int = 0
    malformed_packets: int = 0
    bad_crcs: int = 0


def n_bits_mask(n: int) -> int:
    """Return a bitmask of n bits of all ones
    Ex: n_bits_mask(5) = 0b11111
    Ex: n_bits_mask(3) = 0b111

    Args:
        n (int): number of bits

    Returns:
        int: bitmask
    """
    return (1 << n) - 1


def extract_bits(value: int, bit_width: int, start_bit: int, end_bit: int) -> int:
    """Extract bits from an integer values. Note that start_bit and end_bit
    are 0-indexed.
    E.g. extract_bits(0b1110, 4, 0, 2) = 0b111 for bits 0-2
    E.g. extract_bits(0b0110, 4, 1, 2) = 0b11 for bits 1-2

    Args:
        value (int): The value from which to extract bits
        bit_width (int): total bit width of the value
        start_bit (int): Start bit to grab
        end_bit (int): End bit to grab

    Returns:
        int: Extracted bits
    """
    width = end_bit - start_bit + 1
    mask = n_bits_mask(width)
    shifted = value >> (bit_width - end_bit - 1)
    return shifted & mask


def parse_primary_header(data: bytes, start_byte: int) -> tuple[dict[str, int], int]:
    """Parses primary header (first 6 bytes) from data.

    Args:
        data (bytes): Data to parse

    Returns:
        dict[str, int]:
          packet version number,
          packet type,
          secondary header flag,
          APID,
          sequence flags,
          packet sequence number,
          packet data length
        int: new start byte
    """
    ret = {}
    fmt = ">H"  # 2 bytes
    size = struct.calcsize(fmt) * BITS_PER_BYTE
    first_word = struct.unpack_from(fmt, data, start_byte)[0]

    ret["version_number"] = extract_bits(first_word, size, 0, 2)
    ret["packet_type"] = extract_bits(first_word, size, 3, 3)
    ret["sec_hdr_flag"] = extract_bits(first_word, size, 4, 4)
    ret["apid"] = extract_bits(first_word, size, 5, 15)

    second_word = struct.unpack_from(fmt, data, start_byte + 2)[0]

    ret["sequence_flags"] = extract_bits(second_word, size, 0, 1)
    ret["sequence_count"] = extract_bits(second_word, size, 2, 15)

    ret["data_length"] = struct.unpack_from(fmt, data, start_byte + 4)[0]

    return ret, start_byte + 6


def parse_time_code_field(data: bytes, start_byte: int) -> tuple[float, int]:
    """Parse 5-byte time code field, defined as 4-byte
    coarse time and 1-byte fine time. Coarse time is POSIX seconds,
    fine time is subseconds in 1/256 intervals

    Args:
        data (bytes): Data from which to parse time code
        start_byte (int): Starting byte index to parse

    Returns:
        tuple[float, int]: Posix seconds (float), position of next byte to parse
    """
    sec = struct.unpack_from(">I", data, offset=start_byte)[0]
    subseconds = struct.unpack_from(">B", data, offset=start_byte + 4)[0] / 256
    return sec + subseconds, start_byte + 5


def parse_ancillary_data_field(data: bytes, start_byte: int) -> tuple[dict[str, Any], int]:
    """Parse packet ancillary data field starting from start_byte. Returns
    dict of parsed data and updated start byte resulting from parsing

    Args:
        data (bytes): Data from which to parse
        start_byte (int): Starting byte index to parse

    Returns:
        tuple[dict[str, Any], int]: dict contains parsed packet data, int is position of next byte to parse
    """
    ret = {}
    ret["frame_sync"] = struct.unpack_from(">L", data, start_byte)[0]
    ret["ancillary_data_length"] = struct.unpack_from(">H", data, start_byte + 4)[0]
    data_length = ret["ancillary_data_length"]
    data_start = start_byte + 6
    data_end = data_start + data_length
    ret["data"] = data[data_start:data_end]
    ret["crc"] = struct.unpack_from(">H", data, data_end)[0]

    return ret, data_end + 2


def parse_secondary_header(data: bytes, start_byte) -> tuple[dict[str, Any], int]:
    time, start_byte = parse_time_code_field(data, start_byte)
    ancillary_data, start_byte = parse_ancillary_data_field(data, start_byte)
    ret = {"time": time}
    return ret | ancillary_data, start_byte


def parse_packets(data: bytes) -> tuple[list[dict], DebugMetaData]:
    """Parses a byte stream of data and returns a tuple of [list[dict], DebugMetaData],
    representing packets parsed and some metadata associated with the parsing

    Args:
        data (bytes): byte stream of data

    Returns:
        tuple[list[dict], DebugMetaData]: Parsed packet data and metadata
    """
    metadata = DebugMetaData()
    packets = []
    start_byte = 0
    data_len = len(data)
    while start_byte < data_len:
        hdr, post_primary_byte = parse_primary_header(data, start_byte)
        # TODO: check frame sync
        sec, new_start_byte = parse_secondary_header(data, post_primary_byte)
        actual_crc = binascii.crc_hqx(data[start_byte : new_start_byte - 2], 0)
        if actual_crc != sec["crc"]:
            metadata.bad_crcs += 1
        else:
            packets.append(hdr | sec)
            # TODO: Implement more metadata metrics
            metadata.packets_parsed += 1
        start_byte = new_start_byte

    # TODO: Implement a loop to parse all packets from data
    return packets, metadata


def add_ancillary_header_to(data: bytes, timestamp: datetime | None = None) -> bytes:
    """Recieves data to wrap in ancillary data field headers but
    without CRC. CRC will be added later, once the primary header
    is known

    Args:
        data (bytes): Data to wrap in header
        timestamp (datetime | None): Timestamp for header. If none is passed in,
            datetime.now(UTC) will be used

    Returns:
        bytes: Packet framed with ancillary header, not including CRC
    """
    # TODO: Use struct.pack_into and preallocate buffer
    if timestamp is None:
        timestamp = datetime.now(UTC)
    coarse_time = int(timestamp.timestamp())
    fine_time = round(timestamp.microsecond / 1e6 * 256) % 256
    data_len = len(data)
    # We're packing the headers closest to the data field first
    data = struct.pack(">H", data_len) + data
    data = struct.pack(">L", FRAME_SYNC_HEADER) + data
    data = struct.pack(">B", fine_time) + data
    data = struct.pack(">L", coarse_time) + data

    return data


def create_space_packet_header(data_len: int, apid: int) -> bytes:
    """Frames packet data field with space packet primary
    header.

    Args:
        data_len (int): Space packet data length
        apid (int): APID for space packet. Will be packed into 11 bits

    Returns:
        bytes: Framed space packet
    """
    # TODO: Use struct.pack_into to add into a buffer
    if apid > 2**11 - 1 or apid < 1:
        raise ValueError(f"APID {apid} is not valid. APID must be 11 bits max, or less than or equal to 2047")
    packet_version_and_id = (VERSION_NUMBER << 13) | (PACKET_TYPE << 12) | (SECONDARY_HEADER_FLAG << 11) | apid
    sequence_count_masked = sequence_count & n_bits_mask(14)
    packet_sequence_control = (SEQUENCE_FLAGS << 14) | sequence_count_masked

    data = struct.pack(">H", packet_version_and_id)
    data += struct.pack(">H", packet_sequence_control)
    data += struct.pack(">H", data_len)

    return data


def frame_packet(data: bytes, apid: int) -> bytes:
    """Recieves data to wrap in ancillary data field,
    secondary_header, and space packet primary header.
    Returns data framed as a CCSDS space packet.

    Args:
        data (bytes): Data to wrap in header
        apid (int): APID for space packet
    """
    global sequence_count
    sequence_count += 1

    # TODO: use struct.pack_into
    data = add_ancillary_header_to(data)
    data_len = len(data) + CRC_SIZE_BYTES  # add_ancillary_header_to does not include CRC
    header = create_space_packet_header(data_len, apid)
    data = header + data
    crc = binascii.crc_hqx(data, 0)  # 16-bit CRC
    data += struct.pack(">H", crc)
    return data
