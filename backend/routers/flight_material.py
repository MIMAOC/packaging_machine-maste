"""
飞料值分析API路由

作者：C
创建日期：2025-07-23
"""

from fastapi import APIRouter, HTTPException
from models.request_models import FlightMaterialAnalysisRequest
from models.response_models import FlightMaterialAnalysisResponse
from analysis.flight_material_analysis import analyze_flight_material_values

router = APIRouter()

@router.post("/analyze", response_model=FlightMaterialAnalysisResponse)
async def analyze_flight_material(request: FlightMaterialAnalysisRequest):
    try:
        success, avg_flight_material, flight_details, message, analysis_details = analyze_flight_material_values(
            request.target_weight,
            request.recorded_weights
        )
        
        if success:
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
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误")