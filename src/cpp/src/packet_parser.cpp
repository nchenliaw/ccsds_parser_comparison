#include <cstdint>
#include <vector>
#include <tuple>
#include <packet_parser/packet_parser.hpp>


constexpr uint64_t n_bits_mask(const unsigned int n)
{
    if (n > 64) 
    {
        throw std::invalid_argument("n_bits_mask: n exceeds 64 bits");
    }
    if (n == 64) return UINT64_MAX;
    return (uint64_t{1} << n) - 1;
}


// std::tuple<PrimaryHeader, size_t> ParsePrimaryHeader(std::vector<uint8_t> data)
// {
//     return std::make_tuple(123, 456);
// }