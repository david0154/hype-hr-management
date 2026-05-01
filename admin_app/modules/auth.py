"""
Authentication Module — Hype HR Management

SUPER ADMIN LOGIN (default — change after first login):
  Username : admin.hype
  Password : Hype@2024#SuperAdmin

All admin users are stored in Firestore collection: admin_users
Password is hashed with SHA-256 before storage.
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import messagebox
import hashlib
from utils.firebase_config import get_db
from modules.roles import get_role_display, has_permission

# ── Default super admin (seeded to Firestore on first run) ───────────────────
SUPER_ADMIN_USERNAME = "admin.hype"
SUPER_ADMIN_PASSWORD = "Hype@2024#SuperAdmin"  # Change after first login!
SUPER_ADMIN_ROLE     = "super_admin"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def seed_super_admin():
    """Create default super-admin in Firestore if no admin users exist."""
    db = get_db()
    docs = list(db.collection("admin_users").limit(1).stream())
    if not docs:
        db.collection("admin_users").document(SUPER_ADMIN_USERNAME).set({
            "username":     SUPER_ADMIN_USERNAME,
            "display_name": "Super Administrator",
            "role":         SUPER_ADMIN_ROLE,
            "password_hash": _hash(SUPER_ADMIN_PASSWORD),
            "must_change_password": True,
            "active": True,
        })
        print("[AUTH] Super admin seeded:", SUPER_ADMIN_USERNAME)


def authenticate(username: str, password: str) -> dict | None:
    """Return user dict on success, None on failure."""
    db = get_db()
    doc = db.collection("admin_users").document(username.strip().lower()).get()
    if not doc.exists: return None
    user = doc.to_dict()
    if not user.get("active", False): return None
    if user.get("password_hash") != _hash(password): return None
    return user


class LoginWindow:
    def __init__(self, on_success_callback):
        self.on_success = on_success_callback
        self.root = tk.Tk()
        self.root.title("Hype HR — Admin Login")
        self.root.geometry("420x380")
        self.root.configure(bg="#0d1b2a")
        self.root.resizable(False, False)
        seed_super_admin()   # ensure at least one admin exists
        self._build_ui()
        self.root.mainloop()

    def _build_ui(self):
        tk.Label(self.root, text="HYPE HR MANAGEMENT",
                 font=("Arial", 16, "bold"), bg="#0d1b2a", fg="#f0c040").pack(pady=(30, 5))
        tk.Label(self.root, text="Admin Login",
                 font=("Arial", 11), bg="#0d1b2a", fg="#aaa").pack()

        frame = tk.Frame(self.root, bg="#1a2740", padx=30, pady=25)
        frame.pack(padx=30, pady=20, fill="x")

        tk.Label(frame, text="Username", bg="#1a2740", fg="#ccc",
                 font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=6)
        self.user_entry = tk.Entry(frame, width=28, font=("Arial", 11),
                                   bg="#0d1b2a", fg="white", insertbackground="white",
                                   relief="flat", bd=5)
        self.user_entry.grid(row=0, column=1, pady=6)

        tk.Label(frame, text="Password", bg="#1a2740", fg="#ccc",
                 font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=6)
        self.pass_entry = tk.Entry(frame, width=28, show="*", font=("Arial", 11),
                                   bg="#0d1b2a", fg="white", insertbackground="white",
                                   relief="flat", bd=5)
        self.pass_entry.grid(row=1, column=1, pady=6)
        self.pass_entry.bind("<Return>", lambda e: self._login())

        tk.Button(frame, text="Login", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=20, pady=6,
                  cursor="hand2", command=self._login).grid(
                  row=2, column=0, columnspan=2, pady=(15, 0))

        self.status_lbl = tk.Label(self.root, text="",
                                    bg="#0d1b2a", fg="#e74c3c", font=("Arial", 9))
        self.status_lbl.pack()

        # Default credentials reminder
        tk.Label(self.root,
                 text="Default: admin.hype / Hype@2024#SuperAdmin",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(pady=(5, 0))

    def _login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        if not username or not password:
            self.status_lbl.config(text="Please enter username and password.")
            return
        user = authenticate(username, password)
        if user:
            role_name = get_role_display(user.get("role", ""))
            if user.get("must_change_password"):
                messagebox.showwarning("Security",
                    "You are using the default password.\n"
                    "Please change it in Settings > My Account immediately!")
            self.root.destroy()
            self.on_success(user)
        else:
            self.status_lbl.config(text="❌ Invalid username or password.")
            self.pass_entry.delete(0, "end")


class ChangePasswordDialog:
    """Accessible from Settings > My Account for any logged-in user."""
    def __init__(self, parent, current_user):
        self.current_user = current_user
        win = tk.Toplevel(parent)
        win.title("Change Password")
        win.geometry("380x280")
        win.configure(bg="#0d1b2a")

        tk.Label(win, text="Change Your Password",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="#f0c040").pack(pady=15)

        frame = tk.Frame(win, bg="#1a2740", padx=20, pady=15)
        frame.pack(padx=20, fill="x")

        for i, (label, attr) in enumerate([
            ("Current Password", "old"),
            ("New Password",     "new"),
            ("Confirm New",      "confirm")
        ]):
            tk.Label(frame, text=label, bg="#1a2740", fg="#ccc").grid(
                row=i, column=0, sticky="w", pady=5)
            e = tk.Entry(frame, show="*", width=22, bg="#0d1b2a",
                         fg="white", insertbackground="white", relief="flat", bd=4)
            e.grid(row=i, column=1, pady=5)
            setattr(self, f"{attr}_entry", e)

        tk.Button(frame, text="Update Password", bg="#27ae60", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                  command=lambda: self._save(win)).grid(
                  row=3, column=0, columnspan=2, pady=10)

    def _save(self, win):
        old = self.old_entry.get()
        new = self.new_entry.get()
        cfm = self.confirm_entry.get()
        if len(new) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters.", parent=win)
            return
        if new != cfm:
            messagebox.showerror("Error", "Passwords do not match.", parent=win)
            return
        user = authenticate(self.current_user["username"], old)
        if not user:
            messagebox.showerror("Error", "Current password is incorrect.", parent=win)
            return
        try:
            db = get_db()
            db.collection("admin_users").document(self.current_user["username"]).update({
                "password_hash": _hash(new),
                "must_change_password": False
            })
            messagebox.showinfo("Success", "Password updated successfully!", parent=win)
            win.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=win)
