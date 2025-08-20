"""
健康检查API路由

作者：C
创建日期：2025-07-23
更新日期：2025-08-19
"""

from fastapi import APIRouter
from models.response_models import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():    
    return HealthResponse(
        success=True,
        status="healthy",
        service="包装机分析API服务",
        version="1.5.1",
        endpoints=[
            "/api/health",
            "/api/weight/analyze", 
            "/api/weight/rules",
            "/api/coarse_time/analyze",
            "/api/flight_material/analyze",
            "/api/fine_time/analyze",
            "/api/adaptive_learning/analyze"
        ]
    )