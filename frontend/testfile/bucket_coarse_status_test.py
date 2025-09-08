#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
料斗快加状态监测测试文件
每隔20ms监测6个料斗的快加状态数值

使用方法：
python bucket_coarse_status_test.py

作者：AI助手  
创建日期：2025-07-30
"""

import time
import threading
import logging
from datetime import datetime
from typing import List, Optional
from modbus_client import create_modbus_client, ModbusClient
from plc_addresses import get_all_bucket_coarse_add_addresses

class BucketCoarseStatusMonitor:
    """
    料斗快加状态监测器
    每隔20ms读取6个料斗的快加状态并输出
    """
    
    def __init__(self, modbus_client: ModbusClient):
        """
        初始化监测器
        
        Args:
            modbus_client (ModbusClient): Modbus客户端实例
        """
        self.modbus_client = modbus_client
        self.monitoring = False
        self.monitor_thread = None
        self.start_time = None
        self.monitoring_interval = 0.02  # 20ms = 0.02秒
        
        # 获取所有料斗的快加线圈地址
        self.coarse_add_addresses = get_all_bucket_coarse_add_addresses()
        
        # 配置日志
        logging.basicConfig(level=logging.WARNING)  # 只显示警告和错误，减少干扰
        self.logger = logging.getLogger(__name__)
        
        print("=" * 80)
        print("🔍 料斗快加状态监测器")
        print("=" * 80)
        print(f"监测间隔: {self.monitoring_interval * 1000}ms")
        print(f"料斗快加线圈地址: {self.coarse_add_addresses}")
        print("=" * 80)
    
    def read_all_coarse_status(self) -> Optional[List[bool]]:
        """
        读取所有料斗的快加状态
        
        Returns:
            Optional[List[bool]]: 6个料斗的快加状态列表，失败返回None
        """
        try:
            # 使用批量读取方式（地址是连续的：171-176）
            start_address = min(self.coarse_add_addresses)
            count = len(self.coarse_add_addresses)
            
            coil_states = self.modbus_client.read_coils(start_address, count)
            
            if coil_states is not None and len(coil_states) >= count:
                return coil_states[:count]  # 确保只返回6个状态
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"读取快加状态异常: {e}")
            return None
    
    def format_status_output(self, elapsed_ms: int, coarse_states: List[bool]) -> str:
        """
        格式化状态输出
        
        Args:
            elapsed_ms (int): 经过的毫秒数
            coarse_states (List[bool]): 料斗快加状态列表
            
        Returns:
            str: 格式化的输出字符串
        """
        status_parts = []
        for i, state in enumerate(coarse_states, 1):
            status_parts.append(f"料斗{i}={1 if state else 0}")
        
        return f"{elapsed_ms:5d}ms: {', '.join(status_parts)}"
    
    def monitoring_loop(self):
        """
        监测循环线程函数
        """
        self.start_time = time.time()
        print("\n🚀 开始监测...")
        print("时间格式: 经过时间(ms): 料斗1=状态, 料斗2=状态, ...")
        print("-" * 80)
        
        try:
            while self.monitoring:
                # 记录当前时间
                current_time = time.time()
                elapsed_time = current_time - self.start_time
                elapsed_ms = int(elapsed_time * 1000)
                
                # 读取快加状态
                coarse_states = self.read_all_coarse_status()
                
                if coarse_states is not None:
                    # 格式化并输出状态
                    status_line = self.format_status_output(elapsed_ms, coarse_states)
                    print(status_line)
                    
                    # 检查是否有状态变化（可选：高亮显示变化）
                    if hasattr(self, 'last_states') and self.last_states != coarse_states:
                        changes = []
                        for i, (old, new) in enumerate(zip(self.last_states, coarse_states), 1):
                            if old != new:
                                changes.append(f"料斗{i}: {1 if old else 0}→{1 if new else 0}")
                        if changes:
                            print(f"      ⚡ 状态变化: {', '.join(changes)}")
                    
                    self.last_states = coarse_states.copy()
                else:
                    print(f"{elapsed_ms:5d}ms: ❌ 读取失败")
                
                # 等待下次监测
                time.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  监测被用户中断")
        except Exception as e:
            print(f"\n❌ 监测异常: {e}")
        finally:
            self.monitoring = False
            print("🏁 监测结束")
    
    def start_monitoring(self):
        """
        开始监测
        """
        if self.monitoring:
            print("⚠️  监测已在进行中")
            return
        
        if not self.modbus_client.is_connected:
            print("❌ PLC未连接，无法开始监测")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """
        停止监测
        """
        if not self.monitoring:
            print("⚠️  监测未在进行中")
            return
        
        print("\n🛑 正在停止监测...")
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
    
    def run_test(self, duration_seconds: int = 30):
        """
        运行测试指定时间
        
        Args:
            duration_seconds (int): 测试持续时间（秒），默认30秒
        """
        print(f"📊 将监测 {duration_seconds} 秒...")
        
        # 开始监测
        self.start_monitoring()
        
        try:
            # 等待指定时间
            time.sleep(duration_seconds)
        except KeyboardInterrupt:
            print("\n⚡ 用户中断测试")
        finally:
            # 停止监测
            self.stop_monitoring()

def main():
    """
    主函数
    """
    print("正在连接PLC...")
    
    # 创建Modbus客户端
    modbus_client = create_modbus_client(
        host="192.168.6.6",  # 根据实际PLC IP地址调整
        port=502,
        timeout=3,
        slave_id=1
    )
    
    # 连接PLC
    success, message = modbus_client.connect()
    if not success:
        print(f"❌ PLC连接失败: {message}")
        return
    
    print(f"✅ PLC连接成功: {message.split()[0]}")
    
    try:
        # 创建监测器
        monitor = BucketCoarseStatusMonitor(modbus_client)
        
        # 提供用户选择
        print("\n选择测试模式:")
        print("1. 自动测试30秒")
        print("2. 自动测试60秒") 
        print("3. 手动控制 (按Ctrl+C停止)")
        print("4. 自定义时间")
        
        try:
            choice = input("请输入选择 (1-4): ").strip()
            
            if choice == "1":
                monitor.run_test(30)
            elif choice == "2":
                monitor.run_test(60)
            elif choice == "3":
                print("手动控制模式，按 Ctrl+C 停止监测")
                monitor.start_monitoring()
                # 保持运行直到用户中断
                while monitor.monitoring:
                    time.sleep(0.1)
            elif choice == "4":
                duration = int(input("请输入测试时间（秒）: "))
                monitor.run_test(duration)
            else:
                print("无效选择，使用默认30秒测试")
                monitor.run_test(30)
                
        except ValueError:
            print("输入无效，使用默认30秒测试")
            monitor.run_test(30)
        except KeyboardInterrupt:
            print("\n用户中断")
            monitor.stop_monitoring()
    
    finally:
        # 断开PLC连接
        print("\n断开PLC连接...")
        modbus_client.disconnect()
        print("✅ 测试完成")

if __name__ == "__main__":
    main()