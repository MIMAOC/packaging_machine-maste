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
            # 确保输入框获得焦点
            entry_widget.focus_set()
            TouchScreenUtils.show_virtual_keyboard()
            
            if placeholder_text and entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_click_focus(event):
            # 点击时强制设置焦点到输入框
            entry_widget.focus_force()
            TouchScreenUtils.show_virtual_keyboard()
            
            if placeholder_text and entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            if placeholder_text and entry_widget.get() == '':
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        entry_widget.bind('<FocusIn>', on_touch_focus)
        entry_widget.bind('<Button-1>', on_click_focus)
        
        if placeholder_text:
            entry_widget.bind('<FocusOut>', on_focus_out)
            entry_widget.insert(0, placeholder_text)
            entry_widget.config(fg='#999999')
    
    @staticmethod
    def setup_window_focus_handling(window, entry_widgets=None):
        """
        设置窗口焦点处理，点击输入框外部区域时将焦点设置到当前窗口
        
        Args:
            window: 要设置的窗口（tk.Tk 或 tk.Toplevel）
            entry_widgets: 输入框控件列表，如果为None则自动查找
        """
        try:
            # 如果没有提供entry_widgets，自动查找窗口中的所有Entry和Text控件
            if entry_widgets is None:
                entry_widgets = TouchScreenUtils._find_all_entry_widgets(window)
            
            def on_window_click(event):
                try:
                    # 检查点击的是否是输入框或其子控件
                    clicked_widget = event.widget
                    
                    # 检查是否点击在输入框上
                    is_entry_click = False
                    clicked_entry = None
                    for entry_widget in entry_widgets:
                        if clicked_widget == entry_widget:
                            is_entry_click = True
                            clicked_entry = entry_widget
                            break
                        elif TouchScreenUtils._is_child_widget(clicked_widget, entry_widget):
                            is_entry_click = True
                            clicked_entry = entry_widget
                            break
                    
                    # 如果点击的是输入框，确保其获得焦点
                    if is_entry_click and clicked_entry:
                        clicked_entry.focus_force()
                    # 如果不是点击输入框，则将焦点设置到窗口
                    elif not is_entry_click:
                        window.focus_set()
                        
                        # 对于对话框，确保其保持在顶层
                        if isinstance(window, tk.Toplevel):
                            window.lift()
                            window.focus_force()
                            
                except Exception as e:
                    pass  # 静默处理异常，避免影响正常操作
            
            # 绑定点击事件到窗口和所有子控件
            TouchScreenUtils._bind_click_recursively(window, on_window_click, entry_widgets)
            
        except Exception as e:
            pass  # 静默处理异常
    
    @staticmethod
    def _find_all_entry_widgets(parent):
        """递归查找所有Entry和Text控件"""
        entry_widgets = []
        
        def find_entries(widget):
            try:
                if isinstance(widget, (tk.Entry, tk.Text)):
                    entry_widgets.append(widget)
                
                # 递归查找子控件
                for child in widget.winfo_children():
                    find_entries(child)
            except Exception:
                pass
        
        find_entries(parent)
        return entry_widgets
    
    @staticmethod
    def _is_child_widget(widget, parent):
        """检查widget是否是parent的子控件"""
        try:
            current = widget
            while current:
                if current == parent:
                    return True
                current = current.master
            return False
        except Exception:
            return False
    
    @staticmethod
    def _bind_click_recursively(widget, click_handler, entry_widgets):
        """递归绑定点击事件到所有控件"""
        try:
            # 为所有控件绑定点击事件，让焦点处理逻辑统一处理
            widget.bind('<Button-1>', click_handler, add=True)
            
            # 递归处理子控件
            for child in widget.winfo_children():
                TouchScreenUtils._bind_click_recursively(child, click_handler, entry_widgets)
                
        except Exception:
            pass
    
    @staticmethod
    def setup_dialog_focus_handling(dialog_window):
        """
        专门为对话框设置焦点处理
        
        Args:
            dialog_window: 对话框窗口 (tk.Toplevel)
        """
        try:
            # 查找对话框中的所有输入控件
            entry_widgets = TouchScreenUtils._find_all_entry_widgets(dialog_window)
            
            def on_dialog_click(event):
                try:
                    clicked_widget = event.widget
                    
                    # 检查是否点击在输入框上
                    is_entry_click = False
                    clicked_entry = None
                    for entry_widget in entry_widgets:
                        if clicked_widget == entry_widget:
                            is_entry_click = True
                            clicked_entry = entry_widget
                            break
                        elif TouchScreenUtils._is_child_widget(clicked_widget, entry_widget):
                            is_entry_click = True
                            clicked_entry = entry_widget
                            break
                    
                    # 如果点击的是输入框，确保其获得焦点
                    if is_entry_click and clicked_entry:
                        clicked_entry.focus_force()
                    # 如果不是点击输入框，则确保对话框保持焦点和顶层
                    elif not is_entry_click:
                        dialog_window.focus_set()
                        dialog_window.lift()
                        dialog_window.focus_force()
                        
                        # 如果对话框设置了grab_set，确保其保持模态
                        try:
                            if dialog_window.grab_current() == dialog_window:
                                dialog_window.grab_set()
                        except Exception:
                            pass
                            
                except Exception:
                    pass
            
            # 绑定点击事件到对话框和所有子控件
            TouchScreenUtils._bind_click_recursively(dialog_window, on_dialog_click, entry_widgets)
            
            # 确保对话框在显示时获得焦点
            dialog_window.after(100, lambda: dialog_window.focus_force())
            
        except Exception:
            pass
    
    @staticmethod
    def optimize_window_for_touch(window):
        try:
            window.tk.call('tk', 'scaling', 1.5)
            
            # 自动设置窗口焦点处理
            TouchScreenUtils.setup_window_focus_handling(window)
            
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

    @staticmethod
    def setup_enhanced_touch_entry(entry_widget, placeholder_text=None, parent_window=None):
        """
        增强的触摸输入框设置，包含焦点管理
        
        Args:
            entry_widget: 输入框控件
            placeholder_text: 占位符文本
            parent_window: 父窗口，用于焦点管理
        """
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
        
        # 如果提供了父窗口，设置焦点处理
        if parent_window:
            TouchScreenUtils.setup_window_focus_handling(parent_window, [entry_widget])

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