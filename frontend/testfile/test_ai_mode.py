#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模式界面测试文件
用于验证ai_mode_interface.py的基本功能
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_imports():
    """测试基本导入"""
    print("正在测试导入...")
    
    try:
        # 测试导入AI模式界面类
        from ai_mode_interface import AIModeInterface
        print("✅ 成功导入 AIModeInterface")
        
        # 测试辅助类导入
        from ai_mode_interface import DialogManager, InputValidator, DeviceStatusChecker
        print("✅ 成功导入辅助类")
        
        return True, "所有导入测试通过"
        
    except ImportError as e:
        return False, f"导入失败: {e}"
    except Exception as e:
        return False, f"导入异常: {e}"

def test_class_creation():
    """测试类创建"""
    print("正在测试类创建...")
    
    try:
        # 创建模拟的主窗口
        class MockMainWindow:
            def __init__(self):
                self.root = tk.Tk()
                self.root.withdraw()  # 隐藏窗口
                self.modbus_client = MockModbusClient()
            
            def show_main_window(self):
                pass
        
        class MockModbusClient:
            def __init__(self):
                self.is_connected = True
            
            def write_coil(self, address, value):
                return True
                
            def write_register(self, address, value):
                return True
        
        # 创建模拟主窗口
        mock_main = MockMainWindow()
        
        # 测试AI模式界面创建
        from ai_mode_interface import AIModeInterface
        ai_interface = AIModeInterface(parent=None, main_window=mock_main)
        
        print("✅ 成功创建 AIModeInterface 实例")
        
        # 清理
        ai_interface.root.destroy()
        mock_main.root.destroy()
        
        return True, "类创建测试通过"
        
    except Exception as e:
        return False, f"类创建失败: {e}"

def test_helper_classes():
    """测试辅助类功能"""
    print("正在测试辅助类...")
    
    try:
        from ai_mode_interface import DialogManager, InputValidator, DeviceStatusChecker
        
        # 创建临时根窗口
        temp_root = tk.Tk()
        temp_root.withdraw()
        
        # 测试DialogManager
        dialog_manager = DialogManager(temp_root)
        print("✅ DialogManager 创建成功")
        
        # 测试InputValidator
        valid, result = InputValidator.validate_weight("100.5")
        if valid and result == 100.5:
            print("✅ InputValidator.validate_weight 测试通过")
        else:
            print("❌ InputValidator.validate_weight 测试失败")
        
        valid, result = InputValidator.validate_quantity("50")
        if valid and result == 50:
            print("✅ InputValidator.validate_quantity 测试通过")
        else:
            print("❌ InputValidator.validate_quantity 测试失败")
        
        # 测试DeviceStatusChecker
        class MockClient:
            is_connected = True
        
        checker = DeviceStatusChecker(MockClient())
        print("✅ DeviceStatusChecker 创建成功")
        
        # 清理
        temp_root.destroy()
        
        return True, "辅助类测试通过"
        
    except Exception as e:
        return False, f"辅助类测试失败: {e}"

def main():
    """主测试函数"""
    print("=" * 60)
    print("AI模式界面测试程序")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_imports),
        ("类创建测试", test_class_creation), 
        ("辅助类测试", test_helper_classes)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 运行 {test_name}...")
        try:
            success, message = test_func()
            results.append((test_name, success, message))
            
            if success:
                print(f"✅ {test_name}: {message}")
            else:
                print(f"❌ {test_name}: {message}")
                
        except Exception as e:
            error_msg = f"测试异常: {e}"
            results.append((test_name, False, error_msg))
            print(f"❌ {test_name}: {error_msg}")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, success, message in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {test_name}: {message}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 总计: {passed + failed} 个测试，{passed} 个通过，{failed} 个失败")
    
    if failed == 0:
        print("🎉 所有测试通过！AI模式界面代码基本正常。")
        return 0
    else:
        print("⚠️ 有测试失败，请检查相关问题。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试程序异常: {e}")
        sys.exit(1)
