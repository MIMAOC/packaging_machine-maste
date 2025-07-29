#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应学习阶段WebAPI客户端
负责与后端API通信，分析自适应学习阶段的参数是否符合条件

作者：AI助手
创建日期：2025-07-24
"""

import requests
import json
import logging
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

# 导入API配置
try:
    from config.api_config import get_api_config
    API_CONFIG_AVAILABLE = True
except ImportError:
    API_CONFIG_AVAILABLE = False

# 配置日志
logger = logging.getLogger(__name__)

def analyze_adaptive_learning_parameters(
    target_weight: float,
    actual_total_cycle_ms: int,
    actual_coarse_time_ms: int,
    error_value: float,
    current_coarse_advance: float,
    current_fall_value: float,
    fine_flow_rate: float = None  # 新增参数
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
        if not API_CONFIG_AVAILABLE:
            error_msg = "API配置模块不可用"
            logger.error(error_msg)
            return False, False, None, error_msg
        
        # 获取API配置
        config = get_api_config()
        
        # 构建请求数据
        request_data = {
            "target_weight": target_weight,
            "actual_total_cycle_ms": actual_total_cycle_ms,
            "actual_coarse_time_ms": actual_coarse_time_ms,
            "error_value": error_value,
            "current_coarse_advance": current_coarse_advance,
            "current_fall_value": current_fall_value,
            "fine_flow_rate": fine_flow_rate,  # 新增：传递慢加流速
            "analysis_type": "adaptive_learning",
            "client_version": "1.5.1",
            "timestamp": datetime.now().isoformat()
        }
        
        # 获取API端点URL
        url = config.get_endpoint_url("adaptive_learning_analyze")
        
        logger.info(f"发送自适应学习参数分析请求到: {url}")
        logger.debug(f"请求数据: {request_data}")
        
        # 发送POST请求
        response = requests.post(
            url,
            json=request_data,
            timeout=config.timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MHWPM-Client/1.5.1"
            }
        )
        
        # 检查HTTP状态码
        if response.status_code != 200:
            error_msg = f"HTTP请求失败，状态码: {response.status_code}"
            logger.error(error_msg)
            return False, False, None, error_msg
        
        # 解析响应JSON
        response_data = response.json()
        
        # 验证响应格式
        if not isinstance(response_data, dict):
            error_msg = "API响应格式无效，不是字典类型"
            logger.error(error_msg)
            return False, False, None, error_msg
        
        # 检查响应中的成功标志
        if not response_data.get("success", False):
            error_msg = response_data.get("error", "API分析失败，未知错误")
            logger.error(f"API分析失败: {error_msg}")
            return False, False, None, error_msg
        
        # 提取分析结果
        is_compliant = response_data.get("is_compliant", False)
        adjustment_params = response_data.get("adjustment_parameters")
        message = response_data.get("message", "分析完成")
        
        logger.info(f"自适应学习参数分析成功: 符合条件={is_compliant}, 消息={message}")
        
        if adjustment_params:
            logger.debug(f"调整参数: {adjustment_params}")
        
        return True, is_compliant, adjustment_params, message
        
    except requests.exceptions.Timeout:
        error_msg = f"API请求超时（{config.timeout}秒）"
        logger.error(error_msg)
        return False, False, None, error_msg
        
    except requests.exceptions.ConnectionError:
        error_msg = "无法连接到后端API服务器"
        logger.error(error_msg)
        return False, False, None, error_msg
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API请求异常: {str(e)}"
        logger.error(error_msg)
        return False, False, None, error_msg
        
    except json.JSONDecodeError as e:
        error_msg = f"API响应JSON解析失败: {str(e)}"
        logger.error(error_msg)
        return False, False, None, error_msg
        
    except Exception as e:
        error_msg = f"自适应学习参数分析异常: {str(e)}"
        logger.error(error_msg)
        return False, False, None, error_msg

def test_adaptive_learning_api() -> Tuple[bool, str]:
    """
    测试自适应学习API连接
    
    Returns:
        Tuple[bool, str]: (测试是否成功, 测试消息)
    """
    try:
        if not API_CONFIG_AVAILABLE:
            return False, "API配置模块不可用"
        
        config = get_api_config()
        
        # 测试数据
        test_data = {
            "target_weight": 200.0,
            "actual_total_cycle_ms": 9500,
            "actual_coarse_time_ms": 3800,
            "error_value": 0.3,
            "current_coarse_advance": 15.0,
            "current_fall_value": 0.4,
            "fine_flow_rate": 0.37,  # 新增：传递慢加流速
            "analysis_type": "adaptive_learning_test",
            "client_version": "1.5.1",
            "timestamp": datetime.now().isoformat()
        }
        
        url = config.get_endpoint_url("adaptive_learning_analyze")
        
        response = requests.post(
            url,
            json=test_data,
            timeout=config.timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MHWPM-Client/1.5.1"
            }
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("success", False):
                return True, "自适应学习API连接测试成功"
            else:
                return False, f"API返回错误: {response_data.get('error', '未知错误')}"
        else:
            return False, f"HTTP状态码错误: {response.status_code}"
            
    except Exception as e:
        return False, f"自适应学习API测试异常: {str(e)}"

# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 测试API连接
    success, message = test_adaptive_learning_api()
    print(f"API连接测试: {success} - {message}")
    
    if success:
        # 测试参数分析
        success, is_compliant, params, msg = analyze_adaptive_learning_parameters(
            target_weight=200.0,
            actual_total_cycle_ms=9500,
            actual_coarse_time_ms=3800,
            error_value=0.3,
            current_coarse_advance=15.0,
            current_fall_value=0.4,
            fine_flow_rate=0.37,  # 新增：传递慢加流速
        )
        
        print(f"参数分析结果: {success} - {msg}")
        if success:
            print(f"符合条件: {is_compliant}")
            if params:
                print(f"调整参数: {params}")