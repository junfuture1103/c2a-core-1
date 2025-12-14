#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import isslwings as wings
import pytest

# ROOT_PATH = "../../../"
ROOT_PATH = "../../"
path = os.path.dirname(__file__) + "/" + ROOT_PATH + "utils"
print(path)

sys.path.append(os.path.dirname(__file__) + "/" + ROOT_PATH + "utils")
import c2a_enum_utils
import wings_utils

c2a_enum = c2a_enum_utils.get_c2a_enum()
ope = wings_utils.get_wings_operation()

@pytest.mark.real
@pytest.mark.sils
def test_event_utility():
    tlm_EH = wings.util.generate_and_receive_tlm(
        ope, c2a_enum.Cmd_CODE_TG_GENERATE_RT_TLM, c2a_enum.Tlm_CODE_EH
    )
    print("c2a_enum.Cmd_CODE_TG_GENERATE_RT_TLM", dir(c2a_enum))
    print("tlm_EH : ", tlm_EH)
    print("tlm_EH[EH.EVENT_UTIL.IS_ENABLED_EH_EXECUTION] : ", tlm_EH["EH.EVENT_UTIL.IS_ENABLED_EH_EXECUTION"])
    assert tlm_EH["EH.EVENT_UTIL.IS_ENABLED_EH_EXECUTION"] == "ENABLE"

def test_send_nop():
    wings.util.send_rt_cmd_and_confirm(
        ope, c2a_enum.Cmd_CODE_NOP, (), c2a_enum.Tlm_CODE_HK
    )

def test_tmgr_set_time():
    wings.util.send_rt_cmd_and_confirm(
        ope, c2a_enum.Cmd_CODE_TMGR_SET_TIME, (0xFFFFFFFF,), c2a_enum.Tlm_CODE_HK
    )
# ...existing code...
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


def send_mem_load_rt(address=0x20000000, sample_data=b'\x01\x02\x03\x04', strategy="sample"):
    """
    MEM_LOAD 계열 명령을 찾아서 RT로 전송한다.
    - enum에서 "MEM_LOAD"가 이름에 포함된 명령을 찾아 Cmd DB 정보로 파라미터를 생성하거나,
      정보가 없으면 안전한 샘플 파라미터(address, length, data)로 전송한다.
    Returns: send_command_rt의 반환값 또는 "SKIP"
    """
    cmd_db_parser = CommandDBParser(CMD_DB_CSV_PATH)
    enum_cmd_codes = get_all_cmd_codes_from_enum(c2a_enum)
    param_generator = FuzzingParamGenerator(strategy=strategy)

    for cmd_name, cmd_code in enum_cmd_codes.items():
        if "MEM_LOAD" in cmd_name:
            cmd_info = cmd_db_parser.get_command_info(cmd_name)
            if cmd_info is None:
                # 기본 안전 샘플 정보 (파라미터 개수/타입은 환경에 따라 조정 필요)
                cmd_info = {
                    'code': cmd_code,
                    'num_params': 3,
                    'param_types': ['uint32', 'uint32', 'byte_array'],
                    'param_descriptions': ['address', 'length', 'data_bytes'],
                    'description': 'Auto-generated sample for MEM_LOAD',
                    'danger_flag': True
                }

            # 가능한 경우 Cmd DB 기반으로 파라미터 생성 시도
            params = generate_params_from_cmd_info(cmd_info, param_generator)
            if not params:
                # 안전 샘플: (address, length, data_as_tuple)
                params = (address, len(sample_data), tuple(sample_data))

            print(f"Sending MEM_LOAD RT: {cmd_name} (0x{cmd_code:04X}) params={params}")
            return send_command_rt(cmd_name, cmd_code, params)

    print("MEM_LOAD 명령을 enum에서 찾을 수 없음")
    return "SKIP"

if __name__ == "__main__":
    test_send_nop()
    # send_mem_load_rt()

