"""
Salary Slip PDF Generator — Hype HR Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
from fpdf import FPDF
from datetime import datetime
import os


class SalarySlipPDF(FPDF):
    def __init__(self, company_info: dict):
        super().__init__()
        self.company_info = company_info

    def header(self):
        logo_path = os.path.join(os.path.dirname(__file__), '../../assets/logo.png')
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 25)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, self.company_info.get('name', 'HYPE PVT LTD'), align='C')
        self.ln(7)
        self.set_font('Arial', '', 9)
        self.cell(0, 5, self.company_info.get('address', ''), align='C')
        self.ln(5)
        self.cell(0, 5, f"Email: {self.company_info.get('email', 'nexuzylab@gmail.com')}", align='C')
        self.ln(8)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-25)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, 'Authorized Signature: ____________________', align='R')
        self.ln(5)
        self.cell(0, 5,
            f'Generated on {datetime.now().strftime("%d/%m/%Y %H:%M")} | Managed by Nexuzy Lab | nexuzylab@gmail.com',
            align='C')


def generate_salary_slip(employee: dict, salary_data: dict, company_info: dict, output_path: str) -> str:
    pdf = SalarySlipPDF(company_info)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)
    col_w = 90

    # Title bar
    pdf.set_font('Arial', 'B', 13)
    pdf.set_fill_color(30, 30, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, '  SALARY SLIP', fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Employee info
    rows = [
        ('Employee Name',  employee.get('name', '')),
        ('Employee ID',    employee.get('employee_id', '')),
        ('Designation',    employee.get('designation', 'Employee')),
        ('Month / Year',   f"{salary_data.get('month', '')} {salary_data.get('year', '')}"),
        ('Payment Mode',   salary_data.get('payment_mode', 'CASH')),
    ]
    for label, value in rows:
        pdf.set_font('Arial', 'B', 10); pdf.cell(col_w, 7, f'  {label}', border=1)
        pdf.set_font('Arial', '',  10); pdf.cell(col_w, 7, f'  {value}', border=1)
        pdf.ln()
    pdf.ln(4)

    # Attendance summary
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(230, 236, 255)
    pdf.cell(0, 8, '  ATTENDANCE SUMMARY', fill=True, border=1)
    pdf.ln()
    att_rows = [
        ('Total Working Days',  str(salary_data.get('total_working_days', 0))),
        ('Total Present Days',  str(salary_data.get('total_present', 0))),
        ('Half Days',           str(salary_data.get('half_days', 0))),
        ('Absent Days',         str(salary_data.get('absent_days', 0))),
        ('Paid Holidays',       str(salary_data.get('paid_holidays', 0))),
        ('Overtime Hours',      f"{salary_data.get('ot_hours', 0)} hrs"),
    ]
    pdf.set_font('Arial', '', 10)
    for label, value in att_rows:
        pdf.set_font('Arial', 'B', 10); pdf.cell(col_w, 7, f'  {label}', border=1)
        pdf.set_font('Arial', '',  10); pdf.cell(col_w, 7, f'  {value}', border=1)
        pdf.ln()
    pdf.ln(4)

    # Salary details
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(230, 255, 236)
    pdf.cell(0, 8, '  SALARY DETAILS', fill=True, border=1)
    pdf.ln()
    sal_rows = [
        ('Base Salary',       f"Rs. {salary_data.get('base_salary', 0):,.0f}"),
        ('Attendance Salary', f"Rs. {salary_data.get('attendance_salary', 0):,.0f}"),
        ('Overtime Pay',      f"Rs. {salary_data.get('ot_pay', 0):,.0f}"),
        ('Bonus',             f"Rs. {salary_data.get('bonus', 0):,.0f}"),
        ('Deduction',         f"- Rs. {salary_data.get('deduction', 0):,.0f}"),
        ('Advance',           f"- Rs. {salary_data.get('advance', 0):,.0f}"),
    ]
    for label, value in sal_rows:
        pdf.set_font('Arial', 'B', 10); pdf.cell(col_w, 7, f'  {label}', border=1)
        pdf.set_font('Arial', '',  10); pdf.cell(col_w, 7, f'  {value}', border=1)
        pdf.ln()

    # Final salary
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 13)
    pdf.set_fill_color(20, 100, 60)
    pdf.set_text_color(255, 255, 255)
    final = salary_data.get('final_salary', 0)
    pdf.cell(col_w, 10, '  FINAL SALARY', border=1, fill=True)
    pdf.cell(col_w, 10, f'  Rs. {final:,.0f}', border=1, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(12)

    pdf.output(output_path)
    return output_path
