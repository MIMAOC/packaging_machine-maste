"""
慢加时间WebAPI分析模块

作者：C
创建日期：2025-07-24
更新日期：2025-08-19
"""

import requests
import json
from typing import Tuple, Optional, Dict, Any
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class FineTimeAnalysisAPI:
    
    def __init__(self):
        self.config = get_api_config()
        
    def _format_error_message(self, error_message: str) -> str:
        formatted_msg = error_message
        
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
        try:
            if fine_time_ms <= 0:
                error_msg = self._format_error_message("慢加时间必须大于0毫秒")
                return False, False, None, None, None, error_msg
            
            if current_fine_speed <= 0:
                error_msg = self._format_error_message("当前慢加速度必须大于0")
                return False, False, None, None, None, error_msg
            
            if target_weight <= 0:
                error_msg = self._format_error_message("目标重量必须大于0")
                return False, False, None, None, None, error_msg
            
            success, is_compliant, new_speed, coarse_advance, fine_flow_rate, message = self._call_backend_fine_time_api(
                target_weight, fine_time_ms, current_fine_speed, original_target_weight, flight_material_value)
            
            if success:
                return True, is_compliant, new_speed, coarse_advance, fine_flow_rate, message
            else:
                return False, False, None, None, None, message
                
        except requests.exceptions.ConnectionError:
            error_msg = self._format_error_message(f"无法连接到后端API服务器 ({self.config.base_url})")
            return False, False, None, None, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = self._format_error_message(f"后端API请求超时（超过{self.config.timeout}秒）")
            return False, False, None, None, None, error_msg
            
        except Exception as e:
            error_msg = self._format_error_message(f"慢加时间分析异常: {str(e)}")
            return False, False, None, None, None, error_msg
    
    def _call_backend_fine_time_api(self, target_weight: float, fine_time_ms: int, 
                                   current_fine_speed: int, original_target_weight: float,
                                   flight_material_value: float) -> Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]:
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
                    new_speed = result.get('new_fine_speed')
                    coarse_advance = result.get('coarse_advance')
                    fine_flow_rate = result.get('fine_flow_rate')
                    message = result.get('message', '分析成功')
                    
                    return True, is_compliant, new_speed, coarse_advance, fine_flow_rate, message
                else:
                    return False, False, None, None, None, "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, False, None, None, None, error_msg

        elif response.status_code == 422:
            try:
                error_data = response.json()
                
                if 'error' in error_data:
                    raw_error_message = error_data['error']
                    
                    formatted_error_message = self._format_error_message(raw_error_message)
                    
                    return False, False, None, None, None, formatted_error_message
                else:
                    formatted_error = self._format_error_message("请求参数验证失败")
                    return False, False, None, None, None, formatted_error
                    
            except json.JSONDecodeError:
                error_msg = self._format_error_message("服务器返回422错误，但响应格式无法解析")
                return False, False, None, None, None, error_msg

        else:
            try:
                error_data = response.json()
                raw_error_message = error_data.get('error', f"HTTP错误: {response.status_code}")
            except:
                raw_error_message = f"后端API HTTP错误: {response.status_code}"
            
            formatted_error_message = self._format_error_message(raw_error_message)
            
            return False, False, None, None, None, formatted_error_message
    
    def test_api_connection(self) -> Tuple[bool, str]:
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

fine_time_analysis_api = FineTimeAnalysisAPI()

def analyze_fine_time(target_weight: float, fine_time_ms: int, 
                     current_fine_speed: int, original_target_weight: float = 0.0,
                     flight_material_value: float = 0.0) -> Tuple[bool, bool, Optional[int], Optional[float], Optional[float], str]:
    return fine_time_analysis_api.analyze_fine_time(
        target_weight, fine_time_ms, current_fine_speed, 
        original_target_weight, flight_material_value
    )

def test_fine_time_api_connection() -> Tuple[bool, str]:
    return fine_time_analysis_api.test_api_connection()