# routers/weight.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重量分析API路由

作者：AI助手
创建日期：2025-07-23
"""

from fastapi import APIRouter, HTTPException
from models.request_models import WeightAnalysisRequest
from models.response_models import WeightAnalysisResponse, ErrorResponse
from analysis.weight_analysis import analyze_target_weight_for_coarse_speed, get_all_speed_rules
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=WeightAnalysisResponse)
async def analyze_weight(request: WeightAnalysisRequest):
    """分析目标重量对应的快加速度"""
    try:
        logger.info(f"收到重量分析请求: 重量={request.target_weight}g, 类型={request.analysis_type}")
        
        # 调用分析函数
        success, coarse_speed, message, rule_info = analyze_target_weight_for_coarse_speed(
            request.target_weight
        )
        
        if success:
            logger.info(f"分析成功: {request.target_weight}g -> {coarse_speed}档")
            return WeightAnalysisResponse(
                success=True,
                target_weight=request.target_weight,
                coarse_speed=coarse_speed,
                message=message,
                analysis_type=request.analysis_type,
                rule_matched=rule_info
            )
        else:
            logger.error(f"分析失败: {message}")
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重量分析服务器内部错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/rules")
async def get_weight_rules():
    """获取重量分析规则"""
    logger.info("收到获取重量规则请求")
    
    try:
        rules_info = get_all_speed_rules()
        return {
            "success": True,
            "rules": rules_info,
            "message": "成功获取重量分析规则"
        }
    except Exception as e:
        logger.error(f"获取规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取规则失败")