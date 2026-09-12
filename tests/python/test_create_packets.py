import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_PYTHON = REPO_ROOT / "src" / "python"
sys.path.insert(0, str(SRC_PYTHON))

from src.python import create_packets
from src.python.create_packets import main, parse_args


class TestCreatePackets(unittest.TestCase):
    def setUp(self):
        """Create a temporary directore prior to each test"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the temporary directory after each test"""
        shutil.rmtree(self.temp_dir)

    def test_parse_args(self):
        """Test parse_args"""
        valid_args = [("1", "n/a"), ("2", "n/a"), ("-1", "path/to/file")]
        for arg in valid_args:
            parsed_args = parse_args(arg)
            self.assertEqual(parsed_args.n, int(arg[0]))
            self.assertEqual(parsed_args.outfile, arg[1])

    def test_main_invalid_args(self):
        """Test that a ValueError is raised if invalid values are passed in"""
        with self.assertRaises(ValueError):
            main(["-1"])
        with self.assertRaises(SystemExit):
            main(["asdf"])
        with self.assertRaises(SystemExit):
            main(["10.123"])

    def test_main_create_outfile(self):
        """End-to-end test validating a created output file"""
        outfile = Path(self.temp_dir, "test_outfile.bin")
        apid = 4444
        data_length = 12
        with (
            patch.object(create_packets, "frame_packet") as frame_packet_patch,
            patch.object(create_packets, "random") as random_patch,
        ):
            random_patch.randint.side_effect = [data_length, apid]
            random_patch.randbytes.return_value = bytes(data_length)
            frame_packet_patch.return_value = bytes(data_length)
            main(["1", str(outfile)])

            random_patch.randbytes.assert_called_with(data_length)
            frame_packet_patch.assert_called_with(bytes(data_length), apid)
        with open(outfile, "rb") as f:
            written_data = f.read()

        self.assertEqual(written_data, frame_packet_patch.return_value)


if __name__ == "__main__":
    unittest.main()
