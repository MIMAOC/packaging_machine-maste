# analysis/coarse_time_analysis.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快加时间分析模块
分析快加时间是否符合条件并提供调整建议

作者：AI助手
创建日期：2025-07-23
"""

import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

def analyze_coarse_time_compliance(target_weight: float, coarse_time_ms: int, 
                                 current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str, Dict[str, Any]]:
    """
    分析快加时间是否符合条件
    
    Args:
        target_weight: 目标重量（克）
        coarse_time_ms: 快加时间（毫秒）
        current_coarse_speed: 当前快加速度
        
    Returns:
        Tuple[bool, bool, Optional[int], str, Dict]: (是否成功, 是否符合条件, 新快加速度, 消息, 详细信息)
    """
    try:
        logger.info(f"分析快加时间: 重量={target_weight}g, 时间={coarse_time_ms}ms, 速度={current_coarse_speed}")
        
        # 计算标准总周期
        standard_total_cycle = calculate_total_cycle_time(target_weight)
        
        # 计算快加时间占比
        coarse_time_ratio = calculate_coarse_time_ratio(target_weight)
        
        # 计算快加时间边界
        max_coarse_time = standard_total_cycle * coarse_time_ratio
        min_coarse_time = max_coarse_time * 0.7
        
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
        
        logger.info(f"标准总周期: {standard_total_cycle}ms, 快加占比: {coarse_time_ratio}, 时间范围: {min_coarse_time:.0f}-{max_coarse_time:.0f}ms")
        
        # 判断是否在合格范围内
        if min_coarse_time <= coarse_time_ms <= max_coarse_time:
            # 符合条件
            message = f"快加时间 {coarse_time_ms}ms 在合格范围 {min_coarse_time:.0f}-{max_coarse_time:.0f}ms 内，当前快加速度 {current_coarse_speed} 档符合条件"
            analysis_details["compliance_status"] = "compliant"
            return True, True, None, message, analysis_details
        
        # 不符合条件，计算新的快加速度
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
            # 速度异常
            analysis_details["speed_adjustment_error"] = adjustment_msg
            return True, False, None, adjustment_msg, analysis_details
            
    except Exception as e:
        error_msg = f"快加时间分析异常: {str(e)}"
        logger.error(error_msg)
        return False, False, None, error_msg, {}

def calculate_total_cycle_time(target_weight: float) -> int:
    """
    计算标准总周期时间
    
    Args:
        target_weight: 目标重量（克）
        
    Returns:
        int: 标准总周期时间（毫秒）
    """
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
    """
    计算快加时间占比
    
    Args:
        target_weight: 目标重量（克）
        
    Returns:
        float: 快加时间占比
    """
    if 100 <= target_weight <= 300:
        return 0.4  # 40%
    elif 300 < target_weight <= 400:
        return 0.5  # 50%
    else:
        # 对于超出范围的重量，使用默认值
        return 0.4 if target_weight < 100 else 0.5

def calculate_speed_adjustment(actual_time: int, min_time: float, max_time: float, 
                             current_speed: int) -> Tuple[bool, Optional[int], str]:
    """
    计算快加速度调整
    
    Args:
        actual_time: 实际快加时间（毫秒）
        min_time: 最小快加时间（毫秒）
        max_time: 最大快加时间（毫秒）
        current_speed: 当前快加速度
        
    Returns:
        Tuple[bool, Optional[int], str]: (是否成功, 新的快加速度, 消息)
    """
    if actual_time < min_time:
        # 快加时间太短，需要降低速度
        time_offset_ratio = (min_time - actual_time) / min_time * 100
        
        if time_offset_ratio <= 20:
            speed_adjustment = -1
        elif time_offset_ratio <= 50:
            speed_adjustment = -2
        elif time_offset_ratio <= 70:
            speed_adjustment = -3
        else:
            speed_adjustment = -4
        
        new_speed = current_speed + speed_adjustment
        message = f"快加时间过短，时间偏移比例 {time_offset_ratio:.1f}%，速度调整 {speed_adjustment}"
        
    elif actual_time > max_time:
        # 快加时间太长，需要提高速度
        time_offset_ratio = (actual_time - max_time) / max_time * 100
        
        if time_offset_ratio <= 40:
            speed_adjustment = 1
        elif time_offset_ratio <= 60:
            speed_adjustment = 2
        elif time_offset_ratio <= 90:
            speed_adjustment = 3
        else:
            speed_adjustment = 4
        
        new_speed = current_speed + speed_adjustment
        message = f"快加时间过长，时间偏移比例 {time_offset_ratio:.1f}%，速度调整 +{speed_adjustment}"
    else:
        # 理论上不会到这里
        return False, None, "快加时间分析逻辑错误"
    
    # 检查速度是否在有效范围内
    if new_speed < 1 or new_speed > 100:
        return False, None, f"料斗快加速度异常（计算得到 {new_speed}），请人工检修"
    
    return True, new_speed, message