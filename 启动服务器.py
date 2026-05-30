# -*- coding: utf-8 -*-
# 启动服务器.py - 完整修复版 v16.1

import subprocess
import os
import sys
import threading
import time
import json
import shutil
import socket
import winsound
import requests
import re
import zipfile
import tempfile
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog

# 设置控制台编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class OnlineServerManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Minecraft服务器管理器 v16.1 | 制作：houukhhk")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # 现代配色
        self.colors = {
            'bg_main': '#f8f9fa',
            'bg_card': '#ffffff', 
            'bg_dark': '#e9ecef',
            'accent_green': '#20c997',
            'accent_red': '#dc3545',
            'accent_orange': '#fd7e14',
            'accent_yellow': '#ffc107',
            'accent_blue': '#0d6efd',
            'accent_purple': '#6f42c1',
            'accent_cyan': '#0dcaf0',
            'accent_pink': '#d63384',
            'accent_teal': '#20c997',
            'text_dark': '#212529',
            'text_gray': '#6c757d',
            'console_bg': '#1a1a2e',
            'console_text': '#00ff88'
        }
        
        self.server_process = None
        self.server_running = False
        self.start_time = None
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.server_exe = os.path.join(self.current_dir, "bedrock_server.exe")
        self.online_players = []
        self.all_logs = []
        self.player_logs = {}
        self.blacklist = []
        self.whitelist = []
        self.local_ip = self.get_local_ip()
        self.public_ip = self.get_public_ip()
        self.config_file = os.path.join(self.current_dir, "server_manager_config.json")
        
        # 服务器模式
        self.server_mode = "normal"
        self.server_owner = "houukhhk"
        self.bdsx_path = ""
        self.friend_mode = "friends_of_friends"
        
        # 备份相关
        self.backup_folder = os.path.join(self.current_dir, "backups")
        self.worlds_folder = os.path.join(self.current_dir, "worlds_backup")
        self.addons_folder = os.path.join(self.current_dir, "addons")
        self.current_world_path = None
        
        # Discord Webhook
        self.discord_webhooks = []
        self.discord_enabled = False
        self.last_discord_message_time = 0
        
        # 自动备份
        self.auto_backup_enabled = False
        self.backup_interval = 30
        self.keep_backups = 10
        self.sound_enabled = True
        self.online_mode = False
        self.command_blocks = True
        self.allow_cheats = True
        self.server_settings = {
            "server-name": "houukhhk-开服",
            "motd": "欢迎来到 houukhhk 的服务器！",
            "gamemode": "survival",
            "difficulty": "normal",
            "max-players": "100",
            "view-distance": "10",
            "visible_to_lan": True
        }
        self.gamerules = {
            "keepInventory": False,
            "doFireTick": True,
            "tntExplodes": True,
            "pvp": True,
            "showDeathMessages": True,
            "doMobSpawning": True,
            "doDaylightCycle": True
        }
        
        self.running = True
        
        # UI控件
        self.console = None
        self.backup_tree = None
        self.world_tree = None
        self.addons_listbox = None
        self.online_listbox = None
        self.blacklist_tree = None
        self.whitelist_listbox = None
        self.online_count_label = None
        self.uptime_label = None
        self.start_btn = None
        self.stop_btn = None
        self.restart_btn = None
        self.status_label = None
        self.time_label = None
        self.cmd_entry = None
        self.last_backup_label = None
        self.mcworld_path_var = None
        self.content_frame = None
        self.server_name_label = None
        
        self.log_queue = []
        
        self.load_all_configs()
        self.update_server_name()
        
        os.makedirs(self.backup_folder, exist_ok=True)
        os.makedirs(self.worlds_folder, exist_ok=True)
        os.makedirs(self.addons_folder, exist_ok=True)
        
        self.setup_main_ui()
        self.start_background_threads()
        
        self.safe_log("服务器管理器已启动 | 制作：houukhhk")
        self.safe_log(f"本机IP: {self.local_ip}")
        self.safe_log(f"外网IP: {self.public_ip if self.public_ip else '获取失败'}")
        self.safe_log(f"Discord通知: {'已启用' if self.discord_enabled else '已禁用'}")
        self.play_sound('startup')
    
    def update_server_name(self):
        default_name = f"houukhhk-开服"
        if not self.server_settings.get("server-name") or "houukhhk" not in self.server_settings.get("server-name", ""):
            self.server_settings["server-name"] = default_name
        self.save_all_configs()
        self.update_server_properties()
    
    def safe_log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {msg}\n"
        self.log_queue.append(formatted_msg)
        self.all_logs.append(formatted_msg)
        if len(self.all_logs) > 50000:
            self.all_logs = self.all_logs[-30000:]
        print(formatted_msg, end='')
    
    def add_player_log(self, player_name, msg):
        if player_name not in self.player_logs:
            self.player_logs[player_name] = []
        self.player_logs[player_name].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        if len(self.player_logs[player_name]) > 500:
            self.player_logs[player_name] = self.player_logs[player_name][-300:]
    
    def start_background_threads(self):
        def process_logs():
            while self.running:
                if self.log_queue:
                    msg = self.log_queue.pop(0)
                    try:
                        if self.console and self.console.winfo_exists():
                            self.console.insert(tk.END, msg)
                            self.console.see(tk.END)
                            line_count = int(self.console.index('end-1c').split('.')[0])
                            if line_count > 10000:
                                self.console.delete(1.0, 5000.0)
                    except:
                        pass
                time.sleep(0.1)
        threading.Thread(target=process_logs, daemon=True).start()
        
        def refresh_loop():
            while self.running:
                time.sleep(5)
                if self.server_running:
                    try:
                        if self.server_process and self.server_process.stdin:
                            self.server_process.stdin.write("list\n")
                            self.server_process.stdin.flush()
                    except:
                        pass
        threading.Thread(target=refresh_loop, daemon=True).start()
        
        def update_uptime():
            while self.running:
                if self.server_running and self.start_time:
                    elapsed = int(time.time() - self.start_time)
                    hours = elapsed // 3600
                    minutes = (elapsed % 3600) // 60
                    seconds = elapsed % 60
                    uptime_str = f"运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}"
                    try:
                        if self.uptime_label and self.uptime_label.winfo_exists():
                            self.root.after(0, lambda: self.uptime_label.config(text=uptime_str))
                    except:
                        pass
                time.sleep(1)
        threading.Thread(target=update_uptime, daemon=True).start()
    
    def get_public_ip(self):
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except:
            pass
        return None
    
    def send_discord_message(self, content):
        """发送Discord消息 - 修复版"""
        if not self.discord_enabled:
            self.safe_log("Discord通知未启用，跳过发送")
            return False
        
        if not self.discord_webhooks:
            self.safe_log("没有配置Webhook，跳过发送")
            return False
        
        # 限流保护
        current_time = time.time()
        if current_time - self.last_discord_message_time < 3:
            self.safe_log("Discord消息发送太频繁，跳过")
            return False
        
        # 限制消息长度
        if len(content) > 1900:
            content = content[:1897] + "..."
        
        def send_to_webhook(webhook):
            try:
                data = {
                    "content": content,
                    "username": "Minecraft服务器管家",
                    "avatar_url": "https://cdn.discordapp.com/attachments/1326940330310762626/1326941390054232064/minecraft-icon.png"
                }
                response = requests.post(webhook["url"], json=data, timeout=10)
                if response.status_code in [204, 200]:
                    self.safe_log(f"Discord消息发送成功: {webhook.get('name', 'Webhook')}")
                    return True
                else:
                    self.safe_log(f"Discord发送失败: HTTP {response.status_code}")
                    return False
            except Exception as e:
                self.safe_log(f"Discord发送异常: {e}")
                return False
        
        def send_all():
            success_count = 0
            for webhook in self.discord_webhooks:
                if webhook.get("enabled", True) and webhook.get("url"):
                    if send_to_webhook(webhook):
                        success_count += 1
            if success_count > 0:
                self.last_discord_message_time = time.time()
                self.safe_log(f"Discord消息已发送到 {success_count} 个频道")
            else:
                self.safe_log("Discord消息发送失败，请检查Webhook配置")
        
        threading.Thread(target=send_all, daemon=True).start()
        return True
    
    def play_sound(self, sound_type='backup'):
        if not self.sound_enabled:
            return
        try:
            if sound_type == 'backup':
                winsound.Beep(880, 200)
                winsound.Beep(988, 200)
            elif sound_type == 'error':
                winsound.Beep(440, 300)
                winsound.Beep(330, 300)
            elif sound_type == 'startup':
                winsound.Beep(523, 150)
                winsound.Beep(659, 150)
                winsound.Beep(784, 300)
            elif sound_type == 'player_join':
                winsound.Beep(659, 100)
                winsound.Beep(784, 100)
            elif sound_type == 'player_leave':
                winsound.Beep(784, 100)
                winsound.Beep(659, 100)
        except:
            pass
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_world_path(self):
        prop_path = os.path.join(os.path.dirname(self.server_exe), "server.properties")
        level_name = "Bedrock level"
        
        if os.path.exists(prop_path):
            try:
                with open(prop_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("level-name="):
                            level_name = line.strip().split('=', 1)[1].strip()
                            break
            except:
                pass
        
        world_path = os.path.join(os.path.dirname(self.server_exe), "worlds", level_name)
        self.current_world_path = world_path
        return world_path
    
    def load_all_configs(self):
        default_config = {
            "server_exe": self.server_exe,
            "backup_enabled": False,
            "backup_interval": 30,
            "keep_backups": 10,
            "online_mode": False,
            "command_blocks": True,
            "allow_cheats": True,
            "sound_enabled": True,
            "discord_enabled": False,
            "discord_webhooks": [],
            "server_mode": "normal",
            "server_owner": "houukhhk",
            "bdsx_path": "",
            "friend_mode": "friends_of_friends",
            "blacklist": [],
            "whitelist": [],
            "server_settings": {
                "server-name": "houukhhk-开服",
                "motd": "欢迎来到 houukhhk 的服务器！",
                "gamemode": "survival",
                "difficulty": "normal",
                "max-players": "100",
                "view-distance": "10",
                "visible_to_lan": True
            },
            "gamerules": {
                "keepInventory": False,
                "doFireTick": True,
                "tntExplodes": True,
                "pvp": True,
                "showDeathMessages": True,
                "doMobSpawning": True,
                "doDaylightCycle": True
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.server_exe = config.get("server_exe", default_config["server_exe"])
                self.auto_backup_enabled = config.get("backup_enabled", default_config["backup_enabled"])
                self.backup_interval = config.get("backup_interval", default_config["backup_interval"])
                self.keep_backups = config.get("keep_backups", default_config["keep_backups"])
                self.online_mode = config.get("online_mode", default_config["online_mode"])
                self.command_blocks = config.get("command_blocks", default_config["command_blocks"])
                self.allow_cheats = config.get("allow_cheats", default_config["allow_cheats"])
                self.sound_enabled = config.get("sound_enabled", default_config["sound_enabled"])
                self.discord_enabled = config.get("discord_enabled", default_config["discord_enabled"])
                self.discord_webhooks = config.get("discord_webhooks", default_config["discord_webhooks"])
                self.server_mode = config.get("server_mode", default_config["server_mode"])
                self.server_owner = config.get("server_owner", default_config["server_owner"])
                self.bdsx_path = config.get("bdsx_path", default_config["bdsx_path"])
                self.friend_mode = config.get("friend_mode", default_config["friend_mode"])
                self.blacklist = config.get("blacklist", default_config["blacklist"])
                self.whitelist = config.get("whitelist", default_config["whitelist"])
                self.server_settings = config.get("server_settings", default_config["server_settings"])
                self.gamerules = config.get("gamerules", default_config["gamerules"])
            except Exception as e:
                self.safe_log(f"加载配置失败: {e}")
                self.use_default_config(default_config)
        else:
            self.use_default_config(default_config)
            self.save_all_configs()
        
        if "houukhhk" not in self.server_settings.get("server-name", ""):
            self.server_settings["server-name"] = f"houukhhk-开服"
    
    def use_default_config(self, dc):
        self.server_exe = dc["server_exe"]
        self.auto_backup_enabled = dc["backup_enabled"]
        self.backup_interval = dc["backup_interval"]
        self.keep_backups = dc["keep_backups"]
        self.online_mode = dc["online_mode"]
        self.command_blocks = dc["command_blocks"]
        self.allow_cheats = dc["allow_cheats"]
        self.sound_enabled = dc["sound_enabled"]
        self.discord_enabled = dc["discord_enabled"]
        self.discord_webhooks = dc["discord_webhooks"]
        self.server_mode = dc["server_mode"]
        self.server_owner = dc["server_owner"]
        self.bdsx_path = dc["bdsx_path"]
        self.friend_mode = dc.get("friend_mode", "friends_of_friends")
        self.blacklist = dc.get("blacklist", [])
        self.whitelist = dc.get("whitelist", [])
        self.server_settings = dc["server_settings"]
        self.gamerules = dc["gamerules"]
    
    def save_all_configs(self):
        try:
            config = {
                "server_exe": self.server_exe,
                "backup_enabled": self.auto_backup_enabled,
                "backup_interval": self.backup_interval,
                "keep_backups": self.keep_backups,
                "online_mode": self.online_mode,
                "command_blocks": self.command_blocks,
                "allow_cheats": self.allow_cheats,
                "sound_enabled": self.sound_enabled,
                "discord_enabled": self.discord_enabled,
                "discord_webhooks": self.discord_webhooks,
                "server_mode": self.server_mode,
                "server_owner": self.server_owner,
                "bdsx_path": self.bdsx_path,
                "friend_mode": self.friend_mode,
                "blacklist": self.blacklist,
                "whitelist": self.whitelist,
                "server_settings": self.server_settings,
                "gamerules": self.gamerules
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False
    
    def update_server_properties(self):
        prop_path = os.path.join(os.path.dirname(self.server_exe), "server.properties")
        
        if "houukhhk" not in self.server_settings.get("server-name", ""):
            self.server_settings["server-name"] = "houukhhk-开服"
        
        if os.path.exists(prop_path):
            try:
                with open(prop_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                found_server_name = False
                for i, line in enumerate(lines):
                    if line.startswith("server-name="):
                        lines[i] = f"server-name={self.server_settings.get('server-name', 'houukhhk-开服')}\n"
                        found_server_name = True
                    elif line.startswith("max-players="):
                        lines[i] = f"max-players={self.server_settings.get('max-players', '100')}\n"
                    elif line.startswith("gamemode="):
                        lines[i] = f"gamemode={self.server_settings.get('gamemode', 'survival')}\n"
                    elif line.startswith("difficulty="):
                        lines[i] = f"difficulty={self.server_settings.get('difficulty', 'normal')}\n"
                    elif line.startswith("motd="):
                        lines[i] = f"motd={self.server_settings.get('motd', '欢迎来到 houukhhk 的服务器！')}\n"
                    elif line.startswith("allow-cheats="):
                        lines[i] = f"allow-cheats={'true' if self.allow_cheats else 'false'}\n"
                
                if not found_server_name:
                    lines.append(f"server-name={self.server_settings.get('server-name', 'houukhhk-开服')}\n")
                
                with open(prop_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            except:
                pass
    
    # ==================== UI设置 ====================
    
    def setup_main_ui(self):
        header = tk.Frame(self.root, bg=self.colors['accent_blue'], height=60)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        logo_frame = tk.Frame(header, bg=self.colors['accent_blue'])
        logo_frame.pack(side='left', padx=20, pady=10)
        
        tk.Label(logo_frame, text="🎮", font=("Segoe UI", 24),
                bg=self.colors['accent_blue'], fg='white').pack(side='left')
        
        tk.Label(logo_frame, text="Minecraft Server Manager", font=("Segoe UI", 16, "bold"),
                bg=self.colors['accent_blue'], fg='white').pack(side='left', padx=10)
        
        server_name_text = self.server_settings.get("server-name", "houukhhk-开服")
        self.server_name_label = tk.Label(header, text=f"🌐 {server_name_text}", 
                                          font=("Segoe UI", 11, "bold"),
                                          bg=self.colors['accent_blue'], fg='#ffd700')
        self.server_name_label.pack(side='left', padx=20)
        
        right_frame = tk.Frame(header, bg=self.colors['accent_blue'])
        right_frame.pack(side='right', padx=20)
        
        self.status_label = tk.Label(right_frame, text="● 离线", font=("Segoe UI", 11, "bold"),
                                     bg=self.colors['accent_blue'], fg=self.colors['accent_red'])
        self.status_label.pack(side='top')
        
        self.time_label = tk.Label(right_frame, text="", font=("Segoe UI", 9),
                                   bg=self.colors['accent_blue'], fg='white')
        self.time_label.pack(side='top')
        self.update_time()
        
        self.content_frame = tk.Frame(self.root, bg=self.colors['bg_main'])
        self.content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.show_main_menu()
    
    def update_time(self):
        try:
            if self.time_label and self.time_label.winfo_exists():
                self.time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except:
            pass
        self.root.after(1000, self.update_time)
    
    def show_main_menu(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        title_frame = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        title_frame.pack(pady=20)
        
        tk.Label(title_frame, text="欢迎使用服务器管理器", font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['text_dark']).pack()
        tk.Label(title_frame, text="请选择功能模块", font=("Segoe UI", 14),
                bg=self.colors['bg_main'], fg=self.colors['text_gray']).pack(pady=5)
        
        buttons_frame = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        buttons_frame.pack(expand=True, pady=20)
        
        modules = [
            {"name": "备份管理", "icon": "💾", "color": self.colors['accent_cyan'],
             "desc": "自动/手动备份\n还原存档", "command": self.show_backup_management},
            {"name": "世界管理", "icon": "🌍", "color": self.colors['accent_green'],
             "desc": "导入mcworld\n切换世界", "command": self.show_world_management},
            {"name": "主控制台", "icon": "🎮", "color": self.colors['accent_blue'],
             "desc": "启动/停止服务器\n实时控制台", "command": self.show_main_console},
            {"name": "插件/行为包", "icon": "📦", "color": self.colors['accent_purple'],
             "desc": "导入/管理addons\n资源包", "command": self.show_addons_management},
            {"name": "玩家黑名单", "icon": "🚫", "color": self.colors['accent_red'],
             "desc": "管理黑名单\n封禁玩家记录", "command": self.show_blacklist_management},
            {"name": "玩家管理", "icon": "👥", "color": self.colors['accent_orange'],
             "desc": "在线玩家管理\n踢出/OP/封禁", "command": self.show_player_management}
        ]
        
        for i, module in enumerate(modules):
            row = i // 3
            col = i % 3
            
            btn_container = tk.Frame(buttons_frame, bg=self.colors['bg_main'])
            btn_container.grid(row=row, column=col, padx=25, pady=20, sticky='nsew')
            
            card = tk.Frame(btn_container, bg=self.colors['bg_card'], relief='raised', bd=1)
            card.pack(padx=5, pady=5)
            
            btn = tk.Button(card, text=f"{module['icon']}\n{module['name']}", 
                           font=("Segoe UI", 16, "bold"),
                           bg=module['color'], fg='white',
                           width=14, height=3, relief='flat',
                           cursor='hand2', command=module['command'])
            btn.pack(padx=20, pady=15)
            
            desc_label = tk.Label(card, text=module['desc'], font=("Segoe UI", 9),
                                  bg=self.colors['bg_card'], fg=self.colors['text_gray'])
            desc_label.pack(pady=(0, 10))
            
            def on_enter(e, b=btn, c=module['color']):
                b.config(bg=self.lighten_color(c))
            def on_leave(e, b=btn, c=module['color']):
                b.config(bg=c)
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        
        for i in range(3):
            buttons_frame.grid_columnconfigure(i, weight=1)
        for i in range(2):
            buttons_frame.grid_rowconfigure(i, weight=1)
        
        settings_frame = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        settings_frame.pack(side='bottom', fill='x', pady=20)
        
        tk.Button(settings_frame, text="⚙️ Discord通知设置", command=self.show_discord_settings,
                 bg=self.colors['accent_purple'], fg='white', font=("Segoe UI", 10), 
                 relief='flat', padx=15, pady=8, cursor='hand2').pack(side='left', padx=5)
        tk.Button(settings_frame, text="🔧 服务器设置", command=self.show_server_settings,
                 bg=self.colors['accent_cyan'], fg='white', font=("Segoe UI", 10), 
                 relief='flat', padx=15, pady=8, cursor='hand2').pack(side='left', padx=5)
        tk.Button(settings_frame, text="🔄 同步状态", command=self.sync_server_status,
                 bg=self.colors['accent_yellow'], fg=self.colors['text_dark'], font=("Segoe UI", 10), 
                 relief='flat', padx=15, pady=8, cursor='hand2').pack(side='left', padx=5)
        tk.Button(settings_frame, text="📡 测试Discord", command=self.test_discord_connection,
                 bg=self.colors['accent_green'], fg='white', font=("Segoe UI", 10), 
                 relief='flat', padx=15, pady=8, cursor='hand2').pack(side='left', padx=5)
    
    def lighten_color(self, color):
        colors = {
            self.colors['accent_green']: '#2dd4a0',
            self.colors['accent_red']: '#e84c5e',
            self.colors['accent_blue']: '#3b82f6',
            self.colors['accent_purple']: '#8b5cf6',
            self.colors['accent_cyan']: '#22d3ee',
            self.colors['accent_yellow']: '#fbbf24',
            self.colors['accent_orange']: '#fb923c',
            self.colors['accent_pink']: '#ec4899',
        }
        return colors.get(color, color)
    
    def test_discord_connection(self):
        """测试Discord连接"""
        if not self.discord_webhooks:
            messagebox.showwarning("未配置", "请先在Discord通知设置中添加Webhook")
            return
        
        result = self.send_discord_message("🎮 测试消息：服务器管理器连接成功！")
        if result:
            messagebox.showinfo("测试已发送", "测试消息已发送，请检查Discord频道")
        else:
            messagebox.showerror("发送失败", "消息发送失败，请检查Webhook配置和网络连接")
    
    # ==================== 其他页面（简化版） ====================
    
    def show_backup_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.add_back_button()
        
        tk.Label(self.content_frame, text="💾 备份管理", font=("Segoe UI", 24, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_cyan']).pack(pady=10)
        
        main_panel = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        main_panel.pack(fill='both', expand=True, padx=10, pady=10)
        
        left_panel = tk.LabelFrame(main_panel, text="备份列表", font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        left_panel.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        columns = ("name", "size", "time")
        self.backup_tree = ttk.Treeview(left_panel, columns=columns, show='headings', height=20)
        self.backup_tree.heading("name", text="备份名称")
        self.backup_tree.heading("size", text="大小(MB)")
        self.backup_tree.heading("time", text="创建时间")
        self.backup_tree.column("name", width=250)
        self.backup_tree.column("size", width=100)
        self.backup_tree.column("time", width=150)
        
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.backup_tree.yview)
        self.backup_tree.configure(yscrollcommand=scrollbar.set)
        self.backup_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')
        
        right_panel = tk.LabelFrame(main_panel, text="备份操作", font=("Segoe UI", 12, "bold"),
                                    bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        right_panel.pack(side='right', fill='y', padx=5, pady=5, ipadx=20)
        
        tk.Label(right_panel, text="自动备份设置", font=("Segoe UI", 11, "bold"),
                bg=self.colors['bg_card'], fg=self.colors['text_dark']).pack(pady=10)
        
        backup_enabled_var = tk.BooleanVar(value=self.auto_backup_enabled)
        
        def toggle_auto():
            self.auto_backup_enabled = backup_enabled_var.get()
            self.save_all_configs()
        
        tk.Checkbutton(right_panel, text="启用自动备份", variable=backup_enabled_var,
                      command=toggle_auto, bg=self.colors['bg_card']).pack(pady=5)
        
        interval_frame = tk.Frame(right_panel, bg=self.colors['bg_card'])
        interval_frame.pack(pady=5)
        tk.Label(interval_frame, text="备份间隔:", bg=self.colors['bg_card']).pack(side='left')
        interval_var = tk.StringVar(value=str(self.backup_interval))
        tk.Spinbox(interval_frame, from_=5, to=360, textvariable=interval_var, width=6).pack(side='left', padx=5)
        tk.Label(interval_frame, text="分钟", bg=self.colors['bg_card']).pack(side='left')
        
        keep_frame = tk.Frame(right_panel, bg=self.colors['bg_card'])
        keep_frame.pack(pady=5)
        tk.Label(keep_frame, text="保留备份数:", bg=self.colors['bg_card']).pack(side='left')
        keep_var = tk.StringVar(value=str(self.keep_backups))
        tk.Spinbox(keep_frame, from_=1, to=100, textvariable=keep_var, width=6).pack(side='left', padx=5)
        
        def do_backup():
            if not self.server_running:
                messagebox.showwarning("警告", "服务器未运行，无法备份")
                return
            self.perform_backup()
        
        tk.Button(right_panel, text="立即手动备份", command=do_backup,
                 bg=self.colors['accent_green'], fg='white', relief='flat', width=20, pady=5).pack(pady=10)
        tk.Button(right_panel, text="还原选中备份", command=self.restore_backup,
                 bg=self.colors['accent_yellow'], fg='white', relief='flat', width=20, pady=5).pack(pady=5)
        tk.Button(right_panel, text="删除选中备份", command=self.delete_backup,
                 bg=self.colors['accent_red'], fg='white', relief='flat', width=20, pady=5).pack(pady=5)
        tk.Button(right_panel, text="刷新列表", command=self.refresh_backup_list,
                 bg=self.colors['accent_blue'], fg='white', relief='flat', width=20, pady=5).pack(pady=5)
        
        self.last_backup_label = tk.Label(right_panel, text="最后备份: 无",
                                         bg=self.colors['bg_card'], fg=self.colors['text_gray'])
        self.last_backup_label.pack(pady=10)
        
        self.refresh_backup_list()
    
    def perform_backup(self):
        try:
            self.safe_log("开始备份...")
            
            if self.server_running:
                self.send_command("save-all")
                time.sleep(2)
                self.send_command("save-off")
                time.sleep(1)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.backup_folder, backup_name)
            os.makedirs(backup_path, exist_ok=True)
            
            world_path = self.get_world_path()
            if os.path.exists(world_path):
                shutil.copytree(world_path, os.path.join(backup_path, "world"))
            
            config_backup = os.path.join(backup_path, "config")
            os.makedirs(config_backup, exist_ok=True)
            server_dir = os.path.dirname(self.server_exe)
            for config_file in ["server.properties", "permissions.json", "allowlist.json"]:
                src = os.path.join(server_dir, config_file)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(config_backup, config_file))
            
            self.cleanup_old_backups()
            self.safe_log(f"✅ 备份完成: {backup_name}")
            if self.last_backup_label and self.last_backup_label.winfo_exists():
                self.last_backup_label.config(text=f"最后备份: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.refresh_backup_list()
            self.play_sound('backup')
            
        except Exception as e:
            self.safe_log(f"❌ 备份失败: {e}")
        finally:
            if self.server_running:
                self.send_command("save-on")
    
    def cleanup_old_backups(self):
        try:
            backups = [d for d in os.listdir(self.backup_folder) 
                      if os.path.isdir(os.path.join(self.backup_folder, d)) and d.startswith("backup_")]
            backups.sort(reverse=True)
            for old in backups[self.keep_backups:]:
                shutil.rmtree(os.path.join(self.backup_folder, old))
        except:
            pass
    
    def refresh_backup_list(self):
        try:
            if self.backup_tree and self.backup_tree.winfo_exists():
                for item in self.backup_tree.get_children():
                    self.backup_tree.delete(item)
                
                if os.path.exists(self.backup_folder):
                    backups = [d for d in os.listdir(self.backup_folder) 
                              if os.path.isdir(os.path.join(self.backup_folder, d)) and d.startswith("backup_")]
                    for backup in sorted(backups, reverse=True):
                        size_mb = self.get_folder_size(os.path.join(self.backup_folder, backup)) / (1024 * 1024)
                        create_time = backup.replace("backup_", "")[:15]
                        self.backup_tree.insert("", "end", values=(backup, f"{size_mb:.2f}", create_time))
        except:
            pass
    
    def restore_backup(self):
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个备份")
            return
        
        backup_name = self.backup_tree.item(selection[0])['values'][0]
        
        if not messagebox.askyesno("确认回档", f"确定要回档到 {backup_name} 吗？\n服务器需要重启"):
            return
        
        try:
            was_running = self.server_running
            if was_running:
                self.stop_server()
                time.sleep(3)
            
            world_path = self.get_world_path()
            backup_path = os.path.join(self.backup_folder, backup_name)
            
            if os.path.exists(world_path):
                shutil.rmtree(world_path)
            if os.path.exists(os.path.join(backup_path, "world")):
                shutil.copytree(os.path.join(backup_path, "world"), world_path)
            
            self.safe_log(f"✅ 回档成功: {backup_name}")
            
            if was_running:
                self.start_server()
            
            messagebox.showinfo("成功", "回档完成！")
        except Exception as e:
            messagebox.showerror("回档失败", str(e))
    
    def delete_backup(self):
        selection = self.backup_tree.selection()
        if selection and messagebox.askyesno("确认", "确定删除选中备份？"):
            backup_name = self.backup_tree.item(selection[0])['values'][0]
            shutil.rmtree(os.path.join(self.backup_folder, backup_name))
            self.refresh_backup_list()
    
    def show_world_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.add_back_button()
        
        tk.Label(self.content_frame, text="🌍 世界管理", font=("Segoe UI", 24, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_green']).pack(pady=10)
        
        main_panel = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        main_panel.pack(fill='both', expand=True, padx=10, pady=10)
        
        current_frame = tk.LabelFrame(main_panel, text="当前世界", font=("Segoe UI", 12, "bold"),
                                      bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        current_frame.pack(fill='x', padx=5, pady=5)
        
        current_world = self.get_world_path()
        tk.Label(current_frame, text=f"世界路径: {current_world}", font=("Segoe UI", 10),
                bg=self.colors['bg_card'], fg=self.colors['text_gray'], wraplength=600).pack(pady=5, padx=10)
        
        if os.path.exists(current_world):
            world_size = self.get_folder_size(current_world) / (1024 * 1024)
            tk.Label(current_frame, text=f"世界大小: {world_size:.2f} MB", font=("Segoe UI", 10),
                    bg=self.colors['bg_card'], fg=self.colors['accent_green']).pack(pady=5)
        
        action_frame = tk.LabelFrame(main_panel, text="世界操作", font=("Segoe UI", 12, "bold"),
                                     bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        action_frame.pack(fill='x', padx=5, pady=5)
        
        import_frame = tk.Frame(action_frame, bg=self.colors['bg_card'])
        import_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(import_frame, text="导入mcworld文件:", font=("Segoe UI", 11),
                bg=self.colors['bg_card']).pack(anchor='w')
        
        file_frame = tk.Frame(import_frame, bg=self.colors['bg_card'])
        file_frame.pack(fill='x', pady=5)
        
        self.mcworld_path_var = tk.StringVar()
        tk.Entry(file_frame, textvariable=self.mcworld_path_var, font=("Segoe UI", 10),
                bg='white', relief='solid', bd=1).pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Button(file_frame, text="浏览", command=self.select_mcworld_file,
                 bg=self.colors['accent_blue'], fg='white', relief='flat').pack(side='right')
        
        tk.Button(import_frame, text="导入并应用mcworld", command=self.import_mcworld,
                 bg=self.colors['accent_green'], fg='white', relief='flat', pady=5, width=20).pack(pady=10)
        
        list_frame = tk.LabelFrame(main_panel, text="可用世界存档", font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        columns = ("name", "size", "modified")
        self.world_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        self.world_tree.heading("name", text="世界名称")
        self.world_tree.heading("size", text="大小(MB)")
        self.world_tree.heading("modified", text="最后修改")
        self.world_tree.column("name", width=250)
        self.world_tree.column("size", width=100)
        self.world_tree.column("modified", width=150)
        
        world_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.world_tree.yview)
        self.world_tree.configure(yscrollcommand=world_scroll.set)
        self.world_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        world_scroll.pack(side='right', fill='y')
        
        world_btn_frame = tk.Frame(list_frame, bg=self.colors['bg_card'])
        world_btn_frame.pack(fill='x', padx=5, pady=5)
        
        def switch_world():
            selection = self.world_tree.selection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个世界")
                return
            
            world_name = self.world_tree.item(selection[0])['values'][0]
            
            if self.server_running:
                if not messagebox.askyesno("确认", f"切换到世界 {world_name} 需要重启服务器。是否继续？"):
                    return
                self.stop_server()
                time.sleep(2)
            
            try:
                prop_path = os.path.join(os.path.dirname(self.server_exe), "server.properties")
                if os.path.exists(prop_path):
                    with open(prop_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines):
                        if line.startswith("level-name="):
                            lines[i] = f"level-name={world_name}\n"
                            break
                    
                    with open(prop_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    self.safe_log(f"已切换到世界: {world_name}")
                    messagebox.showinfo("成功", f"已切换到世界: {world_name}")
                    
                    if self.server_running:
                        self.start_server()
                        
            except Exception as e:
                messagebox.showerror("切换失败", str(e))
        
        def backup_world():
            if not self.server_running:
                messagebox.showwarning("警告", "服务器未运行")
                return
            self.perform_backup()
            messagebox.showinfo("完成", "当前世界已备份")
        
        def delete_world():
            selection = self.world_tree.selection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个世界")
                return
            
            world_name = self.world_tree.item(selection[0])['values'][0]
            current_world = os.path.basename(self.get_world_path())
            
            if world_name == current_world:
                messagebox.showwarning("警告", "不能删除当前正在使用的世界")
                return
            
            if messagebox.askyesno("确认", f"确定要删除世界 {world_name} 吗？\n此操作不可恢复！"):
                world_path = os.path.join(os.path.dirname(self.server_exe), "worlds", world_name)
                try:
                    shutil.rmtree(world_path)
                    self.refresh_world_list()
                    self.safe_log(f"已删除世界: {world_name}")
                except Exception as e:
                    messagebox.showerror("删除失败", str(e))
        
        tk.Button(world_btn_frame, text="切换到选中世界", command=switch_world,
                 bg=self.colors['accent_cyan'], fg='white', relief='flat').pack(side='left', padx=5, expand=True, fill='x')
        tk.Button(world_btn_frame, text="备份当前世界", command=backup_world,
                 bg=self.colors['accent_green'], fg='white', relief='flat').pack(side='left', padx=5, expand=True, fill='x')
        tk.Button(world_btn_frame, text="删除选中世界", command=delete_world,
                 bg=self.colors['accent_red'], fg='white', relief='flat').pack(side='left', padx=5, expand=True, fill='x')
        tk.Button(world_btn_frame, text="刷新列表", command=self.refresh_world_list,
                 bg=self.colors['accent_blue'], fg='white', relief='flat').pack(side='left', padx=5, expand=True, fill='x')
        
        self.refresh_world_list()
    
    def select_mcworld_file(self):
        filename = filedialog.askopenfilename(
            title="选择mcworld文件",
            filetypes=[("Minecraft世界文件", "*.mcworld"), ("所有文件", "*.*")]
        )
        if filename:
            self.mcworld_path_var.set(filename)
    
    def import_mcworld(self):
        filepath = self.mcworld_path_var.get()
        if not filepath or not os.path.exists(filepath):
            messagebox.showwarning("警告", "请先选择有效的mcworld文件")
            return
        
        if self.server_running:
            if not messagebox.askyesno("确认", "服务器正在运行，导入世界需要重启服务器。是否继续？"):
                return
            self.stop_server()
            time.sleep(2)
        
        try:
            self.safe_log(f"正在导入世界: {filepath}")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                world_name = None
                for root, dirs, files in os.walk(temp_dir):
                    if "level.dat" in files:
                        world_name = os.path.basename(root)
                        break
                
                if not world_name:
                    world_name = f"imported_world_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                worlds_dir = os.path.join(os.path.dirname(self.server_exe), "worlds")
                target_path = os.path.join(worlds_dir, world_name)
                
                if os.path.exists(target_path):
                    world_name = f"{world_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    target_path = os.path.join(worlds_dir, world_name)
                
                shutil.copytree(temp_dir, target_path)
                
                prop_path = os.path.join(os.path.dirname(self.server_exe), "server.properties")
                if os.path.exists(prop_path):
                    with open(prop_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines):
                        if line.startswith("level-name="):
                            lines[i] = f"level-name={world_name}\n"
                            break
                    
                    with open(prop_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                
                self.safe_log(f"世界导入成功: {world_name}")
                messagebox.showinfo("导入成功", f"世界已导入: {world_name}")
                self.refresh_world_list()
                
                if self.server_running:
                    self.start_server()
                    
        except Exception as e:
            self.safe_log(f"导入失败: {e}")
            messagebox.showerror("导入失败", str(e))
    
    def refresh_world_list(self):
        try:
            if self.world_tree and self.world_tree.winfo_exists():
                for item in self.world_tree.get_children():
                    self.world_tree.delete(item)
                
                worlds_dir = os.path.join(os.path.dirname(self.server_exe), "worlds")
                if os.path.exists(worlds_dir):
                    for world in os.listdir(worlds_dir):
                        world_path = os.path.join(worlds_dir, world)
                        if os.path.isdir(world_path):
                            size_mb = self.get_folder_size(world_path) / (1024 * 1024)
                            modified = datetime.fromtimestamp(os.path.getmtime(world_path)).strftime("%Y-%m-%d %H:%M")
                            self.world_tree.insert("", "end", values=(world, f"{size_mb:.2f}", modified))
        except:
            pass
    
    def show_addons_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.add_back_button()
        
        tk.Label(self.content_frame, text="📦 插件/行为包管理", font=("Segoe UI", 24, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_purple']).pack(pady=10)
        
        main_panel = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        main_panel.pack(fill='both', expand=True, padx=10, pady=10)
        
        left_panel = tk.LabelFrame(main_panel, text="已安装行为包", font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        left_panel.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        self.addons_listbox = tk.Listbox(left_panel, bg=self.colors['bg_card'],
                                        font=("Segoe UI", 10), height=15)
        self.addons_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        right_panel = tk.LabelFrame(main_panel, text="操作", font=("Segoe UI", 12, "bold"),
                                    bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        right_panel.pack(side='right', fill='y', padx=5, pady=5, ipadx=30)
        
        def import_addon():
            filename = filedialog.askopenfilename(
                title="选择行为包/资源包",
                filetypes=[("Minecraft Addon", "*.mcaddon"), ("Minecraft Pack", "*.mcpack"), ("所有文件", "*.*")]
            )
            if filename:
                try:
                    dest = os.path.join(self.addons_folder, os.path.basename(filename))
                    shutil.copy2(filename, dest)
                    self.safe_log(f"已导入: {os.path.basename(filename)}")
                    self.refresh_addons_list()
                    messagebox.showinfo("导入成功", f"已导入: {os.path.basename(filename)}\n需要重启服务器生效")
                except Exception as e:
                    messagebox.showerror("导入失败", str(e))
        
        def delete_addon():
            selection = self.addons_listbox.curselection()
            if selection:
                addon = self.addons_listbox.get(selection[0])
                if messagebox.askyesno("确认", f"确定要删除 {addon} 吗？"):
                    try:
                        os.remove(os.path.join(self.addons_folder, addon))
                        self.refresh_addons_list()
                        self.safe_log(f"已删除: {addon}")
                    except Exception as e:
                        messagebox.showerror("删除失败", str(e))
        
        tk.Button(right_panel, text="导入行为包", command=import_addon,
                 bg=self.colors['accent_green'], fg='white', relief='flat', width=20, pady=5).pack(pady=10)
        tk.Button(right_panel, text="删除选中", command=delete_addon,
                 bg=self.colors['accent_red'], fg='white', relief='flat', width=20, pady=5).pack(pady=5)
        tk.Button(right_panel, text="刷新列表", command=self.refresh_addons_list,
                 bg=self.colors['accent_blue'], fg='white', relief='flat', width=20, pady=5).pack(pady=5)
        
        info_frame = tk.LabelFrame(right_panel, text="说明", font=("Segoe UI", 11, "bold"),
                                   bg=self.colors['bg_dark'], fg=self.colors['text_dark'])
        info_frame.pack(fill='x', pady=20)
        
        tk.Label(info_frame, text="支持的文件格式:\n.mcaddon (行为包/资源包)\n.mcpack (资源包)\n\n导入后需要重启服务器生效",
                bg=self.colors['bg_dark'], fg=self.colors['text_gray'], justify='left').pack(padx=10, pady=10)
        
        self.refresh_addons_list()
    
    def refresh_addons_list(self):
        try:
            if self.addons_listbox and self.addons_listbox.winfo_exists():
                self.addons_listbox.delete(0, tk.END)
                if os.path.exists(self.addons_folder):
                    for addon in os.listdir(self.addons_folder):
                        if addon.endswith(('.mcaddon', '.mcpack')):
                            self.addons_listbox.insert(tk.END, addon)
        except:
            pass
    
    def show_player_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.add_back_button()
        
        tk.Label(self.content_frame, text="👥 玩家管理", font=("Segoe UI", 24, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_orange']).pack(pady=10)
        
        main_panel = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        main_panel.pack(fill='both', expand=True, padx=10, pady=10)
        
        online_frame = tk.LabelFrame(main_panel, text="🟢 在线玩家", font=("Segoe UI", 12, "bold"),
                                     bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        online_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        online_list_frame = tk.Frame(online_frame, bg=self.colors['bg_card'])
        online_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.online_listbox = tk.Listbox(online_list_frame, bg=self.colors['bg_card'],
                                        font=("Segoe UI", 11), height=15)
        self.online_listbox.pack(side='left', fill='both', expand=True)
        
        online_scroll = tk.Scrollbar(online_list_frame, orient="vertical", command=self.online_listbox.yview)
        online_scroll.pack(side='right', fill='y')
        self.online_listbox.configure(yscrollcommand=online_scroll.set)
        
        self.online_count_label = tk.Label(online_frame, text="在线人数: 0", font=("Segoe UI", 10),
                                          bg=self.colors['bg_card'], fg=self.colors['accent_green'])
        self.online_count_label.pack(pady=5)
        
        op_frame = tk.Frame(main_panel, bg=self.colors['bg_main'])
        op_frame.pack(side='right', padx=10, fill='y')
        
        tk.Button(op_frame, text="👢 踢出玩家", command=self.kick_player,
                 bg=self.colors['accent_yellow'], fg=self.colors['text_dark'], 
                 relief='flat', width=12, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        tk.Button(op_frame, text="🔨 封禁玩家", command=self.ban_player,
                 bg=self.colors['accent_red'], fg='white', relief='flat', 
                 width=12, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        tk.Button(op_frame, text="👑 设为OP", command=self.set_op,
                 bg=self.colors['accent_green'], fg='white', relief='flat', 
                 width=12, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        tk.Button(op_frame, text="🔄 刷新列表", command=self.refresh_players,
                 bg=self.colors['accent_blue'], fg='white', relief='flat', 
                 width=12, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        tk.Button(op_frame, text="📋 查询日志", command=self.query_player_logs,
                 bg=self.colors['accent_purple'], fg='white', relief='flat', 
                 width=12, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        
        self.refresh_players()
    
    def show_blacklist_management(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.add_back_button()
        
        tk.Label(self.content_frame, text="🚫 玩家黑名单", font=("Segoe UI", 24, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_red']).pack(pady=10)
        
        main_panel = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        main_panel.pack(fill='both', expand=True, padx=10, pady=10)
        
        list_frame = tk.LabelFrame(main_panel, text="黑名单列表", font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        list_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        columns = ("name", "reason", "time")
        self.blacklist_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        self.blacklist_tree.heading("name", text="玩家名称")
        self.blacklist_tree.heading("reason", text="封禁原因")
        self.blacklist_tree.heading("time", text="封禁时间")
        self.blacklist_tree.column("name", width=150)
        self.blacklist_tree.column("reason", width=200)
        self.blacklist_tree.column("time", width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.blacklist_tree.yview)
        self.blacklist_tree.configure(yscrollcommand=scrollbar.set)
        self.blacklist_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')
        
        op_frame = tk.Frame(main_panel, bg=self.colors['bg_main'])
        op_frame.pack(side='right', padx=10, fill='y')
        
        def add_to_blacklist():
            player = simpledialog.askstring("添加黑名单", "请输入要封禁的玩家名称:")
            if player:
                reason = simpledialog.askstring("封禁原因", f"请输入封禁 {player} 的原因:")
                if reason:
                    self.blacklist.append({"name": player, "reason": reason, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    self.save_all_configs()
                    self.refresh_blacklist()
                    self.send_command(f"ban {player} {reason}")
                    self.safe_log(f"已添加黑名单: {player}")
                    messagebox.showinfo("成功", f"已添加 {player} 到黑名单")
        
        def remove_from_blacklist():
            selection = self.blacklist_tree.selection()
            if selection:
                idx = int(selection[0])
                player = self.blacklist[idx].get("name")
                if messagebox.askyesno("确认", f"确定要解除 {player} 的封禁吗？"):
                    self.blacklist.pop(idx)
                    self.save_all_configs()
                    self.refresh_blacklist()
                    self.send_command(f"unban {player}")
                    self.safe_log(f"已解除封禁: {player}")
                    messagebox.showinfo("成功", f"已解除 {player} 的封禁")
        
        tk.Button(op_frame, text="➕ 添加黑名单", command=add_to_blacklist,
                 bg=self.colors['accent_green'], fg='white', relief='flat', 
                 width=15, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        tk.Button(op_frame, text="❌ 移除黑名单", command=remove_from_blacklist,
                 bg=self.colors['accent_red'], fg='white', relief='flat', 
                 width=15, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        tk.Button(op_frame, text="🔄 刷新列表", command=self.refresh_blacklist,
                 bg=self.colors['accent_blue'], fg='white', relief='flat', 
                 width=15, pady=8, font=("Segoe UI", 10)).pack(pady=5)
        
        self.refresh_blacklist()
    
    def refresh_blacklist(self):
        if hasattr(self, 'blacklist_tree') and self.blacklist_tree.winfo_exists():
            for item in self.blacklist_tree.get_children():
                self.blacklist_tree.delete(item)
            for i, player in enumerate(self.blacklist):
                self.blacklist_tree.insert("", "end", iid=str(i), values=(
                    player.get("name", "未知"),
                    player.get("reason", "无"),
                    player.get("time", "未知")
                ))
    
    def show_main_console(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.add_back_button()
        
        tk.Label(self.content_frame, text="🎮 主控制台", font=("Segoe UI", 24, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_blue']).pack(pady=10)
        
        control_frame = tk.LabelFrame(self.content_frame, text="服务器控制", font=("Segoe UI", 12, "bold"),
                                      bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        control_frame.pack(fill='x', padx=10, pady=10)
        
        btn_frame = tk.Frame(control_frame, bg=self.colors['bg_card'])
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="启动服务器", command=self.start_server,
                                  font=("Segoe UI", 12), bg=self.colors['accent_green'],
                                  fg='white', width=12, relief='flat', cursor='hand2')
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="停止服务器", command=self.stop_server,
                                 font=("Segoe UI", 12), bg=self.colors['accent_red'],
                                 fg='white', width=12, relief='flat', state='disabled', cursor='hand2')
        self.stop_btn.pack(side='left', padx=5)
        
        self.restart_btn = tk.Button(btn_frame, text="重启服务器", command=self.restart_server,
                                    font=("Segoe UI", 12), bg=self.colors['accent_yellow'],
                                    fg='white', width=12, relief='flat', state='disabled', cursor='hand2')
        self.restart_btn.pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="同步状态", command=self.sync_server_status,
                 font=("Segoe UI", 12), bg=self.colors['accent_cyan'],
                 fg='white', width=12, relief='flat', cursor='hand2').pack(side='left', padx=5)
        
        self.uptime_label = tk.Label(control_frame, text="运行时间: --:--:--", font=("Segoe UI", 10),
                                    bg=self.colors['bg_card'], fg=self.colors['text_gray'])
        self.uptime_label.pack(pady=5)
        
        console_frame = tk.LabelFrame(self.content_frame, text="控制台输出", font=("Segoe UI", 12, "bold"),
                                      bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        console_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        console_toolbar = tk.Frame(console_frame, bg=self.colors['bg_card'])
        console_toolbar.pack(fill='x', padx=5, pady=5)
        
        def clear_console():
            if self.console and self.console.winfo_exists():
                self.console.delete(1.0, tk.END)
        
        tk.Button(console_toolbar, text="清空控制台", command=clear_console,
                 bg=self.colors['accent_red'], fg='white', relief='flat', cursor='hand2').pack(side='right')
        
        self.console = scrolledtext.ScrolledText(console_frame, bg=self.colors['console_bg'],
                                                  fg=self.colors['console_text'],
                                                  font=("Consolas", 10), wrap=tk.WORD)
        self.console.pack(fill='both', expand=True, padx=5, pady=5)
        
        cmd_frame = tk.Frame(console_frame, bg=self.colors['bg_card'])
        cmd_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(cmd_frame, text="命令:", font=("Segoe UI", 10),
                bg=self.colors['bg_card']).pack(side='left')
        
        self.cmd_entry = tk.Entry(cmd_frame, bg='white', font=("Consolas", 10),
                                  relief='solid', bd=1)
        self.cmd_entry.pack(side='left', padx=5, fill='x', expand=True)
        self.cmd_entry.bind('<Return>', lambda e: self.send_command())
        
        tk.Button(cmd_frame, text="发送", command=self.send_command,
                 bg=self.colors['accent_blue'], fg='white', relief='flat', cursor='hand2').pack(side='right')
    
    def show_server_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("服务器设置")
        settings_window.geometry("550x600")
        settings_window.configure(bg=self.colors['bg_main'])
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        tk.Label(settings_window, text="服务器设置", font=("Segoe UI", 18, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_blue']).pack(pady=15)
        
        main_frame = tk.Frame(settings_window, bg=self.colors['bg_card'], relief='ridge', bd=1)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        name_frame = tk.Frame(main_frame, bg=self.colors['bg_card'])
        name_frame.pack(fill='x', padx=15, pady=10)
        tk.Label(name_frame, text="服务器名称:", bg=self.colors['bg_card'], font=("Segoe UI", 11)).pack(side='left')
        name_entry = tk.Entry(name_frame, bg='white', font=("Segoe UI", 11), relief='solid', bd=1, width=25)
        name_entry.pack(side='left', padx=10)
        name_entry.insert(0, self.server_settings.get("server-name", "houukhhk-开服").replace("houukhhk-", ""))
        
        owner_frame = tk.Frame(main_frame, bg=self.colors['bg_card'])
        owner_frame.pack(fill='x', padx=15, pady=10)
        tk.Label(owner_frame, text="开服者名称:", bg=self.colors['bg_card'], font=("Segoe UI", 11)).pack(side='left')
        owner_entry = tk.Entry(owner_frame, bg='white', font=("Segoe UI", 11), relief='solid', bd=1, width=25)
        owner_entry.pack(side='left', padx=10)
        owner_entry.insert(0, self.server_owner)
        
        max_frame = tk.Frame(main_frame, bg=self.colors['bg_card'])
        max_frame.pack(fill='x', padx=15, pady=10)
        tk.Label(max_frame, text="最大玩家数:", bg=self.colors['bg_card'], font=("Segoe UI", 11)).pack(side='left')
        max_var = tk.StringVar(value=self.server_settings.get("max-players", "100"))
        tk.Spinbox(max_frame, from_=1, to=200, textvariable=max_var, width=8, font=("Segoe UI", 11)).pack(side='left', padx=10)
        
        tk.Frame(main_frame, bg=self.colors['bg_dark'], height=2).pack(fill='x', padx=15, pady=10)
        
        cheats_var = tk.BooleanVar(value=self.allow_cheats)
        cheat_frame = tk.Frame(main_frame, bg=self.colors['bg_card'])
        cheat_frame.pack(fill='x', padx=15, pady=10)
        tk.Checkbutton(cheat_frame, text="🔓 启用作弊模式", variable=cheats_var,
                      bg=self.colors['bg_card'], font=("Segoe UI", 11, "bold")).pack(side='left')
        
        tk.Label(main_frame, text="好友联机设置", font=("Segoe UI", 12, "bold"),
                bg=self.colors['bg_card']).pack(anchor='w', padx=15, pady=10)
        
        friend_var = tk.StringVar(value=self.friend_mode)
        
        tk.Radiobutton(main_frame, text="🔒 仅邀请", variable=friend_var, value="invite_only",
                      bg=self.colors['bg_card'], font=("Segoe UI", 10)).pack(anchor='w', padx=30, pady=3)
        tk.Radiobutton(main_frame, text="👥 仅好友", variable=friend_var, value="friends_only",
                      bg=self.colors['bg_card'], font=("Segoe UI", 10)).pack(anchor='w', padx=30, pady=3)
        tk.Radiobutton(main_frame, text="🌟 好友的好友", variable=friend_var, value="friends_of_friends",
                      bg=self.colors['bg_card'], font=("Segoe UI", 10)).pack(anchor='w', padx=30, pady=3)
        
        lan_var = tk.BooleanVar(value=self.server_settings.get("visible_to_lan", True))
        tk.Checkbutton(main_frame, text="📡 对局域网玩家可见", variable=lan_var,
                      bg=self.colors['bg_card'], font=("Segoe UI", 10)).pack(anchor='w', padx=30, pady=10)
        
        def save_settings():
            new_name = name_entry.get().strip()
            if new_name:
                if not new_name.startswith("houukhhk-"):
                    final_name = f"houukhhk-{new_name}"
                else:
                    final_name = new_name
                self.server_settings["server-name"] = final_name
                if self.server_name_label and self.server_name_label.winfo_exists():
                    self.server_name_label.config(text=f"🌐 {final_name}")
            
            self.server_owner = owner_entry.get().strip() or "houukhhk"
            
            try:
                max_players = int(max_var.get())
                if max_players > 200:
                    max_players = 200
                self.server_settings["max-players"] = str(max_players)
            except:
                pass
            
            self.allow_cheats = cheats_var.get()
            self.friend_mode = friend_var.get()
            self.server_settings["visible_to_lan"] = lan_var.get()
            
            self.save_all_configs()
            self.update_server_properties()
            
            messagebox.showinfo("保存成功", "设置已保存！\n重启服务器后完全生效")
            settings_window.destroy()
        
        tk.Button(settings_window, text="保存设置", command=save_settings,
                 bg=self.colors['accent_green'], fg='white', relief='flat', 
                 width=20, pady=8, font=("Segoe UI", 11)).pack(pady=15)
    
    def show_discord_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Discord Webhook 设置")
        settings_window.geometry("700x550")
        settings_window.configure(bg=self.colors['bg_main'])
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        tk.Label(settings_window, text="Discord Webhook 通知设置", font=("Segoe UI", 18, "bold"),
                bg=self.colors['bg_main'], fg=self.colors['accent_purple']).pack(pady=15)
        
        main_frame = tk.Frame(settings_window, bg=self.colors['bg_card'], relief='ridge', bd=1)
        main_frame.pack(fill='x', padx=20, pady=10)
        
        discord_enabled_var = tk.BooleanVar(value=self.discord_enabled)
        
        def toggle_discord():
            self.discord_enabled = discord_enabled_var.get()
            self.save_all_configs()
            self.safe_log(f"Discord通知已{'启用' if self.discord_enabled else '禁用'}")
        
        tk.Checkbutton(main_frame, text="启用Discord通知", variable=discord_enabled_var,
                      command=toggle_discord, bg=self.colors['bg_card'],
                      font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        list_frame = tk.LabelFrame(settings_window, text="Webhook列表", font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        columns = ("name", "url", "status")
        webhook_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=5)
        webhook_tree.heading("name", text="名称")
        webhook_tree.heading("url", text="Webhook URL")
        webhook_tree.heading("status", text="状态")
        webhook_tree.column("name", width=150)
        webhook_tree.column("url", width=380)
        webhook_tree.column("status", width=80)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=webhook_tree.yview)
        webhook_tree.configure(yscrollcommand=scrollbar.set)
        webhook_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')
        
        def refresh_list():
            for item in webhook_tree.get_children():
                webhook_tree.delete(item)
            for i, webhook in enumerate(self.discord_webhooks):
                status = "启用" if webhook.get("enabled", True) else "禁用"
                url_display = webhook.get("url", "")[:50] + "..." if len(webhook.get("url", "")) > 50 else webhook.get("url", "")
                webhook_tree.insert("", "end", iid=str(i), values=(
                    webhook.get("name", f"Webhook {i+1}"),
                    url_display,
                    status
                ))
        
        refresh_list()
        
        edit_frame = tk.LabelFrame(settings_window, text="添加/编辑Webhook", font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg_card'], fg=self.colors['text_dark'])
        edit_frame.pack(fill='x', padx=20, pady=10)
        
        name_frame = tk.Frame(edit_frame, bg=self.colors['bg_card'])
        name_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(name_frame, text="名称:", bg=self.colors['bg_card'], width=8).pack(side='left')
        webhook_name_entry = tk.Entry(name_frame, bg='white', font=("Segoe UI", 10), relief='solid', bd=1)
        webhook_name_entry.pack(side='left', fill='x', expand=True)
        
        url_frame = tk.Frame(edit_frame, bg=self.colors['bg_card'])
        url_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(url_frame, text="URL:", bg=self.colors['bg_card'], width=8).pack(side='left')
        webhook_url_entry = tk.Entry(url_frame, bg='white', font=("Segoe UI", 10), relief='solid', bd=1)
        webhook_url_entry.pack(side='left', fill='x', expand=True)
        
        def add_webhook():
            name = webhook_name_entry.get().strip()
            url = webhook_url_entry.get().strip()
            if not url:
                messagebox.showwarning("警告", "请输入Webhook URL")
                return
            if not name:
                name = f"Webhook {len(self.discord_webhooks) + 1}"
            self.discord_webhooks.append({"name": name, "url": url, "enabled": True})
            self.save_all_configs()
            refresh_list()
            webhook_name_entry.delete(0, tk.END)
            webhook_url_entry.delete(0, tk.END)
            self.safe_log(f"已添加Discord Webhook: {name}")
            messagebox.showinfo("成功", f"已添加Webhook: {name}")
        
        def delete_webhook():
            selection = webhook_tree.selection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个Webhook")
                return
            idx = int(selection[0])
            name = self.discord_webhooks[idx].get("name", "未知")
            if messagebox.askyesno("确认", f"确定要删除Webhook '{name}' 吗？"):
                self.discord_webhooks.pop(idx)
                self.save_all_configs()
                refresh_list()
                webhook_name_entry.delete(0, tk.END)
                webhook_url_entry.delete(0, tk.END)
                self.safe_log(f"已删除Webhook: {name}")
        
        def test_webhook():
            selection = webhook_tree.selection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个Webhook")
                return
            idx = int(selection[0])
            webhook = self.discord_webhooks[idx]
            try:
                data = {"content": "测试消息：服务器管理器连接成功！🎮", "username": "Minecraft服务器管家"}
                response = requests.post(webhook["url"], json=data, timeout=10)
                if response.status_code in [204, 200]:
                    messagebox.showinfo("成功", f"测试消息已发送到 {webhook.get('name', 'Webhook')}！")
                    self.safe_log(f"测试消息发送成功: {webhook.get('name')}")
                else:
                    messagebox.showerror("失败", f"发送失败: HTTP {response.status_code}")
                    self.safe_log(f"测试消息发送失败: HTTP {response.status_code}")
            except Exception as e:
                messagebox.showerror("失败", f"发送失败: {str(e)}")
                self.safe_log(f"测试消息发送异常: {e}")
        
        def on_select(event):
            selection = webhook_tree.selection()
            if selection:
                idx = int(selection[0])
                if idx < len(self.discord_webhooks):
                    webhook = self.discord_webhooks[idx]
                    webhook_name_entry.delete(0, tk.END)
                    webhook_name_entry.insert(0, webhook.get("name", ""))
                    webhook_url_entry.delete(0, tk.END)
                    webhook_url_entry.insert(0, webhook.get("url", ""))
        
        webhook_tree.bind('<<TreeviewSelect>>', on_select)
        
        btn_frame = tk.Frame(edit_frame, bg=self.colors['bg_card'])
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(btn_frame, text="添加", command=add_webhook,
                 bg=self.colors['accent_green'], fg='white', relief='flat', width=10).pack(side='left', padx=5)
        tk.Button(btn_frame, text="删除", command=delete_webhook,
                 bg=self.colors['accent_red'], fg='white', relief='flat', width=10).pack(side='left', padx=5)
        tk.Button(btn_frame, text="测试", command=test_webhook,
                 bg=self.colors['accent_yellow'], fg='white', relief='flat', width=10).pack(side='left', padx=5)
        
        tk.Button(settings_window, text="关闭", command=settings_window.destroy,
                 bg=self.colors['accent_cyan'], fg='white', relief='flat', width=15).pack(pady=15)
    
    def sync_server_status(self):
        if self.server_process:
            try:
                poll_result = self.server_process.poll()
                if poll_result is None:
                    if not self.server_running:
                        self.server_running = True
                        if not self.start_time:
                            self.start_time = time.time()
                        self.update_ui_state()
                        self.safe_log("状态已同步：服务器运行中")
                        messagebox.showinfo("同步成功", "服务器状态已更新为在线")
                    else:
                        messagebox.showinfo("状态正常", "服务器已经是在线状态")
                else:
                    if self.server_running:
                        self.server_running = False
                        self.update_ui_state()
                        self.safe_log("状态已同步：服务器已停止")
                        messagebox.showinfo("同步成功", "服务器状态已更新为离线")
                    else:
                        messagebox.showinfo("状态正常", "服务器已经是离线状态")
            except:
                pass
        else:
            messagebox.showwarning("无法同步", "没有找到服务器进程，请先启动服务器")
    
    # ==================== 玩家管理功能 ====================
    
    def kick_player(self):
        if self.online_listbox:
            selection = self.online_listbox.curselection()
            if selection:
                player = self.online_listbox.get(selection[0])
                reason = simpledialog.askstring("踢出玩家", f"踢出 {player} 的原因:")
                if reason:
                    self.send_command(f"kick {player} {reason}")
                    self.safe_log(f"已踢出玩家: {player}")
    
    def ban_player(self):
        if self.online_listbox:
            selection = self.online_listbox.curselection()
            if selection:
                player = self.online_listbox.get(selection[0])
                reason = simpledialog.askstring("封禁玩家", f"封禁 {player} 的原因:")
                if reason:
                    self.send_command(f"ban {player} {reason}")
                    if player not in [p.get("name") for p in self.blacklist]:
                        self.blacklist.append({"name": player, "reason": reason, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                        self.save_all_configs()
                        self.refresh_blacklist()
                    self.safe_log(f"已封禁玩家: {player}")
                    self.refresh_players()
    
    def set_op(self):
        if self.online_listbox:
            selection = self.online_listbox.curselection()
            if selection:
                player = self.online_listbox.get(selection[0])
                self.send_command(f"op {player}")
                self.safe_log(f"已给予 {player} OP权限")
    
    def refresh_players(self):
        if self.server_running:
            self.send_command("list")
    
    def parse_player_list(self, line):
        try:
            match = re.search(r'There are (\d+) of \d+ players online:(.*)', line)
            if match:
                players_str = match.group(2).strip()
                self.online_players = [p.strip() for p in players_str.split(',')] if players_str else []
                
                if self.online_listbox and self.online_listbox.winfo_exists():
                    self.online_listbox.delete(0, tk.END)
                    for player in self.online_players:
                        self.online_listbox.insert(tk.END, player)
                    if self.online_count_label:
                        self.online_count_label.config(text=f"在线人数: {len(self.online_players)}")
        except:
            pass
    
    def query_player_logs(self):
        if self.online_listbox:
            selection = self.online_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个在线玩家")
                return
            
            player = self.online_listbox.get(selection[0])
            
            log_window = tk.Toplevel(self.root)
            log_window.title(f"玩家日志 - {player}")
            log_window.geometry("800x500")
            log_window.configure(bg=self.colors['bg_main'])
            
            tk.Label(log_window, text=f"玩家 {player} 的日志", font=("Segoe UI", 16, "bold"),
                    bg=self.colors['bg_main'], fg=self.colors['accent_purple']).pack(pady=10)
            
            log_text = scrolledtext.ScrolledText(log_window, bg=self.colors['console_bg'],
                                                  fg=self.colors['console_text'],
                                                  font=("Consolas", 10), wrap=tk.WORD)
            log_text.pack(fill='both', expand=True, padx=10, pady=10)
            
            player_logs = []
            for log in self.all_logs:
                if player in log:
                    player_logs.append(log)
            
            if player_logs:
                for log in player_logs[-200:]:
                    log_text.insert(tk.END, log)
            else:
                log_text.insert(tk.END, f"没有找到玩家 {player} 的相关日志")
            
            log_text.see(tk.END)
            log_text.config(state='disabled')
    
    # ==================== 服务器核心功能 ====================
    
    def start_server(self):
        if not os.path.exists(self.server_exe):
            messagebox.showerror("错误", "找不到服务器文件")
            return
        
        try:
            server_dir = os.path.dirname(self.server_exe)
            os.chdir(server_dir)
            
            self.update_server_properties()
            
            if sys.platform == "win32":
                self.server_process = subprocess.Popen(
                    [self.server_exe],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.server_process = subprocess.Popen(
                    [self.server_exe],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace'
                )
            
            self.server_running = True
            self.start_time = time.time()
            self.update_ui_state()
            self.safe_log("✅ 服务器启动成功！")
            
            # 发送启动通知
            start_msg = f"**服务器已启动**\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n本机IP: {self.local_ip}\n服务器: {self.server_settings.get('server-name', 'houukhhk-开服')}"
            if self.public_ip:
                start_msg += f"\n外网IP: {self.public_ip}:19132"
            self.send_discord_message(start_msg)
            
            threading.Thread(target=self.read_output, daemon=True).start()
            
        except Exception as e:
            self.server_running = False
            self.safe_log(f"❌ 启动失败: {e}")
            messagebox.showerror("启动失败", str(e))
    
    def read_output(self):
        while self.server_running and self.server_process:
            try:
                if self.server_process.stdout:
                    line = self.server_process.stdout.readline()
                    if not line:
                        break
                    
                    line = line.rstrip('\n\r')
                    if line:
                        line_lower = line.lower()
                        
                        # 过滤list命令响应
                        if "players online:" in line_lower:
                            self.parse_player_list(line)
                            continue
                        
                        self.safe_log(line)
                        
                        if "server started" in line_lower or "ipv4 supported" in line_lower:
                            self.safe_log("=" * 50)
                            self.safe_log("✅ 服务器已完全启动！")
                            self.safe_log("=" * 50)
                        
                        if "joined the game" in line_lower:
                            self.play_sound('player_join')
                            match = re.search(r'(.+?) joined the game', line, re.IGNORECASE)
                            if match:
                                player = match.group(1).strip()
                                self.safe_log(f"🎉 玩家 {player} 加入了游戏")
                                self.send_discord_message(f"**{player}** 加入了游戏")
                                self.add_player_log(player, f"加入了游戏")
                            self.refresh_players()
                        
                        elif "left the game" in line_lower:
                            self.play_sound('player_leave')
                            match = re.search(r'(.+?) left the game', line, re.IGNORECASE)
                            if match:
                                player = match.group(1).strip()
                                self.safe_log(f"👋 玩家 {player} 离开了游戏")
                                self.send_discord_message(f"**{player}** 离开了游戏")
                                self.add_player_log(player, f"离开了游戏")
                            self.refresh_players()
                        
                        elif "error" in line_lower or "failed" in line_lower:
                            self.safe_log(f"⚠️ {line}")
                            
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.safe_log(f"读取输出错误: {e}")
                break
        
        if self.server_running:
            self.server_running = False
            self.update_ui_state()
            self.safe_log("服务器已停止")
            self.send_discord_message(f"**服务器已关闭**\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def stop_server(self):
        """停止服务器 - 修复版"""
        if self.server_process and self.server_running:
            self.safe_log("正在停止服务器...")
            # 发送停止命令
            self.send_command("stop")
            
            def wait_for_stop():
                # 等待最多10秒
                for _ in range(10):
                    time.sleep(1)
                    if self.server_process.poll() is not None:
                        self.server_running = False
                        self.update_ui_state()
                        self.safe_log("服务器已停止")
                        self.send_discord_message(f"**服务器已关闭**\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        return
                
                # 如果10秒后还没停止，强制结束
                if self.server_running:
                    self.safe_log("服务器未响应，强制结束进程...")
                    try:
                        self.server_process.terminate()
                        time.sleep(2)
                        if self.server_process.poll() is None:
                            self.server_process.kill()
                        self.server_running = False
                        self.update_ui_state()
                        self.safe_log("已强制结束服务器进程")
                    except:
                        pass
            
            threading.Thread(target=wait_for_stop, daemon=True).start()
    
    def restart_server(self):
        if self.server_running:
            self.stop_server()
            time.sleep(3)
        self.start_server()
    
    def send_command(self, cmd=None):
        if cmd is None:
            if self.cmd_entry and self.cmd_entry.winfo_exists():
                cmd = self.cmd_entry.get().strip()
            else:
                return
        if not cmd:
            return
        if not self.server_running:
            self.safe_log("服务器未运行")
            return
        try:
            if self.server_process and self.server_process.stdin:
                self.server_process.stdin.write(cmd + "\n")
                self.server_process.stdin.flush()
                self.safe_log(f">>> {cmd}")
                if self.cmd_entry and self.cmd_entry.winfo_exists():
                    self.cmd_entry.delete(0, tk.END)
        except Exception as e:
            self.safe_log(f"发送失败: {e}")
    
    def update_ui_state(self):
        def _update():
            try:
                if self.start_btn and self.start_btn.winfo_exists():
                    if self.server_running:
                        if self.status_label and self.status_label.winfo_exists():
                            self.status_label.config(text="● 在线", fg=self.colors['accent_green'])
                        self.start_btn.config(state='disabled')
                        if self.stop_btn:
                            self.stop_btn.config(state='normal')
                        if self.restart_btn:
                            self.restart_btn.config(state='normal')
                    else:
                        if self.status_label and self.status_label.winfo_exists():
                            self.status_label.config(text="● 离线", fg=self.colors['accent_red'])
                        self.start_btn.config(state='normal')
                        if self.stop_btn:
                            self.stop_btn.config(state='disabled')
                        if self.restart_btn:
                            self.restart_btn.config(state='disabled')
            except:
                pass
        try:
            self.root.after(0, _update)
        except:
            pass
    
    def add_back_button(self):
        back_frame = tk.Frame(self.content_frame, bg=self.colors['bg_main'])
        back_frame.pack(fill='x', pady=(0, 10))
        tk.Button(back_frame, text="← 返回主菜单", command=self.show_main_menu,
                 font=("Segoe UI", 10), bg=self.colors['accent_cyan'], fg='white',
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side='left')
    
    def get_folder_size(self, folder):
        total = 0
        for dirpath, dirnames, filenames in os.walk(folder):
            for filename in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, filename))
                except:
                    pass
        return total
    
    def on_closing(self):
        self.running = False
        self.save_all_configs()
        if self.server_running:
            self.stop_server()
            time.sleep(2)
        try:
            self.root.destroy()
        except:
            pass
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


if __name__ == "__main__":
    server = OnlineServerManager()
    try:
        server.run()
    except KeyboardInterrupt:
        server.running = False
        print("程序已退出")