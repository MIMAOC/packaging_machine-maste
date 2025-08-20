"""
统一的Logo图片处理模块

作者：C
创建日期：2025-08-04
修改日期：2025-08-19
"""

import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkFont
from PIL import Image, ImageTk
import os
import sys

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LogoHandler:
    
    def __init__(self):
        self.algormula_image = None
        self.tianteng_image = None
        self.load_images()
    
    def load_images(self):
        try:
            algormula_path = get_resource_path("algormula.png")
            if os.path.exists(algormula_path):
                algormula_pil = Image.open(algormula_path)
                algormula_pil = algormula_pil.resize((80, 20), Image.Resampling.LANCZOS)
                self.algormula_image = ImageTk.PhotoImage(algormula_pil)
            
            tianteng_path = get_resource_path("tianteng.png")
            if os.path.exists(tianteng_path):
                tianteng_pil = Image.open(tianteng_path)
                tianteng_pil = tianteng_pil.resize((80, 10), Image.Resampling.LANCZOS)
                self.tianteng_image = ImageTk.PhotoImage(tianteng_pil)
                
        except Exception as e:
            pass
    
    def show_contact_dialog(self, parent_window):
        try:
            contact_window = tk.Toplevel(parent_window)
            contact_window.title("联系我们")
            contact_window.geometry("600x400")
            contact_window.configure(bg='white')
            contact_window.resizable(False, False)
            contact_window.transient(parent_window)
            contact_window.grab_set()
            
            self.center_dialog_relative_to_parent(contact_window, parent_window, 600, 400)
            
            tk.Label(contact_window, text="如需更多信息 请电话联系我们", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='white', fg='#333333').pack(pady=40)
            
            tk.Label(contact_window, text="138 0680 0177", 
                    font=tkFont.Font(family="Arial", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=10)
            
            tk.Label(contact_window, text="133 7257 1638", 
                    font=tkFont.Font(family="Arial", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=10)
            
            tk.Button(contact_window, text="关闭", 
                     font=tkFont.Font(family="微软雅黑", size=12),
                     bg='#6c757d', fg='white',
                     relief='flat', bd=0,
                     padx=30, pady=10,
                     command=contact_window.destroy).pack(pady=30)
            
        except Exception as e:
            messagebox.showerror("系统错误", f"显示联系信息时发生错误：{str(e)}")
    
    def center_dialog_relative_to_parent(self, dialog_window, parent_window, dialog_width, dialog_height):
        try:
            dialog_window.update_idletasks()
            parent_window.update_idletasks()
            
            parent_x = parent_window.winfo_x()
            parent_y = parent_window.winfo_y()
            parent_width = parent_window.winfo_width()
            parent_height = parent_window.winfo_height()
            
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
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
            pass
    
    def create_logo_components(self, parent_frame, bg_color='white'):
        try:
            logo_frame = tk.Frame(parent_frame, bg=bg_color)
            logo_frame.pack()
            
            algormula_component = None
            tianteng_component = None
            
            if self.algormula_image:
                algormula_component = tk.Label(logo_frame, image=self.algormula_image, 
                                             bg=bg_color, cursor='hand2')
                algormula_component.pack(side=tk.LEFT, padx=(0, 20))
                
                def on_algormula_click(event):
                    parent_window = parent_frame.winfo_toplevel()
                    self.show_contact_dialog(parent_window)
                
                algormula_component.bind("<Button-1>", on_algormula_click)
            else:
                algormula_component = tk.Label(logo_frame, text="LOGO", 
                                             bg=bg_color, fg='#666666',
                                             font=tkFont.Font(family="Arial", size=10))
                algormula_component.pack(side=tk.LEFT, padx=(0, 20))
            
            if self.tianteng_image:
                tianteng_component = tk.Label(logo_frame, image=self.tianteng_image, 
                                            bg=bg_color, cursor='hand2')
                tianteng_component.pack(side=tk.LEFT)
                
                def on_tianteng_click(event):
                    parent_window = parent_frame.winfo_toplevel()
                    self.show_contact_dialog(parent_window)
                
                tianteng_component.bind("<Button-1>", on_tianteng_click)
            else:
                tianteng_component = tk.Label(logo_frame, text="BRAND", 
                                            bg=bg_color, fg='#666666',
                                            font=tkFont.Font(family="Arial", size=10))
                tianteng_component.pack(side=tk.LEFT)
            
            return algormula_component, tianteng_component
            
        except Exception as e:
            return None, None

logo_handler = LogoHandler()

def create_logo_components(parent_frame, bg_color='white'):
    return logo_handler.create_logo_components(parent_frame, bg_color)