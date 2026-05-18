"""
Attendance Module — Hype HR Management
Features:
  - View all attendance logs (filterable by employee / date)
  - Manual Mark: Mark Present (Full/Half) or Absent for any employee
  - Edit existing session: change duty_status / ot_status
  - Delete log entry (Super Admin / Admin only)
FIX: All .where() use FieldFilter keyword → no UserWarning.
FIX: Employee lookup queries by employee_id field (not doc ID = UID).
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
    # Try direct doc lookup first (legacy: doc key == emp_id)
    direct = db.collection("employees").document(emp_id).get()
    if direct.exists:
        d = direct.to_dict()
        return d.get("uid", emp_id), d
    # Standard: doc key == UID, query by field
    results = list(_ff(db.collection("employees"), "employee_id", "==", emp_id).limit(1).stream())
    if results:
        d = results[0].to_dict()
        return d.get("uid", results[0].id), d
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

        ff = tk.Frame(self.parent, bg="#0d1b2a")
        ff.pack(fill="x", padx=10, pady=4)
        tk.Label(ff, text="Employee ID:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.filter_emp = tk.StringVar()
        tk.Entry(ff, textvariable=self.filter_emp, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=13).pack(side="left", padx=4)
        tk.Label(ff, text="Date (YYYY-MM-DD):", bg="#0d1b2a", fg="#ccc").pack(side="left", padx=(8,0))
 