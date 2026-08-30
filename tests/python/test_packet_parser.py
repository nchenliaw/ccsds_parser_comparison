import struct
import sys
import unittest
import binascii
from unittest.mock import patch, MagicMock
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.python.packet_parser import (
    FRAME_SYNC_HEADER,
    VERSION_NUMBER,
    PACKET_TYPE,
    SECONDARY_HEADER_FLAG,
    SEQUENCE_FLAGS,
    CRC_SIZE_BYTES,
    add_ancillary_header_to,
    create_space_packet_header,
    frame_packet,
)


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
            f"Parsed sequence_flags incorrect for {apid=} {data_len=}. Expected={bin(SEQUENCE_FLAGS)}, Actual={bin(parsed_sequence_flagsS)}",
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
            patch("src.python.packet_parser.binascii.crc32") as crc32_patch,
        ):
            ancillary_hdr_patch.return_value = mock_packet_data
            sp_hdr_patch.return_value = mock_sp_header
            crc32_patch.return_value = mock_crc_value

            pkt = frame_packet(mock_packet_data, apid)

            ancillary_hdr_patch.assert_called_with(mock_packet_data)
            sp_hdr_patch.assert_called_with(data_len + CRC_SIZE_BYTES, apid)
            crc32_patch.assert_called_with(mock_sp_data)
            self.assertEqual(pkt, mock_sp_data + struct.pack(">I", mock_crc_value))


if __name__ == "__main__":
    unittest.main()
