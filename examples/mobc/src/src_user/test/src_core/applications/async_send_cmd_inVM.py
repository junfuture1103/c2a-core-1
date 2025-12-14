#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
import socket
from typing import Any

import isslwings as wings
import pytest

ROOT_PATH = "../../"
sys.path.append(os.path.dirname(__file__) + "/" + ROOT_PATH + "utils")
sys.path.append(os.path.dirname(__file__))

import c2a_enum_utils
import wings_utils

c2a_enum = c2a_enum_utils.get_c2a_enum()
ope = wings_utils.get_wings_operation()


class UDPTeeStdout:
    """
    sys.stdout을 대체해서:
      - 원래 stdout에도 쓰고
      - UDP로도 동일 라인을 전송
    """
    def __init__(self, udp_host: str, udp_port: int, original):
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.original = original
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def write(self, s: str) -> int:
        # stdout
        n = self.original.write(s)
        self.original.flush()

        # UDP (best-effort)
        try:
            if s:
                self.sock.sendto(s.encode("utf-8", errors="replace"), (self.udp_host, self.udp_port))
        except Exception:
            pass
        return n

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass


def send_command_tl(cmd_name, cmd_code, params, ti_offset=10000):
    """
    Timeline Command로 명령 전송 (기존 구현 유지)
    """
    try:
        tlm_HK = wings.util.generate_and_receive_tlm(
            ope, c2a_enum.Cmd_CODE_TG_GENERATE_RT_TLM, c2a_enum.Tlm_CODE_HK
        )
        current_ti = tlm_HK.get("HK.SH.TI", 0)
        future_ti = current_ti + ti_offset

        wings.util.send_tl_cmd(ope, future_ti, cmd_code, params)
        return "SUC"
    except Exception as e:
        print(f"Error sending TL {cmd_name}: {e}")
        return "ERR"


def parse_one_json(datagram: bytes) -> dict[str, Any]:
    # newline-delimited JSON 가정
    text = datagram.decode("utf-8", errors="replace").strip()
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="0.0.0.0")
    ap.add_argument("--listen-port", type=int, default=3000, help="(1) generator가 보내는 포트")
    ap.add_argument("--stdout-udp-host", default="127.0.0.1")
    ap.add_argument("--stdout-udp-port", type=int, default=3001, help="(3) stdout_receiver가 받을 포트")
    ap.add_argument("--ti-offset", type=int, default=10000)
    args = ap.parse_args()

    # stdout tee 설정: 모든 print가 UDP로도 나감
    sys.stdout = UDPTeeStdout(args.stdout_udp_host, args.stdout_udp_port, sys.__stdout__)
    sys.stderr = UDPTeeStdout(args.stdout_udp_host, args.stdout_udp_port, sys.__stderr__)

    print(f"[EXEC] listening on {args.listen_host}:{args.listen_port}")
    print(f"[EXEC] mirroring stdout to UDP {args.stdout_udp_host}:{args.stdout_udp_port}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.listen_host, args.listen_port))

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            obj = parse_one_json(data)
        except Exception as e:
            print(f"[EXEC] invalid json from {addr}: {e}")
            continue

        cmd_name = obj.get("cmd_name", "")
        cmd_code = obj.get("cmd_code", 0)
        params = obj.get("params", [])

        # cmd_code가 "0xABCD" 문자열로 넘어올 가능성까지 방어
        if isinstance(cmd_code, str):
            cmd_code = int(cmd_code, 0)

        print(f"[EXEC] recv from {addr}: cmd_name={cmd_name}, cmd_code=0x{int(cmd_code):04X}, params={params}")

        result = send_command_tl(cmd_name, int(cmd_code), params, ti_offset=args.ti_offset)
        print(f"[EXEC] result={result}")
        # 필요하면 여기서 result도 JSON으로 별도 포트로 쏠 수 있음


if __name__ == "__main__":
    main()
