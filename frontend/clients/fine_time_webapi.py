# clients/fine_time_webapi.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
慢加时间WebAPI分析模块 - 前端版本
用于分析慢加时间是否符合条件，并提供速度调整建议

作者：AI助手
创建日期：2025-07-24
更新日期：2025-07-24（返回慢加流速）
"""

import requests
import json
import logging
from typing import Tuple, Optional, Dict, Any
import sys
import os

# 添加config模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class FineTimeAnalysisAPI:
    """
    慢加时间分析API客户端类 - 前端版本
    连接到后端FastAPI服务进行慢加时间分析
    """
    
    def __init__(self):
        """初始化API客户端"""
        self.config = get_api_config()
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def analyze_fine_time(self, target_weight: float, fine_time_ms: int, 
                         current_fine_speed: int, original_target_weight: float = 0.0,
                         flight_material_value: float = 0.0) -> Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]:
        """
        分析慢加时间是否符合条件
        
        Args:
            target_weight (float): 目标重量（克）固定为6g
            fine_time_ms (int): 慢加时间（毫秒）
            current_fine_speed (int): 当前慢加速度
            original_target_weight (float): 原始目标重量（AI生产时输入的真实重量）
            flight_material_value (float): 快加飞料值（来自第二阶段）
            
        Returns:
            Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]: 
                (是否成功, 是否符合条件, 新的慢加速度, 快加提前量, 慢加流速, 消息)
        """
        try:
            self.logger.info(f"分析慢加时间: 重量={target_weight}g, 时间={fine_time_ms}ms, 速度={current_fine_speed}")
            self.logger.info(f"原始目标重量={original_target_weight}g, 快加飞料值={flight_material_value}g")
            
            # 调用后端API
            success, is_compliant, new_speed, coarse_advance, fine_flow_rate, message = self._call_backend_fine_time_api(
                target_weight, fine_time_ms, current_fine_speed, original_target_weight, flight_material_value)
            
            if success:
                self.logger.info(f"后端API分析成功: 符合条件={is_compliant}, 新速度={new_speed}, 快加提前量={coarse_advance}, 慢加流速={fine_flow_rate}")
                return True, is_compliant, new_speed, coarse_advance, fine_flow_rate, message
            else:
                error_msg = f"后端API分析失败: {message}"
                self.logger.error(error_msg)
                return False, False, None, None, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})"
            self.logger.error(error_msg)
            return False, False, None, None, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            self.logger.error(error_msg)
            return False, False, None, None, None, error_msg
            
        except Exception as e:
            error_msg = f"慢加时间分析异常: {str(e)}"
            self.logger.error(error_msg)
            return False, False, None, None, None, error_msg
    
    def _call_backend_fine_time_api(self, target_weight: float, fine_time_ms: int, 
                                   current_fine_speed: int, original_target_weight: float,
                                   flight_material_value: float) -> Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]:
        """
        调用后端慢加时间分析API
        
        Args:
            target_weight (float): 目标重量
            fine_time_ms (int): 慢加时间
            current_fine_speed (int): 当前慢加速度
            original_target_weight (float): 原始目标重量
            flight_material_value (float): 快加飞料值
            
        Returns:
            Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]: 
                (是否成功, 是否符合条件, 新慢加速度, 快加提前量, 慢加流速, 消息)
        """
        url = self.config.get_endpoint_url("fine_time_analyze")
        
        payload = {
            "target_weight": target_weight,
            "fine_time_ms": fine_time_ms,
            "current_fine_speed": current_fine_speed,
            "original_target_weight": original_target_weight,
            "flight_material_value": flight_material_value,
            "analysis_type": "fine_time",
            "client_version": "1.5.1"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'MHWPM-Frontend/1.5.1'
        }
        
        self.logger.info(f"发送后端API请求: {url}")
        self.logger.debug(f"请求数据: {payload}")
        
        # 发送POST请求
        response = requests.post(
            url=url,
            json=payload,
            headers=headers,
            timeout=self.config.timeout
        )
        
        # 处理响应
        if response.status_code == 200:
            try:
                result = response.json()
                
                if result.get('success', False):
                    is_compliant = result.get('is_compliant', False)
                    new_speed = result.get('new_fine_speed')
                    coarse_advance = result.get('coarse_advance')
                    fine_flow_rate = result.get('fine_flow_rate')  # 新增：获取慢加流速
                    message = result.get('message', '分析成功')
                    
                    return True, is_compliant, new_speed, coarse_advance, fine_flow_rate, message
                else:
                    return False, False, None, None, None, "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, False, None, None, None, error_msg
        else:
            error_msg = f"后端API HTTP错误: {response.status_code}"
            return False, False, None, None, None, error_msg
    
    def test_api_connection(self) -> Tuple[bool, str]:
        """测试API连接状态"""
        try:
            url = self.config.get_endpoint_url("health")
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                return True, "慢加时间分析API连接正常"
            else:
                return False, f"API返回错误状态码: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "无法连接到慢加时间分析API服务器"
        except Exception as e:
            return False, f"API连接测试失败: {str(e)}"

# 创建全局API客户端实例
fine_time_analysis_api = FineTimeAnalysisAPI()

def analyze_fine_time(target_weight: float, fine_time_ms: int, 
                     current_fine_speed: int, original_target_weight: float = 0.0,
                     flight_material_value: float = 0.0) -> Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]:
    """
    分析慢加时间（便捷函数）
    
    Args:
        target_weight (float): 目标重量（克）
        fine_time_ms (int): 慢加时间（毫秒）
        current_fine_speed (int): 当前慢加速度
        original_target_weight (float): 原始目标重量（AI生产时输入的真实重量）
        flight_material_value (float): 快加飞料值（来自第二阶段）
        
    Returns:
        Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]: 
            (是否成功, 是否符合条件, 新的慢加速度, 快加提前量, 慢加流速, 消息)
    """
    return fine_time_analysis_api.analyze_fine_time(target_weight, fine_time_ms, current_fine_speed, 
                                                   original_target_weight, flight_material_value)

def test_fine_time_api_connection() -> Tuple[bool, str]:
    """
    测试慢加时间分析API连接状态（便捷函数）
    
    Returns:
        Tuple[bool, str]: (连接状态, 消息)
    """
    return fine_time_analysis_api.test_api_connection()