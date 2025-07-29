#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebAPI客户端模块 - 前端版本
用于调用后端API分析快加速度等参数

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

class WeightAnalysisAPI:
    """
    重量分析API客户端类 - 前端版本
    连接到后端FastAPI服务进行重量分析
    """
    
    def __init__(self):
        """初始化API客户端"""
        self.config = get_api_config()
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def analyze_coarse_speed(self, target_weight: float) -> Tuple[bool, int, str]:
        """
        分析目标重量对应的快加速度
        
        Args:
            target_weight (float): 目标重量（克）
            
        Returns:
            Tuple[bool, int, str]: (是否成功, 快加速度, 消息)
        """
        # 输入验证
        if target_weight <= 0:
            return False, 0, "目标重量必须大于0"
        
        try:
            self.logger.info(f"调用后端API分析目标重量: {target_weight}g")
            
            # 调用后端API
            success, coarse_speed, message = self._call_backend_weight_api(target_weight)
            
            if success:
                self.logger.info(f"后端API成功分析目标重量 {target_weight}g，快加速度: {coarse_speed}")
                return True, coarse_speed, message
            else:
                error_msg = f"后端API分析失败: {message}"
                self.logger.error(error_msg)
                return False, 0, error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到后端API服务器 ({self.config.base_url})。请检查："
            error_msg += "\n1. 后端服务是否启动"
            error_msg += "\n2. 网络连接是否正常"
            error_msg += "\n3. API地址配置是否正确"
            self.logger.error(error_msg)
            return False, 0, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = f"后端API请求超时（超过{self.config.timeout}秒）"
            self.logger.error(error_msg)
            return False, 0, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"后端API请求异常: {str(e)}"
            self.logger.error(error_msg)
            return False, 0, error_msg
            
        except Exception as e:
            error_msg = f"WebAPI客户端未知异常: {str(e)}"
            self.logger.error(error_msg)
            return False, 0, error_msg
    
    def _call_backend_weight_api(self, target_weight: float) -> Tuple[bool, int, str]:
        """
        调用后端重量分析API
        
        Args:
            target_weight (float): 目标重量
            
        Returns:
            Tuple[bool, int, str]: (是否成功, 快加速度, 消息)
        """
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
        
        self.logger.info(f"发送后端API请求: {url}")
        self.logger.debug(f"请求数据: {payload}")
        
        # 发送POST请求
        response = requests.post(
            url=url,
            json=payload,
            headers=headers,
            timeout=self.config.timeout
        )
        
        # 检查HTTP状态码
        if response.status_code == 200:
            try:
                result = response.json()
                
                if result.get('success', False):
                    coarse_speed = result.get('coarse_speed', 0)
                    message = result.get('message', '分析成功')
                    
                    # 验证返回的速度值是否合理
                    if 60 <= coarse_speed <= 90:
                        self.logger.info(f"后端API返回有效速度值: {coarse_speed}")
                        return True, coarse_speed, message
                    else:
                        error_msg = f"后端API返回的速度值不合理: {coarse_speed}（期望范围: 60-90）"
                        self.logger.error(error_msg)
                        return False, 0, error_msg
                else:
                    error_msg = "后端API返回失败状态"
                    self.logger.error(f"后端API错误: {result}")
                    return False, 0, error_msg
                    
            except json.JSONDecodeError as e:
                error_msg = f"后端API响应JSON解析失败: {str(e)}"
                self.logger.error(error_msg)
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
            self.logger.error(error_msg)
            return False, 0, error_msg
    
    def test_api_connection(self) -> Tuple[bool, str]:
        """
        测试后端API连接状态
        
        Returns:
            Tuple[bool, str]: (连接状态, 消息)
        """
        try:
            url = self.config.get_endpoint_url("health")
            self.logger.info(f"测试后端API连接: {url}")
            
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
        """
        获取API客户端信息
        
        Returns:
            Dict[str, Any]: 包含API配置信息的字典
        """
        config_dict = self.config.get_config_dict()
        config_dict.update({
            'client_type': 'frontend',
            'backend_dependent': True,
            'version': '1.5.1'
        })
        return config_dict
    
    def get_weight_rules(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        从后端获取重量分析规则
        
        Returns:
            Tuple[bool, Dict[str, Any], str]: (是否成功, 规则信息, 消息)
        """
        try:
            url = self.config.get_endpoint_url("weight_rules")
            self.logger.info(f"获取后端重量规则: {url}")
            
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
            self.logger.error(error_msg)
            return False, {}, error_msg

# 创建全局API客户端实例
weight_analysis_api = WeightAnalysisAPI()

def analyze_target_weight(target_weight: float) -> Tuple[bool, int, str]:
    """
    分析目标重量的快加速度（便捷函数）
    
    Args:
        target_weight (float): 目标重量（克）
        
    Returns:
        Tuple[bool, int, str]: (是否成功, 快加速度, 消息)
    """
    return weight_analysis_api.analyze_coarse_speed(target_weight)

def test_webapi_connection() -> Tuple[bool, str]:
    """
    测试后端API连接状态（便捷函数）
    
    Returns:
        Tuple[bool, str]: (连接状态, 消息)
    """
    return weight_analysis_api.test_api_connection()

def get_webapi_info() -> Dict[str, Any]:
    """
    获取WebAPI客户端信息（便捷函数）
    
    Returns:
        Dict[str, Any]: API配置信息
    """
    return weight_analysis_api.get_api_info()

# 示例使用和测试
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 前端WebAPI客户端测试")
    print("=" * 60)
    
    # 显示配置信息
    print("1. API配置信息:")
    api_info = get_webapi_info()
    for key, value in api_info.items():
        if key == "endpoints":
            print(f"   {key}:")
            for endpoint, path in value.items():
                print(f"     {endpoint}: {api_info['base_url']}{path}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # 测试连接
    print("2. 测试后端API连接...")
    conn_success, conn_msg = test_webapi_connection()
    print(f"   连接状态: {'✅ 成功' if conn_success else '❌ 失败'}")
    print(f"   消息: {conn_msg}")
    print()
    
    if conn_success:
        # 测试重量分析
        test_weights = [150, 200, 250, 300, 350, 390]
        
        print("3. 测试重量分析...")
        for weight in test_weights:
            success, speed, message = analyze_target_weight(weight)
            status = "✅ 成功" if success else "❌ 失败"
            print(f"   重量 {weight:3}g: {status} - 速度 {speed:2} - {message[:50]}...")
        print()
        
        # 测试获取规则
        print("4. 测试获取重量规则...")
        rules_success, rules_data, rules_msg = weight_analysis_api.get_weight_rules()
        if rules_success:
            print(f"   ✅ 成功获取规则: {rules_msg}")
            rules_info = rules_data.get('rules', [])
            if isinstance(rules_info, list):
                print(f"   共 {len(rules_info)} 条规则")
        else:
            print(f"   ❌ 获取规则失败: {rules_msg}")
    
    print()
    print("=" * 60)
    print("⚠️  注意：此前端客户端依赖后端API服务")
    print("   请确保后端服务正在运行在配置的地址上")
    print("=" * 60)