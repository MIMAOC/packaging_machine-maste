#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置界面
包装机系统设置管理界面

功能特点：
1. 物料管理
2. 生产记录
3. 出厂设置

文件名：system_settings_interface.py
作者：AI助手
创建日期：2025-08-05
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont


class SystemSettingsInterface:
    """
    系统设置界面类
    
    负责：
    1. 创建系统设置的用户界面
    2. 处理各个功能模块的跳转
    3. 管理界面显示和隐藏
    """
    
    def __init__(self, parent=None, ai_mode_window=None):
        """
        初始化系统设置界面
        
        Args:
            parent: 父窗口对象
            ai_mode_window: AI模式界面引用，用于返回时显示
        """
        # 保存AI模式界面引用
        self.ai_mode_window = ai_mode_window
        
        # 创建主窗口
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        # 设置窗口属性
        self.setup_window()
        
        # 设置字体
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 居中显示窗口
        self.center_window()
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.title("系统设置")
        self.root.geometry("950x750")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置界面字体"""
        # 标题字体
        self.title_font = tkFont.Font(family="微软雅黑", size=20, weight="bold")
        
        # 按钮字体
        self.button_font = tkFont.Font(family="微软雅黑", size=16, weight="bold")
        
        # 描述字体
        self.desc_font = tkFont.Font(family="微软雅黑", size=12)
        
        # 小按钮字体
        self.small_button_font = tkFont.Font(family="微软雅黑", size=10)
        
        # 底部信息字体
        self.footer_font = tkFont.Font(family="微软雅黑", size=10)
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=30)
        
        # 创建标题栏
        self.create_title_bar(main_frame)
        
        # 创建功能按钮区域
        self.create_function_buttons(main_frame)
        
        # 创建底部信息区域
        self.create_footer_section(main_frame)
    
    def create_title_bar(self, parent):
        """
        创建标题栏
        
        Args:
            parent: 父容器
        """
        # 标题栏容器
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧标题
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        # 系统设置标题
        title_label = tk.Label(left_frame, text="系统设置", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # 右侧返回按钮
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        # 返回AI模式按钮
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_click)
        return_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线（放在标题栏下方）
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 40))
    
    def create_function_buttons(self, parent):
        """
        创建功能按钮区域
        
        Args:
            parent: 父容器
        """
        # 功能按钮容器
        function_frame = tk.Frame(parent, bg='white')
        function_frame.pack(expand=True, fill='both', pady=(50, 100))
        
        # 三个功能按钮的容器（水平排列）
        buttons_container = tk.Frame(function_frame, bg='white')
        buttons_container.pack(expand=True)
        
        # 物料管理按钮
        self.create_function_button(buttons_container, 
                                   "物料管理", 
                                   "新增物料并启动AI学习\n查看AI状态和管理物料启用",
                                   self.on_material_management_click,
                                   side=tk.LEFT, padx=(0, 60))
        
        # 生产记录按钮
        self.create_function_button(buttons_container, 
                                   "生产记录", 
                                   "查看历史生产数据和合格率\n按时间和条件搜索记录",
                                   self.on_production_records_click,
                                   side=tk.LEFT, padx=(0, 60))
        
        # 出厂设置按钮
        self.create_function_button(buttons_container, 
                                   "出厂设置", 
                                   "设定重量误差报警阈值\n需要管理员密码验证",
                                   self.on_factory_settings_click,
                                   side=tk.LEFT)
    
    def create_function_button(self, parent, title, description, command, side=tk.LEFT, padx=0):
        """
        创建功能按钮
        
        Args:
            parent: 父容器
            title: 按钮标题
            description: 按钮描述
            command: 点击回调函数
            side: 布局方向
            padx: 水平间距
        """
        # 按钮容器
        button_container = tk.Frame(parent, bg='#d3d3d3', relief='flat', bd=0)
        button_container.pack(side=side, padx=padx)
        button_container.configure(width=250, height=180)
        button_container.pack_propagate(False)
        
        # 创建按钮内容
        content_frame = tk.Frame(button_container, bg='#d3d3d3')
        content_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(content_frame, text=title, 
                              font=self.button_font, bg='#d3d3d3', fg='#333333')
        title_label.pack(pady=(20, 10))
        
        # 描述
        desc_label = tk.Label(content_frame, text=description, 
                             font=self.desc_font, bg='#d3d3d3', fg='#666666',
                             justify=tk.CENTER)
        desc_label.pack(pady=(0, 20))
        
        # 绑定点击事件
        def bind_click_event(widget):
            widget.bind("<Button-1>", lambda e: command())
            widget.bind("<Enter>", lambda e: self.on_button_enter(button_container))
            widget.bind("<Leave>", lambda e: self.on_button_leave(button_container))
        
        bind_click_event(button_container)
        bind_click_event(content_frame)
        bind_click_event(title_label)
        bind_click_event(desc_label)
    
    def on_button_enter(self, button_container):
        """鼠标悬停效果"""
        button_container.config(bg='#b0b0b0')
        for child in button_container.winfo_children():
            child.config(bg='#b0b0b0')
            for grandchild in child.winfo_children():
                grandchild.config(bg='#b0b0b0')
    
    def on_button_leave(self, button_container):
        """鼠标离开效果"""
        button_container.config(bg='#d3d3d3')
        for child in button_container.winfo_children():
            child.config(bg='#d3d3d3')
            for grandchild in child.winfo_children():
                grandchild.config(bg='#d3d3d3')
    
    def create_footer_section(self, parent):
        """
        创建底部信息区域
        
        Args:
            parent: 父容器
        """
        # 底部信息容器
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        # 版本信息
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        # 公司logo区域
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        # 导入并使用logo处理器
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
            print("[SystemSettings] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
    def center_window(self):
        """将窗口居中显示"""
        try:
            # 确保窗口已经完全创建
            self.root.update_idletasks()
            
            # 获取窗口尺寸
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            # 如果窗口尺寸为1（未正确获取），使用设定的尺寸
            if width <= 1 or height <= 1:
                width = 950
                height = 750
            
            # 计算居中位置
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            # 设置窗口位置
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            print(f"系统设置界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("950x750")
    
    # 按钮事件处理函数
    
    def on_material_management_click(self):
        """物料管理按钮点击事件"""
        print("点击了物料管理")
        try:
            # 隐藏系统设置界面
            self.root.withdraw()
            
            # 导入并创建物料管理界面
            from material_management_interface import MaterialManagementInterface
            material_interface = MaterialManagementInterface(parent=self.root, 
                                                            ai_mode_window=self.ai_mode_window)
            print("物料管理界面已打开，系统设置界面已隐藏")
        except Exception as e:
            # 如果出错，重新显示系统设置界面
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开物料管理界面失败：{str(e)}")
    
    def on_production_records_click(self):
        """生产记录按钮点击事件"""
        print("点击了生产记录")
        try:
            # 隐藏系统设置界面
            self.root.withdraw()
            
            # 导入并创建生产记录界面
            from production_records_interface import ProductionRecordsInterface
            records_interface = ProductionRecordsInterface(parent=self.root, 
                                                         system_settings_window=self)
            print("生产记录界面已打开，系统设置界面已隐藏")
        except Exception as e:
            # 如果出错，重新显示系统设置界面
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开生产记录界面失败：{str(e)}")
    
    def on_factory_settings_click(self):
        """出厂设置按钮点击事件"""
        print("点击了出厂设置")
        try:
            # 隐藏系统设置界面
            self.root.withdraw()
            
            # 导入并创建出厂设置界面
            from factory_settings_interface import FactorySettingsInterface
            factory_interface = FactorySettingsInterface(parent=self.root, 
                                                       system_settings_window=self)
            print("出厂设置界面已打开，系统设置界面已隐藏")
        except Exception as e:
            # 如果出错，重新显示系统设置界面
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开出厂设置界面失败：{str(e)}")
    
    def on_return_click(self):
        """返回AI模式按钮点击事件"""
        print("点击了返回AI模式")
        
        # 如果有AI模式界面引用，重新显示AI模式界面
        if self.ai_mode_window:
            try:
                # 显示AI模式界面
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
                print("AI模式界面已显示")
            except Exception as e:
                print(f"显示AI模式界面时发生错误: {e}")
        
        # 关闭系统设置界面
        self.root.destroy()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 如果有AI模式界面引用，重新显示AI模式界面
        if self.ai_mode_window:
            try:
                # 显示AI模式界面
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
                print("AI模式界面已显示")
            except Exception as e:
                print(f"显示AI模式界面时发生错误: {e}")
        
        # 关闭系统设置界面
        self.root.destroy()
    
    def show(self):
        """显示界面（如果是主窗口）"""
        if self.is_main_window:
            self.root.mainloop()


def main():
    """
    主函数 - 程序入口点（用于测试）
    """
    # 创建系统设置界面实例
    settings_interface = SystemSettingsInterface()
    
    # 显示界面
    settings_interface.show()


# 当作为主程序运行时，启动界面
if __name__ == "__main__":
    main()