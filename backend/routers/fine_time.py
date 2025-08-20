"""
慢加时间分析API路由

作者：C
创建日期：2025-07-24
"""

from fastapi import APIRouter, HTTPException
from models.request_models import FineTimeAnalysisRequest
from models.response_models import FineTimeAnalysisResponse
from analysis.fine_time_analysis import FineTimeAnalysisService

router = APIRouter()

fine_time_service = FineTimeAnalysisService()

@router.post("/analyze", response_model=FineTimeAnalysisResponse)
async def analyze_fine_time(request: FineTimeAnalysisRequest):
    try:
        result = fine_time_service.analyze_fine_time(
            request.target_weight,
            request.fine_time_ms,
            request.current_fine_speed,
            request.original_target_weight,
            request.flight_material_value
        )
        
        return FineTimeAnalysisResponse(
            success=True,
            target_weight=request.target_weight,
            fine_time_ms=request.fine_time_ms,
            current_fine_speed=request.current_fine_speed,
            is_compliant=result['is_compliant'],
            new_fine_speed=result.get('new_fine_speed'),
            coarse_advance=result.get('coarse_advance'),
            fine_flow_rate=result.get('fine_flow_rate'),
            message=result['message'],
            analysis_details=result.get('analysis_details')
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="慢加时间分析失败")