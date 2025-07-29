# analysis/weight_analysis.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重量分析模块
根据目标重量分析推荐的快加速度

作者：AI助手
创建日期：2025-07-23
"""

import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

# 快加速度规则
SPEED_RULES = [
    {"min_weight": 100, "max_weight": 125, "coarse_speed": 70, "description": "100-125g -> 70档"},
    {"min_weight": 125, "max_weight": 175, "coarse_speed": 72, "description": "125-175g -> 72档"},
    {"min_weight": 175, "max_weight": 225, "coarse_speed": 74, "description": "175-225g -> 74档"},
    {"min_weight": 225, "max_weight": 275, "coarse_speed": 76, "description": "225-275g -> 76档"},
    {"min_weight": 275, "max_weight": 325, "coarse_speed": 78, "description": "275-325g -> 78档"},
    {"min_weight": 325, "max_weight": 375, "coarse_speed": 80, "description": "325-375g -> 80档"},
    {"min_weight": 375, "max_weight": 400, "coarse_speed": 82, "description": "375-400g -> 82档"},
]

def analyze_target_weight_for_coarse_speed(target_weight: float) -> Tuple[bool, int, str, Dict[str, Any]]:
    """
    根据目标重量分析推荐的快加速度
    
    Args:
        target_weight: 目标重量（克）
        
    Returns:
        Tuple[bool, int, str, Dict]: (是否成功, 快加速度, 消息, 规则信息)
    """
    try:
        logger.info(f"分析目标重量: {target_weight}g")
        
        # 查找匹配的规则
        for rule in SPEED_RULES:
            if rule["min_weight"] <= target_weight < rule["max_weight"]:
                speed = rule["coarse_speed"]
                message = f"重量 {target_weight}g 在范围 {rule['min_weight']}-{rule['max_weight']}g 内，推荐快加速度 {speed} 档"
                
                rule_info = {
                    "matched_rule": rule,
                    "weight_range": f"{rule['min_weight']}-{rule['max_weight']}g",
                    "recommended_speed": speed
                }
                
                logger.info(f"匹配规则: {rule['description']}")
                return True, speed, message, rule_info
        
        # 处理边界情况
        if target_weight < 100:
            speed = 70
            message = f"重量 {target_weight}g 小于最小范围，使用最小速度 {speed} 档"
            rule_info = {
                "matched_rule": None,
                "weight_range": f"< 100g",
                "recommended_speed": speed,
                "boundary_case": "below_minimum"
            }
            logger.info(f"边界情况（小于最小值）: {message}")
            return True, speed, message, rule_info
            
        elif target_weight >= 400:
            speed = 82
            message = f"重量 {target_weight}g 大于最大范围，使用最大速度 {speed} 档"
            rule_info = {
                "matched_rule": None,
                "weight_range": f">= 400g",
                "recommended_speed": speed,
                "boundary_case": "above_maximum"
            }
            logger.info(f"边界情况（大于最大值）: {message}")
            return True, speed, message, rule_info
        else:
            # 理论上不会到这里
            error_msg = f"重量 {target_weight}g 无法匹配任何规则"
            logger.error(error_msg)
            return False, 0, error_msg, {}
            
    except Exception as e:
        error_msg = f"分析目标重量异常: {str(e)}"
        logger.error(error_msg)
        return False, 0, error_msg, {}

def get_all_speed_rules() -> Dict[str, Any]:
    """
    获取所有速度规则
    
    Returns:
        Dict: 包含所有规则的字典
    """
    return {
        "rules": SPEED_RULES,
        "total_rules": len(SPEED_RULES),
        "weight_range": f"{SPEED_RULES[0]['min_weight']}-{SPEED_RULES[-1]['max_weight']}g",
        "speed_range": f"{min(rule['coarse_speed'] for rule in SPEED_RULES)}-{max(rule['coarse_speed'] for rule in SPEED_RULES)}档"
    }