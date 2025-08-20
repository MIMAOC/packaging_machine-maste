__version__ = "1.5.1"
__author__ = "L&C"

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