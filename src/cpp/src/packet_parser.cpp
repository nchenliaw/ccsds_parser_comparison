#include <cstdint>
#include <vector>
#include <tuple>
#include <string>
#include <stdexcept>

#include <packet_parser/packet_parser.hpp>

constexpr uint64_t n_bits_mask(const unsigned int n)
{
    if (n > 64)
    {
        throw std::invalid_argument("n_bits_mask: n exceeds 64 bits");
    }
    if (n == 64)
        return UINT64_MAX;
    return (uint64_t{1} << n) - 1;
}

uint16_t extract_bits(const uint16_t value, const unsigned bit_width, const unsigned start_bit, const unsigned end_bit)
{
    if (bit_width == 0 || bit_width > 16)
    {
        std::string msg = "extract_bits: bit width must be in [1, 16]. You entered: " + std::to_string(bit_width);
        throw std::invalid_argument(msg);
    }
    if (start_bit > end_bit)
    {
        std::string msg = "extract_bits: start bit cannot be greater than end bit. You entered: start_bit=" + std::to_string(start_bit) + " end_bit=" + std::to_string(end_bit);
        throw std::invalid_argument(msg);
    }
    if (end_bit >= bit_width)
    {
        std::string msg = "extract_bits: end bit cannot be greater than or equal to bit width. You entered: end_bit=" + std::to_string(end_bit) + " bit_width=" + std::to_string(bit_width);
        throw std::invalid_argument(msg);
    }
    const unsigned width = end_bit - start_bit + 1;
    const uint64_t mask = n_bits_mask(width);
    uint64_t shifted = static_cast<uint64_t>(value) >> (bit_width - end_bit - 1);
    return static_cast<uint16_t>(shifted & mask);
}

constexpr uint16_t read_bigendian16(const uint8_t *p)
{
    return static_cast<uint16_t>(p[0] << 8 | p[1]);
}

PrimaryHeader ParsePrimaryHeader(const std::vector<uint8_t> &data, size_t &start_byte)
{
    constexpr size_t primary_header_size = 6;
    if (start_byte > data.size() || data.size() - start_byte < primary_header_size)
        throw std::out_of_range("ParsePrimaryHeader: need 6 bytes for primary header");

    PrimaryHeader header{}; // zero-init the struct, or else we'd need to worry about uninitialized fields
    // Header fields are big-endian. Byte 0 is the high byte
    const uint16_t first_word = read_bigendian16(data.data() + start_byte);
    header.packet_version_number = static_cast<uint8_t>(extract_bits(first_word, WIDTH_16_BIT, 0, 2));
    header.packet_type = static_cast<uint8_t>(extract_bits(first_word, WIDTH_16_BIT, 3, 3));
    header.sec_hdr_flag = extract_bits(first_word, WIDTH_16_BIT, 4, 4) != 0;
    header.apid = extract_bits(first_word, WIDTH_16_BIT, 5, 15);

    const uint16_t second_word = read_bigendian16(data.data() + start_byte + 2);

    header.sequence_flags = static_cast<uint8_t>(extract_bits(second_word, WIDTH_16_BIT, 0, 1));
    header.sequence_count = extract_bits(second_word, WIDTH_16_BIT, 2, 15);

    header.data_length = read_bigendian16(data.data() + start_byte + 4);

    start_byte += 6;

    return header;
}