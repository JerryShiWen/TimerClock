import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
from datetime import datetime, timedelta
import json
import os
import pytz
import calendar

class CountdownTimer:
    """倒计时器对象"""
    def __init__(self, name, minutes, seconds):
        self.name = name
        self.total_seconds = minutes * 60 + seconds
        self.end_time = datetime.now() + timedelta(seconds=self.total_seconds)
        self.running = True

    def remaining_time(self):
        return self.end_time - datetime.now()

    def to_dict(self):
        return {
            "type": "timer",
            "name": self.name,
            "total_seconds": self.total_seconds,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "running": self.running
        }

    @staticmethod
    def from_dict(data):
        timer = CountdownTimer(data["name"], 0, 0)
        timer.total_seconds = data["total_seconds"]
        timer.end_time = datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
        timer.running = data["running"]
        return timer

class Alarm:
    """闹钟对象"""
    def __init__(self, name, hour, minute, repeat="once"):
        self.name = name
        self.hour = hour
        self.minute = minute
        self.repeat = repeat  # "once", "daily", "weekend"
        now = datetime.now()
        self.alarm_time = datetime(now.year, now.month, now.day, hour, minute)
        
        # 调整闹钟时间
        if self.alarm_time < now:
            self._increment_alarm_time()
            
        self.active = True

    def _increment_alarm_time(self):
        """根据重复类型增加闹钟时间"""
        if self.repeat == "once":
            self.alarm_time += timedelta(days=1)
        elif self.repeat == "daily":
            self.alarm_time += timedelta(days=1)
        elif self.repeat == "weekend":
            while True:
                self.alarm_time += timedelta(days=1)
                # 5是周六，6是周日
                if self.alarm_time.weekday() in (5, 6):
                    break

    def check_and_update(self):
        """检查闹钟是否触发并更新下一次时间"""
        now = datetime.now()
        if self.active and now >= self.alarm_time:
            if self.repeat == "once":
                self.active = False
            else:
                self._increment_alarm_time()
            return True
        return False

    def to_dict(self):
        return {
            "type": "alarm",
            "name": self.name,
            "hour": self.hour,
            "minute": self.minute,
            "repeat": self.repeat,
            "alarm_time": self.alarm_time.strftime("%Y-%m-%d %H:%M:%S"),
            "active": self.active
        }

    @staticmethod
    def from_dict(data):
        alarm = Alarm(data["name"], data["hour"], data["minute"], data["repeat"])
        alarm.alarm_time = datetime.strptime(data["alarm_time"], "%Y-%m-%d %H:%M:%S")
        alarm.active = data["active"]
        return alarm

class Countdown:
    """倒计日对象"""
    def __init__(self, name, target_date):
        self.name = name
        self.target_date = target_date

    def to_dict(self):
        return {
            "type": "countdown",
            "name": self.name,
            "target_date": self.target_date.strftime("%Y-%m-%d")
        }

    @staticmethod
    def from_dict(data):
        target_date = datetime.strptime(data["target_date"], "%Y-%m-%d")
        return Countdown(data["name"], target_date)

class Stopwatch:
    """秒表对象"""
    def __init__(self, elapsed_time=0, running=False):
        self.elapsed_time = elapsed_time
        self.running = running
        self.start_time = time.time() if running else 0

    def to_dict(self):
        return {
            "type": "stopwatch",
            "elapsed_time": self.elapsed_time,
            "running": self.running,
            "start_time": self.start_time
        }

    @staticmethod
    def from_dict(data):
        stopwatch = Stopwatch(data["elapsed_time"], data["running"])
        stopwatch.start_time = data["start_time"]
        return stopwatch

class TodoItem:
    """待办事项对象"""
    def __init__(self, title, description="", start_time=None, end_time=None, completed=False):
        self.title = title
        self.description = description
        self.start_time = start_time  # datetime对象
        self.end_time = end_time      # datetime对象
        self.completed = completed
        self.notified_start = False
        self.notified_end = False

    def to_dict(self):
        return {
            "type": "todo",
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "completed": self.completed
        }

    @staticmethod
    def from_dict(data):
        start_time = datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S") if data["start_time"] else None
        end_time = datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S") if data["end_time"] else None
        return TodoItem(
            data["title"],
            data["description"],
            start_time,
            end_time,
            data["completed"]
        )

class ClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Timer Clock")
        self.root.geometry("1000x700")  # 增大窗口尺寸以容纳新功能
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_main_window)

        # 初始化数据结构
        self.timers = []     # 存储多个倒计时器
        self.alarms = []     # 存储多个闹钟
        self.countdowns = [] # 存储多个倒计日
        self.stopwatch = Stopwatch()  # 秒表
        self.todos = []      # 存储待办事项
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year
        
        # 历史记录文件路径
        self.history_file = "clock_history.json"
        
        # 加载历史记录
        self.load_history()

        # 创建顶部菜单栏
        self.create_menu_bar()
        
        # 主界面布局
        self.create_widgets()
        self.update_main_clock()

    def create_menu_bar(self):
        # 创建菜单栏
        menu_bar = tk.Menu(self.root)
        
        # 创建"文件"菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="历史记录", command=self.show_history_window)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_close_main_window)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 创建"工具"菜单
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="世界时钟", command=self.show_world_clock)
        tools_menu.add_command(label="日历", command=self.show_calendar)
        menu_bar.add_cascade(label="工具", menu=tools_menu)
        
        # 创建"关于"菜单
        about_menu = tk.Menu(menu_bar, tearoff=0)
        about_menu.add_command(label="关于时钟", command=self.show_about_dialog)
        menu_bar.add_cascade(label="关于", menu=about_menu)
        
        # 设置菜单栏
        self.root.config(menu=menu_bar)

    def show_about_dialog(self):
        # 创建关于对话框
        about_window = tk.Toplevel(self.root)
        about_window.title("关于")
        about_window.geometry("300x200")
        about_window.resizable(False, False)
        
        # 居中显示
        about_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + self.root.winfo_width() // 2 - 150,
            self.root.winfo_rooty() + self.root.winfo_height() // 2 - 100
        ))
        
        # 添加标题
        title_label = tk.Label(about_window, text="关于时钟TimerClock", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)
        
        # 添加应用名称
        name_label = tk.Label(about_window, text="TimerClock", font=("Helvetica", 14))
        name_label.pack(pady=5)
        
        # 添加版本号
        version_label = tk.Label(about_window, text="v2.0", font=("Helvetica", 12))
        version_label.pack(pady=5)
        
        # 添加描述
        desc_label = tk.Label(about_window, text="时钟应用，支持倒计时、闹钟、倒计日、秒表、世界时钟、待办事项和日历功能，作者Jerry，https://space.bilibili.com/3546730406611340")
        desc_label.pack(pady=10, padx=10)
        
        # 添加确定按钮
        ok_button = ttk.Button(about_window, text="确定", command=about_window.destroy)
        ok_button.pack(pady=10)

    def create_widgets(self):
        # 主时钟显示
        self.main_clock_label = tk.Label(
            self.root, font=('Helvetica', 48), fg='blue')
        self.main_clock_label.pack(pady=20)

        # 创建主容器
        main_notebook = ttk.Notebook(self.root)
        main_notebook.pack(expand=True, fill='both', padx=10, pady=5)

        # 创建功能标签页
        self.create_timer_tab(main_notebook)
        self.create_alarm_tab(main_notebook)
        self.create_countdown_tab(main_notebook)
        self.create_stopwatch_tab(main_notebook)
        self.create_todo_tab(main_notebook)  # 新增ToDo标签页

    def create_timer_tab(self, notebook):
        # 倒计时器标签页
        timer_frame = ttk.Frame(notebook)
        notebook.add(timer_frame, text="倒计时器")

        # 输入区域
        input_frame = ttk.Frame(timer_frame)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="名称:").grid(row=0, column=0)
        self.timer_name = ttk.Entry(input_frame, width=15)
        self.timer_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="分钟:").grid(row=0, column=2)
        self.timer_min = ttk.Entry(input_frame, width=5)
        self.timer_min.grid(row=0, column=3, padx=5)
        
        ttk.Label(input_frame, text="秒钟:").grid(row=0, column=4)
        self.timer_sec = ttk.Entry(input_frame, width=5)
        self.timer_sec.grid(row=0, column=5, padx=5)
        
        ttk.Button(input_frame, text="添加倒计时", 
                 command=self.add_timer).grid(row=0, column=6, padx=10)

        # 倒计时列表
        columns = ('name', 'time', 'status')
        self.timer_tree = ttk.Treeview(timer_frame, columns=columns, show='headings', height=8)
        self.timer_tree.heading('name', text='名称')
        self.timer_tree.heading('time', text='剩余时间')
        self.timer_tree.heading('status', text='状态')
        self.timer_tree.column('name', width=150)
        self.timer_tree.column('time', width=100)
        self.timer_tree.column('status', width=80)
        self.timer_tree.pack(expand=True, fill='both', padx=10, pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(timer_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="停止选中", command=self.stop_selected_timer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="独立窗口", command=self.open_selected_timer_window).pack(side=tk.LEFT, padx=5)

    def create_alarm_tab(self, notebook):
        # 闹钟标签页
        alarm_frame = ttk.Frame(notebook)
        notebook.add(alarm_frame, text="闹钟")

        # 输入区域
        input_frame = ttk.Frame(alarm_frame)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="名称:").grid(row=0, column=0)
        self.alarm_name = ttk.Entry(input_frame, width=15)
        self.alarm_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="小时:").grid(row=0, column=2)
        self.alarm_hour = ttk.Entry(input_frame, width=5)
        self.alarm_hour.grid(row=0, column=3, padx=5)
        
        ttk.Label(input_frame, text="分钟:").grid(row=0, column=4)
        self.alarm_min = ttk.Entry(input_frame, width=5)
        self.alarm_min.grid(row=0, column=5, padx=5)
        
        ttk.Label(input_frame, text="重复:").grid(row=0, column=6)
        self.alarm_repeat = ttk.Combobox(input_frame, values=["不重复", "每天", "仅周末"], width=8)
        self.alarm_repeat.grid(row=0, column=7, padx=5)
        self.alarm_repeat.current(0)
        
        ttk.Button(input_frame, text="添加闹钟", 
                 command=self.add_alarm).grid(row=0, column=8, padx=10)

        # 闹钟列表
        columns = ('name', 'time', 'repeat', 'status')
        self.alarm_tree = ttk.Treeview(alarm_frame, columns=columns, show='headings', height=8)
        self.alarm_tree.heading('name', text='名称')
        self.alarm_tree.heading('time', text='闹钟时间')
        self.alarm_tree.heading('repeat', text='重复')
        self.alarm_tree.heading('status', text='状态')
        self.alarm_tree.column('name', width=120)
        self.alarm_tree.column('time', width=120)
        self.alarm_tree.column('repeat', width=80)
        self.alarm_tree.column('status', width=80)
        self.alarm_tree.pack(expand=True, fill='both', padx=10, pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(alarm_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_alarm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="独立窗口", command=self.open_selected_alarm_window).pack(side=tk.LEFT, padx=5)

    def create_countdown_tab(self, notebook):
        # 倒计日标签页
        countdown_frame = ttk.Frame(notebook)
        notebook.add(countdown_frame, text="倒计日")

        # 输入区域
        input_frame = ttk.Frame(countdown_frame)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="名称:").grid(row=0, column=0)
        self.countdown_name = ttk.Entry(input_frame, width=15)
        self.countdown_name.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="目标日期 (YYYY-MM-DD):").grid(row=0, column=2)
        self.target_date_entry = ttk.Entry(input_frame, width=15)
        self.target_date_entry.grid(row=0, column=3, padx=5)
        
        ttk.Button(input_frame, text="添加倒计日", 
                 command=self.add_countdown).grid(row=0, column=4, padx=10)

        # 倒计日列表
        columns = ('name', 'days', 'date')
        self.countdown_tree = ttk.Treeview(countdown_frame, columns=columns, show='headings', height=8)
        self.countdown_tree.heading('name', text='名称')
        self.countdown_tree.heading('days', text='剩余天数')
        self.countdown_tree.heading('date', text='目标日期')
        self.countdown_tree.column('name', width=150)
        self.countdown_tree.column('days', width=100)
        self.countdown_tree.column('date', width=150)
        self.countdown_tree.pack(expand=True, fill='both', padx=10, pady=5)
        
        # 控制按钮
        btn_frame = ttk.Frame(countdown_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_countdown).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="独立窗口", command=self.open_selected_countdown_window).pack(side=tk.LEFT, padx=5)

    def create_stopwatch_tab(self, notebook):
        # 秒表标签页
        stopwatch_frame = ttk.Frame(notebook)
        notebook.add(stopwatch_frame, text="秒表")
        
        self.stopwatch_label = tk.Label(stopwatch_frame, font=('Helvetica', 36))
        self.stopwatch_label.pack(pady=20)
        
        btn_frame = ttk.Frame(stopwatch_frame)
        btn_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="开始", command=self.start_stopwatch)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(btn_frame, text="暂停", command=self.pause_stopwatch)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = ttk.Button(btn_frame, text="重置", command=self.reset_stopwatch)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="独立窗口", command=self.open_stopwatch_window).pack(side=tk.LEFT, padx=5)

    def create_todo_tab(self, notebook):
        """创建待办事项标签页"""
        todo_frame = ttk.Frame(notebook)
        notebook.add(todo_frame, text="待办事项")
        
        # 输入区域
        input_frame = ttk.LabelFrame(todo_frame, text="添加待办事项")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 标题
        ttk.Label(input_frame, text="标题:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.todo_title = ttk.Entry(input_frame, width=30)
        self.todo_title.grid(row=0, column=1, padx=5, pady=5)
        
        # 描述
        ttk.Label(input_frame, text="描述:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.todo_description = ttk.Entry(input_frame, width=30)
        self.todo_description.grid(row=1, column=1, padx=5, pady=5)
        
        # 开始时间
        ttk.Label(input_frame, text="开始时间:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        start_frame = ttk.Frame(input_frame)
        start_frame.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.todo_start_date = ttk.Entry(start_frame, width=10)
        self.todo_start_date.grid(row=0, column=0, padx=2)
        self.todo_start_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.todo_start_hour = ttk.Spinbox(start_frame, from_=0, to=23, width=3)
        self.todo_start_hour.grid(row=0, column=1, padx=2)
        self.todo_start_hour.set("09")
        
        ttk.Label(start_frame, text=":").grid(row=0, column=2)
        
        self.todo_start_min = ttk.Spinbox(start_frame, from_=0, to=59, width=3)
        self.todo_start_min.grid(row=0, column=3, padx=2)
        self.todo_start_min.set("00")
        
        # 结束时间
        ttk.Label(input_frame, text="结束时间:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        end_frame = ttk.Frame(input_frame)
        end_frame.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.todo_end_date = ttk.Entry(end_frame, width=10)
        self.todo_end_date.grid(row=0, column=0, padx=2)
        self.todo_end_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.todo_end_hour = ttk.Spinbox(end_frame, from_=0, to=23, width=3)
        self.todo_end_hour.grid(row=0, column=1, padx=2)
        self.todo_end_hour.set("17")
        
        ttk.Label(end_frame, text=":").grid(row=0, column=2)
        
        self.todo_end_min = ttk.Spinbox(end_frame, from_=0, to=59, width=3)
        self.todo_end_min.grid(row=0, column=3, padx=2)
        self.todo_end_min.set("00")
        
        # 添加按钮
        add_btn = ttk.Button(input_frame, text="添加待办事项", command=self.add_todo)
        add_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        # 待办事项列表
        list_frame = ttk.LabelFrame(todo_frame, text="待办事项列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('title', 'start', 'end', 'status')
        self.todo_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列
        self.todo_tree.heading('title', text='标题')
        self.todo_tree.column('title', width=150)
        
        self.todo_tree.heading('start', text='开始时间')
        self.todo_tree.column('start', width=150)
        
        self.todo_tree.heading('end', text='结束时间')
        self.todo_tree.column('end', width=150)
        
        self.todo_tree.heading('status', text='状态')
        self.todo_tree.column('status', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.todo_tree.yview)
        self.todo_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.todo_tree.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        btn_frame = ttk.Frame(todo_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="标记完成", command=self.mark_todo_completed).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_selected_todo).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查看详情", command=self.view_todo_details).pack(side=tk.LEFT, padx=5)
        
        # 更新待办事项列表
        self.update_todo_list()

    def update_main_clock(self):
        current_time = time.strftime("%H:%M:%S")
        self.main_clock_label.config(text=current_time)
        
        # 更新所有组件
        self.update_timers()
        self.check_alarms()
        self.update_countdowns()
        self.update_stopwatch()
        self.check_todo_notifications()  # 检查待办事项通知
        
        self.root.after(1000, self.update_main_clock)

    # 倒计时器相关方法
    def add_timer(self):
        try:
            name = self.timer_name.get() or "倒计时"
            minutes = int(self.timer_min.get() or 0)
            seconds = int(self.timer_sec.get() or 0)
            if minutes == 0 and seconds == 0:
                messagebox.showerror("错误", "时间不能为零")
                return
            new_timer = CountdownTimer(name, minutes, seconds)
            self.timers.append(new_timer)
            self.update_timer_list()
        except ValueError:
            messagebox.showerror("错误", "请输入有效数字")

    def update_timers(self):
        for timer in self.timers:
            if timer.running:
                remaining = timer.remaining_time().total_seconds()
                if remaining <= 0:
                    timer.running = False
                    messagebox.showinfo("时间到", f"{timer.name} 倒计时结束！")
        self.update_timer_list()

    def update_timer_list(self):
        for item in self.timer_tree.get_children():
            self.timer_tree.delete(item)
            
        for timer in self.timers:
            if timer.running:
                remaining = timer.remaining_time().total_seconds()
                if remaining <= 0:
                    status = "已结束"
                    time_str = "00:00"
                else:
                    status = "进行中"
                    mins, secs = divmod(int(remaining), 60)
                    time_str = f"{mins:02d}:{secs:02d}"
            else:
                status = "已结束"
                time_str = "00:00"
                
            self.timer_tree.insert("", tk.END, values=(timer.name, time_str, status))

    def stop_selected_timer(self):
        selection = self.timer_tree.selection()
        if selection:
            index = self.timer_tree.index(selection[0])
            if 0 <= index < len(self.timers):
                del self.timers[index]
                self.update_timer_list()

    def open_selected_timer_window(self):
        selection = self.timer_tree.selection()
        if selection:
            index = self.timer_tree.index(selection[0])
            if 0 <= index < len(self.timers):
                timer = self.timers[index]
                self.create_timer_window(timer)

    def create_timer_window(self, timer):
        window = tk.Toplevel(self.root)
        window.title(timer.name)
        window.geometry("300x200")
        
        label = tk.Label(window, text=timer.name, font=('Helvetica', 24))
        label.pack(pady=10)
        
        time_label = tk.Label(window, text="00:00", font=('Helvetica', 48))
        time_label.pack(pady=20)
        
        def update_window_timer():
            if timer.running:
                remaining = timer.remaining_time().total_seconds()
                if remaining <= 0:
                    timer.running = False
                    time_label.config(text="00:00")
                    messagebox.showinfo("时间到", f"{timer.name} 倒计时结束！")
                    window.destroy()
                    return
                else:
                    mins, secs = divmod(int(remaining), 60)
                    time_label.config(text=f"{mins:02d}:{secs:02d}")
            else:
                time_label.config(text="00:00")
                
            window.after(1000, update_window_timer)
            
        update_window_timer()
        
        stop_btn = ttk.Button(window, text="停止", command=lambda: setattr(timer, 'running', False))
        stop_btn.pack(pady=10)

    # 闹钟相关方法
    def add_alarm(self):
        try:
            name = self.alarm_name.get() or "闹钟"
            hour = int(self.alarm_hour.get())
            minute = int(self.alarm_min.get())
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
                
            repeat_map = {"不重复": "once", "每天": "daily", "仅周末": "weekend"}
            repeat = repeat_map[self.alarm_repeat.get()]
            
            new_alarm = Alarm(name, hour, minute, repeat)
            self.alarms.append(new_alarm)
            self.update_alarm_list()
        except ValueError:
            messagebox.showerror("错误", "请输入有效时间（小时0-23，分钟0-59）")

    def check_alarms(self):
        for alarm in self.alarms[:]:
            if alarm.check_and_update():
                messagebox.showinfo("闹钟", f"{alarm.name} 时间到了！")
                self.update_alarm_list()

    def update_alarm_list(self):
        for item in self.alarm_tree.get_children():
            self.alarm_tree.delete(item)
            
        repeat_text = {"once": "不重复", "daily": "每天", "weekend": "仅周末"}
            
        for alarm in self.alarms:
            status = "开启" if alarm.active else "关闭"
            time_str = alarm.alarm_time.strftime("%H:%M")
            self.alarm_tree.insert("", tk.END, values=(
                alarm.name, time_str, repeat_text[alarm.repeat], status))

    def delete_selected_alarm(self):
        selection = self.alarm_tree.selection()
        if selection:
            index = self.alarm_tree.index(selection[0])
            if 0 <= index < len(self.alarms):
                del self.alarms[index]
                self.update_alarm_list()

    def open_selected_alarm_window(self):
        selection = self.alarm_tree.selection()
        if selection:
            index = self.alarm_tree.index(selection[0])
            if 0 <= index < len(self.alarms):
                alarm = self.alarms[index]
                self.create_alarm_window(alarm)

    def create_alarm_window(self, alarm):
        window = tk.Toplevel(self.root)
        window.title(alarm.name)
        window.geometry("300x200")
        
        label = tk.Label(window, text=alarm.name, font=('Helvetica', 24))
        label.pack(pady=10)
        
        time_label = tk.Label(window, text="00:00", font=('Helvetica', 48))
        time_label.pack(pady=20)
        
        repeat_map = {"once": "不重复", "daily": "每天", "weekend": "仅周末"}
        repeat_label = tk.Label(window, text=f"重复: {repeat_map[alarm.repeat]}")
        repeat_label.pack(pady=5)
        
        def update_window_alarm():
            time_str = alarm.alarm_time.strftime("%H:%M:%S")
            time_label.config(text=time_str)
            window.after(1000, update_window_alarm)
            
        update_window_alarm()
        
        stop_btn = ttk.Button(window, text="关闭", command=lambda: setattr(alarm, 'active', False))
        stop_btn.pack(pady=10)

    # 倒计日相关方法
    def add_countdown(self):
        date_str = self.target_date_entry.get()
        name = self.countdown_name.get() or "倒计日"
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            self.countdowns.append(Countdown(name, target_date))
            self.update_countdown_list()
        except ValueError:
            messagebox.showerror("错误", "无效日期格式，请使用YYYY-MM-DD")

    def update_countdowns(self):
        self.update_countdown_list()

    def update_countdown_list(self):
        for item in self.countdown_tree.get_children():
            self.countdown_tree.delete(item)
            
        now = datetime.now().date()
        for countdown in self.countdowns:
            target_date = countdown.target_date.date()
            delta = (target_date - now).days
            status = f"剩余 {delta} 天" if delta >=0 else f"已过期 {-delta} 天"
            self.countdown_tree.insert("", tk.END, values=(countdown.name, status, target_date.strftime("%Y-%m-%d")))

    def delete_selected_countdown(self):
        selection = self.countdown_tree.selection()
        if selection:
            index = self.countdown_tree.index(selection[0])
            if 0 <= index < len(self.countdowns):
                del self.countdowns[index]
                self.update_countdown_list()

    def open_selected_countdown_window(self):
        selection = self.countdown_tree.selection()
        if selection:
            index = self.countdown_tree.index(selection[0])
            if 0 <= index < len(self.countdowns):
                countdown = self.countdowns[index]
                self.create_countdown_window(countdown)

    def create_countdown_window(self, countdown):
        window = tk.Toplevel(self.root)
        window.title(countdown.name)
        window.geometry("300x200")
        
        label = tk.Label(window, text=countdown.name, font=('Helvetica', 24))
        label.pack(pady=10)
        
        days_label = tk.Label(window, text="0天", font=('Helvetica', 48))
        days_label.pack(pady=20)
        
        date_label = tk.Label(window, text=countdown.target_date.strftime("%Y-%m-%d"))
        date_label.pack(pady=5)
        
        def update_window_countdown():
            now = datetime.now().date()
            delta = (countdown.target_date.date() - now).days
            if delta >= 0:
                status = f"剩余 {delta} 天"
            else:
                status = f"已过期 {-delta} 天"
            days_label.config(text=status)
            window.after(86400000, update_window_countdown)  # 每天更新一次
            
        update_window_countdown()

    # 秒表功能
    def start_stopwatch(self):
        if not self.stopwatch.running:
            self.stopwatch.start_time = time.time() - self.stopwatch.elapsed_time
            self.stopwatch.running = True

    def update_stopwatch(self):
        if self.stopwatch.running:
            self.stopwatch.elapsed_time = time.time() - self.stopwatch.start_time
            minutes, seconds = divmod(int(self.stopwatch.elapsed_time), 60)
            milliseconds = int((self.stopwatch.elapsed_time - int(self.stopwatch.elapsed_time)) * 100)
            self.stopwatch_label.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
        else:
            minutes, seconds = divmod(int(self.stopwatch.elapsed_time), 60)
            milliseconds = int((self.stopwatch.elapsed_time - int(self.stopwatch.elapsed_time)) * 100)
            self.stopwatch_label.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")

    def pause_stopwatch(self):
        self.stopwatch.running = False

    def reset_stopwatch(self):
        self.stopwatch.running = False
        self.stopwatch.elapsed_time = 0
        self.stopwatch_label.config(text="00:00.00")

    def open_stopwatch_window(self):
        window = tk.Toplevel(self.root)
        window.title("秒表")
        window.geometry("300x250")
        
        stopwatch_label = tk.Label(window, text="00:00.00", font=('Helvetica', 48))
        stopwatch_label.pack(pady=20)
        
        btn_frame = ttk.Frame(window)
        btn_frame.pack(pady=10)
        
        def start_window_stopwatch():
            nonlocal running
            if not running:
                self.start_stopwatch()
                running = True
                update_window_stopwatch()

        def pause_window_stopwatch():
            nonlocal running
            self.pause_stopwatch()
            running = False

        def reset_window_stopwatch():
            nonlocal running
            self.reset_stopwatch()
            running = False
            stopwatch_label.config(text="00:00.00")

        def update_window_stopwatch():
            minutes, seconds = divmod(int(self.stopwatch.elapsed_time), 60)
            milliseconds = int((self.stopwatch.elapsed_time - int(self.stopwatch.elapsed_time)) * 100)
            stopwatch_label.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
            if running:
                window.after(10, update_window_stopwatch)

        ttk.Button(btn_frame, text="开始", command=start_window_stopwatch).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="暂停", command=pause_window_stopwatch).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置", command=reset_window_stopwatch).pack(side=tk.LEFT, padx=5)
        
        # 与主窗口秒表同步状态
        running = self.stopwatch.running
        if running:
            update_window_stopwatch()
        else:
            minutes, seconds = divmod(int(self.stopwatch.elapsed_time), 60)
            milliseconds = int((self.stopwatch.elapsed_time - int(self.stopwatch.elapsed_time)) * 100)
            stopwatch_label.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")

    # ====== 待办事项功能 ======
    def add_todo(self):
        """添加待办事项"""
        title = self.todo_title.get().strip()
        if not title:
            messagebox.showerror("错误", "标题不能为空")
            return
            
        description = self.todo_description.get().strip()
        
        # 解析开始时间
        try:
            start_date_str = self.todo_start_date.get()
            start_hour = int(self.todo_start_hour.get())
            start_min = int(self.todo_start_min.get())
            start_time = datetime.strptime(f"{start_date_str} {start_hour}:{start_min}", "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror("错误", "开始时间格式无效，请使用YYYY-MM-DD格式")
            return
            
        # 解析结束时间
        try:
            end_date_str = self.todo_end_date.get()
            end_hour = int(self.todo_end_hour.get())
            end_min = int(self.todo_end_min.get())
            end_time = datetime.strptime(f"{end_date_str} {end_hour}:{end_min}", "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror("错误", "结束时间格式无效，请使用YYYY-MM-DD格式")
            return
            
        # 检查时间有效性
        if end_time <= start_time:
            messagebox.showerror("错误", "结束时间必须晚于开始时间")
            return
            
        # 创建待办事项
        new_todo = TodoItem(title, description, start_time, end_time)
        self.todos.append(new_todo)
        
        # 清空输入框
        self.todo_title.delete(0, tk.END)
        self.todo_description.delete(0, tk.END)
        
        # 更新列表
        self.update_todo_list()
        messagebox.showinfo("成功", "待办事项已添加")

    def update_todo_list(self):
        """更新待办事项列表"""
        # 清空当前列表
        for item in self.todo_tree.get_children():
            self.todo_tree.delete(item)
            
        # 添加所有待办事项
        for i, todo in enumerate(self.todos):
            start_str = todo.start_time.strftime("%Y-%m-%d %H:%M") if todo.start_time else "无"
            end_str = todo.end_time.strftime("%Y-%m-%d %H:%M") if todo.end_time else "无"
            
            status = "已完成" if todo.completed else "进行中"
            if todo.start_time and datetime.now() < todo.start_time:
                status = "未开始"
                
            self.todo_tree.insert("", tk.END, values=(todo.title, start_str, end_str, status), tags=("completed" if todo.completed else "active"))

    def mark_todo_completed(self):
        """标记选中的待办事项为已完成"""
        selection = self.todo_tree.selection()
        if not selection:
            return
            
        index = self.todo_tree.index(selection[0])
        if 0 <= index < len(self.todos):
            self.todos[index].completed = True
            self.update_todo_list()

    def delete_selected_todo(self):
        """删除选中的待办事项"""
        selection = self.todo_tree.selection()
        if not selection:
            return
            
        index = self.todo_tree.index(selection[0])
        if 0 <= index < len(self.todos):
            del self.todos[index]
            self.update_todo_list()

    def view_todo_details(self):
        """查看待办事项详情"""
        selection = self.todo_tree.selection()
        if not selection:
            return
            
        index = self.todo_tree.index(selection[0])
        if 0 <= index < len(self.todos):
            todo = self.todos[index]
            
            # 创建详情窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"待办事项详情: {todo.title}")
            detail_window.geometry("400x300")
            
            # 标题
            tk.Label(detail_window, text=todo.title, font=("Helvetica", 16, "bold")).pack(pady=10)
            
            # 描述
            desc_frame = ttk.LabelFrame(detail_window, text="描述")
            desc_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(desc_frame, text=todo.description, wraplength=350).pack(padx=5, pady=5)
            
            # 时间信息
            time_frame = ttk.Frame(detail_window)
            time_frame.pack(fill=tk.X, padx=10, pady=10)
            
            if todo.start_time:
                tk.Label(time_frame, text="开始时间:").grid(row=0, column=0, sticky=tk.W, padx=5)
                tk.Label(time_frame, text=todo.start_time.strftime("%Y-%m-%d %H:%M")).grid(row=0, column=1, sticky=tk.W)
                
            if todo.end_time:
                tk.Label(time_frame, text="结束时间:").grid(row=1, column=0, sticky=tk.W, padx=5)
                tk.Label(time_frame, text=todo.end_time.strftime("%Y-%m-%d %H:%M")).grid(row=1, column=1, sticky=tk.W)
            
            # 状态
            status_frame = ttk.Frame(detail_window)
            status_frame.pack(fill=tk.X, padx=10, pady=10)
            tk.Label(status_frame, text="状态:").grid(row=0, column=0, sticky=tk.W, padx=5)
            status_text = "已完成" if todo.completed else "进行中"
            if todo.start_time and datetime.now() < todo.start_time:
                status_text = "未开始"
            tk.Label(status_frame, text=status_text, fg="green" if todo.completed else "blue").grid(row=0, column=1, sticky=tk.W)
            
            # 关闭按钮
            ttk.Button(detail_window, text="关闭", command=detail_window.destroy).pack(pady=10)

    def check_todo_notifications(self):
        """检查待办事项通知"""
        now = datetime.now()
        
        for todo in self.todos:
            if todo.completed:
                continue
                
            # 检查开始时间通知
            if todo.start_time and not todo.notified_start:
                # 提前5分钟通知
                if now >= todo.start_time - timedelta(minutes=5) and now < todo.start_time:
                    messagebox.showinfo("待办事项即将开始", 
                                      f"待办事项 '{todo.title}' 即将在5分钟后开始！\n"
                                      f"开始时间: {todo.start_time.strftime('%Y-%m-%d %H:%M')}")
                    todo.notified_start = True
                    
                # 到开始时间通知
                elif now >= todo.start_time and now < todo.start_time + timedelta(minutes=1):
                    messagebox.showinfo("待办事项已开始", 
                                      f"待办事项 '{todo.title}' 已开始！\n"
                                      f"开始时间: {todo.start_time.strftime('%Y-%m-%d %H:%M')}")
                    todo.notified_start = True
            
            # 检查结束时间通知
            if todo.end_time and not todo.notified_end:
                # 提前5分钟通知
                if now >= todo.end_time - timedelta(minutes=5) and now < todo.end_time:
                    messagebox.showinfo("待办事项即将结束", 
                                      f"待办事项 '{todo.title}' 即将在5分钟后结束！\n"
                                      f"结束时间: {todo.end_time.strftime('%Y-%m-%d %H:%M')}")
                    todo.notified_end = True
                    
                # 到结束时间通知
                elif now >= todo.end_time and now < todo.end_time + timedelta(minutes=1):
                    messagebox.showinfo("待办事项已结束", 
                                      f"待办事项 '{todo.title}' 已结束！\n"
                                      f"结束时间: {todo.end_time.strftime('%Y-%m-%d %H:%M')}")
                    todo.notified_end = True

    # ====== 世界时钟功能 ======
    def show_world_clock(self):
        """显示世界时钟窗口"""
        world_clock_window = tk.Toplevel(self.root)
        world_clock_window.title("世界时钟")
        world_clock_window.geometry("400x300")
        
        # 时区选择
        tz_frame = ttk.LabelFrame(world_clock_window, text="选择时区")
        tz_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 常用时区列表
        common_timezones = [
            ("UTC", "UTC"),
            ("伦敦", "Europe/London"),
            ("纽约", "America/New_York"),
            ("洛杉矶", "America/Los_Angeles"),
            ("东京", "Asia/Tokyo"),
            ("悉尼", "Australia/Sydney"),
            ("巴黎", "Europe/Paris"),
            ("柏林", "Europe/Berlin"),
            ("莫斯科", "Europe/Moscow"),
            ("北京", "Asia/Shanghai"),
            ("新加坡", "Asia/Singapore"),
            ("迪拜", "Asia/Dubai"),
            ("孟买", "Asia/Kolkata")
        ]
        
        self.selected_tz = tk.StringVar(value=common_timezones[0][1])
        
        # 创建时区选择下拉框
        tz_combobox = ttk.Combobox(tz_frame, textvariable=self.selected_tz, state="readonly")
        tz_combobox['values'] = [tz[1] for tz in common_timezones]
        tz_combobox.pack(padx=10, pady=5, fill=tk.X)
        
        # 时间显示
        time_frame = ttk.Frame(world_clock_window)
        time_frame.pack(pady=20)
        
        self.world_time_label = tk.Label(time_frame, font=('Helvetica', 24))
        self.world_time_label.pack()
        
        self.world_date_label = tk.Label(time_frame, font=('Helvetica', 14))
        self.world_date_label.pack(pady=5)
        
        # 更新世界时钟
        self.update_world_clock()
        
        # 设置定时器持续更新
        def update_clock():
            self.update_world_clock()
            world_clock_window.after(1000, update_clock)
            
        update_clock()

    def update_world_clock(self):
        """更新世界时钟显示"""
        try:
            # 获取选定时区
            tz = pytz.timezone(self.selected_tz.get())
            
            # 获取该时区的当前时间
            now = datetime.now(tz)
            
            # 更新时间显示
            self.world_time_label.config(text=now.strftime("%H:%M:%S"))
            self.world_date_label.config(text=now.strftime("%Y-%m-%d %A"))
        except pytz.UnknownTimeZoneError:
            self.world_time_label.config(text="无效时区")
            self.world_date_label.config(text="")

    # ====== 日历功能 ======
    def show_calendar(self):
        """显示日历窗口"""
        calendar_window = tk.Toplevel(self.root)
        calendar_window.title("日历")
        calendar_window.geometry("600x500")
        
        # 导航栏
        nav_frame = ttk.Frame(calendar_window)
        nav_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 上一年按钮
        prev_year_btn = ttk.Button(nav_frame, text="<<", width=5, 
                                 command=lambda: self.change_calendar_month(-12, calendar_window))
        prev_year_btn.pack(side=tk.LEFT, padx=2)
        
        # 上一月按钮
        prev_month_btn = ttk.Button(nav_frame, text="<", width=5, 
                                  command=lambda: self.change_calendar_month(-1, calendar_window))
        prev_month_btn.pack(side=tk.LEFT, padx=2)
        
        # 当前年月显示
        self.calendar_header = tk.Label(nav_frame, text=f"{self.current_year}年 {self.current_month}月", 
                                      font=("Helvetica", 14))
        self.calendar_header.pack(side=tk.LEFT, expand=True)
        
        # 下一月按钮
        next_month_btn = ttk.Button(nav_frame, text=">", width=5, 
                                  command=lambda: self.change_calendar_month(1, calendar_window))
        next_month_btn.pack(side=tk.RIGHT, padx=2)
        
        # 下一年按钮
        next_year_btn = ttk.Button(nav_frame, text=">>", width=5, 
                                 command=lambda: self.change_calendar_month(12, calendar_window))
        next_year_btn.pack(side=tk.RIGHT, padx=2)
        
        # 今天按钮
        today_btn = ttk.Button(nav_frame, text="今天", command=lambda: self.go_to_today(calendar_window))
        today_btn.pack(side=tk.RIGHT, padx=10)
        
        # 日历显示区域
        self.calendar_frame = ttk.Frame(calendar_window)
        self.calendar_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 初始化日历
        self.update_calendar(calendar_window)

    def change_calendar_month(self, delta, window):
        """改变日历显示的月份"""
        self.current_month += delta
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        elif self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
            
        self.calendar_header.config(text=f"{self.current_year}年 {self.current_month}月")
        self.update_calendar(window)

    def go_to_today(self, window):
        """回到当前月份"""
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        self.calendar_header.config(text=f"{self.current_year}年 {self.current_month}月")
        self.update_calendar(window)

    def update_calendar(self, window):
        """更新日历显示"""
        # 清除现有日历
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
            
        # 创建星期标题
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        for i, day in enumerate(weekdays):
            label = tk.Label(self.calendar_frame, text=day, width=10, height=2, 
                           relief=tk.RIDGE, bg="#f0f0f0")
            label.grid(row=0, column=i, sticky="nsew")
            
        # 获取当月的日历
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        
        # 获取有todo的日期
        todo_dates = set()
        for todo in self.todos:
            if todo.start_time:
                if todo.start_time.year == self.current_year and todo.start_time.month == self.current_month:
                    todo_dates.add(todo.start_time.day)
            if todo.end_time:
                if todo.end_time.year == self.current_year and todo.end_time.month == self.current_month:
                    todo_dates.add(todo.end_time.day)
        
        # 填充日历
        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    # 不在当前月的日期
                    label = tk.Label(self.calendar_frame, text="", width=10, height=3, 
                                   relief=tk.RIDGE, bg="#f8f8f8")
                else:
                    # 当前月的日期
                    bg_color = "#ffffff"
                    fg_color = "#000000"
                    
                    # 如果是今天，高亮显示
                    now = datetime.now()
                    if (day == now.day and 
                        self.current_month == now.month and 
                        self.current_year == now.year):
                        bg_color = "#e6f7ff"
                    
                    # 如果有待办事项，添加标记
                    todo_marker = ""
                    if day in todo_dates:
                        todo_marker = " ●"
                        fg_color = "#ff0000"
                    
                    label = tk.Label(self.calendar_frame, text=f"{day}{todo_marker}", 
                                   width=10, height=3, relief=tk.RIDGE,
                                   bg=bg_color, fg=fg_color)
                    
                    # 添加点击事件
                    label.bind("<Button-1>", lambda e, d=day: self.show_day_todos(d, window))
                    
                label.grid(row=week_num+1, column=day_num, sticky="nsew")
                
        # 设置网格权重，使日历单元格均匀分布
        for i in range(7):
            self.calendar_frame.columnconfigure(i, weight=1)
        for i in range(6):  # 最多6行
            self.calendar_frame.rowconfigure(i+1, weight=1)

    def show_day_todos(self, day, parent_window):
        """显示某一天的待办事项"""
        # 获取该日期的所有待办事项
        day_todos = []
        target_date = datetime(self.current_year, self.current_month, day)
        
        for todo in self.todos:
            # 检查开始或结束时间是否匹配
            if (todo.start_time and todo.start_time.date() == target_date.date()) or \
               (todo.end_time and todo.end_time.date() == target_date.date()):
                day_todos.append(todo)
                
        if not day_todos:
            messagebox.showinfo("待办事项", f"{target_date.strftime('%Y-%m-%d')} 没有待办事项")
            return
            
        # 创建待办事项列表窗口
        todos_window = tk.Toplevel(parent_window)
        todos_window.title(f"{target_date.strftime('%Y-%m-%d')} 的待办事项")
        todos_window.geometry("500x400")
        
        # 标题
        tk.Label(todos_window, text=f"{target_date.strftime('%Y-%m-%d')} 的待办事项", 
                font=("Helvetica", 14, "bold")).pack(pady=10)
        
        # 列表框架
        list_frame = ttk.Frame(todos_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建列表
        columns = ('title', 'time', 'status')
        todo_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        # 设置列
        todo_tree.heading('title', text='标题')
        todo_tree.column('title', width=200)
        
        todo_tree.heading('time', text='时间')
        todo_tree.column('time', width=150)
        
        todo_tree.heading('status', text='状态')
        todo_tree.column('status', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=todo_tree.yview)
        todo_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        todo_tree.pack(fill=tk.BOTH, expand=True)
        
        # 填充数据
        for todo in day_todos:
            time_str = ""
            if todo.start_time and todo.start_time.date() == target_date.date():
                time_str += f"开始: {todo.start_time.strftime('%H:%M')}"
            if todo.end_time and todo.end_time.date() == target_date.date():
                if time_str:
                    time_str += "\n"
                time_str += f"结束: {todo.end_time.strftime('%H:%M')}"
                
            status = "已完成" if todo.completed else "进行中"
            if todo.start_time and datetime.now() < todo.start_time:
                status = "未开始"
                
            todo_tree.insert("", tk.END, values=(todo.title, time_str, status))
        
        # 关闭按钮
        ttk.Button(todos_window, text="关闭", command=todos_window.destroy).pack(pady=10)

    def on_close_main_window(self):
        # 保存历史记录
        self.save_history()
        
        self.root.withdraw()
        self.create_small_window()

    def create_small_window(self):
        small_window = tk.Toplevel()
        small_window.title("时钟状态")
        screen_width = small_window.winfo_screenwidth()
        screen_height = small_window.winfo_screenheight()
        window_width = 200
        window_height = 150
        x = screen_width - window_width
        y = 0
        small_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        small_window.protocol("WM_DELETE_WINDOW", self.on_close_small_window)

        has_timer = len(self.timers) > 0
        has_alarm = len(self.alarms) > 0
        has_countdown = len(self.countdowns) > 0
        has_stopwatch = self.stopwatch.running
        has_todo = any(not todo.completed for todo in self.todos)  # 检查是否有未完成的待办事项

        status_text = f"倒计时: {'有' if has_timer else '无'}\n"
        status_text += f"闹钟: {'有' if has_alarm else '无'}\n"
        status_text += f"倒计日: {'有' if has_countdown else '无'}\n"
        status_text += f"秒表: {'运行中' if has_stopwatch else '停止'}\n"
        status_text += f"待办事项: {'有' if has_todo else '无'}"

        status_label = tk.Label(small_window, text=status_text)
        status_label.pack(pady=10)

        main_window_btn = ttk.Button(small_window, text="主界面", command=lambda: self.show_main_window(small_window))
        main_window_btn.pack(pady=10)

    def show_main_window(self, small_window):
        small_window.destroy()
        self.root.deiconify()

    def on_close_small_window(self):
        result = messagebox.askokcancel("确认关闭", "关闭程序后倒计时、秒表、倒计日、闹钟和待办事项将不能运行，程序无法提醒您。")
        if result:
            # 保存历史记录
            self.save_history()
            self.root.destroy()

    # 历史记录功能
    def save_history(self):
        """保存所有计时器、闹钟、倒计日、秒表和待办事项的历史记录"""
        history_data = {
            "timers": [timer.to_dict() for timer in self.timers],
            "alarms": [alarm.to_dict() for alarm in self.alarms],
            "countdowns": [countdown.to_dict() for countdown in self.countdowns],
            "stopwatch": self.stopwatch.to_dict(),
            "todos": [todo.to_dict() for todo in self.todos],
            "current_month": self.current_month,
            "current_year": self.current_year
        }
        
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history_data, f, indent=4)
        except Exception as e:
            print(f"保存历史记录失败: {e}")

    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history_data = json.load(f)
                
                # 加载计时器
                self.timers = []
                for timer_data in history_data.get("timers", []):
                    timer = CountdownTimer.from_dict(timer_data)
                    self.timers.append(timer)
                
                # 加载闹钟
                self.alarms = []
                for alarm_data in history_data.get("alarms", []):
                    alarm = Alarm.from_dict(alarm_data)
                    self.alarms.append(alarm)
                
                # 加载倒计日
                self.countdowns = []
                for countdown_data in history_data.get("countdowns", []):
                    countdown = Countdown.from_dict(countdown_data)
                    self.countdowns.append(countdown)
                
                # 加载秒表
                if "stopwatch" in history_data:
                    self.stopwatch = Stopwatch.from_dict(history_data["stopwatch"])
                    # 调整开始时间
                    if self.stopwatch.running:
                        self.stopwatch.start_time = time.time() - self.stopwatch.elapsed_time
                
                # 加载待办事项
                self.todos = []
                for todo_data in history_data.get("todos", []):
                    todo = TodoItem.from_dict(todo_data)
                    self.todos.append(todo)
                
                # 加载日历状态
                self.current_month = history_data.get("current_month", datetime.now().month)
                self.current_year = history_data.get("current_year", datetime.now().year)
                
            except Exception as e:
                print(f"加载历史记录失败: {e}")

    def show_history_window(self):
        """显示历史记录窗口"""
        history_window = tk.Toplevel(self.root)
        history_window.title("历史记录")
        history_window.geometry("700x500")
        
        # 创建标签页
        notebook = ttk.Notebook(history_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 倒计时历史
        timer_frame = ttk.Frame(notebook)
        notebook.add(timer_frame, text="倒计时")
        
        # 添加隐藏索引列
        columns = ('index', 'name', 'time', 'status')
        timer_tree = ttk.Treeview(timer_frame, columns=columns, show='headings')
        timer_tree.column('index', width=0, stretch=False)  # 隐藏索引列
        timer_tree.heading('name', text='名称')
        timer_tree.heading('time', text='剩余时间')
        timer_tree.heading('status', text='状态')
        timer_tree.pack(fill='both', expand=True, side=tk.LEFT)
        
        # 填充数据时记录索引
        for index, timer in enumerate(self.timers):
            remaining = timer.remaining_time().total_seconds()
            if remaining <= 0:
                status = "已结束"
                time_str = "00:00"
            else:
                status = "进行中"
                mins, secs = divmod(int(remaining), 60)
                time_str = f"{mins:02d}:{secs:02d}"
            timer_tree.insert("", tk.END, values=(index, timer.name, time_str, status))
        
        # 闹钟历史
        alarm_frame = ttk.Frame(notebook)
        notebook.add(alarm_frame, text="闹钟")
        
        columns = ('index', 'name', 'time', 'repeat', 'status')
        alarm_tree = ttk.Treeview(alarm_frame, columns=columns, show='headings')
        alarm_tree.column('index', width=0, stretch=False)
        alarm_tree.heading('name', text='名称')
        alarm_tree.heading('time', text='闹钟时间')
        alarm_tree.heading('repeat', text='重复')
        alarm_tree.heading('status', text='状态')
        alarm_tree.pack(fill='both', expand=True, side=tk.LEFT)
        
        # 填充数据
        repeat_text = {"once": "不重复", "daily": "每天", "weekend": "仅周末"}
        for index, alarm in enumerate(self.alarms):
            status = "开启" if alarm.active else "关闭"
            time_str = alarm.alarm_time.strftime("%H:%M")
            alarm_tree.insert("", tk.END, values=(index, alarm.name, time_str, repeat_text[alarm.repeat], status))
        
        # 倒计日历史
        countdown_frame = ttk.Frame(notebook)
        notebook.add(countdown_frame, text="倒计日")
        
        columns = ('index', 'name', 'days', 'date')
        countdown_tree = ttk.Treeview(countdown_frame, columns=columns, show='headings')
        countdown_tree.column('index', width=0, stretch=False)
        countdown_tree.heading('name', text='名称')
        countdown_tree.heading('days', text='剩余天数')
        countdown_tree.heading('date', text='目标日期')
        countdown_tree.pack(fill='both', expand=True, side=tk.LEFT)
        
        # 填充数据
        now = datetime.now().date()
        for index, countdown in enumerate(self.countdowns):
            target_date = countdown.target_date.date()
            delta = (target_date - now).days
            status = f"剩余 {delta} 天" if delta >=0 else f"已过期 {-delta} 天"
            countdown_tree.insert("", tk.END, values=(index, countdown.name, status, target_date.strftime("%Y-%m-%d")))
        
        # 秒表历史
        stopwatch_frame = ttk.Frame(notebook)
        notebook.add(stopwatch_frame, text="秒表")
        
        stopwatch_label = tk.Label(stopwatch_frame, text="秒表状态", font=('Helvetica', 24))
        stopwatch_label.pack(pady=20)
        
        stopwatch_time_label = tk.Label(stopwatch_frame, text="00:00.00", font=('Helvetica', 36))
        stopwatch_time_label.pack(pady=10)
        
        def update_stopwatch_display():
            minutes, seconds = divmod(int(self.stopwatch.elapsed_time), 60)
            milliseconds = int((self.stopwatch.elapsed_time - int(self.stopwatch.elapsed_time)) * 100)
            stopwatch_time_label.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
            if self.stopwatch.running:
                stopwatch_label.config(text="秒表状态: 运行中")
                stopwatch_frame.after(10, update_stopwatch_display)
            else:
                stopwatch_label.config(text="秒表状态: 已暂停")
        
        update_stopwatch_display()
        
        # 待办事项历史
        todo_frame = ttk.Frame(notebook)
        notebook.add(todo_frame, text="待办事项")
        
        columns = ('index', 'title', 'start', 'end', 'status')
        todo_tree = ttk.Treeview(todo_frame, columns=columns, show='headings')
        todo_tree.column('index', width=0, stretch=False)
        todo_tree.heading('title', text='标题')
        todo_tree.heading('start', text='开始时间')
        todo_tree.heading('end', text='结束时间')
        todo_tree.heading('status', text='状态')
        todo_tree.pack(fill='both', expand=True, side=tk.LEFT)
        
        # 填充数据
        for index, todo in enumerate(self.todos):
            start_str = todo.start_time.strftime("%Y-%m-%d %H:%M") if todo.start_time else "无"
            end_str = todo.end_time.strftime("%Y-%m-%d %H:%M") if todo.end_time else "无"
            status = "已完成" if todo.completed else "进行中"
            if todo.start_time and datetime.now() < todo.start_time:
                status = "未开始"
            todo_tree.insert("", tk.END, values=(index, todo.title, start_str, end_str, status))
        
        # 控制按钮
        btn_frame = ttk.Frame(history_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="继续选中", command=lambda: self.resume_selected(notebook)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中", command=lambda: self.delete_selected_history(notebook)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=history_window.destroy).pack(side=tk.LEFT, padx=5)

    def resume_selected(self, notebook):
        """继续选中的历史记录项"""
        current_tab = notebook.index(notebook.select())
        tree = notebook.nametowidget(notebook.select()).winfo_children()[0]
        selection = tree.selection()
        
        if not selection:
            return
        
        selected_item = selection[0]
        index = int(tree.item(selected_item, 'values')[0])  # 获取隐藏的索引
        
        if current_tab == 0:  # 倒计时
            if 0 <= index < len(self.timers):
                self.timers[index].running = True
                self.update_timer_list()
        elif current_tab == 1:  # 闹钟
            if 0 <= index < len(self.alarms):
                self.alarms[index].active = True
                self.update_alarm_list()
        elif current_tab == 3:  # 秒表
            self.start_stopwatch()
        elif current_tab == 4:  # 待办事项
            if 0 <= index < len(self.todos):
                self.todos[index].completed = False
                self.update_todo_list()

    def delete_selected_history(self, notebook):
        """删除选中的历史记录项"""
        current_tab = notebook.index(notebook.select())
        tree = notebook.nametowidget(notebook.select()).winfo_children()[0]
        selection = tree.selection()
        
        if not selection:
            return
        
        selected_item = selection[0]
        index = int(tree.item(selected_item, 'values')[0])
        
        if current_tab == 0:  # 倒计时
            if 0 <= index < len(self.timers):
                del self.timers[index]
        elif current_tab == 1:  # 闹钟
            if 0 <= index < len(self.alarms):
                del self.alarms[index]
        elif current_tab == 2:  # 倒计日
            if 0 <= index < len(self.countdowns):
                del self.countdowns[index]
        elif current_tab == 4:  # 待办事项
            if 0 <= index < len(self.todos):
                del self.todos[index]
        
        tree.delete(selected_item)  # 刷新显示

if __name__ == "__main__":
    root = tk.Tk()
    app = ClockApp(root)
    root.mainloop()