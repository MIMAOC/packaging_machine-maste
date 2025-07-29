# frontend/clients/__init__.py
"""
API客户端模块包
提供与后端API服务通信的客户端

模块列表：
- webapi_client: 重量分析API客户端
- coarse_time_webapi: 快加时间分析API客户端  
- flight_material_webapi: 飞料值分析API客户端
"""

__version__ = "1.5.1"
__author__ = "AI助手"

# 导入主要客户端类
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