"""Script to run the packet parser on an input file of packets"""

import argparse
import time
from pathlib import Path

from packet_parser import parse_packets

CURRENT_FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(prog="Run Python Packet Parser")
    parser.add_argument("f", type=str, help="Path to input file")
    args = parser.parse_args()

    with open(Path(args.f), "rb") as f:
        data = f.read()
    start = time.perf_counter()
    parsed_packets, metadata = parse_packets(data)
    end = time.perf_counter()

    duration = end - start
    data_size = len(data)
    speed_bytes_per_sec = data_size / duration
    speed_megabits_per_sec = speed_bytes_per_sec * 8 / 1e6

    print(f"Parsed {metadata.packets_parsed} packets in {duration}s, {speed_megabits_per_sec}mbps")


if __name__ == "__main__":
    main()
