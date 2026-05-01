"""
Hype HR Management — Employee Management Module (Tkinter)
Full CRUD: Add / Edit / Delete / Activate / Salary Increase / Bonus / Deduction / Advance
QR generation for employee ID cards
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import hashlib
from datetime import datetime

from utils.firebase_config import get_db
from modules.roles import can_access


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class EmployeesModule(tk.Frame):
    """
    Employee management panel — embedded as a tab inside the main window.
    role_info = {'role': 'admin'|'hr'|'manager'|'ca'|'security', 'username': ...}
    """

    COLUMNS = (
        "employee_id", "name", "mobile", "username",
        "salary", "status", "email", "pan",
    )
    COL_HEADS = (
        "Emp ID", "Name", "Mobile", "Username",
        "Base Salary", "Status", "Email", "PAN",
    )
    COL_WIDTHS = (80, 160, 110, 140, 100, 70, 180, 110)

    def __init__(self, parent, role_info: dict, **kwargs):
        super().__init__(parent, bg="#0d1b2a", **kwargs)
        self.role_info = role_info
        self.db = get_db()
        self._employees: list[dict] = []
        self._selected_id: str | None = None
        self._build_ui()
        self.refresh_list()

    # ─────────────────────────── UI BUILD ────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg="#0d1b2a")
        top.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(top, text="👥  Employee Management",
                 font=("Segoe UI", 15, "bold"),
                 bg="#0d1b2a", fg="#f77f00").pack(side="left")

        btn_frame = tk.Frame(top, bg="#0d1b2a")
        btn_frame.pack(side="right", gap=6)

        self._btn(btn_frame, "＋ Add Employee", self._open_add, "#2e8b57").pack(side="left", padx=4)
        self._btn(btn_frame, "✏ Edit", self._open_edit, "#1e6f9f").pack(side="left", padx=4)
        self._btn(btn_frame, "🔄 Toggle Active", self._toggle_active, "#7b4fa6").pack(side="left", padx=4)
        self._btn(btn_frame, "🗑 Delete", self._delete_employee, "#c0392b").pack(side="left", padx=4)
        self._btn(btn_frame, "📈 Salary+", self._salary_increase, "#2e8b57").pack(side="left", padx=4)
        self._btn(btn_frame, "🎁 Bonus/Ded/Adv", self._open_adjustment, "#e67e22").pack(side="left", padx=4)
        self._btn(btn_frame, "🔲 QR Card", self._gen_qr_card, "#1e6f9f").pack(side="left", padx=4)
        self._btn(btn_frame, "🔃 Refresh", self.refresh_list, "#444").pack(side="left", padx=4)

        # Search bar
        sf = tk.Frame(self, bg="#0d1b2a")
        sf.pack(fill="x", padx=16, pady=(0, 6))
        tk.Label(sf, text="Search:", bg="#0d1b2a", fg="#8ab4c8",
                 font=("Segoe UI", 10)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(sf, textvariable=self._search_var, bg="#162436", fg="#e0e0e0",
                 insertbackground="#f77f00", relief="flat", width=30,
                 font=("Segoe UI", 10)).pack(side="left", padx=8)
        tk.Label(sf, textvariable=tk.StringVar(), bg="#0d1b2a").pack(side="left")  # spacer
        self._count_var = tk.StringVar(value="")
        tk.Label(sf, textvariable=self._count_var, bg="#0d1b2a",
                 fg="#8ab4c8", font=("Segoe UI", 10)).pack(side="right")

        # Treeview
        tree_frame = tk.Frame(self, bg="#162436")
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Emp.Treeview",
                        background="#162436", fieldbackground="#162436",
                        foreground="#e0e0e0", rowheight=28,
                        font=("Segoe UI", 10))
        style.configure("Emp.Treeview.Heading",
                        background="#0d1b2a", foreground="#f77f00",
                        font=("Segoe UI", 10, "bold"))
        style.map("Emp.Treeview",
                  background=[("selected", "#1e3050")],
                  foreground=[("selected", "#f77f00")])

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            style="Emp.Treeview",
            selectmode="browse",
        )

        for col, head, w in zip(self.COLUMNS, self.COL_HEADS, self.COL_WIDTHS):
            self._tree.heading(col, text=head,
                               command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=w, minwidth=60, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                            command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._open_edit())

    # ─────────────────────────── DATA ────────────────────────────────────────

    def refresh_list(self):
        try:
            docs = self.db.collection("employees").stream()
            self._employees = [d.to_dict() | {"_doc_id": d.id} for d in docs]
        except Exception as e:
            messagebox.showerror("Firebase Error", str(e))
            self._employees = []
        self._apply_filter()

    def _apply_filter(self):
        q = self._search_var.get().lower().strip()
        rows = self._employees if not q else [
            e for e in self._employees
            if q in (e.get("name", "") + e.get("employee_id", "") +
                     e.get("mobile", "") + e.get("username", "")).lower()
        ]
        self._tree.delete(*self._tree.get_children())
        for emp in rows:
            tag = "active" if emp.get("is_active", True) else "inactive"
            self._tree.insert("", "end", iid=emp.get("employee_id", ""),
                              values=[
                                  emp.get("employee_id", ""),
                                  emp.get("name", ""),
                                  emp.get("mobile", ""),
                                  emp.get("username", ""),
                                  f"₹{emp.get('salary', 0):,.0f}",
                                  "Active" if emp.get("is_active", True) else "Inactive",
                                  emp.get("email", ""),
                                  emp.get("pan", ""),
                              ], tags=(tag,))
        self._tree.tag_configure("inactive", foreground="#888")
        self._count_var.set(f"Total: {len(rows)} employee(s)")

    def _sort_by(self, col: str):
        self._employees.sort(key=lambda e: str(e.get(col, "")).lower())
        self._apply_filter()

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        self._selected_id = sel[0] if sel else None

    def _get_selected_emp(self) -> dict | None:
        if not self._selected_id:
            messagebox.showwarning("Select Employee", "Please select an employee first.")
            return None
        for e in self._employees:
            if e.get("employee_id") == self._selected_id:
                return e
        return None

    # ─────────────────────────── AUTO ID ─────────────────────────────────────

    def _next_emp_id(self) -> str:
        ids = [e.get("employee_id", "") for e in self._employees
               if re.match(r"EMP-\d{4}", e.get("employee_id", ""))]
        nums = [int(i.split("-")[1]) for i in ids]
        n = max(nums) + 1 if nums else 1
        return f"EMP-{n:04d}"

    # ─────────────────────────── ADD EMPLOYEE ────────────────────────────────

    def _open_add(self):
        if not can_access(self.role_info["role"], "employees"):
            messagebox.showerror("Access Denied", "Your role cannot add employees.")
            return
        dlg = _EmpDialog(self, title="Add Employee",
                         emp=None, next_id=self._next_emp_id())
        self.wait_window(dlg)
        if dlg.result:
            self._save_new_employee(dlg.result)

    def _save_new_employee(self, data: dict):
        emp_id = data["employee_id"]
        company = self._fetch_company_suffix()
        username = f"{data['name'].split()[0].lower()}.{company}"
        password_hash = _sha256(data["password"])

        doc = {
            "employee_id":  emp_id,
            "name":         data["name"],
            "mobile":       data["mobile"],
            "address":      data.get("address", ""),
            "aadhaar":      data.get("aadhaar", ""),
            "salary":       float(data["salary"]),
            "username":     username,
            "password_hash": password_hash,
            "email":        data.get("email", ""),
            "pan":          data.get("pan", ""),
            "is_active":    True,
            "created_at":   datetime.now().isoformat(),
            "bonus":        0.0,
            "deduction":    0.0,
            "advance":      0.0,
        }
        try:
            self.db.collection("employees").document(emp_id).set(doc)
            messagebox.showinfo("Success",
                f"Employee {emp_id} added.\nUsername: {username}\nPassword: {data['password']}")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────── EDIT EMPLOYEE ───────────────────────────────

    def _open_edit(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        if not can_access(self.role_info["role"], "employees"):
            messagebox.showerror("Access Denied", "Your role cannot edit employees.")
            return
        dlg = _EmpDialog(self, title="Edit Employee",
                         emp=emp, next_id=emp["employee_id"])
        self.wait_window(dlg)
        if dlg.result:
            self._update_employee(emp["employee_id"], dlg.result)

    def _update_employee(self, emp_id: str, data: dict):
        update = {
            "name":     data["name"],
            "mobile":   data["mobile"],
            "address":  data.get("address", ""),
            "aadhaar":  data.get("aadhaar", ""),
            "salary":   float(data["salary"]),
            "email":    data.get("email", ""),
            "pan":      data.get("pan", ""),
        }
        if data.get("password"):
            update["password_hash"] = _sha256(data["password"])
        try:
            self.db.collection("employees").document(emp_id).update(update)
            messagebox.showinfo("Updated", f"{emp_id} updated successfully.")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────── DELETE ──────────────────────────────────────

    def _delete_employee(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        if self.role_info["role"] != "admin":
            messagebox.showerror("Access Denied", "Only Admin can delete employees.")
            return
        if not messagebox.askyesno("Confirm Delete",
                f"Permanently delete {emp['name']} ({emp['employee_id']})?\n"
                "This cannot be undone."):
            return
        try:
            self.db.collection("employees").document(emp["employee_id"]).delete()
            messagebox.showinfo("Deleted", f"{emp['employee_id']} deleted.")
            self._selected_id = None
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────── TOGGLE ACTIVE ───────────────────────────────

    def _toggle_active(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        new_state = not emp.get("is_active", True)
        label = "Activate" if new_state else "Deactivate"
        if not messagebox.askyesno("Confirm", f"{label} {emp['name']}?"):
            return
        try:
            self.db.collection("employees").document(emp["employee_id"]).update(
                {"is_active": new_state})
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────── SALARY INCREASE ─────────────────────────────

    def _salary_increase(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        if not can_access(self.role_info["role"], "salary"):
            messagebox.showerror("Access Denied", "Your role cannot modify salary.")
            return
        dlg = _AmountDialog(self, title="Salary Increase",
                            prompt=f"New salary for {emp['name']} (current: ₹{emp.get('salary', 0):,.0f}):")
        self.wait_window(dlg)
        if dlg.amount is None:
            return
        try:
            self.db.collection("employees").document(emp["employee_id"]).update(
                {"salary": dlg.amount})
            messagebox.showinfo("Updated", f"Salary updated to ₹{dlg.amount:,.0f}")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────── BONUS / DEDUCTION / ADVANCE ─────────────────

    def _open_adjustment(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        if not can_access(self.role_info["role"], "salary"):
            messagebox.showerror("Access Denied", "Your role cannot adjust salary.")
            return
        dlg = _AdjustmentDialog(self, emp=emp)
        self.wait_window(dlg)
        if dlg.result:
            try:
                self.db.collection("employees").document(emp["employee_id"]).update(dlg.result)
                messagebox.showinfo("Saved", "Adjustments saved for next salary cycle.")
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ─────────────────────────── QR ID CARD ──────────────────────────────────

    def _gen_qr_card(self):
        emp = self._get_selected_emp()
        if not emp:
            return
        try:
            import qrcode
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            messagebox.showerror("Missing Library",
                "Install qrcode and Pillow: pip install qrcode pillow")
            return

        # Build QR payload
        payload = (
            f"HYPE_EMP|{emp['employee_id']}|{emp['name']}|"
            f"{emp.get('username', '')}|{self._fetch_company_suffix()}"
        )
        qr = qrcode.QRCode(version=2, box_size=8, border=2)
        qr.add_data(payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#0d1b2a", back_color="white").convert("RGB")

        # Build ID card canvas 400x250
        card = Image.new("RGB", (400, 250), "#0d1b2a")
        # Orange header
        header = Image.new("RGB", (400, 60), "#f77f00")
        card.paste(header, (0, 0))

        draw = ImageDraw.Draw(card)
        try:
            font_big = ImageFont.truetype("arial.ttf", 18)
            font_med = ImageFont.truetype("arial.ttf", 13)
            font_sm  = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            font_big = font_med = font_sm = ImageFont.load_default()

        company = self._fetch_company_name()
        draw.text((14, 14), company, fill="#0d1b2a", font=font_big)
        draw.text((14, 36), "EMPLOYEE ID CARD", fill="#0d1b2a", font=font_sm)

        # QR on right
        qr_small = qr_img.resize((130, 130))
        card.paste(qr_small, (258, 68))

        # Text info
        draw.text((14, 72),  f"Name:    {emp.get('name', '')}",        fill="#e0e0e0", font=font_med)
        draw.text((14, 96),  f"Emp ID:  {emp.get('employee_id', '')}", fill="#e0e0e0", font=font_med)
        draw.text((14, 120), f"User:    {emp.get('username', '')}",     fill="#8ab4c8", font=font_sm)
        draw.text((14, 140), f"Mobile:  {emp.get('mobile', '')}",       fill="#8ab4c8", font=font_sm)

        # Footer
        draw.rectangle([(0, 220), (400, 250)], fill="#162436")
        draw.text((10, 230), "Scan QR for attendance check-in",
                  fill="#8ab4c8", font=font_sm)

        # Save
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialfile=f"IDCard_{emp['employee_id']}.png",
        )
        if path:
            card.save(path)
            messagebox.showinfo("Saved", f"ID Card saved to:\n{path}")

    # ─────────────────────────── HELPERS ─────────────────────────────────────

    def _fetch_company_suffix(self) -> str:
        try:
            doc = self.db.collection("settings").document("company").get()
            if doc.exists:
                name = doc.to_dict().get("name", "hype")
                return name.split()[0].lower()
        except Exception:
            pass
        return "hype"

    def _fetch_company_name(self) -> str:
        try:
            doc = self.db.collection("settings").document("company").get()
            if doc.exists:
                return doc.to_dict().get("name", "Hype Pvt Ltd")
        except Exception:
            pass
        return "Hype Pvt Ltd"

    @staticmethod
    def _btn(parent, text, cmd, color) -> tk.Button:
        return tk.Button(parent, text=text, command=cmd,
                         bg=color, fg="white",
                         font=("Segoe UI", 9, "bold"),
                         relief="flat", padx=10, pady=5,
                         cursor="hand2")


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOGS
# ═══════════════════════════════════════════════════════════════════════════════

class _EmpDialog(tk.Toplevel):
    """
    Add / Edit employee dialog.
    Mandatory: name, mobile, address, aadhaar, salary, password
    Optional:  email, pan
    """

    def __init__(self, parent, title: str, emp: dict | None, next_id: str):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="#0d1b2a")
        self.resizable(False, False)
        self.grab_set()
        self.result: dict | None = None
        self._emp = emp
        self._next_id = next_id
        self._build()
        self._center()

    def _build(self):
        pad = {"padx": 14, "pady": 6}
        e = self._emp or {}

        tk.Label(self, text=self.title(),
                 bg="#0d1b2a", fg="#f77f00",
                 font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(16, 8), padx=14, sticky="w")

        fields = [
            ("Employee ID",  "_id_var",      self._next_id, False),
            ("Full Name *",  "_name_var",    e.get("name", ""), True),
            ("Mobile *",     "_mob_var",     e.get("mobile", ""), True),
            ("Address *",    "_addr_var",    e.get("address", ""), True),
            ("Aadhaar *",    "_aadh_var",   e.get("aadhaar", ""), True),
            ("Base Salary *","_sal_var",     str(e.get("salary", "")), True),
            ("Password" + (" (leave blank to keep)" if self._emp else " *"),
             "_pass_var", "", not bool(self._emp)),
            ("Email (opt)",  "_email_var",   e.get("email", ""), False),
            ("PAN (opt)",    "_pan_var",     e.get("pan", ""), False),
        ]

        for row, (label, attr, default, _req) in enumerate(fields, start=1):
            tk.Label(self, text=label,
                     bg="#0d1b2a", fg="#8ab4c8",
                     font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="e", **pad)
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            show = "*" if "pass" in attr.lower() else ""
            state = "disabled" if attr == "_id_var" else "normal"
            ent = tk.Entry(self, textvariable=var, show=show, state=state,
                           bg="#162436", fg="#e0e0e0",
                           disabledbackground="#0d1b2a", disabledforeground="#555",
                           insertbackground="#f77f00", relief="flat", width=30,
                           font=("Segoe UI", 10))
            ent.grid(row=row, column=1, sticky="w", **pad)

        r = len(fields) + 1
        btn_f = tk.Frame(self, bg="#0d1b2a")
        btn_f.grid(row=r, column=0, columnspan=2, pady=14)
        tk.Button(btn_f, text="Save", command=self._save,
                  bg="#f77f00", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=18, pady=6).pack(side="left", padx=8)
        tk.Button(btn_f, text="Cancel", command=self.destroy,
                  bg="#444", fg="white",
                  font=("Segoe UI", 10),
                  relief="flat", padx=18, pady=6).pack(side="left", padx=8)

    def _save(self):
        name = self._name_var.get().strip()
        mob  = self._mob_var.get().strip()
        addr = self._addr_var.get().strip()
        aadh = self._aadh_var.get().strip()
        sal  = self._sal_var.get().strip()
        pwd  = self._pass_var.get().strip()
        email = self._email_var.get().strip()
        pan   = self._pan_var.get().strip()

        errors = []
        if not name:  errors.append("Full Name is required")
        if not mob or not re.match(r"^\d{10}$", mob):
            errors.append("Mobile must be 10 digits")
        if not addr:  errors.append("Address is required")
        if not aadh or not re.match(r"^\d{12}$", aadh):
            errors.append("Aadhaar must be 12 digits")
        try:
            float(sal)
        except ValueError:
            errors.append("Salary must be a number")
        if not self._emp and not pwd:
            errors.append("Password is required for new employee")
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("Invalid email format")
        if pan and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan.upper()):
            errors.append("PAN format invalid (e.g. ABCDE1234F)")

        if errors:
            messagebox.showerror("Validation", "\n".join(errors))
            return

        self.result = {
            "employee_id": self._next_id,
            "name":     name,
            "mobile":   mob,
            "address":  addr,
            "aadhaar":  aadh,
            "salary":   float(sal),
            "password": pwd,
            "email":    email,
            "pan":      pan.upper() if pan else "",
        }
        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


class _AmountDialog(tk.Toplevel):
    def __init__(self, parent, title: str, prompt: str):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="#0d1b2a")
        self.resizable(False, False)
        self.grab_set()
        self.amount: float | None = None
        tk.Label(self, text=prompt, bg="#0d1b2a", fg="#8ab4c8",
                 font=("Segoe UI", 10), wraplength=340).pack(padx=20, pady=(18, 8))
        self._var = tk.StringVar()
        tk.Entry(self, textvariable=self._var,
                 bg="#162436", fg="#e0e0e0",
                 insertbackground="#f77f00", relief="flat",
                 font=("Segoe UI", 11), width=20).pack(padx=20, pady=6)
        bf = tk.Frame(self, bg="#0d1b2a")
        bf.pack(pady=14)
        tk.Button(bf, text="Save", command=self._save,
                  bg="#f77f00", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=5).pack(side="left", padx=8)
        tk.Button(bf, text="Cancel", command=self.destroy,
                  bg="#444", fg="white",
                  relief="flat", padx=16, pady=5).pack(side="left", padx=8)

    def _save(self):
        try:
            self.amount = float(self._var.get().strip())
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number")


class _AdjustmentDialog(tk.Toplevel):
    """Dialog for Bonus / Deduction / Advance — one-time values reset after salary run."""

    def __init__(self, parent, emp: dict):
        super().__init__(parent)
        self.title(f"Adjustments — {emp['name']} ({emp['employee_id']})")
        self.configure(bg="#0d1b2a")
        self.resizable(False, False)
        self.grab_set()
        self.result: dict | None = None
        self._emp = emp
        self._build()

    def _build(self):
        tk.Label(self, text="Set values for THIS month's salary slip.",
                 bg="#0d1b2a", fg="#8ab4c8",
                 font=("Segoe UI", 9)).pack(padx=18, pady=(14, 4))

        fields = [
            ("Bonus (₹)",     "_bonus",  self._emp.get("bonus", 0)),
            ("Deduction (₹)", "_ded",    self._emp.get("deduction", 0)),
            ("Advance (₹)",   "_adv",    self._emp.get("advance", 0)),
        ]
        for label, attr, default in fields:
            row = tk.Frame(self, bg="#0d1b2a")
            row.pack(fill="x", padx=18, pady=5)
            tk.Label(row, text=label, width=16, anchor="e",
                     bg="#0d1b2a", fg="#8ab4c8",
                     font=("Segoe UI", 10)).pack(side="left")
            var = tk.StringVar(value=str(default))
            setattr(self, attr, var)
            tk.Entry(row, textvariable=var,
                     bg="#162436", fg="#e0e0e0",
                     insertbackground="#f77f00", relief="flat",
                     font=("Segoe UI", 10), width=16).pack(side="left", padx=8)

        bf = tk.Frame(self, bg="#0d1b2a")
        bf.pack(pady=14)
        tk.Button(bf, text="Save", command=self._save,
                  bg="#f77f00", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=5).pack(side="left", padx=8)
        tk.Button(bf, text="Cancel", command=self.destroy,
                  bg="#444", fg="white",
                  relief="flat", padx=16, pady=5).pack(side="left", padx=8)

    def _save(self):
        try:
            self.result = {
                "bonus":     float(self._bonus.get()),
                "deduction": float(self._ded.get()),
                "advance":   float(self._adv.get()),
            }
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "All values must be numbers (use 0 if none)")
