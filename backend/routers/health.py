# routers/health.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查API路由

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-24（添加自适应学习分析端点信息）
"""

from fastapi import APIRouter
from models.response_models import HealthResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    logger.info("收到健康检查请求")
    
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