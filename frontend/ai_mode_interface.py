#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模式界面 - 自学习自适应 - 前端版本
包装机AI模式操作界面，集成后端API服务

功能特点：
1. 目标重量设置
2. 包装数量设置  
3. 物料选择和管理
4. AI生产控制（连接后端API）
5. 清理和重置功能
6. 快加时间测定功能
7. 增强的放料+清零功能（带弹窗确认）
8. 清料功能（三个弹窗流程）

文件名：ai_mode_interface.py
作者：AI助手
创建日期：2025-07-22
更新日期：2025-07-24（增加清料功能）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time

# 导入后端API客户端模块
try:
    from clients.webapi_client import analyze_target_weight
    WEBAPI_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入WebAPI客户端模块: {e}")
    WEBAPI_AVAILABLE = False

# 导入PLC操作模块
try:
    from plc_operations import create_plc_operations
    PLC_OPERATIONS_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入PLC操作模块: {e}")
    print(f"详细错误: {str(e)}")
    PLC_OPERATIONS_AVAILABLE = False
    # 定义一个空的函数以避免 NameError
    def create_plc_operations(client):
        return None

# 导入清料控制器模块
try:
    from material_cleaning_controller import create_material_cleaning_controller
    CLEANING_CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入清料控制器模块: {e}")
    print(f"详细错误: {str(e)}")
    CLEANING_CONTROLLER_AVAILABLE = False
    # 定义一个空的函数以避免 NameError
    def create_material_cleaning_controller(client):
        return None

# 导入Modbus客户端
try:
    from modbus_client import ModbusClient
    MODBUS_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入Modbus客户端模块: {e}")
    MODBUS_CLIENT_AVAILABLE = False

# 导入API配置
try:
    from config.api_config import get_api_config
    API_CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入API配置模块: {e}")
    API_CONFIG_AVAILABLE = False

class AIModeInterface:
    """
    AI模式界面类 - 前端版本
    
    负责：
    1. 创建AI模式的用户界面
    2. 处理用户输入和交互
    3. 提供参数设置功能
    4. 管理物料选择
    5. 执行AI生产流程（通过后端API）
    6. 快加时间测定控制
    7. 增强的放料+清零功能
    8. 清料功能控制
    """
    
    def __init__(self, parent=None, main_window=None):
        """
        初始化AI模式界面
        
        Args:
            parent: 父窗口对象，如果为None则创建独立窗口
            main_window: 主程序窗口引用，用于返回首页时显示
        """
        # 保存主窗口引用
        self.main_window = main_window
        
        # 获取主窗口的modbus_client引用
        self.modbus_client = None
        if main_window and hasattr(main_window, 'modbus_client'):
            self.modbus_client = main_window.modbus_client
        
        # 创建PLC操作实例
        self.plc_operations = None
        if self.modbus_client and PLC_OPERATIONS_AVAILABLE:
            try:
                self.plc_operations = create_plc_operations(self.modbus_client)
                print("PLC操作模块已成功初始化")
            except Exception as e:
                print(f"PLC操作模块初始化失败: {e}")
                self.plc_operations = None
        
        # 创建清料控制器实例
        self.cleaning_controller = None
        if self.modbus_client and CLEANING_CONTROLLER_AVAILABLE:
            try:
                self.cleaning_controller = create_material_cleaning_controller(self.modbus_client)
                print("清料控制器已成功初始化")
            except Exception as e:
                print(f"清料控制器初始化失败: {e}")
                self.cleaning_controller = None
        
        # 创建主窗口或使用父窗口
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        # 界面变量
        self.weight_var = tk.StringVar()           # 目标重量变量
        self.quantity_var = tk.StringVar()         # 包装数量变量
        self.material_var = tk.StringVar()         # 物料选择变量
        
        # 预设物料列表（示例数据）
        self.material_list = [
            "请选择已记录物料",
            "大米 - 密度1.2g/cm³",
            "小麦 - 密度1.4g/cm³", 
            "玉米 - 密度1.3g/cm³",
            "黄豆 - 密度1.1g/cm³",
            "绿豆 - 密度1.2g/cm³",
            "红豆 - 密度1.15g/cm³"
        ]
        
        # 快加时间测定控制器（新增）
        self.coarse_time_controller = None
        
        # 获取API配置
        self.api_config = None
        if API_CONFIG_AVAILABLE:
            self.api_config = get_api_config()
        
        # 设置窗口属性
        self.setup_window()
        
        # 设置字体
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 居中显示窗口（新增）
        self.center_window()
    
    def center_window(self):
        """将AI模式界面窗口居中显示"""
        try:
            # 确保窗口已经完全创建
            self.root.update_idletasks()
            
            # 获取窗口尺寸
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # 如果窗口尺寸为1（未正确获取），使用设定的尺寸
            if width <= 1 or height <= 1:
                width = 950
                height = 750
            
            # 计算居中位置
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            # 设置窗口位置
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
            print(f"AI模式界面已居中显示: {width}x{height}+{x}+{y}")
            
        except Exception as e:
            print(f"AI模式界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("1000x750")
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.title("AI模式 - 自学习自适应 (前端)")
        self.root.geometry("950x750")
        self.root.configure(bg='#f8f9fa')
        self.root.resizable(True, True)
        
        # 绑定窗口关闭事件（无论是否为主窗口都需要处理）
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置界面字体"""
        # 标题字体
        self.title_font = tkFont.Font(family="微软雅黑", size=20, weight="bold")
        
        # 标签字体
        self.label_font = tkFont.Font(family="微软雅黑", size=14, weight="bold")
        
        # 输入框字体
        self.entry_font = tkFont.Font(family="微软雅黑", size=12)
        
        # 按钮字体
        self.button_font = tkFont.Font(family="微软雅黑", size=12, weight="bold")
        
        # 小按钮字体
        self.small_button_font = tkFont.Font(family="微软雅黑", size=10)
        
        # 底部信息字体
        self.footer_font = tkFont.Font(family="微软雅黑", size=10)
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='#f8f9fa')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=30)
        
        # 创建标题栏
        self.create_title_bar(main_frame)
        
        # 创建状态信息栏
        self.create_status_bar(main_frame)
        
        # 创建参数设置区域
        self.create_parameter_section(main_frame)
        
        # 创建控制按钮区域
        self.create_control_section(main_frame)
        
        # 创建底部信息区域
        self.create_footer_section(main_frame)
    
    def create_title_bar(self, parent):
        """
        创建标题栏
        
        Args:
            parent: 父容器
        """
        # 标题栏容器
        title_frame = tk.Frame(parent, bg='#f8f9fa')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧标题和AI图标
        left_frame = tk.Frame(title_frame, bg='#f8f9fa')
        left_frame.pack(side=tk.LEFT)
        
        # AI模式标题
        title_label = tk.Label(left_frame, text="AI模式 - 自学习自适应", 
                             font=self.title_font, bg='#f8f9fa', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # 前端标识
        frontend_label = tk.Label(left_frame, text="(前端)", 
                                font=tkFont.Font(family="微软雅黑", size=10),
                                bg='#f8f9fa', fg='#666666')
        frontend_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # AI图标（用蓝色圆形背景 + AI文字模拟）
        ai_icon = tk.Button(left_frame, text="🤖AI", 
                          font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                          bg='#4a90e2', fg='white', width=4, height=1,
                          relief='flat', bd=0,
                          command=self.on_ai_icon_click)
        ai_icon.pack(side=tk.LEFT, padx=(15, 0))
        
        # 右侧按钮区域
        right_frame = tk.Frame(title_frame, bg='#f8f9fa')
        right_frame.pack(side=tk.RIGHT)
        
        # 返回首页按钮
        home_btn = tk.Button(right_frame, text="返回首页", 
                           font=self.small_button_font,
                           bg='#e9ecef', fg='#333333',
                           relief='flat', bd=1,
                           padx=20, pady=8,
                           command=self.on_home_click)
        home_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # API设置按钮
        api_btn = tk.Button(right_frame, text="API设置", 
                          font=self.small_button_font,
                          bg='#d1ecf1', fg='#333333',
                          relief='flat', bd=1,
                          padx=20, pady=8,
                          command=self.on_api_settings_click)
        api_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 设置按钮
        settings_btn = tk.Button(right_frame, text="设置", 
                               font=self.small_button_font,
                               bg='#e9ecef', fg='#333333',
                               relief='flat', bd=1,
                               padx=20, pady=8,
                               command=self.on_settings_click)
        settings_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线（放在标题栏下方）
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 15))
    
    def create_status_bar(self, parent):
        """
        创建状态信息栏
        
        Args:
            parent: 父容器
        """
        status_frame = tk.Frame(parent, bg='#f8f9fa', relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # PLC连接状态
        plc_frame = tk.Frame(status_frame, bg='#f8f9fa')
        plc_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        tk.Label(plc_frame, text="PLC:", font=self.small_button_font, 
                bg='#f8f9fa', fg='#333333').pack(side=tk.LEFT)
        
        plc_status = "已连接" if (self.modbus_client and self.modbus_client.is_connected) else "未连接"
        plc_color = '#00aa00' if (self.modbus_client and self.modbus_client.is_connected) else '#ff0000'
        
        tk.Label(plc_frame, text=plc_status, font=self.small_button_font,
                bg='#f8f9fa', fg=plc_color).pack(side=tk.LEFT, padx=(5, 0))
        
        # 分隔线
        tk.Frame(status_frame, width=2, bg='#ddd').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 后端API状态
        api_frame = tk.Frame(status_frame, bg='#f8f9fa')
        api_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        tk.Label(api_frame, text="后端API:", font=self.small_button_font, 
                bg='#f8f9fa', fg='#333333').pack(side=tk.LEFT)
        
        self.api_status_label = tk.Label(api_frame, text="检测中...", font=self.small_button_font,
                                       bg='#f8f9fa', fg='#ff6600')
        self.api_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # API地址显示
        if self.api_config:
            tk.Label(api_frame, text=f"({self.api_config.base_url})", 
                    font=tkFont.Font(family="微软雅黑", size=8),
                    bg='#f8f9fa', fg='#888888').pack(side=tk.LEFT, padx=(5, 0))
        
        # 测试API连接按钮
        test_api_btn = tk.Button(status_frame, text="测试API", 
                               font=tkFont.Font(family="微软雅黑", size=9),
                               bg='#28a745', fg='white',
                               command=self.test_api_connection)
        test_api_btn.pack(side=tk.RIGHT, padx=10, pady=2)
        
        # 初始测试API连接
        self.test_api_connection()
    
    def create_parameter_section(self, parent):
        """
        创建参数设置区域
        
        Args:
            parent: 父容器
        """
        # 参数设置容器
        param_frame = tk.Frame(parent, bg='#f8f9fa')
        param_frame.pack(fill=tk.X, pady=(40, 60))
        
        # 三个参数设置区域的容器
        params_container = tk.Frame(param_frame, bg='#f8f9fa')
        params_container.pack()
        
        # 每包重量设置区域
        self.create_weight_section(params_container)
        
        # 包装数量设置区域
        self.create_quantity_section(params_container)
        
        # 物料选择区域
        self.create_material_section(params_container)
    
    def create_weight_section(self, parent):
        """
        创建每包重量设置区域
        
        Args:
            parent: 父容器
        """
        # 每包重量容器
        weight_frame = tk.Frame(parent, bg='#f8f9fa')
        weight_frame.pack(side=tk.LEFT, padx=(0, 60))
        
        # 标题标签
        weight_title = tk.Label(weight_frame, text="每包重量", 
                              font=self.label_font, bg='#f8f9fa', fg='#333333')
        weight_title.pack(anchor='w')
        
        # 单位标签
        unit_label = tk.Label(weight_frame, text="克g", 
                            font=tkFont.Font(family="微软雅黑", size=12),
                            bg='#f8f9fa', fg='#666666')
        unit_label.pack(anchor='w', pady=(0, 10))
        
        # 输入框
        weight_entry = tk.Entry(weight_frame, textvariable=self.weight_var,
                              font=self.entry_font,
                              width=25,
                              relief='solid', bd=1,
                              bg='white', fg='#333333')
        weight_entry.pack(ipady=8)
        
        # 设置输入框占位符效果
        self.setup_placeholder(weight_entry, "请输入目标重量克数")
    
    def create_quantity_section(self, parent):
        """
        创建包装数量设置区域
        
        Args:
            parent: 父容器
        """
        # 包装数量容器
        quantity_frame = tk.Frame(parent, bg='#f8f9fa')
        quantity_frame.pack(side=tk.LEFT, padx=(0, 60))
        
        # 标题标签
        quantity_title = tk.Label(quantity_frame, text="包装数量", 
                                font=self.label_font, bg='#f8f9fa', fg='#333333')
        quantity_title.pack(anchor='w')
        
        # 空白区域（对齐用）
        tk.Label(quantity_frame, text=" ", 
               font=tkFont.Font(family="微软雅黑", size=12),
               bg='#f8f9fa').pack(pady=(0, 10))
        
        # 输入框
        quantity_entry = tk.Entry(quantity_frame, textvariable=self.quantity_var,
                                font=self.entry_font,
                                width=25,
                                relief='solid', bd=1,
                                bg='white', fg='#333333')
        quantity_entry.pack(ipady=8)
        
        # 设置输入框占位符效果
        self.setup_placeholder(quantity_entry, "请输入所需包装数量")
    
    def create_material_section(self, parent):
        """
        创建物料选择区域
        
        Args:
            parent: 父容器
        """
        # 物料选择容器
        material_frame = tk.Frame(parent, bg='#f8f9fa')
        material_frame.pack(side=tk.LEFT)
        
        # 标题和新增按钮的容器
        title_frame = tk.Frame(material_frame, bg='#f8f9fa')
        title_frame.pack(fill=tk.X)
        
        # 标题标签
        material_title = tk.Label(title_frame, text="物料选择", 
                                font=self.label_font, bg='#f8f9fa', fg='#333333')
        material_title.pack(side=tk.LEFT)
        
        # 新增物料按钮
        new_material_btn = tk.Button(title_frame, text="新增物料", 
                                   font=tkFont.Font(family="微软雅黑", size=10),
                                   bg='#28a745', fg='white',
                                   relief='flat', bd=0,
                                   padx=15, pady=5,
                                   command=self.on_new_material_click)
        new_material_btn.pack(side=tk.RIGHT)
        
        # 空白区域（对齐用）
        tk.Label(material_frame, text=" ", 
               font=tkFont.Font(family="微软雅黑", size=12),
               bg='#f8f9fa').pack(pady=(0, 10))
        
        # 下拉选择框
        material_combobox = ttk.Combobox(material_frame, textvariable=self.material_var,
                                       font=self.entry_font,
                                       width=23,
                                       values=self.material_list,
                                       state='readonly')
        material_combobox.pack(ipady=5)
        material_combobox.set(self.material_list[0])  # 设置默认值
    
    def create_control_section(self, parent):
        """
        创建控制按钮区域
        
        Args:
            parent: 父容器
        """
        # 控制按钮容器
        control_frame = tk.Frame(parent, bg='#f8f9fa')
        control_frame.pack(fill=tk.X, pady=(40, 60))
        
        # 左侧按钮区域
        left_buttons = tk.Frame(control_frame, bg='#f8f9fa')
        left_buttons.pack(side=tk.LEFT)
        
        # 放料+清零按钮
        feed_clear_btn = tk.Button(left_buttons, text="放料+清零", 
                                 font=self.button_font,
                                 bg='#6c757d', fg='white',
                                 relief='flat', bd=0,
                                 padx=25, pady=12,
                                 command=self.on_feed_clear_click)
        feed_clear_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 清料按钮
        clear_btn = tk.Button(left_buttons, text="清料", 
                            font=self.button_font,
                            bg='#6c757d', fg='white',
                            relief='flat', bd=0,
                            padx=25, pady=12,
                            command=self.on_clear_click)
        clear_btn.pack(side=tk.LEFT)
        
        # 右侧主要操作按钮
        right_buttons = tk.Frame(control_frame, bg='#f8f9fa')
        right_buttons.pack(side=tk.RIGHT)
        
        # 开始AI生产按钮
        start_ai_btn = tk.Button(right_buttons, text="开始AI生产", 
                               font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=40, pady=15,
                               command=self.on_start_ai_click)
        start_ai_btn.pack()
    
    def create_footer_section(self, parent):
        """
        创建底部信息区域
        
        Args:
            parent: 父容器
        """
        # 底部信息容器
        footer_frame = tk.Frame(parent, bg='#f8f9fa')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        # 版本信息
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='#f8f9fa', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        # 架构信息
        arch_text = "前后端分离架构 | AI分析由后端API服务提供"
        arch_label = tk.Label(footer_frame, text=arch_text, 
                            font=tkFont.Font(family="微软雅黑", size=9), 
                            bg='#f8f9fa', fg='#aaaaaa')
        arch_label.pack(pady=(0, 10))
        
        # 公司logo区域
        logo_frame = tk.Frame(footer_frame, bg='#f8f9fa')
        logo_frame.pack()
        
        # algorumla logo
        algorumla_label = tk.Label(logo_frame, text="algorumla", 
                                 font=tkFont.Font(family="Arial", size=12, weight="bold"), 
                                 bg='#f8f9fa', fg='#4a90e2')
        algorumla_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # TIAN TENG logo
        tianteng_label = tk.Label(logo_frame, text="TIAN TENG", 
                                font=tkFont.Font(family="Arial", size=12, weight="bold"), 
                                bg='#f8f9fa', fg='#333333')
        tianteng_label.pack(side=tk.LEFT)
    
    def setup_placeholder(self, entry_widget, placeholder_text):
        """
        为输入框设置占位符效果
        
        Args:
            entry_widget: 输入框组件
            placeholder_text: 占位符文本
        """
        def on_focus_in(event):
            """输入框获得焦点时的处理"""
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            """输入框失去焦点时的处理"""
            if entry_widget.get() == '':
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        # 设置初始占位符
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        # 绑定事件
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    # 以下是按钮事件处理函数
    
    def test_api_connection(self):
        """测试后端API连接"""
        def test_thread():
            try:
                if WEBAPI_AVAILABLE:
                    from clients.webapi_client import test_webapi_connection
                    success, message = test_webapi_connection()
                    self.root.after(0, self.handle_api_test_result, success, message)
                else:
                    self.root.after(0, self.handle_api_test_result, False, "WebAPI客户端模块不可用")
            except Exception as e:
                error_msg = f"API连接测试异常：{str(e)}"
                self.root.after(0, self.handle_api_test_result, False, error_msg)
        
        # 更新状态为检测中
        self.api_status_label.config(text="检测中...", fg='#ff6600')
        
        # 启动测试线程
        threading.Thread(target=test_thread, daemon=True).start()
    
    def handle_api_test_result(self, success, message):
        """处理API测试结果"""
        if success:
            self.api_status_label.config(text="已连接", fg='#00aa00')
        else:
            self.api_status_label.config(text="未连接", fg='#ff0000')
    
    def on_ai_icon_click(self):
        """AI图标按钮点击事件"""
        print("点击了AI图标")
        messagebox.showinfo("AI功能", "AI语音助手功能 - 前端版本")
    
    def on_home_click(self):
        """返回首页按钮点击事件"""
        print("点击了返回首页")
        
        # 如果有快加时间测定控制器正在运行，先停止它
        if self.coarse_time_controller:
            try:
                self.coarse_time_controller.stop_all_coarse_time_test()
                self.coarse_time_controller.dispose()
                self.coarse_time_controller = None
                print("快加时间测定控制器已停止")
            except Exception as e:
                print(f"停止快加时间测定控制器时发生错误: {e}")
        
        # 如果有清料控制器正在运行，先停止它
        if self.cleaning_controller:
            try:
                self.cleaning_controller.dispose()
                self.cleaning_controller = None
                print("清料控制器已停止")
            except Exception as e:
                print(f"停止清料控制器时发生错误: {e}")
        
        # 如果有主窗口引用，重新显示主窗口
        if self.main_window:
            try:
                # 使用主窗口的便捷方法显示窗口
                if hasattr(self.main_window, 'show_main_window'):
                    self.main_window.show_main_window()
                else:
                    # 备用方式：直接操作root属性
                    if hasattr(self.main_window, 'root'):
                        self.main_window.root.deiconify()
                        self.main_window.root.lift()
                        self.main_window.root.focus_force()
                    else:
                        print("警告：无法显示主窗口")
            except Exception as e:
                print(f"显示主窗口时发生错误: {e}")
        
        # 关闭AI模式界面
        self.root.destroy()
    
    def on_api_settings_click(self):
        """API设置按钮点击事件"""
        print("点击了API设置")
        if API_CONFIG_AVAILABLE:
            try:
                # 导入并显示API设置界面
                self.show_api_settings_dialog()
            except Exception as e:
                messagebox.showerror("设置错误", f"打开API设置失败：{str(e)}")
        else:
            messagebox.showerror("功能不可用", "API配置模块未加载")
    
    def show_api_settings_dialog(self):
        """显示API设置对话框"""
        from config.api_config import set_api_config
        
        settings_window = tk.Toplevel(self.root)
        settings_window.title("后端API设置")
        settings_window.geometry("500x400")
        settings_window.configure(bg='white')
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 配置变量
        host_var = tk.StringVar(value=self.api_config.host if self.api_config else "localhost")
        port_var = tk.StringVar(value=str(self.api_config.port) if self.api_config else "8080")
        timeout_var = tk.StringVar(value=str(self.api_config.timeout) if self.api_config else "10")
        protocol_var = tk.StringVar(value=self.api_config.protocol if self.api_config else "http")
        
        # 标题
        tk.Label(settings_window, text="后端API连接配置", 
                font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                bg='white').pack(pady=20)
        
        # 配置项
        config_items = [
            ("API主机地址:", host_var),
            ("API端口:", port_var),
            ("请求超时(秒):", timeout_var),
            ("协议类型:", protocol_var)
        ]
        
        for label_text, var in config_items:
            frame = tk.Frame(settings_window, bg='white')
            frame.pack(pady=10, padx=20, fill=tk.X)
            tk.Label(frame, text=label_text, font=self.small_button_font, 
                    bg='white', width=15, anchor='w').pack(side=tk.LEFT)
            tk.Entry(frame, textvariable=var, font=self.small_button_font, 
                    width=30).pack(side=tk.RIGHT, padx=10)
        
        # 当前配置显示
        info_frame = tk.LabelFrame(settings_window, text="当前配置信息", bg='white', fg='#333333')
        info_frame.pack(fill=tk.X, padx=20, pady=15)
        
        current_url = self.api_config.base_url if self.api_config else "未配置"
        tk.Label(info_frame, text=f"API基础地址: {current_url}", 
                font=tkFont.Font(family="微软雅黑", size=9), 
                bg='white', fg='#666666').pack(pady=5, anchor='w', padx=10)
        
        # 按钮区域
        button_frame = tk.Frame(settings_window, bg='white')
        button_frame.pack(pady=20)
        
        def apply_settings():
            try:
                new_host = host_var.get().strip()
                new_port = int(port_var.get().strip())
                new_timeout = int(timeout_var.get().strip())
                new_protocol = protocol_var.get().strip()
                
                # 更新配置
                set_api_config(new_host, new_port, new_timeout, new_protocol)
                
                # 重新获取配置
                self.api_config = get_api_config()
                
                settings_window.destroy()
                
                # 重新测试连接
                self.test_api_connection()
                
                messagebox.showinfo("配置更新", "API配置已更新，正在重新测试连接...")
                
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的端口号和超时时间")
            except Exception as e:
                messagebox.showerror("配置错误", f"配置更新失败：{str(e)}")
        
        tk.Button(button_frame, text="应用配置", command=apply_settings,
                 font=self.small_button_font, bg='#4a90e2', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="测试连接", command=self.test_api_connection,
                 font=self.small_button_font, bg='#28a745', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=settings_window.destroy,
                 font=self.small_button_font, bg='#e0e0e0', padx=20).pack(side=tk.LEFT, padx=5)
    
    def on_settings_click(self):
        """设置按钮点击事件"""
        print("点击了设置")
        messagebox.showinfo("设置", "AI模式设置功能")
    
    def on_new_material_click(self):
        """新增物料按钮点击事件"""
        print("点击了新增物料")
        messagebox.showinfo("新增物料", "新增物料功能")
    
    def check_plc_status(self, operation_name: str = "操作") -> bool:
        """
        检查PLC连接状态和操作模块可用性
        
        Args:
            operation_name (str): 操作名称，用于错误提示
            
        Returns:
            bool: True表示检查通过，False表示检查失败
        """
        # 检查PLC连接状态
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("连接错误", f"PLC未连接，无法执行{operation_name}！\n请检查PLC连接状态后重试。")
            return False
        
        # 检查PLC操作模块是否可用
        if not self.plc_operations:
            messagebox.showerror("模块错误", f"PLC操作模块未初始化，无法执行{operation_name}！")
            return False
        
        return True
    
    def on_feed_clear_click(self):
        """
        放料+清零按钮点击事件
        执行PLC放料和清零序列操作，包含用户确认流程
        """
        print("点击了放料+清零")
        
        # 检查PLC状态
        if not self.check_plc_status("放料+清零操作"):
            return
        
        # 创建进度弹窗 - 显示"正在放料清零，请稍后"
        progress_window = tk.Toplevel(self.root)
        progress_window.title("放料清零操作")
        progress_window.geometry("400x200")
        progress_window.configure(bg='white')
        progress_window.resizable(False, False)
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # 居中显示进度弹窗
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (200 // 2)
        progress_window.geometry(f"400x200+{x}+{y}")
        
        # 进度弹窗内容
        tk.Label(progress_window, text="正在放料清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=40)
        
        tk.Label(progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=10)
        
        # 在后台线程中执行PLC操作，避免阻塞界面
        def execute_discharge_clear_operation():
            """
            在后台线程中执行放料和清零操作
            调用plc_operations模块的execute_discharge_and_clear_sequence方法
            """
            try:
                print("[信息] 开始执行PLC放料和清零序列操作")
                
                # 调用PLC操作模块的放料和清零序列方法
                success, message = self.plc_operations.execute_discharge_and_clear_sequence()
                
                print(f"[结果] PLC操作完成: {success}, {message}")
                
                # 在主线程中处理操作结果
                self.root.after(0, self.handle_discharge_clear_result, 
                               progress_window, success, message)
                
            except Exception as e:
                error_msg = f"放料清零操作异常：{str(e)}"
                print(f"[错误] {error_msg}")
                # 在主线程中显示错误信息
                self.root.after(0, self.handle_discharge_clear_result, 
                               progress_window, False, error_msg)
        
        # 启动后台操作线程
        operation_thread = threading.Thread(target=execute_discharge_clear_operation, daemon=True)
        operation_thread.start()
        
        print("[信息] 放料清零操作已启动，正在后台执行...")
    
    def handle_discharge_clear_result(self, progress_window, success, message):
        """
        处理放料清零操作结果（在主线程中调用）
        
        Args:
            progress_window: 进度弹窗对象
            success (bool): 操作是否成功
            message (str): 操作结果消息
        """
        try:
            # 关闭进度弹窗
            progress_window.destroy()
            
            if success:
                print(f"[成功] 放料清零操作完成：{message}")
                # 显示完成确认弹窗
                self.show_discharge_clear_completion_dialog()
            else:
                print(f"[失败] 放料清零操作失败：{message}")
                # 显示错误信息
                messagebox.showerror("操作失败", f"放料清零操作失败：\n{message}")
                
        except Exception as e:
            print(f"[错误] 处理放料清零结果时发生异常：{e}")
            messagebox.showerror("系统错误", f"处理操作结果时发生异常：{str(e)}")
    
    def show_discharge_clear_completion_dialog(self):
        """
        显示放料清零完成确认对话框
        内容为"已清零，请取走余料包装袋并确认"，有"确认 已取走"按钮
        """
        # 创建完成确认弹窗
        completion_window = tk.Toplevel(self.root)
        completion_window.title("操作完成")
        completion_window.geometry("400x250")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        # 居中显示完成确认弹窗
        completion_window.update_idletasks()
        x = (completion_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (completion_window.winfo_screenheight() // 2) - (250 // 2)
        completion_window.geometry(f"400x250+{x}+{y}")
        
        # 完成确认弹窗内容
        tk.Label(completion_window, text="已清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)
        
        tk.Label(completion_window, text="请取走余料包装袋", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        tk.Label(completion_window, text="并确认", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        # 确认按钮
        def on_confirm_taken():
            """
            确认已取走按钮点击事件
            用户确认已取走余料包装袋后，关闭弹窗返回AI模式页面
            """
            print("[信息] 用户确认已取走余料包装袋")
            completion_window.destroy()  # 关闭弹窗，返回AI模式页面
        
        confirm_btn = tk.Button(completion_window, text="确认 已取走", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=40, pady=12,
                               command=on_confirm_taken)
        confirm_btn.pack(pady=30)
        
        print("[信息] 显示放料清零完成确认对话框")
    
    def on_clear_click(self):
        """
        清料按钮点击事件
        按照要求实现三个弹窗流程：确认 -> 处理中 -> 完成
        """
        print("点击了清料")
        
        # 检查PLC状态
        if not self.check_plc_status("清料操作"):
            return
        
        # 检查清料控制器是否可用
        if not self.cleaning_controller:
            messagebox.showerror("模块错误", "清料控制器未初始化，无法执行清料操作！")
            return
        
        # 显示弹窗：准备清料确认对话框
        self.show_cleaning_preparation_dialog()
    
    def show_cleaning_preparation_dialog(self):
        """
        显示清料准备确认对话框
        内容："准备清料，请放置包装袋或回收桶，点击确认开始"，按钮："确认 开始清料"
        """
        # 创建准备确认弹窗
        preparation_window = tk.Toplevel(self.root)
        preparation_window.title("清料准备")
        preparation_window.geometry("400x250")
        preparation_window.configure(bg='white')
        preparation_window.resizable(False, False)
        preparation_window.transient(self.root)
        preparation_window.grab_set()
        
        # 居中显示准备确认弹窗
        preparation_window.update_idletasks()
        x = (preparation_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (preparation_window.winfo_screenheight() // 2) - (250 // 2)
        preparation_window.geometry(f"400x250+{x}+{y}")
        
        # 准备确认弹窗内容
        tk.Label(preparation_window, text="准备清料", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)
        
        tk.Label(preparation_window, text="请放置包装袋或回收桶", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        tk.Label(preparation_window, text="点击确认开始", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        # 确认开始清料按钮
        def on_confirm_start_cleaning():
            """
            确认开始清料按钮点击事件
            关闭弹窗，显示弹窗并启动清料操作
            """
            print("[信息] 用户确认开始清料")
            preparation_window.destroy()  # 关闭图1弹窗
            
            # 显示图2弹窗并启动清料操作
            self.show_cleaning_progress_dialog()
        
        confirm_btn = tk.Button(preparation_window, text="确认 开始清料", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=40, pady=12,
                               command=on_confirm_start_cleaning)
        confirm_btn.pack(pady=30)
        
        print("[信息] 显示清料准备确认对话框")
    
    def show_cleaning_progress_dialog(self):
        """
        显示清料进行中对话框
        内容："正在清料中，请稍后"，无按钮，同时启动清料操作
        """
        # 创建清料进度弹窗
        self.cleaning_progress_window = tk.Toplevel(self.root)
        self.cleaning_progress_window.title("清料操作")
        self.cleaning_progress_window.geometry("400x200")
        self.cleaning_progress_window.configure(bg='white')
        self.cleaning_progress_window.resizable(False, False)
        self.cleaning_progress_window.transient(self.root)
        self.cleaning_progress_window.grab_set()
        
        # 居中显示清料进度弹窗
        self.cleaning_progress_window.update_idletasks()
        x = (self.cleaning_progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.cleaning_progress_window.winfo_screenheight() // 2) - (200 // 2)
        self.cleaning_progress_window.geometry(f"400x200+{x}+{y}")
        
        # 清料进度弹窗内容
        tk.Label(self.cleaning_progress_window, text="正在清料中", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=50)
        
        tk.Label(self.cleaning_progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=10)
        
        print("[信息] 显示清料进行中对话框")
        
        # 设置清料控制器事件回调
        self.cleaning_controller.on_cleaning_completed = self.on_cleaning_completed
        self.cleaning_controller.on_cleaning_failed = self.on_cleaning_failed
        self.cleaning_controller.on_log_message = self.on_cleaning_log_message
        
        # 启动清料操作
        success, message = self.cleaning_controller.start_cleaning()
        if not success:
            # 清料启动失败，关闭进度弹窗并显示错误
            self.cleaning_progress_window.destroy()
            messagebox.showerror("清料启动失败", f"无法启动清料操作：\n{message}")
            return
        
        print(f"[信息] 清料操作已启动：{message}")
    
    def on_cleaning_completed(self):
        """
        清料完成事件回调
        关闭弹窗，显示完成弹窗
        """
        print("[信息] 清料操作完成")
        
        # 在主线程中处理界面更新
        self.root.after(0, self._show_cleaning_completion_dialog)
    
    def on_cleaning_failed(self, error_message: str):
        """
        清料失败事件回调
        关闭弹窗，显示错误信息
        """
        print(f"[错误] 清料操作失败：{error_message}")
        
        # 在主线程中处理界面更新
        self.root.after(0, lambda: self._handle_cleaning_failure(error_message))
    
    def on_cleaning_log_message(self, message: str):
        """
        清料日志消息回调
        """
        print(f"[清料日志] {message}")
    
    def _show_cleaning_completion_dialog(self):
        """
        显示清料完成对话框
        内容："清料完成"，按钮："返回"
        """
        try:
            # 关闭进度弹窗
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            print(f"[错误] 关闭清料进度弹窗时发生异常：{e}")
        
        # 创建完成确认弹窗
        completion_window = tk.Toplevel(self.root)
        completion_window.title("清料完成")
        completion_window.geometry("400x200")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        # 居中显示完成确认弹窗
        completion_window.update_idletasks()
        x = (completion_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (completion_window.winfo_screenheight() // 2) - (200 // 2)
        completion_window.geometry(f"400x200+{x}+{y}")
        
        # 完成确认弹窗内容
        tk.Label(completion_window, text="清料完成", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=50)
        
        # 返回按钮
        def on_return_click():
            """
            返回按钮点击事件
            发送总清料=0命令，关闭弹窗，显示AI模式界面
            """
            print("[信息] 用户点击返回，停止清料操作")
            
            # 停止清料操作（发送总清料=0命令）
            success, message = self.cleaning_controller.stop_cleaning()
            if not success:
                print(f"[警告] 停止清料操作失败：{message}")
            else:
                print(f"[信息] 清料操作已停止：{message}")
            
            # 关闭弹窗，返回AI模式界面
            completion_window.destroy()
            print("[信息] 返回AI模式界面")
        
        return_btn = tk.Button(completion_window, text="返回", 
                              font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                              bg='#007bff', fg='white',
                              relief='flat', bd=0,
                              padx=40, pady=12,
                              command=on_return_click)
        return_btn.pack(pady=20)
        
        print("[信息] 显示清料完成确认对话框")
    
    def _handle_cleaning_failure(self, error_message: str):
        """
        处理清料失败情况
        关闭弹窗，显示错误信息
        """
        try:
            # 关闭图2进度弹窗
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            print(f"[错误] 关闭清料进度弹窗时发生异常：{e}")
        
        # 显示错误信息
        messagebox.showerror("清料操作失败", f"清料操作失败：\n{error_message}")
        
        # 尝试停止清料操作
        try:
            self.cleaning_controller.stop_cleaning()
        except Exception as e:
            print(f"[错误] 停止清料操作时发生异常：{e}")
    
    def on_start_ai_click(self):
        """开始AI生产按钮点击事件（使用后端API版本）"""
        print("点击了开始AI生产")
        
        # 获取用户输入的参数
        weight = self.weight_var.get()
        quantity = self.quantity_var.get()
        material = self.material_var.get()
        
        # 简单的输入验证
        if weight in ["", "请输入目标重量克数"]:
            messagebox.showwarning("参数缺失", "请输入目标重量")
            return
        
        if quantity in ["", "请输入所需包装数量"]:
            messagebox.showwarning("参数缺失", "请输入包装数量")
            return
        
        if material == "请选择已记录物料":
            messagebox.showwarning("参数缺失", "请选择物料类型")
            return
        
        # 验证重量是否为有效数字
        try:
            target_weight = float(weight)
            if target_weight <= 0:
                messagebox.showerror("参数错误", "目标重量必须大于0")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的目标重量数值")
            return
        
        # 验证数量是否为有效整数
        try:
            package_quantity = int(quantity)
            if package_quantity <= 0:
                messagebox.showerror("参数错误", "包装数量必须大于0")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的包装数量")
            return
        
        # 检查PLC状态
        if not self.check_plc_status("AI生产"):
            return
        
        # 检查WebAPI可用性
        if not WEBAPI_AVAILABLE:
            messagebox.showerror("WebAPI不可用", 
                               "WebAPI客户端模块未加载！\n\n"
                               "AI模式需要WebAPI客户端来连接后端分析服务。\n"
                               "请确保：\n"
                               "1. clients/webapi_client.py文件存在\n"
                               "2. 后端API服务正在运行\n"
                               "3. 网络连接正常\n"
                               "4. API配置正确")
            return
        
        # 显示确认信息
        api_url = self.api_config.base_url if self.api_config else "未配置"
        confirm_msg = f"AI生产参数确认：\n\n" \
                     f"目标重量：{target_weight} 克\n" \
                     f"包装数量：{package_quantity} 包\n" \
                     f"选择物料：{material}\n" \
                     f"后端API：{api_url}\n\n" \
                     f"⚠️ 注意：AI模式将通过后端API执行分析，\n" \
                     f"并执行完整的生产流程。\n" \
                     f"确认开始AI自适应生产？"
        
        result = messagebox.askyesno("确认AI生产", confirm_msg)
        if not result:
            return
        
        # 在后台线程执行AI生产流程，避免阻塞界面
        def ai_production_thread():
            try:
                self.execute_ai_production_sequence(target_weight, package_quantity, material)
            except Exception as e:
                # 在主线程显示错误信息
                self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"AI生产过程中发生异常：\n{str(e)}"))
        
        # 启动后台线程
        production_thread = threading.Thread(target=ai_production_thread, daemon=True)
        production_thread.start()
        
        # 显示开始信息
        messagebox.showinfo("AI生产", "AI自学习自适应生产已启动！\n正在连接后端API服务进行参数分析...")
    
    def execute_ai_production_sequence(self, target_weight: float, package_quantity: int, material: str):
        """
        执行AI生产序列（使用后端API版本）
        
        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            material (str): 物料类型
        """
        try:
            print(f"开始执行AI生产序列: 重量={target_weight}g, 数量={package_quantity}, 物料={material}")
            
            # 步骤1: 检查料斗重量并执行清料操作（如需要）
            self.root.after(0, lambda: self.show_progress_message("步骤1/4", "正在检查料斗重量状态..."))
            
            check_success, has_weight, check_message = self.plc_operations.check_any_bucket_has_weight()
            
            if not check_success:
                error_msg = f"检查料斗重量失败：{check_message}"
                self.root.after(0, lambda: messagebox.showerror("检查失败", error_msg))
                return
            
            if has_weight:
                # 显示余料清理进度弹窗
                self.root.after(0, lambda: self.show_material_cleaning_progress_dialog())
                
                # 执行清料操作
                discharge_success, discharge_message = self.plc_operations.execute_discharge_and_clear_sequence()
                
                # 关闭清理进度弹窗
                self.root.after(0, lambda: self.close_material_cleaning_progress_dialog())
                
                if not discharge_success:
                    error_msg = f"清料操作失败：{discharge_message}"
                    self.root.after(0, lambda: messagebox.showerror("清料失败", error_msg))
                    return
                
                print("清料操作完成")
                
                # 显示清零完成确认弹窗（图2样式），等待用户确认后继续
                self.root.after(0, lambda: self.show_cleaning_completion_confirmation_dialog(target_weight, package_quantity, material))
                return  # 暂停当前执行流程，等待用户确认后继续
            else:
                print("料斗无重量，跳过清料操作")
                # 直接进入后续步骤
                self.continue_ai_production_after_cleaning(target_weight, package_quantity, material)
            
        except Exception as e:
            error_msg = f"AI生产序列异常：{str(e)}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
    
    def show_material_cleaning_progress_dialog(self):
        """
        显示余料清理进度弹窗
        显示"检测到余料，正在清料处理，请稍后"
        """
        # 创建清理进度弹窗
        self.cleaning_progress_window = tk.Toplevel(self.root)
        self.cleaning_progress_window.title("清料操作")
        self.cleaning_progress_window.geometry("400x200")
        self.cleaning_progress_window.configure(bg='white')
        self.cleaning_progress_window.resizable(False, False)
        self.cleaning_progress_window.transient(self.root)
        self.cleaning_progress_window.grab_set()

        # 居中显示清理进度弹窗
        self.cleaning_progress_window.update_idletasks()
        x = (self.cleaning_progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.cleaning_progress_window.winfo_screenheight() // 2) - (200 // 2)
        self.cleaning_progress_window.geometry(f"400x200+{x}+{y}")

        # 清理进度弹窗内容
        tk.Label(self.cleaning_progress_window, text="检测到余料", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)

        tk.Label(self.cleaning_progress_window, text="正在清料处理", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        tk.Label(self.cleaning_progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        print("[信息] 显示余料清理进度弹窗")

    def close_material_cleaning_progress_dialog(self):
        """
        关闭余料清理进度弹窗
        """
        try:
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
                print("[信息] 关闭余料清理进度弹窗")
        except Exception as e:
            print(f"[错误] 关闭清理进度弹窗时发生异常：{e}")
    
    def show_cleaning_completion_confirmation_dialog(self, target_weight: float, package_quantity: int, material: str):
        """
        显示清零完成确认对话框
        内容为"已清零，请取走余料包装袋并确认"，有"确认 开始生产"按钮

        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            material (str): 物料类型
        """
        # 创建完成确认弹窗
        completion_window = tk.Toplevel(self.root)
        completion_window.title("操作完成")
        completion_window.geometry("400x250")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()

        # 居中显示完成确认弹窗
        completion_window.update_idletasks()
        x = (completion_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (completion_window.winfo_screenheight() // 2) - (250 // 2)
        completion_window.geometry(f"400x250+{x}+{y}")

        # 完成确认弹窗内容
        tk.Label(completion_window, text="已清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)

        tk.Label(completion_window, text="请取走余料包装袋", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        tk.Label(completion_window, text="并确认", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        # 确认开始生产按钮
        def on_confirm_start_production():
            """
            确认开始生产按钮点击事件
            用户确认已取走余料包装袋后，关闭弹窗并继续AI生产流程
            """
            print("[信息] 用户确认开始生产，继续AI生产流程")
            completion_window.destroy()  # 关闭弹窗

            # 在后台线程中继续执行AI生产的后续步骤
            def continue_production_thread():
                try:
                    self.continue_ai_production_after_cleaning(target_weight, package_quantity, material)
                except Exception as e:
                    # 在主线程显示错误信息
                    self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"继续AI生产过程中发生异常：\n{str(e)}"))

            # 启动后台线程继续生产
            production_thread = threading.Thread(target=continue_production_thread, daemon=True)
            production_thread.start()

        confirm_btn = tk.Button(completion_window, text="确认 开始生产", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=40, pady=12,
                               command=on_confirm_start_production)
        confirm_btn.pack(pady=30)

        print("[信息] 显示清零完成确认对话框")
    
    def continue_ai_production_after_cleaning(self, target_weight: float, package_quantity: int, material: str):
        """
        在清料操作完成后继续执行AI生产序列的后续步骤
        包括：步骤2-4（API分析、参数写入、快加时间测定）
        
        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            material (str): 物料类型
        """
        try:
            print(f"继续执行AI生产序列后续步骤: 重量={target_weight}g, 数量={package_quantity}, 物料={material}")
            
            # 步骤2: 通过后端API分析快加速度
            self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在通过后端API分析目标重量对应的快加速度..."))
            
            if not WEBAPI_AVAILABLE:
                error_msg = "WebAPI客户端模块不可用，无法进行参数分析"
                self.root.after(0, lambda: messagebox.showerror("WebAPI错误", error_msg))
                return
            
            # 调用后端API分析
            analysis_success, coarse_speed, analysis_message = analyze_target_weight(target_weight)
            
            if not analysis_success:
                error_msg = f"后端API分析失败：{analysis_message}\n\n" \
                           f"可能原因：\n" \
                           f"1. 后端API服务器未启动\n" \
                           f"2. 网络连接问题\n" \
                           f"3. API配置错误\n" \
                           f"4. 目标重量超出支持范围\n\n" \
                           f"请检查后端服务状态和API配置后重试。"
                self.root.after(0, lambda: messagebox.showerror("后端API分析失败", error_msg))
                return
            
            print(f"后端API分析完成：速度={coarse_speed}档, 消息={analysis_message}")
            
            # 步骤3: 写入参数到所有料斗
            self.root.after(0, lambda: self.show_progress_message("步骤3/4", "正在写入参数到所有料斗..."))
            
            write_success, write_message = self.plc_operations.write_bucket_parameters_all(
                target_weight=target_weight,
                coarse_speed=coarse_speed,
                fine_speed=48,
                coarse_advance=0,
                fall_value=0
            )
            
            if not write_success:
                error_msg = f"参数写入失败：{write_message}"
                self.root.after(0, lambda: messagebox.showerror("写入失败", error_msg))
                return
            
            # 步骤4: 启动快加时间测定（如果模块可用）
            self.root.after(0, lambda: self.show_progress_message("步骤4/4", "正在启动快加时间测定..."))
            
            try:
                from coarse_time_controller import create_coarse_time_test_controller
                
                # 创建快加时间测定控制器
                self.coarse_time_controller = create_coarse_time_test_controller(self.modbus_client)
                
                # 设置事件回调（修改为处理合并结果）
                def on_bucket_completed(bucket_id: int, success: bool, message: str):
                    # 检查是否是合并的自适应学习结果
                    if bucket_id == 0 and isinstance(message, dict):
                        # 这是所有料斗自适应学习完成的合并结果
                        print("[信息] 收到所有料斗自适应学习完成的合并结果")
                        # 在主线程中显示合并弹窗
                        self.root.after(0, lambda: self._show_all_buckets_completed_dialog(message))
                    elif success:
                        popup_msg = message
                        self.root.after(0, lambda: messagebox.showinfo(f"料斗{bucket_id}测定成功", popup_msg))
                        print(f"[测定成功] 料斗{bucket_id}完成")
                    else:
                        error_msg = message
                        self.root.after(0, lambda: messagebox.showerror(f"料斗{bucket_id}测定失败", error_msg))
                        print(f"[测定失败] 料斗{bucket_id}: {message}")
                
                def on_progress_update(bucket_id: int, current_attempt: int, max_attempts: int, message: str):
                    progress_msg = f"料斗{bucket_id}进度: {current_attempt}/{max_attempts} - {message}"
                    self.root.after(0, lambda: self.show_progress_message("步骤4/4", progress_msg))
                    print(f"[测定进度] {progress_msg}")
                
                def on_log_message(message: str):
                    print(f"[测定日志] {message}")
                
                # 设置事件回调
                self.coarse_time_controller.on_bucket_completed = on_bucket_completed
                self.coarse_time_controller.on_progress_update = on_progress_update
                self.coarse_time_controller.on_log_message = on_log_message
                
                # 启动快加时间测定
                test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                    target_weight, coarse_speed)
                
                if not test_success:
                    error_msg = f"启动快加时间测定失败：{test_message}"
                    self.root.after(0, lambda: messagebox.showerror("测定启动失败", error_msg))
                    # 不return，继续显示完成信息
                
                print(f"快加时间测定已启动：{test_message}")
                
            except ImportError as e:
                error_msg = f"无法导入快加时间测定模块：{str(e)}\n\n请确保相关模块文件存在"
                print(f"警告：{error_msg}")
                # 不中断流程，继续显示完成信息
            except Exception as e:
                error_msg = f"快加时间测定启动异常：{str(e)}"
                print(f"警告：{error_msg}")
                # 不中断流程，继续显示完成信息
            
            # 成功完成所有步骤
            success_message = (
                f"🎉 AI生产流程启动完成！\n\n"
                f"📊 后端API分析结果：\n"
                f"  • API地址：{self.api_config.base_url if self.api_config else '未配置'}\n"
                f"  • 目标重量：{target_weight}g\n"
                f"  • 推荐快加速度：{coarse_speed} 档\n"
                f"  • 慢加速度：48 档\n"
                f"  • 快加提前量：0\n"
                f"  • 落差值：0\n\n"
                f"📝 操作摘要：\n"
                f"  • 料斗检查：已清料\n"
                f"  • 后端API分析：{analysis_message}\n"
                f"  • 参数写入：成功写入所有6个料斗\n"
                f"  • 快加时间测定：{'已启动' if 'coarse_time_controller' in locals() else '模块不可用'}\n\n"
                f"🔍 系统正在进行自动化测定流程...\n"
                f"测定完成后将自动弹窗显示结果。"
            )
            
            self.root.after(0, lambda: messagebox.showinfo("AI生产流程启动完成", success_message))
            print("AI生产序列执行完成，后端API分析和自动化测定正在进行中")
            
        except Exception as e:
            error_msg = f"AI生产序列后续步骤异常：{str(e)}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
    
    def _show_all_buckets_completed_dialog(self, completed_states):
        """
        显示所有料斗自适应学习完成的合并弹窗
        
        Args:
            completed_states (dict): 所有已完成料斗的状态字典
        """
        try:
            # 创建合并结果弹窗
            completed_window = tk.Toplevel(self.root)
            completed_window.title("自适应学习完成")
            completed_window.geometry("700x600")
            completed_window.configure(bg='white')
            completed_window.resizable(False, False)
            completed_window.transient(self.root)
            completed_window.grab_set()
            
            # 居中显示弹窗
            completed_window.update_idletasks()
            x = (completed_window.winfo_screenwidth() // 2) - (700 // 2)
            y = (completed_window.winfo_screenheight() // 2) - (600 // 2)
            completed_window.geometry(f"700x600+{x}+{y}")
            
            # 标题
            tk.Label(completed_window, text="自适应学习阶段完成", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)
            
            # 创建滚动区域
            canvas = tk.Canvas(completed_window, bg='white', highlightthickness=0)
            scrollbar = ttk.Scrollbar(completed_window, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg='white')
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True, padx=20)
            scrollbar.pack(side="right", fill="y")
            
            # 显示每个料斗的结果
            for bucket_id in sorted(completed_states.keys()):
                state = completed_states[bucket_id]
                
                # 料斗结果框架
                bucket_frame = tk.LabelFrame(scrollable_frame, 
                                           text=f"料斗{bucket_id}", 
                                           font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                           bg='white', fg='#333333',
                                           padx=10, pady=10)
                bucket_frame.pack(fill='x', padx=10, pady=5)
                
                if state.is_success:
                    # 成功的料斗显示详细参数
                    success_label = tk.Label(bucket_frame, 
                                           text="✅ 成功", 
                                           font=tkFont.Font(family="微软雅黑", size=11, weight="bold"),
                                           bg='white', fg='#00aa00')
                    success_label.pack(anchor='w')
                    
                    # 参数信息
                    param_info = (
                        f"目标重量: {state.original_target_weight}g\n"
                        f"快加速度: {state.final_coarse_speed}档\n"
                        f"慢加速度: {state.final_fine_speed}档\n"
                        f"快加提前量: {state.final_coarse_advance}g\n"
                        f"落差值: {state.final_fall_value}g"
                    )
                    
                    param_label = tk.Label(bucket_frame, 
                                         text=param_info,
                                         font=tkFont.Font(family="微软雅黑", size=10),
                                         bg='white', fg='#666666',
                                         justify='left')
                    param_label.pack(anchor='w', pady=(5, 0))
                    
                else:
                    # 失败的料斗显示失败信息
                    failure_label = tk.Label(bucket_frame, 
                                           text="❌ 失败", 
                                           font=tkFont.Font(family="微软雅黑", size=11, weight="bold"),
                                           bg='white', fg='#ff0000')
                    failure_label.pack(anchor='w')
                    
                    failure_info = (
                        f"失败阶段: {state.failure_stage}\n"
                        f"失败原因: {state.failure_reason}"
                    )
                    
                    failure_info_label = tk.Label(bucket_frame, 
                                                text=failure_info,
                                                font=tkFont.Font(family="微软雅黑", size=10),
                                                bg='white', fg='#666666',
                                                justify='left')
                    failure_info_label.pack(anchor='w', pady=(5, 0))
            
            # 确认按钮
            def on_confirm_click():
                """确认按钮点击事件，关闭第一个弹窗，显示第二个训练完成弹窗"""
                completed_window.destroy()
                # 显示第二个训练完成弹窗
                self._show_training_completed_dialog()
            
            confirm_btn = tk.Button(completed_window, text="确认", 
                                   font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                   bg='#007bff', fg='white',
                                   relief='flat', bd=0,
                                   padx=40, pady=12,
                                   command=on_confirm_click)
            confirm_btn.pack(pady=20)
            
            print("[信息] 显示所有料斗自适应学习完成合并弹窗")
            
        except Exception as e:
            error_msg = f"显示合并完成弹窗异常: {str(e)}"
            self.logger.error(error_msg)
            print(f"[错误] {error_msg}")
    
    def _show_training_completed_dialog(self):
        """
        显示训练完成弹窗（第二个弹窗）
        包含计时器功能
        """
        try:
            # 创建训练完成弹窗
            training_window = tk.Toplevel(self.root)
            training_window.title("训练完成")
            training_window.geometry("400x300")
            training_window.configure(bg='white')
            training_window.resizable(False, False)
            training_window.transient(self.root)
            training_window.grab_set()
            
            # 居中显示弹窗
            training_window.update_idletasks()
            x = (training_window.winfo_screenwidth() // 2) - (400 // 2)
            y = (training_window.winfo_screenheight() // 2) - (300 // 2)
            training_window.geometry(f"400x300+{x}+{y}")
            
            # 训练完成标题
            tk.Label(training_window, text="训练完成", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            # 计时器显示
            self.timer_label = tk.Label(training_window, text="00:00:00", 
                                       font=tkFont.Font(family="Arial", size=24, weight="bold"),
                                       bg='white', fg='#333333')
            self.timer_label.pack(pady=20)
            
            # 开始生产按钮
            def on_start_production_click():
                """开始生产按钮点击事件"""
                training_window.destroy()
                # 停止计时器
                if hasattr(self, 'timer_running'):
                    self.timer_running = False
    
                print("[信息] 用户点击开始生产，切换到生产界面")
            
                try:
                    # 准备生产参数
                    production_params = {
                        'material_name': self.material_var.get() if self.material_var.get() != "请选择已记录物料" else "未知物料",
                        'target_weight': float(self.weight_var.get()) if self.weight_var.get() and self.weight_var.get() != "请输入目标重量克数" else 0,
                        'package_quantity': int(self.quantity_var.get()) if self.quantity_var.get() and self.quantity_var.get() != "请输入所需包装数量" else 0
                    }
                    
                    # 隐藏AI模式界面
                    self.root.withdraw()
                    
                    # 导入并创建生产界面
                    from production_interface import create_production_interface
                    production_interface = create_production_interface(self.root, self, production_params)
                    
                    print(f"生产界面已打开，参数: {production_params}")
                    
                except Exception as e:
                    # 如果出错，重新显示AI模式界面
                    self.root.deiconify()
                    error_msg = f"打开生产界面失败：{str(e)}"
                    print(f"[错误] {error_msg}")
                    messagebox.showerror("界面错误", error_msg)
            
            start_production_btn = tk.Button(training_window, text="开始生产", 
                                           font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                           bg='#007bff', fg='white',
                                           relief='flat', bd=0,
                                           padx=40, pady=12,
                                           command=on_start_production_click)
            start_production_btn.pack(pady=30)
            
            # 启动计时器
            self._start_timer()
            
            print("[信息] 显示训练完成弹窗")
            
        except Exception as e:
            error_msg = f"显示训练完成弹窗异常: {str(e)}"
            self.logger.error(error_msg)
            print(f"[错误] {error_msg}")
    
    def _start_timer(self):
        """启动计时器"""
        try:
            import datetime
            
            # 记录开始时间
            self.timer_start_time = datetime.datetime.now()
            self.timer_running = True
            
            def update_timer():
                """更新计时器显示"""
                if hasattr(self, 'timer_running') and self.timer_running:
                    try:
                        # 计算经过的时间
                        current_time = datetime.datetime.now()
                        elapsed_time = current_time - self.timer_start_time
                        
                        # 格式化为 HH:MM:SS
                        total_seconds = int(elapsed_time.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        # 更新标签
                        if hasattr(self, 'timer_label') and self.timer_label.winfo_exists():
                            self.timer_label.config(text=time_str)
                            # 继续更新
                            self.root.after(1000, update_timer)
                        else:
                            self.timer_running = False
                    except Exception as e:
                        print(f"[错误] 更新计时器异常: {e}")
                        self.timer_running = False
            
            # 开始更新计时器
            update_timer()
            
        except Exception as e:
            error_msg = f"启动计时器异常: {str(e)}"
            self.logger.error(error_msg)
            print(f"[错误] {error_msg}")
    
    def show_progress_message(self, step: str, message: str):
        """
        显示进度消息（在主线程中调用）
        
        Args:
            step (str): 步骤信息
            message (str): 进度消息
        """
        print(f"[{step}] {message}")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 如果有快加时间测定控制器正在运行，先停止它
        if self.coarse_time_controller:
            try:
                self.coarse_time_controller.stop_all_coarse_time_test()
                self.coarse_time_controller.dispose()
                self.coarse_time_controller = None
                print("快加时间测定控制器已停止")
            except Exception as e:
                print(f"停止快加时间测定控制器时发生错误: {e}")
        
        # 如果有清料控制器正在运行，先停止它
        if self.cleaning_controller:
            try:
                self.cleaning_controller.dispose()
                self.cleaning_controller = None
                print("清料控制器已停止")
            except Exception as e:
                print(f"停止清料控制器时发生错误: {e}")
        
        # 如果有主窗口引用，重新显示主窗口
        if self.main_window:
            try:
                # 使用主窗口的便捷方法显示窗口
                if hasattr(self.main_window, 'show_main_window'):
                    self.main_window.show_main_window()
                else:
                    # 备用方式：直接操作root属性
                    if hasattr(self.main_window, 'root'):
                        self.main_window.root.deiconify()
                        self.main_window.root.lift()
                        self.main_window.root.focus_force()
                    else:
                        print("警告：无法显示主窗口")
            except Exception as e:
                print(f"显示主窗口时发生错误: {e}")
        
        # 关闭AI模式界面
        self.root.destroy()
    
    def show(self):
        """显示界面（如果是主窗口）"""
        if self.is_main_window:
            self.root.mainloop()

def main():
    """
    主函数 - 程序入口点
    创建并显示AI模式界面
    """
    # 创建AI模式界面实例
    ai_interface = AIModeInterface()
    
    # 居中显示窗口
    ai_interface.root.update_idletasks()
    width = ai_interface.root.winfo_width()
    height = ai_interface.root.winfo_height()
    x = (ai_interface.root.winfo_screenwidth() // 2) - (width // 2)
    y = (ai_interface.root.winfo_screenheight() // 2) - (height // 2)
    ai_interface.root.geometry(f'{width}x{height}+{x}+{y}')
    
    # 显示界面
    ai_interface.show()

# 当作为主程序运行时，启动界面
if __name__ == "__main__":
    main()