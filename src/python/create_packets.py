"""Script to create n packets of random data"""
import argparse
import random
from pathlib import Path

from packet_parser import frame_packet

CURRENT_FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(
        prog="CCSDS Packet Creator"
    )
    parser.add_argument("n", type=int, help="Number of packets to create")
    args = parser.parse_args()

    outfile = Path(CURRENT_FOLDER, f"{args.n}_packets.bin")
    total_file_size = 0

    with open(outfile, "wb") as f:
        for _ in range(args.n):
            data_length = random.randint(1, 65520)
            apid = random.randint(1, 2^11 - 1)
            rand_pkt_data = random.randbytes(data_length)
            pkt = frame_packet(rand_pkt_data, apid)
            total_file_size += len(pkt)
            f.write(pkt)
    print(f"Wrote {args.n} packets to {outfile}, totaling {total_file_size/1e6:.0f}MB!")

if __name__ == "__main__":
    main()