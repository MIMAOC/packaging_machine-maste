"""
料斗学习状态管理器

作者：C
创建日期：2025-07-30
"""

import threading
from typing import Dict, Optional, Callable
from enum import Enum

class LearningStage(Enum):
    NONE = "none"
    COARSE_TIME = "coarse_time"
    FLIGHT_MATERIAL = "flight_material"
    FINE_TIME = "fine_time"
    ADAPTIVE_LEARNING = "adaptive_learning"
class LearningStatus(Enum):
    NOT_STARTED = "not_started"
    LEARNING = "learning"
    FAILED = "failed"
    COMPLETED = "completed"

class BucketLearningState:
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.current_stage = LearningStage.NONE
        self.status = LearningStatus.NOT_STARTED
        self.failure_message = ""
        self.completion_time = None
        
        self.stage_results = {
            LearningStage.COARSE_TIME: None,
            LearningStage.FLIGHT_MATERIAL: None,
            LearningStage.FINE_TIME: None,
            LearningStage.ADAPTIVE_LEARNING: None
        }
    
    def start_stage(self, stage: LearningStage):
        self.current_stage = stage
        self.status = LearningStatus.LEARNING
        self.failure_message = ""
    
    def complete_stage(self, stage: LearningStage, success: bool, message: str = ""):
        self.stage_results[stage] = success
        
        if not success:
            self.status = LearningStatus.FAILED
            self.failure_message = message
        else:
            if self._all_stages_completed():
                self.status = LearningStatus.COMPLETED
                self.completion_time = None
    
    def _all_stages_completed(self) -> bool:
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
        if self.status == LearningStatus.NOT_STARTED:
            return "#888888"
        elif self.status == LearningStatus.LEARNING:
            return "#4a90e2"
        elif self.status == LearningStatus.FAILED:
            return "#ff0000"
        elif self.status == LearningStatus.COMPLETED:
            return "#00aa00"
        return "#888888"
    
    def reset(self):
        self.current_stage = LearningStage.NONE
        self.status = LearningStatus.NOT_STARTED
        self.failure_message = ""
        self.completion_time = None
        for stage in self.stage_results:
            self.stage_results[stage] = None

class BucketLearningStateManager:
    
    def __init__(self):
        self.bucket_states: Dict[int, BucketLearningState] = {}
        self.lock = threading.RLock()
        
        self.on_state_changed: Optional[Callable[[int, BucketLearningState], None]] = None
        self.on_all_completed: Optional[Callable[[Dict[int, BucketLearningState]], None]] = None
        
        self._initialize_bucket_states()
    
    def _initialize_bucket_states(self):
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketLearningState(bucket_id)
    
    def start_bucket_stage(self, bucket_id: int, stage: LearningStage):
        with self.lock:
            if bucket_id in self.bucket_states:
                state = self.bucket_states[bucket_id]
                state.start_stage(stage)
                self._trigger_state_changed(bucket_id, state)
    
    def complete_bucket_stage(self, bucket_id: int, stage: LearningStage, 
                            success: bool, message: str = ""):
        with self.lock:
            if bucket_id in self.bucket_states:
                state = self.bucket_states[bucket_id]
                state.complete_stage(stage, success, message)
                self._trigger_state_changed(bucket_id, state)
                
                self._check_all_buckets_completed()
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketLearningState]:
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def get_all_states(self) -> Dict[int, BucketLearningState]:
        with self.lock:
            return self.bucket_states.copy()
    
    def reset_all_states(self):
        with self.lock:
            for state in self.bucket_states.values():
                state.reset()
    
    def is_all_completed(self) -> bool:
        with self.lock:
            for state in self.bucket_states.values():
                if state.status in [LearningStatus.NOT_STARTED, LearningStatus.LEARNING]:
                    return False
            return True
    
    def get_completed_count(self) -> tuple[int, int, int]:
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
        if self.is_all_completed():
            if self.on_all_completed:
                try:
                    self.on_all_completed(self.get_all_states())
                except Exception as e:
                    pass
    
    def _trigger_state_changed(self, bucket_id: int, state: BucketLearningState):
        if self.on_state_changed:
            try:
                self.on_state_changed(bucket_id, state)
            except Exception as e:
                pass

def create_bucket_learning_state_manager() -> BucketLearningStateManager:
    return BucketLearningStateManager()