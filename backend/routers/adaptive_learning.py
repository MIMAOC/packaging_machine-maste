#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应学习阶段API路由 - 后端版本

作者：AI助手
创建日期：2025-07-24
"""

from fastapi import APIRouter, HTTPException
from models.request_models import AdaptiveLearningAnalysisRequest
from models.response_models import (
    AdaptiveLearningAnalysisResponse,
    AdaptiveLearningErrorResponse
)
from analysis.adaptive_learning_analysis import handle_adaptive_learning_analysis
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=AdaptiveLearningAnalysisResponse)
async def analyze_adaptive_learning_parameters(request: AdaptiveLearningAnalysisRequest):
    """
    自适应学习阶段参数分析端点
    
    Args:
        request (AdaptiveLearningAnalysisRequest): 分析请求
        
    Returns:
        AdaptiveLearningAnalysisResponse: 分析结果
        
    Raises:
        HTTPException: 当分析失败时
    """
    try:
        logger.info(f"收到自适应学习参数分析请求: 目标重量={request.target_weight}g, "
                   f"总周期={request.actual_total_cycle_ms}ms, 快加时间={request.actual_coarse_time_ms}ms")
        
        # 调用分析函数
        response = handle_adaptive_learning_analysis(request)
        
        logger.info(f"自适应学习参数分析完成: 符合条件={response.is_compliant}")
        
        return response
        
    except ValueError as e:
        error_msg = f"参数验证失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
        
    except Exception as e:
        error_msg = f"自适应学习参数分析失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)