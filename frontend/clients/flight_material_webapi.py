"""
飞料值WebAPI分析模块

作者：C
创建日期：2025-07-23
更新日期：2025-08-19
"""

import requests
import json
from typing import Tuple, List, Dict, Any
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class FlightMaterialAnalysisAPI:
    def __init__(self):
        self.config = get_api_config()
    
    def analyze_flight_material(self, target_weight: float, 
                              recorded_weights: List[float]) -> Tuple[bool, float, List[float], str]:
        try:
            if len(recorded_weights) != 3:
                return False, 0.0, [], f"需要3次实时重量数据，实际提供了{len(recorded_weights)}次"
            
            success, avg_flight_material, flight_details, message = self._call_backend_flight_material_api(
                target_weight, recorded_weights)
            
            if success:
                return True, avg_flight_material, flight_details, message
            else:
                error_msg = f"后端API分析失败: {message}"
                return False, 0.0, [], error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})"
            return False, 0.0, [], error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            return False, 0.0, [], error_msg
            
        except Exception as e:
            error_msg = f"飞料值分析异常: {str(e)}"
            return False, 0.0, [], error_msg
        
    def _format_error_message(self, error_message: str) -> str:
        formatted_msg = error_message
        
        prefixes_to_remove = [
            "Value error, ",
            "Validation error, ",
            "Request validation failed: ",
            "飞料值分析失败: ",
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
            "recorded_weights": "实时重量数据",
            "target_weight": "目标重量",
            "flight_material": "飞料值",
            "flight_material_value": "飞料值",
            "average_flight_material": "平均飞料值",
            "flight_material_details": "飞料值详情",
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
    
    def _call_backend_flight_material_api(self, target_weight: float, 
                                        recorded_weights: List[float]) -> Tuple[bool, float, List[float], str]:
        url = self.config.get_endpoint_url("flight_material_analyze")
        
        payload = {
            "target_weight": target_weight,
            "recorded_weights": recorded_weights,
            "analysis_type": "flight_material",
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
                    avg_flight_material = result.get('average_flight_material', 0.0)
                    flight_details = result.get('flight_material_details', [])
                    message = result.get('message', '分析成功')
                    
                    return True, avg_flight_material, flight_details, message
                else:
                    return False, 0.0, [], "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, 0.0, [], error_msg

        elif response.status_code == 422:
            try:
                error_data = response.json()
                
                if 'error' in error_data:
                    raw_error_message = error_data['error']
                    
                    formatted_error_message = self._format_error_message(raw_error_message)
                    
                    return False, 0.0, [], formatted_error_message
                else:
                    formatted_error = self._format_error_message("请求参数验证失败")
                    return False, 0.0, [], formatted_error
                    
            except json.JSONDecodeError:
                error_msg = self._format_error_message("服务器返回422错误，但响应格式无法解析")
                return False, 0.0, [], error_msg
        
        else:
            try:
                error_data = response.json()
                raw_error_message = error_data.get('error', f"HTTP错误: {response.status_code}")
            except:
                raw_error_message = f"后端API HTTP错误: {response.status_code}"
            
            formatted_error_message = self._format_error_message(raw_error_message)
            
            return False, 0.0, [], formatted_error_message
    
    def test_api_connection(self) -> Tuple[bool, str]:
        try:
            url = self.config.get_endpoint_url("health")
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                return True, "飞料值分析API连接正常"
            else:
                return False, f"API返回错误状态码: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "无法连接到飞料值分析API服务器"
        except Exception as e:
            return False, f"API连接测试失败: {str(e)}"

flight_material_analysis_api = FlightMaterialAnalysisAPI()

def analyze_flight_material(target_weight: float, 
                          recorded_weights: List[float]) -> Tuple[bool, float, List[float], str]:
    return flight_material_analysis_api.analyze_flight_material(target_weight, recorded_weights)

def test_flight_material_api_connection() -> Tuple[bool, str]:
    return flight_material_analysis_api.test_api_connection()