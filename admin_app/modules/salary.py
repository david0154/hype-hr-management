# salary.py — Salary Panel + Bonus Logic (religion-based dates)
# Developed by David | Nexuzy Lab | nexuzylab@gmail.com
# https://github.com/david0154

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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


# ─── Working Days Helper ─────────────────────────────────────────────────────
def get_actual_working_days(year: int, month: int) -> int:
    """Returns working days = all days in month minus Sundays."""
    cal = calendar.monthcalendar(year, month)
    return sum(1 for week in cal for day_idx, d in enumerate(week)
               if d != 0 and day_idx != 6)


# ─── Bonus Helpers ───────────────────────────────────────────────────────────
def get_bonus_config():
    return read("settings", "bonus_dates") or {}


def get_app_settings():
    return read("settings", "app") or {}


def is_bonus_month_for_religion(religion: str, month: int, year: int) -> bool:
    bonus_config = get_bonus_config()
    key  = (religion or "other").lower()
    conf = bonus_config.get(key, bonus_config.get("other", {}))
    if not conf or not conf.get("enabled", False):
        return False
    bonus_month = MONTH_MAP.get(conf.get("month", "March"), 3)
    return month == bonus_month


def is_bonus_eligible(employee_id: str, current_year: int) -> bool:
    """Employee must have worked >= BONUS_MIN_DAYS in the previous year."""
    app_settings = get_app_settings()
    min_days  = int(app_settings.get("bonus_min_days", BONUS_MIN_DAYS))
    prev_year = current_year - 1
    sessions  = read_all("sessions", "employee_id", employee_id)
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
    daily_rate = base_salary / working_days if working_days else 0
    return round(max(base_salary - absent_days * daily_rate, 0), 2)


# ─── Main Salary Calculation ─────────────────────────────────────────────────
def calculate_salary(employee, month_sessions, month, year, working_days=None):
    """
    Core calculation — used by both overview panel and month-end bulk generator.
    FIX: working_days now defaults to actual calendar working days (excl. Sundays)
    instead of the old hardcoded 26.
    """
    if working_days is None:
        # Prefer setting from app config; fall back to actual calendar days
        cfg_days = int(get_app_settings().get("working_days", 0))
        working_days = cfg_days if cfg_days > 0 else get_actual_working_days(year, month)

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

    att_ratio  = (full_days + half_days * 0.5 + paid_sundays) / working_days if working_days else 0
    att_salary = round(base_salary * att_ratio, 2)

    ot_units   = ot_full + ot_half * 0.5
    daily_rate = base_salary / working_days if working_days else 0
    ot_rate    = float(get_app_settings().get("ot_multiplier", OT_MULTIPLIER))
    # FIX: OT pay = (daily_rate / 8h) * ot_hours * multiplier  — consistent with Android side
    ot_hours   = ot_full * 7.0 + ot_half * 4.0   # default hours if duty_hours not stored
    ot_pay     = round((daily_rate / 8.0) * ot_hours * ot_rate, 2) if daily_rate else 0.0

    annual_bonus   = 0.0
    bonus_eligible = False
    if is_bonus_month_for_religion(religion, month, year):
        bonus_eligible = is_bonus_eligible(employee["employee_id"], year)
        if bonus_eligible:
            annual_bonus = calculate_bonus(base_salary, absent_days, working_days)

    # FIX: partial advance deduction — only deduct up to gross (avoid negative net)
    gross        = att_salary + ot_pay + annual_bonus
    deduct_adv   = min(advance, gross)            # never go below 0
    final_salary = round(gross - deduct_adv, 2)

    return {
        "employee_id":       employee["employee_id"],
        "name":              employee["name"],
        "designation":       employee.get("designation", ""),
        "department":        employee.get("department", ""),
        "religion":          religion,
        "base_salary":       base_salary,
        "working_days_used": working_days,
        "full_days":         full_days,
        "half_days":         half_days,
        "absent_days":       round(absent_days, 2),
        "paid_holidays":     paid_sundays,
        "ot_full_days":      ot_full,
        "ot_half_days":      ot_half,
        "ot_day_units":      ot_units,
        "ot_pay":            ot_pay,
        "attendance_salary": att_salary,
        "annual_bonus":      annual_bonus,
        "bonus_paid":        annual_bonus > 0,
        "bonus_eligible":    bonus_eligible,
        "advance":           advance,
        "advance_deducted":  deduct_adv,
        "final_salary":      final_salary,
        "payment_mode":      employee.get("payment_mode", "CASH"),
        "month":             month,
        "year":              year,
    }


def _count_paid_sundays(employee_id, month, year, sessions_map):
    """Sunday is paid only if Saturday present AND next Monday present (full pay)
    or Saturday present but Monday absent (half pay)."""
    paid = 0.0
    cal  = calendar.monthcalendar(year, month)
    for week_idx, week in enumerate(cal):
        if week[6] == 0:          # no Sunday this row
            continue
        sat_n = week[5]
        sat_d = date(year, month, sat_n) if sat_n != 0 else None
        mon_d = None
        if week_idx + 1 < len(cal) and cal[week_idx + 1][0] != 0:
            mon_d = date(year, month, cal[week_idx + 1][0])
        sat_ok = sat_d and sessions_map.get(
            sat_d.isoformat(), {}).get("duty_status") in ("full", "half")
        mon_ok = mon_d and sessions_map.get(
            mon_d.isoformat(), {}).get("duty_status") in ("full", "half")
        if sat_ok and mon_ok:       paid += 1.0
        elif sat_ok and not mon_ok: paid += 0.5
    return paid


# ─── Salary Detail Popup ─────────────────────────────────────────────────────
class SalaryDetailPopup(tk.Toplevel):
    """Click any row in the overview tree → shows full breakdown."""
    def __init__(self, parent, result: dict):
        super().__init__(parent)
        self.title(f"Salary Detail — {result['name']} ({result['employee_id']})")
        self.geometry("480x540")
        self.resizable(False, False)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build(result)

    def _build(self, r):
        frm = tk.Frame(self, bg="#0d1b2a", padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text=f"💰 {r['name']}  [{r['employee_id']}]",
                 font=("Helvetica", 13, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", pady=(0, 4))
        tk.Label(frm, text=f"{r.get('designation','')}  |  {r.get('department','')}",
                 bg="#0d1b2a", fg="#aaa", font=("Helvetica", 9)).pack(anchor="w", pady=(0, 8))

        sep = lambda: tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)

        def row(label, val, fg="#ccc"):
            r_frm = tk.Frame(frm, bg="#0d1b2a"); r_frm.pack(fill="x", pady=1)
            tk.Label(r_frm, text=label, width=26, anchor="w",
                     bg="#0d1b2a", fg="#aaa", font=("Helvetica", 9)).pack(side="left")
            tk.Label(r_frm, text=str(val), anchor="e",
                     bg="#0d1b2a", fg=fg, font=("Helvetica", 9, "bold")).pack(side="right")

        tk.Label(frm, text="📅 ATTENDANCE", font=("Helvetica", 10, "bold"),
                 bg="#0d1b2a", fg="#5dade2").pack(anchor="w")
        row("Working Days Used",  r["working_days_used"])
        row("Full Days",          int(r["full_days"]))
        row("Half Days",          int(r["half_days"]))
        row("Absent Days",        r["absent_days"])
        row("Paid Sundays",       r["paid_holidays"])
        row("OT Full Days",       int(r["ot_full_days"]))
        row("OT Half Days",       int(r["ot_half_days"]))
        sep()

        tk.Label(frm, text="💵 EARNINGS", font=("Helvetica", 10, "bold"),
                 bg="#0d1b2a", fg="#2ecc71").pack(anchor="w")
        row("Base Salary",        f"Rs. {r['base_salary']:,.2f}")
        row("Attendance Earned",  f"Rs. {r['attendance_salary']:,.2f}", fg="#2ecc71")
        row("OT Pay",             f"Rs. {r['ot_pay']:,.2f}",           fg="#2ecc71")
        row("Annual Bonus",       f"Rs. {r['annual_bonus']:,.2f}  ({'Yes' if r['bonus_paid'] else 'No'})",
            fg="#f1c40f" if r["bonus_paid"] else "#ccc")
        sep()

        tk.Label(frm, text="➖ DEDUCTIONS", font=("Helvetica", 10, "bold"),
                 bg="#0d1b2a", fg="#e74c3c").pack(anchor="w")
        row("Advance Deducted",   f"Rs. {r['advance_deducted']:,.2f}", fg="#e74c3c")
        sep()

        row("✔ NET PAY",           f"Rs. {r['final_salary']:,.2f}",    fg="#27ae60")
        row("Payment Mode",      r["payment_mode"])

        tk.Button(frm, text="Close", command=self.destroy,
                  padx=12, relief="flat", bg="#2c3e50", fg="white").pack(anchor="e", pady=(12, 0))


# ─── Advance Panel ────────────────────────────────────────────────────────────
class AdvancePanel(tk.Toplevel):
    def __init__(self, parent, employee):
        super().__init__(parent)
        self.employee = employee
        self.title(f"Advance Payment — {employee['name']} ({employee['employee_id']})")
        self.geometry("420x340")
        self.resizable(False, False)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        emp     = self.employee
        current = float(emp.get("advance", 0))
        frm = tk.Frame(self, padx=20, pady=20, bg="#0d1b2a")
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="💵 Advance Payment",
                 font=("Helvetica", 13, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", pady=(0, 8))
        tk.Label(frm, text=f"Employee: {emp['name']}  ({emp['employee_id']})",
                 bg="#0d1b2a", fg="#ccc", font=("Helvetica", 10)).pack(anchor="w")
        tk.Label(frm, text=f"Outstanding Advance: Rs. {current:,.2f}",
                 fg="#e74c3c", bg="#0d1b2a", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=4)
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)

        for label, attr in [("New Advance (Rs.):", "amt_var"), ("Note (optional):", "note_var")]:
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=3)
            tk.Label(row, text=label, width=22, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar()
            tk.Entry(row, textvariable=var, width=20,
                     bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left")
            setattr(self, attr, var)

        tk.Label(frm,
                 text="⚠️ Added to outstanding. Full balance deducted from next salary.\n"
                      "   If salary < advance, only salary amount is deducted (no negative net).",
                 fg="#e67e22", bg="#0d1b2a", font=("Helvetica", 8),
                 justify="left").pack(anchor="w", pady=(6, 0))

        btn_row = tk.Frame(frm, bg="#0d1b2a"); btn_row.pack(fill="x", pady=10)
        tk.Button(btn_row, text="✔ Save", command=self._save,
                  bg="#27ae60", fg="white", padx=12, relief="flat").pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Clear Outstanding", command=self._clear,
                  bg="#e74c3c", fg="white", padx=12, relief="flat").pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Cancel", command=self.destroy,
                  padx=12, relief="flat").pack(side="left")

    def _save(self):
        try:
            amt = float(self.amt_var.get().strip())
            if amt < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid positive amount.", parent=self); return
        emp_id  = self.employee["employee_id"]
        current = float(self.employee.get("advance", 0))
        total   = round(current + amt, 2)
        update("employees", emp_id, {"advance": total})
        write("advance_logs", f"{emp_id}_{date.today().isoformat()}_{int(amt)}", {
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
        write("advance_logs", f"{emp_id}_cleared_{date.today().isoformat()}", {
            "employee_id": emp_id, "amount": 0,
            "total_outstanding": 0,
            "note": "Cleared / fully repaid",
            "date": date.today().isoformat(),
        })
        messagebox.showinfo("Done", "Outstanding advance cleared.", parent=self)
        self.destroy()


# ─── Salary Panel (main tab with sub-tabs) ───────────────────────────────────
class SalaryPanel(tk.Frame):
    def __init__(self, parent, role="admin"):
        super().__init__(parent, bg="#0d1b2a")
        self.role = role
        self._build_ui()

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        # Tab 1 — Monthly overview (per-employee live preview)
        tab1 = tk.Frame(nb, bg="#0d1b2a")
        nb.add(tab1, text="  💰 Monthly Overview  ")
        self._build_overview(tab1)

        # Tab 2 — Bulk month-end generation + PDF + export
        from modules.salary_monthend import MonthEndPanel
        tab2 = MonthEndPanel(nb, role=self.role)
        nb.add(tab2, text="  📅 Month-End Generate & Export  ")

    def _build_overview(self, parent):
        hdr = tk.Frame(parent, bg="#1a2740", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💰 Salary Management — Monthly Overview",
                 font=("Helvetica", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=12)

        bar = tk.Frame(parent, bg="#0d1b2a")
        bar.pack(fill="x", padx=12, pady=6)

        tk.Button(bar, text="🔍 Preview Selected",
                  command=self._preview_salary,
                  bg="#2980b9", fg="white", padx=10, relief="flat").pack(side="left", padx=4)
        tk.Button(bar, text="💵 Advance Payment",
                  command=self._open_advance,
                  bg="#e67e22", fg="white", padx=10, relief="flat").pack(side="left", padx=4)
        if self.role in ("super_admin", "admin", "ca"):
            tk.Button(bar, text="📈 Salary Raise",
                      command=self._salary_raise,
                      bg="#27ae60", fg="white", padx=10, relief="flat").pack(side="left", padx=4)
        tk.Button(bar, text="📄 Export CSV",
                  command=self._export_csv,
                  bg="#8e44ad", fg="white", padx=10, relief="flat").pack(side="left", padx=4)
        tk.Button(bar, text="🔄 Refresh",
                  command=self._load,
                  bg="#555", fg="white", padx=10, relief="flat").pack(side="left", padx=4)

        sel = tk.Frame(parent, bg="#0d1b2a")
        sel.pack(fill="x", padx=12, pady=4)
        tk.Label(sel, text="Month:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.month_var = tk.StringVar(value=str(datetime.now().month))
        ttk.Combobox(sel, textvariable=self.month_var, width=4,
                     values=[str(i) for i in range(1, 13)]).pack(side="left", padx=4)
        tk.Label(sel, text="Year:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        tk.Entry(sel, textvariable=self.year_var, width=6,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(side="left", padx=4)
        tk.Button(sel, text="Load", command=self._load_with_calc,
                  bg="#2980b9", fg="white", padx=8, relief="flat").pack(side="left", padx=6)

        cols = ("id", "name", "religion", "base", "present", "ot", "advance", "bonus_m", "final", "status")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", height=16)
        for col, w, label in [
            ("id",       90,  "Emp ID"),
            ("name",    155, "Name"),
            ("religion", 70, "Religion"),
            ("base",     90, "Base"),
            ("present",  65, "Present"),
            ("ot",       55, "OT Days"),
            ("advance",  80, "Advance"),
            ("bonus_m", 100, "Bonus Month"),
            ("final",   110, "Net Pay"),
            ("status",   70, "Status"),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w)

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 4))
        self.tree.pack(fill="both", expand=True, padx=(12, 0), pady=8)
        self.tree.bind("<Double-1>", self._on_double)
        self._load()

    # ── Load (base data only, fast) ──────────────────────────────────────────
    def _load(self):
        self.tree.delete(*self.tree.get_children())
        employees = read_all("employees", "status", "active")
        self.employees = {e["employee_id"]: e for e in employees}
        self._calc_cache = {}     # clear previous preview cache
        bonus_config = read("settings", "bonus_dates") or {}
        for e in employees:
            rel  = e.get("religion", "Other").lower()
            conf = bonus_config.get(rel, {})
            bonus_month = conf.get("month", "—") if conf.get("enabled") else "—"
            self.tree.insert("", "end", iid=e["employee_id"], values=(
                e["employee_id"],
                e["name"],
                e.get("religion", "Other"),
                f"Rs. {float(e.get('salary', 0)):,.0f}",
                "—", "—",
                f"Rs. {float(e.get('advance', 0)):,.0f}",
                bonus_month,
                "—",
                "Pending",
            ))

    # ── Load + calculate all (slower, fires on "Load" button) ────────────────
    def _load_with_calc(self):
        try:
            month = int(self.month_var.get())
            year  = int(self.year_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid month/year."); return

        self._load()    # reset rows first
        self._calc_cache = {}
        month_str = f"{year}-{month:02d}"

        for emp_id, emp in self.employees.items():
            try:
                all_sess = read_all("sessions", "employee_id", emp_id)
                sessions = [s for s in all_sess if s.get("date", "").startswith(month_str)]
                result   = calculate_salary(emp, sessions, month, year)
                self._calc_cache[emp_id] = result
                self.tree.item(emp_id, values=(
                    emp_id,
                    emp["name"],
                    emp.get("religion", "Other"),
                    f"Rs. {result['base_salary']:,.0f}",
                    f"{int(result['full_days'])}F / {int(result['half_days'])}H",
                    f"{int(result['ot_full_days'])}F / {int(result['ot_half_days'])}H",
                    f"Rs. {result['advance']:,.0f}",
                    "✔ Bonus" if result["bonus_paid"] else "—",
                    f"Rs. {result['final_salary']:,.0f}",
                    "Calculated",
                ))
            except Exception as ex:
                print(f"[SalaryPanel.load_calc] {emp_id}: {ex}")

    # ── Double-click → detail popup ─────────────────────────────────────────
    def _on_double(self, _e):
        emp = self._selected_employee()
        if not emp: return
        result = self._calc_cache.get(emp["employee_id"])
        if result:
            SalaryDetailPopup(self, result)
        else:
            # Not yet calculated — open advance panel instead
            AdvancePanel(self, emp)

    # ── Preview salary for selected row ─────────────────────────────────────
    def _preview_salary(self):
        emp = self._selected_employee()
        if not emp: return
        try:
            month = int(self.month_var.get())
            year  = int(self.year_var.get())
        except ValueError:
            messagebox.showerror("Error", "Set valid month/year first."); return
        month_str = f"{year}-{month:02d}"
        all_sess  = read_all("sessions", "employee_id", emp["employee_id"])
        sessions  = [s for s in all_sess if s.get("date", "").startswith(month_str)]
        result    = calculate_salary(emp, sessions, month, year)
        self._calc_cache = getattr(self, "_calc_cache", {})
        self._calc_cache[emp["employee_id"]] = result
        SalaryDetailPopup(self, result)

    # ── Export visible results to CSV ────────────────────────────────────────
    def _export_csv(self):
        if not getattr(self, "_calc_cache", {}):
            messagebox.showwarning("No Data",
                "Press Load first to calculate salaries."); return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Save Salary Report")
        if not path: return
        import csv
        fields = ["employee_id", "name", "designation", "department", "religion",
                  "base_salary", "working_days_used", "full_days", "half_days",
                  "absent_days", "paid_holidays", "ot_full_days", "ot_half_days",
                  "ot_pay", "attendance_salary", "annual_bonus", "advance",
                  "advance_deducted", "final_salary", "payment_mode", "month", "year"]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(self._calc_cache.values())
            messagebox.showinfo("✅ Exported", f"Saved to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Export Failed", str(ex))

    def _selected_employee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an employee first.")
            return None
        return self.employees.get(self.tree.item(sel[0])["values"][0])

    def _open_advance(self):
        emp = self._selected_employee()
        if emp: AdvancePanel(self, emp)

    # ── Salary Raise dialog ──────────────────────────────────────────────────
    def _salary_raise(self):
        emp = self._selected_employee()
        if not emp: return
        dlg = tk.Toplevel(self)
        dlg.title(f"Salary Raise — {emp['name']}")
        dlg.geometry("320x200")
        dlg.resizable(False, False)
        dlg.configure(bg="#0d1b2a")
        dlg.grab_set()
        frm = tk.Frame(dlg, padx=20, pady=16, bg="#0d1b2a")
        frm.pack(fill="both", expand=True)
        tk.Label(frm,
                 text=f"{emp['name']} ({emp['employee_id']})",
                 font=("Helvetica", 10), bg="#0d1b2a", fg="#aaa").pack(anchor="w")
        tk.Label(frm, text=f"Current: Rs. {float(emp.get('salary', 0)):,.0f}",
                 font=("Helvetica", 11, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", pady=4)
        tk.Label(frm, text="New Salary (Rs.):",
                 bg="#0d1b2a", fg="#ccc").pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(frm, textvariable=var, width=14,
                 bg="#1e3a5f", fg="white", insertbackground="white").pack(anchor="w", pady=4)

        def save():
            try:
                s = float(var.get().strip())
                if s <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount.", parent=dlg); return
            update("employees", emp["employee_id"], {"salary": s})
            messagebox.showinfo("Saved", f"Salary updated to Rs. {s:,.0f}.", parent=dlg)
            dlg.destroy()
            self._load()

        btn = tk.Frame(frm, bg="#0d1b2a"); btn.pack(fill="x", pady=8)
        tk.Button(btn, text="✔ Save", command=save,
                  bg="#27ae60", fg="white", padx=12, relief="flat").pack(side="left", padx=(0, 8))
        tk.Button(btn, text="Cancel", command=dlg.destroy,
                  padx=12, relief="flat").pack(side="left")
