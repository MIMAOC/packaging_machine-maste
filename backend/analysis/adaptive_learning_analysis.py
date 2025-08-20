"""
自适应学习阶段分析模块

作者：C
创建日期：2025-07-24
更新日期：2025-08-19
"""
from typing import Dict, Any, Optional, Tuple
from models.request_models import AdaptiveLearningAnalysisRequest
from models.response_models import (
    AdaptiveLearningAnalysisResponse,
    AdaptiveLearningErrorResponse
)

# 导入快加时间分析模块
from analysis.coarse_time_analysis import (
    calculate_total_cycle_time,
    calculate_coarse_time_ratio
)

def analyze_adaptive_learning_parameters(request: AdaptiveLearningAnalysisRequest) -> AdaptiveLearningAnalysisResponse:
    try:
        standard_total_cycle_ms = calculate_total_cycle_time(request.target_weight)
        coarse_time_ratio = calculate_coarse_time_ratio(request.target_weight)
        
        actual_fine_time_ms = request.actual_total_cycle_ms - request.actual_coarse_time_ms
        
        fine_flow_rate = getattr(request, 'fine_flow_rate', None)
        
        error_check = check_error_value_boundary(request.error_value)
        cycle_check = check_cycle_time_boundary(request.actual_total_cycle_ms, standard_total_cycle_ms)
        fine_time_check = check_fine_time_boundary(actual_fine_time_ms)
        fall_value_check = check_fall_value_boundary(request.current_fall_value)
        
        is_compliant = (error_check["compliant"] and 
                       cycle_check["compliant"] and 
                       fine_time_check["compliant"] and 
                       fall_value_check["compliant"])
        
        adjustment_parameters = None
        if not is_compliant:
            adjustment_parameters = calculate_adjustment_parameters(
                request, actual_fine_time_ms, standard_total_cycle_ms, 
                fine_flow_rate, error_check, cycle_check, fine_time_check, fall_value_check
            )
        
        message = generate_analysis_message(is_compliant, error_check, cycle_check, 
                                          fine_time_check, fall_value_check, adjustment_parameters)
        
        response = AdaptiveLearningAnalysisResponse(
            success=True,
            target_weight=request.target_weight,
            actual_total_cycle_ms=request.actual_total_cycle_ms,
            actual_coarse_time_ms=request.actual_coarse_time_ms,
            actual_fine_time_ms=actual_fine_time_ms,
            error_value=request.error_value,
            is_compliant=is_compliant,
            standard_total_cycle_ms=standard_total_cycle_ms,
            coarse_time_ratio=coarse_time_ratio,
            fine_flow_rate=fine_flow_rate,
            error_check=error_check,
            cycle_check=cycle_check,
            fine_time_check=fine_time_check,
            fall_value_check=fall_value_check,
            adjustment_parameters=adjustment_parameters,
            message=message
        )
        
        return response
        
    except Exception as e:
        error_msg = f"自适应学习参数分析异常: {str(e)}"
        raise ValueError(error_msg)

def check_error_value_boundary(error_value: float) -> Dict[str, Any]:
    compliant = 0.0 <= error_value <= 0.4
    
    return {
        "compliant": compliant,
        "error_value": error_value,
        "min_required": 0.0,
        "max_required": 0.4,
        "description": f"误差值{error_value:.2f}g，要求范围[0.0g, 0.4g]"
    }

def check_cycle_time_boundary(actual_total_cycle_ms: int, standard_total_cycle_ms: int) -> Dict[str, Any]:
    compliant = 0 < actual_total_cycle_ms <= standard_total_cycle_ms
    
    return {
        "compliant": compliant,
        "actual_cycle": actual_total_cycle_ms,
        "standard_cycle": standard_total_cycle_ms,
        "description": f"实际总周期{actual_total_cycle_ms}ms，标准周期{standard_total_cycle_ms}ms"
    }

def check_fine_time_boundary(actual_fine_time_ms: int) -> Dict[str, Any]:
    compliant = actual_fine_time_ms >= 2000
    
    return {
        "compliant": compliant,
        "actual_fine_time": actual_fine_time_ms,
        "min_required": 2000,
        "description": f"实际慢加时间{actual_fine_time_ms}ms，要求≥2000ms"
    }

def check_fall_value_boundary(fall_value: float) -> Dict[str, Any]:
    compliant = 0.0 <= fall_value <= 1.0
    
    return {
        "compliant": compliant,
        "fall_value": fall_value,
        "min_required": 0.0,
        "max_required": 1.0,
        "description": f"落差值{fall_value}g，要求范围[0.0g, 1.0g]"
    }

def calculate_adjustment_parameters(
    request: AdaptiveLearningAnalysisRequest,
    actual_fine_time_ms: int,
    standard_total_cycle_ms: int,
    fine_flow_rate: Optional[float],
    error_check: Dict[str, Any],
    cycle_check: Dict[str, Any],
    fine_time_check: Dict[str, Any],
    fall_value_check: Dict[str, Any]
) -> Dict[str, float]:
    adjustment_params = {}
    new_coarse_advance = request.current_coarse_advance
    new_fall_value = request.current_fall_value
    
    if not fall_value_check["compliant"]:
        return {}
    
    if not fine_time_check["compliant"]:
        fine_time = actual_fine_time_ms
        
        if 0 <= fine_time < 800:
            new_coarse_advance += 5.0
        elif 800 <= fine_time < 1600:
            new_coarse_advance += 2.4
        elif 1600 <= fine_time < 2000:
            new_coarse_advance += 1.5
        elif 2000 <= fine_time < 2700:
            new_coarse_advance += 1.0
    
    if not cycle_check["compliant"] and request.actual_total_cycle_ms > standard_total_cycle_ms:
        if fine_flow_rate is not None:
            cycle_diff = (request.actual_total_cycle_ms - standard_total_cycle_ms)/1000
            reduction = cycle_diff * fine_flow_rate + 1
            new_coarse_advance = round(max(0, new_coarse_advance - reduction), 1)
    
    if not error_check["compliant"]:        
        if request.error_value > 0.4:
            new_fall_value += 0.1
        elif request.error_value < 0.0:
            new_fall_value = max(0.0, new_fall_value - 0.1)
    
    new_coarse_advance = round(max(0.0, new_coarse_advance), 1)
    new_fall_value = round(max(0.0, min(1.0, new_fall_value)), 1)
    
    if new_fall_value < 0.0 or new_fall_value > 1.0:
        return {}
    
    if new_coarse_advance != request.current_coarse_advance:
        adjustment_params["coarse_advance"] = round(new_coarse_advance, 1)
    
    if new_fall_value != request.current_fall_value:
        adjustment_params["fall_value"] = round(new_fall_value, 1)
    
    return adjustment_params

def generate_analysis_message(
    is_compliant: bool,
    error_check: Dict[str, Any],
    cycle_check: Dict[str, Any],
    fine_time_check: Dict[str, Any],
    fall_value_check: Dict[str, Any],
    adjustment_parameters: Optional[Dict[str, float]]
) -> str:
    if is_compliant:
        return "✅ 自适应学习参数符合所有边界条件"
    
    issues = []
    
    if not error_check["compliant"]:
        issues.append(f"误差值{error_check['error_value']:.2f}g超出范围[0.0g, 0.4g]")
    
    if not cycle_check["compliant"]:
        if cycle_check["actual_cycle"] > cycle_check["standard_cycle"]:
            issues.append(f"总周期{cycle_check['actual_cycle']}ms超出标准{cycle_check['standard_cycle']}ms")
        else:
            issues.append(f"总周期{cycle_check['actual_cycle']}ms≤0")
    
    if not fine_time_check["compliant"]:
        issues.append(f"慢加时间{fine_time_check['actual_fine_time']}ms < 2000ms")
    
    if not fall_value_check["compliant"]:
        issues.append(f"落差值{fall_value_check['fall_value']}g超出范围[0.0g, 1.0g]")
    
    message = f"❌ 不符合条件: {'; '.join(issues)}"
    
    if adjustment_parameters:
        adjustments = []
        for param, value in adjustment_parameters.items():
            if param == "coarse_advance":
                adjustments.append(f"快加提前量→{value:.1f}g")
            elif param == "fall_value":
                adjustments.append(f"落差值→{value:.1f}g")
        
        if adjustments:
            message += f"; 调整参数: {', '.join(adjustments)}"
    
    return message

def handle_adaptive_learning_analysis(request: AdaptiveLearningAnalysisRequest) -> AdaptiveLearningAnalysisResponse:
    try:
        return analyze_adaptive_learning_parameters(request)
    except Exception as e:
        raise