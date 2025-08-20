"""
手动界面模块

作者：L
创建日期：2025-08-06
"""
import tkinter as tk
from tkinter import messagebox
import tkinter.font as font
import time
from typing import Optional, Dict, Any

try:
    from traditional_plc_addresses import (
        get_traditional_control_address,
        get_traditional_global_address,
        get_traditional_disable_address
    )
except ImportError as e:
    pass


class ManualModeInterface:
    
    def __init__(self, modbus_client, parent_interface):
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        self.main_content_frame = parent_interface.get_main_content_frame()
        
        self.disable_buttons = {}
        self.clean_buttons = {}
        self.discharge_buttons = {}
        self.global_buttons = {}
        
        self.bucket_disabled = {}
        self.bucket_cleaning = {}
        self.global_cleaning = False
        
        for i in range(1, 7):
            self.bucket_disabled[i] = False
            self.bucket_cleaning[i] = False
        
        self.setup_fonts()
    
    def setup_fonts(self):
        self.title_font = font.Font(family="Microsoft YaHei", size=56, weight="bold")
        self.row_label_font = font.Font(family="Microsoft YaHei", size=48, weight="bold")
        self.bucket_button_font = font.Font(family="Arial", size=54, weight="bold")
        self.global_button_font = font.Font(family="Microsoft YaHei", size=36, weight="bold")
        self.home_button_font = font.Font(family="Microsoft YaHei", size=28, weight="bold")
    
    def show_interface(self):
        try:
            self.create_manual_interface()
            self.load_initial_states()
            self.start_data_refresh()
        except Exception as e:
            messagebox.showerror("错误", f"手动界面显示失败: {e}")
    
    def create_manual_interface(self):
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=0, minsize=140)
        self.main_content_frame.grid_rowconfigure(1, weight=1, minsize=550)
        self.main_content_frame.grid_rowconfigure(2, weight=0, minsize=110)
        
        self.create_header_area()
        self.create_control_area()
        self.create_global_control_area()
    
    def create_header_area(self):
        header_frame = tk.Frame(self.main_content_frame, bg='#ffffff', height=120)
        header_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(40, 20))
        header_frame.grid_propagate(False)
        
        title_label = tk.Label(header_frame, text="手动画面",
                              font=self.title_font, bg='#ffffff', fg='#333333')
        title_label.place(relx=0.5, rely=0.5, anchor='center')
        
        home_button = tk.Button(header_frame, text="主页",
                               font=self.home_button_font,
                               bg='#e0e0e0', fg='#333333',
                               relief='solid', bd=2, padx=35, pady=12,
                               command=self.go_back_to_menu)
        home_button.place(relx=1.0, rely=0.5, anchor='e', x=-30)
    
    def create_control_area(self):
        control_frame = tk.Frame(self.main_content_frame, bg='#ffffff')
        control_frame.grid(row=1, column=0, sticky='nsew', padx=40, pady=(10, 15))
        
        control_frame.grid_columnconfigure(0, weight=0, minsize=180)
        control_frame.grid_columnconfigure(1, weight=1)
        
        for i in range(3):
            control_frame.grid_rowconfigure(i, weight=1, minsize=165)
        
        self.create_disable_row(control_frame, 0)
        self.create_clean_row(control_frame, 1)
        self.create_discharge_row(control_frame, 2)
    
    def create_disable_row(self, parent, row):
        label_frame = tk.Frame(parent, bg='#1e90ff', width=180, height=125)
        label_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 25), pady=10)
        label_frame.grid_propagate(False)
        
        label = tk.Label(label_frame, text="禁用",
                        font=self.row_label_font, bg='#1e90ff', fg='white')
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.grid(row=row, column=1, sticky='nsew', pady=10)
        
        for i in range(6):
            buttons_frame.grid_columnconfigure(i, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)
        
        for bucket_id in range(1, 7):
            btn = tk.Button(buttons_frame, text=str(bucket_id),
                           font=self.bucket_button_font,
                           bg='#1e90ff', fg='white',
                           relief='solid', bd=3, width=5, height=2,
                           command=lambda bid=bucket_id: self.toggle_disable(bid))
            btn.grid(row=0, column=bucket_id-1, sticky='nsew', padx=15, pady=0)
            self.disable_buttons[bucket_id] = btn
    
    def create_clean_row(self, parent, row):
        label_frame = tk.Frame(parent, bg='#1e90ff', width=180, height=125)
        label_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 25), pady=10)
        label_frame.grid_propagate(False)
        
        label = tk.Label(label_frame, text="清料",
                        font=self.row_label_font, bg='#1e90ff', fg='white')
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.grid(row=row, column=1, sticky='nsew', pady=10)
        
        for i in range(6):
            buttons_frame.grid_columnconfigure(i, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)
        
        for bucket_id in range(1, 7):
            btn = tk.Button(buttons_frame, text=str(bucket_id),
                           font=self.bucket_button_font,
                           bg='#1e90ff', fg='white',
                           relief='solid', bd=3, width=5, height=2,
                           command=lambda bid=bucket_id: self.toggle_clean(bid))
            btn.grid(row=0, column=bucket_id-1, sticky='nsew', padx=15, pady=0)
            self.clean_buttons[bucket_id] = btn
    
    def create_discharge_row(self, parent, row):
        label_frame = tk.Frame(parent, bg='#1e90ff', width=180, height=125)
        label_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 25), pady=10)
        label_frame.grid_propagate(False)
        
        label = tk.Label(label_frame, text="放料",
                        font=self.row_label_font, bg='#1e90ff', fg='white')
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.grid(row=row, column=1, sticky='nsew', pady=10)
        
        for i in range(6):
            buttons_frame.grid_columnconfigure(i, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)
        
        for bucket_id in range(1, 7):
            btn = tk.Button(buttons_frame, text=str(bucket_id),
                           font=self.bucket_button_font,
                           bg='#1e90ff', fg='white',
                           relief='solid', bd=3, width=5, height=2,
                           command=lambda bid=bucket_id: self.discharge_bucket(bid))
            btn.grid(row=0, column=bucket_id-1, sticky='nsew', padx=15, pady=0)
            self.discharge_buttons[bucket_id] = btn
    
    def create_global_control_area(self):
        global_frame = tk.Frame(self.main_content_frame, bg='#ffffff', height=110)
        global_frame.grid(row=2, column=0, sticky='ew', padx=40, pady=(10, 30))
        global_frame.grid_propagate(False)
        
        global_frame.grid_columnconfigure(0, weight=1)
        global_frame.grid_columnconfigure(1, weight=0)
        global_frame.grid_columnconfigure(2, weight=0)
        global_frame.grid_columnconfigure(3, weight=1)
        global_frame.grid_rowconfigure(0, weight=1)
        
        global_discharge_btn = tk.Button(global_frame, text="总放料",
                                        font=self.global_button_font,
                                        bg='#1e90ff', fg='white',
                                        relief='solid', bd=2,
                                        width=10, height=2,
                                        command=self.global_discharge)
        global_discharge_btn.grid(row=0, column=1, sticky='', padx=25)
        self.global_buttons['discharge'] = global_discharge_btn
        
        global_clean_btn = tk.Button(global_frame, text="总清料",
                                    font=self.global_button_font,
                                    bg='#1e90ff', fg='white',
                                    relief='solid', bd=2,
                                    width=10, height=2,
                                    command=self.global_clean)
        global_clean_btn.grid(row=0, column=2, sticky='', padx=25)
        self.global_buttons['clean'] = global_clean_btn
    
    def toggle_disable(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            success = self.parent.shared_toggle_bucket_disable(bucket_id)
            
            if success:
                self.bucket_disabled[bucket_id] = not self.bucket_disabled[bucket_id]
                self.update_disable_button_display(bucket_id)
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}禁用状态切换失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}禁用操作异常: {e}")
    
    def toggle_clean(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            success = self.parent.shared_toggle_bucket_clean(bucket_id)
            
            if success:
                self.bucket_cleaning[bucket_id] = not self.bucket_cleaning[bucket_id]
                self.update_clean_button_display(bucket_id)
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}清料状态切换失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}清料操作异常: {e}")
    
    def discharge_bucket(self, bucket_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            success = self.parent.shared_send_bucket_pulse_command(bucket_id, "Discharge")
            
            if success:
                self.provide_discharge_feedback(bucket_id)
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}放料操作失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}放料操作异常: {e}")
    
    def global_discharge(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            success = self.parent.shared_send_global_pulse_command("GlobalDischarge")
            
            if success:
                self.provide_global_feedback('discharge')
            else:
                messagebox.showerror("错误", "总放料操作失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"总放料操作异常: {e}")
    
    def global_clean(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            global_clean_addr = get_traditional_global_address('GlobalClean')
            
            new_state = not self.global_cleaning
            success = self.modbus_client.write_coil(global_clean_addr, new_state)
            
            if success:
                self.global_cleaning = new_state
                self.update_global_clean_button_display()
            else:
                messagebox.showerror("错误", "总清料状态切换失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"总清料操作异常: {e}")
    
    def update_disable_button_display(self, bucket_id: int):
        if bucket_id in self.disable_buttons:
            btn = self.disable_buttons[bucket_id]
            if self.bucket_disabled[bucket_id]:
                btn.configure(bg='#ff4444', fg='white')
            else:
                btn.configure(bg='#1e90ff', fg='white')
    
    def update_clean_button_display(self, bucket_id: int):
        if bucket_id in self.clean_buttons:
            btn = self.clean_buttons[bucket_id]
            if self.bucket_cleaning[bucket_id]:
                btn.configure(bg='#ff4444', fg='white')
            else:
                btn.configure(bg='#1e90ff', fg='white')
    
    def provide_discharge_feedback(self, bucket_id: int):
        if bucket_id in self.discharge_buttons:
            btn = self.discharge_buttons[bucket_id]
            original_bg = btn.cget('bg')
            
            btn.configure(bg='#ff6b6b')
            self.root.after(500, lambda: btn.configure(bg=original_bg))
    
    def provide_global_feedback(self, action: str):
        if action in self.global_buttons:
            btn = self.global_buttons[action]
            original_bg = btn.cget('bg')
            
            btn.configure(bg='#ff6b6b')
            duration = 1500 if action == 'discharge' else 500
            self.root.after(duration, lambda: btn.configure(bg=original_bg))
    
    def start_data_refresh(self):
        if self.modbus_client and self.modbus_client.is_connected:
            self.parent.shared_start_data_refresh(self.update_manual_data)
    
    def stop_data_refresh(self):
        self.parent.shared_stop_data_refresh()
    
    def update_manual_data(self):
        try:
            self.update_disable_states()
            self.update_clean_states()
            self.update_global_clean_state()
            
        except Exception as e:
            pass
    
    def update_disable_states(self):
        try:
            for bucket_id in range(1, 7):
                disable_addr = get_traditional_disable_address(bucket_id)
                state_data = self.modbus_client.read_coils(disable_addr, 1)
                
                if state_data and len(state_data) > 0:
                    plc_disabled = state_data[0]
                    
                    if self.bucket_disabled[bucket_id] != plc_disabled:
                        self.bucket_disabled[bucket_id] = plc_disabled
                        self.update_disable_button_display(bucket_id)
                        
        except Exception as e:
            pass
    
    def update_clean_states(self):
        try:
            for bucket_id in range(1, 7):
                clean_addr = get_traditional_control_address(bucket_id, 'Clean')
                state_data = self.modbus_client.read_coils(clean_addr, 1)
                
                if state_data and len(state_data) > 0:
                    plc_cleaning = state_data[0]
                    
                    if self.bucket_cleaning[bucket_id] != plc_cleaning:
                        self.bucket_cleaning[bucket_id] = plc_cleaning
                        self.update_clean_button_display(bucket_id)
                        
        except Exception as e:
            pass
    
    def load_initial_states(self):
        try:
            self.update_disable_states()
            self.update_clean_states()
            self.update_global_clean_state()

            for bucket_id in range(1, 7):
                self.update_disable_button_display(bucket_id)
                self.update_clean_button_display(bucket_id)
            self.update_global_clean_button_display()
            
        except Exception as e:
            pass
    
    def go_back_to_menu(self):
        try:
            self.cleanup()
            self.parent.show_menu_interface()
        except Exception as e:
            messagebox.showerror("错误", f"返回主菜单失败: {e}")

    def update_global_clean_button_display(self):
        if 'clean' in self.global_buttons:
            btn = self.global_buttons['clean']
            if self.global_cleaning:
                btn.configure(bg='#ff4444', fg='white')
            else:
                btn.configure(bg='#1e90ff', fg='white')

    def update_global_clean_state(self):
        try:
            global_clean_addr = get_traditional_global_address('GlobalClean')
            state_data = self.modbus_client.read_coils(global_clean_addr, 1)
            
            if state_data and len(state_data) > 0:
                plc_global_cleaning = state_data[0]
                
                if self.global_cleaning != plc_global_cleaning:
                    self.global_cleaning = plc_global_cleaning
                    self.update_global_clean_button_display()
                    
        except Exception as e:
            pass
    
    def cleanup(self):
        try:
            self.stop_data_refresh()
            
            self.disable_buttons.clear()
            self.clean_buttons.clear()
            self.discharge_buttons.clear()
            self.global_buttons.clear()
            
        except Exception as e:
            pass


if __name__ == "__main__":
    pass