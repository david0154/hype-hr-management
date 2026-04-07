"""
Attendance Module — Hype HR Management
Duty rules: <4=Absent, 4-7=HalfDay, >=7=FullDay
OT rules:   <4=NoOT,  4-7=HalfOT,  >=7=FullOT
Sunday pay: Sat+Mon=Full, Sat+!Mon=Half, !Sat=None
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
from utils.firebase_config import get_db


def classify_duty(hours: float) -> str:
    if hours < 4:   return "Absent"
    elif hours < 7: return "Half Day"
    return "Full Day"


def classify_ot(hours: float) -> str:
    if hours < 4:   return "No OT"
    elif hours < 7: return "Half OT"
    return "Full OT"


def sunday_pay_status(db, employee_id: str, sunday: date) -> str:
    sat = sunday - timedelta(days=1)
    mon = sunday + timedelta(days=1)

    def is_present(check_date):
        docs = db.collection("sessions") \
            .where("employee_id", "==", employee_id) \
            .where("date", "==", str(check_date)).get()
        return any(d.to_dict().get("status") in ("Full Day", "Half Day") for d in docs)

    sat_p = is_present(sat)
    mon_p = is_present(mon)
    if sat_p and mon_p:       return "Full Pay"
    elif sat_p and not mon_p: return "Half Pay"
    else:                     return "No Pay"


def calculate_monthly_summary(employee_id: str, year: int, month: int) -> dict:
    import calendar
    db = get_db()
    month_str = f"{year}-{month:02d}"
    sessions = db.collection("sessions") \
        .where("employee_id", "==", employee_id) \
        .where("date", ">=", f"{month_str}-01") \
        .where("date", "<=", f"{month_str}-31").stream()

    total_present = 0
    half_days = 0
    absent_days = 0
    ot_hours = 0.0

    for sess in sessions:
        s = sess.to_dict()
        status = s.get("status", "Absent")
        if status == "Full Day":        total_present += 1
        elif status == "Half Day":      half_days += 1; total_present += 0.5
        else:                           absent_days += 1
        ot_stat = s.get("ot_status", "No OT")
        if ot_stat in ("Full OT", "Half OT"): ot_hours += s.get("ot_hours", 0)

    _, days_in_month = calendar.monthrange(year, month)
    paid_holidays = 0
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() == 6:
            pay = sunday_pay_status(db, employee_id, d)
            if pay == "Full Pay":  paid_holidays += 1
            elif pay == "Half Pay": paid_holidays += 0.5

    return {
        "total_present":      total_present,
        "half_days":          half_days,
        "absent_days":        absent_days,
        "ot_hours":           round(ot_hours, 2),
        "paid_holidays":      paid_holidays,
        "total_working_days": days_in_month,
    }


class AttendanceModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.db = get_db()
        self._build_ui()
        self._load_logs()

    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="📋 Attendance Logs",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

        ff = tk.Frame(self.parent, bg="#0d1b2a")
        ff.pack(fill="x", padx=10, pady=5)
        tk.Label(ff, text="Employee ID:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.filter_emp  = tk.StringVar()
        tk.Entry(ff, textvariable=self.filter_emp, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=14).pack(side="left", padx=5)
        tk.Label(ff, text="Date (YYYY-MM-DD):", bg="#0d1b2a", fg="#ccc").pack(side="left", padx=(10, 0))
        self.filter_date = tk.StringVar()
        tk.Entry(ff, textvariable=self.filter_date, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=13).pack(side="left", padx=5)
        tk.Button(ff, text="Filter", bg="#f77f00", fg="white", relief="flat",
                  command=self._load_logs).pack(side="left", padx=5)
        tk.Button(ff, text="Reset", bg="#555", fg="white", relief="flat",
                  command=self._reset).pack(side="left")

        cols = ("Employee ID", "Name", "Date", "Time", "Location", "Action", "Session")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.status_var = tk.StringVar(value="Loading...")
        tk.Label(self.parent, textvariable=self.status_var,
                 bg="#0d1b2a", fg="#aaa", font=("Arial", 9)).pack(anchor="w", padx=10, pady=3)

    def _reset(self):
        self.filter_emp.set("")
        self.filter_date.set("")
        self._load_logs()

    def _load_logs(self):
        try:
            query = self.db.collection("attendance_logs") \
                .order_by("timestamp", direction="DESCENDING").limit(200)
            emp_f  = self.filter_emp.get().strip()
            date_f = self.filter_date.get().strip()
            if emp_f: query = query.where("employee_id", "==", emp_f)
            docs = query.stream()
            for row in self.tree.get_children(): self.tree.delete(row)
            count = 0
            for doc in docs:
                log = doc.to_dict()
                ts  = log.get("timestamp", "")
                if date_f and date_f not in str(ts): continue
                emp_id = log.get("employee_id", "")
                emp_doc = self.db.collection("employees").document(emp_id).get()
                emp_name = emp_doc.to_dict().get("name", "") if emp_doc.exists else ""
                action = log.get("action", "")
                self.tree.insert("", "end", values=(
                    emp_id, emp_name, str(ts)[:10], str(ts)[11:19],
                    log.get("location", ""), action, log.get("session", 1)
                ), tags=("in" if action == "IN" else "out",))
                count += 1
            self.tree.tag_configure("in",  foreground="#00ff88")
            self.tree.tag_configure("out", foreground="#ff8844")
            self.status_var.set(f"Showing {count} records")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load attendance: {e}")
