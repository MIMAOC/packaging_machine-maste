"""
重量校准界面模块

作者：L
创建日期：2025-08-06
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
        get_traditional_disable_address,
        get_traditional_calibration_address
    )
    from modbus_client import ModbusClient
except ImportError as e:
    pass


class WeightCalibrationInterface:
    def __init__(self, modbus_client: Optional[ModbusClient] = None, parent_interface = None):
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        self.main_content_frame = parent_interface.get_main_content_frame()
        
        self.weight_labels = {}
        self.standard_weight_entry = None
        self.calibration_buttons = {}

        self.setup_fonts()
        
        self.calibration_in_progress = {}
        for i in range(1, 7):
            self.calibration_in_progress[i] = False
    
    def setup_fonts(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if screen_width >= 2560:
            window_width = int(screen_width * 0.75)
            window_height = int(screen_height * 0.8)
            font_scale = 1.2
        elif screen_width >= 1920:
            window_width = int(screen_width * 0.8)
            window_height = int(screen_height * 0.85)
            font_scale = 1.0
        else:
            window_width = int(screen_width * 0.9)
            window_height = int(screen_height * 0.9)
            font_scale = 0.8
        
        self.root.geometry(f"{window_width}x{window_height}")
        
        base_instruction = int(42 * font_scale)
        base_standard = int(32 * font_scale)
        base_number = int(32 * font_scale)
        base_display = int(32 * font_scale)
        base_button = int(28 * font_scale)
        
        self.instruction_font = font.Font(family="Microsoft YaHei", size=base_instruction, weight="bold")
        self.standard_weight_font = font.Font(family="Arial", size=base_standard, weight="bold")
        self.hopper_number_font = font.Font(family="Arial", size=base_number, weight="bold")
        self.weight_display_font = font.Font(family="Arial", size=base_display, weight="bold")
        self.button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
        self.return_button_font = font.Font(family="Microsoft YaHei", size=base_button, weight="bold")
        
        self.font_scale = font_scale
    
    def show_interface(self):
        if hasattr(self.parent, 'shared_clear_main_content'):
            self.parent.shared_clear_main_content()
        
        self.create_calibration_interface()
        
        self.load_standard_weight()

        self.start_data_refresh()
    
    def create_calibration_interface(self):
        base_padding = int(40 * self.font_scale)
        content_padding = int(25 * self.font_scale)
        
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=0)
        self.main_content_frame.grid_rowconfigure(1, weight=1)
        self.main_content_frame.grid_rowconfigure(2, weight=0)
        
        self.create_instruction_area(base_padding)
        self.create_hoppers_area(base_padding, content_padding)
        self.create_return_button(base_padding)
    
    def create_instruction_area(self, base_padding):
        content_padding = int(base_padding * 0.6)
        
        instruction_frame = tk.Frame(self.main_content_frame, bg='#e8e8e8')
        instruction_frame.grid(row=0, column=0, sticky='nsew', padx=base_padding, pady=(content_padding, 0))
        instruction_frame.grid_columnconfigure(0, weight=1)
        
        line1 = tk.Label(instruction_frame, 
                        text="提示：请先清空称斗并进行零点标定，然后在称斗内放入",
                        font=self.instruction_font, bg='#e8e8e8', fg='#333333')
        line1.grid(row=0, column=0, pady=(content_padding//2, content_padding//3))
        
        line2_frame = tk.Frame(instruction_frame, bg='#e8e8e8')
        line2_frame.grid(row=1, column=0, pady=(0, content_padding//2))
        
        entry_width = max(8, int(10 * self.font_scale))
        self.standard_weight_entry = tk.Entry(line2_frame,
                                            font=self.standard_weight_font,
                                            width=entry_width, justify='center',
                                            relief='solid', bd=3,
                                            highlightthickness=2)
        self.standard_weight_entry.pack(side='left', padx=(0, content_padding))
        self.standard_weight_entry.insert(0, "000.0")
        
        self.standard_weight_entry.bind('<Button-1>', lambda e: self.standard_weight_entry.focus_force(), add=True)

        self.standard_weight_entry.bind('<KeyRelease>', self.validate_standard_weight)
        self.standard_weight_entry.bind('<FocusOut>', self.save_standard_weight)
        self.standard_weight_entry.bind('<Return>', self.save_standard_weight)
        
        tk.Label(line2_frame, text="g标准砝码按校准键确认。",
                font=self.instruction_font, bg='#e8e8e8', fg='#333333').pack(side='left')
    
    def create_hoppers_area(self, base_padding, content_padding):
        main_frame = tk.Frame(self.main_content_frame, bg='#e8e8e8')
        main_frame.grid(row=1, column=0, sticky='nsew', padx=base_padding, pady=(content_padding, content_padding))
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)
        main_frame.grid_rowconfigure(2, weight=1)
        
        hoppers_container = tk.Frame(main_frame, bg='#e8e8e8')
        hoppers_container.grid(row=1, column=0, sticky='ew')
        
        for i in range(6):
            hoppers_container.grid_columnconfigure(i, weight=1)
        hoppers_container.grid_rowconfigure(0, weight=1)
        
        for hopper_id in range(1, 7):
            self.create_single_hopper(hoppers_container, hopper_id, hopper_id - 1, content_padding)
    
    def create_single_hopper(self, parent, hopper_id: int, col: int, content_padding: int):
        hopper_padding = max(6, int(content_padding * 0.3))
        element_spacing = max(40, int(content_padding * 1.0))
        
        hopper_frame = tk.Frame(parent, bg='#e8e8e8')
        hopper_frame.grid(row=0, column=col, sticky='nsew', padx=hopper_padding, pady=content_padding)
        hopper_frame.grid_columnconfigure(0, weight=1)
        
        hopper_frame.grid_rowconfigure(0, weight=2)
        hopper_frame.grid_rowconfigure(1, weight=2)
        hopper_frame.grid_rowconfigure(2, weight=2)
        hopper_frame.grid_rowconfigure(3, weight=1)
        
        number_frame = tk.Frame(hopper_frame, bg='#e8e8e8')
        number_frame.grid(row=0, column=0, sticky='', pady=(0, element_spacing))
        
        number_width = max(2, int(3 * self.font_scale))
        weight_width = max(8, int(12 * self.font_scale))
        button_width = max(6, int(8 * self.font_scale))
        
        number_label = tk.Label(number_frame, text=str(hopper_id),
                               font=self.hopper_number_font,
                               bg='white', fg='#333333',
                               width=number_width, height=1,
                               relief='solid', bd=4)
        number_label.pack()
        
        weight_label = tk.Label(hopper_frame, text="-0000.0",
                               font=self.weight_display_font,
                               bg='white', fg='#333333',
                               width=weight_width, height=1,
                               relief='solid', bd=3)
        weight_label.grid(row=1, column=0, sticky='', pady=(0, element_spacing))
        self.weight_labels[hopper_id] = weight_label
        
        zero_btn = tk.Button(hopper_frame, text="零点标定",
                            font=self.button_font,
                            bg='#1e90ff', fg='white',
                            width=button_width, height=1,
                            relief='solid', bd=2,
                            command=lambda: self.zero_calibration(hopper_id))
        zero_btn.grid(row=2, column=0, sticky='', pady=(0, element_spacing))
        self.calibration_buttons[f'{hopper_id}_zero'] = zero_btn
        
        weight_btn = tk.Button(hopper_frame, text="校 准",
                              font=self.button_font,
                              bg='#1e90ff', fg='white',
                              width=button_width, height=1,
                              relief='solid', bd=2,
                              command=lambda: self.weight_calibration(hopper_id))
        weight_btn.grid(row=3, column=0, sticky='')
        self.calibration_buttons[f'{hopper_id}_weight'] = weight_btn
        
        def show_address_info(event):
            weight_addr = f"D{700 + (hopper_id - 1) * 2}"
            zero_addr = f"M{hopper_id}"
            calib_addr = f"M{hopper_id + 6}"
            tooltip_text = f"料斗{hopper_id}\n重量: {weight_addr}\n零点: {zero_addr}\n校准: {calib_addr}"
        
        hopper_frame.bind("<Enter>", show_address_info)
    
    def create_return_button(self, base_padding):
        content_padding = int(base_padding * 0.5)
        
        bottom_frame = tk.Frame(self.main_content_frame, bg='#e8e8e8')
        bottom_frame.grid(row=2, column=0, sticky='nsew', padx=base_padding, pady=(0, content_padding))
        
        button_width = max(6, int(8 * self.font_scale))
        
        return_btn = tk.Button(bottom_frame, text="返 回",
                              font=self.return_button_font,
                              bg='#666666', fg='white',
                              width=button_width, height=1,
                              relief='solid', bd=3,
                              command=self.go_back_to_menu)
        return_btn.pack(side='right', pady=content_padding)
    
    def zero_calibration(self, hopper_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法执行零点标定")
            return
        
        if self.calibration_in_progress.get(hopper_id, False):
            messagebox.showwarning("警告", f"料斗{hopper_id}校准操作进行中，请等待...")
            return
        
        try:
            self.calibration_in_progress[hopper_id] = True
            self.update_calibration_status(hopper_id, "零点标定中...", True)
            
            success = self.send_calibration_pulse_command(hopper_id, "ZeroCalibration")
            
            if success:
                self.root.after(1000, lambda: self.finish_calibration(hopper_id, "零点标定完成"))
            else:
                messagebox.showerror("错误", f"料斗{hopper_id}零点标定命令发送失败")
                self.calibration_in_progress[hopper_id] = False
                self.update_calibration_status(hopper_id, "标定失败", False)
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{hopper_id}零点标定异常: {str(e)}")
            self.calibration_in_progress[hopper_id] = False
            self.update_calibration_status(hopper_id, "标定异常", False)
    
    def weight_calibration(self, hopper_id: int):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法执行重量校准")
            return
        
        if self.calibration_in_progress.get(hopper_id, False):
            messagebox.showwarning("警告", f"料斗{hopper_id}校准操作进行中，请等待...")
            return
        
        try:
            standard_weight_str = self.standard_weight_entry.get().strip()
            standard_weight = float(standard_weight_str)
            
            if standard_weight <= 0:
                messagebox.showerror("错误", "请输入有效的标准重量（大于0）")
                return
                
        except ValueError:
            messagebox.showerror("错误", f"标准重量格式错误: {standard_weight_str}")
            return
        
        try:
            self.calibration_in_progress[hopper_id] = True
            self.update_calibration_status(hopper_id, f"校准中({standard_weight}g)...", True)
            
            success = self.send_calibration_pulse_command(hopper_id, "WeightCalibration")
            
            if success:
                self.root.after(1500, lambda: self.finish_calibration(hopper_id, "重量校准完成"))
            else:
                messagebox.showerror("错误", f"料斗{hopper_id}重量校准命令发送失败")
                self.calibration_in_progress[hopper_id] = False
                self.update_calibration_status(hopper_id, "校准失败", False)
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{hopper_id}重量校准异常: {str(e)}")
            self.calibration_in_progress[hopper_id] = False
            self.update_calibration_status(hopper_id, "校准异常", False)
    

    def send_calibration_pulse_command(self, hopper_id: int, command_type: str) -> bool:
        try:
            coil_address = get_traditional_calibration_address(hopper_id, command_type)
            
            if hasattr(self.parent, 'shared_send_pulse_command'):
                return self.parent.shared_send_pulse_command(coil_address, 1000)
            else:
                return self.send_pulse_command(coil_address, 100)
                
        except Exception as e:
            return False
    
    def send_pulse_command(self, address: int, pulse_duration: int = 1000) -> bool:
        try:
            success = self.modbus_client.write_coil(address, True)
            if success:
                self.root.after(pulse_duration, lambda: self.modbus_client.write_coil(address, False))
                return True
            else:
                return False
        except Exception as e:
            return False
    
    def update_calibration_status(self, hopper_id: int, message: str, is_active: bool):
        pass
    
    def finish_calibration(self, hopper_id: int, message: str):
        self.calibration_in_progress[hopper_id] = False
        self.update_calibration_status(hopper_id, message, False)
        
        self.show_temporary_message(f"料斗{hopper_id}{message}")
    
    def show_temporary_message(self, message: str, duration: int = 2000):
        msg_label = tk.Label(self.main_content_frame, text=message,
                            font=('Microsoft YaHei', 24, 'bold'),
                            bg='#333333', fg='white',
                            padx=30, pady=15)
        msg_label.place(relx=0.5, rely=0.5, anchor='center')
        
        self.root.after(duration, msg_label.destroy)
    
    def validate_standard_weight(self, event=None):
        try:
            entry = event.widget
            value = entry.get()
            
            if value and not value.replace('.', '').isdigit():
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                parts = cleaned.split('.')
                if len(parts) > 2:
                    cleaned = parts[0] + '.' + ''.join(parts[1:])
                
                entry.delete(0, tk.END)
                entry.insert(0, cleaned)
                
        except Exception as e:
            pass
    
    def start_data_refresh(self):
        if hasattr(self.parent, 'shared_start_data_refresh'):
            self.parent.shared_start_data_refresh(self.update_calibration_data)
    
    def stop_data_refresh(self):
        if hasattr(self.parent, 'shared_stop_data_refresh'):
            self.parent.shared_stop_data_refresh()
    
    def update_calibration_data(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            for hopper_id in range(1, 7):
                if hopper_id in self.weight_labels:
                    try:
                        weight_address = 700 + (hopper_id - 1) * 2
                        
                        try:
                            weight_address = get_traditional_weight_address(hopper_id)
                        except:
                            pass
                        
                        weight_data = self.modbus_client.read_holding_registers(weight_address, 1)
                        if weight_data:
                            raw_value = weight_data[0]
                            if raw_value > 32767:
                                signed_value = raw_value - 65536
                            else:
                                signed_value = raw_value
                            
                            weight_value = signed_value / 10.0
                            weight_text = f"{weight_value:.1f}"
                            self.weight_labels[hopper_id].configure(text=weight_text)
                            
                            if weight_value > 0:
                                self.weight_labels[hopper_id].configure(fg='#00aa00')
                            elif weight_value < 0:
                                self.weight_labels[hopper_id].configure(fg='#ff4444')
                            else:
                                self.weight_labels[hopper_id].configure(fg='#333333')
                        
                    except Exception as e:
                        pass
            
        except Exception as e:
            pass
    
    def go_back_to_menu(self):
        try:
            self.cleanup()
            
            if hasattr(self.parent, 'show_menu_interface'):
                self.parent.show_menu_interface()
            else:
                pass
                
        except Exception as e:
            messagebox.showerror("错误", f"返回主菜单时出错: {str(e)}")

    def load_standard_weight(self):
        if not self.modbus_client or not self.modbus_client.is_connected:
            return
        
        try:
            from traditional_plc_addresses import get_traditional_system_address
            address = get_traditional_system_address('StandardWeight')
            data = self.modbus_client.read_holding_registers(address, 1)
            
            if data:
                standard_weight = data[0] / 10.0
                self.standard_weight_entry.delete(0, tk.END)
                self.standard_weight_entry.insert(0, f"{standard_weight:.1f}")
            else:
                pass
                
        except Exception as e:
            pass

    def save_standard_weight(self, event=None):
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接，无法保存标准重量")
            return
        
        try:
            standard_weight_str = self.standard_weight_entry.get().strip()
            standard_weight = float(standard_weight_str)
            
            if standard_weight < 0:
                messagebox.showerror("错误", "标准重量不能为负数")
                return
            
            plc_value = int(standard_weight * 10)
            
            from traditional_plc_addresses import get_traditional_system_address
            address = get_traditional_system_address('StandardWeight')
            success = self.modbus_client.write_holding_register(address, plc_value)
            
            if not success:
                messagebox.showerror("错误", "保存标准重量失败")
                
        except ValueError:
            messagebox.showerror("错误", f"标准重量格式错误: {standard_weight_str}")
        except Exception as e:
            messagebox.showerror("错误", f"保存标准重量异常: {e}")
    
    def cleanup(self):
        try:
            self.stop_data_refresh()
            
            self.weight_labels.clear()
            self.calibration_buttons.clear()
            self.standard_weight_entry = None
            
            for hopper_id in range(1, 7):
                self.calibration_in_progress[hopper_id] = False
            
        except Exception as e:
            pass


if __name__ == "__main__":
    test_root = tk.Tk()
    test_root.title("重量校准界面测试 - 自适应版本")
    test_root.configure(bg='#e8e8e8')
    
    test_root.minsize(1000, 700)
    
    test_frame = tk.Frame(test_root, bg='#e8e8e8')
    test_frame.pack(fill='both', expand=True)
    
    class MockParentInterface:
        def __init__(self, root):
            self.root = root
            self.main_content_frame = test_frame
        
        def get_main_root(self):
            return self.root
            
        def get_main_content_frame(self):
            return self.main_content_frame
            
        def shared_clear_main_content(self):
            for widget in self.main_content_frame.winfo_children():
                widget.destroy()
        
        def shared_start_data_refresh(self, callback):
            pass
        
        def shared_stop_data_refresh(self):
            pass
            
        def shared_send_pulse_command(self, address, duration):
            return True
        
        def show_menu_interface(self):
            pass
    
    class MockModbusClient:
        def __init__(self):
            self.is_connected = True
            
        def read_holding_registers(self, address, count):
            import random
            return [random.randint(-100, 1000)]
        
        def write_coil(self, address, value):
            return True
    
    parent = MockParentInterface(test_root)
    modbus_client = MockModbusClient()
    
    calibration_interface = WeightCalibrationInterface(modbus_client, parent)
    calibration_interface.show_interface()
    
    test_root.mainloop()