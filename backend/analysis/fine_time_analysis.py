"""
慢加时间分析服务

作者：C
创建日期：2025-07-24
更新日期：2025-08-19
"""
from typing import Dict, Any, Optional

from analysis.coarse_time_analysis import calculate_total_cycle_time, calculate_coarse_time_ratio

class FineTimeAnalysisService:
    def __init__(self):
        self.min_flow_rate = 0.30
        self.max_flow_rate = 0.50
        
        self.min_fine_speed = 1
        self.max_fine_speed = 100
    
    def analyze_fine_time(self, target_weight: float, fine_time_ms: int, 
                         current_fine_speed: int, original_target_weight: float = 0.0,
                         flight_material_value: float = 0.0) -> Dict[str, Any]:
        try:
            fine_time_s = fine_time_ms / 1000.0
            flow_rate = target_weight / fine_time_s
            
            analysis_details = {
                "flow_rate": round(flow_rate, 3),
                "min_flow_rate": self.min_flow_rate,
                "max_flow_rate": self.max_flow_rate,
                "fine_time_s": fine_time_s,
                "is_in_range": self.min_flow_rate <= flow_rate <= self.max_flow_rate,
                "original_target_weight": original_target_weight,
                "flight_material_value": flight_material_value
            }
            
            if self.min_flow_rate <= flow_rate <= self.max_flow_rate:
                coarse_advance = None
                if original_target_weight > 0:
                    coarse_advance = self._calculate_coarse_advance(
                        flow_rate, original_target_weight, flight_material_value)
                    analysis_details["coarse_advance"] = coarse_advance
                    
                    message = (f"✅ 慢加时间符合条件！流速: {flow_rate:.3f} g/s"
                             f"，计算快加提前量: {coarse_advance:.1f}g")
                else:
                    message = f"✅ 慢加时间符合条件！流速: {flow_rate:.3f} g/s）"
                
                return {
                    "is_compliant": True,
                    "new_fine_speed": None,
                    "coarse_advance": coarse_advance,
                    "fine_flow_rate": round(flow_rate, 3),
                    "message": message,
                    "analysis_details": analysis_details
                }
            
            new_fine_speed, adjustment_details = self._calculate_speed_adjustment(
                flow_rate, current_fine_speed)
            
            analysis_details.update(adjustment_details)
            
            if new_fine_speed is None or new_fine_speed < self.min_fine_speed or new_fine_speed > self.max_fine_speed:
                error_msg = f"❌ 慢加速度异常，请人工检修！计算得到速度: {new_fine_speed}"
                return {
                    "is_compliant": False,
                    "new_fine_speed": None,
                    "coarse_advance": None,
                    "fine_flow_rate": round(flow_rate, 3),
                    "message": error_msg,
                    "analysis_details": analysis_details
                }
            
            if flow_rate < self.min_flow_rate:
                message = f"⚠️ 流速过低({flow_rate:.3f} g/s < {self.min_flow_rate} g/s)，调整慢加速度: {current_fine_speed} → {new_fine_speed}"
            else:
                message = f"⚠️ 流速过高({flow_rate:.3f} g/s > {self.max_flow_rate} g/s)，调整慢加速度: {current_fine_speed} → {new_fine_speed}"
            
            return {
                "is_compliant": False,
                "new_fine_speed": new_fine_speed,
                "coarse_advance": None,
                "fine_flow_rate": round(flow_rate, 3),
                "message": message,
                "analysis_details": analysis_details
            }
            
        except Exception as e:
            error_msg = f"慢加时间分析异常: {str(e)}"
            raise ValueError(error_msg)
    
    def _calculate_coarse_advance(self, flow_rate: float, original_target_weight: float, 
                                 flight_material_value: float) -> float:
        try:
            standard_total_cycle = calculate_total_cycle_time(original_target_weight)
            coarse_time_ratio = calculate_coarse_time_ratio(original_target_weight)
            
            standard_fine_time_s = standard_total_cycle * (1 - coarse_time_ratio) / 1000.0
            
            coarse_advance = (flight_material_value + 
                            flow_rate * standard_fine_time_s + 
                            8.0 + 
                            original_target_weight * 0.01)
            
            return round(coarse_advance, 1)
            
        except Exception as e:
            error_msg = f"计算快加提前量异常: {str(e)}"
            return 0.0
    
    def _calculate_speed_adjustment(self, flow_rate: float, 
                                  current_fine_speed: int) -> tuple[Optional[int], Dict[str, Any]]:
        try:
            adjustment_details = {
                "flow_rate": flow_rate,
                "current_fine_speed": current_fine_speed
            }
            
            if flow_rate < self.min_flow_rate:
                offset_ratio = (self.min_flow_rate - flow_rate) / self.min_flow_rate * 100
                adjustment_details["offset_ratio"] = round(offset_ratio, 2)
                adjustment_details["offset_type"] = "low_flow_rate"
                
                if offset_ratio <= 60:
                    adjustment = 1
                elif offset_ratio <= 90:
                    adjustment = 2
                else:
                    adjustment = 3
                
                new_fine_speed = current_fine_speed + adjustment
                adjustment_details["adjustment"] = adjustment
                adjustment_details["direction"] = "increase"
                
            elif flow_rate > self.max_flow_rate:
                offset_ratio = (flow_rate - self.max_flow_rate) / self.max_flow_rate * 100
                adjustment_details["offset_ratio"] = round(offset_ratio, 2)
                adjustment_details["offset_type"] = "high_flow_rate"
                
                if offset_ratio <= 60:
                    adjustment = 1
                else:
                    adjustment = 2
                
                new_fine_speed = current_fine_speed - adjustment
                adjustment_details["adjustment"] = adjustment
                adjustment_details["direction"] = "decrease"
                
            else:
                new_fine_speed = current_fine_speed
                adjustment_details["adjustment"] = 0
                adjustment_details["direction"] = "none"
            
            adjustment_details["new_fine_speed"] = new_fine_speed
            
            return new_fine_speed, adjustment_details
            
        except Exception as e:
            error_msg = f"计算速度调整异常: {str(e)}"
            return None, {"error": error_msg}