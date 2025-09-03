"""
出厂设置界面

作者：C
创建日期：2025-08-05
"""

import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont

class ErrorThresholdConfig:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.lower_error = -0.2
            self.upper_error = 0.6
            self.initialized = True
    
    def update_thresholds(self, lower_error: float, upper_error: float):
        with self._lock:
            self.lower_error = lower_error
            self.upper_error = upper_error
    
    def get_thresholds(self) -> tuple:
        with self._lock:
            return self.lower_error, self.upper_error
        
error_config = ErrorThresholdConfig()

class FactorySettingsInterface:
    
    def __init__(self, parent=None, system_settings_window=None):
        self.system_settings_window = system_settings_window
        
        self.admin_password = "1234"
        
        self.default_lower_error = -0.2
        self.default_upper_error = 0.6
        self.min_lower_error = -0.2
        self.min_upper_error = 0.6
        self.min_error_diff = 0.8
        
        self._load_from_config_file()
        
        self.show_password_verification()
        
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
        
    def _load_from_config_file(self):
        try:
            import json
            import os
            
            config_file = os.path.join("config", "error_thresholds.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.current_lower_error = round(config_data.get("lower_error", self.default_lower_error), 1)
                self.current_upper_error = round(config_data.get("upper_error", self.default_upper_error), 1)
                
                global error_config
                error_config.update_thresholds(self.current_lower_error, self.current_upper_error)
                
            else:
                self.current_lower_error = round(self.default_lower_error, 1)
                self.current_upper_error = round(self.default_upper_error, 1)
                
        except Exception as e:
            self.current_lower_error = round(self.default_lower_error, 1)
            self.current_upper_error = round(self.default_upper_error, 1)
    
    def show_password_verification(self):
        self.password_window = tk.Toplevel()
        self.password_window.title("出厂设置")
        self.password_window.attributes('-fullscreen', True)
        self.password_window.state('zoomed')
        self.password_window.geometry("1920x1080")
        self.password_window.configure(bg='white')
        self.password_window.resizable(True, True)
        self.password_window.transient()
        self.password_window.grab_set()
        
        self.password_window.protocol("WM_DELETE_WINDOW", self.on_password_window_closing)
        
        self.setup_force_exit_mechanism(self.password_window)
        
        self.setup_fonts()
        
        self.create_password_widgets()
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=32, weight="bold")
        
        self.label_font = tkFont.Font(family="微软雅黑", size=20)
        
        self.entry_font = tkFont.Font(family="微软雅黑", size=18)
        
        self.button_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)
        
        self.value_font = tkFont.Font(family="微软雅黑", size=24, weight="bold")
        
        self.unit_font = tkFont.Font(family="微软雅黑", size=16)
    
    def create_password_widgets(self):
        main_frame = tk.Frame(self.password_window, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=120, pady=50)
        
        self.create_password_title_bar(main_frame)
        
        self.create_password_input_section(main_frame)
        
        self.create_footer_section(main_frame)
    
    def create_password_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="出厂设置", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_to_ai_mode)
        return_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 40))
    
    def create_password_input_section(self, parent):
        password_frame = tk.Frame(parent, bg='white')
        password_frame.pack(expand=True, fill='both')
        
        center_frame = tk.Frame(password_frame, bg='white')
        center_frame.pack(expand=True)
        
        prompt_label = tk.Label(center_frame, text="请输入管理员密码", 
                               font=self.label_font, bg='white', fg='#333333')
        prompt_label.pack(pady=(0, 50))
        
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(center_frame, textvariable=self.password_var,
                                 font=self.entry_font,
                                 width=30, show='*',
                                 relief='solid', bd=1,
                                 bg='white', fg='#333333')
        password_entry.pack(ipady=12, pady=(0, 80))
        
        self.setup_placeholder(password_entry, "请输入密码")
        password_entry.bind('<Button-1>', lambda e: password_entry.focus_force(), add=True)
        
        password_entry.focus()
        password_entry.bind('<Return>', lambda e: self.verify_password())
        
        confirm_btn = tk.Button(center_frame, text="确认", 
                               font=self.button_font,
                               bg='#e9ecef', fg='#333333',
                               relief='flat', bd=1,
                               padx=60, pady=18,
                               command=self.verify_password)
        confirm_btn.pack()
    
    def verify_password(self):
        entered_password = self.password_var.get()
        
        if entered_password == "请输入密码" or entered_password == "":
            messagebox.showwarning("密码错误", "请输入管理员密码！")
            return
        
        if entered_password == self.admin_password:
            self.password_window.destroy()
            self.show_settings_window()
        else:
            messagebox.showerror("密码错误", "管理员密码不正确，请重新输入！")
            self.password_var.set("")
    
    def show_settings_window(self):
        self.settings_window = tk.Toplevel()
        self.settings_window.title("出厂设置")
        self.settings_window.attributes('-fullscreen', True)
        self.settings_window.state('zoomed')
        self.settings_window.geometry("1920x1080")
        self.settings_window.configure(bg='white')
        self.settings_window.resizable(True, True)
        self.settings_window.transient()
        self.settings_window.grab_set()
        
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_window_closing)
        
        self.setup_force_exit_mechanism(self.settings_window)
        
        self.create_settings_widgets()
        
        # self.center_window(self.settings_window)
    
    def create_settings_widgets(self):
        main_frame = tk.Frame(self.settings_window, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=120, pady=50)
        
        self.create_settings_title_bar(main_frame)
        
        self.create_error_settings_section(main_frame)
        
        self.create_settings_buttons_section(main_frame)
        
        self.create_footer_section(main_frame)
    
    def create_settings_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="出厂设置", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_to_ai_mode)
        return_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 40))
    
    def create_error_settings_section(self, parent):
        error_frame = tk.Frame(parent, bg='white')
        error_frame.pack(expand=True, fill='both', pady=(50, 100))
        
        center_frame = tk.Frame(error_frame, bg='white')
        center_frame.pack(expand=True)
        
        settings_row = tk.Frame(center_frame, bg='white')
        settings_row.pack()
        
        self.create_error_setting(settings_row, "下限误差", self.current_lower_error, 
                                 self.on_lower_error_change, side=tk.LEFT, padx=(0, 100))
        
        self.create_error_setting(settings_row, "上限误差", self.current_upper_error, 
                                 self.on_upper_error_change, side=tk.LEFT)
        
    def setup_force_exit_mechanism(self, window):
        window.bind('<Control-Alt-q>', lambda e: self.force_exit())
        window.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        window.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        exit_zone = tk.Frame(window, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        self.click_count = 0
        self.last_click_time = 0

    def show_exit_confirmation(self):
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出出厂设置吗？\n\n"
            "退出将返回主界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_return_to_ai_mode()
        except Exception as e:
            import os
            os._exit(0)
    
    def create_error_setting(self, parent, title, initial_value, change_callback, side=tk.LEFT, padx=0):
        setting_frame = tk.Frame(parent, bg='white')
        setting_frame.pack(side=side, padx=padx)
        
        title_label = tk.Label(setting_frame, text=title, 
                              font=self.label_font, bg='white', fg='#333333')
        title_label.pack(pady=(0, 20))
        
        value_frame = tk.Frame(setting_frame, bg='white')
        value_frame.pack()
        
        value_display = tk.Entry(value_frame,
                                font=self.value_font,
                                width=8, justify='center',
                                relief='solid', bd=1,
                                bg='white', fg='#333333',
                                state='readonly')
        value_display.pack(pady=(0, 15))
        
        value_display.config(state='normal')
        value_display.delete(0, tk.END)
        value_display.insert(0, f"{initial_value:+.1f}")
        value_display.config(state='readonly')
        
        unit_button_frame = tk.Frame(value_frame, bg='white')
        unit_button_frame.pack()
        
        unit_label = tk.Label(unit_button_frame, text="克g", 
                             font=self.unit_font, bg='white', fg='#333333')
        unit_label.pack(side=tk.LEFT, padx=(0, 20))
        
        plus_btn = tk.Button(unit_button_frame, text="+", 
                            font=self.button_font,
                            bg='#e9ecef', fg='#333333',
                            relief='flat', bd=1,
                            width=3, height=1,
                            command=lambda: change_callback(0.1, value_display))
        plus_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        minus_btn = tk.Button(unit_button_frame, text="-", 
                             font=self.button_font,
                             bg='#e9ecef', fg='#333333',
                             relief='flat', bd=1,
                             width=3, height=1,
                             command=lambda: change_callback(-0.1, value_display))
        minus_btn.pack(side=tk.LEFT)
        
        if title == "下限误差":
            self.lower_error_display = value_display
        else:
            self.upper_error_display = value_display
    
    def on_lower_error_change(self, delta, display_widget):
        new_value = round(self.current_lower_error + delta, 1)
        
        if new_value < self.min_lower_error:
            messagebox.showwarning("参数限制", f"下限误差不得小于{self.min_lower_error:+.1f}g")
            return
        
        self.current_lower_error = new_value
        
        display_widget.config(state='normal')
        display_widget.delete(0, tk.END)
        display_widget.insert(0, f"{new_value:+.1f}")
        display_widget.config(state='readonly')
    
    def on_upper_error_change(self, delta, display_widget):
        new_value = round(self.current_upper_error + delta, 1)
        
        if new_value < self.min_upper_error:
            messagebox.showwarning("参数限制", f"上限误差不得小于{self.min_upper_error:+.1f}g")
            return
        
        self.current_upper_error = new_value
        
        display_widget.config(state='normal')
        display_widget.delete(0, tk.END)
        display_widget.insert(0, f"{new_value:+.1f}")
        display_widget.config(state='readonly')
    
    def create_settings_buttons_section(self, parent):
        button_frame = tk.Frame(parent, bg='white')
        button_frame.pack(pady=(0, 50))
        
        reset_btn = tk.Button(button_frame, text="恢复默认", 
                             font=self.button_font,
                             bg='#e9ecef', fg='#333333',
                             relief='flat', bd=1,
                             padx=40, pady=12,
                             command=self.reset_to_default)
        reset_btn.pack(side=tk.LEFT, padx=(0, 30))
        
        save_btn = tk.Button(button_frame, text="保存设置", 
                            font=self.button_font,
                            bg='#e9ecef', fg='#333333',
                            relief='flat', bd=1,
                            padx=40, pady=12,
                            command=self.save_settings)
        save_btn.pack(side=tk.LEFT, padx=(30, 0))
    
    def reset_to_default(self):
        result = messagebox.askyesno("恢复默认", 
                                   f"确认要恢复默认设置吗？\n\n"
                                   f"下限误差：{self.default_lower_error:+.1f}g\n"
                                   f"上限误差：{self.default_upper_error:+.1f}g")
        
        if result:
            self.current_lower_error = round(self.default_lower_error, 1)
            self.current_upper_error = round(self.default_upper_error, 1)
            
            self.lower_error_display.config(state='normal')
            self.lower_error_display.delete(0, tk.END)
            self.lower_error_display.insert(0, f"{self.current_lower_error:+.1f}")
            self.lower_error_display.config(state='readonly')
            
            self.upper_error_display.config(state='normal')
            self.upper_error_display.delete(0, tk.END)
            self.upper_error_display.insert(0, f"{self.current_upper_error:+.1f}")
            self.upper_error_display.config(state='readonly')
            
            messagebox.showinfo("恢复成功", "已恢复默认设置")
    
    def save_settings(self):
        """保存设置"""
        error_diff = round(self.current_upper_error - self.current_lower_error, 1)
        
        if error_diff < (self.min_error_diff - 0.05):
            messagebox.showerror("参数错误", 
                               f"误差范围不足！\n\n"
                               f"请调整参数使误差范围至少为 {self.min_error_diff}g")
            return
        
        result = messagebox.askyesno("保存设置", 
                                   f"确认保存当前设置吗？\n\n"
                                   f"下限误差：{self.current_lower_error:+.1f}g\n"
                                   f"上限误差：{self.current_upper_error:+.1f}g\n")

        if result:
            try:
                global error_config
                error_config.update_thresholds(self.current_lower_error, self.current_upper_error)
                
                self._save_to_config_file()

                messagebox.showinfo("保存成功", 
                                  f"出厂设置已保存！\n\n"
                                  f"下限误差：{self.current_lower_error:+.1f}g\n"
                                  f"上限误差：{self.current_upper_error:+.1f}g\n\n"
                                  f"新的误差设置将在下次生产时生效")

            except Exception as e:
                error_msg = f"保存设置异常: {str(e)}"
                messagebox.showerror("保存失败", f"保存设置时发生错误：\n{error_msg}")
                
    def _save_to_config_file(self):
        try:
            import json
            import os

            config_dir = "config"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            config_file = os.path.join(config_dir, "error_thresholds.json")
            config_data = {
                "lower_error": self.current_lower_error,
                "upper_error": self.current_upper_error,
                "saved_time": time.time()
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)

        except Exception as e:
            pass
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
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
    
    def center_window(self, window):
        try:
            window.update_idletasks()
            
            width = window.winfo_width()
            height = window.winfo_height()
            
            if width <= 1 or height <= 1:
                width = 950
                height = 750
            
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            window.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            window.geometry("950x750")
    
    def on_return_to_ai_mode(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        if hasattr(self, 'password_window') and self.password_window.winfo_exists():
            self.password_window.destroy()
        
        if self.system_settings_window:
            try:
                self.system_settings_window.root.deiconify()
                self.system_settings_window.root.lift()
                self.system_settings_window.root.focus_force()
            except Exception as e:
                if hasattr(self.system_settings_window, 'ai_mode_window') and self.system_settings_window.ai_mode_window:
                    try:
                        self.system_settings_window.ai_mode_window.root.deiconify()
                        self.system_settings_window.ai_mode_window.root.lift()
                        self.system_settings_window.ai_mode_window.root.focus_force()
                    except Exception as e2:
                        pass
    
    def on_password_window_closing(self):
        self.on_return_to_ai_mode()
    
    def on_settings_window_closing(self):
        self.on_return_to_ai_mode()


def main():
    root = tk.Tk()
    root.withdraw()
    
    factory_settings = FactorySettingsInterface()

if __name__ == "__main__":
    main()