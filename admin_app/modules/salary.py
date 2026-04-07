"""
Salary Module — Hype HR Management
Formula: Final = (Base x AttRatio) + OT + Bonus - Deduction - Advance
Auto-generates PDF, uploads to Firebase Storage, emails employee
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import os, tempfile
from utils.firebase_config import get_db, get_bucket
from utils.pdf_generator import generate_salary_slip
from modules.attendance import calculate_monthly_summary
from modules.roles import has_permission

MONTH_NAMES = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]


def calculate_salary(employee: dict, summary: dict, ot_rate: float = 1.5,
                     bonus: float = 0, deduction: float = 0, advance: float = 0,
                     payment_mode: str = "CASH") -> dict:
    base          = employee.get("salary", 0)
    total_working = summary.get("total_working_days", 26)
    present       = summary.get("total_present", 0)
    half_days     = summary.get("half_days", 0)
    paid_holidays = summary.get("paid_holidays", 0)

    paid_days        = present + (half_days * 0.5) + paid_holidays
    attendance_ratio = min(paid_days / total_working, 1.0) if total_working > 0 else 0
    attendance_salary = round(base * attendance_ratio, 2)

    ot_hours  = summary.get("ot_hours", 0)
    daily_rate   = base / total_working if total_working else 0
    hourly_rate  = daily_rate / 8
    ot_pay    = round(ot_hours * ot_rate * hourly_rate, 2)

    final_salary = round(attendance_salary + ot_pay + bonus - deduction - advance, 2)

    return {
        "base_salary":        base,
        "attendance_salary":  attendance_salary,
        "ot_pay":             ot_pay,
        "bonus":              bonus,
        "deduction":          deduction,
        "advance":            advance,
        "final_salary":       final_salary,
        "payment_mode":       payment_mode,
        "total_working_days": total_working,
        "total_present":      present,
        "half_days":          half_days,
        "absent_days":        summary.get("absent_days", 0),
        "paid_holidays":      paid_holidays,
        "ot_hours":           ot_hours,
    }


class SalaryModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.role = current_user.get("role", "ca")
        self.db = get_db()
        self._build_ui()
        self._load_salary_records()

    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="💰 Salary Management",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)
        if has_permission(self.role, "salary"):
            tk.Button(top, text="⚙ Generate This Month", bg="#f77f00", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._generate_all).pack(side="right", padx=10)

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

        cols = ("Employee ID", "Name", "Month", "Base", "Final Salary", "OT Hrs", "Status")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=18)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=112, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", self._download_slip)
        tk.Label(self.parent, text="Double-click row to download salary slip",
                 bg="#0d1b2a", fg="#666", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load_salary_records(self):
        m = self.month_var.get(); y = self.year_var.get()
        try:
            docs = self.db.collection("salary") \
                .where("month_num", "==", m).where("year", "==", y).stream()
            for row in self.tree.get_children(): self.tree.delete(row)
            for doc in docs:
                s = doc.to_dict()
                self.tree.insert("", "end", values=(
                    s.get("employee_id"), s.get("employee_name", ""),
                    f"{MONTH_NAMES[m-1]} {y}",
                    f"Rs.{s.get('base_salary', 0):,}",
                    f"Rs.{s.get('final_salary', 0):,}",
                    f"{s.get('ot_hours', 0)} hrs",
                    "Ready" if s.get("slip_url") else "Pending"
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load salary: {e}")

    def _generate_all(self):
        if not messagebox.askyesno("Confirm", "Generate salary slips for all active employees?"):
            return
        m = self.month_var.get(); y = self.year_var.get()
        db = get_db()
        settings = db.collection("settings").document("company").get()
        company_info = settings.to_dict() if settings.exists else {}
        ot_rate      = float(company_info.get("ot_rate_multiplier", 1.5))
        payment_mode = company_info.get("default_payment_mode", "CASH")
        employees    = db.collection("employees").where("status", "==", "active").stream()
        count = 0
        for emp_doc in employees:
            emp = emp_doc.to_dict()
            try:
                summary     = calculate_monthly_summary(emp["employee_id"], y, m)
                salary_data = calculate_salary(emp, summary, ot_rate, payment_mode=payment_mode)
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
            <hr/><small>{company_info.get('name','Hype Pvt Ltd')} | nexuzylab@gmail.com</small>"""
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(host, port) as s:
                s.starttls(); s.login(user, pwd)
                s.sendmail(user, emp["email"], msg.as_string())
        except Exception as e:
            print(f"Email failed: {e}")

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
