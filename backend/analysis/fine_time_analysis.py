# services/fine_time_analysis.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢加时间分析服务
根据附件6中的规则分析慢加时间是否符合条件

作者：AI助手
创建日期：2025-07-24
更新日期：2025-07-24（调用coarse_time_analysis模块避免代码重复）
"""

import logging
from typing import Dict, Any, Optional

# 导入快加时间分析模块中的函数
from analysis.coarse_time_analysis import calculate_total_cycle_time, calculate_coarse_time_ratio

class FineTimeAnalysisService:
    """
    慢加时间分析服务类
    
    根据目标重量、慢加时间和当前慢加速度分析是否符合条件，
    并提供速度调整建议
    """
    
    def __init__(self):
        """初始化分析服务"""
        self.logger = logging.getLogger(__name__)
        
        # 慢加流速边界条件（g/s）
        self.min_flow_rate = 0.35
        self.max_flow_rate = 0.55
        
        # 慢加速度范围
        self.min_fine_speed = 1
        self.max_fine_speed = 100
    
    def analyze_fine_time(self, target_weight: float, fine_time_ms: int, 
                         current_fine_speed: int, original_target_weight: float = 0.0,
                         flight_material_value: float = 0.0) -> Dict[str, Any]:
        """
        分析慢加时间是否符合条件
        
        Args:
            target_weight (float): 目标重量（克，固定为6g）
            fine_time_ms (int): 慢加时间（毫秒）
            current_fine_speed (int): 当前慢加速度
            original_target_weight (float): 原始目标重量（AI生产时输入的真实重量）
            flight_material_value (float): 快加飞料值（来自第二阶段）
            
        Returns:
            Dict[str, Any]: 分析结果
                - is_compliant (bool): 是否符合条件
                - new_fine_speed (Optional[int]): 新的慢加速度（如需调整）
                - coarse_advance (Optional[float]): 快加提前量（符合条件时计算）
                - message (str): 分析结果消息
                - analysis_details (Dict): 详细分析信息
        """
        try:
            self.logger.info(f"开始分析慢加时间: 重量={target_weight}g, 时间={fine_time_ms}ms, 速度={current_fine_speed}")
            self.logger.info(f"原始目标重量={original_target_weight}g, 快加飞料值={flight_material_value}g")
            
            # 计算慢加流速 = 目标重量 / (慢加时间/1000)，单位g/s
            fine_time_s = fine_time_ms / 1000.0
            flow_rate = target_weight / fine_time_s
            
            self.logger.info(f"计算得到慢加流速: {flow_rate:.3f} g/s")
            
            # 检查流速是否在边界条件内
            analysis_details = {
                "flow_rate": round(flow_rate, 3),
                "min_flow_rate": self.min_flow_rate,
                "max_flow_rate": self.max_flow_rate,
                "fine_time_s": fine_time_s,
                "is_in_range": self.min_flow_rate <= flow_rate <= self.max_flow_rate,
                "original_target_weight": original_target_weight,
                "flight_material_value": flight_material_value
            }
            
            # 如果在范围内，符合条件，计算快加提前量
            if self.min_flow_rate <= flow_rate <= self.max_flow_rate:
                # 计算快加提前量
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
            
            # 计算新的慢加速度
            new_fine_speed, adjustment_details = self._calculate_speed_adjustment(
                flow_rate, current_fine_speed)
            
            analysis_details.update(adjustment_details)
            
            # 检查新速度是否在有效范围内
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
            
            # 返回调整建议
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
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _calculate_coarse_advance(self, flow_rate: float, original_target_weight: float, 
                                 flight_material_value: float) -> float:
        """
        计算快加提前量
        根据附件6：快加提前量=快加飞料值 + 慢加流速*标准慢加时间 + 8g + 真实目标重量*1%
        
        Args:
            flow_rate (float): 慢加流速（g/s）
            original_target_weight (float): 原始目标重量（AI生产时输入的真实重量）
            flight_material_value (float): 快加飞料值
            
        Returns:
            float: 快加提前量（克）
        """
        try:
            # 调用coarse_time_analysis模块中的函数，避免代码重复
            standard_total_cycle = calculate_total_cycle_time(original_target_weight)
            coarse_time_ratio = calculate_coarse_time_ratio(original_target_weight)
            
            # 计算标准慢加时间（秒）
            standard_fine_time_s = standard_total_cycle * (1 - coarse_time_ratio) / 1000.0
            
            # 根据附件6公式计算快加提前量
            coarse_advance = (flight_material_value + 
                            flow_rate * standard_fine_time_s + 
                            8.0 + 
                            original_target_weight * 0.01)
            
            self.logger.info(f"快加提前量计算: 飞料值={flight_material_value}g + "
                           f"慢加流速*标准慢加时间={flow_rate:.3f}*{standard_fine_time_s:.3f}={flow_rate * standard_fine_time_s:.3f}g + "
                           f"8g + 目标重量*1%={original_target_weight}*0.01={original_target_weight * 0.01:.3f}g = {coarse_advance:.3f}g")
            self.logger.info(f"使用coarse_time_analysis模块: 标准总周期={standard_total_cycle}ms, 快加占比={coarse_time_ratio}")
            
            return round(coarse_advance, 1)
            
        except Exception as e:
            error_msg = f"计算快加提前量异常: {str(e)}"
            self.logger.error(error_msg)
            return 0.0
    
    def _calculate_speed_adjustment(self, flow_rate: float, 
                                  current_fine_speed: int) -> tuple[Optional[int], Dict[str, Any]]:
        """
        计算慢加速度调整
        
        Args:
            flow_rate (float): 当前流速
            current_fine_speed (int): 当前慢加速度
            
        Returns:
            tuple[Optional[int], Dict[str, Any]]: (新的慢加速度, 调整详情)
        """
        try:
            adjustment_details = {
                "flow_rate": flow_rate,
                "current_fine_speed": current_fine_speed
            }
            
            if flow_rate < self.min_flow_rate:
                # 流速过低，需要增加慢加速度
                offset_ratio = (self.min_flow_rate - flow_rate) / self.min_flow_rate * 100
                adjustment_details["offset_ratio"] = round(offset_ratio, 2)
                adjustment_details["offset_type"] = "low_flow_rate"
                
                # 根据偏移比例确定调整量
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
                # 流速过高，需要减少慢加速度
                offset_ratio = (flow_rate - self.max_flow_rate) / self.max_flow_rate * 100
                adjustment_details["offset_ratio"] = round(offset_ratio, 2)
                adjustment_details["offset_type"] = "high_flow_rate"
                
                # 根据偏移比例确定调整量
                if offset_ratio <= 60:
                    adjustment = 1
                else:
                    adjustment = 2
                
                new_fine_speed = current_fine_speed - adjustment
                adjustment_details["adjustment"] = adjustment
                adjustment_details["direction"] = "decrease"
                
            else:
                # 在范围内，不需要调整
                new_fine_speed = current_fine_speed
                adjustment_details["adjustment"] = 0
                adjustment_details["direction"] = "none"
            
            adjustment_details["new_fine_speed"] = new_fine_speed
            
            self.logger.info(f"速度调整计算: {current_fine_speed} → {new_fine_speed}, "
                           f"偏移比例: {adjustment_details.get('offset_ratio', 0):.2f}%")
            
            return new_fine_speed, adjustment_details
            
        except Exception as e:
            error_msg = f"计算速度调整异常: {str(e)}"
            self.logger.error(error_msg)
            return None, {"error": error_msg}