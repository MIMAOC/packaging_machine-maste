#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置界面模块
六头线性调节秤系统设置功能实现

功能特点：
1. 密码验证保护（硬编码密码：123456）
2. 9个系统参数设置（左右两列布局）
3. 4个系统控制命令（脉冲控制）
4. 完全复用参数设置界面的成功架构
5. 自适应屏幕尺寸和字体缩放

作者：AI助手
创建日期：2025-08-15
基于参数设置界面架构开发
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any
from touchscreen_utils import TouchScreenUtils

# 导入PLC相关模块
try:
    from traditional_plc_addresses import (
        get_traditional_system_address,
        get_traditional_system_control_address,
        TRADITIONAL_SYSTEM_ADDRESSES,
        TRADITIONAL_SYSTEM_CONTROL_ADDRESSES
    )
    from modbus_client import ModbusClient
except ImportError as e:
    print(f"导入PLC模块失败: {e}")
    print("请确保traditional_plc_addresses.py和modbus_client.py在同一目录下")


class SystemSettingInterface:
    """
    系统设置界面类
    
    提供系统参数设置和系统控制命令功能
    完全复用参数设置界面的成功架构
    """
    
    # 系统密码（硬编码）
    SYSTEM_PASSWORD = "123456"
    
    def __init__(self, modbus_client: Optional[ModbusClient], parent_interface):
        """
        初始化系统设置界面
        
        Args:
            modbus_client: Modbus客户端实例
            parent_interface: 主界面引用
        """
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        
        # 界面状态
        self.is_showing = False
        
        # 字体缩放系数（自适应屏幕）
        self.font_scale = 1.0
        
        # 系统参数数据存储
        self.parameter_data = {}
        
        # 添加触摸屏优化
        TouchScreenUtils.optimize_window_for_touch(self.root)

        # 界面组件引用
        self.parameter_entries = {}  # 参数输入框
        self.control_buttons = {}    # 控制按钮
        
        # 系统参数配置（9个参数）
        self.parameter_configs = {
            'ZeroTrackRange': {'type': 'integer', 'decimals': 0, 'label': '零点追踪范围'},
            'ZeroTrackTime': {'type': 'integer', 'decimals': 0, 'label': '零点追踪时间'},
            'ZeroClearRange': {'type': 'integer', 'decimals': 0, 'label': '清零范围(%)'},
            'StabilityRange': {'type': 'integer', 'decimals': 0, 'label': '判稳范围'},
            'StabilityTime': {'type': 'integer', 'decimals': 0, 'label': '判稳时间'},
            'FilterLevelA': {'type': 'integer', 'decimals': 0, 'label': '滤波等级A'},
            'FilterLevelB': {'type': 'integer', 'decimals': 0, 'label': '滤波等级B'},
            'MinDivision': {'type': 'integer', 'decimals': 0, 'label': '最小分度'},
            'MaxCapacity': {'type': 'integer', 'decimals': 0, 'label': '最大量程'}
        }
        
        # 系统控制命令配置（4个命令）
        self.control_configs = {
            'ModuleInit': {'label': '模块初始化', 'color': '#4a90e2'},
            'FeedDataInit': {'label': '加料数据初始化', 'color': '#4a90e2'},
            'ModuleDataRead': {'label': '模块数据读取', 'color': '#4a90e2'},
            'SystemSave': {'label': '保存', 'color': '#4a90e2'}
        }
        
        # 计算字体缩放
        self.calculate_font_scale()
        
        # 设置字体
        self.setup_fonts()
    
    def setup_window(self):
        """设置窗口基本属性（参考material_management_interface.py）"""
        try:
            # 设置窗口大小（系统设置界面内容较多，使用更大尺寸）
            self.root.geometry("1400x900")
            self.root.configure(bg='white')
            self.root.resizable(True, True)
            
            # 居中显示窗口
            self.center_window()
            
            print("窗口设置完成: 1400x900")
            
        except Exception as e:
            print(f"设置窗口失败: {e}")
    
    def center_window(self):
        """将窗口居中显示（参考material_management_interface.py）"""
        try:
            # 确保窗口已经完全创建
            self.root.update_idletasks()
            
            # 获取窗口尺寸
            width = 1400  # 使用设定的尺寸
            height = 900
            
            # 计算居中位置
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            # 设置窗口位置
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
            print("窗口居中完成")
            
        except Exception as e:
            print(f"窗口居中失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("1400x900")
    
    def calculate_font_scale(self):
        """计算字体缩放系数（智能屏幕检测）"""
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            print(f"检测到屏幕分辨率: {screen_width}x{screen_height}")
            
            if screen_width >= 2560:  # 2K及以上屏幕
                self.font_scale = 1.2
                print("使用2K屏幕字体缩放: 1.2")
            elif screen_width >= 1920:  # 1080P屏幕
                self.font_scale = 1.0
                print("使用1080P屏幕字体缩放: 1.0")
            else:  # 小屏幕
                self.font_scale = 0.8
                print("使用小屏幕字体缩放: 0.8")
                
        except Exception as e:
            print(f"计算字体缩放失败: {e}")
            self.font_scale = 1.0
    
    def setup_fonts(self):
        """设置字体（动态缩放）"""
        try:
            # 动态字体计算（参考HTML原型，增大字体）
            base_title = int(48 * self.font_scale)      # 标题字体
            base_label = int(32 * self.font_scale)      # 标签字体  
            base_entry = int(32 * self.font_scale)      # 输入框字体
            base_button = int(24 * self.font_scale)     # 按钮字体
            
            # 界面字体
            self.title_font = font.Font(family="Microsoft YaHei", size=base_title, weight="bold")
            self.label_font = font.Font(family="Microsoft YaHei", size=base_label, weight="normal")
            self.entry_font = font.Font(family="Arial", size=base_entry, weight="bold")
            self.button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
            self.home_button_font = font.Font(family="Microsoft YaHei", size=int(20 * self.font_scale), weight="bold")
            
            print(f"字体设置完成，缩放系数: {self.font_scale}")
            
        except Exception as e:
            print(f"设置字体失败: {e}")
            # 使用默认字体
            self.title_font = font.Font(family="Microsoft YaHei", size=48, weight="bold")
            self.label_font = font.Font(family="Microsoft YaHei", size=32, weight="normal")
            self.entry_font = font.Font(family="Arial", size=32, weight="bold")
            self.button_font = font.Font(family="Microsoft YaHei", size=24, weight="bold")
            self.home_button_font = font.Font(family="Microsoft YaHei", size=20, weight="bold")
    
    def verify_password(self):
        """
        密码验证
        
        Returns:
            bool: 验证成功返回True，失败返回False
        """
        try:
            # 使用简单对话框获取密码输入
            password = simpledialog.askstring(
                "系统设置密码验证",
                "请输入管理员密码:",
                show='*',  # 密码遮盖
                parent=self.root
            )
            
            if password is None:
                # 用户点击取消
                print("用户取消密码验证")
                return False
            
            if password.strip() == self.SYSTEM_PASSWORD:
                print("密码验证成功")
                messagebox.showinfo("验证成功", "密码验证通过，进入系统设置界面", parent=self.root)
                return True
            else:
                print("密码验证失败")
                messagebox.showerror("验证失败", "密码错误，无法进入系统设置", parent=self.root)
                return False
                
        except Exception as e:
            print(f"密码验证异常: {e}")
            messagebox.showerror("验证异常", f"密码验证过程中发生错误: {e}", parent=self.root)
            return False
    
    def show_interface(self):
        """显示系统设置界面"""
        try:
            # 首先进行密码验证
            if not self.verify_password():
                print("密码验证失败，返回主菜单")
                self.parent.show_menu_interface()
                return
            
            print("开始显示系统设置界面")
            
            # 清空主内容区域
            self.parent.clear_main_content()
            self.is_showing = True
            
            # 创建系统设置界面
            self.create_system_interface()
            
            # 加载系统参数
            self.load_all_parameters()
            
            print("系统设置界面显示完成")
            
        except Exception as e:
            print(f"显示系统设置界面失败: {e}")
            messagebox.showerror("界面错误", f"显示系统设置界面时发生错误: {e}")
            # 发生异常时也返回主菜单
            self.parent.show_menu_interface()
    
    def create_system_interface(self):
        """创建系统设置界面"""
        try:
            # 获取主内容框架
            main_content_frame = self.parent.get_main_content_frame()
            
            # 动态间距计算
            base_padding = int(20 * self.font_scale)
            content_padding = int(60 * self.font_scale)
            element_spacing = int(50 * self.font_scale)  # 增大行间距
            
            # 主容器
            main_container = tk.Frame(main_content_frame, bg='#ffffff')
            main_container.pack(fill=tk.BOTH, expand=True, padx=base_padding, pady=base_padding)
            
            # 创建标题栏
            self.create_title_bar(main_container)
            
            # 创建参数设置区域
            self.create_parameters_area(main_container, element_spacing, content_padding)
            
            # 创建控制按钮区域
            self.create_control_area(main_container)
            
            print("系统设置界面组件创建完成")
            
        except Exception as e:
            print(f"创建系统设置界面失败: {e}")
            raise
    
    def create_title_bar(self, parent):
        """创建标题栏"""
        try:
            # 标题栏容器
            title_frame = tk.Frame(parent, bg='#4a90e2', height=100)
            title_frame.pack(fill=tk.X, pady=(0, int(30 * self.font_scale)))
            title_frame.pack_propagate(False)
            
            # 居中容器（完美居中技术）
            center_container = tk.Frame(title_frame, bg='#4a90e2')
            center_container.grid(row=0, column=0, sticky='')
            
            # 标题文字
            title_label = tk.Label(center_container, text="系统设置",
                                 font=self.title_font, bg='#4a90e2', fg='white')
            title_label.pack()
            
            # 配置grid权重实现居中
            title_frame.grid_rowconfigure(0, weight=1)
            title_frame.grid_columnconfigure(0, weight=1)
            
            # 主页按钮（绝对定位）
            home_button = tk.Button(title_frame, text="主页",
                                  font=self.home_button_font, bg='#e0e0e0', fg='#333333',
                                  width=8, height=2,  # 调整主页按钮尺寸
                                  relief='solid', bd=1,
                                  command=self.go_back_to_menu)
            home_button.place(relx=0.98, rely=0.5, anchor='e')
            
            print("标题栏创建完成")
            
        except Exception as e:
            print(f"创建标题栏失败: {e}")
            raise
    
    def create_parameters_area(self, parent, element_spacing, content_padding):
        """创建参数设置区域（左右两列布局）"""
        try:
            # 参数区域容器
            params_frame = tk.Frame(parent, bg='#ffffff')
            params_frame.pack(fill=tk.BOTH, expand=True, padx=content_padding, pady=(0, int(15 * self.font_scale)))
            
            # 左列参数（5个）
            left_column = tk.Frame(params_frame, bg='#ffffff')
            left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, int(30 * self.font_scale)))
            
            # 右列参数（4个+1个隐藏行对齐）
            right_column = tk.Frame(params_frame, bg='#ffffff')
            right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(int(30 * self.font_scale), 0))
            
            # 左列参数列表
            left_params = ['ZeroTrackRange', 'ZeroTrackTime', 'ZeroClearRange', 'StabilityRange', 'StabilityTime']
            
            # 右列参数列表  
            right_params = ['FilterLevelA', 'FilterLevelB', 'MinDivision', 'MaxCapacity']
            
            # 创建左列参数
            for i, param_key in enumerate(left_params):
                self.create_parameter_row(left_column, param_key, element_spacing)
            
            # 创建右列参数
            for i, param_key in enumerate(right_params):
                self.create_parameter_row(right_column, param_key, element_spacing)
            
            # 右列添加隐藏空行对齐
            empty_row = tk.Frame(right_column, bg='#ffffff', height=int(65 * self.font_scale + element_spacing))
            empty_row.pack(fill=tk.X, pady=(element_spacing, 0))
            
            print("参数设置区域创建完成")
            
        except Exception as e:
            print(f"创建参数设置区域失败: {e}")
            raise
    
    def create_parameter_row(self, parent, param_key, element_spacing):
        """创建单个参数行"""
        try:
            config = self.parameter_configs[param_key]
            
            # 参数行容器
            param_row = tk.Frame(parent, bg='#ffffff')
            param_row.pack(fill=tk.X, pady=(element_spacing, 0))
            
            # 参数标签（左侧）
            param_label = tk.Label(param_row, text=f"{config['label']}:",
                                 font=self.label_font, bg='#ffffff', fg='#333333')
            param_label.pack(side=tk.LEFT, anchor='w')
            
            # 参数输入框（右侧）
            param_entry = tk.Entry(param_row, font=self.entry_font, justify='center',
                                 width=15, relief='solid', bd=2, 
                                 highlightthickness=2, highlightcolor='#4a90e2', 
                                 bg='white', fg='#333333')
            param_entry.pack(side=tk.RIGHT, anchor='e', ipady=10)
            
            # 绑定参数修改事件
            param_entry.bind('<FocusOut>', 
                           lambda e, pk=param_key: self.on_parameter_changed(pk, e.widget.get()))
            param_entry.bind('<Return>', 
                           lambda e, pk=param_key: self.on_parameter_changed(pk, e.widget.get()))
            
            # 保存输入框引用
            self.parameter_entries[param_key] = param_entry
            
        except Exception as e:
            print(f"创建参数行 {param_key} 失败: {e}")
    
    def create_control_area(self, parent):
        """创建控制按钮区域"""
        try:
            # 控制区域容器
            control_frame = tk.Frame(parent, bg='#ffffff', height=int(120 * self.font_scale))
            control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=int(20 * self.font_scale))
            control_frame.pack_propagate(False)
            
            # 按钮容器（居中显示）
            button_container = tk.Frame(control_frame, bg='#ffffff')
            button_container.pack(expand=True)
            
            # 创建4个控制按钮
            for command_key, config in self.control_configs.items():
                btn = tk.Button(button_container, text=config['label'],
                              font=self.button_font, bg=config['color'], fg='white',
                              width=18, height=3,  # 增大按钮尺寸
                              relief='solid', bd=1,
                              command=lambda cmd=command_key: self.execute_system_command(cmd))
                btn.pack(side=tk.LEFT, padx=15)  # 减小按钮间距
                
                # 保存按钮引用
                self.control_buttons[command_key] = btn
            
            print("控制按钮区域创建完成")
            
        except Exception as e:
            print(f"创建控制按钮区域失败: {e}")
            raise
    
    def load_all_parameters(self):
        """加载所有系统参数"""
        try:
            print("开始加载系统参数...")
            
            if not self.modbus_client or not self.modbus_client.is_connected:
                print("PLC未连接，使用默认值")
                self.load_default_parameters()
                return
            
            # 逐个读取参数
            success_count = 0
            for param_key in self.parameter_configs.keys():
                try:
                    success = self.load_parameter(param_key)
                    if success:
                        success_count += 1
                except Exception as e:
                    print(f"加载参数 {param_key} 异常: {e}")
            
            print(f"成功加载 {success_count}/{len(self.parameter_configs)} 个系统参数")
            
        except Exception as e:
            print(f"加载系统参数失败: {e}")
            self.load_default_parameters()
    
    def load_parameter(self, param_key: str) -> bool:
        """加载单个参数"""
        try:
            # 获取PLC地址
            address = get_traditional_system_address(param_key)
            
            # 从PLC读取数据
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data:
                # 根据参数类型格式化数值
                config = self.parameter_configs[param_key]
                value = self.format_parameter_value(param_key, data[0])
                
                # 更新界面显示
                self.update_parameter_display(param_key, value)
                
                # 保存到本地数据
                self.parameter_data[param_key] = value
                
                print(f"加载参数 {param_key}: {value} (PLC值: {data[0]}, 地址: {address})")
                return True
            else:
                print(f"读取参数 {param_key} 失败，地址: {address}")
                self.load_default_parameter(param_key)
                return False
                
        except Exception as e:
            print(f"加载参数 {param_key} 异常: {e}")
            self.load_default_parameter(param_key)
            return False
    
    def format_parameter_value(self, param_key: str, plc_value: int) -> str:
        """
        格式化PLC参数值为显示值
        
        Args:
            param_key: 参数键
            plc_value: PLC原始值
            
        Returns:
            str: 格式化后的显示值
        """
        try:
            config = self.parameter_configs[param_key]
            
            # 根据参数类型进行转换（后续连机时可能需要调整）
            if config['type'] == 'decimal':
                # 小数类型，假设PLC存储时乘以了10
                value = plc_value / 10.0
                return f"{value:.{config['decimals']}f}"
            else:
                # 整数类型，直接使用
                return str(plc_value)
                
        except Exception as e:
            print(f"格式化参数 {param_key} 值失败: {e}")
            return str(plc_value)
    
    def update_parameter_display(self, param_key: str, value: str):
        """更新参数显示"""
        try:
            if param_key in self.parameter_entries:
                entry = self.parameter_entries[param_key]
                entry.delete(0, tk.END)
                entry.insert(0, value)
                print(f"更新参数显示 {param_key}: {value}")
        except Exception as e:
            print(f"更新参数 {param_key} 显示失败: {e}")
    
    def load_default_parameters(self):
        """加载默认参数值"""
        try:
            print("加载默认参数值...")
            
            default_values = {
                'ZeroTrackRange': '50',
                'ZeroTrackTime': '100', 
                'ZeroClearRange': '5',
                'StabilityRange': '10',
                'StabilityTime': '2000',
                'FilterLevelA': '3',
                'FilterLevelB': '5',
                'MinDivision': '1',
                'MaxCapacity': '50000'
            }
            
            for param_key, default_value in default_values.items():
                self.update_parameter_display(param_key, default_value)
                self.parameter_data[param_key] = default_value
                
            print("默认参数值加载完成")
            
        except Exception as e:
            print(f"加载默认参数失败: {e}")
    
    def load_default_parameter(self, param_key: str):
        """加载单个默认参数"""
        try:
            default_values = {
                'ZeroTrackRange': '50',
                'ZeroTrackTime': '100',
                'ZeroClearRange': '5', 
                'StabilityRange': '10',
                'StabilityTime': '2000',
                'FilterLevelA': '3',
                'FilterLevelB': '5',
                'MinDivision': '1',
                'MaxCapacity': '50000'
            }
            
            if param_key in default_values:
                default_value = default_values[param_key]
                self.update_parameter_display(param_key, default_value)
                self.parameter_data[param_key] = default_value
                print(f"加载默认参数 {param_key}: {default_value}")
                
        except Exception as e:
            print(f"加载默认参数 {param_key} 失败: {e}")
    
    def on_parameter_changed(self, param_key: str, input_value: str):
        """参数修改事件处理"""
        try:
            config = self.parameter_configs[param_key]
            
            # 验证并格式化输入值
            if not input_value.strip():
                print(f"参数 {param_key} 输入为空，忽略修改")
                return
            
            # 数值验证
            try:
                if config['type'] == 'decimal':
                    value = float(input_value)
                else:
                    value = int(input_value)
            except ValueError:
                messagebox.showerror("参数错误", f"{config['label']}输入格式错误")
                return
            
            # 格式化显示值
            if config['type'] == 'decimal':
                formatted_value = f"{value:.{config['decimals']}f}"
            else:
                formatted_value = str(int(value))
            
            # 更新显示和数据
            self.update_parameter_display(param_key, formatted_value)
            self.parameter_data[param_key] = formatted_value
            
            print(f"参数 {param_key} 修改为: {formatted_value}")
            
        except Exception as e:
            print(f"处理参数 {param_key} 修改异常: {e}")
            messagebox.showerror("参数错误", f"处理参数修改时发生错误: {e}")
    
    def save_all_parameters(self):
        """保存所有参数到PLC"""
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                messagebox.showerror("连接错误", "PLC未连接，无法保存参数")
                return False
            
            print("开始保存所有系统参数...")
            
            # 首先验证所有参数
            for param_key in self.parameter_configs.keys():
                if param_key in self.parameter_entries:
                    entry = self.parameter_entries[param_key]
                    self.on_parameter_changed(param_key, entry.get())
            
            # 逐个保存参数
            success_count = 0
            failed_params = []
            
            for param_key, value_str in self.parameter_data.items():
                try:
                    success = self.save_parameter(param_key, value_str)
                    if success:
                        success_count += 1
                    else:
                        failed_params.append(param_key)
                except Exception as e:
                    print(f"保存参数 {param_key} 异常: {e}")
                    failed_params.append(param_key)
            
            # 显示保存结果
            total_params = len(self.parameter_configs)
            if success_count == total_params:
                messagebox.showinfo("保存成功", f"所有系统参数已成功保存到PLC")
                return True
            else:
                failed_names = [self.parameter_configs[pk]['label'] for pk in failed_params]
                messagebox.showwarning("保存部分失败", 
                                     f"成功保存 {success_count}/{total_params} 个参数\n\n"
                                     f"失败的参数：{', '.join(failed_names)}")
                return False
                
        except Exception as e:
            print(f"保存系统参数异常: {e}")
            messagebox.showerror("保存异常", f"保存系统参数时发生错误: {e}")
            return False
    
    def save_parameter(self, param_key: str, value_str: str) -> bool:
        """保存单个参数到PLC"""
        try:
            config = self.parameter_configs[param_key]
            
            # 转换为PLC值
            if config['type'] == 'decimal':
                value = float(value_str)
                # 假设小数参数需要乘以10存储（后续连机时可能需要调整）
                plc_value = int(value * 10)
            else:
                plc_value = int(float(value_str))
            
            # 获取PLC地址
            address = get_traditional_system_address(param_key)
            
            # 写入PLC
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                print(f"成功保存参数 {param_key}: {value_str} (PLC值: {plc_value}, 地址: {address})")
                return True
            else:
                print(f"保存参数 {param_key} 失败，地址: {address}")
                return False
                
        except Exception as e:
            print(f"保存参数 {param_key} 异常: {e}")
            return False
    
    def execute_system_command(self, command_key: str):
        """执行系统控制命令"""
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                messagebox.showerror("连接错误", "PLC未连接，无法执行系统命令")
                return
            
            config = self.control_configs[command_key]
            command_name = config['label']
            
            # 特殊处理保存命令
            if command_key == 'SystemSave':
                result = messagebox.askyesno("确认保存", "确定要保存所有系统参数吗？")
                if result:
                    # 先保存参数，再发送系统保存命令
                    param_saved = self.save_all_parameters()
                    if param_saved:
                        # 发送系统保存脉冲命令
                        self.send_system_pulse_command(command_key, command_name)
                return
            
            # 其他命令确认
            result = messagebox.askyesno("确认操作", f"确定要执行'{command_name}'命令吗？")
            if result:
                self.send_system_pulse_command(command_key, command_name)
                
        except Exception as e:
            print(f"执行系统命令 {command_key} 异常: {e}")
            messagebox.showerror("命令执行异常", f"执行系统命令时发生错误: {e}")
    
    def send_system_pulse_command(self, command_key: str, command_name: str):
        """发送系统脉冲控制命令"""
        try:
            # 获取控制地址
            address = get_traditional_system_control_address(command_key)
            
            # 按钮视觉反馈
            if command_key in self.control_buttons:
                btn = self.control_buttons[command_key]
                original_color = btn.cget('bg')
                btn.configure(bg='#00aa00')  # 绿色反馈
                self.root.after(200, lambda: btn.configure(bg=original_color))
            
            # 发送脉冲命令
            success = self.send_pulse_command(address)
            
            if success:
                print(f"成功发送系统命令 {command_name} (地址: {address})")
                messagebox.showinfo("命令成功", f"'{command_name}'命令已发送")
                
                # 特定命令执行完后刷新参数
                if command_key in ['FeedDataInit', 'ModuleInit', 'ModuleDataRead']:
                    self.root.after(200, self.refresh_parameters_after_command)  # 0.2秒后刷新
                    
            else:
                print(f"发送系统命令 {command_name} 失败")
                messagebox.showerror("命令失败", f"'{command_name}'命令发送失败")
                
        except Exception as e:
            print(f"发送系统命令 {command_key} 异常: {e}")
            messagebox.showerror("命令异常", f"发送'{command_name}'命令时发生错误: {e}")
    
    def send_pulse_command(self, address: int, pulse_duration: int = 100) -> bool:
        """发送脉冲控制指令"""
        try:
            # 发送脉冲
            success1 = self.modbus_client.write_coil(address, True)
            if success1:
                # 延时后关闭
                self.root.after(pulse_duration, lambda: self.modbus_client.write_coil(address, False))
                return True
            else:
                return False
        except Exception as e:
            print(f"脉冲控制失败: {e}")
            return False
    
    def go_back_to_menu(self):
        """返回主菜单"""
        try:
            print("返回主菜单")
            self.cleanup()
            self.parent.show_menu_interface()
        except Exception as e:
            print(f"返回主菜单失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            print("清理系统设置界面资源")
            
            # 标记为未显示
            self.is_showing = False
            
            # 清空组件引用
            self.parameter_entries.clear()
            self.control_buttons.clear()
            self.parameter_data.clear()
            
            print("系统设置界面资源清理完成")
            
        except Exception as e:
            print(f"清理系统设置界面资源时发生错误: {e}")

    def refresh_parameters_after_command(self):
        """命令执行后刷新参数"""
        try:
            print("正在刷新系统参数...")
            self.load_all_parameters()
            print("系统参数刷新完成")
        except Exception as e:
            print(f"刷新系统参数失败: {e}")



# 测试代码
if __name__ == "__main__":
    # 创建测试窗口
    root = tk.Tk()
    root.title("系统设置界面测试")
    
    # 模拟父界面方法
    class MockParent:
        def __init__(self, root):
            self.root = root
            self.main_content_frame = tk.Frame(root, bg='#ffffff')
            self.main_content_frame.pack(fill=tk.BOTH, expand=True)
            
        def get_main_root(self):
            return self.root
            
        def get_main_content_frame(self):
            return self.main_content_frame
            
        def clear_main_content(self):
            for widget in self.main_content_frame.winfo_children():
                widget.destroy()
                
        def show_menu_interface(self):
            print("返回主菜单（模拟）")
    
    # 创建模拟父界面
    mock_parent = MockParent(root)
    
    # 创建系统设置界面
    system_interface = SystemSettingInterface(None, mock_parent)
    
    # 显示界面
    system_interface.show_interface()
    
    # 运行主循环
    root.mainloop()