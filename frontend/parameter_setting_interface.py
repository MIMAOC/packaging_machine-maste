#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数设置界面模块
基于六头线性调节秤系统，实现系统参数的读取、修改和保存功能

技术架构：
- 界面框架: tkinter (Python)
- 通信协议: Modbus TCP  
- 分辨率: 自适应屏幕尺寸 (2K屏75%空间，1080P屏80%空间，小屏90%空间)
- 字体缩放: 自动根据屏幕尺寸调整 (2K屏×1.2，1080P×1.0，小屏×0.8)

作者：AI助手
创建日期：2025-08-15
版本：V1.0
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any
from touchscreen_utils import TouchScreenUtils

# 导入PLC相关模块
try:
    from traditional_plc_addresses import get_traditional_system_address
    from modbus_client import ModbusClient
except ImportError as e:
    print(f"导入PLC模块失败: {e}")
    print("请确保traditional_plc_addresses.py和modbus_client.py在同一目录下")
    # 为了避免运行时错误，定义空类
    class ModbusClient:
        pass


class ParameterSettingInterface:
    """参数设置界面类"""
    
    def __init__(self, modbus_client: Optional[ModbusClient], parent_interface):
        """
        初始化参数设置界面
        
        Args:
            modbus_client: Modbus通信客户端
            parent_interface: 父界面实例（传统模式界面）
        """
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        
        # 界面元素引用
        self.main_content_frame = None
        self.parameter_entries = {}  # 参数输入框引用
        self.parameter_labels = {}   # 参数标签引用
        self.control_buttons = {}    # 控制按钮引用
        
        # 数据刷新定时器
        self.refresh_timer = None

        # 添加触摸屏优化
        TouchScreenUtils.optimize_window_for_touch(self.root)

        
        # 参数数据存储
        self.parameter_data = {
            'CleanSpeed': 0,      # 清料速度
            'JogTime': 0.0,       # 点动时间
            'DebounceTime': 0.0,  # 消抖时间
            'JogInterval': 0.0,   # 点动间隔
            'DischargeTime': 0.0, # 放料时间
            'AllowableError': 0.0,# 允许误差
            'DoorDelay': 0.0      # 关门延时
        }
        
        # 参数配置：名称、类型、范围、小数位数
        self.parameter_configs = {
            'CleanSpeed': {
                'name': '清料速度',
                'type': 'integer',
                'min': 0,
                'max': 100,
                'decimals': 0,
                'unit': ''
            },
            'JogTime': {
                'name': '点动时间',
                'type': 'decimal', 
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'DebounceTime': {
                'name': '消抖时间',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9, 
                'decimals': 1,
                'unit': ''
            },
            'JogInterval': {
                'name': '点动间隔',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'DischargeTime': {
                'name': '放料时间',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'AllowableError': {
                'name': '允许误差',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'DoorDelay': {
                'name': '关门延时',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            }
        }
        
        self.setup_fonts()
    
    def setup_fonts(self):
        """设置字体（自适应屏幕尺寸）"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 智能屏幕检测和字体缩放
        if screen_width >= 2560:  # 2K及以上屏幕
            self.font_scale = 1.2  # 字体放大
        elif screen_width >= 1920:  # 1080P屏幕
            self.font_scale = 1.0  # 标准字体
        else:  # 小屏幕
            self.font_scale = 0.8  # 字体缩小
        
        # 动态字体计算
        base_title = int(56 * self.font_scale)      # 标题字体
        base_label = int(38 * self.font_scale)      # 标签字体  
        base_entry = int(42 * self.font_scale)      # 输入框字体
        base_button = int(32 * self.font_scale)     # 按钮字体
        
        # 创建字体对象
        self.title_font = font.Font(family="Microsoft YaHei", size=base_title, weight="bold")
        self.label_font = font.Font(family="Microsoft YaHei", size=base_label, weight="normal")
        self.entry_font = font.Font(family="Arial", size=base_entry, weight="bold")
        self.button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
        
        # 动态尺寸计算
        self.entry_width = int(200 * self.font_scale)  # 减小宽度
        self.entry_height = int(50 * self.font_scale)  # 增加高度
        self.button_width = int(180 * self.font_scale)
        self.button_height = int(60 * self.font_scale)
        
        # 动态间距计算
        self.base_padding = int(40 * self.font_scale)
        self.content_padding = int(25 * self.font_scale)
        self.element_spacing = max(30, int(self.content_padding * 1.2))
    
    def show_interface(self):
        """显示参数设置界面"""
        self.create_parameter_interface()
        self.load_all_parameters()
        self.start_data_refresh()
    
    def create_parameter_interface(self):
        """创建参数设置界面"""
        # 获取主内容框架
        self.main_content_frame = self.parent.get_main_content_frame()
        
        # 强制重置父容器的grid配置（修复布局问题）
        try:
            # 清理可能的残留grid配置
            for i in range(10):
                self.main_content_frame.grid_rowconfigure(i, weight=0, minsize=0)
                self.main_content_frame.grid_columnconfigure(i, weight=0, minsize=0)
            
            # 清理几何管理器状态
            for child in self.main_content_frame.winfo_children():
                child.grid_forget()
                child.pack_forget()
                
            print("参数界面：主内容框架配置已重置")
        except Exception as e:
            print(f"重置主内容框架配置时出错: {e}")
        
        # 主容器 - 垂直居中布局
        main_frame = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_frame.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        
        # 配置主框架的行列权重
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)  # 主内容区域，置顶
        main_frame.grid_rowconfigure(1, weight=1)  # 下部空白
        main_frame.grid_columnconfigure(0, weight=1)
        
        # 创建主内容区域
        content_frame = tk.Frame(main_frame, bg='#ffffff')
        content_frame.grid(row=0, column=0, sticky='nsew', padx=self.base_padding, pady=(0, self.base_padding))
        content_frame.grid_rowconfigure(0, weight=0)  # 标题区域
        content_frame.grid_rowconfigure(1, weight=1)  # 参数区域
        content_frame.grid_rowconfigure(2, weight=0)  # 按钮区域
        content_frame.grid_columnconfigure(0, weight=1)
        
        # 创建标题区域
        self.create_title_area(content_frame)
        
        # 创建参数设置区域
        self.create_parameters_area(content_frame)
        
        # 创建底部控制区域
        self.create_control_area(content_frame)
    
    def create_title_area(self, parent):
        """创建标题区域"""
        title_frame = tk.Frame(parent, bg='#4a90e2', height=int(120 * self.font_scale))
        title_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(0, self.content_padding))
        title_frame.grid_propagate(False)
        title_frame.grid_columnconfigure(0, weight=1)
        title_frame.grid_rowconfigure(0, weight=1)
        
        # 创建居中容器
        center_container = tk.Frame(title_frame, bg='#4a90e2')
        center_container.grid(row=0, column=0, sticky='')  # 不使用sticky，让它自然居中
        
        # 标题文字 - 完美居中
        title_label = tk.Label(center_container, text="参数设置", 
                              font=self.title_font, bg='#4a90e2', fg='white')
        title_label.pack()
        
        # 主页按钮 - 绝对定位到右上角
        home_button = tk.Button(title_frame, text="主页", 
                               font=self.button_font, bg='#e0e0e0', fg='#333333',
                               relief='solid', bd=2, cursor='hand2',
                               command=self.go_back_to_menu)
        home_button.place(relx=0.98, rely=0.5, anchor='e')  # 使用place精确定位
        self.control_buttons['home'] = home_button
    
    def create_parameters_area(self, parent):
        """创建参数设置区域"""
        # 参数容器
        params_frame = tk.Frame(parent, bg='#ffffff')
        params_frame.grid(row=1, column=0, sticky='nsew', padx=0, pady=self.content_padding)
        params_frame.grid_columnconfigure(0, weight=1)
        params_frame.grid_columnconfigure(1, weight=1)
        params_frame.grid_rowconfigure(0, weight=1)
        
        # 左列参数
        left_frame = tk.Frame(params_frame, bg='#ffffff')
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, self.element_spacing))
        
        # 右列参数
        right_frame = tk.Frame(params_frame, bg='#ffffff')
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(self.element_spacing, 0))
        
        # 参数布局（按图片布局）
        left_params = ['CleanSpeed', 'DebounceTime', 'DischargeTime', 'DoorDelay']
        right_params = ['JogTime', 'JogInterval', 'AllowableError', None]  # None表示空白
        
        # 创建左列参数
        for i, param_key in enumerate(left_params):
            if param_key:
                self.create_parameter_row(left_frame, param_key, i)
        
        # 创建右列参数
        for i, param_key in enumerate(right_params):
            if param_key:
                self.create_parameter_row(right_frame, param_key, i)
    
    def create_parameter_row(self, parent, param_key: str, row: int):
        """创建单个参数行"""
        config = self.parameter_configs[param_key]
        
        # 参数行容器
        row_frame = tk.Frame(parent, bg='#ffffff')
        row_frame.grid(row=row, column=0, sticky='ew', padx=0, pady=int(self.element_spacing * 0.5))
        row_frame.grid_columnconfigure(0, weight=0)
        row_frame.grid_columnconfigure(1, weight=1)
        row_frame.grid_rowconfigure(0, weight=1)
        
        # 参数标签
        label_text = f"{config['name']}:"
        param_label = tk.Label(row_frame, text=label_text,
                              font=self.label_font, bg='#ffffff', fg='#333333')
        param_label.grid(row=0, column=0, sticky='w', padx=(0, self.content_padding))
        self.parameter_labels[param_key] = param_label
        
        # 参数输入框
        param_entry = tk.Entry(row_frame, font=self.entry_font, justify='center',
                              relief='solid', bd=3, fg='#0066ff', bg='white',
                              width=12, 
                              highlightthickness=2, highlightcolor='#4a90e2')
        param_entry.grid(row=0, column=1, sticky='w', padx=0, pady=8, ipady=8)  # 增加内部padding

        # 添加触摸屏支持
        TouchScreenUtils.setup_touch_entry(param_entry)
        
        # 绑定输入验证和保存事件
        param_entry.bind('<KeyRelease>', lambda e, key=param_key: self.validate_input(key, e.widget.get()))
        param_entry.bind('<FocusOut>', lambda e, key=param_key: self.format_parameter_value(key))
        param_entry.bind('<Return>', lambda e, key=param_key: self.format_parameter_value(key))
        
        self.parameter_entries[param_key] = param_entry
    
    def create_control_area(self, parent):
        """创建底部控制区域"""
        control_frame = tk.Frame(parent, bg='#ffffff')
        control_frame.grid(row=2, column=0, sticky='ew', padx=0, pady=(self.content_padding, 0))
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=0)
        control_frame.grid_columnconfigure(2, weight=0)
        control_frame.grid_columnconfigure(3, weight=1)
        control_frame.grid_rowconfigure(0, weight=1)
        
        # 保存按钮
        save_button = tk.Button(control_frame, text="保存", 
                               font=self.button_font, bg='#4a90e2', fg='white',
                               relief='solid', bd=2, cursor='hand2',
                               width=10, height=2,
                               command=self.save_all_parameters)
        save_button.grid(row=0, column=1, sticky='ns', padx=self.element_spacing)
        self.control_buttons['save'] = save_button
        
        # 返回按钮
        return_button = tk.Button(control_frame, text="返回", 
                                 font=self.button_font, bg='#e0e0e0', fg='#333333',
                                 relief='solid', bd=2, cursor='hand2',
                                 width=10, height=2,
                                 command=self.go_back_to_menu)
        return_button.grid(row=0, column=2, sticky='ns', padx=self.element_spacing)
        self.control_buttons['return'] = return_button
    
    def load_all_parameters(self):
        """加载所有参数从PLC"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            print("PLC未连接，使用默认参数值")
            self.load_default_parameters()
            return
        
        try:
            for param_key in self.parameter_configs:
                self.load_parameter(param_key)
            print("所有参数加载完成")
        except Exception as e:
            print(f"加载参数失败: {e}")
            messagebox.showerror("错误", f"加载参数失败: {e}")
            self.load_default_parameters()
    
    def load_parameter(self, param_key: str):
        """加载单个参数"""
        try:
            # 获取PLC地址
            address = get_traditional_system_address(param_key)
            
            # 从PLC读取数据
            data = self.modbus_client.read_holding_registers(address, 1)
            if data:
                config = self.parameter_configs[param_key]
                
                # 根据参数类型处理数据
                if config['type'] == 'decimal' and param_key in ['JogTime', 'DebounceTime', 'JogInterval', 'DischargeTime', 'DoorDelay', 'AllowableError']:
                    # 时间类参数可能需要除以特定值
                    value = data[0] / 10.0
                else:
                    value = data[0]
                
                # 存储参数值
                self.parameter_data[param_key] = value
                
                # 更新界面显示
                self.update_parameter_display(param_key, value)
                
                print(f"参数 {param_key} 加载成功: {value}")
                
        except Exception as e:
            print(f"加载参数 {param_key} 失败: {e}")
            # 使用默认值
            config = self.parameter_configs[param_key]
            default_value = config['min']
            self.parameter_data[param_key] = default_value
            self.update_parameter_display(param_key, default_value)
    
    def load_default_parameters(self):
        """加载默认参数值"""
        for param_key, config in self.parameter_configs.items():
            default_value = config['min']
            self.parameter_data[param_key] = default_value
            self.update_parameter_display(param_key, default_value)
        print("已加载默认参数值")
    
    def update_parameter_display(self, param_key: str, value):
        """更新参数在界面上的显示"""
        if param_key in self.parameter_entries:
            entry = self.parameter_entries[param_key]
            config = self.parameter_configs[param_key]
            
            # 格式化显示值
            if config['type'] == 'decimal':
                display_value = f"{value:.{config['decimals']}f}"
            else:
                display_value = f"{int(value):02d}"
            
            entry.delete(0, tk.END)
            entry.insert(0, display_value)
    
    def validate_input(self, param_key: str, input_value: str):
        """验证输入值"""
        if not input_value:
            return True
        
        try:
            config = self.parameter_configs[param_key]
            
            # 类型验证
            if config['type'] == 'decimal':
                value = float(input_value)
            else:
                value = int(input_value)
            
            # 范围验证
            if value < config['min'] or value > config['max']:
                return False
            
            return True
            
        except ValueError:
            return False
    
    def format_parameter_value(self, param_key: str):
        """格式化参数值"""
        if param_key not in self.parameter_entries:
            return
        
        entry = self.parameter_entries[param_key]
        input_value = entry.get()
        
        if not input_value:
            return
        
        try:
            config = self.parameter_configs[param_key]
            
            # 转换并验证
            if config['type'] == 'decimal':
                value = float(input_value)
            else:
                value = int(input_value)
            
            # 范围限制
            value = max(config['min'], min(config['max'], value))
            
            # 更新显示和存储
            self.parameter_data[param_key] = value
            self.update_parameter_display(param_key, value)
            
        except ValueError:
            # 恢复为之前的值
            old_value = self.parameter_data.get(param_key, config['min'])
            self.update_parameter_display(param_key, old_value)
    
    def save_all_parameters(self):
        """保存所有参数到PLC"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存参数")
            return
        
        # 首先格式化所有当前输入
        for param_key in self.parameter_configs:
            self.format_parameter_value(param_key)
        
        success_count = 0
        total_count = len(self.parameter_configs)
        
        try:
            for param_key, value in self.parameter_data.items():
                if self.save_parameter(param_key, value):
                    success_count += 1
            
            if success_count == total_count:
                messagebox.showinfo("成功", "所有参数保存成功！")
                print("所有参数保存完成")
            else:
                messagebox.showwarning("警告", f"只有 {success_count}/{total_count} 个参数保存成功")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存参数时发生异常: {e}")
    
    def save_parameter(self, param_key: str, value) -> bool:
        """保存单个参数到PLC"""
        try:
            # 获取PLC地址
            address = get_traditional_system_address(param_key)
            
            config = self.parameter_configs[param_key]
            
            # 根据参数类型转换PLC值
            if config['type'] == 'decimal' and param_key in ['JogTime', 'DebounceTime', 'JogInterval', 'DischargeTime', 'DoorDelay', 'AllowableError']:
                # 时间类参数可能需要乘以特定值
                plc_value = int(value * 10) if value < 100 else int(value)
            else:
                plc_value = int(value)
            
            # 写入PLC
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                print(f"参数 {param_key} 保存成功: {value} (PLC值: {plc_value})")
                return True
            else:
                print(f"参数 {param_key} 保存失败")
                return False
                
        except Exception as e:
            print(f"保存参数 {param_key} 异常: {e}")
            return False
    
    def start_data_refresh(self):
        """启动数据刷新"""
        # 参数设置界面通常不需要频繁刷新，只在加载时读取一次即可
        # 如果需要实时刷新，可以取消下面的注释
        # if self.modbus_client and self.modbus_client.is_connected:
        #     self.update_parameters_data()
        pass
    
    def stop_data_refresh(self):
        """停止数据刷新"""
        if self.refresh_timer:
            self.root.after_cancel(self.refresh_timer)
            self.refresh_timer = None
    
    def update_parameters_data(self):
        """更新参数数据（可选的实时刷新）"""
        try:
            # 重新加载所有参数
            for param_key in self.parameter_configs:
                self.load_parameter(param_key)
        except Exception as e:
            print(f"更新参数数据失败: {e}")
        finally:
            # 继续下一次更新（如果需要）
            self.refresh_timer = self.root.after(5000, self.update_parameters_data)  # 5秒刷新一次
    
    def go_back_to_menu(self):
        """返回主菜单"""
        self.cleanup()
        self.parent.show_menu_interface()
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止数据刷新
            self.stop_data_refresh()
            
            # 清空界面元素引用
            self.parameter_entries.clear()
            self.parameter_labels.clear()
            self.control_buttons.clear()
            
            print("参数设置界面资源清理完成")
            
        except Exception as e:
            print(f"清理参数设置界面资源时发生错误: {e}")


# 测试代码
if __name__ == "__main__":
    print("参数设置界面模块测试")
    
    # 这里可以添加单独的测试代码
    # 实际使用时会被传统模式界面调用