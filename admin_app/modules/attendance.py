"""
Attendance Module — Hype HR Management
Features:
  - View all attendance logs (filterable by employee / date)
  - Manual Mark: Mark Present (Full/Half) or Absent for any employee
  - Edit existing session: change duty_status / ot_status
  - Delete log entry (Super Admin / Admin only)
Duty rules: <4h=Absent, 4-7h=HalfDay, >=7h=FullDay
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
from utils.firebase_config import get_db
from utils.db import read_all, write, update
from modules.roles import has_permission

DUTY_OPTIONS = ["full", "half", "absent"]
OT_OPTIONS   = ["none", "half", "full"]


def classify_duty(hours: float) -> str:
    if hours < 4:   return "Absent"
    elif hours < 7: return "Half Day"
    return "Full Day"


def classify_ot(hours: float) -> str:
    if hours < 4:   return "No OT"
    elif hours < 7: return "Half OT"
    return "Full OT"


# ────────────────────────────────────────────────────────────────────
class AttendanceModule:
    def __init__(self, parent_frame, current_user):
        self.parent       = parent_frame
        self.current_user = current_user
        self.role         = current_user.get("role", "manager")
        self.db           = get_db()
        self._build_ui()
        self._load_logs()

    # ────────────────────── UI BUILD ───────────────────────────
    def _build_ui(self):
        # ─ Top header bar
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="📅 Attendance Management",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

        # Action buttons (role-gated)
        if has_permission(self.role, "attendance"):
            tk.Button(top, text="✅ Mark Present",
                      bg="#27ae60", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._mark_present_dialog).pack(side="right", padx=4)
            tk.Button(top, text="❌ Mark Absent",
                      bg="#c0392b", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._mark_absent_dialog).pack(side="right", padx=4)
            tk.Button(top, text="✏️ Edit Session",
                      bg="#1e6f9f", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._edit_selected).pack(side="right", padx=4)
        if self.role in ("super_admin", "admin"):
            tk.Button(top, text="🗑 Delete",
                      bg="#7f1f1f", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._delete_selected).pack(side="right", padx=4)

        # ─ Filter bar
        ff = tk.Frame(self.parent, bg="#0d1b2a")
        ff.pack(fill="x", padx=10, pady=4)
        tk.Label(ff, text="Employee ID:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.filter_emp  = tk.StringVar()
        tk.Entry(ff, textvariable=self.filter_emp, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=13).pack(side="left", padx=4)
        tk.Label(ff, text="Date (YYYY-MM-DD):", bg="#0d1b2a", fg="#ccc").pack(side="left", padx=(8, 0))
        self.filter_date = tk.StringVar(value=str(date.today()))
        tk.Entry(ff, textvariable=self.filter_date, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=13).pack(side="left", padx=4)
        tk.Button(ff, text="Filter",  bg="#f77f00", fg="white", relief="flat",
                  command=self._load_logs).pack(side="left", padx=4)
        tk.Button(ff, text="All",     bg="#555",    fg="white", relief="flat",
                  command=self._reset).pack(side="left", padx=2)
        tk.Button(ff, text="🔄 Refresh", bg="#1e3a5f", fg="white", relief="flat",
                  command=self._load_logs).pack(side="left", padx=4)

        # ─ Sessions tree (sessions = processed duty records)
        tk.Label(self.parent, text="👤 Employee Sessions (Processed Duty)",
                 bg="#0d1b2a", fg="#f0c040",
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))

        sess_cols = ("emp_id", "name", "date", "duty", "ot", "in_time", "out_time", "doc_id")
        self.sess_tree = ttk.Treeview(self.parent, columns=sess_cols,
                                      show="headings", height=10,
                                      displaycolumns=("emp_id","name","date","duty","ot","in_time","out_time"))
        for col, lbl, w in [
            ("emp_id",   "Emp ID",    100),
            ("name",     "Name",      150),
            ("date",     "Date",      100),
            ("duty",     "Duty",       90),
            ("ot",       "OT",         80),
            ("in_time",  "IN Time",    90),
            ("out_time", "OUT Time",   90),
        ]:
            self.sess_tree.heading(col, text=lbl)
            self.sess_tree.column(col, width=w, anchor="center")
        self.sess_tree.pack(fill="x", padx=10)
        self.sess_tree.bind("<Double-1>", lambda e: self._edit_selected())

        # ─ Raw logs tree
        tk.Label(self.parent, text="📌 Raw QR Scan Logs",
                 bg="#0d1b2a", fg="#f0c040",
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))

        log_cols = ("emp_id", "name", "date", "time", "action", "location", "session")
        self.log_tree = ttk.Treeview(self.parent, columns=log_cols, show="headings", height=7)
        for col, lbl, w in [
            ("emp_id",   "Emp ID",  100),
            ("name",     "Name",    150),
            ("date",     "Date",    100),
            ("time",     "Time",     90),
            ("action",   "Action",   70),
            ("location", "Location",130),
            ("session",  "Session",  70),
        ]:
            self.log_tree.heading(col, text=lbl)
            self.log_tree.column(col, width=w, anchor="center")
        self.log_tree.pack(fill="x", padx=10)
        self.log_tree.tag_configure("in",  foreground="#00ff88")
        self.log_tree.tag_configure("out", foreground="#ff8844")

        self.status_var = tk.StringVar(value="Loading...")
        tk.Label(self.parent, textvariable=self.status_var,
                 bg="#0d1b2a", fg="#aaa", font=("Arial", 9)).pack(anchor="w", padx=10, pady=3)

    # ───────────────────── DATA LOAD ──────────────────────────
    def _reset(self):
        self.filter_emp.set("")
        self.filter_date.set("")
        self._load_logs()

    def _emp_name_cache(self):
        """Return {employee_id: name} dict from local cache."""
        emps = read_all("employees")
        return {e["employee_id"]: e.get("name", "") for e in emps}

    def _load_logs(self):
        emp_f  = self.filter_emp.get().strip()
        date_f = self.filter_date.get().strip()
        names  = self._emp_name_cache()

        # ─ Load sessions
        for r in self.sess_tree.get_children(): self.sess_tree.delete(r)
        self._session_ids = {}   # tree_iid → doc_id
        try:
            q = self.db.collection("sessions")
            if emp_f:  q = q.where("employee_id", "==", emp_f)
            if date_f: q = q.where("date", "==", date_f)
            sess_count = 0
            for doc in q.order_by("date", direction="DESCENDING").limit(300).stream():
                s    = doc.to_dict()
                iid  = f"sess_{doc.id}"
                duty = s.get("duty_status", "absent").title()
                ot   = s.get("ot_status",   "none").title()
                self.sess_tree.insert("", "end", iid=iid, values=(
                    s.get("employee_id", ""),
                    names.get(s.get("employee_id", ""), ""),
                    s.get("date", ""),
                    duty, ot,
                    s.get("in_time",  "—"),
                    s.get("out_time", "—"),
                    doc.id,
                ))
                self._session_ids[iid] = doc.id
                # colour rows
                tag = "full" if s.get("duty_status") == "full" else (
                      "half" if s.get("duty_status") == "half" else "absent")
                self.sess_tree.item(iid, tags=(tag,))
                sess_count += 1
            self.sess_tree.tag_configure("full",   foreground="#00cc66")
            self.sess_tree.tag_configure("half",   foreground="#f0c040")
            self.sess_tree.tag_configure("absent", foreground="#e74c3c")
        except Exception as e:
            self.status_var.set(f"Sessions error: {e}")

        # ─ Load raw logs
        for r in self.log_tree.get_children(): self.log_tree.delete(r)
        try:
            q2 = self.db.collection("attendance_logs").order_by(
                     "timestamp", direction="DESCENDING").limit(200)
            if emp_f: q2 = q2.where("employee_id", "==", emp_f)
            log_count = 0
            for doc in q2.stream():
                lg = doc.to_dict()
                ts = str(lg.get("timestamp", ""))
                if date_f and date_f not in ts: continue
                action = lg.get("action", "")
                self.log_tree.insert("", "end", values=(
                    lg.get("employee_id", ""),
                    names.get(lg.get("employee_id", ""), ""),
                    ts[:10], ts[11:19],
                    action,
                    lg.get("location", ""),
                    lg.get("session", 1),
                ), tags=("in" if action == "IN" else "out",))
                log_count += 1
            self.status_var.set(
                f"Sessions: {sess_count}  |  Raw logs: {log_count}  |  Filter: {date_f or 'All dates'}")
        except Exception as e:
            self.status_var.set(f"Logs error: {e}")

    # ─────────────────── MARK PRESENT DIALOG ────────────────────
    def _mark_present_dialog(self):
        _MarkAttendanceDialog(
            parent=self.parent,
            db=self.db,
            default_duty="full",
            on_save=self._load_logs,
        )

    def _mark_absent_dialog(self):
        _MarkAttendanceDialog(
            parent=self.parent,
            db=self.db,
            default_duty="absent",
            on_save=self._load_logs,
        )

    # ─────────────────── EDIT SELECTED SESSION ──────────────────
    def _edit_selected(self):
        sel = self.sess_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a session row to edit.")
            return
        iid    = sel[0]
        doc_id = self._session_ids.get(iid)
        if not doc_id: return
        try:
            doc = self.db.collection("sessions").document(doc_id).get()
            if not doc.exists:
                messagebox.showerror("Error", "Session not found in database.")
                return
            _EditSessionDialog(
                parent=self.parent,
                db=self.db,
                doc_id=doc_id,
                session_data=doc.to_dict(),
                on_save=self._load_logs,
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────── DELETE SELECTED ───────────────────────
    def _delete_selected(self):
        sel = self.sess_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a session to delete.")
            return
        iid    = sel[0]
        doc_id = self._session_ids.get(iid)
        vals   = self.sess_tree.item(iid)["values"]
        if not messagebox.askyesno("Confirm Delete",
                f"Delete session for {vals[0]} on {vals[2]}?\nThis cannot be undone."):
            return
        try:
            self.db.collection("sessions").document(doc_id).delete()
            self._load_logs()
            messagebox.showinfo("Deleted", "Session deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ───────────────────────────────────────────────────────────────────────
# Mark Attendance Dialog (Present / Absent)
# ───────────────────────────────────────────────────────────────────────
class _MarkAttendanceDialog(tk.Toplevel):
    def __init__(self, parent, db, default_duty="full", on_save=None):
        super().__init__(parent)
        self.db       = db
        self.on_save  = on_save
        self.title("Mark Attendance")
        self.geometry("420x380")
        self.resizable(False, False)
        self.configure(bg="#0d1b2a")
        self.grab_set()

        frm = tk.Frame(self, bg="#0d1b2a", padx=24, pady=18)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="✅ Mark Attendance",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w", pady=(0, 10))

        def row(label, widget_fn):
            r = tk.Frame(frm, bg="#0d1b2a"); r.pack(fill="x", pady=4)
            tk.Label(r, text=label, width=18, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            return widget_fn(r)

        # Employee ID + lookup
        emp_row = tk.Frame(frm, bg="#0d1b2a"); emp_row.pack(fill="x", pady=4)
        tk.Label(emp_row, text="Employee ID:", width=18, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.emp_var  = tk.StringVar()
        tk.Entry(emp_row, textvariable=self.emp_var, width=16,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left", padx=4)
        self.emp_name_lbl = tk.Label(emp_row, text="", bg="#0d1b2a", fg="#27ae60",
                                     font=("Arial", 9))
        self.emp_name_lbl.pack(side="left", padx=4)
        self.emp_var.trace_add("write", self._lookup_emp)

        # Date
        self.date_var = tk.StringVar(value=str(date.today()))
        row("Date (YYYY-MM-DD):",
            lambda r: tk.Entry(r, textvariable=self.date_var, width=16,
                               bg="#1e3a5f", fg="white",
                               insertbackground="white").pack(side="left"))

        # Duty status
        self.duty_var = tk.StringVar(value=default_duty)
        dr = tk.Frame(frm, bg="#0d1b2a"); dr.pack(fill="x", pady=4)
        tk.Label(dr, text="Duty Status:", width=18, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        ttk.Combobox(dr, textvariable=self.duty_var, values=DUTY_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        # OT status
        self.ot_var = tk.StringVar(value="none")
        or_ = tk.Frame(frm, bg="#0d1b2a"); or_.pack(fill="x", pady=4)
        tk.Label(or_, text="OT Status:", width=18, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        ttk.Combobox(or_, textvariable=self.ot_var, values=OT_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        # In / Out time (optional)
        self.in_var  = tk.StringVar(value="09:00")
        self.out_var = tk.StringVar(value="18:00")
        row("IN Time (HH:MM):",
            lambda r: tk.Entry(r, textvariable=self.in_var,  width=10,
                               bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left"))
        row("OUT Time (HH:MM):",
            lambda r: tk.Entry(r, textvariable=self.out_var, width=10,
                               bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left"))

        # Note
        self.note_var = tk.StringVar()
        row("Note (optional):",
            lambda r: tk.Entry(r, textvariable=self.note_var, width=22,
                               bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left"))

        btn = tk.Frame(frm, bg="#0d1b2a"); btn.pack(fill="x", pady=12)
        tk.Button(btn, text="✔ Save", bg="#27ae60", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", padx=16, pady=5,
                  cursor="hand2", command=self._save).pack(side="left", padx=(0, 8))
        tk.Button(btn, text="Cancel", command=self.destroy,
                  padx=12, relief="flat").pack(side="left")

    def _lookup_emp(self, *_):
        emp_id = self.emp_var.get().strip().upper()
        if len(emp_id) < 4:
            self.emp_name_lbl.config(text=""); return
        try:
            doc = self.db.collection("employees").document(emp_id).get()
            if doc.exists:
                self.emp_name_lbl.config(
                    text=doc.to_dict().get("name", ""), fg="#27ae60")
            else:
                self.emp_name_lbl.config(text="Not found", fg="#e74c3c")
        except Exception:
            pass

    def _save(self):
        emp_id = self.emp_var.get().strip().upper()
        d      = self.date_var.get().strip()
        duty   = self.duty_var.get()
        ot     = self.ot_var.get()
        if not emp_id or not d:
            messagebox.showerror("Error", "Employee ID and Date are required.", parent=self)
            return
        # Validate date
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Date must be YYYY-MM-DD format.", parent=self)
            return
        # Verify employee exists
        emp_doc = self.db.collection("employees").document(emp_id).get()
        if not emp_doc.exists:
            messagebox.showerror("Error", f"Employee '{emp_id}' not found.", parent=self)
            return

        doc_id   = f"{emp_id}_{d}"
        sess_ref = self.db.collection("sessions").document(doc_id)
        existing = sess_ref.get()

        session_data = {
            "employee_id": emp_id,
            "date":        d,
            "duty_status": duty,
            "ot_status":   ot,
            "in_time":     self.in_var.get().strip()  or "—",
            "out_time":    self.out_var.get().strip() or "—",
            "note":        self.note_var.get().strip(),
            "manual":      True,
            "updated_at":  datetime.now().isoformat(),
        }
        if not existing.exists:
            session_data["created_at"] = datetime.now().isoformat()

        sess_ref.set(session_data, merge=True)
        action = "Updated" if existing.exists else "Created"
        messagebox.showinfo("Saved",
            f"✅ {action} attendance for {emp_id} on {d}\n"
            f"Duty: {duty.title()}  |  OT: {ot.title()}",
            parent=self)
        if self.on_save: self.on_save()
        self.destroy()


# ───────────────────────────────────────────────────────────────────────
# Edit Existing Session Dialog
# ───────────────────────────────────────────────────────────────────────
class _EditSessionDialog(tk.Toplevel):
    def __init__(self, parent, db, doc_id, session_data, on_save=None):
        super().__init__(parent)
        self.db           = db
        self.doc_id       = doc_id
        self.session_data = session_data
        self.on_save      = on_save
        emp_id = session_data.get("employee_id", "")
        d      = session_data.get("date", "")
        self.title(f"Edit Session — {emp_id} / {d}")
        self.geometry("380x320")
        self.resizable(False, False)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        s   = self.session_data
        frm = tk.Frame(self, bg="#0d1b2a", padx=24, pady=18)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text=f"✏️ Edit Session — {s.get('employee_id','')} / {s.get('date','')}",
                 font=("Arial", 11, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w", pady=(0, 10))

        def row(label):
            r = tk.Frame(frm, bg="#0d1b2a"); r.pack(fill="x", pady=4)
            tk.Label(r, text=label, width=18, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            return r

        # Duty
        self.duty_var = tk.StringVar(value=s.get("duty_status", "absent"))
        dr = row("Duty Status:")
        ttk.Combobox(dr, textvariable=self.duty_var, values=DUTY_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        # OT
        self.ot_var = tk.StringVar(value=s.get("ot_status", "none"))
        or_ = row("OT Status:")
        ttk.Combobox(or_, textvariable=self.ot_var, values=OT_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        # IN / OUT
        self.in_var  = tk.StringVar(value=s.get("in_time",  "—"))
        self.out_var = tk.StringVar(value=s.get("out_time", "—"))
        ir = row("IN Time (HH:MM):")
        tk.Entry(ir,  textvariable=self.in_var,  width=10,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
        outr = row("OUT Time (HH:MM):")
        tk.Entry(outr, textvariable=self.out_var, width=10,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")

        # Note
        self.note_var = tk.StringVar(value=s.get("note", ""))
        nr = row("Note:")
        tk.Entry(nr, textvariable=self.note_var, width=22,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")

        btn = tk.Frame(frm, bg="#0d1b2a"); btn.pack(fill="x", pady=12)
        tk.Button(btn, text="✔ Save Changes", bg="#1e6f9f", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", padx=14, pady=5,
                  cursor="hand2", command=self._save).pack(side="left", padx=(0, 8))
        tk.Button(btn, text="Cancel", command=self.destroy,
                  padx=12, relief="flat").pack(side="left")

    def _save(self):
        self.db.collection("sessions").document(self.doc_id).update({
            "duty_status": self.duty_var.get(),
            "ot_status":   self.ot_var.get(),
            "in_time":     self.in_var.get().strip()  or "—",
            "out_time":    self.out_var.get().strip() or "—",
            "note":        self.note_var.get().strip(),
            "manual":      True,
            "updated_at":  datetime.now().isoformat(),
        })
        messagebox.showinfo("Updated", "✅ Session updated successfully.", parent=self)
        if self.on_save: self.on_save()
        self.destroy()


# ───────────────────────────────────────────────────────────────────────
def calculate_monthly_summary(employee_id: str, year: int, month: int) -> dict:
    import calendar
    db = get_db()
    month_str = f"{year}-{month:02d}"
    sessions = db.collection("sessions") \
        .where("employee_id", "==", employee_id) \
        .where("date", ">=", f"{month_str}-01") \
        .where("date", "<=", f"{month_str}-31").stream()
    total_present = half_days = absent_days = 0
    ot_hours = 0.0
    for sess in sessions:
        s = sess.to_dict()
        st = s.get("duty_status", "absent")
        if st == "full":       total_present += 1
        elif st == "half":     half_days += 1; total_present += 0.5
        else:                  absent_days += 1
        ot = s.get("ot_status", "none")
        if ot in ("full", "half"): ot_hours += s.get("ot_hours", 0)
    _, days_in_month = calendar.monthrange(year, month)
    return {
        "total_present":      total_present,
        "half_days":          half_days,
        "absent_days":        absent_days,
        "ot_hours":           round(ot_hours, 2),
        "total_working_days": days_in_month,
    }
