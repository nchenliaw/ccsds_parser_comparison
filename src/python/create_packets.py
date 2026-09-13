"""Script to create n packets of random data"""

import argparse
import random
import sys
from pathlib import Path

from packet_parser import frame_packet

CURRENT_FOLDER = Path(__file__).resolve().parent


def parse_args(args: list[str]) -> argparse.Namespace:
    """Parse input args"""
    parser = argparse.ArgumentParser(prog=__file__)
    parser.add_argument("n", type=int, help="Number of packets to create")
    parser.add_argument("outfile", type=str, default=None, nargs="?", help="Filepath to output file")
    return parser.parse_args(args)


def main(args):
    args = parse_args(args)
    if args.n <= 0:
        raise ValueError(f"Argument n for number of packets must be greater than 1. You entered {args.n}")
    outfile = args.outfile or Path(f"{args.n}_packets.bin")
    total_file_size = 0

    with open(outfile, "wb") as f:
        for _ in range(args.n):
            data_length = random.randint(1, 65522)
            apid = random.randint(1, 2**11 - 1)
            rand_pkt_data = random.randbytes(data_length)
            pkt = frame_packet(rand_pkt_data, apid)
            total_file_size += len(pkt)
            f.write(pkt)
    print(f"Wrote {args.n} packets to {outfile}, totaling {total_file_size / 1e6:.0f}MB!")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))  # pragma: no cover
