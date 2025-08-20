"""
重量分析API路由

作者：C
创建日期：2025-07-23
"""

from fastapi import APIRouter, HTTPException
from models.request_models import WeightAnalysisRequest
from models.response_models import WeightAnalysisResponse, ErrorResponse
from analysis.weight_analysis import analyze_target_weight_for_coarse_speed, get_all_speed_rules

router = APIRouter()

@router.post("/analyze", response_model=WeightAnalysisResponse)
async def analyze_weight(request: WeightAnalysisRequest):
    try:
        success, coarse_speed, message, rule_info = analyze_target_weight_for_coarse_speed(
            request.target_weight
        )
        
        if success:
            return WeightAnalysisResponse(
                success=True,
                target_weight=request.target_weight,
                coarse_speed=coarse_speed,
                message=message,
                analysis_type=request.analysis_type,
                rule_matched=rule_info
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/rules")
async def get_weight_rules():    
    try:
        rules_info = get_all_speed_rules()
        return {
            "success": True,
            "rules": rules_info,
            "message": "成功获取重量分析规则"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取规则失败")