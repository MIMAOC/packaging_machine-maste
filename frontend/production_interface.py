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
6. 故障记录

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
        
        # 获取主窗口的modbus_client引用
        self.modbus_client = None
        if main_window and hasattr(main_window, 'modbus_client'):
            self.modbus_client = main_window.modbus_client
        
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
        self.pause_resume_btn = None  # ✅ 新增：暂停/启动按钮引用
        
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
        self.root.geometry("1200x800")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置界面字体"""
        # 标题字体
        self.title_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        # 标签字体
        self.label_font = tkFont.Font(family="微软雅黑", size=14, weight="bold")
        
        # 数据字体
        self.data_font = tkFont.Font(family="微软雅黑", size=12)
        
        # 大数据字体
        self.big_data_font = tkFont.Font(family="微软雅黑", size=16, weight="bold")
        
        # 按钮字体
        self.button_font = tkFont.Font(family="微软雅黑", size=12, weight="bold")
        
        # 小按钮字体
        self.small_button_font = tkFont.Font(family="微软雅黑", size=10)
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
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
                                        padx=20, pady=8,
                                        command=self.on_pause_resume_click)
        self.pause_resume_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = tk.Button(right_frame, text="✖ 取消", 
                             font=self.button_font,
                             bg='#dc3545', fg='white',
                             relief='flat', bd=0,
                             padx=20, pady=8,
                             command=self.on_cancel_click)
        cancel_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(10, 0))
    
    def create_bucket_monitoring_section(self, parent):
        """
        创建料斗监控区域
        
        Args:
            parent: 父容器
        """
        # 料斗监控容器
        for bucket_id in range(1, 7):
            bucket_frame = tk.Frame(parent, bg='#f8f9fa', relief='raised', bd=1)
            bucket_frame.pack(fill=tk.X, pady=5)
            bucket_frame.configure(width=200, height=50)
            bucket_frame.pack_propagate(False)
            
            # 左侧指示灯和料斗标签
            left_frame = tk.Frame(bucket_frame, bg='#f8f9fa')
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
            
            # 状态指示灯（绿色圆圈）
            indicator_canvas = tk.Canvas(left_frame, width=20, height=20, 
                                       bg='#f8f9fa', highlightthickness=0)
            indicator_canvas.pack(side=tk.LEFT, padx=(0, 10))
            
            # 绘制绿色圆圈
            indicator_canvas.create_oval(3, 3, 17, 17, fill='#28a745', outline='#28a745')
            self.bucket_status_indicators[bucket_id] = indicator_canvas
            
            # 料斗标签
            bucket_label = tk.Label(left_frame, text=f"斗{bucket_id}", 
                                  font=self.label_font, bg='#f8f9fa', fg='#333333')
            bucket_label.pack(side=tk.LEFT)
            
            # 右侧重量显示
            weight_label = tk.Label(bucket_frame, text="0.0g", 
                                  font=self.big_data_font, bg='#f8f9fa', fg='#333333')
            weight_label.pack(side=tk.RIGHT, padx=10, pady=5)
            
            self.bucket_weight_labels[bucket_id] = weight_label
    
    def create_production_info_section(self, parent):
        """
        创建生产信息区域
        
        Args:
            parent: 父容器
        """
        # 顶部生产参数显示
        params_frame = tk.Frame(parent, bg='white')
        params_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 物料名称
        material_frame = tk.Frame(params_frame, bg='#e3f2fd', relief='flat', bd=0)
        material_frame.pack(side=tk.LEFT, padx=(0, 20))
        material_frame.configure(width=200, height=80)
        material_frame.pack_propagate(False)
        
        material_label = tk.Label(material_frame, 
                                text=self.production_params.get('material_name', '未知物料'),
                                font=self.big_data_font, bg='#e3f2fd', fg='#1976d2')
        material_label.pack(expand=True)
        
        # 每包重量
        weight_frame = tk.Frame(params_frame, bg='#e8f5e8', relief='flat', bd=0)
        weight_frame.pack(side=tk.LEFT, padx=(0, 20))
        weight_frame.configure(width=150, height=80)
        weight_frame.pack_propagate(False)
        
        weight_label = tk.Label(weight_frame, 
                              text=f"{self.production_params.get('target_weight', 0)}g/包",
                              font=self.big_data_font, bg='#e8f5e8', fg='#388e3c')
        weight_label.pack(expand=True)
        
        # 总包数
        total_frame = tk.Frame(params_frame, bg='#f3e5f5', relief='flat', bd=0)
        total_frame.pack(side=tk.LEFT)
        total_frame.configure(width=100, height=80)
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
        
        # 故障记录区域
        fault_frame = tk.LabelFrame(parent, text="故障记录", font=self.label_font,
                                  bg='white', fg='#333333')
        fault_frame.pack(fill=tk.BOTH, expand=True)
        
        # 故障记录文本框
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
            
            print(f"生产界面已居中显示: {width}x{height}+{x}+{y}")
            
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
            
            # 在后台线程执行PLC操作
            def production_startup_thread():
                try:
                    # 1. 包数清零=0
                    print("步骤1: 发送包数清零=0命令")
                    if not self.modbus_client.write_coil(get_production_address('PackageCountClear'), False):
                        self.root.after(0, lambda: self.add_fault_record("发送包数清零=0命令失败"))
                        return
                    
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
            self.is_paused = False  # ✅ 新增：确保初始状态为非暂停
            self.production_start_time = datetime.now()
            self.monitoring_threads_running = True
            
            # 确保按钮状态正确
            if self.pause_resume_btn:
                self.pause_resume_btn.config(text="⏸ 暂停", bg='#ffc107')
            
            print("开始生产监控...")
            
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
            
            # 启动所有监控线程
            threading.Thread(target=timer_update_thread, daemon=True).start()
            threading.Thread(target=weight_monitoring_thread, daemon=True).start()
            threading.Thread(target=package_monitoring_thread, daemon=True).start()
            
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
            
            # 显示完成消息
            messagebox.showinfo("生产完成", 
                              f"🎉 生产任务已完成！\n\n"
                              f"目标包数: {self.production_params.get('package_quantity', 0)}\n"
                              f"实际包数: {self.current_package_count}\n"
                              f"用时: {self.timer_label.cget('text')}")
            
        except Exception as e:
            print(f"生产完成处理异常: {e}")
    
    def add_fault_record(self, message: str):
        """添加故障记录"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            record = f"[{timestamp}] {message}\n"
            
            self.fault_text.config(state='normal')
            self.fault_text.insert(tk.END, record)
            self.fault_text.see(tk.END)
            self.fault_text.config(state='disabled')
            
        except Exception as e:
            print(f"添加故障记录异常: {e}")
    
    def on_pause_resume_click(self):
        """暂停/启动按钮点击事件"""
        try:
            if not self.is_paused:
                # 当前是运行状态，执行暂停操作
                self._pause_production()
            else:
                # 当前是暂停状态，执行启动操作
                self._resume_production()

        except Exception as e:
            print(f"暂停/启动操作异常: {e}")
            self.add_fault_record(f"暂停/启动操作异常: {str(e)}")

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
                        self.add_fault_record("发送暂停命令失败")
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
                    
            # 启动所有监控线程
            threading.Thread(target=timer_update_thread, daemon=True).start()
            threading.Thread(target=weight_monitoring_thread, daemon=True).start()
            threading.Thread(target=package_monitoring_thread, daemon=True).start()
            
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
                self.monitoring_threads_running = False
                self.is_production_running = False
                
                if self.modbus_client and self.modbus_client.is_connected:
                    self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                
                self.add_fault_record("生产任务已取消")
                
                # 关闭生产界面，回到AI模式界面
                self.on_closing()
            
        except Exception as e:
            print(f"取消生产异常: {e}")
            self.add_fault_record(f"取消操作异常: {str(e)}")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            # 停止所有监控线程
            self.monitoring_threads_running = False
            self.is_production_running = False
            
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