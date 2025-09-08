#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟键盘模块
文件名：virtual_keyboard.py

提供自定义虚拟键盘功能
- 完全自定义的键盘界面
- 智能位置计算
- 支持数字和全键盘模式
"""

import tkinter as tk
from typing import Optional, Callable, Dict, Any

class VirtualKeyboard:
    """虚拟键盘组件"""
    
    def __init__(self, parent, keyboard_type="numeric"):
        self.parent = parent
        self.keyboard_type = keyboard_type
        self.keyboard_window = None
        self.target_entry = None
        self.on_input_callback = None
        
        # 键盘布局定义
        self.layouts = {
            "numeric": [
                ['1', '2', '3'],
                ['4', '5', '6'], 
                ['7', '8', '9'],
                ['清除', '0', '删除'],
                ['隐藏', '.', '确认']
            ],
            "full": [
                ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '删除'],
                ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
                ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
                ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '.', '-'],
                ['隐藏', '空格', '清除', '确认']
            ]
        }
    
    def show_keyboard(self, target_entry, x=None, y=None, callback=None):
        """显示虚拟键盘"""
        if self.keyboard_window:
            self.hide_keyboard()
        
        self.target_entry = target_entry
        self.on_input_callback = callback
        
        # 创建键盘窗口
        self.keyboard_window = tk.Toplevel(self.parent)
        self.keyboard_window.title("虚拟键盘")
        self.keyboard_window.configure(bg='#f0f0f0')
        self.keyboard_window.resizable(False, False)
        self.keyboard_window.attributes('-topmost', True)
        
        # 移除窗口装饰
        self.keyboard_window.overrideredirect(True)
        
        # 创建键盘布局
        self._create_keyboard_layout()
        
        # 计算键盘位置
        if x is None or y is None:
            x, y = self._calculate_keyboard_position(target_entry)
        
        # 设置键盘位置
        self.keyboard_window.geometry(f"+{x}+{y}")
        
        print(f"[虚拟键盘] 显示键盘，位置: ({x}, {y})")
    
    def hide_keyboard(self):
        """隐藏虚拟键盘"""
        if self.keyboard_window:
            try:
                self.keyboard_window.destroy()
                self.keyboard_window = None
                self.target_entry = None
                print("[虚拟键盘] 键盘已隐藏")
            except:
                pass
    
    def _create_keyboard_layout(self):
        """创建键盘布局"""
        layout = self.layouts[self.keyboard_type]
        
        # 主容器
        main_frame = tk.Frame(self.keyboard_window, bg='#f0f0f0', padx=5, pady=5)
        main_frame.pack()
        
        # 创建按键
        for row_idx, row in enumerate(layout):
            row_frame = tk.Frame(main_frame, bg='#f0f0f0')
            row_frame.pack(pady=2)
            
            for col_idx, key in enumerate(row):
                self._create_key_button(row_frame, key)
    
    def _create_key_button(self, parent, key_text):
        """创建单个按键"""
        # 特殊按键样式
        special_keys = ['删除', '清除', '确认', '隐藏', '空格']
        is_special = key_text in special_keys
        
        # 按键尺寸
        if key_text == '空格':
            width = 12
        elif is_special:
            width = 8
        else:
            width = 6
        
        # 按键颜色
        if key_text == '确认':
            bg_color = '#28a745'
            fg_color = 'white'
        elif key_text == '删除':
            bg_color = '#dc3545'
            fg_color = 'white'
        elif is_special:
            bg_color = '#6c757d'
            fg_color = 'white'
        else:
            bg_color = '#ffffff'
            fg_color = '#333333'
        
        # 创建按钮
        btn = tk.Button(
            parent,
            text=key_text,
            font=('微软雅黑', 12, 'bold'),
            bg=bg_color,
            fg=fg_color,
            relief='raised',
            bd=2,
            width=width,
            height=2,
            command=lambda k=key_text: self._on_key_press(k)
        )
        btn.pack(side=tk.LEFT, padx=1)
        
        # 按键效果
        def on_press(event, button=btn):
            button.configure(relief='sunken')
            
        def on_release(event, button=btn):
            button.configure(relief='raised')
        
        btn.bind('<Button-1>', on_press)
        btn.bind('<ButtonRelease-1>', on_release)
    
    def _on_key_press(self, key):
        """处理按键事件"""
        if not self.target_entry:
            return
        
        try:
            if key == '删除':
                current_text = self.target_entry.get()
                if current_text:
                    self.target_entry.delete(len(current_text)-1)
            
            elif key == '清除':
                self.target_entry.delete(0, tk.END)
            
            elif key == '确认':
                if self.on_input_callback:
                    self.on_input_callback(self.target_entry.get())
                self.hide_keyboard()
            
            elif key == '隐藏':
                self.hide_keyboard()
            
            elif key == '空格':
                self.target_entry.insert(tk.END, ' ')
            
            else:
                # 普通字符输入
                self.target_entry.insert(tk.END, key)
            
            print(f"[虚拟键盘] 按键: {key}, 当前内容: {self.target_entry.get()}")
            
        except Exception as e:
            print(f"[虚拟键盘] 按键处理错误: {e}")
    
    def _calculate_keyboard_position(self, target_entry):
        """计算键盘最佳位置，避免遮挡输入框"""
        try:
            # 更新布局信息
            target_entry.update_idletasks()
            self.parent.update_idletasks()
            
            # 获取输入框位置和尺寸
            entry_x = target_entry.winfo_rootx()
            entry_y = target_entry.winfo_rooty()
            entry_width = target_entry.winfo_width()
            entry_height = target_entry.winfo_height()
            
            # 获取屏幕尺寸
            screen_width = self.parent.winfo_screenwidth()
            screen_height = self.parent.winfo_screenheight()
            
            # 估算键盘尺寸
            if self.keyboard_type == "numeric":
                keyboard_width = 250
                keyboard_height = 300
            else:
                keyboard_width = 600
                keyboard_height = 250
            
            # 计算最佳位置
            # 优先在输入框下方显示
            preferred_x = entry_x
            preferred_y = entry_y + entry_height + 10
            
            # 检查右边界
            if preferred_x + keyboard_width > screen_width:
                preferred_x = screen_width - keyboard_width - 20
            
            # 检查下边界，如果超出则在输入框上方显示
            if preferred_y + keyboard_height > screen_height:
                preferred_y = entry_y - keyboard_height - 10
                
                # 如果上方也放不下，则在屏幕中央显示
                if preferred_y < 0:
                    preferred_x = (screen_width - keyboard_width) // 2
                    preferred_y = (screen_height - keyboard_height) // 2
            
            # 确保不超出边界
            preferred_x = max(10, min(preferred_x, screen_width - keyboard_width - 10))
            preferred_y = max(10, min(preferred_y, screen_height - keyboard_height - 10))
            
            return int(preferred_x), int(preferred_y)
            
        except Exception as e:
            print(f"[虚拟键盘] 位置计算错误: {e}")
            # 默认居中显示
            return 400, 300

class VirtualKeyboardEntry:
    """支持虚拟键盘的智能输入框"""
    
    def __init__(self, parent, keyboard_type="numeric", **kwargs):
        self.parent = parent
        self.keyboard_type = keyboard_type
        self.keyboard = None
        self.on_input_complete = None
        
        # 创建输入框
        self.entry = tk.Entry(parent, **kwargs)
        
        # 绑定事件
        self.entry.bind('<Button-1>', self._on_click)
    
    def _on_click(self, event):
        """点击事件处理"""
        self._show_keyboard()
    
    def _show_keyboard(self):
        """显示虚拟键盘"""
        try:
            # 创建键盘实例
            if not self.keyboard:
                self.keyboard = VirtualKeyboard(self.parent, self.keyboard_type)
            
            # 显示键盘
            self.keyboard.show_keyboard(
                self.entry,
                callback=self._on_input_complete
            )
            
        except Exception as e:
            print(f"[虚拟键盘输入框] 显示键盘错误: {e}")
    
    def _on_input_complete(self, text):
        """输入完成处理"""
        print(f"[虚拟键盘输入框] 输入完成: {text}")
        
        if self.on_input_complete:
            self.on_input_complete(text)
    
    def set_input_complete_callback(self, callback):
        """设置输入完成回调"""
        self.on_input_complete = callback
    
    def hide_keyboard(self):
        """隐藏键盘"""
        if self.keyboard:
            self.keyboard.hide_keyboard()
    
    # 包装Entry的所有方法
    def pack(self, **kwargs):
        return self.entry.pack(**kwargs)
    
    def grid(self, **kwargs):
        return self.entry.grid(**kwargs)
    
    def place(self, **kwargs):
        return self.entry.place(**kwargs)
    
    def get(self):
        return self.entry.get()
    
    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(value))
    
    def delete(self, start, end=None):
        return self.entry.delete(start, end)
    
    def insert(self, index, text):
        return self.entry.insert(index, text)
    
    def configure(self, **kwargs):
        return self.entry.configure(**kwargs)
    
    def config(self, **kwargs):
        return self.entry.config(**kwargs)
    
    def bind(self, event, callback):
        return self.entry.bind(event, callback)
    
    def focus_set(self):
        return self.entry.focus_set()
