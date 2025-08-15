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
        
    def _format_error_message(self, error_message: str) -> str:
        """
        格式化API错误消息，使其更用户友好
        
        Args:
            error_message (str): 原始错误消息
            
        Returns:
            str: 格式化后的错误消息
        """
        # 移除技术性前缀
        formatted_msg = error_message
        
        # 处理常见的验证错误前缀
        prefixes_to_remove = [
            "Value error, ",
            "Validation error, ",
            "Request validation failed: ",
            "慢加时间分析失败: ",
            "后端API分析失败: ",
            "参数验证失败: ",
            "网络请求失败: ",
            "分析过程异常: "
        ]
        
        for prefix in prefixes_to_remove:
            if formatted_msg.startswith(prefix):
                formatted_msg = formatted_msg.replace(prefix, "")
                break
        
        # 处理技术术语替换，让用户更容易理解
        replacements = {
            "fine_time_ms": "慢加时间",
            "target_weight": "目标重量",
            "current_fine_speed": "当前慢加速度",
            "original_target_weight": "原始目标重量",
            "flight_material_value": "快加飞料值",
            "new_fine_speed": "新慢加速度",
            "coarse_advance": "快加提前量",
            "fine_flow_rate": "慢加流速",
            "HTTP错误": "网络连接错误",
            "JSON解析失败": "数据格式错误",
            "连接超时": "网络超时",
            "连接拒绝": "服务器无响应",
            "connection error": "网络连接错误",
            "timeout": "网络超时"
        }
        
        for tech_term, user_friendly in replacements.items():
            formatted_msg = formatted_msg.replace(tech_term, user_friendly)
        
        return formatted_msg.strip()
    
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

        # 处理 422 验证错误，使用格式化辅助方法
        elif response.status_code == 422:
            try:
                error_data = response.json()
                self.logger.debug(f"422错误响应: {error_data}")
                
                # 提取具体的错误信息
                if 'error' in error_data:
                    raw_error_message = error_data['error']
                    
                    # 使用格式化辅助方法处理错误消息
                    formatted_error_message = self._format_error_message(raw_error_message)
                    
                    # 记录详细的验证错误信息
                    field = error_data.get('field', '未知字段')
                    self.logger.warning(f"慢加时间参数验证失败 - 字段: {field}, 原始错误: {raw_error_message}, 格式化错误: {formatted_error_message}")
                    
                    return False, False, None, None, None, formatted_error_message
                else:
                    formatted_error = self._format_error_message("请求参数验证失败")
                    return False, False, None, None, None, formatted_error
                    
            except json.JSONDecodeError:
                error_msg = self._format_error_message("服务器返回422错误，但响应格式无法解析")
                self.logger.error(error_msg)
                return False, False, None, None, None, error_msg

        # 处理其他HTTP错误状态码
        else:
            try:
                # 尝试解析错误响应
                error_data = response.json()
                raw_error_message = error_data.get('error', f"HTTP错误: {response.status_code}")
            except:
                raw_error_message = f"后端API HTTP错误: {response.status_code}"
            
            # 使用格式化辅助方法处理错误消息
            formatted_error_message = self._format_error_message(raw_error_message)
            
            self.logger.error(f"HTTP错误: {response.status_code}, 原始响应: {raw_error_message}, 格式化响应: {formatted_error_message}")
            return False, False, None, None, None, formatted_error_message
    
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
        
        # 输入验证
        if fine_time_ms <= 0:
            error_msg = self._format_error_message("慢加时间必须大于0毫秒")
            return False, False, None, None, None, error_msg
        
        if current_fine_speed <= 0:
            error_msg = self._format_error_message("当前慢加速度必须大于0")
            return False, False, None, None, None, error_msg
        
        if target_weight <= 0:
            error_msg = self._format_error_message("目标重量必须大于0")
            return False, False, None, None, None, error_msg
        
        # 调用后端API
        success, is_compliant, new_speed, coarse_advance, fine_flow_rate, message = self._call_backend_fine_time_api(
            target_weight, fine_time_ms, current_fine_speed, original_target_weight, flight_material_value)
        
        if success:
            self.logger.info(f"后端API分析成功: 符合条件={is_compliant}, 新速度={new_speed}, 快加提前量={coarse_advance}, 慢加流速={fine_flow_rate}")
            return True, is_compliant, new_speed, coarse_advance, fine_flow_rate, message
        else:
            # message 已经在 _call_backend_fine_time_api 中格式化过了
            self.logger.error(f"后端API分析失败: {message}")
            return False, False, None, None, None, message
            
    except requests.exceptions.ConnectionError:
        error_msg = self._format_error_message(f"无法连接到后端API服务器 ({self.config.base_url})")
        self.logger.error(error_msg)
        return False, False, None, None, None, error_msg
        
    except requests.exceptions.Timeout:
        error_msg = self._format_error_message(f"后端API请求超时（超过{self.config.timeout}秒）")
        self.logger.error(error_msg)
        return False, False, None, None, None, error_msg
        
    except Exception as e:
        error_msg = self._format_error_message(f"慢加时间分析异常: {str(e)}")
        self.logger.error(error_msg)
        return False, False, None, None, None, error_msg

def test_fine_time_api_connection() -> Tuple[bool, str]:
    """
    测试慢加时间分析API连接状态（便捷函数）
    
    Returns:
        Tuple[bool, str]: (连接状态, 消息)
    """
    return fine_time_analysis_api.test_api_connection()