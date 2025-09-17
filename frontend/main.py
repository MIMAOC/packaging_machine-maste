#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多斗颗粒称重包装机主程序 - 前端版本
集成Modbus TCP通信功能，连接后端API服务

功能特点：
1. 图形化用户界面（基于tkinter）
2. Modbus TCP自动连接PLC
3. 传统模式和AI模式选择
4. 连接状态实时显示
5. 后端API服务集成
6. API连接重试机制

依赖库安装：
pip install -r requirements.txt

作者：AI助手
创建日期：2025-07-22
更新日期：2025-07-30（增加API重试机制）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time
import requests
import functools
from typing import Optional, Callable, Any

# 导入重试库
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    RETRY_AVAILABLE = True
except ImportError:
    print("警告：tenacity库未安装，将使用简单重试机制")
    print("建议安装：pip install tenacity")
    RETRY_AVAILABLE = False

# 导入自定义的Modbus客户端模块
try:
    from modbus_client import create_modbus_client, ModbusClient, scan_modbus_devices
    MODBUS_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入modbus_client模块: {e}")
    print("请确保modbus_client.py文件在同一目录下，并已安装pymodbus库")
    MODBUS_AVAILABLE = False

# 导入AI模式界面模块
try:
    from ai_mode_interface import AIModeInterface
    AI_MODE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入ai_mode_interface模块: {e}")
    print("请确保ai_mode_interface.py文件在同一目录下")
    AI_MODE_AVAILABLE = False

# 导入传统模式界面模块
try:
    from traditional_mode_interface import SimpleTianTengInterface
    TRADITIONAL_MODE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入传统模式界面模块: {e}")
    print("请确保traditional_mode_interface.py文件在同一目录下")
    TRADITIONAL_MODE_AVAILABLE = False

# 导入API配置模块
try:
    from config.api_config import get_api_config, set_api_config
    API_CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入API配置模块: {e}")
    print("请确保config/api_config.py文件存在")
    API_CONFIG_AVAILABLE = False

# 导入后端API客户端
try:
    from clients.webapi_client import test_webapi_connection, get_webapi_info
    WEBAPI_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入WebAPI客户端模块: {e}")
    print("请确保clients/webapi_client.py文件存在")
    WEBAPI_CLIENT_AVAILABLE = False


def simple_retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):
    """
    简单的重试装饰器（当tenacity不可用时使用）
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型元组
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # 不是最后一次尝试
                        print(f"重试第 {attempt + 1} 次失败，{current_delay:.1f}秒后重试: {str(e)}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"所有重试都失败了，抛出最后的异常")
                except Exception as e:
                    # 对于不需要重试的异常，直接抛出
                    raise e
            
            # 如果所有尝试都失败了，抛出最后的异常
            if last_exception is not None:
                raise last_exception
            else:
                raise Exception("所有重试都失败，但未捕获到异常")
        
        return wrapper
    return decorator


def retry_api_call(func: Callable, max_attempts: int = 3, *args, **kwargs) -> tuple[bool, str]:
    """
    通用的API调用重试包装函数
    
    Args:
        func: 要重试的函数指针
        max_attempts: 最大重试次数
        *args, **kwargs: 传递给函数的参数
    
    Returns:
        tuple[bool, str]: (成功状态, 消息)
    """
    if RETRY_AVAILABLE:
        # 使用tenacity库进行重试
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
            reraise=True
        )
        def _retry_with_tenacity():
            return func(*args, **kwargs)
        
        try:
            return _retry_with_tenacity()
        except Exception as e:
            return False, f"重试{max_attempts}次后仍失败: {str(e)}"
    
    else:
        # 使用简单重试机制
        @simple_retry(
            max_attempts=max_attempts,
            delay=1.0,
            backoff=2.0,
            exceptions=(requests.RequestException, ConnectionError, TimeoutError, OSError)
        )
        def _simple_retry():
            return func(*args, **kwargs)
        
        try:
            return _simple_retry()
        except Exception as e:
            return False, f"重试{max_attempts}次后仍失败: {str(e)}"


class PackagingMachineGUI:
    """
    包装机图形用户界面主类 - 前端版本
    
    负责：
    1. 创建和管理GUI界面
    2. 处理用户交互事件
    3. 管理Modbus连接状态
    4. 管理后端API连接状态
    5. 显示系统状态信息
    6. API连接重试机制
    """
    
    def __init__(self, root):
        """
        初始化图形界面
        
        Args:
            root: tkinter根窗口对象
        """
        self.root = root
        self.modbus_client: Optional[ModbusClient] = None
        self.connection_status = False
        self.api_connection_status = False
        self.status_label = None  # PLC连接状态标签
        self.api_status_label = None  # API连接状态标签
        self.api_retry_count = 0  # API重试计数器
        self.traditional_interface = None   # 传统模式界面实例
        
        # 窗口基本设置
        self.setup_window()
        
        # 字体设置
        self.setup_fonts()
        
        # 创建界面元素
        self.create_widgets()
        
        # 启动Modbus连接
        if MODBUS_AVAILABLE:
            self.start_modbus_connection()
        else:
            self.show_modbus_error()
        
        # 测试后端API连接
        if WEBAPI_CLIENT_AVAILABLE:
            self.test_backend_api_connection()
        else:
            self.show_api_error()
    
    def setup_window(self):
        """设置主窗口属性"""
        self.root.title("多斗颗粒称重包装机 - MHWPM v1.5.2 (前端)")
    
        # 设置全屏模式
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')  # Windows系统的最大化
        
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)  # 允许调整窗口大小
    
        # 添加强制退出机制
        self.setup_force_exit_mechanism()
        
        # 设置窗口图标（如果有的话）
        try:
            # self.root.iconbitmap('icon.ico')  # 可以添加程序图标
            pass
        except:
            pass
    
    def setup_fonts(self):
        """设置界面字体 - 适应1920×1080分辨率"""
        self.title_font = tkFont.Font(family="微软雅黑", size=36, weight="bold")  # 增大标题字体
        self.subtitle_font = tkFont.Font(family="微软雅黑", size=20)  # 增大副标题字体
        self.button_font = tkFont.Font(family="微软雅黑", size=24, weight="bold")  # 增大按钮字体
        self.button_sub_font = tkFont.Font(family="微软雅黑", size=16)  # 增大按钮副字体
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)  # 增大底部字体
        self.status_font = tkFont.Font(family="微软雅黑", size=16)  # 增大状态字体
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 主容器框架
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)
        
        # 创建状态栏（显示连接状态）
        self.create_status_bar(main_frame)
        
        # 创建标题区域
        self.create_title_section(main_frame)
        
        # 创建模式选择区域
        self.create_mode_selection(main_frame)
        
        # 创建底部信息区域
        self.create_footer_section(main_frame)
    
    def create_status_bar(self, parent):
        """
        创建状态栏显示连接状态
        
        Args:
            parent: 父容器
        """
        status_frame = tk.Frame(parent, bg='white', relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # PLC连接状态部分
        plc_frame = tk.Frame(status_frame, bg='white')
        plc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(plc_frame, text="PLC连接:", 
                font=self.status_font, bg='white', fg='#333333').pack(side=tk.LEFT, padx=10)
        
        self.status_label = tk.Label(plc_frame, text="正在连接...", 
                                   font=self.status_font, bg='white', fg='#ff6600')
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # PLC操作按钮
        plc_buttons_frame = tk.Frame(plc_frame, bg='white')
        plc_buttons_frame.pack(side=tk.RIGHT, padx=10)
        
        reconnect_btn = tk.Button(plc_buttons_frame, text="重新连接", 
                                font=tkFont.Font(family="微软雅黑", size=9),
                                command=self.reconnect_modbus, bg='#e0e0e0')
        reconnect_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        settings_btn = tk.Button(plc_buttons_frame, text="连接设置", 
                               font=tkFont.Font(family="微软雅黑", size=9),
                               command=self.show_connection_settings, bg='#e0e0e0')
        settings_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        scan_btn = tk.Button(plc_buttons_frame, text="扫描设备", 
                           font=tkFont.Font(family="微软雅黑", size=9),
                           command=self.scan_modbus_devices, bg='#d4e6f1')
        scan_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 分隔线
        separator = tk.Frame(status_frame, width=2, bg='#ddd')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # API连接状态部分
        api_frame = tk.Frame(status_frame, bg='white')
        api_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(api_frame, text="后端API:", 
                font=self.status_font, bg='white', fg='#333333').pack(side=tk.LEFT, padx=10)
        
        self.api_status_label = tk.Label(api_frame, text="检测中...", 
                                       font=self.status_font, bg='white', fg='#ff6600')
        self.api_status_label.pack(side=tk.LEFT, padx=5)
        
        # API操作按钮
        api_buttons_frame = tk.Frame(api_frame, bg='white')
        api_buttons_frame.pack(side=tk.RIGHT, padx=10)
        api_test_btn = tk.Button(api_buttons_frame, text="测试连接", 
                               font=tkFont.Font(family="微软雅黑", size=9),
                               command=self.test_backend_api_connection, bg='#e0e0e0')
        api_test_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        api_config_btn = tk.Button(api_buttons_frame, text="API配置", 
                                 font=tkFont.Font(family="微软雅黑", size=9),
                                 command=self.show_api_settings, bg='#d1ecf1')
        api_config_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 添加重试连接按钮
        retry_btn = tk.Button(api_buttons_frame, text="重试连接", 
                            font=tkFont.Font(family="微软雅黑", size=9),
                            command=lambda: self.test_backend_api_connection(force_retry=True), 
                            bg='#ffc107')
        retry_btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    def create_title_section(self, parent):
        """
        创建标题区域
        
        Args:
            parent: 父容器
        """
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(pady=(20, 30))
        
        # 中文标题
        chinese_title = tk.Label(title_frame, text="多斗颗粒称重包装机", 
                               font=self.title_font, bg='white', fg='#333333')
        chinese_title.pack()
        
        # 英文标题
        english_title = tk.Label(title_frame, text="Multi-head Weighing & Packaging Machine", 
                               font=self.subtitle_font, bg='white', fg='#666666')
        english_title.pack(pady=(10, 0))
        
        # 蓝色分隔线
        separator = tk.Frame(title_frame, height=3, bg='#7fb3d3', width=600)
        separator.pack(pady=(15, 0))
        separator.pack_propagate(False)
    
    def create_mode_selection(self, parent):
        """
        创建模式选择区域
        
        Args:
            parent: 父容器
        """
        # 选择模式标题
        mode_title = tk.Label(parent, text="选择您的操作模式", 
                            font=self.subtitle_font, bg='white', fg='#333333')
        mode_title.pack(pady=(30, 40))
        
        # 按钮容器
        button_frame = tk.Frame(parent, bg='white')
        button_frame.pack(pady=(0, 30))
        
        # 传统模式按钮容器
        traditional_frame = tk.Frame(button_frame, bg='#d3d3d3', relief='flat', bd=0)
        traditional_frame.pack(side=tk.LEFT, padx=(0, 60))  # 增大按钮间距
        traditional_frame.configure(width=350, height=150)  # 增大按钮尺寸
        traditional_frame.pack_propagate(False)
        
        # 创建传统模式按钮
        self.create_rounded_button(traditional_frame, "传统模式", "手动调试设置", 
                                 self.on_traditional_click, '#d3d3d3')
        
        # AI模式按钮容器
        ai_frame = tk.Frame(button_frame, bg='#d3d3d3', relief='flat', bd=0)
        ai_frame.pack(side=tk.LEFT)
        ai_frame.configure(width=350, height=150)
        ai_frame.pack_propagate(False)
        
        # 创建AI模式按钮
        self.create_rounded_button(ai_frame, "AI模式", "自学习自适应", 
                                 self.on_ai_click, '#d3d3d3')
    
    def create_footer_section(self, parent):
        """
        创建底部信息区域
        
        Args:
            parent: 父容器
        """
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 版本信息
        version_text = "MHWPM v1.5.2 ©杭州公式人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 10))
        
        # 公司logo区域
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        # 导入并使用logo处理器
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
            print("[Main] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
    def create_rounded_button(self, parent, main_text, sub_text, command, bg_color):
        """
        创建圆角按钮效果
        
        Args:
            parent: 父容器
            main_text: 主要文本
            sub_text: 副文本
            command: 点击回调函数
            bg_color: 背景颜色
        """
        canvas = tk.Canvas(parent, width=350, height=150, highlightthickness=0, 
                          bg='white', relief='flat')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绘制圆角矩形背景
        self.draw_rounded_rectangle(canvas, bg_color)
        
        # 添加文本
        canvas.create_text(175, 60, text=main_text, font=self.button_font, 
                          fill='#333333', anchor='center')
        canvas.create_text(175, 100, text=sub_text, font=self.button_sub_font, 
                          fill='#666666', anchor='center')
        
        # 绑定事件
        canvas.bind("<Button-1>", lambda e: command())
        canvas.bind("<Enter>", lambda e: self.on_button_enter(canvas, bg_color, main_text, sub_text))
        canvas.bind("<Leave>", lambda e: self.on_button_leave(canvas, bg_color, main_text, sub_text))
    
    def draw_rounded_rectangle(self, canvas, bg_color):
        """
        绘制圆角矩形
        
        Args:
            canvas: Canvas对象
            bg_color: 背景颜色
        """
        # 设置圆角半径
        radius = 20  # 增大圆角半径
        width = 350   # 新的按钮宽度
        height = 150  # 新的按钮高度
        
        # 清空画布
        canvas.delete("all")
        
        # 绘制圆角矩形的各个部分
        # 主体矩形
        canvas.create_rectangle(radius, 0, width-radius, height, 
                            fill=bg_color, outline=bg_color)
        canvas.create_rectangle(0, radius, width, height-radius, 
                            fill=bg_color, outline=bg_color)
        
        # 四个圆角
        canvas.create_arc(0, 0, 2*radius, 2*radius, 
                        start=90, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(width-2*radius, 0, width, 2*radius, 
                        start=0, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(0, height-2*radius, 2*radius, height, 
                        start=180, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(width-2*radius, height-2*radius, width, height, 
                        start=270, extent=90, fill=bg_color, outline=bg_color)
    
    def on_button_enter(self, canvas, original_color, main_text, sub_text):
        """鼠标悬停效果"""
        hover_color = '#b0b0b0'  # 灰色悬停效果
        canvas.configure(bg='white')
        self.draw_rounded_rectangle(canvas, hover_color)
        canvas.create_text(175, 60, text=main_text, font=self.button_font, 
                          fill='#333333', anchor='center')
        canvas.create_text(175, 100, text=sub_text, font=self.button_sub_font, 
                          fill='#666666', anchor='center')
        
    def on_button_leave(self, canvas, original_color, main_text, sub_text):
        """鼠标离开效果"""
        canvas.configure(bg='white')
        self.draw_rounded_rectangle(canvas, original_color)
        canvas.create_text(175, 60, text=main_text, font=self.button_font, 
                          fill='#333333', anchor='center')
        canvas.create_text(175, 100, text=sub_text, font=self.button_sub_font, 
                          fill='#666666', anchor='center')
        
    def setup_force_exit_mechanism(self):
        """设置强制退出机制"""
        # 键盘快捷键强制退出
        self.root.bind('<Control-Alt-q>', lambda e: self.force_exit())
        self.root.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        self.root.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        # 添加隐藏的强制退出区域（右上角小区域）
        exit_zone = tk.Frame(self.root, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)  # 放在右上角
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        # 连续点击计数器用于紧急退出
        self.click_count = 0
        self.last_click_time = 0
        
    def show_exit_confirmation(self):
        """显示退出确认对话框"""
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出包装机程序吗？\n\n"
            "退出将断开PLC连接并关闭所有功能。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        """强制退出程序"""
        try:
            print("执行强制退出...")
            self.on_closing()
        except Exception as e:
            print(f"强制退出时发生错误: {e}")
            import os
            os._exit(0)  # 强制终止进程
    
    def start_modbus_connection(self):
        """在后台线程中启动Modbus连接"""
        def connect_thread():
            try:
                # 创建Modbus客户端（使用默认配置）
                self.modbus_client = create_modbus_client(
                    host="192.168.6.6",  # 默认PLC IP地址
                    port=502,              # 默认Modbus TCP端口
                    timeout=3              # 3秒超时
                )
                
                # 尝试连接
                success, message = self.modbus_client.connect()
                
                # 在主线程中更新界面
                self.root.after(0, self.handle_modbus_connection_result, success, message)
                
            except Exception as e:
                error_msg = f"Modbus连接初始化失败：{str(e)}"
                self.root.after(0, self.handle_modbus_connection_result, False, error_msg)
        
        # 启动连接线程
        connection_thread = threading.Thread(target=connect_thread, daemon=True)
        connection_thread.start()
    
    def handle_modbus_connection_result(self, success, message):
        """处理Modbus连接结果"""
        self.connection_status = success
        
        if success:
            if self.status_label is not None:
                self.status_label.config(text="已连接", fg='#00aa00')
        else:
            if self.status_label is not None:
                self.status_label.config(text="未连接", fg='#ff0000')
    
    def test_backend_api_connection_basic(self):
        """
        基础的API连接测试函数（被重试包装器调用）
        
        Returns:
            tuple[bool, str]: (成功状态, 消息)
        """
        if not WEBAPI_CLIENT_AVAILABLE:
            return False, "WebAPI客户端模块不可用"
        
        # 调用原始的API测试函数
        return test_webapi_connection()
    
    def test_backend_api_connection(self, force_retry=False, max_attempts=3):
        """
        测试后端API连接
        
        Args:
            force_retry: 是否强制重试
            max_attempts: 最大重试次数
        """
        def test_api_thread():
            try:
                if force_retry:
                    self.api_retry_count += 1
                    print(f"强制重试API连接，第 {self.api_retry_count} 次")
                
                # 使用重试包装器调用API测试函数
                success, message = retry_api_call(
                    self.test_backend_api_connection_basic,
                    max_attempts=max_attempts
                )
                
                # 如果成功，重置重试计数器
                if success:
                    self.api_retry_count = 0
                
                self.root.after(0, self.handle_api_connection_result, success, message, force_retry)
                
            except Exception as e:
                error_msg = f"API连接测试异常：{str(e)}"
                self.root.after(0, self.handle_api_connection_result, False, error_msg, force_retry)
        
        # 更新状态为检测中
        status_text = "重试中..." if force_retry else "检测中..."
        if self.api_status_label is not None:
            self.api_status_label.config(text=status_text, fg='#ff6600')
        
        # 启动测试线程
        test_thread = threading.Thread(target=test_api_thread, daemon=True)
        test_thread.start()
    
    def handle_api_connection_result(self, success, message, was_retry=False):
        """
        处理API连接测试结果
        
        Args:
            success: 连接是否成功
            message: 结果消息
            was_retry: 是否是重试操作
        """
        self.api_connection_status = success
        
        if success:
            if self.api_status_label is not None:
                self.api_status_label.config(text="已连接", fg='#00aa00')
            if was_retry:
                messagebox.showinfo("连接成功", f"API连接重试成功！\n{message}")
        else:
            if self.api_status_label is not None:
                self.api_status_label.config(text="未连接", fg='#ff0000')
            if was_retry:
                messagebox.showerror("连接失败", f"API连接重试失败！\n{message}")
        
        print(f"API连接测试结果: {'成功' if success else '失败'} - {message}")
    
    def test_custom_api_function(self, api_func: Callable, *args, **kwargs):
        """
        测试自定义API函数（通用重试包装器）
        
        Args:
            api_func: 要测试的API函数指针
            *args, **kwargs: 传递给API函数的参数
        
        Returns:
            tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 使用重试机制调用自定义API函数
            success, message = retry_api_call(api_func, 3, *args, **kwargs)
            return success, message
        except Exception as e:
            return False, f"自定义API函数调用失败: {str(e)}"
    
    def show_api_settings(self):
        """显示API配置对话框"""
        if not API_CONFIG_AVAILABLE:
            messagebox.showerror("配置不可用", "API配置模块未加载")
            return
        
        config = get_api_config()
        
        settings_window = tk.Toplevel(self.root)
        settings_window.title("后端API配置")
        settings_window.geometry("500x450")
        settings_window.configure(bg='white')
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 配置输入框变量
        host_var = tk.StringVar(value=config.host)
        port_var = tk.StringVar(value=str(config.port))
        timeout_var = tk.StringVar(value=str(config.timeout))
        protocol_var = tk.StringVar(value=config.protocol)
        
        # 标题
        tk.Label(settings_window, text="后端API连接配置", 
                font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                bg='white').pack(pady=20)
        
        # 配置项
        config_items = [
            ("主机地址:", host_var),
            ("端口:", port_var),
            ("超时时间(秒):", timeout_var),
            ("协议:", protocol_var)
        ]
        
        for label_text, var in config_items:
            frame = tk.Frame(settings_window, bg='white')
            frame.pack(pady=10, padx=20, fill=tk.X)
            tk.Label(frame, text=label_text, font=self.status_font, bg='white', width=12, anchor='w').pack(side=tk.LEFT)
            tk.Entry(frame, textvariable=var, font=self.status_font, width=25).pack(side=tk.RIGHT, padx=10)
        
        # 重试配置区域
        retry_frame = tk.LabelFrame(settings_window, text="重试配置", bg='white', fg='#333333')
        retry_frame.pack(fill=tk.X, padx=20, pady=10)
        
        retry_attempts_var = tk.StringVar(value="3")
        retry_config_frame = tk.Frame(retry_frame, bg='white')
        retry_config_frame.pack(pady=5, padx=10, fill=tk.X)
        tk.Label(retry_config_frame, text="最大重试次数:", font=self.status_font, bg='white', width=12, anchor='w').pack(side=tk.LEFT)
        tk.Entry(retry_config_frame, textvariable=retry_attempts_var, font=self.status_font, width=10).pack(side=tk.RIGHT, padx=10)
        
        # 当前配置显示
        info_frame = tk.LabelFrame(settings_window, text="当前配置", bg='white', fg='#333333')
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(info_frame, text=f"API地址: {config.base_url}", 
                font=tkFont.Font(family="微软雅黑", size=9), bg='white', fg='#666666').pack(pady=2)
        tk.Label(info_frame, text=f"重试机制: {'Tenacity库' if RETRY_AVAILABLE else '简单重试'}", 
                font=tkFont.Font(family="微软雅黑", size=9), bg='white', fg='#666666').pack(pady=2)
        tk.Label(info_frame, text=f"当前重试次数: {self.api_retry_count}", 
                font=tkFont.Font(family="微软雅黑", size=9), bg='white', fg='#666666').pack(pady=2)
        
        # 按钮区域
        button_frame = tk.Frame(settings_window, bg='white')
        button_frame.pack(pady=20)
        
        def apply_settings():
            try:
                new_host = host_var.get().strip()
                new_port = int(port_var.get().strip())
                new_timeout = int(timeout_var.get().strip())
                new_protocol = protocol_var.get().strip()
                max_attempts = int(retry_attempts_var.get().strip())
                
                # 更新配置
                set_api_config(new_host, new_port, new_timeout, new_protocol)
                
                settings_window.destroy()
                
                # 重新测试连接
                self.test_backend_api_connection(max_attempts=max_attempts)
                
                messagebox.showinfo("配置更新", f"API配置已更新，正在重新测试连接（最多重试{max_attempts}次）...")
                
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的端口号、超时时间和重试次数")
            except Exception as e:
                messagebox.showerror("配置错误", f"配置更新失败：{str(e)}")
        
        def test_with_retry():
            try:
                max_attempts = int(retry_attempts_var.get().strip())
                settings_window.destroy()
                self.test_backend_api_connection(force_retry=True, max_attempts=max_attempts)
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的重试次数")
        
        tk.Button(button_frame, text="应用", command=apply_settings,
                 font=self.status_font, bg='#4a90e2', fg='white', padx=20).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="测试连接", command=test_with_retry,
                 font=self.status_font, bg='#28a745', fg='white', padx=20).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="取消", command=settings_window.destroy,
                 font=self.status_font, bg='#e0e0e0', padx=20).pack(side=tk.LEFT, padx=10)
        
    def reconnect_modbus(self):
        """重新连接Modbus"""
        if self.status_label is not None:
            self.status_label.config(text="正在重连...", fg='#ff6600')
        self.start_modbus_connection()
    
    def scan_modbus_devices(self):
        """扫描网络中的Modbus设备（原有代码）"""
        # ... 保持原有实现
        pass
    
    def show_connection_settings(self):
        """显示连接设置对话框（原有代码）"""
        # ... 保持原有实现
        pass
    
    def show_modbus_error(self):
        """显示Modbus模块不可用的错误信息"""
        if self.status_label is not None:
            self.status_label.config(text="模块不可用", fg='#ff0000')
    
    def show_api_error(self):
        """显示API模块不可用的错误信息"""
        if self.api_status_label is not None:
            self.api_status_label.config(text="模块不可用", fg='#ff0000')
    
    def on_traditional_click(self):
        """传统模式按钮点击事件"""
        if not self.connection_status:
            messagebox.showwarning("连接警告", "PLC未连接，某些功能可能不可用！")
        
        result = messagebox.askyesno(
            "模式选择确认", 
            "您选择了传统模式\n\n"
            "传统模式特点：\n"
            "• 手动调试设置\n"
            "• 用户完全控制参数\n"
            "• 适合经验丰富的操作员\n\n"
            "是否确认进入传统模式？"
        )
    
        if not result:
            return
        
        # 发送PLC模式切换命令
        if self.modbus_client and self.connection_status:
            try:
                from plc_addresses import GLOBAL_CONTROL_ADDRESSES
                
                # 先向AI/传统模式地址30发送=0命令
                print("发送传统模式=0命令")
                if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['AIMode'], False):
                    messagebox.showerror("PLC通信失败", "发送AI模式关闭命令失败")
                    return
                
                print("✅ 传统模式PLC命令发送成功")
                messagebox.showinfo("模式切换成功", "PLC已切换至传统模式")
                
            except ImportError as e:
                print(f"警告：无法导入PLC地址模块: {e}")
                messagebox.showwarning("模块错误", "无法导入PLC地址配置")
            except Exception as e:
                error_msg = f"PLC模式切换异常: {str(e)}"
                print(f"错误: {error_msg}")
                messagebox.showerror("PLC操作失败", error_msg)
        else:
            messagebox.showwarning("PLC未连接", "PLC未连接，无法发送模式切换命令")
        
        # 打开传统模式界面
        if TRADITIONAL_MODE_AVAILABLE:
            try:
                # 隐藏主界面
                self.hide_main_window()
                
                # 创建新的顶层窗口专门给传统模式使用
                traditional_window = tk.Toplevel()
                traditional_window.title("六头线性调节秤 V1.8 - 传统模式")
                traditional_window.geometry("1400x900")
                traditional_window.configure(bg='#ffffff')
                traditional_window.minsize(1200, 800)
                
                # 让新窗口显示在前面并获得焦点
                traditional_window.lift()
                traditional_window.focus_force()
                
                # 设置窗口关闭事件
                def on_traditional_close():
                    traditional_window.destroy()
                    self.show_main_window()
                    self.cleanup_traditional_interface()
                
                traditional_window.protocol("WM_DELETE_WINDOW", on_traditional_close)
                
                # 创建传统模式界面实例，使用新窗口作为父窗口
                self.traditional_interface = SimpleTianTengInterface(
                    parent=traditional_window, 
                    main_window=self,
                    modbus_client=self.modbus_client
                )
                print("传统模式界面已打开在新窗口中")
                
            except Exception as e:
                # 如果出错，重新显示主界面
                self.show_main_window()
                messagebox.showerror("界面错误", f"打开传统模式界面失败：{str(e)}")
        else:
            messagebox.showerror("模块错误", "传统模式界面模块未加载，无法打开传统模式")
    
    def on_ai_click(self):
        """AI模式按钮点击事件"""
        # 检查依赖状态
        if not self.connection_status:
            messagebox.showwarning("PLC连接警告", "PLC未连接，AI模式的某些功能将不可用！")
        
        if not self.api_connection_status:
            result = messagebox.askyesno(
                "API连接警告", 
                "后端API服务未连接！\n\n"
                "AI模式需要后端API服务进行数据分析。\n"
                "没有API服务，AI模式将无法正常工作。\n\n"
                "是否要先尝试重新连接API？"
            )
            if result:
                # 尝试重新连接API
                self.test_backend_api_connection(force_retry=True, max_attempts=5)
                return
            else:
                # 用户选择不重连，询问是否继续
                continue_result = messagebox.askyesno(
                    "继续确认",
                    "在没有API连接的情况下，AI模式功能将受限。\n\n"
                    "是否仍要继续？"
                )
                if not continue_result:
                    return
        
        result = messagebox.askyesno(
            "模式选择确认", 
            "您选择了AI模式\n\n"
            "AI模式特点：\n"
            "• 自动学习优化\n"
            "• 智能参数调节\n"
            "• 自适应包装策略\n"
            "• 提高生产效率\n"
            "• 依赖后端API服务\n"
            "• 增强重试机制\n\n"
            "是否确认进入AI模式？"
        )
        
        if result:
            print("进入AI模式")
        
            # 发送PLC模式切换命令
            if self.modbus_client and self.connection_status:
                try:
                    from plc_addresses import GLOBAL_CONTROL_ADDRESSES

                    # 再向AI模式地址20发送=1命令
                    print("发送AI模式=1命令")
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['AIMode'], True):
                        messagebox.showerror("PLC通信失败", "发送AI模式启用命令失败")
                        return

                    print("✅ AI模式PLC命令发送成功")

                except ImportError as e:
                    print(f"警告：无法导入PLC地址模块: {e}")
                    messagebox.showwarning("模块错误", "无法导入PLC地址配置")
                except Exception as e:
                    error_msg = f"PLC模式切换异常: {str(e)}"
                    print(f"错误: {error_msg}")
                    messagebox.showerror("PLC操作失败", error_msg)
            else:
                messagebox.showwarning("PLC未连接", "PLC未连接，无法发送模式切换命令")
                
            try:
                # 隐藏主界面
                self.hide_main_window()
                
                # 创建AI模式界面窗口，并传递主窗口引用和modbus_client
                ai_window = AIModeInterface(parent=self.root, main_window=self)
                print("AI模式界面已打开，主界面已隐藏")
            except Exception as e:
                # 如果出错，重新显示主界面
                self.show_main_window()
                messagebox.showerror("界面错误", f"打开AI模式界面失败：{str(e)}")
    
    def show_main_window(self):
        """显示主窗口的便捷方法"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            print("主窗口已显示")
        except Exception as e:
            print(f"显示主窗口时发生错误: {e}")
    
    def hide_main_window(self):
        """隐藏主窗口的便捷方法"""
        try:
            self.root.withdraw()
            print("主窗口已隐藏")
        except Exception as e:
            print(f"隐藏主窗口时发生错误: {e}")

    def cleanup_traditional_interface(self):
        """清理传统模式界面资源"""
        if self.traditional_interface:
            try:
                if hasattr(self.traditional_interface, 'cleanup'):
                    self.traditional_interface.cleanup()
            except Exception as e:
                print(f"清理传统模式界面时出错: {e}")
            self.traditional_interface = None
    
    def on_closing(self):
        """程序关闭时的清理工作"""
        try:
            # 清理传统模式界面
            self.cleanup_traditional_interface()   
            
            # 断开Modbus连接
            if self.modbus_client and self.connection_status:
                self.modbus_client.disconnect()
                print("Modbus连接已断开")
        except Exception as e:
            print(f"关闭时发生错误: {e}")
        finally:
            self.root.destroy()


def center_window(root):
    """将窗口居中显示"""
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')


def main():
    """主函数 - 程序入口点"""
    print("=" * 60)
    print("🚀 启动包装机")
    print("=" * 60)
    
    # 创建主窗口
    root = tk.Tk()
    
    # 创建应用程序实例
    app = PackagingMachineGUI(root)
    
    # 设置窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 居中显示窗口
    center_window(root)
    
    # 启动GUI主循环
    root.mainloop()


if __name__ == "__main__":
    main()