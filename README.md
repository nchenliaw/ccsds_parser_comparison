[TOC]

# ccsds_parser_comparison

Comparison of CCSDS packet parsing in Python, C++, and Rust. Compares speed of packet parsing for Space Packets as defined by [CCSDS 133.0-B-2](https://ccsds.org/publications/bluebooks/entry/3264/).

This was done with the following goals in mind:

1. Develop a skills relevant to space software engineering that I have not had much exposure to so far in my career:
   - Bitwise operations
   - Endianness
   - Packet parsing
1. Gain familiarity with compiled languages used commonly in industry (C++, Rust) and the supporting tooling for each
   - CMake
   - Rust's Cargo

# Research

## Space Packet
- A CCSDS Space Packet must contain a Primary Header of 6 octets and a Packet Data Field of 1 to 2^16 octets.  
  ![](images/packet_structure.png)
- An octet is defined as a sequence of 8 bits
- Octets in a Space Packet are transmitted MSB first. The MSB is the 0th bit in each octet.
- The Packet Primary Header consists of the following fields:  
  ![](images/packet_primary_header.png)
  - 3-bit packet version number is recommended to be '000'
  - Packet Identification Field is a 13-bit field comprised of a 1-bit Packet Type, 1 bit Secondary Header Flag, and 11-bit APID
- The structure of the Packet Data Field is mandated only to have at least one of the following:
  - User-defined packet secondary header (variable length)
  - User data field
- If a Packet Secondary Header is used, it shall consist of either:
  - A Time Code Field only
  - An Ancillary Data Field only
  - A Time Code Field followed by an Ancillary Data Field

## Frame Syncs and ASM
This project defines a frame sync header for the Space Packet's ancillary data field. The primary synchronization method in a real system happens upstream at transfer frames, and is out of scope for this packet parser. However, the ancillary data field's frame sync header is still used for **re-synchronization** if invalid packets (bad length, bad CRC, etc.) are parsed.

The ancillary data field's frame sync header is used as a more reliable method for resynchronization compared to the other option, which is parsing the Space Packet primary header. Not all 6 bytes of the primary header are the same each time - APID and sequence count may change with each packet. This leaves only 5 bits static for the Primary header - Version Number, Packet Type,and Secondary header flag. In this example, those 5 bits will be `0b00001`, which is an unreliable sequence of bits to use for frame sync.  

[CCSDS 131.0-B-6](https://ccsds.org/publications/bluebooks/entry/4803/) defines TM synhronization and channel coding. An example RF chain is shown below. This repo's space packet parsers only implement the last stage of the chain, highlighted with **. 
```
Modulated RF data stream (e.g. BPSK, QPSK) -> carrier demodulation -> inner FEC decoding -> Frame sync via ASM (Attached Sync Marker) detection
-> outer FEC decoding (e.g. Reed-Solomon decoding) -> VCID demux + packet reassembly (transfer frames are fixed-length and 
space packets may cross transfer frame boundaries) -> **Space packet parsing**
```

In a real system, even with all of these error correction and validity mechanisms, one may not assume that packets reaching the packet parser are all correct. For example, a dropped frame may contain packet data that crosses frame boundaries; the result is that a partial packet may be sent to the packet parser.

As a consequence, these are some considerations for a packet parser:
1. Length field must be validated, and ensure no out-of-bounds errors crash the program (e.g. specified length field exceeds data/array boundary)
1. Validate static/expected field values immediately - version number, packet type, etc.
1. CRC failures should result in discarded packets
1. Implement a resynchronization strategy when validation fails
1. Have metadata to track/preserve rejected data

Tests to include:
1. Packet with invalid length field
1. Packet with bad CRC
1. Valid with good CRC but invalid primary packet header
1. Truncated packet at end of stream (e.g. crossing transfer frame boundaries)

# Project Scope

## Packet Definition

- Packet version number is '000'
- A secondary header is used
- The secondary header is 133.0-B-2 compliant, containing a Time Code field and an Ancillary Data Field
  - Time code is defined by [CCSDS 301.0-B-4](https://ccsds.org/publications/bluebooks/entry/3147/)
    - No Preamble field
    - 4-byte coarse time, measuring seconds since CCSDS Unsegmented Time Code (CUC) epoch of 1 January 1958
    - 1-byte fine time, measuring subsections as 1/256ths of a second
  - For increased realism, the Ancillary Data Field itself contains the following structure:
  - 4-byte frame sync header, fixed at 0xABCD1234
  - 2-byte data length field
  - 2-byte CRC across the entire Space Packet, not including the CRC itself. 16-bit CRC is computed via the CRC-CCITT polynomial, represented as `0x1021`
  - Data field (variable length), max 65523 Bytes, to conform to the Space Packet's 2^16 Byte max Data Field (65536 - (5-byte time code, 4-byte frame sync header, 2-byte data length field, and 2-byte CRC))
- All packet fields are transmitted Big Endian, MSB first.

```json
[
    "primary_header": {
        "version_number": {
            "bits": 3,
            "expected": "0b000"
        },
        "packet_type": {
            "bits": 1,
            "expected": 0,
            "notes": "Value of 0 for telemetry and 1 for commanding"
        },
        "sec_header_flag": {
            "bits": 1,
            "expected": 1,
            "notes": "Indicates that a secondary header is present"
        },
        "apid": {
            "bits": 11
        },
        "sequence_flags": {
            "bits": 2,
            "expected": "0b11",
            "notes": "Shall be 0b11 to indicate the space packet contains unsegmented user data"
        },
        "sequence_count": {
            "bits": 14,
            "notes": "Increments from 0 to 16383"
        },
        "data_length": {
            "bits": 16,
            "notes": "Length of data field, in bytes"
        }
    },
    "secondary_header": {
        "time_code_field": {
            "coarse_time": {
                "bits": 32,
                "notes": "Seconds since CCSDS Unsegmented Time Code (CUC) epoch of 1958 January 1"
            },
            "fine_time": {
                "bits": 8,
                "notes": "Subseconds with 1/256 resolution"
            }
        },
        "ancillary_data_field": {
            "frame_sync": {
                "bits": 32,
                "expected": "0xABCD1234"
            },
            "data_length": {
                "bits": 16,
                "notes": "Length of ancillary data, in bytes. Min length 1, max length 65523"
            },
            "data": {
                "bits": "varied"
            }
            "crc": {
                "bits": 16,
                "notes": "4-byte CRC computed across entire space packet, minus the CRC itself"
            }
        }
    }
]

```

## Requirements

- Must handle the following edge cases:
  - Malformed packets
  - Bad length fields
  - Idle Packets

# Results

# Running Tests

Python: `coverage run -m unittest discover -s tests/python && coverage report --show-missing`
