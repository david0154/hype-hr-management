"""
Attendance Module — Hype HR Management
Features:
  - View all attendance logs (filterable by employee ID / date)
  - Manual Mark: Mark Present (Full/Half) or Absent for any employee
  - Edit existing session: change duty_status / ot_status
  - Delete log entry (Super Admin / Admin only)
FIX: All .where() use FieldFilter keyword arg → no UserWarning.
FIX: Employee lookup queries by employee_id field (not doc ID = UID).
FIX: Live emp-ID lookup preview debounced — works for mark present/absent.
FIX: Raw logs show IST time + parsed location name.
FIX: Employee name resolved from multiple field names + live Firestore fallback.
FIX: QR scan check-in/out — _sync_duty_from_times() recomputes duty_status
     from in_time/out_time whenever a session is saved or refreshed.
     Paid holidays: sessions flagged is_holiday=True count toward paid days.
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
    if hours < 4:   return "absent"
    elif hours < 7: return "half"
    return "full"


def classify_ot(hours: float) -> str:
    if hours < 4:   return "none"
    elif hours < 7: return "half"
    return "full"


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


def _extract_name_from_doc(data: dict) -> str:
    for field in (
        "name", "full_name", "employee_name", "employeeName",
        "displayName", "display_name", "emp_name",
    ):
        val = data.get(field, "")
        if val and str(val).strip():
            return str(val).strip()
    return ""


def _find_employee_by_id(db, emp_id: str):
    emp_id = emp_id.strip().upper()
    if not emp_id:
        return None, None
    try:
        direct = db.collection("employees").document(emp_id).get()
        if direct.exists:
            d = direct.to_dict()
            if d.get("employee_id", emp_id) == emp_id:
                return d.get("uid", emp_id), d
    except Exception:
        pass
    try:
        results = list(_ff(db.collection("employees"), "employee_id", "==", emp_id).limit(1).stream())
        if results:
            d = results[0].to_dict()
            return d.get("uid", results[0].id), d
    except Exception:
        pass
    return None, None


def _hhmm_to_float(hhmm: str) -> float:
    """Convert 'HH:MM' string to decimal hours. Returns 0.0 on error."""
    try:
        parts = hhmm.strip().split(":")
        return int(parts[0]) + int(parts[1]) / 60.0
    except Exception:
        return 0.0


def _sync_duty_from_times(db, doc_id: str, session_data: dict) -> dict:
    """
    Recompute and write duty_status + duty_hours to a sessions doc
    based on in_time and out_time fields.

    Called after every QR-based IN/OUT write and after manual edits.
    Also handles paid holidays: if is_holiday=True, duty_status is set
    to 'full' regardless of hours so the employee gets paid for the holiday.

    Returns the updated session_data dict.
    """
    in_t  = session_data.get("in_time",  "")
    out_t = session_data.get("out_time", "")
    is_holiday = session_data.get("is_holiday", False)

    if is_holiday:
        # Paid holiday — always mark as full day present
        session_data["duty_status"] = "full"
        session_data["duty_hours"]  = session_data.get("duty_hours", 8.0)
        try:
            db.collection("sessions").document(doc_id).update({
                "duty_status": "full",
            })
        except Exception:
            pass
        return session_data

    if in_t and out_t:
        in_f  = _hhmm_to_float(str(in_t)[:5])
        out_f = _hhmm_to_float(str(out_t)[:5])
        hours = out_f - in_f
        if hours < 0:
            hours += 24  # overnight shift
        duty = classify_duty(hours)
        # OT hours (ot_in_time → ot_out_time)
        ot_in  = session_data.get("ot_in_time",  "")
        ot_out = session_data.get("ot_out_time", "")
        ot_hours = 0.0
        if ot_in and ot_out:
            ot_hours = _hhmm_to_float(str(ot_out)[:5]) - _hhmm_to_float(str(ot_in)[:5])
            if ot_hours < 0:
                ot_hours += 24
        ot_status = classify_ot(ot_hours)

        session_data["duty_status"] = duty
        session_data["duty_hours"]  = round(hours, 2)
        session_data["ot_status"]   = ot_status
        session_data["ot_hours"]    = round(ot_hours, 2)
        try:
            db.collection("sessions").document(doc_id).update({
                "duty_status": duty,
                "duty_hours":  round(hours, 2),
                "ot_status":   ot_status,
                "ot_hours":    round(ot_hours, 2),
            })
        except Exception:
            pass
    elif in_t and not out_t:
        # Checked in but not yet checked out — keep as absent until OUT arrives
        if not session_data.get("duty_status"):
            session_data["duty_status"] = "absent"

    return session_data


# ────────────────────────────────────────────────────────────────────
class AttendanceModule:
    def __init__(self, parent_frame, current_user):
        self.parent       = parent_frame
        self.current_user = current_user
        self.role         = current_user.get("role", "manager")
        self.db           = get_db()
        self._emp_name_cache = {}   # emp_id -> name  (avoids repeated Firestore lookups)
        self._build_ui()
        self._load_logs()

    # ───────────────────────────────────────────────────────────────── UI
    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="\U0001f4c5 Attendance Management",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

        if has_permission(self.role, "attendance"):
            tk.Button(top, text="\u2705 Mark Present",
                      bg="#27ae60", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._mark_present_dialog).pack(side="right", padx=4)
            tk.Button(top, text="\u274c Mark Absent",
                      bg="#c0392b", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._mark_absent_dialog).pack(side="right", padx=4)
            tk.Button(top, text="\u270f\ufe0f Edit Session",
                      bg="#1e6f9f", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._edit_selected).pack(side="right", padx=4)
        if self.role in ("super_admin", "admin"):
            tk.Button(top, text="\U0001f5d1 Delete",
                      bg="#7f1f1f", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=self._delete_selected).pack(side="right", padx=4)
        tk.Button(top, text="\U0001f504 Refresh",
                  bg="#555", fg="white", font=("Arial", 9),
                  relief="flat", padx=8, pady=4,
                  command=self._load_logs).pack(side="right", padx=4)
        # Sync button — re-run duty calc on all loaded sessions
        tk.Button(top, text="\U0001f501 Sync Duty",
                  bg="#7d3c98", fg="white", font=("Arial", 9),
                  relief="flat", padx=8, pady=4,
                  command=self._sync_all_duty).pack(side="right", padx=4)

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

        self.tree.tag_configure("present",  foreground="#00cc66")
        self.tree.tag_configure("half",     foreground="#f0c040")
        self.tree.tag_configure("absent",   foreground="#e74c3c")
        self.tree.tag_configure("holiday",  foreground="#3498db")

    # ──────────────────── NAME RESOLVER ───────────────────────────────────────
    def _resolve_name(self, emp_id: str, session_doc: dict) -> str:
        name = _extract_name_from_doc(session_doc)
        if name:
            self._emp_name_cache[emp_id] = name
            return name
        cached = self._emp_name_cache.get(emp_id, "")
        if cached:
            return cached
        _, emp = _find_employee_by_id(self.db, emp_id)
        if emp:
            name = _extract_name_from_doc(emp)
            if name:
                self._emp_name_cache[emp_id] = name
                return name
        return emp_id

    # ───────────────────────────────────────────────────────────────── LOAD
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
            emp_id  = d.get("employee_id", "").strip().upper()
            name    = self._resolve_name(emp_id, d)
            dt      = d.get("date", "")
            # FIX: recompute duty_status live if in_time + out_time present
            # but duty_status is still 'absent' (QR scan wrote absent as default)
            in_t_raw  = d.get("in_time",  "")
            out_t_raw = d.get("out_time", "")
            duty      = d.get("duty_status", d.get("status", ""))
            if in_t_raw and out_t_raw and duty == "absent":
                # Silently recompute without blocking the UI
                in_f  = _hhmm_to_float(str(in_t_raw)[:5])
                out_f = _hhmm_to_float(str(out_t_raw)[:5])
                hours = out_f - in_f
                if hours < 0: hours += 24
                duty = classify_duty(hours)

            is_holiday = d.get("is_holiday", False)
            if is_holiday:
                duty = "full"  # Paid holiday — always full

            ot      = d.get("ot_status", "")
            in_t    = _to_ist_hhmm(d.get("in_time", ""))  if d.get("in_time")  else "\u2014"
            out_t   = _to_ist_hhmm(d.get("out_time", "")) if d.get("out_time") else "\u2014"
            hours   = d.get("duty_hours", "")
            loc     = _parse_location(d.get("location", d.get("check_in_location", "")))

            if is_holiday:
                tag = "holiday"
            elif duty == "full":
                tag = "present"
            elif duty == "half":
                tag = "half"
            else:
                tag = "absent"

            self.tree.insert("", "end", values=(
                emp_id, name, dt,
                ("\U0001f389 Holiday" if is_holiday else duty.title()) if duty else "\u2014",
                ot.title()   if ot   else "\u2014",
                in_t, out_t,
                f"{float(hours):.1f}h" if hours else "\u2014",
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

    # ──────────────────── SYNC ALL DUTY ─────────────────────────────────────
    def _sync_all_duty(self):
        """Re-run _sync_duty_from_times on all currently displayed sessions."""
        children = self.tree.get_children()
        if not children:
            messagebox.showinfo("Sync", "No sessions loaded. Load first."); return
        synced = 0
        for iid in children:
            vals   = self.tree.item(iid)["values"]
            doc_id = vals[9] if len(vals) > 9 else ""
            if not doc_id: continue
            try:
                doc = self.db.collection("sessions").document(doc_id).get()
                if doc.exists:
                    d = doc.to_dict()
                    _sync_duty_from_times(self.db, doc_id, d)
                    synced += 1
            except Exception:
                pass
        messagebox.showinfo("\u2705 Sync Done", f"Recomputed duty for {synced} sessions.")
        self._apply_filter()

    # ────────────────────────────────────────────────────────── MARK PRESENT
    def _mark_present_dialog(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("\u2705 Mark Present")
        dlg.geometry("400x380")
        dlg.configure(bg="#0d1b2a")
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = tk.Frame(dlg, bg="#0d1b2a", padx=24, pady=18)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="\u2705 Mark Employee Present",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w")
        tk.Label(frm, text="Type Employee ID then Tab to validate (e.g. EMP-0001)",
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
                    text=f"\u2705 {_extract_name_from_doc(emp)} | {emp.get('designation', '')}",
                    fg="#27ae60"
                )
            else:
                name_lbl.config(text="\u274c Employee not found", fg="#e74c3c")

        def _schedule_lookup(*_):
            if _lookup_job[0]:
                try: dlg.after_cancel(_lookup_job[0])
                except Exception: pass
            _lookup_job[0] = dlg.after(400, _do_lookup)

        v_emp.trace_add("write", _schedule_lookup)

        def _save():
            eid   = v_emp.get().strip().upper()
            dt    = v_date.get().strip()
            in_t  = v_in.get().strip()
            out_t = v_out.get().strip()
            duty  = v_duty.get()
            ot    = v_ot.get()
            if not eid or not dt:
                messagebox.showerror("Error", "Employee ID and Date are required.", parent=dlg)
                return
            uid, emp = _find_employee_by_id(self.db, eid)
            if not emp:
                messagebox.showerror("Not Found",
                    f"No employee found with ID: {eid}", parent=dlg)
                return
            emp_name = _extract_name_from_doc(emp)
            # Auto-compute duty_hours and duty_status from times if provided
            duty_hours = 0.0
            if in_t and out_t:
                try:
                    in_f  = _hhmm_to_float(in_t)
                    out_f = _hhmm_to_float(out_t)
                    duty_hours = out_f - in_f
                    if duty_hours < 0: duty_hours += 24
                    duty = classify_duty(duty_hours)  # auto-set from hours
                except Exception:
                    pass

            doc_id = f"{eid}_{dt}"
            session_data = {
                "employee_id":   eid,
                "employee_name": emp_name,
                "name":          emp_name,
                "date":          dt,
                "duty_status":   duty,
                "ot_status":     ot,
                "in_time":       in_t,
                "out_time":      out_t,
                "duty_hours":    round(duty_hours, 2),
                "marked_by":     self.current_user.get("employee_id", "admin"),
                "marked_at":     datetime.now(IST).isoformat(),
                "source":        "manual",
            }
            try:
                self.db.collection("sessions").document(doc_id).set(session_data)
                messagebox.showinfo("\u2705 Saved",
                    f"{emp_name or eid} marked {duty.upper()} on {dt}.", parent=dlg)
                dlg.destroy()
                self._load_logs()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=dlg)

        tk.Button(frm, text="\u2705 Save", command=_save,
                  bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=14, pady=5).pack(anchor="w", pady=(10, 0))

    # ───────────────────────────────────────────────────────── MARK ABSENT
    def _mark_absent_dialog(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("\u274c Mark Absent")
        dlg.geometry("380x260")
        dlg.configure(bg="#0d1b2a")
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = tk.Frame(dlg, bg="#0d1b2a", padx=24, pady=18)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="\u274c Mark Employee Absent",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w")
        tk.Label(frm, text="Type Employee ID then Tab to validate (e.g. EMP-0001)",
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

        name_lbl = tk.Label(frm, text="", bg="#0d1b2a", fg="#27ae60", font=("Arial", 9, "bold"))
        name_lbl.pack(anchor="w")
        _lookup_job = [None]

        def _do_lookup():
            eid = v_emp.get().strip().upper()
            if not eid:
                name_lbl.config(text=""); return
            _, emp = _find_employee_by_id(self.db, eid)
            if emp:
                name_lbl.config(text=f"\u2705 {_extract_name_from_doc(emp)}", fg="#27ae60")
            else:
                name_lbl.config(text="\u274c Employee not found", fg="#e74c3c")

        def _schedule_lookup(*_):
            if _lookup_job[0]:
                try: dlg.after_cancel(_lookup_job[0])
                except Exception: pass
            _lookup_job[0] = dlg.after(400, _do_lookup)

        v_emp.trace_add("write", _schedule_lookup)

        def _save():
            eid = v_emp.get().strip().upper()
            dt  = v_date.get().strip()
            if not eid or not dt:
                messagebox.showerror("Error", "Employee ID and Date are required.", parent=dlg)
                return
            uid, emp = _find_employee_by_id(self.db, eid)
            if not emp:
                messagebox.showerror("Not Found",
                    f"No employee found with ID: {eid}", parent=dlg)
                return
            emp_name = _extract_name_from_doc(emp)
            doc_id = f"{eid}_{dt}"
            session_data = {
                "employee_id":   eid,
                "employee_name": emp_name,
                "name":          emp_name,
                "date":          dt,
                "duty_status":   "absent",
                "ot_status":     "none",
                "in_time":       "",
                "out_time":      "",
                "duty_hours":    0.0,
                "marked_by":     self.current_user.get("employee_id", "admin"),
                "marked_at":     datetime.now(IST).isoformat(),
                "source":        "manual",
            }
            try:
                self.db.collection("sessions").document(doc_id).set(session_data)
                messagebox.showinfo("\u2705 Saved",
                    f"{emp_name or eid} marked ABSENT on {dt}.", parent=dlg)
                dlg.destroy()
                self._load_logs()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=dlg)

        tk.Button(frm, text="\u274c Save Absent", command=_save,
                  bg="#c0392b", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=14, pady=5).pack(anchor="w", pady=(10, 0))

    # ───────────────────────────────────────────────────────────────── EDIT
    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a session row to edit."); return
        vals   = self.tree.item(sel[0])["values"]
        doc_id = vals[9] if len(vals) > 9 else ""
        emp_id = vals[0]
        dt     = vals[2]
        duty   = vals[3].lower() if vals[3] else "absent"
        ot     = vals[4].lower() if vals[4] else "none"
        # Strip emoji if present
        for s in DUTY_OPTIONS:
            if s in duty: duty = s; break

        dlg = tk.Toplevel(self.parent)
        dlg.title(f"\u270f\ufe0f Edit Session \u2014 {emp_id} / {dt}")
        dlg.geometry("340x220")
        dlg.configure(bg="#0d1b2a")
        dlg.grab_set()
        dlg.resizable(False, False)

        frm = tk.Frame(dlg, bg="#0d1b2a", padx=24, pady=16)
        frm.pack(fill="both", expand=True)
        tk.Label(frm, text=f"Employee: {emp_id}  |  Date: {dt}",
                 bg="#0d1b2a", fg="#f0c040", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

        dr = tk.Frame(frm, bg="#0d1b2a"); dr.pack(fill="x", pady=4)
        tk.Label(dr, text="Duty Status:", width=14, anchor="w", bg="#0d1b2a", fg="#ccc").pack(side="left")
        v_duty = tk.StringVar(value=duty if duty in DUTY_OPTIONS else "absent")
        ttk.Combobox(dr, textvariable=v_duty, values=DUTY_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        or2 = tk.Frame(frm, bg="#0d1b2a"); or2.pack(fill="x", pady=4)
        tk.Label(or2, text="OT Status:", width=14, anchor="w", bg="#0d1b2a", fg="#ccc").pack(side="left")
        v_ot = tk.StringVar(value=ot if ot in OT_OPTIONS else "none")
        ttk.Combobox(or2, textvariable=v_ot, values=OT_OPTIONS,
                     width=12, state="readonly").pack(side="left")

        def _save():
            if not doc_id:
                messagebox.showerror("Error", "Cannot edit: doc ID missing.", parent=dlg)
                return
            try:
                self.db.collection("sessions").document(doc_id).update({
                    "duty_status": v_duty.get(),
                    "ot_status":   v_ot.get(),
                    "edited_by":   self.current_user.get("employee_id", "admin"),
                    "edited_at":   datetime.now(IST).isoformat(),
                })
                messagebox.showinfo("\u2705 Updated", "Session updated.", parent=dlg)
                dlg.destroy()
                self._apply_filter()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=dlg)

        tk.Button(frm, text="\u2714 Save", command=_save,
                  bg="#1e6f9f", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=14, pady=5).pack(anchor="w", pady=(14, 0))

    # ─────────────────────────────────────────────────────────────── DELETE
    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a session row to delete."); return
        vals   = self.tree.item(sel[0])["values"]
        doc_id = vals[9] if len(vals) > 9 else ""
        emp_id = vals[0]
        dt     = vals[2]
        if not doc_id:
            messagebox.showerror("Error", "Cannot delete: doc ID missing."); return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete session for {emp_id} on {dt}?",
            icon="warning"
        ):
            return
        try:
            self.db.collection("sessions").document(doc_id).delete()
            messagebox.showinfo("\u2705 Deleted", f"Session deleted: {emp_id} / {dt}")
            self._apply_filter()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
