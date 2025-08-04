#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC高级操作模块
提供包装机相关的PLC操作功能

作者：AI助手
创建日期：2025-07-23
"""

import time
import logging
from typing import Tuple, List, Dict, Optional
from modbus_client import ModbusClient
from plc_addresses import (
    BUCKET_PARAMETER_ADDRESSES,
    BUCKET_MONITORING_ADDRESSES,
    GLOBAL_CONTROL_ADDRESSES,
    get_all_bucket_weight_addresses
)

class PLCOperations:
    """
    PLC操作类
    提供包装机相关的高级PLC操作功能
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化PLC操作类
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def read_all_bucket_weights(self) -> Tuple[bool, Dict[int, float], str]:
        """
        读取所有料斗的实时重量
        
        Returns:
            Tuple[bool, Dict[int, float], str]: (是否成功, 重量字典{料斗ID: 重量}, 消息)
        """
        try:
            weights = {}
            has_weight_above_zero = False
            
            self.logger.info("开始读取所有料斗的实时重量")
            
            # 逐个读取每个料斗的重量
            for bucket_id in range(1, 7):
                weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
                
                # 读取原始重量值
                raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                
                if raw_weight_data is not None and len(raw_weight_data) > 0:
                    # 重量值需要除以10（根据需求：读取需要÷10）
                    weight_value = raw_weight_data[0] / 10.0
                    weights[bucket_id] = weight_value
                    
                    if weight_value > 0:
                        has_weight_above_zero = True
                    
                    self.logger.debug(f"料斗{bucket_id}重量: {weight_value}g")
                else:
                    self.logger.error(f"读取料斗{bucket_id}重量失败")
                    return False, {}, f"读取料斗{bucket_id}重量失败"
            
            success_msg = f"成功读取所有料斗重量，{'有' if has_weight_above_zero else '无'}料斗重量>0g"
            self.logger.info(success_msg)
            
            return True, weights, success_msg
            
        except Exception as e:
            error_msg = f"读取料斗重量异常: {str(e)}"
            self.logger.error(error_msg)
            return False, {}, error_msg
    
    def check_any_bucket_has_weight(self) -> Tuple[bool, bool, str]:
        """
        检查是否有任何料斗重量大于0g
        
        Returns:
            Tuple[bool, bool, str]: (操作是否成功, 是否有重量>0g, 消息)
        """
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
        """
        执行放料和清零序列操作
        
        操作流程：
        1. 总停止=1
        2. 总放料=1
        3. 延迟1.5秒
        4. 总放料=0
        5. 总清零=1
        6. 延迟100ms
        7. 总清零=0
        8. 总停止=0
        
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self.logger.info("开始执行放料和清零序列操作")
            
            # 1. 总停止=1
            self.logger.info("步骤1: 发送总启0命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False):
                return False, "发送总启动命令失败"
            
            # 1. 总停止=1
            self.logger.info("步骤1: 发送总停止命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True):
                return False, "发送总停止命令失败"
            
            # 2. 总放料=1
            self.logger.info("步骤2: 发送总放料开始命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalDischarge'], True):
                return False, "发送总放料开始命令失败"
            
            # 3. 延迟1.5秒
            self.logger.info("步骤3: 等待1.5秒放料完成")
            time.sleep(1.5)
            
            # 4. 总放料=0
            self.logger.info("步骤4: 发送总放料停止命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalDischarge'], False):
                return False, "发送总放料停止命令失败"
            # 延迟1秒
            time.sleep(1)
            
            # 5. 总清零=1
            self.logger.info("步骤5: 发送总清零开始命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClear'], True):
                return False, "发送总清零开始命令失败"
            
            # 6. 延迟100ms
            self.logger.info("步骤6: 等待100ms清零完成")
            time.sleep(1)
            
            # 7. 总清零=0
            self.logger.info("步骤7: 发送总清零停止命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalClear'], False):
                return False, "发送总清零停止命令失败"
            
            # 8. 总停止=0
            self.logger.info("步骤8: 取消总停止命令")
            if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False):
                return False, "取消总停止命令失败"
            
            success_msg = "✅ 放料和清零序列操作执行成功"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"❌ 放料和清零序列操作异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def write_bucket_parameters_all(self, target_weight: float, coarse_speed: int, 
                                  fine_speed: int = 44, coarse_advance: int = 0, 
                                  fall_value: int = 0) -> Tuple[bool, str]:
        """
        将参数写入所有料斗的PLC地址
        
        Args:
            target_weight (float): 目标重量（克）
            coarse_speed (int): 快加速度
            fine_speed (int): 慢加速度，默认44
            coarse_advance (int): 快加提前量，默认0
            fall_value (int): 落差值，默认0
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self.logger.info(f"开始向所有料斗写入参数: 目标重量={target_weight}g, 快加速度={coarse_speed}, 慢加速度={fine_speed}")
            
            # 重量值需要乘以10（根据需求：重量值写入需要×10）
            target_weight_plc = int(target_weight * 10)
            
            write_results = []
            
            # 遍历所有料斗
            for bucket_id in range(1, 7):
                bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                self.logger.info(f"正在写入料斗{bucket_id}参数...")
                
                # 写入目标重量
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['TargetWeight'], target_weight_plc):
                    error_msg = f"料斗{bucket_id}目标重量写入失败"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 写入快加速度
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['CoarseSpeed'], coarse_speed):
                    error_msg = f"料斗{bucket_id}快加速度写入失败"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 写入慢加速度
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['FineSpeed'], fine_speed):
                    error_msg = f"料斗{bucket_id}慢加速度写入失败"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 写入快加提前量
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['CoarseAdvance'], coarse_advance):
                    error_msg = f"料斗{bucket_id}快加提前量写入失败"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 写入落差值
                if not self.modbus_client.write_holding_register(
                    bucket_addresses['FallValue'], fall_value):
                    error_msg = f"料斗{bucket_id}落差值写入失败"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                write_results.append(f"料斗{bucket_id}: ✓")
                self.logger.info(f"料斗{bucket_id}参数写入完成")
            
            success_msg = (f"✅ 所有料斗参数写入成功\n"
                          f"目标重量: {target_weight}g (PLC值: {target_weight_plc})\n"
                          f"快加速度: {coarse_speed}\n"
                          f"慢加速度: {fine_speed}\n"
                          f"快加提前量: {coarse_advance}\n"
                          f"落差值: {fall_value}\n"
                          f"写入详情: {', '.join(write_results)}")
            
            self.logger.info("所有料斗参数写入成功")
            return True, success_msg
            
        except Exception as e:
            error_msg = f"❌ 写入料斗参数异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def read_bucket_parameters(self, bucket_id: int) -> Tuple[bool, Dict[str, float], str]:
        """
        读取指定料斗的所有参数
        
        Args:
            bucket_id (int): 料斗ID (1-6)
            
        Returns:
            Tuple[bool, Dict[str, float], str]: (是否成功, 参数字典, 消息)
        """
        try:
            if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                return False, {}, f"无效的料斗ID: {bucket_id}"
            
            bucket_addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
            parameters = {}
            
            self.logger.info(f"读取料斗{bucket_id}参数")
            
            # 读取目标重量
            target_weight_data = self.modbus_client.read_holding_registers(
                bucket_addresses['TargetWeight'], 1)
            if target_weight_data:
                # 重量值需要除以10
                parameters['TargetWeight'] = target_weight_data[0] / 10.0
            
            # 读取快加速度
            coarse_speed_data = self.modbus_client.read_holding_registers(
                bucket_addresses['CoarseSpeed'], 1)
            if coarse_speed_data:
                parameters['CoarseSpeed'] = coarse_speed_data[0]
            
            # 读取慢加速度
            fine_speed_data = self.modbus_client.read_holding_registers(
                bucket_addresses['FineSpeed'], 1)
            if fine_speed_data:
                parameters['FineSpeed'] = fine_speed_data[0]
            
            # 读取快加提前量
            coarse_advance_data = self.modbus_client.read_holding_registers(
                bucket_addresses['CoarseAdvance'], 1)
            if coarse_advance_data:
                parameters['CoarseAdvance'] = coarse_advance_data[0]
            
            # 读取落差值
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
            self.logger.error(error_msg)
            return False, {}, error_msg

def create_plc_operations(modbus_client: ModbusClient) -> PLCOperations:
    """
    创建PLC操作实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        PLCOperations: PLC操作实例
    """
    return PLCOperations(modbus_client)

# 示例使用
if __name__ == "__main__":
    from modbus_client import create_modbus_client
    
    # 创建Modbus客户端并连接
    client = create_modbus_client()
    success, message = client.connect()
    print(f"连接状态: {success} - {message}")
    
    if success:
        # 创建PLC操作实例
        plc_ops = create_plc_operations(client)
        
        # 测试读取料斗重量
        weight_success, weights, weight_msg = plc_ops.read_all_bucket_weights()
        print(f"读取重量: {weight_success} - {weight_msg}")
        if weight_success:
            for bucket_id, weight in weights.items():
                print(f"  料斗{bucket_id}: {weight}g")
        
        # 断开连接
        client.disconnect()