#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出厂设置界面
包装机出厂设置管理界面，包含密码验证和误差设置

功能特点：
1. 管理员密码验证
2. 重量误差阈值设置
3. 参数验证和保存

文件名：factory_settings_interface.py
作者：AI助手
创建日期：2025-08-05
"""

import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont

# 导入触摸屏工具模块
try:
    from touchscreen_utils import TouchScreenUtils
    TOUCHSCREEN_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入触摸屏工具模块: {e}")
    TOUCHSCREEN_UTILS_AVAILABLE = False

class ErrorThresholdConfig:
    """误差阈值配置类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.lower_error = -0.2  # 默认下限误差
            self.upper_error = 0.6   # 默认上限误差
            self.initialized = True
    
    def update_thresholds(self, lower_error: float, upper_error: float):
        """更新误差阈值"""
        with self._lock:
            self.lower_error = lower_error
            self.upper_error = upper_error
    
    def get_thresholds(self) -> tuple:
        """获取误差阈值"""
        with self._lock:
            return self.lower_error, self.upper_error
        
# 全局配置实例
error_config = ErrorThresholdConfig()

class FactorySettingsInterface:
    """
    出厂设置界面类
    
    负责：
    1. 管理员密码验证
    2. 误差阈值参数设置
    3. 参数验证和保存
    """
    
    def __init__(self, parent=None, system_settings_window=None):
        """
        初始化出厂设置界面
        
        Args:
            parent: 父窗口对象
            system_settings_window: 系统设置界面引用，用于返回时显示
        """
        # 保存系统设置界面引用
        self.system_settings_window = system_settings_window
        
        # 管理员密码
        self.admin_password = "1234"
        
        # 误差设置默认值和限制
        self.default_lower_error = -0.2
        self.default_upper_error = 0.6
        self.min_lower_error = -0.2
        self.min_upper_error = 0.6
        self.min_error_diff = 0.8
    
        # 从配置文件加载设置
        self._load_from_config_file()
        
        # 显示密码验证窗口
        self.show_password_verification()
        
    def _load_from_config_file(self):
        """从配置文件加载设置"""
        try:
            import json
            import os
            
            config_file = os.path.join("config", "error_thresholds.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 从配置文件加载并确保精度
                self.current_lower_error = round(config_data.get("lower_error", self.default_lower_error), 1)
                self.current_upper_error = round(config_data.get("upper_error", self.default_upper_error), 1)
                
                # 更新全局配置
                global error_config
                error_config.update_thresholds(self.current_lower_error, self.current_upper_error)
                
                print(f"[配置文件] 已加载误差设置：下限={self.current_lower_error}g, 上限={self.current_upper_error}g")
            else:
                # 使用默认值并确保精度
                self.current_lower_error = round(self.default_lower_error, 1)
                self.current_upper_error = round(self.default_upper_error, 1)
                print(f"[配置文件] 使用默认误差设置")
                
        except Exception as e:
            print(f"[警告] 加载配置文件失败: {e}，使用默认设置")
            # 异常时使用默认值并确保精度
            self.current_lower_error = round(self.default_lower_error, 1)
            self.current_upper_error = round(self.default_upper_error, 1)
    
    def show_password_verification(self):
        """显示密码验证窗口（第一个窗口）"""
        # 创建密码验证窗口
        self.password_window = tk.Toplevel()
        self.password_window.title("出厂设置")
        self.password_window.attributes('-fullscreen', True)
        self.password_window.state('zoomed')  # Windows系统的最大化
        self.password_window.geometry("1920x1080")
        self.password_window.configure(bg='white')
        self.password_window.resizable(True, True)
        self.password_window.transient()
        self.password_window.grab_set()
    
        # 添加触摸屏优化
        if TOUCHSCREEN_UTILS_AVAILABLE:
            TouchScreenUtils.optimize_window_for_touch(self.password_window)
        
        # 绑定窗口关闭事件
        self.password_window.protocol("WM_DELETE_WINDOW", self.on_password_window_closing)
        
        # 添加强制退出机制
        self.setup_force_exit_mechanism(self.password_window)
        
        # 设置字体
        self.setup_fonts()
        
        # 创建密码验证界面
        self.create_password_widgets()
        
        # 居中显示窗口
        # self.center_window(self.password_window)
    
    def setup_fonts(self):
        """设置界面字体"""
        # 标题字体 - 增大
        self.title_font = tkFont.Font(family="微软雅黑", size=32, weight="bold")
        
        # 标签字体 - 增大
        self.label_font = tkFont.Font(family="微软雅黑", size=20)
        
        # 输入框字体 - 增大
        self.entry_font = tkFont.Font(family="微软雅黑", size=18)
        
        # 按钮字体 - 增大
        self.button_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        # 小按钮字体 - 增大
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        
        # 底部信息字体 - 增大
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)
        
        # 数值字体 - 增大
        self.value_font = tkFont.Font(family="微软雅黑", size=24, weight="bold")
        
        # 单位字体 - 增大
        self.unit_font = tkFont.Font(family="微软雅黑", size=16)
    
    def create_password_widgets(self):
        """创建密码验证界面组件"""
        # 主容器
        main_frame = tk.Frame(self.password_window, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=120, pady=50)
        
        # 创建标题栏
        self.create_password_title_bar(main_frame)
        
        # 创建密码输入区域
        self.create_password_input_section(main_frame)
        
        # 创建底部信息区域
        self.create_footer_section(main_frame)
    
    def create_password_title_bar(self, parent):
        """创建密码验证窗口标题栏"""
        # 标题栏容器
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧标题
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        # 出厂设置标题
        title_label = tk.Label(left_frame, text="出厂设置", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # 右侧返回按钮
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        # 返回AI模式按钮
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_to_ai_mode)
        return_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 40))
    
    def create_password_input_section(self, parent):
        """创建密码输入区域"""
        # 密码输入容器
        password_frame = tk.Frame(parent, bg='white')
        password_frame.pack(expand=True, fill='both')
        
        # 居中容器
        center_frame = tk.Frame(password_frame, bg='white')
        center_frame.pack(expand=True)
        
        # 提示标签
        prompt_label = tk.Label(center_frame, text="请输入管理员密码", 
                               font=self.label_font, bg='white', fg='#333333')
        prompt_label.pack(pady=(0, 50))
        
        # 密码输入框
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(center_frame, textvariable=self.password_var,
                                 font=self.entry_font,
                                 width=30, show='*',
                                 relief='solid', bd=1,
                                 bg='white', fg='#333333')
        password_entry.pack(ipady=12, pady=(0, 80))
    
        # 使用触摸屏工具设置输入框
        if TOUCHSCREEN_UTILS_AVAILABLE:
            TouchScreenUtils.setup_touch_entry(password_entry, "请输入密码")
        
        # 设置焦点并绑定回车键
        password_entry.focus()
        password_entry.bind('<Return>', lambda e: self.verify_password())
        
        # 确认按钮
        confirm_btn = tk.Button(center_frame, text="确认", 
                               font=self.button_font,
                               bg='#e9ecef', fg='#333333',
                               relief='flat', bd=1,
                               padx=60, pady=18,
                               command=self.verify_password)
        confirm_btn.pack()
    
    def setup_placeholder(self, entry_widget, placeholder_text):
        """为输入框设置占位符效果"""
        if TOUCHSCREEN_UTILS_AVAILABLE:
            # 使用触摸屏工具
            TouchScreenUtils.setup_touch_entry(entry_widget, placeholder_text)
        else:
            # 原有的占位符实现
            def on_focus_in(event):
                if entry_widget.get() == placeholder_text:
                    entry_widget.delete(0, tk.END)
                    entry_widget.config(fg='#333333', show='*')
            
            def on_focus_out(event):
                if entry_widget.get() == '':
                    entry_widget.insert(0, placeholder_text)
                    entry_widget.config(fg='#999999', show='')
            
            # 设置初始占位符
            entry_widget.insert(0, placeholder_text)
            entry_widget.config(fg='#999999', show='')
            
            # 绑定事件
            entry_widget.bind('<FocusIn>', on_focus_in)
            entry_widget.bind('<FocusOut>', on_focus_out)
    
    def verify_password(self):
        """验证管理员密码"""
        entered_password = self.password_var.get()
        
        # 验证密码（忽略占位符）
        if entered_password == "请输入密码" or entered_password == "":
            messagebox.showwarning("密码错误", "请输入管理员密码！")
            return
        
        if entered_password == self.admin_password:
            # 密码正确，关闭密码窗口，打开设置窗口
            self.password_window.destroy()
            self.show_settings_window()
        else:
            # 密码错误
            messagebox.showerror("密码错误", "管理员密码不正确，请重新输入！")
            self.password_var.set("")
    
    def show_settings_window(self):
        """显示设置窗口（第二个窗口）"""
        # 创建设置窗口
        self.settings_window = tk.Toplevel()
        self.settings_window.title("出厂设置")
        self.settings_window.attributes('-fullscreen', True)
        self.settings_window.state('zoomed')  # Windows系统的最大化
        self.settings_window.geometry("1920x1080")
        self.settings_window.configure(bg='white')
        self.settings_window.resizable(True, True)
        self.settings_window.transient()
        self.settings_window.grab_set()
    
        # 添加触摸屏优化
        if TOUCHSCREEN_UTILS_AVAILABLE:
            TouchScreenUtils.optimize_window_for_touch(self.settings_window)
        
        # 绑定窗口关闭事件
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_window_closing)
        
        # 添加强制退出机制
        self.setup_force_exit_mechanism(self.settings_window)
        
        # 创建设置界面
        self.create_settings_widgets()
        
        # 居中显示窗口
        # self.center_window(self.settings_window)
    
    def create_settings_widgets(self):
        """创建设置界面组件"""
        # 主容器
        main_frame = tk.Frame(self.settings_window, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=120, pady=50)
        
        # 创建标题栏
        self.create_settings_title_bar(main_frame)
        
        # 创建误差设置区域
        self.create_error_settings_section(main_frame)
        
        # 创建按钮区域
        self.create_settings_buttons_section(main_frame)
        
        # 创建底部信息区域
        self.create_footer_section(main_frame)
    
    def create_settings_title_bar(self, parent):
        """创建设置窗口标题栏"""
        # 标题栏容器
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧标题
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        # 出厂设置标题
        title_label = tk.Label(left_frame, text="出厂设置", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # 右侧返回按钮
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        # 返回AI模式按钮
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_to_ai_mode)
        return_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 40))
    
    def create_error_settings_section(self, parent):
        """创建误差设置区域"""
        # 误差设置容器
        error_frame = tk.Frame(parent, bg='white')
        error_frame.pack(expand=True, fill='both', pady=(50, 100))
        
        # 居中容器
        center_frame = tk.Frame(error_frame, bg='white')
        center_frame.pack(expand=True)
        
        # 误差设置行容器
        settings_row = tk.Frame(center_frame, bg='white')
        settings_row.pack()
        
        # 下限误差设置
        self.create_error_setting(settings_row, "下限误差", self.current_lower_error, 
                                 self.on_lower_error_change, side=tk.LEFT, padx=(0, 100))
        
        # 上限误差设置
        self.create_error_setting(settings_row, "上限误差", self.current_upper_error, 
                                 self.on_upper_error_change, side=tk.LEFT)
        
    def setup_force_exit_mechanism(self, window):
        """设置强制退出机制"""
        # 键盘快捷键强制退出
        window.bind('<Control-Alt-q>', lambda e: self.force_exit())
        window.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        window.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        # 添加隐藏的强制退出区域（右上角小区域）
        exit_zone = tk.Frame(window, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)  # 放在右上角
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        # 连续点击计数器用于紧急退出
        self.click_count = 0
        self.last_click_time = 0

    def show_exit_confirmation(self):
        """显示退出确认对话框"""
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出出厂设置吗？\n\n"
            "退出将返回主界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        """强制退出程序"""
        try:
            print("执行强制退出...")
            self.on_return_to_ai_mode()
        except Exception as e:
            print(f"强制退出时发生错误: {e}")
            import os
            os._exit(0)  # 强制终止进程
    
    def create_error_setting(self, parent, title, initial_value, change_callback, side=tk.LEFT, padx=0):
        """创建误差设置组件"""
        # 设置容器
        setting_frame = tk.Frame(parent, bg='white')
        setting_frame.pack(side=side, padx=padx)
        
        # 标题
        title_label = tk.Label(setting_frame, text=title, 
                              font=self.label_font, bg='white', fg='#333333')
        title_label.pack(pady=(0, 20))
        
        # 数值显示和调节容器
        value_frame = tk.Frame(setting_frame, bg='white')
        value_frame.pack()
        
        # 数值显示框
        value_display = tk.Entry(value_frame,
                                font=self.value_font,
                                width=8, justify='center',
                                relief='solid', bd=1,
                                bg='white', fg='#333333',
                                state='readonly')
        value_display.pack(pady=(0, 15))
        
        # 设置初始值
        value_display.config(state='normal')
        value_display.delete(0, tk.END)
        value_display.insert(0, f"{initial_value:+.1f}")
        value_display.config(state='readonly')
        
        # 单位和按钮容器
        unit_button_frame = tk.Frame(value_frame, bg='white')
        unit_button_frame.pack()
        
        # 单位标签
        unit_label = tk.Label(unit_button_frame, text="克g", 
                             font=self.unit_font, bg='white', fg='#333333')
        unit_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # 加号按钮
        plus_btn = tk.Button(unit_button_frame, text="+", 
                            font=self.button_font,
                            bg='#e9ecef', fg='#333333',
                            relief='flat', bd=1,
                            width=3, height=1,
                            command=lambda: change_callback(0.1, value_display))
        plus_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 减号按钮
        minus_btn = tk.Button(unit_button_frame, text="-", 
                             font=self.button_font,
                             bg='#e9ecef', fg='#333333',
                             relief='flat', bd=1,
                             width=3, height=1,
                             command=lambda: change_callback(-0.1, value_display))
        minus_btn.pack(side=tk.LEFT)
        
        # 保存显示框引用
        if title == "下限误差":
            self.lower_error_display = value_display
        else:
            self.upper_error_display = value_display
    
    def on_lower_error_change(self, delta, display_widget):
        """下限误差变化事件"""
        new_value = round(self.current_lower_error + delta, 1)  # 四舍五入避免浮点精度问题
        
        # 验证下限误差不得小于-0.2g
        if new_value < self.min_lower_error:
            messagebox.showwarning("参数限制", f"下限误差不得小于{self.min_lower_error:+.1f}g")
            return
        
        # 更新当前值
        self.current_lower_error = new_value
        
        # 更新显示
        display_widget.config(state='normal')
        display_widget.delete(0, tk.END)
        display_widget.insert(0, f"{new_value:+.1f}")
        display_widget.config(state='readonly')
    
    def on_upper_error_change(self, delta, display_widget):
        """上限误差变化事件"""
        new_value = round(self.current_upper_error + delta, 1)  # 四舍五入避免浮点精度问题
        
        # 验证上限误差不得小于+0.6g
        if new_value < self.min_upper_error:
            messagebox.showwarning("参数限制", f"上限误差不得小于{self.min_upper_error:+.1f}g")
            return
        
        # 更新当前值
        self.current_upper_error = new_value
        
        # 更新显示
        display_widget.config(state='normal')
        display_widget.delete(0, tk.END)
        display_widget.insert(0, f"{new_value:+.1f}")
        display_widget.config(state='readonly')
    
    def create_settings_buttons_section(self, parent):
        """创建设置按钮区域"""
        # 按钮容器
        button_frame = tk.Frame(parent, bg='white')
        button_frame.pack(pady=(0, 50))
        
        # 恢复默认按钮
        reset_btn = tk.Button(button_frame, text="恢复默认", 
                             font=self.button_font,
                             bg='#e9ecef', fg='#333333',
                             relief='flat', bd=1,
                             padx=40, pady=12,
                             command=self.reset_to_default)
        reset_btn.pack(side=tk.LEFT, padx=(0, 30))
        
        # 保存设置按钮
        save_btn = tk.Button(button_frame, text="保存设置", 
                            font=self.button_font,
                            bg='#e9ecef', fg='#333333',
                            relief='flat', bd=1,
                            padx=40, pady=12,
                            command=self.save_settings)
        save_btn.pack(side=tk.LEFT, padx=(30, 0))
    
    def reset_to_default(self):
        """恢复默认设置"""
        result = messagebox.askyesno("恢复默认", 
                                   f"确认要恢复默认设置吗？\n\n"
                                   f"下限误差：{self.default_lower_error:+.1f}g\n"
                                   f"上限误差：{self.default_upper_error:+.1f}g")
        
        if result:
            # 恢复默认值（确保精度）
            self.current_lower_error = round(self.default_lower_error, 1)
            self.current_upper_error = round(self.default_upper_error, 1)
            
            # 更新显示
            self.lower_error_display.config(state='normal')
            self.lower_error_display.delete(0, tk.END)
            self.lower_error_display.insert(0, f"{self.current_lower_error:+.1f}")
            self.lower_error_display.config(state='readonly')
            
            self.upper_error_display.config(state='normal')
            self.upper_error_display.delete(0, tk.END)
            self.upper_error_display.insert(0, f"{self.current_upper_error:+.1f}")
            self.upper_error_display.config(state='readonly')
            
            messagebox.showinfo("恢复成功", "已恢复默认设置")
    
    def save_settings(self):
        """保存设置"""
        # 验证参数（使用四舍五入避免浮点精度问题）
        error_diff = round(self.current_upper_error - self.current_lower_error, 1)

        # 使用 < 比较，但考虑浮点精度，添加小的容差
        if error_diff < (self.min_error_diff - 0.05):  # 0.75 < 0.8 才报错
            messagebox.showerror("参数错误", 
                               f"误差范围不足！\n\n"
                               f"请调整参数使误差范围至少为 {self.min_error_diff}g")
            return

        # 参数验证通过，保存设置
        result = messagebox.askyesno("保存设置", 
                                   f"确认保存当前设置吗？\n\n"
                                   f"下限误差：{self.current_lower_error:+.1f}g\n"
                                   f"上限误差：{self.current_upper_error:+.1f}g\n")

        if result:
            try:
                # 更新全局误差配置（新增）
                global error_config
                error_config.update_thresholds(self.current_lower_error, self.current_upper_error)

                # 这里可以添加实际的保存逻辑（比如写入配置文件）
                self._save_to_config_file()

                messagebox.showinfo("保存成功", 
                                  f"出厂设置已保存！\n\n"
                                  f"下限误差：{self.current_lower_error:+.1f}g\n"
                                  f"上限误差：{self.current_upper_error:+.1f}g\n\n"
                                  f"新的误差设置将在下次生产时生效")

                print(f"[出厂设置] 误差阈值已更新：下限={self.current_lower_error}g, 上限={self.current_upper_error}g")

            except Exception as e:
                error_msg = f"保存设置异常: {str(e)}"
                print(f"[错误] {error_msg}")
                messagebox.showerror("保存失败", f"保存设置时发生错误：\n{error_msg}")
                
    def _save_to_config_file(self):
        """保存设置到配置文件（可选实现）"""
        try:
            # 这里可以实现保存到配置文件的逻辑
            # 比如保存到 config/error_thresholds.json
            import json
            import os

            config_dir = "config"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            config_file = os.path.join(config_dir, "error_thresholds.json")
            config_data = {
                "lower_error": self.current_lower_error,
                "upper_error": self.current_upper_error,
                "saved_time": time.time()
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)

            print(f"[配置文件] 误差设置已保存到 {config_file}")

        except Exception as e:
            print(f"[警告] 保存配置文件失败: {e}")
    
    def create_footer_section(self, parent):
        """创建底部信息区域"""
        # 底部信息容器
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        # 版本信息
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        # 公司logo区域
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        # 导入并使用logo处理器
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
            print("[FactorySettings] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
    def center_window(self, window):
        """将窗口居中显示"""
        try:
            # 确保窗口已经完全创建
            window.update_idletasks()
            
            # 获取窗口尺寸
            width = window.winfo_width()
            height = window.winfo_height()
            
            # 如果窗口尺寸为1（未正确获取），使用设定的尺寸
            if width <= 1 or height <= 1:
                width = 950
                height = 750
            
            # 计算居中位置
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            # 设置窗口位置
            window.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            print(f"出厂设置界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            window.geometry("950x750")
    
    def on_return_to_ai_mode(self):
        """返回AI模式按钮点击事件"""
        print("点击了返回AI模式")
        
        # 关闭当前所有窗口
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        if hasattr(self, 'password_window') and self.password_window.winfo_exists():
            self.password_window.destroy()
        
        # 如果有系统设置界面引用，重新显示系统设置界面
        if self.system_settings_window:
            try:
                # 显示系统设置界面
                self.system_settings_window.root.deiconify()
                self.system_settings_window.root.lift()
                self.system_settings_window.root.focus_force()
                print("系统设置界面已显示")
            except Exception as e:
                print(f"显示系统设置界面时发生错误: {e}")
                # 如果系统设置界面有问题，尝试直接返回AI模式
                if hasattr(self.system_settings_window, 'ai_mode_window') and self.system_settings_window.ai_mode_window:
                    try:
                        self.system_settings_window.ai_mode_window.root.deiconify()
                        self.system_settings_window.ai_mode_window.root.lift()
                        self.system_settings_window.ai_mode_window.root.focus_force()
                        print("AI模式界面已显示")
                    except Exception as e2:
                        print(f"显示AI模式界面时发生错误: {e2}")
    
    def on_password_window_closing(self):
        """密码验证窗口关闭事件处理"""
        self.on_return_to_ai_mode()
    
    def on_settings_window_closing(self):
        """设置窗口关闭事件处理"""
        self.on_return_to_ai_mode()


def main():
    """
    主函数 - 程序入口点（用于测试）
    """
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 创建出厂设置界面实例
    factory_settings = FactorySettingsInterface()


# 当作为主程序运行时，启动界面
if __name__ == "__main__":
    main()