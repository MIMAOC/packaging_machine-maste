"""
API客户端模块包
"""

__version__ = "1.5.1"
__author__ = "L&C"

try:
    from .webapi_client import WeightAnalysisAPI, analyze_target_weight, test_webapi_connection
    from .coarse_time_webapi import CoarseTimeAnalysisAPI, analyze_coarse_time
    from .flight_material_webapi import FlightMaterialAnalysisAPI, analyze_flight_material
    
    __all__ = [
        'WeightAnalysisAPI', 'analyze_target_weight', 'test_webapi_connection',
        'CoarseTimeAnalysisAPI', 'analyze_coarse_time',
        'FlightMaterialAnalysisAPI', 'analyze_flight_material'
    ]
    
except ImportError as e:
    print(f"警告：API客户端模块导入失败: {e}")
    __all__ = []