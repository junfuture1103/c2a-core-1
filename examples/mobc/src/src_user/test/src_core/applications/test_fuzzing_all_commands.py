#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
퍼징을 위한 모든 커맨드 자동 전송 스크립트

이 스크립트는:
1. Cmd DB CSV에서 모든 명령과 파라미터 정보를 자동으로 파싱
2. c2a_enum에서 모든 명령 코드를 가져옴
3. 파라미터 타입에 따라 랜덤 값 생성
4. 모든 명령을 자동으로 전송
"""

import os
import sys
import csv
import random
import re

import isslwings as wings
import pytest

ROOT_PATH = "../../../"
sys.path.append(os.path.dirname(__file__) + "/" + ROOT_PATH + "utils")
sys.path.append(os.path.dirname(__file__))
import c2a_enum_utils
import wings_utils
from fuzzing_helper import (
    CommandDBParser,
    FuzzingParamGenerator,
    generate_params_from_cmd_info,
    get_all_cmd_codes_from_enum
)

c2a_enum = c2a_enum_utils.get_c2a_enum()
ope = wings_utils.get_wings_operation()

# Cmd DB CSV 경로
CMD_DB_CSV_PATH = os.path.dirname(__file__) + "/../../../../../../tlm-cmd-db/CMD_DB/SAMPLE_MOBC_CMD_DB_CMD_DB.csv"


# 함수들은 fuzzing_helper 모듈에서 import됨


def send_command_rt(cmd_name, cmd_code, params):
    """
    Realtime Command로 명령 전송
    
    Returns:
        str: 실행 결과 ("SUC", "PRM", "CNT", "ROE" 등)
    """
    try:
        result = wings.util.send_rt_cmd_and_confirm(
            ope, cmd_code, params, c2a_enum.Tlm_CODE_HK
        )
        return result
    except Exception as e:
        print(f"Error sending {cmd_name}: {e}")
        return "ERR"


def send_command_tl(cmd_name, cmd_code, params, ti_offset=10000):
    """
    Timeline Command로 명령 전송
    
    Args:
        ti_offset: 현재 TI로부터의 오프셋
    """
    try:
        # 현재 TI 가져오기 (HK 텔레메트리에서)
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


def send_command_bl(cmd_name, cmd_code, params, ti_offset=10000):
    """
    Block Command로 명령 전송
    """
    try:
        # 현재 TI 가져오기
        tlm_HK = wings.util.generate_and_receive_tlm(
            ope, c2a_enum.Cmd_CODE_TG_GENERATE_RT_TLM, c2a_enum.Tlm_CODE_HK
        )
        current_ti = tlm_HK.get("HK.SH.TI", 0)
        future_ti = current_ti + ti_offset
        
        ope.send_bl_cmd(future_ti, cmd_code, params)
        return "SUC"
    except Exception as e:
        print(f"Error sending BL {cmd_name}: {e}")
        return "ERR"


@pytest.mark.real
@pytest.mark.sils
def test_fuzz_all_commands_rt(strategy="random", max_commands=None):
    """
    모든 명령을 Realtime Command로 퍼징
    
    Args:
        strategy: "random", "min", "max", "edge" 중 하나
        max_commands: 최대 테스트할 명령 수 (None이면 전체)
    """
    print(f"\n=== Realtime Command 퍼징 시작 (strategy: {strategy}) ===")
    
    # 명령 정보 로드
    cmd_db_parser = CommandDBParser(CMD_DB_CSV_PATH)
    enum_cmd_codes = get_all_cmd_codes_from_enum(c2a_enum)
    param_generator = FuzzingParamGenerator(strategy=strategy)
    
    results = {
        "SUC": 0,
        "PRM": 0,
        "CNT": 0,
        "ROE": 0,
        "ERR": 0,
        "SKIP": 0
    }
    
    tested_commands = []
    
    # 명령 리스트 준비
    commands_to_test = list(enum_cmd_codes.items())
    if max_commands:
        commands_to_test = commands_to_test[:max_commands]
    
    # 모든 명령 테스트
    for cmd_name, cmd_code in commands_to_test:
        # Cmd DB에서 정보 가져오기
        cmd_info = cmd_db_parser.get_command_info(cmd_name)
        
        if cmd_info is None:
            # Cmd DB에 없으면 기본값 사용
            cmd_info = {
                'code': cmd_code,
                'num_params': 0,
                'param_types': [],
                'param_descriptions': [],
                'description': '',
                'danger_flag': False
            }
        
        # 파라미터 생성
        params = generate_params_from_cmd_info(cmd_info, param_generator)
        
        # 명령 전송
        print(f"Testing RT: {cmd_name} (0x{cmd_code:04X}) with params: {params}")
        try:
            result = send_command_rt(cmd_name, cmd_code, params)
        except Exception as e:
            print(f"  Exception: {e}")
            result = "ERR"
        
        results[result] = results.get(result, 0) + 1
        tested_commands.append((cmd_name, cmd_code, params, result))
        
        # 결과 출력
        print(f"  Result: {result}")
    
    # 결과 요약
    print("\n=== 퍼징 결과 요약 ===")
    print(f"총 테스트한 명령 수: {len(tested_commands)}")
    for result_type, count in results.items():
        if count > 0:
            print(f"  {result_type}: {count}")
    
    # 실패한 명령 출력
    failed_commands = [cmd for cmd in tested_commands if cmd[3] not in ["SUC", "PRM"]]
    if failed_commands:
        print("\n=== 실패한 명령 목록 ===")
        for cmd_name, cmd_code, params, result in failed_commands:
            print(f"  {cmd_name} (0x{cmd_code:04X}): {result}")


@pytest.mark.real
@pytest.mark.sils
def test_fuzz_all_commands_tl():
    """
    모든 명령을 Timeline Command로 퍼징
    """
    print("\n=== Timeline Command 퍼징 시작 ===")
    
    cmd_db_commands = parse_cmd_db_csv(CMD_DB_CSV_PATH)
    enum_cmd_codes = get_all_cmd_codes_from_enum()
    
    results = {"SUC": 0, "ERR": 0}
    
    # 샘플 명령만 테스트 (전체는 시간이 오래 걸림)
    sample_commands = list(enum_cmd_codes.items())[:10]  # 처음 10개만
    
    for cmd_name, cmd_code in sample_commands:
        if cmd_name in cmd_db_commands:
            cmd_info = cmd_db_commands[cmd_name]
        else:
            cmd_info = CommandInfo()
            cmd_info.name = cmd_name
            cmd_info.code = cmd_code
        
        params = generate_params_for_cmd(cmd_info)
        
        print(f"Testing TL: {cmd_name} (0x{cmd_code:04X})")
        result = send_command_tl(cmd_name, cmd_code, params)
        results[result] = results.get(result, 0) + 1
    
    print(f"\nTL 퍼징 결과: {results}")


def get_command_info_from_db(cmd_name):
    """
    Cmd DB에서 특정 명령의 정보를 가져옴 (유틸리티 함수)
    """
    cmd_db_commands = parse_cmd_db_csv(CMD_DB_CSV_PATH)
    return cmd_db_commands.get(cmd_name)


def list_all_commands():
    """
    모든 명령 목록과 파라미터 정보를 출력 (디버깅용)
    """
    cmd_db_parser = CommandDBParser(CMD_DB_CSV_PATH)
    enum_cmd_codes = get_all_cmd_codes_from_enum(c2a_enum)
    
    print(f"\n=== 명령 목록 (총 {len(enum_cmd_codes)}개) ===\n")
    
    for cmd_name, cmd_code in sorted(enum_cmd_codes.items()):
        cmd_info = cmd_db_parser.get_command_info(cmd_name)
        if cmd_info:
            print(f"{cmd_name} (0x{cmd_code:04X}):")
            print(f"  Params: {cmd_info['num_params']}")
            print(f"  Description: {cmd_info['description']}")
            if cmd_info['danger_flag']:
                print(f"  [DANGER]")
            for i in range(cmd_info['num_params']):
                param_type = cmd_info['param_types'][i] if i < len(cmd_info['param_types']) else "unknown"
                param_desc = cmd_info['param_descriptions'][i] if i < len(cmd_info['param_descriptions']) else ""
                print(f"    [{i}] {param_type}: {param_desc}")
        else:
            print(f"{cmd_name} (0x{cmd_code:04X}): [Cmd DB에 없음]")


if __name__ == "__main__":
    # 직접 실행 시 명령 목록 출력
    list_all_commands()
    
    # 또는 특정 명령 정보 확인
    # cmd_info = get_command_info_from_db("NOP")
    # if cmd_info:
    #     print(f"NOP 명령 정보:")
    #     print(f"  Code: 0x{cmd_info.code:04X}")
    #     print(f"  Params: {cmd_info.num_params}")
    #     print(f"  Description: {cmd_info.description}")

