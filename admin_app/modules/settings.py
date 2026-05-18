# settings.py — Full Settings Panel (Hype HR Management)
# Tabs: Company | SMTP | SMS | Salary Rules | Attendance Rules | Bonus Dates | Admin Users | My Account
# FIX: Admin Users tab now embeds ManageUsersPanel from manage_users.py
#      which has: Delete User, Firebase Auth auto-create for security/supervisor,
#      email field, employee ID field, and Android credentials popup.
# Developed by David | Nexuzy Lab | nexuzylab@gmail.com

import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
from utils.db import read, write, update, delete, read_all
from utils.firebase_config import get_db
from modules.roles import get_all_roles, get_role_display, has_permission
from modules.manage_users import ManageUsersPanel


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

        row = tk.Frame(frm, bg=frm["bg"]); row.pack(fill="x", pady=4)
        tk.Label(row, text="Default Payment Mode:", width=28, anchor="w",
                 bg=frm["bg"], fg="#ccc").pack(side="left")
        self._default_pay_mode = tk.StringVar(value=data.get("default_payment_mode", "CASH"))
        ttk.Combobox(row, textvariable=self._default_pay_mode, values=PAYMENT_MODES,
                     width=14, state="readonly").pack(side="left")

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
    # 7. ADMIN USERS — now uses ManageUsersPanel from manage_users.py
    #    Features: + Create User, 🗑 Delete User, Firebase Auth
    #    auto-create for Security/Supervisor, email + emp_id fields,
    #    Android credentials popup on save.
    # ════════════════════════════════════════════════════════════
    def _admin_users_tab(self, nb):
        outer = tk.Frame(nb, bg="#0d1b2a")
        nb.add(outer, text=" 👥 Admin Users ")
        # Embed ManageUsersPanel directly — it owns its own toolbar + table
        panel = ManageUsersPanel(outer, current_user=self.current_user)
        panel.pack(fill="both", expand=True)

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
