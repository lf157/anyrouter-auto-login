#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnyRouter 自动登录工具 - GUI版本
支持浏览器选择、定时任务、账号管理等功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import threading
import time
from datetime import datetime, timedelta
import sys
import subprocess
from playwright.sync_api import sync_playwright
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

class AnyRouterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AnyRouter 自动登录工具 v2.0")
        self.root.geometry("1000x800")  # 增大窗口尺寸
        self.root.resizable(True, True)

        # 设置最小窗口尺寸
        self.root.minsize(900, 700)

        # 设置窗口图标和样式
        self.root.configure(bg='#f0f0f0')

        # 设置全局字体和颜色
        self.setup_styles()
        
        # 数据存储
        self.accounts = []
        self.config_file = "config.json"
        self.log_file = "login_log.txt"
        self.accounts_file = "accounts.txt"  # 账号文件
        self.running = False
        self.paused = False  # 暂停状态
        self.pause_event = threading.Event()  # 用于暂停/继续控制
        self.pause_event.set()  # 初始化为非暂停状态
        self.selected_accounts = {}  # 存储选中状态
        self.sort_column = None  # 当前排序列
        self.sort_reverse = False  # 排序方向
        
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 检测浏览器
        self.detect_browsers()

        # 初始化日志
        self.init_log()
        
        # 刷新账号列表显示
        self.refresh_account_list()

        # 检查是否需要导入账号文件
        if not self.accounts and os.path.exists(self.accounts_file):
            self.root.after(500, lambda: self.ask_import_on_startup())

    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()

        # 设置主题
        style.theme_use('clam')

        # 专业色彩系统
        style.configure('Title.TLabel', font=('Microsoft YaHei', 20, 'bold'), foreground='#1976D2')
        style.configure('Heading.TLabel', font=('Microsoft YaHei', 11, 'bold'), foreground='#424242')
        style.configure('Info.TLabel', font=('Microsoft YaHei', 10), foreground='#757575')
        style.configure('Status.TLabel', font=('Microsoft YaHei', 10, 'bold'))

        # 主要操作按钮（高优先级）
        style.configure('Action.TButton',
                       font=('Microsoft YaHei', 11, 'bold'),
                       padding=(20, 12))
        style.map('Action.TButton',
                  background=[('active', '#1976D2'), ('!active', '#2196F3')],
                  foreground=[('active', 'white'), ('!active', 'white')])

        # 成功操作按钮
        style.configure('Success.TButton',
                       font=('Microsoft YaHei', 10, 'bold'),
                       padding=(15, 8))
        style.map('Success.TButton',
                  background=[('active', '#388E3C'), ('!active', '#4CAF50')],
                  foreground=[('active', 'white'), ('!active', 'white')])

        # 警告操作按钮
        style.configure('Warning.TButton',
                       font=('Microsoft YaHei', 10),
                       padding=(12, 8))
        style.map('Warning.TButton',
                  background=[('active', '#F57C00'), ('!active', '#FF9800')],
                  foreground=[('active', 'white'), ('!active', 'white')])

        # 危险操作按钮
        style.configure('Danger.TButton',
                       font=('Microsoft YaHei', 10),
                       padding=(12, 8))
        style.map('Danger.TButton',
                  background=[('active', '#D32F2F'), ('!active', '#F44336')],
                  foreground=[('active', 'white'), ('!active', 'white')])

        # 辅助操作按钮
        style.configure('Secondary.TButton',
                       font=('Microsoft YaHei', 9),
                       padding=(10, 6))
        style.map('Secondary.TButton',
                  background=[('active', '#616161'), ('!active', '#757575')],
                  foreground=[('active', 'white'), ('!active', 'white')])

        # 精致卡片样式
        style.configure('Card.TLabelframe',
                       relief='flat',
                       borderwidth=1,
                       background='#FAFAFA')
        style.configure('Card.TLabelframe.Label',
                       font=('Microsoft YaHei', 12, 'bold'),
                       foreground='#1976D2',
                       background='#FAFAFA')

        # 优化Treeview样式
        style.configure('Modern.Treeview',
                       font=('Microsoft YaHei', 10),
                       rowheight=30,
                       background='white',
                       fieldbackground='white')
        style.configure('Modern.Treeview.Heading',
                       font=('Microsoft YaHei', 10, 'bold'),
                       background='#E3F2FD',
                       foreground='#1976D2')
        style.map('Modern.Treeview',
                  background=[('selected', '#2196F3')],
                  foreground=[('selected', 'white')])

        # 进度条样式
        style.configure('Modern.Horizontal.TProgressbar',
                       troughcolor='#E0E0E0',
                       background='#2196F3',
                       lightcolor='#2196F3',
                       darkcolor='#2196F3')

        # 现代化组合框样式
        style.configure('Modern.TCombobox',
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid')
        style.map('Modern.TCombobox',
                  fieldbackground=[('readonly', '#F5F5F5')],
                  bordercolor=[('focus', '#2196F3')])

        # 复选框样式优化
        style.configure('Modern.TCheckbutton',
                       font=('Microsoft YaHei', 10),
                       focuscolor='none')
        style.map('Modern.TCheckbutton',
                  background=[('active', '#E3F2FD')])

        # 输入框样式
        style.configure('Modern.TEntry',
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid')
        style.map('Modern.TEntry',
                  bordercolor=[('focus', '#2196F3')])
    
    def create_widgets(self):
        """创建界面组件"""
        # --- 创建可滚动区域 ---
        # 1. 创建一个外部容器来容纳Canvas和Scrollbar
        container = ttk.Frame(self.root)
        container.grid(row=0, column=0, sticky='nsew')
        
        # 2. 配置主窗口和容器的grid权重，确保它们能随窗口缩放
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # 3. 创建Canvas和Scrollbar
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 4. 创建一个Frame在Canvas内部，所有控件都将放在这个Frame里
        main_frame = ttk.Frame(canvas, padding="15")
        
        # 5. 将这个Frame添加到Canvas的窗口中，并设置宽度填充
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        # 6. 绑定Canvas大小变化事件，让main_frame宽度跟随Canvas
        def on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig(canvas.find_all()[0], width=canvas_width)
        canvas.bind('<Configure>', on_canvas_configure)

        # 7. 绑定事件，当内部Frame的大小改变时，自动更新Canvas的滚动区域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main_frame.bind("<Configure>", on_frame_configure)

        # 8. 绑定鼠标滚轮事件，让鼠标滚轮可以控制滚动
        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mouse_wheel)

        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)

        # 设置主框架的行权重，让账号管理区域和日志区域可以扩展
        main_frame.rowconfigure(2, weight=2)  # 账号管理区域
        main_frame.rowconfigure(4, weight=1)  # 日志区域

        # 精美标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # 主标题
        title_label = ttk.Label(title_frame, text="🚀 AnyRouter 自动登录工具", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # 状态信息
        status_frame = ttk.Frame(title_frame)
        status_frame.pack(side=tk.RIGHT)

        version_label = ttk.Label(status_frame, text="v2.0", style='Info.TLabel')
        version_label.pack(side=tk.TOP)

        self.connection_status = ttk.Label(status_frame, text="🟢 就绪", style='Status.TLabel', foreground='#4CAF50')
        self.connection_status.pack(side=tk.TOP)
        
        # 浏览器设置区域
        browser_frame = ttk.LabelFrame(main_frame, text="🌐 浏览器配置", padding="12", style='Card.TLabelframe')
        browser_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        browser_frame.columnconfigure(1, weight=1)

        ttk.Label(browser_frame, text="选择浏览器:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.browser_var = tk.StringVar()
        self.browser_combo = ttk.Combobox(browser_frame, textvariable=self.browser_var,
                                         state="readonly", width=30, style='Modern.TCombobox')
        self.browser_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_frame, text="无头模式 (后台运行)",
                       variable=self.headless_var, style='Modern.TCheckbutton').grid(row=0, column=2, padx=(10, 0))

        # 并发数量选择
        ttk.Label(browser_frame, text="并发数量:", style='Heading.TLabel').grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.concurrency_var = tk.StringVar(value="2")
        concurrency_combo = ttk.Combobox(browser_frame, textvariable=self.concurrency_var,
                                        values=["1", "2", "3", "4", "5"],
                                        state="readonly", width=10, style='Modern.TCombobox')
        concurrency_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(8, 0))
        concurrency_combo.current(1)  # 默认选择2
        ttk.Label(browser_frame, text="(同时运行的浏览器数量)", style='Info.TLabel').grid(row=1, column=2, padx=(10, 0), pady=(8, 0))
        
        # 账号管理区域
        account_frame = ttk.LabelFrame(main_frame, text="👥 账号管理", padding="12", style='Card.TLabelframe')
        account_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        account_frame.columnconfigure(0, weight=1)
        account_frame.rowconfigure(1, weight=1)

        # 账号数量显示
        count_frame = ttk.Frame(account_frame)
        count_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

        self.account_count_label = ttk.Label(count_frame,
                                            text="📃 总账号: 0 | ☑ 已选中: 0",
                                            font=('Microsoft YaHei', 11, 'bold'),
                                            foreground='#1976D2')
        self.account_count_label.pack(side=tk.LEFT)
        
        # 账号列表
        list_frame = ttk.Frame(account_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.account_tree = ttk.Treeview(list_frame, columns=("check", "username", "status", "balance"),
                                        show="tree headings", height=6, style='Modern.Treeview')
        self.account_tree.heading("#0", text="选择")
        self.account_tree.heading("check", text="")
        self.account_tree.heading("username", text="用户名")
        self.account_tree.heading("status", text="状态")
        self.account_tree.heading("balance", text="余额信息")
        self.account_tree.column("#0", width=50)
        self.account_tree.column("check", width=0, stretch=False)
        self.account_tree.column("username", width=200)
        self.account_tree.column("status", width=100)
        self.account_tree.column("balance", width=250)

        # 配置状态颜色标签（增强视觉效果）
        self.account_tree.tag_configure('success', foreground='#4CAF50', font=('Microsoft YaHei', 10, 'bold'))
        self.account_tree.tag_configure('failure', foreground='#F44336', font=('Microsoft YaHei', 10, 'bold'))
        self.account_tree.tag_configure('pending', foreground='#757575', font=('Microsoft YaHei', 10))
        self.account_tree.tag_configure('selected_row', background='#E3F2FD')

        # 初始化拖拽数据
        self.drag_data = {"item": None, "x": 0, "y": 0}

        # 绑定事件 - 注意顺序很重要
        # 先绑定勾选事件
        self.account_tree.bind("<ButtonPress-1>", self.on_click)
        # 再绑定拖拽事件
        self.account_tree.bind("<B1-Motion>", self.on_drag_motion)
        self.account_tree.bind("<ButtonRelease-1>", self.on_drag_release)

        # 绑定标题点击事件用于排序
        self.account_tree.heading("username", command=lambda: self.sort_accounts("username"))
        self.account_tree.heading("status", command=lambda: self.sort_accounts("status"))
        self.account_tree.heading("balance", command=lambda: self.sort_accounts("balance"))
        
        # 滚动条
        account_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.account_tree.yview)
        self.account_tree.configure(yscrollcommand=account_scrollbar.set)

        self.account_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        account_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 操作按钮组 - 水平紧凑布局
        buttons_container = ttk.Frame(account_frame)
        buttons_container.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(8, 0))

        # 第一行按钮
        row1_frame = ttk.Frame(buttons_container)
        row1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 4))

        ttk.Button(row1_frame, text="📁 导入", command=self.import_from_file, style='Success.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="➕ 添加", command=self.add_account, style='Success.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="✏️ 编辑", command=self.edit_account, style='Warning.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="🗑️ 删除", command=self.delete_account, style='Danger.TButton').pack(side=tk.LEFT, padx=(0, 15))

        ttk.Button(row1_frame, text="☑ 全选", command=self.select_all, style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(row1_frame, text="☒ 反选", command=self.invert_selection, style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(row1_frame, text="☐ 清空", command=self.unselect_all, style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 4))

        # 第二行按钮
        row2_frame = ttk.Frame(buttons_container)
        row2_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        ttk.Label(row2_frame, text="📊 排序:", style='Heading.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row2_frame, text="用户名", command=lambda: self.sort_accounts("username"), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(row2_frame, text="状态", command=lambda: self.sort_accounts("status"), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(row2_frame, text="余额", command=lambda: self.sort_accounts("balance"), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(row2_frame, text="重置", command=self.reset_order, style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 执行控制区域（调整行号）
        control_frame = ttk.LabelFrame(main_frame, text="🎯 执行控制", padding="12", style='Card.TLabelframe')
        control_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 主要操作按钮行
        main_btn_frame = ttk.Frame(control_frame)
        main_btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

        self.start_btn = ttk.Button(main_btn_frame, text="🚀 立即执行", command=self.start_login, style='Action.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.pause_btn = ttk.Button(main_btn_frame, text="⏸ 暂停", command=self.toggle_pause, state=tk.DISABLED, style='Warning.TButton')
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(main_btn_frame, text="⏹ 停止", command=self.stop_login, state=tk.DISABLED, style='Danger.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 20))

        # 辅助操作按钮
        ttk.Button(main_btn_frame, text="📊 刷新", command=self.refresh_accounts, style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(main_btn_frame, text="📄 日志", command=self.view_log_file, style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(main_btn_frame, text="⚙️ 设置", command=self.open_settings, style='Secondary.TButton').pack(side=tk.LEFT)

        # 进度显示
        progress_frame = ttk.Frame(control_frame)
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        progress_frame.columnconfigure(1, weight=1)

        self.progress_label = ttk.Label(progress_frame, text="进度:", style='Heading.TLabel')
        self.progress_label.grid(row=0, column=0, padx=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100,
                                          style='Modern.Horizontal.TProgressbar', length=300)
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

        self.progress_percent = ttk.Label(progress_frame, text="0%", style='Status.TLabel', foreground='#1976D2')
        self.progress_percent.grid(row=0, column=2)
        
        # 日志区域（调整行号）
        log_frame = ttk.LabelFrame(main_frame, text="📝 执行日志", padding="10", style='Card.TLabelframe')
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # 删除重复的行权重设置
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED,
                                                  font=('Consolas', 9), bg='#263238', fg='#ECEFF1',
                                                  insertbackground='#4CAF50', selectbackground='#37474F')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def detect_browsers(self):
        """检测可用的浏览器"""
        browsers = []
        
        # 检测Chrome
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, channel="chrome")
                browser.close()
            browsers.append(("chrome", "Google Chrome"))
        except:
            pass
        
        # 检测Edge
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, channel="msedge")
                browser.close()
            browsers.append(("msedge", "Microsoft Edge"))
        except:
            pass
        
        # 检测Firefox
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=True)
                browser.close()
            browsers.append(("firefox", "Mozilla Firefox"))
        except:
            pass
        
        # 更新组合框
        if browsers:
            browser_names = [name for _, name in browsers]
            self.browser_combo['values'] = browser_names
            self.browser_combo.current(0)  # 默认选择第一个
            self.browser_channels = {name: channel for channel, name in browsers}
        else:
            messagebox.showerror("错误", "未检测到支持的浏览器！\n请安装 Chrome、Edge 或 Firefox。")
    
    def init_log(self):
        """初始化日志文件"""
        try:
            # 创建日志文件头
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"程序启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
        except Exception as e:
            print(f"初始化日志文件失败: {e}")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # 显示在界面上
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 保存到文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_message)
        except Exception as e:
            print(f"写入日志文件失败: {e}")
        
        # 强制刷新界面
        self.root.update_idletasks()
    
    def add_account(self):
        """添加账号对话框"""
        dialog = AccountDialog(self.root, "添加账号")
        if dialog.result:
            username, password = dialog.result
            # 检查账号是否已存在
            for account in self.accounts:
                if account['username'] == username:
                    messagebox.showerror("错误", "账号已存在！")
                    return
            
            self.accounts.append({
                'username': username,
                'password': password,
                'status': '未登录',
                'balance_info': ''
            })
            self.refresh_account_list()
            self.save_config()
    
    def edit_account(self):
        """编辑选中的账号"""
        selected = self.account_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要编辑的账号！")
            return
        
        item = self.account_tree.item(selected[0])
        display_username = item['values'][1]  # 获取显示的用户名
        # 提取实际用户名（去掉👤前缀）
        username = display_username.replace("👤 ", "") if display_username.startswith("👤 ") else display_username
        
        # 找到账号数据
        account = None
        for acc in self.accounts:
            if acc['username'] == username:
                account = acc
                break
        
        if account:
            old_username = account['username']  # 保存旧用户名
            dialog = AccountDialog(self.root, "编辑账号", account['username'], account['password'])
            if dialog.result:
                new_username, new_password = dialog.result
                account['username'] = new_username
                account['password'] = new_password
                # 同时更新选中状态
                if old_username != new_username:
                    if old_username in self.selected_accounts:
                        self.selected_accounts[new_username] = self.selected_accounts[old_username]
                        del self.selected_accounts[old_username]
                self.refresh_account_list()
                self.save_config()
    
    def delete_account(self):
        """删除勾选的账号（仅从GUI中移除，不影响accounts.txt）"""
        # 获取所有勾选的账号
        selected_usernames = [acc['username'] for acc in self.accounts
                            if self.selected_accounts.get(acc['username'], False)]

        if not selected_usernames:
            messagebox.showwarning("警告", "请先勾选要删除的账号！")
            return

        # 构建确认消息
        if len(selected_usernames) == 1:
            confirm_msg = f"确定要从当前列表中移除账号 {selected_usernames[0]} 吗？"
        else:
            confirm_msg = f"确定要从当前列表中移除以下 {len(selected_usernames)} 个账号吗？\n\n"
            # 显示前5个账号
            for i, username in enumerate(selected_usernames[:5]):
                confirm_msg += f"• {username}\n"
            if len(selected_usernames) > 5:
                confirm_msg += f"• ... 还有 {len(selected_usernames) - 5} 个账号\n"

        confirm_msg += "\n注意：这不会影响 accounts.txt 文件"

        if messagebox.askyesno("确认", confirm_msg):
            # 从列表中移除所有勾选的账号
            self.accounts = [acc for acc in self.accounts
                           if not self.selected_accounts.get(acc['username'], False)]

            # 清理选中状态字典
            for username in selected_usernames:
                if username in self.selected_accounts:
                    del self.selected_accounts[username]

            self.refresh_account_list()
            self.save_config()

            if len(selected_usernames) == 1:
                self.log_message(f"✅ 已从列表中移除账号: {selected_usernames[0]}")
            else:
                self.log_message(f"✅ 已从列表中移除 {len(selected_usernames)} 个账号")
    
    def import_accounts(self):
        """从auto_optimized.py导入账号"""
        try:
            # 尝试从auto_optimized.py读取账号
            if os.path.exists('auto_optimized.py'):
                with open('auto_optimized.py', 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 简单的正则匹配来提取账号信息
                import re
                pattern = r"{'username':\s*'([^']+)',\s*'password':\s*'([^']+)'}"
                matches = re.findall(pattern, content)
                
                imported_count = 0
                for username, password in matches:
                    # 检查是否已存在
                    exists = any(acc['username'] == username for acc in self.accounts)
                    if not exists:
                        self.accounts.append({
                            'username': username,
                            'password': password,
                            'status': '未登录',
                            'balance_info': ''
                        })
                        imported_count += 1
                
                if imported_count > 0:
                    self.refresh_account_list()
                    self.save_config()
                    messagebox.showinfo("成功", f"成功导入 {imported_count} 个账号！")
                else:
                    messagebox.showinfo("提示", "没有新账号需要导入。")
            else:
                messagebox.showerror("错误", "未找到 auto_optimized.py 文件！")
        except Exception as e:
            messagebox.showerror("错误", f"导入账号失败：{str(e)}")
    
    def sort_accounts(self, column):
        """排序账号列表"""
        # 如果点击同一列，切换排序方向
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        # 根据不同列进行排序
        if column == "username":
            self.accounts.sort(key=lambda x: x['username'].lower(), reverse=self.sort_reverse)
        elif column == "status":
            # 状态排序优先级：成功 > 失败 > 未登录
            status_order = {'✅ 登录成功': 0, '❌ 登录失败': 1, '❌ 执行错误': 1, '未登录': 2}
            self.accounts.sort(
                key=lambda x: (status_order.get(x.get('status', '未登录'), 3), x['username']),
                reverse=self.sort_reverse
            )
        elif column == "balance":
            # 余额排序，提取数字进行比较
            def get_balance_value(account):
                balance = account.get('balance_info', '')
                import re
                # 提取第一个金额数字
                match = re.search(r'\$([0-9,]+\.?[0-9]*)', balance)
                if match:
                    return float(match.group(1).replace(',', ''))
                return 0

            self.accounts.sort(key=get_balance_value, reverse=self.sort_reverse)

        # 更新标题显示排序箭头
        for col in ["username", "status", "balance"]:
            if col == column:
                arrow = " ▼" if self.sort_reverse else " ▲"
                if col == "username":
                    self.account_tree.heading(col, text="用户名" + arrow)
                elif col == "status":
                    self.account_tree.heading(col, text="状态" + arrow)
                elif col == "balance":
                    self.account_tree.heading(col, text="余额信息" + arrow)
            else:
                if col == "username":
                    self.account_tree.heading(col, text="用户名")
                elif col == "status":
                    self.account_tree.heading(col, text="状态")
                elif col == "balance":
                    self.account_tree.heading(col, text="余额信息")

        self.refresh_account_list()
        column_names = {'username': '用户名', 'status': '状态', 'balance': '余额'}
        self.log_message(f"🔄 已按{column_names[column]}{'降序' if self.sort_reverse else '升序'}排序")

    def on_click(self, event):
        """处理点击事件 - 区分勾选和拖拽"""
        region = self.account_tree.identify("region", event.x, event.y)

        # 如果点击的是树形区域（勾选框）
        if region == "tree":
            item = self.account_tree.identify_row(event.y)
            if item:
                # 从显示文本中提取实际用户名（去掉👤前缀）
                display_username = self.account_tree.item(item)['values'][1]
                username = display_username.replace("👤 ", "") if display_username.startswith("👤 ") else display_username

                # 切换勾选状态
                if username in self.selected_accounts:
                    self.selected_accounts[username] = not self.selected_accounts[username]
                else:
                    self.selected_accounts[username] = True
                self.refresh_account_list()
                return "break"

        # 如果点击的是单元格区域，准备拖拽
        elif region == "cell" and event.x > 60:  # 勾选框在前60像素
            item = self.account_tree.identify_row(event.y)
            if item:
                self.drag_data["item"] = item
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                self.account_tree.selection_set(item)

    def ask_import_on_startup(self):
        """启动时询问是否导入账号"""
        response = messagebox.askyesno("提示", f"检测到 {self.accounts_file} 文件，是否立即导入账号？")
        if response:
            self.import_from_file()


    def on_drag_motion(self, event):
        """拖拽中"""
        if self.drag_data["item"]:
            # 显示拖拽指示器
            target_item = self.account_tree.identify_row(event.y)
            if target_item and target_item != self.drag_data["item"]:
                # 高亮目标位置
                self.account_tree.selection_set(target_item)

    def on_drag_release(self, event):
        """结束拖拽"""
        if self.drag_data["item"]:
            target_item = self.account_tree.identify_row(event.y)
            if target_item and target_item != self.drag_data["item"]:
                # 获取源和目标的索引
                source_index = self.account_tree.index(self.drag_data["item"])
                target_index = self.account_tree.index(target_item)

                # 重新排序账号列表
                account_to_move = self.accounts.pop(source_index)
                self.accounts.insert(target_index, account_to_move)

                # 刷新显示
                self.refresh_account_list()
                self.save_config()
                self.log_message(f"🔄 已调整账号顺序: {account_to_move['username']} 移动到位置 {target_index + 1}")

            # 重置拖拽数据
            self.drag_data = {"item": None, "x": 0, "y": 0}

    def reset_order(self):
        """重置账号顺序为导入时的顺序"""
        # 按用户名字母顺序排序
        self.accounts.sort(key=lambda x: x['username'].lower())
        self.sort_column = None
        self.sort_reverse = False

        # 重置所有列标题
        self.account_tree.heading("username", text="用户名")
        self.account_tree.heading("status", text="状态")
        self.account_tree.heading("balance", text="余额信息")

        self.refresh_account_list()
        self.save_config()
        self.log_message("🔀 已重置账号顺序")


    def unselect_all(self):
        """取消全选所有账号"""
        for account in self.accounts:
            self.selected_accounts[account['username']] = False
        self.refresh_account_list()
        self.log_message("☐ 已取消全部选择")

    def select_all(self):
        """全选所有账号"""
        for account in self.accounts:
            self.selected_accounts[account['username']] = True
        self.refresh_account_list()
        self.log_message("☑ 已全选所有账号")

    def invert_selection(self):
        """反选账号"""
        for account in self.accounts:
            username = account['username']
            self.selected_accounts[username] = not self.selected_accounts.get(username, False)
        self.refresh_account_list()
        self.log_message("☒ 已反选账号")

    def import_from_file(self):
        """从 accounts.txt 文件导入账号"""
        try:
            if not os.path.exists(self.accounts_file):
                messagebox.showerror("错误", f"账号文件 {self.accounts_file} 不存在！")
                return

            imported_count = 0
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue

                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            username = parts[0].strip()
                            password = parts[1].strip()

                            # 检查是否已存在
                            exists = any(acc['username'] == username for acc in self.accounts)
                            if not exists and username and password:
                                self.accounts.append({
                                    'username': username,
                                    'password': password,
                                    'status': '未登录',
                                    'balance_info': ''
                                })
                                self.selected_accounts[username] = True  # 默认选中
                                imported_count += 1

            if imported_count > 0:
                self.refresh_account_list()
                self.save_config()
                messagebox.showinfo("成功", f"成功从 {self.accounts_file} 导入 {imported_count} 个账号！")
            else:
                messagebox.showinfo("提示", "没有新账号需要导入。")

        except Exception as e:
            messagebox.showerror("错误", f"导入账号失败：{str(e)}")

    def refresh_account_list(self):
        """刷新账号列表显示"""
        # 清空现有项目
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)

        # 统计勾选数量
        total_count = len(self.accounts)
        selected_count = sum(1 for acc in self.accounts
                           if self.selected_accounts.get(acc['username'], True))

        # 更新账号数量显示
        if hasattr(self, 'account_count_label'):
            self.account_count_label.config(
                text=f"📃 总账号: {total_count} | ☑ 已选中: {selected_count}"
            )

        # 添加账号
        for account in self.accounts:
            username = account['username']
            # 勾选状态显示（美化图标）
            check_status = "✅" if self.selected_accounts.get(username, True) else "⬜"

            # 根据状态决定颜色标签和图标
            status = account.get('status', '未登录')
            if status == '✅ 登录成功':
                tag = 'success'
                status_icon = "🟢"
            elif status in ['❌ 登录失败', '❌ 执行错误']:
                tag = 'failure'
                status_icon = "🔴"
            else:
                tag = 'pending'
                status_icon = "⚪"

            # 余额信息美化
            balance_info = account.get('balance_info', '')
            if balance_info and '$' in balance_info:
                balance_display = f"💰 {balance_info}"
            else:
                balance_display = balance_info or "💭 暂无数据"

            item = self.account_tree.insert("", tk.END, text=check_status, values=(
                "",  # 隐藏列
                f"👤 {account['username']}",
                f"{status_icon} {status}",
                balance_display
            ), tags=(tag,))
    
    def refresh_accounts(self):
        """刷新账号状态"""
        self.log_message("正在刷新账号状态...")
        # 这里可以实现快速检查账号状态的逻辑
        self.log_message("账号状态刷新完成")
    
    
    def toggle_pause(self):
        """切换暂停/继续状态"""
        if self.paused:
            # 继续
            self.paused = False
            self.pause_event.set()
            self.pause_btn.config(text="⏸ 暂停")
            self.log_message("▶️ 继续执行")
        else:
            # 暂停
            self.paused = True
            self.pause_event.clear()
            self.pause_btn.config(text="▶️ 继续")
            self.log_message("⏸ 已暂停")

    def start_login(self):
        """开始登录过程"""
        # 获取选中的账号
        selected = [acc for acc in self.accounts if self.selected_accounts.get(acc['username'], True)]

        if not selected:
            messagebox.showwarning("警告", "请至少选择一个账号！")
            return

        if self.running:
            messagebox.showwarning("警告", "任务正在执行中！")
            return
        
        # 检查浏览器选择
        if not self.browser_var.get():
            messagebox.showerror("错误", "请选择浏览器！")
            return
        
        self.running = True
        self.paused = False
        self.pause_event.set()  # 确保不在暂停状态
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL, text="⏸ 暂停")
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)

        # 将选中的账号传递给工作线程
        self.selected_for_login = selected

        # 在新线程中执行登录
        login_thread = threading.Thread(target=self.login_worker, daemon=True)
        login_thread.start()
    
    def stop_login(self):
        """停止登录过程"""
        self.running = False
        self.paused = False
        self.pause_event.set()  # 解除暂停，以便线程可以退出
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="⏸ 暂停")
        self.stop_btn.config(state=tk.DISABLED)
        self.log_message("❌ 用户停止了执行")
    
    def login_worker(self):
        """登录工作线程"""
        try:
            browser_name = self.browser_var.get()
            browser_channel = self.browser_channels.get(browser_name, "chrome")
            headless = self.headless_var.get()
            concurrency = int(self.concurrency_var.get())

            # 使用选中的账号
            accounts_to_process = getattr(self, 'selected_for_login', self.accounts)
            actual_accounts = len(accounts_to_process)

            # 智能调整并发数：不超过实际账号数量
            actual_concurrency = min(concurrency, actual_accounts)

            self.log_message(f"🚀 开始执行自动登录，使用浏览器: {browser_name}")
            if actual_accounts < concurrency and concurrency > 1:
                self.log_message(f"📌 账号数量({actual_accounts})少于并发设置({concurrency})，自动调整为{actual_concurrency}")
            elif actual_concurrency > 1:
                self.log_message(f"🔄 并发数量: {actual_concurrency}")
            self.log_message("=" * 50)

            if actual_concurrency == 1:
                # 串行执行
                self.serial_login(browser_channel, headless)
            else:
                # 并发执行，使用调整后的并发数
                self.concurrent_login(browser_channel, headless, actual_concurrency)

        except Exception as e:
            self.log_message(f"❌ 执行过程中出现错误: {str(e)}")

        finally:
            self.running = False
            self.paused = False
            self.pause_event.set()
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.pause_btn.config(state=tk.DISABLED, text="⏸ 暂停"))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def serial_login(self, browser_channel, headless):
        """串行执行 (原有逻辑)"""
        accounts_to_process = getattr(self, 'selected_for_login', self.accounts)
        total_accounts = len(accounts_to_process)
        success_count = 0

        for i, account in enumerate(accounts_to_process):
            if not self.running:
                break

            self.log_message(f"📋 处理账号 {i+1}/{total_accounts}: {account['username']}")

            # 更新进度
            progress = (i / total_accounts) * 100
            self.progress_var.set(progress)

            try:
                # 执行登录
                result = self.login_account(account, browser_channel, headless)

                if result['success']:
                    account['status'] = '✅ 登录成功'
                    account['balance_info'] = result.get('balance_info', '')
                    success_count += 1
                    self.log_message(f"✅ 账号 {account['username']} 登录成功")
                    if result.get('balance_info'):
                        self.log_message(f"💰 {result['balance_info']}")
                else:
                    account['status'] = '❌ 登录失败'
                    account['balance_info'] = ''
                    self.log_message(f"❌ 账号 {account['username']} 登录失败")

            except Exception as e:
                account['status'] = '❌ 执行错误'
                account['balance_info'] = ''
                self.log_message(f"❌ 账号 {account['username']} 执行错误: {str(e)}")

            # 刷新界面
            self.root.after(0, self.refresh_account_list)

            # 账号间延迟
            if i < total_accounts - 1 and self.running:
                delay = random.randint(3, 7)
                self.log_message(f"⏰ 等待 {delay} 秒后处理下一个账号...")
                for _ in range(delay):
                    if not self.running:
                        break
                    # 检查暂停状态
                    self.pause_event.wait()
                    time.sleep(1)

        # 完成统计
        self.progress_var.set(100)
        self.root.after(0, lambda: self.progress_percent.config(text="100%"))
        self.log_message("=" * 50)
        self.log_message(f"📊 执行完成！成功: {success_count}/{total_accounts}")

    def concurrent_login(self, browser_channel, headless, max_workers):
        """并发登录处理"""
        accounts_to_process = getattr(self, 'selected_for_login', self.accounts)
        total_accounts = len(accounts_to_process)
        success_count = 0
        completed_count = 0

        self.log_message(f"⚡ 启动 {max_workers} 个并发浏览器...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_account = {}
            for i, account in enumerate(accounts_to_process):
                if not self.running:
                    break

                # 检查暂停状态
                if self.paused:
                    self.log_message("⏸ 正在暂停中，等待继续...")
                self.pause_event.wait()  # 如果暂停，在这里等待
                if not self.running:
                    break

                future = executor.submit(self.login_account, account, browser_channel, headless)
                future_to_account[future] = account

            # 收集结果
            for future in as_completed(future_to_account):
                if not self.running:
                    executor.shutdown(wait=False)
                    break

                account = future_to_account[future]
                completed_count += 1

                try:
                    result = future.result()

                    if result['success']:
                        account['status'] = '✅ 登录成功'
                        account['balance_info'] = result.get('balance_info', '')
                        success_count += 1
                        self.log_message(f"✅ [{completed_count}/{total_accounts}] 账号 {account['username']} 登录成功")
                        if result.get('balance_info'):
                            self.log_message(f"💰 {result['balance_info']}")
                    else:
                        account['status'] = '❌ 登录失败'
                        account['balance_info'] = ''
                        self.log_message(f"❌ [{completed_count}/{total_accounts}] 账号 {account['username']} 登录失败")

                except Exception as e:
                    account['status'] = '❌ 执行错误'
                    account['balance_info'] = ''
                    self.log_message(f"❌ [{completed_count}/{total_accounts}] 账号 {account['username']} 执行错误: {str(e)}")

                # 更新进度
                progress = (completed_count / total_accounts) * 100
                self.progress_var.set(progress)

                # 刷新界面
                self.root.after(0, self.refresh_account_list)

        # 完成统计
        self.progress_var.set(100)
        self.root.after(0, lambda: self.progress_percent.config(text="100%"))
        self.log_message("=" * 50)
        self.log_message(f"📊 并发执行完成！成功: {success_count}/{total_accounts}")
    
    def login_account(self, account, browser_channel, headless):
        """登录单个账号 - 复用auto_optimized.py的逻辑"""
        balance_info = None
        
        try:
            with sync_playwright() as p:
                # 根据浏览器类型启动
                if browser_channel == "firefox":
                    browser = p.firefox.launch(headless=headless)
                else:
                    browser = p.chromium.launch(
                        headless=headless,
                        channel=browser_channel,
                        args=['--disable-gpu', '--no-sandbox', '--disable-setuid-sandbox']
                    )
                
                page = browser.new_page()
                
                # 访问登录页面
                page.goto('https://anyrouter.top/login', wait_until='domcontentloaded', timeout=15000)
                
                # 关闭可能的公告弹窗
                try:
                    page.click('button:has-text("关闭公告")', timeout=2000)
                except:
                    pass
                
                # 等待登录表单
                page.wait_for_selector('input[placeholder*="用户名或邮箱"]', timeout=5000)
                
                # 填写登录信息
                page.fill('input[placeholder*="用户名或邮箱"]', account['username'])
                page.fill('input[placeholder*="密码"]', account['password'])
                
                # 提交登录
                page.click('button:has-text("继续")')
                
                # 等待登录结果
                try:
                    page.wait_for_url('https://anyrouter.top/console', timeout=15000)
                except:
                    # 检查是否有登录成功提示
                    if not page.locator('text=登录成功！').is_visible(timeout=5000):
                        raise Exception("登录失败或超时")
                
                # 等待页面加载
                time.sleep(2)
                
                # 获取余额信息
                balance_info = self.get_balance_info(page)
                
                browser.close()
                return {'success': True, 'balance_info': balance_info}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_balance_info(self, page):
        """获取余额信息 - 优化版，只依赖页面DOM元素"""
        try:
            # 等待页面加载完成
            time.sleep(2)

            # 直接从页面获取余额信息
            balance_data = page.evaluate('''
                () => {
                    const result = {};

                    // 查找所有文本节点，更精确地匹配
                    const allElements = Array.from(document.querySelectorAll('*'));

                    // 精确匹配美元金额 - 只查找叶子节点
                    allElements.forEach(el => {
                        // 确保是叶子节点（没有子元素或只有文本）
                        if (el.children.length === 0 && el.textContent) {
                            const text = el.textContent.trim();

                            // 检查是否是美元金额格式
                            if (/^\\$[0-9,]+\\.?[0-9]*$/.test(text)) {
                                // 向上查找包含关键词的父元素
                                let contextEl = el.parentElement;
                                let depth = 0;
                                while (contextEl && depth < 3) {
                                    const contextText = contextEl.textContent || '';

                                    if (contextText.includes('当前余额') && !result.currentBalance) {
                                        result.currentBalance = text;
                                        break;
                                    } else if (contextText.includes('历史消耗') && !result.historicalUsage) {
                                        result.historicalUsage = text;
                                        break;
                                    } else if (contextText.includes('统计额度') && !result.statisticsQuota) {
                                        result.statisticsQuota = text;
                                        break;
                                    }

                                    contextEl = contextEl.parentElement;
                                    depth++;
                                }
                            }

                            // 匹配数字（请求次数等）
                            if (/^"?[0-9,]+"?$/.test(text)) {
                                const cleanText = text.replace(/"/g, '');
                                let contextEl = el.parentElement;
                                let depth = 0;

                                while (contextEl && depth < 3) {
                                    const contextText = contextEl.textContent || '';

                                    if (contextText.includes('请求次数') && !result.requestCount) {
                                        result.requestCount = cleanText;
                                        break;
                                    } else if (contextText.includes('统计次数') && !result.statisticsCount) {
                                        result.statisticsCount = cleanText;
                                        break;
                                    }

                                    contextEl = contextEl.parentElement;
                                    depth++;
                                }
                            }
                        }
                    });

                    // 如果还没有找到，尝试更宽松的搜索
                    if (!result.currentBalance) {
                        // 查找包含"当前余额"的元素，然后找其后的金额
                        const balanceLabels = allElements.filter(el =>
                            el.textContent && el.textContent.includes('当前余额')
                        );

                        for (const label of balanceLabels) {
                            // 查找同级或子级的美元金额
                            const parent = label.parentElement;
                            if (parent) {
                                const dollarEl = parent.querySelector('*');
                                if (dollarEl) {
                                    const matches = parent.textContent.match(/\\$[0-9,]+\\.?[0-9]*/);
                                    if (matches) {
                                        result.currentBalance = matches[0];
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    return result;
                }
            ''')

            # 格式化输出
            if balance_data and len(balance_data) > 0:
                parts = []

                if balance_data.get('currentBalance'):
                    parts.append(f"余额: {balance_data.get('currentBalance')}")

                if balance_data.get('historicalUsage'):
                    parts.append(f"消耗: {balance_data.get('historicalUsage')}")

                if balance_data.get('requestCount'):
                    parts.append(f"请求: {balance_data.get('requestCount')}")

                if balance_data.get('statisticsQuota') and balance_data.get('statisticsQuota') != '$0.00':
                    parts.append(f"统计: {balance_data.get('statisticsQuota')}")

                return " | ".join(parts) if parts else "余额: $0.00"

            # 如果没有获取到数据，返回默认值而不是错误信息
            return "余额: 获取中..."

        except Exception as e:
            # 发生错误时返回友好的提示
            return "余额: 暂时无法获取"
    
    def view_log_file(self):
        """查看日志文件"""
        try:
            if os.path.exists(self.log_file):
                # 使用记事本打开日志文件
                os.startfile(self.log_file)
            else:
                messagebox.showinfo("提示", "日志文件不存在")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开日志文件: {str(e)}")
    
    def open_settings(self):
        """打开设置对话框"""
        messagebox.showinfo("设置", "设置功能开发中...")
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.accounts = config.get('accounts', [])
                    
                    # 加载配置成功
                    pass
                        
                print(f"成功加载 {len(self.accounts)} 个账号")
            else:
                print("未找到配置文件，将创建新的配置")
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            config = {
                'accounts': self.accounts
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}")


class AccountDialog:
    """账号添加/编辑对话框"""
    def __init__(self, parent, title, username="", password=""):
        self.result = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # 创建界面
        frame = ttk.Frame(self.dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 用户名
        ttk.Label(frame, text="用户名/邮箱:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.username_var = tk.StringVar(value=username)
        username_entry = ttk.Entry(frame, textvariable=self.username_var, width=30)
        username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 密码
        ttk.Label(frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.password_var = tk.StringVar(value=password)
        password_entry = ttk.Entry(frame, textvariable=self.password_var, show="*", width=30)
        password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))
        
        ttk.Button(btn_frame, text="确定", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="取消", command=self.cancel_clicked).pack(side=tk.LEFT)
        
        # 配置网格
        frame.columnconfigure(1, weight=1)
        
        # 焦点和回车绑定
        username_entry.focus()
        self.dialog.bind('<Return>', lambda e: self.ok_clicked())
        self.dialog.bind('<Escape>', lambda e: self.cancel_clicked())
    
    def ok_clicked(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "用户名和密码不能为空！")
            return
        
        self.result = (username, password)
        self.dialog.destroy()
    
    def cancel_clicked(self):
        self.dialog.destroy()


def main():
    """主函数"""
    # 检查依赖
    try:
        import playwright
        import schedule
    except ImportError as e:
        print(f"缺少依赖包: {e}")
        print("请运行: pip install playwright schedule")
        input("按回车键退出...")
        return
    
    # 创建主窗口
    root = tk.Tk()
    app = AnyRouterGUI(root)
    
    # 启动界面
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("程序被用户中断")


if __name__ == "__main__":
    main()
