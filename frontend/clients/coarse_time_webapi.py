"""
快加时间WebAPI分析模块

作者：C
创建日期：2025-07-23
更新日期：2025-08-19
"""

import requests
import json
from typing import Tuple, Optional, Dict, Any
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class CoarseTimeAnalysisAPI:
    def __init__(self):
        self.config = get_api_config()
    
    def analyze_coarse_time(self, target_weight: float, coarse_time_ms: int, 
                          current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str]:
        try:
            success, is_compliant, new_speed, message = self._call_backend_coarse_time_api(
                target_weight, coarse_time_ms, current_coarse_speed)
            
            if success:
                return True, is_compliant, new_speed, message
            else:
                error_msg = f"后端API分析失败: {message}"
                return False, False, None, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})"
            return False, False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            return False, False, None, error_msg
            
        except Exception as e:
            error_msg = f"快加时间分析异常: {str(e)}"
            return False, False, None, error_msg
    
    def _call_backend_coarse_time_api(self, target_weight: float, coarse_time_ms: int, 
                                    current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str]:
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
        
        response = requests.post(
            url=url,
            json=payload,
            headers=headers,
            timeout=self.config.timeout
        )
        
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
    
        elif response.status_code == 422:
            try:
                error_data = response.json()
                
                if 'error' in error_data:
                    error_message = self._format_error_message(error_data['error'])
                    return False, False, None, error_message
                else:
                    return False, False, None, "请求参数验证失败"
                    
            except json.JSONDecodeError:
                error_msg = "服务器返回422错误，但响应格式无法解析"
                return False, False, None, error_msg
    
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('error', f"HTTP错误: {response.status_code}")
            except:
                error_message = f"后端API HTTP错误: {response.status_code}"
            
            return False, False, None, error_message
        
    def _format_error_message(self, error_message: str) -> str:
        formatted_msg = error_message
        
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

coarse_time_analysis_api = CoarseTimeAnalysisAPI()

def analyze_coarse_time(target_weight: float, coarse_time_ms: int, 
                       current_coarse_speed: int) -> Tuple[bool, bool, Optional[int], str]:
    return coarse_time_analysis_api.analyze_coarse_time(target_weight, coarse_time_ms, current_coarse_speed)

def test_coarse_time_api_connection() -> Tuple[bool, str]:
    return coarse_time_analysis_api.test_api_connection()