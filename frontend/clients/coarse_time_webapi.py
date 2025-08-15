# clients/coarse_time_webapi.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快加时间WebAPI分析模块 - 前端版本
用于分析快加时间是否符合条件，并提供速度调整建议

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-23（修改为连接后端API服务）
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

class CoarseTimeAnalysisAPI:
    """
    快加时间分析API客户端类 - 前端版本
    连接到后端FastAPI服务进行快加时间分析
    """
    
    def __init__(self):
        """初始化API客户端"""
        self.config = get_api_config()
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def analyze_coarse_time(self, target_weight: float, coarse_time_ms: int, 
                          current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str]:
        """
        分析快加时间是否符合条件
        
        Args:
            target_weight (float): 目标重量（克）
            coarse_time_ms (int): 快加时间（毫秒）
            current_coarse_speed (int): 当前快加速度
            
        Returns:
            Tuple[bool, bool, Optional[int], str]: (是否成功, 是否符合条件, 新的快加速度, 消息)
        """
        try:
            self.logger.info(f"分析快加时间: 重量={target_weight}g, 时间={coarse_time_ms}ms, 速度={current_coarse_speed}")
            
            # 调用后端API
            success, is_compliant, new_speed, message = self._call_backend_coarse_time_api(
                target_weight, coarse_time_ms, current_coarse_speed)
            
            if success:
                self.logger.info(f"后端API分析成功: 符合条件={is_compliant}, 新速度={new_speed}")
                return True, is_compliant, new_speed, message
            else:
                error_msg = f"后端API分析失败: {message}"
                self.logger.error(error_msg)
                return False, False, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})"
            self.logger.error(error_msg)
            return False, False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            self.logger.error(error_msg)
            return False, False, None, error_msg
            
        except Exception as e:
            error_msg = f"快加时间分析异常: {str(e)}"
            self.logger.error(error_msg)
            return False, False, None, error_msg
    
    def _call_backend_coarse_time_api(self, target_weight: float, coarse_time_ms: int, 
                                    current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str]:
        """
        调用后端快加时间分析API
        
        Args:
            target_weight (float): 目标重量
            coarse_time_ms (int): 快加时间
            current_coarse_speed (int): 当前快加速度
            
        Returns:
            Tuple[bool, bool, Optional[int], str]: (是否成功, 是否符合条件, 新快加速度, 消息)
        """
        url = self.config.get_endpoint_url("coarse_time_analyze")
        
        payload = {
            "target_weight": target_weight,
            "coarse_time_ms": coarse_time_ms,
            "current_coarse_speed": current_coarse_speed,
            "analysis_type": "coarse_time",
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
                    new_speed = result.get('new_coarse_speed')
                    message = result.get('message', '分析成功')
                    
                    return True, is_compliant, new_speed, message
                else:
                    return False, False, None, "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, False, None, error_msg
    
        # 处理 422 验证错误
        elif response.status_code == 422:
            try:
                error_data = response.json()
                self.logger.debug(f"422错误响应: {error_data}")
                
                # 提取具体的错误信息
                if 'error' in error_data:
                    error_message = self._format_error_message(error_data['error'])
                    return False, False, None, error_message
                else:
                    return False, False, None, "请求参数验证失败"
                    
            except json.JSONDecodeError:
                error_msg = "服务器返回422错误，但响应格式无法解析"
                self.logger.error(error_msg)
                return False, False, None, error_msg
    
        # 处理其他HTTP错误状态码
        else:
            try:
                # 尝试解析错误响应
                error_data = response.json()
                error_message = error_data.get('error', f"HTTP错误: {response.status_code}")
            except:
                error_message = f"后端API HTTP错误: {response.status_code}"
            
            self.logger.error(f"HTTP错误: {response.status_code}, 响应: {error_message}")
            return False, False, None, error_message
        
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
            "Request validation failed: "
        ]
        
        for prefix in prefixes_to_remove:
            if formatted_msg.startswith(prefix):
                formatted_msg = formatted_msg.replace(prefix, "")
                break
        
        return formatted_msg
    
    def test_api_connection(self) -> Tuple[bool, str]:
        """测试API连接状态"""
        try:
            url = self.config.get_endpoint_url("health")
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                return True, "快加时间分析API连接正常"
            else:
                return False, f"API返回错误状态码: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "无法连接到快加时间分析API服务器"
        except Exception as e:
            return False, f"API连接测试失败: {str(e)}"

# 创建全局API客户端实例
coarse_time_analysis_api = CoarseTimeAnalysisAPI()

def analyze_coarse_time(target_weight: float, coarse_time_ms: int, 
                       current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str]:
    """
    分析快加时间（便捷函数）
    
    Args:
        target_weight (float): 目标重量（克）
        coarse_time_ms (int): 快加时间（毫秒）
        current_coarse_speed (int): 当前快加速度
        
    Returns:
        Tuple[bool, bool, Optional[int], str]: (是否成功, 是否符合条件, 新的快加速度, 消息)
    """
    return coarse_time_analysis_api.analyze_coarse_time(target_weight, coarse_time_ms, current_coarse_speed)

def test_coarse_time_api_connection() -> Tuple[bool, str]:
    """
    测试快加时间分析API连接状态（便捷函数）
    
    Returns:
        Tuple[bool, str]: (连接状态, 消息)
    """
    return coarse_time_analysis_api.test_api_connection()