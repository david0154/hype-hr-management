"""
Attendance Module — Hype HR Management
Features:
  - View all attendance logs (filterable by employee ID / date)
  - Manual Mark: Mark Present (Full/Half) or Absent for any employee
  - Edit existing session: change duty_status / ot_status
  - Delete log entry (Super Admin / Admin only)
FIX: All .where() use FieldFilter keyword arg → no UserWarning.
FIX: Employee lookup queries by employee_id field (not doc ID = UID).
FIX: Live emp-ID lookup preview works for mark present/absent.
FIX: Raw logs show IST time + parsed location name.
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta, timezone
from utils.firebase_config import get_db
from utils.db import read_all, write, update
from modules.roles import has_permission
import json

try:
    from google.cloud.firestore_v1.base_query import FieldFilter
    _HAS_FF = True
except ImportError:
    _HAS_FF = False

DUTY_OPTIONS = ["full", "half", "absent"]
OT_OPTIONS   = ["none", "half", "full"]
IST          = timezone(timedelta(hours=5, minutes=30))


def _ff(col_ref, field, op, val):
    """Safe Firestore .where() using FieldFilter keyword — suppresses UserWarning."""
    if _HAS_FF:
        return col_ref.where(filter=FieldFilter(field, op, val))
    return col_ref.where(field, op, val)


def classify_duty(hours: float) -> str:
    if hours < 4:   return "Absent"
    elif hours < 7: return "Half Day"
    return "Full Day"


def classify_ot(hours: float) -> str:
    if hours < 4:   return "No OT"
    elif hours < 7: return "Half OT"
    return "Full OT"


def _to_ist_hhmm(ts_value) -> str:
    try:
        if hasattr(ts_value, 'tzinfo') and ts_value.tzinfo:
            return ts_value.astimezone(IST).strftime("%H:%M")
        if hasattr(ts_value, 'seconds'):
            return datetime.fromtimestamp(ts_value.seconds, tz=IST).strftime("%H:%M")
        s = str(ts_value)
        if len(s) >= 16:
            h, m = int(s[11:13]), int(s[14:16])
            total = h * 60 + m + 330
            return "%02d:%02d" % (total // 60 % 24, total % 60)
    except Exception:
        pass
    return str(ts_value)[:5]


def _parse_location(loc_raw) -> str:
    if not loc_raw: return ""
    if isinstance(loc_raw, dict):
        return loc_raw.get("location_name") or loc_raw.get("location", "")
    s = str(loc_raw).strip()
    if s.startswith("{"):
        try:
            d = json.loads(s)
            return d.get("location_name") or d.get("location", s)
        except Exception:
            return s
    if s.startswith("HYPE_LOC|"):
        return s[len("HYPE_LOC|"):]
    return s


def _find_employee_by_id(db, emp_id: str):
    """
    Find employee by EMP-XXXX id.
    Firestore doc key = Firebase Auth UID, so we must query by employee_id field.
    Returns (uid, doc_dict) or (None, None).
    """
    emp_id = emp_id.strip().upper()
    if not emp_id:
        return None, None
    # Try direct doc lookup first (legacy: doc key == emp_id)
    try:
        direct = db.collection("employees").document(emp_id).get()
        if direct.exists:
            d = direct.to_dict()
            # Verify it's actually this employee (not an unrelated UID doc)
            if d.get("employee_id", emp_id) == emp_id:
                return d.get("uid", emp_id), d
    except Exception:
        pass
    # Standard: doc key == UID, query by employee_id field
    try:
        results = list(_ff(db.collection("employees"), "employee_id", "==", emp_id).limit(1).stream())
        if results:
            d = results[0].to_dict()
            return d.get("uid", results[0].id), d
    except Exception:
        pass
    return None, None


# ────────────────────────────────────────────────────────────────────
class AttendanceModule:
    def __init__(self, parent_frame, current_user):
        self.parent       = parent_frame
        self.current_user = current_user
        self.role         = current_user.get("role", "manager")
        self.db           = get_db()
        self._build_ui()
        self._load_logs()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="📅 Attendance Management",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

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
        tk.Button(top, text="🔄 Refresh",
                  bg="#555", fg="white", font=("Arial", 9),
                  relief="flat", padx=8, pady=4,
                  command=self._load_logs).pack(side="right", padx=4)

        # ---- Filter bar ----
        ff = tk.Frame(self.parent, bg="#0d1b2a")
        ff.pack(fill="x", padx=10, pady=4)
        tk.Label(ff, text="Employee ID:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.filter_emp = tk.StringVar()
        tk.Entry(ff, textvariable=self.filter_emp, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=13).pack(side="left", padx=4)
        tk.Label(ff, text="Date (YYYY-MM-DD):", bg="#0d1b2a", fg="#ccc").pack(side="left", padx=(8, 0))
        self.filter_date = tk.StringVar()
        tk.Entry(ff, textvariable=self.filter_date, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=13).pack(side="left", padx=4)
        tk.Button(ff, text="Filter", bg="#f77f00", fg="white", relief="flat",
                  padx=8, command=self._apply_filter).pack(side="left", padx=4)
        tk.Button(ff, text="Clear", bg="#444", fg="white", relief="flat",
                  padx=8, command=self._clear_filter).pack(side="left", padx=2)

        # ---- Treeview ----
        cols = ("emp_id", "name", "date", "duty", "ot", "in_t", "out_t", "hours", "location", "doc_id")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=22)
        widths = {"emp_id": 90, "name": 140, "date": 100, "duty": 80, "ot": 70,
                  "in_t": 70, "out_t": 70, "hours": 65, "location": 160, "doc_id": 0}
        labels = {"emp_id": "Emp ID", "name": "Name", "date": "Date",
                  "duty": "Duty", "ot": "OT", "in_t": "IN", "out_t": "OUT",
                  "hours": "Hours", "location": "Location", "doc_id": ""}
        for c in cols:
            self.tree.heading(c, text=labels[c])
            self.tree.column(c, width=widths[c], minwidth=0 if c == "doc_id" else 40)
        self.tree.column("doc_id", width=0, stretch=False)
        sb = ttk.Scrollbar(self.parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=4)
        sb.pack(side="right", fill="y", pady=4)

        self.tree.tag_configure("present", foreground="#00cc66")
        self.tree.tag_configure("half",    foreground="#f0c040")
        self.tree.tag_configure("absent",  foreground="#e74c3c")

    # ------------------------------------------------------------------ LOAD
    def _load_logs(self, emp_f: str = "", date_f: str = ""):
        self.tree.delete(*self.tree.get_children())
        try:
            q = self.db.collection("sessions")
            if date_f:
                q = _ff(q, "date", "==", date_f)
            if emp_f:
                q = _ff(q, "employee_id", "==", emp_f.strip().upper())
            docs = list(q.order_by("date", direction="DESCENDING").limit(300).stream())
        except Exception as ex:
            messagebox.showerror("Error", str(ex)); return

        # Fallback to attendance_logs collection
        if not docs:
            try:
                q2 = self.db.collection("attendance_logs")
                if emp_f:
                    q2 = _ff(q2, "employee_id", "==", emp_f.strip().upper())
                docs = list(q2.limit(300).stream())
            except Exception:
                pass

        for doc in docs:
            d       = doc.to_dict()
            emp_id  = d.get("employee_id", "")
            name    = d.get("employee_name", d.get("name", ""))
            dt      = d.get("date", "")
            duty    = d.get("duty_status", d.get("status", ""))
            ot      = d.get("ot_status", "")
            in_t    = _to_ist_hhmm(d.get("in_time", ""))  if d.get("in_time")  else "—"
            out_t   = _to_ist_hhmm(d.get("out_time", "")) if d.get("out_time") else "—"
            hours   = d.get("duty_hours", "")
            loc     = _parse_location(d.get("location", d.get("check_in_location", "")))
            tag     = "present" if duty == "full" else ("half" if duty == "half" else "absent")
            self.tree.insert("", "end", values=(
                emp_id, name, dt,
                duty.title() if duty else "—",
                ot.title()   if ot   else "—",
                in_t, out_t,
                f"{float(hours):.1f}h" if hours else "—",
                loc, doc.id,
            ), tags=(tag,))

    def _apply_filter(self):
        self._load_logs(
            emp_f  = self.filter_emp.get().strip(),
            date_f = self.filter_date.get().strip(),
        )

    def _clear_filter(self):
        self.filter_emp.set("")
        self.filter_date.set("")
        self._load_logs()

    # ------------------------------------------------------------------ MARK PRESENT
    def _mark_present_dialog(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("✅ Mark Present")
        dlg.geometry("400x360")
        dlg.configure(bg="#0d1b2a")
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = tk.Frame(dlg, bg="#0d1b2a", padx=24, pady=18)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="✅ Mark Employee Present",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w")
        tk.Label(frm, text="Type Employee ID then press Tab to validate (e.g. EMP-0001)",
                 bg="#0d1b2a", fg="#aaa", font=("Arial", 8)).pack(anchor="w", pady=(2, 10))

        def row(label, default=""):
            r = tk.Frame(frm, bg="#0d1b2a"); r.pack(fill="x", pady=4)
            tk.Label(r, text=label, width=18, anchor="w", bg="#0d1b2a", fg="#ccc").pack(side="left")
            v = tk.StringVar(value=default)
            tk.Entry(r, textvariable=v, bg="#1e3a5f", fg="white",
                     insertbackground="white", relief="flat", bd=4, width=20).pack(side="left")
            return v

        v_emp  = row("Employee ID:")
        v_date = row("Date (YYYY-MM-DD):", str(date.today()))
        v_in   = row("IN Time (HH:MM):")
        v_out  = row("OUT Time (HH:MM):")

        dr = tk.Frame(frm, bg="#0d1b2a"); dr.pack(fill="x", pady=4)
        tk.Label(dr, text="Duty Status:", width=18, anchor="w", bg="#0d1b2a", fg="#ccc").pack(side="left")
        v_duty = tk.StringVar(value="full")
        ttk.Combobox(dr, textvariable=v_duty, values=DUTY_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        or2 = tk.Frame(frm, bg="#0d1b2a"); or2.pack(fill="x", pady=4)
        tk.Label(or2, text="OT Status:", width=18, anchor="w", bg="#0d1b2a", fg="#ccc").pack(side="left")
        v_ot = tk.StringVar(value="none")
        ttk.Combobox(or2, textvariable=v_ot, values=OT_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        # Live name preview — debounced via after()
        name_lbl = tk.Label(frm, text="", bg="#0d1b2a", fg="#27ae60", font=("Arial", 9, "bold"))
        name_lbl.pack(anchor="w", pady=(4, 0))
        _lookup_job = [None]

        def _do_lookup():
            eid = v_emp.get().strip().upper()
            if not eid:
                name_lbl.config(text=""); return
            _, emp = _find_employee_by_id(self.db, eid)
            if emp:
                name_lbl.config(
                    text=f"✅ {emp.get('name', '')} | {emp.get('designation', '')}",
                    fg="#27ae60"
                )
            else:
                name_lbl.config(text="❌ Employee not found", fg="#e74c3c")

        def _schedule_lookup(*_):
            if _lookup_job[0]:
                try: dlg.after_cancel(_lookup_job[0])
                except Exception: pass
            _lookup_job[0] = dlg.after(400, _do_lookup)

        v_emp.trace_add("write", _schedule_lookup)

        def _save():
            eid   = v_emp.get()