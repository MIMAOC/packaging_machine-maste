"""
AI模式生产界面

作者：C
创建日期：2025-07-25
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from plc_addresses import BUCKET_PRODUCTION_DISABLE_ADDRESSES, get_all_bucket_target_reached_addresses

try:
    from plc_addresses import BUCKET_MONITORING_ADDRESSES, GLOBAL_CONTROL_ADDRESSES, get_production_address
    from modbus_client import ModbusClient
    PLC_AVAILABLE = True
except ImportError:
    PLC_AVAILABLE = False

try:
    from database.material_dao import MaterialDAO, Material
    MATERIAL_DAO_AVAILABLE = True
except ImportError:
    MATERIAL_DAO_AVAILABLE = False
    
try:
    from database.production_detail_dao import ProductionDetailDAO, ProductionDetail
    PRODUCTION_DETAIL_DAO_AVAILABLE = True
except ImportError:
    PRODUCTION_DETAIL_DAO_AVAILABLE = False

try:
    from database.production_record_dao import ProductionRecordDAO, ProductionRecord
    PRODUCTION_RECORD_DAO_AVAILABLE = True
except ImportError:
    PRODUCTION_RECORD_DAO_AVAILABLE = False
    
try:
    from plc_addresses import get_bucket_disable_address
    BUCKET_DISABLE_AVAILABLE = True
except ImportError:
    BUCKET_DISABLE_AVAILABLE = False

class ProductionInterface:
    
    def __init__(self, parent, main_window, production_params):
        self.main_window = main_window
        self.production_params = production_params
        
        self.production_id = ""
        self.target_weight = production_params.get('target_weight', 0)
        
        self.modbus_client = None
        if main_window and hasattr(main_window, 'modbus_client'):
            self.modbus_client = main_window.modbus_client
        
        if self.modbus_client:
            try:
                from bucket_monitoring import create_bucket_monitoring_service
                self.monitoring_service = create_bucket_monitoring_service(self.modbus_client)
                
                self.monitoring_service.on_material_shortage_detected = self._on_material_shortage_detected
                self.monitoring_service.on_production_detail_recorded = self._on_production_detail_recorded
                self.monitoring_service.on_production_stop_triggered = self._on_production_stop_triggered
                self.monitoring_service.on_single_unqualified_triggered = self._on_single_unqualified_triggered
            except ImportError:
                self.monitoring_service = None
        
        self.root = tk.Toplevel(parent)
        
        self.is_production_running = False
        self.production_start_time = None
        self.monitoring_threads_running = False
        self.is_paused = False
        
        self.bucket_weights = {i: 0.0 for i in range(1, 7)}
        self.bucket_status = {i: 'normal' for i in range(1, 7)}
        self.current_package_count = 0
        self.elapsed_time = timedelta(0)
        
        self.bucket_weight_labels = {}
        self.bucket_status_indicators = {}
        self.timer_label = None
        self.progress_var = None
        self.package_count_label = None
        self.completion_rate_label = None
        self.pause_resume_btn = None
        
        self.setup_window()
        self.setup_fonts()
        self.create_widgets()
        self.center_window()
        self.start_production()
        
    def setup_placeholder(self, entry_widget, placeholder_text):
        def on_focus_in(event):
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            if not entry_widget.get().strip():
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def setup_window(self):
        self.root.title("AI模式 - 正在生产")
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        self.setup_force_exit_mechanism()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=24, weight="bold")  
        self.label_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")  
        self.data_font = tkFont.Font(family="微软雅黑", size=16)  
        self.big_data_font = tkFont.Font(family="微软雅黑", size=20, weight="bold")  
        self.button_font = tkFont.Font(family="微软雅黑", size=16, weight="bold")  
        self.small_button_font = tkFont.Font(family="微软雅黑", size=12)  
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        self.create_title_bar(main_frame)
        
        content_frame = tk.Frame(main_frame, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        left_frame = tk.Frame(content_frame, bg='white')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        self.create_bucket_monitoring_section(left_frame)
        
        right_frame = tk.Frame(content_frame, bg='white')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.create_production_info_section(right_frame)
        self.create_footer_section(main_frame)
        
    def setup_force_exit_mechanism(self):
        self.root.bind('<Control-Alt-q>', lambda e: self.force_exit())
        self.root.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        self.root.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        exit_zone = tk.Frame(self.root, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        self.click_count = 0
        self.last_click_time = 0

    def show_exit_confirmation(self):
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出生产程序吗？\n\n"
            "退出将停止生产并断开PLC连接。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_closing()
        except Exception:
            import os
            os._exit(0)
    
    def create_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X)
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="AI模式 - 正在生产", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        self.pause_resume_btn = tk.Button(right_frame, text="⏸ 暂停", 
                                        font=self.button_font,
                                        bg='#ffc107', fg='white',
                                        relief='flat', bd=0,
                                        padx=30, pady=12,
                                        command=self.on_pause_resume_click)
        self.pause_resume_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        cancel_btn = tk.Button(right_frame, text="✖ 取消", 
                             font=self.button_font,
                             bg='#dc3545', fg='white',
                             relief='flat', bd=0,
                             padx=30, pady=12,
                             command=self.on_cancel_click)
        cancel_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=4, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(15, 0))
        
    def create_bucket_monitoring_section(self, parent):
        for bucket_id in range(1, 7):
            bucket_frame = tk.Frame(parent, bg='#f8f9fa', relief='raised', bd=1)
            bucket_frame.pack(fill=tk.X, pady=8)
            bucket_frame.configure(width=280, height=70)
            bucket_frame.pack_propagate(False)
            
            left_frame = tk.Frame(bucket_frame, bg='#f8f9fa')
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=8)
            
            indicator_canvas = tk.Canvas(left_frame, width=25, height=25, 
                                       bg='#f8f9fa', highlightthickness=0)
            indicator_canvas.pack(side=tk.LEFT, padx=(0, 15))
            
            indicator_canvas.create_oval(3, 3, 22, 22, fill='#28a745', outline='#28a745')
            self.bucket_status_indicators[bucket_id] = indicator_canvas
            
            bucket_label = tk.Label(left_frame, text=f"斗{bucket_id}", 
                                  font=self.label_font, bg='#f8f9fa', fg='#333333')
            bucket_label.pack(side=tk.LEFT)
            
            weight_label = tk.Label(bucket_frame, text="0.0g", 
                                  font=self.big_data_font, bg='#f8f9fa', fg='#333333')
            weight_label.pack(side=tk.RIGHT, padx=15, pady=8)
            
            self.bucket_weight_labels[bucket_id] = weight_label
    
    def create_production_info_section(self, parent):
        params_frame = tk.Frame(parent, bg='white')
        params_frame.pack(fill=tk.X, pady=(0, 30))
        
        material_frame = tk.Frame(params_frame, bg='#e3f2fd', relief='flat', bd=0)
        material_frame.pack(side=tk.LEFT, padx=(0, 30))
        material_frame.configure(width=300, height=100)
        material_frame.pack_propagate(False)
        
        material_label = tk.Label(material_frame, 
                                text=self.production_params.get('material_name', '未知物料'),
                                font=self.big_data_font, bg='#e3f2fd', fg='#1976d2')
        material_label.pack(expand=True)
        
        weight_frame = tk.Frame(params_frame, bg='#e8f5e8', relief='flat', bd=0)
        weight_frame.pack(side=tk.LEFT, padx=(0, 30))
        weight_frame.configure(width=220, height=100)
        weight_frame.pack_propagate(False)
        
        weight_label = tk.Label(weight_frame, 
                              text=f"{self.production_params.get('target_weight', 0)}g/包",
                              font=self.big_data_font, bg='#e8f5e8', fg='#388e3c')
        weight_label.pack(expand=True)
        
        total_frame = tk.Frame(params_frame, bg='#f3e5f5', relief='flat', bd=0)
        total_frame.pack(side=tk.LEFT)
        total_frame.configure(width=150, height=100)
        total_frame.pack_propagate(False)
        
        total_label = tk.Label(total_frame, 
                             text=f"{self.production_params.get('package_quantity', 0)}包",
                             font=self.big_data_font, bg='#f3e5f5', fg='#7b1fa2')
        total_label.pack(expand=True)
        
        status_frame = tk.Frame(parent, bg='white')
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        time_frame = tk.Frame(status_frame, bg='white')
        time_frame.pack(side=tk.LEFT)
        
        tk.Label(time_frame, text="已用时:", font=self.data_font, 
                bg='white', fg='#333333').pack(anchor='w')
        
        self.timer_label = tk.Label(time_frame, text="00:00:00", 
                                  font=self.big_data_font, bg='white', fg='#333333')
        self.timer_label.pack(anchor='w')
        
        count_frame = tk.Frame(status_frame, bg='white')
        count_frame.pack(side=tk.RIGHT)
        
        self.package_count_label = tk.Label(count_frame, 
                                          text=f"0/{self.production_params.get('package_quantity', 0)}包",
                                          font=self.big_data_font, bg='white', fg='#333333')
        self.package_count_label.pack(anchor='e')
        
        self.completion_rate_label = tk.Label(count_frame, text="完成率0%",
                                            font=self.data_font, bg='white', fg='#666666')
        self.completion_rate_label.pack(anchor='e')
        
        progress_frame = tk.Frame(parent, bg='white')
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                     maximum=100, length=600)
        progress_bar.pack(fill=tk.X, pady=5)
        
        fault_frame = tk.LabelFrame(parent, text="运行日志记录", font=self.label_font,
                                  bg='white', fg='#333333')
        fault_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fault_text = tk.Text(fault_frame, height=8, font=self.data_font,
                                bg='white', fg='#333333', state='disabled')
        self.fault_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.add_fault_record("无")
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=tkFont.Font(family="微软雅黑", size=10), 
                               bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
        except ImportError:
            pass
    
    def center_window(self):
        try:
            self.root.update_idletasks()
            
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            if width <= 1 or height <= 1:
                width = 1200
                height = 800
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception:
            self.root.geometry("1200x800")
    
    def start_production(self):
        try:
            if not PLC_AVAILABLE:
                self.add_fault_record("PLC模块不可用，无法启动生产")
                return
            
            if not self.modbus_client or not self.modbus_client.is_connected:
                self.add_fault_record("PLC未连接，无法启动生产")
                return
            
            if PRODUCTION_DETAIL_DAO_AVAILABLE:
                self.production_id = ProductionDetailDAO.generate_production_id()
                self.add_fault_record(f"生产编号: {self.production_id}")
            else:
                self.production_id = f"P{datetime.now().strftime('%y%m%d%H%M')}"
                self.add_fault_record(f"生产编号: {self.production_id} (数据库不可用)")
            
            if PRODUCTION_RECORD_DAO_AVAILABLE:
                success, message, record_id = ProductionRecordDAO.create_production_record(
                    production_id=self.production_id,
                    material_name=self.production_params.get('material_name', ''),
                    target_weight=self.production_params.get('target_weight', 0),
                    package_quantity=self.production_params.get('package_quantity', 0),
                    completed_packages=0
                )

                if success:
                    self.add_fault_record(f"生产记录已创建: {message}")
                else:
                    self.add_fault_record(f"生产记录创建失败: {message}")
            else:
                self.add_fault_record("生产记录DAO不可用，无法创建生产记录")

            if self.monitoring_service:
                self.monitoring_service.set_material_check_enabled(True)
                
            def production_startup_thread():
                try:
                    if not self.modbus_client.write_coil(get_production_address('PackageCountClear'), False):
                        self.root.after(0, lambda: self.add_fault_record("发送包数清零=0命令失败"))
                        return
                    
                    time.sleep(0.05)
                    
                    if not self.modbus_client.write_coil(get_production_address('PackageCountClear'), True):
                        self.root.after(0, lambda: self.add_fault_record("发送包数清零=1命令失败"))
                        return
                    
                    time.sleep(0.05)
                    
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False):
                        self.root.after(0, lambda: self.add_fault_record("发送包装机允许启动命令失败"))
                        return
                    
                    time.sleep(0.05)
                    
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False):
                        self.root.after(0, lambda: self.add_fault_record("发送总停止=0命令失败"))
                        return
                    
                    time.sleep(0.05)
                    
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True):
                        self.root.after(0, lambda: self.add_fault_record("发送总启动=1命令失败"))
                        return
                    
                    self.root.after(0, self._start_monitoring)
                    
                except Exception as e:
                    error_msg = f"生产启动异常: {str(e)}"
                    self.root.after(0, lambda: self.add_fault_record(error_msg))
            
            startup_thread = threading.Thread(target=production_startup_thread, daemon=True)
            startup_thread.start()
            
        except Exception as e:
            error_msg = f"启动生产流程异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _start_monitoring(self):
        try:
            self.is_production_running = True
            self.is_paused = False
            self.production_start_time = datetime.now()
            self.monitoring_threads_running = True
            
            if self.pause_resume_btn:
                self.pause_resume_btn.config(text="⏸ 暂停", bg='#ffc107')
            
            if self.monitoring_service:
                bucket_ids = list(range(1, 7))
                self.monitoring_service.start_monitoring(bucket_ids, "production")
                
                self.monitoring_service.start_production_monitoring(
                    self.production_id, self.target_weight)
            
            def timer_update_thread():
                while self.monitoring_threads_running:
                    try:
                        if self.production_start_time:
                            elapsed = datetime.now() - self.production_start_time
                            self.elapsed_time = elapsed
                            
                            total_seconds = int(elapsed.total_seconds())
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            seconds = total_seconds % 60
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            
                            self.root.after(0, lambda: self.timer_label.config(text=time_str))
                        
                        time.sleep(1)
                    except Exception:
                        break
            
            def weight_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_bucket_weights()
                        time.sleep(0.1)
                    except Exception as e:
                        self.root.after(0, lambda: self.add_fault_record(f"重量监控异常: {str(e)}"))
                        break
            
            def package_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_package_count()
                        time.sleep(1)
                    except Exception as e:
                        self.root.after(0, lambda: self.add_fault_record(f"包装数量监控异常: {str(e)}"))
                        break
            
            threading.Thread(target=timer_update_thread, daemon=True).start()
            threading.Thread(target=weight_monitoring_thread, daemon=True).start()
            threading.Thread(target=package_monitoring_thread, daemon=True).start()
            
        except Exception as e:
            error_msg = f"启动监控异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _read_bucket_weights(self):
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return
            
            for bucket_id in range(1, 7):
                weight_address = BUCKET_MONITORING_ADDRESSES[bucket_id]['Weight']
                
                raw_weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                
                if raw_weight_data is not None and len(raw_weight_data) > 0:
                    raw_value = raw_weight_data[0]
                    
                    if raw_value > 32767:
                        signed_value = raw_value - 65536
                    else:
                        signed_value = raw_value
                
                    weight_value = signed_value / 10.0
                
                    if weight_value != self.bucket_weights[bucket_id]:
                        self.bucket_weights[bucket_id] = weight_value
                        weights_updated = True
                        
                        self.root.after(0, lambda bid=bucket_id, w=weight_value: 
                                      self.bucket_weight_labels[bid].config(text=f"{w:.1f}g"))
                        
                else:
                    if self.bucket_status[bucket_id] != 'error':
                        self.bucket_status[bucket_id] = 'error'
                        self.root.after(0, lambda bid=bucket_id: self._update_bucket_status(bid, 'error'))
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}重量读取失败"))
                
        except Exception:
            pass
    
    def _read_package_count(self):
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return
            
            package_data = self.modbus_client.read_holding_registers(
                get_production_address('PackageCountRegister'), 1)
            
            if package_data is not None and len(package_data) > 0:
                new_count = package_data[0]
                
                if new_count != self.current_package_count:
                    self.current_package_count = new_count
                    self.root.after(0, self._update_package_display)
            else:
                self.root.after(0, lambda: self.add_fault_record("包装数量读取失败"))
                
        except Exception:
            pass
    
    def _update_package_display(self):
        try:
            total_packages = self.production_params.get('package_quantity', 0)
            
            self.package_count_label.config(text=f"{self.current_package_count}/{total_packages}包")
            
            if total_packages > 0:
                completion_rate = (self.current_package_count / total_packages) * 100
                self.completion_rate_label.config(text=f"完成率{completion_rate:.1f}%")
                
                self.progress_var.set(completion_rate)
                
                if self.current_package_count >= total_packages + 1:
                    self._production_completed()
            
        except Exception:
            pass
    
    def _update_bucket_status(self, bucket_id: int, status: str):
        try:
            self.bucket_status[bucket_id] = status
            
            if bucket_id in self.bucket_status_indicators:
                canvas = self.bucket_status_indicators[bucket_id]
                canvas.delete("all")
                
                if status == 'normal':
                    canvas.create_oval(3, 3, 17, 17, fill='#28a745', outline='#28a745')
                else:
                    canvas.create_oval(3, 3, 17, 17, fill='#dc3545', outline='#dc3545')
                    
        except Exception:
            pass
            
    def _on_production_detail_recorded(self, bucket_id: int, detail: ProductionDetail):
        try:
            status = "有效" if detail.is_valid else "无效"
            qualified = "合格" if detail.is_qualified else "不合格"
            
            log_message = (f"料斗{bucket_id}: {detail.real_weight:.1f}g, "
                         f"误差{detail.error_value:+.1f}g, {qualified}, {status}")
            
            self.add_fault_record(log_message)
            
        except Exception:
            pass
            
    def _on_production_stop_triggered(self, bucket_id: int, reason: str):
        try:
            self.add_fault_record(f"生产已停止 - 料斗{bucket_id}: {reason}")
            
            if "连续3次不合格" in reason:
                self.root.after(0, lambda: self.show_e002_dialog(bucket_id))
            else:
                self.root.after(0, self._handle_production_auto_pause)

        except Exception:
            pass
            
    def show_e002_dialog(self, bucket_id: int):
        try:
            e002_window = tk.Toplevel(self.root)
            e002_window.title("")
            e002_window.geometry("700x500")
            e002_window.configure(bg='#ffb444')
            e002_window.resizable(False, False)
            e002_window.transient(self.root)
            e002_window.grab_set()
            
            e002_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            self.center_dialog_relative_to_main(e002_window, 700, 500)
            
            tk.Label(e002_window, text="故障代码：E002", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=50)
            
            tk.Label(e002_window, text="故障类型：算法失效", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=90)
            
            tk.Label(e002_window, text=f"故障描述：连续三次超出允许范围，认定为算法失效", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=130)
            
            processing_text = "处理方法：请选择弃用故障料斗，或全部重新自适应学习"
            tk.Label(e002_window, text=processing_text, 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white', justify='left').place(x=50, y=170)
            
            button_frame = tk.Frame(e002_window, bg='#ffb444')
            button_frame.place(x=150, y=350)
            
            disable_btn = tk.Button(button_frame, text="✕ 弃用料斗", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='white', fg='#333333',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=lambda: self._handle_disable_bucket_choice(e002_window, bucket_id))
            disable_btn.pack(side=tk.LEFT, padx=20)
            
            relearn_btn = tk.Button(button_frame, text="▶ 重新学习", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#2196f3', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=lambda: self._handle_relearn_choice(e002_window, bucket_id))
            relearn_btn.pack(side=tk.LEFT, padx=20)

        except Exception as e:
            error_msg = f"显示E002弹窗异常: {str(e)}"
            self.add_fault_record(error_msg)

    def _handle_disable_bucket_choice(self, e002_window, bucket_id: int):
        try:
            e002_window.destroy()
            self.show_disable_confirm_dialog(bucket_id)
        except Exception:
            pass

    def _handle_relearn_choice(self, e002_window, bucket_id: int):
        try:
            e002_window.destroy()
            
            result = messagebox.askyesno("确认重新学习", 
                                       f"确定要重新学习料斗{bucket_id}参数吗？\n\n"
                                       f"将跳转到AI模式界面重新开始AI生产流程。")

            if result:
                self.monitoring_threads_running = False
                self.is_production_running = False
                
                if self.monitoring_service:
                    self.monitoring_service.stop_production_monitoring()
                
                if self.modbus_client and self.modbus_client.is_connected:
                    self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                    time.sleep(0.05)
                
                    self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                    time.sleep(0.05)
                
                    self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                    time.sleep(0.05)
                    
                    self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)

                self.add_fault_record(f"料斗{bucket_id}选择重新学习，跳转到AI模式")
                self.on_closing()

        except Exception:
            pass

    def show_disable_confirm_dialog(self, bucket_id: int):
        try:
            disable_confirm_window = tk.Toplevel(self.root)
            disable_confirm_window.title("")
            disable_confirm_window.geometry("700x500")
            disable_confirm_window.configure(bg='#ffb444')
            disable_confirm_window.resizable(False, False)
            disable_confirm_window.transient(self.root)
            disable_confirm_window.grab_set()
            
            def on_window_close():
                disable_confirm_window.destroy()
                self.show_e002_dialog(bucket_id)

            disable_confirm_window.protocol("WM_DELETE_WINDOW", on_window_close)
            
            self.center_dialog_relative_to_main(disable_confirm_window, 700, 500)
            
            tk.Label(disable_confirm_window, text="请确认弃用故障料斗", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='#ffb444', fg='white').place(x=250, y=150)

            tk.Label(disable_confirm_window, text="其他料斗继续生产运行", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='#ffb444', fg='white').place(x=230, y=200)
            
            button_frame = tk.Frame(disable_confirm_window, bg='#ffb444')
            button_frame.place(x=200, y=320)
            
            def on_cancel():
                disable_confirm_window.destroy()
                self.show_e002_dialog(bucket_id)

            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='white', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=40, pady=10,
                                 command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=30)
            
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

        except Exception as e:
            error_msg = f"显示确认弃用弹窗异常: {str(e)}"
            self.add_fault_record(error_msg)

    def _execute_disable_bucket(self, bucket_id: int):
        try:
            if not BUCKET_DISABLE_AVAILABLE:
                self.add_fault_record("料斗禁用功能不可用")
                return
            
            def disable_thread():
                try:
                    disable_address = get_bucket_disable_address(bucket_id)
                    success = self.modbus_client.write_coil(disable_address, True)

                    if success:
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}已禁用"))
                    else:
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}禁用命令发送失败"))
                        
                    success1 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)
                    time.sleep(0.05)
                    
                    success2 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)

                    if success and success1 and success2:
                        self.root.after(0, lambda: self.add_fault_record(f"料斗{bucket_id}已弃用，其他料斗继续生产"))
                    else:
                        self.root.after(0, lambda: self.add_fault_record("继续生产命令发送失败"))

                except Exception as e:
                    error_msg = f"弃用料斗{bucket_id}操作异常: {str(e)}"
                    self.root.after(0, lambda: self.add_fault_record(error_msg))
                    
            threading.Thread(target=disable_thread, daemon=True).start()

        except Exception as e:
            error_msg = f"执行弃用料斗{bucket_id}操作异常: {str(e)}"
            self.add_fault_record(error_msg)

    def _handle_production_auto_pause(self):
        try:
            if self.is_production_running and not self.is_paused:
                self.is_paused = True
                self.is_production_running = False
                
                if self.pause_resume_btn:
                    self.pause_resume_btn.config(text="▶ 启动", bg='#28a745')
                
                self.add_fault_record("生产因质量问题自动暂停")
            
        except Exception:
            pass
    
    def _production_completed(self):
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                time.sleep(0.05)
                
                try:                    
                    target_reached_addresses = get_all_bucket_target_reached_addresses()
                    
                    disable_addresses = [BUCKET_PRODUCTION_DISABLE_ADDRESSES[i] for i in range(1, 7)]
                    disabled_count = 0
                    
                    for addr in disable_addresses:
                        disable_state = self.modbus_client.read_coils(addr, 1)
                        if disable_state is not None and len(disable_state) > 0 and disable_state[0]:
                            disabled_count += 1
                            
                    active_bucket_count = 6 - disabled_count
                    
                    max_wait_time = 120.0
                    check_interval = 0.5
                    start_wait_time = time.time()
                    all_buckets_reached = False
                    
                    while time.time() - start_wait_time < max_wait_time:
                        coil_states = self.modbus_client.read_coils(
                            target_reached_addresses[0], len(target_reached_addresses))
                        
                        if coil_states is not None and len(coil_states) >= active_bucket_count:
                            active_buckets_reached = 0
                            for i in range(6):
                                disable_state = self.modbus_client.read_coils(BUCKET_PRODUCTION_DISABLE_ADDRESSES[i+1], 1)
                                is_disabled = (disable_state is not None and len(disable_state) > 0 and disable_state[0])
                                
                                if not is_disabled and i < len(coil_states) and coil_states[i]:
                                    active_buckets_reached += 1
                            
                            all_buckets_reached = (active_buckets_reached == active_bucket_count)
                            
                            if all_buckets_reached:
                                break
                        
                        time.sleep(check_interval)
                    
                    if all_buckets_reached:
                        success1 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                        
                        time.sleep(0.05)
                        
                        success2 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                        
                        time.sleep(0.05)
                                
                        self.monitoring_threads_running = False
                        self.is_production_running = False
                        
                        self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)
            
                        self._update_bucket_weights_to_offline()
                        
                        if not (success1 and success2):
                            self.add_fault_record("生产停止失败")
                    else:
                        pass
                        
                except Exception as e:
                    error_msg = f"监测斗到量状态异常: {str(e)}"
                    self.add_fault_record(error_msg)
            
            material_name = self.production_params.get('material_name', '')
            
            if PRODUCTION_RECORD_DAO_AVAILABLE and self.production_id:
                success, message = ProductionRecordDAO.update_production_record(
                    production_id=self.production_id,
                    completed_packages=self.current_package_count
                )

                if success:
                    self.add_fault_record(f"生产记录已更新: {message}")
                else:
                    self.add_fault_record(f"生产记录更新失败: {message}")
            
            if MATERIAL_DAO_AVAILABLE and material_name:
                try:
                    material = MaterialDAO.get_material_by_name(material_name)
                    if material:
                        update_success, update_message = MaterialDAO.update_material_ai_status(
                            material.id, "已生产"
                        )

                        if update_success:
                            self.add_fault_record(f"物料AI状态已更新: {material_name} -> 已生产")
                        else:
                            self.add_fault_record(f"物料AI状态更新失败: {update_message}")
                    else:
                        self.add_fault_record(f"未找到物料: {material_name}")

                except Exception as e:
                    error_msg = f"更新物料AI状态异常: {str(e)}"
                    self.add_fault_record(error_msg)
            else:
                if not MATERIAL_DAO_AVAILABLE:
                    self.add_fault_record("物料DAO不可用，无法更新物料AI状态")
                if not material_name:
                    self.add_fault_record("物料名称为空，无法更新物料AI状态")
            
            target_packages = self.production_params.get('package_quantity', 0)
            actual_completion_rate = (self.current_package_count / target_packages * 100) if target_packages > 0 else 0
            
            self.show_production_completed_dialog(material_name, target_packages, actual_completion_rate)

        except Exception:
            pass
            
    def _update_bucket_weights_to_offline(self):
        try:
            def update_ui():
                updated_count = 0
                for bucket_id in range(1, 7):
                    try:
                        if bucket_id in self.bucket_weight_labels:
                            if self.bucket_weight_labels[bucket_id].winfo_exists():
                                self.bucket_weight_labels[bucket_id].config(text="--.--g")
                                updated_count += 1
                            else:
                                pass
                        else:
                            pass
                    except Exception as e:
                        pass
                
                self.add_fault_record(f"料斗重量显示已更新为离线状态 ({updated_count}/6)")
            
            self.root.after(0, update_ui)
            
            def verify_update():
                offline_count = 0
                for bucket_id in range(1, 7):
                    try:
                        if (bucket_id in self.bucket_weight_labels and 
                            self.bucket_weight_labels[bucket_id].winfo_exists()):
                            current_text = self.bucket_weight_labels[bucket_id].cget('text')
                            if current_text == "--.--g":
                                offline_count += 1
                            else:
                                self.bucket_weight_labels[bucket_id].config(text="--.--g")
                    except Exception:
                        pass
            
            self.root.after(1000, verify_update)
            
        except Exception as e:
            error_msg = f"更新料斗重量显示为离线状态异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def show_production_completed_dialog(self, material_name, target_packages, actual_completion_rate):
        try:
            completed_window = tk.Toplevel(self.root)
            completed_window.title("生产完成")
            completed_window.geometry("1425x800")
            completed_window.configure(bg='white')
            completed_window.resizable(False, False)
            completed_window.transient(self.root)
            completed_window.grab_set()
            
            completed_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            self.center_dialog_relative_to_main(completed_window, 1425, 800)
            
            tk.Label(completed_window, text="🎉", 
                    font=tkFont.Font(family="微软雅黑", size=36),
                    bg='white', fg='#28a745').pack(pady=20)
            
            tk.Label(completed_window, text="生产任务已完成！", 
                    font=tkFont.Font(family="微软雅黑", size=20, weight="bold"),
                    bg='white', fg='#333333').pack(pady=10)
            
            info_frame = tk.Frame(completed_window, bg='#f8f9fa', relief='solid', bd=1)
            info_frame.pack(fill=tk.X, padx=40, pady=20)
            
            info_text = (f"生产编号: {self.production_id}\n"
                        f"物料名称: {material_name}\n"
                        f"目标重量: {self.production_params.get('target_weight', 0)}g\n"
                        f"目标包数: {target_packages}\n\n"
                        f"请取走料斗内剩余物料！\n"
                        f"用时: {self.timer_label.cget('text')}")
            
            tk.Label(info_frame, text=info_text,
                    font=tkFont.Font(family="微软雅黑", size=20),
                    bg='#f8f9fa', fg='#333333',
                    justify='left').pack(padx=20, pady=20)
            
            button_frame = tk.Frame(completed_window, bg='white')
            button_frame.pack(pady=30)
            
            return_btn = tk.Button(button_frame, text="返回生产界面", 
                                font=tkFont.Font(family="微软雅黑", size=14),
                                bg='#6c757d', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=12,
                                command=lambda: self._handle_return_to_production(completed_window))
            return_btn.pack(side=tk.LEFT, padx=15)
            
            continue_btn = tk.Button(button_frame, text="继续生产", 
                                font=tkFont.Font(family="微软雅黑", size=14),
                                bg='#28a745', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=12,
                                command=lambda: self._handle_continue_production(completed_window, material_name))
            continue_btn.pack(side=tk.LEFT, padx=15)
            
        except Exception as e:
            error_msg = f"显示生产完成对话框异常: {str(e)}"
            self.add_fault_record(error_msg)

    def _handle_return_to_production(self, completed_window):
        try:
            completed_window.destroy()
            
            self.on_closing()
            
        except Exception:
            pass

    def _handle_continue_production(self, completed_window, material_name):
        try:
            completed_window.destroy()
            
            self.show_continue_production_dialog(material_name)
            
        except Exception:
            pass
        
    def show_continue_production_dialog(self, material_name):
        try:
            continue_window = tk.Toplevel(self.root)
            continue_window.title("继续生产")
            continue_window.geometry("1425x800")
            continue_window.configure(bg='white')
            continue_window.resizable(False, False)
            continue_window.transient(self.root)
            continue_window.grab_set()
            
            def set_grab():
                try:
                    continue_window.grab_set()
                except Exception:
                    pass
            continue_window.after(300, set_grab)
            
            self.center_dialog_relative_to_main(continue_window, 1425, 800)
            
            tk.Label(continue_window, text="继续生产", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            info_text = f"物料名称: {material_name}\n目标重量: {self.production_params.get('target_weight', 0)}g"
            tk.Label(continue_window, text=info_text,
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#666666',
                    justify='center').pack(pady=10)
            
            input_frame = tk.Frame(continue_window, bg='white')
            input_frame.pack(pady=20)
            
            tk.Label(input_frame, text="请输入继续生产的包装数量：",
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='white', fg='#333333').pack()
            
            package_quantity_var = tk.StringVar()
            package_entry = tk.Entry(input_frame, textvariable=package_quantity_var,
                                font=tkFont.Font(family="微软雅黑", size=14),
                                width=15, justify='center')
            package_entry.pack(pady=10)
            package_entry.focus_set()
            
            self.setup_placeholder(package_entry, "包装数量")
            
            button_frame = tk.Frame(continue_window, bg='white')
            button_frame.pack(pady=30)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                font=tkFont.Font(family="微软雅黑", size=14),
                                bg='#6c757d', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=10,
                                command=continue_window.destroy)
            cancel_btn.pack(side=tk.LEFT, padx=15)
            
            def on_confirm():
                try:
                    quantity_text = package_quantity_var.get().strip()
                    if not quantity_text:
                        messagebox.showerror("输入错误", "请输入包装数量")
                        return
                    
                    try:
                        package_quantity = int(quantity_text)
                        if package_quantity <= 0:
                            messagebox.showerror("输入错误", "包装数量必须大于0")
                            return
                    except ValueError:
                        messagebox.showerror("输入错误", "请输入有效的数字")
                        return
                    
                    continue_window.destroy()
                    
                    self._start_new_production(material_name, package_quantity)
                    
                except Exception as e:
                    messagebox.showerror("错误", f"处理继续生产时发生错误: {str(e)}")
            
            confirm_btn = tk.Button(button_frame, text="确认", 
                                font=tkFont.Font(family="微软雅黑", size=14),
                                bg='#28a745', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=10,
                                command=on_confirm)
            confirm_btn.pack(side=tk.LEFT, padx=15)
            
            continue_window.bind('<Return>', lambda e: on_confirm())
            
        except Exception as e:
            error_msg = f"显示继续生产输入对话框异常: {str(e)}"
            self.add_fault_record(error_msg)

    def _start_new_production(self, material_name, package_quantity):
        try:
            self.monitoring_threads_running = False
            self.is_production_running = False
            
            if self.monitoring_service:
                self.monitoring_service.stop_production_monitoring()
                self.monitoring_service.stop_all_monitoring()
            
            new_production_params = {
                'material_name': material_name,
                'target_weight': self.production_params.get('target_weight', 0),
                'package_quantity': package_quantity
            }
            
            self.root.destroy()
            
            if self.main_window:
                parent = self.main_window.root if hasattr(self.main_window, 'root') else None
                if parent:
                    new_production_interface = create_production_interface(parent, self.main_window, new_production_params)
                else:
                    pass
            else:
                pass
            
        except Exception as e:
            messagebox.showerror("错误", f"开始新生产任务时发生错误: {str(e)}")
    
    def add_fault_record(self, message: str):
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            record = f"[{timestamp}] {message}\n"
            
            self.fault_text.config(state='normal')
            self.fault_text.insert(tk.END, record)
            self.fault_text.see(tk.END)
            self.fault_text.config(state='disabled')
            
        except Exception:
            pass
    
    def on_pause_resume_click(self):
        try:
            if not self.is_paused:
                self.show_pause_confirmation_dialog()
            else:
                self._resume_production()
        except Exception as e:
            self.add_fault_record(f"暂停/启动操作异常: {str(e)}")
            
    def show_pause_confirmation_dialog(self):
        try:
            pause_confirm_window = tk.Toplevel(self.root)
            pause_confirm_window.title("")
            pause_confirm_window.geometry("600x400")
            pause_confirm_window.configure(bg='white')
            pause_confirm_window.resizable(False, False)
            pause_confirm_window.transient(self.root)
            pause_confirm_window.grab_set()
            
            self.center_dialog_relative_to_main(pause_confirm_window, 600, 400)
            
            tk.Label(pause_confirm_window, text="⏸", 
                    font=tkFont.Font(family="微软雅黑", size=36, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=30)
            
            tk.Label(pause_confirm_window, text="请再次确认你希望", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            tk.Label(pause_confirm_window, text="暂停运行", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            button_frame = tk.Frame(pause_confirm_window, bg='white')
            button_frame.pack(pady=40)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='#f0f0f0', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=40, pady=10,
                                 command=pause_confirm_window.destroy)
            cancel_btn.pack(side=tk.LEFT, padx=20)
            
            def on_confirm_pause():
                pause_confirm_window.destroy()
                self._pause_production()
                self.show_pausing_progress_dialog()
            
            confirm_btn = tk.Button(button_frame, text="确认", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=10,
                                  command=on_confirm_pause)
            confirm_btn.pack(side=tk.LEFT, padx=20)
            
        except Exception:
            pass
            
    def show_pausing_progress_dialog(self):
        try:
            self.pausing_progress_window = tk.Toplevel(self.root)
            self.pausing_progress_window.title("")
            self.pausing_progress_window.geometry("600x400")
            self.pausing_progress_window.configure(bg='white')
            self.pausing_progress_window.resizable(False, False)
            self.pausing_progress_window.transient(self.root)
            self.pausing_progress_window.grab_set()
            
            self.center_dialog_relative_to_main(self.pausing_progress_window, 600, 400)
            
            tk.Label(self.pausing_progress_window, text="⏸", 
                    font=tkFont.Font(family="微软雅黑", size=36, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            tk.Label(self.pausing_progress_window, text="设备正在暂停中", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=10)
            
            self.pausing_timer_label = tk.Label(self.pausing_progress_window, text="00:00:00", 
                                               font=tkFont.Font(family="Arial", size=18, weight="bold"),
                                               bg='white', fg='#333333')
            self.pausing_timer_label.pack(pady=10)
            
            self.pausing_timer_start_time = datetime.now()
            self.pausing_timer_running = True
            self.start_pausing_timer()
            
            button_frame = tk.Frame(self.pausing_progress_window, bg='white')
            button_frame.pack(pady=40)
            
            cancel_production_btn = tk.Button(button_frame, text="✖ 取消生产", 
                                            font=tkFont.Font(family="微软雅黑", size=14),
                                            bg='#f0f0f0', fg='#333333',
                                            relief='flat', bd=0,
                                            padx=30, pady=10,
                                            command=self.show_cancel_production_dialog)
            cancel_production_btn.pack(side=tk.LEFT, padx=20)
            
            def on_continue():
                self.stop_pausing_timer()
                self.pausing_progress_window.destroy()
                self._resume_production()
            
            continue_btn = tk.Button(button_frame, text="▶ 继续", 
                                   font=tkFont.Font(family="微软雅黑", size=14),
                                   bg='#4a90e2', fg='white',
                                   relief='flat', bd=0,
                                   padx=30, pady=10,
                                   command=on_continue)
            continue_btn.pack(side=tk.LEFT, padx=20)
            
        except Exception:
            pass
            
    def show_cancel_production_dialog(self):
        try:
            self.stop_pausing_timer()
            
            if hasattr(self, 'pausing_progress_window') and self.pausing_progress_window:
                self.pausing_progress_window.destroy()
            
            cancel_confirm_window = tk.Toplevel(self.root)
            cancel_confirm_window.title("")
            cancel_confirm_window.geometry("600x400")
            cancel_confirm_window.configure(bg='white')
            cancel_confirm_window.resizable(False, False)
            cancel_confirm_window.transient(self.root)
            cancel_confirm_window.grab_set()
            
            self.center_dialog_relative_to_main(cancel_confirm_window, 600, 400)
            
            tk.Label(cancel_confirm_window, text="✖", 
                    font=tkFont.Font(family="微软雅黑", size=36, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=30)
            
            tk.Label(cancel_confirm_window, text="请再次确认你希望", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            tk.Label(cancel_confirm_window, text="取消生产", 
                    font=tkFont.Font(family="微软雅黑", size=16),
                    bg='white', fg='#333333').pack(pady=5)
            
            button_frame = tk.Frame(cancel_confirm_window, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel():
                cancel_confirm_window.destroy()
                self.show_pausing_progress_dialog()
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='#f0f0f0', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=40, pady=10,
                                 command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=20)
            
            def on_confirm_cancel():
                cancel_confirm_window.destroy()
                self.on_closing()
            
            confirm_btn = tk.Button(button_frame, text="确认", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=10,
                                  command=on_confirm_cancel)
            confirm_btn.pack(side=tk.LEFT, padx=20)
            
        except Exception:
            pass
            
    def start_pausing_timer(self):
        try:
            def update_pausing_timer():
                if (hasattr(self, 'pausing_timer_running') and self.pausing_timer_running and
                    hasattr(self, 'pausing_progress_window') and self.pausing_progress_window and
                    self.pausing_progress_window.winfo_exists()):
                    try:
                        current_time = datetime.now()
                        elapsed_time = current_time - self.pausing_timer_start_time
                        
                        total_seconds = int(elapsed_time.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        if (hasattr(self, 'pausing_timer_label') and 
                            self.pausing_timer_label.winfo_exists()):
                            self.pausing_timer_label.config(text=time_str)
                            self.root.after(1000, update_pausing_timer)
                        else:
                            self.pausing_timer_running = False
                    except Exception:
                        self.pausing_timer_running = False
            
            update_pausing_timer()
            
        except Exception:
            pass
            
    def stop_pausing_timer(self):
        try:
            if hasattr(self, 'pausing_timer_running'):
                self.pausing_timer_running = False
        except Exception:
            pass
            
    def center_dialog_relative_to_main(self, dialog_window, dialog_width, dialog_height):
        try:
            dialog_window.update_idletasks()
            self.root.update_idletasks()
            
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()
            
            x = main_x + (main_width - dialog_width) // 2
            y = main_y + (main_height - dialog_height) // 2
            
            screen_width = dialog_window.winfo_screenwidth()
            screen_height = dialog_window.winfo_screenheight()
            
            if x + dialog_width > screen_width:
                x = screen_width - dialog_width - 20
            if x < 20:
                x = 20
            if y + dialog_height > screen_height:
                y = screen_height - dialog_height - 20
            if y < 20:
                y = 20

            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        except Exception:
            x = (dialog_window.winfo_screenwidth() - dialog_width) // 2
            y = (dialog_window.winfo_screenheight() - dialog_height) // 2
            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _pause_production(self):
        try:
            if self.is_production_running:
                self.monitoring_threads_running = False
                
                if self.modbus_client and self.modbus_client.is_connected:
                    success2 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                    if not success2:
                        self.add_fault_record("发送包装机停止命令失败")
                        return
                    
                    time.sleep(0.05)
                    
                    success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                    if not success:
                        self.add_fault_record("发送总启动=0命令失败")
                        return
                    
                    time.sleep(0.05)
                    
                    success1 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                    if not success1:
                        self.add_fault_record("发送总停止=1命令失败")
                        return
                        
                    time.sleep(0.05)
                    
                    success3 = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)
                    if not success3:
                        self.add_fault_record("发送包装机停止命令失败")
                        return
                
                self.is_paused = True
                self.is_production_running = False
                
                self.pause_resume_btn.config(text="▶ 启动", bg='#28a745')
                self.add_fault_record("生产已暂停")
                
        except Exception as e:
            self.add_fault_record(f"暂停生产异常: {str(e)}")
    
    def _resume_production(self):
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                def resume_thread():
                    try:
                        if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False):
                            self.root.after(0, lambda: self.add_fault_record("发送包装机取消停止命令失败"))
                            return
                        
                        time.sleep(0.05)
                        
                        if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False):
                            self.root.after(0, lambda: self.add_fault_record("发送总停止=0命令失败"))
                            return
                        
                        time.sleep(0.05)
                        
                        if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True):
                            self.root.after(0, lambda: self.add_fault_record("发送总启动=1命令失败"))
                            return
                        
                        self.root.after(0, self._handle_resume_success)
                        
                    except Exception as e:
                        error_msg = f"恢复生产异常: {str(e)}"
                        self.root.after(0, lambda: self.add_fault_record(error_msg))
                
                resume_operation_thread = threading.Thread(target=resume_thread, daemon=True)
                resume_operation_thread.start()
            else:
                self.add_fault_record("PLC未连接，无法恢复生产")
                
        except Exception as e:
            self.add_fault_record(f"恢复生产异常: {str(e)}")
    
    def _handle_resume_success(self):
        try:
            self.is_paused = False
            self.is_production_running = True
            
            self.pause_resume_btn.config(text="⏸ 暂停", bg='#ffc107')
            
            self._restart_monitoring()
            self.add_fault_record("生产已恢复")
            
        except Exception as e:
            self.add_fault_record(f"处理恢复生产成功异常: {str(e)}")
    
    def _restart_monitoring(self):
        try:
            self.monitoring_threads_running = True
            
            if self.monitoring_service and self.production_id and self.target_weight:
                self.monitoring_service.start_production_monitoring(
                    self.production_id, self.target_weight)
            
            def timer_update_thread():
                while self.monitoring_threads_running:
                    try:
                        if self.production_start_time:
                            elapsed = datetime.now() - self.production_start_time
                            self.elapsed_time = elapsed
                            
                            total_seconds = int(elapsed.total_seconds())
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            seconds = total_seconds % 60
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            
                            self.root.after(0, lambda: self.timer_label.config(text=time_str))
                        
                        time.sleep(1)
                    except Exception:
                        break
            
            def weight_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_bucket_weights()
                        time.sleep(0.1)
                    except Exception as e:
                        self.root.after(0, lambda: self.add_fault_record(f"重量监控异常: {str(e)}"))
                        break
            
            def package_monitoring_thread():
                while self.monitoring_threads_running:
                    try:
                        self._read_package_count()
                        time.sleep(1)
                    except Exception as e:
                        self.root.after(0, lambda: self.add_fault_record(f"包装数量监控异常: {str(e)}"))
                        break
            
            threading.Thread(target=timer_update_thread, daemon=True).start()
            threading.Thread(target=weight_monitoring_thread, daemon=True).start()
            threading.Thread(target=package_monitoring_thread, daemon=True).start()
            
        except Exception as e:
            error_msg = f"重新启动监控异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def on_cancel_click(self):
        try:
            result = messagebox.askyesno("确认取消", "确定要取消当前生产任务吗？")
            if result:
                self._pause_production()
                self.add_fault_record("生产任务已取消")
                self.on_closing()
            
        except Exception as e:
            self.add_fault_record(f"取消操作异常: {str(e)}")
            
    def _on_material_shortage_detected(self, bucket_id: int, stage: str, is_production: bool):
        try:
            if is_production and stage == "production":
                self._handle_material_shortage_stop()
                self.root.after(0, lambda: self._show_material_shortage_dialog(bucket_id))
            
        except Exception as e:
            error_msg = f"处理料斗{bucket_id}物料不足事件异常: {str(e)}"
            self.root.after(0, lambda: self.add_fault_record(error_msg))
    
    def _handle_material_shortage_stop(self):
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                def stop_thread():
                    try:
                        success = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], True)
                        
                        time.sleep(0.05)
                        
                        success1 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                        
                        time.sleep(0.05)
                        
                        success2 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
                        
                        time.sleep(0.05)
                        
                        success3 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)
                        
                        if success and success1 and success2 and success3:
                            self.root.after(0, lambda: self.add_fault_record("物料不足，生产已自动停止"))
                        else:
                            self.root.after(0, lambda: self.add_fault_record("物料不足总停止命令发送失败"))
                    
                    except Exception as e:
                        error_msg = f"物料不足停止命令异常: {str(e)}"
                        self.root.after(0, lambda: self.add_fault_record(error_msg))
                
                threading.Thread(target=stop_thread, daemon=True).start()
        
        except Exception as e:
            error_msg = f"处理E100停止命令异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _show_material_shortage_dialog(self, bucket_id: int):
        try:
            material_shortage_window = tk.Toplevel(self.root)
            material_shortage_window.title("")
            material_shortage_window.geometry("700x500")
            material_shortage_window.configure(bg='#ffb444')
            material_shortage_window.resizable(False, False)
            material_shortage_window.transient(self.root)
            material_shortage_window.grab_set()
            
            material_shortage_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            self.center_dialog_relative_to_main(material_shortage_window, 700, 500)
            
            tk.Label(material_shortage_window, text="故障代码：E001", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=50)
            
            tk.Label(material_shortage_window, text="故障类型：物料不足/闭合异常", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=90)
            
            tk.Label(material_shortage_window, text=f"故障描述：料斗物料低于最低水平线或闭合不正常", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white').place(x=50, y=130)
            
            processing_text = ("处理方法：1.请检查料斗物料是否低于最低水平线，如果是请加料\n"
                               "2.请检查料斗闭合是否正常，如闭合不正常，请手动归位完全闭合")
            tk.Label(material_shortage_window, text=processing_text, 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='#ffb444', fg='white', justify='left').place(x=50, y=170)
            
            button_frame = tk.Frame(material_shortage_window, bg='#ffb444')
            button_frame.place(x=150, y=300)
            
            cancel_btn = tk.Button(button_frame, text="✕ 取消生产", 
                                 font=tkFont.Font(family="微软雅黑", size=14),
                                 bg='white', fg='#333333',
                                 relief='flat', bd=0,
                                 padx=30, pady=10,
                                 command=lambda: self._handle_material_shortage_cancel(material_shortage_window))
            cancel_btn.pack(side=tk.LEFT, padx=20)
            
            continue_btn = tk.Button(button_frame, text="▶ 继续", 
                                   font=tkFont.Font(family="微软雅黑", size=14),
                                   bg='#2196f3', fg='white',
                                   relief='flat', bd=0,
                                   padx=30, pady=10,
                                   command=lambda: self._handle_material_shortage_continue(material_shortage_window))
            continue_btn.pack(side=tk.LEFT, padx=20)
            
        except Exception as e:
            error_msg = f"显示物料不足弹窗异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _handle_material_shortage_continue(self, dialog_window):
        try:
            dialog_window.destroy()
            
            if self.monitoring_service:
                self.monitoring_service.handle_material_shortage_continue(0, True)
            
            self._resume_production_after_material_shortage()
            
        except Exception as e:
            error_msg = f"处理物料不足继续操作异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _handle_material_shortage_cancel(self, dialog_window):
        try:
            dialog_window.destroy()
            self._show_cancel_production_confirm_dialog()
            
        except Exception as e:
            error_msg = f"处理E001取消操作异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _show_cancel_production_confirm_dialog(self):
        try:
            cancel_confirm_window = tk.Toplevel(self.root)
            cancel_confirm_window.title("")
            cancel_confirm_window.geometry("600x400")
            cancel_confirm_window.configure(bg='#ffb444')
            cancel_confirm_window.resizable(False, False)
            cancel_confirm_window.transient(self.root)
            cancel_confirm_window.grab_set()
            
            def on_window_close():
                cancel_confirm_window.destroy()
                self._show_material_shortage_dialog(1)
            
            cancel_confirm_window.protocol("WM_DELETE_WINDOW", on_window_close)
            
            self.center_dialog_relative_to_main(cancel_confirm_window, 700, 500)
            
            processing_text = ("你确定要取消\n"
                               "结束此次生产")
            tk.Label(cancel_confirm_window, text=processing_text, 
                    font=tkFont.Font(family="微软雅黑", size=24, weight="bold"),
                    bg='#ffb444', fg='white').place(x=250, y=150)
            
            button_frame = tk.Frame(cancel_confirm_window, bg='#ffb444')
            button_frame.place(x=300, y=300)
            
            def on_confirm_cancel():
                cancel_confirm_window.destroy()
                self._execute_cancel_production()
            
            confirm_btn = tk.Button(button_frame, text="确定", 
                                  font=tkFont.Font(family="微软雅黑", size=14),
                                  bg='#ff4444', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=on_confirm_cancel)
            confirm_btn.pack()
            
        except Exception as e:
            error_msg = f"显示取消生产确认弹窗异常: {str(e)}"
            self.add_fault_record(error_msg)
            
    def _on_single_unqualified_triggered(self, bucket_id: int, real_weight: float, error_value: float):
        try:
            log_message = f"料斗{bucket_id}单次不合格: {real_weight:.1f}g, 误差{error_value:+.1f}g"
            self.add_fault_record(log_message)
            
            self.root.after(0, lambda: self._show_remove_unqualified_product_dialog(bucket_id, real_weight, error_value))
            
        except Exception:
            pass
    
    def _show_remove_unqualified_product_dialog(self, bucket_id: int, real_weight: float, error_value: float):
        try:
            remove_window = tk.Toplevel(self.root)
            remove_window.title("")
            remove_window.geometry("600x400")
            remove_window.configure(bg='white')
            remove_window.resizable(False, False)
            remove_window.transient(self.root)
            remove_window.grab_set()
            
            remove_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            self.center_dialog_relative_to_main(remove_window, 600, 400)
            
            tk.Label(remove_window, text="请取走不合格产品", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='white', fg='#333333').place(x=200, y=120)
            
            detail_text = f"料斗{bucket_id}: {real_weight:.1f}g (误差{error_value:+.1f}g)"
            tk.Label(remove_window, text=detail_text, 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#666666').place(x=180, y=180)
            
            def on_confirm_removed():
                remove_window.destroy()
                self._send_resume_production_commands()
            
            confirm_btn = tk.Button(remove_window, text="确认", 
                                  font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                                  bg='#28a745', fg='white',
                                  relief='flat', bd=0,
                                  padx=50, pady=15,
                                  command=on_confirm_removed)
            confirm_btn.place(x=250, y=280)
            
        except Exception as e:
            error_msg = f"显示取走不合格产品弹窗异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def _send_resume_production_commands(self):
        def resume_commands_thread():
            try:
                success = self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['PackagingMachineStop'], False)
                
                if success:
                    self.root.after(0, lambda: self.add_fault_record("恢复生产命令发送成功，生产已继续"))
                else:
                    self.root.after(0, lambda: self.add_fault_record("恢复生产命令发送失败"))
                    
            except Exception as e:
                error_msg = f"发送恢复生产命令异常: {str(e)}"
                self.root.after(0, lambda: self.add_fault_record(error_msg))
        
        threading.Thread(target=resume_commands_thread, daemon=True).start()
    
    def _execute_cancel_production(self):
        try:
            if self.monitoring_service:
                self.monitoring_service.handle_material_shortage_cancel()
            
            self._pause_production()
            
            material_name = self.production_params.get('material_name', '')
            
            if PRODUCTION_RECORD_DAO_AVAILABLE and self.production_id:
                success, message = ProductionRecordDAO.update_production_record(
                    production_id=self.production_id,
                    completed_packages=self.current_package_count
                )
                
                if success:
                    self.add_fault_record(f"生产记录已更新（取消）: {message}")
            
            if MATERIAL_DAO_AVAILABLE and material_name:
                try:
                    material = MaterialDAO.get_material_by_name(material_name)
                    if material:
                        update_success, update_message = MaterialDAO.update_material_ai_status(
                            material.id, "已生产"
                        )
                        
                        if update_success:
                            self.add_fault_record(f"物料AI状态已更新: {material_name} -> 已生产（取消）")
                        else:
                            self.add_fault_record(f"物料AI状态更新失败: {update_message}")
                    else:
                        self.add_fault_record(f"未找到物料: {material_name}")
                        
                except Exception as e:
                    error_msg = f"更新物料AI状态异常: {str(e)}"
                    self.add_fault_record(error_msg)
            else:
                if not MATERIAL_DAO_AVAILABLE:
                    self.add_fault_record("物料DAO不可用，无法更新物料AI状态")
                if not material_name:
                    self.add_fault_record("物料名称为空，无法更新物料AI状态")
            
            self.add_fault_record("用户取消生产，生产任务已终止")
            self.on_closing()
            
        except Exception as e:
            error_msg = f"执行取消生产操作异常: {str(e)}"
            pass
    
    def _resume_production_after_material_shortage(self):
        try:
            if self.modbus_client and self.modbus_client.is_connected:
                def resume_thread():
                    try:
                        success1 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStop'], False)
                        
                        time.sleep(0.05)
                        
                        success2 = self.modbus_client.write_coil(
                            GLOBAL_CONTROL_ADDRESSES['GlobalStart'], True)
                        
                        if success1 and success2:
                            self.root.after(0, lambda: self.add_fault_record("物料不足问题已解决，生产已恢复"))
                        else:
                            self.root.after(0, lambda: self.add_fault_record("恢复生产命令发送失败"))
                    
                    except Exception as e:
                        error_msg = f"恢复生产异常: {str(e)}"
                        self.root.after(0, lambda: self.add_fault_record(error_msg))
                
                threading.Thread(target=resume_thread, daemon=True).start()
            else:
                self.add_fault_record("PLC未连接，无法恢复生产")
        
        except Exception as e:
            error_msg = f"恢复生产异常: {str(e)}"
            self.add_fault_record(error_msg)
    
    def on_closing(self):
        try:
            self.monitoring_threads_running = False
            self.is_production_running = False
            
            if self.monitoring_service:
                self.monitoring_service.stop_production_monitoring()
                self.monitoring_service.set_material_check_enabled(False)
                self.monitoring_service.stop_all_monitoring()
            
            if self.monitoring_service:
                self.monitoring_service.set_material_check_enabled(False)
                self.monitoring_service.stop_all_monitoring()
            
            if self.modbus_client and self.modbus_client.is_connected:                
                self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStart'], False)
                time.sleep(0.05)
                self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['GlobalStop'], True)
            
            if self.main_window:
                try:
                    if hasattr(self.main_window, 'show_main_window'):
                        self.main_window.show_main_window()
                    else:
                        if hasattr(self.main_window, 'root'):
                            self.main_window.root.deiconify()
                            self.main_window.root.lift()
                            self.main_window.root.focus_force()
                except Exception:
                    pass
            
        except Exception:
            pass
        finally:
            self.root.destroy()

def create_production_interface(parent, main_window, production_params):
    return ProductionInterface(parent, main_window, production_params)

if __name__ == "__main__":
    test_params = {
        'material_name': '珠光267LG',
        'target_weight': 268,
        'package_quantity': 500
    }
    
    root = tk.Tk()
    root.withdraw()
    
    production_interface = create_production_interface(root, None, test_params)
    
    root.mainloop()