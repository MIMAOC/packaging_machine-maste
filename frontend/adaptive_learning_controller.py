"""
自适应学习阶段控制器
"""

import threading
import time
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from bucket_monitoring import BucketMonitoringService, create_bucket_monitoring_service
from clients.adaptive_learning_webapi import analyze_adaptive_learning_parameters
from plc_addresses import BUCKET_PARAMETER_ADDRESSES, BUCKET_MONITORING_ADDRESSES, get_bucket_control_address

try:
    from database.intelligent_learning_dao import IntelligentLearningDAO
    INTELLIGENT_LEARNING_DAO_AVAILABLE = True
except ImportError as e:
    INTELLIGENT_LEARNING_DAO_AVAILABLE = False

class BucketAdaptiveLearningState:
    """料斗自适应学习阶段状态"""
    
    def __init__(self, bucket_id: int):
        self.bucket_id = bucket_id
        self.is_testing = False
        self.is_completed = False
        self.original_target_weight = 0.0
        self.current_round = 1
        self.current_attempt = 0
        self.max_rounds = 3
        self.max_attempts_per_round = 15
        self.consecutive_success_count = 0
        self.consecutive_success_required = 3
        self.parameters_initialized = False
        self.material_name = "未知物料"
        
        self.start_time = None
        self.coarse_end_time = None
        self.target_reached_time = None
        self.actual_total_cycle_ms = 0
        self.actual_coarse_time_ms = 0
        self.error_value = 0.0
        self.error_message = ""
        
        self.current_coarse_advance = 0.0
        self.current_fall_value = 0.4
        
        self.bucket_fine_flow_rates: Dict[int, float] = {}
        
        self.is_success = False
        self.final_coarse_speed = 0
        self.final_fine_speed = 44
        self.final_coarse_advance = 0.0
        self.final_fall_value = 0.4
        self.failure_stage = ""
        self.failure_reason = ""
    
    def reset_for_new_test(self, original_target_weight: float):
        self.is_testing = False
        self.is_completed = False
        self.original_target_weight = original_target_weight
        self.current_round = 1
        self.current_attempt = 0
        self.consecutive_success_count = 0
        self.parameters_initialized = False
        self.start_time = None
        self.coarse_end_time = None
        self.target_reached_time = None
        self.actual_total_cycle_ms = 0
        self.actual_coarse_time_ms = 0
        self.error_value = 0.0
        self.error_message = ""
        self.current_coarse_advance = 0.0
        self.current_fall_value = 0.4
        
        self.is_success = False
        self.final_coarse_speed = 0
        self.final_fine_speed = 44
        self.final_coarse_advance = 0.0
        self.final_fall_value = 0.4
        self.failure_stage = ""
        self.failure_reason = ""
    
    def start_new_round(self):
        self.current_round += 1
        self.current_attempt = 0
    
    def start_next_attempt(self):
        self.is_testing = True
        self.current_attempt += 1
        self.start_time = datetime.now()
        self.coarse_end_time = None
        self.target_reached_time = None
    
    def record_coarse_end(self, coarse_end_time: datetime):
        self.coarse_end_time = coarse_end_time
        self.actual_coarse_time_ms = int((coarse_end_time - self.start_time).total_seconds() * 1000)
    
    def record_target_reached(self, reached_time: datetime):
        self.target_reached_time = reached_time
        self.actual_total_cycle_ms = int((reached_time - self.start_time).total_seconds() * 1000)
        self.is_testing = False
    
    def record_error_value(self, error_value: float):
        self.error_value = error_value
    
    def record_success(self):
        self.consecutive_success_count += 1
    
    def reset_consecutive_success(self):
        self.consecutive_success_count = 0
    
    def is_current_round_exhausted(self) -> bool:
        return self.current_attempt >= self.max_attempts_per_round
    
    def has_reached_max_rounds(self) -> bool:
        return self.current_round >= self.max_rounds
    
    def is_learning_successful(self) -> bool:
        return self.consecutive_success_count >= self.consecutive_success_required
    
    def complete_successfully(self, coarse_speed: int, fine_speed: int):
        self.is_testing = False
        self.is_completed = True
        self.is_success = True
        self.final_coarse_speed = coarse_speed
        self.final_fine_speed = fine_speed
        self.final_coarse_advance = self.current_coarse_advance
        self.final_fall_value = self.current_fall_value
    
    def fail_with_error(self, error_message: str, failure_stage: str = "自适应学习阶段"):
        self.is_testing = False
        self.is_completed = True
        self.is_success = False
        self.error_message = error_message
        self.failure_stage = failure_stage
        self.failure_reason = error_message

class AdaptiveLearningController:
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
        self.bucket_states: Dict[int, BucketAdaptiveLearningState] = {}
        self.lock = threading.RLock()
        
        self.root_reference = None
        
        self.monitoring_service = create_bucket_monitoring_service(modbus_client)
        
        self.on_bucket_completed: Optional[Callable[[int, bool, str], None]] = None
        self.on_bucket_failed: Optional[Callable[[int, str, str], None]] = None
        self.on_progress_update: Optional[Callable[[int, int, int, str], None]] = None
        self.on_log_message: Optional[Callable[[str], None]] = None
        
        self.on_material_shortage: Optional[Callable[[int, str, bool], None]] = None
        
        self.active_buckets: set = set()
        
        self._initialize_bucket_states()
        
        self.monitoring_service.on_target_reached = self._on_target_reached
        self.monitoring_service.on_coarse_status_changed = self._on_coarse_status_changed
        self.monitoring_service.on_monitoring_log = self._on_monitoring_log
        
        self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
    
    def _initialize_bucket_states(self):
        with self.lock:
            for bucket_id in range(1, 7):
                self.bucket_states[bucket_id] = BucketAdaptiveLearningState(bucket_id)
                
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        try:
            if stage == "adaptive_learning" and not is_production:
                self._handle_material_shortage_for_bucket(bucket_id)
                
                def trigger_shortage_failure():
                    error_message = "料斗物料低于最低水平线或闭合不正常"
                    self._handle_bucket_failure(bucket_id, error_message, stage)
                
                import threading
                threading.Timer(0.2 * bucket_id, trigger_shortage_failure).start()

        except Exception as e:
            pass
    
    def _handle_material_shortage_for_bucket(self, bucket_id: int):
        try:
            self.stop_bucket_adaptive_learning_test(bucket_id)
            
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if state:
                    state.fail_with_error("物料不足", "自适应学习阶段")
            
        except Exception as e:
            pass
    
    def start_adaptive_learning_test(self, bucket_id: int, original_target_weight: float, 
                                    fine_flow_rate: float = None) -> bool:
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return False
                
                state = self.bucket_states[bucket_id]
                if state.is_testing or state.is_completed:
                    return True
                
                self.active_buckets.add(bucket_id)
                
                state.reset_for_new_test(original_target_weight)
                
                if fine_flow_rate is not None and fine_flow_rate > 0:
                    state.bucket_fine_flow_rates[bucket_id] = fine_flow_rate
                else:
                    pass
            
            self.monitoring_service.set_material_check_enabled(True)
            
            self._start_single_attempt(bucket_id)
            
            return True
            
        except Exception as e:
            return False
    
    def _read_current_parameters_from_plc(self, bucket_id: int) -> bool:
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return False
            
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            state = self.bucket_states[bucket_id]
            
            coarse_advance_data = self.modbus_client.read_holding_registers(
                bucket_addresses['CoarseAdvance'], 1)
            if coarse_advance_data and len(coarse_advance_data) > 0:
                state.current_coarse_advance = coarse_advance_data[0] / 10.0
            else:
                return False
            
            fall_value_data = self.modbus_client.read_holding_registers(
                bucket_addresses['FallValue'], 1)
            if fall_value_data and len(fall_value_data) > 0:
                state.current_fall_value = fall_value_data[0] / 10.0
            else:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _start_single_attempt(self, bucket_id: int):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.start_next_attempt()
            
            total_progress = max(0, (state.current_round - 1) * state.max_attempts_per_round + state.current_attempt)
            total_max = state.max_rounds * state.max_attempts_per_round
            self._update_progress(bucket_id, total_progress, total_max, 
                                f"第{state.current_round}轮第{state.current_attempt}次测定（连续成功{state.consecutive_success_count}次）")
            
            def attempt_thread():
                self._execute_single_attempt(bucket_id)
            
            thread = threading.Thread(target=attempt_thread, daemon=True, 
                                    name=f"AdaptiveLearning-{bucket_id}-{state.current_round}-{state.current_attempt}")
            thread.start()
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}单次尝试异常: {str(e)}")
    
    def _execute_single_attempt(self, bucket_id: int):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                is_first_attempt = not state.parameters_initialized
            
            if is_first_attempt:
                success = self._write_adaptive_learning_parameters(bucket_id)
                if not success:
                    self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}初始化自适应学习参数失败")
                    return
                
                with self.lock:
                    state.parameters_initialized = True
            else:
                pass
            
            success = self._start_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"启动料斗{bucket_id}失败")
                return
            
            self.monitoring_service.start_monitoring([bucket_id], "adaptive_learning")
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"执行料斗{bucket_id}单次尝试异常: {str(e)}")
    
    def _write_adaptive_learning_parameters(self, bucket_id: int) -> bool:
        try:            
            with self.lock:
                state = self.bucket_states[bucket_id]
                original_target_weight = state.original_target_weight
                fall_value = state.current_fall_value
            
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            
            target_weight_plc = int(original_target_weight * 10)
            fall_value_plc = int(fall_value * 10)
            
            success = self.modbus_client.write_holding_register(
                bucket_addresses['TargetWeight'], target_weight_plc)
            if not success:
                return False
            
            success = self.modbus_client.write_holding_register(
                bucket_addresses['FallValue'], fall_value_plc)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _start_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        try:
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            success = self.modbus_client.write_coil(stop_address, False)
            if not success:
                return False
            
            time.sleep(0.05)
            
            success = self.modbus_client.write_coil(start_address, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _on_coarse_status_changed(self, bucket_id: int, coarse_active: bool):
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                if not coarse_active and state.coarse_end_time is None:
                    state.record_coarse_end(datetime.now())
            
        except Exception as e:
            pass
    
    def _on_target_reached(self, bucket_id: int, time_ms: int):
        try:
            with self.lock:
                if bucket_id not in self.bucket_states:
                    return
                
                state = self.bucket_states[bucket_id]
                if not state.is_testing:
                    return
                
                state.record_target_reached(datetime.now())
            
            def process_thread():
                self._process_target_reached_for_adaptive_learning(bucket_id)
            
            thread = threading.Thread(target=process_thread, daemon=True, 
                                    name=f"ProcessAdaptiveTarget-{bucket_id}")
            thread.start()
            
        except Exception as e:
            pass
    
    def _process_target_reached_for_adaptive_learning(self, bucket_id: int):
        try:
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"停止料斗{bucket_id}失败")
                return
            
            time.sleep(1)
            
            real_weight = self._read_bucket_weight(bucket_id)
            if real_weight is None:
                self._handle_bucket_failure(bucket_id, f"读取料斗{bucket_id}实时重量失败")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                original_target_weight = state.original_target_weight
                error_value = real_weight - original_target_weight
                state.record_error_value(error_value)
            
            success = self._execute_discharge_sequence(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}放料操作失败")
                return
            
            success = self._read_current_parameters_from_plc(bucket_id)
            if not success:
                self._handle_bucket_failure(bucket_id, f"料斗{bucket_id}读取当前PLC参数失败")
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                fine_flow_rate = state.bucket_fine_flow_rates.get(bucket_id)
                
                analysis_params = {
                    'target_weight': original_target_weight,
                    'actual_total_cycle_ms': state.actual_total_cycle_ms,
                    'actual_coarse_time_ms': state.actual_coarse_time_ms,
                    'error_value': error_value,
                    'current_coarse_advance': state.current_coarse_advance,
                    'current_fall_value': state.current_fall_value,
                    'fine_flow_rate': fine_flow_rate
                }
            
            none_params = [key for key, value in analysis_params.items() if value is None and key != 'fine_flow_rate']
            if none_params:
                error_msg = f"料斗{bucket_id}分析参数中包含None值: {none_params}"
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            analysis_success, is_compliant, new_params, analysis_msg = analyze_adaptive_learning_parameters(**analysis_params)
            
            if not analysis_success:
                error_msg = f"料斗{bucket_id}自适应学习参数分析API调用失败: {analysis_msg}"
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            if is_compliant:
                with self.lock:
                    state.record_success()
                    consecutive_count = state.consecutive_success_count
                
                if state.is_learning_successful():
                    self._handle_bucket_success(bucket_id)
                else:
                    time.sleep(1.0)
                    self._start_single_attempt(bucket_id)
            else:
                self._handle_adaptive_learning_not_compliant(bucket_id, new_params, analysis_msg)
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}自适应学习到量流程异常: {str(e)}")
    
    def _handle_adaptive_learning_not_compliant(self, bucket_id: int, new_params: dict, reason: str):
        try:
            if new_params is None:
                error_msg = f"料斗{bucket_id}API分析失败，未返回调整参数，无法继续测定"
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            if not isinstance(new_params, dict):
                error_msg = f"料斗{bucket_id}API返回的调整参数格式错误（期望dict，实际{type(new_params)}），无法继续测定"
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            if not new_params:
                error_msg = f"料斗{bucket_id}API返回空的调整参数，可能是参数超出边界范围，无法继续测定"
                self._handle_bucket_failure(bucket_id, error_msg)
                return
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                old_consecutive_count = state.consecutive_success_count
                state.reset_consecutive_success()
                
                old_coarse_advance = state.current_coarse_advance
                old_fall_value = state.current_fall_value
                
                params_updated = []
                if 'coarse_advance' in new_params:
                    state.current_coarse_advance = new_params['coarse_advance']
                    params_updated.append(f"快加提前量: {old_coarse_advance}g → {new_params['coarse_advance']}g")
                    
                if 'fall_value' in new_params:
                    state.current_fall_value = new_params['fall_value']
                    params_updated.append(f"落差值: {old_fall_value}g → {new_params['fall_value']}g")
                
                current_round = state.current_round
                current_attempt = state.current_attempt
                is_round_exhausted = state.is_current_round_exhausted()
                has_reached_max_rounds = state.has_reached_max_rounds()
                
            success = self._update_bucket_parameters(bucket_id, new_params)
            if not success:
                self._handle_bucket_failure(bucket_id, f"更新料斗{bucket_id}参数失败，无法继续测定")
                return
            
            time.sleep(0.1)
            
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                if is_round_exhausted:
                    if has_reached_max_rounds:
                        self._handle_bucket_failure(bucket_id, 
                            f"已达最大轮次({state.max_rounds})且连续成功次数未达到要求，自适应学习测定失败")
                        return
                    else:
                        state.start_new_round()
                
                time.sleep(1.0)
                self._start_single_attempt(bucket_id)
            
        except Exception as e:
            self._handle_bucket_failure(bucket_id, f"处理料斗{bucket_id}不符合条件异常: {str(e)}，无法继续测定")
    
    def _update_bucket_parameters(self, bucket_id: int, new_params: dict) -> bool:
        try:
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            
            if 'coarse_advance' in new_params:
                coarse_advance_plc = int(new_params['coarse_advance'] * 10)
                success = self.modbus_client.write_holding_register(
                    bucket_addresses['CoarseAdvance'], coarse_advance_plc)
                if not success:
                    return False
            
            if 'fall_value' in new_params:
                fall_value_plc = int(new_params['fall_value'] * 10)
                success = self.modbus_client.write_holding_register(
                    bucket_addresses['FallValue'], fall_value_plc)
                if not success:
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _stop_bucket_with_mutex_protection(self, bucket_id: int) -> bool:
        try:
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            success = self.modbus_client.write_coil(start_address, False)
            if not success:
                return False
            
            time.sleep(0.05)
            
            success = self.modbus_client.write_coil(stop_address, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _read_bucket_weight(self, bucket_id: int) -> Optional[float]:
        try:
            if bucket_id not in BUCKET_MONITORING_ADDRESSES:
                return None
            
            weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
            
            raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
            
            if raw_weight_data is not None and len(raw_weight_data) > 0:
                weight_value = raw_weight_data[0] / 10.0
                return weight_value
            else:
                return None
                
        except Exception as e:
            return None
    
    def _execute_discharge_sequence(self, bucket_id: int) -> bool:
        try:
            discharge_address = get_bucket_control_address(bucket_id, 'DischargeAddress')
            
            success = self.modbus_client.write_coil(discharge_address, True)
            if not success:
                return False
            
            time.sleep(1.5)
            
            success = self.modbus_client.write_coil(discharge_address, False)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _handle_bucket_success(self, bucket_id: int):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                
                coarse_speed = self._get_current_coarse_speed(bucket_id)
                fine_speed = self._get_current_fine_speed(bucket_id)
                
                state.complete_successfully(coarse_speed, fine_speed)
                
                self.active_buckets.discard(bucket_id)
                
                self._save_learning_result_to_database(bucket_id, state)
            
            success_msg = f"🎉 料斗{bucket_id}自适应学习阶段测定成功！连续成功{state.consecutive_success_count}次"
            
            if self.on_bucket_completed:
                try:
                    self.on_bucket_completed(bucket_id, True, success_msg)
                except Exception as e:
                    pass
            
        except Exception as e:
            pass
            
    def _save_learning_result_to_database(self, bucket_id: int, state):
        try:
            if not INTELLIGENT_LEARNING_DAO_AVAILABLE:
                return
            
            material_name = getattr(state, 'material_name', '未知物料')
            
            success, message = IntelligentLearningDAO.save_learning_result(
                material_name=material_name,
                target_weight=state.original_target_weight,
                bucket_id=bucket_id,
                coarse_speed=state.final_coarse_speed,
                fine_speed=state.final_fine_speed,
                coarse_advance=state.final_coarse_advance,
                fall_value=state.final_fall_value
            )
            
            if success:
                self._update_material_ai_status(material_name)
                
        except Exception as e:
            pass
            
    def _update_material_ai_status(self, material_name: str):
        try:
            from database.material_dao import MaterialDAO
            success, message = MaterialDAO.update_material_ai_status_by_name(material_name, "已学习")
        except Exception as e:
            pass
            
    def set_material_name(self, material_name: str):
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.material_name = material_name
            
            self.current_material_name = material_name
            
        except Exception as e:
            pass
    
    def _handle_bucket_failure(self, bucket_id: int, error_message: str, failed_stage: str = "adaptive_learning"):
        try:
            with self.lock:
                state = self.bucket_states[bucket_id]
                state.fail_with_error(error_message, "自适应学习阶段")
                
                self.active_buckets.discard(bucket_id)
            
            total_attempts = (state.current_round-1) * state.max_attempts_per_round + state.current_attempt
            
            def trigger_failure_callback():
                if self.on_bucket_failed:
                    try:
                        self.on_bucket_failed(bucket_id, error_message, failed_stage)
                    except Exception as e:
                        pass
            
            if self.root_reference:
                self.root_reference.after(100, trigger_failure_callback)
            
        except Exception as e:
            pass
    
    def _get_current_coarse_speed(self, bucket_id: int) -> int:
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return 0
            
            coarse_speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['CoarseSpeed']
            data = self.modbus_client.read_holding_registers(coarse_speed_address, 1)
            
            if data and len(data) > 0:
                return data[0]
            else:
                return 0
                
        except Exception as e:
            return 0
    
    def _get_current_fine_speed(self, bucket_id: int) -> int:
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return 44
            
            fine_speed_address = BUCKET_PARAMETER_ADDRESSES[bucket_id]['FineSpeed']
            data = self.modbus_client.read_holding_registers(fine_speed_address, 1)
            
            if data and len(data) > 0:
                return data[0]
            else:
                return 44
                
        except Exception as e:
            return 44
    
    def handle_material_shortage_continue(self, bucket_id: int) -> Tuple[bool, str]:
        try:
            self.monitoring_service.handle_material_shortage_continue(bucket_id, False)
            
            with self.lock:
                state = self.bucket_states.get(bucket_id)
                if not state:
                    return False, f"无效的料斗ID: {bucket_id}"
                
                state.is_testing = False
                state.is_completed = False
                state.error_message = ""
                state.failure_stage = ""
                state.failure_reason = ""
                original_target_weight = state.original_target_weight
                fine_flow_rate = state.bucket_fine_flow_rates.get(bucket_id)
                
                self.active_buckets.add(bucket_id)
            
            restart_success = self.start_adaptive_learning_test(bucket_id, original_target_weight, fine_flow_rate)
            
            if restart_success:
                success_msg = f"料斗{bucket_id}物料不足已恢复，自适应学习测定重新启动成功"
                return True, success_msg
            else:
                error_msg = f"料斗{bucket_id}自适应学习测定重新启动失败"
                return False, error_msg
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足继续操作异常: {str(e)}"
            return False, error_msg
    
    def handle_material_shortage_cancel(self) -> Tuple[bool, str]:
        try:
            self.stop_all_adaptive_learning_test()
            
            cancel_success = self.monitoring_service.handle_material_shortage_cancel()
            
            success_msg = "✅ 已取消生产，所有自适应学习测定已停止，准备返回AI模式自适应自学习界面"
            
            return cancel_success, success_msg
            
        except Exception as e:
            error_msg = f"处理取消生产操作异常: {str(e)}"
            return False, error_msg
    
    def stop_bucket_adaptive_learning_test(self, bucket_id: int):
        try:
            with self.lock:
                if bucket_id in self.bucket_states:
                    state = self.bucket_states[bucket_id]
                    if state.is_testing:
                        state.is_testing = False
                
                self.active_buckets.discard(bucket_id)
            
            self.monitoring_service.stop_bucket_monitoring(bucket_id)
            
            success = self._stop_bucket_with_mutex_protection(bucket_id)
            
        except Exception as e:
            pass
    
    def stop_all_adaptive_learning_test(self):
        try:
            with self.lock:
                for state in self.bucket_states.values():
                    state.is_testing = False
                
                self.active_buckets.clear()
            
            self.monitoring_service.set_material_check_enabled(False)
            
            self.monitoring_service.stop_all_monitoring()
            
        except Exception as e:
            pass
    
    def get_bucket_state(self, bucket_id: int) -> Optional[BucketAdaptiveLearningState]:
        with self.lock:
            return self.bucket_states.get(bucket_id)
    
    def _update_progress(self, bucket_id: int, current_progress: int, max_progress: int, message: str):
        if self.on_progress_update:
            try:
                self.on_progress_update(bucket_id, current_progress, max_progress, message)
            except Exception as e:
                pass
    
    def _log(self, message: str):
        if self.on_log_message:
            try:
                self.on_log_message(message)
            except Exception as e:
                pass
    
    def _on_monitoring_log(self, message: str):
        self._log(f"[自适应学习监测] {message}")
    
    def dispose(self):
        try:
            self.stop_all_adaptive_learning_test()
            self.monitoring_service.dispose()
        except Exception as e:
            pass

def create_adaptive_learning_controller(modbus_client: ModbusClient) -> AdaptiveLearningController:
    return AdaptiveLearningController(modbus_client)