"""
系统设置界面模块

作者：L
创建日期：2025-08-15
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any

try:
    from traditional_plc_addresses import (
        get_traditional_system_address,
        get_traditional_system_control_address,
        TRADITIONAL_SYSTEM_ADDRESSES,
        TRADITIONAL_SYSTEM_CONTROL_ADDRESSES
    )
    from modbus_client import ModbusClient
except ImportError as e:
    pass


class SystemSettingInterface:
    
    SYSTEM_PASSWORD = "123456"
    
    def __init__(self, modbus_client: Optional[ModbusClient], parent_interface):
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        
        self.is_showing = False
        
        self.font_scale = 1.0
        
        self.parameter_data = {}

        self.parameter_entries = {}
        self.control_buttons = {}
        
        self.parameter_configs = {
            'ZeroTrackRange': {'type': 'integer', 'decimals': 0, 'label': '零点追踪范围'},
            'ZeroTrackTime': {'type': 'integer', 'decimals': 0, 'label': '零点追踪时间'},
            'ZeroClearRange': {'type': 'integer', 'decimals': 0, 'label': '清零范围(%)'},
            'StabilityRange': {'type': 'integer', 'decimals': 0, 'label': '判稳范围'},
            'StabilityTime': {'type': 'integer', 'decimals': 0, 'label': '判稳时间'},
            'FilterLevelA': {'type': 'integer', 'decimals': 0, 'label': '滤波等级A'},
            'FilterLevelB': {'type': 'integer', 'decimals': 0, 'label': '滤波等级B'},
            'MinDivision': {'type': 'integer', 'decimals': 0, 'label': '最小分度'},
            'MaxCapacity': {'type': 'integer', 'decimals': 0, 'label': '最大量程'}
        }
        
        self.control_configs = {
            'ModuleInit': {'label': '模块初始化', 'color': '#4a90e2'},
            'FeedDataInit': {'label': '加料数据初始化', 'color': '#4a90e2'},
            'ModuleDataRead': {'label': '模块数据读取', 'color': '#4a90e2'},
            'SystemSave': {'label': '保存', 'color': '#4a90e2'}
        }
        
        self.calculate_font_scale()
        
        self.setup_fonts()
    
    def setup_window(self):
        try:
            self.root.geometry("1400x900")
            self.root.configure(bg='white')
            self.root.resizable(True, True)
            
            self.center_window()
            
        except Exception as e:
            pass
    
    def center_window(self):
        try:
            self.root.update_idletasks()
            
            width = 1400
            height = 900
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            self.root.geometry("1400x900")
    
    def calculate_font_scale(self):
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if screen_width >= 2560:
                self.font_scale = 1.2
            elif screen_width >= 1920:
                self.font_scale = 1.0
            else:
                self.font_scale = 0.8
                
        except Exception as e:
            self.font_scale = 1.0
    
    def setup_fonts(self):
        try:
            base_title = int(48 * self.font_scale)
            base_label = int(32 * self.font_scale)
            base_entry = int(32 * self.font_scale)
            base_button = int(24 * self.font_scale)
            
            self.title_font = font.Font(family="Microsoft YaHei", size=base_title, weight="bold")
            self.label_font = font.Font(family="Microsoft YaHei", size=base_label, weight="normal")
            self.entry_font = font.Font(family="Arial", size=base_entry, weight="bold")
            self.button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
            self.home_button_font = font.Font(family="Microsoft YaHei", size=int(20 * self.font_scale), weight="bold")
            
        except Exception as e:
            self.title_font = font.Font(family="Microsoft YaHei", size=48, weight="bold")
            self.label_font = font.Font(family="Microsoft YaHei", size=32, weight="normal")
            self.entry_font = font.Font(family="Arial", size=32, weight="bold")
            self.button_font = font.Font(family="Microsoft YaHei", size=24, weight="bold")
            self.home_button_font = font.Font(family="Microsoft YaHei", size=20, weight="bold")
    
    def verify_password(self):
        try:
            password_dialog = tk.Toplevel(self.root)
            password_dialog.title("系统设置密码验证")
            password_dialog.geometry("400x200")
            password_dialog.resizable(False, False)
            password_dialog.configure(bg='white')
            password_dialog.grab_set()
            
            password_dialog.transient(self.root)
            password_dialog.update_idletasks()
            x = (password_dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (password_dialog.winfo_screenheight() // 2) - (200 // 2)
            password_dialog.geometry(f"400x200+{x}+{y}")
            
            password_result = {"password": None, "confirmed": False}
            
            title_label = tk.Label(password_dialog, text="请输入管理员密码:", 
                                font=("Microsoft YaHei", 16), bg='white', fg='#333333')
            title_label.pack(pady=20)
            
            password_entry = tk.Entry(password_dialog, font=("Arial", 14), justify='center',
                                    show='*', width=20, relief='solid', bd=2)
            password_entry.pack(pady=10)
            password_entry.focus_set()
            
            button_frame = tk.Frame(password_dialog, bg='white')
            button_frame.pack(pady=20)
            
            def on_confirm():
                password_result["password"] = password_entry.get()
                password_result["confirmed"] = True
                password_dialog.destroy()
            
            def on_cancel():
                password_result["confirmed"] = False
                password_dialog.destroy()
            
            confirm_btn = tk.Button(button_frame, text="确认", font=("Microsoft YaHei", 12),
                                bg='#4a90e2', fg='white', width=8, height=1,
                                command=on_confirm)
            confirm_btn.pack(side=tk.LEFT, padx=10)
            
            cancel_btn = tk.Button(button_frame, text="取消", font=("Microsoft YaHei", 12),
                                bg='#e0e0e0', fg='#333333', width=8, height=1,
                                command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=10)
            
            password_entry.bind('<Return>', lambda e: on_confirm())
            
            password_entry.focus_set()
            
            password_dialog.wait_window()
            
            if not password_result["confirmed"]:
                return False
            
            if password_result["password"] and password_result["password"].strip() == self.SYSTEM_PASSWORD:
                messagebox.showinfo("验证成功", "密码验证通过，进入系统设置界面", parent=self.root)
                return True
            else:
                messagebox.showerror("验证失败", "密码错误，无法进入系统设置", parent=self.root)
                return False
                
        except Exception as e:
            messagebox.showerror("验证异常", f"密码验证过程中发生错误: {e}", parent=self.root)
            return False
    
    def show_interface(self):
        try:
            if not self.verify_password():
                self.parent.show_menu_interface()
                return
            
            self.parent.clear_main_content()
            self.is_showing = True
            
            self.create_system_interface()
            
            self.load_all_parameters()
            
        except Exception as e:
            messagebox.showerror("界面错误", f"显示系统设置界面时发生错误: {e}")
            self.parent.show_menu_interface()
    
    def create_system_interface(self):
        try:
            main_content_frame = self.parent.get_main_content_frame()
            
            base_padding = int(20 * self.font_scale)
            content_padding = int(60 * self.font_scale)
            element_spacing = int(50 * self.font_scale)
            
            main_container = tk.Frame(main_content_frame, bg='#ffffff')
            main_container.pack(fill=tk.BOTH, expand=True, padx=base_padding, pady=base_padding)
            
            self.create_title_bar(main_container)
            
            self.create_parameters_area(main_container, element_spacing, content_padding)
            
            self.create_control_area(main_container)
            
        except Exception as e:
            raise
    
    def create_title_bar(self, parent):
        try:
            title_frame = tk.Frame(parent, bg='#4a90e2', height=100)
            title_frame.pack(fill=tk.X, pady=(0, int(30 * self.font_scale)))
            title_frame.pack_propagate(False)
            
            center_container = tk.Frame(title_frame, bg='#4a90e2')
            center_container.grid(row=0, column=0, sticky='')
            
            title_label = tk.Label(center_container, text="系统设置",
                                 font=self.title_font, bg='#4a90e2', fg='white')
            title_label.pack()
            
            title_frame.grid_rowconfigure(0, weight=1)
            title_frame.grid_columnconfigure(0, weight=1)
            
            home_button = tk.Button(title_frame, text="主页",
                                  font=self.home_button_font, bg='#e0e0e0', fg='#333333',
                                  width=8, height=2,
                                  relief='solid', bd=1,
                                  command=self.go_back_to_menu)
            home_button.place(relx=0.98, rely=0.5, anchor='e')
            
        except Exception as e:
            raise
    
    def create_parameters_area(self, parent, element_spacing, content_padding):
        try:
            params_frame = tk.Frame(parent, bg='#ffffff')
            params_frame.pack(fill=tk.BOTH, expand=True, padx=content_padding, pady=(0, int(15 * self.font_scale)))
            
            left_column = tk.Frame(params_frame, bg='#ffffff')
            left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, int(30 * self.font_scale)))
            
            right_column = tk.Frame(params_frame, bg='#ffffff')
            right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(int(30 * self.font_scale), 0))
            
            left_params = ['ZeroTrackRange', 'ZeroTrackTime', 'ZeroClearRange', 'StabilityRange', 'StabilityTime']
            
            right_params = ['FilterLevelA', 'FilterLevelB', 'MinDivision', 'MaxCapacity']
            
            for i, param_key in enumerate(left_params):
                self.create_parameter_row(left_column, param_key, element_spacing)
            
            for i, param_key in enumerate(right_params):
                self.create_parameter_row(right_column, param_key, element_spacing)
            
            empty_row = tk.Frame(right_column, bg='#ffffff', height=int(65 * self.font_scale + element_spacing))
            empty_row.pack(fill=tk.X, pady=(element_spacing, 0))
            
        except Exception as e:
            raise
    
    def create_parameter_row(self, parent, param_key, element_spacing):
        try:
            config = self.parameter_configs[param_key]
            
            param_row = tk.Frame(parent, bg='#ffffff')
            param_row.pack(fill=tk.X, pady=(element_spacing, 0))
            
            param_label = tk.Label(param_row, text=f"{config['label']}:",
                                 font=self.label_font, bg='#ffffff', fg='#333333')
            param_label.pack(side=tk.LEFT, anchor='w')
            
            param_entry = tk.Entry(param_row, font=self.entry_font, justify='center',
                                 width=15, relief='solid', bd=2, 
                                 highlightthickness=2, highlightcolor='#4a90e2', 
                                 bg='white', fg='#333333')
            param_entry.pack(side=tk.RIGHT, anchor='e', ipady=10)
            param_entry.focus_set()
            
            param_entry.bind('<FocusOut>', 
                           lambda e, pk=param_key: self.on_parameter_changed(pk, e.widget.get()))
            param_entry.bind('<Return>', 
                           lambda e, pk=param_key: self.on_parameter_changed(pk, e.widget.get()))
            
            self.parameter_entries[param_key] = param_entry
            
        except Exception as e:
            pass
    
    def create_control_area(self, parent):
        try:
            control_frame = tk.Frame(parent, bg='#ffffff', height=int(120 * self.font_scale))
            control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=int(20 * self.font_scale))
            control_frame.pack_propagate(False)
            
            button_container = tk.Frame(control_frame, bg='#ffffff')
            button_container.pack(expand=True)
            
            for command_key, config in self.control_configs.items():
                btn = tk.Button(button_container, text=config['label'],
                              font=self.button_font, bg=config['color'], fg='white',
                              width=18, height=3,
                              relief='solid', bd=1,
                              command=lambda cmd=command_key: self.execute_system_command(cmd))
                btn.pack(side=tk.LEFT, padx=15)
                
                self.control_buttons[command_key] = btn
            
        except Exception as e:
            raise
    
    def load_all_parameters(self):
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                self.load_default_parameters()
                return
            
            success_count = 0
            for param_key in self.parameter_configs.keys():
                try:
                    success = self.load_parameter(param_key)
                    if success:
                        success_count += 1
                except Exception as e:
                    pass
            
        except Exception as e:
            self.load_default_parameters()
    
    def load_parameter(self, param_key: str) -> bool:
        try:
            address = get_traditional_system_address(param_key)
            
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data:
                config = self.parameter_configs[param_key]
                value = self.format_parameter_value(param_key, data[0])
                
                self.update_parameter_display(param_key, value)
                
                self.parameter_data[param_key] = value
                
                return True
            else:
                self.load_default_parameter(param_key)
                return False
                
        except Exception as e:
            self.load_default_parameter(param_key)
            return False
    
    def format_parameter_value(self, param_key: str, plc_value: int) -> str:
        try:
            config = self.parameter_configs[param_key]
            
            if config['type'] == 'decimal':
                value = plc_value / 10.0
                return f"{value:.{config['decimals']}f}"
            else:
                return str(plc_value)
                
        except Exception as e:
            return str(plc_value)
    
    def update_parameter_display(self, param_key: str, value: str):
        try:
            if param_key in self.parameter_entries:
                entry = self.parameter_entries[param_key]
                entry.delete(0, tk.END)
                entry.insert(0, value)
        except Exception as e:
            pass
    
    def load_default_parameters(self):
        try:
            default_values = {
                'ZeroTrackRange': '50',
                'ZeroTrackTime': '100', 
                'ZeroClearRange': '5',
                'StabilityRange': '10',
                'StabilityTime': '2000',
                'FilterLevelA': '3',
                'FilterLevelB': '5',
                'MinDivision': '1',
                'MaxCapacity': '50000'
            }
            
            for param_key, default_value in default_values.items():
                self.update_parameter_display(param_key, default_value)
                self.parameter_data[param_key] = default_value
                
        except Exception as e:
            pass
    
    def load_default_parameter(self, param_key: str):
        try:
            default_values = {
                'ZeroTrackRange': '50',
                'ZeroTrackTime': '100',
                'ZeroClearRange': '5', 
                'StabilityRange': '10',
                'StabilityTime': '2000',
                'FilterLevelA': '3',
                'FilterLevelB': '5',
                'MinDivision': '1',
                'MaxCapacity': '50000'
            }
            
            if param_key in default_values:
                default_value = default_values[param_key]
                self.update_parameter_display(param_key, default_value)
                self.parameter_data[param_key] = default_value
                
        except Exception as e:
            pass
    
    def on_parameter_changed(self, param_key: str, input_value: str):
        try:
            config = self.parameter_configs[param_key]
            
            if not input_value.strip():
                return
            
            try:
                if config['type'] == 'decimal':
                    value = float(input_value)
                else:
                    value = int(input_value)
            except ValueError:
                messagebox.showerror("参数错误", f"{config['label']}输入格式错误")
                return
            
            if config['type'] == 'decimal':
                formatted_value = f"{value:.{config['decimals']}f}"
            else:
                formatted_value = str(int(value))
            
            self.update_parameter_display(param_key, formatted_value)
            self.parameter_data[param_key] = formatted_value
            
        except Exception as e:
            messagebox.showerror("参数错误", f"处理参数修改时发生错误: {e}")
    
    def save_all_parameters(self):
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                messagebox.showerror("连接错误", "PLC未连接，无法保存参数")
                return False
            
            for param_key in self.parameter_configs.keys():
                if param_key in self.parameter_entries:
                    entry = self.parameter_entries[param_key]
                    self.on_parameter_changed(param_key, entry.get())
            
            success_count = 0
            failed_params = []
            
            for param_key, value_str in self.parameter_data.items():
                try:
                    success = self.save_parameter(param_key, value_str)
                    if success:
                        success_count += 1
                    else:
                        failed_params.append(param_key)
                except Exception as e:
                    failed_params.append(param_key)
            
            total_params = len(self.parameter_configs)
            if success_count == total_params:
                messagebox.showinfo("保存成功", f"所有系统参数已成功保存到PLC")
                return True
            else:
                failed_names = [self.parameter_configs[pk]['label'] for pk in failed_params]
                messagebox.showwarning("保存部分失败", 
                                     f"成功保存 {success_count}/{total_params} 个参数\n\n"
                                     f"失败的参数：{', '.join(failed_names)}")
                return False
                
        except Exception as e:
            messagebox.showerror("保存异常", f"保存系统参数时发生错误: {e}")
            return False
    
    def save_parameter(self, param_key: str, value_str: str) -> bool:
        try:
            config = self.parameter_configs[param_key]
            
            if config['type'] == 'decimal':
                value = float(value_str)
                plc_value = int(value * 10)
            else:
                plc_value = int(float(value_str))
            
            address = get_traditional_system_address(param_key)
            
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def execute_system_command(self, command_key: str):
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                messagebox.showerror("连接错误", "PLC未连接，无法执行系统命令")
                return
            
            config = self.control_configs[command_key]
            command_name = config['label']
            
            if command_key == 'SystemSave':
                result = messagebox.askyesno("确认保存", "确定要保存所有系统参数吗？")
                if result:
                    param_saved = self.save_all_parameters()
                    if param_saved:
                        self.send_system_pulse_command(command_key, command_name)
                return
            
            result = messagebox.askyesno("确认操作", f"确定要执行'{command_name}'命令吗？")
            if result:
                self.send_system_pulse_command(command_key, command_name)
                
        except Exception as e:
            messagebox.showerror("命令执行异常", f"执行系统命令时发生错误: {e}")
    
    def send_system_pulse_command(self, command_key: str, command_name: str):
        try:
            address = get_traditional_system_control_address(command_key)
            
            if command_key in self.control_buttons:
                btn = self.control_buttons[command_key]
                original_color = btn.cget('bg')
                btn.configure(bg='#00aa00')
                self.root.after(200, lambda: btn.configure(bg=original_color))
            
            success = self.send_pulse_command(address)
            
            if success:
                messagebox.showinfo("命令成功", f"'{command_name}'命令已发送")
                
                if command_key in ['FeedDataInit', 'ModuleInit', 'ModuleDataRead']:
                    self.root.after(200, self.refresh_parameters_after_command)
                    
            else:
                messagebox.showerror("命令失败", f"'{command_name}'命令发送失败")
                
        except Exception as e:
            messagebox.showerror("命令异常", f"发送'{command_name}'命令时发生错误: {e}")
    
    def send_pulse_command(self, address: int, pulse_duration: int = 100) -> bool:
        try:
            success1 = self.modbus_client.write_coil(address, True)
            if success1:
                self.root.after(pulse_duration, lambda: self.modbus_client.write_coil(address, False))
                return True
            else:
                return False
        except Exception as e:
            return False
    
    def go_back_to_menu(self):
        try:
            self.cleanup()
            self.parent.show_menu_interface()
        except Exception as e:
            pass
    
    def cleanup(self):
        try:
            self.is_showing = False
            
            self.parameter_entries.clear()
            self.control_buttons.clear()
            self.parameter_data.clear()
            
        except Exception as e:
            pass

    def refresh_parameters_after_command(self):
        try:
            self.load_all_parameters()
        except Exception as e:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    root.title("系统设置界面测试")
    
    class MockParent:
        def __init__(self, root):
            self.root = root
            self.main_content_frame = tk.Frame(root, bg='#ffffff')
            self.main_content_frame.pack(fill=tk.BOTH, expand=True)
            
        def get_main_root(self):
            return self.root
            
        def get_main_content_frame(self):
            return self.main_content_frame
            
        def clear_main_content(self):
            for widget in self.main_content_frame.winfo_children():
                widget.destroy()
                
        def show_menu_interface(self):
            pass
    
    mock_parent = MockParent(root)
    
    system_interface = SystemSettingInterface(None, mock_parent)
    
    system_interface.show_interface()
    
    root.mainloop()