"""
Authentication Module — Hype HR Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import messagebox
import hashlib
from utils.firebase_config import get_db


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class LoginWindow:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.root.title("Hype HR Management — Login")
        self.root.geometry("420x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#0d1b2a")
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self.root, bg="#0d1b2a")
        frame.pack(expand=True, fill="both", padx=40, pady=30)

        tk.Label(frame, text="🏢", font=("Arial", 48), bg="#0d1b2a", fg="white").pack(pady=(0, 5))
        tk.Label(frame, text="HYPE HR MANAGEMENT",
                 font=("Arial", 16, "bold"), bg="#0d1b2a", fg="#f77f00").pack()
        tk.Label(frame, text="Admin Portal",
                 font=("Arial", 10), bg="#0d1b2a", fg="#aaa").pack(pady=(2, 25))

        tk.Label(frame, text="Username", font=("Arial", 10),
                 bg="#0d1b2a", fg="#ccc").pack(anchor="w")
        self.username_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.username_var, font=("Arial", 11),
                 bg="#1e3a5f", fg="white", insertbackground="white",
                 relief="flat", bd=8).pack(fill="x", pady=(2, 14))

        tk.Label(frame, text="Password", font=("Arial", 10),
                 bg="#0d1b2a", fg="#ccc").pack(anchor="w")
        self.password_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.password_var, show="•",
                 font=("Arial", 11), bg="#1e3a5f", fg="white",
                 insertbackground="white", relief="flat", bd=8).pack(fill="x", pady=(2, 22))

        tk.Button(frame, text="LOGIN", font=("Arial", 12, "bold"),
                  bg="#f77f00", fg="white", relief="flat", bd=0,
                  padx=20, pady=11, cursor="hand2",
                  command=self._do_login).pack(fill="x")

        tk.Label(frame,
                 text="Managed by Nexuzy Lab  |  nexuzylab@gmail.com",
                 font=("Arial", 8), bg="#0d1b2a", fg="#555").pack(side="bottom")

    def _do_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password.")
            return
        try:
            db = get_db()
            docs = db.collection("admin_users").where("username", "==", username).get()
            if not docs:
                messagebox.showerror("Error", "Invalid credentials.")
                return
            user = docs[0].to_dict()
            if user.get("password_hash") != hash_password(password):
                messagebox.showerror("Error", "Invalid credentials.")
                return
            if not user.get("active", True):
                messagebox.showerror("Error", "Account deactivated. Contact Admin.")
                return
            self.on_login_success(user)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Cannot connect to Firebase:\n{e}")
