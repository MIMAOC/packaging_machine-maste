#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应学习阶段WebAPI客户端 - 前端版本
负责与后端API通信，分析自适应学习阶段的参数是否符合条件

作者：AI助手
创建日期：2025-07-24
更新日期：2025-08-15（重构为类结构并添加错误格式化）
"""

import requests
import json
import logging
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import sys
import os

# 添加config模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class AdaptiveLearningAnalysisAPI:
    """
    自适应学习分析API客户端类 - 前端版本
    连接到后端FastAPI服务进行自适应学习参数分析
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
            "自适应学习分析失败: ",
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
            "target_weight": "目标重量",
            "actual_total_cycle_ms": "实际总周期",
            "actual_coarse_time_ms": "实际快加时间",
            "error_value": "误差值",
            "current_coarse_advance": "当前快加提前量",
            "current_fall_value": "当前落差值",
            "fine_flow_rate": "慢加流速",
            "adjustment_parameters": "调整参数",
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

    def analyze_adaptive_learning_parameters(self,
        target_weight: float,
        actual_total_cycle_ms: int,
        actual_coarse_time_ms: int,
        error_value: float,
        current_coarse_advance: float,
        current_fall_value: float,
        fine_flow_rate: float = None
    ) -> Tuple[bool, bool, Optional[Dict[str, Any]], str]:
        """
        分析自适应学习阶段参数是否符合条件
        
        Args:
            target_weight (float): 目标重量（克）
            actual_total_cycle_ms (int): 实际总周期（毫秒）
            actual_coarse_time_ms (int): 实际快加时间（毫秒）
            error_value (float): 误差值（克）
            current_coarse_advance (float): 当前快加提前量（克）
            current_fall_value (float): 当前落差值（克）
            fine_flow_rate (float): 慢加流速（g/s），来自慢加时间测定API响应
            
        Returns:
            Tuple[bool, bool, Optional[Dict[str, Any]], str]: 
                (请求是否成功, 是否符合条件, 调整参数字典, 消息)
        """
        try:
            self.logger.info(f"分析自适应学习参数: 目标重量={target_weight}g, 总周期={actual_total_cycle_ms}ms")
            self.logger.info(f"快加时间={actual_coarse_time_ms}ms, 误差={error_value}g, 慢加流速={fine_flow_rate}g/s")
            
            # 输入验证
            if target_weight <= 0:
                error_msg = self._format_error_message("目标重量必须大于0")
                return False, False, None, error_msg
            
            if actual_total_cycle_ms <= 0:
                error_msg = self._format_error_message("实际总周期必须大于0毫秒")
                return False, False, None, error_msg
            
            if actual_coarse_time_ms <= 0:
                error_msg = self._format_error_message("实际快加时间必须大于0毫秒")
                return False, False, None, error_msg
            
            # 调用后端API
            success, is_compliant, adjustment_params, message = self._call_backend_adaptive_learning_api(
                target_weight, actual_total_cycle_ms, actual_coarse_time_ms, 
                error_value, current_coarse_advance, current_fall_value, fine_flow_rate)
            
            if success:
                self.logger.info(f"后端API分析成功: 符合条件={is_compliant}, 消息={message}")
                if adjustment_params:
                    self.logger.debug(f"调整参数: {adjustment_params}")
                return True, is_compliant, adjustment_params, message
            else:
                # message 已经在 _call_backend_adaptive_learning_api 中格式化过了
                self.logger.error(f"后端API分析失败: {message}")
                return False, False, None, message
                
        except requests.exceptions.ConnectionError:
            error_msg = self._format_error_message(f"无法连接到后端API服务器 ({self.config.base_url})")
            self.logger.error(error_msg)
            return False, False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = self._format_error_message(f"后端API请求超时（超过{self.config.timeout}秒）")
            self.logger.error(error_msg)
            return False, False, None, error_msg
            
        except Exception as e:
            error_msg = self._format_error_message(f"自适应学习参数分析异常: {str(e)}")
            self.logger.error(error_msg)
            return False, False, None, error_msg

    def _call_backend_adaptive_learning_api(self,
        target_weight: float,
        actual_total_cycle_ms: int,
        actual_coarse_time_ms: int,
        error_value: float,
        current_coarse_advance: float,
        current_fall_value: float,
        fine_flow_rate: float = None
    ) -> Tuple[bool, bool, Optional[Dict[str, Any]], str]:
        """
        调用后端自适应学习分析API
        
        Returns:
            Tuple[bool, bool, Optional[Dict[str, Any]], str]: 
                (是否成功, 是否符合条件, 调整参数字典, 消息)
        """
        url = self.config.get_endpoint_url("adaptive_learning_analyze")
        
        payload = {
            "target_weight": target_weight,
            "actual_total_cycle_ms": actual_total_cycle_ms,
            "actual_coarse_time_ms": actual_coarse_time_ms,
            "error_value": error_value,
            "current_coarse_advance": current_coarse_advance,
            "current_fall_value": current_fall_value,
            "fine_flow_rate": fine_flow_rate,
            "analysis_type": "adaptive_learning",
            "client_version": "1.5.1",
            "timestamp": datetime.now().isoformat()
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
                    adjustment_params = result.get('adjustment_parameters')
                    message = result.get('message', '分析成功')
                    
                    return True, is_compliant, adjustment_params, message
                else:
                    return False, False, None, "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, False, None, error_msg

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
                    self.logger.warning(f"自适应学习参数验证失败 - 字段: {field}, 原始错误: {raw_error_message}, 格式化错误: {formatted_error_message}")
                    
                    return False, False, None, formatted_error_message
                else:
                    formatted_error = self._format_error_message("请求参数验证失败")
                    return False, False, None, formatted_error
                    
            except json.JSONDecodeError:
                error_msg = self._format_error_message("服务器返回422错误，但响应格式无法解析")
                self.logger.error(error_msg)
                return False, False, None, error_msg

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
            return False, False, None, formatted_error_message

    def test_api_connection(self) -> Tuple[bool, str]:
        """测试API连接状态"""
        try:
            url = self.config.get_endpoint_url("health")
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                return True, "自适应学习分析API连接正常"
            else:
                return False, f"API返回错误状态码: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "无法连接到自适应学习分析API服务器"
        except Exception as e:
            return False, f"API连接测试失败: {str(e)}"

# 创建全局API客户端实例
adaptive_learning_analysis_api = AdaptiveLearningAnalysisAPI()

def analyze_adaptive_learning_parameters(
    target_weight: float,
    actual_total_cycle_ms: int,
    actual_coarse_time_ms: int,
    error_value: float,
    current_coarse_advance: float,
    current_fall_value: float,
    fine_flow_rate: float = None
) -> Tuple[bool, bool, Optional[Dict[str, Any]], str]:
    """
    分析自适应学习阶段参数是否符合条件（便捷函数）
    """
    return adaptive_learning_analysis_api.analyze_adaptive_learning_parameters(
        target_weight, actual_total_cycle_ms, actual_coarse_time_ms, 
        error_value, current_coarse_advance, current_fall_value, fine_flow_rate)

def test_adaptive_learning_api_connection() -> Tuple[bool, str]:
    """
    测试自适应学习分析API连接状态（便捷函数）
    """
    return adaptive_learning_analysis_api.test_api_connection()