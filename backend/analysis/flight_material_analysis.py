# analysis/flight_material_analysis.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞料值分析模块
分析实时重量并计算平均飞料值

作者：AI助手
创建日期：2025-07-23
"""

import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

def analyze_flight_material_values(target_weight: float, 
                                 recorded_weights: List[float]) -> Tuple[bool, float, List[float], str, Dict[str, Any]]:
    """
    分析飞料值
    
    Args:
        target_weight: 目标重量（克）
        recorded_weights: 3次记录的实时重量（克）
        
    Returns:
        Tuple[bool, float, List[float], str, Dict]: (是否成功, 平均飞料值, 3次飞料值详情, 消息, 分析详情)
    """
    try:
        logger.info(f"分析飞料值: 目标重量={target_weight}g, 实时重量={recorded_weights}")
        
        # 输入验证
        if len(recorded_weights) != 3:
            error_msg = f"需要3次实时重量数据，实际提供了{len(recorded_weights)}次"
            logger.error(error_msg)
            return False, 0.0, [], error_msg, {}
        
        # 计算3次快加飞料值 = 实时重量 - 目标重量
        flight_details = []
        for i, actual_weight in enumerate(recorded_weights):
            flight_material = round(actual_weight - target_weight, 2)  # 保留2位小数
            flight_details.append(flight_material)
            logger.debug(f"第{i+1}次飞料值: {actual_weight:.1f}g - {target_weight:.1f}g = {flight_material:.2f}g")

        # 计算平均飞料值 = (飞料值1 + 飞料值2 + 飞料值3) / 3
        average_flight_material = round(sum(flight_details) / len(flight_details), 2)  # 保留2位小数
        
        # 构建分析详情
        analysis_details = {
            "target_weight": target_weight,
            "recorded_weights": recorded_weights,
            "flight_material_calculations": [
                {
                    "attempt": i + 1,
                    "actual_weight": round(recorded_weights[i], 1),  # 保留1位小数
                    "flight_material": round(flight_details[i], 2),  # 保留2位小数
                    "calculation": f"{recorded_weights[i]:.1f}g - {target_weight:.1f}g = {flight_details[i]:.2f}g"
                }
                for i in range(3)
            ],
            "average_calculation": {
                "formula": f"({flight_details[0]:.2f} + {flight_details[1]:.2f} + {flight_details[2]:.2f}) / 3",
                "result": round(average_flight_material, 2)  # 保留2位小数
            },
            "statistics": {
                "min_flight_material": round(min(flight_details), 2),  # 保留2位小数
                "max_flight_material": round(max(flight_details), 2),  # 保留2位小数
                "variance": round(calculate_variance(flight_details), 2),  # 保留2位小数
                "standard_deviation": round(calculate_standard_deviation(flight_details), 2)  # 保留2位小数
            }
        }
        
        message = (f"飞料值分析成功：\n"
                f"目标重量: {target_weight:.1f}g\n"
                f"3次实时重量: {recorded_weights[0]:.1f}g, {recorded_weights[1]:.1f}g, {recorded_weights[2]:.1f}g\n"
                f"3次飞料值: {flight_details[0]:.2f}g, {flight_details[1]:.2f}g, {flight_details[2]:.2f}g\n"
                f"平均飞料值: {average_flight_material:.2f}g")

        logger.info(f"飞料值分析完成，平均飞料值: {average_flight_material:.2f}g")
        return True, average_flight_material, flight_details, message, analysis_details
        
    except Exception as e:
        error_msg = f"飞料值分析异常: {str(e)}"
        logger.error(error_msg)
        return False, 0.0, [], error_msg, {}

def calculate_variance(values: List[float]) -> float:
    """计算方差"""
    if not values:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance

def calculate_standard_deviation(values: List[float]) -> float:
    """计算标准差"""
    return calculate_variance(values) ** 0.5

def get_flight_material_statistics(flight_details: List[float]) -> Dict[str, Any]:
    """
    获取飞料值统计信息
    
    Args:
        flight_details: 飞料值列表
        
    Returns:
        Dict: 统计信息
    """
    if not flight_details:
        return {}
    
    return {
        "count": len(flight_details),
        "min": round(min(flight_details), 2),  # 保留2位小数
        "max": round(max(flight_details), 2),  # 保留2位小数
        "average": round(sum(flight_details) / len(flight_details), 2),  # 保留2位小数
        "variance": round(calculate_variance(flight_details), 2),  # 保留2位小数
        "standard_deviation": round(calculate_standard_deviation(flight_details), 2),  # 保留2位小数
        "range": round(max(flight_details) - min(flight_details), 2)  # 保留2位小数
    }