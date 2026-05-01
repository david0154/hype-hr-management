# employees.py — Employee CRUD
# Includes religion field for bonus date mapping

import tkinter as tk
from tkinter import ttk, messagebox
from utils.db import read_all, write, update, delete
from datetime import date


RELIGIONS = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]
PAYMENT_MODES = ["CASH", "BANK TRANSFER", "UPI", "CHEQUE"]


class EmployeePanel(tk.Frame):
    def __init__(self, parent, role="admin"):
        super().__init__(parent)
        self.role = role
        self._build_ui()
        self._load()

    def _build_ui(self):
        # Top button bar
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=12, pady=6)
        tk.Label(bar, text="👥 Employees",
                 font=("Helvetica", 14, "bold")).pack(side="left")
        tk.Button(bar, text="+ Add Employee",
                  command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=10).pack(side="right")

        # Employee list
        cols = ("id", "name", "religion", "mobile", "salary", "advance", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        widths = {"id": 90, "name": 160, "religion": 90,
                  "mobile": 110, "salary": 90, "advance": 80, "status": 80}
        labels = {"id": "Emp ID", "name": "Name", "religion": "Religion",
                  "mobile": "Mobile", "salary": "Salary",
                  "advance": "Advance", "status": "Status"}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, padx=12, pady=4)
        self.tree.bind("<Double-1>", self._edit_selected)

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        self.employees = {}
        for e in read_all("employees"):
            self.employees[e["employee_id"]] = e
            self.tree.insert("", "end", values=(
                e["employee_id"],
                e["name"],
                e.get("religion", "Other"),
                e.get("mobile", ""),
                f"Rs. {float(e.get('salary', 0)):,.0f}",
                f"Rs. {float(e.get('advance', 0)):,.0f}",
                e.get("status", "active"),
            ))

    def _add_dialog(self):
        EmployeeDialog(self, mode="add", on_save=self._load)

    def _edit_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        emp_id = self.tree.item(sel[0])["values"][0]
        emp    = self.employees.get(emp_id)
        if emp:
            EmployeeDialog(self, mode="edit", employee=emp, on_save=self._load)


class EmployeeDialog(tk.Toplevel):
    """
    Add / Edit employee dialog.
    Includes religion field for religion-based bonus date mapping.
    """
    def __init__(self, parent, mode="add", employee=None, on_save=None):
        super().__init__(parent)
        self.mode      = mode
        self.employee  = employee or {}
        self.on_save   = on_save
        self.title("Add Employee" if mode == "add" else f"Edit — {employee.get('name', '')}")
        self.geometry("480x620")
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        e   = self.employee
        frm = tk.Frame(self, padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        def field(label, key, default="", show="", width=32):
            row = tk.Frame(frm)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=18, anchor="w").pack(side="left")
            var = tk.StringVar(value=e.get(key, default))
            tk.Entry(row, textvariable=var, width=width, show=show).pack(side="left")
            return var

        def dropdown(label, key, options, default):
            row = tk.Frame(frm)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=18, anchor="w").pack(side="left")
            var = tk.StringVar(value=e.get(key, default))
            ttk.Combobox(row, textvariable=var, values=options,
                         width=18, state="readonly").pack(side="left")
            return var

        tk.Label(frm, text="— Mandatory —",
                 fg="#7f8c8d", font=("Helvetica", 8)).pack(anchor="w", pady=(0, 2))

        self.v_name     = field("Full Name",       "name")
        self.v_mobile   = field("Mobile",          "mobile")
        self.v_address  = field("Address",         "address")
        self.v_aadhaar  = field("Aadhaar Number",  "aadhaar")
        self.v_salary   = field("Base Salary (Rs)","salary")

        # Religion dropdown — used for bonus date mapping
        tk.Frame(frm, height=1, bg="#bdc3c7").pack(fill="x", pady=6)
        tk.Label(frm, text="— Religion & Bonus —",
                 fg="#8e44ad", font=("Helvetica", 8)).pack(anchor="w", pady=(0, 2))
        self.v_religion = dropdown("Religion", "religion", RELIGIONS, "Other")
        tk.Label(frm,
                 text="  ℹ️ Bonus date is set per religion in Settings → 🎁 Bonus Dates",
                 fg="#7f8c8d", font=("Helvetica", 8)
                 ).pack(anchor="w", pady=(0, 4))

        tk.Frame(frm, height=1, bg="#bdc3c7").pack(fill="x", pady=4)
        tk.Label(frm, text="— Optional —",
                 fg="#7f8c8d", font=("Helvetica", 8)).pack(anchor="w", pady=(0, 2))

        self.v_pan       = field("PAN Number",    "pan")
        self.v_email     = field("Email",         "email")
        self.v_desig     = field("Designation",   "designation")
        self.v_dept      = field("Department",    "department")
        self.v_pay_mode  = dropdown("Payment Mode", "payment_mode", PAYMENT_MODES, "CASH")

        # Buttons
        btn_row = tk.Frame(frm)
        btn_row.pack(fill="x", pady=10)
        tk.Button(btn_row, text="✔ Save",
                  command=self._save,
                  bg="#2980b9", fg="white", padx=14).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel",
                  command=self.destroy, padx=14).pack(side="left")

    def _save(self):
        name    = self.v_name.get().strip()
        mobile  = self.v_mobile.get().strip()
        aadhaar = self.v_aadhaar.get().strip()
        try:
            salary = float(self.v_salary.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid salary.", parent=self)
            return

        if not all([name, mobile, aadhaar]):
            messagebox.showerror("Error", "Name, Mobile and Aadhaar are required.", parent=self)
            return

        if self.mode == "add":
            # Auto-generate employee ID
            all_emps = read_all("employees")
            next_num = len(all_emps) + 1
            emp_id   = f"EMP-{next_num:04d}"

            # Auto username: firstname.domain
            from utils.db import read
            company = read("settings", "company") or {}
            domain  = company.get("company_domain", "hype")
            uname   = f"{name.split()[0].lower()}.{domain}"
        else:
            emp_id = self.employee["employee_id"]
            uname  = self.employee.get("username", "")

        data = {
            "employee_id":  emp_id,
            "name":         name,
            "mobile":       mobile,
            "address":      self.v_address.get().strip(),
            "aadhaar":      aadhaar,
            "salary":       salary,
            "religion":     self.v_religion.get(),
            "pan":          self.v_pan.get().strip(),
            "email":        self.v_email.get().strip(),
            "designation":  self.v_desig.get().strip(),
            "department":   self.v_dept.get().strip(),
            "payment_mode": self.v_pay_mode.get(),
            "username":     uname,
            "advance":      float(self.employee.get("advance", 0)),
            "status":       self.employee.get("status", "active"),
        }

        if self.mode == "add":
            write("employees", emp_id, data)
        else:
            update("employees", emp_id, data)

        if self.on_save:
            self.on_save()
        self.destroy()
