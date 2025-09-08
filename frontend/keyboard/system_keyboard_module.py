#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统键盘模块
文件名：system_keyboard.py

提供系统自带键盘功能
- 调用系统原生键盘
- 跨平台支持
- 自动检测可用键盘程序
"""

import tkinter as tk
import subprocess
import platform
import os
import threading
import time
from typing import Optional, Callable

class SystemKeyboardController:
    """系统键盘控制器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.keyboard_process = None
        self.is_keyboard_visible = False
        
        # 检测平台和可用的键盘程序
        self._detect_keyboard_program()
    
    def _detect_keyboard_program(self):
        """检测系统可用的键盘程序"""
        self.keyboard_cmd = None
        
        if self.system == "windows":
            # Windows系统
            self.keyboard_cmd = self._get_windows_keyboard_cmd()
        elif self.system == "linux":
            # Linux系统
            self.keyboard_cmd = self._get_linux_keyboard_cmd()
        elif "android" in self.system or os.getenv('ANDROID_ROOT'):
            # Android系统
            self.keyboard_cmd = self._get_android_keyboard_cmd()
        else:
            print(f"[系统键盘] 不支持的系统: {self.system}")
    
    def _get_windows_keyboard_cmd(self):
        """获取Windows键盘命令"""
        # Windows 10/11 触摸键盘
        touch_keyboard = r"C:\Program Files\Common Files\microsoft shared\ink\TabTip.exe"
        if os.path.exists(touch_keyboard):
            return ["cmd", "/c", "start", "", touch_keyboard]
        
        # 备用：屏幕键盘
        osk_path = r"C:\Windows\System32\osk.exe"
        if os.path.exists(osk_path):
            return [osk_path]
        
        return None
    
    def _get_linux_keyboard_cmd(self):
        """获取Linux键盘命令"""
        # 尝试常见的虚拟键盘程序
        keyboards = [
            "onboard",      # Ubuntu默认
            "florence",     # GNOME
            "matchbox-keyboard",  # 轻量级
            "xvkbd",        # X11虚拟键盘
            "kvkbd"         # KDE虚拟键盘
        ]
        
        for kb in keyboards:
            try:
                # 检查程序是否存在
                result = subprocess.run(["which", kb], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=2)
                if result.returncode == 0:
                    return [kb]
            except:
                continue
        
        return None
    
    def _get_android_keyboard_cmd(self):
        """获取Android键盘命令"""
        # Android通过InputMethodManager控制
        return ["am", "broadcast", "-a", "android.intent.action.CLOSE_SYSTEM_DIALOGS"]
    
    def show_keyboard(self, keyboard_type="default"):
        """显示系统键盘"""
        if not self.keyboard_cmd:
            print("[系统键盘] 未找到可用的键盘程序")
            return False
        
        if self.is_keyboard_visible:
            return True
        
        try:
            if self.system == "windows":
                self._show_windows_keyboard(keyboard_type)
            elif self.system == "linux":
                self._show_linux_keyboard(keyboard_type)
            elif "android" in self.system:
                self._show_android_keyboard()
            
            self.is_keyboard_visible = True
            print(f"[系统键盘] 键盘已显示 - {keyboard_type}")
            return True
            
        except Exception as e:
            print(f"[系统键盘] 显示键盘失败: {e}")
            return False
    
    def hide_keyboard(self):
        """隐藏系统键盘"""
        if not self.is_keyboard_visible:
            return True
        
        try:
            if self.system == "windows":
                self._hide_windows_keyboard()
            elif self.system == "linux":
                self._hide_linux_keyboard()
            elif "android" in self.system:
                self._hide_android_keyboard()
            
            self.is_keyboard_visible = False
            print("[系统键盘] 键盘已隐藏")
            return True
            
        except Exception as e:
            print(f"[系统键盘] 隐藏键盘失败: {e}")
            return False
    
    def _show_windows_keyboard(self, keyboard_type):
        """显示Windows键盘"""
        if "TabTip.exe" in str(self.keyboard_cmd):
            # 触摸键盘需要特殊处理
            self._show_windows_touch_keyboard()
        else:
            # 屏幕键盘
            self.keyboard_process = subprocess.Popen(
                self.keyboard_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    
    def _show_windows_touch_keyboard(self):
        """显示Windows触摸键盘"""
        try:
            # 方法1: 直接启动TouchKeyboard
            subprocess.run([
                "powershell", "-Command",
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.InputPanel]::new().Enabled = $true"
            ], timeout=3)
        except:
            try:
                # 方法2: 通过注册表启用
                subprocess.run([
                    "reg", "add", 
                    "HKCU\\Software\\Microsoft\\TabletTip\\1.7",
                    "/v", "EnableDesktopModeAutoInvoke", "/t", "REG_DWORD", "/d", "1", "/f"
                ], timeout=3)
                
                # 启动TabTip
                subprocess.Popen([
                    "C:\\Program Files\\Common Files\\microsoft shared\\ink\\TabTip.exe"
                ])
            except Exception as e:
                print(f"[系统键盘] Windows触摸键盘启动失败: {e}")
    
    def _hide_windows_keyboard(self):
        """隐藏Windows键盘"""
        try:
            # 关闭屏幕键盘进程
            subprocess.run(["taskkill", "/f", "/im", "osk.exe"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            
            # 关闭触摸键盘进程
            subprocess.run(["taskkill", "/f", "/im", "TabTip.exe"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        except:
            pass
        
        if self.keyboard_process:
            try:
                self.keyboard_process.terminate()
                self.keyboard_process = None
            except:
                pass
    
    def _show_linux_keyboard(self, keyboard_type):
        """显示Linux键盘"""
        cmd = self.keyboard_cmd.copy()
        
        # 根据键盘类型添加参数
        if "onboard" in cmd[0]:
            if keyboard_type == "numeric":
                cmd.extend(["--layout", "Compact"])
        elif "florence" in cmd[0]:
            if keyboard_type == "numeric":
                cmd.extend(["--layout", "numpad"])
        
        self.keyboard_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    def _hide_linux_keyboard(self):
        """隐藏Linux键盘"""
        if self.keyboard_process:
            try:
                self.keyboard_process.terminate()
                self.keyboard_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.keyboard_process.kill()
            except:
                pass
            finally:
                self.keyboard_process = None
        
        # 确保关闭所有键盘进程
        keyboard_procs = ["onboard", "florence", "matchbox-keyboard", "xvkbd", "kvkbd"]
        for proc in keyboard_procs:
            try:
                subprocess.run(["pkill", proc], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
            except:
                pass
    
    def _show_android_keyboard(self):
        """显示Android键盘"""
        try:
            # Android上需要通过Intent调用输入法
            subprocess.run([
                "am", "start", "-a", "android.intent.action.VIEW",
                "-d", "content://settings/secure",
                "com.android.settings/.inputmethod.InputMethodAndLanguageSettings"
            ], timeout=3)
        except Exception as e:
            print(f"[系统键盘] Android键盘调用失败: {e}")
    
    def _hide_android_keyboard(self):
        """隐藏Android键盘"""
        try:
            subprocess.run([
                "input", "keyevent", "KEYCODE_BACK"
            ], timeout=2)
        except:
            pass

class SystemKeyboardEntry:
    """支持系统键盘的智能输入框"""
    
    def __init__(self, parent, keyboard_type="default", auto_hide=True, **kwargs):
        self.parent = parent
        self.keyboard_type = keyboard_type
        self.auto_hide = auto_hide
        self.keyboard_controller = SystemKeyboardController()
        
        # 创建输入框
        self.entry = tk.Entry(parent, **kwargs)
        
        # 绑定事件
        self.entry.bind('<Button-1>', self._on_click)
        self.entry.bind('<FocusIn>', self._on_focus_in)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        
        # 输入完成回调
        self.on_input_complete = None
        
        # 绑定回车键
        self.entry.bind('<Return>', self._on_enter)
    
    def _on_click(self, event):
        """点击事件"""
        self._show_keyboard()
    
    def _on_focus_in(self, event):
        """获得焦点"""
        # 延迟显示键盘，避免程序启动时误触发
        self.parent.after(100, self._show_keyboard)
    
    def _on_focus_out(self, event):
        """失去焦点"""
        if self.auto_hide:
            self.parent.after(500, self._hide_keyboard_if_needed)
    
    def _on_enter(self, event):
        """回车键处理"""
        if self.on_input_complete:
            self.on_input_complete(self.entry.get())
        self._hide_keyboard()
    
    def _show_keyboard(self):
        """显示键盘"""
        self.keyboard_controller.show_keyboard(self.keyboard_type)
    
    def _hide_keyboard_if_needed(self):
        """检查是否需要隐藏键盘"""
        try:
            # 检查当前焦点
            focused = self.parent.focus_get()
            if focused != self.entry:
                self.keyboard_controller.hide_keyboard()
        except:
            pass
    
    def _hide_keyboard(self):
        """强制隐藏键盘"""
        self.keyboard_controller.hide_keyboard()
    
    def set_input_complete_callback(self, callback):
        """设置输入完成回调"""
        self.on_input_complete = callback
    
    def hide_keyboard(self):
        """公开方法：隐藏键盘"""
        self._hide_keyboard()
    
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
