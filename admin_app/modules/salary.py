"""
Salary Module — Hype HR Management
Bonus: Yearly only (based on total annual present days incl paid holidays)
Salary Raise: CA can increase per-employee salary
Role permissions: Admin=all, HR=view+bonus, CA=bonus+raise, Manager=view
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date
import os, tempfile
from utils.firebase_config import get_db, get_bucket
from utils.pdf_generator import generate_salary_slip
from modules.attendance import calculate_monthly_summary
from modules.roles import has_permission

MONTH_NAMES = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

# ── Bonus is yearly, based on total annual present days (incl paid holidays) ──
# Bonus eligibility: >= MIN_DAYS_FOR_BONUS working days in the year
MIN_DAYS_FOR_BONUS  = 240   # ~10 months full attendance
BONUS_MONTH         = 3     # March (month number) — pay in March salary
# Bonus amount stored per employee in Firestore field: annual_bonus_amount
# Default fallback if not set: 0 (admin/HR/CA must configure per employee)


def calculate_annual_present(employee_id: str, year: int) -> float:
    """Sum all monthly present+half+paid_holidays for the year."""
    db = get_db()
    total = 0.0
    for m in range(1, 13):
        try:
            summary = calculate_monthly_summary(employee_id, year, m)
            total += summary.get("total_present", 0)
            total += summary.get("half_days", 0) * 0.5
            total += summary.get("paid_holidays", 0)
        except Exception:
            pass
    return total


def calculate_salary(employee: dict, summary: dict, ot_rate: float = 1.5,
                     manual_bonus: float = 0, advance: float = 0,
                     payment_mode: str = "CASH",
                     month: int = None, year: int = None) -> dict:
    base          = employee.get("salary", 0)
    total_working = summary.get("total_working_days", 26)
    present       = summary.get("total_present", 0)
    half_days     = summary.get("half_days", 0)
    paid_holidays = summary.get("paid_holidays", 0)

    paid_days        = present + (half_days * 0.5) + paid_holidays
    attendance_ratio = min(paid_days / total_working, 1.0) if total_working > 0 else 0
    attendance_salary = round(base * attendance_ratio, 2)

    # OT — flat day-rate (not hourly)
    ot_full_days = summary.get("ot_full_days", 0)
    ot_half_days = summary.get("ot_half_days", 0)
    ot_day_units = ot_full_days + (ot_half_days * 0.5)
    daily_rate   = base / total_working if total_working else 0
    ot_pay       = round(ot_day_units * daily_rate * ot_rate, 2)

    # Bonus — yearly, paid in BONUS_MONTH only
    bonus = 0.0
    if month is not None and year is not None and month == BONUS_MONTH:
        annual_days  = calculate_annual_present(employee.get("employee_id", ""), year - 1)
        if annual_days >= MIN_DAYS_FOR_BONUS:
            stored_bonus = float(employee.get("annual_bonus_amount", 0))
            bonus        = manual_bonus if manual_bonus > 0 else stored_bonus

    final_salary = round(attendance_salary + ot_pay + bonus - advance, 2)

    return {
        "base_salary":        base,
        "attendance_salary":  attendance_salary,
        "ot_pay":             ot_pay,
        "ot_full_days":       ot_full_days,
        "ot_half_days":       ot_half_days,
        "ot_day_units":       ot_day_units,
        "bonus":              bonus,
        "advance":            advance,
        "final_salary":       final_salary,
        "payment_mode":       payment_mode,
        "total_working_days": total_working,
        "total_present":      present,
        "half_days":          half_days,
        "absent_days":        summary.get("absent_days", 0),
        "paid_holidays":      paid_holidays,
        "annual_days_used":   0,  # filled during bonus month
    }


class SalaryModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.role = current_user.get("role", "ca")
        self.db = get_db()
        self._build_ui()
        self._load_salary_records()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="💰 Salary Management",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

        if has_permission(self.role, "salary"):
            tk.Button(top, text="⚙ Generate This Month", bg="#f77f00", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._generate_all).pack(side="right", padx=5)

        # CA and HR and Admin can pay / mark bonus
        if self.role in ("admin", "super_admin", "hr", "ca"):
            tk.Button(top, text="🎁 Pay Bonus", bg="#27ae60", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._open_bonus_panel).pack(side="right", padx=5)

        # CA (and admin) can increase salary
        if self.role in ("admin", "super_admin", "ca"):
            tk.Button(top, text="📈 Salary Raise", bg="#8e44ad", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._open_raise_panel).pack(side="right", padx=5)

        sel = tk.Frame(self.parent, bg="#0d1b2a")
        sel.pack(fill="x", padx=10, pady=5)
        now = datetime.now()
        tk.Label(sel, text="Month:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.month_var = tk.IntVar(value=now.month)
        ttk.Spinbox(sel, from_=1, to=12, textvariable=self.month_var, width=4).pack(side="left", padx=5)
        tk.Label(sel, text="Year:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.year_var = tk.IntVar(value=now.year)
        ttk.Spinbox(sel, from_=2024, to=2030, textvariable=self.year_var, width=6).pack(side="left", padx=5)
        tk.Button(sel, text="Load", bg="#1e6f9f", fg="white", relief="flat",
                  command=self._load_salary_records).pack(side="left", padx=5)

        cols = ("Employee ID", "Name", "Month", "Base", "Final Salary",
                "OT Days", "Bonus", "Status")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=16)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=105, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", self._download_slip)
        tk.Label(self.parent, text="Double-click row to download salary slip",
                 bg="#0d1b2a", fg="#666", font=("Arial", 8)).pack(anchor="w", padx=10)

    # ── Load Records ─────────────────────────────────────────────────────────
    def _load_salary_records(self):
        m = self.month_var.get(); y = self.year_var.get()
        try:
            docs = self.db.collection("salary") \
                .where("month_num", "==", m).where("year", "==", y).stream()
            for row in self.tree.get_children(): self.tree.delete(row)
            for doc in docs:
                s = doc.to_dict()
                ot_full = s.get("ot_full_days", 0)
                ot_half = s.get("ot_half_days", 0)
                ot_disp = f"{ot_full}F+{ot_half}H" if (ot_full or ot_half) else "0"
                bonus_disp = f"Rs.{s.get('bonus',0):,}" if s.get('bonus', 0) > 0 else "—"
                self.tree.insert("", "end", values=(
                    s.get("employee_id"), s.get("employee_name", ""),
                    f"{MONTH_NAMES[m-1]} {y}",
                    f"Rs.{s.get('base_salary', 0):,}",
                    f"Rs.{s.get('final_salary', 0):,}",
                    ot_disp, bonus_disp,
                    "Ready" if s.get("slip_url") else "Pending"
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load salary: {e}")

    # ── Generate All ─────────────────────────────────────────────────────────
    def _generate_all(self):
        if not messagebox.askyesno("Confirm", "Generate salary slips for all active employees?"):
            return
        m = self.month_var.get(); y = self.year_var.get()
        db = get_db()
        settings     = db.collection("settings").document("company").get()
        company_info = settings.to_dict() if settings.exists else {}
        ot_rate      = float(company_info.get("ot_rate_multiplier", 1.5))
        payment_mode = company_info.get("default_payment_mode", "CASH")
        employees    = db.collection("employees").where("status", "==", "active").stream()
        count = 0
        for emp_doc in employees:
            emp = emp_doc.to_dict()
            try:
                summary     = calculate_monthly_summary(emp["employee_id"], y, m)
                salary_data = calculate_salary(emp, summary, ot_rate,
                                               advance=float(emp.get("advance", 0)),
                                               payment_mode=payment_mode,
                                               month=m, year=y)
                salary_data.update({
                    "month":         MONTH_NAMES[m - 1],
                    "month_num":     m,
                    "year":          y,
                    "employee_id":   emp["employee_id"],
                    "employee_name": emp["name"],
                })
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name
                generate_salary_slip(emp, salary_data, company_info, tmp_path)
                bucket    = get_bucket()
                blob_path = f"salary_slips/{emp['employee_id']}/{y}_{m:02d}_slip.pdf"
                blob      = bucket.blob(blob_path)
                blob.upload_from_filename(tmp_path, content_type="application/pdf")
                blob.make_public()
                slip_url = blob.public_url
                os.unlink(tmp_path)
                from datetime import timedelta
                expires = date(y + 1 if m == 12 else y, 1 if m == 12 else m + 1, 1)
                salary_data["slip_url"]        = slip_url
                salary_data["generated_at"]    = str(date.today())
                salary_data["slip_expires_at"] = str(expires)
                db.collection("salary").document(f"{emp['employee_id']}_{y}_{m:02d}").set(salary_data)
                if emp.get("email"):
                    self._send_email(emp, salary_data, slip_url, company_info)
                count += 1
            except Exception as e:
                print(f"Error for {emp.get('employee_id')}: {e}")
        messagebox.showinfo("Done", f"Generated {count} salary slips!")
        self._load_salary_records()

    # ── Bonus Panel (HR / CA / Admin) ─────────────────────────────────────────
    def _open_bonus_panel(self):
        win = tk.Toplevel(self.parent)
        win.title("🎁 Annual Bonus Management")
        win.geometry("700x500")
        win.configure(bg="#0d1b2a")

        tk.Label(win, text="Annual Bonus — Eligibility & Payment",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#f0c040").pack(pady=10)

        info_text = (
            f"Bonus eligibility: >= {MIN_DAYS_FOR_BONUS} working days in previous year (incl. paid holidays).\n"
            f"Bonus is paid in {MONTH_NAMES[BONUS_MONTH-1]} salary only.\n"
            "You can set each employee's annual bonus amount below."
        )
        tk.Label(win, text=info_text, bg="#0d1b2a", fg="#aaa",
                 font=("Arial", 9), justify="left").pack(padx=20, anchor="w")

        cols = ("Employee ID", "Name", "Annual Days (prev yr)",
                "Eligible", "Bonus Amount (Rs)", "Action")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=110, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        prev_year = datetime.now().year - 1
        try:
            docs = self.db.collection("employees").where("status", "==", "active").stream()
            for doc in docs:
                emp = doc.to_dict()
                ann = calculate_annual_present(emp["employee_id"], prev_year)
                eligible = "✅ Yes" if ann >= MIN_DAYS_FOR_BONUS else "❌ No"
                amt = emp.get("annual_bonus_amount", 0)
                tree.insert("", "end", iid=emp["employee_id"], values=(
                    emp["employee_id"], emp["name"],
                    f"{ann:.1f}", eligible, f"Rs.{amt:,}", "Edit"
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=win)

        def on_edit(event):
            sel = tree.selection()
            if not sel: return
            emp_id = sel[0]
            row    = tree.item(emp_id)["values"]
            new_amt = simpledialog.askfloat(
                "Set Bonus Amount",
                f"Enter annual bonus for {row[1]} (Rs):\n"
                f"Annual days last year: {row[2]}  |  Eligible: {row[3]}",
                parent=win, minvalue=0)
            if new_amt is None: return
            try:
                self.db.collection("employees").document(emp_id).update(
                    {"annual_bonus_amount": new_amt})
                messagebox.showinfo("Saved",
                    f"Bonus for {row[1]} set to Rs.{new_amt:,}", parent=win)
                tree.set(emp_id, "Bonus Amount (Rs)", f"Rs.{new_amt:,}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        tree.bind("<Double-1>", on_edit)
        tk.Label(win, text="Double-click a row to set/edit bonus amount",
                 bg="#0d1b2a", fg="#666", font=("Arial", 8)).pack()

    # ── Salary Raise Panel (CA / Admin) ───────────────────────────────────────
    def _open_raise_panel(self):
        win = tk.Toplevel(self.parent)
        win.title("📈 Salary Raise")
        win.geometry("620x450")
        win.configure(bg="#0d1b2a")

        tk.Label(win, text="Salary Raise — Per Employee",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#a29bfe").pack(pady=10)

        cols = ("Employee ID", "Name", "Current Salary (Rs)", "New Salary")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=145, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        try:
            docs = self.db.collection("employees").where("status", "==", "active").stream()
            for doc in docs:
                emp = doc.to_dict()
                tree.insert("", "end", iid=emp["employee_id"], values=(
                    emp["employee_id"], emp["name"],
                    f"Rs.{emp.get('salary', 0):,}", "—"
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=win)

        def on_raise(event):
            sel = tree.selection()
            if not sel: return
            emp_id = sel[0]
            row    = tree.item(emp_id)["values"]
            new_sal = simpledialog.askfloat(
                "New Salary",
                f"Enter NEW base salary for {row[1]}:\n(Current: {row[2]})",
                parent=win, minvalue=1)
            if new_sal is None: return
            if not messagebox.askyesno("Confirm Raise",
                f"Set salary for {row[1]} to Rs.{new_sal:,}?\n"
                "This change takes effect from next month's payroll.",
                parent=win): return
            try:
                self.db.collection("employees").document(emp_id).update(
                    {"salary": new_sal,
                     "last_raise_by": self.current_user.get("username", ""),
                     "last_raise_date": str(date.today())})
                messagebox.showinfo("Updated",
                    f"{row[1]}'s salary updated to Rs.{new_sal:,}", parent=win)
                tree.set(emp_id, "Current Salary (Rs)", f"Rs.{new_sal:,}")
                tree.set(emp_id, "New Salary", f"✅ Rs.{new_sal:,}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        tree.bind("<Double-1>", on_raise)
        tk.Label(win, text="Double-click a row to set new salary",
                 bg="#0d1b2a", fg="#666", font=("Arial", 8)).pack()

    # ── Email ─────────────────────────────────────────────────────────────────
    def _send_email(self, emp, salary_data, slip_url, company_info):
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        host = company_info.get("smtp_host", "")
        port = int(company_info.get("smtp_port", 587))
        user = company_info.get("smtp_user", "")
        pwd  = company_info.get("smtp_pass", "")
        if not all([host, user, pwd]): return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Salary Slip - {salary_data['month']} {salary_data['year']}"
            msg["From"]    = user
            msg["To"]      = emp["email"]
            html = f"""<h2>Salary Slip — {salary_data['month']} {salary_data['year']}</h2>
            <p>Dear {emp['name']},</p>
            <p>Your salary slip has been generated.</p>
            <p><b>Final Salary: Rs.{salary_data['final_salary']:,}</b></p>
            <p><a href="{slip_url}">Download Salary Slip PDF</a></p>
            <hr/><small>{company_info.get('name','Hype Pvt Ltd')}</small>"""
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(host, port) as s:
                s.starttls(); s.login(user, pwd)
                s.sendmail(user, emp["email"], msg.as_string())
        except Exception as e:
            print(f"Email failed: {e}")

    # ── Download Slip ─────────────────────────────────────────────────────────
    def _download_slip(self, event):
        sel = self.tree.selection()
        if not sel: return
        emp_id = self.tree.item(sel[0])["values"][0]
        m = self.month_var.get(); y = self.year_var.get()
        doc = self.db.collection("salary").document(f"{emp_id}_{y}_{m:02d}").get()
        if doc.exists:
            slip_url = doc.to_dict().get("slip_url", "")
            if slip_url:
                import webbrowser; webbrowser.open(slip_url)
            else:
                messagebox.showinfo("Info", "Slip not generated yet.")
        else:
            messagebox.showinfo("Info", "No salary record found.")
