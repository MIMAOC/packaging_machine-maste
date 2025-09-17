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

# 导入清料控制器模块
try:
    from material_cleaning_controller import create_material_cleaning_controller
    CLEANING_CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"警告：无法导入清料控制器模块: {e}")
    print(f"详细错误: {str(e)}")
    CLEANING_CONTROLLER_AVAILABLE = False
    

# 导入客户端
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

class SafeLearningStateManager:
    def __init__(self, original_manager):
        self._manager = original_manager
        self._lock = threading.RLock()
        self._disposed = False
    
    def safe_call(self, method_name, *args, **kwargs):
        with self._lock:
            if self._disposed or not self._manager:
                return None
            try:
                method = getattr(self._manager, method_name)
                return method(*args, **kwargs)
            except Exception as e:
                print(f"状态管理器调用异常: {e}")
                return None
    
    def dispose(self):
        with self._lock:
            self._disposed = True
            self._manager = None

class WindowManager:
    def __init__(self):
        self._windows = {}
        self._lock = threading.Lock()
    
    def create_window(self, window_id, create_func):
        with self._lock:
            if window_id in self._windows:
                self.destroy_window(window_id)
            
            window = create_func()
            self._windows[window_id] = window
            return window
    
    def destroy_window(self, window_id):
        with self._lock:
            if window_id in self._windows:
                try:
                    window = self._windows[window_id]
                    if window and window.winfo_exists():
                        window.destroy()
                except:
                    pass
                finally:
                    del self._windows[window_id]

class DialogManager:
    """统一的弹窗管理器"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        
    def create_dialog(self, title, width=550, height=350, **kwargs):
        """创建标准弹窗"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.configure(bg='white')
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 居中显示
        self.center_dialog(dialog, width, height)
        
        return dialog
    
    def center_dialog(self, dialog, width, height):
        """居中显示弹窗"""
        try:
            # 确保窗口信息是最新的
            dialog.update_idletasks()
            self.parent.update_idletasks()

            # 获取父窗口的位置和尺寸
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()

            # 计算相对于父窗口居中的位置
            x = parent_x + (parent_width - width) // 2
            y = parent_y + (parent_height - height) // 2

            # 确保弹窗不会超出屏幕边界
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()

            # 调整坐标，确保不超出屏幕边界
            if x + width > screen_width:
                x = screen_width - width - 20
            if x < 20:
                x = 20
            if y + height > screen_height:
                y = screen_height - height - 20
            if y < 20:
                y = 20

            dialog.geometry(f"{width}x{height}+{x}+{y}")

        except Exception as e:
            print(f"[错误] 弹窗居中失败: {e}")
            # 备用：屏幕居中
            x = (dialog.winfo_screenwidth() - width) // 2
            y = (dialog.winfo_screenheight() - height) // 2
            dialog.geometry(f"{width}x{height}+{x}+{y}")

class InputValidator:
    """输入验证工具类"""
    
    @staticmethod
    def validate_weight(weight_str):
        """验证重量输入"""
        try:
            weight = float(weight_str)
            if weight <= 0:
                return False, "重量必须大于0"
            if weight < 60 or weight > 425:
                return False, f"重量超出范围(60-425g)，当前:{weight}g"
            return True, weight
        except ValueError:
            return False, "请输入有效的重量数值"
    
    @staticmethod
    def validate_quantity(quantity_str):
        """验证数量输入"""
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                return False, "数量必须大于0"
            return True, quantity
        except ValueError:
            return False, "请输入有效的数量"

class DeviceStatusChecker:
    """设备状态检查器"""
    
    def __init__(self, modbus_client, cleaning_controller=None):
        self.modbus_client = modbus_client
        self.cleaning_controller = cleaning_controller
    
    def check_plc_connection(self, operation_name="操作"):
        """检查PLC连接状态"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("连接错误", 
                f"PLC未连接，无法执行{operation_name}！\n请检查PLC连接状态后重试。")
            return False
        return True
    
    def check_cleaning_controller(self):
        """检查清料控制器状态"""
        if not self.cleaning_controller:
            messagebox.showerror("模块错误", "清料控制器未初始化，无法执行清料操作！")
            return False
        return True
    
    def check_all_devices(self, operation_name="操作"):
        """检查所有设备状态"""
        if not self.check_plc_connection(operation_name):
            return False
        return True

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

        # 创建API客户端实例
        self.api_client = None
        if WEBAPI_AVAILABLE:
            try:
                # WebAPIClient already imported in the global try-catch block at the top
                # Just create an instance if available
                self.api_client = None  # Will be set if needed in test_api_connection
                print("WebAPI模块已加载，客户端将在需要时初始化")
            except Exception as e:
                print(f"WebAPI客户端初始化失败: {e}")
                self.api_client = None
        
        # 获取API配置（确保与主页一致）
        self.api_config = None
        if API_CONFIG_AVAILABLE:
            try:
                self.api_config = get_api_config()
                print(f"[信息] API配置已加载: {self.api_config.base_url if self.api_config else 'None'}")
            except Exception as e:
                print(f"[警告] 获取API配置失败: {e}")

        
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
        # self.root.attributes('-fullscreen', True)
        # self.root.state('zoomed')  # Windows系统的最大化
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
                    return 2, 1, 3  # 成功2个，失败1个，总共6个

                def is_all_completed(self):
                    return False
                
                def reset_all_states(self):
                    """模拟重置所有状态方法"""
                    pass

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

                for bucket_id in range(1, 4):
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
        
        # # 后端API状态
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
        version_text = "MHWPM v1.5.1 ©杭州公式人工智能科技有限公司 温州天腾机械有限公司"
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
                if not self.api_client:
                # 如果没有API客户端，尝试直接调用API函数
                    if WEBAPI_AVAILABLE:
                        # 使用导入的analyze_target_weight函数测试连接
                        success, _, message = analyze_target_weight(100)  # 测试用重量
                        self.safe_gui_update(self.handle_api_test_result, success, message)
                    else:
                        self.safe_gui_update(self.handle_api_test_result, False, "WebAPI模块不可用")
                    return
                
                # 使用API客户端测试连接
                result = self.api_client.test_connection()
                self.safe_gui_update(self.handle_api_test_result, result.success, result.message)
                
            except Exception as e:
                error_msg = f"API连接测试异常: {str(e)}"
                print(f"[错误] {error_msg}")
                self.safe_gui_update(self.handle_api_test_result, False, error_msg)
    
        
        # 更新状态为检测中
        self.api_status_label.config(text="检测中...", fg='#ff6600')
        
        # 启动测试线程
        threading.Thread(target=test_thread, daemon=True).start()
    
    def handle_api_test_result(self, success, message):
        """处理API测试结果"""
        try:
            if success:
                self.api_status_label.config(text="已连接", fg='#00aa00')
                print(f"[成功] API连接测试成功: {message}")
            else:
                self.api_status_label.config(text="未连接", fg='#ff0000')
                print(f"[失败] API连接测试失败: {message}")
        except Exception as e:
            print(f"[错误] 更新API状态显示异常: {e}")
            # 备用处理
            try:
                self.api_status_label.config(text="检测失败", fg='#ff0000')
            except:
                pass
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
                if not self.check_plc_status("放料+清零操作"):
                    return
                
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
        按按照要求实现三个弹窗流程：确认 -> 处理中 -> 完成
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
        
        def on_user_confirm(confirmed):
            if confirmed:
                self._continue_ai_production()
            else:
                print("用户取消AI生产")

        
        confirm_msg = f"AI生产参数确认：\n\n目标重量：{target_weight} 克\n包装数量：{package_quantity} 包\n选择物料：{material}\n\n确认开始AI自适应生产？"
        
        # 使用标准messagebox而不是未定义的self.message_box
        result = messagebox.askyesno("确认AI生产", confirm_msg)
        if not result:
            print("用户取消AI生产")
            return
        
        # 继续执行AI生产流程
        def ai_production_thread():
            try:
                self.execute_ai_production_sequence(target_weight, package_quantity, material)
            except Exception as e:
                self.safe_gui_update(
                    lambda: messagebox.showerror("AI生产错误", f"AI生产过程中发生异常：\n{str(e)}")
                )
        
        threading.Thread(target=ai_production_thread, daemon=True).start()
    
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
                    self.root.after(0, lambda: messagebox.showerror("启用失败", error_msg))
                    return
            
            # 步骤2: 将历史学习参数写入PLC
            self.show_progress_message("步骤2/3", "正在将历史学习参数写入PLC...")
            
            # 转换为字典格式
            learned_params_dict = {param.bucket_id: param for param in learned_params}
            
            write_success = self._write_product_parameters_to_plc(learned_params_dict, target_weight)
            if not write_success:
                error_msg = "写入历史学习参数失败，回退到API分析模式"
                self._log(f"❌ {error_msg}")
                self.root.after(0, lambda: messagebox.showwarning("参数写入失败", error_msg))
                use_learned_params = False
            
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
            self.root.after(0, lambda: messagebox.showerror("序列异常", error_msg))
    
    def _enable_all_buckets(self) -> tuple:
        """启用所有料斗，复用已有的PLC检查"""
        # 不再重复检查PLC状态，调用方已检查
        try:
            success_count = 0
            failed_buckets = []
            
            # 向每个料斗的禁用地址发送0命令
            for bucket_id in range(1, 4):
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
            
            if success_count == 3:
                return True, f"所有{success_count}个料斗已成功启用"
            elif success_count > 0:
                return False, f"只有{success_count}/6个料斗启用成功，失败料斗: {failed_buckets}"
            else:
                return False, f"所有料斗启用失败，失败料斗: {failed_buckets}"
                
        except Exception as e:
            error_msg = f"启用料斗操作异常: {str(e)}"
            self._log(f"❌ {error_msg}")
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
            print(f"[错误] 关闭清料进度弹窗时发生异常：{e}")
    
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
        """
        
        print(f"继续执行AI生产序列后续步骤: 重量={target_weight}g, 数量={package_quantity}, 物料={material}")
            
        # 步骤2: 查询数据库是否有已学习的参数
        self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在查询智能学习数据库..."))
            
        learned_params = None
        use_learned_params = False  # 在这里初始化变量
            
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
                        print(f"[成功] 智能学习参数已写入PLC")
                        # 直接跳转到步骤4，传递参数
                        self._start_coarse_time_testing(target_weight, package_quantity, material, use_learned_params, learned_params)
                        return

        # 如果没有使用已学习参数，则通过后端API分析
        if not use_learned_params:
            self.root.after(0, lambda: self.show_progress_message("步骤2/4", "正在通过后端API分析目标重量..."))
            
            if not WEBAPI_AVAILABLE:
                error_msg = "WebAPI客户端模块不可用，无法进行参数分析"
                self.root.after(0, lambda: messagebox.showerror("WebAPI错误", error_msg))
                return
            
            # 在后台线程执行API分析
            def api_analysis_thread():
                try:
                    analysis_success, coarse_speed, analysis_message = analyze_target_weight(target_weight)
                    
                    # 在主线程处理结果
                    self.root.after(0, lambda: self._handle_api_analysis_result(
                        analysis_success, coarse_speed, analysis_message, target_weight, package_quantity, material, use_learned_params
                    ))
                    
                except Exception as e:
                    error_msg = f"API分析异常：{str(e)}"
                    self.root.after(0, lambda: messagebox.showerror("API分析错误", error_msg))
            
            # 启动API分析线程
            threading.Thread(target=api_analysis_thread, daemon=True).start()

    def _handle_api_analysis_result(self, analysis_success, coarse_speed, analysis_message, target_weight, package_quantity, material, use_learned_params):
        """处理API分析结果"""
        if getattr(self, '_is_disposed', False):
            print("[警告] 窗口已销毁，跳过API分析结果处理")
            return
            
        if not analysis_success:
            error_msg = f"后端API分析失败：{analysis_message}"
            self.safe_gui_update(lambda: messagebox.showerror("分析失败", error_msg))
            return
        
        print(f"[成功] API分析完成，快加速度: {coarse_speed}")
        
        # 步骤3: 写入参数到所有料斗
        self.safe_gui_update(lambda: self.show_progress_message("步骤3/4", "正在写入参数到所有料斗..."))
        
        
        write_success, write_message = self.plc_operations.write_bucket_parameters_all(
            target_weight=target_weight,
            coarse_speed=coarse_speed,
            fine_speed=44,
            coarse_advance=0,
            fall_value=0
        )
        
        if not write_success:
            error_msg = f"参数写入失败：{write_message}"
            messagebox.showerror("写入失败", error_msg)
            return
        
        # 继续步骤4，传递参数
        self._start_coarse_time_testing(target_weight, package_quantity, material, use_learned_params, None, coarse_speed)

    def _start_coarse_time_testing(self, target_weight, package_quantity, material, use_learned_params=False, learned_params=None, coarse_speed=None):
        """启动快加时间测定"""
        # 步骤4: 启动快加时间测定
        self.show_progress_message("步骤4/4", "正在启动快加时间测定...")
        
        # 显示多斗学习状态弹窗
        self.show_multi_bucket_learning_status_dialog()
        
        # 重置学习状态管理器
        if self.learning_state_manager:
            self.learning_state_manager.reset_all_states()
            print("[信息] 学习状态管理器已重置")
        
        # 启动快加时间测定控制器
        # ... 原有的快加时间测定逻辑 ...
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
            if use_learned_params and learned_params:
                # 使用智能学习参数，启动测定时使用已学习的快加速度
                first_learned_result = next(iter(learned_params.values()))
                test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                    target_weight, first_learned_result.coarse_speed)
            else:
                # 使用API分析结果
                if coarse_speed is None:
                    error_msg = "快加速度参数缺失，无法启动测定"
                    self.root.after(0, lambda: messagebox.showerror("参数错误", error_msg))
                    return
                test_success, test_message = self.coarse_time_controller.start_coarse_time_test_after_parameter_writing(
                    target_weight, coarse_speed)
            
            # 初始化学习状态管理器中各料斗的快加时间测定状态
            if self.learning_state_manager and test_success:
                for bucket_id in range(1, 4):
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
        
    def _manage_timer(self, timer_type, action):
        """统一的计时器管理方法"""
        if timer_type == "learning":
            if action == "start":
                self._stop_learning_timer()  # 先停止避免重复
                # 启动学习计时器
                self.learning_timer_running = True
                self._start_learning_timer()
            elif action == "stop":
                self._stop_learning_timer()
        elif timer_type == "statistics":
            if action == "start":
                self._stop_statistics_timer()  # 先停止避免重复
                # 启动统计计时器
                self.statistics_timer_running = True
                self._start_statistics_timer()
            elif action == "stop":
                self._stop_statistics_timer()
    
    def _stop_all_timers(self):
        """统一停止所有计时器"""
        self._stop_learning_timer()
        self._stop_statistics_timer()
    
    def _stop_learning_timer(self):
        """改进的学习计时器停止"""
        self.learning_timer_running = False
        if hasattr(self, 'learning_timer_id') and self.learning_timer_id:
            try:
                if hasattr(self, 'root') and self.root:
                    self.root.after_cancel(self.learning_timer_id)
            except (tk.TclError, AttributeError):
                pass  # 窗口已销毁或其他异常
            finally:
                self.learning_timer_id = None
    
    def _stop_statistics_timer(self):
        """改进的统计计时器停止"""
        self.statistics_timer_running = False
        if hasattr(self, 'statistics_timer_id') and self.statistics_timer_id:
            try:
                if hasattr(self, 'root') and self.root:
                    self.root.after_cancel(self.statistics_timer_id)
            except (tk.TclError, AttributeError):
                pass
            finally:
                self.statistics_timer_id = None
    
    def _start_learning_timer(self):
        """启动学习计时器"""
        if not hasattr(self, 'learning_timer_running') or not self.learning_timer_running:
            return
            
        def timer_callback():
            if hasattr(self, 'learning_timer_running') and self.learning_timer_running:
                # 更新学习状态显示
                try:
                    if hasattr(self, 'learning_status_window') and self.learning_status_window:
                        self._update_learning_statistics()
                except Exception as e:
                    print(f"[错误] 学习计时器回调异常: {e}")
                
                # 调度下次执行
                if self.learning_timer_running:
                    self.learning_timer_id = self.root.after(1000, timer_callback)
        
        # 启动计时器
        self.learning_timer_id = self.root.after(1000, timer_callback)
    
    def _start_statistics_timer(self):
        """启动统计计时器"""
        if not hasattr(self, 'statistics_timer_running') or not self.statistics_timer_running:
            return
            
        def timer_callback():
            if hasattr(self, 'statistics_timer_running') and self.statistics_timer_running:
                # 更新统计信息显示
                try:
                    if hasattr(self, 'learning_status_window') and self.learning_status_window:
                        self._update_statistics_display()
                except Exception as e:
                    print(f"[错误] 统计计时器回调异常: {e}")
                
                # 调度下次执行
                if self.statistics_timer_running:
                    self.statistics_timer_id = self.root.after(2000, timer_callback)
        
        # 启动计时器
        self.statistics_timer_id = self.root.after(2000, timer_callback)
    
    def _update_learning_statistics(self):
        """更新学习统计信息"""
        try:
            # 检查窗口和状态管理器是否存在
            if (not hasattr(self, 'learning_status_window') or 
                not self.learning_status_window or 
                not hasattr(self, 'learning_state_manager') or 
                not self.learning_state_manager):
                if hasattr(self, 'statistics_timer_running'):
                    self.statistics_timer_running = False
                return
            
            # 检查窗口是否还存在
            try:
                if not self.learning_status_window.winfo_exists():
                    if hasattr(self, 'statistics_timer_running'):
                        self.statistics_timer_running = False
                    return
            except tk.TclError:
                if hasattr(self, 'statistics_timer_running'):
                    self.statistics_timer_running = False
                return
            
            if not getattr(self, 'statistics_timer_running', False):
                return


            # 获取统计信息
            success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
            learning_count = 0
            not_started_count = 0

            # 统计各状态数量 - 只统计前3个料斗
            all_states = self.learning_state_manager.get_all_states()
            for bucket_id in range(1, 4):  # 只检查前3个料斗
                if bucket_id in all_states:
                    state = all_states[bucket_id]
                    if hasattr(state, 'status'):
                        if state.status.value == "learning":
                            learning_count += 1
                        elif state.status.value == "not_started":
                            not_started_count += 1

            # 更新统计信息显示
            stats_text = f"学习状态：未开始 {not_started_count}个，学习中 {learning_count}个，成功 {success_count}个，失败 {failed_count}个"
            
            # 安全更新标签
            if (hasattr(self, 'stats_label') and 
                self.stats_label):
                try:
                    if self.stats_label.winfo_exists():
                        self.stats_label.config(text=stats_text)
                except tk.TclError:
                    pass
            
            # 检查是否所有3个料斗都已完成学习（成功或失败）
            all_buckets_finished = (success_count + failed_count) >= 3 and learning_count == 0 and not_started_count == 0

            # 安全更新确认按钮状态
            if (hasattr(self, 'confirm_btn') and 
                self.confirm_btn):
                
                try:
                    if self.confirm_btn.winfo_exists():
                        if all_buckets_finished:
                            # 所有料斗都完成了（成功或失败），启用确认按钮
                            self.confirm_btn.config(
                                state='normal',
                                bg='#28a745', 
                                fg='white',
                                text="确认 全部完成"
                            )
                            # 只在第一次检测到完成时打印日志
                            if not getattr(self, 'all_learning_completed_notified', False):
                                print("[信息] 所有料斗学习完成，确认按钮已启用")
                                self.all_learning_completed_notified = True
                                # 当确认按钮启用时，停止学习计时器
                                self._stop_learning_timer()
                                print("[调试] 学习计时器已停止（所有料斗学习完成）")
                        else:
                            # 还有料斗未完成，保持确认按钮禁用状态
                            self.confirm_btn.config(
                                state='disabled',
                                bg='#cccccc', 
                                fg='#666666',
                                text="确认"
                            )
                            # 如果状态从完成变为未完成（例如重新学习），重置通知标志
                            if getattr(self, 'all_learning_completed_notified', False):
                                self.all_learning_completed_notified = False
                                print("[信息] 检测到学习状态变化，重置完成通知标志")
                except tk.TclError:
                    pass
            
            # 调度下次更新（非递归方式）
            if getattr(self, 'statistics_timer_running', False):
                if hasattr(self, 'root') and self.root:
                    try:
                        self.statistics_timer_id = self.root.after(1000, self._update_learning_statistics)
                    except tk.TclError:
                        self.statistics_timer_running = False
            
        except Exception as e:
            print(f"[错误] 更新学习统计信息异常: {e}")
            if hasattr(self, 'statistics_timer_running'):
                self.statistics_timer_running = False
            import traceback
            traceback.print_exc()

    # 修改强制刷新逻辑
    def _force_refresh_learning_status(self):
        """强制刷新学习状态显示 - 3斗版本"""
        try:
            if (not hasattr(self, 'learning_status_window') or 
                not self.learning_status_window or 
                not hasattr(self, 'learning_state_manager') or 
                not self.learning_state_manager):
                return
                
            # 检查窗口是否还存在
            try:
                if not self.learning_status_window.winfo_exists():
                    print("[警告] 学习状态窗口已不存在")
                    return
            except tk.TclError:
                print("[警告] 学习状态窗口已销毁")
                return
                
            print("[调试] 强制刷新学习状态显示（3斗模式）")
            
            # 获取所有状态并更新显示 - 只处理前3个料斗
            all_states = self.learning_state_manager.get_all_states()
            
            for bucket_id in range(1, 4):  # 改为前3个料斗
                if (hasattr(self, 'bucket_status_labels') and 
                    bucket_id in self.bucket_status_labels and 
                    bucket_id in all_states):
                    try:
                        state = all_states[bucket_id]
                        status_label = self.bucket_status_labels[bucket_id]
                        
                        # 检查标签是否还存在
                        try:
                            if not status_label.winfo_exists():
                                print(f"[警告] 料斗{bucket_id}状态标签已不存在")
                                continue
                        except tk.TclError:
                            print(f"[警告] 料斗{bucket_id}状态标签已销毁")
                            continue
                        
                        status_text = state.get_display_text()
                        status_color = state.get_display_color()
                        
                        print(f"[调试] 更新料斗{bucket_id}显示: {status_text} (颜色: {status_color})")
                        
                        # 更新标签显示
                        status_label.config(text=status_text, fg=status_color)
                        
                    except Exception as e:
                        print(f"[错误] 更新料斗{bucket_id}状态显示异常: {e}")
            
            # 更新统计信息
            self._update_learning_statistics()
            
            # 强制刷新窗口显示
            try:
                self.learning_status_window.update_idletasks()
            except (tk.TclError, AttributeError):
                pass
            
            print("[调试] 强制刷新完成（3斗模式）")
            
        except Exception as e:
            print(f"[错误] 强制刷新学习状态异常: {e}")
            import traceback
            traceback.print_exc()


    
    def _update_statistics_display(self):
        """更新统计显示"""
        try:
            # 这里可以添加更多的统计信息更新逻辑
            pass
        except Exception as e:
            print(f"[错误] 更新统计显示异常: {e}")
    
    def show_progress_message(self, step, message):
        """改进的进度消息显示"""
        try:
            progress_text = f"{step}: {message}"
            print(f"[进度] {progress_text}")
            
            # 安全更新GUI
            def update_gui():
                try:
                    # 如果有进度标签，更新显示
                    if hasattr(self, 'progress_label') and self.progress_label:
                        self.progress_label.config(text=progress_text)
                        
                    # 如果有学习状态窗口，在其中显示进度
                    if (hasattr(self, 'learning_status_window') and 
                        self.learning_status_window and
                        hasattr(self, 'progress_display_label') and
                        self.progress_display_label):
                        self.progress_display_label.config(text=progress_text)
                except Exception as e:
                    print(f"更新进度显示时发生错误: {e}")
            
            self.safe_gui_update(update_gui)
                    
        except Exception as e:
            print(f"[错误] 显示进度消息异常: {e}")
    
    def _log(self, message):
        """记录日志消息"""
        print(f"[AI模式] {message}")
    
    def _write_learned_parameters_to_plc(self, learned_params_dict, target_weight):
        """将智能学习参数写入PLC"""
        try:
            if not self.plc_operations:
                print("[错误] PLC操作模块不可用")
                return False
            
            success_count = 0
            total_buckets = len(learned_params_dict)
            
            for bucket_id, learned_param in learned_params_dict.items():
                try:
                    # 写入该料斗的学习参数
                    write_success, write_message = self.plc_operations.write_bucket_parameters_single(
                        bucket_id=bucket_id,
                        target_weight=target_weight,
                        coarse_speed=learned_param.coarse_speed,
                        fine_speed=learned_param.fine_speed,
                        coarse_advance=learned_param.coarse_advance,
                        fall_value=learned_param.fall_value
                    )
                    
                    if write_success:
                        success_count += 1
                        print(f"[成功] 料斗{bucket_id}智能学习参数已写入PLC")
                    else:
                        print(f"[失败] 料斗{bucket_id}参数写入失败: {write_message}")
                        
                except Exception as e:
                    print(f"[错误] 料斗{bucket_id}参数写入异常: {e}")
            
            if success_count == total_buckets:
                print(f"[成功] 所有{total_buckets}个料斗的智能学习参数已写入PLC")
                return True
            else:
                print(f"[警告] 只有{success_count}/{total_buckets}个料斗参数写入成功")
                return False
                
        except Exception as e:
            print(f"[错误] 写入智能学习参数异常: {e}")
            return False
    
    def _write_product_parameters_to_plc(self, learned_params_dict, target_weight):
        """将产品参数写入PLC（兼容方法）"""
        return self._write_learned_parameters_to_plc(learned_params_dict, target_weight)
    
    def show_multi_bucket_learning_status_dialog(self):
        """显示多斗学习状态对话框"""
        try:
            # 如果已经有窗口存在，先关闭
            if hasattr(self, 'learning_status_window') and self.learning_status_window:
                self._stop_learning_timer()
                self._stop_statistics_timer()
                try:
                    self.learning_status_window.destroy()
                except:
                    pass
                self.learning_status_window = None
                if hasattr(self, 'bucket_status_labels'):
                    self.bucket_status_labels.clear()
        
            # 初始化属性（如果不存在）
            if not hasattr(self, 'bucket_status_labels'):
                self.bucket_status_labels = {}
            if not hasattr(self, 'all_learning_completed_notified'):
                self.all_learning_completed_notified = False
            
            # 重置学习完成通知标志
            self.all_learning_completed_notified = False


            # 创建学习状态弹窗
            self.learning_status_window = tk.Toplevel(self.root)
            self.learning_status_window.title("多斗学习状态")
            self.learning_status_window.geometry("600x500")
            self.learning_status_window.configure(bg='white')
            self.learning_status_window.resizable(False, False)
            self.learning_status_window.transient(self.root)

            # 禁止用户关闭弹窗（除非点击确认按钮）
            self.learning_status_window.protocol("WM_DELETE_WINDOW", lambda: None)

            # 立即更新窗口显示，避免空白
            self.learning_status_window.update_idletasks()
            
            # 居中显示
            self.center_dialog_relative_to_main(self.learning_status_window, 600, 400)
            
            # 标题
            title_label =tk.Label(self.learning_status_window, text="料斗学习状态监控", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)
            title_label.pack(pady=20)

            
            # 计时器显示
            self.learning_timer_label = tk.Label(self.learning_status_window, text="00:00:00", 
                                           font=tkFont.Font(family="Arial", size=20, weight="bold"),
                                           bg='white', fg='#007bff')
            self.learning_timer_label.pack(pady=(0, 10))
            
            # 立即更新显示
            self.learning_status_window.update()
            
            # 状态显示区域
            grid_frame = tk.Frame(self.learning_status_window, bg='white')
            grid_frame.pack(expand=True, fill='both', padx=20, pady=0)
            
            
            # 创建3个料斗的状态显示区域（1行3列布局）
            for i in range(3):  # 改为3个料斗
                bucket_id = i + 1
                row = 0  # 全部在第一行
                col = i
                
                # 料斗状态框架
                bucket_frame = tk.Frame(grid_frame, bg='white', relief='solid', bd=1)
                bucket_frame.grid(row=row, column=col, padx=20, pady=20, sticky='nsew')
                
                # 配置网格权重
                grid_frame.grid_rowconfigure(row, weight=1)
                grid_frame.grid_columnconfigure(col, weight=1)
                
                # 料斗标题
                bucket_title = tk.Label(bucket_frame, text=f"料斗{bucket_id}", 
                        font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                        bg='white', fg='#333333')
                bucket_title.pack(pady=(10, 5))
                
                # 获取初始状态
                if hasattr(self, 'learning_state_manager') and self.learning_state_manager:
                    state = self.learning_state_manager.get_bucket_state(bucket_id)
                    status_text = state.get_display_text() if state else "未开始"
                    status_color = state.get_display_color() if state else "#888888"
                else:
                    status_text = "未开始"
                    status_color = "#888888"
                
                # 状态标签
                status_label = tk.Label(bucket_frame, text=status_text,
                                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                    bg='white', fg=status_color)
                status_label.pack(pady=(5, 10))
                
                # 保存状态标签引用，用于实时更新
                self.bucket_status_labels[bucket_id] = status_label
            
            # 立即更新网格显示
            grid_frame.update_idletasks()
            
            # 统计信息标签
            self.stats_label = tk.Label(self.learning_status_window, text="学习状态：正在初始化...", 
                                    font=tkFont.Font(family="微软雅黑", size=10),
                                    bg='white', fg='#666666')
            self.stats_label.pack(pady=10)

            
            # 按钮区域
            button_frame = tk.Frame(self.learning_status_window, bg='white')
            button_frame.pack(pady=20)
            
            # 确认按钮处理函数
            def on_confirm_click():
                """确认按钮点击事件"""
                # 最后一次检查所有料斗是否都已完成
                if hasattr(self, 'learning_state_manager') and self.learning_state_manager:
                    success_count, failed_count, total_count = self.learning_state_manager.get_completed_count()
                    if (success_count + failed_count) < 3:  # 改为3
                        messagebox.showwarning("操作提示", "还有料斗未完成学习，请等待所有料斗学习完成后再确认！")
                        return
                
                print("[信息] 用户点击确认，关闭多斗学习状态弹窗")

                # 停止学习计时器
                self._stop_learning_timer()
                self._stop_statistics_timer()
                
                # 关闭多斗学习状态弹窗
                if hasattr(self, 'learning_status_window') and self.learning_status_window:
                    self.learning_status_window.destroy()
                    self.learning_status_window = None
                if hasattr(self, 'bucket_status_labels'):
                    self.bucket_status_labels.clear()
                
                # 显示训练完成弹窗
                if hasattr(self, '_show_training_completed_dialog'):
                    self._show_training_completed_dialog()


            # 取消按钮处理函数
            def on_cancel_click():
                """取消按钮点击事件"""
                print("[信息] 用户点击取消，准备停止所有学习过程")
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
                    if hasattr(self, '_execute_cancel_learning_process'):
                        self._execute_cancel_learning_process()

            # 确认按钮（初始禁用）
            self.confirm_btn = tk.Button(button_frame, text="确认", 
                                        font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                        bg='#cccccc', fg='#666666',
                                        relief='flat', bd=0,
                                        padx=30, pady=15,
                                        command=on_confirm_click,
                                        state='disabled')
            self.confirm_btn.pack(side=tk.LEFT, padx=(0, 30))

            # 取消按钮
            self.cancel_btn = tk.Button(button_frame, text="取消", 
                                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                    bg='#dc3545', fg='white',
                                    relief='flat', bd=0,
                                    padx=30, pady=15,
                                    command=on_cancel_click)
            self.cancel_btn.pack(side=tk.LEFT, padx=(30, 0))


            # 最终更新显示
            self.learning_status_window.update()
            
            # 启动计时器（延迟启动，避免冲突）
            self.root.after(500, self._delayed_start_timers)
            
            # 立即更新一次状态显示
            self.root.after(100, self._force_refresh_learning_status)
            
            print("[信息] 多斗学习状态弹窗已显示（3斗模式）")
            
        except Exception as e:
            error_msg = f"显示多斗学习状态弹窗异常: {str(e)}"
            print(f"[错误] {error_msg}")
            import traceback
            traceback.print_exc()
            
    
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
        """从失败阶段字符串获取学习阶段枚举"""
        if not LEARNING_STATE_MANAGER_AVAILABLE:
            return None
            
        stage_mapping = {
            "coarse_time": LearningStage.COARSE_TIME,
            "flight_material": LearningStage.FLIGHT_MATERIAL,
            "fine_time": LearningStage.FINE_TIME,
            "adaptive_learning": LearningStage.ADAPTIVE_LEARNING
        }
        
        return stage_mapping.get(failed_stage, None)
    
    def show_relearning_choice_dialog(self, bucket_id: int, error_message: str, failed_stage: str):
        """显示重新学习选择对话框"""
        try:
            # 创建重新学习选择弹窗
            relearning_window = tk.Toplevel(self.root)
            relearning_window.title("学习失败")
            relearning_window.geometry("600x400")
            relearning_window.configure(bg='white')
            relearning_window.resizable(False, False)
            relearning_window.transient(self.root)
            relearning_window.grab_set()
            
            # 居中显示
            self.center_dialog_relative_to_main(relearning_window, 600, 400)
            
            # 标题
            tk.Label(relearning_window, text=f"料斗{bucket_id}学习失败", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#ff0000').pack(pady=20)
            
            # 错误信息
            tk.Label(relearning_window, text=f"失败阶段：{failed_stage}", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#333333').pack(pady=5)
            
            tk.Label(relearning_window, text=f"错误信息：{error_message}", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#666666', wraplength=500).pack(pady=10)
            
            # 选择提示
            tk.Label(relearning_window, text="请选择处理方式：", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack(pady=20)
            
            # 按钮区域
            button_frame = tk.Frame(relearning_window, bg='white')
            button_frame.pack(pady=20)
            
            def on_retry_click():
                """重新学习按钮点击事件"""
                print(f"[用户选择] 料斗{bucket_id}重新学习{failed_stage}阶段")
                relearning_window.destroy()
                # 这里可以添加重新学习的逻辑
                
            def on_skip_click():
                """跳过按钮点击事件"""
                print(f"[用户选择] 料斗{bucket_id}跳过{failed_stage}阶段")
                relearning_window.destroy()
                # 这里可以添加跳过的逻辑
                
            def on_stop_click():
                """停止学习按钮点击事件"""
                print(f"[用户选择] 停止所有学习")
                relearning_window.destroy()
                # 这里可以添加停止学习的逻辑
            
            # 重新学习按钮
            retry_btn = tk.Button(button_frame, text="重新学习", 
                                 font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                 bg='#007bff', fg='white',
                                 relief='flat', bd=0,
                                 padx=30, pady=15,
                                 command=on_retry_click)
            retry_btn.pack(side=tk.LEFT, padx=10)
            
            # 跳过按钮
            skip_btn = tk.Button(button_frame, text="跳过此料斗", 
                                font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                bg='#ffc107', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=15,
                                command=on_skip_click)
            skip_btn.pack(side=tk.LEFT, padx=10)
            
            # 停止学习按钮
            stop_btn = tk.Button(button_frame, text="停止学习", 
                                font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                                bg='#dc3545', fg='white',
                                relief='flat', bd=0,
                                padx=30, pady=15,
                                command=on_stop_click)
            stop_btn.pack(side=tk.LEFT, padx=10)
            
            print(f"[信息] 显示料斗{bucket_id}重新学习选择对话框")
            
        except Exception as e:
            print(f"[错误] 显示重新学习选择对话框异常: {e}")
            messagebox.showerror("显示错误", f"无法显示重新学习选择窗口：{str(e)}")
    
    def _on_bucket_state_changed(self, bucket_id: int, bucket_state):
        """料斗状态变化事件回调"""
        try:
            # 从bucket_state中提取状态信息
            stage_text = bucket_state.current_stage.value if bucket_state.current_stage else '未知阶段'
            status_text = bucket_state.status.value if bucket_state.status else '未知状态'
            message = bucket_state.completion_message if hasattr(bucket_state, 'completion_message') else ''
            
            print(f"[状态变化] 料斗{bucket_id} {stage_text}: {status_text} - {message}")
            
            # 更新界面显示
            if hasattr(self, 'bucket_status_labels') and bucket_id in self.bucket_status_labels:
                status_label = self.bucket_status_labels[bucket_id]
                
                # 根据状态设置颜色和文本
                if bucket_state.status:
                    if bucket_state.status.value == "completed":
                        status_label.config(text="学习完成", fg='#00aa00')
                    elif bucket_state.status.value == "failed":
                        status_label.config(text="学习失败", fg='#ff0000')
                    elif bucket_state.status.value == "learning":
                        status_label.config(text="学习中", fg='#4a90e2')
                    else:
                        status_label.config(text="未开始", fg='#888888')
                else:
                    status_label.config(text=message, fg='#666666')
            
            # 更新统计信息
            self._update_learning_statistics()
            
        except Exception as e:
            print(f"[错误] 处理料斗状态变化异常: {e}")
    
    def _on_all_learning_completed(self, all_states):
        """所有学习完成事件回调"""
        try:
            print("[信息] 所有料斗学习已完成")
            
            # 显示完成通知
            if not self.all_learning_completed_notified:
                self.all_learning_completed_notified = True
                messagebox.showinfo("学习完成", "所有料斗的学习过程已完成！")
            
        except Exception as e:
            print(f"[错误] 处理学习完成事件异常: {e}")
    
    def safe_gui_update(self, func, *args, **kwargs):
        """改进的线程安全GUI更新"""
        try:
            # 检查窗口是否仍然存在
            if (hasattr(self, 'root') and self.root and 
                hasattr(self.root, 'winfo_exists') and 
                self.root.winfo_exists() and 
                not getattr(self, '_is_disposed', False)):
                self.root.after(0, func, *args, **kwargs)
        except Exception as e:
            print(f"[错误] 安全GUI更新异常: {e}")
    
    def on_closing(self):
        """改进的窗口关闭事件处理"""
        try:
            print("[AI模式] 正在关闭AI模式界面...")
            
            # 设置销毁标志
            self._is_disposed = True
            
            # 停止所有计时器
            self._stop_all_timers()
            
            # 清理控制器资源
            if hasattr(self, 'coarse_time_controller') and self.coarse_time_controller:
                try:
                    if hasattr(self.coarse_time_controller, 'stop_all_coarse_time_test'):
                        self.coarse_time_controller.stop_all_coarse_time_test()
                    if hasattr(self.coarse_time_controller, 'dispose'):
                        self.coarse_time_controller.dispose()
                    self.coarse_time_controller = None
                    print("快加时间测定控制器已停止")
                except Exception as e:
                    print(f"停止快加时间测定控制器时发生错误: {e}")
            
            if hasattr(self, 'cleaning_controller') and self.cleaning_controller:
                try:
                    if hasattr(self.cleaning_controller, 'dispose'):
                        self.cleaning_controller.dispose()
                    self.cleaning_controller = None
                    print("清料控制器已停止")
                except Exception as e:
                    print(f"停止清料控制器时发生错误: {e}")
            
            # 关闭所有子窗口
            self._close_all_child_windows()
            
            # 清理学习状态管理器
            if hasattr(self, 'learning_state_manager') and self.learning_state_manager:
                try:
                    self.learning_state_manager.reset_all_states()
                    print("学习状态管理器已重置")
                except Exception as e:
                    print(f"重置学习状态管理器时发生错误: {e}")
            
            # 销毁主窗口
            if hasattr(self, 'root') and self.root:
                self.root.destroy()
            
        except Exception as e:
            print(f"[错误] 关闭AI模式界面异常: {e}")
            # 强制销毁
            try:
                if hasattr(self, 'root') and self.root:
                    self.root.destroy()
            except:
                pass
    
    def _close_all_child_windows(self):
        """关闭所有子窗口"""
        child_windows = [
            'learning_status_window',
            'cleaning_progress_window'
        ]
        
        for window_attr in child_windows:
            if hasattr(self, window_attr):
                window = getattr(self, window_attr)
                if window:
                    try:
                        window.destroy()
                        setattr(self, window_attr, None)
                    except Exception as e:
                        print(f"关闭{window_attr}时发生错误: {e}")
    

    def _show_training_completed_dialog(self):
        """显示训练完成对话框"""
        try:
            # 创建训练完成弹窗
            completion_window = tk.Toplevel(self.root)
            completion_window.title("训练完成")
            completion_window.geometry("550x350")
            completion_window.configure(bg='white')
            completion_window.resizable(False, False)
            completion_window.transient(self.root)
            completion_window.grab_set()
            
            # 居中显示
            self.center_dialog_relative_to_main(completion_window, 550, 350)
            
            # 标题
            tk.Label(completion_window, text="AI训练完成", 
                    font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                    bg='white', fg='#28a745').pack(pady=40)
            
            # 完成信息
            tk.Label(completion_window, text="所有料斗的AI学习已完成", 
                    font=tkFont.Font(family="微软雅黑", size=14),
                    bg='white', fg='#333333').pack(pady=10)
            
            tk.Label(completion_window, text="现在可以开始生产了", 
                    font=tkFont.Font(family="微软雅黑", size=12),
                    bg='white', fg='#666666').pack(pady=5)
            
            # 按钮区域
            button_frame = tk.Frame(completion_window, bg='white')
            button_frame.pack(pady=30)
            
            def on_start_production():
                """开始生产按钮点击事件"""
                print("[信息] 用户选择开始生产")
                completion_window.destroy()
                # 这里可以添加跳转到生产界面的逻辑
                try:
                    # 获取当前的生产参数
                    material_name = self.material_var.get()
                    target_weight = float(self.weight_var.get()) if self.weight_var.get() else 0
                    package_quantity = int(self.quantity_var.get()) if self.quantity_var.get() else 0
                    
                    # 准备生产参数
                    production_params = {
                        'material_name': material_name,
                        'target_weight': target_weight,
                        'package_quantity': package_quantity
                    }
                    
                    # 隐藏AI模式界面
                    self.root.withdraw()
                    
                    # 导入并创建生产界面
                    from production_interface import create_production_interface
                    production_interface = create_production_interface(self.root, self, production_params)
                    
                    print(f"[成功] 已进入生产模式，参数: {production_params}")
                    
                except Exception as e:
                    # 如果出错，重新显示AI模式界面
                    self.root.deiconify()
                    messagebox.showerror("启动生产失败", f"无法启动生产界面：{str(e)}")
            
            def on_return_to_ai():
                """返回AI模式按钮点击事件"""
                print("[信息] 用户选择返回AI模式")
                completion_window.destroy()
            
            # 开始生产按钮
            start_btn = tk.Button(button_frame, text="开始生产", 
                                 font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                 bg='#28a745', fg='white',
                                 relief='flat', bd=0,
                                 padx=30, pady=15,
                                 command=on_start_production)
            start_btn.pack(side=tk.LEFT, padx=(0, 20))
            
            # 返回按钮
            return_btn = tk.Button(button_frame, text="返回AI模式", 
                                  font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                  bg='#6c757d', fg='white',
                                  relief='flat', bd=0,
                                  padx=30, pady=15,
                                  command=on_return_to_ai)
            return_btn.pack(side=tk.LEFT, padx=(20, 0))
            
            print("[信息] 显示训练完成对话框")
            
        except Exception as e:
            error_msg = f"显示训练完成对话框异常: {str(e)}"
            print(f"[错误] {error_msg}")
            messagebox.showerror("显示错误", error_msg)
