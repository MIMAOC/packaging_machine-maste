# clients/flight_material_webapi.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞料值WebAPI分析模块 - 前端版本
用于分析3次实时重量并计算平均飞料值

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-23（修改为连接后端API服务）
"""

import requests
import json
import logging
from typing import Tuple, List, Dict, Any
import sys
import os

# 添加config模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.api_config import get_api_config

class FlightMaterialAnalysisAPI:
    """
    飞料值分析API客户端类 - 前端版本
    连接到后端FastAPI服务进行飞料值分析
    """
    
    def __init__(self):
        """初始化API客户端"""
        self.config = get_api_config()
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def analyze_flight_material(self, target_weight: float, 
                              recorded_weights: List[float]) -> Tuple[bool, float, List[float], str]:
        """
        分析飞料值
        
        Args:
            target_weight (float): 目标重量（克）
            recorded_weights (List[float]): 3次记录的实时重量（克）
            
        Returns:
            Tuple[bool, float, List[float], str]: (是否成功, 平均飞料值, 3次飞料值详情, 消息)
        """
        try:
            self.logger.info(f"分析飞料值: 目标重量={target_weight}g, 实时重量={recorded_weights}")
            
            # 输入验证
            if len(recorded_weights) != 3:
                return False, 0.0, [], f"需要3次实时重量数据，实际提供了{len(recorded_weights)}次"
            
            # 调用后端API
            success, avg_flight_material, flight_details, message = self._call_backend_flight_material_api(
                target_weight, recorded_weights)
            
            if success:
                self.logger.info(f"后端API分析成功，平均飞料值: {avg_flight_material}g")
                return True, avg_flight_material, flight_details, message
            else:
                error_msg = f"后端API分析失败: {message}"
                self.logger.error(error_msg)
                return False, 0.0, [], error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})"
            self.logger.error(error_msg)
            return False, 0.0, [], error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            self.logger.error(error_msg)
            return False, 0.0, [], error_msg
            
        except Exception as e:
            error_msg = f"飞料值分析异常: {str(e)}"
            self.logger.error(error_msg)
            return False, 0.0, [], error_msg
        
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
        
        # 处理技术术语替换，让用户更容易理解
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
        """
        调用后端飞料值分析API
        
        Args:
            target_weight (float): 目标重量
            recorded_weights (List[float]): 3次实时重量
            
        Returns:
            Tuple[bool, float, List[float], str]: (是否成功, 平均飞料值, 3次飞料值详情, 消息)
        """
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
                    avg_flight_material = result.get('average_flight_material', 0.0)
                    flight_details = result.get('flight_material_details', [])
                    message = result.get('message', '分析成功')
                    
                    self.logger.info(f"后端API返回飞料值: 平均={avg_flight_material}g, 详情={flight_details}")
                    return True, avg_flight_material, flight_details, message
                else:
                    return False, 0.0, [], "后端API返回失败状态"
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                return False, 0.0, [], error_msg

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
                    self.logger.warning(f"飞料值参数验证失败 - 字段: {field}, 原始错误: {raw_error_message}, 格式化错误: {formatted_error_message}")
                    
                    return False, 0.0, [], formatted_error_message
                else:
                    formatted_error = self._format_error_message("请求参数验证失败")
                    return False, 0.0, [], formatted_error
                    
            except json.JSONDecodeError:
                error_msg = self._format_error_message("服务器返回422错误，但响应格式无法解析")
                self.logger.error(error_msg)
                return False, 0.0, [], error_msg
        
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
            return False, 0.0, [], formatted_error_message
    
    def test_api_connection(self) -> Tuple[bool, str]:
        """测试API连接状态"""
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

# 创建全局API客户端实例
flight_material_analysis_api = FlightMaterialAnalysisAPI()

def analyze_flight_material(self, target_weight: float, 
                          recorded_weights: List[float]) -> Tuple[bool, float, List[float], str]:
    """
    分析飞料值
    
    Args:
        target_weight (float): 目标重量（克）
        recorded_weights (List[float]): 3次记录的实时重量（克）
        
    Returns:
        Tuple[bool, float, List[float], str]: (是否成功, 平均飞料值, 3次飞料值详情, 消息)
    """
    try:
        self.logger.info(f"分析飞料值: 目标重量={target_weight}g, 实时重量={recorded_weights}")
        
        # 输入验证
        if len(recorded_weights) != 3:
            error_msg = self._format_error_message(f"需要3次实时重量数据，实际提供了{len(recorded_weights)}次")
            return False, 0.0, [], error_msg
        
        # 调用后端API
        success, avg_flight_material, flight_details, message = self._call_backend_flight_material_api(
            target_weight, recorded_weights)
        
        if success:
            self.logger.info(f"后端API分析成功，平均飞料值: {avg_flight_material}g")
            return True, avg_flight_material, flight_details, message
        else:
            # message 已经在 _call_backend_flight_material_api 中格式化过了
            self.logger.error(f"后端API分析失败: {message}")
            return False, 0.0, [], message
            
    except requests.exceptions.ConnectionError:
        error_msg = self._format_error_message(f"无法连接到后端API服务器 ({self.config.base_url})")
        self.logger.error(error_msg)
        return False, 0.0, [], error_msg
        
    except requests.exceptions.Timeout:
        error_msg = self._format_error_message(f"后端API请求超时（超过{self.config.timeout}秒）")
        self.logger.error(error_msg)
        return False, 0.0, [], error_msg
        
    except Exception as e:
        error_msg = self._format_error_message(f"飞料值分析异常: {str(e)}")
        self.logger.error(error_msg)
        return False, 0.0, [], error_msg

def test_flight_material_api_connection() -> Tuple[bool, str]:
    """
    测试飞料值分析API连接状态（便捷函数）
    
    Returns:
        Tuple[bool, str]: (连接状态, 消息)
    """
    return flight_material_analysis_api.test_api_connection()

# 示例使用和测试
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 前端飞料值分析API客户端测试")
    print("=" * 60)
    
    # 测试连接
    print("1. 测试后端API连接...")
    conn_success, conn_msg = test_flight_material_api_connection()
    print(f"   连接状态: {'✅ 成功' if conn_success else '❌ 失败'}")
    print(f"   消息: {conn_msg}")
    print()
    
    if conn_success:
        # 测试不同场景
        test_cases = [
            # (目标重量, 3次实时重量, 预期结果)
            (200.0, [201.5, 202.0, 199.8], "正常情况"),
            (150.0, [151.2, 150.8, 151.5], "小重量"),
            (300.0, [305.0, 298.5, 302.2], "大重量"),
            (250.0, [248.0, 247.5, 249.0], "负飞料值"),
        ]
        
        print("2. 测试飞料值分析...")
        for target_weight, recorded_weights, description in test_cases:
            print(f"\n   测试案例: {description}")
            print(f"   目标重量: {target_weight}g")
            print(f"   实时重量: {recorded_weights}")
            
            success, avg_flight_material, flight_details, message = analyze_flight_material(
                target_weight, recorded_weights)
            
            status = "✅ 成功" if success else "❌ 失败"
            print(f"   结果: {status}")
            
            if success:
                print(f"   平均飞料值: {avg_flight_material:.1f}g")
                print(f"   飞料值详情: {[f'{f:.1f}g' for f in flight_details]}")
            else:
                print(f"   错误: {message}")
    
    print("\n" + "=" * 60)
    print("⚠️  注意：此前端客户端依赖后端API服务")
    print("   请确保后端服务正在运行在配置的地址上")
    print("=" * 60)