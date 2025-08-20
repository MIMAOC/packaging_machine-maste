"""
PLC高级操作模块

作者：C
创建日期：2025-07-23
"""

import time
from typing import Tuple, List, Dict, Optional
from modbus_client import ModbusClient
from plc_addresses import (
    BUCKET_PARAMETER_ADDRESSES,
    BUCKET_MONITORING_ADDRESSES,
    GLOBAL_CONTROL_ADDRESSES,
    COARSE_TIME_MONITORING_ADDRESSES,
    get_all_bucket_weight_addresses
)

class PLCOperations:
    
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client
    
    def read_all_bucket_weights(self) -> Tuple[bool, Dict[int, float], str]:
        try:
            weights = {}
            has_weight_above_zero = False
            
            for bucket_id in range(1, 7):
                weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
                
                raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                
                if raw_weight_data is not None and len(raw_weight_data) > 0:
                    weight_value = raw_weight_data[0] / 10.0
                    weights[bucket_id] = weight_value
                    
                    if weight_value > 0:
                        has_weight_above_zero = True
                else:
                    return False, {}, f"读取料斗{bucket_id}重量失败"
            
            success_msg = f"成功读取所有料斗重量，{'有' if has_weight_above_zero else '无'}料斗重量>0g"
            
            return True, weights, success_msg
            
        except Exception as e:
            error_msg = f"读取料斗重量异常: {str(e)}"
            return False, {}, error_msg
    
    def check_any_bucket_has_weight(self) -> Tuple[bool, bool, str]:
        success, weights, message = self.read_all_bucket_weights()
        
        if not success:
            return False, False, message
        
        has_weight = any(weight > 0 for weight in weights.values())
        
        if has_weight:
            heavy_buckets = [bucket_id for bucket_id, weight in weights.items() if weight > 0]
            result_msg = f"检测到料斗 {heavy_buckets} 有重量，需要执行清料操作"
        else:
            result_msg = "所有料斗重量为0，无需清料"
        
        return True, has_weight, result_msg
    
    def execute_discharge_and_clear_sequence(self) -> Tuple[bool, str]:
        try:
            start_coil_address = COARSE_TIME_MONITORING_ADDRESSES['START_COIL_START_ADDRESS']
            start_values = [False] * 6
            if not self.modbus_client.write_multiple_coils(start_coil_address, start_values):
                return False, "发送所有料斗启动命令失败"
            
            time.sleep(0.05)
            
            stop_coil_address = COARSE_TIME_MONITORING_ADDRESSES['STOP_COIL_START_ADDRESS']
            stop_values = [True] * 6
            if not self.modbus_client.write_multiple_coils(stop_coil_address, stop_values):
                return False, "发送所有料斗停止命令失败"
            
            time.sleep(0.05)
            
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False):
                return False, "发送总启动命令失败"
            
            time.sleep(0.05)
            
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True):
                return False, "发送总停止命令失败"
            
            time.sleep(0.05)
            
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalDischarge'], True):
                return False, "发送总放料开始命令失败"
            
            time.sleep(1.5)
            
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalDischarge'], False):
                return False, "发送总放料停止命令失败"
            time.sleep(1)
            
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClear'], True):
                return False, "发送总清零开始命令失败"
            
            time.sleep(1)
            
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClear'], False):
                return False, "发送总清零停止命令失败"
            
            time.sleep(1)
            
            start_coil_address = COARSE_TIME_MONITORING_ADDRESSES['START_COIL_START_ADDRESS']
            start_values = [False] * 6
            if not self.modbus_client.write_multiple_coils(start_coil_address, start_values):
                return False, "发送所有料斗启动命令失败"
            
            time.sleep(0.05)
            
            stop_coil_address = COARSE_TIME_MONITORING_ADDRESSES['STOP_COIL_START_ADDRESS']
            stop_values = [True] * 6
            if not self.modbus_client.write_multiple_coils(stop_coil_address, stop_values):
                return False, "发送所有料斗停止命令失败"
            
            success_msg = "放料和清零序列操作执行成功"
            return True, success_msg
            
        except Exception as e:
            error_msg = f"放料和清零序列操作异常: {str(e)}"
            return False, error_msg
    
    def write_bucket_parameters_all(self, target_weight: float, coarse_speed: int, 
                                  fine_speed: int = 44, coarse_advance: int = 0, 
                                  fall_value: int = 0) -> Tuple[bool, str]:
        try:
            target_weight_plc = int(target_weight * 10)
            
            write_results = []
            
            for bucket_id in range(1, 7):
                bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['TargetWeight'], target_weight_plc):
                    error_msg = f"料斗{bucket_id}目标重量写入失败"
                    return False, error_msg
                
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['CoarseSpeed'], coarse_speed):
                    error_msg = f"料斗{bucket_id}快加速度写入失败"
                    return False, error_msg
                
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['FineSpeed'], fine_speed):
                    error_msg = f"料斗{bucket_id}慢加速度写入失败"
                    return False, error_msg
                
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['CoarseAdvance'], coarse_advance):
                    error_msg = f"料斗{bucket_id}快加提前量写入失败"
                    return False, error_msg
                
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['FallValue'], fall_value):
                    error_msg = f"料斗{bucket_id}落差值写入失败"
                    return False, error_msg
                
                write_results.append(f"料斗{bucket_id}: ✓")
            
            success_msg = (f"所有料斗参数写入成功\n"
                          f"目标重量: {target_weight}g (PLC值: {target_weight_plc})\n"
                          f"快加速度: {coarse_speed}\n"
                          f"慢加速度: {fine_speed}\n"
                          f"快加提前量: {coarse_advance}\n"
                          f"落差值: {fall_value}\n"
                          f"写入详情: {', '.join(write_results)}")
            
            return True, success_msg
            
        except Exception as e:
            error_msg = f"写入料斗参数异常: {str(e)}"
            return False, error_msg
    
    def read_bucket_parameters(self, bucket_id: int) -> Tuple[bool, Dict[str, float], str]:
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return False, {}, f"无效的料斗ID: {bucket_id}"
            
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            parameters = {}
            
            target_weight_data = self.modbus_client.read_holding_registers(
                bucket_addresses['TargetWeight'], 1)
            if target_weight_data:
                parameters['TargetWeight'] = target_weight_data[0] / 10.0
            
            coarse_speed_data = self.modbus_client.read_holding_registers(
                bucket_addresses['CoarseSpeed'], 1)
            if coarse_speed_data:
                parameters['CoarseSpeed'] = coarse_speed_data[0]
            
            fine_speed_data = self.modbus_client.read_holding_registers(
                bucket_addresses['FineSpeed'], 1)
            if fine_speed_data:
                parameters['FineSpeed'] = fine_speed_data[0]
            
            coarse_advance_data = self.modbus_client.read_holding_registers(
                bucket_addresses['CoarseAdvance'], 1)
            if coarse_advance_data:
                parameters['CoarseAdvance'] = coarse_advance_data[0]
            
            fall_value_data = self.modbus_client.read_holding_registers(
                bucket_addresses['FallValue'], 1)
            if fall_value_data:
                parameters['FallValue'] = fall_value_data[0]
            
            if len(parameters) == 5:
                success_msg = f"成功读取料斗{bucket_id}所有参数"
                return True, parameters, success_msg
            else:
                error_msg = f"料斗{bucket_id}参数读取不完整，只读取到 {len(parameters)}/5 个参数"
                return False, parameters, error_msg
                
        except Exception as e:
            error_msg = f"读取料斗{bucket_id}参数异常: {str(e)}"
            return False, {}, error_msg

def create_plc_operations(modbus_client: ModbusClient) -> PLCOperations:
    return PLCOperations(modbus_client)