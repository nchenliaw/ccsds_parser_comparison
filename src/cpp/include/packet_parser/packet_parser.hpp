#include <cstdint>
#include <stdexcept>
#include <vector>

/**
 * @brief Running counters of packet-parsing outcomes for diagnostics and monitoring
 */
struct DebugMetaData
{
    uint32_t packets_parsed = 0;
    uint32_t dropped_packets = 0;
    uint32_t malformed_packets = 0;
    uint32_t bad_crcs = 0;
};

/**
 * @brief Primary header of the CCSDS packet
 */
struct PrimaryHeader
{
    uint8_t packet_version_number;
    uint8_t packet_type;
    bool sec_hdr_flag;
    uint16_t apid;
    uint8_t sequence_flags;
    uint16_t sequence_count;
    uint16_t data_length;
};

/**
 * @brief Secondary header of the CCSDS packet
 */
struct SecondaryHeader
{
    uint32_t coarse_time;            ///< UNIX seconds
    uint8_t fine_time;               ///< Subseconds, in 1/256 second increments
    uint32_t frame_sync;             ///< Expected frame sync value of 0xABCD1234
    uint16_t ancillary_data_length;
    std::vector<uint8_t> data;
    uint16_t crc;                    ///< 2-byte CRC computed across the entire packet: Both the primary + secondary header
};

/**
 * @brief Struct representing the contents of a single parsed packet
 */
struct ParsedPacket
{
    PrimaryHeader primary;
    SecondaryHeader secondary;
};

/**
 * @brief Create a bitmask of n bits all set to ones.
 *
 * Example: n_bits_mask(5) == 0b11111
 * Example: n_bits_mask(3) == 0b111
 * Example: n_bits_mask(0) == 0
 * Example: n_bits_mask(64) == 0xFFFFFFFFFFFFFFFF
 *
 * @param n  Number of bits to set, in the range [0, 64].
 * @return   A uint64_t with the low n bits set to 1 and all other bits 0.
 *
 * @throws std::invalid_argument if n > 64
 */
constexpr uint64_t n_bits_mask(unsigned int n);