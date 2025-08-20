"""
物料清料控制器

作者：C
创建日期：2025-07-24
"""

import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from modbus_client import ModbusClient
from plc_addresses import BUCKET_MONITORING_ADDRESSES, GLOBAL_CONTROL_ADDRESSES

class MaterialCleaningController:
    
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
        
        self.is_cleaning = False
        self.cleaning_start_time = None
        self.stop_cleaning_flag = threading.Event()
        self.cleaning_thread = None
        
        self.weight_readings = []
        self.reading_interval = 3.0
        self.required_readings = 3
        self.weight_threshold = 2.0
        self.zero_threshold = 0.0
        
        self.on_cleaning_completed: Optional[Callable[[], None]] = None
        self.on_cleaning_failed: Optional[Callable[[str], None]] = None
        self.on_log_message: Optional[Callable[[str], None]] = None
    
    def start_cleaning(self) -> Tuple[bool, str]:
        try:
            if self.is_cleaning:
                return False, "清料操作已在进行中"
            
            if not self.modbus_client or not self.modbus_client.is_connected:
                return False, "PLC未连接，无法执行清料操作"
            
            success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClean'], True)
            if not success:
                error_msg = "发送总清料=1命令失败"
                return False, error_msg
            
            self.is_cleaning = True
            self.cleaning_start_time = datetime.now()
            self.weight_readings = []
            self.stop_cleaning_flag.clear()
            
            self.cleaning_thread = threading.Thread(
                target=self._cleaning_monitor_thread,
                daemon=True,
                name="MaterialCleaning"
            )
            self.cleaning_thread.start()
            
            success_msg = "清料操作已启动，正在监测料斗重量变化"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"启动清料操作异常: {str(e)}"
            return False, error_msg
    
    def stop_cleaning(self) -> Tuple[bool, str]:
        try:
            if not self.is_cleaning:
                return True, "清料操作未在进行中"
            
            self.stop_cleaning_flag.set()
            
            if self.cleaning_thread and self.cleaning_thread.is_alive():
                self.cleaning_thread.join(timeout=2.0)
            
            success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClean'], False)
            if not success:
                error_msg = "发送总清料=0命令失败"
                return False, error_msg
            
            self.is_cleaning = False
            self.weight_readings = []
            
            success_msg = "清料操作已停止"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"停止清料操作异常: {str(e)}"
            return False, error_msg
    
    def _cleaning_monitor_thread(self):
        try:
            while not self.stop_cleaning_flag.is_set() and self.is_cleaning:
                bucket_weights = self._read_all_bucket_weights()
                
                if bucket_weights is None:
                    error_msg = "读取料斗重量失败，清料监测中断"
                    self._trigger_cleaning_failed(error_msg)
                    break
                
                self.weight_readings.append(bucket_weights)
                
                if len(self.weight_readings) > self.required_readings:
                    self.weight_readings.pop(0)
                
                if len(self.weight_readings) >= self.required_readings:
                    if self._check_cleaning_completion():
                        self._trigger_cleaning_completed()
                        break
                
                self.stop_cleaning_flag.wait(self.reading_interval)
                
        except Exception as e:
            error_msg = f"清料监测线程异常: {str(e)}"
            self._trigger_cleaning_failed(error_msg)
    
    def _read_all_bucket_weights(self) -> Optional[Dict[int, float]]:
        try:
            bucket_weights = {}
        
            for bucket_id in range(1, 7):
                weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
            
                raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                
                if raw_weight_data is not None and len(raw_weight_data) > 0:
                    weight_value = raw_weight_data[0] / 10.0
                    bucket_weights[bucket_id] = weight_value
                else:
                    return None
            
            return bucket_weights
            
        except Exception as e:
            return None
    
    def _check_cleaning_completion(self) -> bool:
        try:
            if len(self.weight_readings) < self.required_readings:
                return False
            
            weight1 = self.weight_readings[0]
            weight2 = self.weight_readings[1]
            weight3 = self.weight_readings[2]
            
            for bucket_id in range(1, 7):
                w1 = weight1[bucket_id]
                w2 = weight2[bucket_id]
                w3 = weight3[bucket_id]
                
                diff_2_1 = abs(w2 - w1)
                if diff_2_1 > self.weight_threshold:
                    return False
                
                diff_3_2 = abs(w3 - w2)
                if diff_3_2 > self.weight_threshold:
                    return False
                
                if w3 >= self.zero_threshold:
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _trigger_cleaning_completed(self):
        self.is_cleaning = False
        if self.on_cleaning_completed:
            try:
                self.on_cleaning_completed()
            except Exception as e:
                pass
    
    def _trigger_cleaning_failed(self, error_message: str):
        self.is_cleaning = False
        if self.on_cleaning_failed:
            try:
                self.on_cleaning_failed(error_message)
            except Exception as e:
                pass
    
    def _log(self, message: str):
        pass
    
    def get_cleaning_status(self) -> Dict:
        return {
            'is_cleaning': self.is_cleaning,
            'start_time': self.cleaning_start_time,
            'readings_count': len(self.weight_readings),
            'last_weights': self.weight_readings[-1] if self.weight_readings else None
        }
    
    def dispose(self):
        try:
            if self.is_cleaning:
                self.stop_cleaning()
        except Exception as e:
            pass

def create_material_cleaning_controller(modbus_client: ModbusClient) -> MaterialCleaningController:
    return MaterialCleaningController(modbus_client)