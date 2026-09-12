import struct
import math
import binascii
from datetime import datetime, UTC
from dataclasses import dataclass

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
    packets_parsed: int
    dropped_packets: int
    malformed_packets: int
    bad_crcs: int


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


def parse_primary_header(data: bytes) -> dict[str, int]:
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
    """
    ret = {}
    fmt = ">H"
    size = struct.calcsize(fmt) * BITS_PER_BYTE
    first_word = struct.unpack(fmt, data[0:2])[0]

    ret["version_number"] = extract_bits(first_word, size, 0, 2)
    ret["packet_type"] = extract_bits(first_word, size, 3, 3)
    ret["sec_hdr_flag"] = extract_bits(first_word, size, 4, 4)
    ret["apid"] = extract_bits(first_word, size, 5, 15)

    second_word = struct.unpack(fmt, data[2:4])[0]

    ret["sequence_flags"] = extract_bits(second_word, size, 0, 1)
    ret["sequence_count"] = extract_bits(second_word, size, 2, 15)

    ret["data_length"] = struct.unpack(fmt, data[4:6])[0]

    return ret


def parse_secondary_header(data: bytes):
    time_code = parse_time_code_field(data)
    ancillary_data = parse_ancillary_data_field(data)


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
    parse_primary_header(data)

    return packets, metadata


def create_packet(data, secondary_hdr_config) -> bytes:
    pass


def add_ancillary_header_to(data: bytes, timestamp: datetime | None = None) -> bytes:
    """Recieves data to wrap in ancillary data field headers but
    without CRC. CRC will be added later, once the primary header
    is known

    Args:
        data (bytes): Data to wrap in header
        timestamp (datetime | None): Timestamp for header. If none is passed in,
            datetime.now(UTC) will be used

    Returns:
        bytes: Packet framed with ancillary header
    """
    if timestamp is None:
        timestamp = datetime.now(UTC)
    coarse_time = int(timestamp.timestamp())
    fine_time = int(timestamp.microsecond / 1e6 * 256)
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

    data = add_ancillary_header_to(data)
    data_len = len(data) + CRC_SIZE_BYTES  # add_ancillary_header_to does not include CRC
    header = create_space_packet_header(data_len, apid)
    data = header + data
    crc = binascii.crc_hqx(data, 0)  # 16-bit CRC
    data += struct.pack(">I", crc)
    return data


if __name__ == "__main__":
    data = b"\xb1\xb2\xb3\xb4\xb5\xb6"
    ret = frame_packet(data, apid=1234)
    parse_packets(ret)
