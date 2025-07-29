#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus TCP连接测试脚本
用于快速验证修正后的Modbus客户端是否能正确连接信捷PLC

使用方法：
1. 确保PLC已经启动并连接到网络
2. 运行此脚本: python modbus_test.py
3. 观察输出结果，找到正确的unit_id

作者：AI助手
创建日期：2025-07-25
"""

import sys
import time
from typing import Dict, Any

# 导入修正后的modbus客户端
try:
    # 如果是单独运行此脚本，需要确保modbus_client.py在同一目录
    from modbus_client import create_modbus_client, ModbusClient
    print("✅ 成功导入修正后的Modbus客户端模块")
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保修正后的modbus_client.py文件在同一目录下")
    sys.exit(1)

def detailed_connection_test(host: str = "192.168.6.6", port: int = 502, unit_id: int = 1) -> Dict[str, Any]:
    """
    详细的连接测试，包含多种读写操作
    
    Args:
        host: PLC IP地址
        port: Modbus端口
        unit_id: 从站地址
        
    Returns:
        测试结果字典
    """
    print(f"\n{'='*50}")
    print(f"详细测试 unit_id = {unit_id}")
    print(f"{'='*50}")
    
    result = {
        'unit_id': unit_id,
        'connection_success': False,
        'tests': {}
    }
    
    # 创建客户端
    client = create_modbus_client(host=host, port=port, timeout=3, unit_id=unit_id)
    
    # 1. 连接测试
    print("1. 正在测试连接...")
    success, message = client.connect()
    result['connection_success'] = success
    
    if not success:
        print(f"❌ 连接失败: {message.split('可能原因')[0].strip()}")
        return result
    
    print(f"✅ 连接成功！unit_id={unit_id}")
    
    # 2. 保持寄存器读取测试
    print("\n2. 测试保持寄存器读取...")
    test_addresses = [0, 1, 100, 40001, 400001]
    holding_register_results = {}
    
    for addr in test_addresses:
        try:
            data = client.read_holding_registers(address=addr, count=1)
            if data is not None:
                holding_register_results[addr] = {'success': True, 'data': data[0]}
                print(f"   地址 {addr}: ✅ 成功，值 = {data[0]}")
            else:
                holding_register_results[addr] = {'success': False, 'data': None}
                print(f"   地址 {addr}: ❌ 失败")
        except Exception as e:
            holding_register_results[addr] = {'success': False, 'error': str(e)}
            print(f"   地址 {addr}: ❌ 异常 - {e}")
    
    result['tests']['holding_registers'] = holding_register_results
    
    # 3. 线圈读取测试
    print("\n3. 测试线圈读取...")
    coil_addresses = [0, 1, 100, 191]
    coil_results = {}
    
    for addr in coil_addresses:
        try:
            data = client.read_coils(address=addr, count=1)
            if data is not None:
                coil_results[addr] = {'success': True, 'data': data[0]}
                print(f"   线圈 {addr}: ✅ 成功，状态 = {data[0]}")
            else:
                coil_results[addr] = {'success': False, 'data': None}
                print(f"   线圈 {addr}: ❌ 失败")
        except Exception as e:
            coil_results[addr] = {'success': False, 'error': str(e)}
            print(f"   线圈 {addr}: ❌ 异常 - {e}")
    
    result['tests']['coils'] = coil_results
    
    # 4. 批量读取测试
    print("\n4. 测试批量读取...")
    try:
        batch_data = client.read_holding_registers(address=0, count=10)
        if batch_data is not None:
            result['tests']['batch_read'] = {'success': True, 'count': len(batch_data)}
            print(f"   批量读取: ✅ 成功读取 {len(batch_data)} 个寄存器")
            print(f"   数据预览: {batch_data[:5]}...")
        else:
            result['tests']['batch_read'] = {'success': False}
            print(f"   批量读取: ❌ 失败")
    except Exception as e:
        result['tests']['batch_read'] = {'success': False, 'error': str(e)}
        print(f"   批量读取: ❌ 异常 - {e}")
    
    # 5. 写入测试（可选，谨慎执行）
    print("\n5. 测试写入操作（注意：会修改PLC数据）...")
    write_test_confirmed = input("   是否执行写入测试？这会修改PLC寄存器值 (y/N): ").lower().strip()
    
    if write_test_confirmed == 'y':
        try:
            # 先读取当前值
            original_value = client.read_holding_registers(address=100, count=1)
            if original_value is not None:
                original_val = original_value[0]
                test_value = (original_val + 1) % 65536  # 确保值在有效范围内
                
                # 写入测试值
                write_success = client.write_holding_register(address=100, value=test_value)
                if write_success:
                    # 读取验证
                    new_value = client.read_holding_registers(address=100, count=1)
                    if new_value and new_value[0] == test_value:
                        print(f"   写入测试: ✅ 成功！ {original_val} -> {test_value}")
                        result['tests']['write'] = {'success': True}
                        
                        # 恢复原值
                        client.write_holding_register(address=100, value=original_val)
                        print(f"   已恢复原值: {original_val}")
                    else:
                        print(f"   写入测试: ❌ 写入成功但验证失败")
                        result['tests']['write'] = {'success': False, 'reason': 'verification_failed'}
                else:
                    print(f"   写入测试: ❌ 写入失败")
                    result['tests']['write'] = {'success': False, 'reason': 'write_failed'}
            else:
                print(f"   写入测试: ❌ 无法读取原始值")
                result['tests']['write'] = {'success': False, 'reason': 'read_original_failed'}
        except Exception as e:
            print(f"   写入测试: ❌ 异常 - {e}")
            result['tests']['write'] = {'success': False, 'error': str(e)}
    else:
        print("   写入测试: 已跳过")
        result['tests']['write'] = {'success': None, 'reason': 'skipped'}
    
    # 断开连接
    client.disconnect()
    print(f"\n✅ unit_id={unit_id} 的详细测试完成")
    
    return result

def quick_scan_unit_ids(host: str = "192.168.6.6", port: int = 502) -> Dict[int, bool]:
    """
    快速扫描常见的unit_id值
    """
    print(f"\n{'='*60}")
    print(f"快速扫描 {host}:{port} 的可用 unit_id")
    print(f"{'='*60}")
    
    # 扩展的unit_id测试范围
    unit_ids_to_test = [0, 1, 2, 3, 10, 16, 17, 20, 100, 247, 255]
    results = {}
    
    for unit_id in unit_ids_to_test:
        print(f"测试 unit_id = {unit_id:3d}...", end=" ")
        
        client = create_modbus_client(host=host, port=port, timeout=2, unit_id=unit_id)
        success, _ = client.connect()
        results[unit_id] = success
        
        if success:
            print("✅ 成功")
            client.disconnect()
        else:
            print("❌ 失败")
        
        # 小延迟避免过快连接
        time.sleep(0.1)
    
    return results

def main():
    """主测试函数"""
    print("=" * 60)
    print("信捷PLC Modbus TCP连接测试工具")
    print("=" * 60)
    print("此工具将帮助您找到正确的unit_id参数")
    
    # 获取PLC连接信息
    host = input("请输入PLC IP地址 (默认: 192.168.6.6): ").strip()
    if not host:
        host = "192.168.6.6"
    
    port_input = input("请输入Modbus端口 (默认: 502): ").strip()
    port = 502
    if port_input:
        try:
            port = int(port_input)
        except ValueError:
            print("端口号无效，使用默认值502")
    
    print(f"\n目标PLC: {host}:{port}")
    
    # 选择测试模式
    print("\n请选择测试模式:")
    print("1. 快速扫描 - 快速测试常见unit_id值")
    print("2. 详细测试 - 对指定unit_id进行全面测试")
    print("3. 两者都执行")
    
    choice = input("请选择 (1/2/3, 默认: 1): ").strip()
    if not choice:
        choice = "1"
    
    successful_unit_ids = []
    
    # 执行测试
    if choice in ["1", "3"]:
        # 快速扫描
        scan_results = quick_scan_unit_ids(host, port)
        successful_unit_ids = [uid for uid, success in scan_results.items() if success]
        
        print(f"\n快速扫描结果:")
        print(f"成功的unit_id: {successful_unit_ids}")
        
        if not successful_unit_ids:
            print("❌ 没有找到可用的unit_id")
            print("\n可能的原因:")
            print("1. PLC未正确启动或网络连接问题")
            print("2. Modbus TCP服务未在PLC上启用")
            print("3. IP地址或端口配置错误")
            print("4. 需要尝试其他unit_id值")
            return
    
    if choice in ["2", "3"]:
        # 详细测试
        if choice == "3" and successful_unit_ids:
            # 如果已经扫描过，选择第一个成功的unit_id进行详细测试
            test_unit_id = successful_unit_ids[0]
            print(f"\n将对找到的第一个可用unit_id ({test_unit_id}) 进行详细测试")
        else:
            # 手动输入unit_id
            unit_id_input = input("请输入要详细测试的unit_id (默认: 1): ").strip()
            test_unit_id = 1
            if unit_id_input:
                try:
                    test_unit_id = int(unit_id_input)
                except ValueError:
                    print("unit_id无效，使用默认值1")
        
        detailed_result = detailed_connection_test(host, port, test_unit_id)
        
        if detailed_result['connection_success']:
            print(f"\n🎯 推荐配置:")
            print(f"   host = \"{host}\"")
            print(f"   port = {port}")
            print(f"   unit_id = {test_unit_id}")
            
            print(f"\n📝 在您的main.py中，请修改create_modbus_client调用:")
            print(f"   self.modbus_client = create_modbus_client(")
            print(f"       host=\"{host}\",")
            print(f"       port={port},")
            print(f"       timeout=3,")
            print(f"       unit_id={test_unit_id}")
            print(f"   )")
    
    # 总结
    print(f"\n{'='*60}")
    print("测试完成！")
    
    if successful_unit_ids:
        print(f"✅ 找到可用的unit_id: {successful_unit_ids}")
        print(f"🔧 修改建议: 在modbus_client代码中使用unit_id={successful_unit_ids[0]}")
    else:
        print("❌ 未找到可用的unit_id")
        print("🔧 故障排查建议:")
        print("   1. 检查PLC是否启动并配置了Modbus TCP")
        print("   2. 验证网络连接和IP地址")
        print("   3. 确认PLC的Modbus TCP端口设置")
        print("   4. 查看PLC手册确认正确的unit_id范围")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        print("请检查网络连接和PLC状态")