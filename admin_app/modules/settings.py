"""
Settings Module — Hype HR Management
Company Details + SMTP Email + Salary Rules + Admin User Management
+ Super Admin Rename / Company Rename
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from utils.db import read, write, update, read_all
from modules.roles import has_permission, get_all_roles, get_role_display


class SettingsModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.role = current_user.get("role", "admin")
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

        comp   = tk.Frame(nb, bg="#0d1b2a"); nb.add(comp,   text="🏢 Company")
        smtp   = tk.Frame(nb, bg="#0d1b2a"); nb.add(smtp,   text="📧 Email / SMTP")
        rules  = tk.Frame(nb, bg="#0d1b2a"); nb.add(rules,  text="💰 Salary Rules")
        users  = tk.Frame(nb, bg="#0d1b2a"); nb.add(users,  text="👥 Admin Users")
        me_tab = tk.Frame(nb, bg="#0d1b2a"); nb.add(me_tab, text="🔑 My Account")

        self._company_tab(comp)
        self._smtp_tab(smtp)
        self._rules_tab(rules)
        self._users_tab(users)
        self._my_account_tab(me_tab)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _entry_row(self, parent, row, label, key, show="", store=None):
        tk.Label(parent, text=label, bg="#0d1b2a", fg="#ccc",
                 font=("Arial", 10)).grid(row=row, column=0, sticky="w", padx=15, pady=7)
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=36, show=show
                 ).grid(row=row, column=1, padx=10, pady=7)
        if store is not None: store[key] = var
        return var

    # ── Company Tab ─────────────────────────────────────────────────────────
    def _company_tab(self, p):
        tk.Label(p, text="🏢 Company Information",
                 bg="#0d1b2a", fg="#f0c040",
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2,
                                                   sticky="w", padx=15, pady=(12, 4))
        labels = [
            ("Company Name *",             "name"),
            ("Company Address *",           "address"),
            ("Company Email",               "email"),
            ("Company Phone",               "phone"),
            ("Username Domain (e.g. hype)", "company_domain"),
            ("City",                        "city"),
            ("State",                       "state"),
            ("Country",                     "country"),
        ]
        for i, (l, k) in enumerate(labels, start=1):
            self._entry_row(p, i, l, k, store=self.fields)

        # Domain hint
        tk.Label(p,
                 text="ℹ Username domain is used in employee usernames: name.<domain>"
                      "\n  e.g. domain=nexuzy  →  rahul.nexuzy",
                 bg="#0d1b2a", fg="#666", font=("Arial", 8),
                 justify="left"
                 ).grid(row=9, column=0, columnspan=2, sticky="w", padx=15)

        tk.Button(p, text="💾 Save Company Info", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=15, pady=8, cursor="hand2",
                  command=self._save_company
                  ).grid(row=10, column=0, columnspan=2, pady=15, padx=15, sticky="ew")

    # ── SMTP Tab ─────────────────────────────────────────────────────────────
    def _smtp_tab(self, p):
        labels = [
            ("SMTP Host",            "smtp_host"),
            ("SMTP Port",            "smtp_port"),
            ("SMTP Username (email)","smtp_user"),
            ("SMTP Password",        "smtp_pass"),
            ("From Name",            "smtp_from_name"),
        ]
        for i, (l, k) in enumerate(labels):
            self._entry_row(p, i, l, k,
                            show="•" if k == "smtp_pass" else "",
                            store=self.smtp_fields)
        tk.Button(p, text="Test Connection", bg="#1e6f9f", fg="white", relief="flat",
                  padx=10, pady=6, cursor="hand2",
                  command=self._test_smtp).grid(row=8, column=0, pady=10, padx=15, sticky="w")
        tk.Button(p, text="💾 Save SMTP", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=15, pady=8, cursor="hand2",
                  command=self._save_smtp).grid(row=8, column=1, pady=10, padx=10)

    # ── Rules Tab ─────────────────────────────────────────────────────────────
    def _rules_tab(self, p):
        labels = [
            ("OT Rate Multiplier (e.g. 1.5)", "ot_rate_multiplier"),
            ("Default Payment Mode",          "default_payment_mode"),
            ("Monthly Working Days",           "monthly_working_days"),
        ]
        for i, (l, k) in enumerate(labels):
            self._entry_row(p, i, l, k, store=self.salary_rule_fields)
        tk.Button(p, text="💾 Save Rules", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=15, pady=8, cursor="hand2",
                  command=self._save_rules
                  ).grid(row=8, column=0, columnspan=2, pady=15, padx=15, sticky="ew")

    # ── Admin Users Tab ─────────────────────────────────────────────────────────
    def _users_tab(self, p):
        tk.Label(p, text="Admin / HR / CA / Manager Users",
                 bg="#0d1b2a", fg="#ccc", font=("Arial", 11, "bold")).pack(pady=10)

        cols = ("Username", "Display Name", "Role", "Status")
        self.users_tree = ttk.Treeview(p, columns=cols, show="headings", height=12)
        for col in cols:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=140, anchor="center")
        self.users_tree.pack(fill="both", expand=True, padx=10)
        self.users_tree.bind("<Double-1>", self._edit_user)

        bf = tk.Frame(p, bg="#0d1b2a")
        bf.pack(pady=5)
        tk.Button(bf, text="+ Add User",  bg="#f77f00", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2",
                  command=self._add_user).pack(side="left", padx=5)
        tk.Button(bf, text="Refresh", bg="#555", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2",
                  command=self._load_users).pack(side="left")
        tk.Label(p, text="Double-click a user to edit / deactivate / delete",
                 bg="#0d1b2a", fg="#444", font=("Arial", 8)).pack()
        self._load_users()

    # ── My Account Tab ────────────────────────────────────────────────────────
    def _my_account_tab(self, p):
        tk.Label(p, text="🔑 My Account",
                 bg="#0d1b2a", fg="#f0c040", font=("Arial", 12, "bold")
                 ).pack(pady=(15, 5), anchor="w", padx=20)

        frame = tk.Frame(p, bg="#1a2740", padx=20, pady=20)
        frame.pack(padx=20, pady=10, fill="x")

        cur_user = self.current_user
        tk.Label(frame, text=f"Username:  {cur_user.get('username','')} ",
                 bg="#1a2740", fg="#ccc", font=("Arial", 10)).grid(
                 row=0, column=0, columnspan=2, sticky="w", pady=4)
        tk.Label(frame, text=f"Role:      {get_role_display(cur_user.get('role',''))}",
                 bg="#1a2740", fg="#aaa", font=("Arial", 10)).grid(
                 row=1, column=0, columnspan=2, sticky="w", pady=4)

        # Password change
        tk.Label(frame, text="Current Password",
                 bg="#1a2740", fg="#ccc").grid(row=2, column=0, sticky="w", pady=6)
        self._old_pass = tk.Entry(frame, show="*", width=26, bg="#0d1b2a",
                                   fg="white", insertbackground="white", relief="flat", bd=4)
        self._old_pass.grid(row=2, column=1, pady=6)

        tk.Label(frame, text="New Password",
                 bg="#1a2740", fg="#ccc").grid(row=3, column=0, sticky="w", pady=6)
        self._new_pass = tk.Entry(frame, show="*", width=26, bg="#0d1b2a",
                                   fg="white", insertbackground="white", relief="flat", bd=4)
        self._new_pass.grid(row=3, column=1, pady=6)

        tk.Label(frame, text="Confirm New",
                 bg="#1a2740", fg="#ccc").grid(row=4, column=0, sticky="w", pady=6)
        self._cfm_pass = tk.Entry(frame, show="*", width=26, bg="#0d1b2a",
                                   fg="white", insertbackground="white", relief="flat", bd=4)
        self._cfm_pass.grid(row=4, column=1, pady=6)

        tk.Button(frame, text="🔒 Change Password", bg="#27ae60", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", padx=12, pady=6,
                  cursor="hand2", command=self._change_password
                  ).grid(row=5, column=0, columnspan=2, pady=12, sticky="ew")

        # Super admin: rename username
        if cur_user.get("role") in ("super_admin", "admin"):
            sep = tk.Frame(p, bg="#333", height=1)
            sep.pack(fill="x", padx=20, pady=5)

            tk.Label(p, text="✏️ Rename Admin Username",
                     bg="#0d1b2a", fg="#f0c040", font=("Arial", 11, "bold")
                     ).pack(anchor="w", padx=20, pady=(8, 2))
            tk.Label(p,
                     text="Change your login username (e.g. admin.hype → admin.nexuzy)\n"
                          "You will be asked to log in again after renaming.",
                     bg="#0d1b2a", fg="#666", font=("Arial", 8)
                     ).pack(anchor="w", padx=20)

            rf = tk.Frame(p, bg="#1a2740", padx=20, pady=12)
            rf.pack(padx=20, pady=6, fill="x")
            tk.Label(rf, text="New Username", bg="#1a2740", fg="#ccc").grid(
                row=0, column=0, sticky="w", pady=6)
            self._new_uname = tk.Entry(rf, width=26, bg="#0d1b2a",
                                        fg="white", insertbackground="white",
                                        relief="flat", bd=4)
            self._new_uname.grid(row=0, column=1, pady=6, padx=10)
            tk.Button(rf, text="Rename", bg="#8e44ad", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._rename_username
                      ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)

    # ── Load / Save ────────────────────────────────────────────────────────────
    def _load_settings(self):
        try:
            data = read("settings", "company") or {}
            for k, v in self.fields.items():             v.set(data.get(k, ""))
            for k, v in self.smtp_fields.items():        v.set(data.get(k, ""))
            for k, v in self.salary_rule_fields.items(): v.set(str(data.get(k, "")))
        except Exception as e:
            print(f"Settings load: {e}")

    def _save_company(self):
        data = {k: v.get().strip() for k, v in self.fields.items()}
        if not data.get("name"):
            messagebox.showerror("Error", "Company name is required.")
            return
        write("settings", "company", data, merge=True)
        messagebox.showinfo("Saved",
            f"Company info saved!\n\nCompany: {data['name']}\n"
            f"Domain: {data.get('company_domain','hype')}\n\n"
            "Employee usernames will use the new domain from now on.")

    def _save_smtp(self):
        data = {k: v.get().strip() for k, v in self.smtp_fields.items()}
        write("settings", "company", data, merge=True)
        messagebox.showinfo("Saved", "SMTP settings saved!")

    def _test_smtp(self):
        import smtplib
        host = self.smtp_fields["smtp_host"].get()
        port = int(self.smtp_fields["smtp_port"].get() or 587)
        user = self.smtp_fields["smtp_user"].get()
        pwd  = self.smtp_fields["smtp_pass"].get()
        try:
            with smtplib.SMTP(host, port) as s:
                s.starttls(); s.login(user, pwd)
            messagebox.showinfo("SMTP", "✅ Connection successful!")
        except Exception as e:
            messagebox.showerror("SMTP", f"Failed: {e}")

    def _save_rules(self):
        data = {k: v.get().strip() for k, v in self.salary_rule_fields.items()}
        write("settings", "company", data, merge=True)
        messagebox.showinfo("Saved", "Salary rules saved!")

    # ── Users ──────────────────────────────────────────────────────────────────
    def _load_users(self):
        for row in self.users_tree.get_children():
            self.users_tree.delete(row)
        for u in read_all("admin_users"):
            self.users_tree.insert("", "end", iid=u.get("username", ""), values=(
                u.get("username"), u.get("display_name", u.get("full_name", "")),
                get_role_display(u.get("role", "")),
                "Active" if u.get("active", True) else "Inactive"))

    def _add_user(self):
        self._user_dialog()

    def _edit_user(self, event):
        sel = self.users_tree.selection()
        if not sel: return
        username = sel[0]
        data = read("admin_users", username)
        if data:
            self._user_dialog(existing=data)

    def _user_dialog(self, existing: dict = None):
        is_edit = existing is not None
        d = tk.Toplevel(self.parent)
        d.title("Edit User" if is_edit else "Add Admin User")
        d.geometry("420x380")
        d.configure(bg="#0d1b2a")
        d.grab_set()

        flds = {}
        field_defs = [
            ("Username",    "username"),
            ("Password",    "password"),
            ("Display Name","display_name"),
        ]
        for i, (label, key) in enumerate(field_defs):
            tk.Label(d, text=label, bg="#0d1b2a", fg="#ccc").grid(
                row=i, column=0, padx=15, pady=8, sticky="w")
            var = tk.StringVar(value=existing.get(key, "") if is_edit and key != "password" else "")
            e = tk.Entry(d, textvariable=var, bg="#1e3a5f", fg="white",
                         insertbackground="white",
                         show="*" if key == "password" else "")
            e.grid(row=i, column=1, padx=10, pady=8)
            flds[key] = var
            if is_edit and key == "username":
                e.config(state="disabled")  # can't rename from here, use My Account

        tk.Label(d, text="Role", bg="#0d1b2a", fg="#ccc").grid(
            row=3, column=0, padx=15, pady=8, sticky="w")
        role_var = tk.StringVar(value=existing.get("role", "hr") if is_edit else "hr")
        ttk.Combobox(d, textvariable=role_var,
                     values=[r for r in get_all_roles() if r != "super_admin"]
                     ).grid(row=3, column=1, padx=10, pady=8)

        tk.Label(d, text="Status", bg="#0d1b2a", fg="#ccc").grid(
            row=4, column=0, padx=15, pady=8, sticky="w")
        status_var = tk.BooleanVar(value=existing.get("active", True) if is_edit else True)
        ttk.Checkbutton(d, text="Active", variable=status_var).grid(
            row=4, column=1, padx=10, sticky="w")

        def save():
            import hashlib
            u    = (existing["username"] if is_edit else flds["username"].get().strip())
            pwd  = flds["password"].get().strip()
            name = flds["display_name"].get().strip()
            if not u:
                messagebox.showerror("Error", "Username required.", parent=d)
                return
            data = {
                "username":     u,
                "display_name": name,
                "role":         role_var.get(),
                "active":       status_var.get(),
            }
            if pwd:
                data["password_hash"] = hashlib.sha256(pwd.encode()).hexdigest()
                data["must_change_password"] = False
            write("admin_users", u, data, merge=True)
            messagebox.showinfo("Saved", "User saved!", parent=d)
            d.destroy()
            self._load_users()

        action_lbl = "Update User" if is_edit else "Create User"
        tk.Button(d, text=action_lbl, bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=15, pady=8, cursor="hand2", command=save
                  ).grid(row=8, column=0, columnspan=2, pady=15, padx=15, sticky="ew")

    # ── My Account Actions ────────────────────────────────────────────────────────
    def _change_password(self):
        import hashlib
        old = self._old_pass.get()
        new = self._new_pass.get()
        cfm = self._cfm_pass.get()
        if len(new) < 8:
            messagebox.showerror("Error", "New password must be at least 8 characters.")
            return
        if new != cfm:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        existing = read("admin_users", self.current_user["username"]) or {}
        if existing.get("password_hash") != hashlib.sha256(old.encode()).hexdigest():
            messagebox.showerror("Error", "Current password is incorrect.")
            return
        update("admin_users", self.current_user["username"], {
            "password_hash": hashlib.sha256(new.encode()).hexdigest(),
            "must_change_password": False
        })
        messagebox.showinfo("Success", "✅ Password updated. Please log in again.")
        self._old_pass.delete(0, "end")
        self._new_pass.delete(0, "end")
        self._cfm_pass.delete(0, "end")

    def _rename_username(self):
        new_name = self._new_uname.get().strip()
        if not new_name:
            messagebox.showerror("Error", "Enter a new username."); return
        if not messagebox.askyesno("Confirm Rename",
                f"Rename '{self.current_user['username']}' → '{new_name}'?\n"
                "You will need to log in again with the new username."):
            return
        import hashlib
        existing = read("admin_users", self.current_user["username"]) or {}
        existing["username"] = new_name
        # Write new doc
        write("admin_users", new_name, existing)
        # Delete old doc
        from utils.db import delete
        delete("admin_users", self.current_user["username"])
        messagebox.showinfo("Renamed",
            f"✅ Username changed to '{new_name}'.\nPlease restart and log in with the new username.")
        # Close the whole app to force re-login
        self.parent.winfo_toplevel().destroy()
