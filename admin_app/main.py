"""
Hype HR Management — Admin Application
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from modules.auth import LoginWindow
from modules.roles import has_permission, get_role_display
from utils.local_cache import start_background_sync
import os

LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")


def _set_icon(window):
    if not os.path.exists(LOGO_PATH): return
    try:
        from PIL import Image, ImageTk
        icon_img   = Image.open(LOGO_PATH).resize((64, 64), Image.LANCZOS)
        icon_photo = ImageTk.PhotoImage(icon_img)
        window.iconphoto(True, icon_photo)
        window._icon_photo_ref = icon_photo
    except Exception:
        try: window.iconbitmap(LOGO_PATH)
        except Exception: pass


def launch_main_app(current_user):
    start_background_sync()
    root = tk.Tk()
    root.title(f"Hype HR — {get_role_display(current_user['role'])} Panel")
    root.geometry("1100x700")
    root.configure(bg="#0d1b2a")
    _set_icon(root)

    # ─ Header
    header = tk.Frame(root, bg="#1a2740", height=56)
    header.pack(fill="x")
    header.pack_propagate(False)

    if os.path.exists(LOGO_PATH):
        try:
            from PIL import Image, ImageTk
            logo_img   = Image.open(LOGO_PATH).resize((36, 36), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_img)
            logo_lbl   = tk.Label(header, image=logo_photo, bg="#1a2740", bd=0)
            logo_lbl.image = logo_photo
            logo_lbl.pack(side="left", padx=(10, 4), pady=10)
        except Exception: pass

    tk.Label(header, text="HYPE HR MANAGEMENT",
             font=("Arial", 15, "bold"), bg="#1a2740", fg="#f0c040").pack(side="left", padx=(2, 16))
    tk.Label(header,
             text=f"Logged in as: {current_user.get('display_name', current_user['username'])}  "
                  f"[{get_role_display(current_user['role'])}]",
             font=("Arial", 9), bg="#1a2740", fg="#888").pack(side="right", padx=16)
    sync_lbl = tk.Label(header, text="\u21bb Syncing...", bg="#1a2740",
                        fg="#f77f00", font=("Arial", 8))
    sync_lbl.pack(side="right", padx=8)
    root.after(4000, lambda: sync_lbl.config(text="☁ Synced", fg="#27ae60"))

    # ─ Notebook
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TNotebook",     background="#0d1b2a", borderwidth=0)
    style.configure("TNotebook.Tab", background="#1a2740", foreground="#ccc",
                    padding=[12, 6], font=("Arial", 10))
    style.map("TNotebook.Tab",
              background=[("selected", "#f77f00")],
              foreground=[("selected", "white")])

    nb   = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=8, pady=8)
    role = current_user.get("role", "manager")

    def add_tab(label, perm, builder_fn):
        if not has_permission(role, perm): return
        frame = tk.Frame(nb, bg="#0d1b2a")
        nb.add(frame, text=label)
        try:
            builder_fn(frame, current_user)
        except Exception as exc:
            import traceback; traceback.print_exc()
            tk.Label(frame,
                     text=f"❌ Error loading {label}:\n{exc}\n\nCheck terminal.",
                     bg="#0d1b2a", fg="#ff6666", font=("Arial", 10),
                     justify="left", wraplength=700).pack(padx=30, pady=40)

    def load_dashboard(f, u):
        from modules.dashboard import DashboardModule; DashboardModule(f, u)

    def load_employees(f, u):
        from modules.employees import EmployeePanel
        EmployeePanel(f, role=u.get("role","admin")).pack(fill="both", expand=True)

    def load_attendance(f, u):
        from modules.attendance import AttendanceModule; AttendanceModule(f, u)

    def load_salary(f, u):
        from modules.salary import SalaryPanel
        SalaryPanel(f, role=u.get("role","admin")).pack(fill="both", expand=True)

    def load_qr(f, u):
        from modules.qr_generator import QRGeneratorModule; QRGeneratorModule(f, u)

    def load_id_card(f, u):
        from modules.id_card import IdCardModule; IdCardModule(f, u)

    def load_security(f, u):
        from modules.security import SecurityModule; SecurityModule(f, u)

    def load_settings(f, u):
        from modules.settings import SettingsModule; SettingsModule(f, u)

    add_tab("🏠 Dashboard",   "dashboard",    load_dashboard)
    add_tab("👥 Employees",   "employees",    load_employees)
    add_tab("📅 Attendance",  "attendance",   load_attendance)
    add_tab("💰 Salary",      "salary",       load_salary)
    add_tab("🔳 QR Codes",    "qr_generator", load_qr)
    add_tab("🪚 ID Cards",    "id_card",      load_id_card)
    add_tab("🛡️ Security",   "security",     load_security)
    add_tab("⚙ Settings",    "settings",     load_settings)

    root.mainloop()


if __name__ == "__main__":
    LoginWindow(on_success_callback=launch_main_app)
