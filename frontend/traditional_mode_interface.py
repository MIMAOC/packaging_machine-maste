"""
传统模式完整界面系统

作者：L
创建日期：2025-08-05
修复日期：2025-08-06
"""
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any

try:
    from traditional_plc_addresses import (
        get_traditional_weight_address,
        get_traditional_monitoring_address, 
        get_traditional_control_address,
        get_traditional_parameter_address,
        get_traditional_global_address,
        get_traditional_system_address,
        get_traditional_disable_address,
        TRADITIONAL_MONITORING_ADDRESSES,
        TRADITIONAL_PARAMETER_ADDRESSES
    )
    from modbus_client import ModbusClient
except ImportError as e:
    pass


class SimpleTianTengInterface:
    def __init__(self, parent=None, main_window=None, modbus_client: Optional[ModbusClient] = None):
        if parent:
            self.root = parent
            self.is_embedded = True
            self.main_window = main_window
        else:
            self.root = tk.Tk()
            self.is_embedded = False
            self.main_window = None
            
        if self.is_embedded:
            self.root.title("六头线性调节秤 V1.8")
            self.root.attributes('-fullscreen', True)
            self.root.state('zoomed')
            self.root.geometry("1920x1080")
            self.root.configure(bg='#ffffff')
            self.root.minsize(1200, 800)
        
        self.current_interface = "menu"
        self.current_bucket_id = 1
        
        self.modbus_client = modbus_client
        
        self.manual_interface = None
        self.calibration_interface = None
        self.parameter_interface = None
        self.system_interface = None
        
        self.refresh_timer = None
        self._external_update_callback = None
        
        self.main_content_frame = None
        self.bucket_widgets = {}
        self.status_labels = {}
        self.weight_labels = {}
        self.parameter_entries = {}
        self.control_buttons = {}
        self.bucket_number_labels = {}
        self.target_weight_entry = None
        
        self.global_started = False
        
        self.bucket_started = {}
        self.bucket_cleaning = {}
        for i in range(1, 7):
            self.bucket_started[i] = False
            self.bucket_cleaning[i] = False
        
        self.logo_image = None

        self.setup_logo_path()
        
        self.setup_fonts()
        self.create_base_layout()
        self.show_menu_interface()

    def setup_logo_path(self):
        import os
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        logo_files = ["tianteng.png", "tianteng.PNG", "LOGO.png", "LOGO.PNG", "logo.png"]
        
        self.logo_path = None
        for logo_file in logo_files:
            logo_path = os.path.join(current_dir, logo_file)
            if os.path.exists(logo_path):
                self.logo_path = logo_path
                break
            
            parent_dir = os.path.dirname(current_dir)
            logo_path = os.path.join(parent_dir, logo_file)
            if os.path.exists(logo_path):
                self.logo_path = logo_path
                break
        
    def setup_fonts(self):
        self.title_font = font.Font(family="Microsoft YaHei", size=48, weight="normal")
        self.version_font = font.Font(family="Microsoft YaHei", size=42, weight="normal")
        self.menu_font = font.Font(family="Microsoft YaHei", size=38, weight="normal")
        self.company_font = font.Font(family="Microsoft YaHei", size=20, weight="normal")
        self.logo_font = font.Font(family="Arial", size=22, weight="bold")
        
        self.bucket_number_font = font.Font(family="Arial", size=72, weight="bold")
        self.weight_font = font.Font(family="Arial", size=42, weight="bold")
        self.status_font = font.Font(family="Microsoft YaHei", size=16, weight="normal")
        self.button_font = font.Font(family="Microsoft YaHei", size=18, weight="normal")
        self.target_font = font.Font(family="Arial", size=28, weight="bold")
        
        self.detail_weight_font = font.Font(family="Arial", size=84, weight="bold")
        self.param_label_font = font.Font(family="Microsoft YaHei", size=24, weight="normal")
        self.param_value_font = font.Font(family="Arial", size=20, weight="bold")
        self.bucket_select_font = font.Font(family="Arial", size=18, weight="bold")
        
    def create_base_layout(self):
        self.main_container = tk.Frame(self.root, bg='#ffffff')
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.main_content_frame = tk.Frame(self.main_container, bg='#ffffff')
        self.main_content_frame.pack(fill=tk.BOTH, expand=True)
        
    def clear_main_content(self):
        if self.main_content_frame:
            for widget in self.main_content_frame.winfo_children():
                widget.destroy()
        
        self.stop_data_refresh()
        
        self.bucket_widgets.clear()
        self.status_labels.clear()
        self.weight_labels.clear()
        self.parameter_entries.clear()
        self.control_buttons.clear()
        self.target_weight_entry = None
        self.detail_target_weight_entry = None

    def show_menu_interface(self):
        self.clear_main_content()
        self.current_interface = "menu"
        self.create_menu_interface()
    
    def show_monitoring_interface(self):
        self.clear_main_content()
        self.current_interface = "monitoring"
        self.create_monitoring_interface()
        self.start_data_refresh()
    
    def show_manual_interface(self):
        if self.manual_interface is None:
            try:
                from manual_mode_interface import ManualModeInterface
                self.manual_interface = ManualModeInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"手动界面模块加载失败: {e}\n请确保manual_mode_interface.py文件存在")
                return
        
        self.clear_main_content()
        self.current_interface = "manual"
        self.manual_interface.show_interface()

    def show_calibration_interface(self):
        if self.calibration_interface is None:
            try:
                from weight_calibration_interface import WeightCalibrationInterface
                self.calibration_interface = WeightCalibrationInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"重量校准界面模块加载失败: {e}\n请确保weight_calibration_interface.py文件存在")
                return
        self.clear_main_content()
        self.current_interface = "calibration"
        self.calibration_interface.show_interface()
            
    def show_parameter_interface(self):
        if self.parameter_interface is None:
            try:
                from parameter_setting_interface import ParameterSettingInterface
                self.parameter_interface = ParameterSettingInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"参数设置界面模块加载失败: {e}\n请确保parameter_setting_interface.py文件存在")
                return
        
        self.clear_main_content()
        self.current_interface = "parameter"
        self.parameter_interface.show_interface()      

    def show_system_interface(self):
        if self.system_interface is None:
            try:
                from system_setting_interface import SystemSettingInterface
                self.system_interface = SystemSettingInterface(self.modbus_client, self)
            except ImportError as e:
                messagebox.showerror("错误", f"系统设置界面模块加载失败: {e}\n请确保system_setting_interface.py文件存在")
                return
        
        self.clear_main_content()
        self.current_interface = "system"
        self.system_interface.show_interface()
    
    def show_bucket_detail_interface(self, bucket_id: int):
        self.clear_main_content()
        self.current_interface = "bucket_detail"
        self.current_bucket_id = bucket_id
        self.create_bucket_detail_interface(bucket_id)
        self.start_data_refresh()

    def create_menu_interface(self):
        top_spacer = tk.Frame(self.main_content_frame, bg='#ffffff', height=20)
        top_spacer.pack(side=tk.TOP, fill=tk.X)
        
        main_content = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        left_frame = tk.Frame(main_content, bg='#ffffff', width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(40, 20))
        left_frame.pack_propagate(False)
        
        right_frame = tk.Frame(main_content, bg='#ffffff')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 20))
        
        self.create_menu_area(left_frame)
        
        self.create_title_area(right_frame)
        
        company_frame = tk.Frame(self.main_content_frame, bg='#ffffff')
        company_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 25))
        
        company_label = tk.Label(company_frame, 
                               text="温州天腾机械有限公司 • 13395779890",
                               font=self.company_font, bg='#ffffff', fg='#666666')
        company_label.pack(side=tk.RIGHT, padx=150)
        
    def create_menu_area(self, parent):
        menu_items = [
            "传统模式",
            "手动画面", 
            "参数设置",
            "重量校准",
            "系统设置"
        ]
        menu_items.append("返回主菜单")
        
        top_spacer = tk.Frame(parent, bg='#ffffff', height=50)
        top_spacer.pack(side=tk.TOP)
        
        for i, text in enumerate(menu_items):
            menu_item_frame = tk.Frame(parent, bg='#ffffff')
            menu_item_frame.pack(side=tk.TOP, fill=tk.X, pady=15)
            
            triangle = tk.Label(menu_item_frame, text="▶", 
                              font=("Arial", 12), 
                              bg='#ffffff', fg='#999999')
            triangle.pack(side=tk.LEFT, padx=(5, 0))
            
            menu_label = tk.Label(menu_item_frame, text=text, 
                                font=self.menu_font,
                                bg='#ffffff', fg='#333333',
                                cursor='hand2')
            menu_label.pack(side=tk.LEFT, padx=10)
            
            menu_label.bind("<Button-1>", lambda e, t=text: self.menu_click(t))
            menu_label.bind("<Enter>", lambda e, l=menu_label: l.configure(fg='#1a365d'))
            menu_label.bind("<Leave>", lambda e, l=menu_label: l.configure(fg='#333333'))
    
    def create_title_area(self, parent):
        content_frame = tk.Frame(parent, bg='#ffffff')
        content_frame.pack(expand=True)
        
        self.logo_label = tk.Label(content_frame, text="TiAN TENG", 
                                font=self.logo_font, bg='#ffffff', fg='#1a365d')
        self.logo_label.pack(pady=(0, 30))

        self.load_logo_image()
        
        title_frame = tk.Frame(content_frame, bg='#ffffff')
        title_frame.pack()
        
        main_title = tk.Label(title_frame, text="六头线性调节秤", 
                             font=self.title_font, 
                             bg='#ffffff', fg='#2d3748')
        main_title.pack()
        
        version_label = tk.Label(title_frame, text="V1.8", 
                                font=self.version_font, 
                                bg='#ffffff', fg='#2d3748')
        version_label.pack(pady=(10, 0))

    def create_monitoring_interface(self):
        main_container = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        buckets_frame = tk.Frame(main_container, bg='#ffffff')
        buckets_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        control_frame = tk.Frame(main_container, bg='#ffffff', width=300)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        control_frame.pack_propagate(False)
        
        self.create_buckets_area(buckets_frame)
        
        self.create_control_panel(control_frame)
        
    def create_buckets_area(self, parent):
        row1_frame = tk.Frame(parent, bg='#ffffff')
        row1_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 8))
        
        bucket1_widget = self.create_bucket_widget(row1_frame, 1)
        bucket1_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.bucket_widgets[1] = bucket1_widget
        
        bucket2_widget = self.create_bucket_widget(row1_frame, 2)
        bucket2_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.bucket_widgets[2] = bucket2_widget
        
        row2_frame = tk.Frame(parent, bg='#ffffff')
        row2_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=8)
        
        bucket3_widget = self.create_bucket_widget(row2_frame, 3)
        bucket3_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.bucket_widgets[3] = bucket3_widget
        
        bucket4_widget = self.create_bucket_widget(row2_frame, 4)
        bucket4_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.bucket_widgets[4] = bucket4_widget
        
        row3_frame = tk.Frame(parent, bg='#ffffff')
        row3_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(8, 0))
        
        bucket5_widget = self.create_bucket_widget(row3_frame, 5)
        bucket5_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.bucket_widgets[5] = bucket5_widget
        
        bucket6_widget = self.create_bucket_widget(row3_frame, 6)
        bucket6_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.bucket_widgets[6] = bucket6_widget
    
    def create_bucket_widget(self, parent, bucket_id: int):
        bucket_frame = tk.Frame(parent, bg='#d5d5d5', relief='raised', bd=2, height=230)
        bucket_frame.pack_propagate(False)
        
        content_frame = tk.Frame(bucket_frame, bg='#d5d5d5')
        content_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(5, 0))
        
        number_label = tk.Label(content_frame, text=str(bucket_id),
                               font=('Arial', 110, 'bold'), bg='#d5d5d5', fg='#333333')
        number_label.pack(side=tk.LEFT, padx=(15, 40), anchor='n')
        self.bucket_number_labels[bucket_id] = number_label
        
        weight_label = tk.Label(content_frame, text="-0000.0",
                               font=('Arial', 68, 'bold'), bg='#d5d5d5', fg='#333333')
        weight_label.pack(side=tk.RIGHT, padx=(0, 15), pady=(20, 0), anchor='n')
        self.weight_labels[bucket_id] = weight_label
        
        status_frame = tk.Frame(bucket_frame, bg='#d5d5d5')
        status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(20, 0))

        status_types = ['CoarseAdd', 'FineAdd', 'Jog', 'TargetReached']
        status_texts = ['快加', '慢加', '点动', '到量']
        
        if bucket_id not in self.status_labels:
            self.status_labels[bucket_id] = {}
        
        for i, (status_type, status_text) in enumerate(zip(status_types, status_texts)):
            status_label = tk.Label(status_frame, text=status_text,
                                   font=('Microsoft YaHei', 13), bg='#bdbdbd', fg='#333333',
                                   relief='solid', bd=1, padx=10, pady=5, width=6)
            
            status_label.pack(side=tk.LEFT, expand=True, padx=4)
            self.status_labels[bucket_id][status_type] = status_label
        
        def on_bucket_click(event):
            self.show_bucket_detail_interface(bucket_id)
        
        bucket_frame.bind("<Button-1>", on_bucket_click)
        number_label.bind("<Button-1>", on_bucket_click)
        weight_label.bind("<Button-1>", on_bucket_click)
        
        bucket_frame.configure(cursor='hand2')
        number_label.configure(cursor='hand2')
        weight_label.configure(cursor='hand2')
        
        return bucket_frame
    
    def create_control_panel(self, parent):
        target_frame = tk.Frame(parent, bg='#ffffff')
        target_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 30))
        
        tk.Label(target_frame, text="目标重量",
                font=('Microsoft YaHei', 20, 'bold'), bg='#ffffff', fg='#333333').pack()
        
        self.target_weight_entry = tk.Entry(target_frame, font=('Arial', 32, 'bold'), justify='center',
                               relief='solid', bd=2, width=8)
        self.target_weight_entry.pack(pady=(8, 0))
        self.target_weight_entry.insert(0, "0000.0")
        
        self.target_weight_entry.bind('<Button-1>', lambda e: self.target_weight_entry.focus_force(), add=True)
        
        self.target_weight_entry.bind('<FocusOut>', self.save_target_weight)
        self.target_weight_entry.bind('<Return>', self.save_target_weight)
        
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.pack(side=tk.TOP, fill=tk.X)
        
        button_configs = [
            ("总放料", "#4a90e2", "GlobalDischarge"),
            ("总清零", "#4a90e2", "GlobalClear"),
            ("总启动", "#4a90e2", "GlobalStart"),
            ("主页", "#e0e0e0", "Home")
        ]
        
        for i, (text, color, action) in enumerate(button_configs):
            if action == "GlobalStart":
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
        
        self.load_target_weight()

    def create_bucket_detail_interface(self, bucket_id: int):
        main_container = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        left_container = tk.Frame(main_container, bg='#ffffff')
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(7, 10))
        
        right_container = tk.Frame(main_container, bg='#ffffff', width=250)
        right_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 7))
        right_container.pack_propagate(False)
        
        self.create_detail_top_area(left_container, bucket_id)
        self.create_detail_main_area(left_container, bucket_id)
        self.create_detail_bottom_area(left_container, bucket_id)
        
        self.create_detail_control_panel_fixed(right_container)
        
        self.load_bucket_parameters(bucket_id)
        self.load_detail_target_weight(bucket_id)
        
    def create_detail_top_area(self, parent, bucket_id: int):
        top_frame = tk.Frame(parent, bg='#ffffff', height=180)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        top_frame.pack_propagate(False)
        
        content_frame = tk.Frame(top_frame, bg='#ffffff')
        content_frame.pack(expand=True)
        
        weight_label = tk.Label(content_frame, text="-0000.0",
                               font=('Arial', 100, 'bold'), bg='#ffffff', fg='#333333')
        weight_label.pack(pady=(5, 15))
        self.weight_labels[f'detail_{bucket_id}'] = weight_label
        
        status_frame = tk.Frame(content_frame, bg='#ffffff')
        status_frame.pack(pady=(0, 5))
        
        status_types = ['CoarseAdd', 'FineAdd', 'Jog', 'TargetReached']
        status_texts = ['快加', '慢加', '点动', '到量']
        
        if f'detail_{bucket_id}' not in self.status_labels:
            self.status_labels[f'detail_{bucket_id}'] = {}
        
        for i, (status_type, status_text) in enumerate(zip(status_types, status_texts)):
            status_label = tk.Label(status_frame, text=status_text,
                                   font=('Microsoft YaHei', 17), bg='#cccccc', fg='#333333',
                                   relief='solid', bd=1, padx=14, pady=8, width=7)
            status_label.pack(side=tk.LEFT, padx=8)
            self.status_labels[f'detail_{bucket_id}'][status_type] = status_label
    
    def create_detail_main_area(self, parent, bucket_id: int):
        main_frame = tk.Frame(parent, bg='#ffffff', height=450)
        main_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        main_frame.pack_propagate(False)
        
        params_container = tk.Frame(main_frame, bg='#ffffff')
        params_container.pack(expand=True)
        
        param_configs = [
            ("快加料速度", "CoarseSpeed", 0),
            ("慢加料速度", "FineSpeed", 0),
            ("快加料提前量", "CoarseAdvance", 1),
            ("慢加料提前量", "FineAdvance", 1)
        ]
        
        if bucket_id not in self.parameter_entries:
            self.parameter_entries[bucket_id] = {}
        
        for i, (param_text, param_type, decimal_places) in enumerate(param_configs):
            param_row = tk.Frame(params_container, bg='#ffffff')
            param_row.pack(side=tk.TOP, pady=20)
            
            param_label = tk.Label(param_row, text=param_text,
                      font=('Microsoft YaHei', 24, 'normal'), bg='#ffffff', fg='#333333',
                      width=8, anchor='e')
            param_label.pack(side=tk.LEFT, padx=(0, 40))
            
            param_entry = tk.Entry(param_row, font=('Arial', 28, 'bold'), justify='center',
                                  relief='solid', bd=2, width=15, highlightthickness=2)
            param_entry.pack(side=tk.LEFT)
            
            param_entry.bind('<Button-1>', lambda e: param_entry.focus_force(), add=True)
            
            param_entry.bind('<FocusOut>', 
                           lambda e, bid=bucket_id, pt=param_type: self.save_parameter(bid, pt, e.widget.get()))
            param_entry.bind('<Return>', 
                           lambda e, bid=bucket_id, pt=param_type: self.save_parameter(bid, pt, e.widget.get()))
            
            self.parameter_entries[bucket_id][param_type] = param_entry
    
    def create_detail_control_panel_fixed(self, parent):
        weight_frame = tk.Frame(parent, bg='#ffffff')
        weight_frame.pack(side=tk.TOP, fill=tk.X, pady=(20, 30))
        
        tk.Label(weight_frame, text="重量",
                font=('Microsoft YaHei', 24, 'bold'), bg='#ffffff', fg='#333333').pack()
        
        weight_entry = tk.Entry(weight_frame, font=('Arial', 36, 'bold'), justify='center',
                       relief='solid', bd=2, width=8)
        weight_entry.pack(pady=(10, 0))
        self.detail_target_weight_entry = weight_entry

        weight_entry.bind('<FocusOut>', self.save_detail_target_weight)
        weight_entry.bind('<Return>', self.save_detail_target_weight)
        
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.pack(side=tk.TOP, fill=tk.X, pady=20)
        
        button_configs = [
            ("放料", "#4a90e2", "Discharge"),
            ("清零", "#4a90e2", "Clear"),
            ("启动", "#4a90e2", "Start"),
            ("返回", "#e0e0e0", "Back")
        ]
        
        for i, (text, color, action) in enumerate(button_configs):
            if action == "Start":
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
        
        spacer_frame = tk.Frame(parent, bg='#ffffff')
        spacer_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    def create_detail_bottom_area(self, parent, current_bucket_id: int):
        bottom_frame = tk.Frame(parent, bg='#ffffff', height=75)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        bottom_frame.pack_propagate(False)
        
        buckets_container = tk.Frame(bottom_frame, bg='#ffffff')
        buckets_container.pack(expand=True)
        
        for bucket_id in range(1, 7):
            if bucket_id == current_bucket_id:
                bg_color = '#00aa00'
                fg_color = 'white'
            else:
                bg_color = '#4a90e2'
                fg_color = 'white'
            
            btn = tk.Button(buckets_container, text=str(bucket_id),
                           font=('Arial', 20, 'bold'), bg=bg_color, fg=fg_color,
                           width=4, height=2, relief='solid', bd=2,
                           command=lambda bid=bucket_id: self.switch_bucket(bid))
            btn.pack(side=tk.LEFT, padx=15)
    
    def save_target_weight(self, event=None):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存目标重量")
            return
        
        try:
            target_weight_str = self.target_weight_entry.get()
            target_weight = float(target_weight_str)
            
            plc_value = int(target_weight * 10)
            
            address = get_traditional_system_address('GlobalTargetWeight')
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if not success:
                messagebox.showerror("错误", "保存全局目标重量失败")
                
        except ValueError:
            messagebox.showerror("错误", f"目标重量格式错误: {target_weight_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存目标重量异常: {e}")
    
    def load_target_weight(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            address = get_traditional_system_address('GlobalTargetWeight')
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data:
                target_weight = data[0] / 10.0
                self.target_weight_entry.delete(0, tk.END)
                self.target_weight_entry.insert(0, f"{target_weight:.1f}")
                
        except Exception as e:
            pass

    def load_bucket_parameters(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            param_types = ['CoarseSpeed', 'FineSpeed', 'CoarseAdvance', 'FineAdvance']
            
            for param_type in param_types:
                try:
                    address = get_traditional_parameter_address(bucket_id, param_type)
                    data = self.modbus_client.read_holding_registers(address, 1)
                    
                    if data and bucket_id in self.parameter_entries:
                        if param_type in self.parameter_entries[bucket_id]:
                            entry = self.parameter_entries[bucket_id][param_type]
                            
                            if param_type in ['CoarseAdvance', 'FineAdvance']:
                                value = f"{data[0] / 10:.1f}"
                            else:
                                value = str(data[0])
                            
                            entry.delete(0, tk.END)
                            entry.insert(0, value)
                            
                except Exception as e:
                    pass
                    
        except Exception as e:
            pass
    
    def save_parameter(self, bucket_id: int, param_type: str, value_str: str):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存参数")
            return
        
        try:
            value = float(value_str)
            
            if param_type in ['CoarseAdvance', 'FineAdvance']:
                plc_value = int(value * 10)
            else:
                plc_value = int(value)
            
            address = get_traditional_parameter_address(bucket_id, param_type)
            
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if not success:
                messagebox.showerror("错误", f"保存参数失败: {param_type}")
                
        except ValueError:
            messagebox.showerror("错误", f"参数格式错误: {value_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存参数异常: {e}")

    def load_detail_target_weight(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            address = get_traditional_parameter_address(bucket_id, 'TargetWeight')
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data and hasattr(self, 'detail_target_weight_entry') and self.detail_target_weight_entry:
                target_weight = data[0] / 10.0
                self.detail_target_weight_entry.delete(0, tk.END)
                self.detail_target_weight_entry.insert(0, f"{target_weight:.1f}")
            else:
                pass
                
        except Exception as e:
            if hasattr(self, 'detail_target_weight_entry') and self.detail_target_weight_entry:
                self.detail_target_weight_entry.delete(0, tk.END)
                self.detail_target_weight_entry.insert(0, "0000.0")

    def save_detail_target_weight(self, event=None):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存目标重量")
            return
        
        try:
            target_weight_str = self.detail_target_weight_entry.get().strip()
            target_weight = float(target_weight_str)
            
            if target_weight < 0:
                messagebox.showerror("错误", "目标重量不能为负数")
                return
            
            plc_value = int(target_weight * 10)
            
            address = get_traditional_parameter_address(self.current_bucket_id, 'TargetWeight')
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                if hasattr(self, 'target_weight_entry') and self.target_weight_entry:
                    self.target_weight_entry.delete(0, tk.END)
                    self.target_weight_entry.insert(0, f"{target_weight:.1f}")
            else:
                messagebox.showerror("错误", f"保存料斗{self.current_bucket_id}目标重量失败")
                
        except ValueError:
            messagebox.showerror("错误", f"目标重量格式错误: {target_weight_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存目标重量异常: {e}")

    def menu_click(self, text):
        
        if text == "传统模式":
            self.show_monitoring_interface()
        elif text == "手动画面":
            self.show_manual_interface()
        elif text == "参数设置":
            self.show_parameter_interface()
        elif text == "重量校准":
            self.show_calibration_interface()
        elif text == "系统设置":
            self.show_system_interface()
        elif text == "返回主菜单":
            if self.is_embedded:
                self.return_to_main_menu()
            else:
                self.show_menu_interface()

    def return_to_main_menu(self):
        if self.is_embedded and self.main_window:
            try:
                self.root.destroy()
                
                self.main_window.show_main_window()
                
                if hasattr(self.main_window, 'cleanup_traditional_interface'):
                    self.main_window.cleanup_traditional_interface()
                    
            except Exception as e:
                pass            
    
    def on_control_button_click(self, action: str):
        if action == "Home":
            self.show_menu_interface()
        elif action == "GlobalDischarge":
            self.send_global_pulse_command("GlobalDischarge")
        elif action == "GlobalClear":
            self.send_global_pulse_command("GlobalClear")
    
    def on_detail_control_click(self, action: str):
        if action == "Back":
            self.show_monitoring_interface()
        elif action == "Discharge":
            self.send_bucket_pulse_command(self.current_bucket_id, "Discharge")
        elif action == "Clear":
            self.send_bucket_pulse_command(self.current_bucket_id, "Clear")
    
    def toggle_global_start(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        if 'global_start' in self.control_buttons:
            btn = self.control_buttons['global_start']
            
            try:
                if self.global_started:
                    success = self.execute_global_stop_with_mutex()
                    if success:
                        btn.configure(text="总启动", bg="#4a90e2")
                        self.global_started = False
                    else:
                        messagebox.showerror("错误", "全局停止操作失败")
                else:
                    success = self.execute_global_start_with_mutex()
                    if success:
                        btn.configure(text="总停止", bg="#ff0000")
                        self.global_started = True
                    else:
                        messagebox.showerror("错误", "全局启动操作失败")
                        
            except Exception as e:
                messagebox.showerror("错误", f"全局启动/停止操作异常: {e}")
    
    def toggle_bucket_start(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
            
        btn_key = f'bucket_{self.current_bucket_id}_start'
        if btn_key in self.control_buttons:
            btn = self.control_buttons[btn_key]
            
            try:
                current_text = btn.cget('text')
                if current_text == "启动":
                    success = self.execute_bucket_start(self.current_bucket_id)
                    if success:
                        btn.configure(text="停止", bg="#ff0000")
                        self.bucket_started[self.current_bucket_id] = True
                    else:
                        messagebox.showerror("错误", f"料斗{self.current_bucket_id}启动操作失败")
                else:
                    success = self.execute_bucket_stop(self.current_bucket_id)
                    if success:
                        btn.configure(text="启动", bg="#4a90e2")
                        self.bucket_started[self.current_bucket_id] = False
                    else:
                        messagebox.showerror("错误", f"料斗{self.current_bucket_id}停止操作失败")
                        
            except Exception as e:
                messagebox.showerror("错误", f"料斗{self.current_bucket_id}启动/停止操作异常: {e}")
    
    def switch_bucket(self, bucket_id: int):
        if bucket_id != self.current_bucket_id:
            self.show_bucket_detail_interface(bucket_id)

    def execute_global_start_with_mutex(self) -> bool:
        try:
            global_stop_addr = get_traditional_global_address('GlobalStop')
            success = self.modbus_client.write_coil(global_stop_addr, False)
            if not success:
                return False
            
            time.sleep(0.05)
            
            global_start_addr = get_traditional_global_address('GlobalStart')
            success = self.modbus_client.write_coil(global_start_addr, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def execute_global_stop_with_mutex(self) -> bool:
        try:
            global_start_addr = get_traditional_global_address('GlobalStart')
            success = self.modbus_client.write_coil(global_start_addr, False)
            if not success:
                return False
            
            time.sleep(0.05)
            
            global_stop_addr = get_traditional_global_address('GlobalStop')
            success = self.modbus_client.write_coil(global_stop_addr, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def execute_bucket_start(self, bucket_id: int) -> bool:
        try:
            bucket_start_addr = get_traditional_control_address(bucket_id, 'Start')
            success = self.modbus_client.write_coil(bucket_start_addr, True)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def execute_bucket_stop(self, bucket_id: int) -> bool:
        try:
            bucket_start_addr = get_traditional_control_address(bucket_id, 'Start')
            success = self.modbus_client.write_coil(bucket_start_addr, False)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            return False

    def send_global_pulse_command(self, command: str):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return False
        
        try:
            address = get_traditional_global_address(command)
            success = self.send_pulse_command(address)
            
            if success:
                return True
            else:
                messagebox.showerror("错误", f"全局命令{command}发送失败")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"发送全局命令异常: {e}")
            return False
    
    def send_bucket_pulse_command(self, bucket_id: int, command: str):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return False
        
        try:
            pulse_commands = ['Clear', 'Discharge', 'Jog']
            
            if command not in pulse_commands:
                return False
            
            address = get_traditional_control_address(bucket_id, command)
            
            if command == "Discharge":
                pulse_duration = 1500
            else:
                pulse_duration = 100
            
            success = self.send_pulse_command(address, pulse_duration)
            
            if success:
                return True
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}命令{command}发送失败")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"发送料斗命令异常: {e}")
            return False
    
    def toggle_bucket_clean(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            clean_addr = get_traditional_control_address(bucket_id, 'Clean')
            
            current_cleaning = self.bucket_cleaning.get(bucket_id, False)
            new_state = not current_cleaning
            
            success = self.modbus_client.write_coil(clean_addr, new_state)
            
            if success:
                self.bucket_cleaning[bucket_id] = new_state
                return True
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}清料操作失败")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}清料操作异常: {e}")
            return False
    
    def toggle_bucket_disable(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            disable_addr = get_traditional_disable_address(bucket_id)
            
            current_state_data = self.modbus_client.read_coils(disable_addr, 1)
            if not current_state_data:
                messagebox.showerror("错误", f"读取料斗{bucket_id}禁用状态失败")
                return False
            
            current_disabled = current_state_data[0]
            new_state = not current_disabled
            
            success = self.modbus_client.write_coil(disable_addr, new_state)
            
            if success:
                return True
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}禁用状态切换失败")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}禁用状态切换异常: {e}")
            return False
    
    def send_pulse_command(self, address: int, pulse_duration: int = 100):
        try:
            success1 = self.modbus_client.write_coil(address, True)
            
            if success1:
                self.root.after(pulse_duration, lambda: self.modbus_client.write_coil(address, False))
                return True
            else:
                return False
        except Exception as e:
            return False

    def start_data_refresh(self):
        if self.modbus_client and self.modbus_client.is_connected:
            self.update_realtime_data()
    
    def stop_data_refresh(self):
        if self.refresh_timer:
            self.root.after_cancel(self.refresh_timer)
            self.refresh_timer = None
    
    def update_realtime_data(self):
        try:
            if self.current_interface == "monitoring":
                self.update_monitoring_data()
            elif self.current_interface == "bucket_detail":
                self.update_detail_data()
            elif self.current_interface in ["manual", "calibration"] and hasattr(self, '_external_update_callback'):
                if self._external_update_callback:
                    self._external_update_callback()
                
        except Exception as e:
            pass
        finally:
            if self.current_interface in ["monitoring", "bucket_detail", "manual", "calibration"]:
                self.refresh_timer = self.root.after(100, self.update_realtime_data)
    
    def update_monitoring_data(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            for bucket_id in range(1, 7):
                if bucket_id in self.weight_labels:
                    try:
                        weight_addr = get_traditional_weight_address(bucket_id)
                        weight_data = self.modbus_client.read_holding_registers(weight_addr, 1)
                        if weight_data:
                            raw_value = weight_data[0]
                            if raw_value > 32767:
                                signed_value = raw_value - 65536
                            else:
                                signed_value = raw_value
                            
                            weight_value = signed_value / 10.0
                            weight_text = f"{weight_value:.1f}"
                            self.weight_labels[bucket_id].configure(text=weight_text)
                    except Exception as e:
                        pass
                    
                    try:
                        disable_addr = get_traditional_disable_address(bucket_id)
                        disable_data = self.modbus_client.read_coils(disable_addr, 1)
                        if disable_data and bucket_id in self.bucket_number_labels:
                            is_disabled = disable_data[0]
                            number_label = self.bucket_number_labels[bucket_id]
                            if is_disabled:
                                number_label.configure(fg='#ff0000')
                            else:
                                number_label.configure(fg='#333333')
                    except Exception as e:
                        pass
            
            self.update_status_indicators()
            
        except Exception as e:
            pass
    
    def update_detail_data(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            bucket_id = self.current_bucket_id
            
            try:
                weight_addr = get_traditional_weight_address(bucket_id)
                weight_data = self.modbus_client.read_holding_registers(weight_addr, 1)
                if weight_data:
                    raw_value = weight_data[0]
                    if raw_value > 32767:
                        signed_value = raw_value - 65536
                    else:
                        signed_value = raw_value
                    
                    weight_value = signed_value / 10.0
                    weight_text = f"{weight_value:.1f}"
                    detail_key = f'detail_{bucket_id}'
                    if detail_key in self.weight_labels:
                        self.weight_labels[detail_key].configure(text=weight_text)
            except Exception as e:
                pass
            
            self.update_status_indicators_detail(bucket_id)
            
        except Exception as e:
            pass
    
    def update_status_indicators(self):
        try:
            for bucket_id in range(1, 7):
                if bucket_id in self.status_labels:
                    status_data = {}
                    
                    try:
                        target_addr = get_traditional_monitoring_address(bucket_id, 'TargetReached')
                        target_data = self.modbus_client.read_coils(target_addr, 1)
                        if target_data:
                            status_data['TargetReached'] = target_data[0]
                        
                        coarse_addr = get_traditional_monitoring_address(bucket_id, 'CoarseAdd')
                        coarse_data = self.modbus_client.read_coils(coarse_addr, 1)
                        if coarse_data:
                            status_data['CoarseAdd'] = coarse_data[0]
                        
                        fine_addr = get_traditional_monitoring_address(bucket_id, 'FineAdd')
                        fine_data = self.modbus_client.read_coils(fine_addr, 1)
                        if fine_data:
                            status_data['FineAdd'] = fine_data[0]
                        
                        jog_addr = get_traditional_monitoring_address(bucket_id, 'Jog')
                        jog_data = self.modbus_client.read_coils(jog_addr, 1)
                        if jog_data:
                            status_data['Jog'] = jog_data[0]
                        
                        for status_type, is_active in status_data.items():
                            if status_type in self.status_labels[bucket_id]:
                                label = self.status_labels[bucket_id][status_type]
                                if is_active:
                                    label.configure(bg='#00aa00', fg='white')
                                else:
                                    label.configure(bg='#cccccc', fg='#333333')
                                    
                    except Exception as e:
                        pass
                        
        except Exception as e:
            pass
    
    def update_status_indicators_detail(self, bucket_id: int):
        detail_key = f'detail_{bucket_id}'
        if detail_key not in self.status_labels:
            return
        
        try:
            status_data = {}
            
            try:
                target_addr = get_traditional_monitoring_address(bucket_id, 'TargetReached')
                target_data = self.modbus_client.read_coils(target_addr, 1)
                if target_data:
                    status_data['TargetReached'] = target_data[0]
                
                coarse_addr = get_traditional_monitoring_address(bucket_id, 'CoarseAdd')
                coarse_data = self.modbus_client.read_coils(coarse_addr, 1)
                if coarse_data:
                    status_data['CoarseAdd'] = coarse_data[0]
                
                fine_addr = get_traditional_monitoring_address(bucket_id, 'FineAdd')
                fine_data = self.modbus_client.read_coils(fine_addr, 1)
                if fine_data:
                    status_data['FineAdd'] = fine_data[0]
                
                jog_addr = get_traditional_monitoring_address(bucket_id, 'Jog')
                jog_data = self.modbus_client.read_coils(jog_addr, 1)
                if jog_data:
                    status_data['Jog'] = jog_data[0]
                
                for status_type, is_active in status_data.items():
                    if status_type in self.status_labels[detail_key]:
                        label = self.status_labels[detail_key][status_type]
                        if is_active:
                            label.configure(bg='#00aa00', fg='white')
                        else:
                            label.configure(bg='#cccccc', fg='#333333')
                            
            except Exception as e:
                pass
                
        except Exception as e:
            pass

    def get_shared_modbus_client(self):
        return self.modbus_client
    
    def get_main_root(self):
        return self.root
    
    def get_main_content_frame(self):
        return self.main_content_frame
    
    def shared_clear_main_content(self):
        self.clear_main_content()
    
    def shared_start_data_refresh(self, update_callback):
        if self.modbus_client and self.modbus_client.is_connected:
            self._external_update_callback = update_callback
            self.update_realtime_data()
    
    def shared_stop_data_refresh(self):
        self.stop_data_refresh()
        self._external_update_callback = None
    
    def shared_toggle_bucket_disable(self, bucket_id: int):
        return self.toggle_bucket_disable(bucket_id)
    
    def shared_toggle_bucket_clean(self, bucket_id: int):
        return self.toggle_bucket_clean(bucket_id)
    
    def shared_send_pulse_command(self, address: int, pulse_duration: int = 100):
        return self.send_pulse_command(address, pulse_duration)
    
    def shared_send_bucket_pulse_command(self, bucket_id: int, command: str):
        return self.send_bucket_pulse_command(bucket_id, command)
    
    def shared_send_global_pulse_command(self, command: str):
        return self.send_global_pulse_command(command)
    
    def cleanup_manual_interface(self):
        if self.manual_interface:
            try:
                if hasattr(self.manual_interface, 'cleanup'):
                    self.manual_interface.cleanup()
            except Exception as e:
                pass
            self.manual_interface = None

    def cleanup_calibration_interface(self):
        if self.calibration_interface:
            try:
                if hasattr(self.calibration_interface, 'cleanup'):
                    self.calibration_interface.cleanup()
            except Exception as e:
                pass
            self.calibration_interface = None

    def cleanup_parameter_interface(self):
        if self.parameter_interface:
            try:
                if hasattr(self.parameter_interface, 'cleanup'):
                    self.parameter_interface.cleanup()
            except Exception as e:
                pass
            self.parameter_interface = None

    def cleanup_system_interface(self):
        if self.system_interface:
            try:
                if hasattr(self.system_interface, 'cleanup'):
                    self.system_interface.cleanup()
            except Exception as e:
                pass
            self.system_interface = None     

    def set_modbus_client(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client

    def load_logo_image(self):
        if not self.logo_path:
            return
        
        try:
            original_image = tk.PhotoImage(file=self.logo_path)
            
            original_width = original_image.width()
            original_height = original_image.height()
            
            target_width = 450
            if original_width > target_width:
                scale_factor = original_width // target_width
                scale_factor = max(1, scale_factor)
                
                self.logo_image = original_image.subsample(scale_factor)
            else:
                self.logo_image = original_image
            
            if hasattr(self, 'logo_label') and self.logo_label:
                self.logo_label.configure(image=self.logo_image, text='')
                self.logo_label.image = self.logo_image
            
        except Exception as e:
            pass

    def cleanup(self):
        try:
            self.stop_data_refresh()
            
            self.cleanup_manual_interface()
            self.cleanup_calibration_interface()
            self.cleanup_parameter_interface()
            self.cleanup_system_interface()
            
            if self.is_embedded:
                self.clear_main_content()
                
        except Exception as e:
            pass
    
    def run(self):
        if not self.is_embedded:
            self.root.mainloop()
        else:
            self.show_menu_interface()
    
    def __del__(self):
        self.stop_data_refresh()
        self.cleanup_manual_interface()
        self.cleanup_calibration_interface()


if __name__ == "__main__":
    import os
    
    app = SimpleTianTengInterface()
    
    app.run()