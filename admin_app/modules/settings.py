# settings.py — Full Settings Panel (Hype HR Management)
# Tabs: Company | SMTP | SMS | Salary Rules | Attendance Rules | Bonus Dates | Admin Users | My Account
# Developed by David | Nexuzy Lab | nexuzylab@gmail.com

import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
from utils.db import read, write, update, delete, read_all
from utils.firebase_config import get_db
from modules.roles import get_all_roles, get_role_display, has_permission


RELIGIONS = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
PAYMENT_MODES  = ["CASH", "BANK TRANSFER", "UPI", "CHEQUE"]
ENCRYPTIONS    = ["TLS", "SSL", "NONE"]
SMS_PROVIDERS  = ["Fast2SMS", "MSG91", "Twilio", "Disabled"]


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class SettingsModule(tk.Frame):
    """Main settings panel — loaded by main.py as SettingsModule(frame, current_user)."""

    def __init__(self, parent_frame, current_user):
        super().__init__(parent_frame, bg="#0d1b2a")
        self.current_user = current_user
        self.role = current_user.get("role", "manager")
        self.pack(fill="both", expand=True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._company_tab(nb)
        self._smtp_tab(nb)
        self._sms_tab(nb)
        self._salary_rules_tab(nb)
        self._attendance_rules_tab(nb)
        self._bonus_dates_tab(nb)
        if self.role in ("super_admin", "admin"):
            self._admin_users_tab(nb)
        self._my_account_tab(nb)

    # ════════════════════════════════════════════════════════════
    # 1. COMPANY INFO
    # ════════════════════════════════════════════════════════════
    def _company_tab(self, nb):
        frm = self._tab(nb, " 🏢 Company ")
        data = read("settings", "company") or {}
        fields = [
            ("Company Name",      "company_name"),
            ("Address Line 1",    "address1"),
            ("Address Line 2",    "address2"),
            ("City / State",      "city_state"),
            ("PIN Code",          "pincode"),
            ("Country",           "country"),
            ("Company Email",     "email"),
            ("Phone / Mobile",    "phone"),
            ("Website",           "website"),
            ("GST Number",        "gst_number"),
            ("Username Domain",   "company_domain"),
        ]
        self._vars_company = self._field_group(frm, fields, data)
        self._save_btn(frm, "Company Info", self._save_company, "#27ae60")

    def _save_company(self):
        write("settings", "company", {k: v.get().strip() for k, v in self._vars_company.items()})
        messagebox.showinfo("Saved", "Company info saved.")

    # ════════════════════════════════════════════════════════════
    # 2. SMTP EMAIL
    # ════════════════════════════════════════════════════════════
    def _smtp_tab(self, nb):
        frm = self._tab(nb, " 📧 SMTP ")
        data = read("settings", "company") or {}
        fields = [
            ("SMTP Host",       "smtp_host"),
            ("SMTP Port",       "smtp_port"),
            ("Username",        "smtp_user"),
            ("Password",        "smtp_pass"),
            ("From Name",       "smtp_from_name"),
            ("Reply-To Email",  "smtp_reply_to"),
        ]
        self._vars_smtp = self._field_group(frm, fields, data, secret_keys=["smtp_pass"])

        # Encryption dropdown
        row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=3)
        tk.Label(row, text="Encryption:", width=20, anchor="w", bg=frm["bg"], fg="#ccc").pack(side="left")
        self._smtp_enc = tk.StringVar(value=data.get("smtp_encryption", "TLS"))
        ttk.Combobox(row, textvariable=self._smtp_enc, values=ENCRYPTIONS,
                     width=10, state="readonly").pack(side="left")

        tk.Button(frm, text="📨 Test SMTP Connection",
                  command=self._test_smtp,
                  bg="#1e6f9f", fg="white", padx=10, pady=3).pack(anchor="w", pady=(8, 2))
        self._save_btn(frm, "SMTP Settings", self._save_smtp, "#27ae60")

    def _save_smtp(self):
        existing = read("settings", "company") or {}
        existing.update({k: v.get().strip() for k, v in self._vars_smtp.items()})
        existing["smtp_encryption"] = self._smtp_enc.get()
        write("settings", "company", existing)
        messagebox.showinfo("Saved", "SMTP settings saved.")

    def _test_smtp(self):
        try:
            import smtplib
            host = self._vars_smtp["smtp_host"].get().strip()
            port = int(self._vars_smtp["smtp_port"].get().strip() or "587")
            user = self._vars_smtp["smtp_user"].get().strip()
            pwd  = self._vars_smtp["smtp_pass"].get().strip()
            enc  = self._smtp_enc.get()
            if enc == "SSL":
                s = smtplib.SMTP_SSL(host, port, timeout=8)
            else:
                s = smtplib.SMTP(host, port, timeout=8)
                if enc == "TLS":
                    s.starttls()
            s.login(user, pwd)
            s.quit()
            messagebox.showinfo("SMTP Test", "✅ Connection successful! SMTP is working.")
        except Exception as e:
            messagebox.showerror("SMTP Test Failed", f"❌ {e}")

    # ════════════════════════════════════════════════════════════
    # 3. SMS SETTINGS
    # ════════════════════════════════════════════════════════════
    def _sms_tab(self, nb):
        frm = self._tab(nb, " 📲 SMS ")
        data = read("settings", "sms") or {}

        row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=4)
        tk.Label(row, text="SMS Provider:", width=20, anchor="w", bg=frm["bg"], fg="#ccc").pack(side="left")
        self._sms_provider = tk.StringVar(value=data.get("provider", "Disabled"))
        ttk.Combobox(row, textvariable=self._sms_provider, values=SMS_PROVIDERS,
                     width=14, state="readonly").pack(side="left")

        fields = [
            ("API Key / Auth Token",  "sms_api_key"),
            ("Sender ID / From",      "sms_sender_id"),
            ("Account SID (Twilio)",  "sms_account_sid"),
            ("Route (Fast2SMS)",      "sms_route"),
            ("Template (optional)",   "sms_template"),
        ]
        self._vars_sms = self._field_group(frm, fields, data, secret_keys=["sms_api_key", "sms_account_sid"])

        # Toggles
        self._sms_on_salary  = tk.BooleanVar(value=data.get("send_on_salary",  True))
        self._sms_on_advance = tk.BooleanVar(value=data.get("send_on_advance", False))
        for var, text in [
            (self._sms_on_salary,  "Send SMS when salary slip is generated"),
            (self._sms_on_advance, "Send SMS when advance payment is recorded"),
        ]:
            tk.Checkbutton(frm, text=text, variable=var,
                           bg=frm["bg"], fg="#ccc", selectcolor="#1a2740",
                           activebackground=frm["bg"]).pack(anchor="w", pady=2)

        self._save_btn(frm, "SMS Settings", self._save_sms, "#27ae60")

    def _save_sms(self):
        data = {k: v.get().strip() for k, v in self._vars_sms.items()}
        data["provider"]        = self._sms_provider.get()
        data["send_on_salary"]  = self._sms_on_salary.get()
        data["send_on_advance"] = self._sms_on_advance.get()
        write("settings", "sms", data)
        messagebox.showinfo("Saved", "SMS settings saved.")

    # ════════════════════════════════════════════════════════════
    # 4. SALARY RULES
    # ════════════════════════════════════════════════════════════
    def _salary_rules_tab(self, nb):
        frm = self._tab(nb, " ⚙️ Salary Rules ")
        data = read("settings", "app") or {}
        fields = [
            ("Working Days / Month",       "working_days",          "26"),
            ("OT Multiplier  (e.g. 1.5)",  "ot_multiplier",         "1.5"),
            ("Bonus Min Days / Year",       "bonus_min_days",        "240"),
            ("Salary PDF Retention (mo)",   "salary_pdf_retention",  "12"),
        ]
        self._vars_rules = {}
        for label, key, default in fields:
            row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=4)
            tk.Label(row, text=label + ":", width=28, anchor="w",
                     bg=frm["bg"], fg="#ccc").pack(side="left")
            var = tk.StringVar(value=data.get(key, default))
            tk.Entry(row, textvariable=var, width=10,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
            self._vars_rules[key] = var

        # Payment mode dropdown
        row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=4)
        tk.Label(row, text="Default Payment Mode:", width=28, anchor="w",
                 bg=frm["bg"], fg="#ccc").pack(side="left")
        self._default_pay_mode = tk.StringVar(value=data.get("default_payment_mode", "CASH"))
        ttk.Combobox(row, textvariable=self._default_pay_mode, values=PAYMENT_MODES,
                     width=14, state="readonly").pack(side="left")

        # Toggles
        self._auto_deduct_advance = tk.BooleanVar(value=data.get("auto_deduct_advance", True))
        self._show_bonus_employee = tk.BooleanVar(value=data.get("show_bonus_employee", False))
        for var, text in [
            (self._auto_deduct_advance, "Auto-deduct advance from next salary"),
            (self._show_bonus_employee, "Show bonus amount in employee app (not recommended)"),
        ]:
            tk.Checkbutton(frm, text=text, variable=var,
                           bg=frm["bg"], fg="#ccc", selectcolor="#1a2740",
                           activebackground=frm["bg"]).pack(anchor="w", pady=2)

        self._save_btn(frm, "Salary Rules", self._save_rules, "#27ae60")

    def _save_rules(self):
        existing = read("settings", "app") or {}
        for k, v in self._vars_rules.items():
            existing[k] = v.get().strip()
        existing["default_payment_mode"] = self._default_pay_mode.get()
        existing["auto_deduct_advance"]   = self._auto_deduct_advance.get()
        existing["show_bonus_employee"]   = self._show_bonus_employee.get()
        write("settings", "app", existing)
        messagebox.showinfo("Saved", "Salary rules saved.")

    # ════════════════════════════════════════════════════════════
    # 5. ATTENDANCE RULES
    # ════════════════════════════════════════════════════════════
    def _attendance_rules_tab(self, nb):
        frm = self._tab(nb, " 📅 Attendance Rules ")
        data = read("settings", "attendance") or {}

        tk.Label(frm, text="Duty Day Classification",
                 font=("Helvetica", 10, "bold"), bg=frm["bg"], fg="#f0c040").pack(anchor="w", pady=(0, 4))

        duty_fields = [
            ("Full Day min hours  (e.g. 7)",  "full_day_hours",  "7"),
            ("Half Day min hours  (e.g. 4)",  "half_day_hours",  "4"),
        ]
        self._vars_att = {}
        for label, key, default in duty_fields:
            row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=30, anchor="w",
                     bg=frm["bg"], fg="#ccc").pack(side="left")
            var = tk.StringVar(value=data.get(key, default))
            tk.Entry(row, textvariable=var, width=6,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
            self._vars_att[key] = var

        tk.Label(frm, text="ℹ️ Below Half Day threshold = Absent (0 days credited)",
                 fg="#7f8c8d", bg=frm["bg"], font=("Helvetica", 8)).pack(anchor="w", pady=(0, 10))

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)
        tk.Label(frm, text="OT Classification",
                 font=("Helvetica", 10, "bold"), bg=frm["bg"], fg="#f0c040").pack(anchor="w", pady=(0, 4))

        ot_fields = [
            ("OT Full Day min hours  (e.g. 7)", "ot_full_hours", "7"),
            ("OT Half Day min hours  (e.g. 4)", "ot_half_hours", "4"),
        ]
        for label, key, default in ot_fields:
            row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=30, anchor="w",
                     bg=frm["bg"], fg="#ccc").pack(side="left")
            var = tk.StringVar(value=data.get(key, default))
            tk.Entry(row, textvariable=var, width=6,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
            self._vars_att[key] = var

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)
        tk.Label(frm, text="Sunday Pay Rule",
                 font=("Helvetica", 10, "bold"), bg=frm["bg"], fg="#f0c040").pack(anchor="w", pady=(0, 4))

        self._sunday_rule_enabled = tk.BooleanVar(value=data.get("sunday_rule_enabled", True))
        tk.Checkbutton(frm, text="Enable Sunday pay rule (Sat+Mon check)",
                       variable=self._sunday_rule_enabled,
                       bg=frm["bg"], fg="#ccc", selectcolor="#1a2740",
                       activebackground=frm["bg"]).pack(anchor="w", pady=2)

        tk.Label(frm,
                 text="  Sat ✅ + Mon ✅ → Full Sunday Pay\n"
                      "  Sat ✅ + Mon ❌ → Half Sunday Pay\n"
                      "  Sat ❌         → No Sunday Pay",
                 fg="#7f8c8d", bg=frm["bg"], font=("Helvetica", 9), justify="left"
                 ).pack(anchor="w", padx=12, pady=2)

        self._save_btn(frm, "Attendance Rules", self._save_attendance, "#27ae60")

    def _save_attendance(self):
        data = {k: v.get().strip() for k, v in self._vars_att.items()}
        data["sunday_rule_enabled"] = self._sunday_rule_enabled.get()
        write("settings", "attendance", data)
        messagebox.showinfo("Saved", "Attendance rules saved.")

    # ════════════════════════════════════════════════════════════
    # 6. BONUS DATES (per religion)
    # ════════════════════════════════════════════════════════════
    def _bonus_dates_tab(self, nb):
        frm = self._tab(nb, " 🎁 Bonus Dates ")
        tk.Label(frm,
                 text="Configure per-religion bonus month and day.",
                 bg=frm["bg"], fg="#ccc", font=("Helvetica", 10)).pack(anchor="w", pady=(0, 2))
        tk.Label(frm,
                 text="🔒 Bonus AMOUNT is always hidden from employee app — visible to HR/CA/Admin only.",
                 fg="#e67e22", bg=frm["bg"], font=("Helvetica", 9)).pack(anchor="w", pady=(0, 10))

        existing = read("settings", "bonus_dates") or {}
        hdr = tk.Frame(frm, bg="#1a2740"); hdr.pack(fill="x")
        for txt, w in [("Religion", 14), ("Bonus Month", 14), ("Day", 6), ("Enabled", 8)]:
            tk.Label(hdr, text=txt, width=w, anchor="w",
                     font=("Helvetica", 9, "bold"), bg="#1a2740", fg="#f0c040",
                     pady=4).pack(side="left", padx=2)

        self._bonus_rows = {}
        for religion in RELIGIONS:
            key  = religion.lower()
            conf = existing.get(key, {})
            row  = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=1)
            tk.Label(row, text=religion, width=14, anchor="w",
                     bg=frm["bg"], fg="#ccc").pack(side="left", padx=2)
            month_var = tk.StringVar(value=conf.get("month", "March"))
            ttk.Combobox(row, textvariable=month_var, values=MONTHS,
                         width=12, state="readonly").pack(side="left", padx=2)
            day_var = tk.StringVar(value=str(conf.get("day", 1)))
            tk.Entry(row, textvariable=day_var, width=5,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left", padx=2)
            enabled_var = tk.BooleanVar(value=conf.get("enabled", False))
            tk.Checkbutton(row, variable=enabled_var,
                           bg=frm["bg"], selectcolor="#1a2740",
                           activebackground=frm["bg"]).pack(side="left", padx=6)
            self._bonus_rows[key] = {"month": month_var, "day": day_var, "enabled": enabled_var}

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        app_settings = read("settings", "app") or {}
        min_row = tk.Frame(frm, bg=frm["bg"]); min_row.pack(fill="x", pady=2)
        tk.Label(min_row, text="Min Days for Bonus Eligibility:",
                 width=30, anchor="w", bg=frm["bg"], fg="#ccc").pack(side="left")
        self._bonus_min_var = tk.StringVar(value=str(app_settings.get("bonus_min_days", "240")))
        tk.Entry(min_row, textvariable=self._bonus_min_var, width=6,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
        tk.Label(min_row, text="working days in previous year",
                 fg="#7f8c8d", bg=frm["bg"]).pack(side="left", padx=4)

        self._save_btn(frm, "Bonus Dates", self._save_bonus_dates, "#8e44ad")

    def _save_bonus_dates(self):
        data = {}
        for religion, v in self._bonus_rows.items():
            try:
                day = max(1, min(int(v["day"].get().strip()), 31))
            except ValueError:
                day = 1
            data[religion] = {"month": v["month"].get(), "day": day, "enabled": v["enabled"].get()}
        write("settings", "bonus_dates", data)
        app_settings = read("settings", "app") or {}
        try:
            app_settings["bonus_min_days"] = int(self._bonus_min_var.get().strip())
        except ValueError:
            pass
        write("settings", "app", app_settings)
        messagebox.showinfo("Saved", "Bonus dates saved.\nRemember to set each employee's religion in their profile.")

    # ════════════════════════════════════════════════════════════
    # 7. ADMIN USERS (Super Admin / Admin only)
    # ════════════════════════════════════════════════════════════
    def _admin_users_tab(self, nb):
        frm = self._tab(nb, " 👥 Admin Users ")

        top = tk.Frame(frm, bg=frm["bg"]); top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="Manage admin users and their roles.",
                 bg=frm["bg"], fg="#ccc", font=("Helvetica", 10)).pack(side="left")
        if self.role == "super_admin":
            tk.Button(top, text="+ Add User", bg="#27ae60", fg="white",
                      relief="flat", padx=10,
                      command=self._add_user_dialog).pack(side="right")

        cols = ("username", "display_name", "role", "active")
        self._users_tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        for col, lbl, w in [
            ("username",     "Username",     140),
            ("display_name", "Display Name", 180),
            ("role",         "Role",         140),
            ("active",       "Status",        80),
        ]:
            self._users_tree.heading(col, text=lbl)
            self._users_tree.column(col, width=w)
        self._users_tree.pack(fill="both", expand=True, padx=0)
        self._users_tree.bind("<Double-1>", lambda e: self._edit_user_dialog())

        btn_row = tk.Frame(frm, bg=frm["bg"]); btn_row.pack(fill="x", pady=6)
        tk.Button(btn_row, text="✏️ Edit Selected",
                  command=self._edit_user_dialog,
                  bg="#1e6f9f", fg="white", relief="flat", padx=10).pack(side="left", padx=(0, 6))
        if self.role == "super_admin":
            tk.Button(btn_row, text="🔴 Deactivate",
                      command=self._toggle_user_active,
                      bg="#c0392b", fg="white", relief="flat", padx=10).pack(side="left", padx=(0, 6))
            tk.Button(btn_row, text="🔑 Reset Password",
                      command=self._reset_user_password,
                      bg="#8e44ad", fg="white", relief="flat", padx=10).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="🔄 Refresh",
                  command=self._load_users,
                  bg="#555", fg="white", relief="flat", padx=10).pack(side="left")

        self._load_users()

    def _load_users(self):
        self._users_tree.delete(*self._users_tree.get_children())
        try:
            db = get_db()
            for doc in db.collection("admin_users").stream():
                u = doc.to_dict()
                self._users_tree.insert("", "end", iid=u["username"], values=(
                    u.get("username", ""),
                    u.get("display_name", ""),
                    get_role_display(u.get("role", "")),
                    "Active" if u.get("active", True) else "Inactive",
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {e}")

    def _selected_username(self):
        sel = self._users_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a user first.")
            return None
        return self._users_tree.item(sel[0])["values"][0]

    def _add_user_dialog(self):
        _AdminUserDialog(self, mode="add", on_save=self._load_users)

    def _edit_user_dialog(self):
        uname = self._selected_username()
        if not uname: return
        try:
            doc = get_db().collection("admin_users").document(uname).get()
            if not doc.exists:
                messagebox.showerror("Error", "User not found.")
                return
            _AdminUserDialog(self, mode="edit", user_data=doc.to_dict(), on_save=self._load_users)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _toggle_user_active(self):
        uname = self._selected_username()
        if not uname: return
        if uname == self.current_user.get("username"):
            messagebox.showwarning("Blocked", "You cannot deactivate your own account.")
            return
        try:
            ref  = get_db().collection("admin_users").document(uname)
            user = ref.get().to_dict()
            new_status = not user.get("active", True)
            ref.update({"active": new_status})
            status_text = "Activated" if new_status else "Deactivated"
            messagebox.showinfo("Done", f"{uname} has been {status_text}.")
            self._load_users()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_user_password(self):
        uname = self._selected_username()
        if not uname: return
        new_pass = "Hype@Reset#123"
        if not messagebox.askyesno("Reset Password",
                f"Reset password for '{uname}' to:\n{new_pass}\n\nUser must change it on next login."):
            return
        try:
            get_db().collection("admin_users").document(uname).update({
                "password_hash": _hash(new_pass),
                "must_change_password": True,
            })
            messagebox.showinfo("Done",
                f"Password reset for {uname}.\nTemporary password: {new_pass}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ════════════════════════════════════════════════════════════
    # 8. MY ACCOUNT
    # ════════════════════════════════════════════════════════════
    def _my_account_tab(self, nb):
        frm = self._tab(nb, " 🔑 My Account ")
        u = self.current_user

        info = tk.Frame(frm, bg="#1a2740", padx=15, pady=12)
        info.pack(fill="x", pady=(0, 14))
        tk.Label(info, text=f"👤  {u.get('display_name', u.get('username', ''))}",
                 font=("Arial", 13, "bold"), bg="#1a2740", fg="#f0c040").pack(anchor="w")
        tk.Label(info, text=f"Username: {u.get('username', '')}   |   Role: {get_role_display(u.get('role', ''))}",
                 font=("Arial", 9), bg="#1a2740", fg="#aaa").pack(anchor="w", pady=4)

        # Change display name
        tk.Label(frm, text="― Update Display Name ―",
                 font=("Helvetica", 10, "bold"), bg=frm["bg"], fg="#ccc").pack(anchor="w", pady=(0, 4))
        name_row = tk.Frame(frm, bg=frm["bg"]); name_row.pack(fill="x", pady=2)
        tk.Label(name_row, text="Display Name:", width=18, anchor="w",
                 bg=frm["bg"], fg="#ccc").pack(side="left")
        self._display_name_var = tk.StringVar(value=u.get("display_name", ""))
        tk.Entry(name_row, textvariable=self._display_name_var, width=28,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
        tk.Button(frm, text="💾 Save Name",
                  command=self._save_display_name,
                  bg="#1e6f9f", fg="white", padx=10, pady=3).pack(anchor="w", pady=6)

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=10)

        # Change password
        tk.Label(frm, text="― Change Password ―",
                 font=("Helvetica", 10, "bold"), bg=frm["bg"], fg="#ccc").pack(anchor="w", pady=(0, 4))
        self._old_pass  = self._pass_field(frm, "Current Password")
        self._new_pass  = self._pass_field(frm, "New Password")
        self._conf_pass = self._pass_field(frm, "Confirm New Password")
        tk.Label(frm, text="ℹ️ Minimum 8 characters.",
                 fg="#7f8c8d", bg=frm["bg"], font=("Helvetica", 8)).pack(anchor="w", pady=(0, 4))
        tk.Button(frm, text="🔒 Update Password",
                  command=self._change_password,
                  bg="#c0392b", fg="white", padx=12, pady=4).pack(anchor="w", pady=6)

    def _pass_field(self, frm, label):
        row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=2)
        tk.Label(row, text=label + ":", width=22, anchor="w",
                 bg=frm["bg"], fg="#ccc").pack(side="left")
        var = tk.StringVar()
        tk.Entry(row, textvariable=var, show="*", width=24,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
        return var

    def _save_display_name(self):
        name = self._display_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Display name cannot be empty.")
            return
        try:
            get_db().collection("admin_users").document(
                self.current_user["username"]).update({"display_name": name})
            self.current_user["display_name"] = name
            messagebox.showinfo("Saved", "Display name updated.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _change_password(self):
        from modules.auth import authenticate
        old  = self._old_pass.get()
        new  = self._new_pass.get()
        conf = self._conf_pass.get()
        if len(new) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters.")
            return
        if new != conf:
            messagebox.showerror("Error", "New passwords do not match.")
            return
        user = authenticate(self.current_user["username"], old)
        if not user:
            messagebox.showerror("Error", "Current password is incorrect.")
            return
        try:
            get_db().collection("admin_users").document(
                self.current_user["username"]).update({
                "password_hash": _hash(new),
                "must_change_password": False,
            })
            messagebox.showinfo("Success", "✅ Password updated successfully!")
            self._old_pass.set("")
            self._new_pass.set("")
            self._conf_pass.set("")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════
    def _tab(self, nb, title):
        """Create a scrollable tab frame."""
        outer = tk.Frame(nb, bg="#0d1b2a")
        nb.add(outer, text=title)
        canvas = tk.Canvas(outer, bg="#0d1b2a", highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frm = tk.Frame(canvas, bg="#0d1b2a", padx=20, pady=16)
        frm["bg"] = "#0d1b2a"
        win = canvas.create_window((0, 0), window=frm, anchor="nw")
        frm.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return frm

    def _field_group(self, frm, fields, data, secret_keys=None):
        secret_keys = secret_keys or []
        vars_ = {}
        for label, key in fields:
            row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=22, anchor="w",
                     bg=frm["bg"], fg="#ccc").pack(side="left")
            var  = tk.StringVar(value=data.get(key, ""))
            show = "*" if key in secret_keys else ""
            tk.Entry(row, textvariable=var, width=34, show=show,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
            vars_[key] = var
        return vars_

    @staticmethod
    def _save_btn(frm, label, command, color):
        tk.Button(frm, text=f"💾 Save {label}",
                  command=command,
                  bg=color, fg="white", padx=12, pady=4,
                  relief="flat", cursor="hand2").pack(anchor="w", pady=12)


# ════════════════════════════════════════════════════════════
# Admin User Add / Edit Dialog
# ════════════════════════════════════════════════════════════
class _AdminUserDialog(tk.Toplevel):
    def __init__(self, parent, mode="add", user_data=None, on_save=None):
        super().__init__(parent)
        self.mode      = mode
        self.user_data = user_data or {}
        self.on_save   = on_save
        self.title("Add Admin User" if mode == "add" else f"Edit — {user_data.get('username', '')}")
        self.geometry("420x400")
        self.resizable(False, False)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        frm = tk.Frame(self, bg="#0d1b2a", padx=20, pady=16)
        frm.pack(fill="both", expand=True)
        u = self.user_data

        def field(label, key, default="", show=""):
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=4)
            tk.Label(row, text=label + ":", width=18, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar(value=u.get(key, default))
            tk.Entry(row, textvariable=var, width=26, show=show,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
            return var

        self.v_username = field("Username",     "username")
        if self.mode == "edit":
            # username is read-only in edit mode
            pass
        self.v_display  = field("Display Name", "display_name")

        # Role dropdown
        row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=4)
        tk.Label(row, text="Role:", width=18, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_role = tk.StringVar(value=u.get("role", "manager"))
        all_roles = [(r, get_role_display(r)) for r in get_all_roles()]
        ttk.Combobox(row, textvariable=self.v_role,
                     values=[f"{r}" for r, _ in all_roles],
                     width=18, state="readonly").pack(side="left")

        if self.mode == "add":
            self.v_pass    = field("Password",     "",    show="*")
            self.v_confirm = field("Confirm Pass", "",    show="*")
        else:
            self.v_pass = self.v_confirm = None

        # Active toggle
        self.v_active = tk.BooleanVar(value=u.get("active", True))
        tk.Checkbutton(frm, text="Account Active", variable=self.v_active,
                       bg="#0d1b2a", fg="#ccc", selectcolor="#1a2740",
                       activebackground="#0d1b2a").pack(anchor="w", pady=4)

        btn_row = tk.Frame(frm, bg="#0d1b2a"); btn_row.pack(fill="x", pady=10)
        tk.Button(btn_row, text="✔ Save", command=self._save,
                  bg="#27ae60", fg="white", padx=14, relief="flat").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=self.destroy,
                  padx=14, relief="flat").pack(side="left")

    def _save(self):
        username = self.v_username.get().strip().lower()
        display  = self.v_display.get().strip()
        role     = self.v_role.get().strip()
        active   = self.v_active.get()

        if not username or not display:
            messagebox.showerror("Error", "Username and Display Name are required.", parent=self)
            return

        try:
            db = get_db()
            if self.mode == "add":
                pwd = self.v_pass.get()
                cfm = self.v_confirm.get()
                if len(pwd) < 8:
                    messagebox.showerror("Error", "Password must be at least 8 characters.", parent=self)
                    return
                if pwd != cfm:
                    messagebox.showerror("Error", "Passwords do not match.", parent=self)
                    return
                if db.collection("admin_users").document(username).get().exists:
                    messagebox.showerror("Error", f"Username '{username}' already exists.", parent=self)
                    return
                db.collection("admin_users").document(username).set({
                    "username":             username,
                    "display_name":         display,
                    "role":                 role,
                    "password_hash":        _hash(pwd),
                    "must_change_password": True,
                    "active":               active,
                })
            else:
                db.collection("admin_users").document(self.user_data["username"]).update({
                    "display_name": display,
                    "role":         role,
                    "active":       active,
                })
            messagebox.showinfo("Saved", f"User '{username}' saved successfully.", parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
