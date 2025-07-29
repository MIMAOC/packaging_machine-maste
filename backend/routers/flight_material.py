# routers/flight_material.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞料值分析API路由

作者：AI助手
创建日期：2025-07-23
"""

from fastapi import APIRouter, HTTPException
from models.request_models import FlightMaterialAnalysisRequest
from models.response_models import FlightMaterialAnalysisResponse
from analysis.flight_material_analysis import analyze_flight_material_values
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=FlightMaterialAnalysisResponse)
async def analyze_flight_material(request: FlightMaterialAnalysisRequest):
    """分析飞料值"""
    try:
        logger.info(f"收到飞料值分析请求: 目标重量={request.target_weight}g, 实时重量={request.recorded_weights}")
        
        # 调用分析函数
        success, avg_flight_material, flight_details, message, analysis_details = analyze_flight_material_values(
            request.target_weight,
            request.recorded_weights
        )
        
        if success:
            logger.info(f"飞料值分析成功: 平均飞料值={avg_flight_material}g")
            return FlightMaterialAnalysisResponse(
                success=True,
                target_weight=request.target_weight,
                recorded_weights=request.recorded_weights,
                flight_material_details=flight_details,
                average_flight_material=avg_flight_material,
                message=message,
                analysis_type=request.analysis_type
            )
        else:
            logger.error(f"飞料值分析失败: {message}")
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"飞料值分析服务器内部错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")