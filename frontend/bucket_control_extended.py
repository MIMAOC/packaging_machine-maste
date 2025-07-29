#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展的料斗控制模块
提供批量和单独的料斗控制功能，专用于快加时间测定

作者：AI助手
创建日期：2025-07-23
"""

import time
import logging
from typing import List, Tuple
from modbus_client import ModbusClient
from plc_addresses import (
    BUCKET_CONTROL_ADDRESSES,
    COARSE_TIME_MONITORING_ADDRESSES,
    get_bucket_control_address,
    get_coarse_time_monitoring_address
)

class BucketControlExtended:
    """
    扩展的料斗控制类
    提供批量启动、单独停止、单独放料等功能
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化扩展料斗控制
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def start_all_buckets_with_mutex_protection(self) -> Tuple[bool, str]:
        """
        一次性启动所有6个料斗（带互斥保护）
        先写入停止=0的互斥保护，然后写入6个斗的启动=1命令
        
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self.logger.info("开始执行6个料斗批量启动（带互斥保护）")
            
            # 步骤1: 先发送停止=0命令（互斥保护）
            stop_coil_start_address = get_coarse_time_monitoring_address('STOP_COIL_START_ADDRESS')
            stop_commands = [False] * 6  # 6个料斗的停止命令都设为False
            
            success = self.modbus_client.write_multiple_coils(stop_coil_start_address, stop_commands)
            if not success:
                error_msg = "发送停止=0命令（互斥保护）失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info("已发送停止=0命令（互斥保护）")
            
            # 步骤2: 等待50ms确保互斥保护生效
            time.sleep(0.05)
            
            # 步骤3: 发送启动=1命令
            start_coil_start_address = get_coarse_time_monitoring_address('START_COIL_START_ADDRESS')
            start_commands = [True] * 6  # 6个料斗的启动命令都设为True
            
            success = self.modbus_client.write_multiple_coils(start_coil_start_address, start_commands)
            if not success:
                error_msg = "发送启动=1命令失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            success_msg = "✅ 6个料斗批量启动成功（带互斥保护）"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"6个料斗批量启动异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def stop_single_bucket_with_mutex_protection(self, bucket_id: int) -> Tuple[bool, str]:
        """
        停止单个料斗（带互斥保护）
        先发送启动=0命令（互斥保护），然后发送停止=1命令
        
        Args:
            bucket_id (int): 料斗ID (1-6)
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            if bucket_id < 1 or bucket_id > 6:
                return False, f"无效的料斗ID: {bucket_id}，有效范围: 1-6"
            
            self.logger.info(f"开始停止料斗{bucket_id}（带互斥保护）")
            
            # 获取该料斗的控制地址
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            # 步骤1: 先发送启动=0命令（互斥保护）
            success = self.modbus_client.write_coil(start_address, False)
            if not success:
                error_msg = f"料斗{bucket_id}发送启动=0命令（互斥保护）失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 步骤2: 等待50ms确保互斥保护生效
            time.sleep(0.05)
            
            # 步骤3: 发送停止=1命令
            success = self.modbus_client.write_coil(stop_address, True)
            if not success:
                error_msg = f"料斗{bucket_id}发送停止=1命令失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            success_msg = f"✅ 料斗{bucket_id}停止成功（带互斥保护）"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"停止料斗{bucket_id}异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def discharge_single_bucket(self, bucket_id: int) -> Tuple[bool, str]:
        """
        单个料斗放料操作
        发送放料=1命令，延迟1.5s后发送放料=0命令
        
        Args:
            bucket_id (int): 料斗ID (1-6)
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            if bucket_id < 1 or bucket_id > 6:
                return False, f"无效的料斗ID: {bucket_id}，有效范围: 1-6"
            
            self.logger.info(f"开始料斗{bucket_id}放料操作")
            
            # 获取该料斗的放料地址
            discharge_address = get_bucket_control_address(bucket_id, 'DischargeAddress')
            
            # 步骤1: 发送放料=1命令
            success = self.modbus_client.write_coil(discharge_address, True)
            if not success:
                error_msg = f"料斗{bucket_id}发送放料=1命令失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info(f"料斗{bucket_id}已发送放料=1命令，等待1.5秒...")
            
            # 步骤2: 延迟1.5秒
            time.sleep(1.5)
            
            # 步骤3: 发送放料=0命令
            success = self.modbus_client.write_coil(discharge_address, False)
            if not success:
                error_msg = f"料斗{bucket_id}发送放料=0命令失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            success_msg = f"✅ 料斗{bucket_id}放料操作完成"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}放料操作异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def restart_single_bucket(self, bucket_id: int) -> Tuple[bool, str]:
        """
        重新启动单个料斗
        先确保停止=0，然后发送启动=1命令
        
        Args:
            bucket_id (int): 料斗ID (1-6)
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            if bucket_id < 1 or bucket_id > 6:
                return False, f"无效的料斗ID: {bucket_id}，有效范围: 1-6"
            
            self.logger.info(f"开始重新启动料斗{bucket_id}")
            
            # 获取该料斗的控制地址
            start_address = get_bucket_control_address(bucket_id, 'StartAddress')
            stop_address = get_bucket_control_address(bucket_id, 'StopAddress')
            
            # 步骤1: 确保停止=0
            success = self.modbus_client.write_coil(stop_address, False)
            if not success:
                error_msg = f"料斗{bucket_id}设置停止=0失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 步骤2: 等待50ms
            time.sleep(0.05)
            
            # 步骤3: 发送启动=1命令
            success = self.modbus_client.write_coil(start_address, True)
            if not success:
                error_msg = f"料斗{bucket_id}发送启动=1命令失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            success_msg = f"✅ 料斗{bucket_id}重新启动成功"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"重新启动料斗{bucket_id}异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def stop_all_buckets(self) -> Tuple[bool, str]:
        """
        停止所有料斗
        
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self.logger.info("开始停止所有料斗")
            
            # 步骤1: 先发送启动=0命令（互斥保护）
            start_coil_start_address = get_coarse_time_monitoring_address('START_COIL_START_ADDRESS')
            start_commands = [False] * 6  # 6个料斗的启动命令都设为False
            
            success = self.modbus_client.write_multiple_coils(start_coil_start_address, start_commands)
            if not success:
                error_msg = "发送启动=0命令（互斥保护）失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 步骤2: 等待50ms
            time.sleep(0.05)
            
            # 步骤3: 发送停止=1命令
            stop_coil_start_address = get_coarse_time_monitoring_address('STOP_COIL_START_ADDRESS')
            stop_commands = [True] * 6  # 6个料斗的停止命令都设为True
            
            success = self.modbus_client.write_multiple_coils(stop_coil_start_address, stop_commands)
            if not success:
                error_msg = "发送停止=1命令失败"
                self.logger.error(error_msg)
                return False, error_msg
            
            success_msg = "✅ 所有料斗停止操作完成"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"停止所有料斗异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def execute_bucket_stop_and_discharge_sequence(self, bucket_id: int) -> Tuple[bool, str]:
        """
        执行料斗停止和放料序列操作
        包括：停止料斗（带互斥保护）-> 延迟500ms -> 放料操作
        
        Args:
            bucket_id (int): 料斗ID (1-6)
            
        Returns:
            Tuple[bool, str]: (是否成功, 操作消息)
        """
        try:
            self.logger.info(f"开始执行料斗{bucket_id}停止和放料序列")
            
            # 步骤1: 停止料斗（带互斥保护）
            stop_success, stop_msg = self.stop_single_bucket_with_mutex_protection(bucket_id)
            if not stop_success:
                return False, f"停止料斗失败: {stop_msg}"
            
            # 步骤2: 延迟500ms
            self.logger.info(f"料斗{bucket_id}已停止，等待500ms后放料")
            time.sleep(0.5)
            
            # 步骤3: 放料操作
            discharge_success, discharge_msg = self.discharge_single_bucket(bucket_id)
            if not discharge_success:
                return False, f"放料操作失败: {discharge_msg}"
            
            success_msg = f"✅ 料斗{bucket_id}停止和放料序列操作完成"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"料斗{bucket_id}停止和放料序列异常: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

def create_bucket_control_extended(modbus_client: ModbusClient) -> BucketControlExtended:
    """
    创建扩展料斗控制实例的工厂函数
    
    Args:
        modbus_client (ModbusClient): Modbus客户端实例
        
    Returns:
        BucketControlExtended: 扩展料斗控制实例
    """
    return BucketControlExtended(modbus_client)

# 示例使用
if __name__ == "__main__":
    from modbus_client import create_modbus_client
    
    # 创建Modbus客户端并连接
    client = create_modbus_client()
    success, message = client.connect()
    print(f"连接状态: {success} - {message}")
    
    if success:
        # 创建扩展料斗控制实例
        bucket_control = create_bucket_control_extended(client)
        
        # 测试批量启动
        print("\n测试批量启动所有料斗...")
        success, msg = bucket_control.start_all_buckets_with_mutex_protection()
        print(f"批量启动结果: {success} - {msg}")
        
        # 等待一段时间
        time.sleep(2)
        
        # 测试单个料斗停止和放料
        print("\n测试料斗1停止和放料...")
        success, msg = bucket_control.execute_bucket_stop_and_discharge_sequence(1)
        print(f"停止和放料结果: {success} - {msg}")
        
        # 测试重新启动
        print("\n测试重新启动料斗1...")
        success, msg = bucket_control.restart_single_bucket(1)
        print(f"重新启动结果: {success} - {msg}")
        
        # 等待一段时间后停止所有料斗
        time.sleep(2)
        print("\n停止所有料斗...")
        success, msg = bucket_control.stop_all_buckets()
        print(f"停止所有料斗结果: {success} - {msg}")
        
        # 断开连接
        client.disconnect()