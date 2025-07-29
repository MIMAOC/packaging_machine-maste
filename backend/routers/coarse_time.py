# routers/coarse_time.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快加时间分析API路由

作者：AI助手
创建日期：2025-07-23
"""

from fastapi import APIRouter, HTTPException
from models.request_models import CoarseTimeAnalysisRequest
from models.response_models import CoarseTimeAnalysisResponse
from analysis.coarse_time_analysis import analyze_coarse_time_compliance
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=CoarseTimeAnalysisResponse)
async def analyze_coarse_time(request: CoarseTimeAnalysisRequest):
    """分析快加时间是否符合条件"""
    try:
        logger.info(f"收到快加时间分析请求: 重量={request.target_weight}g, 时间={request.coarse_time_ms}ms, 速度={request.current_coarse_speed}")
        
        # 调用分析函数 
        success, is_compliant, new_speed, message, analysis_details = analyze_coarse_time_compliance(
            request.target_weight,
            request.coarse_time_ms,
            request.current_coarse_speed
        )
        
        if success:
            logger.info(f"快加时间分析成功: 符合条件={is_compliant}, 新速度={new_speed}")
            return CoarseTimeAnalysisResponse(
                success=True,
                target_weight=request.target_weight,
                coarse_time_ms=request.coarse_time_ms,
                current_coarse_speed=request.current_coarse_speed,
                is_compliant=is_compliant,
                new_coarse_speed=new_speed,
                message=message,
                analysis_details=analysis_details
            )
        else:
            logger.error(f"快加时间分析失败: {message}")
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快加时间分析服务器内部错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")