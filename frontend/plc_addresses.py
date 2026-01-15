"""
PLC地址定义模块

作者：C
创建日期：2025-07-23
"""

BUCKET_PARAMETER_ADDRESSES = {
    1: {
        'CoarseAdvance': 41588,
        'FallValue': 41590,
        'CoarseSpeed': 41388,
        'FineSpeed': 41390,
        'TargetWeight': 41229
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

BUCKET_MONITORING_ADDRESSES = {
    1: {
        'Weight': 20,
        'TargetReached': 191,
        'CoarseAdd': 171,
        'DischargeAddress':71
    },
    2: {
        'Weight': 22,
        'TargetReached': 192,
        'CoarseAdd': 172,
        'DischargeAddress':72
    },
    3: {
        'Weight': 24,
        'TargetReached': 193,
        'CoarseAdd': 173,
        'DischargeAddress':73
    },
    4: {
        'Weight': 26,
        'TargetReached': 194,
        'CoarseAdd': 174,
        'DischargeAddress':74
    },
    5: {
        'Weight': 28,
        'TargetReached': 195,
        'CoarseAdd': 175,
        'DischargeAddress':75
    },
    6: {
        'Weight': 30,
        'TargetReached': 196,
        'CoarseAdd': 176,
        'DischargeAddress':76
    }
}

BUCKET_CONTROL_ADDRESSES = {
    1: {
        'StartAddress': 110,
        'StopAddress': 120,
        'ClearAddress': 181,
        'DischargeAddress': 51,
        'CleanAddress': 61
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

BUCKET_PRODUCTION_DISABLE_ADDRESSES = {
    1: 49409,
    2: 49410,
    3: 49411,
    4: 49412,
    5: 49413,
    6: 49414
}

GLOBAL_CONTROL_ADDRESSES = {
    'GlobalStart': 300,
    'GlobalStop': 301,
    'GlobalClear': 6,
    'GlobalDischarge': 5,
    'GlobalClean': 7,
    'AIMode': 40,
    'PackagingMachineStop': 70

}

PRODUCTION_ADDRESSES = {
    'PackageCountRegister': 41094,
    'PackageCountClear': 2
}

COARSE_TIME_MONITORING_ADDRESSES = {
    'START_COIL_START_ADDRESS': 110,
    'STOP_COIL_START_ADDRESS': 120,
    'TARGET_REACHED_START_ADDRESS': 191,
    'DISCHARGE_COIL_START_ADDRESS': 51,
}

def get_bucket_parameter_address(bucket_id: int, parameter_name: str) -> int:
    if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if parameter_name not in BUCKET_PARAMETER_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的参数名称: {parameter_name}")
    
    return BUCKET_PARAMETER_ADDRESSES[bucket_id][parameter_name]

def get_bucket_disable_address(bucket_id: int) -> int:
    if bucket_id not in BUCKET_PRODUCTION_DISABLE_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return BUCKET_PRODUCTION_DISABLE_ADDRESSES[bucket_id]

def get_bucket_weight_address(bucket_id: int) -> int:
    if bucket_id not in BUCKET_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']

def get_bucket_target_reached_address(bucket_id: int) -> int:
    if bucket_id not in BUCKET_MONITORING_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    return BUCKET_MONITORING_ADDRESSES[bucket_id]['TargetReached']

def get_bucket_control_address(bucket_id: int, control_name: str) -> int:
    if bucket_id not in BUCKET_CONTROL_ADDRESSES:
        raise ValueError(f"无效的料斗ID: {bucket_id}，有效范围: 1-6")
    
    if control_name not in BUCKET_CONTROL_ADDRESSES[bucket_id]:
        raise ValueError(f"无效的控制名称: {control_name}")
    
    return BUCKET_CONTROL_ADDRESSES[bucket_id][control_name]

def get_global_control_address(control_name: str) -> int:
    if control_name not in GLOBAL_CONTROL_ADDRESSES:
        raise ValueError(f"无效的控制名称: {control_name}")
    
    return GLOBAL_CONTROL_ADDRESSES[control_name]

def get_production_address(address_name: str) -> int:
    if address_name not in PRODUCTION_ADDRESSES:
        raise ValueError(f"无效的生产地址名称: {address_name}")
    
    return PRODUCTION_ADDRESSES[address_name]

def get_all_bucket_weight_addresses() -> list:
    return [BUCKET_MONITORING_ADDRESSES[i]['Weight'] for i in range(1, 7)]

def get_all_bucket_target_reached_addresses() -> list:
    return [BUCKET_MONITORING_ADDRESSES[i]['TargetReached'] for i in range(1, 7)]

def get_all_bucket_coarse_add_addresses() -> list:
    return [BUCKET_MONITORING_ADDRESSES[i]['CoarseAdd'] for i in range(1, 7)]

def get_all_bucket_discharge_addresses() -> list:
    return [BUCKET_MONITORING_ADDRESSES[i]['DischargeAddress'] for i in range(1, 7)]

def get_coarse_time_monitoring_address(address_type: str) -> int:
    if address_type not in COARSE_TIME_MONITORING_ADDRESSES:
        raise ValueError(f"无效的地址类型: {address_type}")
    
    return COARSE_TIME_MONITORING_ADDRESSES[address_type]