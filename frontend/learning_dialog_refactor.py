#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的多斗学习界面 - 根本解决卡死问题
采用单线程事件驱动架构，彻底解决多线程竞争和UI卡死问题
"""

import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkFont
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum



class LearningStatus(Enum):
    NOT_STARTED = "not_started"
    LEARNING = "learning" 
    COMPLETED = "completed"
    FAILED = "failed"

class LearningStage(Enum):
    COARSE_TIME = "coarse_time"
    FLIGHT_MATERIAL = "flight_material"
    FINE_TIME = "fine_time"
    ADAPTIVE_LEARNING = "adaptive_learning"

@dataclass
class BucketState:
    """料斗状态数据类"""
    status: LearningStatus = LearningStatus.NOT_STARTED
    current_stage: LearningStage = LearningStage.COARSE_TIME
    is_successful: bool = False
    completion_message: str = ""
    last_update: float = 0
    
    def get_display_text(self) -> str:
        if self.status == LearningStatus.NOT_STARTED:
            return "未开始"
        elif self.status == LearningStatus.LEARNING:
            return f"学习中({self.current_stage.value})"
        elif self.status == LearningStatus.COMPLETED:
            return "学习完成" if self.is_successful else "学习失败"
        elif self.status == LearningStatus.FAILED:
            return "学习失败"
        return "未知状态"
    
    def get_display_color(self) -> str:
        if self.status == LearningStatus.NOT_STARTED:
            return "#888888"
        elif self.status == LearningStatus.LEARNING:
            return "#4a90e2"
        elif self.status == LearningStatus.COMPLETED:
            return "#00aa00" if self.is_successful else "#ff0000"
        elif self.status == LearningStatus.FAILED:
            return "#ff0000"
        return "#888888"

class SimplifiedLearningDialog:
    """
    简化的多斗学习对话框
    
    核心设计原则：
    1. 单一定时器驱动所有更新
    2. 无锁设计，使用状态标志
    3. 批量处理状态更新
    4. 最小化跨线程通信
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.is_active = False
        
        # UI组件引用
        self.bucket_labels = {}  # {bucket_id: label}
        self.stats_label = None
        self.timer_label = None
        self.confirm_btn = None
        
        # 状态管理（内存中，线程安全）
        self.bucket_states = {i: BucketState() for i in range(1, 7)}
        self.learning_start_time = 0
        self.all_completed = False
        
        # 单一定时器
        self.timer_id = None
        self.update_interval = 200  # 200ms更新一次
        
        # 外部控制器回调缓冲
        self.pending_updates = []
        self.update_in_progress = False
        
    def show(self):
        """显示学习对话框"""
        if self.is_active:
            return
            
        try:
            self._create_window()
            self._create_widgets()
            self._center_window()
            self._start_unified_timer()
            
            self.is_active = True
            self.learning_start_time = time.time()
            
            print("[简化学习] 对话框已显示")
            
        except Exception as e:
            print(f"[错误] 显示学习对话框异常: {e}")
            self._cleanup()
    
    def _create_window(self):
        """创建窗口"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("多斗学习状态")
        self.window.geometry("800x600")
        self.window.configure(bg='white')
        self.window.resizable(False, False)
        self.window.transient(self.parent)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """创建UI组件"""
        # 标题
        title_label = tk.Label(self.window, text="多斗学习状态", 
                              font=tkFont.Font(family="微软雅黑", size=16, weight="bold"),
                              bg='white', fg='#333333')
        title_label.pack(pady=20)
        
        # 计时器
        self.timer_label = tk.Label(self.window, text="00:00:00", 
                                   font=tkFont.Font(family="Arial", size=20, weight="bold"),
                                   bg='white', fg='#007bff')
        self.timer_label.pack(pady=(0, 10))
        
        # 料斗状态网格
        grid_frame = tk.Frame(self.window, bg='white')
        grid_frame.pack(expand=True, fill='both', padx=20, pady=0)
        
        for i in range(6):
            bucket_id = i + 1
            row = i // 3
            col = i % 3
            
            bucket_frame = tk.Frame(grid_frame, bg='white', relief='solid', bd=1)
            bucket_frame.grid(row=row, column=col, padx=20, pady=20, sticky='nsew')
            
            grid_frame.grid_rowconfigure(row, weight=1)
            grid_frame.grid_columnconfigure(col, weight=1)
            
            # 料斗标题
            tk.Label(bucket_frame, text=f"料斗{bucket_id}", 
                    font=tkFont.Font(family="微软雅黑", size=12, weight="bold"),
                    bg='white', fg='#333333').pack(pady=(10, 5))
            
            # 状态标签
            status_label = tk.Label(bucket_frame, text="未开始",
                                   font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                   bg='white', fg="#888888")
            status_label.pack(pady=(5, 10))
            
            self.bucket_labels[bucket_id] = status_label
        
        # 统计信息
        self.stats_label = tk.Label(self.window, text="学习状态:正在初始化...", 
                                   font=tkFont.Font(family="微软雅黑", size=10),
                                   bg='white', fg='#666666')
        self.stats_label.pack(pady=10)
        
        # 按钮区域
        button_frame = tk.Frame(self.window, bg='white')
        button_frame.pack(pady=20)
        
        # 确认按钮
        self.confirm_btn = tk.Button(button_frame, text="确认", 
                                    font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                                    bg='#cccccc', fg='#666666',
                                    relief='flat', bd=0, padx=30, pady=15,
                                    command=self._on_confirm,
                                    state='disabled')
        self.confirm_btn.pack(side=tk.LEFT, padx=(0, 30))
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame, text="取消", 
                              font=tkFont.Font(family="微软雅黑", size=14, weight="bold"),
                              bg='#dc3545', fg='white',
                              relief='flat', bd=0, padx=30, pady=15,
                              command=self._on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=(30, 0))
    
    def _center_window(self):
        """居中显示窗口"""
        try:
            # 添加空值检查
            if not self.window:
                print("[错误] 窗口对象为空，无法居中显示")
                return
                
            # 确保窗口存在且未被销毁
            if not self.window.winfo_exists():
                print("[错误] 窗口已被销毁，无法居中显示")
                return
                
            self.window.update_idletasks()
            
            # 获取父窗口信息
            if not self.parent or not self.parent.winfo_exists():
                print("[错误] 父窗口不存在，使用屏幕居中")
                # 使用屏幕居中作为备选方案
                screen_width = self.window.winfo_screenwidth()
                screen_height = self.window.winfo_screenheight()
                x = (screen_width - 800) // 2
                y = (screen_height - 600) // 2
                self.window.geometry(f"800x600+{x}+{y}")
                return
                
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            window_width = 800
            window_height = 600
            
            x = parent_x + (parent_width - window_width) // 2
            y = parent_y + (parent_height - window_height) // 2
            
            # 确保窗口不会超出屏幕边界
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            
            if x + window_width > screen_width:
                x = screen_width - window_width - 20
            if x < 20:
                x = 20
            if y + window_height > screen_height:
                y = screen_height - window_height - 20
            if y < 20:
                y = 20
                
            self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
        except tk.TclError as e:
            print(f"[错误] 窗口操作失败: {e}")
        except Exception as e:
            print(f"[错误] 居中窗口异常: {e}")
    
    def _start_unified_timer(self):
        """启动统一定时器"""
        def timer_update():
            if not self.is_active:
                return
                
            try:
                # 避免重入
                if self.update_in_progress:
                    self._schedule_next_update()
                    return
                
                self.update_in_progress = True
                
                # 批量处理所有更新
                self._process_pending_updates()
                self._update_timer_display()
                self._update_statistics()
                self._update_confirm_button()
                
                # 调度下次更新
                self._schedule_next_update()
                
            except Exception as e:
                print(f"[错误] 定时器更新异常: {e}")
            finally:
                self.update_in_progress = False
        
        # 启动定时器
        self.timer_id = self.parent.after(self.update_interval, timer_update)
    
    def _schedule_next_update(self):
        """调度下次更新"""
        if self.is_active:
            self.timer_id = self.parent.after(self.update_interval, self._start_unified_timer)
    
    def _process_pending_updates(self):
        """批量处理待处理的状态更新"""
        if not self.pending_updates:
            return
        
        # 按料斗分组，只保留最新状态
        latest_updates = {}
        current_time = time.time()
        
        for update in self.pending_updates:
            bucket_id = update.get('bucket_id')
            if bucket_id and (bucket_id not in latest_updates or 
                             update.get('timestamp', 0) > latest_updates[bucket_id].get('timestamp', 0)):
                latest_updates[bucket_id] = update
        
        # 清空待处理队列
        self.pending_updates.clear()
        
        # 应用更新到状态
        for bucket_id, update in latest_updates.items():
            if 1 <= bucket_id <= 6:
                state = self.bucket_states[bucket_id]
                
                # 更新状态
                if 'status' in update:
                    state.status = update['status']
                if 'stage' in update:
                    state.current_stage = update['stage']
                if 'success' in update:
                    state.is_successful = update['success']
                if 'message' in update:
                    state.completion_message = update['message']
                
                state.last_update = current_time
                
                # 更新UI
                self._update_bucket_display(bucket_id)
    
    def _update_bucket_display(self, bucket_id: int):
        """更新单个料斗显示"""
        try:
            if bucket_id not in self.bucket_labels:
                return
                
            state = self.bucket_states[bucket_id]
            label = self.bucket_labels[bucket_id]
            
            if label and label.winfo_exists():
                label.config(
                    text=state.get_display_text(),
                    fg=state.get_display_color()
                )
        except Exception as e:
            print(f"[错误] 更新料斗{bucket_id}显示异常: {e}")
    
    def _update_timer_display(self):
        """更新计时器显示"""
        try:
            if not self.timer_label or not self.timer_label.winfo_exists():
                return
                
            if self.learning_start_time > 0:
                elapsed = time.time() - self.learning_start_time
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                self.timer_label.config(text=time_str)
        except Exception as e:
            print(f"[错误] 更新计时器显示异常: {e}")
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            if not self.stats_label or not self.stats_label.winfo_exists():
                return
            
            # 统计各状态数量
            success_count = sum(1 for s in self.bucket_states.values() 
                              if s.status == LearningStatus.COMPLETED and s.is_successful)
            failed_count = sum(1 for s in self.bucket_states.values() 
                             if s.status == LearningStatus.FAILED or 
                             (s.status == LearningStatus.COMPLETED and not s.is_successful))
            learning_count = sum(1 for s in self.bucket_states.values() 
                               if s.status == LearningStatus.LEARNING)
            not_started_count = sum(1 for s in self.bucket_states.values() 
                                  if s.status == LearningStatus.NOT_STARTED)
            
            stats_text = (f"学习状态：未开始 {not_started_count}个，"
                         f"学习中 {learning_count}个，"
                         f"成功 {success_count}个，"
                         f"失败 {failed_count}个")
            
            self.stats_label.config(text=stats_text)
            
            # 检查是否全部完成
            completed_count = success_count + failed_count
            self.all_completed = (completed_count >= 6 and learning_count == 0 and not_started_count == 0)
            
        except Exception as e:
            print(f"[错误] 更新统计信息异常: {e}")
    
    def _update_confirm_button(self):
        """更新确认按钮状态"""
        try:
            if not self.confirm_btn or not self.confirm_btn.winfo_exists():
                return
                
            if self.all_completed:
                self.confirm_btn.config(
                    state='normal',
                    bg='#28a745',
                    fg='white',
                    text='确认 全部完成'
                )
            else:
                self.confirm_btn.config(
                    state='disabled',
                    bg='#cccccc',
                    fg='#666666',
                    text='确认'
                )
        except Exception as e:
            print(f"[错误] 更新确认按钮异常: {e}")
    
    # ===== 外部接口方法 =====
    
    def update_bucket_state(self, bucket_id: int, status: LearningStatus, 
                           stage: Optional[LearningStage] = None, success: bool = False, 
                           message: str = ""):
        """
        外部调用接口：更新料斗状态
        
        这个方法是线程安全的，可以从任意线程调用
        """
        update = {
            'bucket_id': bucket_id,
            'status': status,
            'success': success,
            'message': message,
            'timestamp': time.time()
        }
        
        if stage:
            update['stage'] = stage
        
        # 添加到待处理队列，等待定时器处理
        self.pending_updates.append(update)
    
    def start_bucket_learning(self, bucket_id: int, stage: LearningStage):
        """开始料斗学习"""
        self.update_bucket_state(bucket_id, LearningStatus.LEARNING, stage)
    
    def complete_bucket_learning(self, bucket_id: int, success: bool, message: str):
        """完成料斗学习"""
        status = LearningStatus.COMPLETED if success else LearningStatus.FAILED
        self.update_bucket_state(bucket_id, status, success=success, message=message)
    
    def reset_all_states(self):
        """重置所有状态"""
        for bucket_id in range(1, 7):
            self.bucket_states[bucket_id] = BucketState()
            self.update_bucket_state(bucket_id, LearningStatus.NOT_STARTED)
    
    # ===== 事件处理 =====
    
    def _on_confirm(self):
        """确认按钮点击"""
        if self.all_completed:
            self._cleanup()
            print("[简化学习] 用户确认学习完成")
    
    def _on_cancel(self):
        """取消按钮点击"""
        result = messagebox.askyesno("确认取消", "确定要取消学习过程吗？")
        if result:
            self._cleanup()
            print("[简化学习] 用户取消学习过程")
    
    def _on_close(self):
        """窗口关闭事件"""
        self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            self.is_active = False
            
            # 停止定时器
            if self.timer_id:
                self.parent.after_cancel(self.timer_id)
                self.timer_id = None
            
            # 清理状态
            self.pending_updates.clear()
            self.update_in_progress = False
            
            # 关闭窗口
            if self.window:
                self.window.destroy()
                self.window = None
            
            print("[简化学习] 资源已清理")
            
        except Exception as e:
            print(f"[错误] 清理资源异常: {e}")

# ===== 使用示例 =====

class TestApplication:
    """测试应用程序"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("测试应用")
        self.root.geometry("400x300")
        
        self.learning_dialog = None
        
        # 创建测试按钮
        tk.Button(self.root, text="显示学习对话框", 
                 command=self.show_learning_dialog).pack(pady=20)
        
        tk.Button(self.root, text="模拟学习开始", 
                 command=self.simulate_learning_start).pack(pady=10)
        
        tk.Button(self.root, text="模拟学习完成", 
                 command=self.simulate_learning_complete).pack(pady=10)
    
    def show_learning_dialog(self):
        """显示学习对话框"""
        if not self.learning_dialog or not self.learning_dialog.is_active:
            self.learning_dialog = SimplifiedLearningDialog(self.root)
            self.learning_dialog.show()
    
    def simulate_learning_start(self):
        """模拟开始学习"""
        if self.learning_dialog and self.learning_dialog.is_active:
            for bucket_id in range(1, 7):
                self.learning_dialog.start_bucket_learning(bucket_id, LearningStage.COARSE_TIME)
    
    def simulate_learning_complete(self):
        """模拟学习完成"""
        if self.learning_dialog and self.learning_dialog.is_active:
            for bucket_id in range(1, 7):
                success = bucket_id % 2 == 1  # 奇数成功，偶数失败
                message = "学习成功" if success else "学习失败"
                self.learning_dialog.complete_bucket_learning(bucket_id, success, message)
    
    def run(self):
        """运行应用"""
        self.root.mainloop()

if __name__ == "__main__":
    app = TestApplication()
    app.run()