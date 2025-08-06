#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产记录界面
包装机系统生产记录查看界面

功能特点：
1. 生产记录列表显示
2. 按条件搜索
3. 分页显示
4. 查看详情

文件名：production_records_interface.py
作者：AI助手
创建日期：2025-08-06
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
from datetime import datetime, date
from typing import List, Optional

# 导入数据库相关模块
try:
    from database.production_record_dao import ProductionRecordDAO, ProductionRecord, ProductionRecordDetail
    from database.db_connection import db_manager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入数据库模块: {e}")
    DATABASE_AVAILABLE = False


class ProductionRecordsInterface:
    """
    生产记录界面类
    
    负责：
    1. 创建生产记录查看界面
    2. 从数据库读取和显示生产记录
    3. 处理搜索功能
    4. 处理分页显示
    5. 处理查看详情功能
    """
    
    def __init__(self, parent=None, system_settings_window=None):
        """
        初始化生产记录界面
        
        Args:
            parent: 父窗口对象
            system_settings_window: 系统设置界面引用，用于返回时显示
        """
        # 保存系统设置界面引用
        self.system_settings_window = system_settings_window
        
        # 创建主窗口
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        # 生产记录数据
        self.production_records = []
        self.filtered_records = []  # 搜索过滤后的记录
        self.current_page = 1
        self.items_per_page = 6  # 每页显示6条记录
        self.total_pages = 1
        
        # 搜索条件
        self.search_text_var = tk.StringVar()
        self.search_date_var = tk.StringVar()
    
        # 日期范围变量（新增）
        self.start_date = None
        self.end_date = None
        
        # 设置窗口属性
        self.setup_window()
        
        # 设置字体
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 加载生产记录数据
        self.load_production_records()
        
        # 居中显示窗口
        self.center_window()
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.title("生产记录")
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
        self.header_font = tkFont.Font(family="微软雅黑", size=12, weight="bold")
        
        # 内容字体
        self.content_font = tkFont.Font(family="微软雅黑", size=11)
        
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
        
        # 创建生产记录列表区域
        self.create_records_list_area(main_frame)
        
        # 创建搜索和分页控制区域
        self.create_search_and_pagination_area(main_frame)
        
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
        
        # 生产记录标题
        title_label = tk.Label(left_frame, text="生产记录", 
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
    
    def create_records_list_area(self, parent):
        """
        创建生产记录列表区域
        
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
            ("生产日期", 0.14),
            ("生产编号", 0.16),
            ("物料名称", 0.16),
            ("目标重量g", 0.13),
            ("生产包数", 0.13),
            ("完成率", 0.1),
            ("查看", 0.18)
        ]
        
        for i, (header_text, width_ratio) in enumerate(headers):
            header_label = tk.Label(header_frame, text=header_text, 
                                   font=self.header_font, bg='#f8f9fa', fg='#333333')
            header_label.place(relx=sum(h[1] for h in headers[:i]), rely=0.5, 
                              relwidth=width_ratio, anchor='w')
        
        # 内容区域（可滚动）
        self.content_frame = tk.Frame(list_container, bg='white')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_search_and_pagination_area(self, parent):
        """
        创建搜索和分页控制区域
        
        Args:
            parent: 父容器
        """
        # 搜索和分页容器
        search_pagination_frame = tk.Frame(parent, bg='white')
        search_pagination_frame.pack(fill=tk.X, pady=(10, 20))

        # 搜索区域（左侧）
        search_frame = tk.Frame(search_pagination_frame, bg='white')
        search_frame.pack(side=tk.LEFT)

        # 搜索输入框
        search_entry = tk.Entry(search_frame, textvariable=self.search_text_var,
                               font=self.content_font, width=25,
                               relief='solid', bd=1)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))

        # 设置占位符
        self.setup_placeholder(search_entry, "请输入生产编号或物料名称")

        # 日期选择输入框（修改这部分）
        self.date_entry = tk.Entry(search_frame, textvariable=self.search_date_var,
                                  font=self.content_font, width=20,
                                  relief='solid', bd=1, state='readonly')
        self.date_entry.pack(side=tk.LEFT, padx=(0, 10))

        # 绑定日期输入框点击事件
        self.date_entry.bind("<Button-1>", self.on_date_entry_click)

        # 设置日期占位符
        self.search_date_var.set("请选择搜索日期范围")
        self.date_entry.config(fg='#999999')

        # 搜索按钮
        search_btn = tk.Button(search_frame, text="搜索", 
                              font=self.button_font,
                              bg='#4a90e2', fg='white',
                              relief='flat', bd=0,
                              padx=20, pady=5,
                              command=self.on_search_click)
        search_btn.pack(side=tk.LEFT)

        # 分页控制（右侧）
        pagination_frame = tk.Frame(search_pagination_frame, bg='white')
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
        
    def on_date_entry_click(self, event):
        """日期输入框点击事件"""
        self.show_date_range_dialog()
        
    def show_date_range_dialog(self):
        """显示日期范围选择对话框"""
        try:
            # 创建日期选择弹窗
            date_window = tk.Toplevel(self.root)
            date_window.title("选择日期范围")
            date_window.geometry("400x300")
            date_window.configure(bg='white')
            date_window.resizable(False, False)
            date_window.transient(self.root)
            date_window.grab_set()

            # 居中显示弹窗
            self.center_dialog_relative_to_main(date_window, 400, 300)

            # 标题
            tk.Label(date_window, text="选择日期范围", 
                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)

            # 开始日期选择
            start_frame = tk.Frame(date_window, bg='white')
            start_frame.pack(pady=10, padx=20, fill=tk.X)

            tk.Label(start_frame, text="开始日期:", 
                    font=self.content_font, bg='white', fg='#333333').pack(side=tk.LEFT)

            start_date_var = tk.StringVar()
            start_date_entry = tk.Entry(start_frame, textvariable=start_date_var,
                                       font=self.content_font, width=15,
                                       relief='solid', bd=1)
            start_date_entry.pack(side=tk.RIGHT, padx=(10, 0))
            self.setup_placeholder(start_date_entry, "YYYY-MM-DD")

            # 结束日期选择
            end_frame = tk.Frame(date_window, bg='white')
            end_frame.pack(pady=10, padx=20, fill=tk.X)

            tk.Label(end_frame, text="结束日期:", 
                    font=self.content_font, bg='white', fg='#333333').pack(side=tk.LEFT)

            end_date_var = tk.StringVar()
            end_date_entry = tk.Entry(end_frame, textvariable=end_date_var,
                                     font=self.content_font, width=15,
                                     relief='solid', bd=1)
            end_date_entry.pack(side=tk.RIGHT, padx=(10, 0))
            self.setup_placeholder(end_date_entry, "YYYY-MM-DD")

            # 快捷选择按钮
            shortcut_frame = tk.Frame(date_window, bg='white')
            shortcut_frame.pack(pady=15)

            def set_today():
                today = datetime.now().strftime("%Y-%m-%d")
                start_date_var.set(today)
                end_date_var.set(today)
                start_date_entry.config(fg='#333333')
                end_date_entry.config(fg='#333333')

            def set_last_week():
                from datetime import timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                start_date_var.set(start_date.strftime("%Y-%m-%d"))
                end_date_var.set(end_date.strftime("%Y-%m-%d"))
                start_date_entry.config(fg='#333333')
                end_date_entry.config(fg='#333333')

            def set_last_month():
                from datetime import timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                start_date_var.set(start_date.strftime("%Y-%m-%d"))
                end_date_var.set(end_date.strftime("%Y-%m-%d"))
                start_date_entry.config(fg='#333333')
                end_date_entry.config(fg='#333333')

            tk.Button(shortcut_frame, text="今天", command=set_today,
                     font=self.button_font, bg='#e9ecef', padx=10).pack(side=tk.LEFT, padx=5)
            tk.Button(shortcut_frame, text="最近7天", command=set_last_week,
                     font=self.button_font, bg='#e9ecef', padx=10).pack(side=tk.LEFT, padx=5)
            tk.Button(shortcut_frame, text="最近30天", command=set_last_month,
                     font=self.button_font, bg='#e9ecef', padx=10).pack(side=tk.LEFT, padx=5)

            # 按钮区域
            button_frame = tk.Frame(date_window, bg='white')
            button_frame.pack(pady=20)

            def on_confirm():
                start_date_str = start_date_var.get().strip()
                end_date_str = end_date_var.get().strip()

                try:
                    # 验证日期格式
                    if start_date_str and start_date_str != "YYYY-MM-DD":
                        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    else:
                        self.start_date = None

                    if end_date_str and end_date_str != "YYYY-MM-DD":
                        self.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    else:
                        self.end_date = None

                    # 设置显示文本
                    if self.start_date and self.end_date:
                        if self.start_date == self.end_date:
                            display_text = self.start_date.strftime("%Y-%m-%d")
                        else:
                            display_text = f"{self.start_date.strftime('%Y-%m-%d')} 至 {self.end_date.strftime('%Y-%m-%d')}"
                    elif self.start_date:
                        display_text = f"从 {self.start_date.strftime('%Y-%m-%d')} 开始"
                    elif self.end_date:
                        display_text = f"到 {self.end_date.strftime('%Y-%m-%d')} 结束"
                    else:
                        display_text = "请选择搜索日期范围"

                    self.search_date_var.set(display_text)
                    self.date_entry.config(fg='#333333')

                    date_window.destroy()
                    print(f"[日期选择] 开始日期: {self.start_date}, 结束日期: {self.end_date}")

                except ValueError:
                    messagebox.showerror("日期格式错误", "请输入正确的日期格式：YYYY-MM-DD")

            def on_clear():
                self.start_date = None
                self.end_date = None
                self.search_date_var.set("请选择搜索日期范围")
                self.date_entry.config(fg='#999999')
                date_window.destroy()

            tk.Button(button_frame, text="确认", command=on_confirm,
                     font=self.button_font, bg='#4a90e2', fg='white', padx=20).pack(side=tk.LEFT, padx=10)
            tk.Button(button_frame, text="清除", command=on_clear,
                     font=self.button_font, bg='#6c757d', fg='white', padx=20).pack(side=tk.LEFT, padx=10)
            tk.Button(button_frame, text="取消", command=date_window.destroy,
                     font=self.button_font, bg='#e9ecef', padx=20).pack(side=tk.LEFT, padx=10)

        except Exception as e:
            print(f"[错误] 显示日期选择对话框异常: {e}")
            
    def center_dialog_relative_to_main(self, dialog_window, dialog_width, dialog_height):
        """
        将弹窗相对于主界面居中显示
    
        Args:
            dialog_window: 弹窗对象
            dialog_width (int): 弹窗宽度
            dialog_height (int): 弹窗高度
        """
        try:
            # 确保窗口信息是最新的
            dialog_window.update_idletasks()
            self.root.update_idletasks()
    
            # 获取主界面的位置和尺寸
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()
    
            # 计算相对于主界面居中的位置
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
            print("[ProductionRecords] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
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
    
    def load_production_records(self):
        """从数据库加载生产记录数据"""
        try:
            if DATABASE_AVAILABLE:
                # 获取最近的生产记录
                self.production_records = ProductionRecordDAO.get_recent_production_records(100)
                print(f"[信息] 从数据库加载了{len(self.production_records)}个生产记录")
            else:
                # 数据库不可用时显示空列表
                self.production_records = []
                print("[警告] 数据库不可用，无法加载生产记录")
            
            # 初始化过滤后的记录（显示所有记录）
            self.filtered_records = self.production_records.copy()
            
            # 计算总页数
            self.total_pages = max(1, (len(self.filtered_records) + self.items_per_page - 1) // self.items_per_page)
            
            # 刷新显示
            self.refresh_records_display()
            
        except Exception as e:
            print(f"[错误] 加载生产记录数据异常: {e}")
            messagebox.showerror("数据加载失败", f"加载生产记录数据失败：\n{str(e)}")
    
    def get_mock_data(self) -> List[ProductionRecord]:
        """获取模拟数据"""
        mock_records = []
        
        # 模拟3条生产记录
        mock_data = [
            {
                'id': 1,
                'production_date': date(2025, 7, 12),
                'production_id': 'P20250712001',
                'material_name': '珠料A872',
                'target_weight': 386.0,
                'package_quantity': 100,
                'completed_packages': 99,
                'completion_rate': 99.0,
                'create_time': datetime(2025, 7, 12, 10, 30),
                'update_time': datetime(2025, 7, 12, 16, 45)
            },
            {
                'id': 2,
                'production_date': date(2025, 7, 15),
                'production_id': 'P20250715001',
                'material_name': '粉料C6',
                'target_weight': 260.0,
                'package_quantity': 200,
                'completed_packages': 200,
                'completion_rate': 100.0,
                'create_time': datetime(2025, 7, 15, 8, 15),
                'update_time': datetime(2025, 7, 15, 17, 20)
            },
            {
                'id': 3,
                'production_date': date(2025, 7, 20),
                'production_id': 'P20250720001',
                'material_name': '石料162G',
                'target_weight': 192.0,
                'package_quantity': 200,
                'completed_packages': 126,
                'completion_rate': 63.0,
                'create_time': datetime(2025, 7, 20, 9, 0),
                'update_time': datetime(2025, 7, 20, 15, 30)
            }
        ]
        
        for data in mock_data:
            record = ProductionRecord(**data)
            mock_records.append(record)
        
        return mock_records
    
    def refresh_records_display(self):
        """刷新生产记录显示"""
        try:
            # 清空当前显示
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            # 计算当前页的数据范围
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = start_index + self.items_per_page
            page_records = self.filtered_records[start_index:end_index]
            
            # 显示生产记录行
            for i, record in enumerate(page_records):
                self.create_record_row(self.content_frame, record, i)
            
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
            print(f"[错误] 刷新生产记录显示异常: {e}")
    
    def create_record_row(self, parent, record: ProductionRecord, row_index: int):
        """
        创建生产记录行
        
        Args:
            parent: 父容器
            record: 生产记录对象
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
            
            # 生产日期
            date_text = record.production_date.strftime("%Y-%m-%d") if record.production_date else "未知"
            date_label = tk.Label(content_frame, text=date_text, 
                                 font=self.content_font, bg='white', fg='#333333')
            date_label.place(relx=0, rely=0.5, relwidth=0.14, anchor='w')
            
            # 生产编号
            id_label = tk.Label(content_frame, text=record.production_id, 
                               font=self.content_font, bg='white', fg='#333333')
            id_label.place(relx=0.14, rely=0.5, relwidth=0.16, anchor='w')
            
            # 物料名称
            material_label = tk.Label(content_frame, text=record.material_name, 
                                     font=self.content_font, bg='white', fg='#333333')
            material_label.place(relx=0.3, rely=0.5, relwidth=0.16, anchor='w')
            
            # 目标重量
            weight_text = f"{record.target_weight}g"
            weight_label = tk.Label(content_frame, text=weight_text, 
                                   font=self.content_font, bg='white', fg='#333333')
            weight_label.place(relx=0.46, rely=0.5, relwidth=0.13, anchor='w')
            
            # 生产包数
            packages_text = f"{record.completed_packages}/{record.package_quantity}"
            packages_label = tk.Label(content_frame, text=packages_text, 
                                     font=self.content_font, bg='white', fg='#333333')
            packages_label.place(relx=0.59, rely=0.5, relwidth=0.13, anchor='w')
            
            # 完成率
            rate_text = f"{record.completion_rate:.0f}%"
            rate_label = tk.Label(content_frame, text=rate_text, 
                                 font=self.content_font, bg='white', fg='#333333')
            rate_label.place(relx=0.72, rely=0.5, relwidth=0.1, anchor='w')
            
            # 查看按钮
            view_btn = tk.Button(content_frame, text="详情", 
                                font=self.button_font,
                                bg='#28a745', fg='white',
                                relief='flat', bd=0,
                                padx=15, pady=5,
                                command=lambda r=record: self.view_record_detail(r))
            view_btn.place(relx=0.85, rely=0.5, anchor='center')
            
        except Exception as e:
            print(f"[错误] 创建生产记录行异常: {e}")
    
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
            print(f"生产记录界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("950x750")
    
    # 事件处理函数
    
    def on_search_click(self):
        """搜索按钮点击事件"""
        search_text = self.search_text_var.get().strip()
        
        # 过滤记录
        self.filtered_records = []
        for record in self.production_records:
            # 检查文本搜索条件（模糊匹配）
            text_match = True
            if search_text and search_text != "请输入生产编号或物料名称":
                text_match = (search_text.lower() in record.production_id.lower() or 
                             search_text.lower() in record.material_name.lower())
            
            # 检查日期范围搜索条件
            date_match = True
            if self.start_date or self.end_date:
                record_date = record.production_date
                if record_date:
                    if self.start_date and record_date < self.start_date:
                        date_match = False
                    if self.end_date and record_date > self.end_date:
                        date_match = False
                else:
                    date_match = False  # 记录没有日期，不匹配
            
            if text_match and date_match:
                self.filtered_records.append(record)
        
        # 重置到第一页
        self.current_page = 1
        
        # 重新计算总页数
        self.total_pages = max(1, (len(self.filtered_records) + self.items_per_page - 1) // self.items_per_page)
        
        # 刷新显示
        self.refresh_records_display()
        
        # 输出搜索结果
        search_info = []
        if search_text and search_text != "请输入生产编号或物料名称":
            search_info.append(f"文本: '{search_text}'")
        if self.start_date or self.end_date:
            if self.start_date and self.end_date:
                search_info.append(f"日期: {self.start_date} 至 {self.end_date}")
            elif self.start_date:
                search_info.append(f"日期: 从 {self.start_date}")
            elif self.end_date:
                search_info.append(f"日期: 到 {self.end_date}")
        
        print(f"[搜索] 条件: {', '.join(search_info) if search_info else '无'}, 找到{len(self.filtered_records)}条匹配记录")
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_records_display()
    
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_records_display()
    
    def view_record_detail(self, record: ProductionRecord):
        """
        查看生产记录详情
        
        Args:
            record: 生产记录对象
        """
        try:
            # 从数据库获取详细统计信息
            if not DATABASE_AVAILABLE:
                messagebox.showerror("数据库错误", "数据库功能不可用，无法查看详情")
                return
            
            detail = ProductionRecordDAO.get_production_record_detail_by_id(record.production_id)
            
            if not detail:
                messagebox.showerror("数据错误", "无法获取生产记录详情")
                return
            
            # 创建详情弹窗
            self.show_production_detail_dialog(detail)
            
        except Exception as e:
            error_msg = f"查看生产记录详情异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("查看异常", error_msg)
            
    def show_production_detail_dialog(self, detail: ProductionRecordDetail):
        """
        显示生产记录详情弹窗

        Args:
            detail: 生产记录详情对象
        """
        try:
            # 创建详情弹窗
            detail_window = tk.Toplevel(self.root)
            detail_window.title("生产记录详情")
            detail_window.geometry("600x500")
            detail_window.configure(bg='white')
            detail_window.resizable(False, False)
            detail_window.transient(self.root)
            detail_window.grab_set()

            # 居中显示弹窗
            self.center_dialog_relative_to_main(detail_window, 600, 500)

            # 关闭按钮（右上角X）
            close_frame = tk.Frame(detail_window, bg='white')
            close_frame.pack(fill=tk.X, padx=10, pady=5)

            close_btn = tk.Button(close_frame, text="×", 
                                 font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                                 bg='white', fg='#666666', bd=0,
                                 width=3, height=1,
                                 command=detail_window.destroy)
            close_btn.pack(side=tk.RIGHT)

            # 目标信息区域
            target_frame = tk.Frame(detail_window, bg='white')
            target_frame.pack(pady=(20, 30), padx=40, fill=tk.X)

            # 目标包数和目标重量
            target_info_frame = tk.Frame(target_frame, bg='white')
            target_info_frame.pack()

            tk.Label(target_info_frame, text=f"目标包数：{detail.package_quantity}包", 
                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                    bg='white', fg='#333333').pack(side=tk.LEFT, padx=(0, 50))

            tk.Label(target_info_frame, text=f"目标重量：{detail.target_weight}g/包", 
                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                    bg='white', fg='#333333').pack(side=tk.LEFT)

            # 统计数据区域
            stats_frame = tk.Frame(detail_window, bg='white')
            stats_frame.pack(pady=20, padx=40, fill=tk.BOTH, expand=True)

            # 不合格数据（第一行）
            unqualified_frame = tk.Frame(stats_frame, bg='white')
            unqualified_frame.pack(pady=(0, 20), fill=tk.X)

            # 不合格包数
            unq_count_frame = tk.Frame(unqualified_frame, bg='white')
            unq_count_frame.pack(side=tk.LEFT, padx=(0, 40))
            tk.Label(unq_count_frame, text="不合格包数", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            tk.Label(unq_count_frame, text=f"{detail.unqualified_count}包", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))

            # 不合格最低值
            unq_min_frame = tk.Frame(unqualified_frame, bg='white')
            unq_min_frame.pack(side=tk.LEFT, padx=(0, 40))
            tk.Label(unq_min_frame, text="不合格最低值", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            min_text = f"{detail.unqualified_min_weight}g" if detail.unqualified_min_weight else "无"
            tk.Label(unq_min_frame, text=min_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))

            # 不合格最高值
            unq_max_frame = tk.Frame(unqualified_frame, bg='white')
            unq_max_frame.pack(side=tk.LEFT)
            tk.Label(unq_max_frame, text="不合格最高值", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            max_text = f"{detail.unqualified_max_weight}g" if detail.unqualified_max_weight else "无"
            tk.Label(unq_max_frame, text=max_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))

            # 合格数据（第二行）
            qualified_frame = tk.Frame(stats_frame, bg='white')
            qualified_frame.pack(fill=tk.X)

            # 合格包数
            q_count_frame = tk.Frame(qualified_frame, bg='white')
            q_count_frame.pack(side=tk.LEFT, padx=(0, 40))
            tk.Label(q_count_frame, text="合格包数", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            tk.Label(q_count_frame, text=f"{detail.qualified_count}包", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#00aa00',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))

            # 合格最低值
            q_min_frame = tk.Frame(qualified_frame, bg='white')
            q_min_frame.pack(side=tk.LEFT, padx=(0, 40))
            tk.Label(q_min_frame, text="合格最低值", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            q_min_text = f"{detail.qualified_min_weight}g" if detail.qualified_min_weight else "无"
            tk.Label(q_min_frame, text=q_min_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#00aa00',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))

            # 合格最高值
            q_max_frame = tk.Frame(qualified_frame, bg='white')
            q_max_frame.pack(side=tk.LEFT)
            tk.Label(q_max_frame, text="合格最高值", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            q_max_text = f"{detail.qualified_max_weight}g" if detail.qualified_max_weight else "无"
            tk.Label(q_max_frame, text=q_max_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#00aa00',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))

            # 返回按钮
            return_btn = tk.Button(detail_window, text="返回", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#e9ecef', fg='#333333',
                                  relief='flat', bd=0,
                                  padx=30, pady=10,
                                  command=detail_window.destroy)
            return_btn.pack(pady=30)

            print(f"[详情] 显示生产记录详情: {detail.production_id}")

        except Exception as e:
            error_msg = f"显示生产记录详情弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("显示异常", error_msg)
            
    def get_mock_detail_data(self, record: ProductionRecord) -> ProductionRecordDetail:
        """获取模拟详情数据"""
        from database.production_record_dao import ProductionRecordDetail

        # 根据不同的生产记录返回不同的模拟数据
        if record.production_id == "P20250712001":
            return ProductionRecordDetail(
                production_date=record.production_date,
                production_id=record.production_id,
                material_name=record.material_name,
                target_weight=record.target_weight,
                package_quantity=record.package_quantity,
                completed_packages=record.completed_packages,
                completion_rate=record.completion_rate,
                qualified_count=99,
                qualified_min_weight=385.9,
                qualified_max_weight=386.5,
                unqualified_count=1,
                unqualified_min_weight=None,
                unqualified_max_weight=386.9
            )
        else:
            return ProductionRecordDetail(
                production_date=record.production_date,
                production_id=record.production_id,
                material_name=record.material_name,
                target_weight=record.target_weight,
                package_quantity=record.package_quantity,
                completed_packages=record.completed_packages,
                completion_rate=record.completion_rate,
                qualified_count=record.completed_packages,
                qualified_min_weight=record.target_weight - 2.0,
                qualified_max_weight=record.target_weight + 1.5,
                unqualified_count=0,
                unqualified_min_weight=None,
                unqualified_max_weight=None
            )
    
    def on_return_click(self):
        """返回AI模式按钮点击事件"""
        print("点击了返回AI模式")
        
        # 如果有系统设置界面引用，重新显示系统设置界面
        if self.system_settings_window:
            try:
                # 显示系统设置界面
                self.system_settings_window.root.deiconify()
                self.system_settings_window.root.lift()
                self.system_settings_window.root.focus_force()
                print("系统设置界面已显示")
            except Exception as e:
                print(f"显示系统设置界面时发生错误: {e}")
        
        # 关闭生产记录界面
        self.root.destroy()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 如果有系统设置界面引用，重新显示系统设置界面
        if self.system_settings_window:
            try:
                # 显示系统设置界面
                self.system_settings_window.root.deiconify()
                self.system_settings_window.root.lift()
                self.system_settings_window.root.focus_force()
                print("系统设置界面已显示")
            except Exception as e:
                print(f"显示系统设置界面时发生错误: {e}")
        
        # 关闭生产记录界面
        self.root.destroy()
    
    def show(self):
        """显示界面（如果是主窗口）"""
        if self.is_main_window:
            self.root.mainloop()


def main():
    """
    主函数 - 程序入口点（用于测试）
    """
    # 创建生产记录界面实例
    records_interface = ProductionRecordsInterface()
    
    # 显示界面
    records_interface.show()


# 当作为主程序运行时，启动界面
if __name__ == "__main__":
    main()