"""
生产记录界面

作者：C
创建日期：2025-08-06
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
from datetime import datetime, date
from typing import List, Optional
try:
    from database.production_record_dao import ProductionRecordDAO, ProductionRecord, ProductionRecordDetail
    from database.db_connection import db_manager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False


class ProductionRecordsInterface:
    
    def __init__(self, parent=None, system_settings_window=None):
        self.system_settings_window = system_settings_window
        
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        self.production_records = []
        self.filtered_records = []
        self.current_page = 1
        self.items_per_page = 6
        self.total_pages = 1
        
        self.search_text_var = tk.StringVar()
        self.search_date_var = tk.StringVar()
        
        self.start_date = None
        self.end_date = None
        
        self.setup_window()
        self.setup_fonts()
        self.create_widgets()
        
        self.load_production_records()
        
    def setup_placeholder(self, entry_widget, placeholder_text):
        def on_focus_in(event):
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            if not entry_widget.get().strip():
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def setup_window(self):
        self.root.title("生产记录")
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        self.setup_force_exit_mechanism()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=28, weight="bold")
        self.header_font = tkFont.Font(family="微软雅黑", size=16, weight="bold")
        self.content_font = tkFont.Font(family="微软雅黑", size=14)
        self.button_font = tkFont.Font(family="微软雅黑", size=14)
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=30)
        
        self.create_title_bar(main_frame)
        self.create_records_list_area(main_frame)
        self.create_search_and_pagination_area(main_frame)
        self.create_footer_section(main_frame)
    
    def create_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="生产记录", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        return_btn = tk.Button(right_frame, text="返回系统设置", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_click)
        return_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 20))
    
    def create_records_list_area(self, parent):
        list_container = tk.Frame(parent, bg='white', relief='solid', bd=1)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(20, 20))
        
        header_frame = tk.Frame(list_container, bg='#f8f9fa', height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        headers = [
            ("生产日期", 0.14),
            ("生产编号", 0.16),
            ("物料名称", 0.16),
            ("目标重量g", 0.13),
            ("生产包数", 0.13),
            ("完成率", 0.1),
            ("操作", 0.18)
        ]
        
        for i, (header_text, width_ratio) in enumerate(headers):
            header_label = tk.Label(header_frame, text=header_text, 
                                   font=self.header_font, bg='#f8f9fa', fg='#333333')
            header_label.place(relx=sum(h[1] for h in headers[:i]), rely=0.5, 
                              relwidth=width_ratio, anchor='w')
        
        self.content_frame = tk.Frame(list_container, bg='white')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_search_and_pagination_area(self, parent):
        search_pagination_frame = tk.Frame(parent, bg='white')
        search_pagination_frame.pack(fill=tk.X, pady=(10, 20))
        
        search_frame = tk.Frame(search_pagination_frame, bg='white')
        search_frame.pack(side=tk.LEFT)
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_text_var,
                           font=tkFont.Font(family="微软雅黑", size=12),
                           width=25,
                           relief='solid', bd=2)
        search_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=8)
        search_entry.focus_set()
        
        self.setup_placeholder(search_entry, "请输入生产编号或物料名称")
        
        self.date_entry = tk.Entry(search_frame, textvariable=self.search_date_var,
                                  font=self.content_font, width=25,
                                  relief='solid', bd=1, state='readonly')
        self.date_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=6)
        
        self.date_entry.bind("<Button-1>", self.on_date_entry_click)
        
        self.search_date_var.set("请选择搜索日期范围")
        self.date_entry.config(fg='#999999')
        
        search_btn = tk.Button(search_frame, text="搜索", 
                              font=self.button_font,
                              bg='#4a90e2', fg='white',
                              relief='flat', bd=0,
                              padx=20, pady=5,
                              command=self.on_search_click)
        search_btn.pack(side=tk.LEFT)
        
        pagination_frame = tk.Frame(search_pagination_frame, bg='white')
        pagination_frame.pack(side=tk.RIGHT)
        
        self.prev_page_btn = tk.Button(pagination_frame, text="上一页", 
                                      font=self.button_font,
                                      bg='#e9ecef', fg='#333333',
                                      relief='flat', bd=1,
                                      padx=15, pady=5,
                                      command=self.prev_page,
                                      state='disabled')
        self.prev_page_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.page_info_label = tk.Label(pagination_frame, text="1/1", 
                                       font=self.content_font, bg='white', fg='#666666')
        self.page_info_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.next_page_btn = tk.Button(pagination_frame, text="下一页", 
                                      font=self.button_font,
                                      bg='#e9ecef', fg='#333333',
                                      relief='flat', bd=1,
                                      padx=15, pady=5,
                                      command=self.next_page,
                                      state='disabled')
        self.next_page_btn.pack(side=tk.LEFT)
        
    def on_date_entry_click(self, event):
        self.show_date_range_dialog()
        
    def show_date_range_dialog(self):
        try:
            date_window = tk.Toplevel(self.root)
            date_window.title("选择日期范围")
            date_window.geometry("400x500")
            date_window.configure(bg='white')
            date_window.resizable(False, False)
            date_window.transient(self.root)
            date_window.grab_set()
            
            self.center_dialog_relative_to_main(date_window, 400, 500)
            
            tk.Label(date_window, text="选择日期范围", 
                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)
            
            start_frame = tk.Frame(date_window, bg='white')
            start_frame.pack(pady=10, padx=20, fill=tk.X)

            tk.Label(start_frame, text="开始日期:", 
                    font=self.content_font, bg='white', fg='#333333').pack(side=tk.LEFT)

            start_date_var = tk.StringVar()
            start_date_entry = tk.Entry(start_frame, textvariable=start_date_var,
                               font=tkFont.Font(family="微软雅黑", size=12),
                               width=15,
                               relief='solid', bd=2)
            start_date_entry.pack(side=tk.RIGHT, padx=(10, 0), ipady=6)
            start_date_entry.focus_set()
            
            self.setup_placeholder(start_date_entry, "YYYY-MM-DD")
            
            end_frame = tk.Frame(date_window, bg='white')
            end_frame.pack(pady=10, padx=20, fill=tk.X)

            tk.Label(end_frame, text="结束日期:", 
                    font=self.content_font, bg='white', fg='#333333').pack(side=tk.LEFT)

            end_date_var = tk.StringVar()
            end_date_entry = tk.Entry(end_frame, textvariable=end_date_var,
                             font=tkFont.Font(family="微软雅黑", size=12),
                             width=15,
                             relief='solid', bd=2)
            end_date_entry.pack(side=tk.RIGHT, padx=(10, 0), ipady=6)
            end_date_entry.focus_set()
            
            self.setup_placeholder(end_date_entry, "YYYY-MM-DD")
            
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
            
            button_frame = tk.Frame(date_window, bg='white')
            button_frame.pack(pady=20)

            def on_confirm():
                start_date_str = start_date_var.get().strip()
                end_date_str = end_date_var.get().strip()

                try:
                    if start_date_str and start_date_str != "YYYY-MM-DD":
                        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    else:
                        self.start_date = None

                    if end_date_str and end_date_str != "YYYY-MM-DD":
                        self.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    else:
                        self.end_date = None
                    
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

        except Exception:
            pass
            
    def setup_force_exit_mechanism(self):
        self.root.bind('<Control-Alt-q>', lambda e: self.force_exit())
        self.root.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        self.root.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        exit_zone = tk.Frame(self.root, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        self.click_count = 0
        self.last_click_time = 0

    def show_exit_confirmation(self):
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出生产记录界面吗？\n\n"
            "将返回到系统设置界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_closing()
        except Exception:
            import os
            os._exit(0)
            
    def center_dialog_relative_to_main(self, dialog_window, dialog_width, dialog_height):
        try:
            dialog_window.update_idletasks()
            self.root.update_idletasks()
            
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()
            
            x = main_x + (main_width - dialog_width) // 2
            y = main_y + (main_height - dialog_height) // 2
            
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
    
        except Exception:
            x = (dialog_window.winfo_screenwidth() - dialog_width) // 2
            y = (dialog_window.winfo_screenheight() - dialog_height) // 2
            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        version_text = "MHWPM v1.5.1 ©杭州公式人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
        except ImportError:
            pass
    
    def load_production_records(self):
        try:
            if DATABASE_AVAILABLE:
                self.production_records = ProductionRecordDAO.get_recent_production_records(100)
            else:
                self.production_records = []
            
            self.filtered_records = self.production_records.copy()
            
            self.total_pages = max(1, (len(self.filtered_records) + self.items_per_page - 1) // self.items_per_page)
            
            self.refresh_records_display()
            
        except Exception as e:
            messagebox.showerror("数据加载失败", f"加载生产记录数据失败：\n{str(e)}")
    
    def refresh_records_display(self):
        try:
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = start_index + self.items_per_page
            page_records = self.filtered_records[start_index:end_index]
            
            for i, record in enumerate(page_records):
                self.create_record_row(self.content_frame, record, i)
            
            self.page_info_label.config(text=f"{self.current_page}/{self.total_pages}")
            
            if self.current_page > 1:
                self.prev_page_btn.config(state='normal')
            else:
                self.prev_page_btn.config(state='disabled')
            
            if self.current_page < self.total_pages:
                self.next_page_btn.config(state='normal')
            else:
                self.next_page_btn.config(state='disabled')
            
        except Exception:
            pass
    
    def create_record_row(self, parent, record: ProductionRecord, row_index: int):
        try:
            row_frame = tk.Frame(parent, bg='white', height=65)
            row_frame.pack(fill=tk.X, pady=1)
            row_frame.pack_propagate(False)
            
            if row_index > 0:
                separator = tk.Frame(row_frame, height=1, bg='#e9ecef')
                separator.pack(fill=tk.X)
            
            content_frame = tk.Frame(row_frame, bg='white')
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            date_text = record.production_date.strftime("%Y-%m-%d") if record.production_date else "未知"
            date_label = tk.Label(content_frame, text=date_text, 
                                 font=self.content_font, bg='white', fg='#333333')
            date_label.place(relx=0, rely=0.5, relwidth=0.14, anchor='w')
            
            id_label = tk.Label(content_frame, text=record.production_id, 
                               font=self.content_font, bg='white', fg='#333333')
            id_label.place(relx=0.14, rely=0.5, relwidth=0.16, anchor='w')
            
            material_label = tk.Label(content_frame, text=record.material_name, 
                                     font=self.content_font, bg='white', fg='#333333')
            material_label.place(relx=0.3, rely=0.5, relwidth=0.16, anchor='w')
            
            weight_text = f"{record.target_weight}g"
            weight_label = tk.Label(content_frame, text=weight_text, 
                                   font=self.content_font, bg='white', fg='#333333')
            weight_label.place(relx=0.46, rely=0.5, relwidth=0.13, anchor='w')
            
            packages_text = f"{record.completed_packages}/{record.package_quantity}"
            packages_label = tk.Label(content_frame, text=packages_text, 
                                     font=self.content_font, bg='white', fg='#333333')
            packages_label.place(relx=0.59, rely=0.5, relwidth=0.13, anchor='w')
            
            rate_text = f"{record.completion_rate:.0f}%"
            rate_label = tk.Label(content_frame, text=rate_text, 
                                 font=self.content_font, bg='white', fg='#333333')
            rate_label.place(relx=0.72, rely=0.5, relwidth=0.1, anchor='w')
            
            view_btn = tk.Button(content_frame, text="详情", 
                                font=self.button_font,
                                bg='#28a745', fg='white',
                                relief='flat', bd=0,
                                padx=12, pady=5,
                                command=lambda r=record: self.view_record_detail(r))
            view_btn.place(relx=0.85, rely=0.5, anchor='center')
            
            relearn_btn = tk.Button(content_frame, text="再学习", 
                                font=self.button_font,
                                bg='#007bff', fg='white',
                                relief='flat', bd=0,
                                padx=10, pady=5,
                                command=lambda r=record: self.on_relearn_click(r))
            relearn_btn.place(relx=0.92, rely=0.5, anchor='center')
            
        except Exception:
            pass
    
    def center_window(self):
        try:
            self.root.update_idletasks()
            
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            if width <= 1 or height <= 1:
                width = 950
                height = 750
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception:
            self.root.geometry("950x750")
    
    def on_search_click(self):
        search_text = self.search_text_var.get().strip()
        
        self.filtered_records = []
        for record in self.production_records:
            text_match = True
            if search_text and search_text != "请输入生产编号或物料名称":
                text_match = (search_text.lower() in record.production_id.lower() or 
                             search_text.lower() in record.material_name.lower())
            
            date_match = True
            if self.start_date or self.end_date:
                record_date = record.production_date
                if record_date:
                    if self.start_date and record_date < self.start_date:
                        date_match = False
                    if self.end_date and record_date > self.end_date:
                        date_match = False
                else:
                    date_match = False
            
            if text_match and date_match:
                self.filtered_records.append(record)
        
        self.current_page = 1
        
        self.total_pages = max(1, (len(self.filtered_records) + self.items_per_page - 1) // self.items_per_page)
        
        self.refresh_records_display()
    
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_records_display()
    
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_records_display()
    
    def view_record_detail(self, record: ProductionRecord):
        try:
            if not DATABASE_AVAILABLE:
                messagebox.showerror("数据库错误", "数据库功能不可用，无法查看详情")
                return
            
            detail = ProductionRecordDAO.get_production_record_detail_by_id(record.production_id)
            
            if not detail:
                messagebox.showerror("数据错误", "无法获取生产记录详情")
                return
            
            self.show_production_detail_dialog(detail)
            
        except Exception as e:
            error_msg = f"查看生产记录详情异常: {str(e)}"
            messagebox.showerror("查看异常", error_msg)
            
    def show_production_detail_dialog(self, detail: ProductionRecordDetail):
        try:
            detail_window = tk.Toplevel(self.root)
            detail_window.title("生产记录详情")
            detail_window.geometry("800x600")
            detail_window.configure(bg='white')
            detail_window.resizable(False, False)
            detail_window.transient(self.root)
            detail_window.grab_set()
            
            self.center_dialog_relative_to_main(detail_window, 800, 600)
            
            close_frame = tk.Frame(detail_window, bg='white')
            close_frame.pack(fill=tk.X, padx=10, pady=5)

            close_btn = tk.Button(close_frame, text="×", 
                                 font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                                 bg='white', fg='#666666', bd=0,
                                 width=3, height=1,
                                 command=detail_window.destroy)
            close_btn.pack(side=tk.RIGHT)
            
            target_frame = tk.Frame(detail_window, bg='white')
            target_frame.pack(pady=(20, 30), padx=40, fill=tk.X)
            
            target_info_frame = tk.Frame(target_frame, bg='white')
            target_info_frame.pack()

            tk.Label(target_info_frame, text=f"目标包数：{detail.package_quantity}包", 
                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                    bg='white', fg='#333333').pack(side=tk.LEFT, padx=(0, 50))

            tk.Label(target_info_frame, text=f"目标重量：{detail.target_weight}g/包", 
                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                    bg='white', fg='#333333').pack(side=tk.LEFT)
            
            stats_frame = tk.Frame(detail_window, bg='white')
            stats_frame.pack(pady=20, padx=50, fill=tk.BOTH, expand=True)
            
            unqualified_frame = tk.Frame(stats_frame, bg='white')
            unqualified_frame.pack(pady=(0, 20), padx=100, fill=tk.X)
            
            unq_count_frame = tk.Frame(unqualified_frame, bg='white')
            unq_count_frame.pack(side=tk.LEFT, padx=(0, 50))
            tk.Label(unq_count_frame, text="不合格包数", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            tk.Label(unq_count_frame, text=f"{detail.unqualified_count}包", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))
            
            unq_min_frame = tk.Frame(unqualified_frame, bg='white')
            unq_min_frame.pack(side=tk.LEFT, padx=(0, 50))
            tk.Label(unq_min_frame, text="不合格最低值", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            min_text = f"{detail.unqualified_min_weight}g" if detail.unqualified_min_weight else "无"
            tk.Label(unq_min_frame, text=min_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))
            
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
            
            qualified_frame = tk.Frame(stats_frame, bg='white')
            qualified_frame.pack(pady=(0, 20), padx=100, fill=tk.X)
            
            q_count_frame = tk.Frame(qualified_frame, bg='white')
            q_count_frame.pack(side=tk.LEFT, padx=(0, 50))
            tk.Label(q_count_frame, text="合格包数", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            tk.Label(q_count_frame, text=f"{detail.qualified_count}包", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#00aa00',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))
            
            q_min_frame = tk.Frame(qualified_frame, bg='white')
            q_min_frame.pack(side=tk.LEFT, padx=(0, 50))
            tk.Label(q_min_frame, text="合格最低值", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack()
            q_min_text = f"{detail.qualified_min_weight}g" if detail.qualified_min_weight else "无"
            tk.Label(q_min_frame, text=q_min_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#00aa00',
                    relief='solid', bd=1, padx=20, pady=10).pack(pady=(10, 0))
            
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
            
            return_btn = tk.Button(detail_window, text="返回", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#e9ecef', fg='#333333',
                                  relief='flat', bd=0,
                                  padx=30, pady=15,
                                  command=detail_window.destroy)
            return_btn.pack(pady=30)

        except Exception as e:
            error_msg = f"显示生产记录详情弹窗异常: {str(e)}"
            messagebox.showerror("显示异常", error_msg)
            
    def on_relearn_click(self, record: ProductionRecord):
        try:
            confirm_msg = f"再学习确认\n\n" \
                        f"生产编号：{record.production_id}\n" \
                        f"物料名称：{record.material_name}\n" \
                        f"目标重量：{record.target_weight}g\n" \
                        f"包装数量：{record.package_quantity}包\n\n" \
                        f"确认使用此配置重新进行AI学习吗？\n" \
                        f"这将启动新的AI学习流程。"
            
            result = messagebox.askyesno("再学习确认", confirm_msg)
            if not result:
                return
            
            if DATABASE_AVAILABLE:
                try:
                    detail = ProductionRecordDAO.get_production_record_detail_by_id(record.production_id)
                    if not detail:
                        messagebox.showerror("数据错误", "无法获取生产记录详情，再学习失败")
                        return
                except Exception as e:
                    messagebox.showerror("数据异常", f"获取生产记录详情时发生错误：\n{str(e)}")
                    return
            
            self.root.withdraw()
            
            try:
                from ai_mode_interface import AIModeInterface
                
                ai_interface = AIModeInterface(parent=self.root.master)
                
                ai_interface.weight_var.set(str(record.target_weight))
                ai_interface.quantity_var.set(str(record.package_quantity))
                ai_interface.material_var.set(record.material_name)
                
                success_msg = f"AI模式已启动，参数已自动设置：\n\n" \
                            f"目标重量：{record.target_weight}g\n" \
                            f"包装数量：{record.package_quantity}包\n" \
                            f"选择物料：{record.material_name}\n\n" \
                            f"请在AI模式界面中点击『开始AI生产』按钮继续。"
                
                messagebox.showinfo("再学习启动", success_msg)
                
                self.root.destroy()
                
            except ImportError as e:
                self.root.deiconify()
                error_msg = f"无法导入AI模式界面模块：{str(e)}"
                messagebox.showerror("模块错误", f"启动AI模式失败：\n{error_msg}")
                
            except Exception as e:
                self.root.deiconify()
                error_msg = f"启动AI模式异常：{str(e)}"
                messagebox.showerror("启动失败", error_msg)
                
        except Exception as e:
            error_msg = f"再学习操作异常：{str(e)}"
            messagebox.showerror("操作异常", error_msg)
    
    def on_return_click(self):
        if self.system_settings_window:
            try:
                self.system_settings_window.root.deiconify()
                self.system_settings_window.root.lift()
                self.system_settings_window.root.focus_force()
            except Exception:
                pass
        
        self.root.destroy()
    
    def on_closing(self):
        if self.system_settings_window:
            try:
                self.system_settings_window.root.deiconify()
                self.system_settings_window.root.lift()
                self.system_settings_window.root.focus_force()
            except Exception:
                pass
        
        self.root.destroy()
    
    def show(self):
        if self.is_main_window:
            self.root.mainloop()


def main():
    records_interface = ProductionRecordsInterface()
    records_interface.show()

if __name__ == "__main__":
    main()