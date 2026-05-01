# salary.py — Salary Panel (Admin App)
# Handles: Generate All, Advance Payment, Bonus (March auto), Salary Raise

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from utils.db import read_all, write, update
from utils.pdf_generator import generate_salary_slip
import calendar


# ─── Constants ───────────────────────────────────────────────────────────────
OT_MULTIPLIER   = 1.5
WORKING_DAYS    = 26   # default; overridden by settings
BONUS_MIN_DAYS  = 240  # minimum days worked previous year for bonus eligibility


# ─── Bonus Calculation ───────────────────────────────────────────────────────
def calculate_bonus(base_salary, absent_days, working_days=WORKING_DAYS):
    """
    Annual Bonus (March only, if eligible).

    Rule:
        Bonus = 1 month salary  BUT  only absent days are deducted.
        Half-days, OT, advance, deductions are NOT included/excluded.

        Bonus = Base Salary - (Absent Days × Daily Rate)
        Daily Rate = Base Salary / Working Days

    This gives the employee a clean month salary with only
    absent-day cuts applied — nothing else.
    """
    daily_rate   = base_salary / working_days
    absent_cut   = absent_days * daily_rate
    bonus_amount = base_salary - absent_cut
    return round(max(bonus_amount, 0), 2)


def is_bonus_eligible(employee_id, current_year):
    """
    Check if employee worked >= BONUS_MIN_DAYS in previous calendar year.
    Reads from Firestore sessions collection.
    """
    prev_year = current_year - 1
    sessions  = read_all("sessions", filters={
        "employee_id": employee_id,
        "year": prev_year
    })
    total_days = sum(
        1.0 if s.get("duty_status") == "full" else
        0.5 if s.get("duty_status") == "half" else 0.0
        for s in sessions
    )
    return total_days >= BONUS_MIN_DAYS


# ─── Salary Calculation ───────────────────────────────────────────────────────
def calculate_salary(employee, month_sessions, month, year, working_days=WORKING_DAYS):
    """
    Full salary calculation for one employee for a given month.
    Returns a dict with all components.
    """
    base_salary = float(employee.get("salary", 0))
    advance     = float(employee.get("advance", 0))   # outstanding advance

    # Attendance counts
    full_days    = sum(1.0 for s in month_sessions if s.get("duty_status") == "full")
    half_days    = sum(1.0 for s in month_sessions if s.get("duty_status") == "half")
    absent_days  = working_days - full_days - (half_days * 0.5)
    paid_sundays = _count_paid_sundays(employee["employee_id"], month, year)

    attendance_ratio   = (full_days + half_days * 0.5 + paid_sundays) / working_days
    attendance_salary  = round(base_salary * attendance_ratio, 2)

    # OT (flat day units)
    ot_full  = sum(1.0 for s in month_sessions if s.get("ot_status") == "full")
    ot_half  = sum(1.0 for s in month_sessions if s.get("ot_status") == "half")
    ot_units = ot_full + ot_half * 0.5
    daily_rate = base_salary / working_days
    ot_pay     = round(ot_units * daily_rate * OT_MULTIPLIER, 2)

    # Annual bonus — March only
    annual_bonus = 0.0
    bonus_eligible = False
    if month == 3:   # March
        bonus_eligible = is_bonus_eligible(employee["employee_id"], year)
        if bonus_eligible:
            annual_bonus = calculate_bonus(base_salary, absent_days, working_days)

    final_salary = round(
        attendance_salary + ot_pay + annual_bonus - advance, 2
    )

    return {
        "employee_id":       employee["employee_id"],
        "name":              employee["name"],
        "base_salary":       base_salary,
        "full_days":         full_days,
        "half_days":         half_days,
        "absent_days":       round(absent_days, 2),
        "paid_holidays":     paid_sundays,
        "ot_full_days":      ot_full,
        "ot_half_days":      ot_half,
        "ot_day_units":      ot_units,
        "ot_pay":            ot_pay,
        "attendance_salary": attendance_salary,
        "annual_bonus":      annual_bonus,
        "bonus_eligible":    bonus_eligible,
        "advance":           advance,
        "final_salary":      final_salary,
        "payment_mode":      employee.get("payment_mode", "CASH"),
        "month":             month,
        "year":              year,
    }


def _count_paid_sundays(employee_id, month, year):
    """Count Sundays with pay based on Sat+Mon presence rule."""
    sessions_map = {}
    sessions = read_all("sessions", filters={"employee_id": employee_id})
    for s in sessions:
        try:
            d = datetime.strptime(s["date"], "%Y-%m-%d").date()
            if d.month == month and d.year == year:
                sessions_map[d] = s
        except Exception:
            pass

    paid = 0.0
    cal  = calendar.monthcalendar(year, month)
    for week in cal:
        sat_d = date(year, month, week[5]) if week[5] != 0 else None
        sun_d = date(year, month, week[6]) if week[6] != 0 else None
        mon_d = None
        # Monday of next week
        next_week_idx = cal.index(week) + 1
        if next_week_idx < len(cal) and cal[next_week_idx][0] != 0:
            mon_d = date(year, month, cal[next_week_idx][0])

        if sun_d is None:
            continue

        sat_present = sat_d and sessions_map.get(sat_d, {}).get("duty_status") in ("full", "half")
        mon_present = mon_d and sessions_map.get(mon_d, {}).get("duty_status") in ("full", "half")

        if sat_present and mon_present:
            paid += 1.0
        elif sat_present and not mon_present:   # Saturday only → half pay
            paid += 0.5
        # else: no Sunday pay

    return paid


# ─── Advance Payment Panel ────────────────────────────────────────────────────
class AdvancePanel(tk.Toplevel):
    """
    Dialog to record an advance payment given to an employee.
    Advance is stored in the employee record and deducted from next salary.
    """

    def __init__(self, parent, employee):
        super().__init__(parent)
        self.employee = employee
        self.title(f"Advance Payment — {employee['name']} ({employee['employee_id']})")        
        self.geometry("420x320")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        emp = self.employee
        current_advance = float(emp.get("advance", 0))

        frm = tk.Frame(self, padx=20, pady=20)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="💵 Advance Payment",
                 font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))

        # Info row
        info = tk.Frame(frm)
        info.pack(fill="x", pady=4)
        tk.Label(info, text="Employee:", width=18, anchor="w").pack(side="left")
        tk.Label(info, text=f"{emp['name']}  ({emp['employee_id']})",
                 font=("Helvetica", 10, "bold")).pack(side="left")

        tk.Frame(frm, height=1, bg="#cccccc").pack(fill="x", pady=8)

        # Current outstanding advance
        cur = tk.Frame(frm)
        cur.pack(fill="x", pady=2)
        tk.Label(cur, text="Outstanding Advance:", width=22, anchor="w").pack(side="left")
        tk.Label(cur, text=f"Rs. {current_advance:,.2f}",
                 fg="#c0392b", font=("Helvetica", 10, "bold")).pack(side="left")

        tk.Frame(frm, height=1, bg="#cccccc").pack(fill="x", pady=8)

        # New advance amount
        amt_row = tk.Frame(frm)
        amt_row.pack(fill="x", pady=4)
        tk.Label(amt_row, text="New Advance Amount (Rs.):",
                 width=24, anchor="w").pack(side="left")
        self.advance_var = tk.StringVar()
        tk.Entry(amt_row, textvariable=self.advance_var, width=12).pack(side="left")

        # Note
        note_row = tk.Frame(frm)
        note_row.pack(fill="x", pady=4)
        tk.Label(note_row, text="Note (optional):",
                 width=24, anchor="w").pack(side="left")
        self.note_var = tk.StringVar()
        tk.Entry(note_row, textvariable=self.note_var, width=24).pack(side="left")

        tk.Label(frm,
                 text="⚠️ New advance is ADDED to existing outstanding advance.\n"
                      "Full outstanding amount is deducted from next salary.",
                 fg="#e67e22", font=("Helvetica", 8), justify="left"
                 ).pack(anchor="w", pady=(8, 0))

        # Buttons
        btn_row = tk.Frame(frm)
        btn_row.pack(fill="x", pady=(12, 0))
        tk.Button(btn_row, text="✔ Save Advance",
                  command=self._save, bg="#27ae60", fg="white",
                  padx=12, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Clear Outstanding",
                  command=self._clear_advance, bg="#e74c3c", fg="white",
                  padx=12, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel",
                  command=self.destroy, padx=12, pady=4).pack(side="left")

    def _save(self):
        try:
            new_amt = float(self.advance_var.get().strip())
            if new_amt < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid positive advance amount.", parent=self)
            return

        emp_id = self.employee["employee_id"]
        current = float(self.employee.get("advance", 0))
        total   = round(current + new_amt, 2)
        note    = self.note_var.get().strip() or "-"

        # Update employee record
        update("employees", emp_id, {"advance": total})

        # Log the advance transaction
        write("advance_logs", None, {
            "employee_id":   emp_id,
            "amount":        new_amt,
            "total_outstanding": total,
            "note":          note,
            "date":          date.today().isoformat(),
            "recorded_by":   "admin",   # replace with logged-in user
        })

        messagebox.showinfo(
            "Saved",
            f"Advance of Rs. {new_amt:,.2f} recorded.\n"
            f"Total outstanding: Rs. {total:,.2f}\n"
            f"Will be deducted from {self.employee['name']}'s next salary.",
            parent=self
        )
        self.destroy()

    def _clear_advance(self):
        """Mark advance as fully repaid (set to 0)."""
        if not messagebox.askyesno(
            "Clear Advance",
            f"Mark all outstanding advance for {self.employee['name']} as repaid?\n"
            "This will set the outstanding balance to Rs. 0.",
            parent=self
        ):
            return
        emp_id = self.employee["employee_id"]
        update("employees", emp_id, {"advance": 0})
        write("advance_logs", None, {
            "employee_id": emp_id,
            "amount":      0,
            "total_outstanding": 0,
            "note":        "Advance cleared / fully repaid",
            "date":        date.today().isoformat(),
            "recorded_by": "admin",
        })
        messagebox.showinfo("Cleared", "Outstanding advance set to Rs. 0.", parent=self)
        self.destroy()


# ─── Salary Panel (main tab) ──────────────────────────────────────────────────
class SalaryPanel(tk.Frame):
    """
    Main Salary tab in the Admin App.
    Buttons: Generate All | Generate Single | Advance Payment | Salary Raise
    """

    def __init__(self, parent, role="admin"):
        super().__init__(parent)
        self.role = role
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💰 Salary Management",
                 font=("Helvetica", 15, "bold")).pack(side="left", padx=12)

        # Action buttons
        btn_bar = tk.Frame(self)
        btn_bar.pack(fill="x", padx=12, pady=4)

        tk.Button(btn_bar, text="⚡ Generate All Salaries",
                  command=self._generate_all,
                  bg="#2980b9", fg="white", padx=10, pady=5).pack(side="left", padx=4)

        tk.Button(btn_bar, text="💵 Advance Payment",
                  command=self._open_advance,
                  bg="#e67e22", fg="white", padx=10, pady=5).pack(side="left", padx=4)

        if self.role in ("super_admin", "admin", "ca"):
            tk.Button(btn_bar, text="📈 Salary Raise",
                      command=self._salary_raise,
                      bg="#27ae60", fg="white", padx=10, pady=5).pack(side="left", padx=4)

        # Month/Year selector
        sel = tk.Frame(self)
        sel.pack(fill="x", padx=12, pady=4)
        tk.Label(sel, text="Month:").pack(side="left")
        self.month_var = tk.StringVar(value=str(datetime.now().month))
        ttk.Combobox(sel, textvariable=self.month_var, width=4,
                     values=[str(i) for i in range(1, 13)]).pack(side="left", padx=4)
        tk.Label(sel, text="Year:").pack(side="left")
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        ttk.Entry(sel, textvariable=self.year_var, width=6).pack(side="left", padx=4)

        # Employee list
        self.tree = ttk.Treeview(self,
            columns=("id", "name", "base", "advance", "final", "status"),
            show="headings", height=18)
        for col, w, label in [
            ("id", 90, "Emp ID"),
            ("name", 180, "Name"),
            ("base", 100, "Base Salary"),
            ("advance", 100, "Advance"),
            ("final", 120, "Final Salary"),
            ("status", 100, "Status"),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=12, pady=8)
        self.tree.bind("<Double-1>", self._on_row_double_click)
        self._load_employees()

    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())
        employees = read_all("employees", filters={"status": "active"})
        self.employees = {e["employee_id"]: e for e in employees}
        for e in employees:
            self.tree.insert("", "end", values=(
                e["employee_id"],
                e["name"],
                f"Rs. {float(e.get('salary', 0)):,.0f}",
                f"Rs. {float(e.get('advance', 0)):,.0f}",
                "—",
                "Pending"
            ))

    def _selected_employee(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an employee first.")
            return None
        emp_id = self.tree.item(sel[0])["values"][0]
        return self.employees.get(emp_id)

    def _open_advance(self):
        emp = self._selected_employee()
        if emp:
            AdvancePanel(self, emp)

    def _on_row_double_click(self, event):
        emp = self._selected_employee()
        if emp:
            AdvancePanel(self, emp)

    def _generate_all(self):
        try:
            month = int(self.month_var.get())
            year  = int(self.year_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid month or year.")
            return

        confirm = messagebox.askyesno(
            "Generate Salaries",
            f"Generate salary slips for ALL employees for {calendar.month_name[month]} {year}?\n\n"
            f"{'(March — Annual bonus will be applied for eligible employees)' if month == 3 else ''}"
        )
        if not confirm:
            return

        employees = read_all("employees", filters={"status": "active"})
        success, failed = 0, 0
        for emp in employees:
            try:
                sessions = read_all("sessions", filters={
                    "employee_id": emp["employee_id"],
                    "month": month, "year": year
                })
                result = calculate_salary(emp, sessions, month, year)
                slip_key = f"{emp['employee_id']}_{year}_{month:02d}"

                from datetime import timedelta
                from dateutil.relativedelta import relativedelta
                expires = datetime.now() + relativedelta(months=12)

                write("salary", slip_key, {
                    **result,
                    "generated_at":   datetime.now().isoformat(),
                    "slip_expires_at": expires.isoformat(),
                })

                # After saving, clear advance from employee record
                if result["advance"] > 0:
                    update("employees", emp["employee_id"], {"advance": 0})

                success += 1
            except Exception as ex:
                print(f"[SalaryPanel] Error for {emp.get('employee_id')}: {ex}")
                failed += 1

        messagebox.showinfo(
            "Done",
            f"Salary generation complete.\n✅ Success: {success}\n❌ Failed: {failed}"
        )
        self._load_employees()

    def _salary_raise(self):
        emp = self._selected_employee()
        if not emp:
            return
        dlg = tk.Toplevel(self)
        dlg.title(f"Salary Raise — {emp['name']}")
        dlg.geometry("340x180")
        dlg.resizable(False, False)
        dlg.grab_set()

        frm = tk.Frame(dlg, padx=20, pady=20)
        frm.pack(fill="both", expand=True)
        tk.Label(frm, text=f"Current Salary: Rs. {float(emp.get('salary', 0)):,.0f}",
                 font=("Helvetica", 11, "bold")).pack(anchor="w", pady=4)
        tk.Label(frm, text="New Salary (Rs.):").pack(anchor="w")
        new_sal_var = tk.StringVar()
        tk.Entry(frm, textvariable=new_sal_var, width=16).pack(anchor="w", pady=4)

        def save_raise():
            try:
                new_sal = float(new_sal_var.get().strip())
                if new_sal <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter a valid salary.", parent=dlg)
                return
            update("employees", emp["employee_id"], {"salary": new_sal})
            messagebox.showinfo("Saved", f"Salary updated to Rs. {new_sal:,.0f}.", parent=dlg)
            dlg.destroy()
            self._load_employees()

        btn_row = tk.Frame(frm)
        btn_row.pack(fill="x", pady=8)
        tk.Button(btn_row, text="✔ Save", command=save_raise,
                  bg="#27ae60", fg="white", padx=12).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=dlg.destroy, padx=12).pack(side="left")
