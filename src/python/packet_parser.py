import struct

BITS_PER_BYTE = 8


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
    shifted = value >> (bit_width  - end_bit)
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
    ret["packet_sequence"] = extract_bits(second_word, size, 2, 15)

    ret["data_length"] = struct.unpack(fmt, data[4:6])[0]

    return ret


def parse_secondary_header(data: bytes):
    pass


def create_packet(data, secondary_hdr_config) -> bytes:
    pass


def send_packet(pkt) -> None:
    pass


if __name__ == "__main__":
    data = b"\xb1\xb2\xb3\xb4\xb5\xb6"
    parse_primary_header(data)
