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
        else:
            error_msg = f"后端API HTTP错误: {response.status_code}"
            return False, 0.0, [], error_msg
    
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

def analyze_flight_material(target_weight: float, 
                          recorded_weights: List[float]) -> Tuple[bool, float, List[float], str]:
    """
    分析飞料值（便捷函数）
    
    Args:
        target_weight (float): 目标重量（克）
        recorded_weights (List[float]): 3次记录的实时重量（克）
        
    Returns:
        Tuple[bool, float, List[float], str]: (是否成功, 平均飞料值, 3次飞料值详情, 消息)
    """
    return flight_material_analysis_api.analyze_flight_material(target_weight, recorded_weights)

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