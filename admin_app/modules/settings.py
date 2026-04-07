"""
Settings Module — Hype HR Management
Company Details + SMTP Email + Salary Rules + Admin User Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from utils.firebase_config import get_db


class SettingsModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.db = get_db()
        self.fields = {}
        self.smtp_fields = {}
        self.salary_rule_fields = {}
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        tk.Label(self.parent, text="⚙ Settings",
                 font=("Arial", 14, "bold"), bg="#0d1b2a", fg="white").pack(pady=10, anchor="w", padx=15)
        nb = ttk.Notebook(self.parent)
        nb.pack(fill="both", expand=True, padx=10, pady=5)
        comp  = tk.Frame(nb, bg="#0d1b2a"); nb.add(comp,  text="🏢 Company")
        smtp  = tk.Frame(nb, bg="#0d1b2a"); nb.add(smtp,  text="📧 Email / SMTP")
        rules = tk.Frame(nb, bg="#0d1b2a"); nb.add(rules, text="💰 Salary Rules")
        users = tk.Frame(nb, bg="#0d1b2a"); nb.add(users, text="👥 Admin Users")
        self._company_tab(comp)
        self._smtp_tab(smtp)
        self._rules_tab(rules)
        self._users_tab(users)

    def _entry_row(self, parent, row, label, key, show=""):
        tk.Label(parent, text=label, bg="#0d1b2a", fg="#ccc",
                 font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=15, pady=7)
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=36, show=show).grid(row=row, column=1, padx=10, pady=7)
        return var

    def _company_tab(self, p):
        labels = [("Company Name *","name"),("Company Address *","address"),
                  ("Company Email","email"),("Company Phone","phone"),
                  ("Company Domain (e.g. hype)","company_domain"),
                  ("City","city"),("State","state"),("Country","country")]
        for i,(l,k) in enumerate(labels):
            self.fields[k] = self._entry_row(p, i, l, k)
        tk.Button(p, text="Save Company Info", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=15, pady=8, cursor="hand2",
                  command=self._save_company).grid(row=10, column=0, columnspan=2, pady=15, padx=15, sticky="ew")

    def _smtp_tab(self, p):
        labels = [("SMTP Host","smtp_host"),("SMTP Port","smtp_port"),
                  ("SMTP Username (email)","smtp_user"),("SMTP Password","smtp_pass"),
                  ("From Name","smtp_from_name")]
        for i,(l,k) in enumerate(labels):
            self.smtp_fields[k] = self._entry_row(p, i, l, k, show="•" if k=="smtp_pass" else "")
        tk.Button(p, text="Test Connection", bg="#1e6f9f", fg="white", relief="flat",
                  padx=10, pady=6, cursor="hand2", command=self._test_smtp).grid(row=8, column=0, pady=10, padx=15, sticky="w")
        tk.Button(p, text="Save SMTP", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=15, pady=8, cursor="hand2",
                  command=self._save_smtp).grid(row=8, column=1, pady=10, padx=10)

    def _rules_tab(self, p):
        labels = [("OT Rate Multiplier (e.g. 1.5)","ot_rate_multiplier"),
                  ("Default Payment Mode","default_payment_mode"),
                  ("Monthly Working Days","monthly_working_days")]
        for i,(l,k) in enumerate(labels):
            self.salary_rule_fields[k] = self._entry_row(p, i, l, k)
        tk.Button(p, text="Save Rules", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=15, pady=8, cursor="hand2",
                  command=self._save_rules).grid(row=8, column=0, columnspan=2, pady=15, padx=15, sticky="ew")

    def _users_tab(self, p):
        tk.Label(p, text="Admin / HR / CA / Manager Users",
                 bg="#0d1b2a", fg="#ccc", font=("Arial", 11, "bold")).pack(pady=10)
        cols = ("Username", "Role", "Status")
        self.users_tree = ttk.Treeview(p, columns=cols, show="headings", height=12)
        for col in cols:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=155, anchor="center")
        self.users_tree.pack(fill="both", expand=True, padx=10)
        bf = tk.Frame(p, bg="#0d1b2a"); bf.pack(pady=5)
        tk.Button(bf, text="+ Add User", bg="#f77f00", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2", command=self._add_user).pack(side="left", padx=5)
        tk.Button(bf, text="Refresh", bg="#555", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2", command=self._load_users).pack(side="left")
        self._load_users()

    def _load_settings(self):
        try:
            doc = self.db.collection("settings").document("company").get()
            if doc.exists:
                data = doc.to_dict()
                for k, v in self.fields.items():             v.set(data.get(k, ""))
                for k, v in self.smtp_fields.items():        v.set(data.get(k, ""))
                for k, v in self.salary_rule_fields.items(): v.set(str(data.get(k, "")))
        except Exception as e: print(f"Settings load: {e}")

    def _save_company(self):
        data = {k: v.get().strip() for k, v in self.fields.items()}
        if not data.get("name"): messagebox.showerror("Error", "Company name required."); return
        try:
            self.db.collection("settings").document("company").set(data, merge=True)
            messagebox.showinfo("Saved", "Company info saved!")
        except Exception as e: messagebox.showerror("Error", str(e))

    def _save_smtp(self):
        data = {k: v.get().strip() for k, v in self.smtp_fields.items()}
        try:
            self.db.collection("settings").document("company").set(data, merge=True)
            messagebox.showinfo("Saved", "SMTP settings saved!")
        except Exception as e: messagebox.showerror("Error", str(e))

    def _test_smtp(self):
        import smtplib
        host = self.smtp_fields["smtp_host"].get()
        port = int(self.smtp_fields["smtp_port"].get() or 587)
        user = self.smtp_fields["smtp_user"].get()
        pwd  = self.smtp_fields["smtp_pass"].get()
        try:
            with smtplib.SMTP(host, port) as s:
                s.starttls(); s.login(user, pwd)
            messagebox.showinfo("SMTP", "Connection successful!")
        except Exception as e: messagebox.showerror("SMTP", f"Failed: {e}")

    def _save_rules(self):
        data = {k: v.get().strip() for k, v in self.salary_rule_fields.items()}
        try:
            self.db.collection("settings").document("company").set(data, merge=True)
            messagebox.showinfo("Saved", "Salary rules saved!")
        except Exception as e: messagebox.showerror("Error", str(e))

    def _load_users(self):
        for row in self.users_tree.get_children(): self.users_tree.delete(row)
        try:
            for doc in self.db.collection("admin_users").stream():
                u = doc.to_dict()
                self.users_tree.insert("", "end", values=(
                    u.get("username"), u.get("role"),
                    "Active" if u.get("active", True) else "Inactive"))
        except Exception as e: print(f"Load users: {e}")

    def _add_user(self):
        d = tk.Toplevel(self.parent)
        d.title("Add Admin User"); d.geometry("400x300")
        d.configure(bg="#0d1b2a"); d.grab_set()
        flds = {}
        for i,(label,key) in enumerate([("Username","username"),("Password","password"),("Full Name","full_name")]):
            tk.Label(d, text=label, bg="#0d1b2a", fg="#ccc").grid(row=i, column=0, padx=15, pady=8, sticky="w")
            var = tk.StringVar()
            tk.Entry(d, textvariable=var, bg="#1e3a5f", fg="white",
                     insertbackground="white", show="•" if key=="password" else "").grid(row=i, column=1, padx=10, pady=8)
            flds[key] = var
        tk.Label(d, text="Role", bg="#0d1b2a", fg="#ccc").grid(row=3, column=0, padx=15, pady=8, sticky="w")
        role_var = tk.StringVar(value="hr")
        ttk.Combobox(d, textvariable=role_var, values=["admin","hr","ca","manager"]).grid(row=3, column=1, padx=10, pady=8)
        def save():
            import hashlib
            u = flds["username"].get().strip()
            p = flds["password"].get().strip()
            if not u or not p: messagebox.showerror("Error", "Username and password required.", parent=d); return
            try:
                self.db.collection("admin_users").document(u).set({
                    "username": u, "full_name": flds["full_name"].get().strip(),
                    "password_hash": hashlib.sha256(p.encode()).hexdigest(),
                    "role": role_var.get(), "active": True,
                    "company": self.current_user.get("company", "hype")
                })
                messagebox.showinfo("Success", "User created!", parent=d)
                d.destroy(); self._load_users()
            except Exception as e: messagebox.showerror("Error", str(e), parent=d)
        tk.Button(d, text="Create User", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=15, pady=8,
                  cursor="hand2", command=save).grid(row=8, column=0, columnspan=2, pady=15, padx=15, sticky="ew")
