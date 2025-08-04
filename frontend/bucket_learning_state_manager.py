#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
料斗学习状态管理器
用于跟踪和管理每个料斗在学习过程中的状态

作者：AI助手
创建日期：2025-07-30
"""

import threading
from typing import Dict, Optional, Callable
from enum import Enum

class LearningStage(Enum):
    """学习阶段枚举"""
    NONE = "none"                           # 未开始
    COARSE_TIME = "coarse_time"            # 快加时间测定
    FLIGHT_MATERIAL = "flight_material"     # 快加飞料测定  
    FINE_TIME = "fine_time"                # 慢加速度测定
    ADAPTIVE_LEARNING = "adaptive_learning" # 自适应学习阶段

class LearningStatus(Enum):
    """学习状态枚举"""
    NOT_STARTED = "not_started"    # 未开始
    LEARNING = "learning"          # 学习中
    FAILED = "failed"             # 学习失败
    COMPLETED = "completed"       # 学习完成

class BucketLearningState:
    """单个料斗的学习状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.current_stage = LearningStage.NONE
        self.status = LearningStatus.NOT_STARTED
        self.failure_message = ""
        self.completion_time = None
        
        # 记录各阶段的完成情况
        self.stage_results = {
            LearningStage.COARSE_TIME: None,        # None/True/False
            LearningStage.FLIGHT_MATERIAL: None,
            LearningStage.FINE_TIME: None,
            LearningStage.ADAPTIVE_LEARNING: None
        }
    
    def start_stage(self, stage: LearningStage):
        """开始新的学习阶段"""
        self.current_stage = stage
        self.status = LearningStatus.LEARNING
        self.failure_message = ""
    
    def complete_stage(self, stage: LearningStage, success: bool, message: str = ""):
        """完成当前学习阶段"""
        self.stage_results[stage] = success
        
        if not success:
            self.status = LearningStatus.FAILED
            self.failure_message = message
        else:
            # 检查是否所有阶段都完成
            if self._all_stages_completed():
                self.status = LearningStatus.COMPLETED
                self.completion_time = None  # 可以记录完成时间
    
    def _all_stages_completed(self) -> bool:
        """检查是否所有阶段都成功完成"""
        required_stages = [
            LearningStage.COARSE_TIME,
            LearningStage.FLIGHT_MATERIAL, 
            LearningStage.FINE_TIME,
            LearningStage.ADAPTIVE_LEARNING
        ]
        
        for stage in required_stages:
            if self.stage_results.get(stage) != True:
                return False
        return True
    
    def get_display_text(self) -> str:
        """获取显示文本"""
        if self.status == LearningStatus.NOT_STARTED:
            return "未开始"
        elif self.status == LearningStatus.LEARNING:
            return "学习中"
        elif self.status == LearningStatus.FAILED:
            return "学习失败"
        elif self.status == LearningStatus.COMPLETED:
            return "学习完成"
        return "未知状态"
    
    def get_display_color(self) -> str:
        """获取显示颜色"""
        if self.status == LearningStatus.NOT_STARTED:
            return "#888888"  # 灰色
        elif self.status == LearningStatus.LEARNING:
            return "#4a90e2"  # 蓝色
        elif self.status == LearningStatus.FAILED:
            return "#ff0000"  # 红色
        elif self.status == LearningStatus.COMPLETED:
            return "#00aa00"  # 绿色
        return "#888888"
    
    def reset(self):
        """重置状态"""
        self.current_stage = LearningStage.NONE
        self.status = LearningStatus.NOT_STARTED
        self.failure_message = ""
        self.completion_time = None
        for stage in self.stage_results:
            self.stage_results[stage] = None

class BucketLearningStateManager:
    """料斗学习状态管理器"""
    
    def __init__(self):
        self.bucket_states: Dict[int, BucketLearningState] = {}
        self.lock = threading.RLock()
        
        # 事件回调
        self.on_state_changed: Optional[Callable[[int, BucketLearningState], None]] = None
        self.on_all_completed: Optional[Callable[[Dict[int, BucketLearningState]], None]] = None
        
        # 初始化6个料斗的状态
        self._initialize_bucket_states()
    
    def _initialize_bucket_states(self):
        """初始化料斗状态"""
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketLearningState(bucket_id)
    
    def start_bucket_stage(self, bucket_id: int, stage: LearningStage):
        """启动料斗的学习阶段"""
        with self.lock:
            if bucket_id in self.bucket_states:
                state = self.bucket_states[bucket_id]
                state.start_stage(stage)
                self._trigger_state_changed(bucket_id, state)
    
    def complete_bucket_stage(self, bucket_id: int, stage: LearningStage, 
                            success: bool, message: str = ""):
        """完成料斗的学习阶段"""
        with self.lock:
            if bucket_id in self.bucket_states:
                state = self.bucket_states[bucket_id]
                state.complete_stage(stage, success, message)
                self._trigger_state_changed(bucket_id, state)
                
                # 检查是否所有料斗都完成
                self._check_all_buckets_completed()
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketLearningState]:
        """获取料斗状态"""
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def get_all_states(self) -> Dict[int, BucketLearningState]:
        """获取所有料斗状态"""
        with self.lock:
            return self.bucket_states.copy()
    
    def reset_all_states(self):
        """重置所有料斗状态"""
        with self.lock:
            for state in self.bucket_states.values():
                state.reset()
    
    def is_all_completed(self) -> bool:
        """检查是否所有料斗都已完成（成功或失败）"""
        with self.lock:
            for state in self.bucket_states.values():
                if state.status in [LearningStatus.NOT_STARTED, LearningStatus.LEARNING]:
                    return False
            return True
    
    def get_completed_count(self) -> tuple[int, int, int]:
        """获取完成统计 (成功数量, 失败数量, 总数量)"""
        with self.lock:
            success_count = 0
            failed_count = 0
            total_count = len(self.bucket_states)
            
            for state in self.bucket_states.values():
                if state.status == LearningStatus.COMPLETED:
                    success_count += 1
                elif state.status == LearningStatus.FAILED:
                    failed_count += 1
            
            return success_count, failed_count, total_count
    
    def _check_all_buckets_completed(self):
        """检查所有料斗是否都完成"""
        if self.is_all_completed():
            if self.on_all_completed:
                try:
                    self.on_all_completed(self.get_all_states())
                except Exception as e:
                    print(f"[错误] 所有料斗完成事件回调异常: {e}")
    
    def _trigger_state_changed(self, bucket_id: int, state: BucketLearningState):
        """触发状态变化事件"""
        if self.on_state_changed:
            try:
                self.on_state_changed(bucket_id, state)
            except Exception as e:
                print(f"[错误] 状态变化事件回调异常: {e}")

def create_bucket_learning_state_manager() -> BucketLearningStateManager:
    """创建料斗学习状态管理器实例的工厂函数"""
    return BucketLearningStateManager()