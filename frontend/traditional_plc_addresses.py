#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传统模式PLC地址定义模块
存放传统模式所有PLC寄存器地址和线圈地址的定义

基于原始PLC地址表转换为Modbus地址：
- M线圈: 直接对应 (M191 → 191)
- D数据寄存器: 直接对应 (D700 → 700)  
- HD保持寄存器: 基址49280 + 偏移 (HD111 → 49280+111 = 49391)
- HM保持线圈: 基址49408 + 偏移 (HM1 → 49408+1 = 49409)

作者：L
创建日期：2025-08-04
"""

# 6个料斗的监控地址映射（实时数据，只读）
TRADITIONAL_MONITORING_ADDRESSES = {
    1: {
        'Weight': 700,
        'TargetReached': 191,
        'CoarseAdd': 211,
        'FineAdd': 212,
        'Jog': 120,
    },
    2: {
        'Weight': 702,
        'TargetReached': 192,
        'CoarseAdd': 213,
        'FineAdd': 214,
        'Jog': 121,
    },
    3: {
        'Weight': 704,
        'TargetReached': 193,
        'CoarseAdd': 215,
        'FineAdd': 216,
        'Jog': 122,
    },
    4: {
        'Weight': 706,
        'TargetReached': 194,
        'CoarseAdd': 217,
        'FineAdd': 218,
        'Jog': 123,
    },
    5: {
        'Weight': 708,
        'TargetReached': 195,
        'CoarseAdd': 219,
        'FineAdd': 220,
        'Jog': 124,
    },
    6: {
        'Weight': 710,
        'TargetReached': 196,
        'CoarseAdd': 221,
        'FineAdd': 222,
        'Jog': 125,
    }
}

TRADITIONAL_CONTROL_ADDRESSES = {
    1: {
        'Start': 110,
        'Jog': 120,
        'Clear': 181,
        'Discharge': 51,
        'Clean': 21,
    },
    2: {
        'Start': 111,
        'Jog': 121,
        'Clear': 182,
        'Discharge': 52,
        'Clean': 22,
    },
    3: {
        'Start': 112,
        'Jog': 122,
        'Clear': 183,
        'Discharge': 53,
        'Clean': 23,
    },
    4: {
        'Start': 113,
        'Jog': 123,
        'Clear': 184,
        'Discharge': 54,
        'Clean': 24,
    },
    5: {
        'Start': 114,
        'Jog': 124,
        'Clear': 185,
        'Discharge': 55,
        'Clean': 25,
    },
    6: {
        'Start': 115,
        'Jog': 125,
        'Clear': 186,
        'Discharge': 56,
        'Clean': 26,
    }
}

TRADITIONAL_PARAMETER_ADDRESSES = {
    1: {
        'TargetWeight': 41199,      # 目标重量 (HD111 → 41088+111)
        'CoarseSpeed': 41388,       # 快加速度 (HD300 → 41088+300)
        'FineSpeed': 41390,         # 慢加速度 (HD302 → 41088+302)
        'CoarseAdvance': 41588,     # 快加提前量 (HD500 → 41088+500)
        'FineAdvance': 41612,       # 慢加提前量 (HD524 → 41088+524)
    },
    2: {
        'TargetWeight': 41200,      # 目标重量 (HD112 → 41088+112)
        'CoarseSpeed': 41408,       # 快加速度 (HD320 → 41088+320)
        'FineSpeed': 41410,         # 慢加速度 (HD322 → 41088+322)
        'CoarseAdvance': 41592,     # 快加提前量 (HD504 → 41088+504)
        'FineAdvance': 41614,       # 慢加提前量 (HD526 → 41088+526)
    },
    3: {
        'TargetWeight': 41201,      # 目标重量 (HD113 → 41088+113)
        'CoarseSpeed': 41428,       # 快加速度 (HD340 → 41088+340)
        'FineSpeed': 41430,         # 慢加速度 (HD342 → 41088+342)
        'CoarseAdvance': 41596,     # 快加提前量 (HD508 → 41088+508)
        'FineAdvance': 41616,       # 慢加提前量 (HD528 → 41088+528)
    },
    4: {
        'TargetWeight': 41202,      # 目标重量 (HD114 → 41088+114)
        'CoarseSpeed': 41448,       # 快加速度 (HD360 → 41088+360)
        'FineSpeed': 41450,         # 慢加速度 (HD362 → 41088+362)
        'CoarseAdvance': 41600,     # 快加提前量 (HD512 → 41088+512)
        'FineAdvance': 41618,       # 慢加提前量 (HD530 → 41088+530)
    },
    5: {
        'TargetWeight': 41203,      # 目标重量 (HD115 → 41088+115)
        'CoarseSpeed': 41468,       # 快加速度 (HD380 → 41088+380)
        'FineSpeed': 41470,         # 慢加速度 (HD382 → 41088+382)
        'CoarseAdvance': 41604,     # 快加提前量 (HD516 → 41088+516)
        'FineAdvance': 41620,       # 慢加提前量 (HD532 → 41088+532)
    },
    6: {
        'TargetWeight': 41204,      # 目标重量 (HD116 → 41088+116)
        'CoarseSpeed': 41488,       # 快加速度 (HD400 → 41088+400)
        'FineSpeed': 41490,         # 慢加速度 (HD402 → 41088+402)
        'CoarseAdvance': 41608,     # 快加提前量 (HD520 → 41088+520)
        'FineAdvance': 41622,       # 慢加提前量 (HD534 → 41088+534)
    }
}

TRADITIONAL_STATE_ADDRESSES = {
    1: {'Disable': 49409},          # 禁用状态 (HM1 → 49408+1)
    2: {'Disable': 49410},          # 禁用状态 (HM2 → 49408+2)
    3: {'Disable': 49411},          # 禁用状态 (HM3 → 49408+3)
    4: {'Disable': 49412},          # 禁用状态 (HM4 → 49408+4)
    5: {'Disable': 49413},          # 禁用状态 (HM5 → 49408+5)
    6: {'Disable': 49414},          # 禁用状态 (HM6 → 49408+6)
}

TRADITIONAL_GLOBAL_ADDRESSES = {
    'GlobalStart': 300,
    'GlobalStop': 301,
    'GlobalDischarge': 5,
    'GlobalClear': 6,
    'GlobalClean': 7,
}

TRADITIONAL_CALIBRATION_ADDRESSES = {
    1: {
        'ZeroCalibration': 11,
        'WeightCalibration': 3,
    },
    2: {
        'ZeroCalibration': 12,
        'WeightCalibration': 32,
    },
    3: {
        'ZeroCalibration': 13,
        'WeightCalibration': 33,
    },
    4: {
        'ZeroCalibration': 14,
        'WeightCalibration': 34,
    },
    5: {
        'ZeroCalibration': 15,
        'WeightCalibration': 35,
    },
    6: {
        'ZeroCalibration': 16,
        'WeightCalibration': 36,
    }
}

TRADITIONAL_SYSTEM_ADDRESSES = {
    'GlobalTargetWeight': 41092,
    'AllowableError': 41096,
    'CleanSpeed': 41378,
    
    'JogTime': 41158,
    'JogInterval': 41160,
    'DebounceTime': 41168,
    'DischargeTime': 41178,
    'DoorDelay': 41179,
    
    'ZeroTrackRange': 41288,
    'ZeroTrackTime': 41289,
    'ZeroClearRange': 41290,
    
    'StabilityRange': 41291,
    'StabilityTime': 41292,
    'FilterLevelA': 41293,
    'FilterLevelB': 41294,
    
    'MinDivision': 41188,
    'MaxCapacity': 41192,
    'StandardWeight': 41098,
}

TRADITIONAL_SYSTEM_CONTROL_ADDRESSES = {
    'ModuleInit': 102,
    'FeedDataInit': 0,
    'ModuleDataRead': 101,
    'SystemSave': 100,
}

def get_traditional_weight_address(bucket_id: int) -> int:
    if bucket_id not in TRADITIONAL_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return TRADITIONAL_MONITORING_ADDRESSES[bucket_id]['Weight']

def get_traditional_monitoring_address(bucket_id: int, monitor_type: str) -> int:
    if bucket_id not in TRADITIONAL_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if monitor_type not in TRADITIONAL_MONITORING_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的监控类型: {monitor_type}")
    
    return TRADITIONAL_MONITORING_ADDRESSES[bucket_id][monitor_type]

def get_traditional_control_address(bucket_id: int, control_type: str) -> int:
    if bucket_id not in TRADITIONAL_CONTROL_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if control_type not in TRADITIONAL_CONTROL_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的控制类型: {control_type}")
    
    return TRADITIONAL_CONTROL_ADDRESSES[bucket_id][control_type]

def get_traditional_parameter_address(bucket_id: int, param_type: str) -> int:
    if bucket_id not in TRADITIONAL_PARAMETER_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if param_type not in TRADITIONAL_PARAMETER_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的参数类型: {param_type}")
    
    return TRADITIONAL_PARAMETER_ADDRESSES[bucket_id][param_type]

def get_traditional_disable_address(bucket_id: int) -> int:
    if bucket_id not in TRADITIONAL_STATE_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return TRADITIONAL_STATE_ADDRESSES[bucket_id]['Disable']

def get_traditional_global_address(control_type: str) -> int:
    if control_type not in TRADITIONAL_GLOBAL_ADDRESSES:
        raise ValueError(f"无效的全局控制类型: {control_type}")
    
    return TRADITIONAL_GLOBAL_ADDRESSES[control_type]

def get_traditional_calibration_address(bucket_id: int, calib_type: str) -> int:
    if bucket_id not in TRADITIONAL_CALIBRATION_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if calib_type not in TRADITIONAL_CALIBRATION_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的校准类型: {calib_type}")
    
    return TRADITIONAL_CALIBRATION_ADDRESSES[bucket_id][calib_type]

def get_traditional_system_address(system_param: str) -> int:
    if system_param not in TRADITIONAL_SYSTEM_ADDRESSES:
        raise ValueError(f"无效的系统参数: {system_param}")
    
    return TRADITIONAL_SYSTEM_ADDRESSES[system_param]

def get_traditional_system_control_address(control_type: str) -> int:
    if control_type not in TRADITIONAL_SYSTEM_CONTROL_ADDRESSES:
        raise ValueError(f"无效的系统控制类型: {control_type}")
    
    return TRADITIONAL_SYSTEM_CONTROL_ADDRESSES[control_type]

def get_all_traditional_weight_addresses() -> list:
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['Weight'] for i in range(1, 7)]

def get_all_traditional_target_reached_addresses() -> list:
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['TargetReached'] for i in range(1, 7)]

def get_all_traditional_coarse_add_addresses() -> list:
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['CoarseAdd'] for i in range(1, 7)]

def get_all_traditional_fine_add_addresses() -> list:
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['FineAdd'] for i in range(1, 7)]

def get_all_traditional_start_addresses() -> list:
    return [TRADITIONAL_CONTROL_ADDRESSES[i]['Start'] for i in range(1, 7)]

def get_all_traditional_discharge_addresses() -> list:
    return [TRADITIONAL_CONTROL_ADDRESSES[i]['Discharge'] for i in range(1, 7)]

def get_all_traditional_disable_addresses() -> list:
    return [TRADITIONAL_STATE_ADDRESSES[i]['Disable'] for i in range(1, 7)]

def get_traditional_bucket_all_addresses(bucket_id: int) -> dict:
    if bucket_id not in range(1, 7):
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return {
        'monitoring': TRADITIONAL_MONITORING_ADDRESSES[bucket_id],
        'control': TRADITIONAL_CONTROL_ADDRESSES[bucket_id],
        'parameter': TRADITIONAL_PARAMETER_ADDRESSES[bucket_id],
        'state': TRADITIONAL_STATE_ADDRESSES[bucket_id],
        'calibration': TRADITIONAL_CALIBRATION_ADDRESSES[bucket_id]
    }

def validate_traditional_bucket_id(bucket_id: int) -> bool:
    return bucket_id in range(1, 7)

def get_traditional_address_info() -> dict:
    return {
        'bucket_count': 6,
        'monitoring_addresses_per_bucket': len(TRADITIONAL_MONITORING_ADDRESSES[1]),
        'control_addresses_per_bucket': len(TRADITIONAL_CONTROL_ADDRESSES[1]),
        'parameter_addresses_per_bucket': len(TRADITIONAL_PARAMETER_ADDRESSES[1]),
        'global_addresses': len(TRADITIONAL_GLOBAL_ADDRESSES),
        'system_addresses': len(TRADITIONAL_SYSTEM_ADDRESSES),
        'system_control_addresses': len(TRADITIONAL_SYSTEM_CONTROL_ADDRESSES),
        'total_addresses': (
            len(TRADITIONAL_MONITORING_ADDRESSES) * len(TRADITIONAL_MONITORING_ADDRESSES[1]) +
            len(TRADITIONAL_CONTROL_ADDRESSES) * len(TRADITIONAL_CONTROL_ADDRESSES[1]) +
            len(TRADITIONAL_PARAMETER_ADDRESSES) * len(TRADITIONAL_PARAMETER_ADDRESSES[1]) +
            len(TRADITIONAL_STATE_ADDRESSES) * len(TRADITIONAL_STATE_ADDRESSES[1]) +
            len(TRADITIONAL_CALIBRATION_ADDRESSES) * len(TRADITIONAL_CALIBRATION_ADDRESSES[1]) +
            len(TRADITIONAL_GLOBAL_ADDRESSES) +
            len(TRADITIONAL_SYSTEM_ADDRESSES) +
            len(TRADITIONAL_SYSTEM_CONTROL_ADDRESSES)
        )
    }