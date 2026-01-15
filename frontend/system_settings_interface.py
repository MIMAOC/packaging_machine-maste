"""
系统设置界面

作者：C
创建日期：2025-08-05
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont


class SystemSettingsInterface:
    
    def __init__(self, parent=None, ai_mode_window=None):
        self.ai_mode_window = ai_mode_window
        
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        self.setup_window()
        self.setup_fonts()
        self.create_widgets()
    
    def setup_window(self):
        self.root.title("系统设置")
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
        
        self.setup_force_exit_mechanism()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        self.title_font = tkFont.Font(family="微软雅黑", size=28, weight="bold")
        self.button_font = tkFont.Font(family="微软雅黑", size=20, weight="bold")
        self.desc_font = tkFont.Font(family="微软雅黑", size=16)
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        self.footer_font = tkFont.Font(family="微软雅黑", size=14)
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=40)
        
        self.create_title_bar(main_frame)
        self.create_function_buttons(main_frame)
        self.create_footer_section(main_frame)
    
    def create_title_bar(self, parent):
        title_frame = tk.Frame(parent, bg='white')
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(left_frame, text="系统设置", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
        
        return_btn = tk.Button(right_frame, text="返回AI模式", 
                              font=self.small_button_font,
                              bg='#e9ecef', fg='#333333',
                              relief='flat', bd=1,
                              padx=25, pady=10,
                              command=self.on_return_click)
        return_btn.pack(side=tk.LEFT)
        
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 40))
    
    def create_function_buttons(self, parent):
        function_frame = tk.Frame(parent, bg='white')
        function_frame.pack(expand=True, fill='both', pady=(80, 150))
        
        buttons_container = tk.Frame(function_frame, bg='white')
        buttons_container.pack(expand=True)
        
        self.create_function_button(buttons_container, 
                                   "物料管理", 
                                   "新增物料并启动AI学习\n查看AI状态和管理物料可用",
                                   self.on_material_management_click,
                                   side=tk.LEFT, padx=(0, 80))
        
        self.create_function_button(buttons_container, 
                                   "生产记录", 
                                   "查看历史生产数据和合格率\n按时间和条件搜索记录",
                                   self.on_production_records_click,
                                   side=tk.LEFT, padx=(0, 80))
        
        self.create_function_button(buttons_container, 
                                   "出厂设置", 
                                   "设定重量误差报警阈值\n需要管理员密码验证",
                                   self.on_factory_settings_click,
                                   side=tk.LEFT)
    
    def create_function_button(self, parent, title, description, command, side=tk.LEFT, padx=0):
        button_container = tk.Frame(parent, bg='#d3d3d3', relief='flat', bd=0)
        button_container.pack(side=side, padx=padx)
        button_container.configure(width=320, height=240)
        button_container.pack_propagate(False)
        
        content_frame = tk.Frame(button_container, bg='#d3d3d3')
        content_frame.pack(expand=True, fill='both', padx=25, pady=25)
        
        title_label = tk.Label(content_frame, text=title, 
                              font=self.button_font, bg='#d3d3d3', fg='#333333')
        title_label.pack(pady=(30, 15))
        
        desc_label = tk.Label(content_frame, text=description, 
                             font=self.desc_font, bg='#d3d3d3', fg='#666666',
                             justify=tk.CENTER)
        desc_label.pack(pady=(0, 30))
        
        def bind_click_event(widget):
            widget.bind("<Button-1>", lambda e: command())
            widget.bind("<Enter>", lambda e: self.on_button_enter(button_container))
            widget.bind("<Leave>", lambda e: self.on_button_leave(button_container))
        
        bind_click_event(button_container)
        bind_click_event(content_frame)
        bind_click_event(title_label)
        bind_click_event(desc_label)
        
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
            "确定要退出系统设置界面吗？\n\n"
            "这将返回到AI模式界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        try:
            self.on_closing()
        except Exception:
            import os
            os._exit(0)
    
    def on_button_enter(self, button_container):
        button_container.config(bg='#b0b0b0')
        for child in button_container.winfo_children():
            child.config(bg='#b0b0b0')
            for grandchild in child.winfo_children():
                grandchild.config(bg='#b0b0b0')
    
    def on_button_leave(self, button_container):
        button_container.config(bg='#d3d3d3')
        for child in button_container.winfo_children():
            child.config(bg='#d3d3d3')
            for grandchild in child.winfo_children():
                grandchild.config(bg='#d3d3d3')
    
    def create_footer_section(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        version_text = "MHWPM v1.5.1 ©杭公式人工智能科技有限公司 温州天腾机械有限公司"
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
    
    def on_material_management_click(self):
        try:
            self.root.withdraw()
            
            from material_management_interface import MaterialManagementInterface
            material_interface = MaterialManagementInterface(parent=self.root, 
                                                            ai_mode_window=self.ai_mode_window)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开物料管理界面失败：{str(e)}")
    
    def on_production_records_click(self):
        try:
            self.root.withdraw()
            
            from production_records_interface import ProductionRecordsInterface
            records_interface = ProductionRecordsInterface(parent=self.root, 
                                                         system_settings_window=self)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开生产记录界面失败：{str(e)}")
    
    def on_factory_settings_click(self):
        try:
            self.root.withdraw()
            
            from factory_settings_interface import FactorySettingsInterface
            factory_interface = FactorySettingsInterface(parent=self.root, 
                                                       system_settings_window=self)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开出厂设置界面失败：{str(e)}")
    
    def on_return_click(self):
        if self.ai_mode_window:
            try:
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
            except Exception:
                pass
        
        self.root.destroy()
    
    def on_closing(self):
        if self.ai_mode_window:
            try:
                self.ai_mode_window.root.deiconify()
                self.ai_mode_window.root.lift()
                self.ai_mode_window.root.focus_force()
            except Exception:
                pass
        
        self.root.destroy()
    
    def show(self):
        if self.is_main_window:
            self.root.mainloop()


def main():
    settings_interface = SystemSettingsInterface()
    settings_interface.show()

if __name__ == "__main__":
    main()