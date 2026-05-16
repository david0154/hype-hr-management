# employees.py — Employee CRUD with Photo Upload
# Developed by David | Nexuzy Lab | nexuzylab@gmail.com

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.db import read_all, write, update, delete
from utils.firebase_config import get_bucket
from datetime import date
import os

RELIGIONS     = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]
PAYMENT_MODES = ["CASH", "BANK TRANSFER", "UPI", "CHEQUE"]


class EmployeePanel(tk.Frame):
    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg="#0d1b2a")
        self.role = role
        self._build_ui()
        self._load()

    def _build_ui(self):
        bar = tk.Frame(self, bg="#1a2740", pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="👥 Employees",
                 font=("Helvetica", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=12)
        tk.Button(bar, text="+ Add Employee",
                  command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=8)
        tk.Button(bar, text="🔄 Refresh",
                  command=self._load,
                  bg="#555", fg="white", padx=10, relief="flat").pack(side="right", padx=4)

        # Search bar
        sf = tk.Frame(self, bg="#0d1b2a"); sf.pack(fill="x", padx=10, pady=5)
        tk.Label(sf, text="Search:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(sf, textvariable=self.search_var, width=25, bg="#1a2740",
                 fg="white", insertbackground="white", relief="flat", bd=4).pack(side="left", padx=5)
        tk.Button(sf, text="Search", bg="#1e6f9f", fg="white", relief="flat",
                  command=self._search).pack(side="left", padx=3)
        tk.Button(sf, text="All", bg="#444", fg="white", relief="flat",
                  command=self._load).pack(side="left", padx=3)

        cols = ("id", "name", "designation", "dept", "religion", "mobile", "salary", "advance", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        widths = {"id": 90, "name": 160, "designation": 120, "dept": 100,
                  "religion": 80, "mobile": 110, "salary": 90, "advance": 80, "status": 70}
        labels = {"id": "Emp ID", "name": "Name", "designation": "Designation",
                  "dept": "Department", "religion": "Religion", "mobile": "Mobile",
                  "salary": "Salary", "advance": "Advance", "status": "Status"}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree.bind("<Double-1>", self._edit_selected)
        tk.Label(self, text="Double-click to edit employee",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load(self, query: str = ""):
        self.tree.delete(*self.tree.get_children())
        self.employees = {}
        for e in read_all("employees"):
            if query and query.lower() not in e.get("name", "").lower() \
                    and query.lower() not in e.get("employee_id", "").lower():
                continue
            self.employees[e["employee_id"]] = e
            self.tree.insert("", "end", values=(
                e["employee_id"],
                e.get("name", ""),
                e.get("designation", ""),
                e.get("department", ""),
                e.get("religion", "Other"),
                e.get("mobile", ""),
                f"Rs. {float(e.get('salary', 0)):,.0f}",
                f"Rs. {float(e.get('advance', 0)):,.0f}",
                e.get("status", "active"),
            ))

    def _search(self):
        self._load(self.search_var.get().strip())

    def _add_dialog(self):
        EmployeeDialog(self, mode="add", on_save=self._load)

    def _edit_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel: return
        emp_id = self.tree.item(sel[0])["values"][0]
        emp    = self.employees.get(emp_id)
        if emp:
            EmployeeDialog(self, mode="edit", employee=emp, on_save=self._load)


class EmployeeDialog(tk.Toplevel):
    """
    Add / Edit employee dialog with photo upload to Firebase Storage.
    """
    def __init__(self, parent, mode="add", employee=None, on_save=None):
        super().__init__(parent)
        self.mode      = mode
        self.employee  = employee or {}
        self.on_save   = on_save
        self.photo_path = None       # local path of selected photo
        self.title("Add Employee" if mode == "add" else f"Edit — {employee.get('name', '')}")
        self.geometry("520x700")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        # Scrollable canvas
        canvas = tk.Canvas(self, bg="#0d1b2a", highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frm    = tk.Frame(canvas, bg="#0d1b2a", padx=24, pady=16)
        win    = canvas.create_window((0, 0), window=frm, anchor="nw")
        frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        e = self.employee

        def field(label, key, default="", show="", width=30):
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=20, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar(value=e.get(key, default))
            tk.Entry(row, textvariable=var, width=width, show=show,
                     bg="#1e3a5f", fg="white", insertbackground="white",
                     relief="flat", bd=4).pack(side="left")
            return var

        def dropdown(label, key, options, default):
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=20, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar(value=e.get(key, default))
            ttk.Combobox(row, textvariable=var, values=options,
                         width=20, state="readonly").pack(side="left")
            return var

        def section(title):
            tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)
            tk.Label(frm, text=title, fg="#f0c040",
                     bg="#0d1b2a", font=("Helvetica", 9, "bold")).pack(anchor="w", pady=(0, 2))

        # ── PHOTO UPLOAD ────────────────────────────────────────────────
        section("🖼️ Photo")
        photo_row = tk.Frame(frm, bg="#0d1b2a"); photo_row.pack(fill="x", pady=4)

        # Preview thumbnail
        self.photo_lbl = tk.Label(photo_row, bg="#1a2740", width=10, height=5,
                                  text="No Photo", fg="#555", relief="flat")
        self.photo_lbl.pack(side="left", padx=(0, 12))

        photo_btns = tk.Frame(photo_row, bg="#0d1b2a"); photo_btns.pack(side="left")
        tk.Button(photo_btns, text="📂 Browse Photo",
                  bg="#1e6f9f", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2", command=self._browse_photo).pack(anchor="w", pady=2)
        self.photo_status = tk.Label(photo_btns,
                                     text=" Current: " + ("Set" if e.get("photo_url") else "None"),
                                     bg="#0d1b2a",
                                     fg="#27ae60" if e.get("photo_url") else "#aaa",
                                     font=("Arial", 8))
        self.photo_status.pack(anchor="w")
        tk.Label(photo_btns, text="JPG/PNG, max 2MB",
                 bg="#0d1b2a", fg="#555", font=("Arial", 7)).pack(anchor="w")

        # If existing photo, load thumbnail
        if e.get("photo_url"):
            self._load_existing_thumb(e["photo_url"])

        # ── MANDATORY FIELDS ──────────────────────────────────────────
        section("— Mandatory —")
        self.v_name    = field("Full Name",       "name")
        self.v_mobile  = field("Mobile",          "mobile")
        self.v_address = field("Address",         "address")
        self.v_aadhaar = field("Aadhaar Number",  "aadhaar")
        self.v_salary  = field("Base Salary (Rs)","salary")

        # ── DESIGNATION & DEPARTMENT ───────────────────────────────
        section("— Job Details —")
        self.v_desig  = field("Designation",   "designation")
        self.v_dept   = field("Department",    "department")
        self.v_doj    = field("Date of Join",  "date_of_join",
                             default=str(date.today()))

        # ── RELIGION & BONUS ────────────────────────────────────────
        section("— Religion & Bonus —")
        self.v_religion = dropdown("Religion", "religion", RELIGIONS, "Other")
        tk.Label(frm, text="  ℹ️ Bonus date is auto-set per religion in Settings → 🎁 Bonus Dates",
                 fg="#7f8c8d", bg="#0d1b2a", font=("Helvetica", 8)).pack(anchor="w", pady=(0, 4))

        # ── OPTIONAL ─────────────────────────────────────────────────
        section("— Optional —")
        self.v_pan      = field("PAN Number",    "pan")
        self.v_email    = field("Email",         "email")
        self.v_pay_mode = dropdown("Payment Mode", "payment_mode", PAYMENT_MODES, "CASH")

        # Buttons
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        btn_row = tk.Frame(frm, bg="#0d1b2a"); btn_row.pack(fill="x", pady=6)
        tk.Button(btn_row, text="✔ Save Employee",
                  command=self._save,
                  bg="#f77f00", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="Cancel",
                  command=self.destroy, padx=14, relief="flat").pack(side="left")

    def _browse_photo(self):
        path = filedialog.askopenfilename(
            title="Select Employee Photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All", "*.*")])
        if not path: return
        if os.path.getsize(path) > 2 * 1024 * 1024:
            messagebox.showerror("Too Large", "Photo must be under 2 MB.", parent=self)
            return
        self.photo_path = path
        self.photo_status.config(text=f" Selected: {os.path.basename(path)}",
                                  fg="#27ae60")
        # Show thumbnail
        try:
            from PIL import Image, ImageTk
            img  = Image.open(path).convert("RGB")
            img.thumbnail((80, 80))
            photo = ImageTk.PhotoImage(img)
            self.photo_lbl.config(image=photo, text="", width=80, height=80)
            self.photo_lbl.image = photo
        except Exception:
            pass

    def _load_existing_thumb(self, url: str):
        try:
            import urllib.request, io
            from PIL import Image, ImageTk
            with urllib.request.urlopen(url, timeout=5) as r:
                data = r.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img.thumbnail((80, 80))
            photo = ImageTk.PhotoImage(img)
            self.photo_lbl.config(image=photo, text="", width=80, height=80)
            self.photo_lbl.image = photo
        except Exception:
            pass

    def _upload_photo(self, emp_id: str) -> str | None:
        """Upload self.photo_path to Firebase Storage, return public URL."""
        if not self.photo_path:
            return self.employee.get("photo_url")   # keep existing
        try:
            bucket = get_bucket()
            ext    = os.path.splitext(self.photo_path)[1].lower() or ".jpg"
            blob   = bucket.blob(f"employee_photos/{emp_id}{ext}")
            blob.upload_from_filename(self.photo_path,
                                      content_type="image/jpeg")
            blob.make_public()
            return blob.public_url
        except Exception as ex:
            messagebox.showwarning("Photo Upload",
                f"Employee saved but photo upload failed:\n{ex}", parent=self)
            return self.employee.get("photo_url")

    def _save(self):
        name    = self.v_name.get().strip()
        mobile  = self.v_mobile.get().strip()
        aadhaar = self.v_aadhaar.get().strip()
        try:
            salary = float(self.v_salary.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid salary.", parent=self); return
        if not all([name, mobile, aadhaar]):
            messagebox.showerror("Error", "Name, Mobile and Aadhaar are required.", parent=self)
            return

        if self.mode == "add":
            all_emps = read_all("employees")
            next_num = len(all_emps) + 1
            emp_id   = f"EMP-{next_num:04d}"
            from utils.db import read
            company  = read("settings", "company") or {}
            domain   = company.get("company_domain", "hype")
            uname    = f"{name.split()[0].lower()}.{domain}"
        else:
            emp_id = self.employee["employee_id"]
            uname  = self.employee.get("username", "")

        # Upload photo first (uses emp_id)
        self.title("Saving... please wait")
        self.update()
        photo_url = self._upload_photo(emp_id)

        data = {
            "employee_id":  emp_id,
            "name":         name,
            "mobile":       mobile,
            "address":      self.v_address.get().strip(),
            "aadhaar":      aadhaar,
            "salary":       salary,
            "religion":     self.v_religion.get(),
            "designation":  self.v_desig.get().strip(),
            "department":   self.v_dept.get().strip(),
            "date_of_join": self.v_doj.get().strip(),
            "pan":          self.v_pan.get().strip(),
            "email":        self.v_email.get().strip(),
            "payment_mode": self.v_pay_mode.get(),
            "username":     uname,
            "advance":      float(self.employee.get("advance", 0)),
            "status":       self.employee.get("status", "active"),
            "photo_url":    photo_url or "",
        }

        if self.mode == "add":
            write("employees", emp_id, data)
        else:
            from utils.db import update as db_update
            db_update("employees", emp_id, data)

        messagebox.showinfo("Saved",
            f"✅ Employee {emp_id} saved successfully!"
            + ("\n🖼️ Photo uploaded." if photo_url else ""),
            parent=self)
        if self.on_save: self.on_save()
        self.destroy()
