# employees.py — Employee CRUD + Android App Credential Management
# Developed by David | Nexuzy Lab | nexuzylab@gmail.com

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.db import read_all, write, update, delete
from utils.firebase_config import get_db, get_bucket
from datetime import date
import hashlib, os

RELIGIONS     = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]
PAYMENT_MODES = ["CASH", "BANK TRANSFER", "UPI", "CHEQUE"]


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _default_password(mobile: str, name: str) -> str:
    """Default Android app password: first name (title) + last 4 mobile digits + @123"""
    first = name.strip().split()[0].title() if name.strip() else "Emp"
    last4 = mobile.strip()[-4:] if len(mobile.strip()) >= 4 else "0000"
    return f"{first}{last4}@123"


# ───────────────────────────────────────────────────────────────────────
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

        # Action buttons
        tk.Button(bar, text="+ Add Employee",
                  command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bar, text="🔑 Credentials",
                  command=self._show_credentials,
                  bg="#8e44ad", fg="white", padx=10, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=4)
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

        # Treeview
        cols = ("id", "name", "designation", "dept", "mobile",
                "salary", "username", "app_access", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        widths = {"id": 90, "name": 155, "designation": 115, "dept": 100,
                  "mobile": 110, "salary": 90, "username": 140,
                  "app_access": 90, "status": 70}
        labels = {"id": "Emp ID", "name": "Name", "designation": "Designation",
                  "dept": "Department", "mobile": "Mobile", "salary": "Salary",
                  "username": "App Username", "app_access": "App Access", "status": "Status"}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree.bind("<Double-1>", self._edit_selected)

        tk.Label(self,
                 text="Double-click to edit  |  Select row then click 🔑 Credentials to view/reset Android login",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load(self, query: str = ""):
        self.tree.delete(*self.tree.get_children())
        self.employees = {}
        for e in read_all("employees"):
            if query and query.lower() not in e.get("name", "").lower() \
                    and query.lower() not in e.get("employee_id", "").lower():
                continue
            self.employees[e["employee_id"]] = e
            has_pass = "✅ Active" if e.get("app_password_hash") else "❌ Not Set"
            self.tree.insert("", "end", iid=e["employee_id"], values=(
                e["employee_id"],
                e.get("name", ""),
                e.get("designation", ""),
                e.get("department", ""),
                e.get("mobile", ""),
                f"Rs. {float(e.get('salary', 0)):,.0f}",
                e.get("username", ""),
                has_pass,
                e.get("status", "active"),
            ))

    def _search(self):
        self._load(self.search_var.get().strip())

    def _add_dialog(self):
        EmployeeDialog(self, mode="add", on_save=self._load)

    def _edit_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel: return
        emp = self.employees.get(self.tree.item(sel[0])["values"][0])
        if emp:
            EmployeeDialog(self, mode="edit", employee=emp, on_save=self._load)

    def _show_credentials(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select an employee row first.")
            return
        emp = self.employees.get(self.tree.item(sel[0])["values"][0])
        if emp:
            CredentialsDialog(self, employee=emp, on_refresh=self._load)


# ───────────────────────────────────────────────────────────────────────
class CredentialsDialog(tk.Toplevel):
    """
    Shows Android app username + password (plain text) for the selected employee.
    Allows admin to:
      - Copy username / password to clipboard
      - Reset password to a new value
      - Generate / re-generate default password
    """
    def __init__(self, parent, employee: dict, on_refresh=None):
        super().__init__(parent)
        self.employee   = employee
        self.on_refresh = on_refresh
        self.db         = get_db()
        emp_id = employee.get("employee_id", "")
        self.title(f"🔑 Android App Credentials — {employee.get('name', '')}")
        self.geometry("440x420")
        self.resizable(False, False)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        e   = self.employee
        frm = tk.Frame(self, bg="#0d1b2a", padx=28, pady=20)
        frm.pack(fill="both", expand=True)

        # Title
        tk.Label(frm, text="📱 Android App Login Credentials",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w")
        tk.Label(frm, text=f"{e.get('name', '')}  |  {e.get('employee_id', '')}",
                 bg="#0d1b2a", fg="#aaa", font=("Arial", 9)).pack(anchor="w", pady=(2, 12))

        # ─ Info card
        card = tk.Frame(frm, bg="#1a2740", padx=16, pady=14)
        card.pack(fill="x", pady=(0, 14))

        def cred_row(label, value, show_copy=True):
            r = tk.Frame(card, bg="#1a2740"); r.pack(fill="x", pady=5)
            tk.Label(r, text=label, width=14, anchor="w",
                     bg="#1a2740", fg="#aaa", font=("Arial", 9)).pack(side="left")
            val_lbl = tk.Label(r, text=value,
                               bg="#1a2740", fg="#f0c040",
                               font=("Arial", 11, "bold"), anchor="w")
            val_lbl.pack(side="left", padx=4)
            if show_copy:
                tk.Button(r, text="📋 Copy",
                          command=lambda v=value: self._copy(v),
                          bg="#2c3e50", fg="#ccc", relief="flat",
                          font=("Arial", 8), padx=6).pack(side="right")
            return val_lbl

        username = e.get("username", "")
        cred_row("Username:", username)

        # Password: show plain if stored, else show default formula
        plain_pass = e.get("app_password_plain", "")
        if not plain_pass:
            plain_pass = _default_password(e.get("mobile", ""), e.get("name", ""))
            status_text = "⚠️ Not yet set — default shown"
            status_color = "#e67e22"
        else:
            status_text = "✅ Password is active"
            status_color = "#27ae60"

        self.pass_lbl = cred_row("Password:", plain_pass)
        self.plain_pass_val = plain_pass

        tk.Label(card, text=status_text, bg="#1a2740",
                 fg=status_color, font=("Arial", 8)).pack(anchor="w", pady=(4, 0))

        # ─ How to login info
        info = tk.Frame(frm, bg="#132030", padx=12, pady=10)
        info.pack(fill="x", pady=(0, 12))
        tk.Label(info, text="ℹ️ How employee logs into Android app:",
                 bg="#132030", fg="#f0c040", font=("Arial", 9, "bold")).pack(anchor="w")
        tk.Label(info,
                 text=f"  • Open Hype HR Employee App\n"
                      f"  • Enter Username: {username}\n"
                      f"  • Enter Password (shown above)",
                 bg="#132030", fg="#ccc", font=("Arial", 9),
                 justify="left").pack(anchor="w", pady=(4, 0))

        # ─ Reset password section
        tk.Label(frm, text="― Reset Password ―",
                 bg="#0d1b2a", fg="#ccc", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 6))

        new_row = tk.Frame(frm, bg="#0d1b2a"); new_row.pack(fill="x", pady=3)
        tk.Label(new_row, text="New Password:", width=16, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.new_pass_var = tk.StringVar()
        tk.Entry(new_row, textvariable=self.new_pass_var, width=22,
                 bg="#1e3a5f", fg="white", insertbackground="white",
                 relief="flat", bd=4).pack(side="left", padx=6)

        btn_row = tk.Frame(frm, bg="#0d1b2a"); btn_row.pack(fill="x", pady=8)
        tk.Button(btn_row, text="🔒 Set Password",
                  command=self._set_password,
                  bg="#c0392b", fg="white", relief="flat",
                  font=("Arial", 9, "bold"), padx=12, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="↺ Reset to Default",
                  command=self._reset_to_default,
                  bg="#1e6f9f", fg="white", relief="flat",
                  font=("Arial", 9, "bold"), padx=12, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Close",
                  command=self.destroy,
                  padx=12, pady=5, relief="flat").pack(side="left")

    def _copy(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("✔ Copied", f"Copied to clipboard:\n{text}", parent=self)

    def _set_password(self):
        new_pass = self.new_pass_var.get().strip()
        if len(new_pass) < 4:
            messagebox.showerror("Error", "Password must be at least 4 characters.", parent=self)
            return
        self._save_credentials(new_pass)

    def _reset_to_default(self):
        default = _default_password(
            self.employee.get("mobile", ""),
            self.employee.get("name",   ""))
        if messagebox.askyesno("Confirm Reset",
                f"Reset password to default:\n{default}\n\nContinue?", parent=self):
            self._save_credentials(default)

    def _save_credentials(self, plain_pass: str):
        emp_id = self.employee["employee_id"]
        try:
            self.db.collection("employees").document(emp_id).update({
                "app_password_hash":  _hash(plain_pass),
                "app_password_plain": plain_pass,   # stored for admin view
            })
            self.pass_lbl.config(text=plain_pass)
            self.plain_pass_val = plain_pass
            messagebox.showinfo("✅ Saved",
                f"Password updated for {self.employee.get('name', '')}:\n{plain_pass}",
                parent=self)
            if self.on_refresh: self.on_refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


# ───────────────────────────────────────────────────────────────────────
class EmployeeDialog(tk.Toplevel):
    """Add / Edit employee dialog with photo upload."""

    def __init__(self, parent, mode="add", employee=None, on_save=None):
        super().__init__(parent)
        self.mode       = mode
        self.employee   = employee or {}
        self.on_save    = on_save
        self.photo_path = None
        self.title("Add Employee" if mode == "add" else f"Edit — {employee.get('name', '')}")
        self.geometry("520x740")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
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

        # ── PHOTO
        section("🖼️ Photo")
        photo_row = tk.Frame(frm, bg="#0d1b2a"); photo_row.pack(fill="x", pady=4)
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
        if e.get("photo_url"): self._load_existing_thumb(e["photo_url"])

        # ── MANDATORY
        section("— Mandatory —")
        self.v_name    = field("Full Name",        "name")
        self.v_mobile  = field("Mobile",           "mobile")
        self.v_address = field("Address",          "address")
        self.v_aadhaar = field("Aadhaar Number",   "aadhaar")
        self.v_salary  = field("Base Salary (Rs)", "salary")

        # ── JOB DETAILS
        section("— Job Details —")
        self.v_desig = field("Designation",  "designation")
        self.v_dept  = field("Department",   "department")
        self.v_doj   = field("Date of Join", "date_of_join", default=str(date.today()))

        # ── ANDROID APP LOGIN ───────────────────────────────────────
        section("📱 Android App Login")
        self.v_username = field("App Username",   "username")

        if self.mode == "add":
            # Auto-fill username when name changes
            self.v_name.trace_add("write", self._auto_fill_username)
            self.v_mobile.trace_add("write", self._auto_fill_username)

            # Password display (auto-generated, editable)
            pass_row = tk.Frame(frm, bg="#0d1b2a"); pass_row.pack(fill="x", pady=3)
            tk.Label(pass_row, text="App Password:", width=20, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            self.v_app_pass = tk.StringVar()
            self.pass_entry = tk.Entry(pass_row, textvariable=self.v_app_pass,
                                       width=22, bg="#1e3a5f", fg="#f0c040",
                                       insertbackground="white", relief="flat", bd=4)
            self.pass_entry.pack(side="left", padx=4)
            tk.Label(pass_row, text="(auto)",
                     bg="#0d1b2a", fg="#555", font=("Arial", 7)).pack(side="left")
            tk.Label(frm,
                     text="ℹ️ Auto: FirstName + last 4 mobile + @123  —  can be changed after saving via 🔑 Credentials",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w")
        else:
            # In edit mode show existing username; password managed via Credentials button
            existing_pass = e.get("app_password_plain", "")
            disp = existing_pass if existing_pass else "⚠️ Not set — use 🔑 Credentials button"
            tk.Label(frm,
                     text=f"  Current password: {disp}",
                     bg="#0d1b2a", fg="#27ae60" if existing_pass else "#e67e22",
                     font=("Arial", 9)).pack(anchor="w", pady=(2, 0))
            tk.Label(frm,
                     text="  To reset password → close this dialog → click 🔑 Credentials button",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w")

        # ── RELIGION
        section("— Religion & Bonus —")
        self.v_religion = dropdown("Religion", "religion", RELIGIONS, "Other")
        tk.Label(frm, text="  ℹ️ Bonus date auto-set per religion in Settings → 🎁 Bonus Dates",
                 fg="#7f8c8d", bg="#0d1b2a", font=("Helvetica", 8)).pack(anchor="w", pady=(0, 4))

        # ── OPTIONAL
        section("— Optional —")
        self.v_pan      = field("PAN Number",    "pan")
        self.v_email    = field("Email",         "email")
        self.v_pay_mode = dropdown("Payment Mode", "payment_mode", PAYMENT_MODES, "CASH")

        # Save button
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        btn_row = tk.Frame(frm, bg="#0d1b2a"); btn_row.pack(fill="x", pady=6)
        tk.Button(btn_row, text="✔ Save Employee",
                  command=self._save,
                  bg="#f77f00", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="Cancel",
                  command=self.destroy, padx=14, relief="flat").pack(side="left")

    def _auto_fill_username(self, *_):
        name   = self.v_name.get().strip()
        mobile = self.v_mobile.get().strip()
        from utils.db import read
        company = read("settings", "company") or {}
        domain  = company.get("company_domain", "hype")
        if name:
            uname = f"{name.split()[0].lower()}.{domain}"
            self.v_username.set(uname)
        # Auto password
        if name and mobile:
            self.v_app_pass.set(_default_password(mobile, name))

    # ── Photo helpers
    def _browse_photo(self):
        path = filedialog.askopenfilename(
            title="Select Employee Photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All", "*.*")])
        if not path: return
        if os.path.getsize(path) > 2 * 1024 * 1024:
            messagebox.showerror("Too Large", "Photo must be under 2 MB.", parent=self); return
        self.photo_path = path
        self.photo_status.config(text=f" Selected: {os.path.basename(path)}", fg="#27ae60")
        try:
            from PIL import Image, ImageTk
            img   = Image.open(path).convert("RGB")
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
            img   = Image.open(io.BytesIO(data)).convert("RGB")
            img.thumbnail((80, 80))
            photo = ImageTk.PhotoImage(img)
            self.photo_lbl.config(image=photo, text="", width=80, height=80)
            self.photo_lbl.image = photo
        except Exception:
            pass

    def _upload_photo(self, emp_id: str) -> str | None:
        if not self.photo_path:
            return self.employee.get("photo_url")
        try:
            bucket = get_bucket()
            ext    = os.path.splitext(self.photo_path)[1].lower() or ".jpg"
            blob   = bucket.blob(f"employee_photos/{emp_id}{ext}")
            blob.upload_from_filename(self.photo_path, content_type="image/jpeg")
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
        else:
            emp_id = self.employee["employee_id"]

        uname = self.v_username.get().strip()
        if not uname:
            from utils.db import read
            company = read("settings", "company") or {}
            domain  = company.get("company_domain", "hype")
            uname   = f"{name.split()[0].lower()}.{domain}"

        # Password (only on add)
        if self.mode == "add":
            plain_pass = self.v_app_pass.get().strip()
            if not plain_pass:
                plain_pass = _default_password(mobile, name)
            app_pass_hash  = _hash(plain_pass)
            app_pass_plain = plain_pass
        else:
            app_pass_hash  = self.employee.get("app_password_hash",  "")
            app_pass_plain = self.employee.get("app_password_plain", "")

        self.title("Saving…")
        self.update()
        photo_url = self._upload_photo(emp_id)

        data = {
            "employee_id":         emp_id,
            "name":                name,
            "mobile":              mobile,
            "address":             self.v_address.get().strip(),
            "aadhaar":             aadhaar,
            "salary":              salary,
            "religion":            self.v_religion.get(),
            "designation":         self.v_desig.get().strip(),
            "department":          self.v_dept.get().strip(),
            "date_of_join":        self.v_doj.get().strip(),
            "pan":                 self.v_pan.get().strip(),
            "email":               self.v_email.get().strip(),
            "payment_mode":        self.v_pay_mode.get(),
            "username":            uname,
            "app_password_hash":   app_pass_hash,
            "app_password_plain":  app_pass_plain,
            "advance":             float(self.employee.get("advance", 0)),
            "status":              self.employee.get("status", "active"),
            "photo_url":           photo_url or "",
        }

        if self.mode == "add":
            write("employees", emp_id, data)
        else:
            from utils.db import update as db_update
            db_update("employees", emp_id, data)

        msg = f"✅ Employee {emp_id} saved!"
        if self.mode == "add":
            msg += f"\n\n📱 Android App Login:\n   Username: {uname}\n   Password: {app_pass_plain}"
        if photo_url:
            msg += "\n🖼️ Photo uploaded."
        messagebox.showinfo("Saved", msg, parent=self)
        if self.on_save: self.on_save()
        self.destroy()
