"""
Hype HR Management — Admin Application
Main entry point with role-based tab visibility
SQLite cache layer for fast reads (Firebase syncs in background)
Super Admin default login: admin.hype / Hype@2024#SuperAdmin
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk
from modules.auth import LoginWindow
from modules.roles import has_permission, get_role_display
from utils.local_cache import start_background_sync


def launch_main_app(current_user):
    # Start background Firebase → SQLite sync (runs every 2 min, daemon thread)
    start_background_sync()

    root = tk.Tk()
    root.title(f"Hype HR — {get_role_display(current_user['role'])} Panel")
    root.geometry("1100x680")
    root.configure(bg="#0d1b2a")

    # Header
    header = tk.Frame(root, bg="#1a2740", height=48)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(header, text="HYPE HR MANAGEMENT",
             font=("Arial", 15, "bold"), bg="#1a2740", fg="#f0c040").pack(side="left", padx=16)
    tk.Label(header,
             text=f"Logged in as: {current_user.get('display_name', current_user['username'])}  "
                  f"[{get_role_display(current_user['role'])}]",
             font=("Arial", 9), bg="#1a2740", fg="#888").pack(side="right", padx=16)

    # Sync status badge
    sync_lbl = tk.Label(header, text="↻ Syncing...", bg="#1a2740",
                         fg="#f77f00", font=("Arial", 8))
    sync_lbl.pack(side="right", padx=8)
    def update_sync_label():
        sync_lbl.config(text="☁ Synced", fg="#27ae60")
    root.after(4000, update_sync_label)  # show synced after 4s

    # Notebook (tabs visible based on role)
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TNotebook", background="#0d1b2a", borderwidth=0)
    style.configure("TNotebook.Tab", background="#1a2740", foreground="#ccc",
                    padding=[12, 6], font=("Arial", 10))
    style.map("TNotebook.Tab",
              background=[("selected", "#f77f00")],
              foreground=[("selected", "white")])

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=8, pady=8)
    role = current_user.get("role", "manager")

    def add_tab(label, perm, builder_fn):
        if has_permission(role, perm):
            frame = tk.Frame(nb, bg="#0d1b2a")
            nb.add(frame, text=label)
            builder_fn(frame, current_user)

    def load_dashboard(f, u):
        from modules.dashboard import DashboardModule
        DashboardModule(f, u)

    def load_employees(f, u):
        from modules.employees import EmployeeModule
        EmployeeModule(f, u)

    def load_attendance(f, u):
        from modules.attendance import AttendanceModule
        AttendanceModule(f, u)

    def load_salary(f, u):
        from modules.salary import SalaryModule
        SalaryModule(f, u)

    def load_qr(f, u):
        from modules.qr_generator import QRGeneratorModule
        QRGeneratorModule(f, u)

    def load_id_card(f, u):
        from modules.id_card import IdCardModule
        IdCardModule(f, u)

    def load_settings(f, u):
        from modules.settings import SettingsModule
        SettingsModule(f, u)

    add_tab("🏠 Dashboard",  "dashboard",    load_dashboard)
    add_tab("👥 Employees",  "employees",    load_employees)
    add_tab("📅 Attendance", "attendance",   load_attendance)
    add_tab("💰 Salary",     "salary",       load_salary)
    add_tab("🔳 QR Codes",   "qr_generator", load_qr)
    add_tab("🪪 ID Cards",   "id_card",      load_id_card)
    add_tab("⚙ Settings",   "settings",     load_settings)

    root.mainloop()


if __name__ == "__main__":
    LoginWindow(on_success_callback=launch_main_app)
