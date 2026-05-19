"""
Live Dashboard — Hype HR Management
KPIs: Total Employees, Present Today, Absent, Inside Now
All times displayed in IST (Asia/Kolkata).
FIX: Employee name now resolved from multiple field names + cached to avoid repeated Firestore calls.
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
    try:
        from google.cloud.firestore_v1 import base_document
        from google.protobuf.timestamp_pb2 import Timestamp as ProtoTS
    except ImportError:
        pass

    try:
        if hasattr(ts_value, 'tzinfo'):
            from datetime import timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            dt = ts_value.astimezone(ist)
            return dt.strftime("%H:%M")
        if hasattr(ts_value, 'seconds'):
            from datetime import datetime, timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            dt = datetime.fromtimestamp(ts_value.seconds, tz=ist)
            return dt.strftime("%H:%M")
        s = str(ts_value)
        if len(s) >= 19:
            time_part = s[11:16]
            h, m = int(time_part[:2]), int(time_part[3:5])
            total = h * 60 + m + 330
            return "%02d:%02d" % (total // 60 % 24, total % 60)
        return s
    except Exception:
        return str(ts_value)[:5]


def _parse_location(loc_raw) -> str:
    if not loc_raw:
        return ""
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


def _extract_name(data: dict) -> str:
    """
    Try every possible field name an employee doc or log doc
    might store the display name under.
    """
    for field in (
        "name", "full_name", "employee_name", "employeeName",
        "displayName", "display_name", "emp_name",
    ):
        val = data.get(field, "")
        if val and str(val).strip():
            return str(val).strip()
    return ""


class DashboardModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.db = get_db()
        # Cache: emp_id / uid -> (display_id, name)
        self._emp_cache = {}   # key -> {"display_id": ..., "name": ...}
        self._build_ui()
        self._preload_emp_cache()
        self._refresh()

    # ──────────────────── CACHE ───────────────────────────────────
    def _preload_emp_cache(self):
        """
        Load all active employees into memory once.
        Keyed by both employee_id (EMP-XXXX) and uid so
        both formats found in attendance_logs are resolved.
        """
        try:
            docs = self.db.collection("employees").stream()
            for doc in docs:
                d = doc.to_dict()
                name       = _extract_name(d)
                emp_id     = d.get("employee_id", "").strip().upper()
                uid        = d.get("uid", doc.id).strip()
                entry      = {"display_id": emp_id or uid, "name": name}
                if emp_id:
                    self._emp_cache[emp_id] = entry
                if uid:
                    self._emp_cache[uid]    = entry
        except Exception:
            pass

    def _resolve(self, raw_id: str):
        """
        Given raw_id (either EMP-XXXX or Firebase UID from log),
        return (display_id, name).
        Falls back to live Firestore lookup if not in cache.
        """
        raw_id = (raw_id or "").strip()
        if not raw_id:
            return "", ""

        # 1. Cache hit
        hit = self._emp_cache.get(raw_id) or self._emp_cache.get(raw_id.upper())
        if hit:
            return hit["display_id"], hit["name"]

        # 2. Live lookup — direct doc (legacy: doc key == emp_id)
        try:
            doc = self.db.collection("employees").document(raw_id).get()
            if doc.exists:
                d    = doc.to_dict()
                name = _extract_name(d)
                did  = d.get("employee_id", raw_id)
                self._emp_cache[raw_id] = {"display_id": did, "name": name}
                return did, name
        except Exception:
            pass

        # 3. Live lookup by employee_id field
        try:
            results = list(
                self.db.collection("employees")
                    .where("employee_id", "==", raw_id.upper())
                    .limit(1).stream()
            )
            if results:
                d    = results[0].to_dict()
                name = _extract_name(d)
                did  = d.get("employee_id", raw_id)
                uid  = d.get("uid", results[0].id)
                entry = {"display_id": did, "name": name}
                self._emp_cache[raw_id] = entry
                if uid: self._emp_cache[uid] = entry
                return did, name
        except Exception:
            pass

        # 4. Live lookup by uid field (raw_id is a Firebase UID)
        try:
            results = list(
                self.db.collection("employees")
                    .where("uid", "==", raw_id)
                    .limit(1).stream()
            )
            if results:
                d    = results[0].to_dict()
                name = _extract_name(d)
                did  = d.get("employee_id", raw_id)
                entry = {"display_id": did, "name": name}
                self._emp_cache[raw_id] = entry
                return did, name
        except Exception:
            pass

        # 5. Not found — show raw_id, never blank
        return raw_id, raw_id

    # ──────────────────── UI ────────────────────────────────────
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
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(tz=ist)
        self.clock_label.config(text=now_ist.strftime("%A, %d %B %Y  %H:%M:%S"))
        self.parent.after(1000, self._update_clock)

    def _refresh(self):
        # Re-populate cache on every refresh so new employees appear
        self._preload_emp_cache()
        try:
            db = self.db
            today = str(date.today())

            emp_count = len(list(db.collection("employees").where("status", "==", "active").stream()))
            self.kpi_vars["total_emp"].set(str(emp_count))

            sessions = list(db.collection("sessions").where("date", "==", today).stream())
            present = sum(1 for s in sessions if s.to_dict().get("status") in ("Full Day", "Half Day"))
            self.kpi_vars["present_today"].set(str(present))
            self.kpi_vars["absent_today"].set(str(emp_count - present))

            # ─ Employees Currently Inside ────────────────────────────────────
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
                    raw_id              = last_log.get("employee_id", key)
                    display_id, name    = self._resolve(raw_id)
                    # Also try log doc itself for name (saves a Firestore round-trip)
                    if not name or name == raw_id:
                        name = _extract_name(last_log) or name
                    in_time  = _to_ist_hhmm(last_log.get("timestamp", ""))
                    location = _parse_location(last_log.get("location", ""))
                    self.inside_tree.insert("", "end",
                        values=(display_id, name, in_time, location))
                    inside_count += 1
            self.kpi_vars["inside_now"].set(str(inside_count))

            # ─ Recent Activity ─────────────────────────────────────────────
            for row in self.activity_tree.get_children():
                self.activity_tree.delete(row)

            recent = list(
                db.collection("attendance_logs")
                  .order_by("timestamp", direction="DESCENDING")
                  .limit(20).stream()
            )
            for log in recent:
                l               = log.to_dict()
                raw_id          = l.get("employee_id", "")
                display_id, name = self._resolve(raw_id)
                # Also try log doc itself for name
                if not name or name == raw_id:
                    name = _extract_name(l) or name
                ist_time  = _to_ist_hhmm(l.get("timestamp", ""))
                action    = (l.get("action") or l.get("type", "")).upper()
                location  = _parse_location(l.get("location", ""))
                tag = {"IN": "in_t", "OUT": "out_t",
                       "OT_IN": "ot_in_t", "OT_OUT": "ot_out_t"}.get(action, "")
                self.activity_tree.insert("", "end",
                    values=(ist_time, display_id, name, action, location),
                    tags=(tag,))

            self.activity_tree.tag_configure("in_t",     foreground="#00cc66")
            self.activity_tree.tag_configure("out_t",    foreground="#ff8844")
            self.activity_tree.tag_configure("ot_in_t",  foreground="#00aaff")
            self.activity_tree.tag_configure("ot_out_t", foreground="#ffaa00")

        except Exception as e:
            print(f"Dashboard error: {e}")
