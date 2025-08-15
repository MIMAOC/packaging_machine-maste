# models/request_models.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
请求数据模型
定义API请求的数据结构

作者：AI助手
创建日期：2025-07-23
更新日期：2025-07-24（添加慢加时间分析请求模型和自适应学习分析请求模型）
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class WeightAnalysisRequest(BaseModel):
    """重量分析请求模型"""
    target_weight: float = Field(..., description="目标重量（克）")
    analysis_type: str = Field(default="coarse_speed", description="分析类型")
    client_version: Optional[str] = Field(default="1.5.1", description="客户端版本")
    timestamp: Optional[str] = Field(default=None, description="请求时间戳")
    
    @validator('target_weight')
    def validate_target_weight(cls, v):
        if v <= 0:
            raise ValueError('目标重量必须大于0')
        if v > 2000:
            raise ValueError('目标重量不能超过2000克')
        return v
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        allowed_types = ['coarse_speed']
        if v not in allowed_types:
            raise ValueError(f'分析类型必须是: {", ".join(allowed_types)}')
        return v

class CoarseTimeAnalysisRequest(BaseModel):
    """快加时间分析请求模型"""
    target_weight: float = Field(..., description="目标重量（克）")
    coarse_time_ms: int = Field(..., description="快加时间（毫秒）")
    current_coarse_speed: int = Field(..., description="当前快加速度")
    analysis_type: str = Field(default="coarse_time", description="分析类型")
    client_version: Optional[str] = Field(default="1.5.1", description="客户端版本")
    timestamp: Optional[str] = Field(default=None, description="请求时间戳")
    
    @validator('target_weight')
    def validate_target_weight(cls, v):
        if v <= 0:
            raise ValueError('目标重量必须大于0')
        if v > 2000:
            raise ValueError('目标重量不能超过2000克')
        return v
    
    @validator('coarse_time_ms')
    def validate_coarse_time(cls, v):
        if v <= 0:
            raise ValueError('快加时间必须大于0')
        if v > 30000:
            raise ValueError('快加时间不能超过30秒')
        return v
    
    @validator('current_coarse_speed')
    def validate_coarse_speed(cls, v):
        if not (1 <= v <= 100):
            raise ValueError('快加速度必须在1-100档之间')
        return v

class FlightMaterialAnalysisRequest(BaseModel):
    """飞料值分析请求模型"""
    target_weight: float = Field(..., description="目标重量（克）")
    recorded_weights: List[float] = Field(..., min_items=3, max_items=3, description="3次记录的实时重量")
    analysis_type: str = Field(default="flight_material", description="分析类型")
    client_version: Optional[str] = Field(default="1.5.1", description="客户端版本")
    timestamp: Optional[str] = Field(default=None, description="请求时间戳")
    
    @validator('target_weight')
    def validate_target_weight(cls, v):
        if v <= 0:
            raise ValueError('目标重量必须大于0')
        if v > 2000:
            raise ValueError('目标重量不能超过2000克')
        return v
    
    @validator('recorded_weights')
    def validate_recorded_weights(cls, v):
        if len(v) != 3:
            raise ValueError('必须提供3次实时重量数据')
        
        for i, weight in enumerate(v):
            if weight <= 0:
                raise ValueError(f'第{i+1}次实时重量必须大于0')
            if weight > 2000:
                raise ValueError(f'第{i+1}次实时重量不能超过2000克')
        
        return v

class FineTimeAnalysisRequest(BaseModel):
    """慢加时间分析请求模型"""
    target_weight: float = Field(..., description="目标重量（克）")
    fine_time_ms: int = Field(..., description="慢加时间（毫秒）")
    current_fine_speed: int = Field(..., description="当前慢加速度")
    original_target_weight: float = Field(..., description="原始目标重量（AI生产时输入的真实重量）")
    flight_material_value: Optional[float] = Field(default=0.0, description="快加飞料值（来自第二阶段）")
    analysis_type: str = Field(default="fine_time", description="分析类型")
    client_version: Optional[str] = Field(default="1.5.1", description="客户端版本")
    timestamp: Optional[str] = Field(default=None, description="请求时间戳")
    
    @validator('target_weight')
    def validate_target_weight(cls, v):
        if v <= 0:
            raise ValueError('目标重量必须大于0')
        if v > 2000:
            raise ValueError('目标重量不能超过2000克')
        return v
    
    @validator('fine_time_ms')
    def validate_fine_time(cls, v):
        if v <= 0:
            raise ValueError('慢加时间必须大于0')
        if v > 80000:
            raise ValueError('慢加时间不能超过80秒')
        return v
    
    @validator('current_fine_speed')
    def validate_fine_speed(cls, v):
        if not (1 <= v <= 100):
            raise ValueError('慢加速度必须在1-100档之间')
        return v
    
    @validator('original_target_weight')
    def validate_original_target_weight(cls, v):
        if v <= 0:
            raise ValueError('原始目标重量必须大于0')
        if v > 2000:
            raise ValueError('原始目标重量不能超过2000克')
        return v

class AdaptiveLearningAnalysisRequest(BaseModel):
    """自适应学习阶段参数分析请求模型"""
    target_weight: float = Field(..., description="目标重量（克）")
    actual_total_cycle_ms: int = Field(..., description="实际总周期（毫秒）")
    actual_coarse_time_ms: int = Field(..., description="实际快加时间（毫秒）")
    error_value: float = Field(..., description="误差值（实时重量-目标重量，克）")
    current_coarse_advance: float = Field(..., description="当前快加提前量（克）")
    current_fall_value: float = Field(..., description="当前落差值（克）")
    fine_flow_rate: Optional[float] = Field(default=None, description="慢加流速（g/s），来自慢加时间测定结果")
    analysis_type: str = Field(default="adaptive_learning", description="分析类型")
    client_version: Optional[str] = Field(default="1.5.1", description="客户端版本")
    timestamp: Optional[str] = Field(default=None, description="请求时间戳")
    
    @validator('target_weight')
    def validate_target_weight(cls, v):
        if v <= 0:
            raise ValueError('目标重量必须大于0')
        if v > 2000:
            raise ValueError('目标重量不能超过2000克')
        return v
    
    @validator('actual_total_cycle_ms')
    def validate_total_cycle(cls, v):
        if v <= 0:
            raise ValueError('实际总周期必须大于0')
        if v > 60000:
            raise ValueError('实际总周期不能超过60秒')
        return v
    
    @validator('actual_coarse_time_ms')
    def validate_coarse_time(cls, v):
        if v <= 0:
            raise ValueError('实际快加时间必须大于0')
        if v > 30000:
            raise ValueError('实际快加时间不能超过30秒')
        return v
    
    @validator('error_value')
    def validate_error_value(cls, v):
        if abs(v) > 50:
            raise ValueError('误差值过大，请检查测量数据')
        return v
    
    @validator('current_coarse_advance')
    def validate_coarse_advance(cls, v):
        if v < 0:
            raise ValueError('快加提前量不能小于0')
        return v
    
    @validator('current_fall_value')
    def validate_fall_value(cls, v):
        if v < 0:
            raise ValueError('落差值不能小于0')
        if v > 1.0:
            raise ValueError('落差值不能大于1.0g')
        return v
    
    @validator('fine_flow_rate')
    def validate_fine_flow_rate(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError('慢加流速不能小于0')
            if v > 10:
                raise ValueError('慢加流速不能超过10g/s')
        return v