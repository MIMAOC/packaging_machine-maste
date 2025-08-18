#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动界面模块
实现六头线性调节秤的手动控制界面

功能包含：
- 6个料斗的禁用/启用控制（状态保持）
- 6个料斗的清料控制（状态保持）
- 6个料斗的放料控制（脉冲控制）
- 总放料/总清料控制（脉冲控制）

作者：AI助手
创建日期：2025-08-06
"""

import tkinter as tk
from tkinter import messagebox
import tkinter.font as font
import time
from typing import Optional, Dict, Any

# 导入PLC地址映射
try:
    from traditional_plc_addresses import (
        get_traditional_control_address,
        get_traditional_global_address,
        get_traditional_disable_address
    )
except ImportError as e:
    print(f"导入PLC地址映射失败: {e}")


class ManualModeInterface:
    """手动界面类"""
    
    def __init__(self, modbus_client, parent_interface):
        """
        初始化手动界面
        
        Args:
            modbus_client: PLC通信客户端
            parent_interface: 主界面引用
        """
        self.modbus_client = modbus_client
        self.parent = parent_interface
        self.root = parent_interface.get_main_root()
        self.main_content_frame = parent_interface.get_main_content_frame()
        
        # 界面元素引用
        self.disable_buttons = {}       # 禁用按钮 {bucket_id: button}
        self.clean_buttons = {}         # 清料按钮 {bucket_id: button}
        self.discharge_buttons = {}     # 放料按钮 {bucket_id: button}
        self.global_buttons = {}        # 全局按钮
        
        # 料斗状态
        self.bucket_disabled = {}       # 禁用状态 {bucket_id: True/False}
        self.bucket_cleaning = {}       # 清料状态 {bucket_id: True/False}
        self.global_cleaning = False    # 全局清料状态
        
        # 初始化状态
        for i in range(1, 7):
            self.bucket_disabled[i] = False
            self.bucket_cleaning[i] = False
        
        # 设置字体（按1.43倍缩放）
        self.setup_fonts()
        
        print("手动界面模块初始化完成")
    
    def setup_fonts(self):
        """设置字体（按1024x600→1400x900比例换算）"""
        # 标题字体：增大到适应全屏
        self.title_font = font.Font(family="Microsoft YaHei", size=56, weight="bold")
        
        # 行标签字体：增大
        self.row_label_font = font.Font(family="Microsoft YaHei", size=48, weight="bold")
        
        # 料斗按钮字体：增大
        self.bucket_button_font = font.Font(family="Arial", size=54, weight="bold")
        
        # 全局按钮字体：增大
        self.global_button_font = font.Font(family="Microsoft YaHei", size=36, weight="bold")
        
        # 主页按钮字体：增大
        self.home_button_font = font.Font(family="Microsoft YaHei", size=28, weight="bold")
    
    def show_interface(self):
        """显示手动界面"""
        try:
            print("正在显示手动界面...")
            self.create_manual_interface()
            self.load_initial_states()
            self.start_data_refresh()
            print("手动界面显示完成")
        except Exception as e:
            print(f"显示手动界面失败: {e}")
            messagebox.showerror("错误", f"手动界面显示失败: {e}")
    
    def create_manual_interface(self):
        """创建手动界面布局"""
        # 配置主内容框架的网格权重
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=0, minsize=140)  # 顶部标题栏（增大更多）
        self.main_content_frame.grid_rowconfigure(1, weight=1, minsize=550)  # 主要控制区域（相应减小）
        self.main_content_frame.grid_rowconfigure(2, weight=0, minsize=110)  # 底部全局控制
        
        # 创建界面各部分
        self.create_header_area()
        self.create_control_area()
        self.create_global_control_area()
    
    def create_header_area(self):
        """创建顶部标题栏"""
        header_frame = tk.Frame(self.main_content_frame, bg='#ffffff', height=120)
        header_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(40, 20))
        header_frame.grid_propagate(False)  # 防止框架缩小
        
        # 使用place让标题在整个frame中完全居中（不考虑其他元素）
        title_label = tk.Label(header_frame, text="手动画面",
                              font=self.title_font, bg='#ffffff', fg='#333333')
        title_label.place(relx=0.5, rely=0.5, anchor='center')  # 在整个frame中心
        
        # 主页按钮固定在右侧（独立布局，不影响标题居中）
        home_button = tk.Button(header_frame, text="主页",
                               font=self.home_button_font,
                               bg='#e0e0e0', fg='#333333',
                               relief='solid', bd=2, padx=35, pady=12,
                               command=self.go_back_to_menu)
        home_button.place(relx=1.0, rely=0.5, anchor='e', x=-30)  # 距离右边界30px
    
    def create_control_area(self):
        """创建主要控制区域（3行6列按钮矩阵）"""
        control_frame = tk.Frame(self.main_content_frame, bg='#ffffff')
        control_frame.grid(row=1, column=0, sticky='nsew', padx=40, pady=(10, 15))  # 与其他区域保持一致的边距
        
        # 配置控制区域网格
        control_frame.grid_columnconfigure(0, weight=0, minsize=180)  # 行标签列（稍微小一点）
        control_frame.grid_columnconfigure(1, weight=1)              # 按钮列
        
        for i in range(3):  # 3行
            control_frame.grid_rowconfigure(i, weight=1, minsize=165)  # 减小行高
        
        # 创建3行控制
        self.create_disable_row(control_frame, 0)    # 第0行：禁用
        self.create_clean_row(control_frame, 1)      # 第1行：清料
        self.create_discharge_row(control_frame, 2)  # 第2行：放料
    
    def create_disable_row(self, parent, row):
        """创建禁用控制行"""
        # 行标签
        label_frame = tk.Frame(parent, bg='#1e90ff', width=180, height=125)
        label_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 25), pady=10)
        label_frame.grid_propagate(False)
        
        label = tk.Label(label_frame, text="禁用",
                        font=self.row_label_font, bg='#1e90ff', fg='white')
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        # 按钮组
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.grid(row=row, column=1, sticky='nsew', pady=10)
        
        # 配置按钮组网格
        for i in range(6):
            buttons_frame.grid_columnconfigure(i, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)
        
        # 创建6个禁用按钮（稍微小一点）
        for bucket_id in range(1, 7):
            btn = tk.Button(buttons_frame, text=str(bucket_id),
                           font=self.bucket_button_font,
                           bg='#1e90ff', fg='white',
                           relief='solid', bd=3, width=5, height=2,  # 减小尺寸
                           command=lambda bid=bucket_id: self.toggle_disable(bid))
            btn.grid(row=0, column=bucket_id-1, sticky='nsew', padx=15, pady=0)
            self.disable_buttons[bucket_id] = btn
    
    def create_clean_row(self, parent, row):
        """创建清料控制行"""
        # 行标签
        label_frame = tk.Frame(parent, bg='#1e90ff', width=180, height=125)
        label_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 25), pady=10)
        label_frame.grid_propagate(False)
        
        label = tk.Label(label_frame, text="清料",
                        font=self.row_label_font, bg='#1e90ff', fg='white')
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        # 按钮组
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.grid(row=row, column=1, sticky='nsew', pady=10)
        
        # 配置按钮组网格
        for i in range(6):
            buttons_frame.grid_columnconfigure(i, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)
        
        # 创建6个清料按钮（稍微小一点）
        for bucket_id in range(1, 7):
            btn = tk.Button(buttons_frame, text=str(bucket_id),
                           font=self.bucket_button_font,
                           bg='#1e90ff', fg='white',
                           relief='solid', bd=3, width=5, height=2,  # 减小尺寸
                           command=lambda bid=bucket_id: self.toggle_clean(bid))
            btn.grid(row=0, column=bucket_id-1, sticky='nsew', padx=15, pady=0)
            self.clean_buttons[bucket_id] = btn
    
    def create_discharge_row(self, parent, row):
        """创建放料控制行"""
        # 行标签
        label_frame = tk.Frame(parent, bg='#1e90ff', width=180, height=125)
        label_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 25), pady=10)
        label_frame.grid_propagate(False)
        
        label = tk.Label(label_frame, text="放料",
                        font=self.row_label_font, bg='#1e90ff', fg='white')
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        # 按钮组
        buttons_frame = tk.Frame(parent, bg='#ffffff')
        buttons_frame.grid(row=row, column=1, sticky='nsew', pady=10)
        
        # 配置按钮组网格
        for i in range(6):
            buttons_frame.grid_columnconfigure(i, weight=1)
        buttons_frame.grid_rowconfigure(0, weight=1)
        
        # 创建6个放料按钮（稍微小一点）
        for bucket_id in range(1, 7):
            btn = tk.Button(buttons_frame, text=str(bucket_id),
                           font=self.bucket_button_font,
                           bg='#1e90ff', fg='white',
                           relief='solid', bd=3, width=5, height=2,  # 减小尺寸
                           command=lambda bid=bucket_id: self.discharge_bucket(bid))
            btn.grid(row=0, column=bucket_id-1, sticky='nsew', padx=15, pady=0)
            self.discharge_buttons[bucket_id] = btn
    
    def create_global_control_area(self):
        """创建底部全局控制区域"""
        global_frame = tk.Frame(self.main_content_frame, bg='#ffffff', height=110)
        global_frame.grid(row=2, column=0, sticky='ew', padx=40, pady=(10, 30))  # 保持一致的边距
        global_frame.grid_propagate(False)
        
        # 配置网格让按钮居中
        global_frame.grid_columnconfigure(0, weight=1)
        global_frame.grid_columnconfigure(1, weight=0)
        global_frame.grid_columnconfigure(2, weight=0)
        global_frame.grid_columnconfigure(3, weight=1)
        global_frame.grid_rowconfigure(0, weight=1)
        
        # 总放料按钮（稍微小一点）
        global_discharge_btn = tk.Button(global_frame, text="总放料",
                                        font=self.global_button_font,
                                        bg='#1e90ff', fg='white',
                                        relief='solid', bd=2,
                                        width=10, height=2,  # 稍微减小
                                        command=self.global_discharge)
        global_discharge_btn.grid(row=0, column=1, sticky='', padx=25)
        self.global_buttons['discharge'] = global_discharge_btn
        
        # 总清料按钮（稍微小一点）
        global_clean_btn = tk.Button(global_frame, text="总清料",
                                    font=self.global_button_font,
                                    bg='#1e90ff', fg='white',
                                    relief='solid', bd=2,
                                    width=10, height=2,  # 稍微减小
                                    command=self.global_clean)
        global_clean_btn.grid(row=0, column=2, sticky='', padx=25)
        self.global_buttons['clean'] = global_clean_btn
    
    # ==================== 控制逻辑方法 ====================
    
    def toggle_disable(self, bucket_id: int):
        """切换料斗禁用状态（状态保持）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 调用父界面的共享方法
            success = self.parent.shared_toggle_bucket_disable(bucket_id)
            
            if success:
                # 切换本地状态
                self.bucket_disabled[bucket_id] = not self.bucket_disabled[bucket_id]
                self.update_disable_button_display(bucket_id)
                
                state_text = "已禁用" if self.bucket_disabled[bucket_id] else "已启用"
                print(f"料斗{bucket_id}{state_text}")
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}禁用状态切换失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}禁用操作异常: {e}")
    
    def toggle_clean(self, bucket_id: int):
        """切换料斗清料状态（状态保持）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 调用父界面的共享方法
            success = self.parent.shared_toggle_bucket_clean(bucket_id)
            
            if success:
                # 切换本地状态
                self.bucket_cleaning[bucket_id] = not self.bucket_cleaning[bucket_id]
                self.update_clean_button_display(bucket_id)
                
                state_text = "开始清料" if self.bucket_cleaning[bucket_id] else "停止清料"
                print(f"料斗{bucket_id}{state_text}")
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}清料状态切换失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}清料操作异常: {e}")
    
    def discharge_bucket(self, bucket_id: int):
        """料斗放料操作（脉冲控制）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 调用父界面的共享脉冲控制方法
            success = self.parent.shared_send_bucket_pulse_command(bucket_id, "Discharge")
            
            if success:
                # 提供视觉反馈
                self.provide_discharge_feedback(bucket_id)
                print(f"料斗{bucket_id}放料操作完成")
            else:
                messagebox.showerror("错误", f"料斗{bucket_id}放料操作失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"料斗{bucket_id}放料操作异常: {e}")
    
    def global_discharge(self):
        """总放料操作（脉冲控制）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 调用父界面的共享全局脉冲控制方法
            success = self.parent.shared_send_global_pulse_command("GlobalDischarge")
            
            if success:
                # 提供视觉反馈
                self.provide_global_feedback('discharge')
                print("总放料操作完成")
            else:
                messagebox.showerror("错误", "总放料操作失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"总放料操作异常: {e}")
    
    def global_clean(self):
        """总清料操作（状态保持控制）"""
        if not self.modbus_client or not self.modbus_client.is_connected:
            messagebox.showerror("错误", "PLC未连接")
            return
        
        try:
            # 获取总清料地址
            global_clean_addr = get_traditional_global_address('GlobalClean')
            
            # 切换全局清料状态
            new_state = not self.global_cleaning
            success = self.modbus_client.write_coil(global_clean_addr, new_state)
            
            if success:
                # 更新本地状态
                self.global_cleaning = new_state
                self.update_global_clean_button_display()
                
                state_text = "开始总清料" if new_state else "停止总清料"
                print(f"{state_text}")
            else:
                messagebox.showerror("错误", "总清料状态切换失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"总清料操作异常: {e}")
    
    # ==================== 界面更新方法 ====================
    
    def update_disable_button_display(self, bucket_id: int):
        """更新禁用按钮显示"""
        if bucket_id in self.disable_buttons:
            btn = self.disable_buttons[bucket_id]
            if self.bucket_disabled[bucket_id]:
                # 禁用状态：红色背景
                btn.configure(bg='#ff4444', fg='white')
            else:
                # 正常状态：蓝色背景
                btn.configure(bg='#1e90ff', fg='white')
    
    def update_clean_button_display(self, bucket_id: int):
        """更新清料按钮显示"""
        if bucket_id in self.clean_buttons:
            btn = self.clean_buttons[bucket_id]
            if self.bucket_cleaning[bucket_id]:
                # 清料中状态：红色背景
                btn.configure(bg='#ff4444', fg='white')
            else:
                # 正常状态：蓝色背景
                btn.configure(bg='#1e90ff', fg='white')
    
    def provide_discharge_feedback(self, bucket_id: int):
        """提供放料操作的视觉反馈"""
        if bucket_id in self.discharge_buttons:
            btn = self.discharge_buttons[bucket_id]
            original_bg = btn.cget('bg')
            
            # 短暂变红色表示操作执行
            btn.configure(bg='#ff6b6b')
            self.root.after(500, lambda: btn.configure(bg=original_bg))
    
    def provide_global_feedback(self, action: str):
        """提供全局操作的视觉反馈"""
        if action in self.global_buttons:
            btn = self.global_buttons[action]
            original_bg = btn.cget('bg')
            
            # 短暂变红色表示操作执行
            btn.configure(bg='#ff6b6b')
            duration = 1500 if action == 'discharge' else 500  # 放料反馈时间更长
            self.root.after(duration, lambda: btn.configure(bg=original_bg))
    
    # ==================== 数据刷新方法 ====================
    
    def start_data_refresh(self):
        """启动数据刷新"""
        if self.modbus_client and self.modbus_client.is_connected:
            # 使用父界面的共享数据刷新机制
            self.parent.shared_start_data_refresh(self.update_manual_data)
            print("手动界面数据刷新已启动")
    
    def stop_data_refresh(self):
        """停止数据刷新"""
        self.parent.shared_stop_data_refresh()
        print("手动界面数据刷新已停止")
    
    def update_manual_data(self):
        """更新手动界面数据（每100ms调用）"""
        try:
            # 读取禁用状态
            self.update_disable_states()
            # 读取清料状态
            self.update_clean_states()
            # 读取全局清料状态
            self.update_global_clean_state()
            
        except Exception as e:
            print(f"手动界面数据更新错误: {e}")
    
    def update_disable_states(self):
        """更新所有料斗的禁用状态"""
        try:
            for bucket_id in range(1, 7):
                # 读取PLC中的禁用状态
                disable_addr = get_traditional_disable_address(bucket_id)
                state_data = self.modbus_client.read_coils(disable_addr, 1)
                
                if state_data and len(state_data) > 0:
                    plc_disabled = state_data[0]
                    
                    # 如果状态有变化，更新本地状态和显示
                    if self.bucket_disabled[bucket_id] != plc_disabled:
                        self.bucket_disabled[bucket_id] = plc_disabled
                        self.update_disable_button_display(bucket_id)
                        
        except Exception as e:
            print(f"更新禁用状态失败: {e}")
    
    def update_clean_states(self):
        """更新所有料斗的清料状态"""
        try:
            for bucket_id in range(1, 7):
                # 读取PLC中的清料状态
                clean_addr = get_traditional_control_address(bucket_id, 'Clean')
                state_data = self.modbus_client.read_coils(clean_addr, 1)
                
                if state_data and len(state_data) > 0:
                    plc_cleaning = state_data[0]
                    
                    # 如果状态有变化，更新本地状态和显示
                    if self.bucket_cleaning[bucket_id] != plc_cleaning:
                        self.bucket_cleaning[bucket_id] = plc_cleaning
                        self.update_clean_button_display(bucket_id)
                        
        except Exception as e:
            print(f"更新清料状态失败: {e}")
    
    def load_initial_states(self):
        """加载初始状态"""
        try:
            print("正在加载初始状态...")
            
            # 立即更新一次状态显示
            self.update_disable_states()
            self.update_clean_states()
            self.update_global_clean_state()

            # 更新所有按钮显示
            for bucket_id in range(1, 7):
                self.update_disable_button_display(bucket_id)
                self.update_clean_button_display(bucket_id)
            # 更新全局清料按钮显示
                self.update_global_clean_button_display()
            
            print("初始状态加载完成")
            
        except Exception as e:
            print(f"加载初始状态失败: {e}")
    
    # ==================== 界面管理方法 ====================
    
    def go_back_to_menu(self):
        """返回主菜单"""
        try:
            print("正在返回主菜单...")
            self.cleanup()
            self.parent.show_menu_interface()
        except Exception as e:
            print(f"返回主菜单失败: {e}")
            messagebox.showerror("错误", f"返回主菜单失败: {e}")

    def update_global_clean_button_display(self):
        """更新总清料按钮显示"""
        if 'clean' in self.global_buttons:
            btn = self.global_buttons['clean']
            if self.global_cleaning:
                # 清料中状态：红色背景
                btn.configure(bg='#ff4444', fg='white')
            else:
                # 正常状态：蓝色背景
                btn.configure(bg='#1e90ff', fg='white')

    def update_global_clean_state(self):
        """更新全局清料状态"""
        try:
            # 读取PLC中的全局清料状态
            global_clean_addr = get_traditional_global_address('GlobalClean')
            state_data = self.modbus_client.read_coils(global_clean_addr, 1)
            
            if state_data and len(state_data) > 0:
                plc_global_cleaning = state_data[0]
                
                # 如果状态有变化，更新本地状态和显示
                if self.global_cleaning != plc_global_cleaning:
                    self.global_cleaning = plc_global_cleaning
                    self.update_global_clean_button_display()
                    
        except Exception as e:
            print(f"更新全局清料状态失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            print("正在清理手动界面资源...")
            
            # 停止数据刷新
            self.stop_data_refresh()
            
            # 清空按钮引用
            self.disable_buttons.clear()
            self.clean_buttons.clear()
            self.discharge_buttons.clear()
            self.global_buttons.clear()
            
            print("手动界面资源清理完成")
            
        except Exception as e:
            print(f"清理手动界面资源失败: {e}")


# 测试代码
if __name__ == "__main__":
    print("手动界面模块已加载")
    print("使用方法：")
    print("from manual_mode_interface import ManualModeInterface")
    print("manual_interface = ManualModeInterface(modbus_client, parent_interface)")
    print("manual_interface.show_interface()")