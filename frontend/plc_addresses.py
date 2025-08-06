#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC地址定义模块
存放所有PLC寄存器地址和线圈地址的定义

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-25（添加生产相关地址定义）
"""

# 6个料斗的参数寄存器地址映射
BUCKET_PARAMETER_ADDRESSES = {
    1: {
        'CoarseAdvance': 41588,    # 快加提前量
        'FallValue': 41590,        # 落差值
        'CoarseSpeed': 41388,      # 快加速度
        'FineSpeed': 41390,        # 慢加速度
        'TargetWeight': 41229      # 目标重量
    },
    2: {
        'CoarseAdvance': 41592,
        'FallValue': 41594,
        'CoarseSpeed': 41408,
        'FineSpeed': 41410,
        'TargetWeight': 41230
    },
    3: {
        'CoarseAdvance': 41596,
        'FallValue': 41598,
        'CoarseSpeed': 41428,
        'FineSpeed': 41430,
        'TargetWeight': 41231
    },
    4: {
        'CoarseAdvance': 41600,
        'FallValue': 41602,
        'CoarseSpeed': 41448,
        'FineSpeed': 41450,
        'TargetWeight': 41232
    },
    5: {
        'CoarseAdvance': 41604,
        'FallValue': 41606,
        'CoarseSpeed': 41468,
        'FineSpeed': 41470,
        'TargetWeight': 41233
    },
    6: {
        'CoarseAdvance': 41608,
        'FallValue': 41610,
        'CoarseSpeed': 41488,
        'FineSpeed': 41490,
        'TargetWeight': 41234
    }
}

# 6个料斗的监控地址映射（实时重量、到量、快加线圈）
BUCKET_MONITORING_ADDRESSES = {
    1: {
        'Weight': 20,           # 实时重量寄存器地址
        'TargetReached': 191,   # 到量线圈地址
        'CoarseAdd': 171        # 快加线圈地址
    },
    2: {
        'Weight': 22,
        'TargetReached': 192,
        'CoarseAdd': 172
    },
    3: {
        'Weight': 24,
        'TargetReached': 193,
        'CoarseAdd': 173
    },
    4: {
        'Weight': 26,
        'TargetReached': 194,
        'CoarseAdd': 174
    },
    5: {
        'Weight': 28,
        'TargetReached': 195,
        'CoarseAdd': 175
    },
    6: {
        'Weight': 30,
        'TargetReached': 196,
        'CoarseAdd': 176
    }
}

# 6个料斗的控制线圈地址映射
BUCKET_CONTROL_ADDRESSES = {
    1: {
        'StartAddress': 110,     # 启动
        'StopAddress': 120,      # 停止
        'ClearAddress': 181,     # 清零
        'DischargeAddress': 51,  # 放料
        'CleanAddress': 61       # 清料
    },
    2: {
        'StartAddress': 111,
        'StopAddress': 121,
        'ClearAddress': 182,
        'DischargeAddress': 52,
        'CleanAddress': 62
    },
    3: {
        'StartAddress': 112,
        'StopAddress': 122,
        'ClearAddress': 183,
        'DischargeAddress': 53,
        'CleanAddress': 63
    },
    4: {
        'StartAddress': 113,
        'StopAddress': 123,
        'ClearAddress': 184,
        'DischargeAddress': 54,
        'CleanAddress': 64
    },
    5: {
        'StartAddress': 114,
        'StopAddress': 124,
        'ClearAddress': 185,
        'DischargeAddress': 55,
        'CleanAddress': 65
    },
    6: {
        'StartAddress': 115,
        'StopAddress': 125,
        'ClearAddress': 186,
        'DischargeAddress': 56,
        'CleanAddress': 66
    }
}

# 6个料斗的禁用线圈地址
BUCKET_DISABLE_ADDRESSES = {
    1: 49409,
    2: 49410,
    3: 49411,
    4: 49412,
    5: 49413,
    6: 49414
}

# 总控制线圈地址
GLOBAL_CONTROL_ADDRESSES = {
    'GlobalStart': 300,      # 总启动
    'GlobalStop': 301,       # 总停止
    'GlobalClear': 6,        # 总清零
    'GlobalDischarge': 5,    # 总放料
    'GlobalClean': 7,        # 总清料
    'AIMode': 40,           # 切换AI/传统模式地址
    'PackagingMachineStop': 70  # 包装机停止地址

}

# 生产相关地址
PRODUCTION_ADDRESSES = {
    'PackageCountRegister': 41094,   # 总包装计数寄存器地址
    'PackageCountClear': 2           # 包数清零线圈地址
}

# 快加时间监测相关地址（新增）
COARSE_TIME_MONITORING_ADDRESSES = {
    # 连续地址配置，用于批量读写
    'START_COIL_START_ADDRESS': 110,    # 启动线圈起始地址（料斗1-6：110-115）
    'STOP_COIL_START_ADDRESS': 120,     # 停止线圈起始地址（料斗1-6：120-125）
    'TARGET_REACHED_START_ADDRESS': 191, # 到量线圈起始地址（料斗1-6：191-196）
    'DISCHARGE_COIL_START_ADDRESS': 51,  # 放料线圈起始地址（料斗1-6：51-56）
}

def get_bucket_parameter_address(bucket_id: int, parameter_name: str) -> int:
    """
    获取指定料斗的参数寄存器地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        parameter_name (str): 参数名称 ('CoarseAdvance', 'FallValue', 'CoarseSpeed', 'FineSpeed', 'TargetWeight')
        
    Returns:
        int: 寄存器地址
        
    Raises:
        ValueError: 如果料斗ID或参数名称无效
    """
    if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if parameter_name not in BUCKET_PARAMETER_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的参数名称: {parameter_name}")
    
    return BUCKET_PARAMETER_ADDRESSES[bucket_id][parameter_name]

def get_bucket_weight_address(bucket_id: int) -> int:
    """
    获取指定料斗的实时重量寄存器地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        
    Returns:
        int: 重量寄存器地址
        
    Raises:
        ValueError: 如果料斗ID无效
    """
    if bucket_id not in BUCKET_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']

def get_bucket_target_reached_address(bucket_id: int) -> int:
    """
    获取指定料斗的到量线圈地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        
    Returns:
        int: 到量线圈地址
        
    Raises:
        ValueError: 如果料斗ID无效
    """
    if bucket_id not in BUCKET_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return BUCKET_MONITORING_ADDRESSES[bucket_id]['TargetReached']

def get_bucket_control_address(bucket_id: int, control_name: str) -> int:
    """
    获取指定料斗的控制线圈地址
    
    Args:
        bucket_id (int): 料斗ID (1-6)
        control_name (str): 控制名称 ('StartAddress', 'StopAddress', 'ClearAddress', 'DischargeAddress', 'CleanAddress')
        
    Returns:
        int: 控制线圈地址
        
    Raises:
        ValueError: 如果料斗ID或控制名称无效
    """
    if bucket_id not in BUCKET_CONTROL_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if control_name not in BUCKET_CONTROL_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的控制名称: {control_name}")
    
    return BUCKET_CONTROL_ADDRESSES[bucket_id][control_name]

def get_global_control_address(control_name: str) -> int:
    """
    获取总控制线圈地址
    
    Args:
        control_name (str): 控制名称 ('GlobalStart', 'GlobalStop', 'GlobalClear', 'GlobalDischarge', 'GlobalClean')
        
    Returns:
        int: 线圈地址
        
    Raises:
        ValueError: 如果控制名称无效
    """
    if control_name not in GLOBAL_CONTROL_ADDRESSES:
        raise ValueError(f"无效的控制名称: {control_name}")
    
    return GLOBAL_CONTROL_ADDRESSES[control_name]

def get_production_address(address_name: str) -> int:
    """
    获取生产相关地址（新增）
    
    Args:
        address_name (str): 地址名称 ('PackageCountRegister', 'PackageCountClear')
        
    Returns:
        int: 地址
        
    Raises:
        ValueError: 如果地址名称无效
    """
    if address_name not in PRODUCTION_ADDRESSES:
        raise ValueError(f"无效的生产地址名称: {address_name}")
    
    return PRODUCTION_ADDRESSES[address_name]

def get_all_bucket_weight_addresses() -> list:
    """
    获取所有料斗的实时重量寄存器地址列表
    
    Returns:
        list: 包含所有料斗重量地址的列表
    """
    return [BUCKET_MONITORING_ADDRESSES[i]['Weight'] for i in range(1, 7)]

def get_all_bucket_target_reached_addresses() -> list:
    """
    获取所有料斗的到量线圈地址列表（新增）
    
    Returns:
        list: 包含所有料斗到量线圈地址的列表
    """
    return [BUCKET_MONITORING_ADDRESSES[i]['TargetReached'] for i in range(1, 7)]

def get_all_bucket_coarse_add_addresses() -> list:
    """
    获取所有料斗的快加线圈地址列表（新增）
    
    Returns:
        list: 包含所有料斗快加线圈地址的列表
    """
    return [BUCKET_MONITORING_ADDRESSES[i]['CoarseAdd'] for i in range(1, 7)]

def get_coarse_time_monitoring_address(address_type: str) -> int:
    """
    获取快加时间监测相关的连续地址（新增）
    
    Args:
        address_type (str): 地址类型
        
    Returns:
        int: 地址
        
    Raises:
        ValueError: 如果地址类型无效
    """
    if address_type not in COARSE_TIME_MONITORING_ADDRESSES:
        raise ValueError(f"无效的地址类型: {address_type}")
    
    return COARSE_TIME_MONITORING_ADDRESSES[address_type]