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

作者：AI助手
创建日期：2025-08-04
"""

# 6个料斗的监控地址映射（实时数据，只读）
TRADITIONAL_MONITORING_ADDRESSES = {
    1: {
        'Weight': 700,              # 实时重量 (D700)
        'TargetReached': 191,       # 到量状态 (M191)
        'CoarseAdd': 211,           # 快加状态 (M211)
        'FineAdd': 212,             # 慢加状态 (M212)
        'Jog': 120,                 # 点动状态 (M120)    
    },
    2: {
        'Weight': 702,              # 实时重量 (D702)
        'TargetReached': 192,       # 到量状态 (M192)
        'CoarseAdd': 213,           # 快加状态 (M213)
        'FineAdd': 214,             # 慢加状态 (M214)
        'Jog': 121,                 # 点动状态 (M121)    
    },
    3: {
        'Weight': 704,              # 实时重量 (D704)
        'TargetReached': 193,       # 到量状态 (M193)
        'CoarseAdd': 215,           # 快加状态 (M215)
        'FineAdd': 216,             # 慢加状态 (M216)
        'Jog': 122,                 # 点动状态 (M122)    
    },
    4: {
        'Weight': 706,              # 实时重量 (D706)
        'TargetReached': 194,       # 到量状态 (M194)
        'CoarseAdd': 217,           # 快加状态 (M217)
        'FineAdd': 218,             # 慢加状态 (M218)
        'Jog': 123,                 # 点动状态 (M123)    
    },
    5: {
        'Weight': 708,              # 实时重量 (D708)
        'TargetReached': 195,       # 到量状态 (M195)
        'CoarseAdd': 219,           # 快加状态 (M219)
        'FineAdd': 220,             # 慢加状态 (M220)
        'Jog': 124,                 # 点动状态 (M124)    
    },
    6: {
        'Weight': 710,              # 实时重量 (D710)
        'TargetReached': 196,       # 到量状态 (M196)
        'CoarseAdd': 221,           # 快加状态 (M221)
        'FineAdd': 222,             # 慢加状态 (M222)
        'Jog': 125,                 # 点动状态 (M125)    
    }
}

# 6个料斗的控制地址映射（脉冲写入）
TRADITIONAL_CONTROL_ADDRESSES = {
    1: {
        'Start': 110,               # 启动 (M110)
        'Jog': 120,                 # 点动 (M120)
        'Clear': 181,               # 清零 (M181)
        'Discharge': 51,            # 放料 (M51)
        'Clean': 21,                # 清料 (M21)
    },
    2: {
        'Start': 111,               # 启动 (M111)
        'Jog': 121,                 # 点动 (M121)
        'Clear': 182,               # 清零 (M182)
        'Discharge': 52,            # 放料 (M52)
        'Clean': 22,                # 清料 (M22)
    },
    3: {
        'Start': 112,               # 启动 (M112)
        'Jog': 122,                 # 点动 (M122)
        'Clear': 183,               # 清零 (M183)
        'Discharge': 53,            # 放料 (M53)
        'Clean': 23,                # 清料 (M23)
    },
    4: {
        'Start': 113,               # 启动 (M113)
        'Jog': 123,                 # 点动 (M123)
        'Clear': 184,               # 清零 (M184)
        'Discharge': 54,            # 放料 (M54)
        'Clean': 24,                # 清料 (M24)
    },
    5: {
        'Start': 114,               # 启动 (M114)
        'Jog': 124,                 # 点动 (M124)
        'Clear': 185,               # 清零 (M185)
        'Discharge': 55,            # 放料 (M55)
        'Clean': 25,                # 清料 (M25)
    },
    6: {
        'Start': 115,               # 启动 (M115)
        'Jog': 125,                 # 点动 (M125)
        'Clear': 186,               # 清零 (M186)
        'Discharge': 56,            # 放料 (M56)
        'Clean': 26,                # 清料 (M26)
    }
}

# 6个料斗的参数地址映射（读写）
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

# 6个料斗的状态地址映射（读写保持）
TRADITIONAL_STATE_ADDRESSES = {
    1: {'Disable': 49409},          # 禁用状态 (HM1 → 49408+1)
    2: {'Disable': 49410},          # 禁用状态 (HM2 → 49408+2)
    3: {'Disable': 49411},          # 禁用状态 (HM3 → 49408+3)
    4: {'Disable': 49412},          # 禁用状态 (HM4 → 49408+4)
    5: {'Disable': 49413},          # 禁用状态 (HM5 → 49408+5)
    6: {'Disable': 49414},          # 禁用状态 (HM6 → 49408+6)
}

# 全局控制地址映射（脉冲写入）
TRADITIONAL_GLOBAL_ADDRESSES = {
    'GlobalStart': 300,             # 总启动 (M300)
    'GlobalStop': 301,              # 总停止 (M301)
    'GlobalDischarge': 5,           # 总放料 (M5)
    'GlobalClear': 6,               # 总清零 (M6)
    'GlobalClean': 7,               # 总清料 (M7)
}

# 校准相关地址映射（脉冲写入）
TRADITIONAL_CALIBRATION_ADDRESSES = {
    1: {
        'ZeroCalibration': 12,      # 零点标定 (M12)
        'WeightCalibration': 3,     # 重量校准 (M3)
    },
    2: {
        'ZeroCalibration': 12,      # 零点标定 (M12) - 注意：原表中可能有误，暂用M12
        'WeightCalibration': 32,    # 重量校准 (M32)
    },
    3: {
        'ZeroCalibration': 13,      # 零点标定 (M13)
        'WeightCalibration': 33,    # 重量校准 (M33)
    },
    4: {
        'ZeroCalibration': 14,      # 零点标定 (M14)
        'WeightCalibration': 34,    # 重量校准 (M34)
    },
    5: {
        'ZeroCalibration': 15,      # 零点标定 (M15)
        'WeightCalibration': 35,    # 重量校准 (M35)
    },
    6: {
        'ZeroCalibration': 16,      # 零点标定 (M16)
        'WeightCalibration': 36,    # 重量校准 (M36)
    }
}

# 系统参数地址映射（读写）
TRADITIONAL_SYSTEM_ADDRESSES = {
    # 全局参数
    'GlobalTargetWeight': 41092,    # 总目标重量 (HD4 → 41088+4)
    'AllowableError': 41096,        # 允许误差 (HD8 → 41088+8)
    'CleanSpeed': 41378,            # 清料速度 (HD290 → 41088+290)
    
    # 时间参数
    'JogTime': 49350,               # 点动时间 (HD70 → 49280+70)
    'JogInterval': 49352,           # 点动间隔 (HD72 → 49280+72)
    'DebounceTime': 49340,          # 消抖时间 (HD60 → 49280+60)
    'DischargeTime': 49370,         # 放料时间 (HD90 → 49280+90)
    'DoorDelay': 49371,             # 关门延时 (HD91 → 49280+91)
    
    # 零点追踪参数
    'ZeroTrackRange': 49480,        # 零点追踪范围 (HD200 → 49280+200)
    'ZeroTrackTime': 49481,         # 零点追踪时间 (HD201 → 49280+201)
    'ZeroClearRange': 49482,        # 清零范围% (HD202 → 49280+202)
    
    # 稳定性参数
    'StabilityRange': 49483,        # 判稳范围 (HD203 → 49280+203)
    'StabilityTime': 49484,         # 判稳时间 (HD204 → 49280+204)
    'FilterLevelA': 49485,          # 滤波等级A (HD205 → 49280+205)
    'FilterLevelB': 49486,          # 滤波等级B (HD206 → 49280+206)
    
    # 量程参数
    'MinDivision': 49380,           # 最小分度 (HD100 → 49280+100)
    'MaxCapacity': 49384,           # 最大量程 (HD104 → 49280+104)
}

# 系统初始化地址映射（脉冲写入）
TRADITIONAL_SYSTEM_CONTROL_ADDRESSES = {
    'ModuleInit': 102,              # 模块初始化 (M102)
    'FeedDataInit': 0,              # 加料数据初始化 (M0)
    'ModuleDataRead': 101,          # 模块数据读取 (M101)
    'SystemSave': 100,              # 系统保存 (M100)
}

# ==================== Helper函数 ====================

def get_traditional_weight_address(bucket_id: int) -> int:
    """
    获取指定料斗的实时重量地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        
    Returns:
        int: 重量寄存器地址
        
    Raises:
        ValueError: 如果料斗ID无效
    """
    if bucket_id not in TRADITIONAL_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return TRADITIONAL_MONITORING_ADDRESSES[bucket_id]['Weight']

def get_traditional_monitoring_address(bucket_id: int, monitor_type: str) -> int:
    """
    获取指定料斗的监控地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        monitor_type (str): 监控类型 ('Weight', 'TargetReached', 'CoarseAdd', 'FineAdd')
        
    Returns:
        int: 监控地址
        
    Raises:
        ValueError: 如果料斗ID或监控类型无效
    """
    if bucket_id not in TRADITIONAL_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if monitor_type not in TRADITIONAL_MONITORING_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的监控类型: {monitor_type}")
    
    return TRADITIONAL_MONITORING_ADDRESSES[bucket_id][monitor_type]

def get_traditional_control_address(bucket_id: int, control_type: str) -> int:
    """
    获取指定料斗的控制地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        control_type (str): 控制类型 ('Start', 'Jog', 'Clear', 'Discharge', 'Clean')
        
    Returns:
        int: 控制地址
        
    Raises:
        ValueError: 如果料斗ID或控制类型无效
    """
    if bucket_id not in TRADITIONAL_CONTROL_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if control_type not in TRADITIONAL_CONTROL_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的控制类型: {control_type}")
    
    return TRADITIONAL_CONTROL_ADDRESSES[bucket_id][control_type]

def get_traditional_parameter_address(bucket_id: int, param_type: str) -> int:
    """
    获取指定料斗的参数地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        param_type (str): 参数类型 ('TargetWeight', 'CoarseSpeed', 'FineSpeed', 'CoarseAdvance', 'FineAdvance')
        
    Returns:
        int: 参数地址
        
    Raises:
        ValueError: 如果料斗ID或参数类型无效
    """
    if bucket_id not in TRADITIONAL_PARAMETER_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if param_type not in TRADITIONAL_PARAMETER_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的参数类型: {param_type}")
    
    return TRADITIONAL_PARAMETER_ADDRESSES[bucket_id][param_type]

def get_traditional_disable_address(bucket_id: int) -> int:
    """
    获取指定料斗的禁用地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        
    Returns:
        int: 禁用地址
        
    Raises:
        ValueError: 如果料斗ID无效
    """
    if bucket_id not in TRADITIONAL_STATE_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return TRADITIONAL_STATE_ADDRESSES[bucket_id]['Disable']

def get_traditional_global_address(control_type: str) -> int:
    """
    获取全局控制地址
    
    Args:
        control_type (str): 控制类型 ('GlobalStart', 'GlobalStop', 'GlobalDischarge', 'GlobalClear', 'GlobalClean')
        
    Returns:
        int: 全局控制地址
        
    Raises:
        ValueError: 如果控制类型无效
    """
    if control_type not in TRADITIONAL_GLOBAL_ADDRESSES:
        raise ValueError(f"无效的全局控制类型: {control_type}")
    
    return TRADITIONAL_GLOBAL_ADDRESSES[control_type]

def get_traditional_calibration_address(bucket_id: int, calib_type: str) -> int:
    """
    获取校准地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        calib_type (str): 校准类型 ('ZeroCalibration', 'WeightCalibration')
        
    Returns:
        int: 校准地址
        
    Raises:
        ValueError: 如果料斗ID或校准类型无效
    """
    if bucket_id not in TRADITIONAL_CALIBRATION_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if calib_type not in TRADITIONAL_CALIBRATION_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的校准类型: {calib_type}")
    
    return TRADITIONAL_CALIBRATION_ADDRESSES[bucket_id][calib_type]

def get_traditional_system_address(system_param: str) -> int:
    """
    获取系统参数地址
    
    Args:
        system_param (str): 系统参数名称
        
    Returns:
        int: 系统参数地址
        
    Raises:
        ValueError: 如果系统参数名称无效
    """
    if system_param not in TRADITIONAL_SYSTEM_ADDRESSES:
        raise ValueError(f"无效的系统参数: {system_param}")
    
    return TRADITIONAL_SYSTEM_ADDRESSES[system_param]

def get_traditional_system_control_address(control_type: str) -> int:
    """
    获取系统控制地址
    
    Args:
        control_type (str): 控制类型 ('ModuleInit', 'FeedDataInit', 'ModuleDataRead', 'SystemSave')
        
    Returns:
        int: 系统控制地址
        
    Raises:
        ValueError: 如果控制类型无效
    """
    if control_type not in TRADITIONAL_SYSTEM_CONTROL_ADDRESSES:
        raise ValueError(f"无效的系统控制类型: {control_type}")
    
    return TRADITIONAL_SYSTEM_CONTROL_ADDRESSES[control_type]

# ==================== 批量操作函数 ====================

def get_all_traditional_weight_addresses() -> list:
    """
    获取所有料斗的实时重量地址列表
    
    Returns:
        list: 包含所有料斗重量地址的列表 [700, 702, 704, 706, 708, 710]
    """
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['Weight'] for i in range(1, 7)]

def get_all_traditional_target_reached_addresses() -> list:
    """
    获取所有料斗的到量地址列表
    
    Returns:
        list: 包含所有料斗到量地址的列表 [191, 192, 193, 194, 195, 196]
    """
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['TargetReached'] for i in range(1, 7)]

def get_all_traditional_coarse_add_addresses() -> list:
    """
    获取所有料斗的快加地址列表
    
    Returns:
        list: 包含所有料斗快加地址的列表 [211, 213, 215, 217, 219, 221]
    """
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['CoarseAdd'] for i in range(1, 7)]

def get_all_traditional_fine_add_addresses() -> list:
    """
    获取所有料斗的慢加地址列表
    
    Returns:
        list: 包含所有料斗慢加地址的列表 [212, 214, 216, 218, 220, 222]
    """
    return [TRADITIONAL_MONITORING_ADDRESSES[i]['FineAdd'] for i in range(1, 7)]

def get_all_traditional_start_addresses() -> list:
    """
    获取所有料斗的启动地址列表
    
    Returns:
        list: 包含所有料斗启动地址的列表 [110, 111, 112, 113, 114, 115]
    """
    return [TRADITIONAL_CONTROL_ADDRESSES[i]['Start'] for i in range(1, 7)]

def get_all_traditional_discharge_addresses() -> list:
    """
    获取所有料斗的放料地址列表
    
    Returns:
        list: 包含所有料斗放料地址的列表 [51, 52, 53, 54, 55, 56]
    """
    return [TRADITIONAL_CONTROL_ADDRESSES[i]['Discharge'] for i in range(1, 7)]

def get_all_traditional_disable_addresses() -> list:
    """
    获取所有料斗的禁用地址列表
    
    Returns:
        list: 包含所有料斗禁用地址的列表 [49409, 49410, 49411, 49412, 49413, 49414]
    """
    return [TRADITIONAL_STATE_ADDRESSES[i]['Disable'] for i in range(1, 7)]

def get_traditional_bucket_all_addresses(bucket_id: int) -> dict:
    """
    获取指定料斗的所有地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        
    Returns:
        dict: 包含该料斗所有地址的字典
        
    Raises:
        ValueError: 如果料斗ID无效
    """
    if bucket_id not in range(1, 7):
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return {
        'monitoring': TRADITIONAL_MONITORING_ADDRESSES[bucket_id],
        'control': TRADITIONAL_CONTROL_ADDRESSES[bucket_id],
        'parameter': TRADITIONAL_PARAMETER_ADDRESSES[bucket_id],
        'state': TRADITIONAL_STATE_ADDRESSES[bucket_id],
        'calibration': TRADITIONAL_CALIBRATION_ADDRESSES[bucket_id]
    }

# ==================== 地址验证函数 ====================

def validate_traditional_bucket_id(bucket_id: int) -> bool:
    """
    验证料斗ID是否有效
    
    Args:
        bucket_id (int): 料斗ID
        
    Returns:
        bool: True表示有效，False表示无效
    """
    return bucket_id in range(1, 7)

def get_traditional_address_info() -> dict:
    """
    获取传统模式地址信息统计
    
    Returns:
        dict: 地址统计信息
    """
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