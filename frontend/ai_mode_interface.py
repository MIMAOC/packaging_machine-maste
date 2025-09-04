"""
AI模式界面

作者：C
创建日期：2025-07-22
更新日期：2025-08-19
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time
from typing import Dict, List
from production_interface import create_production_interface

try:
    from clients.webapi_client import analyze_target_weight
    WEBAPI_AVAILABLE = True
except ImportError as e:
    WEBAPI_AVAILABLE = False
    
try:
    from plc_addresses import get_bucket_disable_address
    BUCKET_DISABLE_AVAILABLE = True
except ImportError as e:
    BUCKET_DISABLE_AVAILABLE = False

try:
    from plc_operations import create_plc_operations
    PLC_OPERATIONS_AVAILABLE = True
except ImportError as e:
    PLC_OPERATIONS_AVAILABLE = False
    def create_plc_operations(client):
        return None

try:
    from material_cleaning_controller import create_material_cleaning_controller
    CLEANING_CONTROLLER_AVAILABLE = True
except ImportError as e:
    CLEANING_CONTROLLER_AVAILABLE = False
    def create_material_cleaning_controller(client):
        return None

try:
    from modbus_client import ModbusClient
    MODBUS_CLIENT_AVAILABLE = True
except ImportError as e:
    MODBUS_CLIENT_AVAILABLE = False

try:
    from coarse_time_controller import create_coarse_time_test_controller
    COARSE_TIME_CONTROLLER_AVAILABLE = True
except ImportError as e:
    COARSE_TIME_CONTROLLER_AVAILABLE = False
    def create_coarse_time_test_controller(client):
        return None

try:
    from bucket_learning_state_manager import (
        create_bucket_learning_state_manager, 
        LearningStage, 
        LearningStatus
    )
    LEARNING_STATE_MANAGER_AVAILABLE = True
except ImportError as e:
    LEARNING_STATE_MANAGER_AVAILABLE = False

try:
    from database.material_dao import MaterialDAO, Material
    from database.db_connection import db_manager
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    
try:
    from database.intelligent_learning_dao import IntelligentLearningDAO, IntelligentLearning
    INTELLIGENT_LEARNING_DAO_AVAILABLE = True
except ImportError as e:
    INTELLIGENT_LEARNING_DAO_AVAILABLE = False
    
try:
    from database.production_record_dao import ProductionRecordDAO
    PRODUCTION_RECORD_DAO_AVAILABLE = True
except ImportError as e:
    PRODUCTION_RECORD_DAO_AVAILABLE = False

class AIModeInterface:
    def __init__(self, parent=None, main_window=None):
        self.main_window = main_window
        
        self.modbus_client = None
        if main_window and hasattr(main_window, 'modbus_client'):
            self.modbus_client = main_window.modbus_client
        
        self.plc_operations = None
        if self.modbus_client and PLC_OPERATIONS_AVAILABLE:
            try:
                self.plc_operations = create_plc_operations(self.modbus_client)
            except Exception as e:
                self.plc_operations = None
        
        self.cleaning_controller = None
        if self.modbus_client and CLEANING_CONTROLLER_AVAILABLE:
            try:
                self.cleaning_controller = create_material_cleaning_controller(self.modbus_client)
            except Exception as e:
                self.cleaning_controller = None
        
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        self.weight_var = tk.StringVar()
        self.quantity_var = tk.StringVar()
        self.material_var = tk.StringVar()
        
        self.material_list = self.get_material_list_from_database()
        
        self.coarse_time_controller = None
        
        self.learning_status_window = None
        self.bucket_status_labels = {}
        
        if LEARNING_STATE_MANAGER_AVAILABLE:
            self.learning_state_manager = create_bucket_learning_state_manager()
            self.learning_state_manager.on_state_changed = self._on_bucket_state_changed
            self.learning_state_manager.on_all_completed = self._on_all_learning_completed
        else:
            self.learning_state_manager = None
        
        self.setup_window()
        
        self.setup_fonts()
        
        self.create_widgets()
        
        self.center_window()
        
        self.active_dialogs = set()
        self.material_shortage_dialogs = {}
        self.dialog_lock = threading.Lock()
        
        self.all_learning_completed_notified = False
        
        self.learning_timer_id = None
        self.statistics_timer_id = None
        self.learning_timer_running = False
        self.statistics_timer_running = False
        
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

    def get_material_list_from_database(self) -> List[str]:
        material_list = ["请选择已记录物料"]
        
        if DATABASE_AVAILABLE:
            try:
                success, message = db_manager.test_connection()
                if success:
                    material_names = MaterialDAO.get_material_names(enabled_only=True)
                    material_list.extend(material_names)
                else:
                    pass
            except Exception as e:
                pass
        else:
            pass
        
        return material_list
    
    def refresh_material_list(self):
        try:
            self.material_list = self.get_material_list_from_database()
            
            if hasattr(self, 'material_combobox'):
                current_value = self.material_var.get()
                self.material_combobox['values'] = self.material_list
                
                if current_value not in self.material_list:
                    self.material_var.set(self.material_list[0])
            
        except Exception as e:
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

        except Exception as e:
            x = (dialog_window.winfo_screenwidth() - dialog_width) // 2
            y = (dialog_window.winfo_screenheight() - dialog_height) // 2
            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
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
            "确定要退出AI模式吗？\n\n"
            "退出将停止所有AI学习过程并返回主界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_closing()
        except Exception as e:
            if self.main_window:
                try:
                    self.main_window.show_main_window()
                    self.root.destroy()
                except:
                    import os
                    os._exit(0)
            else:
                import os
                os._exit(0)
    
    def center_window(self):
        try:
            self.root.update_idletasks()
            
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            if width <= 1 or height <= 1:
                width = 950
                height = 750
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            self.root.geometry("1000x750")
    
    def setup_window(self):
        self.root.title("AI模式 - 自学习自适应")
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        self.setup_force_exit_mechanism()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=28, weight="bold")
        
        self.label_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        self.entry_font = tkFont.Font(family="微软雅黑", size=16)
        
        self.button_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        
        self.footer_font = tkFont.Font(family="微软雅黑", size=12)
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)
        
        self.create_title_bar(main_frame)
        
        self.create_status_bar(main_frame)
        
        self.create_parameter_section(main_frame)
        
        self.create_control_section(main_frame)
        
        self.create_footer_section(main_frame)
    
    def create_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="AI模式 - 自学习自适应", 
                            font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        ai_icon = tk.Button(left_frame, text="🤖AI", 
                        font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                        bg='#4a90e2', fg='white', width=4, height=1,
                        relief='flat', bd=0,
                        padx=30, pady=15,
                        command=self.on_ai_icon_click)
        ai_icon.pack(side=tk.LEFT, padx=(15, 0))
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        home_btn = tk.Button(right_frame, text="返回首页", 
                        font=self.small_button_font,
                        bg='#e9ecef', fg='#333333',
                        relief='flat', bd=1,
                        padx=30, pady=15,
                        command=self.on_home_click)
        home_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        settings_btn = tk.Button(right_frame, text="设置", 
                            font=self.small_button_font,
                            bg='#e9ecef', fg='#333333',
                            relief='flat', bd=1,
                            padx=30, pady=15,
                            command=self.on_settings_click)
        settings_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 15))
    
    def create_status_bar(self, parent):
        status_frame = tk.Frame(parent, bg='white', relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        plc_frame = tk.Frame(status_frame, bg='white')
        plc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(plc_frame, text="PLC:", font=self.small_button_font, 
                bg='white', fg='#333333').pack(side=tk.LEFT)
        
        plc_status = "已连接" if (self.modbus_client and self.modbus_client.is_connected) else "未连接"
        plc_color = '#00aa00' if (self.modbus_client and self.modbus_client.is_connected) else '#ff0000'
        
        tk.Label(plc_frame, text=plc_status, font=self.small_button_font,
                bg='white', fg=plc_color).pack(side=tk.LEFT, padx=(5, 0))
    
    def create_parameter_section(self, parent):
        param_frame = tk.Frame(parent, bg='white')
        param_frame.pack(fill=tk.X, pady=(60, 80))
        
        params_container = tk.Frame(param_frame, bg='white')
        params_container.pack()
        
        self.create_weight_section(params_container)
        
        self.create_quantity_section(params_container)
        
        self.create_material_section(params_container)
    
    def create_weight_section(self, parent):
        weight_frame = tk.Frame(parent, bg='white')
        weight_frame.pack(side=tk.LEFT, padx=(0, 60))
        
        weight_title = tk.Label(weight_frame, text="每包重量", 
                              font=self.label_font, bg='white', fg='#333333')
        weight_title.pack(anchor='w')
        
        unit_label = tk.Label(weight_frame, text="克g", 
                            font=tkFont.Font(family="微软雅黑", size=14),
                            bg='white', fg='#666666')
        unit_label.pack(anchor='w', pady=(0, 10))
        
        weight_entry = tk.Entry(weight_frame, textvariable=self.weight_var,
                          font=tkFont.Font(family="微软雅黑", size=14),
                          width=25,
                          relief='solid', bd=2,
                          bg='white', fg='#333333')
        weight_entry.pack(ipady=12)
        weight_entry.focus_set()
        self.setup_placeholder(weight_entry, "请输入目标重量克数")
    
    def create_quantity_section(self, parent):
        quantity_frame = tk.Frame(parent, bg='white')
        quantity_frame.pack(side=tk.LEFT, padx=(0, 60))
        
        quantity_title = tk.Label(quantity_frame, text="包装数量", 
                                font=self.label_font, bg='white', fg='#333333')
        quantity_title.pack(anchor='w')
        
        tk.Label(quantity_frame, text=" ", 
               font=tkFont.Font(family="微软雅黑", size=12),
               bg='white').pack(pady=(0, 10))
        
        quantity_entry = tk.Entry(quantity_frame, textvariable=self.quantity_var,
                            font=tkFont.Font(family="微软雅黑", size=14),
                            width=25,
                            relief='solid', bd=2,
                            bg='white', fg='#333333')
        quantity_entry.pack(ipady=12)
        quantity_entry.focus_set()
        self.setup_placeholder(quantity_entry, "请输入所需包装数量")
    
    def create_material_section(self, parent):
        material_frame = tk.Frame(parent, bg='white')
        material_frame.pack(side=tk.LEFT)
        
        title_frame = tk.Frame(material_frame, bg='white')
        title_frame.pack(fill=tk.X)
        
        material_title = tk.Label(title_frame, text="物料选择", 
                                font=self.label_font, bg='white', fg='#333333')
        material_title.pack(side=tk.LEFT)
        
        new_material_btn = tk.Button(title_frame, text="新增物料", 
                                   font=tkFont.Font(family="微软雅黑", size=10),
                                   bg='#28a745', fg='white',
                                   relief='flat', bd=0,
                                   padx=30, pady=15,
                                   command=self.on_new_material_click)
        new_material_btn.pack(side=tk.RIGHT)
        
        tk.Label(material_frame, text=" ", 
               font=tkFont.Font(family="微软雅黑", size=6),
               bg='white').pack(pady=0)
        
        self.root.option_add('*TCombobox*Listbox.Font', ('微软雅黑', 14))
        
        material_combobox = ttk.Combobox(material_frame, textvariable=self.material_var,
                                       font=self.entry_font,
                                       width=25,
                                       values=self.material_list,
                                       state='readonly',
                                       style="Large.TCombobox")
        material_combobox.pack(ipady=12)
        material_combobox.set(self.material_list[0])
        
        self.material_combobox = material_combobox
    
    def create_control_section(self, parent):
        control_frame = tk.Frame(parent, bg='white')
        control_frame.pack(fill=tk.X, pady=(60, 80))
        
        left_buttons = tk.Frame(control_frame, bg='white')
        left_buttons.pack(side=tk.LEFT)
        
        feed_clear_btn = tk.Button(left_buttons, text="放料+清零", 
                                 font=self.button_font,
                                 bg='#6c757d', fg='white',
                                 relief='flat', bd=0,
                                 padx=40, pady=20,
                                 command=self.on_feed_clear_click)
        feed_clear_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        clear_btn = tk.Button(left_buttons, text="清料", 
                            font=self.button_font,
                            bg='#6c757d', fg='white',
                            relief='flat', bd=0,
                            padx=40, pady=20,
                            command=self.on_clear_click)
        clear_btn.pack(side=tk.LEFT)
        
        right_buttons = tk.Frame(control_frame, bg='white')
        right_buttons.pack(side=tk.RIGHT)
        
        start_ai_btn = tk.Button(right_buttons, text="开始AI生产", 
                               font=tkFont.Font(family="微软雅黑", size=20, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=50, pady=25,
                               command=self.on_start_ai_click)
        start_ai_btn.pack()
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        version_text = "MHWPM v1.5.1 ©杭州公式人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
        except ImportError as e:
            pass
    
    def on_ai_icon_click(self):
        messagebox.showinfo("AI功能", "AI语音助手功能正在开发中，敬请期待...")
    
    def on_home_click(self):
        if self.coarse_time_controller:
            try:
                self.coarse_time_controller.stop_all_coarse_time_test()
                self.coarse_time_controller.dispose()
                self.coarse_time_controller = None
            except Exception as e:
                pass
        
        if self.cleaning_controller:
            try:
                self.cleaning_controller.dispose()
                self.cleaning_controller = None
            except Exception as e:
                pass
        
        if self.learning_state_manager:
            try:
                self.learning_state_manager.reset_all_states()
            except Exception as e:
                pass
        
        if self.learning_status_window:
            try:
                self.learning_status_window.destroy()
                self.learning_status_window = None
            except Exception as e:
                pass
        
        if self.main_window:
            try:
                if hasattr(self.main_window, 'show_main_window'):
                    self.main_window.show_main_window()
                else:
                    if hasattr(self.main_window, 'root'):
                        self.main_window.root.deiconify()
                        self.main_window.root.lift()
                        self.main_window.root.focus_force()
                    else:
                        pass
            except Exception as e:
                pass
        
        self.root.destroy()
    
    def on_settings_click(self):
        try:
            self.root.withdraw()
            
            from system_settings_interface import SystemSettingsInterface
            settings_interface = SystemSettingsInterface(parent=self.root, ai_mode_window=self)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开系统设置界面失败：{str(e)}")
    
    def on_new_material_click(self):
        self.show_new_material_name_dialog()
    
    def show_new_material_name_dialog(self):
        try:
            name_dialog = tk.Toplevel(self.root)
            name_dialog.title("新物料名称")
            name_dialog.geometry("700x600")
            name_dialog.configure(bg='white')
            name_dialog.resizable(False, False)
            name_dialog.transient(self.root)
            name_dialog.grab_set()
            
            self.center_dialog_relative_to_main(name_dialog, 700, 600)
            
            tk.Label(name_dialog, text="新物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=40)
            
            name_var = tk.StringVar()
            name_entry_frame = tk.Frame(name_dialog, bg='white')
            name_entry_frame.pack(pady=20)
            
            name_entry = tk.Entry(name_entry_frame, textvariable=name_var,
                                 font=tkFont.Font(family="微软雅黑", size=12),
                                 width=30, justify='center',
                                 relief='solid', bd=1,
                                 bg='white', fg='#333333')
            name_entry.pack(ipady=8)
            name_entry.focus_set()
            self.setup_placeholder(name_entry, "请输入物料名称")
            
            button_frame = tk.Frame(name_dialog, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel_click():
                name_dialog.destroy()
            
            def on_next_click():
                material_name = name_var.get().strip()
                
                if not material_name or material_name == "请输入物料名称":
                    messagebox.showwarning("输入错误", "请输入有效的物料名称！")
                    return
                
                if DATABASE_AVAILABLE:
                    try:
                        existing_material = MaterialDAO.get_material_by_name(material_name)
                        if existing_material:
                            messagebox.showerror("物料已存在", f"物料名称'{material_name}'已存在，请使用其他名称！")
                            return
                    except Exception as e:
                        messagebox.showerror("检查错误", f"检查物料是否存在时发生错误：{str(e)}")
                        return
                
                name_dialog.destroy()
                
                self.show_new_material_params_dialog(material_name)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=15,
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            next_btn = tk.Button(button_frame, text="下一步", 
                                font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                bg='#007bff', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=15,
                                command=on_next_click)
            next_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            name_dialog.bind('<Return>', lambda e: on_next_click())
            
        except Exception as e:
            error_msg = f"显示新物料名称对话框异常: {str(e)}"
            messagebox.showerror("系统错误", error_msg)
    
    def show_new_material_params_dialog(self, material_name: str):
        try:
            params_dialog = tk.Toplevel(self.root)
            params_dialog.title("新物料名称")
            params_dialog.geometry("700x600")
            params_dialog.configure(bg='white')
            params_dialog.resizable(False, False)
            params_dialog.transient(self.root)
            params_dialog.grab_set()
            
            self.center_dialog_relative_to_main(params_dialog, 700, 600)
            
            tk.Label(params_dialog, text="新物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            name_frame = tk.Frame(params_dialog, bg='white')
            name_frame.pack(pady=10)
            
            tk.Label(name_frame, text="物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            name_display = tk.Entry(name_frame,
                                   font=tkFont.Font(family="微软雅黑", size=12),
                                   width=30, justify='center',
                                   relief='solid', bd=1,
                                   bg='#f0f0f0', fg='#333333',
                                   state='readonly')
            name_display.pack(ipady=8, pady=(5, 0))
            
            name_display.config(state='normal')
            name_display.insert(0, material_name)
            name_display.config(state='readonly')
            
            weight_frame = tk.Frame(params_dialog, bg='white')
            weight_frame.pack(pady=15)
            
            tk.Label(weight_frame, text="每包重量 g", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            weight_var = tk.StringVar()
            current_weight = self.weight_var.get()
            if current_weight and current_weight != "请输入目标重量克数":
                weight_var.set(current_weight)
            
            weight_entry = tk.Entry(weight_frame, textvariable=weight_var,
                                font=tkFont.Font(family="微软雅黑", size=12),
                                width=30, justify='center',
                                relief='solid', bd=1,
                                bg='white', fg='#333333')
            weight_entry.pack(ipady=8, pady=(5, 0))
            weight_entry.focus_set()
            
            if not weight_var.get():
                self.setup_placeholder(weight_entry, "请输入目标重量克数")
            
            quantity_frame = tk.Frame(params_dialog, bg='white')
            quantity_frame.pack(pady=15)
            
            tk.Label(quantity_frame, text="包装数量", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            quantity_var = tk.StringVar()
            current_quantity = self.quantity_var.get()
            if current_quantity and current_quantity != "请输入所需包装数量":
                quantity_var.set(current_quantity)
            
            quantity_entry = tk.Entry(quantity_frame, textvariable=quantity_var,
                                    font=tkFont.Font(family="微软雅黑", size=12),
                                    width=30, justify='center',
                                    relief='solid', bd=1,
                                    bg='white', fg='#333333')
            quantity_entry.pack(ipady=8, pady=(5, 0))
            quantity_entry.focus_set()
            
            if not quantity_var.get():
                self.setup_placeholder(quantity_entry, "请输入目标包数")
            
            button_frame = tk.Frame(params_dialog, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel_click():
                params_dialog.destroy()
                self.show_new_material_name_dialog()
            
            def on_start_click():
                weight_str = weight_var.get().strip()
                quantity_str = quantity_var.get().strip()
                
                if not weight_str or weight_str == "请输入目标重量":
                    messagebox.showwarning("参数缺失", "请输入每包重量")
                    return
                
                if not quantity_str or quantity_str == "请输入目标包数":
                    messagebox.showwarning("参数缺失", "请输入包装数量")
                    return
                
                try:
                    target_weight = float(weight_str)
                    if target_weight <= 0:
                        messagebox.showerror("参数错误", "每包重量必须大于0")
                        return
                except ValueError:
                    messagebox.showerror("参数错误", "请输入有效的重量数值")
                    return
                
                if target_weight < 60 or target_weight > 425:
                    messagebox.showerror("参数错误", 
                                    f"输入重量超出范围\n\n"
                                    f"允许范围：60g - 425g\n"
                                    f"当前输入：{target_weight}g\n\n"
                                    f"请重新输入正确的重量范围")
                    return
                
                try:
                    package_quantity = int(quantity_str)
                    if package_quantity <= 0:
                        messagebox.showerror("参数错误", "包装数量必须大于0")
                        return
                except ValueError:
                    messagebox.showerror("参数错误", "请输入有效的包装数量")
                    return
                
                if DATABASE_AVAILABLE:
                    try:
                        success, message, material_id = MaterialDAO.create_material(
                            material_name=material_name,
                            ai_status="未学习",
                            is_enabled=1
                        )
                        
                        if success:
                            self.refresh_material_list()
                            
                            self.material_var.set(material_name)
                            
                            self.weight_var.set(str(target_weight))
                            self.quantity_var.set(str(package_quantity))
                            
                            params_dialog.destroy()
                            
                            messagebox.showinfo("物料创建成功", 
                                              f"物料'{material_name}'已成功创建！\n\n"
                                              f"每包重量：{target_weight}g\n"
                                              f"包装数量：{package_quantity}包\n\n"
                                              f"现在将开始AI学习流程...")
                            
                            self.start_ai_production_for_new_material(target_weight, package_quantity, material_name)
                            
                        else:
                            messagebox.showerror("创建物料失败", f"创建物料失败：\n{message}")
                        
                    except Exception as e:
                        error_msg = f"创建物料时发生异常：{str(e)}"
                        messagebox.showerror("创建异常", error_msg)
                else:
                    messagebox.showwarning("数据库不可用", 
                                         "数据库功能不可用，无法保存新物料！\n"
                                         "新物料将仅在本次会话中有效。")
                    
                    self.material_list.append(material_name)
                    self.refresh_material_list()
                    self.material_var.set(material_name)
                    self.weight_var.set(str(target_weight))
                    self.quantity_var.set(str(package_quantity))
                    
                    params_dialog.destroy()
                    
                    self.start_ai_production_for_new_material(target_weight, package_quantity, material_name)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=15,
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            start_btn = tk.Button(button_frame, text="开始", 
                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                 bg='#007bff', fg='white',
                                 relief='flat', bd=0,
                                 padx=30, pady=15,
                                 command=on_start_click)
            start_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            params_dialog.bind('<Return>', lambda e: on_start_click())
            
        except Exception as e:
            error_msg = f"显示新物料参数对话框异常: {str(e)}"
            messagebox.showerror("系统错误", error_msg)
    
    def start_ai_production_for_new_material(self, target_weight: float, package_quantity: int, material_name: str):
        try:
            def ai_production_thread():
                try:
                    self.execute_ai_production_sequence(target_weight, package_quantity, material_name)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"AI生产过程中发生异常：\n{str(e)}"))
            
            production_thread = threading.Thread(target=ai_production_thread, daemon=True)
            production_thread.start()
            
        except Exception as e:
            error_msg = f"启动AI生产流程异常: {str(e)}"
            messagebox.showerror("启动异常", error_msg)
    
    def check_plc_status(self, operation_name: str = "操作") -> bool:
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("连接错误", f"PLC未连接，无法执行{operation_name}！\n请检查PLC连接状态后重试。")
            return False
        
        if not self.plc_operations:
            messagebox.showerror("模块错误", f"PLC操作模块未初始化，无法执行{operation_name}！")
            return False
        
        return True
    
    def on_feed_clear_click(self):
        if not self.check_plc_status("放料+清零操作"):
            return
        
        progress_window = tk.Toplevel(self.root)
        progress_window.title("放料清零操作")
        progress_window.geometry("550x350")
        progress_window.configure(bg='white')
        progress_window.resizable(False, False)
        progress_window.transient(self.root)
        progress_window.grab_set()
        progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        self.center_dialog_relative_to_main(progress_window, 550, 350)
        
        tk.Label(progress_window, text="正在放料清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=40)
        
        tk.Label(progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=10)
        
        def execute_discharge_clear_operation():
            try:
                success, message = self.plc_operations.execute_discharge_and_clear_sequence()
                
                self.root.after(0, self.handle_discharge_clear_result, 
                               progress_window, success, message)
                
            except Exception as e:
                error_msg = f"放料清零操作异常：{str(e)}"
                self.root.after(0, self.handle_discharge_clear_result, 
                               progress_window, False, error_msg)
        
        operation_thread = threading.Thread(target=execute_discharge_clear_operation, daemon=True)
        operation_thread.start()
    
    def handle_discharge_clear_result(self, progress_window, success, message):
        try:
            progress_window.destroy()
            
            if success:
                self.show_discharge_clear_completion_dialog()
            else:
                messagebox.showerror("操作失败", f"放料清零操作失败：\n{message}")
                
        except Exception as e:
            messagebox.showerror("系统错误", f"处理操作结果时发生异常：{str(e)}")
    
    def show_discharge_clear_completion_dialog(self):
        completion_window = tk.Toplevel(self.root)
        completion_window.title("操作完成")
        completion_window.geometry("550x350")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        self.center_dialog_relative_to_main(completion_window, 550, 350)
        
        tk.Label(completion_window, text="已清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)
        
        tk.Label(completion_window, text="请取走余料包装袋", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        tk.Label(completion_window, text="并确认", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        def on_confirm_taken():
            completion_window.destroy()
        
        confirm_btn = tk.Button(completion_window, text="确认 已取走", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=15,
                               command=on_confirm_taken)
        confirm_btn.pack(pady=30)
    
    def on_clear_click(self):
        if not self.check_plc_status("清料操作"):
            return
        
        if not self.cleaning_controller:
            messagebox.showerror("模块错误", "清料控制器未初始化，无法执行清料操作！")
            return
        
        self.show_cleaning_preparation_dialog()
    
    def show_cleaning_preparation_dialog(self):
        preparation_window = tk.Toplevel(self.root)
        preparation_window.title("清料准备")
        preparation_window.geometry("550x350")
        preparation_window.configure(bg='white')
        preparation_window.resizable(False, False)
        preparation_window.transient(self.root)
        preparation_window.grab_set()
        
        self.center_dialog_relative_to_main(preparation_window, 550, 350)
        
        tk.Label(preparation_window, text="准备清料", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)
        
        tk.Label(preparation_window, text="请放置包装袋或回收桶", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        tk.Label(preparation_window, text="点击确认开始", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        def on_confirm_start_cleaning():
            preparation_window.destroy()
            
            self.show_cleaning_progress_dialog()
        
        confirm_btn = tk.Button(preparation_window, text="确认 开始清料", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=15,
                               command=on_confirm_start_cleaning)
        confirm_btn.pack(pady=30)
    
    def show_cleaning_progress_dialog(self):
        self.cleaning_progress_window = tk.Toplevel(self.root)
        self.cleaning_progress_window.title("清料操作")
        self.cleaning_progress_window.geometry("550x350")
        self.cleaning_progress_window.configure(bg='white')
        self.cleaning_progress_window.resizable(False, False)
        self.cleaning_progress_window.transient(self.root)
        self.cleaning_progress_window.grab_set()
        
        self.center_dialog_relative_to_main(self.cleaning_progress_window, 550, 350)
        
        tk.Label(self.cleaning_progress_window, text="正在清料中", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=50)
        
        tk.Label(self.cleaning_progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=10)
        
        self.cleaning_controller.on_cleaning_completed = self.on_cleaning_completed
        self.cleaning_controller.on_cleaning_failed = self.on_cleaning_failed
        self.cleaning_controller.on_log_message = self.on_cleaning_log_message
        
        success, message = self.cleaning_controller.start_cleaning()
        if not success:
            self.cleaning_progress_window.destroy()
            messagebox.showerror("清料启动失败", f"无法启动清料操作：\n{message}")
            return
    
    def on_cleaning_completed(self):
        self.root.after(0, self._show_cleaning_completion_dialog)
    
    def on_cleaning_failed(self, error_message: str):
        self.root.after(0, lambda: self._handle_cleaning_failure(error_message))
    
    def on_cleaning_log_message(self, message: str):
        pass
    
    def _show_cleaning_completion_dialog(self):
        try:
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            pass
        
        completion_window = tk.Toplevel(self.root)
        completion_window.title("清料完成")
        completion_window.geometry("550x350")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        self.center_dialog_relative_to_main(completion_window, 550, 350)
        
        tk.Label(completion_window, text="清料完成", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=50)
        
        def on_return_click():
            success, message = self.cleaning_controller.stop_cleaning()
            if not success:
                pass
            else:
                pass
            
            completion_window.destroy()
        
        return_btn = tk.Button(completion_window, text="返回", 
                              font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                              bg='#007bff', fg='white',
                              relief='flat', bd=0,
                              padx=30, pady=15,
                              command=on_return_click)
        return_btn.pack(pady=20)
    
    def _handle_cleaning_failure(self, error_message: str):
        try:
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            pass
        
        messagebox.showerror("清料操作失败", f"清料操作失败：\n{error_message}")
        
        try:
            self.cleaning_controller.stop_cleaning()
        except Exception as e:
            pass
    
    def on_start_ai_click(self):
        weight = self.weight_var.get()
        quantity = self.quantity_var.get()
        material = self.material_var.get()
        
        if weight in ["", "请输入目标重量克数"]:
            messagebox.showwarning("参数缺失", "请输入目标重量")
            return
        
        if quantity in ["", "请输入所需包装数量"]:
            messagebox.showwarning("参数缺失", "请输入包装数量")
            return
        
        if material == "请选择已记录物料":
            messagebox.showwarning("参数缺失", "请选择物料类型")
            return
        
        try:
            target_weight = float(weight)
            if target_weight <= 0:
                messagebox.showerror("参数错误", "目标重量必须大于0")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的目标重量数值")
            return
        
        if target_weight < 60 or target_weight > 425:
            messagebox.showerror("参数错误", 
                            f"输入重量超出范围\n\n"
                            f"允许范围：60g - 425g\n"
                            f"当前输入：{target_weight}g\n\n"
                            f"请重新输入正确的重量范围")
            return
        
        try:
            package_quantity = int(quantity)
            if package_quantity <= 0:
                messagebox.showerror("参数错误", "包装数量必须大于0")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的包装数量")
            return
        
        if not self.check_plc_status("AI生产"):
            return
        
        if not WEBAPI_AVAILABLE:
            messagebox.showerror("WebAPI不可用", 
                               "WebAPI客户端模块未加载！\n\n"
                               "请确保API配置正确")
            return
        
        try:
            if hasattr(db_manager, 'execute_query'):
                from database.production_record_dao import ProductionRecordDAO
                latest_record = ProductionRecordDAO.get_latest_production_record_by_material_weight(material, target_weight)
                
                if latest_record:
                    if INTELLIGENT_LEARNING_DAO_AVAILABLE:
                        learned_params = IntelligentLearningDAO.get_all_learning_results_by_material(material, target_weight)
                        
                        if learned_params and len(learned_params) > 0:
                            confirm_msg = f"发现历史学习参数！\n\n" \
                                        f"物料：{material}\n" \
                                        f"目标重量：{target_weight}g\n" \
                                        f"包装数量：{package_quantity}包\n\n" \
                                        f"找到历史生产记录：{latest_record.production_id}\n" \
                                        f"已有{len(learned_params)}个料斗的学习参数\n\n" \
                                        f"是否使用历史参数直接开始生产？\n" \
                                        f"（选择'否'将重新开始AI学习）"
                            
                            use_history = messagebox.askyesno("使用历史参数", confirm_msg)
                            
                            if use_history:
                                success = self._start_production_with_learned_params(
                                    learned_params, target_weight, package_quantity, material
                                )
                                
                                if success:
                                    return
                                else:
                                    pass
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
                    
        except Exception as e:
            pass
        
        confirm_msg = f"AI生产参数确认：\n\n" \
                     f"目标重量：{target_weight} 克\n" \
                     f"包装数量：{package_quantity} 包\n" \
                     f"选择物料：{material}\n\n" \
                     f"确认开始AI自适应生产？"
        
        result = messagebox.askyesno("确认AI生产", confirm_msg)
        if not result:
            return
        
        def ai_production_thread():
            try:
                self.execute_ai_production_sequence(target_weight, package_quantity, material)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"AI生产过程中发生异常：\n{str(e)}"))
        
        production_thread = threading.Thread(target=ai_production_thread, daemon=True)
        production_thread.start()
        
    def _start_production_with_learned_params(self, learned_params: List, target_weight: float, 
                                            package_quantity: int, material: str) -> bool:
        try:            
            if BUCKET_DISABLE_AVAILABLE:
                enable_success, enable_message = self._enable_all_buckets()
                if not enable_success:
                    error_msg = f"启用料斗失败：{enable_message}"
                    messagebox.showerror("启用失败", error_msg)
                    return False
            
            learned_params_dict = {param.bucket_id: param for param in learned_params}
            
            write_success = self._write_product_parameters_to_plc(learned_params_dict, target_weight)
            if not write_success:
                error_msg = "写入历史学习参数失败"
                messagebox.showerror("参数写入失败", error_msg)
                return False
            
            production_params = {
                'material_name': material,
                'target_weight': target_weight,
                'package_quantity': package_quantity
            }
            
            self.root.withdraw()
            
            production_interface = create_production_interface(self.root, self, production_params)
            
            return True
            
        except Exception as e:
            error_msg = f"使用历史参数启动生产异常：{str(e)}"
            messagebox.showerror("生产启动异常", error_msg)
            
            try:
                self.root.deiconify()
            except:
                pass
            
            return False
    
    def execute_ai_production_sequence(self, target_weight: float, package_quantity: int, material: str):
        try:
            self.root.after(0, lambda: self.show_progress_message("步骤0/5", "正在启用所有料斗..."))
            
            if BUCKET_DISABLE_AVAILABLE:
                enable_success, enable_message = self._enable_all_buckets()
                if not enable_success:
                    error_msg = f"启用料斗失败：{enable_message}"
                    self.root.after(0, lambda: messagebox.showerror("启用失败", error_msg))
                    return
            else:
                pass
            
            self.root.after(0, lambda: self.show_progress_message("步骤1/5", "正在检查料斗重量状态..."))
            
            check_success, has_weight, check_message = self.plc_operations.check_any_bucket_has_weight()
            
            if not check_success:
                error_msg = f"检查料斗重量失败：{check_message}"
                self.root.after(0, lambda: messagebox.showerror("检查失败", error_msg))
                return
            
            if has_weight:
                self.root.after(0, lambda: self.show_material_cleaning_progress_dialog())
                
                discharge_success, discharge_message = self.plc_operations.execute_discharge_and_clear_sequence()
                
                self.root.after(0, lambda: self.close_material_cleaning_progress_dialog())
                
                if not discharge_success:
                    error_msg = f"清料操作失败：{discharge_message}"
                    self.root.after(0, lambda: messagebox.showerror("清料失败", error_msg))
                    return
                
                self.root.after(0, lambda: self.show_cleaning_completion_confirmation_dialog(target_weight, package_quantity, material))
                return
            else:
                self.continue_ai_production_after_cleaning(target_weight, package_quantity, material)
            
        except Exception as e:
            error_msg = f"AI生产序列异常：{str(e)}"
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
            
    def _enable_all_buckets(self) -> tuple:
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return False, "PLC未连接"
            
            success_count = 0
            failed_buckets = []
            
            for bucket_id in range(1, 7):
                try:
                    disable_address = get_bucket_disable_address(bucket_id)
                    success = self.modbus_client.write_coil(disable_address, False)
                    
                    if success:
                        success_count += 1
                    else:
                        failed_buckets.append(bucket_id)
                        
                except Exception as e:
                    failed_buckets.append(bucket_id)
            
            if success_count == 6:
                return True, f"所有{success_count}个料斗已成功启用"
            elif success_count > 0:
                return False, f"只有{success_count}/6个料斗启用成功，失败料斗: {failed_buckets}"
            else:
                return False, f"所有料斗启用失败，失败料斗: {failed_buckets}"
                
        except Exception as e:
            error_msg = f"启用料斗操作异常: {str(e)}"
            return False, error_msg
    
    def show_material_cleaning_progress_dialog(self):
        self.cleaning_progress_window = tk.Toplevel(self.root)
        self.cleaning_progress_window.title("清料操作")
        self.cleaning_progress_window.geometry("550x350")
        self.cleaning_progress_window.configure(bg='white')
        self.cleaning_progress_window.resizable(False, False)
        self.cleaning_progress_window.transient(self.root)
        self.cleaning_progress_window.grab_set()
        
        self.center_dialog_relative_to_main(self.cleaning_progress_window, 550, 350)
        
        tk.Label(self.cleaning_progress_window, text="检测到余料", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)

        tk.Label(self.cleaning_progress_window, text="正在清料处理", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        tk.Label(self.cleaning_progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

    def close_material_cleaning_progress_dialog(self):
        try:
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            pass
    
    def show_cleaning_completion_confirmation_dialog(self, target_weight: float, package_quantity: int, material: str):
        completion_window = tk.Toplevel(self.root)
        completion_window.title("操作完成")
        completion_window.geometry("550x350")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        self.center_dialog_relative_to_main(completion_window, 550, 350)
        
        tk.Label(completion_window, text="已清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)

        tk.Label(completion_window, text="请取走余料包装袋", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        tk.Label(completion_window, text="并确认", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        def on_confirm_start_production():
            completion_window.destroy()
            
            def continue_production_thread():
                try:
                    self.continue_ai_production_after_cleaning(target_weight, package_quantity, material)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"继续AI生产过程中发生异常：\n{str(e)}"))
                    
            production_thread = threading.Thread(target=continue_production_thread, daemon=True)
            production_thread.start()

        confirm_btn = tk.Button(completion_window, text="确认 开始生产", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=15,
                               command=on_confirm_start_production)
        confirm_btn.pack(pady=30)
    
    def continue_ai_production_after_cleaning(self, target_weight: float, package_quantity: int, material: str):
        try:
            self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在查询智能学习数据库..."))
            
            learned_params = None
            use_learned_params = False
            
            if INTELLIGENT_LEARNING_DAO_AVAILABLE:
                has_data = IntelligentLearningDAO.has_learning_data(material, target_weight)
                
                if has_data:
                    learned_results = IntelligentLearningDAO.get_all_learning_results_by_material(material, target_weight)
                    
                    if learned_results:
                        use_learned_params = True
                        learned_params = {result.bucket_id: result for result in learned_results}
                        
                        self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在使用智能学习参数写入PLC..."))
                        
                        write_success = self._write_learned_parameters_to_plc(learned_params, target_weight)
                        if not write_success:
                            error_msg = "写入智能学习参数失败，回退到API分析模式"
                            self.root.after(0, lambda: messagebox.showwarning("参数写入失败", error_msg))
                            use_learned_params = False
                    else:
                        pass
                else:
                    pass
            else:
                pass
            
            if not use_learned_params:
                self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在通过后端API分析目标重量对应的快加速度..."))
                
                if not WEBAPI_AVAILABLE:
                    error_msg = "WebAPI客户端模块不可用，无法进行参数分析"
                    self.root.after(0, lambda: messagebox.showerror("WebAPI错误", error_msg))
                    return
                
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
                
                self.root.after(0, lambda: self.show_progress_message("步骤3/4", "正在写入参数到所有料斗..."))
                
                write_success, write_message = self.plc_operations.write_bucket_parameters_all(
                    target_weight=target_weight,
                    coarse_speed=coarse_speed,
                    fine_speed=44,
                    coarse_advance=0,
                    fall_value=0
                )
                
                if not write_success:
                    error_msg = f"参数写入失败：{write_message}"
                    self.root.after(0, lambda: messagebox.showerror("写入失败", error_msg))
                    return
            
            self.root.after(0, lambda: self.show_progress_message("步骤4/4", "正在启动快加时间测定..."))
            
            self.root.after(0, lambda: self.show_multi_bucket_learning_status_dialog())
            
            if self.learning_state_manager:
                self.learning_state_manager.reset_all_states()
            
            try:
                from coarse_time_controller import create_coarse_time_test_controller
                
                self.coarse_time_controller = create_coarse_time_test_controller(self.modbus_client)
                
                self.coarse_time_controller.root_reference = self.root
                
                if hasattr(self.coarse_time_controller, 'set_material_name'):
                    self.coarse_time_controller.set_material_name(material)
                
                if hasattr(self.coarse_time_controller, 'flight_material_controller'):
                    self.coarse_time_controller.flight_material_controller.root_reference = self.root
                
                if hasattr(self.coarse_time_controller, 'fine_time_controller'):
                    self.coarse_time_controller.fine_time_controller.root_reference = self.root
                
                def on_bucket_completed(bucket_id: int, success: bool, message: str):
                    if self.learning_state_manager:
                        stage = self._determine_learning_stage_from_message(message)
                        if stage:
                            self.learning_state_manager.complete_bucket_stage(
                                bucket_id, stage, success, message
                            )
                        
                        if success and "自适应学习" in message:
                            bucket_state = self.learning_state_manager.get_bucket_state(bucket_id)
                            if bucket_state:
                                from bucket_learning_state_manager import LearningStatus
                                bucket_state.status = LearningStatus.COMPLETED
                                bucket_state.is_successful = True
                                bucket_state.completion_message = message
                                
                                if hasattr(self.learning_state_manager, 'on_state_changed') and self.learning_state_manager.on_state_changed:
                                    self.learning_state_manager.on_state_changed(bucket_id, bucket_state)
                
                def on_bucket_failed(bucket_id: int, error_message: str, failed_stage: str):
                    if self.learning_state_manager:
                        stage = self._get_learning_stage_from_failed_stage(failed_stage)
                        if stage:
                            self.learning_state_manager.complete_bucket_stage(
                                bucket_id, stage, False, error_message
                            )
                    
                    self.root.after(0, lambda: self.show_relearning_choice_dialog(bucket_id, error_message, failed_stage))
                
                def on_progress_update(bucket_id: int, current_attempt: int, max_attempts: int, message: str):
                    if self.learning_state_manager and current_attempt == 1:
                        stage = self._determine_learning_stage_from_message(message)
                        if stage:
                            self.learning_state_manager.start_bucket_stage(bucket_id, stage)
                    
                    progress_msg = f"料斗{bucket_id}进度: {current_attempt}/{max_attempts} - {message}"
                    self.root.after(0, lambda: self.show_progress_message("步骤4/4", progress_msg))
                
                def on_log_message(message: str):
                    pass
                
                self.coarse_time_controller.on_bucket_completed = on_bucket_completed
                self.coarse_time_controller.on_bucket_failed = on_bucket_failed
                self.coarse_time_controller.on_progress_update = on_progress_update
                self.coarse_time_controller.on_log_message = on_log_message
                
                if use_learned_params:
                    first_learned_result = next(iter(learned_params.values()))
                    test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                        target_weight, first_learned_result.coarse_speed)
                else:
                    test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                        target_weight, coarse_speed)
                
                if self.learning_state_manager and test_success:
                    for bucket_id in range(1, 7):
                        self.learning_state_manager.start_bucket_stage(bucket_id, LearningStage.COARSE_TIME)
                
                if not test_success:
                    error_msg = f"启动快加时间测定失败：{test_message}"
                    self.root.after(0, lambda: messagebox.showerror("测定启动失败", error_msg))
                
            except ImportError as e:
                error_msg = f"无法导入快加时间测定模块：{str(e)}\n\n请确保相关模块文件存在"
            except Exception as e:
                error_msg = f"快加时间测定启动异常：{str(e)}"
                
        except Exception as e:
            error_msg = f"AI生产序列后续步骤异常：{str(e)}"
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
            
    def _write_learned_parameters_to_plc(self, learned_params: Dict[int, IntelligentLearning], target_weight: float) -> bool:
        try:
            from plc_addresses import BUCKET_PARAMETER_ADDRESSES
            
            success_count = 0
            total_buckets = 6
            
            for bucket_id in range(1, 7):
                if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                    continue
                
                addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                if bucket_id in learned_params:
                    learned_result = learned_params[bucket_id]
                    coarse_speed = learned_result.coarse_speed
                    fine_speed = learned_result.fine_speed
                else:
                    coarse_speed = 72
                    fine_speed = 44
                    coarse_advance = 0
                    fall_value = 0
                
                bucket_success = True
                
                target_weight_plc = int(target_weight * 10)
                if not self.modbus_client.write_holding_register(addresses['TargetWeight'], target_weight_plc):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['CoarseSpeed'], coarse_speed):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['FineSpeed'], fine_speed):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['CoarseAdvance'], 0):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['FallValue'], 0):
                    bucket_success = False
                
                if bucket_success:
                    success_count += 1
            
            if success_count == total_buckets:
                return True
            else:
                return False
                
        except Exception as e:
            return False
        
    def _write_product_parameters_to_plc(self, learned_params: Dict[int, IntelligentLearning], target_weight: float) -> bool:
        try:
            from plc_addresses import BUCKET_PARAMETER_ADDRESSES
            
            success_count = 0
            total_buckets = 6
            
            for bucket_id in range(1, 7):
                if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                    continue
                
                addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                if bucket_id in learned_params:
                    learned_result = learned_params[bucket_id]
                    coarse_speed = learned_result.coarse_speed
                    fine_speed = learned_result.fine_speed
                    coarse_advance = learned_result.coarse_advance
                    fall_value = learned_result.fall_value
                else:
                    coarse_speed = 72
                    fine_speed = 44
                    coarse_advance = 0
                    fall_value = 0
                
                bucket_success = True
                
                target_weight_plc = int(target_weight * 10)
                coarse_advance_plc = int(coarse_advance * 10)
                fall_value_plc = int(fall_value * 10)
                if not self.modbus_client.write_holding_register(addresses['TargetWeight'], target_weight_plc):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['CoarseSpeed'], coarse_speed):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['FineSpeed'], fine_speed):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['CoarseAdvance'], coarse_advance_plc):
                    bucket_success = False
                
                if not self.modbus_client.write_holding_register(addresses['FallValue'], fall_value_plc):
                    bucket_success = False
                
                if bucket_success:
                    success_count += 1
            
            if success_count == total_buckets:
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def _log(self, message: str):
        pass
    
    def _determine_learning_stage_from_message(self, message: str):
        if not LEARNING_STATE_MANAGER_AVAILABLE:
            return None
            
        message_lower = message.lower()
        
        if "快加时间测定" in message or ("快加" in message and "时间" in message):
            return LearningStage.COARSE_TIME
        elif "飞料值测定" in message or ("飞料" in message and ("测定" in message or "完成" in message)):
            return LearningStage.FLIGHT_MATERIAL
        elif "慢加时间测定" in message or ("慢加" in message and "时间" in message):
            return LearningStage.FINE_TIME
        elif "自适应学习" in message or "adaptive" in message_lower:
            return LearningStage.ADAPTIVE_LEARNING
        
        if "coarse" in message_lower and "time" in message_lower:
            return LearningStage.COARSE_TIME
        elif "flight" in message_lower:
            return LearningStage.FLIGHT_MATERIAL
        elif "fine" in message_lower and "time" in message_lower:
            return LearningStage.FINE_TIME
        
        return None
    
    def _get_learning_stage_from_failed_stage(self, failed_stage: str):
        if not LEARNING_STATE_MANAGER_AVAILABLE:
            return None
            
        stage_mapping = {
            "coarse_time": LearningStage.COARSE_TIME,
            "flight_material": LearningStage.FLIGHT_MATERIAL,
            "fine_time": LearningStage.FINE_TIME,
            "adaptive_learning": LearningStage.ADAPTIVE_LEARNING
        }
        return stage_mapping.get(failed_stage)
    
    def _format_error_message(self, original_message: str) -> str:
        formatted_msg = original_message
        
        prefixes_to_remove = [
            "快加时间分析失败: ",
            "飞料值分析失败: ",
            "飞料值测定失败: ",
            "慢加时间测定失败: ", 
            "自适应学习失败: ",
            "后端API分析失败: ",
            "参数验证失败: ",
            "网络请求失败: ",
            "分析过程异常: ",
            "停止和放料失败: ",
            "重新启动失败: ",
            "更新快加速度失败: "
        ]
        
        for prefix in prefixes_to_remove:
            if formatted_msg.startswith(prefix):
                formatted_msg = formatted_msg.replace(prefix, "")
                break
        
        replacements = {
            "coarse_time_ms": "快加时间",
            "target_weight": "目标重量",
            "current_coarse_speed": "快加速度",
            "fine_time_ms": "慢加时间",
            "flight_material_value": "飞料值",
            "recorded_weights": "实时重量数据",
            "flight_material": "飞料值",
            "HTTP错误": "网络连接错误",
            "JSON解析失败": "数据格式错误",
            "连接超时": "网络超时",
            "连接拒绝": "服务器无响应"
        }
        
        for tech_term, user_friendly in replacements.items():
            formatted_msg = formatted_msg.replace(tech_term, user_friendly)
        
        return formatted_msg.strip()
    
    def show_relearning_choice_dialog(self, bucket_id: int, error_message: str, failed_stage: str):
        try:
            relearning_window = tk.Toplevel(self.root)
            relearning_window.title("学习失败")
            relearning_window.geometry("600x400")
            relearning_window.configure(bg='white')
            relearning_window.resizable(False, False)
            relearning_window.transient(self.root)
            
            if (self.learning_status_window and 
                self.learning_status_window.winfo_exists()):
                pass  
            else:
                relearning_window.grab_set()
            
            self.center_dialog_relative_to_main(relearning_window, 600, 400)
            
            def on_dialog_close():
                if hasattr(self, 'active_failure_dialogs'):
                    self.active_failure_dialogs.discard(bucket_id)
                relearning_window.destroy()
            
            relearning_window.protocol("WM_DELETE_WINDOW", on_dialog_close)
            
            stage_names = {
                "coarse_time": "快加时间测定",
                "flight_material": "飞料值测定", 
                "fine_time": "慢加时间测定",
                "adaptive_learning": "自适应学习"
            }
            stage_name = stage_names.get(failed_stage, failed_stage)
            
            tk.Label(relearning_window, text=f"料斗{bucket_id}学习失败", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=20)
            
            info_frame = tk.Frame(relearning_window, bg='white')
            info_frame.pack(pady=10, padx=20, fill=tk.X)
            
            tk.Label(info_frame, text=f"失败阶段：{stage_name}", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack(anchor='w', pady=2)
            
            formatted_error = self._format_error_message(error_message)
            
            error_text = formatted_error[:120] + "..." if len(formatted_error) > 120 else formatted_error
            tk.Label(info_frame, text=f"错误信息：{error_text}", 
                    font=tkFont.Font(family="微软雅黑", size=10),
                    bg='white', fg='#666666', 
                    wraplength=450,
                    justify='left').pack(anchor='w', pady=2)
            
            tip_frame = tk.LabelFrame(relearning_window, text="重要提示", bg='white', fg='#333333')
            tip_frame.pack(fill=tk.X, padx=20, pady=15)
            
            tip_text = "请先检查料斗是否设置正确，再选择是否重新学习"
            tk.Label(tip_frame, text=tip_text, 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#ff6600', wraplength=450).pack(pady=10, padx=10)
            
            tk.Label(relearning_window, text="请选择重新学习方式：", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack(pady=(10, 5))
            
            button_frame = tk.Frame(relearning_window, bg='white')
            button_frame.pack(pady=20)
            
            def on_restart_from_beginning():
                on_dialog_close()
                relearning_window.destroy()
                
                def restart_thread():
                    try:
                        success, message = self.coarse_time_controller.restart_bucket_learning(
                            bucket_id, "from_beginning")
                        
                        if success:
                            if self.learning_state_manager:
                                self.learning_state_manager.start_bucket_stage(bucket_id, LearningStage.COARSE_TIME)
                        else:
                            self.root.after(0, lambda: messagebox.showerror("重新学习失败", 
                                f"料斗{bucket_id}从头开始学习失败：\n{message}"))
                    except Exception as e:
                        error_msg = f"料斗{bucket_id}重新学习异常: {str(e)}"
                        self.root.after(0, lambda: messagebox.showerror("重新学习异常", error_msg))
                
                threading.Thread(target=restart_thread, daemon=True).start()
            
            def on_restart_from_current_stage():
                on_dialog_close()
                relearning_window.destroy()
                
                def restart_thread():
                    try:
                        success, message = self.coarse_time_controller.restart_bucket_learning(
                            bucket_id, "from_current_stage")
                        
                        if success:
                            if self.learning_state_manager:
                                stage = self._get_learning_stage_from_failed_stage(failed_stage)
                                if stage:
                                    self.learning_state_manager.start_bucket_stage(bucket_id, stage)
                        else:
                            self.root.after(0, lambda: messagebox.showerror("重新学习失败", 
                                f"料斗{bucket_id}从当前阶段开始学习失败：\n{message}"))
                    except Exception as e:
                        error_msg = f"料斗{bucket_id}重新学习异常: {str(e)}"
                        self.root.after(0, lambda: messagebox.showerror("重新学习异常", error_msg))
                
                threading.Thread(target=restart_thread, daemon=True).start()
            
            def on_cancel():
                """取消按钮点击事件"""
                on_dialog_close()
                relearning_window.destroy()
            
            restart_from_beginning_btn = tk.Button(button_frame, text="从头开始学习", 
                                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                                 bg='#007bff', fg='white',
                                                 relief='flat', bd=0,
                                                 padx=30, pady=15,
                                                 command=on_restart_from_beginning)
            restart_from_beginning_btn.pack(side=tk.LEFT, padx=10)
            
            restart_from_current_btn = tk.Button(button_frame, text="当前阶段开始学习", 
                                               font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                               bg='#28a745', fg='white',
                                               relief='flat', bd=0,
                                               padx=30, pady=15,
                                               command=on_restart_from_current_stage)
            restart_from_current_btn.pack(side=tk.LEFT, padx=10)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=12),
                                 bg='#6c757d', fg='white',
                                 relief='flat', bd=0,
                                 padx=30, pady=15,
                                 command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=10)
            
        except Exception as e:
            if hasattr(self, 'active_failure_dialogs'):
                self.active_failure_dialogs.discard(bucket_id)
                
            error_msg = f"显示重新学习选择弹窗异常: {str(e)}"
            messagebox.showerror("系统错误", error_msg)
    
    def _on_bucket_state_changed(self, bucket_id: int, state):
        if self.learning_status_window and bucket_id in self.bucket_status_labels:
            try:
                status_label = self.bucket_status_labels[bucket_id]
                status_text = state.get_display_text()
                status_color = state.get_display_color()
                
                self.root.after(0, lambda: status_label.config(text=status_text, fg=status_color))
                
                if state.status.value == "completed" and state.is_successful:
                    self.root.after(100, self._check_confirm_button_state)
                    
            except Exception as e:
                pass
                
    def _force_refresh_learning_status(self):
        try:
            if not self.learning_status_window or not self.learning_state_manager:
                return
            
            all_states = self.learning_state_manager.get_all_states()
            
            for bucket_id in range(1, 7):
                if bucket_id in self.bucket_status_labels and bucket_id in all_states:
                    state = all_states[bucket_id]
                    status_label = self.bucket_status_labels[bucket_id]
                    
                    status_text = state.get_display_text()
                    status_color = state.get_display_color()
                    
                    status_label.config(text=status_text, fg=status_color)
            
            self._update_learning_statistics()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
                
    def _check_confirm_button_state(self):
        try:
            if not self.learning_status_window or not self.learning_state_manager:
                return

            if not hasattr(self, 'confirm_btn') or not self.confirm_btn.winfo_exists():
                return
            
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            learning_count = 0
            not_started_count = 0
            
            all_states = self.learning_state_manager.get_all_states()
            
            for bid, state in all_states.items():
                if state.status.value == "learning":
                    learning_count += 1
                elif state.status.value == "not_started":
                    not_started_count += 1
                    
            all_buckets_finished = (success_count + failed_count) >= 6 and learning_count == 0 and not_started_count == 0

            if all_buckets_finished:
                self.confirm_btn.config(
                    state='normal',
                    bg='#28a745', 
                    fg='white',
                    text="确认 全部完成"
                )
                self._stop_learning_timer()
            else:
                self.confirm_btn.config(
                    state='disabled',
                    bg='#cccccc', 
                    fg='#666666',
                    text="确认"
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def _on_all_learning_completed(self, all_states):
        if self.learning_state_manager:
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            
            for bucket_id, state in all_states.items():
                pass
    
    def show_multi_bucket_learning_status_dialog(self):
        try:
            if self.learning_status_window:
                self._stop_learning_timer()
                self._stop_statistics_timer()
                self.learning_status_window.destroy()
                self.learning_status_window = None
                self.bucket_status_labels.clear()
                
            self.all_learning_completed_notified = False
            
            self.learning_status_window = tk.Toplevel(self.root)
            self.learning_status_window.title("多斗学习状态")
            self.learning_status_window.geometry("800x600")
            self.learning_status_window.configure(bg='white')
            self.learning_status_window.resizable(False, False)
            self.learning_status_window.transient(self.root)
            
            self.learning_status_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            self.center_dialog_relative_to_main(self.learning_status_window, 800, 600)
            
            tk.Label(self.learning_status_window, text="多斗学习状态", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)
            
            self.learning_timer_label = tk.Label(self.learning_status_window, text="00:00:00", 
                                               font=tkFont.Font(family="Arial", size=20, weight="bold"),
                                               bg='white', fg='#007bff')
            self.learning_timer_label.pack(pady=(0, 10))
            
            self._start_learning_timer()
            
            grid_frame = tk.Frame(self.learning_status_window, bg='white')
            grid_frame.pack(expand=True, fill='both', padx=20, pady=0)
            
            for i in range(6):
                bucket_id = i + 1
                row = i // 3
                col = i % 3
                
                bucket_frame = tk.Frame(grid_frame, bg='white', relief='solid', bd=1)
                bucket_frame.grid(row=row, column=col, padx=20, pady=20, sticky='nsew')
                
                grid_frame.grid_rowconfigure(row, weight=1)
                grid_frame.grid_columnconfigure(col, weight=1)
                
                tk.Label(bucket_frame, text=f"料斗{bucket_id}", 
                        font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                        bg='white', fg='#333333').pack(pady=(10, 5))
                
                if self.learning_state_manager:
                    state = self.learning_state_manager.get_bucket_state(bucket_id)
                    status_text = state.get_display_text() if state else "未开始"
                    status_color = state.get_display_color() if state else "#888888"
                else:
                    status_text = "未开始"
                    status_color = "#888888"
                
                status_label = tk.Label(bucket_frame, text=status_text,
                                      font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                      bg='white', fg=status_color)
                status_label.pack(pady=(5, 10))
                
                self.bucket_status_labels[bucket_id] = status_label
            
            self.stats_label = tk.Label(self.learning_status_window, text="学习状态：正在初始化...", 
                                      font=tkFont.Font(family="微软雅黑", size=10),
                                      bg='white', fg='#666666')
            self.stats_label.pack(pady=10)
            
            button_frame = tk.Frame(self.learning_status_window, bg='white')
            button_frame.pack(pady=20)
            
            def on_confirm_click():
                if self.learning_state_manager:
                    success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
                    
                    if (success_count + failed_count) < 6:
                        messagebox.showwarning("操作提示", "还有料斗未完成学习，请等待所有料斗学习完成后再确认！")
                        return
                    
                self._stop_learning_timer()
                self._stop_statistics_timer()
                
                self.learning_status_window.destroy()
                self.learning_status_window = None
                self.bucket_status_labels.clear()
                
                self._show_training_completed_dialog()
                
            def on_cancel_click():
                result = messagebox.askyesno(
                    "取消学习确认", 
                    "您确定要取消训练\n"
                    "结束这次生产\n\n"
                    "取消后将：\n"
                    "• 停止所有料斗的学习过程\n"
                    "• 清除当前学习进度\n"
                    "• 返回AI模式主界面\n\n"
                    "此操作不可撤销，是否确认？"
                )
            
                if result:
                    self._execute_cancel_learning_process()
            
            self.confirm_btn = tk.Button(button_frame, text="确认", 
                                        font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                        bg='#cccccc', fg='#666666',
                                        relief='flat', bd=0,
                                        padx=30, pady=15,
                                        command=on_confirm_click,
                                        state='disabled')
            self.confirm_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            self.cancel_btn = tk.Button(button_frame, text="取消", 
                                      font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                      bg='#dc3545', fg='white',
                                      relief='flat', bd=0,
                                      padx=30, pady=15,
                                      command=on_cancel_click)
            self.cancel_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            self._start_statistics_timer()
            
        except Exception as e:
            error_msg = f"显示多斗学习状态弹窗异常: {str(e)}"
            
    def _start_learning_timer(self):
        try:
            import datetime
            
            self._stop_learning_timer()
            
            self.learning_timer_start_time = datetime.datetime.now()
            self.learning_timer_running = True
            
            def update_learning_timer():
                if not self.learning_timer_running:
                    return
                    
                try:
                    current_time = datetime.datetime.now()
                    elapsed_time = current_time - self.learning_timer_start_time
                    
                    total_seconds = int(elapsed_time.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    if hasattr(self, 'learning_timer_label') and self.learning_timer_label.winfo_exists():
                        self.learning_timer_label.config(text=time_str)
                        if self.learning_timer_running:
                            self.learning_timer_id = self.root.after(1000, update_learning_timer)
                    else:
                        self.learning_timer_running = False
                        
                except Exception as e:
                    self.learning_timer_running = False
            
            self.learning_timer_id = self.root.after(1000, update_learning_timer)
            
        except Exception as e:
            error_msg = f"启动学习计时器异常: {str(e)}"

    def _stop_learning_timer(self):
        try:
            self.learning_timer_running = False
            
            if hasattr(self, 'learning_timer_id') and self.learning_timer_id:
                self.root.after_cancel(self.learning_timer_id)
                self.learning_timer_id = None
                
        except Exception as e:
            pass
    
    def _start_statistics_timer(self):
        try:
            self._stop_statistics_timer()
            
            self.statistics_timer_running = True
            
            self._update_learning_statistics()
            
        except Exception as e:
            pass

    def _stop_statistics_timer(self):
        try:
            self.statistics_timer_running = False
            
            if hasattr(self, 'statistics_timer_id') and self.statistics_timer_id:
                self.root.after_cancel(self.statistics_timer_id)
                self.statistics_timer_id = None
                
        except Exception as e:
            pass

    def _execute_cancel_learning_process(self):
        try:
            cancel_progress_window = self._show_cancel_progress_dialog()
            
            def cancel_thread():
                try:
                    cancel_success = True
                    cancel_messages = []
                    
                    if self.coarse_time_controller:
                        try:
                            stop_success, stop_msg = self.coarse_time_controller.stop_all_coarse_time_test()
                            if stop_success:
                                cancel_messages.append("✅ 快加时间测定已停止")
                            else:
                                cancel_messages.append(f"⚠️ 停止快加时间测定失败: {stop_msg}")
                        except Exception as e:
                            cancel_messages.append(f"⚠️ 停止快加时间测定异常: {str(e)}")
                            
                    if self.check_plc_status("取消学习"):
                        try:
                            plc_success, plc_msg = self.plc_operations.execute_discharge_and_clear_sequence()
                            if plc_success:
                                cancel_messages.append("✅ PLC取消命令发送成功")
                            else:
                                cancel_messages.append(f"⚠️ PLC取消命令发送失败: {plc_msg}")
                                cancel_success = False
                        except Exception as e:
                            cancel_messages.append(f"⚠️ PLC取消命令异常: {str(e)}")
                            cancel_success = False
                    else:
                        cancel_messages.append("⚠️ PLC未连接，无法发送取消命令")
                        cancel_success = False
                        
                    if self.learning_state_manager:
                        try:
                            self.learning_state_manager.reset_all_states()
                            cancel_messages.append("✅ 学习状态已重置")
                        except Exception as e:
                            cancel_messages.append(f"⚠️ 重置学习状态异常: {str(e)}")
                            
                    if self.coarse_time_controller:
                        try:
                            self.coarse_time_controller.dispose()
                            self.coarse_time_controller = None
                            cancel_messages.append("✅ 控制器资源已清理")
                        except Exception as e:
                            cancel_messages.append(f"⚠️ 清理控制器资源异常: {str(e)}")
                            
                    self.root.after(0, self._handle_cancel_learning_completed, 
                                  cancel_progress_window, cancel_success, cancel_messages)

                except Exception as e:
                    error_msg = f"取消学习过程异常: {str(e)}"
                    self.root.after(0, self._handle_cancel_learning_completed, 
                                  cancel_progress_window, False, [f"❌ {error_msg}"])
                    
            cancel_thread = threading.Thread(target=cancel_thread, daemon=True)
            cancel_thread.start()

        except Exception as e:
            error_msg = f"执行取消学习过程操作异常: {str(e)}"
            messagebox.showerror("取消操作失败", error_msg)
            
    def _show_cancel_progress_dialog(self):
        try:
            cancel_progress_window = tk.Toplevel(self.root)
            cancel_progress_window.title("取消学习")
            cancel_progress_window.geometry("550x350")
            cancel_progress_window.configure(bg='white')
            cancel_progress_window.resizable(False, False)
            cancel_progress_window.transient(self.root)
            cancel_progress_window.grab_set()
            cancel_progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            self.center_dialog_relative_to_main(cancel_progress_window, 550, 350)
            
            tk.Label(cancel_progress_window, text="正在取消学习", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=40)

            tk.Label(cancel_progress_window, text="请稍后", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='white', fg='#666666').pack(pady=10)

            return cancel_progress_window

        except Exception as e:
            return None
        
    def _handle_cancel_learning_completed(self, cancel_progress_window, success, messages):
        try:
            if cancel_progress_window:
                cancel_progress_window.destroy()
            
            self._stop_learning_timer()
            self._stop_statistics_timer()
            
            if self.learning_status_window:
                self.learning_status_window.destroy()
                self.learning_status_window = None
                self.bucket_status_labels.clear()
            
            result_title = "学习已取消" if success else "取消操作完成"
            result_message = "学习过程已成功取消！\n\n操作结果：\n" + "\n".join(messages)
            
            if success:
                result_message += "\n\n✅ 已返回AI模式主界面"
            else:
                result_message += "\n\n⚠️ 部分操作可能未完全成功，请检查系统状态"
            
            if success:
                messagebox.showinfo(result_title, result_message)
            else:
                messagebox.showwarning(result_title, result_message)
            
        except Exception as e:
            error_msg = f"处理取消学习完成事件异常: {str(e)}"
            messagebox.showerror("系统错误", error_msg)
    
    def _update_learning_statistics(self):
        try:
            if not self.learning_status_window or not self.learning_state_manager:
                self.statistics_timer_running = False
                return
            
            if not self.statistics_timer_running:
                return
            
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            learning_count = 0
            not_started_count = 0
            
            all_states = self.learning_state_manager.get_all_states()
            for state in all_states.values():
                if state.status.value == "learning":
                    learning_count += 1
                elif state.status.value == "not_started":
                    not_started_count += 1
            
            stats_text = f"学习状态：未开始 {not_started_count}个，学习中 {learning_count}个，成功 {success_count}个，失败 {failed_count}个"
            
            if hasattr(self, 'stats_label') and self.stats_label.winfo_exists():
                self.stats_label.config(text=stats_text)
            
            all_buckets_finished = (success_count + failed_count) >= 6 and learning_count == 0 and not_started_count == 0

            if hasattr(self, 'confirm_btn') and self.confirm_btn.winfo_exists():
                if all_buckets_finished:
                    self.confirm_btn.config(
                        state='normal',
                        bg='#28a745', 
                        fg='white',
                        text="确认 全部完成"
                    )
                    if not self.all_learning_completed_notified:
                        self.all_learning_completed_notified = True
                else:
                    self.confirm_btn.config(
                        state='disabled',
                        bg='#cccccc', 
                        fg='#666666',
                        text="确认"
                    )
                    if self.all_learning_completed_notified:
                        self.all_learning_completed_notified = False
            
            if self.statistics_timer_running:
                self.statistics_timer_id = self.root.after(1000, self._update_learning_statistics)
            
        except Exception as e:
            self.statistics_timer_running = False
    
    def _show_training_completed_dialog(self):
        try:
            training_window = tk.Toplevel(self.root)
            training_window.title("训练完成")
            training_window.geometry("550x350")
            training_window.configure(bg='white')
            training_window.resizable(False, False)
            training_window.transient(self.root)
            training_window.grab_set()
            
            self.center_dialog_relative_to_main(training_window, 550, 350)
            
            tk.Label(training_window, text="训练完成", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            timer_frame = tk.Frame(training_window, bg='white')
            timer_frame.pack(pady=20)
            
            timer_row_frame = tk.Frame(timer_frame, bg='white')
            timer_row_frame.pack()
            
            elapsed_label = tk.Label(timer_row_frame, text="已过去", 
                                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                                    bg='white', fg='#333333')
            elapsed_label.pack(side=tk.LEFT, padx=(0, 10))
            
            self.timer_label = tk.Label(timer_row_frame, text="00:00:00", 
                                       font=tkFont.Font(family="Arial", size=24, weight="bold"),
                                       bg='white', fg='#333333')
            self.timer_label.pack(side=tk.LEFT)
            
            tip_label = tk.Label(timer_frame, text="如果要生产，请点击下方按钮", 
                                font=tkFont.Font(family="微软雅黑", size=12),
                                bg='white', fg='#666666')
            tip_label.pack(pady=(15, 0))
            
            def on_start_production_click():
                """开始生产按钮点击事件"""
                training_window.destroy()
                if hasattr(self, 'timer_running'):
                    self.timer_running = False
            
                try:
                    production_params = {
                        'material_name': self.material_var.get() if self.material_var.get() != "请选择已记录物料" else "未知物料",
                        'target_weight': float(self.weight_var.get()) if self.weight_var.get() and self.weight_var.get() != "请输入目标重量克数" else 0,
                        'package_quantity': int(self.quantity_var.get()) if self.quantity_var.get() and self.quantity_var.get() != "请输入所需包装数量" else 0
                    }
                    
                    self.root.withdraw()
                    
                    production_interface = create_production_interface(self.root, self, production_params)
                    
                except Exception as e:
                    self.root.deiconify()
                    error_msg = f"打开生产界面失败：{str(e)}"
                    messagebox.showerror("界面错误", error_msg)
            
            start_production_btn = tk.Button(training_window, text="开始生产", 
                                           font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                           bg='#007bff', fg='white',
                                           relief='flat', bd=0,
                                           padx=30, pady=15,
                                           command=on_start_production_click)
            start_production_btn.pack(pady=30)
            
            self._start_timer()
            
        except Exception as e:
            error_msg = f"显示训练完成弹窗异常: {str(e)}"
    
    def _start_timer(self):
        try:
            import datetime
            
            self.timer_start_time = datetime.datetime.now()
            self.timer_running = True
            
            def update_timer():
                if hasattr(self, 'timer_running') and self.timer_running:
                    try:
                        current_time = datetime.datetime.now()
                        elapsed_time = current_time - self.timer_start_time
                        
                        total_seconds = int(elapsed_time.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        if hasattr(self, 'timer_label') and self.timer_label.winfo_exists():
                            self.timer_label.config(text=time_str)
                            self.root.after(1000, update_timer)
                        else:
                            self.timer_running = False
                    except Exception as e:
                        self.timer_running = False
            
            update_timer()
            
        except Exception as e:
            error_msg = f"启动计时器异常: {str(e)}"
    
    def show_progress_message(self, step: str, message: str):
        pass
    
    def on_closing(self):
        if self.coarse_time_controller:
            try:
                self.coarse_time_controller.stop_all_coarse_time_test()
                self.coarse_time_controller.dispose()
                self.coarse_time_controller = None
            except Exception as e:
                pass
        
        if self.cleaning_controller:
            try:
                self.cleaning_controller.dispose()
                self.cleaning_controller = None
            except Exception as e:
                pass
        
        if self.learning_state_manager:
            try:
                self.learning_state_manager.reset_all_states()
            except Exception as e:
                pass
        
        if self.learning_status_window:
            try:
                self.learning_status_window.destroy()
                self.learning_status_window = None
            except Exception as e:
                pass
        
        if self.main_window:
            try:
                if hasattr(self.main_window, 'show_main_window'):
                    self.main_window.show_main_window()
                else:
                    if hasattr(self.main_window, 'root'):
                        self.main_window.root.deiconify()
                        self.main_window.root.lift()
                        self.main_window.root.focus_force()
                    else:
                        pass
            except Exception as e:
                pass
        
        self.root.destroy()
    
    def show(self):
        if self.is_main_window:
            self.root.mainloop()

def main():
    ai_interface = AIModeInterface()
    
    ai_interface.root.update_idletasks()
    width = ai_interface.root.winfo_width()
    height = ai_interface.root.winfo_height()
    x = (ai_interface.root.winfo_screenwidth() // 2) - (width // 2)
    y = (ai_interface.root.winfo_screenheight() // 2) - (height // 2)
    ai_interface.root.geometry(f'{width}x{height}+{x}+{y}')
    
    ai_interface.show()

if __name__ == "__main__":
    main()