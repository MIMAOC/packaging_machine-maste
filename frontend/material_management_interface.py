#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物料管理界面
包装机系统物料管理界面

功能特点：
1. 物料列表显示
2. 启用/禁用物料
3. 再学习功能
4. 新建物料
5. 分页显示

文件名：material_management_interface.py
作者：AI助手
创建日期：2025-08-05
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
from typing import List

# 导入数据库相关模块
try:
    from database.material_dao import MaterialDAO, Material
    from database.db_connection import db_manager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入数据库模块: {e}")
    DATABASE_AVAILABLE = False


class MaterialManagementInterface:
    """
    物料管理界面类
    
    负责：
    1. 创建物料管理的用户界面
    2. 从数据库读取和显示物料数据
    3. 处理物料的启用/禁用操作
    4. 处理再学习功能
    5. 处理新建物料功能
    """
    
    def __init__(self, parent=None, ai_mode_window=None):
        """
        初始化物料管理界面
        
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
        
        # 物料数据
        self.materials = []
        self.current_page = 1
        self.items_per_page = 5
        self.total_pages = 1
        
        # 设置窗口属性
        self.setup_window()
        
        # 设置字体
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 加载物料数据
        self.load_materials()
        
        # 居中显示窗口
        self.center_window()
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.title("物料管理")
        self.root.geometry("950x750")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置界面字体"""
        # 标题字体
        self.title_font = tkFont.Font(family="微软雅黑", size=20, weight="bold")
        
        # 表头字体
        self.header_font = tkFont.Font(family="微软雅黑", size=14, weight="bold")
        
        # 内容字体
        self.content_font = tkFont.Font(family="微软雅黑", size=12)
        
        # 按钮字体
        self.button_font = tkFont.Font(family="微软雅黑", size=10)
        
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
        
        # 创建物料列表区域
        self.create_material_list_area(main_frame)
        
        # 创建底部控制区域
        self.create_bottom_controls(main_frame)
        
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
        
        # 物料管理标题
        title_label = tk.Label(left_frame, text="物料管理", 
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
        separator.pack(fill=tk.X, pady=(0, 20))
    
    def create_material_list_area(self, parent):
        """
        创建物料列表区域
        
        Args:
            parent: 父容器
        """
        # 列表容器
        list_container = tk.Frame(parent, bg='white', relief='solid', bd=1)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(20, 20))
        
        # 表头
        header_frame = tk.Frame(list_container, bg='#f8f9fa', height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # 表头内容
        headers = [
            ("物料信息", 0.3),
            ("AI状态", 0.15),
            ("创建时间", 0.2),
            ("操作", 0.35)
        ]
        
        for i, (header_text, width_ratio) in enumerate(headers):
            header_label = tk.Label(header_frame, text=header_text, 
                                   font=self.header_font, bg='#f8f9fa', fg='#333333')
            header_label.place(relx=sum(h[1] for h in headers[:i]), rely=0.5, 
                              relwidth=width_ratio, anchor='w')
        
        # 内容区域（可滚动）
        self.content_frame = tk.Frame(list_container, bg='white')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_bottom_controls(self, parent):
        """
        创建底部控制区域
        
        Args:
            parent: 父容器
        """
        # 底部控制容器
        bottom_frame = tk.Frame(parent, bg='white')
        bottom_frame.pack(fill=tk.X, pady=(10, 20))
        
        # 左侧新建物料按钮
        new_material_btn = tk.Button(bottom_frame, text="⊕ 新建物料", 
                                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                    bg='#007bff', fg='white',
                                    relief='flat', bd=0,
                                    padx=30, pady=10,
                                    command=self.on_new_material_click)
        new_material_btn.pack(side=tk.LEFT)
        
        # 右侧分页控制
        pagination_frame = tk.Frame(bottom_frame, bg='white')
        pagination_frame.pack(side=tk.RIGHT)

        # 上一页按钮
        self.prev_page_btn = tk.Button(pagination_frame, text="上一页", 
                                      font=self.button_font,
                                      bg='#e9ecef', fg='#333333',
                                      relief='flat', bd=1,
                                      padx=15, pady=5,
                                      command=self.prev_page,
                                      state='disabled')
        self.prev_page_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 分页信息
        self.page_info_label = tk.Label(pagination_frame, text="1/1", 
                                       font=self.content_font, bg='white', fg='#666666')
        self.page_info_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 下一页按钮
        self.next_page_btn = tk.Button(pagination_frame, text="下一页", 
                                      font=self.button_font,
                                      bg='#e9ecef', fg='#333333',
                                      relief='flat', bd=1,
                                      padx=15, pady=5,
                                      command=self.next_page,
                                      state='disabled')
        self.next_page_btn.pack(side=tk.LEFT)
    
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
            print("[MaterialManagement] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
    def load_materials(self):
        """从数据库加载物料数据"""
        try:
            if DATABASE_AVAILABLE:
                # 获取所有物料（包括禁用的）
                self.materials = MaterialDAO.get_all_materials(enabled_only=False)
                print(f"[信息] 从数据库加载了{len(self.materials)}个物料")
            else:
                # 模拟数据（如果数据库不可用）
                self.materials = []
                print("[警告] 数据库不可用，使用空列表")
            
            # 计算总页数
            self.total_pages = max(1, (len(self.materials) + self.items_per_page - 1) // self.items_per_page)
            
            # 刷新显示
            self.refresh_material_display()
            
        except Exception as e:
            print(f"[错误] 加载物料数据异常: {e}")
            messagebox.showerror("数据加载失败", f"加载物料数据失败：\n{str(e)}")
    
    def refresh_material_display(self):
        """刷新物料显示"""
        try:
            # 清空当前显示
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            # 计算当前页的数据范围
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = start_index + self.items_per_page
            page_materials = self.materials[start_index:end_index]
            
            # 显示物料行
            for i, material in enumerate(page_materials):
                self.create_material_row(self.content_frame, material, i)
            
            # 更新分页信息
            self.page_info_label.config(text=f"{self.current_page}/{self.total_pages}")
            
            # 更新上一页按钮状态
            if self.current_page > 1:
                self.prev_page_btn.config(state='normal')
            else:
                self.prev_page_btn.config(state='disabled')
            
            # 更新下一页按钮状态
            if self.current_page < self.total_pages:
                self.next_page_btn.config(state='normal')
            else:
                self.next_page_btn.config(state='disabled')
            
        except Exception as e:
            print(f"[错误] 刷新物料显示异常: {e}")
    
    def create_material_row(self, parent, material: Material, row_index: int):
        """
        创建物料行
        
        Args:
            parent: 父容器
            material: 物料对象
            row_index: 行索引
        """
        try:
            # 行容器
            row_frame = tk.Frame(parent, bg='white', height=65)
            row_frame.pack(fill=tk.X, pady=1)
            row_frame.pack_propagate(False)
            
            # 添加分隔线
            if row_index > 0:
                separator = tk.Frame(row_frame, height=1, bg='#e9ecef')
                separator.pack(fill=tk.X)
            
            # 内容容器
            content_frame = tk.Frame(row_frame, bg='white')
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 物料信息
            material_name_label = tk.Label(content_frame, text=material.material_name, 
                                          font=self.content_font, bg='white', fg='#333333')
            material_name_label.place(relx=0, rely=0.5, relwidth=0.3, anchor='w')
            
            # AI状态
            ai_status_label = tk.Label(content_frame, text=material.ai_status, 
                                      font=self.content_font, bg='white', fg='#333333')
            ai_status_label.place(relx=0.3, rely=0.5, relwidth=0.15, anchor='w')
            
            # 创建时间
            create_time_text = material.create_time.strftime("%Y-%m-%d") if material.create_time else "未知"
            create_time_label = tk.Label(content_frame, text=create_time_text, 
                                        font=self.content_font, bg='white', fg='#333333')
            create_time_label.place(relx=0.45, rely=0.5, relwidth=0.2, anchor='w')
            
            # 操作按钮区域
            operation_container = tk.Frame(content_frame, bg='white')
            operation_container.place(relx=0.65, rely=0, relwidth=0.35, relheight=1)

            # 按钮容器 - 水平居中排列
            button_container = tk.Frame(operation_container, bg='white')
            button_container.pack(expand=True)

            # 启用/禁用按钮
            enable_text = "启用" if material.is_enabled == 0 else "禁用"
            enable_color = "#28a745" if material.is_enabled == 0 else "#dc3545"
            enable_btn = tk.Button(button_container, text=enable_text, 
                                  font=self.button_font,
                                  bg=enable_color, fg='white',
                                  relief='flat', bd=0,
                                  padx=15, pady=5,
                                  command=lambda m=material: self.toggle_material_status(m))
            enable_btn.pack(side=tk.LEFT, padx=(0, 20))

            # 再学习按钮
            relearn_state = 'normal' if material.is_enabled == 1 else 'disabled'
            relearn_color = "#28a745" if material.is_enabled == 1 else "#cccccc"
            relearn_btn = tk.Button(button_container, text="再学习", 
                                   font=self.button_font,
                                   bg=relearn_color, fg='white',
                                   relief='flat', bd=0,
                                   padx=15, pady=5,
                                   state=relearn_state,
                                   command=lambda m=material: self.relearn_material(m))
            relearn_btn.pack(side=tk.LEFT)
            
        except Exception as e:
            print(f"[错误] 创建物料行异常: {e}")
    
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
            print(f"物料管理界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("950x750")
    
    # 事件处理函数
    
    def toggle_material_status(self, material: Material):
        """
        切换物料启用/禁用状态
        
        Args:
            material: 物料对象
        """
        try:
            if not DATABASE_AVAILABLE:
                messagebox.showwarning("数据库不可用", "数据库功能不可用，无法修改物料状态")
                return
            
            new_status = 0 if material.is_enabled == 1 else 1
            status_text = "启用" if new_status == 1 else "禁用"
            
            # 确认操作
            result = messagebox.askyesno("确认操作", f"确定要{status_text}物料'{material.material_name}'吗？")
            if not result:
                return
            
            # 更新数据库
            if new_status == 1:
                success, message = MaterialDAO.enable_material(material.id)
            else:
                success, message = MaterialDAO.disable_material(material.id)
            
            if success:
                print(f"[成功] {message}")
                # 重新加载数据并刷新显示
                self.load_materials()
                messagebox.showinfo("操作成功", f"物料'{material.material_name}'已{status_text}")
            else:
                print(f"[失败] {message}")
                messagebox.showerror("操作失败", f"{status_text}物料失败：\n{message}")
        
        except Exception as e:
            error_msg = f"切换物料状态异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("操作异常", error_msg)
    
    def relearn_material(self, material: Material):
        """
        重新学习物料
        
        Args:
            material: 物料对象
        """
        try:
            if material.is_enabled == 0:
                messagebox.showwarning("操作受限", "禁用状态的物料无法进行再学习")
                return
            
            # 确认操作
            result = messagebox.askyesno("确认再学习", 
                                       f"确定要对物料'{material.material_name}'进行再学习吗？\n\n"
                                       f"再学习将：\n"
                                       f"• 重置AI学习状态\n"
                                       f"• 重新开始学习过程\n"
                                       f"• 可能需要较长时间\n\n"
                                       f"此操作无法撤销，是否确认？")
            if not result:
                return
            
            # 更新AI状态为"未学习"
            if DATABASE_AVAILABLE:
                success, message = MaterialDAO.update_material_ai_status(material.id, "未学习")
                if success:
                    print(f"[成功] 物料'{material.material_name}'AI状态已重置为'未学习'")
                    # 重新加载数据并刷新显示
                    self.load_materials()
                    messagebox.showinfo("再学习启动", 
                                      f"物料'{material.material_name}'的再学习已启动！\n\n"
                                      f"AI状态已重置为'未学习'，可以在AI模式中重新选择此物料进行学习。")
                else:
                    print(f"[失败] {message}")
                    messagebox.showerror("再学习失败", f"启动再学习失败：\n{message}")
            else:
                messagebox.showwarning("数据库不可用", "数据库功能不可用，无法进行再学习")
        
        except Exception as e:
            error_msg = f"再学习操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("操作异常", error_msg)
    
    def on_new_material_click(self):
        """新建物料按钮点击事件"""
        print("点击了新建物料")
        self.show_new_material_name_dialog()
    
    def center_dialog_relative_to_main(self, dialog_window, dialog_width, dialog_height):
        """
        将弹窗相对于物料管理界面居中显示

        Args:
            dialog_window: 弹窗对象
            dialog_width (int): 弹窗宽度
            dialog_height (int): 弹窗高度
        """
        try:
            # 确保窗口信息是最新的
            dialog_window.update_idletasks()
            self.root.update_idletasks()

            # 获取物料管理界面的位置和尺寸
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()

            # 计算相对于物料管理界面居中的位置
            x = main_x + (main_width - dialog_width) // 2
            y = main_y + (main_height - dialog_height) // 2

            # 确保弹窗不会超出屏幕边界
            screen_width = dialog_window.winfo_screenwidth()
            screen_height = dialog_window.winfo_screenheight()

            # 调整坐标，确保不超出屏幕边界
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
            # 备用：屏幕居中
            x = (dialog_window.winfo_screenwidth() - dialog_width) // 2
            y = (dialog_window.winfo_screenheight() - dialog_height) // 2
            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def setup_placeholder(self, entry_widget, placeholder_text):
        """
        为输入框设置占位符效果
        
        Args:
            entry_widget: 输入框组件
            placeholder_text: 占位符文本
        """
        def on_focus_in(event):
            """输入框获得焦点时的处理"""
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            """输入框失去焦点时的处理"""
            if entry_widget.get() == '':
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        # 设置初始占位符
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        # 绑定事件
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def show_new_material_name_dialog(self):
        """
        显示新物料名称输入对话框（第一个弹窗）
        """
        try:
            # 创建物料名称输入弹窗
            name_dialog = tk.Toplevel(self.root)
            name_dialog.title("新物料名称")
            name_dialog.geometry("700x600")
            name_dialog.configure(bg='white')
            name_dialog.resizable(False, False)
            name_dialog.transient(self.root)
            name_dialog.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(name_dialog, 700, 600)
            
            # 标题
            tk.Label(name_dialog, text="新物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=40)
            
            # 物料名称输入框
            name_var = tk.StringVar()
            name_entry_frame = tk.Frame(name_dialog, bg='white')
            name_entry_frame.pack(pady=20)
            
            name_entry = tk.Entry(name_entry_frame, textvariable=name_var,
                                 font=tkFont.Font(family="微软雅黑", size=12),
                                 width=30, justify='center',
                                 relief='solid', bd=1,
                                 bg='white', fg='#333333')
            name_entry.pack(ipady=8)
            
            # 设置占位符
            self.setup_placeholder(name_entry, "请输入物料名称")
            name_entry.focus()  # 设置焦点到输入框
            
            # 按钮区域
            button_frame = tk.Frame(name_dialog, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel_click():
                """取消按钮点击事件"""
                print("[信息] 用户取消输入物料名称")
                name_dialog.destroy()
            
            def on_next_click():
                """下一步按钮点击事件"""
                material_name = name_var.get().strip()
                
                # 验证输入的物料名称
                if not material_name or material_name == "请输入物料名称":
                    messagebox.showwarning("输入错误", "请输入有效的物料名称！")
                    return
                
                # 检查物料名称是否已存在
                if DATABASE_AVAILABLE:
                    try:
                        existing_material = MaterialDAO.get_material_by_name(material_name)
                        if existing_material:
                            messagebox.showerror("物料已存在", f"物料名称'{material_name}'已存在，请使用其他名称！")
                            return
                    except Exception as e:
                        print(f"[错误] 检查物料名称是否存在时发生异常: {e}")
                        messagebox.showerror("检查错误", f"检查物料是否存在时发生错误：{str(e)}")
                        return
                
                print(f"[信息] 用户输入物料名称: {material_name}")
                name_dialog.destroy()
                
                # 显示第二个弹窗
                self.show_new_material_params_dialog(material_name)
            
            # 取消按钮
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=12,
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            # 下一步按钮
            next_btn = tk.Button(button_frame, text="下一步", 
                                font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                bg='#007bff', fg='white',
                                relief='flat', bd=0,
                                padx=40, pady=12,
                                command=on_next_click)
            next_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            # 绑定回车键到下一步按钮
            name_dialog.bind('<Return>', lambda e: on_next_click())
            
            print("[信息] 显示新物料名称输入对话框")
            
        except Exception as e:
            error_msg = f"显示新物料名称对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("系统错误", error_msg)
    
    def show_new_material_params_dialog(self, material_name: str):
        """
        显示新物料参数输入对话框（第二个弹窗）
        
        Args:
            material_name (str): 物料名称
        """
        try:
            # 创建物料参数输入弹窗
            params_dialog = tk.Toplevel(self.root)
            params_dialog.title("新物料名称")
            params_dialog.geometry("700x600")
            params_dialog.configure(bg='white')
            params_dialog.resizable(False, False)
            params_dialog.transient(self.root)
            params_dialog.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(params_dialog, 700, 600)
            
            # 标题
            tk.Label(params_dialog, text="新物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            # 物料名称显示（不可编辑）
            name_frame = tk.Frame(params_dialog, bg='white')
            name_frame.pack(pady=10)
            
            tk.Label(name_frame, text="物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            name_display = tk.Entry(name_frame,
                                   font=tkFont.Font(family="微软雅黑", size=12),
                                   width=30, justify='center',
                                   relief='solid', bd=1,
                                   bg='#f0f0f0', fg='#333333',
                                   state='readonly')
            name_display.pack(ipady=8, pady=(5, 0))
            
            # 设置物料名称显示
            name_display.config(state='normal')
            name_display.insert(0, material_name)
            name_display.config(state='readonly')
            
            # 每包重量输入
            weight_frame = tk.Frame(params_dialog, bg='white')
            weight_frame.pack(pady=15)
            
            tk.Label(weight_frame, text="每包重量 g", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            weight_var = tk.StringVar()
            weight_entry = tk.Entry(weight_frame, textvariable=weight_var,
                                   font=tkFont.Font(family="微软雅黑", size=12),
                                   width=30, justify='center',
                                   relief='solid', bd=1,
                                   bg='white', fg='#333333')
            weight_entry.pack(ipady=8, pady=(5, 0))
            self.setup_placeholder(weight_entry, "请输入目标重量")
            
            # 包装数量输入
            quantity_frame = tk.Frame(params_dialog, bg='white')
            quantity_frame.pack(pady=15)
            
            tk.Label(quantity_frame, text="包装数量", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            quantity_var = tk.StringVar()
            quantity_entry = tk.Entry(quantity_frame, textvariable=quantity_var,
                                     font=tkFont.Font(family="微软雅黑", size=12),
                                     width=30, justify='center',
                                     relief='solid', bd=1,
                                     bg='white', fg='#333333')
            quantity_entry.pack(ipady=8, pady=(5, 0))
            self.setup_placeholder(quantity_entry, "请输入目标包数")
            
            # 按钮区域
            button_frame = tk.Frame(params_dialog, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel_click():
                """取消按钮点击事件 - 返回第一个弹窗"""
                print("[信息] 用户取消参数输入，返回物料名称输入")
                params_dialog.destroy()
                # 返回第一个弹窗
                self.show_new_material_name_dialog()
            
            def on_start_click():
                """保存并开始AI训练按钮点击事件"""
                # 验证输入参数
                weight_str = weight_var.get().strip()
                quantity_str = quantity_var.get().strip()
                
                if not weight_str or weight_str == "请输入目标重量":
                    messagebox.showwarning("参数缺失", "请输入每包重量")
                    return
                
                if not quantity_str or quantity_str == "请输入目标包数":
                    messagebox.showwarning("参数缺失", "请输入包装数量")
                    return
                
                try:
                    target_weight = float(weight_str)
                    if target_weight <= 0:
                        messagebox.showerror("参数错误", "每包重量必须大于0")
                        return
                except ValueError:
                    messagebox.showerror("参数错误", "请输入有效的重量数值")
                    return
                
                try:
                    package_quantity = int(quantity_str)
                    if package_quantity <= 0:
                        messagebox.showerror("参数错误", "包装数量必须大于0")
                        return
                except ValueError:
                    messagebox.showerror("参数错误", "请输入有效的包装数量")
                    return
                
                print(f"[信息] 创建新物料: {material_name}, 重量: {target_weight}g, 数量: {package_quantity}")
                
                # 在数据库中创建新物料
                if DATABASE_AVAILABLE:
                    try:
                        success, message, material_id = MaterialDAO.create_material(
                            material_name=material_name,
                            ai_status="未学习",
                            is_enabled=1
                        )
                        
                        if success:
                            print(f"[成功] {message}, 物料ID: {material_id}")
                            
                            # 刷新物料列表
                            self.load_materials()
                            
                            params_dialog.destroy()
                            
                            # 显示创建成功消息
                            messagebox.showinfo("物料创建成功", 
                                              f"物料'{material_name}'已成功创建！\n\n"
                                              f"每包重量：{target_weight}g\n"
                                              f"包装数量：{package_quantity}包\n\n"
                                              f"现在将开始AI学习流程...")
                            
                            # 启动AI训练流程
                            self.start_ai_training_for_new_material(target_weight, package_quantity, material_name)
                            
                        else:
                            print(f"[失败] {message}")
                            messagebox.showerror("创建物料失败", f"创建物料失败：\n{message}")
                        
                    except Exception as e:
                        error_msg = f"创建物料时发生异常：{str(e)}"
                        print(f"[错误] {error_msg}")
                        messagebox.showerror("创建异常", error_msg)
                else:
                    # 数据库不可用时的处理
                    messagebox.showwarning("数据库不可用", 
                                         "数据库功能不可用，无法保存新物料！\n"
                                         "新物料将仅在本次会话中有效。")
                    
                    params_dialog.destroy()
                    
                    # 直接调用AI生产逻辑
                    self.start_ai_training_for_new_material(target_weight, package_quantity, material_name)
            
            # 取消按钮
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=12,
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            # 保存并开始AI训练按钮
            start_btn = tk.Button(button_frame, text="保存并开始AI训练", 
                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                 bg='#007bff', fg='white',
                                 relief='flat', bd=0,
                                 padx=40, pady=12,
                                 command=on_start_click)
            start_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            # 绑定回车键到开始按钮
            params_dialog.bind('<Return>', lambda e: on_start_click())
            
            print(f"[信息] 显示新物料参数输入对话框，物料名称: {material_name}")
            
        except Exception as e:
            error_msg = f"显示新物料参数对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("系统错误", error_msg)
    
    def start_ai_training_for_new_material(self, target_weight: float, package_quantity: int, material_name: str):
        """
        为新物料启动AI训练流程
        
        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量  
            material_name (str): 物料名称
        """
        try:
            print(f"[信息] 为新物料'{material_name}'启动AI训练流程")
            
            # 检查是否有AI模式界面引用
            if self.ai_mode_window:
                # 隐藏物料管理界面
                self.root.withdraw()
                
                # 显示AI模式界面
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
                
                # 设置AI模式界面的参数
                if hasattr(self.ai_mode_window, 'material_var'):
                    self.ai_mode_window.material_var.set(material_name)
                if hasattr(self.ai_mode_window, 'weight_var'):
                    self.ai_mode_window.weight_var.set(str(target_weight))
                if hasattr(self.ai_mode_window, 'quantity_var'):
                    self.ai_mode_window.quantity_var.set(str(package_quantity))
                
                # 刷新AI模式界面的物料列表
                if hasattr(self.ai_mode_window, 'refresh_material_list'):
                    self.ai_mode_window.refresh_material_list()
                
                # 启动AI训练流程
                if hasattr(self.ai_mode_window, 'start_ai_production_for_new_material'):
                    self.ai_mode_window.start_ai_production_for_new_material(target_weight, package_quantity, material_name)
                else:
                    # 如果没有这个方法，显示提示信息
                    messagebox.showinfo("切换到AI模式", 
                                      f"物料'{material_name}'已创建完成！\n\n"
                                      f"参数已设置：\n"
                                      f"• 每包重量：{target_weight}g\n"
                                      f"• 包装数量：{package_quantity}包\n\n"
                                      f"请在AI模式界面中点击'开始AI生产'开始训练。")
                
                print("[信息] 已切换到AI模式界面并设置参数")
            else:
                # 没有AI模式界面引用，显示提示信息
                messagebox.showinfo("AI训练", 
                                  f"物料'{material_name}'已创建！\n\n"
                                  f"参数：\n"
                                  f"• 每包重量：{target_weight}g\n"
                                  f"• 包装数量：{package_quantity}包\n\n"
                                  f"请切换到AI模式进行训练。")
        
        except Exception as e:
            error_msg = f"启动AI训练流程异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("启动异常", error_msg)
            
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_material_display()
    
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_material_display()
    
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
        
        # 关闭物料管理界面
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
        
        # 关闭物料管理界面
        self.root.destroy()
    
    def show(self):
        """显示界面（如果是主窗口）"""
        if self.is_main_window:
            self.root.mainloop()


def main():
    """
    主函数 - 程序入口点（用于测试）
    """
    # 创建物料管理界面实例
    material_interface = MaterialManagementInterface()
    
    # 显示界面
    material_interface.show()


# 当作为主程序运行时，启动界面
if __name__ == "__main__":
    main()