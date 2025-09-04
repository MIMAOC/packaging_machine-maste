"""
作者：C
创建日期：2025-07-22
更新日期：2025-08-19
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time
import requests
import functools
from typing import Optional, Callable, Any

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    RETRY_AVAILABLE = True
except ImportError:
    RETRY_AVAILABLE = False

try:
    from modbus_client import create_modbus_client, ModbusClient
    MODBUS_AVAILABLE = True
except ImportError as e:
    MODBUS_AVAILABLE = False

try:
    from ai_mode_interface import AIModeInterface
    AI_MODE_AVAILABLE = True
except ImportError as e:
    AI_MODE_AVAILABLE = False

try:
    from traditional_mode_interface import SimpleTianTengInterface
    TRADITIONAL_MODE_AVAILABLE = True
except ImportError as e:
    TRADITIONAL_MODE_AVAILABLE = False

try:
    from config.api_config import get_api_config, set_api_config
    API_CONFIG_AVAILABLE = True
except ImportError as e:
    API_CONFIG_AVAILABLE = False

try:
    from clients.webapi_client import test_webapi_connection, get_webapi_info
    WEBAPI_CLIENT_AVAILABLE = True
except ImportError as e:
    WEBAPI_CLIENT_AVAILABLE = False


def simple_retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                except Exception as e:
                    raise e
            raise last_exception
        return wrapper
    return decorator

def retry_api_call(func: Callable, max_attempts: int = 10, *args, **kwargs) -> tuple[bool, str]:
    if RETRY_AVAILABLE:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
            reraise=True
        )
        def _retry_with_tenacity():
            return func(*args, **kwargs)
        
        try:
            return _retry_with_tenacity()
        except Exception as e:
            return False, f"重试{max_attempts}次后仍失败: {str(e)}"
    
    else:
        @simple_retry(
            max_attempts=max_attempts,
            delay=1.0,
            backoff=2.0,
            exceptions=(requests.RequestException, ConnectionError, TimeoutError, OSError)
        )
        def _simple_retry():
            return func(*args, **kwargs)
        
        try:
            return _simple_retry()
        except Exception as e:
            return False, f"重试{max_attempts}次后仍失败: {str(e)}"

class PackagingMachineGUI:
    def __init__(self, root):
        self.root = root
        self.modbus_client: Optional[ModbusClient] = None
        self.connection_status = False
        self.api_connection_status = False
        self.status_label = None
        self.api_status_label = None
        self.api_retry_count = 0
        self.traditional_interface = None
        
        self.setup_window()
        
        self.setup_fonts()
        
        self.create_widgets()
        
        if MODBUS_AVAILABLE:
            self.start_modbus_connection()
        else:
            self.show_modbus_error()
        
        if WEBAPI_CLIENT_AVAILABLE:
            self.test_backend_api_connection()
        else:
            self.show_api_error()
    
    def setup_window(self):
        self.root.title("多斗颗粒称重包装机 - MHWPM v1.5.2 (前端)")
        
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        self.setup_force_exit_mechanism()
        
        try:
            pass
        except:
            pass
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=36, weight="bold")
        self.subtitle_font = tkFont.Font(family="微软雅黑", size=20)
        self.button_font = tkFont.Font(family="微软雅黑", size=24, weight="bold")
        self.button_sub_font = tkFont.Font(family="微软雅黑", size=16)
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)
        self.status_font = tkFont.Font(family="微软雅黑", size=16)
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)
        
        self.create_status_bar(main_frame)
        
        self.create_title_section(main_frame)
        
        self.create_mode_selection(main_frame)
        
        self.create_footer_section(main_frame)
    
    def create_status_bar(self, parent):
        status_frame = tk.Frame(parent, bg='white', relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        plc_frame = tk.Frame(status_frame, bg='white')
        plc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(plc_frame, text="PLC连接:", 
                font=self.status_font, bg='white', fg='#333333').pack(side=tk.LEFT, padx=10)
        
        self.status_label = tk.Label(plc_frame, text="正在连接...", 
                                   font=self.status_font, bg='white', fg='#ff6600')
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        plc_buttons_frame = tk.Frame(plc_frame, bg='white')
        plc_buttons_frame.pack(side=tk.RIGHT, padx=10)
        
        reconnect_btn = tk.Button(plc_buttons_frame, text="重新连接", 
                                font=tkFont.Font(family="微软雅黑", size=9),
                                command=self.reconnect_modbus, bg='#e0e0e0')
        reconnect_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        separator = tk.Frame(status_frame, width=2, bg='#ddd')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        api_frame = tk.Frame(status_frame, bg='white')
        api_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(api_frame, text="后端API:", 
                font=self.status_font, bg='white', fg='#333333').pack(side=tk.LEFT, padx=10)
        
        self.api_status_label = tk.Label(api_frame, text="检测中...", 
                                    font=self.status_font, bg='white', fg='#ff6600')
        self.api_status_label.pack(side=tk.LEFT, padx=5)
        
        api_buttons_frame = tk.Frame(api_frame, bg='white')
        api_buttons_frame.pack(side=tk.RIGHT, padx=10)
        
        api_test_btn = tk.Button(api_buttons_frame, text="测试连接", 
                            font=tkFont.Font(family="微软雅黑", size=9),
                            command=self.test_backend_api_connection, bg='#e0e0e0')
        api_test_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        retry_btn = tk.Button(api_buttons_frame, text="重试连接", 
                            font=tkFont.Font(family="微软雅黑", size=9),
                            command=lambda: self.test_backend_api_connection(force_retry=True), 
                            bg='#ffc107')
        retry_btn.pack(side=tk.LEFT, padx=2, pady=2)
    
    def create_title_section(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(pady=(20, 30))
        
        chinese_title = tk.Label(title_frame, text="多斗颗粒称重包装机", 
                               font=self.title_font, bg='white', fg='#333333')
        chinese_title.pack()
        
        english_title = tk.Label(title_frame, text="Multi-head Weighing & Packaging Machine", 
                               font=self.subtitle_font, bg='white', fg='#666666')
        english_title.pack(pady=(10, 0))
        
        separator = tk.Frame(title_frame, height=3, bg='#7fb3d3', width=600)
        separator.pack(pady=(15, 0))
        separator.pack_propagate(False)
    
    def create_mode_selection(self, parent):
        mode_title = tk.Label(parent, text="选择您的操作模式", 
                            font=self.subtitle_font, bg='white', fg='#333333')
        mode_title.pack(pady=(30, 40))
        
        button_frame = tk.Frame(parent, bg='white')
        button_frame.pack(pady=(0, 30))
        
        traditional_frame = tk.Frame(button_frame, bg='#d3d3d3', relief='flat', bd=0)
        traditional_frame.pack(side=tk.LEFT, padx=(0, 60))
        traditional_frame.configure(width=350, height=150)
        traditional_frame.pack_propagate(False)
        
        self.create_rounded_button(traditional_frame, "传统模式", "手动调试设置", 
                                 self.on_traditional_click, '#d3d3d3')
        
        ai_frame = tk.Frame(button_frame, bg='#d3d3d3', relief='flat', bd=0)
        ai_frame.pack(side=tk.LEFT)
        ai_frame.configure(width=350, height=150)
        ai_frame.pack_propagate(False)
        
        self.create_rounded_button(ai_frame, "AI模式", "自学习自适应", 
                                 self.on_ai_click, '#d3d3d3')
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        version_text = "MHWPM v1.5.2 ©杭公式人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 10))
        
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
        except ImportError as e:
            pass
    
    def create_rounded_button(self, parent, main_text, sub_text, command, bg_color):
        canvas = tk.Canvas(parent, width=350, height=150, highlightthickness=0, 
                          bg='white', relief='flat')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        self.draw_rounded_rectangle(canvas, bg_color)
        
        canvas.create_text(175, 60, text=main_text, font=self.button_font, 
                          fill='#333333', anchor='center')
        canvas.create_text(175, 100, text=sub_text, font=self.button_sub_font, 
                          fill='#666666', anchor='center')
        
        canvas.bind("<Button-1>", lambda e: command())
        canvas.bind("<Enter>", lambda e: self.on_button_enter(canvas, bg_color, main_text, sub_text))
        canvas.bind("<Leave>", lambda e: self.on_button_leave(canvas, bg_color, main_text, sub_text))
    
    def draw_rounded_rectangle(self, canvas, bg_color):
        radius = 20
        width = 350
        height = 150
        
        canvas.delete("all")
        
        canvas.create_rectangle(radius, 0, width-radius, height, 
                            fill=bg_color, outline=bg_color)
        canvas.create_rectangle(0, radius, width, height-radius, 
                            fill=bg_color, outline=bg_color)
        
        canvas.create_arc(0, 0, 2*radius, 2*radius, 
                        start=90, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(width-2*radius, 0, width, 2*radius, 
                        start=0, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(0, height-2*radius, 2*radius, height, 
                        start=180, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(width-2*radius, height-2*radius, width, height, 
                        start=270, extent=90, fill=bg_color, outline=bg_color)
    
    def on_button_enter(self, canvas, original_color, main_text, sub_text):
        hover_color = '#b0b0b0'
        canvas.configure(bg='white')
        self.draw_rounded_rectangle(canvas, hover_color)
        canvas.create_text(175, 60, text=main_text, font=self.button_font, 
                          fill='#333333', anchor='center')
        canvas.create_text(175, 100, text=sub_text, font=self.button_sub_font, 
                          fill='#666666', anchor='center')
        
    def on_button_leave(self, canvas, original_color, main_text, sub_text):
        canvas.configure(bg='white')
        self.draw_rounded_rectangle(canvas, original_color)
        canvas.create_text(175, 60, text=main_text, font=self.button_font, 
                          fill='#333333', anchor='center')
        canvas.create_text(175, 100, text=sub_text, font=self.button_sub_font, 
                          fill='#666666', anchor='center')
        
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
            "确定要退出包装机程序吗？\n\n"
            "退出将断开PLC连接并关闭所有功能。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_closing()
        except Exception as e:
            import os
            os._exit(0)
    
    def start_modbus_connection(self):
        def connect_thread():
            try:
                self.modbus_client = create_modbus_client(
                    host="192.168.6.6",
                    port=502,
                    timeout=3
                )
                
                success, message = self.modbus_client.connect()
                
                self.root.after(0, self.handle_modbus_connection_result, success, message)
                
            except Exception as e:
                error_msg = f"Modbus连接初始化失败：{str(e)}"
                self.root.after(0, self.handle_modbus_connection_result, False, error_msg)
        
        connection_thread = threading.Thread(target=connect_thread, daemon=True)
        connection_thread.start()
    
    def handle_modbus_connection_result(self, success, message):
        self.connection_status = success
        
        if success:
            self.status_label.config(text="已连接", fg='#00aa00')
        else:
            self.status_label.config(text="未连接", fg='#ff0000')
    
    def test_backend_api_connection_basic(self):
        if not WEBAPI_CLIENT_AVAILABLE:
            return False, "WebAPI客户端模块不可用"
        
        return test_webapi_connection()
    
    def test_backend_api_connection(self, force_retry=False, max_attempts=10):
        def test_thread():
            try:
                if force_retry:
                    self.api_retry_count += 1
                
                success, message = retry_api_call(
                    self.test_backend_api_connection_basic,
                    max_attempts=max_attempts
                )
                
                if success:
                    self.api_retry_count = 0
                
                self.root.after(0, self.handle_api_connection_result, success, message, force_retry)
                
            except Exception as e:
                error_msg = f"API连接测试异常：{str(e)}"
                self.root.after(0, self.handle_api_connection_result, False, error_msg, force_retry)
        
        status_text = "重试中..." if force_retry else "检测中..."
        self.api_status_label.config(text=status_text, fg='#ff6600')
        
        test_thread = threading.Thread(target=test_thread, daemon=True)
        test_thread.start()
    
    def handle_api_connection_result(self, success, message, was_retry=False):
        self.api_connection_status = success
        
        if success:
            self.api_status_label.config(text="已连接", fg='#00aa00')
            if was_retry:
                messagebox.showinfo("连接成功", f"API连接重试成功！\n{message}")
        else:
            self.api_status_label.config(text="未连接", fg='#ff0000')
            if was_retry:
                messagebox.showerror("连接失败", f"API连接重试失败！\n{message}")
    
    def test_custom_api_function(self, api_func: Callable, *args, **kwargs):
        try:
            success, message = retry_api_call(api_func, 3, *args, **kwargs)
            return success, message
        except Exception as e:
            return False, f"自定义API函数调用失败: {str(e)}"
        
    def reconnect_modbus(self):
        self.status_label.config(text="正在重连...", fg='#ff6600')
        self.start_modbus_connection()
    
    def show_modbus_error(self):
        self.status_label.config(text="模块不可用", fg='#ff0000')
    
    def show_api_error(self):
        self.api_status_label.config(text="模块不可用", fg='#ff0000')
    
    def on_traditional_click(self):
        if not self.connection_status:
            messagebox.showwarning("连接警告", "PLC未连接，某些功能可能不可用！")
        
        result = messagebox.askyesno(
            "模式选择确认", 
            "您选择了传统模式\n\n"
            "传统模式特点：\n"
            "• 手动调试设置\n"
            "• 用户完全控制参数\n"
            "• 适合经验丰富的操作员\n\n"
            "是否确认进入传统模式？"
        )
        
        if result:        
            if self.modbus_client and self.connection_status:
                try:
                    from plc_addresses import GLOBAL_CONTROL_ADDRESSES
                    
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['AIMode'], False):
                        messagebox.showerror("PLC通信失败", "发送AI模式关闭命令失败")
                        return
                    
                except ImportError as e:
                    messagebox.showwarning("模块错误", "无法导入PLC地址配置")
                except Exception as e:
                    error_msg = f"PLC模式切换异常: {str(e)}"
                    messagebox.showerror("PLC操作失败", error_msg)
            else:
                messagebox.showwarning("PLC未连接", "PLC未连接，无法发送模式切换命令")
        
        if TRADITIONAL_MODE_AVAILABLE:
            try:
                self.hide_main_window()
                
                traditional_window = tk.Toplevel()
                traditional_window.title("六头线性调节秤 V1.8 - 传统模式")
                traditional_window.geometry("1400x900")
                traditional_window.configure(bg='#ffffff')
                traditional_window.minsize(1200, 800)
                
                traditional_window.lift()
                traditional_window.focus_force()
                
                def on_traditional_close():
                    traditional_window.destroy()
                    self.show_main_window()
                    self.cleanup_traditional_interface()
                
                traditional_window.protocol("WM_DELETE_WINDOW", on_traditional_close)
                
                self.traditional_interface = SimpleTianTengInterface(
                    parent=traditional_window, 
                    main_window=self,
                    modbus_client=self.modbus_client
                )
                
            except Exception as e:
                self.show_main_window()
                messagebox.showerror("界面错误", f"打开传统模式界面失败：{str(e)}")
        else:
            messagebox.showerror("模块错误", "传统模式界面模块未加载，无法打开传统模式")
    
    def on_ai_click(self):
        if not self.connection_status:
            messagebox.showwarning("PLC连接警告", "PLC未连接，AI模式的某些功能将不可用！")
        
        if not self.api_connection_status:
            result = messagebox.askyesno(
                "API连接警告", 
                "后端API服务未连接！\n\n"
                "AI模式需要后端API服务进行数据分析。\n"
                "没有API服务，AI模式将无法正常工作。\n\n"
                "是否要先尝试重新连接API？"
            )
            if result:
                self.test_backend_api_connection(force_retry=True, max_attempts=10)
                return
            else:
                continue_result = messagebox.askyesno(
                    "继续确认",
                    "在没有API连接的情况下，AI模式功能将受限。\n\n"
                    "是否仍要继续？"
                )
                if not continue_result:
                    return
        
        result = messagebox.askyesno(
            "模式选择确认", 
            "您选择了AI模式\n\n"
            "AI模式特点：\n"
            "• 自动学习优化\n"
            "• 智能参数调节\n"
            "• 自适应包装策略\n"
            "• 提高生产效率\n"
            "• 依赖后端API服务\n"
            "• 增强重试机制\n\n"
            "是否确认进入AI模式？"
        )
        
        if result:
            if self.modbus_client and self.connection_status:
                try:
                    from plc_addresses import GLOBAL_CONTROL_ADDRESSES
                    
                    if not self.modbus_client.write_coil(GLOBAL_CONTROL_ADDRESSES['AIMode'], True):
                        messagebox.showerror("PLC通信失败", "发送AI模式启用命令失败")
                        return

                except ImportError as e:
                    messagebox.showwarning("模块错误", "无法导入PLC地址配置")
                except Exception as e:
                    error_msg = f"PLC模式切换异常: {str(e)}"
                    messagebox.showerror("PLC操作失败", error_msg)
            else:
                messagebox.showwarning("PLC未连接", "PLC未连接，无法发送模式切换命令")
                
            try:
                self.hide_main_window()
                
                ai_window = AIModeInterface(parent=self.root, main_window=self)
            except Exception as e:
                self.show_main_window()
                messagebox.showerror("界面错误", f"打开AI模式界面失败：{str(e)}")
    
    def show_main_window(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception as e:
            pass
    
    def hide_main_window(self):
        try:
            self.root.withdraw()
        except Exception as e:
            pass

    def cleanup_traditional_interface(self):
        if self.traditional_interface:
            try:
                if hasattr(self.traditional_interface, 'cleanup'):
                    self.traditional_interface.cleanup()
            except Exception as e:
                pass
            self.traditional_interface = None
    
    def on_closing(self):
        try:
            self.cleanup_traditional_interface()   
            
            if self.modbus_client and self.connection_status:
                self.modbus_client.disconnect()
        except Exception as e:
            pass
        finally:
            self.root.destroy()

def center_window(root):
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')


def main():
    root = tk.Tk()
    
    app = PackagingMachineGUI(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    center_window(root)
    
    root.mainloop()


if __name__ == "__main__":
    main()