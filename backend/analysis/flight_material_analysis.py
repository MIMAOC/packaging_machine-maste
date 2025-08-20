"""
飞料值分析模块

作者：C
创建日期：2025-07-23
"""
from typing import Tuple, List, Dict, Any

def analyze_flight_material_values(target_weight: float, 
                                 recorded_weights: List[float]) -> Tuple[bool, float, List[float], str, Dict[str, Any]]:
    try:
        if len(recorded_weights) != 3:
            error_msg = f"需要3次实时重量数据，实际提供了{len(recorded_weights)}次"
            return False, 0.0, [], error_msg, {}
        
        flight_details = []
        for i, actual_weight in enumerate(recorded_weights):
            flight_material = round(actual_weight - target_weight, 2)
            flight_details.append(flight_material)
        
        average_flight_material = round(sum(flight_details) / len(flight_details), 2)
        
        analysis_details = {
            "target_weight": target_weight,
            "recorded_weights": recorded_weights,
            "flight_material_calculations": [
                {
                    "attempt": i + 1,
                    "actual_weight": round(recorded_weights[i], 1),
                    "flight_material": round(flight_details[i], 2),
                    "calculation": f"{recorded_weights[i]:.1f}g - {target_weight:.1f}g = {flight_details[i]:.2f}g"
                }
                for i in range(3)
            ],
            "average_calculation": {
                "formula": f"({flight_details[0]:.2f} + {flight_details[1]:.2f} + {flight_details[2]:.2f}) / 3",
                "result": round(average_flight_material, 2)
            },
            "statistics": {
                "min_flight_material": round(min(flight_details), 2),
                "max_flight_material": round(max(flight_details), 2),
                "variance": round(calculate_variance(flight_details), 2),
                "standard_deviation": round(calculate_standard_deviation(flight_details), 2)
            }
        }
        
        message = (f"飞料值分析成功：\n"
                f"目标重量: {target_weight:.1f}g\n"
                f"3次实时重量: {recorded_weights[0]:.1f}g, {recorded_weights[1]:.1f}g, {recorded_weights[2]:.1f}g\n"
                f"3次飞料值: {flight_details[0]:.2f}g, {flight_details[1]:.2f}g, {flight_details[2]:.2f}g\n"
                f"平均飞料值: {average_flight_material:.2f}g")
        
        return True, average_flight_material, flight_details, message, analysis_details
        
    except Exception as e:
        error_msg = f"飞料值分析异常: {str(e)}"
        return False, 0.0, [], error_msg, {}

def calculate_variance(values: List[float]) -> float:
    if not values:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance

def calculate_standard_deviation(values: List[float]) -> float:
    return calculate_variance(values) ** 0.5

def get_flight_material_statistics(flight_details: List[float]) -> Dict[str, Any]:
    if not flight_details:
        return {}
    
    return {
        "count": len(flight_details),
        "min": round(min(flight_details), 2),
        "max": round(max(flight_details), 2),
        "average": round(sum(flight_details) / len(flight_details), 2),
        "variance": round(calculate_variance(flight_details), 2),
        "standard_deviation": round(calculate_standard_deviation(flight_details), 2),
        "range": round(max(flight_details) - min(flight_details), 2)
    }