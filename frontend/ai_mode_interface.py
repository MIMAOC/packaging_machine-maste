#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模式界面 - 自学习自适应 - 增强多斗学习状态显示
包装机AI模式操作界面，集成后端API服务

功能特点：
1. 目标重量设置
2. 包装数量设置  
3. 物料选择和管理（数据库支持）
4. AI生产控制（连接后端API）
5. 清理和重置功能
6. 快加时间测定功能
7. 增强的放料+清零功能（带弹窗确认）
8. 清料功能（三个弹窗流程）
9. 多斗学习状态管理
10. 实时多斗学习状态弹窗显示
11. 新建物料功能（MySQL数据库支持）

文件名：ai_mode_interface.py
作者：AI助手
创建日期：2025-07-22
更新日期：2025-08-04（增加MySQL数据库支持和新建物料功能）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import threading
import time
from typing import Dict, List
from production_interface import create_production_interface

# 导入后端API客户端模块
try:
    from clients.webapi_client import analyze_target_weight
    WEBAPI_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入WebAPI客户端模块: {e}")
    WEBAPI_AVAILABLE = False
    
try:
    from plc_addresses import get_bucket_disable_address
    BUCKET_DISABLE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入料斗禁用地址: {e}")
    BUCKET_DISABLE_AVAILABLE = False

# 导入PLC操作模块
try:
    from plc_operations import create_plc_operations
    PLC_OPERATIONS_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入PLC操作模块: {e}")
    print(f"详细错误: {str(e)}")
    PLC_OPERATIONS_AVAILABLE = False
    # 定义一个空的函数以避免 NameError
    def create_plc_operations(client):
        return None

# 导入清料控制器模块
try:
    from material_cleaning_controller import create_material_cleaning_controller
    CLEANING_CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入清料控制器模块: {e}")
    print(f"详细错误: {str(e)}")
    CLEANING_CONTROLLER_AVAILABLE = False
    # 定义一个空的函数以避免 NameError
    def create_material_cleaning_controller(client):
        return None

# 导入Modbus客户端
try:
    from modbus_client import ModbusClient
    MODBUS_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入Modbus客户端模块: {e}")
    MODBUS_CLIENT_AVAILABLE = False

# 导入API配置
try:
    from config.api_config import get_api_config
    API_CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入API配置模块: {e}")
    API_CONFIG_AVAILABLE = False

# 导入快加时间测定控制器模块
try:
    from coarse_time_controller import create_coarse_time_test_controller
    COARSE_TIME_CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入快加时间测定控制器模块: {e}")
    COARSE_TIME_CONTROLLER_AVAILABLE = False
    # 定义一个空的函数以避免 NameError
    def create_coarse_time_test_controller(client):
        return None

# 导入料斗学习状态管理器
try:
    from bucket_learning_state_manager import (
        create_bucket_learning_state_manager, 
        LearningStage, 
        LearningStatus
    )
    LEARNING_STATE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入料斗学习状态管理器模块: {e}")
    LEARNING_STATE_MANAGER_AVAILABLE = False

# 导入数据库相关模块
try:
    from database.material_dao import MaterialDAO, Material
    from database.db_connection import db_manager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入数据库模块: {e}")
    print("请确保已安装PyMySQL: pip install PyMySQL")
    DATABASE_AVAILABLE = False
    
try:
    from database.intelligent_learning_dao import IntelligentLearningDAO, IntelligentLearning
    INTELLIGENT_LEARNING_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入智能学习DAO模块: {e}")
    INTELLIGENT_LEARNING_DAO_AVAILABLE = False
    
try:
    from database.production_record_dao import ProductionRecordDAO
    PRODUCTION_RECORD_DAO_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入生产记录DAO模块: {e}")
    PRODUCTION_RECORD_DAO_AVAILABLE = False

class AIModeInterface:
    """
    AI模式界面类
    
    负责：
    1. 创建AI模式的用户界面
    2. 处理用户输入和交互
    3. 提供参数设置功能
    4. 管理物料选择（数据库支持）
    5. 执行AI生产流程（通过后端API）
    6. 快加时间测定控制
    7. 增强的放料+清零功能
    8. 清料功能控制
    9. 多斗学习状态管理
    10. 实时多斗学习状态弹窗显示
    11. 新建物料功能（MySQL数据库支持）
    """
    
    def __init__(self, parent=None, main_window=None):
        """
        初始化AI模式界面
        
        Args:
            parent: 父窗口对象，如果为None则创建独立窗口
            main_window: 主程序窗口引用，用于返回首页时显示
        """
        # 保存主窗口引用
        self.main_window = main_window
        
        # 获取主窗口的modbus_client引用
        self.modbus_client = None
        if main_window and hasattr(main_window, 'modbus_client'):
            self.modbus_client = main_window.modbus_client
        
        # 创建PLC操作实例
        self.plc_operations = None
        if self.modbus_client and PLC_OPERATIONS_AVAILABLE:
            try:
                self.plc_operations = create_plc_operations(self.modbus_client)
                print("PLC操作模块已成功初始化")
            except Exception as e:
                print(f"PLC操作模块初始化失败: {e}")
                self.plc_operations = None
        
        # 创建清料控制器实例
        self.cleaning_controller = None
        if self.modbus_client and CLEANING_CONTROLLER_AVAILABLE:
            try:
                self.cleaning_controller = create_material_cleaning_controller(self.modbus_client)
                print("清料控制器已成功初始化")
            except Exception as e:
                print(f"清料控制器初始化失败: {e}")
                self.cleaning_controller = None
        
        # 创建主窗口或使用父窗口
        if parent is None:
            self.root = tk.Tk()
            self.is_main_window = True
        else:
            self.root = tk.Toplevel(parent)
            self.is_main_window = False
        
        # 界面变量
        self.weight_var = tk.StringVar()           # 目标重量变量
        self.quantity_var = tk.StringVar()         # 包装数量变量
        self.material_var = tk.StringVar()         # 物料选择变量
        
        # 从数据库获取物料列表
        self.material_list = self.get_material_list_from_database()
        
        # 快加时间测定控制器
        self.coarse_time_controller = None
        
        # 多斗学习状态弹窗相关变量
        self.learning_status_window = None
        self.bucket_status_labels = {}  # 存储各料斗状态标签的引用
        
        # 创建料斗学习状态管理器
        if LEARNING_STATE_MANAGER_AVAILABLE:
            self.learning_state_manager = create_bucket_learning_state_manager()
            # 设置状态管理器事件回调
            self.learning_state_manager.on_state_changed = self._on_bucket_state_changed
            self.learning_state_manager.on_all_completed = self._on_all_learning_completed
        else:
            self.learning_state_manager = None
        
        # 获取API配置
        self.api_config = None
        if API_CONFIG_AVAILABLE:
            self.api_config = get_api_config()
        
        # 设置窗口属性
        self.setup_window()
        
        # 设置字体
        self.setup_fonts()
        
        # 创建界面组件
        self.create_widgets()
        
        # 居中显示窗口（新增）
        self.center_window()
        
        # 添加弹窗状态管理
        self.active_dialogs = set()  # 记录当前活跃的弹窗
        self.material_shortage_dialogs = {}  # 记录物料不足弹窗 {bucket_id: dialog_window}
        self.dialog_lock = threading.Lock()  # 弹窗操作锁
    
        # 学习完成通知标志
        self.all_learning_completed_notified = False  # 是否已通知所有学习完成
        
        # 定时器ID管理
        self.learning_timer_id = None           # 学习计时器ID
        self.statistics_timer_id = None         # 统计更新定时器ID
        self.learning_timer_running = False     # 学习计时器运行标志
        self.statistics_timer_running = False   # 统计定时器运行标志
        
    def setup_placeholder(self, entry_widget, placeholder_text):
        """设置输入框占位符功能"""
        def on_focus_in(event):
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#333333')
        
        def on_focus_out(event):
            if not entry_widget.get().strip():
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
        
        # 初始显示占位符
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        # 绑定事件
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def get_material_list_from_database(self) -> List[str]:
        """
        从数据库获取物料列表
        
        Returns:
            List[str]: 物料名称列表，包含默认选项
        """
        material_list = ["请选择已记录物料"]
        
        if DATABASE_AVAILABLE:
            try:
                # 测试数据库连接
                success, message = db_manager.test_connection()
                if success:
                    # 从数据库获取物料名称列表
                    material_names = MaterialDAO.get_material_names(enabled_only=True)
                    material_list.extend(material_names)
                    print(f"[信息] 从SQLite数据库加载了{len(material_names)}个物料")
                else:
                    print(f"[警告] SQLite数据库连接失败: {message}")
            except Exception as e:
                print(f"[错误] 获取物料列表异常: {e}")
        else:
            print("[警告] 数据库功能不可用")
        
        return material_list
    
    def refresh_material_list(self):
        """
        刷新物料列表
        更新下拉选择框的内容
        """
        try:
            # 重新获取物料列表
            self.material_list = self.get_material_list_from_database()
            
            # 查找物料选择下拉框并更新
            # 需要保存下拉框的引用以便更新
            if hasattr(self, 'material_combobox'):
                current_value = self.material_var.get()
                self.material_combobox['values'] = self.material_list
                
                # 如果当前选择的值不在新列表中，重置为默认值
                if current_value not in self.material_list:
                    self.material_var.set(self.material_list[0])
                
                print("[信息] 物料列表已刷新")
            
        except Exception as e:
            print(f"[错误] 刷新物料列表失败: {e}")
    
    def center_dialog_relative_to_main(self, dialog_window, dialog_width, dialog_height):
        """
        将弹窗相对于AI模式界面居中显示

        Args:
            dialog_window: 弹窗对象
            dialog_width (int): 弹窗宽度
            dialog_height (int): 弹窗高度
        """
        try:
            # 确保窗口信息是最新的
            dialog_window.update_idletasks()
            self.root.update_idletasks()

            # 获取AI模式界面的位置和尺寸
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()

            # 计算相对于AI模式界面居中的位置
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
            
    def setup_force_exit_mechanism(self):
        """设置强制退出机制"""
        # 键盘快捷键强制退出
        self.root.bind('<Control-Alt-q>', lambda e: self.force_exit())
        self.root.bind('<Control-Alt-Q>', lambda e: self.force_exit())
        self.root.bind('<Escape>', lambda e: self.show_exit_confirmation())
        
        # 添加隐藏的强制退出区域（右上角小区域）
        exit_zone = tk.Frame(self.root, bg='white', width=100, height=50)
        exit_zone.place(x=1450, y=0)  # 放在右上角
        exit_zone.bind('<Double-Button-1>', lambda e: self.show_exit_confirmation())
        
        # 连续点击计数器用于紧急退出
        self.click_count = 0
        self.last_click_time = 0

    def show_exit_confirmation(self):
        """显示退出确认对话框"""
        result = messagebox.askyesno(
            "退出确认", 
            "确定要退出AI模式吗？\n\n"
            "退出将停止所有AI学习过程并返回主界面。"
        )
        if result:
            self.force_exit()

    def force_exit(self):
        """强制退出程序"""
        try:
            print("执行AI模式强制退出...")
            self.on_closing()
        except Exception as e:
            print(f"AI模式强制退出时发生错误: {e}")
            # 对于AI模式，强制退出应该返回主界面而不是终止整个程序
            if self.main_window:
                try:
                    self.main_window.show_main_window()
                    self.root.destroy()
                except:
                    import os
                    os._exit(0)  # 最后的备选方案
            else:
                import os
                os._exit(0)
    
    def center_window(self):
        """将AI模式界面窗口居中显示"""
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
            print(f"AI模式界面居中显示失败: {e}")
            # 如果居中失败，至少确保窗口大小正确
            self.root.geometry("1000x750")
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.title("AI模式 - 自学习自适应")
    
        # 设置全屏模式 - 参考main.py
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')  # Windows系统的最大化
        self.root.geometry("1920x1080")
        self.root.configure(bg='white')
        self.root.resizable(True, True)
    
        # 设置强制退出机制
        self.setup_force_exit_mechanism()
        
        # 绑定窗口关闭事件（无论是否为主窗口都需要处理）
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_fonts(self):
        """设置界面字体 - 适应1920×1080分辨率"""
        # 标题字体 - 增大
        self.title_font = tkFont.Font(family="微软雅黑", size=28, weight="bold")
        
        # 标签字体 - 增大
        self.label_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        # 输入框字体 - 增大
        self.entry_font = tkFont.Font(family="微软雅黑", size=16)
        
        # 按钮字体 - 增大
        self.button_font = tkFont.Font(family="微软雅黑", size=18, weight="bold")
        
        # 小按钮字体 - 增大
        self.small_button_font = tkFont.Font(family="微软雅黑", size=14)
        
        # 底部信息字体 - 增大
        self.footer_font = tkFont.Font(family="微软雅黑", size=12)
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)
        
        # 创建标题栏
        self.create_title_bar(main_frame)
        
        # 创建状态信息栏
        self.create_status_bar(main_frame)
        
        # 创建参数设置区域
        self.create_parameter_section(main_frame)
        
        # 创建控制按钮区域
        self.create_control_section(main_frame)
        
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
        
        # 左侧标题和AI图标
        left_frame = tk.Frame(title_frame, bg='white')
        left_frame.pack(side=tk.LEFT)
        
        # AI模式标题
        title_label = tk.Label(left_frame, text="AI模式 - 自学习自适应", 
                             font=self.title_font, bg='white', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # AI图标（用蓝色圆形背景 + AI文字模拟）
        ai_icon = tk.Button(left_frame, text="🤖AI", 
                          font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                          bg='#4a90e2', fg='white', width=4, height=1,
                          relief='flat', bd=0,
                          padx=30, pady=15,  # 增加内边距
                          command=self.on_ai_icon_click)
        ai_icon.pack(side=tk.LEFT, padx=(15, 0))
        
        # 右侧按钮区域
        right_frame = tk.Frame(title_frame, bg='white')
        right_frame.pack(side=tk.RIGHT)
    
        # 调试按钮（仅在开发模式下显示）
        debug_btn = tk.Button(right_frame, text="🐛调试", 
                             font=self.small_button_font,
                             bg='#fd7e14', fg='white',
                             relief='flat', bd=1,
                             padx=30, pady=15,  # 增加内边距
                             command=self.show_debug_menu)
        debug_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 返回首页按钮
        home_btn = tk.Button(right_frame, text="返回首页", 
                           font=self.small_button_font,
                           bg='#e9ecef', fg='#333333',
                           relief='flat', bd=1,
                           padx=30, pady=15,  # 增加内边距
                           command=self.on_home_click)
        home_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # API设置按钮
        api_btn = tk.Button(right_frame, text="API设置", 
                          font=self.small_button_font,
                          bg='#d1ecf1', fg='#333333',
                          relief='flat', bd=1,
                          padx=30, pady=15,  # 增加内边距
                          command=self.on_api_settings_click)
        api_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 设置按钮
        settings_btn = tk.Button(right_frame, text="设置", 
                               font=self.small_button_font,
                               bg='#e9ecef', fg='#333333',
                               relief='flat', bd=1,
                               padx=30, pady=15,  # 增加内边距
                               command=self.on_settings_click)
        settings_btn.pack(side=tk.LEFT)
        
        # 蓝色分隔线（放在标题栏下方）
        separator = tk.Frame(parent, height=3, bg='#7fb3d3')
        separator.pack(fill=tk.X, pady=(0, 15))
    
    def show_debug_menu(self):
        """显示调试菜单"""
        debug_window = tk.Toplevel(self.root)
        debug_window.title("调试测试菜单")
        debug_window.geometry("450x650")  # 增加高度以容纳新按钮
        debug_window.configure(bg='white')
        debug_window.resizable(False, False)
        debug_window.transient(self.root)
        debug_window.grab_set()

        # 居中显示
        self.center_dialog_relative_to_main(debug_window, 450, 650)

        # 标题
        tk.Label(debug_window, text="🐛 调试测试菜单", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=20)

        # 测试按钮列表 - 添加自适应学习失败测试
        test_buttons = [
            ("测试多斗学习状态弹窗", lambda: self.debug_show_multi_bucket_status()),
            ("测试训练完成弹窗", lambda: self._show_training_completed_dialog()),
            ("测试快加时间失败弹窗", lambda: self.show_relearning_choice_dialog(1, "快加时间超时", "coarse_time")),
            ("测试飞料值失败弹窗", lambda: self.show_relearning_choice_dialog(2, "飞料值异常", "flight_material")),
            ("测试慢加时间失败弹窗", lambda: self.show_relearning_choice_dialog(3, "慢加精度不足", "fine_time")),
            ("测试自适应学习失败弹窗", lambda: self.show_relearning_choice_dialog(4, "自适应学习收敛失败", "adaptive_learning")),  # 新增
            ("测试放料清零完成弹窗", lambda: self.show_discharge_clear_completion_dialog()),
            ("测试模拟学习过程", lambda: self.debug_simulate_learning()),
        ]

        for i, (text, command) in enumerate(test_buttons):
            btn = tk.Button(debug_window, text=text, 
                           font=tkFont.Font(family="微软雅黑", size=11),
                           bg='#e9ecef', fg='#333333',
                           relief='flat', bd=1,
                           padx=30, pady=15,  # 增加内边距
                           command=command)
            btn.pack(pady=5, fill=tk.X, padx=20)

        # 关闭按钮
        tk.Button(debug_window, text="关闭", 
                 font=tkFont.Font(family="微软雅黑", size=12),
                 bg='#6c757d', fg='white',
                 relief='flat', bd=0,
                 padx=30, pady=15,  # 增加内边距
                 command=debug_window.destroy).pack(pady=20)
        
    def debug_show_multi_bucket_status(self):
        """调试：显示多斗学习状态弹窗"""
        # 确保学习状态管理器存在（调试模式）
        if not self.learning_state_manager:
            # 创建模拟的学习状态管理器
            class MockLearningStateManager:
                def get_completed_count(self):
                    return 2, 1, 6  # 成功2个，失败1个，总共6个

                def is_all_completed(self):
                    return False

            self.learning_state_manager = MockLearningStateManager()

        # 显示弹窗
        self.show_multi_bucket_learning_status_dialog()

    def debug_simulate_learning(self):
        """调试：模拟学习过程"""
        if not self.learning_status_window:
            messagebox.showwarning("提示", "请先打开多斗学习状态弹窗")
            return

        # 模拟不同状态
        def update_states():
            try:
                import random
                states_info = [
                    ("学习中", "#4a90e2"),
                    ("学习失败", "#ff0000"), 
                    ("学习完成", "#00aa00"),
                    ("未开始", "#888888")
                ]

                for bucket_id in range(1, 7):
                    if bucket_id in self.bucket_status_labels:
                        # 随机选择状态
                        text, color = random.choice(states_info)
                        label = self.bucket_status_labels[bucket_id]
                        label.config(text=text, fg=color)

                # 更新统计信息
                if hasattr(self, 'stats_label'):
                    self.stats_label.config(text="学习状态：模拟测试中...")

            except Exception as e:
                print(f"调试模拟异常: {e}")

        self.root.after(100, update_states)
    
    def create_status_bar(self, parent):
        """
        创建状态信息栏
        
        Args:
            parent: 父容器
        """
        status_frame = tk.Frame(parent, bg='white', relief=tk.RAISED, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # PLC连接状态
        plc_frame = tk.Frame(status_frame, bg='white')
        plc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(plc_frame, text="PLC:", font=self.small_button_font, 
                bg='white', fg='#333333').pack(side=tk.LEFT)
        
        plc_status = "已连接" if (self.modbus_client and self.modbus_client.is_connected) else "未连接"
        plc_color = '#00aa00' if (self.modbus_client and self.modbus_client.is_connected) else '#ff0000'
        
        tk.Label(plc_frame, text=plc_status, font=self.small_button_font,
                bg='white', fg=plc_color).pack(side=tk.LEFT, padx=(5, 0))
        
        # 分隔线
        tk.Frame(status_frame, width=2, bg='#ddd').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 后端API状态
        api_frame = tk.Frame(status_frame, bg='white')
        api_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(api_frame, text="后端API:", font=self.small_button_font, 
                bg='white', fg='#333333').pack(side=tk.LEFT)
        
        self.api_status_label = tk.Label(api_frame, text="检测中...", font=self.small_button_font,
                                       bg='white', fg='#ff6600')
        self.api_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 测试API连接按钮
        test_api_btn = tk.Button(status_frame, text="测试API", 
                               font=tkFont.Font(family="微软雅黑", size=9),
                               bg='#28a745', fg='white',
                               padx=30, pady=15,  # 增加内边距
                               command=self.test_api_connection)
        test_api_btn.pack(side=tk.RIGHT, padx=10, pady=2)
        
        # 初始测试API连接
        self.test_api_connection()
    
    def create_parameter_section(self, parent):
        """
        创建参数设置区域
        
        Args:
            parent: 父容器
        """
        # 参数设置容器
        param_frame = tk.Frame(parent, bg='white')
        param_frame.pack(fill=tk.X, pady=(60, 80))
        
        # 三个参数设置区域的容器
        params_container = tk.Frame(param_frame, bg='white')
        params_container.pack()
        
        # 每包重量设置区域
        self.create_weight_section(params_container)
        
        # 包装数量设置区域
        self.create_quantity_section(params_container)
        
        # 物料选择区域
        self.create_material_section(params_container)
    
    def create_weight_section(self, parent):
        """
        创建每包重量设置区域
        
        Args:
            parent: 父容器
        """
        # 每包重量容器
        weight_frame = tk.Frame(parent, bg='white')
        weight_frame.pack(side=tk.LEFT, padx=(0, 60))
        
        # 标题标签
        weight_title = tk.Label(weight_frame, text="每包重量", 
                              font=self.label_font, bg='white', fg='#333333')
        weight_title.pack(anchor='w')
        
        # 单位标签
        unit_label = tk.Label(weight_frame, text="克g", 
                            font=tkFont.Font(family="微软雅黑", size=14),
                            bg='white', fg='#666666')
        unit_label.pack(anchor='w', pady=(0, 10))
        
        # 输入框
        weight_entry = tk.Entry(weight_frame, textvariable=self.weight_var,
                          font=tkFont.Font(family="微软雅黑", size=14),  # 增加字体
                          width=25,
                          relief='solid', bd=2,  # 增加边框
                          bg='white', fg='#333333')
        weight_entry.pack(ipady=12)  # 增加内边距
        weight_entry.focus_set()
        
        # 设置输入框占位符效果
        self.setup_placeholder(weight_entry, "请输入目标重量克数")
    
    def create_quantity_section(self, parent):
        """
        创建包装数量设置区域
        
        Args:
            parent: 父容器
        """
        # 包装数量容器
        quantity_frame = tk.Frame(parent, bg='white')
        quantity_frame.pack(side=tk.LEFT, padx=(0, 60))
        
        # 标题标签
        quantity_title = tk.Label(quantity_frame, text="包装数量", 
                                font=self.label_font, bg='white', fg='#333333')
        quantity_title.pack(anchor='w')
        
        # 空白区域（对齐用）
        tk.Label(quantity_frame, text=" ", 
               font=tkFont.Font(family="微软雅黑", size=12),
               bg='white').pack(pady=(0, 10))
        
        # 输入框
        quantity_entry = tk.Entry(quantity_frame, textvariable=self.quantity_var,
                            font=tkFont.Font(family="微软雅黑", size=14),
                            width=25,
                            relief='solid', bd=2,
                            bg='white', fg='#333333')
        quantity_entry.pack(ipady=12)
        quantity_entry.focus_set()
        
        # 设置输入框占位符效果
        self.setup_placeholder(quantity_entry, "请输入所需包装数量")
    
    def create_material_section(self, parent):
        """
        创建物料选择区域
        
        Args:
            parent: 父容器
        """
        # 物料选择容器
        material_frame = tk.Frame(parent, bg='white')
        material_frame.pack(side=tk.LEFT)
        
        # 标题和新增按钮的容器
        title_frame = tk.Frame(material_frame, bg='white')
        title_frame.pack(fill=tk.X)
        
        # 标题标签
        material_title = tk.Label(title_frame, text="物料选择", 
                                font=self.label_font, bg='white', fg='#333333')
        material_title.pack(side=tk.LEFT)
        
        # 新增物料按钮
        new_material_btn = tk.Button(title_frame, text="新增物料", 
                                   font=tkFont.Font(family="微软雅黑", size=10),
                                   bg='#28a745', fg='white',
                                   relief='flat', bd=0,
                                   padx=30, pady=15,  # 增加内边距
                                   command=self.on_new_material_click)
        new_material_btn.pack(side=tk.RIGHT)
        
        # 空白区域（对齐用）
        tk.Label(material_frame, text=" ", 
               font=tkFont.Font(family="微软雅黑", size=6),
               bg='white').pack(pady=0)
    
        # 配置下拉列表的字体大小
        self.root.option_add('*TCombobox*Listbox.Font', ('微软雅黑', 14))
        
        # 下拉选择框
        material_combobox = ttk.Combobox(material_frame, textvariable=self.material_var,
                                       font=self.entry_font,
                                       width=25,
                                       values=self.material_list,
                                       state='readonly',
                                       style="Large.TCombobox")
        material_combobox.pack(ipady=12)
        material_combobox.set(self.material_list[0])  # 设置默认值
        
        # 保存下拉框引用，用于后续刷新
        self.material_combobox = material_combobox
    
    def create_control_section(self, parent):
        """
        创建控制按钮区域
        
        Args:
            parent: 父容器
        """
        # 控制按钮容器
        control_frame = tk.Frame(parent, bg='white')
        control_frame.pack(fill=tk.X, pady=(60, 80))
        
        # 左侧按钮区域
        left_buttons = tk.Frame(control_frame, bg='white')
        left_buttons.pack(side=tk.LEFT)
        
        # 放料+清零按钮
        feed_clear_btn = tk.Button(left_buttons, text="放料+清零", 
                                 font=self.button_font,
                                 bg='#6c757d', fg='white',
                                 relief='flat', bd=0,
                                 padx=40, pady=20,  # 增加内边距
                                 command=self.on_feed_clear_click)
        feed_clear_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # 清料按钮
        clear_btn = tk.Button(left_buttons, text="清料", 
                            font=self.button_font,
                            bg='#6c757d', fg='white',
                            relief='flat', bd=0,
                            padx=40, pady=20,  # 增加内边距
                            command=self.on_clear_click)
        clear_btn.pack(side=tk.LEFT)
        
        # 右侧主要操作按钮
        right_buttons = tk.Frame(control_frame, bg='white')
        right_buttons.pack(side=tk.RIGHT)
        
        # 开始AI生产按钮
        start_ai_btn = tk.Button(right_buttons, text="开始AI生产", 
                               font=tkFont.Font(family="微软雅黑", size=20, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=50, pady=25,  # 增加内边距
                               command=self.on_start_ai_click)
        start_ai_btn.pack()
    
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
            print("[Main] Logo组件创建成功")
        except ImportError as e:
            print(f"[警告] 无法导入logo处理模块: {e}")
    
    # 以下是按钮事件处理函数
    
    def test_api_connection(self):
        """测试后端API连接"""
        def test_thread():
            try:
                if WEBAPI_AVAILABLE:
                    from clients.webapi_client import test_webapi_connection
                    success, message = test_webapi_connection()
                    self.root.after(0, self.handle_api_test_result, success, message)
                else:
                    self.root.after(0, self.handle_api_test_result, False, "WebAPI客户端模块不可用")
            except Exception as e:
                error_msg = f"API连接测试异常：{str(e)}"
                self.root.after(0, self.handle_api_test_result, False, error_msg)
        
        # 更新状态为检测中
        self.api_status_label.config(text="检测中...", fg='#ff6600')
        
        # 启动测试线程
        threading.Thread(target=test_thread, daemon=True).start()
    
    def handle_api_test_result(self, success, message):
        """处理API测试结果"""
        if success:
            self.api_status_label.config(text="已连接", fg='#00aa00')
        else:
            self.api_status_label.config(text="未连接", fg='#ff0000')
    
    def on_ai_icon_click(self):
        """AI图标按钮点击事件"""
        print("点击了AI图标")
        messagebox.showinfo("AI功能", "AI语音助手功能正在开发中，敬请期待...")
    
    def on_home_click(self):
        """返回首页按钮点击事件"""
        print("点击了返回首页")
        
        # 如果有快加时间测定控制器正在运行，先停止它
        if self.coarse_time_controller:
            try:
                self.coarse_time_controller.stop_all_coarse_time_test()
                self.coarse_time_controller.dispose()
                self.coarse_time_controller = None
                print("快加时间测定控制器已停止")
            except Exception as e:
                print(f"停止快加时间测定控制器时发生错误: {e}")
        
        # 如果有清料控制器正在运行，先停止它
        if self.cleaning_controller:
            try:
                self.cleaning_controller.dispose()
                self.cleaning_controller = None
                print("清料控制器已停止")
            except Exception as e:
                print(f"停止清料控制器时发生错误: {e}")
        
        # 重置学习状态管理器
        if self.learning_state_manager:
            try:
                self.learning_state_manager.reset_all_states()
                print("学习状态管理器已重置")
            except Exception as e:
                print(f"重置学习状态管理器时发生错误: {e}")
        
        # 关闭多斗学习状态弹窗（如果存在）
        if self.learning_status_window:
            try:
                self.learning_status_window.destroy()
                self.learning_status_window = None
                print("多斗学习状态弹窗已关闭")
            except Exception as e:
                print(f"关闭多斗学习状态弹窗时发生错误: {e}")
        
        # 如果有主窗口引用，重新显示主窗口
        if self.main_window:
            try:
                # 使用主窗口的便捷方法显示窗口
                if hasattr(self.main_window, 'show_main_window'):
                    self.main_window.show_main_window()
                else:
                    # 备用方式：直接操作root属性
                    if hasattr(self.main_window, 'root'):
                        self.main_window.root.deiconify()
                        self.main_window.root.lift()
                        self.main_window.root.focus_force()
                    else:
                        print("警告：无法显示主窗口")
            except Exception as e:
                print(f"显示主窗口时发生错误: {e}")
        
        # 关闭AI模式界面
        self.root.destroy()
    
    def on_api_settings_click(self):
        """API设置按钮点击事件"""
        print("点击了API设置")
        if API_CONFIG_AVAILABLE:
            try:
                # 导入并显示API设置界面
                self.show_api_settings_dialog()
            except Exception as e:
                messagebox.showerror("设置错误", f"打开API设置失败：{str(e)}")
        else:
            messagebox.showerror("功能不可用", "API配置模块未加载")
    
    def show_api_settings_dialog(self):
        """显示API设置对话框"""
        from config.api_config import set_api_config
        
        settings_window = tk.Toplevel(self.root)
        settings_window.title("后端API设置")
        settings_window.geometry("500x400")
        settings_window.configure(bg='white')
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        self.center_dialog_relative_to_main(settings_window, 500, 400)
        
        # 配置变量
        host_var = tk.StringVar(value=self.api_config.host if self.api_config else "localhost")
        port_var = tk.StringVar(value=str(self.api_config.port) if self.api_config else "8080")
        timeout_var = tk.StringVar(value=str(self.api_config.timeout) if self.api_config else "10")
        protocol_var = tk.StringVar(value=self.api_config.protocol if self.api_config else "http")
        
        # 标题
        tk.Label(settings_window, text="后端API连接配置", 
                font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                bg='white').pack(pady=20)
        
        # 配置项
        config_items = [
            ("API主机地址:", host_var),
            ("API端口:", port_var),
            ("请求超时(秒):", timeout_var),
            ("协议类型:", protocol_var)
        ]
        
        for label_text, var in config_items:
            frame = tk.Frame(settings_window, bg='white')
            frame.pack(pady=10, padx=20, fill=tk.X)
            tk.Label(frame, text=label_text, font=self.small_button_font, 
                    bg='white', width=15, anchor='w').pack(side=tk.LEFT)
            tk.Entry(frame, textvariable=var, font=self.small_button_font, 
                    width=30).pack(side=tk.RIGHT, padx=10)
        
        # 当前配置显示
        info_frame = tk.LabelFrame(settings_window, text="当前配置信息", bg='white', fg='#333333')
        info_frame.pack(fill=tk.X, padx=20, pady=15)
        
        current_url = self.api_config.base_url if self.api_config else "未配置"
        tk.Label(info_frame, text=f"API基础地址: {current_url}", 
                font=tkFont.Font(family="微软雅黑", size=9), 
                bg='white', fg='#666666').pack(pady=5, anchor='w', padx=10)
        
        # 按钮区域
        button_frame = tk.Frame(settings_window, bg='white')
        button_frame.pack(pady=20)
        
        def apply_settings():
            try:
                new_host = host_var.get().strip()
                new_port = int(port_var.get().strip())
                new_timeout = int(timeout_var.get().strip())
                new_protocol = protocol_var.get().strip()
                
                # 更新配置
                set_api_config(new_host, new_port, new_timeout, new_protocol)
                
                # 重新获取配置
                self.api_config = get_api_config()
                
                settings_window.destroy()
                
                # 重新测试连接
                self.test_api_connection()
                
                messagebox.showinfo("配置更新", "API配置已更新，正在重新测试连接...")
                
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的端口号和超时时间")
            except Exception as e:
                messagebox.showerror("配置错误", f"配置更新失败：{str(e)}")
        
        tk.Button(button_frame, text="应用配置", command=apply_settings,
                 font=self.small_button_font, bg='#4a90e2', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="测试连接", command=self.test_api_connection,
                 font=self.small_button_font, bg='#28a745', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=settings_window.destroy,
                 font=self.small_button_font, bg='#e0e0e0', padx=20).pack(side=tk.LEFT, padx=5)
    
    def on_settings_click(self):
        """设置按钮点击事件"""
        print("点击了设置")
        try:
            # 隐藏AI模式界面
            self.root.withdraw()
            
            # 导入并创建系统设置界面
            from system_settings_interface import SystemSettingsInterface
            settings_interface = SystemSettingsInterface(parent=self.root, ai_mode_window=self)
            print("系统设置界面已打开，AI模式界面已隐藏")
        except Exception as e:
            # 如果出错，重新显示AI模式界面
            self.root.deiconify()
            messagebox.showerror("界面错误", f"打开系统设置界面失败：{str(e)}")
    
    def on_new_material_click(self):
        """新增物料按钮点击事件 - 显示第一个弹窗（输入物料名称）"""
        print("点击了新增物料")
        self.show_new_material_name_dialog()
    
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
            name_entry.focus_set()  # 设置焦点到输入框
            
            # 设置占位符
            self.setup_placeholder(name_entry, "请输入物料名称")
            
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
                                  padx=30, pady=15,  # 增加内边距
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            # 下一步按钮
            next_btn = tk.Button(button_frame, text="下一步", 
                                font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                bg='#007bff', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=15,  # 增加内边距
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
            # 读取AI模式界面的当前每包重量值
            current_weight = self.weight_var.get()
            if current_weight and current_weight != "请输入目标重量克数":
                weight_var.set(current_weight)
            
            weight_entry = tk.Entry(weight_frame, textvariable=weight_var,
                                font=tkFont.Font(family="微软雅黑", size=12),
                                width=30, justify='center',
                                relief='solid', bd=1,
                                bg='white', fg='#333333')
            weight_entry.pack(ipady=8, pady=(5, 0))
            weight_entry.focus_set()
            
            # 只有在没有值的时候才设置占位符
            if not weight_var.get():
                self.setup_placeholder(weight_entry, "请输入目标重量")
            
            # 包装数量输入
            quantity_frame = tk.Frame(params_dialog, bg='white')
            quantity_frame.pack(pady=15)
            
            tk.Label(quantity_frame, text="包装数量", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack()
            
            quantity_var = tk.StringVar()
            # 读取AI模式界面的当前包装数量值
            current_quantity = self.quantity_var.get()
            if current_quantity and current_quantity != "请输入所需包装数量":
                quantity_var.set(current_quantity)
            
            quantity_entry = tk.Entry(quantity_frame, textvariable=quantity_var,
                                    font=tkFont.Font(family="微软雅黑", size=12),
                                    width=30, justify='center',
                                    relief='solid', bd=1,
                                    bg='white', fg='#333333')
            quantity_entry.pack(ipady=8, pady=(5, 0))
            quantity_entry.focus_set()
            
            # 只有在没有值的时候才设置占位符
            if not quantity_var.get():
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
                """开始按钮点击事件"""
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
            
                # 重量范围检查
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
                            self.refresh_material_list()
                            
                            # 设置当前选择的物料为新创建的物料
                            self.material_var.set(material_name)
                            
                            # 设置重量和数量到界面
                            self.weight_var.set(str(target_weight))
                            self.quantity_var.set(str(package_quantity))
                            
                            params_dialog.destroy()
                            
                            # 显示创建成功消息
                            messagebox.showinfo("物料创建成功", 
                                              f"物料'{material_name}'已成功创建！\n\n"
                                              f"每包重量：{target_weight}g\n"
                                              f"包装数量：{package_quantity}包\n\n"
                                              f"现在将开始AI学习流程...")
                            
                            # 直接调用AI生产逻辑
                            self.start_ai_production_for_new_material(target_weight, package_quantity, material_name)
                            
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
                    
                    # 临时添加到物料列表
                    self.material_list.append(material_name)
                    self.refresh_material_list()
                    self.material_var.set(material_name)
                    self.weight_var.set(str(target_weight))
                    self.quantity_var.set(str(package_quantity))
                    
                    params_dialog.destroy()
                    
                    # 直接调用AI生产逻辑
                    self.start_ai_production_for_new_material(target_weight, package_quantity, material_name)
            
            # 取消按钮
            cancel_btn = tk.Button(button_frame, text="取消", 
                                  font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=15,  # 增加内边距
                                  command=on_cancel_click)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 30))
            
            # 开始按钮
            start_btn = tk.Button(button_frame, text="开始", 
                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                 bg='#007bff', fg='white',
                                 relief='flat', bd=0,
                                 padx=30, pady=15,  # 增加内边距
                                 command=on_start_click)
            start_btn.pack(side=tk.LEFT, padx=(30, 0))
            
            # 绑定回车键到开始按钮
            params_dialog.bind('<Return>', lambda e: on_start_click())
            
            print(f"[信息] 显示新物料参数输入对话框，物料名称: {material_name}")
            
        except Exception as e:
            error_msg = f"显示新物料参数对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("系统错误", error_msg)
    
    def start_ai_production_for_new_material(self, target_weight: float, package_quantity: int, material_name: str):
        """
        为新物料启动AI生产流程
        
        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量  
            material_name (str): 物料名称
        """
        try:
            print(f"[信息] 为新物料'{material_name}'启动AI生产流程")
            
            # 在后台线程执行AI生产流程，避免阻塞界面
            def ai_production_thread():
                try:
                    self.execute_ai_production_sequence(target_weight, package_quantity, material_name)
                except Exception as e:
                    # 在主线程显示错误信息
                    self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"AI生产过程中发生异常：\n{str(e)}"))
            
            # 启动后台线程
            production_thread = threading.Thread(target=ai_production_thread, daemon=True)
            production_thread.start()
            
        except Exception as e:
            error_msg = f"启动AI生产流程异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("启动异常", error_msg)
    
    def check_plc_status(self, operation_name: str = "操作") -> bool:
        """
        检查PLC连接状态和操作模块可用性
        
        Args:
            operation_name (str): 操作名称，用于错误提示
            
        Returns:
            bool: True表示检查通过，False表示检查失败
        """
        # 检查PLC连接状态
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("连接错误", f"PLC未连接，无法执行{operation_name}！\n请检查PLC连接状态后重试。")
            return False
        
        # 检查PLC操作模块是否可用
        if not self.plc_operations:
            messagebox.showerror("模块错误", f"PLC操作模块未初始化，无法执行{operation_name}！")
            return False
        
        return True
    
    def on_feed_clear_click(self):
        """
        放料+清零按钮点击事件
        执行PLC放料和清零序列操作，包含用户确认流程
        """
        print("点击了放料+清零")
        
        # 检查PLC状态
        if not self.check_plc_status("放料+清零操作"):
            return
        
        # 创建进度弹窗 - 显示"正在放料清零，请稍后"
        progress_window = tk.Toplevel(self.root)
        progress_window.title("放料清零操作")
        progress_window.geometry("550x350")
        progress_window.configure(bg='white')
        progress_window.resizable(False, False)
        progress_window.transient(self.root)
        progress_window.grab_set()
        progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # 居中显示进度弹窗
        self.center_dialog_relative_to_main(progress_window, 550, 350)
        
        # 进度弹窗内容
        tk.Label(progress_window, text="正在放料清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=40)
        
        tk.Label(progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=10)
        
        # 在后台线程中执行PLC操作，避免阻塞界面
        def execute_discharge_clear_operation():
            """
            在后台线程中执行放料和清零操作
            调用plc_operations模块的execute_discharge_and_clear_sequence方法
            """
            try:
                print("[信息] 开始执行PLC放料和清零序列操作")
                
                # 调用PLC操作模块的放料和清零序列方法
                success, message = self.plc_operations.execute_discharge_and_clear_sequence()
                
                print(f"[结果] PLC操作完成: {success}, {message}")
                
                # 在主线程中处理操作结果
                self.root.after(0, self.handle_discharge_clear_result, 
                               progress_window, success, message)
                
            except Exception as e:
                error_msg = f"放料清零操作异常：{str(e)}"
                print(f"[错误] {error_msg}")
                # 在主线程中显示错误信息
                self.root.after(0, self.handle_discharge_clear_result, 
                               progress_window, False, error_msg)
        
        # 启动后台操作线程
        operation_thread = threading.Thread(target=execute_discharge_clear_operation, daemon=True)
        operation_thread.start()
        
        print("[信息] 放料清零操作已启动，正在后台执行...")
    
    def handle_discharge_clear_result(self, progress_window, success, message):
        """
        处理放料清零操作结果（在主线程中调用）
        
        Args:
            progress_window: 进度弹窗对象
            success (bool): 操作是否成功
            message (str): 操作结果消息
        """
        try:
            # 关闭进度弹窗
            progress_window.destroy()
            
            if success:
                print(f"[成功] 放料清零操作完成：{message}")
                # 显示完成确认弹窗
                self.show_discharge_clear_completion_dialog()
            else:
                print(f"[失败] 放料清零操作失败：{message}")
                # 显示错误信息
                messagebox.showerror("操作失败", f"放料清零操作失败：\n{message}")
                
        except Exception as e:
            print(f"[错误] 处理放料清零结果时发生异常：{e}")
            messagebox.showerror("系统错误", f"处理操作结果时发生异常：{str(e)}")
    
    def show_discharge_clear_completion_dialog(self):
        """
        显示放料清零完成确认对话框
        内容为"已清零，请取走余料包装袋并确认"，有"确认 已取走"按钮
        """
        # 创建完成确认弹窗
        completion_window = tk.Toplevel(self.root)
        completion_window.title("操作完成")
        completion_window.geometry("550x350")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        # 居中显示完成确认弹窗
        self.center_dialog_relative_to_main(completion_window, 550, 350)
        
        # 完成确认弹窗内容
        tk.Label(completion_window, text="已清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)
        
        tk.Label(completion_window, text="请取走余料包装袋", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        tk.Label(completion_window, text="并确认", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        # 确认按钮
        def on_confirm_taken():
            """
            确认已取走按钮点击事件
            用户确认已取走余料包装袋后，关闭弹窗返回AI模式页面
            """
            print("[信息] 用户确认已取走余料包装袋")
            completion_window.destroy()  # 关闭弹窗，返回AI模式页面
        
        confirm_btn = tk.Button(completion_window, text="确认 已取走", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=15,  # 增加内边距
                               command=on_confirm_taken)
        confirm_btn.pack(pady=30)
        
        print("[信息] 显示放料清零完成确认对话框")
    
    def on_clear_click(self):
        """
        清料按钮点击事件
        按照要求实现三个弹窗流程：确认 -> 处理中 -> 完成
        """
        print("点击了清料")
        
        # 检查PLC状态
        if not self.check_plc_status("清料操作"):
            return
        
        # 检查清料控制器是否可用
        if not self.cleaning_controller:
            messagebox.showerror("模块错误", "清料控制器未初始化，无法执行清料操作！")
            return
        
        # 显示弹窗：准备清料确认对话框
        self.show_cleaning_preparation_dialog()
    
    def show_cleaning_preparation_dialog(self):
        """
        显示清料准备确认对话框
        内容："准备清料，请放置包装袋或回收桶，点击确认开始"，按钮："确认 开始清料"
        """
        # 创建准备确认弹窗
        preparation_window = tk.Toplevel(self.root)
        preparation_window.title("清料准备")
        preparation_window.geometry("550x350")
        preparation_window.configure(bg='white')
        preparation_window.resizable(False, False)
        preparation_window.transient(self.root)
        preparation_window.grab_set()
        
        # 居中显示准备确认弹窗
        self.center_dialog_relative_to_main(preparation_window, 550, 350)
        
        # 准备确认弹窗内容
        tk.Label(preparation_window, text="准备清料", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)
        
        tk.Label(preparation_window, text="请放置包装袋或回收桶", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        tk.Label(preparation_window, text="点击确认开始", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)
        
        # 确认开始清料按钮
        def on_confirm_start_cleaning():
            """
            确认开始清料按钮点击事件
            关闭弹窗，显示弹窗并启动清料操作
            """
            print("[信息] 用户确认开始清料")
            preparation_window.destroy()  # 关闭图1弹窗
            
            # 显示图2弹窗并启动清料操作
            self.show_cleaning_progress_dialog()
        
        confirm_btn = tk.Button(preparation_window, text="确认 开始清料", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=15,  # 增加内边距
                               command=on_confirm_start_cleaning)
        confirm_btn.pack(pady=30)
        
        print("[信息] 显示清料准备确认对话框")
    
    def show_cleaning_progress_dialog(self):
        """
        显示清料进行中对话框
        内容："正在清料中，请稍后"，无按钮，同时启动清料操作
        """
        # 创建清料进度弹窗
        self.cleaning_progress_window = tk.Toplevel(self.root)
        self.cleaning_progress_window.title("清料操作")
        self.cleaning_progress_window.geometry("550x350")
        self.cleaning_progress_window.configure(bg='white')
        self.cleaning_progress_window.resizable(False, False)
        self.cleaning_progress_window.transient(self.root)
        self.cleaning_progress_window.grab_set()
        
        # 居中显示清料进度弹窗
        self.center_dialog_relative_to_main(self.cleaning_progress_window, 550, 350)
        
        # 清料进度弹窗内容
        tk.Label(self.cleaning_progress_window, text="正在清料中", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=50)
        
        tk.Label(self.cleaning_progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=10)
        
        print("[信息] 显示清料进行中对话框")
        
        # 设置清料控制器事件回调
        self.cleaning_controller.on_cleaning_completed = self.on_cleaning_completed
        self.cleaning_controller.on_cleaning_failed = self.on_cleaning_failed
        self.cleaning_controller.on_log_message = self.on_cleaning_log_message
        
        # 启动清料操作
        success, message = self.cleaning_controller.start_cleaning()
        if not success:
            # 清料启动失败，关闭进度弹窗并显示错误
            self.cleaning_progress_window.destroy()
            messagebox.showerror("清料启动失败", f"无法启动清料操作：\n{message}")
            return
        
        print(f"[信息] 清料操作已启动：{message}")
    
    def on_cleaning_completed(self):
        """
        清料完成事件回调
        关闭弹窗，显示完成弹窗
        """
        print("[信息] 清料操作完成")
        
        # 在主线程中处理界面更新
        self.root.after(0, self._show_cleaning_completion_dialog)
    
    def on_cleaning_failed(self, error_message: str):
        """
        清料失败事件回调
        关闭弹窗，显示错误信息
        """
        print(f"[错误] 清料操作失败：{error_message}")
        
        # 在主线程中处理界面更新
        self.root.after(0, lambda: self._handle_cleaning_failure(error_message))
    
    def on_cleaning_log_message(self, message: str):
        """
        清料日志消息回调
        """
        print(f"[清料日志] {message}")
    
    def _show_cleaning_completion_dialog(self):
        """
        显示清料完成对话框
        内容："清料完成"，按钮："返回"
        """
        try:
            # 关闭进度弹窗
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            print(f"[错误] 关闭清料进度弹窗时发生异常：{e}")
        
        # 创建完成确认弹窗
        completion_window = tk.Toplevel(self.root)
        completion_window.title("清料完成")
        completion_window.geometry("550x350")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()
        
        # 居中显示完成确认弹窗
        self.center_dialog_relative_to_main(completion_window, 550, 350)
        
        # 完成确认弹窗内容
        tk.Label(completion_window, text="清料完成", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=50)
        
        # 返回按钮
        def on_return_click():
            """
            返回按钮点击事件
            发送总清料=0命令，关闭弹窗，显示AI模式界面
            """
            print("[信息] 用户点击返回，停止清料操作")
            
            # 停止清料操作（发送总清料=0命令）
            success, message = self.cleaning_controller.stop_cleaning()
            if not success:
                print(f"[警告] 停止清料操作失败：{message}")
            else:
                print(f"[信息] 清料操作已停止：{message}")
            
            # 关闭弹窗，返回AI模式界面
            completion_window.destroy()
            print("[信息] 返回AI模式界面")
        
        return_btn = tk.Button(completion_window, text="返回", 
                              font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                              bg='#007bff', fg='white',
                              relief='flat', bd=0,
                              padx=30, pady=15,  # 增加内边距
                              command=on_return_click)
        return_btn.pack(pady=20)
        
        print("[信息] 显示清料完成确认对话框")
    
    def _handle_cleaning_failure(self, error_message: str):
        """
        处理清料失败情况
        关闭弹窗，显示错误信息
        """
        try:
            # 关闭图2进度弹窗
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
        except Exception as e:
            print(f"[错误] 关闭清料进度弹窗时发生异常：{e}")
        
        # 显示错误信息
        messagebox.showerror("清料操作失败", f"清料操作失败：\n{error_message}")
        
        # 尝试停止清料操作
        try:
            self.cleaning_controller.stop_cleaning()
        except Exception as e:
            print(f"[错误] 停止清料操作时发生异常：{e}")
    
    def on_start_ai_click(self):
        """开始AI生产按钮点击事件（使用后端API版本）"""
        print("点击了开始AI生产")
        
        # 获取用户输入的参数
        weight = self.weight_var.get()
        quantity = self.quantity_var.get()
        material = self.material_var.get()
        
        # 简单的输入验证
        if weight in ["", "请输入目标重量克数"]:
            messagebox.showwarning("参数缺失", "请输入目标重量")
            return
        
        if quantity in ["", "请输入所需包装数量"]:
            messagebox.showwarning("参数缺失", "请输入包装数量")
            return
        
        if material == "请选择已记录物料":
            messagebox.showwarning("参数缺失", "请选择物料类型")
            return
        
        # 验证重量是否为有效数字
        try:
            target_weight = float(weight)
            if target_weight <= 0:
                messagebox.showerror("参数错误", "目标重量必须大于0")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的目标重量数值")
            return

        # 重量范围检查
        if target_weight < 60 or target_weight > 425:
            messagebox.showerror("参数错误", 
                            f"输入重量超出范围\n\n"
                            f"允许范围：60g - 425g\n"
                            f"当前输入：{target_weight}g\n\n"
                            f"请重新输入正确的重量范围")
            return
        
        # 验证数量是否为有效整数
        try:
            package_quantity = int(quantity)
            if package_quantity <= 0:
                messagebox.showerror("参数错误", "包装数量必须大于0")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的包装数量")
            return
        
        # 检查PLC状态
        if not self.check_plc_status("AI生产"):
            return
        
        # 检查WebAPI可用性
        if not WEBAPI_AVAILABLE:
            messagebox.showerror("WebAPI不可用", 
                            "WebAPI客户端模块未加载！\n\n"
                            "AI模式需要WebAPI客户端来连接后端分析服务。\n"
                            "请确保：\n"
                            "1. clients/webapi_client.py文件存在\n"
                            "2. 后端API服务正在运行\n"
                            "3. 网络连接正常\n"
                            "4. API配置正确")
            return
        
        # 新增：检查是否有历史记录和对应的智能学习参数
        try:
            print(f"[信息] 检查物料'{material}'重量{target_weight}g的历史记录...")
            
            # 查找最新的相同物料和重量的生产记录
            if hasattr(db_manager, 'execute_query'):  # 确保数据库可用
                from database.production_record_dao import ProductionRecordDAO
                latest_record = ProductionRecordDAO.get_latest_production_record_by_material_weight(material, target_weight)
                
                if latest_record:
                    print(f"[信息] 找到历史生产记录: {latest_record.production_id}")
                    
                    # 查找对应的智能学习参数
                    if INTELLIGENT_LEARNING_DAO_AVAILABLE:
                        learned_params = IntelligentLearningDAO.get_all_learning_results_by_material(material, target_weight)
                        
                        if learned_params and len(learned_params) > 0:
                            print(f"[信息] 找到{len(learned_params)}个料斗的智能学习参数，准备直接进入生产")
                            
                            # 显示确认对话框
                            confirm_msg = f"发现历史学习参数！\n\n" \
                                        f"物料：{material}\n" \
                                        f"目标重量：{target_weight}g\n" \
                                        f"包装数量：{package_quantity}包\n\n" \
                                        f"找到历史生产记录：{latest_record.production_id}\n" \
                                        f"已有{len(learned_params)}个料斗的学习参数\n\n" \
                                        f"是否使用历史参数直接开始生产？\n" \
                                        f"（选择'否'将重新开始AI学习）"
                            
                            use_history = messagebox.askyesno("使用历史参数", confirm_msg)
                            
                            if use_history:
                                # 使用历史参数直接进入生产
                                success = self._start_production_with_learned_params(
                                    learned_params, target_weight, package_quantity, material
                                )
                                
                                if success:
                                    return  # 成功则直接返回，不执行后续的AI学习流程
                                else:
                                    # 如果使用历史参数失败，则继续AI学习流程
                                    print("[警告] 使用历史参数失败，将重新开始AI学习")
                        else:
                            print(f"[信息] 历史记录存在但无对应的智能学习参数，将开始AI学习")
                    else:
                        print("[警告] 智能学习DAO不可用，无法查询历史参数")
                else:
                    print(f"[信息] 未找到物料'{material}'重量{target_weight}g的历史记录，将开始AI学习")
                    
        except Exception as e:
            print(f"[错误] 检查历史记录异常: {e}")
            print("[信息] 将继续正常的AI学习流程")
        
        # 如果没有找到历史参数或用户选择重新学习，继续原有的AI学习流程
        confirm_msg = f"AI生产参数确认：\n\n" \
                    f"目标重量：{target_weight} 克\n" \
                    f"包装数量：{package_quantity} 包\n" \
                    f"选择物料：{material}\n\n" \
                    f"确认开始AI自适应生产？"
        
        result = messagebox.askyesno("确认AI生产", confirm_msg)
        if not result:
            return
        
        # 在后台线程执行AI生产流程，避免阻塞界面
        def ai_production_thread():
            try:
                self.execute_ai_production_sequence(target_weight, package_quantity, material)
            except Exception as e:
                # 在主线程显示错误信息
                self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"AI生产过程中发生异常：\n{str(e)}"))
        
        # 启动后台线程
        production_thread = threading.Thread(target=ai_production_thread, daemon=True)
        production_thread.start()
        
    def _start_production_with_learned_params(self, learned_params: List, target_weight: float, 
                                        package_quantity: int, material: str) -> bool:
        """
        使用历史学习参数直接开始生产
        
        Args:
            learned_params: 智能学习参数列表
            target_weight: 目标重量
            package_quantity: 包装数量
            material: 物料名称
            
        Returns:
            bool: 是否成功
        """
        try:
            print(f"[信息] 使用历史学习参数开始生产")
            
            # 步骤1: 启用所有料斗
            self.show_progress_message("步骤1/3", "正在启用所有料斗...")
            
            if BUCKET_DISABLE_AVAILABLE:
                enable_success, enable_message = self._enable_all_buckets()
                if not enable_success:
                    error_msg = f"启用料斗失败：{enable_message}"
                    messagebox.showerror("启用失败", error_msg)
                    return False
            
            # 步骤2: 将历史学习参数写入PLC
            self.show_progress_message("步骤2/3", "正在将历史学习参数写入PLC...")
            
            # 转换为字典格式
            learned_params_dict = {param.bucket_id: param for param in learned_params}
            
            write_success = self._write_product_parameters_to_plc(learned_params_dict, target_weight)
            if not write_success:
                error_msg = "写入历史学习参数失败"
                messagebox.showerror("参数写入失败", error_msg)
                return False
            
            print(f"[成功] 历史学习参数已写入PLC")
            
            # 步骤3: 直接进入生产界面
            self.show_progress_message("步骤3/3", "正在启动生产界面...")
            
            # 准备生产参数
            production_params = {
                'material_name': material,
                'target_weight': target_weight,
                'package_quantity': package_quantity
            }
            
            # 隐藏AI模式界面
            self.root.withdraw()
            
            # 导入并创建生产界面
            from production_interface import create_production_interface
            production_interface = create_production_interface(self.root, self, production_params)
            
            print(f"[成功] 已使用历史参数直接进入生产模式，参数: {production_params}")
            return True
            
        except Exception as e:
            error_msg = f"使用历史参数启动生产异常：{str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("生产启动异常", error_msg)
            
            # 如果出错，重新显示AI模式界面
            try:
                self.root.deiconify()
            except:
                pass
            
            return False
    
    def execute_ai_production_sequence(self, target_weight: float, package_quantity: int, material: str):
        """
        执行AI生产序列（使用后端API版本）
        
        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            material (str): 物料类型
        """
        try:
            print(f"开始执行AI生产序列: 重量={target_weight}g, 数量={package_quantity}, 物料={material}")
            
            # 步骤0: 启用所有料斗（发送禁用地址=0命令）
            self.root.after(0, lambda: self.show_progress_message("步骤0/5", "正在启用所有料斗..."))
            
            if BUCKET_DISABLE_AVAILABLE:
                enable_success, enable_message = self._enable_all_buckets()
                if not enable_success:
                    error_msg = f"启用料斗失败：{enable_message}"
                    self.root.after(0, lambda: messagebox.showerror("启用失败", error_msg))
                    return
                print("所有料斗已启用")
            else:
                print("警告：料斗禁用功能不可用，跳过启用步骤")
            
            # 步骤1: 检查料斗重量并执行清料操作（如需要）
            self.root.after(0, lambda: self.show_progress_message("步骤1/5", "正在检查料斗重量状态..."))
            
            check_success, has_weight, check_message = self.plc_operations.check_any_bucket_has_weight()
            
            if not check_success:
                error_msg = f"检查料斗重量失败：{check_message}"
                self.root.after(0, lambda: messagebox.showerror("检查失败", error_msg))
                return
            
            if has_weight:
                # 显示余料清理进度弹窗
                self.root.after(0, lambda: self.show_material_cleaning_progress_dialog())
                
                # 执行清料操作
                discharge_success, discharge_message = self.plc_operations.execute_discharge_and_clear_sequence()
                
                # 关闭清理进度弹窗
                self.root.after(0, lambda: self.close_material_cleaning_progress_dialog())
                
                if not discharge_success:
                    error_msg = f"清料操作失败：{discharge_message}"
                    self.root.after(0, lambda: messagebox.showerror("清料失败", error_msg))
                    return
                
                print("清料操作完成")
                
                # 显示清零完成确认弹窗（图2样式），等待用户确认后继续
                self.root.after(0, lambda: self.show_cleaning_completion_confirmation_dialog(target_weight, package_quantity, material))
                return  # 暂停当前执行流程，等待用户确认后继续
            else:
                print("料斗无重量，跳过清料操作")
                # 直接进入后续步骤
                self.continue_ai_production_after_cleaning(target_weight, package_quantity, material)
            
        except Exception as e:
            error_msg = f"AI生产序列异常：{str(e)}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
            
    def _enable_all_buckets(self) -> tuple:
        """
        启用所有料斗（向禁用地址发送0命令）
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not self.modbus_client or not self.modbus_client.is_connected:
                return False, "PLC未连接"
            
            success_count = 0
            failed_buckets = []
            
            # 向每个料斗的禁用地址发送0命令
            for bucket_id in range(1, 7):
                try:
                    disable_address = get_bucket_disable_address(bucket_id)
                    success = self.modbus_client.write_coil(disable_address, False)  # False = 0 = 启用
                    
                    if success:
                        success_count += 1
                        print(f"[成功] 料斗{bucket_id}已启用")
                    else:
                        failed_buckets.append(bucket_id)
                        print(f"[失败] 料斗{bucket_id}启用失败")
                        
                except Exception as e:
                    failed_buckets.append(bucket_id)
                    print(f"[错误] 料斗{bucket_id}启用异常: {e}")
            
            if success_count == 6:
                return True, f"所有{success_count}个料斗已成功启用"
            elif success_count > 0:
                return False, f"只有{success_count}/6个料斗启用成功，失败料斗: {failed_buckets}"
            else:
                return False, f"所有料斗启用失败，失败料斗: {failed_buckets}"
                
        except Exception as e:
            error_msg = f"启用料斗操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
            return False, error_msg
    
    def show_material_cleaning_progress_dialog(self):
        """
        显示余料清理进度弹窗
        显示"检测到余料，正在清料处理，请稍后"
        """
        # 创建清理进度弹窗
        self.cleaning_progress_window = tk.Toplevel(self.root)
        self.cleaning_progress_window.title("清料操作")
        self.cleaning_progress_window.geometry("550x350")
        self.cleaning_progress_window.configure(bg='white')
        self.cleaning_progress_window.resizable(False, False)
        self.cleaning_progress_window.transient(self.root)
        self.cleaning_progress_window.grab_set()

        # 居中显示清理进度弹窗
        self.center_dialog_relative_to_main(self.cleaning_progress_window, 550, 350)

        # 清理进度弹窗内容
        tk.Label(self.cleaning_progress_window, text="检测到余料", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)

        tk.Label(self.cleaning_progress_window, text="正在清料处理", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        tk.Label(self.cleaning_progress_window, text="请稍后", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        print("[信息] 显示余料清理进度弹窗")

    def close_material_cleaning_progress_dialog(self):
        """
        关闭余料清理进度弹窗
        """
        try:
            if hasattr(self, 'cleaning_progress_window') and self.cleaning_progress_window:
                self.cleaning_progress_window.destroy()
                self.cleaning_progress_window = None
                print("[信息] 关闭余料清理进度弹窗")
        except Exception as e:
            print(f"[错误] 关闭清理进度弹窗时发生异常：{e}")
    
    def show_cleaning_completion_confirmation_dialog(self, target_weight: float, package_quantity: int, material: str):
        """
        显示清零完成确认对话框
        内容为"已清零，请取走余料包装袋并确认"，有"确认 开始生产"按钮

        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            material (str): 物料类型
        """
        # 创建完成确认弹窗
        completion_window = tk.Toplevel(self.root)
        completion_window.title("操作完成")
        completion_window.geometry("550x350")
        completion_window.configure(bg='white')
        completion_window.resizable(False, False)
        completion_window.transient(self.root)
        completion_window.grab_set()

        # 居中显示完成确认弹窗
        self.center_dialog_relative_to_main(completion_window, 550, 350)

        # 完成确认弹窗内容
        tk.Label(completion_window, text="已清零", 
                font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                bg='white', fg='#333333').pack(pady=30)

        tk.Label(completion_window, text="请取走余料包装袋", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        tk.Label(completion_window, text="并确认", 
                font=tkFont.Font(family="微软雅黑", size=14),
                bg='white', fg='#666666').pack(pady=5)

        # 确认开始生产按钮
        def on_confirm_start_production():
            """
            确认开始生产按钮点击事件
            用户确认已取走余料包装袋后，关闭弹窗并继续AI生产流程
            """
            print("[信息] 用户确认开始生产，继续AI生产流程")
            completion_window.destroy()  # 关闭弹窗

            # 在后台线程中继续执行AI生产的后续步骤
            def continue_production_thread():
                try:
                    self.continue_ai_production_after_cleaning(target_weight, package_quantity, material)
                except Exception as e:
                    # 在主线程显示错误信息
                    self.root.after(0, lambda: messagebox.showerror("AI生产错误", f"继续AI生产过程中发生异常：\n{str(e)}"))

            # 启动后台线程继续生产
            production_thread = threading.Thread(target=continue_production_thread, daemon=True)
            production_thread.start()

        confirm_btn = tk.Button(completion_window, text="确认 开始生产", 
                               font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                               bg='#007bff', fg='white',
                               relief='flat', bd=0,
                               padx=30, pady=15,  # 增加内边距
                               command=on_confirm_start_production)
        confirm_btn.pack(pady=30)

        print("[信息] 显示清零完成确认对话框")
    
    def continue_ai_production_after_cleaning(self, target_weight: float, package_quantity: int, material: str):
        """
        在清料操作完成后继续执行AI生产序列的后续步骤
        包括：步骤2-4（API分析、参数写入、快加时间测定）
        
        Args:
            target_weight (float): 目标重量
            package_quantity (int): 包装数量
            material (str): 物料类型
        """
        try:
            print(f"继续执行AI生产序列后续步骤: 重量={target_weight}g, 数量={package_quantity}, 物料={material}")
            
            # 步骤2: 查询数据库是否有已学习的参数
            self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在查询智能学习数据库..."))
            
            learned_params = None
            use_learned_params = False
            
            if INTELLIGENT_LEARNING_DAO_AVAILABLE:
                # 检查是否有该物料和重量的学习数据
                has_data = IntelligentLearningDAO.has_learning_data(material, target_weight)
                
                if has_data:
                    # 获取所有料斗的学习结果
                    learned_results = IntelligentLearningDAO.get_all_learning_results_by_material(material, target_weight)
                    
                    if learned_results:
                        use_learned_params = True
                        learned_params = {result.bucket_id: result for result in learned_results}
                        self._log(f"✅ 发现{len(learned_results)}个料斗的智能学习数据，将使用已学习参数")
                        
                        # 将智能学习参数写入到PLC
                        self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在使用智能学习参数写入PLC..."))
                        
                        write_success = self._write_learned_parameters_to_plc(learned_params, target_weight)
                        if not write_success:
                            error_msg = "写入智能学习参数失败，回退到API分析模式"
                            self._log(f"❌ {error_msg}")
                            self.root.after(0, lambda: messagebox.showwarning("参数写入失败", error_msg))
                            use_learned_params = False
                    else:
                        self._log("⚠️ 数据库查询无结果，使用API分析模式")
                else:
                    self._log(f"📊 物料'{material}'重量{target_weight}g暂无智能学习数据，使用API分析模式")
            else:
                self._log("⚠️ 智能学习DAO不可用，使用API分析模式")
            
            # 如果没有使用已学习参数，则通过后端API分析
            if not use_learned_params:
                self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在通过后端API分析目标重量对应的快加速度..."))
                
                if not WEBAPI_AVAILABLE:
                    error_msg = "WebAPI客户端模块不可用，无法进行参数分析"
                    self.root.after(0, lambda: messagebox.showerror("WebAPI错误", error_msg))
                    return
                
                # 调用后端API分析
                analysis_success, coarse_speed, analysis_message = analyze_target_weight(target_weight)
                
                if not analysis_success:
                    error_msg = f"后端API分析失败：{analysis_message}\n\n" \
                               f"可能原因：\n" \
                               f"1. 后端API服务器未启动\n" \
                               f"2. 网络连接问题\n" \
                               f"3. API配置错误\n" \
                               f"4. 目标重量超出支持范围\n\n" \
                               f"请检查后端服务状态和API配置后重试。"
                    self.root.after(0, lambda: messagebox.showerror("后端API分析失败", error_msg))
                    return
                
                print(f"后端API分析完成：速度={coarse_speed}档, 消息={analysis_message}")
                
                # 步骤3: 写入参数到所有料斗
                self.root.after(0, lambda: self.show_progress_message("步骤3/4", "正在写入参数到所有料斗..."))
                
                write_success, write_message = self.plc_operations.write_bucket_parameters_all(
                    target_weight=target_weight,
                    coarse_speed=coarse_speed,
                    fine_speed=44,
                    coarse_advance=0,
                    fall_value=0
                )
                
                if not write_success:
                    error_msg = f"参数写入失败：{write_message}"
                    self.root.after(0, lambda: messagebox.showerror("写入失败", error_msg))
                    return
            
            # 步骤4: 启动快加时间测定（如果模块可用）
            self.root.after(0, lambda: self.show_progress_message("步骤4/4", "正在启动快加时间测定..."))
            
            # 在启动快加时间测定之前，立即显示多斗学习状态弹窗
            self.root.after(0, lambda: self.show_multi_bucket_learning_status_dialog())
            
            # 重置学习状态管理器
            if self.learning_state_manager:
                self.learning_state_manager.reset_all_states()
                print("[信息] 学习状态管理器已重置")
            
            try:
                from coarse_time_controller import create_coarse_time_test_controller
                
                # 创建快加时间测定控制器
                self.coarse_time_controller = create_coarse_time_test_controller(self.modbus_client)
        
                # 添加root引用，用于跨线程UI操作
                self.coarse_time_controller.root_reference = self.root
            
                # 立即设置物料名称到快加时间测定控制器
                if hasattr(self.coarse_time_controller, 'set_material_name'):
                    self.coarse_time_controller.set_material_name(material)
                    print(f"[信息] 已设置物料名称到快加时间测定控制器: {material}")
    
                # 同时设置子控制器的root引用
                if hasattr(self.coarse_time_controller, 'flight_material_controller'):
                    self.coarse_time_controller.flight_material_controller.root_reference = self.root
                
                if hasattr(self.coarse_time_controller, 'fine_time_controller'):
                    self.coarse_time_controller.fine_time_controller.root_reference = self.root
                
                # 设置事件回调（保持原有逻辑）
                def on_bucket_completed(bucket_id: int, success: bool, message: str):
                    """处理单个料斗完成事件"""
                    print(f"[完成事件] 料斗{bucket_id}: {'成功' if success else '失败'} - {message}")
                    
                    # 更新学习状态管理器
                    if self.learning_state_manager:
                        # 根据消息内容判断阶段，直接处理单个料斗
                        stage = self._determine_learning_stage_from_message(message)
                        if stage:
                            self.learning_state_manager.complete_bucket_stage(
                                bucket_id, stage, success, message
                            )
                            print(f"[状态更新] 料斗{bucket_id} {stage.value}阶段: {'成功' if success else '失败'}")
                        
                        # 如果是自适应学习成功，立即更新为"学习成功"状态
                        if success and "自适应学习" in message:
                            bucket_state = self.learning_state_manager.get_bucket_state(bucket_id)
                            if bucket_state:
                                from bucket_learning_state_manager import LearningStatus
                                bucket_state.status = LearningStatus.COMPLETED
                                bucket_state.is_successful = True
                                bucket_state.completion_message = message
                                print(f"[状态更新] 料斗{bucket_id}已更新为学习成功状态")
                                
                                # 触发状态变化事件更新界面
                                if hasattr(self.learning_state_manager, 'on_state_changed') and self.learning_state_manager.on_state_changed:
                                    self.learning_state_manager.on_state_changed(bucket_id, bucket_state)
                
                def on_bucket_failed(bucket_id: int, error_message: str, failed_stage: str):
                    """处理料斗学习失败事件"""
                    print(f"[失败事件] 料斗{bucket_id} {failed_stage}阶段失败: {error_message}")
                    
                    # 更新学习状态管理器
                    if self.learning_state_manager:
                        stage = self._get_learning_stage_from_failed_stage(failed_stage)
                        if stage:
                            self.learning_state_manager.complete_bucket_stage(
                                bucket_id, stage, False, error_message
                            )
                            print(f"[状态更新] 料斗{bucket_id} {stage.value}阶段失败: {error_message}")
                    
                    # 在主线程中显示重新学习选择弹窗
                    self.root.after(0, lambda: self.show_relearning_choice_dialog(bucket_id, error_message, failed_stage))
                
                def on_progress_update(bucket_id: int, current_attempt: int, max_attempts: int, message: str):
                    # 更新学习状态管理器（在第一次尝试时设置开始状态）
                    if self.learning_state_manager and current_attempt == 1:
                        stage = self._determine_learning_stage_from_message(message)
                        if stage:
                            self.learning_state_manager.start_bucket_stage(bucket_id, stage)
                            print(f"[状态更新] 料斗{bucket_id}开始{stage.value}阶段")
                    
                    progress_msg = f"料斗{bucket_id}进度: {current_attempt}/{max_attempts} - {message}"
                    self.root.after(0, lambda: self.show_progress_message("步骤4/4", progress_msg))
                    print(f"[测定进度] {progress_msg}")
                
                def on_log_message(message: str):
                    print(f"[测定日志] {message}")
                
                # 设置事件回调
                self.coarse_time_controller.on_bucket_completed = on_bucket_completed
                self.coarse_time_controller.on_bucket_failed = on_bucket_failed
                self.coarse_time_controller.on_progress_update = on_progress_update
                self.coarse_time_controller.on_log_message = on_log_message
                
                # 启动快加时间测定
                if use_learned_params:
                    # 使用智能学习参数，启动测定时使用已学习的快加速度
                    first_learned_result = next(iter(learned_params.values()))
                    test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                        target_weight, first_learned_result.coarse_speed)
                else:
                    # 使用API分析结果
                    test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                        target_weight, coarse_speed)
                
                # 初始化学习状态管理器中各料斗的快加时间测定状态
                if self.learning_state_manager and test_success:
                    for bucket_id in range(1, 7):
                        self.learning_state_manager.start_bucket_stage(bucket_id, LearningStage.COARSE_TIME)
                    print("[信息] 已初始化所有料斗的快加时间测定状态")
                
                if not test_success:
                    error_msg = f"启动快加时间测定失败：{test_message}"
                    self.root.after(0, lambda: messagebox.showerror("测定启动失败", error_msg))
                    # 不return，继续显示完成信息
                
            except ImportError as e:
                error_msg = f"无法导入快加时间测定模块：{str(e)}\n\n请确保相关模块文件存在"
                print(f"警告：{error_msg}")
                # 不中断流程，继续显示完成信息
            except Exception as e:
                error_msg = f"快加时间测定启动异常：{str(e)}"
                print(f"警告：{error_msg}")
                # 不中断流程，继续显示完成信息
                
            print("AI生产序列执行完成，后端API分析和自动化测定正在进行中")
            
        except Exception as e:
            error_msg = f"AI生产序列后续步骤异常：{str(e)}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
            
    def _write_learned_parameters_to_plc(self, learned_params: Dict[int, IntelligentLearning], target_weight: float) -> bool:
        """
        将智能学习参数写入到PLC
        
        Args:
            learned_params: 学习参数字典 {bucket_id: IntelligentLearning}
            target_weight: 目标重量
            
        Returns:
            bool: 是否成功
        """
        try:
            from plc_addresses import BUCKET_PARAMETER_ADDRESSES
            
            success_count = 0
            total_buckets = 6
            
            for bucket_id in range(1, 7):
                if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                    self._log(f"❌ 料斗{bucket_id}地址配置不存在")
                    continue
                
                addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                # 如果有该料斗的学习参数，使用学习参数；否则使用默认值
                if bucket_id in learned_params:
                    learned_result = learned_params[bucket_id]
                    coarse_speed = learned_result.coarse_speed
                    fine_speed = learned_result.fine_speed
                    self._log(f"📊 料斗{bucket_id}使用智能学习参数：快加速度={coarse_speed}档，慢加速度={fine_speed}档")
                else:
                    # 使用默认值（与API分析相同）
                    coarse_speed = 72  # 默认快加速度
                    fine_speed = 44    # 默认慢加速度
                    coarse_advance = 0
                    fall_value = 0
                    self._log(f"📊 料斗{bucket_id}使用默认参数：快加速度={coarse_speed}档，慢加速度={fine_speed}档")
                
                # 写入参数到PLC
                bucket_success = True
                
                # 目标重量
                target_weight_plc = int(target_weight * 10)
                if not self.modbus_client.write_holding_register(addresses['TargetWeight'], target_weight_plc):
                    self._log(f"❌ 料斗{bucket_id}目标重量写入失败")
                    bucket_success = False
                
                # 快加速度
                if not self.modbus_client.write_holding_register(addresses['CoarseSpeed'], coarse_speed):
                    self._log(f"❌ 料斗{bucket_id}快加速度写入失败")
                    bucket_success = False
                
                # 慢加速度
                if not self.modbus_client.write_holding_register(addresses['FineSpeed'], fine_speed):
                    self._log(f"❌ 料斗{bucket_id}慢加速度写入失败")
                    bucket_success = False
                
                # 快加提前量
                if not self.modbus_client.write_holding_register(addresses['CoarseAdvance'], 0):
                    self._log(f"❌ 料斗{bucket_id}快加提前量写入失败")
                    bucket_success = False
                
                # 落差值
                if not self.modbus_client.write_holding_register(addresses['FallValue'], 0):
                    self._log(f"❌ 料斗{bucket_id}落差值写入失败")
                    bucket_success = False
                
                if bucket_success:
                    success_count += 1
                    self._log(f"✅ 料斗{bucket_id}参数写入成功")
            
            if success_count == total_buckets:
                self._log(f"✅ 所有{total_buckets}个料斗的智能学习参数写入成功")
                return True
            else:
                self._log(f"⚠️ 只有{success_count}/{total_buckets}个料斗参数写入成功")
                return False
                
        except Exception as e:
            error_msg = f"写入智能学习参数到PLC异常: {str(e)}"
            self._log(f"❌ {error_msg}")
            return False
        
    def _write_product_parameters_to_plc(self, learned_params: Dict[int, IntelligentLearning], target_weight: float) -> bool:
        """
        将智能学习参数写入到PLC
        
        Args:
            learned_params: 学习参数字典 {bucket_id: IntelligentLearning}
            target_weight: 目标重量
            
        Returns:
            bool: 是否成功
        """
        try:
            from plc_addresses import BUCKET_PARAMETER_ADDRESSES
            
            success_count = 0
            total_buckets = 6
            
            for bucket_id in range(1, 7):
                if bucket_id not in BUCKET_PARAMETER_ADDRESSES:
                    self._log(f"❌ 料斗{bucket_id}地址配置不存在")
                    continue
                
                addresses = BUCKET_PARAMETER_ADDRESSES[bucket_id]
                
                # 如果有该料斗的学习参数，使用学习参数；否则使用默认值
                if bucket_id in learned_params:
                    learned_result = learned_params[bucket_id]
                    coarse_speed = learned_result.coarse_speed
                    fine_speed = learned_result.fine_speed
                    coarse_advance = learned_result.coarse_advance
                    fall_value = learned_result.fall_value
                    self._log(f"📊 料斗{bucket_id}使用智能学习参数：快加速度={coarse_speed}档，慢加速度={fine_speed}档")
                else:
                    # 使用默认值（与API分析相同）
                    coarse_speed = 72  # 默认快加速度
                    fine_speed = 44    # 默认慢加速度
                    coarse_advance = 0
                    fall_value = 0
                    self._log(f"📊 料斗{bucket_id}使用默认参数：快加速度={coarse_speed}档，慢加速度={fine_speed}档")
                
                # 写入参数到PLC
                bucket_success = True
                
                # 目标重量
                target_weight_plc = int(target_weight * 10)
                if not self.modbus_client.write_holding_register(addresses['TargetWeight'], target_weight_plc):
                    self._log(f"❌ 料斗{bucket_id}目标重量写入失败")
                    bucket_success = False
                
                # 快加速度
                if not self.modbus_client.write_holding_register(addresses['CoarseSpeed'], coarse_speed):
                    self._log(f"❌ 料斗{bucket_id}快加速度写入失败")
                    bucket_success = False
                
                # 慢加速度
                if not self.modbus_client.write_holding_register(addresses['FineSpeed'], fine_speed):
                    self._log(f"❌ 料斗{bucket_id}慢加速度写入失败")
                    bucket_success = False
                
                # 快加提前量
                if not self.modbus_client.write_holding_register(addresses['CoarseAdvance'], coarse_advance):
                    self._log(f"❌ 料斗{bucket_id}快加提前量写入失败")
                    bucket_success = False
                
                # 落差值
                if not self.modbus_client.write_holding_register(addresses['FallValue'], fall_value):
                    self._log(f"❌ 料斗{bucket_id}落差值写入失败")
                    bucket_success = False
                
                if bucket_success:
                    success_count += 1
                    self._log(f"✅ 料斗{bucket_id}参数写入成功")
            
            if success_count == total_buckets:
                self._log(f"✅ 所有{total_buckets}个料斗的智能学习参数写入成功")
                return True
            else:
                self._log(f"⚠️ 只有{success_count}/{total_buckets}个料斗参数写入成功")
                return False
                
        except Exception as e:
            error_msg = f"写入智能学习参数到PLC异常: {str(e)}"
            self._log(f"❌ {error_msg}")
            return False
    
    def _log(self, message: str):
        """记录日志"""
        print(f"[AI模式] {message}")
    
    def _determine_learning_stage_from_message(self, message: str):
        """从消息内容判断学习阶段"""
        if not LEARNING_STATE_MANAGER_AVAILABLE:
            return None
            
        message_lower = message.lower()
        
        # 更精确的阶段判断
        if "快加时间测定" in message or ("快加" in message and "时间" in message):
            return LearningStage.COARSE_TIME
        elif "飞料值测定" in message or ("飞料" in message and ("测定" in message or "完成" in message)):
            return LearningStage.FLIGHT_MATERIAL
        elif "慢加时间测定" in message or ("慢加" in message and "时间" in message):
            return LearningStage.FINE_TIME
        elif "自适应学习" in message or "adaptive" in message_lower:
            return LearningStage.ADAPTIVE_LEARNING
        
        # 备用判断
        if "coarse" in message_lower and "time" in message_lower:
            return LearningStage.COARSE_TIME
        elif "flight" in message_lower:
            return LearningStage.FLIGHT_MATERIAL
        elif "fine" in message_lower and "time" in message_lower:
            return LearningStage.FINE_TIME
        
        return None
    
    def _get_learning_stage_from_failed_stage(self, failed_stage: str):
        """将失败阶段字符串转换为学习阶段枚举"""
        if not LEARNING_STATE_MANAGER_AVAILABLE:
            return None
            
        stage_mapping = {
            "coarse_time": LearningStage.COARSE_TIME,
            "flight_material": LearningStage.FLIGHT_MATERIAL,
            "fine_time": LearningStage.FINE_TIME,
            "adaptive_learning": LearningStage.ADAPTIVE_LEARNING
        }
        return stage_mapping.get(failed_stage)
    
    def _format_error_message(self, original_message: str) -> str:
        """
        格式化错误消息，使其更用户友好
        
        Args:
            original_message (str): 原始错误消息
            
        Returns:
            str: 格式化后的用户友好消息
        """
        formatted_msg = original_message
        
        # 移除各种技术性前缀
        prefixes_to_remove = [
            "快加时间分析失败: ",
            "飞料值分析失败: ",
            "飞料值测定失败: ",
            "慢加时间测定失败: ", 
            "自适应学习失败: ",
            "后端API分析失败: ",
            "参数验证失败: ",
            "网络请求失败: ",
            "分析过程异常: ",
            "停止和放料失败: ",
            "重新启动失败: ",
            "更新快加速度失败: "
        ]
        
        for prefix in prefixes_to_remove:
            if formatted_msg.startswith(prefix):
                formatted_msg = formatted_msg.replace(prefix, "")
                break
        
        # 处理技术术语替换
        replacements = {
            "coarse_time_ms": "快加时间",
            "target_weight": "目标重量",
            "current_coarse_speed": "快加速度",
            "fine_time_ms": "慢加时间",
            "flight_material_value": "飞料值",
            "recorded_weights": "实时重量数据",
            "flight_material": "飞料值",
            "HTTP错误": "网络连接错误",
            "JSON解析失败": "数据格式错误",
            "连接超时": "网络超时",
            "连接拒绝": "服务器无响应"
        }
        
        for tech_term, user_friendly in replacements.items():
            formatted_msg = formatted_msg.replace(tech_term, user_friendly)
        
        return formatted_msg.strip()
    
    def show_relearning_choice_dialog(self, bucket_id: int, error_message: str, failed_stage: str):
        """
        显示重新学习选择弹窗
        
        Args:
            bucket_id (int): 料斗ID
            error_message (str): 错误消息
            failed_stage (str): 失败的阶段
        """
        try:
            # 创建重新学习选择弹窗
            relearning_window = tk.Toplevel(self.root)
            relearning_window.title("学习失败")
            relearning_window.geometry("600x400")
            relearning_window.configure(bg='white')
            relearning_window.resizable(False, False)
            relearning_window.transient(self.root)
        
            # 检查多斗学习状态弹窗是否存在且已grab_set
            if (self.learning_status_window and 
                self.learning_status_window.winfo_exists()):
                # 不要grab_set，避免与多斗学习状态弹窗冲突
                pass  
            else:
                relearning_window.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(relearning_window, 600, 400)
        
            # 设置关闭回调，清理活动弹窗跟踪
            def on_dialog_close():
                if hasattr(self, 'active_failure_dialogs'):
                    self.active_failure_dialogs.discard(bucket_id)
                relearning_window.destroy()
            
            relearning_window.protocol("WM_DELETE_WINDOW", on_dialog_close)
            
            # 获取阶段中文名称
            stage_names = {
                "coarse_time": "快加时间测定",
                "flight_material": "飞料值测定", 
                "fine_time": "慢加时间测定",
                "adaptive_learning": "自适应学习"
            }
            stage_name = stage_names.get(failed_stage, failed_stage)
            
            # 标题
            tk.Label(relearning_window, text=f"料斗{bucket_id}学习失败", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=20)
            
            # 失败阶段和错误信息
            info_frame = tk.Frame(relearning_window, bg='white')
            info_frame.pack(pady=10, padx=20, fill=tk.X)
            
            tk.Label(info_frame, text=f"失败阶段：{stage_name}", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack(anchor='w', pady=2)
            
            # 格式化错误消息
            formatted_error = self._format_error_message(error_message)

            # 错误信息（限制长度）
            error_text = formatted_error[:120] + "..." if len(formatted_error) > 120 else formatted_error
            tk.Label(info_frame, text=f"错误信息：{error_text}", 
                    font=tkFont.Font(family="微软雅黑", size=10),
                    bg='white', fg='#666666', 
                    wraplength=450,
                    justify='left').pack(anchor='w', pady=2)
            
            # 提示信息
            tip_frame = tk.LabelFrame(relearning_window, text="重要提示", bg='white', fg='#333333')
            tip_frame.pack(fill=tk.X, padx=20, pady=15)
            
            tip_text = "请先检查料斗是否设置正确，再选择是否重新学习"
            tk.Label(tip_frame, text=tip_text, 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#ff6600', wraplength=450).pack(pady=10, padx=10)
            
            # 选择提示
            tk.Label(relearning_window, text="请选择重新学习方式：", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack(pady=(10, 5))
            
            # 按钮区域
            button_frame = tk.Frame(relearning_window, bg='white')
            button_frame.pack(pady=20)
            
            def on_restart_from_beginning():
                """从头开始学习按钮点击事件"""
                print(f"[信息] 料斗{bucket_id}选择从头开始学习")
                on_dialog_close()  # 先清理弹窗跟踪
                relearning_window.destroy()
                
                # 在后台线程中执行重新学习
                def restart_thread():
                    try:
                        success, message = self.coarse_time_controller.restart_bucket_learning(
                            bucket_id, "from_beginning")
                        
                        if success:
                            print(f"[成功] 料斗{bucket_id}重新学习启动成功: {message}")
                            # 更新学习状态管理器
                            if self.learning_state_manager:
                                self.learning_state_manager.start_bucket_stage(bucket_id, LearningStage.COARSE_TIME)
                        else:
                            print(f"[失败] 料斗{bucket_id}重新学习启动失败: {message}")
                            self.root.after(0, lambda: messagebox.showerror("重新学习失败", 
                                f"料斗{bucket_id}从头开始学习失败：\n{message}"))
                    except Exception as e:
                        error_msg = f"料斗{bucket_id}重新学习异常: {str(e)}"
                        print(f"[错误] {error_msg}")
                        self.root.after(0, lambda: messagebox.showerror("重新学习异常", error_msg))
                
                # 启动重新学习线程
                threading.Thread(target=restart_thread, daemon=True).start()
            
            def on_restart_from_current_stage():
                """从当前阶段开始学习按钮点击事件"""
                print(f"[信息] 料斗{bucket_id}选择从当前阶段({failed_stage})开始学习")
                on_dialog_close()  # 先清理弹窗跟踪
                relearning_window.destroy()
                
                # 在后台线程中执行重新学习
                def restart_thread():
                    try:
                        success, message = self.coarse_time_controller.restart_bucket_learning(
                            bucket_id, "from_current_stage")
                        
                        if success:
                            print(f"[成功] 料斗{bucket_id}重新学习启动成功: {message}")
                            # 更新学习状态管理器
                            if self.learning_state_manager:
                                stage = self._get_learning_stage_from_failed_stage(failed_stage)
                                if stage:
                                    self.learning_state_manager.start_bucket_stage(bucket_id, stage)
                        else:
                            print(f"[失败] 料斗{bucket_id}重新学习启动失败: {message}")
                            self.root.after(0, lambda: messagebox.showerror("重新学习失败", 
                                f"料斗{bucket_id}从当前阶段开始学习失败：\n{message}"))
                    except Exception as e:
                        error_msg = f"料斗{bucket_id}重新学习异常: {str(e)}"
                        print(f"[错误] {error_msg}")
                        self.root.after(0, lambda: messagebox.showerror("重新学习异常", error_msg))
                
                # 启动重新学习线程
                threading.Thread(target=restart_thread, daemon=True).start()
            
            def on_cancel():
                """取消按钮点击事件"""
                print(f"[信息] 用户取消料斗{bucket_id}重新学习")
                on_dialog_close()  # 先清理弹窗跟踪
                relearning_window.destroy()
            
            # 从头开始学习按钮
            restart_from_beginning_btn = tk.Button(button_frame, text="从头开始学习", 
                                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                                 bg='#007bff', fg='white',
                                                 relief='flat', bd=0,
                                                 padx=30, pady=15,  # 增加内边距
                                                 command=on_restart_from_beginning)
            restart_from_beginning_btn.pack(side=tk.LEFT, padx=10)
            
            # 从当前阶段开始学习按钮
            restart_from_current_btn = tk.Button(button_frame, text="当前阶段开始学习", 
                                               font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                               bg='#28a745', fg='white',
                                               relief='flat', bd=0,
                                               padx=30, pady=15,  # 增加内边距
                                               command=on_restart_from_current_stage)
            restart_from_current_btn.pack(side=tk.LEFT, padx=10)
            
            # 取消按钮
            cancel_btn = tk.Button(button_frame, text="取消", 
                                 font=tkFont.Font(family="微软雅黑", size=12),
                                 bg='#6c757d', fg='white',
                                 relief='flat', bd=0,
                                 padx=30, pady=15,  # 增加内边距
                                 command=on_cancel)
            cancel_btn.pack(side=tk.LEFT, padx=10)
            
            print(f"[信息] 显示料斗{bucket_id}重新学习选择弹窗")
            
        except Exception as e:
            # 清理活动弹窗跟踪
            if hasattr(self, 'active_failure_dialogs'):
                self.active_failure_dialogs.discard(bucket_id)
                
            error_msg = f"显示重新学习选择弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("系统错误", error_msg)
    
    def _on_bucket_state_changed(self, bucket_id: int, state):
        """
        处理料斗状态变化事件（实时更新弹窗显示）
        
        Args:
            bucket_id (int): 料斗ID
            state: 料斗学习状态对象
        """
        print(f"[状态变化] 料斗{bucket_id}: {state.get_display_text()}")
    
        # 如果多斗学习状态弹窗存在，更新对应料斗的状态显示
        if self.learning_status_window and bucket_id in self.bucket_status_labels:
            try:
                status_label = self.bucket_status_labels[bucket_id]
                status_text = state.get_display_text()
                status_color = state.get_display_color()
                
                # 在主线程中更新标签
                self.root.after(0, lambda: status_label.config(text=status_text, fg=status_color))
            
                # 如果料斗学习成功，立即检查确认按钮状态
                if state.status.value == "completed" and state.is_successful:
                    self.root.after(100, self._check_confirm_button_state)
                    
            except Exception as e:
                print(f"[错误] 更新料斗{bucket_id}状态显示异常: {e}")
                
    def _force_refresh_learning_status(self):
        """
        强制刷新学习状态显示
        """
        try:
            if not self.learning_status_window or not self.learning_state_manager:
                return
                
            print("[调试] 强制刷新学习状态显示")
            
            # 获取所有状态并更新显示
            all_states = self.learning_state_manager.get_all_states()
            
            for bucket_id in range(1, 7):
                if bucket_id in self.bucket_status_labels and bucket_id in all_states:
                    state = all_states[bucket_id]
                    status_label = self.bucket_status_labels[bucket_id]
                    
                    status_text = state.get_display_text()
                    status_color = state.get_display_color()
                    
                    print(f"[调试] 更新料斗{bucket_id}显示: {status_text} (颜色: {status_color})")
                    
                    # 更新标签显示
                    status_label.config(text=status_text, fg=status_color)
            
            # 更新统计信息
            self._update_learning_statistics()
            
            print("[调试] 强制刷新完成")
            
        except Exception as e:
            print(f"[错误] 强制刷新学习状态异常: {e}")
            import traceback
            traceback.print_exc()
                
    def _check_confirm_button_state(self):
        """
        检查并更新确认按钮的启用状态
        """
        try:
            if not self.learning_status_window or not self.learning_state_manager:
                return

            if not hasattr(self, 'confirm_btn') or not self.confirm_btn.winfo_exists():
                return

            # 获取统计信息
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            learning_count = 0
            not_started_count = 0

            # 统计各状态数量
            all_states = self.learning_state_manager.get_all_states()
            print(f"[调试] 检查按钮状态 - 所有状态: {[(bid, state.status.value, state.current_stage.value) for bid, state in all_states.items()]}")
            
            for bid, state in all_states.items():
                if state.status.value == "learning":
                    learning_count += 1
                elif state.status.value == "not_started":
                    not_started_count += 1

            print(f"[调试] 状态统计 - 成功:{success_count}, 失败:{failed_count}, 学习中:{learning_count}, 未开始:{not_started_count}")

            # 检查是否所有6个料斗都已完成学习
            all_buckets_finished = (success_count + failed_count) >= 6 and learning_count == 0 and not_started_count == 0

            print(f"[调试] 所有料斗完成状态: {all_buckets_finished}")

            if all_buckets_finished:
                # 启用确认按钮
                self.confirm_btn.config(
                    state='normal',
                    bg='#28a745', 
                    fg='white',
                    text="确认 全部完成"
                )
                print("[调试] 确认按钮已启用")    
                # 当确认按钮启用时，停止学习计时器
                self._stop_learning_timer()
                print("[调试] 学习计时器已停止（所有料斗学习完成）")
            else:
                # 禁用确认按钮
                self.confirm_btn.config(
                    state='disabled',
                    bg='#cccccc', 
                    fg='#666666',
                    text="确认"
                )
                print("[调试] 确认按钮保持禁用")

        except Exception as e:
            print(f"[错误] 检查确认按钮状态异常: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_all_learning_completed(self, all_states):
        """
        处理所有料斗学习完成事件（不再自动显示弹窗）
        
        Args:
            all_states: 所有料斗的状态字典
        """
        print("[信息] 所有料斗学习阶段都已完成！")
        
        # 调试：打印所有状态
        if self.learning_state_manager:
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            print(f"[统计] 成功: {success_count}, 失败: {failed_count}, 总计: {total_count}")
            
            for bucket_id, state in all_states.items():
                print(f"[状态] 料斗{bucket_id}: {state.get_display_text()} (当前阶段: {state.current_stage.value})")
        
        # 不再自动显示弹窗，而是等待用户点击确认按钮
        print("[信息] 等待用户在多斗学习状态弹窗中点击确认按钮")
    
    def show_multi_bucket_learning_status_dialog(self):
        """
        显示多斗学习状态弹窗（实时更新版本）
        在参数写入完成、开启测定后立即显示
        """
        try:
            # 如果弹窗已存在，先关闭并清理定时器
            if self.learning_status_window:
                self._stop_learning_timer()
                self._stop_statistics_timer()
                self.learning_status_window.destroy()
                self.learning_status_window = None
                self.bucket_status_labels.clear()
        
            # 重置学习完成通知标志
            self.all_learning_completed_notified = False
            
            # 创建多斗学习状态弹窗
            self.learning_status_window = tk.Toplevel(self.root)
            self.learning_status_window.title("多斗学习状态")
            self.learning_status_window.geometry("800x600")
            self.learning_status_window.configure(bg='white')
            self.learning_status_window.resizable(False, False)
            self.learning_status_window.transient(self.root)
            
            # 禁止用户关闭弹窗（除非点击确认按钮）
            self.learning_status_window.protocol("WM_DELETE_WINDOW", lambda: None)

            # 获取AI模式界面的位置和尺寸
            self.center_dialog_relative_to_main(self.learning_status_window, 800, 600)
            
            # 标题
            tk.Label(self.learning_status_window, text="多斗学习状态", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)

            # 计时器显示
            self.learning_timer_label = tk.Label(self.learning_status_window, text="00:00:00", 
                                               font=tkFont.Font(family="Arial", size=20, weight="bold"),
                                               bg='white', fg='#007bff')
            self.learning_timer_label.pack(pady=(0, 10))
            

            # 启动学习计时器
            self._start_learning_timer()
            
            # 状态网格容器
            grid_frame = tk.Frame(self.learning_status_window, bg='white')
            grid_frame.pack(expand=True, fill='both', padx=20, pady=0)
            
            # 创建6个料斗的状态显示区域（2行3列布局）
            for i in range(6):
                bucket_id = i + 1
                row = i // 3
                col = i % 3
                
                # 料斗状态框架
                bucket_frame = tk.Frame(grid_frame, bg='white', relief='solid', bd=1)
                bucket_frame.grid(row=row, column=col, padx=20, pady=20, sticky='nsew')
                
                # 配置网格权重
                grid_frame.grid_rowconfigure(row, weight=1)
                grid_frame.grid_columnconfigure(col, weight=1)
                
                # 料斗标题
                tk.Label(bucket_frame, text=f"料斗{bucket_id}", 
                        font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                        bg='white', fg='#333333').pack(pady=(10, 5))
                
                # 状态标签（初始状态为"未开始"）
                if self.learning_state_manager:
                    state = self.learning_state_manager.get_bucket_state(bucket_id)
                    status_text = state.get_display_text() if state else "未开始"
                    status_color = state.get_display_color() if state else "#888888"
                else:
                    status_text = "未开始"
                    status_color = "#888888"
                
                status_label = tk.Label(bucket_frame, text=status_text,
                                      font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                      bg='white', fg=status_color)
                status_label.pack(pady=(5, 10))
                
                # 保存状态标签引用，用于实时更新
                self.bucket_status_labels[bucket_id] = status_label
            
            # 统计信息标签
            self.stats_label = tk.Label(self.learning_status_window, text="学习状态：正在初始化...", 
                                      font=tkFont.Font(family="微软雅黑", size=10),
                                      bg='white', fg='#666666')
            self.stats_label.pack(pady=10)
        
            # 按钮区域
            button_frame = tk.Frame(self.learning_status_window, bg='white')
            button_frame.pack(pady=20)
            
            # 确认按钮
            def on_confirm_click():
                """
                确认按钮点击事件
                关闭多斗学习状态弹窗，显示训练完成弹窗
                """
                # 最后一次检查所有料斗是否都已完成（额外保护）
                if self.learning_state_manager:
                    success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()

                    # 检查是否所有6个料斗都已完成
                    if (success_count + failed_count) < 6:
                        messagebox.showwarning("操作提示", "还有料斗未完成学习，请等待所有料斗学习完成后再确认！")
                        return
                
                print("[信息] 用户点击确认，关闭多斗学习状态弹窗")
    
                # 停止学习计时器
                self._stop_learning_timer()
                self._stop_statistics_timer()
                
                # 关闭多斗学习状态弹窗
                self.learning_status_window.destroy()
                self.learning_status_window = None
                self.bucket_status_labels.clear()
                
                # 显示训练完成弹窗
                self._show_training_completed_dialog()
        
            # 取消按钮（新增）
            def on_cancel_click():
                """
                取消按钮点击事件
                停止所有学习过程，向PLC发送停止命令，关闭弹窗并返回AI模式界面
                """
                print("[信息] 用户点击取消，准备停止所有学习过程")

                # 显示确认对话框
                result = messagebox.askyesno(
                    "取消学习确认", 
                    "您确定要取消训练\n"
                    "结束这次生产\n\n"
                    "取消后将：\n"
                    "• 停止所有料斗的学习过程\n"
                    "• 清除当前学习进度\n"
                    "• 返回AI模式主界面\n\n"
                    "此操作不可撤销，是否确认？"
                )
            
                if result:
                    # 用户确认取消，执行取消操作
                    self._execute_cancel_learning_process()
            
            # 确认按钮
            self.confirm_btn = tk.Button(button_frame, text="确认", 
                                        font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                        bg='#cccccc', fg='#666666',  # 禁用状态的颜色
                                        relief='flat', bd=0,
                                        padx=30, pady=15,  # 增加内边距
                                        command=on_confirm_click,
                                        state='disabled')  # 初始状态为禁用
            self.confirm_btn.pack(side=tk.LEFT, padx=(0, 30))  # 右侧留出30像素间距

            # 取消按钮
            self.cancel_btn = tk.Button(button_frame, text="取消", 
                                      font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                      bg='#dc3545', fg='white',
                                      relief='flat', bd=0,
                                      padx=30, pady=15,  # 增加内边距
                                      command=on_cancel_click)
            self.cancel_btn.pack(side=tk.LEFT, padx=(30, 0))  # 左侧留出30像素间距
            
            # 启动定时更新统计信息
            self._start_statistics_timer()
            
            print("[信息] 多斗学习状态弹窗已显示")
            
        except Exception as e:
            error_msg = f"显示多斗学习状态弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            
    def _start_learning_timer(self):
        """启动学习计时器"""
        try:
            import datetime
            
            # 先停止之前的计时器
            self._stop_learning_timer()
            
            # 记录学习开始时间
            self.learning_timer_start_time = datetime.datetime.now()
            self.learning_timer_running = True
            
            def update_learning_timer():
                """更新学习计时器显示"""
                if not self.learning_timer_running:
                    return
                    
                try:
                    # 计算经过的时间
                    current_time = datetime.datetime.now()
                    elapsed_time = current_time - self.learning_timer_start_time
                    
                    # 格式化为 HH:MM:SS
                    total_seconds = int(elapsed_time.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    # 更新标签
                    if hasattr(self, 'learning_timer_label') and self.learning_timer_label.winfo_exists():
                        self.learning_timer_label.config(text=time_str)
                        # 调度下次更新
                        if self.learning_timer_running:
                            self.learning_timer_id = self.root.after(1000, update_learning_timer)
                    else:
                        self.learning_timer_running = False
                        
                except Exception as e:
                    print(f"[错误] 更新学习计时器异常: {e}")
                    self.learning_timer_running = False
            
            # 开始更新计时器
            self.learning_timer_id = self.root.after(1000, update_learning_timer)
            print("[信息] 学习计时器已启动")
            
        except Exception as e:
            error_msg = f"启动学习计时器异常: {str(e)}"
            print(f"[错误] {error_msg}")

    def _stop_learning_timer(self):
        """停止学习计时器"""
        try:
            self.learning_timer_running = False
            
            # 取消定时器
            if hasattr(self, 'learning_timer_id') and self.learning_timer_id:
                self.root.after_cancel(self.learning_timer_id)
                self.learning_timer_id = None
                
            print("[信息] 学习计时器已停止")
            
        except Exception as e:
            print(f"[错误] 停止学习计时器异常: {e}")
    
    def _start_statistics_timer(self):
        """启动统计更新定时器"""
        try:
            # 先停止之前的定时器
            self._stop_statistics_timer()
            
            self.statistics_timer_running = True
            # 立即执行一次，然后开始定时更新
            self._update_learning_statistics()
            
            print("[信息] 统计更新定时器已启动")
            
        except Exception as e:
            print(f"[错误] 启动统计定时器异常: {e}")

    def _stop_statistics_timer(self):
        """停止统计更新定时器"""
        try:
            self.statistics_timer_running = False
            
            # 取消定时器
            if hasattr(self, 'statistics_timer_id') and self.statistics_timer_id:
                self.root.after_cancel(self.statistics_timer_id)
                self.statistics_timer_id = None
                
            print("[信息] 统计更新定时器已停止")
            
        except Exception as e:
            print(f"[错误] 停止统计定时器异常: {e}")

    def _execute_cancel_learning_process(self):
        """
        执行取消学习过程的完整操作
        包括停止所有控制器、发送PLC取消命令、清理状态等
        """
        try:
            print("[信息] 开始执行取消学习过程操作...")

            # 显示取消进度弹窗
            cancel_progress_window = self._show_cancel_progress_dialog()

            # 在后台线程中执行取消操作，避免阻塞界面
            def cancel_thread():
                try:
                    cancel_success = True
                    cancel_messages = []

                    # 步骤1: 停止快加时间测定控制器
                    if self.coarse_time_controller:
                        try:
                            stop_success, stop_msg = self.coarse_time_controller.stop_all_coarse_time_test()
                            if stop_success:
                                cancel_messages.append("✅ 快加时间测定已停止")
                                print("[信息] 快加时间测定控制器已停止")
                            else:
                                cancel_messages.append(f"⚠️ 停止快加时间测定失败: {stop_msg}")
                                print(f"[警告] 停止快加时间测定失败: {stop_msg}")
                        except Exception as e:
                            cancel_messages.append(f"⚠️ 停止快加时间测定异常: {str(e)}")
                            print(f"[警告] 停止快加时间测定异常: {e}")

                    # 步骤2: 向PLC发送取消命令（总启动=0, 总停止=1）
                    if self.check_plc_status("取消学习"):
                        try:
                            # 调用PLC操作的放料清零序列方法来发送取消命令
                            plc_success, plc_msg = self.plc_operations.execute_discharge_and_clear_sequence()
                            if plc_success:
                                cancel_messages.append("✅ PLC取消命令发送成功")
                                print(f"[信息] PLC取消命令发送成功: {plc_msg}")
                            else:
                                cancel_messages.append(f"⚠️ PLC取消命令发送失败: {plc_msg}")
                                print(f"[警告] PLC取消命令发送失败: {plc_msg}")
                                cancel_success = False
                        except Exception as e:
                            cancel_messages.append(f"⚠️ PLC取消命令异常: {str(e)}")
                            print(f"[警告] PLC取消命令异常: {e}")
                            cancel_success = False
                    else:
                        cancel_messages.append("⚠️ PLC未连接，无法发送取消命令")
                        cancel_success = False

                    # 步骤3: 重置学习状态管理器
                    if self.learning_state_manager:
                        try:
                            self.learning_state_manager.reset_all_states()
                            cancel_messages.append("✅ 学习状态已重置")
                            print("[信息] 学习状态管理器已重置")
                        except Exception as e:
                            cancel_messages.append(f"⚠️ 重置学习状态异常: {str(e)}")
                            print(f"[警告] 重置学习状态异常: {e}")

                    # 步骤4: 清理快加时间测定控制器资源
                    if self.coarse_time_controller:
                        try:
                            self.coarse_time_controller.dispose()
                            self.coarse_time_controller = None
                            cancel_messages.append("✅ 控制器资源已清理")
                            print("[信息] 快加时间测定控制器资源已清理")
                        except Exception as e:
                            cancel_messages.append(f"⚠️ 清理控制器资源异常: {str(e)}")
                            print(f"[警告] 清理控制器资源异常: {e}")

                    # 在主线程中处理取消完成
                    self.root.after(0, self._handle_cancel_learning_completed, 
                                  cancel_progress_window, cancel_success, cancel_messages)

                except Exception as e:
                    error_msg = f"取消学习过程异常: {str(e)}"
                    print(f"[错误] {error_msg}")
                    self.root.after(0, self._handle_cancel_learning_completed, 
                                  cancel_progress_window, False, [f"❌ {error_msg}"])

            # 启动取消操作线程
            cancel_thread = threading.Thread(target=cancel_thread, daemon=True)
            cancel_thread.start()

        except Exception as e:
            error_msg = f"执行取消学习过程操作异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("取消操作失败", error_msg)
            
    def _show_cancel_progress_dialog(self):
        """
        显示取消操作进度弹窗
        返回弹窗对象用于后续关闭
        """
        try:
            # 创建取消进度弹窗
            cancel_progress_window = tk.Toplevel(self.root)
            cancel_progress_window.title("取消学习")
            cancel_progress_window.geometry("550x350")
            cancel_progress_window.configure(bg='white')
            cancel_progress_window.resizable(False, False)
            cancel_progress_window.transient(self.root)
            cancel_progress_window.grab_set()
            cancel_progress_window.protocol("WM_DELETE_WINDOW", lambda: None)

            # 居中显示取消进度弹窗
            self.center_dialog_relative_to_main(cancel_progress_window, 550, 350)

            # 取消进度弹窗内容
            tk.Label(cancel_progress_window, text="正在取消学习", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=40)

            tk.Label(cancel_progress_window, text="请稍后", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='white', fg='#666666').pack(pady=10)

            print("[信息] 显示取消学习进度弹窗")
            return cancel_progress_window

        except Exception as e:
            print(f"[错误] 显示取消进度弹窗异常: {e}")
            return None
        
    def _handle_cancel_learning_completed(self, cancel_progress_window, success, messages):
        """
        处理取消学习完成事件（在主线程中调用）
        
        Args:
            cancel_progress_window: 取消进度弹窗对象
            success (bool): 取消操作是否成功
            messages (list): 操作消息列表
        """
        try:
            # 关闭取消进度弹窗
            if cancel_progress_window:
                cancel_progress_window.destroy()
                
            # 停止学习计时器（新增）
            self._stop_learning_timer()
            self._stop_statistics_timer()
            
            # 关闭多斗学习状态弹窗
            if self.learning_status_window:
                self.learning_status_window.destroy()
                self.learning_status_window = None
                self.bucket_status_labels.clear()
                print("[信息] 多斗学习状态弹窗已关闭，学习计时器已停止")
            
            # 准备结果消息
            result_title = "学习已取消" if success else "取消操作完成"
            result_message = "学习过程已成功取消！\n\n操作结果：\n" + "\n".join(messages)
            
            if success:
                result_message += "\n\n✅ 已返回AI模式主界面"
            else:
                result_message += "\n\n⚠️ 部分操作可能未完全成功，请检查系统状态"
            
            # 显示结果信息
            if success:
                messagebox.showinfo(result_title, result_message)
            else:
                messagebox.showwarning(result_title, result_message)
            
            print(f"[信息] 取消学习操作完成，成功: {success}")
            print(f"[信息] 已返回AI模式主界面")
            
        except Exception as e:
            error_msg = f"处理取消学习完成事件异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("系统错误", error_msg)
    
    def _update_learning_statistics(self):
        """
        定时更新学习统计信息
        """
        try:
            if not self.learning_status_window or not self.learning_state_manager:
                self.statistics_timer_running = False
                return
            
            if not self.statistics_timer_running:
                return
            
            # 获取统计信息
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            learning_count = 0
            not_started_count = 0
            
            # 统计各状态数量
            all_states = self.learning_state_manager.get_all_states()
            for state in all_states.values():
                if state.status.value == "learning":
                    learning_count += 1
                elif state.status.value == "not_started":
                    not_started_count += 1
            
            # 更新统计信息显示
            stats_text = f"学习状态：未开始 {not_started_count}个，学习中 {learning_count}个，成功 {success_count}个，失败 {failed_count}个"
            
            if hasattr(self, 'stats_label') and self.stats_label.winfo_exists():
                self.stats_label.config(text=stats_text)
            
            # 检查是否所有6个料斗都已完成学习（成功或失败）
            all_buckets_finished = (success_count + failed_count) >= 6 and learning_count == 0 and not_started_count == 0

            if hasattr(self, 'confirm_btn') and self.confirm_btn.winfo_exists():
                if all_buckets_finished:
                    # 所有料斗都完成了（成功或失败），启用确认按钮
                    self.confirm_btn.config(
                        state='normal',
                        bg='#28a745', 
                        fg='white',
                        text="确认 全部完成"
                    )
                    # 只在第一次检测到完成时打印日志
                    if not self.all_learning_completed_notified:
                        print("[信息] 所有料斗学习完成，确认按钮已启用")
                        self.all_learning_completed_notified = True
                else:
                    # 还有料斗未完成，保持确认按钮禁用状态
                    self.confirm_btn.config(
                        state='disabled',
                        bg='#cccccc', 
                        fg='#666666',
                        text="确认"
                    )
                    # 如果状态从完成变为未完成（例如重新学习），重置通知标志
                    if self.all_learning_completed_notified:
                        self.all_learning_completed_notified = False
                        print("[信息] 检测到学习状态变化，重置完成通知标志")
            
            # 调度下次更新（非递归方式）
            if self.statistics_timer_running:
                self.statistics_timer_id = self.root.after(1000, self._update_learning_statistics)
            
        except Exception as e:
            print(f"[错误] 更新学习统计信息异常: {e}")
            self.statistics_timer_running = False
    
    def _show_training_completed_dialog(self):
        """
        显示训练完成弹窗（第二个弹窗）
        包含计时器功能
        """
        try:
            # 创建训练完成弹窗
            training_window = tk.Toplevel(self.root)
            training_window.title("训练完成")
            training_window.geometry("550x350")
            training_window.configure(bg='white')
            training_window.resizable(False, False)
            training_window.transient(self.root)
            training_window.grab_set()
            
            # 居中显示弹窗
            self.center_dialog_relative_to_main(training_window, 550, 350)
            
            # 训练完成标题
            tk.Label(training_window, text="训练完成", 
                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                    bg='white', fg='#333333').pack(pady=30)
            
            # 计时器区域容器
            timer_frame = tk.Frame(training_window, bg='white')
            timer_frame.pack(pady=20)

            # "已过去"文字和计时器同行显示
            timer_row_frame = tk.Frame(timer_frame, bg='white')
            timer_row_frame.pack()

            # "已过去"文字
            elapsed_label = tk.Label(timer_row_frame, text="已过去", 
                                    font=tkFont.Font(family="微软雅黑", size=18, weight="bold"),
                                    bg='white', fg='#333333')
            elapsed_label.pack(side=tk.LEFT, padx=(0, 10))

            # 计时器显示
            self.timer_label = tk.Label(timer_row_frame, text="00:00:00", 
                                       font=tkFont.Font(family="Arial", size=24, weight="bold"),
                                       bg='white', fg='#333333')
            self.timer_label.pack(side=tk.LEFT)

            # 提示文字（在计时器下方）
            tip_label = tk.Label(timer_frame, text="如果要生产，请点击下方按钮", 
                                font=tkFont.Font(family="微软雅黑", size=12),
                                bg='white', fg='#666666')
            tip_label.pack(pady=(15, 0))
            
            # 开始生产按钮
            def on_start_production_click():
                """开始生产按钮点击事件"""
                training_window.destroy()
                # 停止计时器
                if hasattr(self, 'timer_running'):
                    self.timer_running = False
    
                print("[信息] 用户点击开始生产，切换到生产界面")
            
                try:
                    # 准备生产参数
                    production_params = {
                        'material_name': self.material_var.get() if self.material_var.get() != "请选择已记录物料" else "未知物料",
                        'target_weight': float(self.weight_var.get()) if self.weight_var.get() and self.weight_var.get() != "请输入目标重量克数" else 0,
                        'package_quantity': int(self.quantity_var.get()) if self.quantity_var.get() and self.quantity_var.get() != "请输入所需包装数量" else 0
                    }
                    
                    # 隐藏AI模式界面
                    self.root.withdraw()
                    
                    # 导入并创建生产界面
                    production_interface = create_production_interface(self.root, self, production_params)
                    
                    print(f"生产界面已打开，参数: {production_params}")
                    
                except Exception as e:
                    # 如果出错，重新显示AI模式界面
                    self.root.deiconify()
                    error_msg = f"打开生产界面失败：{str(e)}"
                    print(f"[错误] {error_msg}")
                    messagebox.showerror("界面错误", error_msg)
            
            start_production_btn = tk.Button(training_window, text="开始生产", 
                                           font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                           bg='#007bff', fg='white',
                                           relief='flat', bd=0,
                                           padx=30, pady=15,  # 增加内边距
                                           command=on_start_production_click)
            start_production_btn.pack(pady=30)
            
            # 启动计时器
            self._start_timer()
            
            print("[信息] 显示训练完成弹窗")
            
        except Exception as e:
            error_msg = f"显示训练完成弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
    
    def _start_timer(self):
        """启动计时器"""
        try:
            import datetime
            
            # 记录开始时间
            self.timer_start_time = datetime.datetime.now()
            self.timer_running = True
            
            def update_timer():
                """更新计时器显示"""
                if hasattr(self, 'timer_running') and self.timer_running:
                    try:
                        # 计算经过的时间
                        current_time = datetime.datetime.now()
                        elapsed_time = current_time - self.timer_start_time
                        
                        # 格式化为 HH:MM:SS
                        total_seconds = int(elapsed_time.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        # 更新标签
                        if hasattr(self, 'timer_label') and self.timer_label.winfo_exists():
                            self.timer_label.config(text=time_str)
                            # 继续更新
                            self.root.after(1000, update_timer)
                        else:
                            self.timer_running = False
                    except Exception as e:
                        print(f"[错误] 更新计时器异常: {e}")
                        self.timer_running = False
            
            # 开始更新计时器
            update_timer()
            
        except Exception as e:
            error_msg = f"启动计时器异常: {str(e)}"
            print(f"[错误] {error_msg}")
    
    def show_progress_message(self, step: str, message: str):
        """
        显示进度消息（在主线程中调用）
        
        Args:
            step (str): 步骤信息
            message (str): 进度消息
        """
        print(f"[{step}] {message}")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 如果有快加时间测定控制器正在运行，先停止它
        if self.coarse_time_controller:
            try:
                self.coarse_time_controller.stop_all_coarse_time_test()
                self.coarse_time_controller.dispose()
                self.coarse_time_controller = None
                print("快加时间测定控制器已停止")
            except Exception as e:
                print(f"停止快加时间测定控制器时发生错误: {e}")
        
        # 如果有清料控制器正在运行，先停止它
        if self.cleaning_controller:
            try:
                self.cleaning_controller.dispose()
                self.cleaning_controller = None
                print("清料控制器已停止")
            except Exception as e:
                print(f"停止清料控制器时发生错误: {e}")
        
        # 清理学习状态管理器
        if self.learning_state_manager:
            try:
                self.learning_state_manager.reset_all_states()
                print("学习状态管理器已清理")
            except Exception as e:
                print(f"清理学习状态管理器时发生错误: {e}")
        
        # 关闭多斗学习状态弹窗（如果存在）
        if self.learning_status_window:
            try:
                self.learning_status_window.destroy()
                self.learning_status_window = None
                print("多斗学习状态弹窗已关闭")
            except Exception as e:
                print(f"关闭多斗学习状态弹窗时发生错误: {e}")
        
        # 如果有主窗口引用，重新显示主窗口
        if self.main_window:
            try:
                # 使用主窗口的便捷方法显示窗口
                if hasattr(self.main_window, 'show_main_window'):
                    self.main_window.show_main_window()
                else:
                    # 备用方式：直接操作root属性
                    if hasattr(self.main_window, 'root'):
                        self.main_window.root.deiconify()
                        self.main_window.root.lift()
                        self.main_window.root.focus_force()
                    else:
                        print("警告：无法显示主窗口")
            except Exception as e:
                print(f"显示主窗口时发生错误: {e}")
        
        # 关闭AI模式界面
        self.root.destroy()
    
    def show(self):
        """显示界面（如果是主窗口）"""
        if self.is_main_window:
            self.root.mainloop()

def main():
    """
    主函数 - 程序入口点
    创建并显示AI模式界面
    """
    # 创建AI模式界面实例
    ai_interface = AIModeInterface()
    
    # 居中显示窗口
    ai_interface.root.update_idletasks()
    width = ai_interface.root.winfo_width()
    height = ai_interface.root.winfo_height()
    x = (ai_interface.root.winfo_screenwidth() // 2) - (width // 2)
    y = (ai_interface.root.winfo_screenheight() // 2) - (height // 2)
    ai_interface.root.geometry(f'{width}x{height}+{x}+{y}')
    
    # 显示界面
    ai_interface.show()

# 当作为主程序运行时，启动界面
if __name__ == "__main__":
    main()