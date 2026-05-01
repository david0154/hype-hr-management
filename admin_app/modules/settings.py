# settings.py — Settings Panel (Admin App)
# Tabs: Company | SMTP | Salary Rules | Bonus Dates | Admin Users | My Account

import tkinter as tk
from tkinter import ttk, messagebox
from utils.db import read, write, update


RELIGIONS = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class SettingsPanel(tk.Frame):
    def __init__(self, parent, role="admin"):
        super().__init__(parent)
        self.role = role
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._company_tab(notebook)
        self._smtp_tab(notebook)
        self._salary_rules_tab(notebook)
        self._bonus_dates_tab(notebook)   # ← NEW
        if role in ("super_admin", "admin"):
            self._admin_users_tab(notebook)
        self._my_account_tab(notebook)

    # ───────────────────────────────────────────────────────────────
    def _company_tab(self, nb):
        frm = tk.Frame(nb, padx=20, pady=20)
        nb.add(frm, text=" 🏢 Company ")

        fields = [
            ("Company Name",    "company_name"),
            ("Address Line 1",  "address1"),
            ("Address Line 2",  "address2"),
            ("City / State",    "city_state"),
            ("Email",           "email"),
            ("Phone",           "phone"),
            ("Username Domain", "company_domain"),
        ]
        data = read("settings", "company") or {}
        self._vars_company = {}
        for label, key in fields:
            row = tk.Frame(frm)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=20, anchor="w").pack(side="left")
            var = tk.StringVar(value=data.get(key, ""))
            tk.Entry(row, textvariable=var, width=36).pack(side="left")
            self._vars_company[key] = var

        tk.Button(frm, text="💾 Save Company Info",
                  command=self._save_company,
                  bg="#27ae60", fg="white", padx=12, pady=4
                  ).pack(anchor="w", pady=12)

    def _save_company(self):
        data = {k: v.get().strip() for k, v in self._vars_company.items()}
        write("settings", "company", data)
        messagebox.showinfo("Saved", "Company info saved.")

    # ───────────────────────────────────────────────────────────────
    def _smtp_tab(self, nb):
        frm = tk.Frame(nb, padx=20, pady=20)
        nb.add(frm, text=" 📧 SMTP ")

        fields = [
            ("SMTP Host",      "smtp_host"),
            ("SMTP Port",      "smtp_port"),
            ("Username",       "smtp_user"),
            ("Password",       "smtp_pass"),
            ("From Name",      "smtp_from_name"),
            ("Encryption",     "smtp_encryption"),
        ]
        data = read("settings", "company") or {}
        self._vars_smtp = {}
        for label, key in fields:
            row = tk.Frame(frm)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=18, anchor="w").pack(side="left")
            var = tk.StringVar(value=data.get(key, ""))
            show = "*" if "pass" in key else ""
            tk.Entry(row, textvariable=var, width=36, show=show).pack(side="left")
            self._vars_smtp[key] = var

        tk.Button(frm, text="💾 Save SMTP",
                  command=self._save_smtp,
                  bg="#27ae60", fg="white", padx=12, pady=4
                  ).pack(anchor="w", pady=12)

    def _save_smtp(self):
        data = {k: v.get().strip() for k, v in self._vars_smtp.items()}
        existing = read("settings", "company") or {}
        existing.update(data)
        write("settings", "company", existing)
        messagebox.showinfo("Saved", "SMTP settings saved.")

    # ───────────────────────────────────────────────────────────────
    def _salary_rules_tab(self, nb):
        frm = tk.Frame(nb, padx=20, pady=20)
        nb.add(frm, text=" ⚙️ Salary Rules ")

        data = read("settings", "app") or {}

        fields = [
            ("Working Days / Month",    "working_days",      "26"),
            ("OT Multiplier (e.g 1.5)", "ot_multiplier",     "1.5"),
            ("Bonus Min Days / Year",   "bonus_min_days",    "240"),
            ("Default Payment Mode",   "default_payment_mode", "CASH"),
        ]
        self._vars_rules = {}
        for label, key, default in fields:
            row = tk.Frame(frm)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label + ":", width=26, anchor="w").pack(side="left")
            var = tk.StringVar(value=data.get(key, default))
            tk.Entry(row, textvariable=var, width=12).pack(side="left")
            self._vars_rules[key] = var

        tk.Button(frm, text="💾 Save Rules",
                  command=self._save_rules,
                  bg="#27ae60", fg="white", padx=12, pady=4
                  ).pack(anchor="w", pady=12)

    def _save_rules(self):
        data = {k: v.get().strip() for k, v in self._vars_rules.items()}
        existing = read("settings", "app") or {}
        existing.update(data)
        write("settings", "app", existing)
        messagebox.showinfo("Saved", "Salary rules saved.")

    # ─── Bonus Dates Tab (NEW) ────────────────────────────────────────────────────
    def _bonus_dates_tab(self, nb):
        """
        Configure per-religion bonus month + day.
        Each religion can have its own bonus date.
        Bonus amount visibility: hidden from employee app always.
        """
        frm = tk.Frame(nb, padx=20, pady=20)
        nb.add(frm, text=" 🎁 Bonus Dates ")

        tk.Label(frm,
                 text="Set bonus month and day for each religion.",
                 font=("Helvetica", 10)
                 ).pack(anchor="w", pady=(0, 4))
        tk.Label(frm,
                 text="🔒 Bonus AMOUNT is always hidden from employee app — only HR/CA/Admin can see it.",
                 fg="#e67e22", font=("Helvetica", 9)
                 ).pack(anchor="w", pady=(0, 12))

        # Load existing bonus_dates from Firestore settings/bonus_dates
        existing = read("settings", "bonus_dates") or {}

        # Table header
        hdr = tk.Frame(frm)
        hdr.pack(fill="x")
        for col, w, txt in [
            (0, 14, "Religion"),
            (1, 14, "Bonus Month"),
            (2, 8,  "Day"),
            (3, 10, "Enabled"),
        ]:
            tk.Label(hdr, text=txt, width=w, anchor="w",
                     font=("Helvetica", 9, "bold"),
                     bg="#ecf0f1").grid(row=0, column=col, padx=2, pady=2)

        self._bonus_rows = {}
        for i, religion in enumerate(RELIGIONS):
            key  = religion.lower()
            conf = existing.get(key, {})

            row = tk.Frame(frm)
            row.pack(fill="x", pady=1)

            # Religion label
            tk.Label(row, text=religion, width=14, anchor="w").pack(side="left", padx=2)

            # Month dropdown
            month_var = tk.StringVar(
                value=conf.get("month", "March") if conf else "March"
            )
            ttk.Combobox(row, textvariable=month_var, values=MONTHS,
                         width=12, state="readonly").pack(side="left", padx=2)

            # Day entry
            day_var = tk.StringVar(value=str(conf.get("day", 1)))
            tk.Entry(row, textvariable=day_var, width=5).pack(side="left", padx=2)

            # Enabled checkbox
            enabled_var = tk.BooleanVar(value=conf.get("enabled", False))
            tk.Checkbutton(row, variable=enabled_var).pack(side="left", padx=6)

            self._bonus_rows[key] = {
                "month":   month_var,
                "day":     day_var,
                "enabled": enabled_var,
            }

        tk.Frame(frm, height=1, bg="#bdc3c7").pack(fill="x", pady=10)

        # Min days field
        min_row = tk.Frame(frm)
        min_row.pack(fill="x", pady=2)
        tk.Label(min_row, text="Min Days for Bonus Eligibility:",
                 width=30, anchor="w").pack(side="left")
        app_settings = read("settings", "app") or {}
        self._bonus_min_var = tk.StringVar(
            value=str(app_settings.get("bonus_min_days", "240"))
        )
        tk.Entry(min_row, textvariable=self._bonus_min_var, width=6).pack(side="left")
        tk.Label(min_row, text="working days in previous year",
                 fg="#7f8c8d").pack(side="left", padx=4)

        tk.Button(frm, text="💾 Save Bonus Dates",
                  command=self._save_bonus_dates,
                  bg="#8e44ad", fg="white", padx=12, pady=4
                  ).pack(anchor="w", pady=12)

    def _save_bonus_dates(self):
        data = {}
        for religion, vars_ in self._bonus_rows.items():
            try:
                day = int(vars_["day"].get().strip())
                day = max(1, min(day, 31))
            except ValueError:
                day = 1
            data[religion] = {
                "month":   vars_["month"].get(),
                "day":     day,
                "enabled": vars_["enabled"].get(),
            }
        write("settings", "bonus_dates", data)

        # Also update bonus_min_days in app settings
        app_settings = read("settings", "app") or {}
        try:
            app_settings["bonus_min_days"] = int(self._bonus_min_var.get().strip())
        except ValueError:
            pass
        write("settings", "app", app_settings)

        messagebox.showinfo("Saved",
            "Bonus dates saved.\n\n"
            "Tip: Add each employee's religion in their profile\n"
            "so the correct bonus date is applied automatically."
        )

    # ───────────────────────────────────────────────────────────────
    def _admin_users_tab(self, nb):
        frm = tk.Frame(nb, padx=20, pady=20)
        nb.add(frm, text=" 👥 Admin Users ")
        tk.Label(frm, text="Admin user management",
                 font=("Helvetica", 11)).pack(anchor="w")
        # (full CRUD implementation in auth.py / roles.py)

    def _my_account_tab(self, nb):
        frm = tk.Frame(nb, padx=20, pady=20)
        nb.add(frm, text=" 🔑 My Account ")
        tk.Label(frm, text="Change password and rename username",
                 font=("Helvetica", 11)).pack(anchor="w")
