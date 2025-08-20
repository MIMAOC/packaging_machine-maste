"""
WebAPI客户端模块

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

class WeightAnalysisAPI:
    def __init__(self):
        self.config = get_api_config()
    
    def analyze_coarse_speed(self, target_weight: float) -> Tuple[bool, int, str]:
        if target_weight <= 0:
            return False, 0, "目标重量必须大于0"
        
        try:
            success, coarse_speed, message = self._call_backend_weight_api(target_weight)
            
            if success:
                return True, coarse_speed, message
            else:
                error_msg = f"后端API分析失败: {message}"
                return False, 0, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})。请检查："
            error_msg += "\n1. 后端服务是否启动"
            error_msg += "\n2. 网络连接是否正常"
            error_msg += "\n3. API地址配置是否正确"
            return False, 0, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            return False, 0, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"后端API请求异常: {str(e)}"
            return False, 0, error_msg
            
        except Exception as e:
            error_msg = f"WebAPI客户端未知异常: {str(e)}"
            return False, 0, error_msg
    
    def _call_backend_weight_api(self, target_weight: float) -> Tuple[bool, int, str]:
        url = self.config.get_endpoint_url("weight_analyze")
        
        payload = {
            "target_weight": target_weight,
            "analysis_type": "coarse_speed",
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
                    coarse_speed = result.get('coarse_speed', 0)
                    message = result.get('message', '分析成功')
                    
                    if 0 <= coarse_speed <= 100:
                        return True, coarse_speed, message
                    else:
                        error_msg = f"后端API返回的速度值不合理: {coarse_speed}"
                        return False, 0, error_msg
                else:
                    error_msg = "后端API返回失败状态"
                    return False, 0, error_msg
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, 0, error_msg
                
        elif response.status_code == 400:
            try:
                result = response.json()
                error_msg = result.get('detail', '请求参数错误')
                return False, 0, f"请求参数错误: {error_msg}"
            except:
                return False, 0, f"请求参数错误 (HTTP 400)"
                
        elif response.status_code == 404:
            return False, 0, "后端API端点不存在，请检查API地址配置"
            
        elif response.status_code == 500:
            return False, 0, "后端API服务器内部错误，请联系管理员"
            
        else:
            error_msg = f"后端API HTTP错误: {response.status_code}"
            return False, 0, error_msg
    
    def test_api_connection(self) -> Tuple[bool, str]:
        try:
            url = self.config.get_endpoint_url("health")
            
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    service_name = result.get('service', 'Unknown Service')
                    version = result.get('version', 'Unknown Version')
                    return True, f"后端API连接正常 - {service_name} v{version}"
                except:
                    return True, "后端API连接正常"
            else:
                return False, f"后端API健康检查失败，HTTP状态码: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, f"无法连接到后端API服务器 ({self.config.base_url})"
        except requests.exceptions.Timeout:
            return False, f"后端API连接超时（超过{self.config.timeout}秒）"
        except Exception as e:
            return False, f"后端API连接测试失败: {str(e)}"
    
    def get_api_info(self) -> Dict[str, Any]:
        config_dict = self.config.get_config_dict()
        config_dict.update({
            'client_type': 'frontend',
            'backend_dependent': True,
            'version': '1.5.1'
        })
        return config_dict
    
    def get_weight_rules(self) -> Tuple[bool, Dict[str, Any], str]:
        try:
            url = self.config.get_endpoint_url("weight_rules")
            
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    return True, result.get('rules', {}), result.get('message', '获取成功')
                else:
                    return False, {}, result.get('message', '获取失败')
            else:
                return False, {}, f"HTTP错误: {response.status_code}"
                
        except Exception as e:
            error_msg = f"获取重量规则异常: {str(e)}"
            return False, {}, error_msg

weight_analysis_api = WeightAnalysisAPI()

def analyze_target_weight(target_weight: float) -> Tuple[bool, int, str]:
    return weight_analysis_api.analyze_coarse_speed(target_weight)

def test_webapi_connection() -> Tuple[bool, str]:
    return weight_analysis_api.test_api_connection()

def get_webapi_info() -> Dict[str, Any]:
    return weight_analysis_api.get_api_info()