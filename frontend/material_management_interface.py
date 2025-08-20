"""
物料管理界面

作者：C
创建日期：2025-08-05
"""

from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
from typing import List
from touchscreen_utils import TouchScreenUtils

try:
    from database.material_dao import MaterialDAO, Material
    from database.db_connection import db_manager
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False


class MaterialManagementInterface:
    
    def __init__(self, parent=None, ai_mode_window=None):
        self.ai_mode_window = ai_mode_window
        
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        self.materials = []
        self.current_page = 1
        self.items_per_page = 5
        self.total_pages = 1
        
        self.setup_window()
        
        self.setup_fonts()
        
        self.create_widgets()
        
        TouchScreenUtils.optimize_window_for_touch(self.root)
        
        self.load_materials()
        
        # self.center_window()
    
    def setup_window(self):
        self.root.title("物料管理")
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        self.setup_force_exit_mechanism()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=28, weight="bold")
        
        self.header_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        self.content_font = tkFont.Font(family="微软雅黑", size=16)
        
        self.button_font = tkFont.Font(family="微软雅黑", size=14)
        
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=40)
        
        self.create_title_bar(main_frame)
        
        self.create_material_list_area(main_frame)
        
        self.create_bottom_controls(main_frame)
        
        self.create_footer_section(main_frame)
    
    def create_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="物料管理", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=20, pady=8,
                              command=self.on_return_click)
        return_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 20))
        
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
            "确定要退出物料管理界面吗？\n\n"
            "这将返回到AI模式界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_closing()
        except Exception as e:
            import os
            os._exit(0)
    
    def create_material_list_area(self, parent):
        list_container = tk.Frame(parent, bg='white', relief='solid', bd=1)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(20, 20))
        
        header_frame = tk.Frame(list_container, bg='#f8f9fa', height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
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
        
        self.content_frame = tk.Frame(list_container, bg='white')
        self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_bottom_controls(self, parent):
        bottom_frame = tk.Frame(parent, bg='white')
        bottom_frame.pack(fill=tk.X, pady=(10, 20))
        
        new_material_btn = tk.Button(bottom_frame, text="⊕ 新建物料", 
                                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                    bg='#007bff', fg='white',
                                    relief='flat', bd=0,
                                    padx=30, pady=10,
                                    command=self.on_new_material_click)
        new_material_btn.pack(side=tk.LEFT)
        
        pagination_frame = tk.Frame(bottom_frame, bg='white')
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
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        version_text = "MHWPM v1.5.1 ©杭州公武人工智能科技有限公司 温州天腾机械有限公司"
        version_label = tk.Label(footer_frame, text=version_text, 
                               font=self.footer_font, bg='white', fg='#888888')
        version_label.pack(pady=(0, 5))
        
        logo_frame = tk.Frame(footer_frame, bg='white')
        logo_frame.pack()
        
        try:
            from logo_handler import create_logo_components
            create_logo_components(footer_frame, bg_color='white')
        except ImportError as e:
            pass
    
    def load_materials(self):
        try:
            if DATABASE_AVAILABLE:
                self.materials = MaterialDAO.get_all_materials(enabled_only=False)
            else:
                self.materials = []
            
            self.total_pages = max(1, (len(self.materials) + self.items_per_page - 1) // self.items_per_page)
            
            self.refresh_material_display()
            
        except Exception as e:
            messagebox.showerror("数据加载失败", f"加载物料数据失败：\n{str(e)}")
    
    def refresh_material_display(self):
        try:
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = start_index + self.items_per_page
            page_materials = self.materials[start_index:end_index]
            
            for i, material in enumerate(page_materials):
                self.create_material_row(self.content_frame, material, i)
            
            self.page_info_label.config(text=f"{self.current_page}/{self.total_pages}")
            
            if self.current_page > 1:
                self.prev_page_btn.config(state='normal')
            else:
                self.prev_page_btn.config(state='disabled')
            
            if self.current_page < self.total_pages:
                self.next_page_btn.config(state='normal')
            else:
                self.next_page_btn.config(state='disabled')
            
        except Exception as e:
            pass
    
    def create_material_row(self, parent, material: Material, row_index: int):
        try:
            row_frame = tk.Frame(parent, bg='white', height=80)
            row_frame.pack(fill=tk.X, pady=1)
            row_frame.pack_propagate(False)
            
            if row_index > 0:
                separator = tk.Frame(row_frame, height=1, bg='#e9ecef')
                separator.pack(fill=tk.X)
            
            content_frame = tk.Frame(row_frame, bg='white')
            content_frame.pack(fill=tk.BOTH, expand=True, padx=13, pady=10)
            
            material_name_label = tk.Label(content_frame, text=material.material_name, 
                                          font=self.content_font, bg='white', fg='#333333')
            material_name_label.place(relx=0, rely=0.5, relwidth=0.3, anchor='w')
            
            ai_status_label = tk.Label(content_frame, text=material.ai_status, 
                                      font=self.content_font, bg='white', fg='#333333')
            ai_status_label.place(relx=0.3, rely=0.5, relwidth=0.15, anchor='w')
            
            create_time_text = self._format_datetime_safe(material.create_time)
            create_time_label = tk.Label(content_frame, text=create_time_text, 
                                        font=self.content_font, bg='white', fg='#333333')
            create_time_label.place(relx=0.45, rely=0.5, relwidth=0.2, anchor='w')
            
            operation_container = tk.Frame(content_frame, bg='white')
            operation_container.place(relx=0.65, rely=0, relwidth=0.35, relheight=1)
            
            button_container = tk.Frame(operation_container, bg='white')
            button_container.pack(expand=True)
            
            enable_text = "启用" if material.is_enabled == 0 else "禁用"
            enable_color = "#28a745" if material.is_enabled == 0 else "#dc3545"
            enable_btn = tk.Button(button_container, text=enable_text, 
                                  font=self.button_font,
                                  bg=enable_color, fg='white',
                                  relief='flat', bd=0,
                                  padx=20, pady=8,
                                  command=lambda m=material: self.toggle_material_status(m))
            enable_btn.pack(side=tk.LEFT, padx=(0, 25))
            
            relearn_state = 'normal' if material.is_enabled == 1 else 'disabled'
            relearn_color = "#28a745" if material.is_enabled == 1 else "#cccccc"
            relearn_btn = tk.Button(button_container, text="再学习", 
                                   font=self.button_font,
                                   bg=relearn_color, fg='white',
                                   relief='flat', bd=0,
                                   padx=20, pady=8,
                                   state=relearn_state,
                                   command=lambda m=material: self.relearn_material(m))
            relearn_btn.pack(side=tk.LEFT)
            
        except Exception as e:
            pass
            
    def _format_datetime_safe(self, dt_value):
        try:
            if dt_value is None:
                return "未知"
            
            if isinstance(dt_value, datetime):
                return dt_value.strftime("%Y-%m-%d")
            
            if isinstance(dt_value, str):
                try:
                    formats = [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%d",
                        "%Y/%m/%d %H:%M:%S",
                        "%Y/%m/%d"
                    ]
                    
                    for fmt in formats:
                        try:
                            parsed_dt = datetime.strptime(dt_value, fmt)
                            return parsed_dt.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                    
                    if len(dt_value) >= 10:
                        return dt_value[:10]
                    else:
                        return dt_value
                        
                except Exception as e:
                    return str(dt_value)[:10] if len(str(dt_value)) >= 10 else str(dt_value)
            
            return str(dt_value)
            
        except Exception as e:
            return "格式错误"
    
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
            
        except Exception as e:
            self.root.geometry("950x750")
    
    def toggle_material_status(self, material: Material):
        try:
            if not DATABASE_AVAILABLE:
                messagebox.showwarning("数据库不可用", "数据库功能不可用，无法修改物料状态")
                return
            
            new_status = 0 if material.is_enabled == 1 else 1
            status_text = "启用" if new_status == 1 else "禁用"
            
            result = messagebox.askyesno("确认操作", f"确定要{status_text}物料'{material.material_name}'吗？")
            if not result:
                return
            
            if new_status == 1:
                success, message = MaterialDAO.enable_material(material.id)
            else:
                success, message = MaterialDAO.disable_material(material.id)
            
            if success:
                self.load_materials()
                messagebox.showinfo("操作成功", f"物料'{material.material_name}'已{status_text}")
            else:
                messagebox.showerror("操作失败", f"{status_text}物料失败：\n{message}")
        
        except Exception as e:
            error_msg = f"切换物料状态异常: {str(e)}"
            messagebox.showerror("操作异常", error_msg)
    
    def relearn_material(self, material: Material):
        try:
            if material.is_enabled == 0:
                messagebox.showwarning("操作受限", "禁用状态的物料无法进行再学习")
                return

            self.show_new_material_params_dialog(material.material_name, is_relearning=True, material_id=material.id)

        except Exception as e:
            error_msg = f"再学习操作异常: {str(e)}"
            messagebox.showerror("操作异常", error_msg)
    
    def on_new_material_click(self):
        self.show_new_material_name_dialog()
    
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

        except Exception as e:
            x = (dialog_window.winfo_screenwidth() - dialog_width) // 2
            y = (dialog_window.winfo_screenheight() - dialog_height) // 2
            dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def setup_placeholder(self, entry_widget, placeholder_text):
        def on_focus_in(event):
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            if entry_widget.get() == '':
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def show_new_material_name_dialog(self):
        try:
            name_dialog = tk.Toplevel(self.root)
            name_dialog.title("新物料名称")
            name_dialog.geometry("700x600")
            name_dialog.configure(bg='white')
            name_dialog.resizable(False, False)
            name_dialog.transient(self.root)
            name_dialog.grab_set()
            
            self.center_dialog_relative_to_main(name_dialog, 700, 600)
            
            tk.Label(name_dialog, text="新物料名称", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=40)
            
            name_var = tk.StringVar()
            name_entry_frame = tk.Frame(name_dialog, bg='white')
            name_entry_frame.pack(pady=20)
            
            name_entry = tk.Entry(name_entry_frame, textvariable=name_var,
                         font=tkFont.Font(family="微软雅黑", size=14),
                         width=30, justify='center',
                         relief='solid', bd=2,
                         bg='white', fg='#333333')
            name_entry.pack(ipady=12)
            
            TouchScreenUtils.setup_touch_entry(name_entry, "请输入物料名称")
            name_entry.focus()
            
            button_frame = tk.Frame(name_dialog, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel_click():
                name_dialog.destroy()
            
            def on_next_click():
                material_name = name_var.get().strip()
                
                if not material_name or material_name == "请输入物料名称":
                    messagebox.showwarning("输入错误", "请输入有效的物料名称！")
                    return
                
                if DATABASE_AVAILABLE:
                    try:
                        existing_material = MaterialDAO.get_material_by_name(material_name)
                        if existing_material:
                            messagebox.showerror("物料已存在", f"物料名称'{material_name}'已存在，请使用其他名称！")
                            return
                    except Exception as e:
                        messagebox.showerror("检查错误", f"检查物料是否存在时发生错误：{str(e)}")
                        return
                
                name_dialog.destroy()
                
                self.show_new_material_params_dialog(material_name)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=12,
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            next_btn = tk.Button(button_frame, text="下一步", 
                                font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                bg='#007bff', fg='white',
                                relief='flat', bd=0,
                                padx=40, pady=12,
                                command=on_next_click)
            next_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            name_dialog.bind('<Return>', lambda e: on_next_click())
            
        except Exception as e:
            error_msg = f"显示新物料名称对话框异常: {str(e)}"
            messagebox.showerror("系统错误", error_msg)
    
    def show_new_material_params_dialog(self, material_name: str, is_relearning: bool = False, material_id: int = None):
        try:
            params_dialog = tk.Toplevel(self.root)
            dialog_title = "再学习物料" if is_relearning else "新物料名称"
            params_dialog.title(dialog_title)
            params_dialog.geometry("700x600")
            params_dialog.configure(bg='white')
            params_dialog.resizable(False, False)
            params_dialog.transient(self.root)
            params_dialog.grab_set()
            
            self.center_dialog_relative_to_main(params_dialog, 700, 600)
            
            title_text = "再学习物料" if is_relearning else "新物料名称"
            tk.Label(params_dialog, text=title_text, 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
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
            
            name_display.config(state='normal')
            name_display.insert(0, material_name)
            name_display.config(state='readonly')
            
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
            
            button_frame = tk.Frame(params_dialog, bg='white')
            button_frame.pack(pady=40)
            
            def on_cancel_click():
                if is_relearning:
                    params_dialog.destroy()
                else:
                    params_dialog.destroy()
                    self.show_new_material_name_dialog()
            
            def on_start_click():
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
                
                if target_weight < 60 or target_weight > 425:
                    messagebox.showerror("参数错误", 
                                    f"输入重量超出范围\n\n"
                                    f"允许范围：60g - 425g\n"
                                    f"当前输入：{target_weight}g\n\n"
                                    f"请重新输入正确的重量范围")
                    return
                
                try:
                    package_quantity = int(quantity_str)
                    if package_quantity <= 0:
                        messagebox.showerror("参数错误", "包装数量必须大于0")
                        return
                except ValueError:
                    messagebox.showerror("参数错误", "请输入有效的包装数量")
                    return
                
                if is_relearning:
                    if DATABASE_AVAILABLE and material_id:
                        try:
                            success, message = MaterialDAO.update_material_ai_status(material_id, "未学习")
                            if success:
                                self.load_materials()
                        except Exception as e:
                            pass
                    
                    params_dialog.destroy()
                    
                    messagebox.showinfo("再学习开始", 
                                      f"物料'{material_name}'再学习已开始！\n\n"
                                      f"每包重量：{target_weight}g\n"
                                      f"包装数量：{package_quantity}包\n\n"
                                      f"现在将开始AI再学习流程...")
                    
                    self.start_ai_training_for_new_material(target_weight, package_quantity, material_name)
                    
                else:
                    if DATABASE_AVAILABLE:
                        try:
                            success, message, material_id = MaterialDAO.create_material(
                                material_name=material_name,
                                ai_status="未学习",
                                is_enabled=1
                            )
                            
                            if success:
                                self.load_materials()
                                
                                params_dialog.destroy()
                                
                                messagebox.showinfo("物料创建成功", 
                                                  f"物料'{material_name}'已成功创建！\n\n"
                                                  f"每包重量：{target_weight}g\n"
                                                  f"包装数量：{package_quantity}包\n\n"
                                                  f"现在将开始AI学习流程...")
                                
                                self.start_ai_training_for_new_material(target_weight, package_quantity, material_name)
                                
                            else:
                                messagebox.showerror("创建物料失败", f"创建物料失败：\n{message}")
                            
                        except Exception as e:
                            error_msg = f"创建物料时发生异常：{str(e)}"
                            messagebox.showerror("创建异常", error_msg)
                    else:
                        messagebox.showwarning("数据库不可用", 
                                             "数据库功能不可用，无法保存新物料！\n"
                                             "新物料将仅在本次会话中有效。")
                        
                        params_dialog.destroy()
                        
                        self.start_ai_training_for_new_material(target_weight, package_quantity, material_name)
            
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=40, pady=12,
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            start_text = "开始再学习" if is_relearning else "保存并开始AI训练"
            start_btn = tk.Button(button_frame, text=start_text, 
                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                 bg='#007bff', fg='white',
                                 relief='flat', bd=0,
                                 padx=40, pady=12,
                                 command=on_start_click)
            start_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            params_dialog.bind('<Return>', lambda e: on_start_click())
            
        except Exception as e:
            error_msg = f"显示物料参数对话框异常: {str(e)}"
            messagebox.showerror("系统错误", error_msg)
    
    def start_ai_training_for_new_material(self, target_weight: float, package_quantity: int, material_name: str):
        try:
            if self.ai_mode_window:
                self.root.withdraw()
                
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
                
                if hasattr(self.ai_mode_window, 'material_var'):
                    self.ai_mode_window.material_var.set(material_name)
                if hasattr(self.ai_mode_window, 'weight_var'):
                    self.ai_mode_window.weight_var.set(str(target_weight))
                if hasattr(self.ai_mode_window, 'quantity_var'):
                    self.ai_mode_window.quantity_var.set(str(package_quantity))
                
                if hasattr(self.ai_mode_window, 'refresh_material_list'):
                    self.ai_mode_window.refresh_material_list()
                
                if hasattr(self.ai_mode_window, 'start_ai_production_for_new_material'):
                    self.ai_mode_window.start_ai_production_for_new_material(target_weight, package_quantity, material_name)
                else:
                    messagebox.showinfo("切换到AI模式", 
                                      f"物料'{material_name}'已创建完成！\n\n"
                                      f"参数已设置：\n"
                                      f"• 每包重量：{target_weight}g\n"
                                      f"• 包装数量：{package_quantity}包\n\n"
                                      f"请在AI模式界面中点击'开始AI生产'开始训练。")
            else:
                messagebox.showinfo("AI训练", 
                                  f"物料'{material_name}'已创建！\n\n"
                                  f"参数：\n"
                                  f"• 每包重量：{target_weight}g\n"
                                  f"• 包装数量：{package_quantity}包\n\n"
                                  f"请切换到AI模式进行训练。")
        
        except Exception as e:
            error_msg = f"启动AI训练流程异常: {str(e)}"
            messagebox.showerror("启动异常", error_msg)
            
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_material_display()
    
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_material_display()
    
    def on_return_click(self):
        if self.ai_mode_window:
            try:
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
            except Exception as e:
                pass
        
        self.root.destroy()
    
    def on_closing(self):
        if self.ai_mode_window:
            try:
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
            except Exception as e:
                pass
        
        self.root.destroy()
    
    def show(self):
        if self.is_main_window:
            self.root.mainloop()


def main():
    material_interface = MaterialManagementInterface()
    
    material_interface.show()

if __name__ == "__main__":
    main()