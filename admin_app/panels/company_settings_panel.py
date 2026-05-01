"""
Hype HR Management — Admin App: Company Settings Panel
Handles: company name, address, email, phone, SMTP config, OT rate, working hours.
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox


class CompanySettingsPanel(tk.Frame):
    """Company & SMTP settings panel for Admin Tkinter app."""

    def __init__(self, master, firebase_manager, **kwargs):
        super().__init__(master, bg='#f0f2f5', **kwargs)
        self.fm = firebase_manager
        self._build_ui()
        self._load_settings()

    # -------------------------------------------------------------------------
    def _build_ui(self):
        tk.Label(self, text='Company & System Settings',
                 font=('Arial', 16, 'bold'), bg='#1A2740', fg='white',
                 pady=10).pack(fill=tk.X)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── Tab 1: Company Info ───────────────────────────────────────────────
        company_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(company_frame, text='Company Info')
        self._company_frame = company_frame
        self._add_company_fields(company_frame)

        # ── Tab 2: SMTP Mail ─────────────────────────────────────────────────
        smtp_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(smtp_frame, text='SMTP / Email')
        self._add_smtp_fields(smtp_frame)

        # ── Tab 3: Salary Rules ───────────────────────────────────────────────
        rules_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(rules_frame, text='Salary Rules')
        self._add_rules_fields(rules_frame)

    # -------------------------------------------------------------------------
    def _field(self, parent, label, row, var_name, show=None):
        tk.Label(parent, text=label, bg='#f0f2f5', anchor='w',
                 width=24).grid(row=row, column=0, sticky='w', padx=12, pady=6)
        var = tk.StringVar()
        entry = tk.Entry(parent, textvariable=var, width=40,
                         show=show if show else '')
        entry.grid(row=row, column=1, sticky='w', padx=4)
        setattr(self, var_name, var)
        return var

    def _add_company_fields(self, frame):
        tk.Label(frame, text='Company Information', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(row=0, column=0,
                 columnspan=2, pady=(10, 4), padx=12, sticky='w')
        self._field(frame, 'Company Name *',    1, 'v_company_name')
        self._field(frame, 'Company Address',   2, 'v_company_address')
        self._field(frame, 'Contact Email',     3, 'v_company_email')
        self._field(frame, 'Phone Number',      4, 'v_company_phone')
        self._field(frame, 'City / State',      5, 'v_company_city')
        self._field(frame, 'GST Number',        6, 'v_company_gst')
        tk.Button(frame, text='Save Company Info', command=self._save_company,
                  bg='#1A2740', fg='white', padx=14, pady=6).grid(
            row=7, column=0, columnspan=2, pady=14)

    def _add_smtp_fields(self, frame):
        tk.Label(frame, text='SMTP Email Configuration', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(row=0, column=0,
                 columnspan=2, pady=(10, 4), padx=12, sticky='w')
        tk.Label(frame, text='Used to send salary slips automatically on the 1st of each month.',
                 bg='#f0f2f5', fg='gray', wraplength=450).grid(
            row=1, column=0, columnspan=2, padx=12, sticky='w')

        self._field(frame, 'SMTP Host',         2, 'v_smtp_host')
        self._field(frame, 'SMTP Port',         3, 'v_smtp_port')
        self._field(frame, 'SMTP Username',     4, 'v_smtp_user')
        self._field(frame, 'SMTP Password',     5, 'v_smtp_pass', show='*')
        self._field(frame, 'From Email',        6, 'v_smtp_from')
        self._field(frame, 'From Name',         7, 'v_smtp_from_name')

        btn_frame = tk.Frame(frame, bg='#f0f2f5')
        btn_frame.grid(row=8, column=0, columnspan=2, pady=14)
        tk.Button(btn_frame, text='Save SMTP', command=self._save_smtp,
                  bg='#1A2740', fg='white', padx=14, pady=6).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='Send Test Email', command=self._test_smtp,
                  bg='#F77F00', fg='white', padx=14, pady=6).pack(side=tk.LEFT)

    def _add_rules_fields(self, frame):
        tk.Label(frame, text='Salary & Attendance Rules', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(row=0, column=0,
                 columnspan=2, pady=(10, 4), padx=12, sticky='w')
        self._field(frame, 'Working Hours / Day',  1, 'v_work_hours')
        self._field(frame, 'Monthly Working Days', 2, 'v_work_days')
        self._field(frame, 'OT Rate Multiplier',   3, 'v_ot_multiplier')
        self._field(frame, 'Payment Mode',         4, 'v_payment_mode')
        tk.Button(frame, text='Save Rules', command=self._save_rules,
                  bg='#1A2740', fg='white', padx=14, pady=6).grid(
            row=5, column=0, columnspan=2, pady=14)

    # -------------------------------------------------------------------------
    def _load_settings(self):
        try:
            co = self.fm.get_document('settings', 'company') or {}
            self.v_company_name.set(co.get('name', ''))
            self.v_company_address.set(co.get('address', ''))
            self.v_company_email.set(co.get('email', ''))
            self.v_company_phone.set(co.get('phone', ''))
            self.v_company_city.set(co.get('city', ''))
            self.v_company_gst.set(co.get('gst', ''))

            smtp = self.fm.get_document('settings', 'smtp') or {}
            self.v_smtp_host.set(smtp.get('host', 'smtp.gmail.com'))
            self.v_smtp_port.set(str(smtp.get('port', 587)))
            self.v_smtp_user.set(smtp.get('user', ''))
            self.v_smtp_pass.set(smtp.get('password', ''))
            self.v_smtp_from.set(smtp.get('from_email', ''))
            self.v_smtp_from_name.set(smtp.get('from_name', 'Hype HR'))

            app = self.fm.get_document('settings', 'app') or {}
            self.v_work_hours.set(str(app.get('working_hours_per_day', 12)))
            self.v_work_days.set(str(app.get('monthly_working_days', 26)))
            self.v_ot_multiplier.set(str(app.get('ot_rate_multiplier', 1.5)))
            self.v_payment_mode.set(app.get('payment_mode', 'CASH'))
        except Exception as e:
            messagebox.showerror('Load Error', str(e))

    def _save_company(self):
        data = {
            'name':    self.v_company_name.get().strip(),
            'address': self.v_company_address.get().strip(),
            'email':   self.v_company_email.get().strip(),
            'phone':   self.v_company_phone.get().strip(),
            'city':    self.v_company_city.get().strip(),
            'gst':     self.v_company_gst.get().strip(),
        }
        if not data['name']:
            messagebox.showwarning('Validation', 'Company Name is required.')
            return
        try:
            self.fm.set_document('settings', 'company', data)
            messagebox.showinfo('Saved', 'Company info saved successfully.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _save_smtp(self):
        data = {
            'host':       self.v_smtp_host.get().strip(),
            'port':       int(self.v_smtp_port.get().strip() or 587),
            'user':       self.v_smtp_user.get().strip(),
            'password':   self.v_smtp_pass.get().strip(),
            'from_email': self.v_smtp_from.get().strip(),
            'from_name':  self.v_smtp_from_name.get().strip(),
        }
        try:
            self.fm.set_document('settings', 'smtp', data)
            messagebox.showinfo('Saved', 'SMTP settings saved.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _save_rules(self):
        try:
            data = {
                'working_hours_per_day':  int(self.v_work_hours.get() or 12),
                'monthly_working_days':   int(self.v_work_days.get()   or 26),
                'ot_rate_multiplier':     float(self.v_ot_multiplier.get() or 1.5),
                'payment_mode':           self.v_payment_mode.get().strip().upper(),
            }
            self.fm.set_document('settings', 'app', data)
            messagebox.showinfo('Saved', 'Salary rules saved.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _test_smtp(self):
        """Send a test email via PHP backend webhook or local SMTP test."""
        import smtplib
        from email.mime.text import MIMEText
        try:
            msg = MIMEText('This is a test email from Hype HR Management Admin App.')
            msg['Subject'] = 'Hype HR — SMTP Test'
            msg['From']    = self.v_smtp_from.get().strip()
            msg['To']      = self.v_smtp_from.get().strip()
            with smtplib.SMTP(self.v_smtp_host.get(), int(self.v_smtp_port.get() or 587),
                              timeout=15) as s:
                s.starttls()
                s.login(self.v_smtp_user.get(), self.v_smtp_pass.get())
                s.send_message(msg)
            messagebox.showinfo('Success', 'Test email sent! Check your inbox.')
        except Exception as e:
            messagebox.showerror('SMTP Error', str(e))
