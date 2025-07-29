# routers/fine_time.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢加时间分析API路由

作者：AI助手
创建日期：2025-07-24
"""

from fastapi import APIRouter, HTTPException
from models.request_models import FineTimeAnalysisRequest
from models.response_models import FineTimeAnalysisResponse
from analysis.fine_time_analysis import FineTimeAnalysisService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# 创建慢加时间分析服务实例
fine_time_service = FineTimeAnalysisService()

@router.post("/analyze", response_model=FineTimeAnalysisResponse)
async def analyze_fine_time(request: FineTimeAnalysisRequest):
    """
    慢加时间分析端点
    
    根据目标重量、慢加时间和当前慢加速度，分析是否符合条件并提供调整建议
    符合条件时计算快加提前量
    """
    try:
        logger.info(f"收到慢加时间分析请求: 重量={request.target_weight}g, "
                   f"时间={request.fine_time_ms}ms, 速度={request.current_fine_speed}")
        logger.info(f"原始目标重量={request.original_target_weight}g, 快加飞料值={request.flight_material_value}g")
        
        # 调用分析服务
        result = fine_time_service.analyze_fine_time(
            request.target_weight,
            request.fine_time_ms,
            request.current_fine_speed,
            request.original_target_weight,
            request.flight_material_value
        )
        
        logger.info(f"慢加时间分析完成: 符合条件={result['is_compliant']}, "
                   f"新速度={result.get('new_fine_speed')}, 快加提前量={result.get('coarse_advance')}")
        
        return FineTimeAnalysisResponse(
            success=True,
            target_weight=request.target_weight,
            fine_time_ms=request.fine_time_ms,
            current_fine_speed=request.current_fine_speed,
            is_compliant=result['is_compliant'],
            new_fine_speed=result.get('new_fine_speed'),
            coarse_advance=result.get('coarse_advance'),
            fine_flow_rate=result.get('fine_flow_rate'),  # 🔥 添加这行
            message=result['message'],
            analysis_details=result.get('analysis_details')
        )
        
    except ValueError as e:
        logger.error(f"慢加时间分析参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"慢加时间分析异常: {str(e)}")
        raise HTTPException(status_code=500, detail="慢加时间分析失败")