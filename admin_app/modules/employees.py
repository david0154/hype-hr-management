# employees.py — Employee CRUD + Duty/Payment Summary + Android App Credentials
# FIX: DutyPayDialog now queries sessions by employee_id ONLY (no compound query)
#      and filters month/year in Python — no composite index needed.
# Developed by David | Nexuzy Lab | nexuzylab@gmail.com

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.db import read_all, write
from utils.firebase_config import get_db, get_bucket
from datetime import date, datetime
import hashlib, os, calendar

RELIGIONS     = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]
PAYMENT_MODES = ["CASH", "BANK TRANSFER", "UPI", "CHEQUE"]
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def _default_password(mobile: str, name: str) -> str:
    first = name.strip().split()[0].title() if name.strip() else "Emp"
    last4 = mobile.strip()[-4:] if len(mobile.strip()) >= 4 else "0000"
    return f"{first}{last4}@123"

def _bind_scroll(canvas):
    def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    def _on_linux_up(event):   canvas.yview_scroll(-1, "units")
    def _on_linux_down(event): canvas.yview_scroll( 1, "units")
    canvas.bind_all("<MouseWheel>",    _on_mousewheel)
    canvas.bind_all("<Button-4>",      _on_linux_up)
    canvas.bind_all("<Button-5>",      _on_linux_down)


# ──────────────────────────────────────────────────────────────────────
class EmployeePanel(tk.Frame):
    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg="#0d1b2a")
        self.role = role
        self.db   = get_db()
        self._build_ui()
        self._load()

    def _build_ui(self):
        bar = tk.Frame(self, bg="#1a2740", pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="👥 Employees",
                 font=("Helvetica", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=12)
        tk.Button(bar, text="+ Add Employee",  command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bar, text="🔑 Credentials",  command=self._show_credentials,
                  bg="#8e44ad", fg="white", padx=10, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=4)
        tk.Button(bar, text="📈 Duty & Pay",    command=self._show_duty_pay,
                  bg="#1e6f9f", fg="white", padx=10, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=4)
        tk.Button(bar, text="🔄 Refresh",       command=self._load,
                  bg="#555",    fg="white", padx=10, relief="flat").pack(side="right", padx=4)

        sf = tk.Frame(self, bg="#0d1b2a"); sf.pack(fill="x", padx=10, pady=5)
        tk.Label(sf, text="Search:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(sf, textvariable=self.search_var, width=25, bg="#1a2740",
                 fg="white", insertbackground="white", relief="flat", bd=4).pack(side="left", padx=5)
        tk.Button(sf, text="Search", bg="#1e6f9f", fg="white", relief="flat",
                  command=self._search).pack(side="left", padx=3)
        tk.Button(sf, text="All", bg="#444", fg="white", relief="flat",
                  command=self._load).pack(side="left", padx=3)

        cols = ("id","name","designation","dept","mobile","salary","advance","username","app_access","status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        widths  = {"id":90,"name":155,"designation":115,"dept":100,
                   "mobile":110,"salary":90,"advance":80,"username":140,"app_access":90,"status":70}
        labels  = {"id":"Emp ID","name":"Name","designation":"Designation",
                   "dept":"Department","mobile":"Mobile","salary":"Salary",
                   "advance":"Advance","username":"App User","app_access":"App Access","status":"Status"}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree.bind("<Double-1>", self._edit_selected)
        tk.Label(self,
                 text="Double-click to edit  |  Select row → 📈 Duty & Pay  or  🔑 Credentials",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load(self, query: str = ""):
        self.tree.delete(*self.tree.get_children())
        self.employees = {}
        for e in read_all("employees"):
            if query and query.lower() not in e.get("name","").lower() \
                    and query.lower() not in e.get("employee_id","").lower():
                continue
            self.employees[e["employee_id"]] = e
            ph = e.get("app_password_hash", "").strip()
            has_pass = "✅ Active" if ph else "❌ Not Set"
            self.tree.insert("", "end", iid=e["employee_id"], values=(
                e["employee_id"],
                e.get("name",""),
                e.get("designation",""),
                e.get("department",""),
                e.get("mobile",""),
                f"Rs. {float(e.get('salary',0)):,.0f}",
                f"Rs. {float(e.get('advance',0)):,.0f}",
                e.get("username",""),
                has_pass,
                e.get("status","active"),
            ))

    def _search(self): self._load(self.search_var.get().strip())
    def _add_dialog(self): EmployeeDialog(self, mode="add", on_save=self._load)
    def _edit_selected(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        emp = self.employees.get(self.tree.item(sel[0])["values"][0])
        if emp: EmployeeDialog(self, mode="edit", employee=emp, on_save=self._load)

    def _show_credentials(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo("Select","Select an employee first."); return
        emp = self.employees.get(self.tree.item(sel[0])["values"][0])
        if emp:
            try:
                doc = self.db.collection("employees").document(emp["employee_id"]).get()
                if doc.exists: emp = doc.to_dict()
            except Exception: pass
            CredentialsDialog(self, employee=emp, on_refresh=self._load)

    def _show_duty_pay(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo("Select","Select an employee first."); return
        emp = self.employees.get(self.tree.item(sel[0])["values"][0])
        if emp: DutyPayDialog(self, employee=emp, db=self.db)


# ───────────────────────────── DUTY & PAYMENT ──────────────────────────
class DutyPayDialog(tk.Toplevel):
    def __init__(self, parent, employee: dict, db):
        super().__init__(parent)
        self.emp = employee
        self.db  = db
        self.title(f"📈 Duty & Payment — {employee.get('name','')}")
        self.geometry("860x640")
        self.resizable(True, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()
        self._load()

    def _build(self):
        e = self.emp
        info = tk.Frame(self, bg="#1a2740", padx=16, pady=10)
        info.pack(fill="x")
        tk.Label(info, text=f"👤  {e.get('name','')}  |  {e.get('employee_id','')}  |  "
                            f"{e.get('designation','')}  |  {e.get('department','')}",
                 bg="#1a2740", fg="#f0c040", font=("Arial",11,"bold")).pack(side="left")
        tk.Label(info, text=f"Base: Rs.{float(e.get('salary',0)):,.0f}  "
                            f"Advance: Rs.{float(e.get('advance',0)):,.0f}  "
                            f"Mode: {e.get('payment_mode','CASH')}",
                 bg="#1a2740", fg="#aaa", font=("Arial",9)).pack(side="right")

        ctrl = tk.Frame(self, bg="#0d1b2a", padx=10, pady=6)
        ctrl.pack(fill="x")
        tk.Label(ctrl, text="Month:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.month_var = tk.StringVar(value=MONTHS[date.today().month-1])
        ttk.Combobox(ctrl, textvariable=self.month_var, values=MONTHS,
                     width=12, state="readonly").pack(side="left", padx=4)
        tk.Label(ctrl, text="Year:", bg="#0d1b2a", fg="#ccc").pack(side="left", padx=(10,0))
        self.year_var = tk.StringVar(value=str(date.today().year))
        tk.Entry(ctrl, textvariable=self.year_var, width=6,
                 bg="#1e3a5f", fg="white", insertbackground="white",
                 relief="flat", bd=4).pack(side="left", padx=4)
        tk.Button(ctrl, text="🔍 Load", bg="#f77f00", fg="white",
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  command=self._load).pack(side="left", padx=6)

        cols = ("date","day","duty","ot","in_t","out_t","hours","day_pay","ot_pay")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        for col, lbl, w in [
            ("date",   "Date",    100),("day",    "Day",      70),
            ("duty",   "Duty",     80),("ot",     "OT",       60),
            ("in_t",   "IN",       80),("out_t",  "OUT",      80),
            ("hours",  "Hours",    70),("day_pay","Day Pay",  90),("ot_pay","OT Pay",90),
        ]:
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree.tag_configure("full",   foreground="#00cc66")
        self.tree.tag_configure("half",   foreground="#f0c040")
        self.tree.tag_configure("absent", foreground="#e74c3c")
        self.tree.tag_configure("sunday", foreground="#888", background="#0d1f30")

        self.summary_frm = tk.Frame(self, bg="#1a2740", padx=14, pady=10)
        self.summary_frm.pack(fill="x", padx=10, pady=(2,8))
        self.summary_lbl = tk.Label(self.summary_frm, text="",
                                    bg="#1a2740", fg="#f0c040",
                                    font=("Arial",10,"bold"), justify="left")
        self.summary_lbl.pack(anchor="w")

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        month_idx = MONTHS.index(self.month_var.get()) + 1
        try: year = int(self.year_var.get().strip())
        except ValueError: return
        emp_id   = self.emp["employee_id"]
        salary   = float(self.emp.get("salary", 0))
        advance  = float(self.emp.get("advance", 0))
        day_rate = salary / 26
        month_str= f"{year}-{month_idx:02d}"
        _, days_in_month = calendar.monthrange(year, month_idx)

        # FIX: query ONLY by employee_id (single-field, no composite index needed)
        # Filter by month in Python instead — avoids Firestore 400 error
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            docs = self.db.collection("sessions") \
                .where(filter=FieldFilter("employee_id", "==", emp_id)).stream()
            sessions = {
                s["date"]: s
                for doc in docs
                for s in [doc.to_dict()]
                if s.get("date", "").startswith(month_str)   # filter month in Python
            }
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self); return

        total_present = 0.0; total_absent = 0; total_half = 0
        total_ot_days = 0;   gross_pay    = 0.0

        for day in range(1, days_in_month+1):
            date_str = f"{month_str}-{day:02d}"
            weekday  = datetime(year, month_idx, day).strftime("%a")
            is_sunday= weekday == "Sun"
            sess     = sessions.get(date_str)
            if sess:
                duty  = sess.get("duty_status","absent")
                ot    = sess.get("ot_status","none")
                in_t  = sess.get("in_time","—")
                out_t = sess.get("out_time","—")
                hours = sess.get("duty_hours","")
            else:
                duty,ot,in_t,out_t,hours = ("sunday" if is_sunday else "absent"),"none","—","—",""

            if duty=="full":   dp=day_rate;  total_present+=1
            elif duty=="half": dp=day_rate/2; total_half+=1; total_present+=0.5
            else:              dp=0;          total_absent+=(0 if is_sunday else 1)

            op=0
            if ot in ("full","half"):
                ot_hours = float(hours) if hours else (7 if ot=="full" else 4)
                op = (ot_hours*day_rate/8)*1.5
                total_ot_days+=1
            gross_pay += dp+op

            self.tree.insert("","end",values=(
                date_str, weekday,
                duty.title(), ot.title(),
                in_t, out_t,
                f"{hours:.1f}h" if isinstance(hours,float) else (str(hours) or "—"),
                f"Rs.{dp:,.0f}" if dp else "—",
                f"Rs.{op:,.0f}" if op else "—",
            ), tags=("sunday" if is_sunday else duty,))

        net_pay = max(0, gross_pay - advance)
        self.summary_lbl.config(
            text=f"  ✅ Present: {total_present}d   🔴 Absent: {total_absent}d   "
                 f"🟡 Half Days: {total_half}d   ⏰ OT Days: {total_ot_days}   |"
                 f"   💰 Gross: Rs.{gross_pay:,.0f}   ➖ Advance: Rs.{advance:,.0f}   "
                 f"🟢 Net Pay: Rs.{net_pay:,.0f}  | Mode: {self.emp.get('payment_mode','CASH')}")


# ───────────────────────────── CREDENTIALS ─────────────────────────────
class CredentialsDialog(tk.Toplevel):
    def __init__(self, parent, employee: dict, on_refresh=None):
        super().__init__(parent)
        self.employee   = employee
        self.on_refresh = on_refresh
        self.db         = get_db()
        self.title(f"🔑 Android Credentials — {employee.get('name','')}")
        self.geometry("460x480")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg="#0d1b2a", highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frm    = tk.Frame(canvas, bg="#0d1b2a", padx=28, pady=20)
        win    = canvas.create_window((0, 0), window=frm, anchor="nw")
        frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        _bind_scroll(canvas)

        e = self.employee
        tk.Label(frm, text="📱 Android App Login Credentials",
                 font=("Arial",13,"bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w")
        tk.Label(frm, text=f"{e.get('name','')}  |  {e.get('employee_id','')}",
                 bg="#0d1b2a", fg="#aaa", font=("Arial",9)).pack(anchor="w", pady=(2,12))

        card = tk.Frame(frm, bg="#1a2740", padx=16, pady=14)
        card.pack(fill="x", pady=(0,14))

        def cred_row(label, value):
            r = tk.Frame(card, bg="#1a2740"); r.pack(fill="x", pady=5)
            tk.Label(r, text=label, width=14, anchor="w",
                     bg="#1a2740", fg="#aaa", font=("Arial",9)).pack(side="left")
            lbl = tk.Label(r, text=value, bg="#1a2740", fg="#f0c040",
                           font=("Arial",11,"bold"), anchor="w")
            lbl.pack(side="left", padx=4)
            tk.Button(r, text="📋 Copy",
                      command=lambda v=value: self._copy(v),
                      bg="#2c3e50", fg="#ccc", relief="flat",
                      font=("Arial",8), padx=6).pack(side="right")
            return lbl

        username   = e.get("username", "")
        ph         = e.get("app_password_hash", "").strip()
        plain_pass = e.get("app_password_plain", "").strip()
        is_active  = bool(ph)
        if not plain_pass:
            plain_pass = _default_password(e.get("mobile",""), e.get("name",""))

        cred_row("Username:", username)
        self.pass_lbl = cred_row("Password:", plain_pass)

        st_text  = "✅  Password is active"         if is_active else "⚠️  Not yet saved — click Set Password below"
        st_color = "#27ae60"                        if is_active else "#e67e22"
        tk.Label(card, text=st_text, bg="#1a2740", fg=st_color, font=("Arial",8)).pack(anchor="w", pady=(4,0))

        info = tk.Frame(frm, bg="#132030", padx=12, pady=10)
        info.pack(fill="x", pady=(0,14))
        tk.Label(info, text="ℹ️  How employee logs into Android app:",
                 bg="#132030", fg="#f0c040", font=("Arial",9,"bold")).pack(anchor="w")
        tk.Label(info, text=f"  • Open Hype HR Employee App\n"
                            f"  • Username: {username}\n"
                            f"  • Password: {plain_pass}",
                 bg="#132030", fg="#ccc", font=("Arial",9), justify="left").pack(anchor="w", pady=(4,0))

        tk.Label(frm, text="— Reset Password —",
                 bg="#0d1b2a", fg="#ccc", font=("Arial",9,"bold")).pack(anchor="w", pady=(0,6))
        nr = tk.Frame(frm, bg="#0d1b2a"); nr.pack(fill="x", pady=3)
        tk.Label(nr, text="New Password:", width=16, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.new_pass_var = tk.StringVar()
        tk.Entry(nr, textvariable=self.new_pass_var, width=22,
                 bg="#1e3a5f", fg="white", insertbackground="white",
                 relief="flat", bd=4).pack(side="left", padx=6)

        br = tk.Frame(frm, bg="#0d1b2a"); br.pack(fill="x", pady=8)
        tk.Button(br, text="🔒 Set Password",  command=self._set_password,
                  bg="#c0392b", fg="white", relief="flat",
                  font=("Arial",9,"bold"), padx=12, pady=5).pack(side="left", padx=(0,8))
        tk.Button(br, text="↺ Reset Default", command=self._reset_to_default,
                  bg="#1e6f9f", fg="white", relief="flat",
                  font=("Arial",9,"bold"), padx=12, pady=5).pack(side="left", padx=(0,8))
        tk.Button(br, text="Close", command=self.destroy,
                  padx=12, pady=5, relief="flat").pack(side="left")

    def _copy(self, text):
        self.clipboard_clear(); self.clipboard_append(text)
        messagebox.showinfo("✔ Copied", f"Copied:\n{text}", parent=self)

    def _set_password(self):
        p = self.new_pass_var.get().strip()
        if len(p) < 4:
            messagebox.showerror("Error","Minimum 4 characters.",parent=self); return
        self._save_creds(p)

    def _reset_to_default(self):
        d = _default_password(self.employee.get("mobile",""), self.employee.get("name",""))
        if messagebox.askyesno("Confirm", f"Reset to default:\n{d}", parent=self):
            self._save_creds(d)

    def _save_creds(self, plain):
        try:
            self.db.collection("employees").document(
                self.employee["employee_id"]).update({
                "app_password_hash":  _hash(plain),
                "app_password_plain": plain,
            })
            self.pass_lbl.config(text=plain)
            messagebox.showinfo("✅ Saved", f"Password updated:\n{plain}", parent=self)
            if self.on_refresh: self.on_refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


# ───────────────────────────── EMPLOYEE DIALOG ─────────────────────────
class EmployeeDialog(tk.Toplevel):
    def __init__(self, parent, mode="add", employee=None, on_save=None):
        super().__init__(parent)
        self.mode       = mode
        self.employee   = employee or {}
        self.on_save    = on_save
        self.photo_path = None
        self.title("Add Employee" if mode=="add" else f"Edit — {employee.get('name','')}")
        self.geometry("520x740")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg="#0d1b2a", highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frm    = tk.Frame(canvas, bg="#0d1b2a", padx=24, pady=16)
        win    = canvas.create_window((0,0), window=frm, anchor="nw")
        frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        _bind_scroll(canvas)
        e = self.employee

        def field(label, key, default="", show="", width=30):
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=3)
            tk.Label(row, text=label+":", width=20, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar(value=e.get(key, default))
            tk.Entry(row, textvariable=var, width=width, show=show,
                     bg="#1e3a5f", fg="white", insertbackground="white",
                     relief="flat", bd=4).pack(side="left")
            return var

        def dropdown(label, key, options, default):
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=3)
            tk.Label(row, text=label+":", width=20, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar(value=e.get(key, default))
            ttk.Combobox(row, textvariable=var, values=options,
                         width=20, state="readonly").pack(side="left")
            return var

        def section(t):
            tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)
            tk.Label(frm, text=t, fg="#f0c040",
                     bg="#0d1b2a", font=("Helvetica",9,"bold")).pack(anchor="w", pady=(0,2))

        section("🖼️ Photo")
        photo_row = tk.Frame(frm, bg="#0d1b2a"); photo_row.pack(fill="x", pady=4)
        self.photo_lbl = tk.Label(photo_row, bg="#1a2740", width=10, height=5,
                                  text="No Photo", fg="#555", relief="flat")
        self.photo_lbl.pack(side="left", padx=(0,12))
        pb = tk.Frame(photo_row, bg="#0d1b2a"); pb.pack(side="left")
        tk.Button(pb, text="📂 Browse Photo",
                  bg="#1e6f9f", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2", command=self._browse_photo).pack(anchor="w", pady=2)
        self.photo_status = tk.Label(pb,
            text=" Current: "+("Set" if e.get("photo_url") else "None"),
            bg="#0d1b2a", fg="#27ae60" if e.get("photo_url") else "#aaa", font=("Arial",8))
        self.photo_status.pack(anchor="w")
        tk.Label(pb, text="JPG/PNG max 2MB", bg="#0d1b2a", fg="#555", font=("Arial",7)).pack(anchor="w")
        if e.get("photo_url"): self._load_existing_thumb(e["photo_url"])

        section("— Mandatory —")
        self.v_name    = field("Full Name",        "name")
        self.v_mobile  = field("Mobile",           "mobile")
        self.v_address = field("Address",          "address")
        self.v_aadhaar = field("Aadhaar Number",   "aadhaar")
        self.v_salary  = field("Base Salary (Rs)", "salary")

        section("— Job Details —")
        self.v_desig = field("Designation",  "designation")
        self.v_dept  = field("Department",   "department")
        self.v_doj   = field("Date of Join", "date_of_join", default=str(date.today()))

        section("📱 Android App Login")
        self.v_username = field("App Username", "username")
        if self.mode == "add":
            self.v_name.trace_add("write",   self._auto_fill)
            self.v_mobile.trace_add("write", self._auto_fill)
            pr = tk.Frame(frm, bg="#0d1b2a"); pr.pack(fill="x", pady=3)
            tk.Label(pr, text="App Password:", width=20, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            self.v_app_pass = tk.StringVar()
            tk.Entry(pr, textvariable=self.v_app_pass, width=22,
                     bg="#1e3a5f", fg="#f0c040",
                     insertbackground="white", relief="flat", bd=4).pack(side="left", padx=4)
            tk.Label(pr, text="(auto)", bg="#0d1b2a", fg="#555", font=("Arial",7)).pack(side="left")
            tk.Label(frm, text="ℹ️ FirstName + last4 mobile + @123  — editable",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial",8)).pack(anchor="w")
        else:
            plain = e.get("app_password_plain","")
            disp  = plain if plain else "⚠️ Not set — use 🔑 Credentials"
            tk.Label(frm, text=f"  Current password: {disp}",
                     bg="#0d1b2a",
                     fg="#27ae60" if plain else "#e67e22", font=("Arial",9)).pack(anchor="w", pady=(2,0))

        section("— Religion & Bonus —")
        self.v_religion = dropdown("Religion","religion",RELIGIONS,"Other")

        section("— Optional —")
        self.v_pan      = field("PAN Number",  "pan")
        self.v_email    = field("Email",        "email")
        self.v_pay_mode = dropdown("Payment Mode","payment_mode",PAYMENT_MODES,"CASH")

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        br = tk.Frame(frm, bg="#0d1b2a"); br.pack(fill="x", pady=6)
        tk.Button(br, text="✔ Save Employee", command=self._save,
                  bg="#f77f00", fg="white", font=("Arial",10,"bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0,10))
        tk.Button(br, text="Cancel", command=self.destroy,
                  padx=14, relief="flat").pack(side="left")

    def _auto_fill(self, *_):
        name   = self.v_name.get().strip()
        mobile = self.v_mobile.get().strip()
        from utils.db import read
        domain = (read("settings","company") or {}).get("company_domain","hype")
        if name:
            self.v_username.set(f"{name.split()[0].lower()}.{domain}")
        if name and mobile:
            self.v_app_pass.set(_default_password(mobile, name))

    def _browse_photo(self):
        path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[("Images","*.jpg *.jpeg *.png"),("All","*.*")])
        if not path: return
        if os.path.getsize(path) > 2*1024*1024:
            messagebox.showerror("Too Large","Max 2MB.",parent=self); return
        self.photo_path = path
        self.photo_status.config(text=f" {os.path.basename(path)}", fg="#27ae60")
        try:
            from PIL import Image, ImageTk
            img = Image.open(path).convert("RGB"); img.thumbnail((80,80))
            ph  = ImageTk.PhotoImage(img)
            self.photo_lbl.config(image=ph, text="", width=80, height=80)
            self.photo_lbl.image = ph
        except Exception: pass

    def _load_existing_thumb(self, url):
        try:
            import urllib.request, io
            from PIL import Image, ImageTk
            with urllib.request.urlopen(url, timeout=5) as r: data=r.read()
            img = Image.open(io.BytesIO(data)).convert("RGB"); img.thumbnail((80,80))
            ph  = ImageTk.PhotoImage(img)
            self.photo_lbl.config(image=ph, text="", width=80, height=80)
            self.photo_lbl.image = ph
        except Exception: pass

    def _upload_photo(self, emp_id):
        if not self.photo_path: return self.employee.get("photo_url")
        try:
            bucket = get_bucket()
            ext  = os.path.splitext(self.photo_path)[1].lower() or ".jpg"
            blob = bucket.blob(f"employee_photos/{emp_id}{ext}")
            blob.upload_from_filename(self.photo_path, content_type="image/jpeg")
            blob.make_public()
            return blob.public_url
        except Exception as ex:
            messagebox.showwarning("Photo",f"Saved but upload failed:\n{ex}",parent=self)
            return self.employee.get("photo_url")

    def _save(self):
        name    = self.v_name.get().strip()
        mobile  = self.v_mobile.get().strip()
        aadhaar = self.v_aadhaar.get().strip()
        try:    salary = float(self.v_salary.get().strip())
        except ValueError:
            messagebox.showerror("Error","Valid salary required.",parent=self); return
        if not all([name, mobile, aadhaar]):
            messagebox.showerror("Error","Name, Mobile, Aadhaar required.",parent=self); return

        if self.mode == "add":
            emp_id = f"EMP-{len(read_all('employees'))+1:04d}"
        else:
            emp_id = self.employee["employee_id"]

        uname = self.v_username.get().strip()
        if not uname:
            from utils.db import read
            domain = (read("settings","company") or {}).get("company_domain","hype")
            uname  = f"{name.split()[0].lower()}.{domain}"

        if self.mode == "add":
            plain = getattr(self,"v_app_pass",tk.StringVar()).get().strip()
            if not plain: plain = _default_password(mobile, name)
            app_hash  = _hash(plain)
            app_plain = plain
        else:
            app_hash  = self.employee.get("app_password_hash","")
            app_plain = self.employee.get("app_password_plain","")

        self.title("Saving…"); self.update()
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
            "app_password_hash":   app_hash,
            "app_password_plain":  app_plain,
            "advance":             float(self.employee.get("advance",0)),
            "status":              self.employee.get("status","active"),
            "photo_url":           photo_url or "",
        }
        if self.mode == "add":  write("employees", emp_id, data)
        else:
            from utils.db import update as db_update
            db_update("employees", emp_id, data)

        msg = f"✅ {emp_id} saved!"
        if self.mode == "add":
            msg += f"\n\n📱 App Login:\n  User: {uname}\n  Pass: {app_plain}"
        messagebox.showinfo("Saved", msg, parent=self)
        if self.on_save: self.on_save()
        self.destroy()
