# models/response_models.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应数据模型
定义API响应的数据结构

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-24（添加慢加时间分析响应模型、自适应学习分析响应模型，并更新慢加时间响应以包含流速）
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(..., description="请求是否成功")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="响应时间戳")

class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = Field(default=False, description="请求失败")
    error: str = Field(..., description="错误信息")

class HealthResponse(BaseResponse):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    endpoints: List[str] = Field(..., description="可用端点列表")

class WeightAnalysisResponse(BaseResponse):
    """重量分析响应模型"""
    target_weight: float = Field(..., description="目标重量")
    coarse_speed: int = Field(..., description="推荐的快加速度")
    message: str = Field(..., description="分析结果消息")
    analysis_type: str = Field(..., description="分析类型")
    rule_matched: Optional[Dict[str, Any]] = Field(default=None, description="匹配的规则信息")

class CoarseTimeAnalysisResponse(BaseResponse):
    """快加时间分析响应模型"""
    target_weight: float = Field(..., description="目标重量")
    coarse_time_ms: int = Field(..., description="快加时间")
    current_coarse_speed: int = Field(..., description="当前快加速度")
    is_compliant: bool = Field(..., description="是否符合条件")
    new_coarse_speed: Optional[int] = Field(default=None, description="新的快加速度（如需调整）")
    message: str = Field(..., description="分析结果消息")
    analysis_details: Optional[Dict[str, Any]] = Field(default=None, description="详细分析信息")

class FlightMaterialAnalysisResponse(BaseResponse):
    """飞料值分析响应模型"""
    target_weight: float = Field(..., description="目标重量")
    recorded_weights: List[float] = Field(..., description="3次记录的实时重量")
    flight_material_details: List[float] = Field(..., description="3次飞料值详情")
    average_flight_material: float = Field(..., description="平均飞料值")
    message: str = Field(..., description="分析结果消息")
    analysis_type: str = Field(..., description="分析类型")

class FineTimeAnalysisResponse(BaseResponse):
    """慢加时间分析响应模型"""
    target_weight: float = Field(..., description="目标重量")
    fine_time_ms: int = Field(..., description="慢加时间")
    current_fine_speed: int = Field(..., description="当前慢加速度")
    is_compliant: bool = Field(..., description="是否符合条件")
    new_fine_speed: Optional[int] = Field(default=None, description="新的慢加速度（如需调整）")
    coarse_advance: Optional[float] = Field(default=None, description="快加提前量（符合条件时计算）")
    fine_flow_rate: Optional[float] = Field(default=None, description="慢加流速（g/s），基于6g目标重量计算")
    message: str = Field(..., description="分析结果消息")
    analysis_details: Optional[Dict[str, Any]] = Field(default=None, description="详细分析信息")

class AdaptiveLearningAnalysisResponse(BaseResponse):
    """自适应学习阶段参数分析响应模型"""
    target_weight: float = Field(..., description="目标重量")
    actual_total_cycle_ms: int = Field(..., description="实际总周期")
    actual_coarse_time_ms: int = Field(..., description="实际快加时间")
    actual_fine_time_ms: int = Field(..., description="实际慢加时间（计算值）")
    error_value: float = Field(..., description="误差值")
    is_compliant: bool = Field(..., description="是否符合条件")
    
    # 分析详情
    standard_total_cycle_ms: int = Field(..., description="标准总周期")
    coarse_time_ratio: float = Field(..., description="快加时间占比")
    fine_flow_rate: Optional[float] = Field(default=None, description="慢加流速（g/s）")
    
    # 边界条件检查结果
    error_check: Dict[str, Any] = Field(..., description="误差值边界检查")
    cycle_check: Dict[str, Any] = Field(..., description="总周期边界检查")
    fine_time_check: Dict[str, Any] = Field(..., description="慢加时间边界检查")
    fall_value_check: Dict[str, Any] = Field(..., description="落差值边界检查")
    
    # 调整参数（如果不符合条件）
    adjustment_parameters: Optional[Dict[str, float]] = Field(default=None, description="需要调整的参数")
    
    message: str = Field(..., description="分析结果消息")

class AdaptiveLearningErrorResponse(BaseResponse):
    """自适应学习阶段错误响应模型"""
    success: bool = Field(default=False, description="请求失败")
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(default=None, description="错误代码")