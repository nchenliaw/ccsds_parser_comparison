import struct
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_PYTHON = REPO_ROOT / "src" / "python"
sys.path.insert(0, str(SRC_PYTHON))

from src.python.packet_parser import *

CURRENT_FOLDER = Path(__file__).parent
TEST_FILES_FOLDER = CURRENT_FOLDER.parent / "test_files"


class TestCreateAncillaryHeader(unittest.TestCase):
    def setUp(self):
        self.data_length = 10
        self.data = bytes(self.data_length)
        self.ancillary_header_bytes_no_crc = 11

    def test_length(self):
        """Validate that the length of the data returned
        by the function is correct"""
        ret = add_ancillary_header_to(self.data)
        assert len(ret) == self.data_length + self.ancillary_header_bytes_no_crc

    def test_header(self):
        """Validate the constructed header is correct"""
        timestamp = datetime(year=2020, month=1, day=1, tzinfo=UTC)
        expected_coarse_time = int(timestamp.timestamp())
        expected_fine_time = int(timestamp.microsecond / 1e6 * 256)
        ret = add_ancillary_header_to(data=self.data, timestamp=timestamp)

        coarse_time = struct.unpack(">L", ret[:4])[0]
        fine_time = struct.unpack(">B", ret[4:5])[0]
        frame_sync = struct.unpack(">L", ret[5:9])[0]
        parsed_data_len = struct.unpack(">H", ret[9:11])[0]
        parsed_data = struct.unpack(f">{parsed_data_len}s", ret[11:])[0]

        self.assertEqual(expected_coarse_time, coarse_time, "Coarse time field not packed correctly")
        self.assertEqual(expected_fine_time, fine_time, "Fine time field not packed correctly")
        self.assertEqual(frame_sync, FRAME_SYNC_HEADER, "Frame sync header not packed correctly")
        self.assertEqual(parsed_data_len, self.data_length, "Data length not packed correctly")
        self.assertEqual(parsed_data, self.data, "Data field not packed correctly")


class TestCreateSpacePacketHeader(unittest.TestCase):
    def run_create_sp_header_test(self, data_len: int, apid: int):
        """Helper method to test different parameters fed into
        create_space_packet_header()

        Args:
            data_len (int): length of data
            apid (int): space packet APID
        """
        expected_version_and_id = (VERSION_NUMBER << 13) | (PACKET_TYPE << 12) | (SECONDARY_HEADER_FLAG << 11) | apid
        ret = create_space_packet_header(data_len, apid)
        parsed_version_and_id = ret[:2]
        parsed_sequence_control = ret[2:4]
        parsed_data_len = ret[4:]

        parsed_sequence_flags = parsed_sequence_control >> 14

        self.assertEqual(data_len, parsed_data_len, f"Parsed data length incorrect for {apid=} {data_len=}")
        self.assertEqual(
            expected_version_and_id,
            parsed_version_and_id,
            f"Parsed version and id incorrect for {apid=} {data_len=}. Expected={hex(expected_version_and_id)}, Actual={hex(parsed_version_and_id)}",
        )
        self.assertEqual(
            parsed_sequence_flags,
            SEQUENCE_FLAGS,
            f"Parsed sequence_flags incorrect for {apid=} {data_len=}. Expected={bin(SEQUENCE_FLAGS)}, Actual={bin(parsed_sequence_flags)}",
        )

    def test_create_space_packet_header(self):
        """Test that space packet header creation works for
        a variety of APIDs and data lengths"""
        for apid in range(1111, 1120):
            for data_length in range(2, 16):
                create_space_packet_header(data_len=data_length, apid=apid)


class TestCreateSpacePacket(unittest.TestCase):
    def test_frame_packet(self):
        """Test that a space packet can be correctly created and framed"""
        data_len = 5
        mock_packet_data = bytes(data_len)
        mock_sp_header = b"\xb1\xb2\xb3\xb4\xb5\xb6"
        mock_sp_data = mock_sp_header + mock_packet_data
        mock_crc_value = 2048
        apid = 1111
        with (
            patch("src.python.packet_parser.add_ancillary_header_to") as ancillary_hdr_patch,
            patch("src.python.packet_parser.create_space_packet_header") as sp_hdr_patch,
            patch("src.python.packet_parser.binascii.crc_hqx") as crc16_patch,
        ):
            ancillary_hdr_patch.return_value = mock_packet_data
            sp_hdr_patch.return_value = mock_sp_header
            crc16_patch.return_value = mock_crc_value

            pkt = frame_packet(mock_packet_data, apid)
            ancillary_hdr_patch.assert_called_with(mock_packet_data)
            sp_hdr_patch.assert_called_with(data_len + CRC_SIZE_BYTES, apid)
            crc16_patch.assert_called_with(mock_sp_data, 0)
            self.assertEqual(pkt, mock_sp_data + struct.pack(">H", mock_crc_value))


class TestParsePackets(unittest.TestCase):
    def test_extract_bits(self):
        value = 0b01100100
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=0, end_bit=0), 0)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=1, end_bit=1), 1)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=2, end_bit=2), 1)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=3, end_bit=3), 0)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=4, end_bit=4), 0)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=5, end_bit=5), 1)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=6, end_bit=6), 0)
        self.assertEqual(extract_bits(value, bit_width=8, start_bit=7, end_bit=7), 0)

    def test_parse_primary_header(self):
        data = bytes.fromhex("0801c001a79a")
        ret, new_start_byte = parse_primary_header(data, 0)

        expected_primary_header = {
            "version_number": 0,
            "packet_type": 0,
            "sec_hdr_flag": 1,
            "apid": 1,
            "sequence_flags": 3,
            "sequence_count": 1,
            "data_length": 42906,
        }

        self.assertEqual(new_start_byte, 6)
        self.assertDictEqual(ret, expected_primary_header)

    def test_parse_time_code_field(self):
        # 2026-01-01T12:00:00.761718
        seconds = 1767225600
        # 0.76171875 = 195/256
        fine_time = 195
        float_repr = seconds + (fine_time / 256)
        # Time code field is 5 bytes, but we're adding 1-byte of fill at position 0
        # This tests the start_byte argument in parse_time_code_field
        buffer = bytearray(6)
        struct.pack_into(">L", buffer, 1, seconds)
        struct.pack_into(">B", buffer, 5, fine_time)

        self.assertEqual(buffer.hex(), "006955b900c3")

        time, idx = parse_time_code_field(buffer, 1)

        self.assertEqual(time, float_repr)
        self.assertEqual(idx, 6)

    def test_parse_ancillary_data_field(self):
        frame_sync = bytes.fromhex("abcd1234")
        data_length = struct.pack(">H", 4)  # 2-byte data length
        data = bytes.fromhex("1122F2B2")
        # Represents 16-bit CRC. CRC should be computed over the whole packet, so a placeholder value is acceptable
        crc = bytes.fromhex("B2C3")

        expected = {"frame_sync": 0xABCD1234, "ancillary_data_length": 4, "data": data, "crc": 0xB2C3}

        # Parse starting at start_index. Zero-fill with start_index bytes before the actual packet data
        start_index = 3
        data_to_parse = bytes(start_index) + frame_sync + data_length + data + crc
        expected_new_start_index = len(data_to_parse)

        pkt, new_start_byte = parse_ancillary_data_field(data_to_parse, start_index)

        self.assertEqual(new_start_byte, expected_new_start_index)
        self.assertDictEqual(pkt, expected)

    def test_parse_packets_end_to_end(self):
        test_file = TEST_FILES_FOLDER / "3_packets.bin"
        with open(test_file, "rb") as f:
            data = f.read()
        packets, metadata = parse_packets(data)

        expected_packets = [
            {
                "version_number": 0,
                "packet_type": 0,
                "sec_hdr_flag": 1,
                "apid": 816,
                "sequence_flags": 3,
                "sequence_count": 1,
                "data_length": 17,
                "time": 1789234936.3515625,
                "frame_sync": 0xABCD1234,
                "ancillary_data_length": 4,
                "data": b"\x00\x00\x00\x00",
                "crc": 0x89A9,
            },
            {
                "version_number": 0,
                "packet_type": 0,
                "sec_hdr_flag": 1,
                "apid": 1088,
                "sequence_flags": 3,
                "sequence_count": 2,
                "data_length": 17,
                "time": 1789234936.3515625,
                "frame_sync": 0xABCD1234,
                "ancillary_data_length": 4,
                "data": b"\x00\x00\x00\x00",
                "crc": 0x80C3,
            },
            {
                "version_number": 0,
                "packet_type": 0,
                "sec_hdr_flag": 1,
                "apid": 1475,
                "sequence_flags": 3,
                "sequence_count": 3,
                "data_length": 17,
                "time": 1789234936.3515625,
                "frame_sync": 0xABCD1234,
                "ancillary_data_length": 4,
                "data": b"\x00\x00\x00\x00",
                "crc": 0x912A,
            },
        ]

        self.assertEqual(metadata.packets_parsed, 3)
        self.assertEqual(metadata.bad_crcs, 0)
        self.assertEqual(metadata.dropped_packets, 0)
        self.assertEqual(metadata.malformed_packets, 0)
        for packet, expected in zip(packets, expected_packets):
            self.assertDictEqual(packet, expected)


if __name__ == "__main__":
    unittest.main()
