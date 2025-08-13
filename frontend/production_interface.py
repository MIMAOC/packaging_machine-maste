#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模式生产界面
实时监控生产过程，显示料斗重量、包装进度等信息

功能特点：
1. 实时显示6个料斗重量（每100ms更新）
2. 实时显示包装数量（每1s更新）  
3. 生产计时器
4. 进度条显示
5. 状态指示灯
6. 运行日志记录

文件名：production_interface.py
作者：AI助手
创建日期：2025-07-25
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict

# 导入PLC操作模块
try:
    from plc_addresses import BUCKET_MONITORING_ADDRESSES, GLOBAL_CONTROL_ADDRESSES, get_production_address
    from modbus_client import ModbusClient
    PLC_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入PLC相关模块: {e}")
    PLC_AVAILABLE = False
    
# 导入物料DAO
try:
    from database.material_dao import MaterialDAO, Material
    MATERIAL_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入物料DAO模块: {e}")
    MATERIAL_DAO_AVAILABLE = False
    
try:
    from database.production_detail_dao import ProductionDetailDAO, ProductionDetail
    PRODUCTION_DETAIL_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入生产明细DAO模块: {e}")
    PRODUCTION_DETAIL_DAO_AVAILABLE = False

# 导入生产记录DAO
try:
    from database.production_record_dao import ProductionRecordDAO, ProductionRecord
    PRODUCTION_RECORD_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入生产记录DAO模块: {e}")
    PRODUCTION_RECORD_DAO_AVAILABLE = False
    
try:
    from plc_addresses import get_bucket_disable_address
    BUCKET_DISABLE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入料斗禁用地址: {e}")
    BUCKET_DISABLE_AVAILABLE = False

class ProductionInterface:
    """
    AI模式生产界面类
    
    负责：
    1. 显示生产界面
    2. 实时监控料斗重量
    3. 监控包装数量
    4. 显示生产进度
    5. 处理生产控制
    """
    
    def __init__(self, parent, main_window, production_params):
        """
        初始化生产界面
        
        Args:
            parent: 父窗口对象
            main_window: 主程序窗口引用
            production_params: 生产参数字典 {
                'material_name': 物料名称,
                'target_weight': 目标重量,
                'package_quantity': 包装数量
            }
        """
        # 保存参数和引用
        self.main_window = main_window
        self.production_params = production_params
        
        # 新增：生产相关属性
        self.production_id = ""
        self.target_weight = production_params.get('target_weight', 0)
        
        # 获取主窗口的modbus_client引用
        self.modbus_client = None
        if main_window and hasattr(main_window, 'modbus_client'):
            self.modbus_client = main_window.modbus_client
        
        # 修改监测服务初始化
        if self.modbus_client:
            try:
                from bucket_monitoring import create_bucket_monitoring_service
                self.monitoring_service = create_bucket_monitoring_service(self.modbus_client)
                
                # 设置物料不足回调
                self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
                
                # 设置生产监测回调
                self.monitoring_service.on_production_detail_recorded = self._on_production_detail_recorded
                self.monitoring_service.on_production_stop_triggered = self._on_production_stop_triggered
                self.monitoring_service.on_single_unqualified_triggered = self._on_single_unqualified_triggered  # 新增
                
                print("[生产界面] 物料监测服务初始化成功")
            except ImportError as e:
                print(f"[警告] 无法导入物料监测服务: {e}")
                self.monitoring_service = None
        
        # 创建生产界面窗口
        self.root = tk.Toplevel(parent)
        
        # 生产状态
        self.is_production_running = False
        self.production_start_time = None
        self.monitoring_threads_running = False
        self.is_paused = False  # ✅ 新增：暂停状态标志
        
        # 界面数据
        self.bucket_weights = {i: 0.0 for i in range(1, 7)}  # 料斗重量
        self.bucket_status = {i: 'normal' for i in range(1, 7)}  # 料斗状态 normal/error
        self.current_package_count = 0  # 当前包装数量
        self.elapsed_time = timedelta(0)  # 已用时间
        
        # 界面组件引用
        self.bucket_weight_labels = {}  # 料斗重量标签
        self.bucket_status_indicators = {}  # 料斗状态指示灯
        self.timer_label = None  # 计时器标签
        self.progress_var = None  # 进度条变量
        self.package_count_label = None  # 包装数量标签
        self.completion_rate_label = None  # 完成率标签
        self.avg_weight_label = None  # 平均重量标签
        self.pause_resume_btn = None  # 暂停/启动按钮引用
        
        # 设置窗口属性
        self.setup_window()
        
        # 设置字体
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 居中显示窗口
        self.center_window()
        
        # 启动生产流程
        self.start_production()
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.title("AI模式 - 正在生产")
        # 设置全屏模式
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')  # Windows系统的最大化
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
    
        # 添加强制退出机制
        self.setup_force_exit_mechanism()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置界面字体"""
        # 标题字体
        self.title_font = tkFont.Font(family="微软雅黑", size=24, weight="bold")  
        
        # 标签字体
        self.label_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")  
        
        # 数据字体
        self.data_font = tkFont.Font(family="微软雅黑", size=16)  
        
        # 大数据字体
        self.big_data_font = tkFont.Font(family="微软雅黑", size=20, weight="bold")  
        
        # 按钮字体
        self.button_font = tkFont.Font(family="微软雅黑", size=16, weight="bold")  
        
        # 小按钮字体
        self.small_button_font = tkFont.Font(family="微软雅黑", size=12)  
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # 创建标题栏
        self.create_title_bar(main_frame)
        
        # 创建主要内容区域
        content_frame = tk.Frame(main_frame, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # 左侧料斗监控区域
        left_frame = tk.Frame(content_frame, bg='white')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        self.create_bucket_monitoring_section(left_frame)
        
        # 右侧生产信息区域
        right_frame = tk.Frame(content_frame, bg='white')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.create_production_info_section(right_frame)
    
        # 创建底部信息区域
        self.create_footer_section(main_frame)
        
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
            "确定要退出生产程序吗？\n\n"
            "退出将停止生产并断开PLC连接。"
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
    
    def create_title_bar(self, parent):
        """
        创建标题栏
        
        Args:
            parent: 父容器
        """
        # 标题栏容器
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X)
        
        # 左侧标题
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="AI模式 - 正在生产", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # 右侧控制按钮
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        # 暂停/启动切换按钮
        self.pause_resume_btn = tk.Button(right_frame, text="⏸ 暂停", 
                                        font=self.button_font,
                                        bg='#ffc107', fg='white',
                                        relief='flat', bd=0,
                                        padx=30, pady=12,
                                        command=self.on_pause_resume_click)
        self.pause_resume_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 取消按钮
        cancel_btn = tk.Button(right_frame, text="✖ 取消", 
                             font=self.button_font,
                             bg='#dc3545', fg='white',
                             relief='flat', bd=0,
                             padx=30, pady=12,
                             command=self.on_cancel_click)
        cancel_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线
        separator = tk.Frame(parent, height=4, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(15, 0))
        
    def create_bucket_monitoring_section(self, parent):
        """
        创建料斗监控区域
        
        Args:
            parent: 父容器
        """
        # 料斗监控容器
        for bucket_id in range(1, 7):
            bucket_frame = tk.Frame(parent, bg='#f8f9fa', relief='raised', bd=1)
            bucket_frame.pack(fill=tk.X, pady=8)
            bucket_frame.configure(width=280, height=70)
            bucket_frame.pack_propagate(False)
            
            # 左侧指示灯和料斗标签
            left_frame = tk.Frame(bucket_frame, bg='#f8f9fa')
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=8)
            
            # 状态指示灯（绿色圆圈）
            indicator_canvas = tk.Canvas(left_frame, width=25, height=25, 
                                       bg='#f8f9fa', highlightthickness=0)
            indicator_canvas.pack(side=tk.LEFT, padx=(0, 15))
            
            # 绘制绿色圆圈
            indicator_canvas.create_oval(3, 3, 22, 22, fill='#28a745', outline='#28a745')
            self.bucket_status_indicators[bucket_id] = indicator_canvas
            
            # 料斗标签
            bucket_label = tk.Label(left_frame, text=f"斗{bucket_id}", 
                                  font=self.label_font, bg='#f8f9fa', fg='#333333')
            bucket_label.pack(side=tk.LEFT)
            
            # 右侧重量显示
            weight_label = tk.Label(bucket_frame, text="0.0g", 
                                  font=self.big_data_font, bg='#f8f9fa', fg='#333333')
            weight_label.pack(side=tk.RIGHT, padx=15, pady=8)
            
            self.bucket_weight_labels[bucket_id] = weight_label
    
    def create_production_info_section(self, parent):
        """
        创建生产信息区域
        
        Args:
            parent: 父容器
        """
        # 顶部生产参数显示
        params_frame = tk.Frame(parent, bg='white')
        params_frame.pack(fill=tk.X, pady=(0, 30))
        
        # 物料名称
        material_frame = tk.Frame(params_frame, bg='#e3f2fd', relief='flat', bd=0)
        material_frame.pack(side=tk.LEFT, padx=(0, 30))
        material_frame.configure(width=300, height=100)
        material_frame.pack_propagate(False)
        
        material_label = tk.Label(material_frame, 
                                text=self.production_params.get('material_name', '未知物料'),
                                font=self.big_data_font, bg='#e3f2fd', fg='#1976d2')
        material_label.pack(expand=True)
        
        # 每包重量
        weight_frame = tk.Frame(params_frame, bg='#e8f5e8', relief='flat', bd=0)
        weight_frame.pack(side=tk.LEFT, padx=(0, 30))
        weight_frame.configure(width=220, height=100)
        weight_frame.pack_propagate(False)
        
        weight_label = tk.Label(weight_frame, 
                              text=f"{self.production_params.get('target_weight', 0)}g/包",
                              font=self.big_data_font, bg='#e8f5e8', fg='#388e3c')
        weight_label.pack(expand=True)
        
        # 总包数
        total_frame = tk.Frame(params_frame, bg='#f3e5f5', relief='flat', bd=0)
        total_frame.pack(side=tk.LEFT)
        total_frame.configure(width=150, height=100)
        total_frame.pack_propagate(False)
        
        total_label = tk.Label(total_frame, 
                             text=f"{self.production_params.get('package_quantity', 0)}包",
                             font=self.big_data_font, bg='#f3e5f5', fg='#7b1fa2')
        total_label.pack(expand=True)
        
        # 生产状态和进度区域
        status_frame = tk.Frame(parent, bg='white')
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 已用时间标签
        time_frame = tk.Frame(status_frame, bg='white')
        time_frame.pack(side=tk.LEFT)
        
        tk.Label(time_frame, text="已用时:", font=self.data_font, 
                bg='white', fg='#333333').pack(anchor='w')
        
        self.timer_label = tk.Label(time_frame, text="00:00:00", 
                                  font=self.big_data_font, bg='white', fg='#333333')
        self.timer_label.pack(anchor='w')
        
        # 当前包数/总包数
        count_frame = tk.Frame(status_frame, bg='white')
        count_frame.pack(side=tk.RIGHT)
        
        self.package_count_label = tk.Label(count_frame, 
                                          text=f"0/{self.production_params.get('package_quantity', 0)}包",
                                          font=self.big_data_font, bg='white', fg='#333333')
        self.package_count_label.pack(anchor='e')
        
        self.completion_rate_label = tk.Label(count_frame, text="完成率0%",
                                            font=self.data_font, bg='white', fg='#666666')
        self.completion_rate_label.pack(anchor='e')
        
        # 进度条
        progress_frame = tk.Frame(parent, bg='white')
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                     maximum=100, length=600)
        progress_bar.pack(fill=tk.X, pady=5)
        
        # 平均重量显示
        avg_frame = tk.Frame(parent, bg='white')
        avg_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(avg_frame, text="平均重量", font=self.data_font,
                bg='white', fg='#333333').pack(side=tk.LEFT)
        
        self.avg_weight_label = tk.Label(avg_frame, text="0.0g", 
                                       font=self.big_data_font, bg='white', fg='#28a745')
        self.avg_weight_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 运行日志记录区域
        fault_frame = tk.LabelFrame(parent, text="运行日志记录", font=self.label_font,
                                  bg='white', fg='#333333')
        fault_frame.pack(fill=tk.BOTH, expand=True)
        
        # 运行日志记录文本框
        self.fault_text = tk.Text(fault_frame, height=8, font=self.data_font,
                                bg='white', fg='#333333', state='disabled')
        self.fault_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加初始消息
        self.add_fault_record("无")
    
    def create_footer_section(self, parent):
        """
        创建底部信息区域

        Args:
            parent: 父容器
        """
        # 底部信息容器
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # 版本信息
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=tkFont.Font(family="微软雅黑", size=10), 
                               bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))

        # 导入logo处理模块并创建logo组件
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
            print("[Production] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
    def center_window(self):
        """将生产界面窗口居中显示"""
        try:
            # 确保窗口已经完全创建
            self.root.update_idletasks()
            
            # 获取窗口尺寸
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # 如果窗口尺寸为1（未正确获取），使用设定的尺寸
            if width <= 1 or height <= 1:
                width = 1200
                height = 800
            
            # 计算居中位置
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            # 设置窗口位置
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            print(f"生产界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("1200x800")
    
    def start_production(self):
        """启动生产流程"""
        try:
            if not PLC_AVAILABLE:
                self.add_fault_record("PLC模块不可用，无法启动生产")
                return
            
            if not self.modbus_client or not self.modbus_client.is_connected:
                self.add_fault_record("PLC未连接，无法启动生产")
                return
            
            print("开始启动生产流程...")
            
            # 生成生产编号
            if PRODUCTION_DETAIL_DAO_AVAILABLE:
                self.production_id = ProductionDetailDAO.generate_production_id()
                self.add_fault_record(f"生产编号: {self.production_id}")
            else:
                self.production_id = f"P{datetime.now().strftime('%y%m%d%H%M')}"
                self.add_fault_record(f"生产编号: {self.production_id} (数据库不可用)")

            # 新增：创建生产记录
            if PRODUCTION_RECORD_DAO_AVAILABLE:
                success, message, record_id = ProductionRecordDAO.create_production_record(
                    production_id=self.production_id,
                    material_name=self.production_params.get('material_name', ''),
                    target_weight=self.production_params.get('target_weight', 0),
                    package_quantity=self.production_params.get('package_quantity', 0),
                    completed_packages=0  # 初始完成包数为0
                )

                if success:
                    self.add_fault_record(f"生产记录已创建: {message}")
                    print(f"[生产界面] 生产记录创建成功: {message}")
                else:
                    self.add_fault_record(f"生产记录创建失败: {message}")
                    print(f"[生产界面] 生产记录创建失败: {message}")
            else:
                self.add_fault_record("生产记录DAO不可用，无法创建生产记录")

            print(f"开始启动生产流程，生产编号: {self.production_id}")
            
            # 启用物料监测
            if self.monitoring_service:
                self.monitoring_service.set_material_check_enabled(True)
                print("[生产界面] E100监测已启用")
            
            # 在后台线程执行PLC操作
            def production_startup_thread():
                try:
                    # 1. 包数清零=0
                    print("步骤1: 发送包数清零=0命令")
                    if not self.modbus_client.write_coil(get_production_address('PackageCountClear'), False):
                        self.root.after(0, lambda: self.add_fault_record("发送包数清零=0命令失败"))
                        return
                    
                    # 等待50ms
                    time.sleep(0.05)
                    
                    # 2. 包数清零=1
                    print("步骤2: 发送包数清零=1命令")
                    if not self.modbus_client.write_coil(get_production_address('PackageCountClear'), True):
                        self.root.after(0, lambda: self.add_fault_record("发送包数清零=1命令失败"))
                        return
                    
                    # 3. 总启动=1（带互斥保护）
                    print("步骤3: 发送总启动命令（互斥保护）")
                    
                    # 先发送总停止=0（互斥保护）
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False):
                        self.root.after(0, lambda: self.add_fault_record("发送总停止=0命令失败"))
                        return
                    
                    # 等待50ms
                    time.sleep(0.05)
                    
                    # 发送总启动=1
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True):
                        self.root.after(0, lambda: self.add_fault_record("发送总启动=1命令失败"))
                        return
                    
                    # 启动成功，开始监控
                    self.root.after(0, self._start_monitoring)
                    print("生产流程启动成功")
                    
                except Exception as e:
                    error_msg = f"生产启动异常: {str(e)}"
                    print(error_msg)
                    self.root.after(0, lambda: self.add_fault_record(error_msg))
            
            # 启动后台线程
            startup_thread = threading.Thread(target=production_startup_thread, daemon=True)
            startup_thread.start()
            
        except Exception as e:
            error_msg = f"启动生产流程异常: {str(e)}"
            print(error_msg)
            self.add_fault_record(error_msg)
    
    def _start_monitoring(self):
        """开始监控生产状态"""
        try:
            self.is_production_running = True
            self.is_paused = False  # 确保初始状态为非暂停
            self.production_start_time = datetime.now()
            self.monitoring_threads_running = True
            
            # 确保按钮状态正确
            if self.pause_resume_btn:
                self.pause_resume_btn.config(text="⏸ 暂停", bg='#ffc107')
            
            print("开始生产监控...")
            
            # 启动物料监测服务（生产阶段）
            if self.monitoring_service:
                bucket_ids = list(range(1, 7))
                self.monitoring_service.start_monitoring(bucket_ids, "production")
                
                # 新增：启动生产监测
                self.monitoring_service.start_production_monitoring(
                    self.production_id, self.target_weight)
                
                print("[生产界面] 物料监测和生产监测服务已启动")
            
            # 启动计时器更新线程
            def timer_update_thread():
                while self.monitoring_threads_running:
                    try:
                        if self.production_start_time:
                            elapsed = datetime.now() - self.production_start_time
                            self.elapsed_time = elapsed
                            
                            # 格式化时间显示
                            total_seconds = int(elapsed.total_seconds())
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            seconds = total_seconds % 60
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            
                            # 在主线程更新界面
                            self.root.after(0, lambda: self.timer_label.config(text=time_str))
                        
                        time.sleep(1)  # 每1秒更新一次计时器
                    except Exception as e:
                        print(f"计时器更新异常: {e}")
                        break
            
            # 启动料斗重量监控线程（每100ms）
            def weight_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_bucket_weights()
                        time.sleep(0.1)  # 每100ms读取一次
                    except Exception as e:
                        print(f"重量监控异常: {e}")
                        self.root.after(0, lambda: self.add_fault_record(f"重量监控异常: {str(e)}"))
                        break
            
            # 启动包装数量监控线程（每1s）
            def package_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_package_count()
                        time.sleep(1)  # 每1秒读取一次
                    except Exception as e:
                        print(f"包装数量监控异常: {e}")
                        self.root.after(0, lambda: self.add_fault_record(f"包装数量监控异常: {str(e)}"))
                        break
            
            # 新增：启动平均重量更新线程（每2s）
            def avg_weight_update_thread():
                while self.monitoring_threads_running:
                    try:
                        self._update_average_weight_from_database()
                        time.sleep(2)  # 每2秒更新一次平均重量
                    except Exception as e:
                        print(f"平均重量更新异常: {e}")
                        break
            
            # 启动所有监控线程
            threading.Thread(target=timer_update_thread, daemon=True).start()
            threading.Thread(target=weight_monitoring_thread, daemon=True).start()
            threading.Thread(target=package_monitoring_thread, daemon=True).start()
            threading.Thread(target=avg_weight_update_thread, daemon=True).start()  # 新增
            
        except Exception as e:
            error_msg = f"启动监控异常: {str(e)}"
            print(error_msg)
            self.add_fault_record(error_msg)
    
    def _read_bucket_weights(self):
        """读取料斗重量（在后台线程中调用）"""
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return
            
            weights_updated = False
            total_weight = 0
            valid_count = 0
            
            # 读取每个料斗的重量
            for bucket_id in range(1, 7):
                weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
                
                # 读取重量数据
                raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                
                if raw_weight_data is not None and len(raw_weight_data) > 0:
                    # 重量值需要除以10
                    raw_value = raw_weight_data[0]
  
                # 如果大于32767，说明是负数（16位补码）
                    if raw_value > 32767:
                        signed_value = raw_value - 65536  # 转换为负数
                    else:
                        signed_value = raw_value
                
                    weight_value = signed_value / 10.0
                
                    if weight_value != self.bucket_weights[bucket_id]:
                        self.bucket_weights[bucket_id] = weight_value
                        weights_updated = True

                        # 在主线程更新界面
                        self.root.after(0, lambda bid=bucket_id, w=weight_value: 
                                      self.bucket_weight_labels[bid].config(text=f"{w:.1f}g"))
                    
                    total_weight += weight_value
                    valid_count += 1
                else:
                    # 读取失败，设置状态为错误
                    if self.bucket_status[bucket_id] != 'error':
                        self.bucket_status[bucket_id] = 'error'
                        self.root.after(0, lambda bid=bucket_id: self._update_bucket_status(bid, 'error'))
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}重量读取失败"))
            
            # 更新平均重量
            if valid_count > 0:
                avg_weight = total_weight / valid_count
                self.root.after(0, lambda: self.avg_weight_label.config(text=f"{avg_weight:.1f}g"))
                
        except Exception as e:
            print(f"读取料斗重量异常: {e}")
    
    def _read_package_count(self):
        """读取包装数量（在后台线程中调用）"""
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return
            
            # 读取包装计数寄存器
            package_data = self.modbus_client.read_holding_registers(
                get_production_address('PackageCountRegister'), 1)
            
            if package_data is not None and len(package_data) > 0:
                new_count = package_data[0]
                
                if new_count != self.current_package_count:
                    self.current_package_count = new_count
                    
                    # 在主线程更新界面
                    self.root.after(0, self._update_package_display)
            else:
                self.root.after(0, lambda: self.add_fault_record("包装数量读取失败"))
                
        except Exception as e:
            print(f"读取包装数量异常: {e}")
    
    def _update_package_display(self):
        """更新包装数量显示（在主线程中调用）"""
        try:
            total_packages = self.production_params.get('package_quantity', 0)
            
            # 更新包装数量标签
            self.package_count_label.config(text=f"{self.current_package_count}/{total_packages}包")
            
            # 更新完成率
            if total_packages > 0:
                completion_rate = (self.current_package_count / total_packages) * 100
                self.completion_rate_label.config(text=f"完成率{completion_rate:.1f}%")
                
                # 更新进度条
                self.progress_var.set(completion_rate)
                
                # 检查是否完成
                if self.current_package_count >= total_packages:
                    self._production_completed()
            
        except Exception as e:
            print(f"更新包装显示异常: {e}")
    
    def _update_bucket_status(self, bucket_id: int, status: str):
        """更新料斗状态指示灯（在主线程中调用）"""
        try:
            self.bucket_status[bucket_id] = status
            
            if bucket_id in self.bucket_status_indicators:
                canvas = self.bucket_status_indicators[bucket_id]
                canvas.delete("all")
                
                if status == 'normal':
                    # 绿色指示灯
                    canvas.create_oval(3, 3, 17, 17, fill='#28a745', outline='#28a745')
                else:
                    # 红色指示灯
                    canvas.create_oval(3, 3, 17, 17, fill='#dc3545', outline='#dc3545')
                    
        except Exception as e:
            print(f"更新料斗状态异常: {e}")
    
    def _update_average_weight_from_database(self):
        """从数据库更新平均重量（在后台线程中调用）"""
        try:
            if not PRODUCTION_DETAIL_DAO_AVAILABLE or not self.production_id:
                return
            
            # 获取有效重量总和和有效记录数
            total_weight, valid_count = ProductionDetailDAO.get_valid_weight_sum_by_production(
                self.production_id)
            
            if valid_count > 0:
                avg_weight = total_weight / valid_count
                # 在主线程更新界面
                self.root.after(0, lambda: self.avg_weight_label.config(text=f"{avg_weight:.1f}g"))
            else:
                # 没有有效数据时显示0
                self.root.after(0, lambda: self.avg_weight_label.config(text="0.0g"))
                
        except Exception as e:
            print(f"从数据库更新平均重量异常: {e}")
            
    def _on_production_detail_recorded(self, bucket_id: int, detail: ProductionDetail):
        """
        处理生产明细记录事件
        
        Args:
            bucket_id: 料斗ID
            detail: 生产明细对象
        """
        try:
            # 记录到故障日志中（用于跟踪）
            status = "有效" if detail.is_valid else "无效"
            qualified = "合格" if detail.is_qualified else "不合格"
            
            log_message = (f"料斗{bucket_id}: {detail.real_weight:.1f}g, "
                         f"误差{detail.error_value:+.1f}g, {qualified}, {status}")
            
            self.add_fault_record(log_message)
            
        except Exception as e:
            print(f"处理生产明细记录事件异常: {e}")
            
    def _on_production_stop_triggered(self, bucket_id: int, reason: str):
        """
        处理生产停止触发事件
        
        Args:
            bucket_id: 料斗ID
            reason: 停止原因
        """
        try:
            # 记录到故障日志
            self.add_fault_record(f"生产已停止 - 料斗{bucket_id}: {reason}")

            # 检查是否是连续3次不合格
            if "连续3次不合格" in reason:
                # 显示E002弹窗(注释恢复)
                # self.root.after(0, lambda: self.show_e002_dialog(bucket_id))
                print(f"[生产界面] 显示料斗{bucket_id}连续3次不合格")
            else:
                # 其他情况自动暂停生产状态
                self.root.after(0, self._handle_production_auto_pause)

        except Exception as e:
            print(f"处理生产停止触发事件异常: {e}")
            
    def show_e002_dialog(self, bucket_id: int):
        """
        显示E002算法失效弹窗（图1）

        Args:
            bucket_id: 故障料斗ID
        """
        try:
            # 创建E002弹窗
            e002_window = tk.Toplevel(self.root)
            e002_window.title("")
            e002_window.geometry("700x500")
            e002_window.configure(bg='#ffb444')  # 橙色背景
            e002_window.resizable(False, False)
            e002_window.transient(self.root)
            e002_window.grab_set()

            # 禁用窗口关闭按钮
            e002_window.protocol("WM_DELETE_WINDOW", lambda: None)

            # 居中显示弹窗
            self.center_dialog_relative_to_main(e002_window, 700, 500)

            # 故障代码
            tk.Label(e002_window, text="故障代码：E002", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=50)

            # 故障类型
            tk.Label(e002_window, text="故障类型：算法失效", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=90)

            # 故障描述
            tk.Label(e002_window, text=f"故障描述：连续三次超出允许范围，认定为算法失效", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=130)

            # 处理方法
            processing_text = "处理方法：请选择弃用故障料斗，或全部重新自适应学习"
            tk.Label(e002_window, text=processing_text, 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white', justify='left').place(x=50, y=170)

            # 按钮区域
            button_frame = tk.Frame(e002_window, bg='#ffb444')
            button_frame.place(x=150, y=350)

            # 弃用料斗按钮
            disable_btn = tk.Button(button_frame, text="✕ 弃用料斗", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='white', fg='#333333',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=lambda: self._handle_disable_bucket_choice(e002_window, bucket_id))
            disable_btn.pack(side=tk.LEFT, padx=20)

            # 重新学习按钮
            relearn_btn = tk.Button(button_frame, text="▶ 重新学习", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#2196f3', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=lambda: self._handle_relearn_choice(e002_window, bucket_id))
            relearn_btn.pack(side=tk.LEFT, padx=20)

            print(f"[生产界面] 显示料斗{bucket_id} E002算法失效弹窗")

        except Exception as e:
            error_msg = f"显示E002弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)

    def _handle_disable_bucket_choice(self, e002_window, bucket_id: int):
        """
        处理弃用料斗选择

        Args:
            e002_window: E002弹窗对象
            bucket_id: 料斗ID
        """
        try:
            # 关闭E002弹窗
            e002_window.destroy()

            # 显示确认弃用弹窗
            self.show_disable_confirm_dialog(bucket_id)

        except Exception as e:
            print(f"[错误] 处理弃用料斗选择异常: {e}")

    def _handle_relearn_choice(self, e002_window, bucket_id: int):
        """
        处理重新学习选择

        Args:
            e002_window: E002弹窗对象
            bucket_id: 料斗ID
        """
        try:
            # 关闭E002弹窗
            e002_window.destroy()

            # 显示确认重新学习弹窗
            result = messagebox.askyesno("确认重新学习", 
                                       f"确定要重新学习料斗{bucket_id}参数吗？\n\n"
                                       f"将跳转到AI模式界面重新开始AI生产流程。")

            if result:
                # 停止当前生产
                self.monitoring_threads_running = False
                self.is_production_running = False

                # 停止生产监测
                if self.monitoring_service:
                    self.monitoring_service.stop_production_monitoring()

                # 停止PLC
                if self.modbus_client and self.modbus_client.is_connected:
                    self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)

                self.add_fault_record(f"料斗{bucket_id}选择重新学习，跳转到AI模式")

                # 跳转到AI模式界面
                self.on_closing()  # 这会返回到AI模式界面

        except Exception as e:
            print(f"[错误] 处理重新学习选择异常: {e}")

    def show_disable_confirm_dialog(self, bucket_id: int):
        """
        显示确认弃用料斗弹窗（图2）

        Args:
            bucket_id: 料斗ID
        """
        try:
            # 创建确认弃用弹窗
            disable_confirm_window = tk.Toplevel(self.root)
            disable_confirm_window.title("")
            disable_confirm_window.geometry("700x500")
            disable_confirm_window.configure(bg='#ffb444')  # 橙色背景
            disable_confirm_window.resizable(False, False)
            disable_confirm_window.transient(self.root)
            disable_confirm_window.grab_set()

            # X按钮点击时返回E002弹窗
            def on_window_close():
                disable_confirm_window.destroy()
                # 返回E002弹窗
                self.show_e002_dialog(bucket_id)

            disable_confirm_window.protocol("WM_DELETE_WINDOW", on_window_close)

            # 居中显示弹窗
            self.center_dialog_relative_to_main(disable_confirm_window, 700, 500)

            # 确认信息
            tk.Label(disable_confirm_window, text="请确认弃用故障料斗", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='#ffb444', fg='white').place(x=250, y=150)

            tk.Label(disable_confirm_window, text="其他料斗继续生产运行", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='#ffb444', fg='white').place(x=230, y=200)

            # 按钮区域
            button_frame = tk.Frame(disable_confirm_window, bg='#ffb444')
            button_frame.place(x=200, y=320)

            # 取消按钮
            def on_cancel():
                disable_confirm_window.destroy()
                # 返回E002弹窗
                self.show_e002_dialog(bucket_id)

            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='white', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=40, pady=10,
                                 command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=30)

            # 确认弃用按钮
            def on_confirm_disable():
                disable_confirm_window.destroy()
                self._execute_disable_bucket(bucket_id)

            confirm_btn = tk.Button(button_frame, text="确认弃用", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=10,
                                  command=on_confirm_disable)
            confirm_btn.pack(side=tk.LEFT, padx=30)

            print(f"[生产界面] 显示料斗{bucket_id}确认弃用弹窗")

        except Exception as e:
            error_msg = f"显示确认弃用弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)

    def _execute_disable_bucket(self, bucket_id: int):
        """
        执行弃用料斗操作

        Args:
            bucket_id: 料斗ID
        """
        try:
            if not BUCKET_DISABLE_AVAILABLE:
                self.add_fault_record("料斗禁用功能不可用")
                return

            # 在后台线程执行PLC操作
            def disable_thread():
                try:
                    # 向对应料斗禁用地址发送1
                    disable_address = get_bucket_disable_address(bucket_id)
                    success = self.modbus_client.write_coil(disable_address, True)

                    if success:
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}已禁用"))
                        print(f"[生产界面] 料斗{bucket_id}禁用命令发送成功")
                    else:
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}禁用命令发送失败"))
                        print(f"[生产界面] 料斗{bucket_id}禁用命令发送失败")

                    # 继续生产（总停止=0，总启动=1）先发送总停止=0
                    success1 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)

                    # 等待50ms
                    time.sleep(0.05)

                    # 发送总启动=1
                    success2 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)

                    if success1 and success2:
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}已弃用，其他料斗继续生产"))
                        print(f"[生产界面] 料斗{bucket_id}弃用后继续生产成功")
                    else:
                        self.root.after(0, lambda: self.add_fault_record("继续生产命令发送失败"))
                        print("[生产界面] 继续生产命令发送失败")

                except Exception as e:
                    error_msg = f"弃用料斗{bucket_id}操作异常: {str(e)}"
                    print(f"[错误] {error_msg}")
                    self.root.after(0, lambda: self.add_fault_record(error_msg))

            # 启动禁用操作线程
            threading.Thread(target=disable_thread, daemon=True).start()

        except Exception as e:
            error_msg = f"执行弃用料斗{bucket_id}操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)

    def _handle_production_auto_pause(self):
        """处理生产自动暂停（在主线程中调用）"""
        try:
            if self.is_production_running and not self.is_paused:
                # 更新状态为暂停
                self.is_paused = True
                self.is_production_running = False
                
                # 更新按钮文本和颜色
                if self.pause_resume_btn:
                    self.pause_resume_btn.config(text="▶ 启动", bg='#28a745')
                
                # 记录日志
                self.add_fault_record("生产因质量问题自动暂停")
                print("生产因质量问题自动暂停")
            
        except Exception as e:
            print(f"处理生产自动暂停异常: {e}")
    
    def _production_completed(self):
        """生产完成处理"""
        try:
            print("生产任务完成")

            # 停止监控
            self.monitoring_threads_running = False
            self.is_production_running = False

            # 停止PLC
            if self.modbus_client and self.modbus_client.is_connected:
                self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)

            # 获取物料名称
            material_name = self.production_params.get('material_name', '')

            # 新增：更新生产记录
            if PRODUCTION_RECORD_DAO_AVAILABLE and self.production_id:
                success, message = ProductionRecordDAO.update_production_record(
                    production_id=self.production_id,
                    completed_packages=self.current_package_count
                )

                if success:
                    self.add_fault_record(f"生产记录已更新: {message}")
                    print(f"[生产界面] 生产记录更新成功: {message}")
                else:
                    self.add_fault_record(f"生产记录更新失败: {message}")
                    print(f"[生产界面] 生产记录更新失败: {message}")

            # 新增：更新物料AI状态为"已生产"
            if MATERIAL_DAO_AVAILABLE and material_name:
                try:
                    # 获取物料信息
                    material = MaterialDAO.get_material_by_name(material_name)
                    if material:
                        # 更新AI状态为"已生产"
                        update_success, update_message = MaterialDAO.update_material_ai_status(
                            material.id, "已生产"
                        )

                        if update_success:
                            self.add_fault_record(f"物料AI状态已更新: {material_name} -> 已生产")
                            print(f"[生产界面] 物料AI状态更新成功: {material_name} -> 已生产")
                        else:
                            self.add_fault_record(f"物料AI状态更新失败: {update_message}")
                            print(f"[生产界面] 物料AI状态更新失败: {update_message}")
                    else:
                        self.add_fault_record(f"未找到物料: {material_name}")
                        print(f"[生产界面] 未找到物料: {material_name}")

                except Exception as e:
                    error_msg = f"更新物料AI状态异常: {str(e)}"
                    self.add_fault_record(error_msg)
                    print(f"[生产界面] {error_msg}")
            else:
                if not MATERIAL_DAO_AVAILABLE:
                    self.add_fault_record("物料DAO不可用，无法更新物料AI状态")
                if not material_name:
                    self.add_fault_record("物料名称为空，无法更新物料AI状态")

            # 计算实际完成率
            target_packages = self.production_params.get('package_quantity', 0)
            actual_completion_rate = (self.current_package_count / target_packages * 100) if target_packages > 0 else 0

            # 显示完成消息
            messagebox.showinfo("生产完成", 
                              f"🎉 生产任务已完成！\n\n"
                              f"生产编号: {self.production_id}\n"
                              f"物料名称: {material_name}\n"
                              f"目标重量: {self.production_params.get('target_weight', 0)}g\n"
                              f"目标包数: {target_packages}\n"
                              f"实际包数: {self.current_package_count}\n"
                              f"完成率: {actual_completion_rate:.2f}%\n"
                              f"用时: {self.timer_label.cget('text')}\n\n"
                              f"✅ 物料AI状态已更新为'已生产'")

        except Exception as e:
            print(f"生产完成处理异常: {e}")
    
    def add_fault_record(self, message: str):
        """添加运行日志记录"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            record = f"[{timestamp}] {message}\n"
            
            self.fault_text.config(state='normal')
            self.fault_text.insert(tk.END, record)
            self.fault_text.see(tk.END)
            self.fault_text.config(state='disabled')
            
        except Exception as e:
            print(f"添加运行日志记录异常: {e}")
    
    def on_pause_resume_click(self):
        """暂停/启动按钮点击事件"""
        try:
            if not self.is_paused:
                # 当前是运行状态，显示确认暂停弹窗
                self.show_pause_confirmation_dialog()
            else:
                # 当前是暂停状态，执行启动操作
                self._resume_production()

        except Exception as e:
            print(f"暂停/启动操作异常: {e}")
            self.add_fault_record(f"暂停/启动操作异常: {str(e)}")
            
    def show_pause_confirmation_dialog(self):
        """显示暂停确认对话框（图1）"""
        try:
            # 创建确认暂停弹窗
            pause_confirm_window = tk.Toplevel(self.root)
            pause_confirm_window.title("")
            pause_confirm_window.geometry("600x400")
            pause_confirm_window.configure(bg='white')
            pause_confirm_window.resizable(False, False)
            pause_confirm_window.transient(self.root)
            pause_confirm_window.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(pause_confirm_window, 600, 400)
            
            # 暂停图标和提示信息
            tk.Label(pause_confirm_window, text="⏸", 
                    font=tkFont.Font(family="微软雅黑", size=36, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=30)
            
            tk.Label(pause_confirm_window, text="请再次确认你希望", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            tk.Label(pause_confirm_window, text="暂停运行", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            # 按钮区域
            button_frame = tk.Frame(pause_confirm_window, bg='white')
            button_frame.pack(pady=40)
            
            # 取消按钮
            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='#f0f0f0', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=40, pady=10,
                                 command=pause_confirm_window.destroy)
            cancel_btn.pack(side=tk.LEFT, padx=20)
            
            # 确认按钮
            def on_confirm_pause():
                pause_confirm_window.destroy()
                # 执行暂停操作
                self._pause_production()
                # 显示暂停进行中弹窗
                self.show_pausing_progress_dialog()
            
            confirm_btn = tk.Button(button_frame, text="确认", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=10,
                                  command=on_confirm_pause)
            confirm_btn.pack(side=tk.LEFT, padx=20)
            
            print("[信息] 显示暂停确认对话框")
            
        except Exception as e:
            error_msg = f"显示暂停确认对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            
    def show_pausing_progress_dialog(self):
        """显示暂停进行中对话框（图2）"""
        try:
            # 创建暂停进行中弹窗
            self.pausing_progress_window = tk.Toplevel(self.root)
            self.pausing_progress_window.title("")
            self.pausing_progress_window.geometry("600x400")
            self.pausing_progress_window.configure(bg='white')
            self.pausing_progress_window.resizable(False, False)
            self.pausing_progress_window.transient(self.root)
            self.pausing_progress_window.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(self.pausing_progress_window, 600, 400)
            
            # 暂停图标
            tk.Label(self.pausing_progress_window, text="⏸", 
                    font=tkFont.Font(family="微软雅黑", size=36, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            # 状态提示
            tk.Label(self.pausing_progress_window, text="设备正在暂停中", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=10)
            
            # 计时器显示
            self.pausing_timer_label = tk.Label(self.pausing_progress_window, text="00:00:00", 
                                               font=tkFont.Font(family="Arial", size=18, weight="bold"),
                                               bg='white', fg='#333333')
            self.pausing_timer_label.pack(pady=10)
            
            # 启动暂停计时器
            self.pausing_timer_start_time = datetime.now()
            self.pausing_timer_running = True
            self.start_pausing_timer()
            
            # 按钮区域
            button_frame = tk.Frame(self.pausing_progress_window, bg='white')
            button_frame.pack(pady=40)
            
            # 取消生产按钮
            cancel_production_btn = tk.Button(button_frame, text="✖ 取消生产", 
                                            font=tkFont.Font(family="微软雅黑", size=14),
                                            bg='#f0f0f0', fg='#333333',
                                            relief='flat', bd=0,
                                            padx=30, pady=10,
                                            command=self.show_cancel_production_dialog)
            cancel_production_btn.pack(side=tk.LEFT, padx=20)
            
            # 继续按钮
            def on_continue():
                self.stop_pausing_timer()
                self.pausing_progress_window.destroy()
                # 恢复生产
                self._resume_production()
            
            continue_btn = tk.Button(button_frame, text="▶ 继续", 
                                   font=tkFont.Font(family="微软雅黑", size=14),
                                   bg='#4a90e2', fg='white',
                                   relief='flat', bd=0,
                                   padx=30, pady=10,
                                   command=on_continue)
            continue_btn.pack(side=tk.LEFT, padx=20)
            
            print("[信息] 显示暂停进行中对话框")
            
        except Exception as e:
            error_msg = f"显示暂停进行中对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            
    def show_cancel_production_dialog(self):
        """显示取消生产确认对话框（图3）"""
        try:
            # 停止暂停计时器
            self.stop_pausing_timer()
            
            # 关闭暂停进行中弹窗
            if hasattr(self, 'pausing_progress_window') and self.pausing_progress_window:
                self.pausing_progress_window.destroy()
            
            # 创建取消生产确认弹窗
            cancel_confirm_window = tk.Toplevel(self.root)
            cancel_confirm_window.title("")
            cancel_confirm_window.geometry("600x400")
            cancel_confirm_window.configure(bg='white')
            cancel_confirm_window.resizable(False, False)
            cancel_confirm_window.transient(self.root)
            cancel_confirm_window.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(cancel_confirm_window, 600, 400)
            
            # 取消图标
            tk.Label(cancel_confirm_window, text="✖", 
                    font=tkFont.Font(family="微软雅黑", size=36, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=30)
            
            # 确认信息
            tk.Label(cancel_confirm_window, text="请再次确认你希望", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            tk.Label(cancel_confirm_window, text="取消生产", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            # 按钮区域
            button_frame = tk.Frame(cancel_confirm_window, bg='white')
            button_frame.pack(pady=40)
            
            # 取消按钮
            def on_cancel():
                cancel_confirm_window.destroy()
                # 返回暂停进行中弹窗
                self.show_pausing_progress_dialog()
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='#f0f0f0', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=40, pady=10,
                                 command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=20)
            
            # 确认按钮
            def on_confirm_cancel():
                cancel_confirm_window.destroy()
                # 退出生产界面，返回AI模式界面
                self.on_closing()
            
            confirm_btn = tk.Button(button_frame, text="确认", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=10,
                                  command=on_confirm_cancel)
            confirm_btn.pack(side=tk.LEFT, padx=20)
            
            print("[信息] 显示取消生产确认对话框")
            
        except Exception as e:
            error_msg = f"显示取消生产确认对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            
    def start_pausing_timer(self):
        """启动暂停计时器"""
        try:
            def update_pausing_timer():
                """更新暂停计时器显示"""
                if (hasattr(self, 'pausing_timer_running') and self.pausing_timer_running and
                    hasattr(self, 'pausing_progress_window') and self.pausing_progress_window and
                    self.pausing_progress_window.winfo_exists()):
                    try:
                        # 计算经过的时间
                        current_time = datetime.now()
                        elapsed_time = current_time - self.pausing_timer_start_time
                        
                        # 格式化为 HH:MM:SS
                        total_seconds = int(elapsed_time.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        # 更新标签
                        if (hasattr(self, 'pausing_timer_label') and 
                            self.pausing_timer_label.winfo_exists()):
                            self.pausing_timer_label.config(text=time_str)
                            # 继续更新
                            self.root.after(1000, update_pausing_timer)
                        else:
                            self.pausing_timer_running = False
                    except Exception as e:
                        print(f"[错误] 更新暂停计时器异常: {e}")
                        self.pausing_timer_running = False
            
            # 开始更新计时器
            update_pausing_timer()
            print("[信息] 暂停计时器已启动")
            
        except Exception as e:
            error_msg = f"启动暂停计时器异常: {str(e)}"
            print(f"[错误] {error_msg}")
            
    def stop_pausing_timer(self):
        """停止暂停计时器"""
        try:
            if hasattr(self, 'pausing_timer_running'):
                self.pausing_timer_running = False
                print("[信息] 暂停计时器已停止")
        except Exception as e:
            print(f"[错误] 停止暂停计时器异常: {e}")
            
    def center_dialog_relative_to_main(self, dialog_window, dialog_width, dialog_height):
        """
        将弹窗相对于生产界面居中显示

        Args:
            dialog_window: 弹窗对象
            dialog_width (int): 弹窗宽度
            dialog_height (int): 弹窗高度
        """
        try:
            # 确保窗口信息是最新的
            dialog_window.update_idletasks()
            self.root.update_idletasks()

            # 获取生产界面的位置和尺寸
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()

            # 计算相对于生产界面居中的位置
            x = main_x + (main_width - dialog_width) // 2
            y = main_y + (main_height - dialog_height) // 2

            # 确保弹窗不会超出屏幕边界
            screen_width = dialog_window.winfo_screenwidth()
            screen_height = dialog_window.winfo_screenheight()

            # 调整坐标，确保不超出屏幕边界
            if x + dialog_width > screen_width:
                x = screen_width - dialog_width - 20
            if x < 20:
                x = 20
            if y + dialog_height > screen_height:
                y = screen_height - dialog_height - 20
            if y < 20:
                y = 20

            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        except Exception as e:
            print(f"[错误] 弹窗居中失败: {e}")
            # 备用：屏幕居中
            x = (dialog_window.winfo_screenwidth() - dialog_width) // 2
            y = (dialog_window.winfo_screenheight() - dialog_height) // 2
            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _pause_production(self):
        """暂停生产"""
        try:
            if self.is_production_running:
                # 停止监控线程
                self.monitoring_threads_running = False
                
                # 发送停止命令到PLC
                if self.modbus_client and self.modbus_client.is_connected:
                    # 发送总启动=0（停止）
                    success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                    if not success:
                        self.add_fault_record("发送总启动=0命令失败")
                        return
                        
                    # 等待50ms
                    time.sleep(0.05)
                    
                    # 发送总停止=1（停止）
                    success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                    if not success:
                        self.add_fault_record("发送总停止=1命令失败")
                        return
                
                # 更新状态
                self.is_paused = True
                self.is_production_running = False
                
                # 更新按钮文本和颜色
                self.pause_resume_btn.config(text="▶ 启动", bg='#28a745')
                
                # 记录日志
                self.add_fault_record("生产已暂停")
                print("生产已暂停")
                
        except Exception as e:
            print(f"暂停生产异常: {e}")
            self.add_fault_record(f"暂停生产异常: {str(e)}")
    
    def _resume_production(self):
        """恢复生产"""
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                # 在后台线程执行PLC操作，避免阻塞界面
                def resume_thread():
                    try:
                        # 互斥保护：先发送总停止=0
                        print("恢复生产：发送总停止=0命令（互斥保护）")
                        if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False):
                            self.root.after(0, lambda: self.add_fault_record("发送总停止=0命令失败"))
                            return
                        
                        # 等待50ms
                        time.sleep(0.05)
                        
                        # 发送总启动=1
                        print("恢复生产：发送总启动=1命令")
                        if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True):
                            self.root.after(0, lambda: self.add_fault_record("发送总启动=1命令失败"))
                            return
                        
                        # 在主线程更新状态
                        self.root.after(0, self._handle_resume_success)
                        
                    except Exception as e:
                        error_msg = f"恢复生产异常: {str(e)}"
                        print(error_msg)
                        self.root.after(0, lambda: self.add_fault_record(error_msg))
                
                # 启动恢复操作线程
                resume_operation_thread = threading.Thread(target=resume_thread, daemon=True)
                resume_operation_thread.start()
            else:
                self.add_fault_record("PLC未连接，无法恢复生产")
                
        except Exception as e:
            print(f"恢复生产异常: {e}")
            self.add_fault_record(f"恢复生产异常: {str(e)}")
    
    def _handle_resume_success(self):
        """处理恢复生产成功（在主线程中调用）"""
        try:
            # 更新状态
            self.is_paused = False
            self.is_production_running = True
            
            # 更新按钮文本和颜色
            self.pause_resume_btn.config(text="⏸ 暂停", bg='#ffc107')
            
            # 重新启动监控线程
            self._restart_monitoring()
            
            # 记录日志
            self.add_fault_record("生产已恢复")
            print("生产已恢复")
            
        except Exception as e:
            print(f"处理恢复生产成功异常: {e}")
            self.add_fault_record(f"处理恢复生产异常: {str(e)}")
    
    def _restart_monitoring(self):
        """重新启动监控线程"""
        try:
            self.monitoring_threads_running = True
            
            print("重新启动生产监控...")
            
            # 重新启动生产监测
            if self.monitoring_service and self.production_id and self.target_weight:
                self.monitoring_service.start_production_monitoring(
                    self.production_id, self.target_weight)
            
            # 启动计时器更新线程
            def timer_update_thread():
                while self.monitoring_threads_running:
                    try:
                        if self.production_start_time:
                            elapsed = datetime.now() - self.production_start_time
                            self.elapsed_time = elapsed
                            
                            # 格式化时间显示
                            total_seconds = int(elapsed.total_seconds())
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            seconds = total_seconds % 60
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            
                            # 在主线程更新界面
                            self.root.after(0, lambda: self.timer_label.config(text=time_str))
                        
                        time.sleep(1)  # 每1秒更新一次计时器
                    except Exception as e:
                        print(f"计时器更新异常: {e}")
                        break
                    
            # 启动料斗重量监控线程（每100ms）
            def weight_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_bucket_weights()
                        time.sleep(0.1)  # 每100ms读取一次
                    except Exception as e:
                        print(f"重量监控异常: {e}")
                        self.root.after(0, lambda: self.add_fault_record(f"重量监控异常: {str(e)}"))
                        break
                    
            # 启动包装数量监控线程（每1s）
            def package_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_package_count()
                        time.sleep(1)  # 每1秒读取一次
                    except Exception as e:
                        print(f"包装数量监控异常: {e}")
                        self.root.after(0, lambda: self.add_fault_record(f"包装数量监控异常: {str(e)}"))
                        break
            
            # 新增：启动平均重量更新线程
            def avg_weight_update_thread():
                while self.monitoring_threads_running:
                    try:
                        self._update_average_weight_from_database()
                        time.sleep(2)
                    except Exception as e:
                        print(f"平均重量更新异常: {e}")
                        break
                    
            # 启动所有监控线程
            threading.Thread(target=timer_update_thread, daemon=True).start()
            threading.Thread(target=weight_monitoring_thread, daemon=True).start()
            threading.Thread(target=package_monitoring_thread, daemon=True).start()
            threading.Thread(target=avg_weight_update_thread, daemon=True).start()
            
        except Exception as e:
            error_msg = f"重新启动监控异常: {str(e)}"
            print(error_msg)
            self.add_fault_record(error_msg)
    
    def on_cancel_click(self):
        """取消按钮点击事件"""
        try:
            result = messagebox.askyesno("确认取消", "确定要取消当前生产任务吗？")
            if result:
                # 停止生产
                self._pause_production()
                
                self.add_fault_record("生产任务已取消")
                
                # 关闭生产界面，回到AI模式界面
                self.on_closing()
            
        except Exception as e:
            print(f"取消生产异常: {e}")
            self.add_fault_record(f"取消操作异常: {str(e)}")
            
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        """
        处理物料不足检测事件
        
        Args:
            bucket_id (int): 料斗ID
            stage (str): 当前阶段
            is_production (bool): 是否为生产阶段
        """
        try:
            # 只处理生产阶段的物料不足
            if is_production and stage == "production":
                print(f"[生产界面] 料斗{bucket_id}在生产阶段检测到物料不足")
                
                # 弹窗显示的同时立即执行停止命令
                print("[生产界面] 生产阶段物料不足，立即停止全部料斗运行")
                self._handle_material_shortage_stop()
                
                # 在主线程显示物料不足弹窗
                self.root.after(0, lambda: self._show_material_shortage_dialog(bucket_id))
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足事件异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.root.after(0, lambda: self.add_fault_record(error_msg))
    
    def _handle_material_shortage_stop(self):
        """
        处理物料不足时的总停止命令
        """
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                # 在后台线程执行PLC操作
                def stop_thread():
                    try:
                        print("[生产界面] 物料不足，发送总启动=0命令")
                        success1 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                        
                        print("[生产界面] 物料不足，发送总停止=1命令")
                        success2 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                        
                        if success1 and success2:
                            self.root.after(0, lambda: self.add_fault_record("物料不足，生产已自动停止"))
                            print("[生产界面] 物料不足总停止命令发送成功")
                        else:
                            self.root.after(0, lambda: self.add_fault_record("物料不足总停止命令发送失败"))
                            print("[生产界面] 物料不足总停止命令发送失败")
                    
                    except Exception as e:
                        error_msg = f"物料不足停止命令异常: {str(e)}"
                        print(f"[错误] {error_msg}")
                        self.root.after(0, lambda: self.add_fault_record(error_msg))
                
                # 启动停止操作线程
                threading.Thread(target=stop_thread, daemon=True).start()
        
        except Exception as e:
            error_msg = f"处理E100停止命令异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
    
    def _show_material_shortage_dialog(self, bucket_id: int):
        """
        显示物料不足弹窗(类似图1的样式)
        
        Args:
            bucket_id (int): 料斗ID
        """
        try:
            # 创建物料不足弹窗
            material_shortage_window = tk.Toplevel(self.root)
            material_shortage_window.title("")
            material_shortage_window.geometry("700x500")
            material_shortage_window.configure(bg='#ffb444')  # 橙色背景
            material_shortage_window.resizable(False, False)
            material_shortage_window.transient(self.root)
            material_shortage_window.grab_set()
            
            # 禁用窗口关闭按钮，不能被关闭
            material_shortage_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(material_shortage_window, 700, 500)
            
            # 故障代码
            tk.Label(material_shortage_window, text="故障代码：E001", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=50)
            
            # 故障类型
            tk.Label(material_shortage_window, text="故障类型：物料不足/闭合异常", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=90)
            
            # 故障描述
            tk.Label(material_shortage_window, text=f"故障描述：料斗物料低于最低水平线或闭合不正常", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=130)
            
            # 处理方法
            processing_text = ("处理方法：1.请检查料斗物料是否低于最低水平线，如果是请加料\n"
                               "2.请检查料斗闭合是否正常，如闭合不正常，请手动归位完全闭合")
            tk.Label(material_shortage_window, text=processing_text, 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white', justify='left').place(x=50, y=170)
            
            # 按钮区域
            button_frame = tk.Frame(material_shortage_window, bg='#ffb444')
            button_frame.place(x=150, y=300)
            
            # 取消生产按钮
            cancel_btn = tk.Button(button_frame, text="✕ 取消生产", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='white', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=30, pady=10,
                                 command=lambda: self._handle_material_shortage_cancel(material_shortage_window))
            cancel_btn.pack(side=tk.LEFT, padx=20)
            
            # 继续按钮
            continue_btn = tk.Button(button_frame, text="▶ 继续", 
                                   font=tkFont.Font(family="微软雅黑", size=14),
                                   bg='#2196f3', fg='white',
                                   relief='flat', bd=0,
                                   padx=30, pady=10,
                                   command=lambda: self._handle_material_shortage_continue(material_shortage_window))
            continue_btn.pack(side=tk.LEFT, padx=20)
            
            print(f"[生产界面] 显示料斗{bucket_id}物料不足弹窗（不可关闭）")
            
        except Exception as e:
            error_msg = f"显示物料不足弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
    
    def _handle_material_shortage_continue(self, dialog_window):
        """
        处理物料不足继续操作
        
        Args:
            dialog_window: 弹窗对象
        """
        try:
            # 关闭弹窗
            dialog_window.destroy()
            
            # 调用物料监测服务的继续方法（生产阶段）
            if self.monitoring_service:
                self.monitoring_service.handle_material_shortage_continue(0, True)  # bucket_id=0表示生产阶段, is_production=True
            
            # 恢复生产
            self._resume_production_after_material_shortage()
            
            print("[生产界面] E001已处理，继续生产")
            
        except Exception as e:
            error_msg = f"处理物料不足继续操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
    
    def _handle_material_shortage_cancel(self, dialog_window):
        """
        处理物料不足取消生产操作
        
        Args:
            dialog_window: 弹窗对象
        """
        try:
            # 关闭弹窗
            dialog_window.destroy()
            
            # 显示取消生产确认弹窗（类似图2的样式）
            self._show_cancel_production_confirm_dialog()
            
            print("[生产界面] 用户选择取消生产")
            
        except Exception as e:
            error_msg = f"处理E001取消操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
    
    def _show_cancel_production_confirm_dialog(self):
        """
        显示取消生产确认弹窗(类似图2的样式)
        """
        try:
            # 创建取消生产确认弹窗
            cancel_confirm_window = tk.Toplevel(self.root)
            cancel_confirm_window.title("")
            cancel_confirm_window.geometry("600x400")
            cancel_confirm_window.configure(bg='#ffb444')  # 橙色背景
            cancel_confirm_window.resizable(False, False)
            cancel_confirm_window.transient(self.root)
            cancel_confirm_window.grab_set()
            
            # 🔥 修正：X按钮点击时返回上一个弹窗（重新显示物料不足弹窗）
            def on_window_close():
                cancel_confirm_window.destroy()
                # 返回上一个弹窗 - 重新显示物料不足弹窗
                self._show_material_shortage_dialog(1)  # 默认料斗1，实际应该保存之前的bucket_id
                print("[生产界面] 取消确认弹窗已关闭，返回物料不足弹窗")
            
            cancel_confirm_window.protocol("WM_DELETE_WINDOW", on_window_close)
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(cancel_confirm_window, 700, 500)
            
            # 确认信息
            processing_text = ("你确定要取消\n"
                               "结束此次生产")
            tk.Label(cancel_confirm_window, text=processing_text, 
                    font=tkFont.Font(family="微软雅黑", size=24, weight="bold"),
                    bg='#ffb444', fg='white').place(x=250, y=150)
            
            # 按钮区域
            button_frame = tk.Frame(cancel_confirm_window, bg='#ffb444')
            button_frame.place(x=300, y=300)
            
            # 确定按钮
            def on_confirm_cancel():
                cancel_confirm_window.destroy()
                # 执行取消生产操作
                self._execute_cancel_production()
            
            confirm_btn = tk.Button(button_frame, text="确定", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=on_confirm_cancel)
            confirm_btn.pack()
            
            print("[生产界面] 显示取消生产确认弹窗（X按钮返回上一弹窗）")
            
        except Exception as e:
            error_msg = f"显示取消生产确认弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
            
    def _on_single_unqualified_triggered(self, bucket_id: int, real_weight: float, error_value: float):
        """
        处理单次不合格事件
        
        Args:
            bucket_id (int): 料斗ID
            real_weight (float): 实际重量
            error_value (float): 误差值
        """
        try:
            # 记录到故障日志
            log_message = f"料斗{bucket_id}单次不合格: {real_weight:.1f}g, 误差{error_value:+.1f}g"
            self.add_fault_record(log_message)
            
            # 在主线程显示取走不合格产品弹窗
            self.root.after(0, lambda: self._show_remove_unqualified_product_dialog(bucket_id, real_weight, error_value))
            
        except Exception as e:
            print(f"处理单次不合格事件异常: {e}")
    
    def _show_remove_unqualified_product_dialog(self, bucket_id: int, real_weight: float, error_value: float):
        """
        显示取走不合格产品弹窗
        
        Args:
            bucket_id (int): 料斗ID
            real_weight (float): 实际重量
            error_value (float): 误差值
        """
        try:
            # 创建取走不合格产品弹窗
            remove_window = tk.Toplevel(self.root)
            remove_window.title("")
            remove_window.geometry("600x400")
            remove_window.configure(bg='white')
            remove_window.resizable(False, False)
            remove_window.transient(self.root)
            remove_window.grab_set()
            
            # 禁用窗口关闭按钮
            remove_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(remove_window, 600, 400)
            
            # 提示信息
            tk.Label(remove_window, text="请取走不合格产品", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='white', fg='#333333').place(x=200, y=120)
            
            # 详细信息（可选显示）
            detail_text = f"料斗{bucket_id}: {real_weight:.1f}g (误差{error_value:+.1f}g)"
            tk.Label(remove_window, text=detail_text, 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#666666').place(x=180, y=180)
            
            # 确认按钮
            def on_confirm_removed():
                """确认已取走按钮点击事件"""
                remove_window.destroy()
                # 发送恢复生产命令(注释恢复)
                self._send_resume_production_commands()
            
            confirm_btn = tk.Button(remove_window, text="确认", 
                                  font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                                  bg='#28a745', fg='white',
                                  relief='flat', bd=0,
                                  padx=50, pady=15,
                                  command=on_confirm_removed)
            confirm_btn.place(x=250, y=280)
            
            print(f"[生产界面] 显示料斗{bucket_id}取走不合格产品弹窗")
            
        except Exception as e:
            error_msg = f"显示取走不合格产品弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
    
    def _send_resume_production_commands(self):
        """发送恢复生产命令序列"""
        def resume_commands_thread():
            try:
                # 1. 总停止=0
                # success1 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)
                
                # 2. 向包装机停止地址发送1
                # success2 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                
                # 等待1s
                # time.sleep(1)
                
                # 3. 向包装机停止地址发送0
                success3 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)
                
                # 4. 总启动=1
                # success4 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)
                
                # if success1 and success2 and success3 and success4:
                if success3:
                    self.root.after(0, lambda: self.add_fault_record("恢复生产命令发送成功，生产已继续"))
                    print("[生产界面] 恢复生产命令发送成功")
                else:
                    self.root.after(0, lambda: self.add_fault_record("恢复生产命令发送失败"))
                    print("[生产界面] 恢复生产命令发送失败")
                    
            except Exception as e:
                error_msg = f"发送恢复生产命令异常: {str(e)}"
                print(f"[错误] {error_msg}")
                self.root.after(0, lambda: self.add_fault_record(error_msg))
        
        # 启动命令发送线程
        threading.Thread(target=resume_commands_thread, daemon=True).start()
    
    def _execute_cancel_production(self):
        """
        执行取消生产操作
        """
        try:
            # 调用物料监测服务的取消方法
            if self.monitoring_service:
                self.monitoring_service.handle_material_shortage_cancel()
            
            # 停止生产
            self._pause_production()
            
            # 获取物料名称
            material_name = self.production_params.get('material_name', '')
            
            # 新增：更新生产记录（记录取消时的完成包数）
            if PRODUCTION_RECORD_DAO_AVAILABLE and self.production_id:
                success, message = ProductionRecordDAO.update_production_record(
                    production_id=self.production_id,
                    completed_packages=self.current_package_count
                )
                
                if success:
                    self.add_fault_record(f"生产记录已更新（取消）: {message}")
                    print(f"[生产界面] 生产记录更新成功（取消）: {message}")
            
            # 新增：更新物料AI状态为"已生产"（即使是取消，也算作已生产过）
            if MATERIAL_DAO_AVAILABLE and material_name:
                try:
                    # 获取物料信息
                    material = MaterialDAO.get_material_by_name(material_name)
                    if material:
                        # 更新AI状态为"已生产"
                        update_success, update_message = MaterialDAO.update_material_ai_status(
                            material.id, "已生产"
                        )
                        
                        if update_success:
                            self.add_fault_record(f"物料AI状态已更新: {material_name} -> 已生产（取消）")
                            print(f"[生产界面] 物料AI状态更新成功: {material_name} -> 已生产（取消）")
                        else:
                            self.add_fault_record(f"物料AI状态更新失败: {update_message}")
                            print(f"[生产界面] 物料AI状态更新失败: {update_message}")
                    else:
                        self.add_fault_record(f"未找到物料: {material_name}")
                        print(f"[生产界面] 未找到物料: {material_name}")
                        
                except Exception as e:
                    error_msg = f"更新物料AI状态异常: {str(e)}"
                    self.add_fault_record(error_msg)
                    print(f"[生产界面] {error_msg}")
            else:
                if not MATERIAL_DAO_AVAILABLE:
                    self.add_fault_record("物料DAO不可用，无法更新物料AI状态")
                if not material_name:
                    self.add_fault_record("物料名称为空，无法更新物料AI状态")
            
            self.add_fault_record("用户取消生产，生产任务已终止")
            
            # 关闭生产界面，回到AI模式界面
            self.on_closing()
            
            print("[生产界面] 生产已取消，返回AI模式界面")
            
        except Exception as e:
            error_msg = f"执行取消生产操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
    
    def _resume_production_after_material_shortage(self):
        """
        物料不足问题解决后恢复生产
        """
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                # 在后台线程执行PLC操作
                def resume_thread():
                    try:
                        print("[生产界面] 物料不足问题解决，发送总停止=0命令（互斥保护）")
                        success1 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)
                        
                        # 等待50ms
                        time.sleep(0.05)
                        
                        print("[生产界面] 物料不足问题解决，发送总启动=1命令")
                        success2 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)
                        
                        if success1 and success2:
                            self.root.after(0, lambda: self.add_fault_record("物料不足问题已解决，生产已恢复"))
                            print("[生产界面] 物料不足问题解决，生产恢复成功")
                        else:
                            self.root.after(0, lambda: self.add_fault_record("恢复生产命令发送失败"))
                            print("[生产界面] 恢复生产命令发送失败")
                    
                    except Exception as e:
                        error_msg = f"恢复生产异常: {str(e)}"
                        print(f"[错误] {error_msg}")
                        self.root.after(0, lambda: self.add_fault_record(error_msg))
                
                # 启动恢复操作线程
                threading.Thread(target=resume_thread, daemon=True).start()
            else:
                self.add_fault_record("PLC未连接，无法恢复生产")
        
        except Exception as e:
            error_msg = f"恢复生产异常: {str(e)}"
            print(f"[错误] {error_msg}")
            self.add_fault_record(error_msg)
    
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            # 停止所有监控线程
            self.monitoring_threads_running = False
            self.is_production_running = False
            
            # 停止生产监测
            if self.monitoring_service:
                self.monitoring_service.stop_production_monitoring()
                self.monitoring_service.set_material_check_enabled(False)
                self.monitoring_service.stop_all_monitoring()
                print("[生产界面] 生产监测和物料监测服务已停止")
            
            # 禁用物料监测
            if self.monitoring_service:
                self.monitoring_service.set_material_check_enabled(False)
                self.monitoring_service.stop_all_monitoring()
                print("[生产界面] 物料监测服务已停止")
            
            # 停止PLC
            if self.modbus_client and self.modbus_client.is_connected:
                self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
            
            # 如果有主窗口引用，重新显示AI模式界面
            if self.main_window:
                try:
                    if hasattr(self.main_window, 'show_main_window'):
                        self.main_window.show_main_window()
                    else:
                        if hasattr(self.main_window, 'root'):
                            self.main_window.root.deiconify()
                            self.main_window.root.lift()
                            self.main_window.root.focus_force()
                except Exception as e:
                    print(f"显示AI模式界面时发生错误: {e}")
            
            print("生产界面已关闭")
            
        except Exception as e:
            print(f"关闭生产界面时发生错误: {e}")
        finally:
            # 关闭生产界面
            self.root.destroy()

def create_production_interface(parent, main_window, production_params):
    """
    创建生产界面实例的工厂函数
    
    Args:
        parent: 父窗口对象
        main_window: 主程序窗口引用
        production_params: 生产参数字典
        
    Returns:
        ProductionInterface: 生产界面实例
    """
    return ProductionInterface(parent, main_window, production_params)

# 示例使用
if __name__ == "__main__":
    # 测试用参数
    test_params = {
        'material_name': '珠光267LG',
        'target_weight': 268,
        'package_quantity': 500
    }
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 创建生产界面
    production_interface = create_production_interface(root, None, test_params)
    
    # 启动界面循环
    root.mainloop()