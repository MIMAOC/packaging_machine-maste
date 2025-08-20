"""
自适应学习阶段API路由

作者：C
创建日期：2025-07-24
"""

from fastapi import APIRouter, HTTPException
from models.request_models import AdaptiveLearningAnalysisRequest
from models.response_models import (
    AdaptiveLearningAnalysisResponse,
    AdaptiveLearningErrorResponse
)
from analysis.adaptive_learning_analysis import handle_adaptive_learning_analysis

router = APIRouter()

@router.post("/analyze", response_model=AdaptiveLearningAnalysisResponse)
async def analyze_adaptive_learning_parameters(request: AdaptiveLearningAnalysisRequest):
    try:
        response = handle_adaptive_learning_analysis(request)
        
        return response
        
    except ValueError as e:
        error_msg = f"参数验证失败: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
        
    except Exception as e:
        error_msg = f"自适应学习参数分析失败: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)