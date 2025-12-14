#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import random
import argparse
from typing import Dict, Any

import isslwings as wings  # 기존 환경 유지
import pytest  # 안 쓰더라도 기존 의존성 유지

# ROOT_PATH = "../../../"
ROOT_PATH = "../../"
sys.path.append(os.path.dirname(__file__) + "/" + ROOT_PATH + "utils")
sys.path.append(os.path.dirname(__file__))

import c2a_enum_utils
import wings_utils
from fuzzing_helper import (
    CommandDBParser,
    FuzzingParamGenerator,
    generate_params_from_cmd_info,
    get_all_cmd_codes_from_enum,
)

# Cmd DB CSV 경로 (기존 코드 그대로)
CMD_DB_CSV_PATH = os.path.dirname(__file__) + "/" + ROOT_PATH + "/../../../tlm-cmd-db/CMD_DB/SAMPLE_MOBC_CMD_DB_CMD_DB.csv"


def build_cmd_json(cmd_name: str, cmd_code: int, params, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # params가 numpy/int 같은 타입일 수 있으니 JSON-friendly로 변환
    if isinstance(params, tuple):
        params = list(params)

    obj = {
        "cmd_name": cmd_name,
        "cmd_code": int(cmd_code),
        "params": params,
    }
    if meta:
        obj["meta"] = meta
    return obj


def pick_one_command(strategy: str, cmd_name: str | None, seed: int | None, max_params_strategy="random"):
    if seed is not None:
        random.seed(seed)

    c2a_enum = c2a_enum_utils.get_c2a_enum()

    cmd_db_parser = CommandDBParser(CMD_DB_CSV_PATH)
    enum_cmd_codes = get_all_cmd_codes_from_enum(c2a_enum)
    param_generator = FuzzingParamGenerator(strategy=max_params_strategy)

    # 기존 skip 룰(필요시 추가/정리)
    SKIP_SUBSTRS = [
        "MEM_LOAD",
        "CDRV_UTIL_HAL_TX",
        "TLM_MGR_START_TLM",
        "NOP",
        "TLM_MGR_REGISTER_REPLAY_TLM",  # Hang
    ]

    items = [(n, c) for (n, c) in enum_cmd_codes.items() if not any(s in n for s in SKIP_SUBSTRS)]
    if not items:
        raise RuntimeError("No commands to test after filtering.")

    if cmd_name:
        # 지정 커맨드
        found = [(n, c) for (n, c) in items if n == cmd_name]
        if not found:
            raise KeyError(f"cmd_name '{cmd_name}' not found (or filtered out).")
        cmd_name, cmd_code = found[0]
    else:
        # 랜덤 1개
        cmd_name, cmd_code = random.choice(items)

    cmd_info = cmd_db_parser.get_command_info(cmd_name)
    if cmd_info is None:
        cmd_info = {
            "code": cmd_code,
            "num_params": 0,
            "param_types": [],
            "param_descriptions": [],
            "description": "",
            "danger_flag": False,
        }

    params = generate_params_from_cmd_info(cmd_info, param_generator)
    return cmd_name, cmd_code, params


def udp_send_json(host: str, port: int, payload: Dict[str, Any]) -> None:
    import socket
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(data, (host, port))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst-host", default="127.0.0.1")
    ap.add_argument("--dst-port", type=int, default=3000, help="(2) executor_listener가 받을 포트")
    ap.add_argument("--cmd-name", default=None, help="지정 커맨드 이름 (없으면 랜덤)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--param-strategy", default="random", choices=["random", "min", "max", "edge"])
    args = ap.parse_args()

    cmd_name, cmd_code, params = pick_one_command(
        strategy="one",
        cmd_name=args.cmd_name,
        seed=args.seed,
        max_params_strategy=args.param_strategy,
    )

    payload = build_cmd_json(
        cmd_name, cmd_code, params,
        meta={"generator_pid": os.getpid()}
    )

    print(f"[GEN] send -> {args.dst_host}:{args.dst_port} : {payload}")
    udp_send_json(args.dst_host, args.dst_port, payload)


if __name__ == "__main__":
    main()
