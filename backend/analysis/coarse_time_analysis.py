"""
快加时间分析模块

作者：C
创建日期：2025-07-23
"""
from typing import Tuple, Optional, Dict, Any

def analyze_coarse_time_compliance(target_weight: float, coarse_time_ms: int, 
                                 current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str, Dict[str, Any]]:
    try:
        standard_total_cycle = calculate_total_cycle_time(target_weight)
        
        coarse_time_ratio = calculate_coarse_time_ratio(target_weight)
        
        max_coarse_time = standard_total_cycle * coarse_time_ratio
        min_coarse_time = max_coarse_time * 0.8
        
        analysis_details = {
            "target_weight": target_weight,
            "coarse_time_ms": coarse_time_ms,
            "current_coarse_speed": current_coarse_speed,
            "standard_total_cycle": standard_total_cycle,
            "coarse_time_ratio": coarse_time_ratio,
            "min_coarse_time": min_coarse_time,
            "max_coarse_time": max_coarse_time,
            "time_range": f"{min_coarse_time:.0f}-{max_coarse_time:.0f}ms"
        }
        
        if min_coarse_time <= coarse_time_ms <= max_coarse_time:
            message = f"快加时间 {coarse_time_ms}ms 在合格范围 {min_coarse_time:.0f}-{max_coarse_time:.0f}ms 内，当前快加速度 {current_coarse_speed} 档符合条件"
            analysis_details["compliance_status"] = "compliant"
            return True, True, None, message, analysis_details
        
        success, new_speed, adjustment_msg = calculate_speed_adjustment(
            coarse_time_ms, min_coarse_time, max_coarse_time, current_coarse_speed)
        
        analysis_details["compliance_status"] = "non_compliant"
        analysis_details["adjustment_needed"] = True
        
        if success:
            message = f"快加时间 {coarse_time_ms}ms 超出范围，{adjustment_msg}，建议调整速度至 {new_speed} 档"
            analysis_details["speed_adjustment"] = adjustment_msg
            analysis_details["new_speed"] = new_speed
            return True, False, new_speed, message, analysis_details
        else:
            analysis_details["speed_adjustment_error"] = adjustment_msg
            return True, False, None, adjustment_msg, analysis_details
            
    except Exception as e:
        error_msg = f"快加时间分析异常: {str(e)}"
        return False, False, None, error_msg, {}

def calculate_total_cycle_time(target_weight: float) -> int:
    if target_weight <= 225:
        return 9000
    elif target_weight <= 325:
        return 11000
    elif target_weight <= 425:
        return 12500
    elif target_weight <= 800:
        return 16500
    elif target_weight <= 1000:
        return 21000
    else:
        return 24000

def calculate_coarse_time_ratio(target_weight: float) -> float:
    if 100 <= target_weight <= 300:
        return 0.7
    elif 300 < target_weight <= 400:
        return 0.7
    else:
        return 0.4 if target_weight < 100 else 0.5

def calculate_speed_adjustment(actual_time: int, min_time: float, max_time: float, 
                             current_speed: int) -> Tuple[bool, Optional[int], str]:
    if actual_time < min_time:
        time_offset_ratio = (min_time - actual_time) / min_time * 100
        
        if time_offset_ratio <= 15:
            speed_adjustment = -1
        elif time_offset_ratio <= 30:
            speed_adjustment = -2
        elif time_offset_ratio <= 45:
            speed_adjustment = -3
        elif time_offset_ratio <= 60:
            speed_adjustment = -4
        elif time_offset_ratio <= 75:
            speed_adjustment = -5
        else:
            speed_adjustment = -6
        
        new_speed = current_speed + speed_adjustment
        message = f"快加时间过短，时间偏移比例 {time_offset_ratio:.1f}%，速度调整 {speed_adjustment}"
        
    elif actual_time > max_time:
        time_offset_ratio = (actual_time - max_time) / max_time * 100
        
        if time_offset_ratio <= 15:
            speed_adjustment = 1
        elif time_offset_ratio <= 30:
            speed_adjustment = 2
        elif time_offset_ratio <= 45:
            speed_adjustment = 3
        elif time_offset_ratio <= 60:
            speed_adjustment = 4
        elif time_offset_ratio <= 75:
            speed_adjustment = 5
        else:
            speed_adjustment = 6
        
        new_speed = current_speed + speed_adjustment
        message = f"快加时间过长，时间偏移比例 {time_offset_ratio:.1f}%，速度调整 +{speed_adjustment}"
    else:
        # 理论上不会到这里
        return False, None, "快加时间分析逻辑错误"
    
    if new_speed < 1 or new_speed > 100:
        return False, None, f"料斗快加速度异常（计算得到 {new_speed}），请人工检修"
    
    return True, new_speed, message