#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import socket
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="0.0.0.0")
    ap.add_argument("--listen-port", type=int, default=3001)
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.listen_host, args.listen_port))

    print(f"[STDOUT-RX] listening on {args.listen_host}:{args.listen_port}")

    while True:
        data, addr = sock.recvfrom(65535)
        line = data.decode("utf-8", errors="replace")
        # executor의 print output이 그대로 들어옴 (개행 포함)
        sys.stdout.write(line)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
