"""
自适应学习阶段WebAPI客户端

作者：C
创建日期：2025-07-24
更新日期：2025-08-19
"""

import requests
import json
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class AdaptiveLearningAnalysisAPI:
    def __init__(self):
        self.config = get_api_config()
    
    def _format_error_message(self, error_message: str) -> str:
        formatted_msg = error_message
        
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
        try:
            if target_weight <= 0:
                error_msg = self._format_error_message("目标重量必须大于0")
                return False, False, None, error_msg
            
            if actual_total_cycle_ms <= 0:
                error_msg = self._format_error_message("实际总周期必须大于0毫秒")
                return False, False, None, error_msg
            
            if actual_coarse_time_ms <= 0:
                error_msg = self._format_error_message("实际快加时间必须大于0毫秒")
                return False, False, None, error_msg
            
            success, is_compliant, adjustment_params, message = self._call_backend_adaptive_learning_api(
                target_weight, actual_total_cycle_ms, actual_coarse_time_ms, 
                error_value, current_coarse_advance, current_fall_value, fine_flow_rate)
            
            if success:
                return True, is_compliant, adjustment_params, message
            else:
                return False, False, None, message
                
        except requests.exceptions.ConnectionError:
            error_msg = self._format_error_message(f"无法连接到后端API服务器 ({self.config.base_url})")
            return False, False, None, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = self._format_error_message(f"后端API请求超时（超过{self.config.timeout}秒）")
            return False, False, None, error_msg
            
        except Exception as e:
            error_msg = self._format_error_message(f"自适应学习参数分析异常: {str(e)}")
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
                    adjustment_params = result.get('adjustment_parameters')
                    message = result.get('message', '分析成功')
                    
                    return True, is_compliant, adjustment_params, message
                else:
                    return False, False, None, "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, False, None, error_msg

        elif response.status_code == 422:
            try:
                error_data = response.json()
                
                if 'error' in error_data:
                    raw_error_message = error_data['error']
                    
                    formatted_error_message = self._format_error_message(raw_error_message)
                    
                    return False, False, None, formatted_error_message
                else:
                    formatted_error = self._format_error_message("请求参数验证失败")
                    return False, False, None, formatted_error
                    
            except json.JSONDecodeError:
                error_msg = self._format_error_message("服务器返回422错误，但响应格式无法解析")
                return False, False, None, error_msg

        else:
            try:
                error_data = response.json()
                raw_error_message = error_data.get('error', f"HTTP错误: {response.status_code}")
            except:
                raw_error_message = f"后端API HTTP错误: {response.status_code}"
            
            formatted_error_message = self._format_error_message(raw_error_message)
            
            return False, False, None, formatted_error_message

    def test_api_connection(self) -> Tuple[bool, str]:
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
    return adaptive_learning_analysis_api.analyze_adaptive_learning_parameters(
        target_weight, actual_total_cycle_ms, actual_coarse_time_ms, 
        error_value, current_coarse_advance, current_fall_value, fine_flow_rate)

def test_adaptive_learning_api_connection() -> Tuple[bool, str]:
    return adaptive_learning_analysis_api.test_api_connection()