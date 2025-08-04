#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的Logo图片处理模块
负责加载logo图片并创建可点击的logo组件

功能特点：
1. 加载algorumla.png和tianteng.png图片
2. 创建可点击的logo组件
3. 实现点击弹出联系信息功能
4. 适配不同窗口尺寸

作者：AI助手
创建日期：2025-08-04
"""

import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkFont
from PIL import Image, ImageTk
import os

class LogoHandler:
    """Logo处理器类"""
    
    def __init__(self):
        self.algorumla_image = None
        self.tianteng_image = None
        self.load_images()
    
    def load_images(self):
        """加载logo图片"""
        try:
            # 加载algorumla.png
            if os.path.exists("algormula.png"):
                algorumla_pil = Image.open("algormula.png")
                # 调整图片大小以适配界面
                algorumla_pil = algorumla_pil.resize((80, 20), Image.Resampling.LANCZOS)
                self.algorumla_image = ImageTk.PhotoImage(algorumla_pil)
                print("[Logo] algormula.png 加载成功")
            else:
                print("[警告] algormula.png 文件不存在")
            
            # 加载tianteng.png  
            if os.path.exists("tianteng.png"):
                tianteng_pil = Image.open("tianteng.png")
                # 调整图片大小以适配界面
                tianteng_pil = tianteng_pil.resize((80, 10), Image.Resampling.LANCZOS)
                self.tianteng_image = ImageTk.PhotoImage(tianteng_pil)
                print("[Logo] tianteng.png 加载成功")
            else:
                print("[警告] tianteng.png 文件不存在")
                
        except Exception as e:
            print(f"[错误] 加载logo图片异常: {e}")
    
    def show_contact_dialog(self, parent_window):
        """显示联系信息弹窗"""
        try:
            # 创建联系信息弹窗
            contact_window = tk.Toplevel(parent_window)
            contact_window.title("联系我们")
            contact_window.geometry("600x400")
            contact_window.configure(bg='white')
            contact_window.resizable(False, False)
            contact_window.transient(parent_window)
            contact_window.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_parent(contact_window, parent_window, 600, 400)
            
            # 联系信息内容
            tk.Label(contact_window, text="如需更多信息 请电话联系我们", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='white', fg='#333333').pack(pady=40)
            
            # 电话号码1
            tk.Label(contact_window, text="138 0680 0177", 
                    font=tkFont.Font(family="Arial", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=10)
            
            # 电话号码2  
            tk.Label(contact_window, text="133 7257 1638", 
                    font=tkFont.Font(family="Arial", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=10)
            
            # 关闭按钮
            tk.Button(contact_window, text="关闭", 
                     font=tkFont.Font(family="微软雅黑", size=12),
                     bg='#6c757d', fg='white',
                     relief='flat', bd=0,
                     padx=30, pady=10,
                     command=contact_window.destroy).pack(pady=30)
            
            print("[Logo] 显示联系信息弹窗")
            
        except Exception as e:
            print(f"[错误] 显示联系信息弹窗异常: {e}")
            messagebox.showerror("系统错误", f"显示联系信息时发生错误：{str(e)}")
    
    def center_dialog_relative_to_parent(self, dialog_window, parent_window, dialog_width, dialog_height):
        """将弹窗相对于父窗口居中显示"""
        try:
            # 确保窗口信息是最新的
            dialog_window.update_idletasks()
            parent_window.update_idletasks()

            # 获取父窗口的位置和尺寸
            parent_x = parent_window.winfo_x()
            parent_y = parent_window.winfo_y()
            parent_width = parent_window.winfo_width()
            parent_height = parent_window.winfo_height()

            # 计算相对于父窗口居中的位置
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2

            # 确保弹窗不会超出屏幕边界
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
            print(f"[错误] 弹窗居中失败: {e}")
    
    def create_logo_components(self, parent_frame, bg_color='white'):
        """
        创建logo组件
        
        Args:
            parent_frame: 父容器
            bg_color: 背景颜色
            
        Returns:
            tuple: (algorumla_component, tianteng_component)
        """
        try:
            # 创建logo容器
            logo_frame = tk.Frame(parent_frame, bg=bg_color)
            logo_frame.pack()
            
            algorumla_component = None
            tianteng_component = None
            
            # 创建algorumla logo组件
            if self.algorumla_image:
                algorumla_component = tk.Label(logo_frame, image=self.algorumla_image, 
                                             bg=bg_color, cursor='hand2')
                algorumla_component.pack(side=tk.LEFT, padx=(0, 20))
                
                # 绑定点击事件
                def on_algorumla_click(event):
                    # 找到顶级窗口
                    parent_window = parent_frame.winfo_toplevel()
                    self.show_contact_dialog(parent_window)
                
                algorumla_component.bind("<Button-1>", on_algorumla_click)
            else:
                print(f"[错误] 创建失败")
            
            # 创建tianteng logo组件
            if self.tianteng_image:
                tianteng_component = tk.Label(logo_frame, image=self.tianteng_image, 
                                            bg=bg_color, cursor='hand2')
                tianteng_component.pack(side=tk.LEFT)
                
                # 绑定点击事件
                def on_tianteng_click(event):
                    parent_window = parent_frame.winfo_toplevel()
                    self.show_contact_dialog(parent_window)
                
                tianteng_component.bind("<Button-1>", on_tianteng_click)
            else:
                # 备用文本显示
                print(f"[错误] 创建失败")
            
            return algorumla_component, tianteng_component
            
        except Exception as e:
            print(f"[错误] 创建logo组件异常: {e}")
            return None, None

# 创建全局logo处理器实例
logo_handler = LogoHandler()

def create_logo_components(parent_frame, bg_color='white'):
    """
    创建logo组件的便捷函数
    
    Args:
        parent_frame: 父容器
        bg_color: 背景颜色
        
    Returns:
        tuple: (algorumla_component, tianteng_component)
    """
    return logo_handler.create_logo_components(parent_frame, bg_color)