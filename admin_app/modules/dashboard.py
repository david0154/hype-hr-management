"""
Live Dashboard — Hype HR Management
KPIs: Total Employees, Present Today, Absent, Inside Now
All times displayed in IST (Asia/Kolkata).
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk
from datetime import date
import json

try:
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
except Exception:
    IST = None

from utils.firebase_config import get_db


def _to_ist_hhmm(ts_value) -> str:
    """
    Convert a Firestore Timestamp / datetime / string to HH:MM in IST.
    Firestore Timestamps are UTC — add +5:30 for IST.
    """
    try:
        from google.cloud.firestore_v1 import base_document
        from google.protobuf.timestamp_pb2 import Timestamp as ProtoTS
    except ImportError:
        pass

    try:
        # google.cloud.firestore DatetimeWithNanoseconds / datetime object
        if hasattr(ts_value, 'tzinfo'):
            from datetime import timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            dt = ts_value.astimezone(ist)
            return dt.strftime("%H:%M")
        # google.cloud.firestore Timestamp with .seconds
        if hasattr(ts_value, 'seconds'):
            from datetime import datetime, timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            dt = datetime.fromtimestamp(ts_value.seconds, tz=ist)
            return dt.strftime("%H:%M")
        # plain string fallback — assume UTC HH:MM, add 5:30
        s = str(ts_value)
        if len(s) >= 19:
            time_part = s[11:16]  # HH:MM
            h, m = int(time_part[:2]), int(time_part[3:5])
            total = h * 60 + m + 330  # add 5h30m in minutes
            return "%02d:%02d" % (total // 60 % 24, total % 60)
        return s
    except Exception:
        return str(ts_value)[:5]


def _parse_location(loc_raw) -> str:
    """
    Location field may be:
      - plain string: "Main Gate"  or  "HYPE_LOC|Main Gate"
      - JSON string: '{"type":"location","location_name":"Main Gate",...}'
      - dict object
    Returns only the human-readable location name.
    """
    if not loc_raw:
        return ""
    # dict
    if isinstance(loc_raw, dict):
        return loc_raw.get("location_name") or loc_raw.get("location", "")
    s = str(loc_raw).strip()
    # JSON string
    if s.startswith("{"):
        try:
            d = json.loads(s)
            return d.get("location_name") or d.get("location", s)
        except Exception:
            return s
    # HYPE_LOC| prefix (new QR format)
    if s.startswith("HYPE_LOC|"):
        return s[len("HYPE_LOC|"):]
    return s


class DashboardModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.db = get_db()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        header = tk.Frame(self.parent, bg="#1a2740", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="\U0001f4ca Live Dashboard",
                 font=("Arial", 15, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=15)
        self.clock_label = tk.Label(header, font=("Arial", 12), bg="#1a2740", fg="#f77f00")
        self.clock_label.pack(side="right", padx=15)
        self._update_clock()

        kpi_frame = tk.Frame(self.parent, bg="#0d1b2a")
        kpi_frame.pack(fill="x", padx=15, pady=10)
        self.kpi_vars = {}
        kpis = [
            ("Total Employees",  "total_emp",     "#1e6f9f"),
            ("Present Today",    "present_today", "#2e8b57"),
            ("Absent Today",     "absent_today",  "#c0392b"),
            ("Inside Right Now", "inside_now",    "#8e44ad"),
        ]
        for i, (label, key, color) in enumerate(kpis):
            card = tk.Frame(kpi_frame, bg=color, padx=20, pady=15)
            card.grid(row=0, column=i, padx=8, ipadx=10)
            self.kpi_vars[key] = tk.StringVar(value="\u2014")
            tk.Label(card, textvariable=self.kpi_vars[key],
                     font=("Arial", 24, "bold"), bg=color, fg="white").pack()
            tk.Label(card, text=label, font=("Arial", 9), bg=color, fg="#ddd").pack()

        tk.Label(self.parent, text="\U0001f7e2 Employees Currently Inside",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", padx=15, pady=(10, 3))
        cols = ("Employee ID", "Name", "IN Time", "Location")
        self.inside_tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=7)
        for col in cols:
            self.inside_tree.heading(col, text=col)
            self.inside_tree.column(col, width=155, anchor="center")
        self.inside_tree.pack(fill="x", padx=15)

        tk.Label(self.parent, text="\U0001f550 Recent Activity",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", padx=15, pady=(10, 3))
        cols2 = ("Time", "Employee ID", "Name", "Action", "Location")
        self.activity_tree = ttk.Treeview(self.parent, columns=cols2, show="headings", height=6)
        for col in cols2:
            self.activity_tree.heading(col, text=col)
            self.activity_tree.column(col, width=130, anchor="center")
        self.activity_tree.pack(fill="x", padx=15)

        tk.Button(self.parent, text="\U0001f504 Refresh", bg="#1e3a5f", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2", command=self._refresh).pack(pady=8)

    def _update_clock(self):
        """Show current IST time in the header clock."""
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(tz=ist)
        self.clock_label.config(text=now_ist.strftime("%A, %d %B %Y  %H:%M:%S"))
        self.parent.after(1000, self._update_clock)

    def _resolve_emp_name(self, emp_id: str, uid: str = "") -> str:
        """Resolve employee name. Tries direct doc, then uid-field query."""
        try:
            doc = self.db.collection("employees").document(emp_id).get()
            if doc.exists:
                return doc.to_dict().get("name", "")
            # emp_id is actually a UID — query by uid field
            if uid:
                q = self.db.collection("employees").where("uid", "==", uid).limit(1).stream()
                for d in q:
                    return d.to_dict().get("name", "")
            # fallback: uid == emp_id slot
            q = self.db.collection("employees").where("uid", "==", emp_id).limit(1).stream()
            for d in q:
                return d.to_dict().get("name", "")
        except Exception:
            pass
        return ""

    def _resolve_display_id(self, emp_id: str) -> str:
        """Return EMP-XXXX code if emp_id looks like a UID."""
        if len(emp_id) > 15:  # UID is long
            try:
                q = self.db.collection("employees").where("uid", "==", emp_id).limit(1).stream()
                for d in q:
                    return d.to_dict().get("employee_id", emp_id)
            except Exception:
                pass
        return emp_id

    def _refresh(self):
        try:
            db = self.db
            today = str(date.today())

            emp_count = len(list(db.collection("employees").where("status", "==", "active").stream()))
            self.kpi_vars["total_emp"].set(str(emp_count))

            sessions = list(db.collection("sessions").where("date", "==", today).stream())
            present = sum(1 for s in sessions if s.to_dict().get("status") in ("Full Day", "Half Day"))
            self.kpi_vars["present_today"].set(str(present))
            self.kpi_vars["absent_today"].set(str(emp_count - present))

            # ─ Employees Currently Inside ───────────────────────────────
            for row in self.inside_tree.get_children():
                self.inside_tree.delete(row)

            logs = list(db.collection("attendance_logs").where("date", "==", today).stream())
            emp_states = {}
            for log in sorted(logs, key=lambda x: x.to_dict().get("timestamp") or ""):
                d = log.to_dict()
                key = d.get("uid") or d.get("employee_id", "")
                emp_states[key] = d

            inside_count = 0
            for key, last_log in emp_states.items():
                action = (last_log.get("action") or last_log.get("type", "")).upper()
                if action in ("IN", "OT_IN"):
                    emp_id_raw = last_log.get("employee_id", key)
                    display_id = self._resolve_display_id(emp_id_raw)
                    emp_name   = self._resolve_emp_name(emp_id_raw)
                    in_time    = _to_ist_hhmm(last_log.get("timestamp", ""))
                    location   = _parse_location(last_log.get("location", ""))
                    self.inside_tree.insert("", "end", values=(display_id, emp_name, in_time, location))
                    inside_count += 1
            self.kpi_vars["inside_now"].set(str(inside_count))

            # ─ Recent Activity ──────────────────────────────────────
            for row in self.activity_tree.get_children():
                self.activity_tree.delete(row)

            recent = list(
                db.collection("attendance_logs")
                  .order_by("timestamp", direction="DESCENDING")
                  .limit(20).stream()
            )
            for log in recent:
                l = log.to_dict()
                emp_id_raw = l.get("employee_id", "")
                display_id = self._resolve_display_id(emp_id_raw)
                emp_name   = self._resolve_emp_name(emp_id_raw)
                ist_time   = _to_ist_hhmm(l.get("timestamp", ""))
                action     = (l.get("action") or l.get("type", "")).upper()
                location   = _parse_location(l.get("location", ""))
                tag = {"IN": "in_t", "OUT": "out_t",
                       "OT_IN": "ot_in_t", "OT_OUT": "ot_out_t"}.get(action, "")
                self.activity_tree.insert("", "end",
                    values=(ist_time, display_id, emp_name, action, location),
                    tags=(tag,))

            self.activity_tree.tag_configure("in_t",     foreground="#00cc66")
            self.activity_tree.tag_configure("out_t",    foreground="#ff8844")
            self.activity_tree.tag_configure("ot_in_t",  foreground="#00aaff")
            self.activity_tree.tag_configure("ot_out_t", foreground="#ffaa00")

        except Exception as e:
            print(f"Dashboard error: {e}")
