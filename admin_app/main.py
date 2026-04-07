"""
Hype HR Management System — Admin Desktop App
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
GitHub: https://github.com/david0154
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from utils.firebase_config import init_firebase
from modules.auth import LoginWindow
from modules.dashboard import DashboardModule
from modules.employees import EmployeesModule
from modules.attendance import AttendanceModule
from modules.salary import SalaryModule
from modules.qr_generator import QRGeneratorModule
from modules.settings import SettingsModule
from modules.roles import has_permission


BG_DARK    = "#0d1b2a"
BG_SIDEBAR = "#111e2e"
BG_HEADER  = "#1a2740"
ACCENT     = "#f77f00"

MODULES = [
    ("🏠  Dashboard",    "dashboard",  "dashboard"),
    ("👥  Employees",    "employees",  "employees"),
    ("📋  Attendance",   "attendance", "attendance"),
    ("💰  Salary",       "salary",     "salary_view"),
    ("🔳  QR Generator", "qr",         "qr_generator"),
    ("⚙   Settings",    "settings",   "settings"),
]


class HypeHRApp:
    def __init__(self, root):
        self.root = root
        self.current_user = None
        self.root.title("Hype HR Management")
        self.root.geometry("1200x720")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG_DARK)
        self._show_login()

    def _show_login(self):
        for w in self.root.winfo_children():
            w.destroy()
        init_firebase()
        LoginWindow(self.root, self._on_login)

    def _on_login(self, user):
        self.current_user = user
        self._build_main_layout()
        self._switch_module("dashboard")

    def _build_main_layout(self):
        for w in self.root.winfo_children():
            w.destroy()

        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, pady=15)
        logo_frame.pack(fill="x")
        try:
            from PIL import Image, ImageTk
            logo_path = os.path.join(os.path.dirname(__file__), '../assets/logo.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path).resize((60, 60))
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(logo_frame, image=self._logo_img, bg=BG_SIDEBAR).pack()
        except Exception:
            pass
        tk.Label(logo_frame, text="HYPE HR", font=("Arial", 13, "bold"),
                 bg=BG_SIDEBAR, fg=ACCENT).pack()
        tk.Label(logo_frame, text="Management", font=("Arial", 8),
                 bg=BG_SIDEBAR, fg="#888").pack()

        tk.Frame(self.sidebar, bg="#2a3a4a", height=1).pack(fill="x", pady=5)

        role  = self.current_user.get("role", "admin")
        uname = self.current_user.get("username", "")
        tk.Label(self.sidebar, text=f"👤 {uname}", font=("Arial", 9, "bold"),
                 bg=BG_SIDEBAR, fg="white").pack(pady=(5, 0))
        tk.Label(self.sidebar, text=role.upper(), font=("Arial", 8),
                 bg=BG_SIDEBAR, fg=ACCENT).pack(pady=(0, 10))

        tk.Frame(self.sidebar, bg="#2a3a4a", height=1).pack(fill="x", pady=5)

        self.nav_buttons = {}
        for (label, key, perm) in MODULES:
            if has_permission(role, perm):
                btn = tk.Button(
                    self.sidebar, text=label, anchor="w",
                    font=("Arial", 10), bg=BG_SIDEBAR, fg="#ccc",
                    relief="flat", padx=15, pady=10, cursor="hand2",
                    command=lambda k=key: self._switch_module(k)
                )
                btn.pack(fill="x")
                self.nav_buttons[key] = btn

        tk.Frame(self.sidebar, bg="#2a3a4a", height=1).pack(fill="x", side="bottom", pady=5)
        tk.Button(self.sidebar, text="🔓 Logout", anchor="w", font=("Arial", 10),
                  bg=BG_SIDEBAR, fg="#ff6b6b", relief="flat", padx=15, pady=10,
                  cursor="hand2", command=self._logout).pack(fill="x", side="bottom")
        tk.Label(self.sidebar, text="Nexuzy Lab | nexuzylab@gmail.com",
                 font=("Arial", 7), bg=BG_SIDEBAR, fg="#444").pack(side="bottom", pady=2)

        self.content_frame = tk.Frame(self.root, bg=BG_DARK)
        self.content_frame.pack(side="right", fill="both", expand=True)

    def _switch_module(self, module_key):
        for key, btn in self.nav_buttons.items():
            btn.configure(bg=BG_SIDEBAR, fg="#ccc")
        if module_key in self.nav_buttons:
            self.nav_buttons[module_key].configure(bg=ACCENT, fg="white")

        for w in self.content_frame.winfo_children():
            w.destroy()

        role = self.current_user.get("role", "admin")
        if module_key == "dashboard":
            DashboardModule(self.content_frame, self.current_user)
        elif module_key == "employees":
            EmployeesModule(self.content_frame, self.current_user)
        elif module_key == "attendance":
            AttendanceModule(self.content_frame, self.current_user)
        elif module_key == "salary":
            SalaryModule(self.content_frame, self.current_user)
        elif module_key == "qr":
            QRGeneratorModule(self.content_frame, self.current_user)
        elif module_key == "settings":
            if has_permission(role, "settings"):
                SettingsModule(self.content_frame, self.current_user)
            else:
                tk.Label(self.content_frame, text="🚫 Access Denied",
                         font=("Arial", 18), bg=BG_DARK, fg="#ff4444").pack(expand=True)

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.current_user = None
            self._show_login()


if __name__ == "__main__":
    root = tk.Tk()
    app = HypeHRApp(root)
    root.mainloop()
