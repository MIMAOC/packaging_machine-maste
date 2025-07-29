# backend/models/__init__.py
"""
数据模型包
定义API请求和响应的数据结构

模块列表：
- request_models: API请求数据模型
- response_models: API响应数据模型
"""

__version__ = "1.5.1"
__author__ = "AI助手"

# 导入主要模型类
try:
    from .request_models import (
        WeightAnalysisRequest, 
        CoarseTimeAnalysisRequest, 
        FlightMaterialAnalysisRequest
    )
    from .response_models import (
        BaseResponse, ErrorResponse, HealthResponse,
        WeightAnalysisResponse, CoarseTimeAnalysisResponse, FlightMaterialAnalysisResponse
    )
    
    __all__ = [
        'WeightAnalysisRequest', 'CoarseTimeAnalysisRequest', 'FlightMaterialAnalysisRequest',
        'BaseResponse', 'ErrorResponse', 'HealthResponse',
        'WeightAnalysisResponse', 'CoarseTimeAnalysisResponse', 'FlightMaterialAnalysisResponse'
    ]
    
except ImportError as e:
    print(f"警告：数据模型导入失败: {e}")
    __all__ = []