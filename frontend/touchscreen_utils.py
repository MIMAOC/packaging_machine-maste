"""
触控屏工具模块
"""

import subprocess
import tkinter as tk
import os
import sys
import ctypes
from ctypes import wintypes

class TouchScreenUtils:
    
    @staticmethod
    def show_virtual_keyboard():
        TouchScreenUtils._call_tabtip_shell()
    
    @staticmethod
    def _call_tabtip_shell():
        try:
            shell32 = ctypes.windll.shell32
            
            tabtip_paths = [
                r"C:\Program Files\Common Files\microsoft shared\ink\TabTip.exe"
            ]
            
            for path in tabtip_paths:
                if os.path.exists(path):
                    result = shell32.ShellExecuteW(
                        None,
                        "open",
                        path,
                        None,
                        None,
                        1
                    )
                    
                    if result > 32:
                        return True
                        
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def setup_touch_entry(entry_widget, placeholder_text=None):
        def on_touch_focus(event):
            TouchScreenUtils.show_virtual_keyboard()
            
            if placeholder_text and entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            if placeholder_text and entry_widget.get() == '':
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        entry_widget.bind('<FocusIn>', on_touch_focus)
        entry_widget.bind('<Button-1>', on_touch_focus)
        
        if placeholder_text:
            entry_widget.bind('<FocusOut>', on_focus_out)
            entry_widget.insert(0, placeholder_text)
            entry_widget.config(fg='#999999')
    
    @staticmethod
    def optimize_window_for_touch(window):
        try:
            window.tk.call('tk', 'scaling', 1.5)
        except Exception:
            pass
    
    @staticmethod
    def optimize_widget_for_touch(widget, min_height=40, extra_padding=5):
        try:
            current_config = widget.config()
            
            if isinstance(widget, tk.Button):
                current_pady = widget.cget('pady') or 0
                widget.config(pady=current_pady + extra_padding)
            
            elif isinstance(widget, tk.Entry):
                widget.config(relief='solid', bd=2)
            
        except Exception:
            pass
    
    @staticmethod
    def create_touch_button(parent, text, command, **kwargs):
        default_config = {
            'font': ('微软雅黑', 12, 'bold'),
            'padx': 20,
            'pady': 12,
            'relief': 'flat',
            'bd': 0,
            'cursor': 'hand2'
        }
        
        button_config = {**default_config, **kwargs}
        
        button = tk.Button(parent, text=text, command=command, **button_config)
        
        def on_press(event):
            button.config(relief='sunken')
        
        def on_release(event):
            button.config(relief='flat')
        
        button.bind('<Button-1>', on_press)
        button.bind('<ButtonRelease-1>', on_release)
        
        return button

def test_virtual_keyboard():
    TouchScreenUtils.show_virtual_keyboard()


# 简单的测试界面
def create_test_window():
    root = tk.Tk()
    root.title("触摸屏测试")
    root.geometry("400x300")
    
    TouchScreenUtils.optimize_window_for_touch(root)
    
    entry = tk.Entry(root, font=('微软雅黑', 14), width=30)
    entry.pack(pady=20, ipady=10)
    TouchScreenUtils.setup_touch_entry(entry, "点击此处测试虚拟键盘")
    
    test_btn = TouchScreenUtils.create_touch_button(
        root, 
        "测试虚拟键盘", 
        TouchScreenUtils.show_virtual_keyboard,
        bg='#4a90e2',
        fg='white'
    )
    test_btn.pack(pady=10)
    
    exit_btn = TouchScreenUtils.create_touch_button(
        root,
        "退出",
        root.quit,
        bg='#dc3545',
        fg='white'
    )
    exit_btn.pack(pady=10)
    
    root.mainloop()


if __name__ == "__main__":
    create_test_window()