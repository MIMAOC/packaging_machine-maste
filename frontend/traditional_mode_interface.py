#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传统模式完整界面系统（Pack布局版本）
包含主菜单、6料斗监控界面、料斗详细界面的完整实现

修改内容：
- 启动/停止使用互斥逻辑（状态保持）
- 清料使用状态保持控制
- 放料/清零/点动使用脉冲控制
- 全面改为Pack布局管理器

作者：AI助手
创建日期：2025-08-05
修复日期：2025-08-06
Pack布局改造：2025-08-13
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any

# 导入PLC相关模块
try:
    from traditional_plc_addresses import (
        get_traditional_weight_address,
        get_traditional_monitoring_address, 
        get_traditional_control_address,
        get_traditional_parameter_address,
        get_traditional_global_address,
        get_traditional_disable_address,
        TRADITIONAL_MONITORING_ADDRESSES,
        TRADITIONAL_PARAMETER_ADDRESSES
    )
    from modbus_client import ModbusClient
except ImportError as e:
    print(f"导入PLC模块失败: {e}")
    print("请确保traditional_plc_addresses.py和modbus_client.py在同一目录下")


class SimpleTianTengInterface:
    def __init__(self, parent=None, main_window=None, modbus_client: Optional[ModbusClient] = None):
        # 如果有父窗口，使用父窗口；否则创建新窗口
        if parent:
            self.root = parent
            self.is_embedded = True  # 标记为嵌入模式
            self.main_window = main_window  # 保存主窗口引用
        else:
            self.root = tk.Tk()
            self.is_embedded = False  # 标记为独立模式
            self.main_window = None
            
        # 只有在独立模式下才设置窗口属性
        if self.is_embedded:
            self.root.title("六头线性调节秤 V1.8")
            self.root.attributes('-fullscreen', True)
            self.root.state('zoomed')  # Windows系统的最大化
            self.root.geometry("1920x1080")
            self.root.configure(bg='#ffffff')
            self.root.resizable(True, True)  # 允许调整窗口大小
            
            # 添加强制退出机制
            self.setup_force_exit_mechanism()
        
        # 界面状态管理
        self.current_interface = "menu"  # menu/monitoring/bucket_detail/manual
        self.current_bucket_id = 1       # 当前选中的料斗
        
        # PLC通信客户端
        self.modbus_client = modbus_client
        
        # 子界面模块引用
        self.manual_interface = None     # 手动界面实例
        self.calibration_interface = None  # 重量校准界面实例
        self.parameter_interface = None  # 参数设置界面实例
        
        # 数据刷新定时器
        self.refresh_timer = None
        self._external_update_callback = None  # 外部数据更新回调
        
        # 界面元素引用
        self.main_content_frame = None
        self.bucket_widgets = {}         # 料斗组件引用
        self.status_labels = {}          # 状态标签引用
        self.weight_labels = {}          # 重量标签引用
        self.parameter_entries = {}      # 参数输入框引用
        self.control_buttons = {}        # 控制按钮引用
        self.target_weight_entry = None  # 目标重量输入框引用
        
        # 全局启动状态
        self.global_started = False
        
        # 料斗状态管理
        self.bucket_started = {}    # 料斗启动状态 {bucket_id: True/False}
        self.bucket_cleaning = {}   # 料斗清料状态 {bucket_id: True/False}
        for i in range(1, 7):
            self.bucket_started[i] = False
            self.bucket_cleaning[i] = False
        
        # LOGO图片引用
        self.logo_image = None
        
        # 强制退出相关变量
        self.click_count = 0
        self.last_click_time = 0
        
        self.setup_fonts()
        self.create_base_layout()
        self.show_menu_interface()
        
        # 在嵌入模式下也设置强制退出机制
        self.setup_force_exit_mechanism()
        
    def setup_fonts(self):
        """设置字体"""
        self.title_font = font.Font(family="Microsoft YaHei", size=48, weight="normal")
        self.version_font = font.Font(family="Microsoft YaHei", size=42, weight="normal")
        self.menu_font = font.Font(family="Microsoft YaHei", size=38, weight="normal")
        self.company_font = font.Font(family="Microsoft YaHei", size=20, weight="normal")
        self.logo_font = font.Font(family="Arial", size=22, weight="bold")
        
        # 监控界面字体
        self.bucket_number_font = font.Font(family="Arial", size=72, weight="bold")
        self.weight_font = font.Font(family="Arial", size=42, weight="bold")
        self.status_font = font.Font(family="Microsoft YaHei", size=16, weight="normal")
        self.button_font = font.Font(family="Microsoft YaHei", size=18, weight="normal")
        self.target_font = font.Font(family="Arial", size=28, weight="bold")
        
        # 详细界面字体
        self.detail_weight_font = font.Font(family="Arial", size=84, weight="bold")
        self.param_label_font = font.Font(family="Microsoft YaHei", size=24, weight="normal")
        self.param_value_font = font.Font(family="Arial", size=20, weight="bold")
        self.bucket_select_font = font.Font(family="Arial", size=18, weight="bold")
        
    def setup_force_exit_mechanism(self):
        """设置强制退出机制"""
        # 键盘快捷键强制退出
        self.root.bind('<Control-Alt-q>', lambda e: self.force_exit())
        self.root.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        self.root.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        # 添加隐藏的强制退出区域（右上角小区域）
        # 直接在传统模式窗口上创建
        exit_zone = tk.Frame(self.root, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)  # 放在右上角
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        # 确保退出区域在最顶层，不被其他组件覆盖
        exit_zone.tkraise()
        
        # 保存引用防止被垃圾回收
        self.exit_zone = exit_zone

    def show_exit_confirmation(self):
        """显示退出确认对话框"""
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出传统模式程序吗？\n\n"
            "退出将返回主菜单或关闭程序。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        """强制退出程序"""
        try:
            print("执行强制退出...")
            if self.is_embedded and self.main_window:
                # 嵌入模式：返回主窗口
                self.return_to_main_menu()
            else:
                # 独立模式：直接退出
                self.cleanup()
                self.root.destroy()
        except Exception as e:
            print(f"强制退出时发生错误: {e}")
            import os
            os._exit(0)  # 强制终止进程
        
    def create_base_layout(self):
        """创建基础布局框架（Pack版本）"""
        # 主容器 - 填满整个窗口
        self.main_container = tk.Frame(self.root, bg='#ffffff')
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # 动态内容区域 - 填满主容器
        self.main_content_frame = tk.Frame(self.main_container, bg='#ffffff')
        self.main_content_frame.pack(fill=tk.BOTH, expand=True)
        
    def clear_main_content(self):
        """清空主内容区域"""
        if self.main_content_frame:
            for widget in self.main_content_frame.winfo_children():
                widget.destroy()
        
        # 停止数据刷新
        self.stop_data_refresh()
        
        # 清空引用
        self.bucket_widgets.clear()
        self.status_labels.clear()
        self.weight_labels.clear()
        self.parameter_entries.clear()
        self.control_buttons.clear()
        self.target_weight_entry = None

    # ==================== 界面切换方法 ====================
    
    def show_menu_interface(self):
        """显示主菜单界面"""
        self.clear_main_content()
        self.current_interface = "menu"
        self.create_menu_interface()
    
    def show_monitoring_interface(self):
        """显示6料斗监控界面"""
        self.clear_main_content()
        self.current_interface = "monitoring"
        self.create_monitoring_interface()
        self.start_data_refresh()
    
    def show_manual_interface(self):
        """显示手动界面"""
        # 延迟导入，避免循环导入
        if self.manual_interface is None:
            try:
                from manual_mode_interface import ManualModeInterface
                self.manual_interface = ManualModeInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"手动界面模块加载失败: {e}\n请确保manual_mode_interface.py文件存在")
                return
        
        # 清空当前界面并切换到手动界面
        self.clear_main_content()
        self.current_interface = "manual"
        self.manual_interface.show_interface()

    def show_calibration_interface(self):
        """显示重量校准界面"""
        # 延迟导入，避免循环导入
        if self.calibration_interface is None:
            try:
                from weight_calibration_interface import WeightCalibrationInterface
                self.calibration_interface = WeightCalibrationInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"重量校准界面模块加载失败: {e}\n请确保weight_calibration_interface.py文件存在")
                return
            
    def show_parameter_interface(self):
        """显示参数设置界面"""
        # 延迟导入，避免循环导入
        if self.parameter_interface is None:
            try:
                from parameter_setting_interface import ParameterSettingInterface
                self.parameter_interface = ParameterSettingInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"参数设置界面模块加载失败: {e}\n请确保parameter_setting_interface.py文件存在")
                return
        
        # 清空当前界面并切换到参数设置界面
        self.clear_main_content()
        self.current_interface = "parameter"
        self.parameter_interface.show_interface()
        
    
        # 清空当前界面并切换到重量校准界面
        self.clear_main_content()
        self.current_interface = "calibration"
        self.parameter_interface.show_interface()
    
    def show_bucket_detail_interface(self, bucket_id: int):
        """显示料斗详细界面"""
        self.clear_main_content()
        self.current_interface = "bucket_detail"
        self.current_bucket_id = bucket_id
        self.create_bucket_detail_interface(bucket_id)
        self.start_data_refresh()

    # ==================== 主菜单界面 ====================
    
    def create_menu_interface(self):
        """创建主菜单界面（Pack版本）"""
        # 顶部空白区域
        top_spacer = tk.Frame(self.main_content_frame, bg='#ffffff', height=60)
        top_spacer.pack(side=tk.TOP, fill=tk.X)
        
        # 主内容区域 - 水平布局
        main_content = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 左侧菜单区域
        left_frame = tk.Frame(main_content, bg='#ffffff', width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(40, 20))
        left_frame.pack_propagate(False)  # 保持固定宽度
        
        # 右侧标题区域  
        right_frame = tk.Frame(main_content, bg='#ffffff')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 20))
        
        # 创建左侧菜单
        self.create_menu_area(left_frame)
        
        # 创建右侧标题
        self.create_title_area(right_frame)
        
        # 底部公司信息
        company_frame = tk.Frame(self.main_content_frame, bg='#ffffff')
        company_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 45))
        
        company_label = tk.Label(company_frame, 
                               text="温州天腾机械有限公司 • 13395779890",
                               font=self.company_font, bg='#ffffff', fg='#666666')
        company_label.pack(side=tk.RIGHT, padx=150)
        
    def create_menu_area(self, parent):
        """创建菜单区域（Pack版本）"""
        menu_items = [
            "传统模式",
            "手动画面", 
            "参数设置",
            "重量校准",
            "系统设置"
        ]
        # 如果是嵌入模式，添加返回主菜单选项
        if self.is_embedded:
            menu_items.append("返回主菜单")
        
        # 顶部空白
        top_spacer = tk.Frame(parent, bg='#ffffff', height=50)
        top_spacer.pack(side=tk.TOP)
        
        # 创建菜单项
        for i, text in enumerate(menu_items):
            # 菜单项容器
            menu_item_frame = tk.Frame(parent, bg='#ffffff')
            menu_item_frame.pack(side=tk.TOP, fill=tk.X, pady=20)
            
            # 三角形
            triangle = tk.Label(menu_item_frame, text="▶", 
                              font=("Arial", 12), 
                              bg='#ffffff', fg='#999999')
            triangle.pack(side=tk.LEFT, padx=(5, 0))
            
            # 菜单文字
            menu_label = tk.Label(menu_item_frame, text=text, 
                                font=self.menu_font,
                                bg='#ffffff', fg='#333333',
                                cursor='hand2')
            menu_label.pack(side=tk.LEFT, padx=10)
            
            # 绑定点击事件
            menu_label.bind("<Button-1>", lambda e, t=text: self.menu_click(t))
            menu_label.bind("<Enter>", lambda e, l=menu_label: l.configure(fg='#1a365d'))
            menu_label.bind("<Leave>", lambda e, l=menu_label: l.configure(fg='#333333'))
    
    def create_title_area(self, parent):
        """创建标题区域（Pack版本）"""
        # 内容容器 - 垂直居中
        content_frame = tk.Frame(parent, bg='#ffffff')
        content_frame.pack(expand=True)  # 自动居中
        
        # Logo区域
        self.logo_label = tk.Label(content_frame, text="TiAN TENG", 
                                  font=self.logo_font, bg='#ffffff', fg='#1a365d')
        self.logo_label.pack(pady=(0, 30))
        
        # 如果有保存的LOGO图片，重新应用
        if self.logo_image:
            self.logo_label.configure(image=self.logo_image, text='')
        
        # 标题容器
        title_frame = tk.Frame(content_frame, bg='#ffffff')
        title_frame.pack()
        
        # 主标题
        main_title = tk.Label(title_frame, text="六头线性调节秤", 
                             font=self.title_font, 
                             bg='#ffffff', fg='#2d3748')
        main_title.pack()
        
        # 版本号
        version_label = tk.Label(title_frame, text="V1.8", 
                                font=self.version_font, 
                                bg='#ffffff', fg='#2d3748')
        version_label.pack(pady=(10, 0))

    # ==================== 6料斗监控界面 ====================
    
    def create_monitoring_interface(self):
        """创建6料斗监控界面（Pack版本，模拟3行2列布局）"""
        # 主容器 - 水平布局
        main_container = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 左侧料斗区域
        buckets_frame = tk.Frame(main_container, bg='#ffffff')
        buckets_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 右侧控制面板
        control_frame = tk.Frame(main_container, bg='#ffffff', width=300)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        control_frame.pack_propagate(False)  # 保持固定宽度
        
        # 创建6个料斗显示区域
        self.create_buckets_area(buckets_frame)
        
        # 创建右侧控制面板
        self.create_control_panel(control_frame)
        
    def create_buckets_area(self, parent):
        """创建6料斗显示区域（Pack版本，用Frame模拟3行2列）"""
        # 第一行（料斗1、2）
        row1_frame = tk.Frame(parent, bg='#ffffff')
        row1_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 8))
        
        bucket1_widget = self.create_bucket_widget(row1_frame, 1)
        bucket1_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.bucket_widgets[1] = bucket1_widget
        
        bucket2_widget = self.create_bucket_widget(row1_frame, 2)
        bucket2_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.bucket_widgets[2] = bucket2_widget
        
        # 第二行（料斗3、4）
        row2_frame = tk.Frame(parent, bg='#ffffff')
        row2_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=8)
        
        bucket3_widget = self.create_bucket_widget(row2_frame, 3)
        bucket3_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.bucket_widgets[3] = bucket3_widget
        
        bucket4_widget = self.create_bucket_widget(row2_frame, 4)
        bucket4_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.bucket_widgets[4] = bucket4_widget
        
        # 第三行（料斗5、6）
        row3_frame = tk.Frame(parent, bg='#ffffff')
        row3_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(8, 0))
        
        bucket5_widget = self.create_bucket_widget(row3_frame, 5)
        bucket5_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.bucket_widgets[5] = bucket5_widget
        
        bucket6_widget = self.create_bucket_widget(row3_frame, 6)
        bucket6_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.bucket_widgets[6] = bucket6_widget
    
    def create_bucket_widget(self, parent, bucket_id: int):
        """创建单个料斗组件（Pack版本）"""
        # 主容器 - 料斗卡片
        bucket_frame = tk.Frame(parent, bg='#d5d5d5', relief='raised', bd=2, height=250)
        bucket_frame.pack_propagate(False)  # 保持固定高度
        
        # 上半部分：料斗编号 + 重量显示（水平布局）
        content_frame = tk.Frame(bucket_frame, bg='#d5d5d5')
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=(20, 12))
        
        # 左侧：料斗编号
        number_label = tk.Label(content_frame, text=str(bucket_id),
                               font=('Arial', 110, 'bold'), bg='#d5d5d5', fg='#333333')
        number_label.pack(side=tk.LEFT, padx=(15, 40))
        
        # 右侧：重量显示
        weight_label = tk.Label(content_frame, text="-0000.0",
                               font=('Arial', 68, 'bold'), bg='#d5d5d5', fg='#333333')
        weight_label.pack(side=tk.RIGHT, padx=(0, 15))
        self.weight_labels[bucket_id] = weight_label
        
        # 下半部分：状态指示灯（水平排列）
        status_frame = tk.Frame(bucket_frame, bg='#d5d5d5')
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 20))
        
        # 4个状态指示灯
        status_types = ['CoarseAdd', 'FineAdd', 'Jog', 'TargetReached']
        status_texts = ['快加', '慢加', '点动', '到重']
        
        if bucket_id not in self.status_labels:
            self.status_labels[bucket_id] = {}
        
        for i, (status_type, status_text) in enumerate(zip(status_types, status_texts)):
            status_label = tk.Label(status_frame, text=status_text,
                                   font=('Microsoft YaHei', 13), bg='#bdbdbd', fg='#333333',
                                   relief='solid', bd=1, padx=10, pady=5, width=6)
            
            # 使用pack均匀分布
            status_label.pack(side=tk.LEFT, expand=True, padx=4)
            self.status_labels[bucket_id][status_type] = status_label
        
        # 绑定点击事件 - 点击料斗卡片进入详细界面
        def on_bucket_click(event):
            self.show_bucket_detail_interface(bucket_id)
        
        bucket_frame.bind("<Button-1>", on_bucket_click)
        number_label.bind("<Button-1>", on_bucket_click)
        weight_label.bind("<Button-1>", on_bucket_click)
        
        # 设置鼠标手型光标
        bucket_frame.configure(cursor='hand2')
        number_label.configure(cursor='hand2')
        weight_label.configure(cursor='hand2')
        
        return bucket_frame
    
    def create_control_panel(self, parent):
        """创建右侧控制面板（Pack版本）"""
        # 目标重量显示区域
        target_frame = tk.Frame(parent, bg='#ffffff')
        target_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 30))
        
        tk.Label(target_frame, text="目标重量",
                font=('Microsoft YaHei', 20, 'bold'), bg='#ffffff', fg='#333333').pack()
        
        self.target_weight_entry = tk.Entry(target_frame, font=('Arial', 32, 'bold'), justify='center',
                               relief='solid', bd=2, width=8)
        self.target_weight_entry.pack(pady=(8, 0))
        self.target_weight_entry.insert(0, "0000.0")
        
        # 绑定目标重量修改事件
        self.target_weight_entry.bind('<FocusOut>', self.save_target_weight)
        self.target_weight_entry.bind('<Return>', self.save_target_weight)
        
        # 控制按钮区域
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.pack(side=tk.TOP, fill=tk.X)
        
        # 按钮配置
        button_configs = [
            ("总放料", "#4a90e2", "GlobalDischarge"),
            ("总清零", "#4a90e2", "GlobalClear"),
            ("总启动", "#4a90e2", "GlobalStart"),
            ("主页", "#e0e0e0", "Home")
        ]
        
        for i, (text, color, action) in enumerate(button_configs):
            if action == "GlobalStart":
                # 总启动按钮需要状态切换
                btn = tk.Button(buttons_frame, text=text, font=('Microsoft YaHei', 18, 'bold'),
                               bg=color, fg='white' if color != "#e0e0e0" else '#333333',
                               relief='solid', bd=1, height=2,
                               command=lambda: self.toggle_global_start())
                self.control_buttons['global_start'] = btn
            else:
                btn = tk.Button(buttons_frame, text=text, font=('Microsoft YaHei', 18, 'bold'),
                               bg=color, fg='white' if color != "#e0e0e0" else '#333333',
                               relief='solid', bd=1, height=2,
                               command=lambda a=action: self.on_control_button_click(a))
            
            btn.pack(side=tk.TOP, fill=tk.X, pady=8)
        
        # 加载目标重量
        self.load_target_weight()

    # ==================== 料斗详细界面 ====================
    
    def create_bucket_detail_interface(self, bucket_id: int):
        """创建料斗详细界面（Pack版本）"""
        # 主容器 - 水平布局
        main_container = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 左侧区域（重量显示+参数+料斗选择）
        left_container = tk.Frame(main_container, bg='#ffffff')
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(7, 10))
        
        # 右侧控制面板
        right_container = tk.Frame(main_container, bg='#ffffff', width=250)
        right_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 7))
        right_container.pack_propagate(False)  # 保持固定宽度
        
        # 创建左侧各部分
        self.create_detail_top_area(left_container, bucket_id)
        self.create_detail_main_area(left_container, bucket_id)
        self.create_detail_bottom_area(left_container, bucket_id)
        
        # 创建右侧控制面板
        self.create_detail_control_panel_fixed(right_container)
        
        # 加载参数数据
        self.load_bucket_parameters(bucket_id)
        
    def create_detail_top_area(self, parent, bucket_id: int):
        """创建顶部重量显示区域（Pack版本）"""
        top_frame = tk.Frame(parent, bg='#ffffff', height=180)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        top_frame.pack_propagate(False)  # 保持固定高度
        
        # 重量显示容器
        content_frame = tk.Frame(top_frame, bg='#ffffff')
        content_frame.pack(expand=True)  # 居中显示
        
        # 重量显示
        weight_label = tk.Label(content_frame, text="-0000.0",
                               font=('Arial', 100, 'bold'), bg='#ffffff', fg='#333333')
        weight_label.pack(pady=(5, 15))
        self.weight_labels[f'detail_{bucket_id}'] = weight_label
        
        # 状态指示区域
        status_frame = tk.Frame(content_frame, bg='#ffffff')
        status_frame.pack(pady=(0, 5))
        
        # 4个状态指示灯
        status_types = ['CoarseAdd', 'FineAdd', 'Jog', 'TargetReached']
        status_texts = ['快加', '慢加', '点动', '到重']
        
        if f'detail_{bucket_id}' not in self.status_labels:
            self.status_labels[f'detail_{bucket_id}'] = {}
        
        for i, (status_type, status_text) in enumerate(zip(status_types, status_texts)):
            status_label = tk.Label(status_frame, text=status_text,
                                   font=('Microsoft YaHei', 17), bg='#cccccc', fg='#333333',
                                   relief='solid', bd=1, padx=14, pady=8, width=7)
            status_label.pack(side=tk.LEFT, padx=8)
            self.status_labels[f'detail_{bucket_id}'][status_type] = status_label
    
    def create_detail_main_area(self, parent, bucket_id: int):
        """创建主要参数区域（Pack版本）"""
        main_frame = tk.Frame(parent, bg='#ffffff', height=450)
        main_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        main_frame.pack_propagate(False)  # 保持固定高度
        
        # 参数容器（居中显示）
        params_container = tk.Frame(main_frame, bg='#ffffff')
        params_container.pack(expand=True)  # 居中
        
        # 参数配置
        param_configs = [
            ("快加料速度", "CoarseSpeed", 0),
            ("慢加料速度", "FineSpeed", 0),
            ("快加料提前量", "CoarseAdvance", 1),
            ("慢加料提前量", "FineAdvance", 1)
        ]
        
        if bucket_id not in self.parameter_entries:
            self.parameter_entries[bucket_id] = {}
        
        # 创建参数输入行
        for i, (param_text, param_type, decimal_places) in enumerate(param_configs):
            # 参数行容器
            param_row = tk.Frame(params_container, bg='#ffffff')
            param_row.pack(side=tk.TOP, pady=20)
            
            # 参数标签
            param_label = tk.Label(param_row, text=param_text,
                                  font=('Microsoft YaHei', 24, 'normal'), bg='#ffffff', fg='#333333')
            param_label.pack(side=tk.LEFT, padx=(0, 40))
            
            # 参数输入框
            param_entry = tk.Entry(param_row, font=('Arial', 28, 'bold'), justify='center',
                                  relief='solid', bd=2, width=15, highlightthickness=2)
            param_entry.pack(side=tk.LEFT)
            
            # 绑定参数修改事件
            param_entry.bind('<FocusOut>', 
                           lambda e, bid=bucket_id, pt=param_type: self.save_parameter(bid, pt, e.widget.get()))
            param_entry.bind('<Return>', 
                           lambda e, bid=bucket_id, pt=param_type: self.save_parameter(bid, pt, e.widget.get()))
            
            self.parameter_entries[bucket_id][param_type] = param_entry
    
    def create_detail_control_panel_fixed(self, parent):
        """创建右侧控制面板（Pack版本）"""
        # 重量显示框
        weight_frame = tk.Frame(parent, bg='#ffffff')
        weight_frame.pack(side=tk.TOP, fill=tk.X, pady=(20, 30))
        
        tk.Label(weight_frame, text="重量",
                font=('Microsoft YaHei', 24, 'bold'), bg='#ffffff', fg='#333333').pack()
        
        weight_entry = tk.Entry(weight_frame, font=('Arial', 36, 'bold'), justify='center',
                               relief='solid', bd=2, width=8)
        weight_entry.pack(pady=(10, 0))
        weight_entry.insert(0, "0000.0")
        
        # 控制按钮区域
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.pack(side=tk.TOP, fill=tk.X, pady=20)
        
        # 控制按钮
        button_configs = [
            ("放料", "#4a90e2", "Discharge"),
            ("清零", "#4a90e2", "Clear"),
            ("启动", "#4a90e2", "Start"),
            ("返回", "#e0e0e0", "Back")
        ]
        
        for i, (text, color, action) in enumerate(button_configs):
            if action == "Start":
                # 启动按钮需要状态切换
                btn = tk.Button(buttons_frame, text=text, font=('Microsoft YaHei', 20, 'bold'),
                               bg=color, fg='white' if color != "#e0e0e0" else '#333333',
                               relief='solid', bd=1, height=2,
                               command=lambda: self.toggle_bucket_start())
                self.control_buttons[f'bucket_{self.current_bucket_id}_start'] = btn
            else:
                btn = tk.Button(buttons_frame, text=text, font=('Microsoft YaHei', 20, 'bold'),
                               bg=color, fg='white' if color != "#e0e0e0" else '#333333',
                               relief='solid', bd=1, height=2,
                               command=lambda a=action: self.on_detail_control_click(a))
            
            btn.pack(side=tk.TOP, fill=tk.X, pady=10)
        
        # 底部空白区域
        spacer_frame = tk.Frame(parent, bg='#ffffff')
        spacer_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    def create_detail_bottom_area(self, parent, current_bucket_id: int):
        """创建底部料斗选择区域（Pack版本）"""
        bottom_frame = tk.Frame(parent, bg='#ffffff', height=75)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        bottom_frame.pack_propagate(False)  # 保持固定高度
        
        # 料斗选择按钮容器
        buckets_container = tk.Frame(bottom_frame, bg='#ffffff')
        buckets_container.pack(expand=True)  # 居中显示
        
        # 创建6个圆形料斗选择按钮
        for bucket_id in range(1, 7):
            if bucket_id == current_bucket_id:
                # 当前选中的料斗显示为绿色
                bg_color = '#00aa00'
                fg_color = 'white'
            else:
                # 其他料斗显示为蓝色
                bg_color = '#4a90e2'
                fg_color = 'white'
            
            # 圆形按钮
            btn = tk.Button(buckets_container, text=str(bucket_id),
                           font=('Arial', 20, 'bold'), bg=bg_color, fg=fg_color,
                           width=4, height=2, relief='solid', bd=2,
                           command=lambda bid=bucket_id: self.switch_bucket(bid))
            btn.pack(side=tk.LEFT, padx=15)

    # ==================== 其他方法保持不变 ====================
    # 保留原有的所有方法，不涉及布局的部分完全不变
    
    def save_target_weight(self, event=None):
        """保存目标重量到所有料斗"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存目标重量")
            return
        
        try:
            # 获取目标重量值
            target_weight_str = self.target_weight_entry.get()
            target_weight = float(target_weight_str)
            
            # 目标重量需要乘以10存储到PLC
            plc_value = int(target_weight * 10)
            
            # 写入所有料斗的目标重量
            success_count = 0
            for bucket_id in range(1, 7):
                try:
                    address = get_traditional_parameter_address(bucket_id, 'TargetWeight')
                    success = self.modbus_client.write_holding_register(address, plc_value)
                    if success:
                        success_count += 1
                    else:
                        print(f"料斗{bucket_id}目标重量保存失败")
                except Exception as e:
                    print(f"保存料斗{bucket_id}目标重量异常: {e}")
            
            if success_count == 6:
                print(f"成功保存目标重量到所有料斗: {target_weight}g (PLC值: {plc_value})")
            else:
                messagebox.showwarning("警告", f"只有{success_count}/6个料斗目标重量保存成功")
                
        except ValueError:
            messagebox.showerror("错误", f"目标重量格式错误: {target_weight_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存目标重量异常: {e}")
    
    def load_target_weight(self):
        """加载目标重量（读取料斗1的目标重量作为全局目标重量）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            # 读取料斗1的目标重量作为全局目标重量
            address = get_traditional_parameter_address(1, 'TargetWeight')
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data:
                # 目标重量需要除以10显示
                target_weight = data[0] / 10.0
                self.target_weight_entry.delete(0, tk.END)
                self.target_weight_entry.insert(0, f"{target_weight:.1f}")
                
        except Exception as e:
            print(f"加载目标重量失败: {e}")

    # ==================== 数据加载和保存 ====================
    
    def load_bucket_parameters(self, bucket_id: int):
        """加载料斗参数"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            # 参数类型映射
            param_types = ['CoarseSpeed', 'FineSpeed', 'CoarseAdvance', 'FineAdvance']
            
            for param_type in param_types:
                try:
                    address = get_traditional_parameter_address(bucket_id, param_type)
                    data = self.modbus_client.read_holding_registers(address, 1)
                    
                    if data and bucket_id in self.parameter_entries:
                        if param_type in self.parameter_entries[bucket_id]:
                            entry = self.parameter_entries[bucket_id][param_type]
                            
                            # 根据参数类型格式化数值
                            if param_type in ['CoarseAdvance', 'FineAdvance']:
                                # 提前量参数，PLC值除以10显示小数
                                value = f"{data[0] / 10:.1f}"
                            else:
                                # 速度参数，直接显示整数
                                value = str(data[0])
                            
                            entry.delete(0, tk.END)
                            entry.insert(0, value)
                            
                except Exception as e:
                    print(f"加载料斗{bucket_id}参数{param_type}失败: {e}")
                    
        except Exception as e:
            print(f"加载料斗{bucket_id}参数失败: {e}")
    
    def save_parameter(self, bucket_id: int, param_type: str, value_str: str):
        """保存参数到PLC"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存参数")
            return
        
        try:
            # 验证数值
            value = float(value_str)
            
            # 根据参数类型转换数值
            if param_type in ['CoarseAdvance', 'FineAdvance']:
                # 提前量参数，PLC存储为整数(乘以10)
                plc_value = int(value * 10)
            else:
                # 速度参数，直接存储为整数
                plc_value = int(value)
            
            # 获取PLC地址
            address = get_traditional_parameter_address(bucket_id, param_type)
            
            # 写入PLC
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                print(f"成功保存料斗{bucket_id}参数{param_type}: {value} (PLC值: {plc_value})")
            else:
                messagebox.showerror("错误", f"保存参数失败: {param_type}")
                
        except ValueError:
            messagebox.showerror("错误", f"参数格式错误: {value_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存参数异常: {e}")

    # ==================== 事件处理方法 ====================
    
    def menu_click(self, text):
        """菜单点击处理"""
        print(f"{text} 被点击")
        
        if text == "传统模式":
            self.show_monitoring_interface()
        elif text == "手动画面":
            self.show_manual_interface()
        elif text == "参数设置":
            self.show_parameter_interface()
        elif text == "重量校准":
            self.show_calibration_interface()
        elif text == "系统设置":
            messagebox.showinfo("提示", "系统设置功能开发中...")
        elif text == "返回主菜单" and self.is_embedded:
            # 返回主程序菜单
            self.return_to_main_menu()

    def return_to_main_menu(self):
        """返回主程序菜单"""
        if self.is_embedded and self.main_window:
            try:
                # 清理当前界面
                self.root.destroy()
                
                # 显示主窗口
                self.main_window.show_main_window()
                
                # 清理自身
                if hasattr(self.main_window, 'cleanup_traditional_interface'):
                    self.main_window.cleanup_traditional_interface()
                    
            except Exception as e:
                print(f"返回主菜单时发生错误: {e}")            
    
    def on_control_button_click(self, action: str):
        """控制按钮点击处理"""
        if action == "Home":
            self.show_menu_interface()
        elif action == "GlobalDischarge":
            self.send_global_pulse_command("GlobalDischarge")
        elif action == "GlobalClear":
            self.send_global_pulse_command("GlobalClear")
    
    def on_detail_control_click(self, action: str):
        """详细界面控制按钮点击处理"""
        if action == "Back":
            self.show_monitoring_interface()
        elif action == "Discharge":
            self.send_bucket_pulse_command(self.current_bucket_id, "Discharge")
        elif action == "Clear":
            self.send_bucket_pulse_command(self.current_bucket_id, "Clear")
    
    def toggle_global_start(self):
        """切换全局启动状态（互斥逻辑）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        if 'global_start' in self.control_buttons:
            btn = self.control_buttons['global_start']
            
            try:
                if self.global_started:
                    # 当前是启动状态，需要停止（互斥逻辑）
                    success = self.execute_global_stop_with_mutex()
                    if success:
                        btn.configure(text="总启动", bg="#4a90e2")
                        self.global_started = False
                        print("全局停止操作完成")
                    else:
                        messagebox.showerror("错误", "全局停止操作失败")
                else:
                    # 当前是停止状态，需要启动（互斥逻辑）
                    success = self.execute_global_start_with_mutex()
                    if success:
                        btn.configure(text="总停止", bg="#ff0000")
                        self.global_started = True
                        print("全局启动操作完成")
                    else:
                        messagebox.showerror("错误", "全局启动操作失败")
                        
            except Exception as e:
                messagebox.showerror("错误", f"全局启动/停止操作异常: {e}")
    
    def toggle_bucket_start(self):
        """切换料斗启动状态（状态切换）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
            
        btn_key = f'bucket_{self.current_bucket_id}_start'
        if btn_key in self.control_buttons:
            btn = self.control_buttons[btn_key]
            
            try:
                current_text = btn.cget('text')
                if current_text == "启动":
                    # 需要启动（状态切换到启动）
                    success = self.execute_bucket_start(self.current_bucket_id)
                    if success:
                        btn.configure(text="停止", bg="#ff0000")
                        self.bucket_started[self.current_bucket_id] = True
                        print(f"料斗{self.current_bucket_id}启动操作完成")
                    else:
                        messagebox.showerror("错误", f"料斗{self.current_bucket_id}启动操作失败")
                else:
                    # 需要停止（状态切换到停止）
                    success = self.execute_bucket_stop(self.current_bucket_id)
                    if success:
                        btn.configure(text="启动", bg="#4a90e2")
                        self.bucket_started[self.current_bucket_id] = False
                        print(f"料斗{self.current_bucket_id}停止操作完成")
                    else:
                        messagebox.showerror("错误", f"料斗{self.current_bucket_id}停止操作失败")
                        
            except Exception as e:
                messagebox.showerror("错误", f"料斗{self.current_bucket_id}启动/停止操作异常: {e}")
    
    def switch_bucket(self, bucket_id: int):
        """切换料斗"""
        if bucket_id != self.current_bucket_id:
            self.show_bucket_detail_interface(bucket_id)

    # ==================== 互斥逻辑控制方法 ====================
    
    def execute_global_start_with_mutex(self) -> bool:
        """执行全局启动（带互斥保护）"""
        try:
            # 步骤1: 先发送全局停止=0命令（互斥保护）
            global_stop_addr = get_traditional_global_address('GlobalStop')
            success = self.modbus_client.write_coil(global_stop_addr, False)
            if not success:
                print("发送全局停止=0命令（互斥保护）失败")
                return False
            
            # 步骤2: 等待50ms确保互斥保护生效
            time.sleep(0.05)
            
            # 步骤3: 发送全局启动=1命令
            global_start_addr = get_traditional_global_address('GlobalStart')
            success = self.modbus_client.write_coil(global_start_addr, True)
            if not success:
                print("发送全局启动=1命令失败")
                return False
            
            print("✅ 全局启动操作成功（带互斥保护）")
            return True
            
        except Exception as e:
            print(f"全局启动操作异常: {e}")
            return False
    
    def execute_global_stop_with_mutex(self) -> bool:
        """执行全局停止（带互斥保护）"""
        try:
            # 步骤1: 先发送全局启动=0命令（互斥保护）
            global_start_addr = get_traditional_global_address('GlobalStart')
            success = self.modbus_client.write_coil(global_start_addr, False)
            if not success:
                print("发送全局启动=0命令（互斥保护）失败")
                return False
            
            # 步骤2: 等待50ms确保互斥保护生效
            time.sleep(0.05)
            
            # 步骤3: 发送全局停止=1命令
            global_stop_addr = get_traditional_global_address('GlobalStop')
            success = self.modbus_client.write_coil(global_stop_addr, True)
            if not success:
                print("发送全局停止=1命令失败")
                return False
            
            print("✅ 全局停止操作成功（带互斥保护）")
            return True
            
        except Exception as e:
            print(f"全局停止操作异常: {e}")
            return False
    
    def execute_bucket_start(self, bucket_id: int) -> bool:
        """执行料斗启动（状态切换到启动）"""
        try:
            # 料斗启动：向同一地址写入1
            bucket_start_addr = get_traditional_control_address(bucket_id, 'Start')
            success = self.modbus_client.write_coil(bucket_start_addr, True)
            if not success:
                print(f"料斗{bucket_id}启动命令发送失败")
                return False
            
            print(f"✅ 料斗{bucket_id}启动操作成功")
            return True
            
        except Exception as e:
            print(f"料斗{bucket_id}启动操作异常: {e}")
            return False
    
    def execute_bucket_stop(self, bucket_id: int) -> bool:
        """执行料斗停止（状态切换到停止）"""
        try:
            # 料斗停止：向同一地址写入0
            bucket_start_addr = get_traditional_control_address(bucket_id, 'Start')
            success = self.modbus_client.write_coil(bucket_start_addr, False)
            if not success:
                print(f"料斗{bucket_id}停止命令发送失败")
                return False
            
            print(f"✅ 料斗{bucket_id}停止操作成功")
            return True
            
        except Exception as e:
            print(f"料斗{bucket_id}停止操作异常: {e}")
            return False

    # ==================== PLC通信方法 ====================
    
    def send_global_pulse_command(self, command: str):
        """发送全局脉冲控制命令"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            address = get_traditional_global_address(command)
            success = self.send_pulse_command(address)
            
            if success:
                print(f"全局命令{command}发送成功")
            else:
                messagebox.showerror("错误", f"全局命令{command}发送失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"发送全局命令异常: {e}")
    
    def send_bucket_pulse_command(self, bucket_id: int, command: str):
        """发送料斗脉冲控制命令（只用于脉冲控制的命令）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 脉冲控制命令：Clear、Discharge、Jog
            pulse_commands = ['Clear', 'Discharge', 'Jog']
            
            if command not in pulse_commands:
                print(f"警告: {command} 不是脉冲控制命令")
                return
            
            address = get_traditional_control_address(bucket_id, command)
            success = self.send_pulse_command(address)
            
            if success:
                print(f"料斗{bucket_id}命令{command}发送成功")
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}命令{command}发送失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"发送料斗命令异常: {e}")
    
    def toggle_bucket_clean(self, bucket_id: int):
        """切换料斗清料状态（状态保持控制）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 获取清料地址
            clean_addr = get_traditional_control_address(bucket_id, 'Clean')
            
            # 切换清料状态
            current_cleaning = self.bucket_cleaning.get(bucket_id, False)
            new_state = not current_cleaning
            
            success = self.modbus_client.write_coil(clean_addr, new_state)
            
            if success:
                self.bucket_cleaning[bucket_id] = new_state
                state_text = "开始清料" if new_state else "停止清料"
                print(f"料斗{bucket_id}{state_text}成功")
                return True
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}清料操作失败")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}清料操作异常: {e}")
            return False
    
    def toggle_bucket_disable(self, bucket_id: int):
        """切换料斗禁用状态（状态保持控制）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 获取禁用地址
            disable_addr = get_traditional_disable_address(bucket_id)
            
            # 读取当前禁用状态
            current_state_data = self.modbus_client.read_coils(disable_addr, 1)
            if not current_state_data:
                messagebox.showerror("错误", f"读取料斗{bucket_id}禁用状态失败")
                return False
            
            current_disabled = current_state_data[0]
            new_state = not current_disabled
            
            # 写入新状态
            success = self.modbus_client.write_coil(disable_addr, new_state)
            
            if success:
                state_text = "已禁用" if new_state else "已启用"
                print(f"料斗{bucket_id}{state_text}")
                return True
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}禁用状态切换失败")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}禁用状态切换异常: {e}")
            return False
    
    def send_pulse_command(self, address: int, pulse_duration: int = 100):
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

    # ==================== 数据刷新方法 ====================
    
    def start_data_refresh(self):
        """启动数据刷新"""
        if self.modbus_client and self.modbus_client.is_connected:
            self.update_realtime_data()
    
    def stop_data_refresh(self):
        """停止数据刷新"""
        if self.refresh_timer:
            self.root.after_cancel(self.refresh_timer)
            self.refresh_timer = None
    
    def update_realtime_data(self):
        """更新实时数据"""
        try:
            if self.current_interface == "monitoring":
                self.update_monitoring_data()
            elif self.current_interface == "bucket_detail":
                self.update_detail_data()
            elif self.current_interface == "manual" and hasattr(self, '_external_update_callback'):
                # 调用外部回调函数（手动界面的数据更新）
                if self._external_update_callback:
                    self._external_update_callback()
                
        except Exception as e:
            print(f"数据更新错误: {e}")
        finally:
            # 继续下一次更新
            if self.current_interface in ["monitoring", "bucket_detail", "manual"]:
                self.refresh_timer = self.root.after(100, self.update_realtime_data)
    
    def update_monitoring_data(self):
        """更新监控界面数据"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            # 逐个读取所有料斗重量（地址不连续，无法批量读取）
            for bucket_id in range(1, 7):
                if bucket_id in self.weight_labels:
                    try:
                        weight_addr = get_traditional_weight_address(bucket_id)
                        weight_data = self.modbus_client.read_holding_registers(weight_addr, 1)
                        if weight_data:
                            # 处理16位有符号整数
                            raw_value = weight_data[0]
                            # 如果大于32767，说明是负数（16位补码）
                            if raw_value > 32767:
                                signed_value = raw_value - 65536  # 转换为负数
                            else:
                                signed_value = raw_value
                            
                            # 重量值需要除以10显示
                            weight_value = signed_value / 10.0
                            weight_text = f"{weight_value:.1f}"
                            self.weight_labels[bucket_id].configure(text=weight_text)
                    except Exception as e:
                        print(f"读取料斗{bucket_id}重量失败: {e}")
            
            # 更新状态指示灯
            self.update_status_indicators()
            
        except Exception as e:
            print(f"更新监控数据失败: {e}")
    
    def update_detail_data(self):
        """更新详细界面数据"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            bucket_id = self.current_bucket_id
            
            # 更新重量显示
            try:
                weight_addr = get_traditional_weight_address(bucket_id)
                weight_data = self.modbus_client.read_holding_registers(weight_addr, 1)
                if weight_data:
                    # 处理16位有符号整数
                    raw_value = weight_data[0]
                    # 如果大于32767，说明是负数（16位补码）
                    if raw_value > 32767:
                        signed_value = raw_value - 65536  # 转换为负数
                    else:
                        signed_value = raw_value
                    
                    # 重量值需要除以10显示
                    weight_value = signed_value / 10.0
                    weight_text = f"{weight_value:.1f}"
                    detail_key = f'detail_{bucket_id}'
                    if detail_key in self.weight_labels:
                        self.weight_labels[detail_key].configure(text=weight_text)
            except Exception as e:
                print(f"读取料斗{bucket_id}重量失败: {e}")
            
            # 更新状态指示灯
            self.update_status_indicators_detail(bucket_id)
            
        except Exception as e:
            print(f"更新详细数据失败: {e}")
    
    def update_status_indicators(self):
        """更新监控界面状态指示灯"""
        try:
            # 逐个读取每个料斗的状态
            for bucket_id in range(1, 7):
                if bucket_id in self.status_labels:
                    status_data = {}
                    
                    # 逐个读取各种状态
                    try:
                        # 到重状态
                        target_addr = get_traditional_monitoring_address(bucket_id, 'TargetReached')
                        target_data = self.modbus_client.read_coils(target_addr, 1)
                        if target_data:
                            status_data['TargetReached'] = target_data[0]
                        
                        # 快加状态
                        coarse_addr = get_traditional_monitoring_address(bucket_id, 'CoarseAdd')
                        coarse_data = self.modbus_client.read_coils(coarse_addr, 1)
                        if coarse_data:
                            status_data['CoarseAdd'] = coarse_data[0]
                        
                        # 慢加状态
                        fine_addr = get_traditional_monitoring_address(bucket_id, 'FineAdd')
                        fine_data = self.modbus_client.read_coils(fine_addr, 1)
                        if fine_data:
                            status_data['FineAdd'] = fine_data[0]
                        
                        # 点动状态
                        jog_addr = get_traditional_monitoring_address(bucket_id, 'Jog')
                        jog_data = self.modbus_client.read_coils(jog_addr, 1)
                        if jog_data:
                            status_data['Jog'] = jog_data[0]
                        
                        # 更新状态指示灯颜色
                        for status_type, is_active in status_data.items():
                            if status_type in self.status_labels[bucket_id]:
                                label = self.status_labels[bucket_id][status_type]
                                if is_active:
                                    label.configure(bg='#00aa00', fg='white')  # 绿色激活
                                else:
                                    label.configure(bg='#cccccc', fg='#333333')  # 灰色未激活
                                    
                    except Exception as e:
                        print(f"读取料斗{bucket_id}状态失败: {e}")
                        
        except Exception as e:
            print(f"更新状态指示灯失败: {e}")
    
    def update_status_indicators_detail(self, bucket_id: int):
        """更新详细界面状态指示灯"""
        detail_key = f'detail_{bucket_id}'
        if detail_key not in self.status_labels:
            return
        
        try:
            status_data = {}
            
            # 逐个读取各种状态
            try:
                # 到重状态
                target_addr = get_traditional_monitoring_address(bucket_id, 'TargetReached')
                target_data = self.modbus_client.read_coils(target_addr, 1)
                if target_data:
                    status_data['TargetReached'] = target_data[0]
                
                # 快加状态
                coarse_addr = get_traditional_monitoring_address(bucket_id, 'CoarseAdd')
                coarse_data = self.modbus_client.read_coils(coarse_addr, 1)
                if coarse_data:
                    status_data['CoarseAdd'] = coarse_data[0]
                
                # 慢加状态
                fine_addr = get_traditional_monitoring_address(bucket_id, 'FineAdd')
                fine_data = self.modbus_client.read_coils(fine_addr, 1)
                if fine_data:
                    status_data['FineAdd'] = fine_data[0]
                
                # 点动状态
                jog_addr = get_traditional_monitoring_address(bucket_id, 'Jog')
                jog_data = self.modbus_client.read_coils(jog_addr, 1)
                if jog_data:
                    status_data['Jog'] = jog_data[0]
                
                # 更新状态指示灯颜色
                for status_type, is_active in status_data.items():
                    if status_type in self.status_labels[detail_key]:
                        label = self.status_labels[detail_key][status_type]
                        if is_active:
                            label.configure(bg='#00aa00', fg='white')  # 绿色激活
                        else:
                            label.configure(bg='#cccccc', fg='#333333')  # 灰色未激活
                            
            except Exception as e:
                print(f"读取料斗{bucket_id}详细状态失败: {e}")
                
        except Exception as e:
            print(f"更新详细状态指示灯失败: {e}")

    # ==================== 公共接口方法（供其他界面模块调用）====================
    
    def get_shared_modbus_client(self):
        """获取共享的Modbus客户端"""
        return self.modbus_client
    
    def get_main_root(self):
        """获取主窗口引用"""
        return self.root
    
    def get_main_content_frame(self):
        """获取主内容框架"""
        return self.main_content_frame
    
    def shared_clear_main_content(self):
        """共享的清空主内容区域方法"""
        self.clear_main_content()
    
    def shared_start_data_refresh(self, update_callback):
        """共享的数据刷新启动方法
        
        Args:
            update_callback: 数据更新回调函数
        """
        if self.modbus_client and self.modbus_client.is_connected:
            self._external_update_callback = update_callback
            self.update_realtime_data()
    
    def shared_stop_data_refresh(self):
        """共享的数据刷新停止方法"""
        self.stop_data_refresh()
        self._external_update_callback = None
    
    def shared_toggle_bucket_disable(self, bucket_id: int):
        """共享的料斗禁用切换方法"""
        return self.toggle_bucket_disable(bucket_id)
    
    def shared_toggle_bucket_clean(self, bucket_id: int):
        """共享的料斗清料切换方法"""
        return self.toggle_bucket_clean(bucket_id)
    
    def shared_send_pulse_command(self, address: int, pulse_duration: int = 100):
        """共享的脉冲控制方法"""
        return self.send_pulse_command(address, pulse_duration)
    
    def shared_send_bucket_pulse_command(self, bucket_id: int, command: str):
        """共享的料斗脉冲控制方法"""
        return self.send_bucket_pulse_command(bucket_id, command)
    
    def shared_send_global_pulse_command(self, command: str):
        """共享的全局脉冲控制方法"""
        return self.send_global_pulse_command(command)
    
    def cleanup_manual_interface(self):
        """清理手动界面资源"""
        if self.manual_interface:
            try:
                if hasattr(self.manual_interface, 'cleanup'):
                    self.manual_interface.cleanup()
            except Exception as e:
                print(f"清理手动界面时出错: {e}")
            self.manual_interface = None

    def cleanup_calibration_interface(self):
        """清理重量校准界面资源"""
        if self.calibration_interface:
            try:
                if hasattr(self.calibration_interface, 'cleanup'):
                    self.calibration_interface.cleanup()
            except Exception as e:
                print(f"清理重量校准界面时出错: {e}")
            self.calibration_interface = None

    def cleanup_parameter_interface(self):
        """清理参数设置界面资源"""
        if self.parameter_interface:
            try:
                if hasattr(self.parameter_interface, 'cleanup'):
                    self.parameter_interface.cleanup()
            except Exception as e:
                print(f"清理参数设置界面时出错: {e}")
            self.parameter_interface = None        

    # ==================== 工具方法 ====================
    
    def set_modbus_client(self, modbus_client: ModbusClient):
        """设置Modbus客户端"""
        self.modbus_client = modbus_client
    
    def set_logo_image(self, image_path: str):
        """设置logo图片"""
        try:
            # 加载原始图片
            original_image = tk.PhotoImage(file=image_path)
            
            # 获取原始尺寸
            original_width = original_image.width()
            original_height = original_image.height()
            
            # 计算缩放比例
            target_width = 450
            scale_factor = max(1, original_width // target_width)
            
            # 缩放图片
            if scale_factor > 1:
                logo_image = original_image.subsample(scale_factor)
            else:
                logo_image = original_image
            
            # 保存图片引用
            self.logo_image = logo_image
            
            # 更新logo标签（如果存在）
            if hasattr(self, 'logo_label') and self.logo_label:
                self.logo_label.configure(image=logo_image, text='')
                self.logo_label.image = logo_image  # 保持引用防止被垃圾回收
                print("Logo加载成功！")
            else:
                print("Logo图片已保存，将在界面创建时应用")
                
        except Exception as e:
            print(f"Logo加载失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止数据刷新
            self.stop_data_refresh()
            
            # 清理子界面
            self.cleanup_manual_interface()
            self.cleanup_calibration_interface()
            self.cleanup_parameter_interface()
            
            # 清空主内容
            if self.is_embedded:
                self.clear_main_content()
                
        except Exception as e:
            print(f"清理传统模式界面资源时发生错误: {e}")

    def run(self):
        """运行程序"""
        if not self.is_embedded:
            # 设置窗口关闭事件
            self.root.protocol("WM_DELETE_WINDOW", self.force_exit)
            self.root.mainloop()
        else:
            # 嵌入模式下直接显示菜单界面
            self.show_menu_interface()
    
    def __del__(self):
        """析构函数"""
        self.stop_data_refresh()
        self.cleanup_manual_interface()
        self.cleanup_calibration_interface()


# 运行程序
if __name__ == "__main__":
    import os
    
    # 创建界面
    app = SimpleTianTengInterface()
    
    # 尝试加载logo文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_files = ["LOGO", "LOGO.png", "logo.png", "LOGO.PNG"]
    logo_loaded = False
    
    for logo_file in logo_files:
        logo_path = os.path.join(script_dir, logo_file)
        try:
            if os.path.exists(logo_path):
                app.set_logo_image(logo_path)
                logo_loaded = True
                print(f"找到并加载了logo: {logo_path}")
                break
        except Exception as e:
            print(f"尝试加载 {logo_path} 失败: {e}")
            continue
    
    if not logo_loaded:
        print("未找到LOGO文件，使用文字logo")
    
    print("传统模式完整界面系统启动！（Pack布局版本）")
    app.run()