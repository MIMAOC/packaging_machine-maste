"""
重量分析模块

作者：C
创建日期：2025-07-23
"""
from typing import Tuple, Dict, Any

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
    try:
        for rule in SPEED_RULES:
            if rule["min_weight"] <= target_weight < rule["max_weight"]:
                speed = rule["coarse_speed"]
                message = f"重量 {target_weight}g 在范围 {rule['min_weight']}-{rule['max_weight']}g 内，推荐快加速度 {speed} 档"
                
                rule_info = {
                    "matched_rule": rule,
                    "weight_range": f"{rule['min_weight']}-{rule['max_weight']}g",
                    "recommended_speed": speed
                }
                return True, speed, message, rule_info
        
        if target_weight < 100:
            speed = 70
            message = f"重量 {target_weight}g 小于最小范围，使用最小速度 {speed} 档"
            rule_info = {
                "matched_rule": None,
                "weight_range": f"< 100g",
                "recommended_speed": speed,
                "boundary_case": "below_minimum"
            }
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
            return True, speed, message, rule_info
        else:
            # 理论上不会到这里
            error_msg = f"重量 {target_weight}g 无法匹配任何规则"
            return False, 0, error_msg, {}
            
    except Exception as e:
        error_msg = f"分析目标重量异常: {str(e)}"
        return False, 0, error_msg, {}

def get_all_speed_rules() -> Dict[str, Any]:
    return {
        "rules": SPEED_RULES,
        "total_rules": len(SPEED_RULES),
        "weight_range": f"{SPEED_RULES[0]['min_weight']}-{SPEED_RULES[-1]['max_weight']}g",
        "speed_range": f"{min(rule['coarse_speed'] for rule in SPEED_RULES)}-{max(rule['coarse_speed'] for rule in SPEED_RULES)}档"
    }