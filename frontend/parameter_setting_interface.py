"""
参数设置界面模块

作者：L
创建日期：2025-08-15
"""
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
import time
import threading
from typing import Optional, Dict, Any

try:
    from traditional_plc_addresses import get_traditional_system_address
    from modbus_client import ModbusClient
except ImportError as e:
    class ModbusClient:
        pass


class ParameterSettingInterface:
    
    def __init__(self, modbus_client: Optional[ModbusClient], parent_interface):
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        
        self.main_content_frame = None
        self.parameter_entries = {}
        self.parameter_labels = {}
        self.control_buttons = {}
        
        self.refresh_timer = None
        
        self.parameter_data = {
            'CleanSpeed': 0,
            'JogTime': 0.0,
            'DebounceTime': 0.0,
            'JogInterval': 0.0,
            'DischargeTime': 0.0,
            'AllowableError': 0.0,
            'DoorDelay': 0.0
        }
        
        self.parameter_configs = {
            'CleanSpeed': {
                'name': '清料速度',
                'type': 'integer',
                'min': 0,
                'max': 100,
                'decimals': 0,
                'unit': ''
            },
            'JogTime': {
                'name': '点动时间',
                'type': 'decimal', 
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'DebounceTime': {
                'name': '消抖时间',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9, 
                'decimals': 1,
                'unit': ''
            },
            'JogInterval': {
                'name': '点动间隔',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'DischargeTime': {
                'name': '放料时间',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'AllowableError': {
                'name': '允许误差',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            },
            'DoorDelay': {
                'name': '关门延时',
                'type': 'decimal',
                'min': 0.0,
                'max': 999.9,
                'decimals': 1,
                'unit': ''
            }
        }
        
        self.setup_fonts()
    
    def setup_fonts(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if screen_width >= 2560:
            self.font_scale = 1.2
        elif screen_width >= 1920:
            self.font_scale = 1.0
        else:
            self.font_scale = 0.8
        
        base_title = int(56 * self.font_scale)
        base_label = int(38 * self.font_scale)
        base_entry = int(42 * self.font_scale)
        base_button = int(32 * self.font_scale)
        
        self.title_font = font.Font(family="Microsoft YaHei", size=base_title, weight="bold")
        self.label_font = font.Font(family="Microsoft YaHei", size=base_label, weight="normal")
        self.entry_font = font.Font(family="Arial", size=base_entry, weight="bold")
        self.button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
        
        self.entry_width = int(200 * self.font_scale)
        self.entry_height = int(50 * self.font_scale)
        self.button_width = int(180 * self.font_scale)
        self.button_height = int(60 * self.font_scale)
        
        self.base_padding = int(40 * self.font_scale)
        self.content_padding = int(25 * self.font_scale)
        self.element_spacing = max(30, int(self.content_padding * 1.2))
    
    def show_interface(self):
        self.create_parameter_interface()
        self.load_all_parameters()
        self.start_data_refresh()
    
    def create_parameter_interface(self):
        self.main_content_frame = self.parent.get_main_content_frame()
        
        try:
            for i in range(10):
                self.main_content_frame.grid_rowconfigure(i, weight=0, minsize=0)
                self.main_content_frame.grid_columnconfigure(i, weight=0, minsize=0)
            
            for child in self.main_content_frame.winfo_children():
                child.grid_forget()
                child.pack_forget()
                
        except Exception as e:
            pass
        
        main_frame = tk.Frame(self.main_content_frame, bg='#ffffff')
        main_frame.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        content_frame = tk.Frame(main_frame, bg='#ffffff')
        content_frame.grid(row=0, column=0, sticky='nsew', padx=self.base_padding, pady=(0, self.base_padding))
        content_frame.grid_rowconfigure(0, weight=0)
        content_frame.grid_rowconfigure(1, weight=1)
        content_frame.grid_rowconfigure(2, weight=0)
        content_frame.grid_columnconfigure(0, weight=1)
        
        self.create_title_area(content_frame)
        
        self.create_parameters_area(content_frame)
        
        self.create_control_area(content_frame)
    
    def create_title_area(self, parent):
        title_frame = tk.Frame(parent, bg='#4a90e2', height=int(120 * self.font_scale))
        title_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(0, self.content_padding))
        title_frame.grid_propagate(False)
        title_frame.grid_columnconfigure(0, weight=1)
        title_frame.grid_rowconfigure(0, weight=1)
        
        center_container = tk.Frame(title_frame, bg='#4a90e2')
        center_container.grid(row=0, column=0, sticky='')
        
        title_label = tk.Label(center_container, text="参数设置", 
                              font=self.title_font, bg='#4a90e2', fg='white')
        title_label.pack()
        
        home_button = tk.Button(title_frame, text="主页", 
                               font=self.button_font, bg='#e0e0e0', fg='#333333',
                               relief='solid', bd=2, cursor='hand2',
                               command=self.go_back_to_menu)
        home_button.place(relx=0.98, rely=0.5, anchor='e')
        self.control_buttons['home'] = home_button
    
    def create_parameters_area(self, parent):
        params_frame = tk.Frame(parent, bg='#ffffff')
        params_frame.grid(row=1, column=0, sticky='nsew', padx=0, pady=self.content_padding)
        params_frame.grid_columnconfigure(0, weight=1)
        params_frame.grid_columnconfigure(1, weight=1)
        params_frame.grid_rowconfigure(0, weight=1)
        
        left_frame = tk.Frame(params_frame, bg='#ffffff')
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, self.element_spacing))
        
        right_frame = tk.Frame(params_frame, bg='#ffffff')
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(self.element_spacing, 0))
        
        left_params = ['CleanSpeed', 'DebounceTime', 'DischargeTime', 'DoorDelay']
        right_params = ['JogTime', 'JogInterval', 'AllowableError', None]
        
        for i, param_key in enumerate(left_params):
            if param_key:
                self.create_parameter_row(left_frame, param_key, i)
        
        for i, param_key in enumerate(right_params):
            if param_key:
                self.create_parameter_row(right_frame, param_key, i)
    
    def create_parameter_row(self, parent, param_key: str, row: int):
        config = self.parameter_configs[param_key]
        
        row_frame = tk.Frame(parent, bg='#ffffff')
        row_frame.grid(row=row, column=0, sticky='ew', padx=0, pady=int(self.element_spacing * 0.5))
        row_frame.grid_columnconfigure(0, weight=0)
        row_frame.grid_columnconfigure(1, weight=1)
        row_frame.grid_rowconfigure(0, weight=1)
        
        label_text = f"{config['name']}:"
        param_label = tk.Label(row_frame, text=label_text,
                              font=self.label_font, bg='#ffffff', fg='#333333')
        param_label.grid(row=0, column=0, sticky='w', padx=(0, self.content_padding))
        self.parameter_labels[param_key] = param_label
        
        param_entry = tk.Entry(row_frame, font=self.entry_font, justify='center',
                              relief='solid', bd=3, fg='#0066ff', bg='white',
                              width=12, 
                              highlightthickness=2, highlightcolor='#4a90e2')
        param_entry.grid(row=0, column=1, sticky='w', padx=0, pady=8, ipady=8)
        param_entry.focus_set()
        
        param_entry.bind('<KeyRelease>', lambda e, key=param_key: self.validate_input(key, e.widget.get()))
        param_entry.bind('<FocusOut>', lambda e, key=param_key: self.format_parameter_value(key))
        param_entry.bind('<Return>', lambda e, key=param_key: self.format_parameter_value(key))
        
        self.parameter_entries[param_key] = param_entry
    
    def create_control_area(self, parent):
        control_frame = tk.Frame(parent, bg='#ffffff')
        control_frame.grid(row=2, column=0, sticky='ew', padx=0, pady=(self.content_padding, 0))
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=0)
        control_frame.grid_columnconfigure(2, weight=0)
        control_frame.grid_columnconfigure(3, weight=1)
        control_frame.grid_rowconfigure(0, weight=1)
        
        save_button = tk.Button(control_frame, text="保存", 
                               font=self.button_font, bg='#4a90e2', fg='white',
                               relief='solid', bd=2, cursor='hand2',
                               width=10, height=2,
                               command=self.save_all_parameters)
        save_button.grid(row=0, column=1, sticky='ns', padx=self.element_spacing)
        self.control_buttons['save'] = save_button
        
        return_button = tk.Button(control_frame, text="返回", 
                                 font=self.button_font, bg='#e0e0e0', fg='#333333',
                                 relief='solid', bd=2, cursor='hand2',
                                 width=10, height=2,
                                 command=self.go_back_to_menu)
        return_button.grid(row=0, column=2, sticky='ns', padx=self.element_spacing)
        self.control_buttons['return'] = return_button
    
    def load_all_parameters(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            self.load_default_parameters()
            return
        
        try:
            for param_key in self.parameter_configs:
                self.load_parameter(param_key)
        except Exception as e:
            messagebox.showerror("错误", f"加载参数失败: {e}")
            self.load_default_parameters()
    
    def load_parameter(self, param_key: str):
        try:
            address = get_traditional_system_address(param_key)
            
            data = self.modbus_client.read_holding_registers(address, 1)
            if data:
                config = self.parameter_configs[param_key]
                
                if config['type'] == 'decimal' and param_key in ['JogTime', 'DebounceTime', 'JogInterval', 'DischargeTime', 'DoorDelay', 'AllowableError']:
                    value = data[0] / 10.0
                else:
                    value = data[0]
                
                self.parameter_data[param_key] = value
                
                self.update_parameter_display(param_key, value)
                
        except Exception as e:
            config = self.parameter_configs[param_key]
            default_value = config['min']
            self.parameter_data[param_key] = default_value
            self.update_parameter_display(param_key, default_value)
    
    def load_default_parameters(self):
        for param_key, config in self.parameter_configs.items():
            default_value = config['min']
            self.parameter_data[param_key] = default_value
            self.update_parameter_display(param_key, default_value)
    
    def update_parameter_display(self, param_key: str, value):
        if param_key in self.parameter_entries:
            entry = self.parameter_entries[param_key]
            config = self.parameter_configs[param_key]
            
            if config['type'] == 'decimal':
                display_value = f"{value:.{config['decimals']}f}"
            else:
                display_value = f"{int(value):02d}"
            
            entry.delete(0, tk.END)
            entry.insert(0, display_value)
    
    def validate_input(self, param_key: str, input_value: str):
        if not input_value:
            return True
        
        try:
            config = self.parameter_configs[param_key]
            
            if config['type'] == 'decimal':
                value = float(input_value)
            else:
                value = int(input_value)
            
            if value < config['min'] or value > config['max']:
                return False
            
            return True
            
        except ValueError:
            return False
    
    def format_parameter_value(self, param_key: str):
        if param_key not in self.parameter_entries:
            return
        
        entry = self.parameter_entries[param_key]
        input_value = entry.get()
        
        if not input_value:
            return
        
        try:
            config = self.parameter_configs[param_key]
            
            if config['type'] == 'decimal':
                value = float(input_value)
            else:
                value = int(input_value)
            
            value = max(config['min'], min(config['max'], value))
            
            self.parameter_data[param_key] = value
            self.update_parameter_display(param_key, value)
            
        except ValueError:
            old_value = self.parameter_data.get(param_key, config['min'])
            self.update_parameter_display(param_key, old_value)
    
    def save_all_parameters(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存参数")
            return
        
        for param_key in self.parameter_configs:
            self.format_parameter_value(param_key)
        
        success_count = 0
        total_count = len(self.parameter_configs)
        
        try:
            for param_key, value in self.parameter_data.items():
                if self.save_parameter(param_key, value):
                    success_count += 1
            
            if success_count == total_count:
                messagebox.showinfo("成功", "所有参数保存成功！")
            else:
                messagebox.showwarning("警告", f"只有 {success_count}/{total_count} 个参数保存成功")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存参数时发生异常: {e}")
    
    def save_parameter(self, param_key: str, value) -> bool:
        try:
            address = get_traditional_system_address(param_key)
            
            config = self.parameter_configs[param_key]
            
            if config['type'] == 'decimal' and param_key in ['JogTime', 'DebounceTime', 'JogInterval', 'DischargeTime', 'DoorDelay', 'AllowableError']:
                plc_value = int(value * 10) if value < 100 else int(value)
            else:
                plc_value = int(value)
            
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if success:
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def start_data_refresh(self):
        pass
    
    def stop_data_refresh(self):
        if self.refresh_timer:
            self.root.after_cancel(self.refresh_timer)
            self.refresh_timer = None
    
    def update_parameters_data(self):
        try:
            for param_key in self.parameter_configs:
                self.load_parameter(param_key)
        except Exception as e:
            pass
        finally:
            self.refresh_timer = self.root.after(5000, self.update_parameters_data)
    
    def go_back_to_menu(self):
        self.cleanup()
        self.parent.show_menu_interface()
    
    def cleanup(self):
        try:
            self.stop_data_refresh()
            
            self.parameter_entries.clear()
            self.parameter_labels.clear()
            self.control_buttons.clear()
            
        except Exception as e:
            pass


if __name__ == "__main__":
    pass