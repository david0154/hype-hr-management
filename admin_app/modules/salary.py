# salary.py — Salary Panel + Bonus Logic (religion-based dates)

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from utils.db import read_all, read, write, update
import calendar

OT_MULTIPLIER  = 1.5
WORKING_DAYS   = 26
BONUS_MIN_DAYS = 240

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12
}


# ─── Bonus helpers ─────────────────────────────────────────────────────────
def get_bonus_config():
    """
    Returns bonus_dates config from Firestore settings/bonus_dates.
    Structure: { "hindu": {"month": "March", "day": 1, "enabled": True}, ... }
    """
    return read("settings", "bonus_dates") or {}


def get_app_settings():
    return read("settings", "app") or {}


def is_bonus_month_for_religion(religion: str, month: int, year: int) -> bool:
    """
    Check if today's month matches the configured bonus month for this religion.
    e.g. Hindu bonus in March, Muslim bonus in April, etc.
    """
    bonus_config = get_bonus_config()
    key  = (religion or "other").lower()
    conf = bonus_config.get(key, bonus_config.get("other", {}))
    if not conf or not conf.get("enabled", False):
        return False
    bonus_month = MONTH_MAP.get(conf.get("month", "March"), 3)
    return month == bonus_month


def is_bonus_eligible(employee_id: str, current_year: int) -> bool:
    """Employee must have worked >= BONUS_MIN_DAYS in previous year."""
    app_settings = get_app_settings()
    min_days = int(app_settings.get("bonus_min_days", BONUS_MIN_DAYS))
    prev_year = current_year - 1
    sessions  = read_all("sessions", filters={"employee_id": employee_id})
    total = sum(
        1.0 if s.get("duty_status") == "full" else
        0.5 if s.get("duty_status") == "half" else 0.0
        for s in sessions
        if _session_year(s) == prev_year
    )
    return total >= min_days


def _session_year(s):
    try:
        return datetime.strptime(s["date"], "%Y-%m-%d").year
    except Exception:
        return 0


def calculate_bonus(base_salary, absent_days, working_days=WORKING_DAYS):
    """
    Bonus = 1 month salary with ONLY absent-day cuts.
    Half-days, OT, advance are NOT involved.
    """
    daily_rate = base_salary / working_days
    return round(max(base_salary - absent_days * daily_rate, 0), 2)


# ─── Main salary calculation ─────────────────────────────────────────────────────
def calculate_salary(employee, month_sessions, month, year, working_days=None):
    if working_days is None:
        working_days = int(get_app_settings().get("working_days", WORKING_DAYS))

    base_salary = float(employee.get("salary", 0))
    advance     = float(employee.get("advance", 0))
    religion    = employee.get("religion", "Other")

    full_days = half_days = ot_full = ot_half = 0.0
    sessions_map = {}
    for s in month_sessions:
        sessions_map[s.get("date", "")] = s
        st = s.get("duty_status", "absent")
        if st == "full":   full_days += 1
        elif st == "half": half_days += 1
        ot = s.get("ot_status", "none")
        if ot == "full":   ot_full += 1
        elif ot == "half": ot_half += 1

    paid_sundays = _count_paid_sundays(employee["employee_id"], month, year, sessions_map)
    absent_days  = max(0, working_days - full_days - half_days * 0.5)

    att_ratio   = (full_days + half_days * 0.5 + paid_sundays) / working_days
    att_salary  = round(base_salary * att_ratio, 2)

    ot_units   = ot_full + ot_half * 0.5
    daily_rate = base_salary / working_days
    ot_rate    = float(get_app_settings().get("ot_multiplier", OT_MULTIPLIER))
    ot_pay     = round(ot_units * daily_rate * ot_rate, 2)

    # Religion-based bonus check
    annual_bonus   = 0.0
    bonus_eligible = False
    if is_bonus_month_for_religion(religion, month, year):
        bonus_eligible = is_bonus_eligible(employee["employee_id"], year)
        if bonus_eligible:
            annual_bonus = calculate_bonus(base_salary, absent_days, working_days)

    final_salary = round(att_salary + ot_pay + annual_bonus - advance, 2)

    return {
        "employee_id":       employee["employee_id"],
        "name":              employee["name"],
        "religion":          religion,
        "base_salary":       base_salary,
        "full_days":         full_days,
        "half_days":         half_days,
        "absent_days":       round(absent_days, 2),
        "paid_holidays":     paid_sundays,
        "ot_full_days":      ot_full,
        "ot_half_days":      ot_half,
        "ot_day_units":      ot_units,
        "ot_pay":            ot_pay,
        "attendance_salary": att_salary,
        "annual_bonus":      annual_bonus,       # amount (admin/HR/CA only)
        "bonus_paid":        annual_bonus > 0,   # boolean for employee app
        "bonus_eligible":    bonus_eligible,
        "advance":           advance,
        "final_salary":      final_salary,
        "payment_mode":      employee.get("payment_mode", "CASH"),
        "month":             month,
        "year":              year,
    }


def _count_paid_sundays(employee_id, month, year, sessions_map):
    paid = 0.0
    cal  = calendar.monthcalendar(year, month)
    for week_idx, week in enumerate(cal):
        if week[6] == 0:
            continue
        sun_d = date(year, month, week[6])
        sat_n = week[5]
        sat_d = date(year, month, sat_n) if sat_n != 0 else None

        # Monday of next week (may be next month)
        mon_d = None
        if week_idx + 1 < len(cal) and cal[week_idx + 1][0] != 0:
            mon_d = date(year, month, cal[week_idx + 1][0])

        sat_ok = sat_d and sessions_map.get(
            sat_d.isoformat(), {}).get("duty_status") in ("full", "half")
        mon_ok = mon_d and sessions_map.get(
            mon_d.isoformat(), {}).get("duty_status") in ("full", "half")

        if sat_ok and mon_ok:
            paid += 1.0
        elif sat_ok and not mon_ok:
            paid += 0.5
    return paid


# ─── Advance Panel ──────────────────────────────────────────────────────────
class AdvancePanel(tk.Toplevel):
    def __init__(self, parent, employee):
        super().__init__(parent)
        self.employee = employee
        self.title(f"Advance Payment — {employee['name']} ({employee['employee_id']})")
        self.geometry("420x320")
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        emp = self.employee
        current = float(emp.get("advance", 0))
        frm = tk.Frame(self, padx=20, pady=20)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="💵 Advance Payment",
                 font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(frm, text=f"Employee: {emp['name']}  ({emp['employee_id']})",
                 font=("Helvetica", 10)).pack(anchor="w")
        tk.Label(frm, text=f"Outstanding Advance: Rs. {current:,.2f}",
                 fg="#c0392b", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=4)

        tk.Frame(frm, height=1, bg="#bdc3c7").pack(fill="x", pady=8)

        amt_row = tk.Frame(frm)
        amt_row.pack(fill="x", pady=3)
        tk.Label(amt_row, text="New Advance (Rs.):", width=22, anchor="w").pack(side="left")
        self.amt_var = tk.StringVar()
        tk.Entry(amt_row, textvariable=self.amt_var, width=12).pack(side="left")

        note_row = tk.Frame(frm)
        note_row.pack(fill="x", pady=3)
        tk.Label(note_row, text="Note (optional):", width=22, anchor="w").pack(side="left")
        self.note_var = tk.StringVar()
        tk.Entry(note_row, textvariable=self.note_var, width=24).pack(side="left")

        tk.Label(frm,
                 text="⚠️ Added to outstanding. Full balance deducted from next salary.",
                 fg="#e67e22", font=("Helvetica", 8)
                 ).pack(anchor="w", pady=(6, 0))

        btn_row = tk.Frame(frm)
        btn_row.pack(fill="x", pady=10)
        tk.Button(btn_row, text="✔ Save", command=self._save,
                  bg="#27ae60", fg="white", padx=12).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Clear Outstanding", command=self._clear,
                  bg="#e74c3c", fg="white", padx=12).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=self.destroy, padx=12).pack(side="left")

    def _save(self):
        try:
            amt = float(self.amt_var.get().strip())
            if amt < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid amount.", parent=self)
            return
        emp_id  = self.employee["employee_id"]
        current = float(self.employee.get("advance", 0))
        total   = round(current + amt, 2)
        update("employees", emp_id, {"advance": total})
        write("advance_logs", None, {
            "employee_id": emp_id, "amount": amt,
            "total_outstanding": total,
            "note": self.note_var.get().strip() or "-",
            "date": date.today().isoformat(),
        })
        messagebox.showinfo("Saved",
            f"Advance Rs. {amt:,.2f} recorded.\nTotal outstanding: Rs. {total:,.2f}",
            parent=self)
        self.destroy()

    def _clear(self):
        if not messagebox.askyesno("Clear",
                f"Mark advance for {self.employee['name']} as fully repaid?", parent=self):
            return
        emp_id = self.employee["employee_id"]
        update("employees", emp_id, {"advance": 0})
        write("advance_logs", None, {
            "employee_id": emp_id, "amount": 0,
            "total_outstanding": 0,
            "note": "Cleared / fully repaid",
            "date": date.today().isoformat(),
        })
        messagebox.showinfo("Done", "Outstanding advance cleared.", parent=self)
        self.destroy()


# ─── Salary Panel (main tab) ──────────────────────────────────────────────────────
class SalaryPanel(tk.Frame):
    def __init__(self, parent, role="admin"):
        super().__init__(parent)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💰 Salary Management",
                 font=("Helvetica", 14, "bold")).pack(side="left", padx=12)

        bar = tk.Frame(self)
        bar.pack(fill="x", padx=12, pady=4)
        tk.Button(bar, text="⚡ Generate All",
                  command=self._generate_all,
                  bg="#2980b9", fg="white", padx=10).pack(side="left", padx=4)
        tk.Button(bar, text="💵 Advance Payment",
                  command=self._open_advance,
                  bg="#e67e22", fg="white", padx=10).pack(side="left", padx=4)
        if self.role in ("super_admin", "admin", "ca"):
            tk.Button(bar, text="📈 Salary Raise",
                      command=self._salary_raise,
                      bg="#27ae60", fg="white", padx=10).pack(side="left", padx=4)

        sel = tk.Frame(self)
        sel.pack(fill="x", padx=12, pady=4)
        tk.Label(sel, text="Month:").pack(side="left")
        self.month_var = tk.StringVar(value=str(datetime.now().month))
        ttk.Combobox(sel, textvariable=self.month_var, width=4,
                     values=[str(i) for i in range(1, 13)]).pack(side="left", padx=4)
        tk.Label(sel, text="Year:").pack(side="left")
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        tk.Entry(sel, textvariable=self.year_var, width=6).pack(side="left", padx=4)

        cols = ("id", "name", "religion", "base", "advance", "bonus", "final", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        for col, w, label in [
            ("id", 90, "Emp ID"), ("name", 160, "Name"),
            ("religion", 80, "Religion"), ("base", 90, "Base Salary"),
            ("advance", 80, "Advance"), ("bonus", 100, "Bonus Month"),
            ("final", 110, "Final Salary"), ("status", 80, "Status"),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=12, pady=8)
        self.tree.bind("<Double-1>", self._on_double)
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        employees = read_all("employees", filters={"status": "active"})
        self.employees = {e["employee_id"]: e for e in employees}
        bonus_config = read("settings", "bonus_dates") or {}
        for e in employees:
            rel = e.get("religion", "Other").lower()
            conf = bonus_config.get(rel, {})
            bonus_month = conf.get("month", "—") if conf.get("enabled") else "—"
            self.tree.insert("", "end", values=(
                e["employee_id"],
                e["name"],
                e.get("religion", "Other"),
                f"Rs. {float(e.get('salary', 0)):,.0f}",
                f"Rs. {float(e.get('advance', 0)):,.0f}",
                bonus_month,
                "—",
                "Pending",
            ))

    def _selected_employee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an employee first.")
            return None
        return self.employees.get(self.tree.item(sel[0])["values"][0])

    def _open_advance(self):
        emp = self._selected_employee()
        if emp:
            AdvancePanel(self, emp)

    def _on_double(self, _e):
        emp = self._selected_employee()
        if emp:
            AdvancePanel(self, emp)

    def _generate_all(self):
        try:
            month = int(self.month_var.get())
            year  = int(self.year_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid month/year.")
            return
        if not messagebox.askyesno("Confirm",
                f"Generate salaries for all employees for "
                f"{calendar.month_name[month]} {year}?"):
            return
        ok = fail = 0
        for emp in read_all("employees", filters={"status": "active"}):
            try:
                sessions = read_all("sessions", filters={
                    "employee_id": emp["employee_id"],
                    "month": month, "year": year
                })
                result   = calculate_salary(emp, sessions, month, year)
                slip_key = f"{emp['employee_id']}_{year}_{month:02d}"
                write("salary", slip_key, {
                    **result,
                    "generated_at": datetime.now().isoformat(),
                })
                if result["advance"] > 0:
                    update("employees", emp["employee_id"], {"advance": 0})
                ok += 1
            except Exception as ex:
                print(f"[SalaryPanel] {emp.get('employee_id')}: {ex}")
                fail += 1
        messagebox.showinfo("Done",
            f"Salary generation complete.\n✅ {ok} success  ❌ {fail} failed")
        self._load()

    def _salary_raise(self):
        emp = self._selected_employee()
        if not emp:
            return
        dlg = tk.Toplevel(self)
        dlg.title(f"Salary Raise — {emp['name']}")
        dlg.geometry("320x160")
        dlg.resizable(False, False)
        dlg.grab_set()
        frm = tk.Frame(dlg, padx=20, pady=16)
        frm.pack(fill="both", expand=True)
        tk.Label(frm,
                 text=f"Current: Rs. {float(emp.get('salary', 0)):,.0f}",
                 font=("Helvetica", 11, "bold")
                 ).pack(anchor="w", pady=4)
        tk.Label(frm, text="New Salary (Rs.):").pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(frm, textvariable=var, width=14).pack(anchor="w", pady=4)

        def save():
            try:
                s = float(var.get().strip())
                if s <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount.", parent=dlg)
                return
            update("employees", emp["employee_id"], {"salary": s})
            messagebox.showinfo("Saved", f"Salary updated to Rs. {s:,.0f}.", parent=dlg)
            dlg.destroy()
            self._load()

        tk.Button(frm, text="✔ Save", command=save,
                  bg="#27ae60", fg="white", padx=12).pack(side="left", pady=8)
        tk.Button(frm, text="Cancel", command=dlg.destroy, padx=12).pack(side="left", padx=8)
