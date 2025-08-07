#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应学习阶段分析模块 - 后端版本
实现自适应学习阶段的边界条件检查和参数调整逻辑

作者：AI助手
创建日期：2025-07-24
修改日期：2025-07-24 - 调用coarse_time_analysis模块避免重复代码
"""

import logging
from typing import Dict, Any, Optional, Tuple
from models.request_models import AdaptiveLearningAnalysisRequest
from models.response_models import (
    AdaptiveLearningAnalysisResponse,
    AdaptiveLearningErrorResponse
)

# 导入快加时间分析模块
from analysis.coarse_time_analysis import (
    calculate_total_cycle_time,
    calculate_coarse_time_ratio
)

# 配置日志
logger = logging.getLogger(__name__)

def analyze_adaptive_learning_parameters(request: AdaptiveLearningAnalysisRequest) -> AdaptiveLearningAnalysisResponse:
    """
    分析自适应学习阶段参数
    
    Args:
        request (AdaptiveLearningAnalysisRequest): 分析请求
        
    Returns:
        AdaptiveLearningAnalysisResponse: 分析结果
    """
    try:
        logger.info(f"开始分析自适应学习参数: 目标重量={request.target_weight}g")
        
        # 调用快加时间分析模块中的函数计算标准值
        standard_total_cycle_ms = calculate_total_cycle_time(request.target_weight)
        coarse_time_ratio = calculate_coarse_time_ratio(request.target_weight)
        
        # 计算实际慢加时间
        actual_fine_time_ms = request.actual_total_cycle_ms - request.actual_coarse_time_ms
        
        # 获取慢加速度测定成功的慢加流速值（不再计算，直接使用传入的值）
        fine_flow_rate = getattr(request, 'fine_flow_rate', None)
        if fine_flow_rate is None:
            # 如果请求中没有慢加流速，报错
            if actual_fine_time_ms > 0:
                logger.warning(f"请求中未提供慢加流速")
        
        logger.debug(f"标准总周期: {standard_total_cycle_ms}ms, 快加占比: {coarse_time_ratio}")
        logger.debug(f"实际慢加时间: {actual_fine_time_ms}ms, 慢加流速: {fine_flow_rate}g/s (来自慢加测定结果)")
        
        # 边界条件检查
        error_check = check_error_value_boundary(request.error_value)
        cycle_check = check_cycle_time_boundary(request.actual_total_cycle_ms, standard_total_cycle_ms)
        fine_time_check = check_fine_time_boundary(actual_fine_time_ms)
        fall_value_check = check_fall_value_boundary(request.current_fall_value)
        
        # 判断是否符合所有条件
        is_compliant = (error_check["compliant"] and 
                       cycle_check["compliant"] and 
                       fine_time_check["compliant"] and 
                       fall_value_check["compliant"])
        
        # 如果不符合条件，计算调整参数
        adjustment_parameters = None
        if not is_compliant:
            adjustment_parameters = calculate_adjustment_parameters(
                request, actual_fine_time_ms, standard_total_cycle_ms, 
                fine_flow_rate, error_check, cycle_check, fine_time_check, fall_value_check
            )
        
        # 生成分析消息
        message = generate_analysis_message(is_compliant, error_check, cycle_check, 
                                          fine_time_check, fall_value_check, adjustment_parameters)
        
        # 构建响应
        response = AdaptiveLearningAnalysisResponse(
            success=True,
            target_weight=request.target_weight,
            actual_total_cycle_ms=request.actual_total_cycle_ms,
            actual_coarse_time_ms=request.actual_coarse_time_ms,
            actual_fine_time_ms=actual_fine_time_ms,
            error_value=request.error_value,
            is_compliant=is_compliant,
            standard_total_cycle_ms=standard_total_cycle_ms,
            coarse_time_ratio=coarse_time_ratio,
            fine_flow_rate=fine_flow_rate,
            error_check=error_check,
            cycle_check=cycle_check,
            fine_time_check=fine_time_check,
            fall_value_check=fall_value_check,
            adjustment_parameters=adjustment_parameters,
            message=message
        )
        
        logger.info(f"自适应学习参数分析完成: 符合条件={is_compliant}")
        return response
        
    except Exception as e:
        error_msg = f"自适应学习参数分析异常: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def check_error_value_boundary(error_value: float) -> Dict[str, Any]:
    """
    检查误差值边界条件：0.0g ≤ 误差值 ≤ 0.4g
    
    Args:
        error_value (float): 误差值（克）
        
    Returns:
        Dict[str, Any]: 检查结果
    """
    compliant = 0.0 <= error_value <= 0.4
    
    return {
        "compliant": compliant,
        "error_value": error_value,
        "min_required": 0.0,
        "max_required": 0.4,
        "description": f"误差值{error_value:.2f}g，要求范围[0.0g, 0.4g]"
    }

def check_cycle_time_boundary(actual_total_cycle_ms: int, standard_total_cycle_ms: int) -> Dict[str, Any]:
    """
    检查总周期边界条件：0 < 实际总周期 ≤ 标准总周期
    
    Args:
        actual_total_cycle_ms (int): 实际总周期（毫秒）
        standard_total_cycle_ms (int): 标准总周期（毫秒）
        
    Returns:
        Dict[str, Any]: 检查结果
    """
    compliant = 0 < actual_total_cycle_ms <= standard_total_cycle_ms
    
    return {
        "compliant": compliant,
        "actual_cycle": actual_total_cycle_ms,
        "standard_cycle": standard_total_cycle_ms,
        "description": f"实际总周期{actual_total_cycle_ms}ms，标准周期{standard_total_cycle_ms}ms"
    }

def check_fine_time_boundary(actual_fine_time_ms: int) -> Dict[str, Any]:
    """
    检查慢加时间边界条件：实际慢加时间 ≥ 2000ms
    
    Args:
        actual_fine_time_ms (int): 实际慢加时间（毫秒）
        
    Returns:
        Dict[str, Any]: 检查结果
    """
    compliant = actual_fine_time_ms >= 2000
    
    return {
        "compliant": compliant,
        "actual_fine_time": actual_fine_time_ms,
        "min_required": 2000,
        "description": f"实际慢加时间{actual_fine_time_ms}ms，要求≥2000ms"
    }

def check_fall_value_boundary(fall_value: float) -> Dict[str, Any]:
    """
    检查落差值边界条件：0.0g ≤ 落差值 ≤ 1.0g
    
    Args:
        fall_value (float): 落差值（克）
        
    Returns:
        Dict[str, Any]: 检查结果
    """
    compliant = 0.0 <= fall_value <= 1.0
    
    return {
        "compliant": compliant,
        "fall_value": fall_value,
        "min_required": 0.0,
        "max_required": 1.0,
        "description": f"落差值{fall_value}g，要求范围[0.0g, 1.0g]"
    }

def calculate_adjustment_parameters(
    request: AdaptiveLearningAnalysisRequest,
    actual_fine_time_ms: int,
    standard_total_cycle_ms: int,
    fine_flow_rate: Optional[float],
    error_check: Dict[str, Any],
    cycle_check: Dict[str, Any],
    fine_time_check: Dict[str, Any],
    fall_value_check: Dict[str, Any]
) -> Dict[str, float]:
    """
    计算需要调整的参数
    
    Args:
        request: 原始请求
        actual_fine_time_ms: 实际慢加时间
        standard_total_cycle_ms: 标准总周期
        fine_flow_rate: 慢加流速
        error_check: 误差值检查结果
        cycle_check: 总周期检查结果
        fine_time_check: 慢加时间检查结果
        fall_value_check: 落差值检查结果
        
    Returns:
        Dict[str, float]: 调整参数字典
    """
    adjustment_params = {}
    new_coarse_advance = request.current_coarse_advance
    new_fall_value = request.current_fall_value
    
    # 检查落差值边界，如果超出则直接失败
    if not fall_value_check["compliant"]:
        logger.warning("落差值超出边界范围，学习失败")
        # 这种情况下应该在上层处理失败
        return {}
    
    # 1. 处理慢加时间不足的情况
    if not fine_time_check["compliant"]:
        fine_time = actual_fine_time_ms
        
        if 0 <= fine_time < 800:
            new_coarse_advance += 5.0
        elif 800 <= fine_time < 1600:
            new_coarse_advance += 2.4
        elif 1600 <= fine_time < 2000:
            new_coarse_advance += 1.5
        elif 2000 <= fine_time < 2700:
            new_coarse_advance += 1.0
        
        logger.info(f"慢加时间{fine_time}ms不足，快加提前量增加到{new_coarse_advance}g")
    
    # 2. 处理总周期超出标准的情况
    if not cycle_check["compliant"] and request.actual_total_cycle_ms > standard_total_cycle_ms:
        if fine_flow_rate is not None:
            cycle_diff = (request.actual_total_cycle_ms - standard_total_cycle_ms)/1000
            reduction = cycle_diff * fine_flow_rate + 1
            new_coarse_advance = round(max(0, new_coarse_advance - reduction), 1)  # 保留1位小数
            logger.info(f"总周期超出{cycle_diff}ms，快加提前量减少到{new_coarse_advance:.1f}g")
    
    # 3. 处理误差值超出边界的情况
    if not error_check["compliant"]:        
        if request.error_value > 0.4:
            new_fall_value += 0.1
            logger.info(f"误差值{request.error_value}g > 0.4g，落差值增加到{new_fall_value}g")
        elif request.error_value < 0.0:
            new_fall_value = max(0.0, new_fall_value - 0.1)
            logger.info(f"误差值{request.error_value}g < 0.0g，落差值减少到{new_fall_value}g")
    
    # 应用约束
    new_coarse_advance = round(max(0.0, new_coarse_advance), 1)  # 保留1位小数
    new_fall_value = max(0.0, min(1.0, new_fall_value))
    
    # 检查调整后的落差值是否仍在范围内
    if new_fall_value < 0.0 or new_fall_value > 1.0:
        logger.error(f"调整后落差值{new_fall_value}g超出范围[0.0g, 1.0g]，学习失败")
        return {}
    
    # 只返回实际需要调整的参数
    if new_coarse_advance != request.current_coarse_advance:
        adjustment_params["coarse_advance"] = round(new_coarse_advance, 1)  # 保留1位小数
    
    if new_fall_value != request.current_fall_value:
        adjustment_params["fall_value"] = new_fall_value
    
    return adjustment_params

def generate_analysis_message(
    is_compliant: bool,
    error_check: Dict[str, Any],
    cycle_check: Dict[str, Any],
    fine_time_check: Dict[str, Any],
    fall_value_check: Dict[str, Any],
    adjustment_parameters: Optional[Dict[str, float]]
) -> str:
    """
    生成分析结果消息
    
    Args:
        is_compliant: 是否符合条件
        error_check: 误差值检查结果
        cycle_check: 总周期检查结果
        fine_time_check: 慢加时间检查结果
        fall_value_check: 落差值检查结果
        adjustment_parameters: 调整参数
        
    Returns:
        str: 分析消息
    """
    if is_compliant:
        return "✅ 自适应学习参数符合所有边界条件"
    
    issues = []
    
    if not error_check["compliant"]:
        issues.append(f"误差值{error_check['error_value']:.2f}g超出范围[0.0g, 0.4g]")
    
    if not cycle_check["compliant"]:
        if cycle_check["actual_cycle"] > cycle_check["standard_cycle"]:
            issues.append(f"总周期{cycle_check['actual_cycle']}ms超出标准{cycle_check['standard_cycle']}ms")
        else:
            issues.append(f"总周期{cycle_check['actual_cycle']}ms≤0")
    
    if not fine_time_check["compliant"]:
        issues.append(f"慢加时间{fine_time_check['actual_fine_time']}ms < 2000ms")
    
    if not fall_value_check["compliant"]:
        issues.append(f"落差值{fall_value_check['fall_value']}g超出范围[0.0g, 1.0g]")
    
    message = f"❌ 不符合条件: {'; '.join(issues)}"
    
    if adjustment_parameters:
        adjustments = []
        for param, value in adjustment_parameters.items():
            if param == "coarse_advance":
                adjustments.append(f"快加提前量→{value:.1f}g")
            elif param == "fall_value":
                adjustments.append(f"落差值→{value}g")
        
        if adjustments:
            message += f"; 调整参数: {', '.join(adjustments)}"
    
    return message

# FastAPI路由处理函数
def handle_adaptive_learning_analysis(request: AdaptiveLearningAnalysisRequest) -> AdaptiveLearningAnalysisResponse:
    """
    处理自适应学习参数分析请求
    
    Args:
        request (AdaptiveLearningAnalysisRequest): 分析请求
        
    Returns:
        AdaptiveLearningAnalysisResponse: 分析结果
    """
    try:
        return analyze_adaptive_learning_parameters(request)
    except Exception as e:
        logger.error(f"处理自适应学习参数分析请求失败: {str(e)}")
        raise

# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 测试分析
    test_request = AdaptiveLearningAnalysisRequest(
        target_weight=200.0,
        actual_total_cycle_ms=9500,
        actual_coarse_time_ms=3800,
        error_value=0.3,
        current_coarse_advance=15.0,
        current_fall_value=0.4,
        fine_flow_rate=1.05  # 来自慢加时间测定的流速值 (6g / 5.7s ≈ 1.05g/s)
    )
    
    try:
        result = analyze_adaptive_learning_parameters(test_request)
        print(f"分析结果: {result.message}")
        print(f"符合条件: {result.is_compliant}")
        if result.adjustment_parameters:
            print(f"调整参数: {result.adjustment_parameters}")
    except Exception as e:
        print(f"分析失败: {e}")