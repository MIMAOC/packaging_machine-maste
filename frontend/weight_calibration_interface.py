#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重量校准界面模块
基于六头线性调节秤系统，实现重量校准功能界面

功能特点：
- 6个料斗的零点标定和重量校准
- 实时重量显示和状态指示
- 标准砝码重量输入
- 工业HMI风格界面设计
- 完整的PLC通信集成

界面尺寸：1400×900 (从1024×600换算)
换算比例：宽度×1.367，高度×1.5，字体×1.43

作者：AI助手
创建日期：2025-08-06
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any
from touchscreen_utils import TouchScreenUtils

# 导入PLC相关模块
try:
    from traditional_plc_addresses import (
        get_traditional_weight_address,
        get_traditional_monitoring_address, 
        get_traditional_control_address,
        get_traditional_parameter_address,
        get_traditional_global_address,
        get_traditional_disable_address,
        get_traditional_calibration_address
    )
    from modbus_client import ModbusClient
except ImportError as e:
    print(f"导入PLC模块失败: {e}")
    print("请确保traditional_plc_addresses.py和modbus_client.py在同一目录下")


class WeightCalibrationInterface:
    def __init__(self, modbus_client: Optional[ModbusClient] = None, parent_interface = None):
        """
        初始化重量校准界面
        
        Args:
            modbus_client: 共享的Modbus客户端
            parent_interface: 主界面引用
        """
        self.modbus_client = modbus_client           # 共享PLC客户端
        self.parent = parent_interface               # 主界面引用
        self.root = parent_interface.get_main_root() # 共享主窗口
        self.main_content_frame = parent_interface.get_main_content_frame()
        
        # 界面元素引用
        self.weight_labels = {}          # 重量显示标签
        self.standard_weight_entry = None # 标准重量输入框
        self.calibration_buttons = {}    # 校准按钮
        
        # 添加触摸屏优化
        TouchScreenUtils.optimize_window_for_touch(self.root)

        # 设置字体
        self.setup_fonts()
        
        # 校准状态管理
        self.calibration_in_progress = {}  # 校准进行中状态
        for i in range(1, 7):
            self.calibration_in_progress[i] = False
    
    def setup_fonts(self):
        """设置界面字体（自适应屏幕尺寸）"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        print(f"屏幕尺寸检测: {screen_width}×{screen_height}")
        
        # 计算窗口尺寸（屏幕的75-85%）
        if screen_width >= 2560:  # 2K及以上屏幕
            window_width = int(screen_width * 0.75)  # 75%
            window_height = int(screen_height * 0.8)  # 80%
            font_scale = 1.2  # 字体放大
        elif screen_width >= 1920:  # 1080P屏幕
            window_width = int(screen_width * 0.8)   # 80%
            window_height = int(screen_height * 0.85) # 85%
            font_scale = 1.0  # 标准字体
        else:  # 1366×768等小屏幕
            window_width = int(screen_width * 0.9)   # 90%
            window_height = int(screen_height * 0.9) # 90%
            font_scale = 0.8  # 字体缩小
        
        # 应用窗口尺寸
        self.root.geometry(f"{window_width}x{window_height}")
        print(f"窗口尺寸设置: {window_width}×{window_height}, 字体缩放: {font_scale}")
        
        # 动态计算字体大小
        base_instruction = int(42 * font_scale)
        base_standard = int(32 * font_scale)
        base_number = int(32 * font_scale)
        base_display = int(32 * font_scale)
        base_button = int(28 * font_scale)
        
        # 设置字体
        self.instruction_font = font.Font(family="Microsoft YaHei", size=base_instruction, weight="bold")
        self.standard_weight_font = font.Font(family="Arial", size=base_standard, weight="bold")
        self.hopper_number_font = font.Font(family="Arial", size=base_number, weight="bold")
        self.weight_display_font = font.Font(family="Arial", size=base_display, weight="bold")
        self.button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
        self.return_button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
        
        # 保存缩放比例供其他组件使用
        self.font_scale = font_scale
    
    def show_interface(self):
        """显示重量校准界面"""
        # 清空当前界面内容
        if hasattr(self.parent, 'shared_clear_main_content'):
            self.parent.shared_clear_main_content()
        
        # 创建校准界面
        self.create_calibration_interface()
        
        # 加载标准重量
        self.load_standard_weight()

        # 启动数据刷新
        self.start_data_refresh()

        print("重量校准界面已显示")
    
    def create_calibration_interface(self):
        """创建重量校准界面布局（自适应版本）"""
        # 动态计算间距（根据字体缩放）
        base_padding = int(40 * self.font_scale)
        content_padding = int(25 * self.font_scale)
        
        # 配置网格权重（比例分配，去掉固定minsize）
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=0)  # 提示区域，高度自适应
        self.main_content_frame.grid_rowconfigure(1, weight=1)  # 主内容区域，占用剩余空间
        self.main_content_frame.grid_rowconfigure(2, weight=0)  # 底部控制区域，高度自适应
        
        # 创建各个区域
        self.create_instruction_area(base_padding)
        self.create_hoppers_area(base_padding, content_padding)
        self.create_return_button(base_padding)
        
        print("重量校准界面布局创建完成 - 自适应版本")
    
    def create_instruction_area(self, base_padding):
        """创建提示信息区域（自适应版本）"""
        content_padding = int(base_padding * 0.6)  # 内部间距
        
        # 提示区域容器
        instruction_frame = tk.Frame(self.main_content_frame, bg='#e8e8e8')
        instruction_frame.grid(row=0, column=0, sticky='nsew', padx=base_padding, pady=(content_padding, 0))
        instruction_frame.grid_columnconfigure(0, weight=1)
        
        # 第一行提示文字
        line1 = tk.Label(instruction_frame, 
                        text="提示：请先清空称斗并进行零点标定，然后在称斗内放入",
                        font=self.instruction_font, bg='#e8e8e8', fg='#333333')
        line1.grid(row=0, column=0, pady=(content_padding//2, content_padding//3))
        
        # 第二行：标准重量输入 + 提示文字
        line2_frame = tk.Frame(instruction_frame, bg='#e8e8e8')
        line2_frame.grid(row=1, column=0, pady=(0, content_padding//2))
        
        # 标准重量输入框（动态宽度）
        entry_width = max(8, int(10 * self.font_scale))
        self.standard_weight_entry = tk.Entry(line2_frame,
                                            font=self.standard_weight_font,
                                            width=entry_width, justify='center',
                                            relief='solid', bd=3,
                                            highlightthickness=2)
        self.standard_weight_entry.pack(side='left', padx=(0, content_padding))
        self.standard_weight_entry.insert(0, "000.0")
        
        # 绑定输入验证和保存事件
        self.standard_weight_entry.bind('<KeyRelease>', self.validate_standard_weight)
        self.standard_weight_entry.bind('<FocusOut>', self.save_standard_weight)
        self.standard_weight_entry.bind('<Return>', self.save_standard_weight)
        
        # 提示文字（g标准砝码...）
        tk.Label(line2_frame, text="g标准砝码按校准键确认。",
                font=self.instruction_font, bg='#e8e8e8', fg='#333333').pack(side='left')
    
    def create_hoppers_area(self, base_padding, content_padding):
        """创建6个料斗区域（自适应版本，居中显示）"""
        # 主内容区域容器
        main_frame = tk.Frame(self.main_content_frame, bg='#e8e8e8')
        main_frame.grid(row=1, column=0, sticky='nsew', padx=base_padding, pady=(content_padding, content_padding))
        
        # 配置主框架网格，让内容垂直居中
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)  # 上部空白，占用剩余空间
        main_frame.grid_rowconfigure(1, weight=0)  # 料斗内容区域，高度自适应
        main_frame.grid_rowconfigure(2, weight=1)  # 下部空白，占用剩余空间
        
        # 料斗内容容器（居中显示）
        hoppers_container = tk.Frame(main_frame, bg='#e8e8e8')
        hoppers_container.grid(row=1, column=0, sticky='ew')
        
        # 6列网格布局（移除固定minsize，让其自适应）
        for i in range(6):
            hoppers_container.grid_columnconfigure(i, weight=1)  # 均匀分配空间
        hoppers_container.grid_rowconfigure(0, weight=1)
        
        # 创建6个料斗组件
        for hopper_id in range(1, 7):
            self.create_single_hopper(hoppers_container, hopper_id, hopper_id - 1, content_padding)
    
    def create_single_hopper(self, parent, hopper_id: int, col: int, content_padding: int):
        """创建单个料斗组件（自适应版本，大幅增大内部间距）
        
        Args:
            parent: 父容器
            hopper_id: 料斗ID (1-6)
            col: 网格列位置 (0-5)
            content_padding: 内容间距
        """
        # 动态计算间距（大幅增大内部间距）
        hopper_padding = max(6, int(content_padding * 0.3))  # 减小外部间距给内部让空间
        element_spacing = max(80, int(content_padding * 2.5))  # 大幅增加间距系数从0.8到1.2
        
        # 料斗容器
        hopper_frame = tk.Frame(parent, bg='#e8e8e8')
        hopper_frame.grid(row=0, column=col, sticky='nsew', padx=hopper_padding, pady=content_padding)
        hopper_frame.grid_columnconfigure(0, weight=1)
        
        # 配置垂直空间分配，让元素更均匀分布（增加权重让间距更大）
        hopper_frame.grid_rowconfigure(0, weight=2)  # 料斗编号区域，增加权重
        hopper_frame.grid_rowconfigure(1, weight=2)  # 重量显示区域
        hopper_frame.grid_rowconfigure(2, weight=2)  # 零点标定按钮区域  
        hopper_frame.grid_rowconfigure(3, weight=1)  # 重量校准按钮区域，最后一个不需要下边距
        
        # 料斗编号（方形）
        number_frame = tk.Frame(hopper_frame, bg='#e8e8e8')
        number_frame.grid(row=0, column=0, sticky='', pady=(0, element_spacing))
        
        # 动态计算组件宽度
        number_width = max(2, int(3 * self.font_scale))
        weight_width = max(8, int(12 * self.font_scale))
        button_width = max(6, int(8 * self.font_scale))
        
        number_label = tk.Label(number_frame, text=str(hopper_id),
                               font=self.hopper_number_font,
                               bg='white', fg='#333333',
                               width=number_width, height=1,
                               relief='solid', bd=4)
        number_label.pack()
        
        # 重量显示框
        weight_label = tk.Label(hopper_frame, text="-0000.0",
                               font=self.weight_display_font,
                               bg='white', fg='#333333',
                               width=weight_width, height=1,
                               relief='solid', bd=3)
        weight_label.grid(row=1, column=0, sticky='', pady=(0, element_spacing))
        self.weight_labels[hopper_id] = weight_label
        
        # 零点标定按钮
        zero_btn = tk.Button(hopper_frame, text="零点标定",
                            font=self.button_font,
                            bg='#1e90ff', fg='white',
                            width=button_width, height=1,
                            relief='solid', bd=2,
                            command=lambda: self.zero_calibration(hopper_id))
        zero_btn.grid(row=2, column=0, sticky='', pady=(0, element_spacing))
        self.calibration_buttons[f'{hopper_id}_zero'] = zero_btn
        
        # 重量校准按钮
        weight_btn = tk.Button(hopper_frame, text="校 准",
                              font=self.button_font,
                              bg='#1e90ff', fg='white',
                              width=button_width, height=1,
                              relief='solid', bd=2,
                              command=lambda: self.weight_calibration(hopper_id))
        weight_btn.grid(row=3, column=0, sticky='')
        self.calibration_buttons[f'{hopper_id}_weight'] = weight_btn
        
        # 鼠标悬停显示PLC地址（调试用）
        def show_address_info(event):
            weight_addr = f"D{700 + (hopper_id - 1) * 2}"
            zero_addr = f"M{hopper_id}"
            calib_addr = f"M{hopper_id + 6}"
            tooltip_text = f"料斗{hopper_id}\n重量: {weight_addr}\n零点: {zero_addr}\n校准: {calib_addr}"
            # 这里可以添加tooltip显示功能
            print(tooltip_text)
        
        hopper_frame.bind("<Enter>", show_address_info)
    
    def create_return_button(self, base_padding):
        """创建返回按钮（自适应版本）"""
        content_padding = int(base_padding * 0.5)
        
        # 底部控制区域
        bottom_frame = tk.Frame(self.main_content_frame, bg='#e8e8e8')
        bottom_frame.grid(row=2, column=0, sticky='nsew', padx=base_padding, pady=(0, content_padding))
        
        # 动态按钮宽度
        button_width = max(6, int(8 * self.font_scale))
        
        # 返回按钮（右下角）
        return_btn = tk.Button(bottom_frame, text="返 回",
                              font=self.return_button_font,
                              bg='#666666', fg='white',
                              width=button_width, height=1,
                              relief='solid', bd=3,
                              command=self.go_back_to_menu)
        return_btn.pack(side='right', pady=content_padding)
    
    def zero_calibration(self, hopper_id: int):
        """执行零点标定
        
        Args:
            hopper_id: 料斗ID (1-6)
        """
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法执行零点标定")
            return
        
        if self.calibration_in_progress.get(hopper_id, False):
            messagebox.showwarning("警告", f"料斗{hopper_id}校准操作进行中，请等待...")
            return
        
        try:
            print(f"开始料斗{hopper_id}零点标定...")
            
            # 设置校准状态
            self.calibration_in_progress[hopper_id] = True
            self.update_calibration_status(hopper_id, "零点标定中...", True)
            
            # 发送零点标定脉冲命令（M1-M6对应料斗1-6）
            success = self.send_calibration_pulse_command(hopper_id, "ZeroCalibration")
            
            if success:
                print(f"料斗{hopper_id}零点标定命令发送成功")
                # 延时后更新状态
                self.root.after(1000, lambda: self.finish_calibration(hopper_id, "零点标定完成"))
            else:
                messagebox.showerror("错误", f"料斗{hopper_id}零点标定命令发送失败")
                self.calibration_in_progress[hopper_id] = False
                self.update_calibration_status(hopper_id, "标定失败", False)
                
        except Exception as e:
            print(f"料斗{hopper_id}零点标定异常: {e}")
            messagebox.showerror("错误", f"料斗{hopper_id}零点标定异常: {str(e)}")
            self.calibration_in_progress[hopper_id] = False
            self.update_calibration_status(hopper_id, "标定异常", False)
    
    def weight_calibration(self, hopper_id: int):
        """执行重量校准
        
        Args:
            hopper_id: 料斗ID (1-6)
        """
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法执行重量校准")
            return
        
        if self.calibration_in_progress.get(hopper_id, False):
            messagebox.showwarning("警告", f"料斗{hopper_id}校准操作进行中，请等待...")
            return
        
        # 验证标准重量输入
        try:
            standard_weight_str = self.standard_weight_entry.get().strip()
            standard_weight = float(standard_weight_str)
            
            if standard_weight <= 0:
                messagebox.showerror("错误", "请输入有效的标准重量（大于0）")
                return
                
        except ValueError:
            messagebox.showerror("错误", f"标准重量格式错误: {standard_weight_str}")
            return
        
        try:
            print(f"开始料斗{hopper_id}重量校准，标准重量: {standard_weight}g")
            
            # 设置校准状态
            self.calibration_in_progress[hopper_id] = True
            self.update_calibration_status(hopper_id, f"校准中({standard_weight}g)...", True)
            
            # 发送重量校准脉冲命令（M7-M12对应料斗1-6）
            success = self.send_calibration_pulse_command(hopper_id, "WeightCalibration")
            
            if success:
                print(f"料斗{hopper_id}重量校准命令发送成功")
                # 延时后更新状态
                self.root.after(1500, lambda: self.finish_calibration(hopper_id, "重量校准完成"))
            else:
                messagebox.showerror("错误", f"料斗{hopper_id}重量校准命令发送失败")
                self.calibration_in_progress[hopper_id] = False
                self.update_calibration_status(hopper_id, "校准失败", False)
                
        except Exception as e:
            print(f"料斗{hopper_id}重量校准异常: {e}")
            messagebox.showerror("错误", f"料斗{hopper_id}重量校准异常: {str(e)}")
            self.calibration_in_progress[hopper_id] = False
            self.update_calibration_status(hopper_id, "校准异常", False)
    

    def send_calibration_pulse_command(self, hopper_id: int, command_type: str) -> bool:
        """发送校准脉冲命令
        
        Args:
            hopper_id: 料斗ID (1-6)  
            command_type: 命令类型 ("ZeroCalibration" 或 "WeightCalibration")
            
        Returns:
            bool: 命令发送是否成功
        """
        try:
            # 使用正确的地址获取函数
            coil_address = get_traditional_calibration_address(hopper_id, command_type)
            
            # 发送100ms脉冲
            if hasattr(self.parent, 'shared_send_pulse_command'):
                return self.parent.shared_send_pulse_command(coil_address, 1000)
            else:
                # 直接使用modbus客户端发送脉冲
                return self.send_pulse_command(coil_address, 100)
                
        except Exception as e:
            print(f"发送校准脉冲命令异常: {e}")
            return False
    
    def send_pulse_command(self, address: int, pulse_duration: int = 1000) -> bool:
        """发送脉冲控制指令
        
        Args:
            address: 线圈地址
            pulse_duration: 脉冲持续时间（毫秒）
            
        Returns:
            bool: 脉冲发送是否成功
        """
        try:
            # 发送脉冲开启
            success = self.modbus_client.write_coil(address, True)
            if success:
                # 延时后关闭脉冲
                self.root.after(pulse_duration, lambda: self.modbus_client.write_coil(address, False))
                return True
            else:
                print(f"脉冲命令发送失败，地址: {address}")
                return False
        except Exception as e:
            print(f"脉冲控制失败: {e}")
            return False
    
    def update_calibration_status(self, hopper_id: int, message: str, is_active: bool):
        """更新校准状态显示
        
        Args:
            hopper_id: 料斗ID
            message: 状态消息
            is_active: 是否激活状态
        """
        # 可以在这里添加更多状态显示逻辑
        print(f"料斗{hopper_id}状态: {message}")
    
    def finish_calibration(self, hopper_id: int, message: str):
        """完成校准操作
        
        Args:
            hopper_id: 料斗ID
            message: 完成消息
        """
        self.calibration_in_progress[hopper_id] = False
        self.update_calibration_status(hopper_id, message, False)
        
        # 显示完成提示
        self.show_temporary_message(f"料斗{hopper_id}{message}")
    
    def show_temporary_message(self, message: str, duration: int = 2000):
        """显示临时消息提示
        
        Args:
            message: 消息内容
            duration: 显示持续时间（毫秒）
        """
        # 创建临时消息标签
        msg_label = tk.Label(self.main_content_frame, text=message,
                            font=('Microsoft YaHei', 24, 'bold'),
                            bg='#333333', fg='white',
                            padx=30, pady=15)
        msg_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # 自动消失
        self.root.after(duration, msg_label.destroy)
    
    def validate_standard_weight(self, event=None):
        """验证标准重量输入"""
        try:
            entry = event.widget
            value = entry.get()
            
            # 基本格式检查
            if value and not value.replace('.', '').isdigit():
                # 如果包含非数字和小数点的字符，清理输入
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                # 确保只有一个小数点
                parts = cleaned.split('.')
                if len(parts) > 2:
                    cleaned = parts[0] + '.' + ''.join(parts[1:])
                
                entry.delete(0, tk.END)
                entry.insert(0, cleaned)
                
        except Exception as e:
            print(f"验证标准重量输入异常: {e}")
    
    def start_data_refresh(self):
        """启动数据刷新"""
        if hasattr(self.parent, 'shared_start_data_refresh'):
            self.parent.shared_start_data_refresh(self.update_calibration_data)
    
    def stop_data_refresh(self):
        """停止数据刷新"""
        if hasattr(self.parent, 'shared_stop_data_refresh'):
            self.parent.shared_stop_data_refresh()
    
    def update_calibration_data(self):
        """更新校准界面数据"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            # 更新6个料斗的重量显示
            for hopper_id in range(1, 7):
                if hopper_id in self.weight_labels:
                    try:
                        # 计算重量地址：D700, D702, D704, D706, D708, D710
                        weight_address = 700 + (hopper_id - 1) * 2
                        
                        # 如果有traditional_plc_addresses模块，使用其地址映射
                        try:
                            weight_address = get_traditional_weight_address(hopper_id)
                        except:
                            # 使用计算的地址
                            pass
                        
                        # 读取重量数据
                        weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                        if weight_data:
                            # 处理16位有符号整数（修复负数显示问题）
                            raw_value = weight_data[0]
                            if raw_value > 32767:
                                signed_value = raw_value - 65536  # 转换为负数（16位补码）
                            else:
                                signed_value = raw_value
                            
                            # PLC重量值除以10得到实际重量
                            weight_value = signed_value / 10.0
                            weight_text = f"{weight_value:.1f}"
                            self.weight_labels[hopper_id].configure(text=weight_text)
                            
                            # 根据重量值调整颜色
                            if weight_value > 0:
                                self.weight_labels[hopper_id].configure(fg='#00aa00')  # 正数绿色
                            elif weight_value < 0:
                                self.weight_labels[hopper_id].configure(fg='#ff4444')  # 负数红色
                            else:
                                self.weight_labels[hopper_id].configure(fg='#333333')  # 零黑色
                        
                    except Exception as e:
                        print(f"读取料斗{hopper_id}重量失败: {e}")
            
        except Exception as e:
            print(f"更新校准数据失败: {e}")
    
    def go_back_to_menu(self):
        """返回主菜单"""
        try:
            # 停止数据刷新
            self.cleanup()
            
            # 返回主菜单
            if hasattr(self.parent, 'show_menu_interface'):
                self.parent.show_menu_interface()
            else:
                print("无法返回主菜单：找不到主界面引用")
                
        except Exception as e:
            print(f"返回主菜单时出错: {e}")
            messagebox.showerror("错误", f"返回主菜单时出错: {str(e)}")

    def load_standard_weight(self):
        """从PLC加载标准重量"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            from traditional_plc_addresses import get_traditional_system_address
            address = get_traditional_system_address('StandardWeight')
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data:
                # 标准重量需要除以10显示
                standard_weight = data[0] / 10.0
                self.standard_weight_entry.delete(0, tk.END)
                self.standard_weight_entry.insert(0, f"{standard_weight:.1f}")
                print(f"成功加载标准重量: {standard_weight}g")
            else:
                print("读取标准重量失败")
                
        except Exception as e:
            print(f"加载标准重量失败: {e}")

    def save_standard_weight(self, event=None):
        """保存标准重量到PLC"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存标准重量")
            return
        
        try:
            standard_weight_str = self.standard_weight_entry.get().strip()
            standard_weight = float(standard_weight_str)
            
            if standard_weight < 0:
                messagebox.showerror("错误", "标准重量不能为负数")
                return
            
            # 标准重量需要乘以10存储到PLC
            plc_value = int(standard_weight * 10)
            
            from traditional_plc_addresses import get_traditional_system_address
            address = get_traditional_system_address('StandardWeight')
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                print(f"成功保存标准重量: {standard_weight}g (PLC值: {plc_value})")
            else:
                messagebox.showerror("错误", "保存标准重量失败")
                
        except ValueError:
            messagebox.showerror("错误", f"标准重量格式错误: {standard_weight_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存标准重量异常: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止数据刷新
            self.stop_data_refresh()
            
            # 清空界面元素引用
            self.weight_labels.clear()
            self.calibration_buttons.clear()
            self.standard_weight_entry = None
            
            # 重置校准状态
            for hopper_id in range(1, 7):
                self.calibration_in_progress[hopper_id] = False
            
            print("重量校准界面资源清理完成")
            
        except Exception as e:
            print(f"清理重量校准界面资源时出错: {e}")


# 测试代码
if __name__ == "__main__":
    # 创建测试窗口
    test_root = tk.Tk()
    test_root.title("重量校准界面测试 - 自适应版本")
    test_root.configure(bg='#e8e8e8')
    
    # 让窗口可调整大小
    test_root.minsize(1000, 700)
    
    # 创建测试框架
    test_frame = tk.Frame(test_root, bg='#e8e8e8')
    test_frame.pack(fill='both', expand=True)
    
    # 模拟父接口
    class MockParentInterface:
        def __init__(self, root):
            self.root = root
            self.main_content_frame = test_frame
        
        def get_main_root(self):
            return self.root
            
        def get_main_content_frame(self):
            return self.main_content_frame
            
        def shared_clear_main_content(self):
            for widget in self.main_content_frame.winfo_children():
                widget.destroy()
        
        def shared_start_data_refresh(self, callback):
            print("模拟启动数据刷新")
        
        def shared_stop_data_refresh(self):
            print("模拟停止数据刷新")
            
        def shared_send_pulse_command(self, address, duration):
            print(f"模拟发送脉冲命令: 地址{address}, 持续{duration}ms")
            return True
        
        def show_menu_interface(self):
            print("模拟返回主菜单")
    
    # 创建模拟Modbus客户端
    class MockModbusClient:
        def __init__(self):
            self.is_connected = True
            
        def read_holding_registers(self, address, count):
            # 模拟返回重量数据
            import random
            return [random.randint(-100, 1000)]  # 模拟重量值（PLC值）
        
        def write_coil(self, address, value):
            print(f"模拟写入线圈: 地址{address}, 值{value}")
            return True
    
    # 创建界面
    parent = MockParentInterface(test_root)
    modbus_client = MockModbusClient()
    
    calibration_interface = WeightCalibrationInterface(modbus_client, parent)
    calibration_interface.show_interface()
    
    print("重量校准界面测试启动 - 自适应版本！")
    print("窗口会根据屏幕尺寸自动调整大小和字体")
    test_root.mainloop()