#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
触控屏工具模块
提供虚拟键盘调用和触摸优化功能
"""

import subprocess
import tkinter as tk
import os
import sys
import ctypes
from ctypes import wintypes

class TouchScreenUtils:
    """触控屏工具类"""
    
    @staticmethod
    def show_virtual_keyboard():
        """显示Windows虚拟键盘"""
        # 使用ctypes调用Shell执行TabTip
        TouchScreenUtils._call_tabtip_shell()
    
    @staticmethod
    def _call_tabtip_shell():
        """使用Shell执行TabTip（推荐方法）"""
        try:
            # 使用ctypes调用Shell执行
            shell32 = ctypes.windll.shell32
            
            # TabTip.exe的可能路径
            tabtip_paths = [
                r"C:\Program Files\Common Files\microsoft shared\ink\TabTip.exe"
            ]
            
            for path in tabtip_paths:
                if os.path.exists(path):
                    # 使用ShellExecute启动TabTip
                    result = shell32.ShellExecuteW(
                        None,           # hwnd
                        "open",         # lpOperation
                        path,           # lpFile
                        None,           # lpParameters
                        None,           # lpDirectory
                        1               # nShowCmd (SW_SHOWNORMAL)
                    )
                    
                    if result > 32:  # ShellExecute成功返回值大于32
                        print(f"[虚拟键盘] Shell调用成功: {path}")
                        return True
                        
            print("[虚拟键盘] Shell调用失败：未找到TabTip.exe")
            return False
            
        except Exception as e:
            print(f"[虚拟键盘] Shell调用异常: {e}")
            return False
    
    @staticmethod
    def setup_touch_entry(entry_widget, placeholder_text=None):
        """
        为输入框设置触摸支持
        
        Args:
            entry_widget: 输入框组件
            placeholder_text: 占位符文本（可选）
        """
        def on_touch_focus(event):
            """触摸获得焦点时显示键盘"""
            TouchScreenUtils.show_virtual_keyboard()
            
            # 如果有占位符处理
            if placeholder_text and entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            """失去焦点时的处理"""
            if placeholder_text and entry_widget.get() == '':
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        # 绑定触摸事件
        entry_widget.bind('<FocusIn>', on_touch_focus)
        entry_widget.bind('<Button-1>', on_touch_focus)
        
        if placeholder_text:
            entry_widget.bind('<FocusOut>', on_focus_out)
            # 设置初始占位符
            entry_widget.insert(0, placeholder_text)
            entry_widget.config(fg='#999999')
    
    @staticmethod
    def optimize_window_for_touch(window):
        """优化窗口触摸支持"""
        try:
            # 设置高DPI支持
            window.tk.call('tk', 'scaling', 1.5)
            print("[触摸优化] 窗口DPI缩放设置成功")
        except Exception as e:
            print(f"[触摸优化] 窗口DPI设置失败: {e}")
    
    @staticmethod
    def optimize_widget_for_touch(widget, min_height=40, extra_padding=5):
        """
        优化单个控件的触摸支持
        
        Args:
            widget: 要优化的控件
            min_height: 最小高度（像素）
            extra_padding: 额外内边距
        """
        try:
            # 增加控件的内边距
            current_config = widget.config()
            
            # 如果是Button，增加pady
            if isinstance(widget, tk.Button):
                current_pady = widget.cget('pady') or 0
                widget.config(pady=current_pady + extra_padding)
            
            # 如果是Entry，增加ipady
            elif isinstance(widget, tk.Entry):
                widget.config(relief='solid', bd=2)  # 增加边框便于点击
                
            print(f"[触摸优化] 控件优化完成: {type(widget).__name__}")
            
        except Exception as e:
            print(f"[触摸优化] 控件优化失败: {e}")
    
    @staticmethod
    def create_touch_button(parent, text, command, **kwargs):
        """
        创建触摸优化的按钮
        
        Args:
            parent: 父容器
            text: 按钮文本
            command: 点击命令
            **kwargs: 其他按钮参数
        
        Returns:
            tk.Button: 优化后的按钮
        """
        # 默认触摸优化参数
        default_config = {
            'font': ('微软雅黑', 12, 'bold'),
            'padx': 20,
            'pady': 12,
            'relief': 'flat',
            'bd': 0,
            'cursor': 'hand2'
        }
        
        # 合并用户参数
        button_config = {**default_config, **kwargs}
        
        button = tk.Button(parent, text=text, command=command, **button_config)
        
        # 添加触摸反馈效果
        def on_press(event):
            button.config(relief='sunken')
        
        def on_release(event):
            button.config(relief='flat')
        
        button.bind('<Button-1>', on_press)
        button.bind('<ButtonRelease-1>', on_release)
        
        return button


# 测试函数
def test_virtual_keyboard():
    """测试虚拟键盘功能"""
    print("测试虚拟键盘调用...")
    TouchScreenUtils.show_virtual_keyboard()


# 简单的测试界面
def create_test_window():
    """创建测试窗口"""
    root = tk.Tk()
    root.title("触摸屏测试")
    root.geometry("400x300")
    
    # 优化窗口
    TouchScreenUtils.optimize_window_for_touch(root)
    
    # 测试输入框
    entry = tk.Entry(root, font=('微软雅黑', 14), width=30)
    entry.pack(pady=20, ipady=10)
    TouchScreenUtils.setup_touch_entry(entry, "点击此处测试虚拟键盘")
    
    # 测试按钮
    test_btn = TouchScreenUtils.create_touch_button(
        root, 
        "测试虚拟键盘", 
        TouchScreenUtils.show_virtual_keyboard,
        bg='#4a90e2',
        fg='white'
    )
    test_btn.pack(pady=10)
    
    # 退出按钮
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
    # 当直接运行此文件时，启动测试界面
    print("启动触摸屏测试界面...")
    create_test_window()