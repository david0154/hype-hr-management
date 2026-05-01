"""
Hype HR Management — Admin App: Company & System Settings Panel
Tabs: Company Info | SMTP / Email | Salary Rules | Bonus Settings | Advance Settings
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox

RELIGIONS = ['Hindu', 'Muslim', 'Christian', 'Sikh', 'Buddhist', 'Jain', 'Other']
MONTHS    = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
]


class CompanySettingsPanel(tk.Frame):
    """Company & SMTP settings panel (Admin Tkinter app)."""

    def __init__(self, master, firebase_manager, current_role='admin', **kwargs):
        super().__init__(master, bg='#f0f2f5', **kwargs)
        self.fm   = firebase_manager
        self.role = current_role.lower()
        self._religion_rows = []   # list of dicts per religion row
        self._build_ui()
        self._load_settings()

    # =========================================================================
    def _build_ui(self):
        tk.Label(self, text='Company & System Settings',
                 font=('Arial', 16, 'bold'), bg='#1A2740', fg='white',
                 pady=10).pack(fill=tk.X)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1 — Company Info
        f1 = tk.Frame(nb, bg='#f0f2f5'); nb.add(f1, text=' Company Info ')
        self._add_company_fields(f1)

        # Tab 2 — SMTP
        f2 = tk.Frame(nb, bg='#f0f2f5'); nb.add(f2, text=' SMTP / Email ')
        self._add_smtp_fields(f2)

        # Tab 3 — Salary Rules
        f3 = tk.Frame(nb, bg='#f0f2f5'); nb.add(f3, text=' Salary Rules ')
        self._add_rules_fields(f3)

        # Tab 4 — Bonus Settings
        f4 = tk.Frame(nb, bg='#f0f2f5'); nb.add(f4, text=' Bonus Settings ')
        self._add_bonus_fields(f4)

        # Tab 5 — Advance Settings
        f5 = tk.Frame(nb, bg='#f0f2f5'); nb.add(f5, text=' Advance Settings ')
        self._add_advance_fields(f5)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _field(self, parent, label, row, var_name, show=None, width=40):
        tk.Label(parent, text=label, bg='#f0f2f5', anchor='w',
                 width=26).grid(row=row, column=0, sticky='w', padx=12, pady=5)
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, width=width,
                 show=show or '').grid(row=row, column=1, sticky='w', padx=4)
        setattr(self, var_name, var)
        return var

    def _combo(self, parent, label, row, var_name, values, width=18):
        tk.Label(parent, text=label, bg='#f0f2f5', anchor='w',
                 width=26).grid(row=row, column=0, sticky='w', padx=12, pady=5)
        var = tk.StringVar()
        ttk.Combobox(parent, textvariable=var, values=values,
                     width=width, state='readonly').grid(
            row=row, column=1, sticky='w', padx=4)
        setattr(self, var_name, var)
        return var

    def _save_btn(self, parent, row, text, cmd):
        tk.Button(parent, text=text, command=cmd,
                  bg='#1A2740', fg='white', padx=14, pady=6).grid(
            row=row, column=0, columnspan=2, pady=14)

    # =========================================================================
    # Tab 1 — Company Info
    # =========================================================================
    def _add_company_fields(self, f):
        tk.Label(f, text='Company Information', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=2, pady=(10,4), padx=12, sticky='w')
        self._field(f, 'Company Name *',  1, 'v_company_name')
        self._field(f, 'Company Address', 2, 'v_company_address')
        self._field(f, 'Contact Email',   3, 'v_company_email')
        self._field(f, 'Phone Number',    4, 'v_company_phone')
        self._field(f, 'City / State',    5, 'v_company_city')
        self._field(f, 'GST Number',      6, 'v_company_gst')
        self._save_btn(f, 7, 'Save Company Info', self._save_company)

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
            messagebox.showinfo('Saved', 'Company info saved.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # =========================================================================
    # Tab 2 — SMTP
    # =========================================================================
    def _add_smtp_fields(self, f):
        tk.Label(f, text='SMTP Email Configuration', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=2, pady=(10,4), padx=12, sticky='w')
        tk.Label(f, text='Used to send salary slips automatically on the 1st of each month.',
                 bg='#f0f2f5', fg='gray', wraplength=460).grid(
            row=1, column=0, columnspan=2, padx=12, sticky='w')
        self._field(f, 'SMTP Host',     2, 'v_smtp_host')
        self._field(f, 'SMTP Port',     3, 'v_smtp_port')
        self._field(f, 'SMTP Username', 4, 'v_smtp_user')
        self._field(f, 'SMTP Password', 5, 'v_smtp_pass', show='*')
        self._field(f, 'From Email',    6, 'v_smtp_from')
        self._field(f, 'From Name',     7, 'v_smtp_from_name')
        bf = tk.Frame(f, bg='#f0f2f5'); bf.grid(row=8, column=0, columnspan=2, pady=14)
        tk.Button(bf, text='Save SMTP',       command=self._save_smtp,
                  bg='#1A2740', fg='white', padx=14, pady=6).pack(side=tk.LEFT, padx=6)
        tk.Button(bf, text='Send Test Email', command=self._test_smtp,
                  bg='#F77F00', fg='white', padx=14, pady=6).pack(side=tk.LEFT)

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

    def _test_smtp(self):
        import smtplib
        from email.mime.text import MIMEText
        try:
            msg = MIMEText('This is a test email from Hype HR Management Admin App.')
            msg['Subject'] = 'Hype HR — SMTP Test'
            msg['From']    = self.v_smtp_from.get().strip()
            msg['To']      = self.v_smtp_from.get().strip()
            with smtplib.SMTP(self.v_smtp_host.get(),
                              int(self.v_smtp_port.get() or 587), timeout=15) as s:
                s.starttls()
                s.login(self.v_smtp_user.get(), self.v_smtp_pass.get())
                s.send_message(msg)
            messagebox.showinfo('Success', 'Test email sent!')
        except Exception as e:
            messagebox.showerror('SMTP Error', str(e))

    # =========================================================================
    # Tab 3 — Salary Rules
    # =========================================================================
    def _add_rules_fields(self, f):
        tk.Label(f, text='Salary & Attendance Rules', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=2, pady=(10,4), padx=12, sticky='w')
        self._field(f, 'Working Hours / Day',  1, 'v_work_hours')
        self._field(f, 'Monthly Working Days', 2, 'v_work_days')
        self._field(f, 'OT Rate Multiplier',   3, 'v_ot_multiplier')
        self._field(f, 'Payment Mode',         4, 'v_payment_mode')
        self._save_btn(f, 5, 'Save Rules', self._save_rules)

    def _save_rules(self):
        try:
            data = {
                'working_hours_per_day': int(self.v_work_hours.get()   or 12),
                'monthly_working_days':  int(self.v_work_days.get()    or 26),
                'ot_rate_multiplier':    float(self.v_ot_multiplier.get() or 1.5),
                'payment_mode':          self.v_payment_mode.get().strip().upper(),
            }
            self.fm.set_document('settings', 'app', data)
            messagebox.showinfo('Saved', 'Salary rules saved.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # =========================================================================
    # Tab 4 — Bonus Settings
    # =========================================================================
    def _add_bonus_fields(self, f):
        tk.Label(f, text='Bonus Settings', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=4, pady=(10,2), padx=12, sticky='w')

        # Mode toggle
        self.v_bonus_mode = tk.StringVar(value='standard')
        mode_f = tk.Frame(f, bg='#f0f2f5')
        mode_f.grid(row=1, column=0, columnspan=4, padx=12, pady=4, sticky='w')
        tk.Radiobutton(mode_f, text='Standard (same date for all)',
                       variable=self.v_bonus_mode, value='standard',
                       bg='#f0f2f5', command=self._toggle_bonus_mode).pack(side=tk.LEFT, padx=8)
        tk.Radiobutton(mode_f, text='Religion-based (per religion)',
                       variable=self.v_bonus_mode, value='religion',
                       bg='#f0f2f5', command=self._toggle_bonus_mode).pack(side=tk.LEFT, padx=8)

        # ── Standard section ─────────────────────────────────────────────────
        self._std_frame = tk.LabelFrame(f, text=' Standard Bonus Date ',
                                        bg='#f0f2f5', font=('Arial', 10, 'bold'))
        self._std_frame.grid(row=2, column=0, columnspan=4,
                             padx=12, pady=6, sticky='ew')
        tk.Label(self._std_frame, text='Bonus Month', bg='#f0f2f5', width=20,
                 anchor='w').grid(row=0, column=0, padx=8, pady=6, sticky='w')
        self.v_std_month = tk.StringVar(value='March')
        ttk.Combobox(self._std_frame, textvariable=self.v_std_month,
                     values=MONTHS, width=14, state='readonly').grid(
            row=0, column=1, sticky='w', padx=4)
        tk.Label(self._std_frame, text='Bonus Day (1–31)', bg='#f0f2f5', width=20,
                 anchor='w').grid(row=1, column=0, padx=8, pady=6, sticky='w')
        self.v_std_day = tk.StringVar(value='1')
        tk.Entry(self._std_frame, textvariable=self.v_std_day,
                 width=6).grid(row=1, column=1, sticky='w', padx=4)
        tk.Label(self._std_frame, text='Min Eligible Days (prev year)',
                 bg='#f0f2f5', width=26, anchor='w').grid(
            row=2, column=0, padx=8, pady=6, sticky='w')
        self.v_bonus_min_days = tk.StringVar(value='240')
        tk.Entry(self._std_frame, textvariable=self.v_bonus_min_days,
                 width=6).grid(row=2, column=1, sticky='w', padx=4)

        # ── Religion section ──────────────────────────────────────────────────
        self._rel_frame = tk.LabelFrame(f, text=' Religion-Based Bonus Dates ',
                                        bg='#f0f2f5', font=('Arial', 10, 'bold'))
        self._rel_frame.grid(row=3, column=0, columnspan=4,
                             padx=12, pady=4, sticky='ew')
        self._religion_rows = []
        self._build_religion_rows()

        tk.Label(f, text='Bonus amount is visible to HR / CA / Admin only.'
                         ' Employee slip shows amount WITHOUT calculation details.',
                 bg='#fff3cd', fg='#856404', wraplength=480,
                 relief='flat', bd=0, padx=8, pady=6).grid(
            row=4, column=0, columnspan=4, padx=12, pady=4, sticky='ew')

        self._save_btn(f, 5, 'Save Bonus Settings', self._save_bonus)

    def _build_religion_rows(self):
        """Draw one row per religion: religion label | month combobox | day entry | label entry."""
        for w in self._rel_frame.winfo_children():
            w.destroy()
        self._religion_rows = []
        hdrs = ['Religion', 'Bonus Month', 'Day (1–31)', 'Label / Festival Name']
        for c, h in enumerate(hdrs):
            tk.Label(self._rel_frame, text=h, bg='#dde3eb', relief='groove',
                     width=[12,14,10,22][c], anchor='w',
                     font=('Arial', 9, 'bold')).grid(
                row=0, column=c, padx=2, pady=2, sticky='ew')
        for i, rel in enumerate(RELIGIONS, start=1):
            v_month = tk.StringVar(value='March')
            v_day   = tk.StringVar(value='1')
            v_label = tk.StringVar(value=f'{rel} Bonus')
            tk.Label(self._rel_frame, text=rel, bg='#f0f2f5',
                     width=12, anchor='w').grid(row=i, column=0, padx=4, pady=3, sticky='w')
            ttk.Combobox(self._rel_frame, textvariable=v_month,
                         values=MONTHS, width=12, state='readonly').grid(
                row=i, column=1, padx=2, pady=2, sticky='w')
            tk.Entry(self._rel_frame, textvariable=v_day,
                     width=8).grid(row=i, column=2, padx=2, pady=2, sticky='w')
            tk.Entry(self._rel_frame, textvariable=v_label,
                     width=20).grid(row=i, column=3, padx=2, pady=2, sticky='w')
            self._religion_rows.append(
                {'religion': rel, 'v_month': v_month,
                 'v_day': v_day, 'v_label': v_label}
            )

    def _toggle_bonus_mode(self):
        mode = self.v_bonus_mode.get()
        if mode == 'standard':
            self._std_frame.grid()
            self._rel_frame.grid_remove()
        else:
            self._std_frame.grid_remove()
            self._rel_frame.grid()

    def _save_bonus(self):
        mode = self.v_bonus_mode.get()
        data = {
            'mode': mode,
            'standard_month':   self.v_std_month.get(),
            'standard_day':     int(self.v_std_day.get() or 1),
            'bonus_min_days':   int(self.v_bonus_min_days.get() or 240),
            'religion_dates':   {},
        }
        for row in self._religion_rows:
            key = row['religion'].lower()
            data['religion_dates'][key] = {
                'month':   row['v_month'].get(),
                'day':     int(row['v_day'].get() or 1),
                'label':   row['v_label'].get().strip(),
                'enabled': True,
            }
        try:
            self.fm.set_document('settings', 'bonus', data)
            messagebox.showinfo('Saved', 'Bonus settings saved.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # =========================================================================
    # Tab 5 — Advance Settings
    # =========================================================================
    def _add_advance_fields(self, f):
        tk.Label(f, text='Advance Payment Settings', bg='#f0f2f5',
                 font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=2, pady=(10,4), padx=12, sticky='w')
        tk.Label(f, text='Configure when and how much advance can be paid to employees.',
                 bg='#f0f2f5', fg='gray', wraplength=460).grid(
            row=1, column=0, columnspan=2, padx=12, pady=2, sticky='w')

        tk.Label(f, text='Fixed Advance Day (1–31, 0=off)',
                 bg='#f0f2f5', width=30, anchor='w').grid(
            row=2, column=0, padx=12, pady=6, sticky='w')
        self.v_adv_day = tk.StringVar(value='0')
        tk.Entry(f, textvariable=self.v_adv_day, width=6).grid(
            row=2, column=1, sticky='w', padx=4)
        tk.Label(f, text='(0 = no fixed date; HR enters manually anytime)',
                 bg='#f0f2f5', fg='gray', font=('Arial', 8)).grid(
            row=3, column=0, columnspan=2, padx=12, sticky='w')

        tk.Label(f, text='Max Single Advance Amount (Rs.)',
                 bg='#f0f2f5', width=30, anchor='w').grid(
            row=4, column=0, padx=12, pady=6, sticky='w')
        self.v_adv_max = tk.StringVar(value='5000')
        tk.Entry(f, textvariable=self.v_adv_max, width=10).grid(
            row=4, column=1, sticky='w', padx=4)

        tk.Label(f, text='Allow Multiple Advances Before Deduction',
                 bg='#f0f2f5', width=30, anchor='w').grid(
            row=5, column=0, padx=12, pady=6, sticky='w')
        self.v_adv_multi = tk.BooleanVar(value=True)
        tk.Checkbutton(f, variable=self.v_adv_multi,
                       bg='#f0f2f5').grid(row=5, column=1, sticky='w', padx=4)

        tk.Label(f, text='Advance Deduction Month',
                 bg='#f0f2f5', width=30, anchor='w').grid(
            row=6, column=0, padx=12, pady=6, sticky='w')
        self.v_adv_deduct = tk.StringVar(value='next_month')
        ttk.Combobox(f, textvariable=self.v_adv_deduct,
                     values=['next_month', 'same_month', 'manual'],
                     width=14, state='readonly').grid(
            row=6, column=1, sticky='w', padx=4)

        # Religion-based advance section
        rel_adv = tk.LabelFrame(f, text=' Religion-Based Advance Date (optional) ',
                                bg='#f0f2f5', font=('Arial', 10, 'bold'))
        rel_adv.grid(row=7, column=0, columnspan=2, padx=12, pady=8, sticky='ew')
        tk.Label(rel_adv,
                 text='Set a specific advance date per religion (e.g. before festival).\n'
                      'Leave day=0 to disable for that religion.',
                 bg='#f0f2f5', fg='gray', wraplength=460,
                 font=('Arial', 8)).grid(
            row=0, column=0, columnspan=3, padx=8, pady=4, sticky='w')

        hdrs = ['Religion', 'Advance Month', 'Day (1–31, 0=off)']
        for c, h in enumerate(hdrs):
            tk.Label(rel_adv, text=h, bg='#dde3eb', relief='groove',
                     width=[12,14,18][c], anchor='w',
                     font=('Arial', 9, 'bold')).grid(
                row=1, column=c, padx=2, pady=2, sticky='ew')

        self._adv_rel_rows = []
        for i, rel in enumerate(RELIGIONS, start=2):
            v_month = tk.StringVar(value='January')
            v_day   = tk.StringVar(value='0')
            tk.Label(rel_adv, text=rel, bg='#f0f2f5',
                     width=12, anchor='w').grid(row=i, column=0, padx=4, pady=3, sticky='w')
            ttk.Combobox(rel_adv, textvariable=v_month,
                         values=MONTHS, width=12, state='readonly').grid(
                row=i, column=1, padx=2, pady=2, sticky='w')
            tk.Entry(rel_adv, textvariable=v_day, width=8).grid(
                row=i, column=2, padx=2, pady=2, sticky='w')
            self._adv_rel_rows.append(
                {'religion': rel, 'v_month': v_month, 'v_day': v_day}
            )

        self._save_btn(f, 8, 'Save Advance Settings', self._save_advance)

    def _save_advance(self):
        rel_dates = {}
        for row in self._adv_rel_rows:
            day = int(row['v_day'].get() or 0)
            if day > 0:
                rel_dates[row['religion'].lower()] = {
                    'month': row['v_month'].get(),
                    'day':   day,
                }
        data = {
            'fixed_advance_day':   int(self.v_adv_day.get()   or 0),
            'max_advance_amount':  float(self.v_adv_max.get() or 5000),
            'allow_multi_advance': self.v_adv_multi.get(),
            'deduction_timing':    self.v_adv_deduct.get(),
            'religion_dates':      rel_dates,
        }
        try:
            self.fm.set_document('settings', 'advance', data)
            messagebox.showinfo('Saved', 'Advance settings saved.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # =========================================================================
    # Load all settings on startup
    # =========================================================================
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

            # Bonus
            bon = self.fm.get_document('settings', 'bonus') or {}
            self.v_bonus_mode.set(bon.get('mode', 'standard'))
            self.v_std_month.set(bon.get('standard_month', 'March'))
            self.v_std_day.set(str(bon.get('standard_day', 1)))
            self.v_bonus_min_days.set(str(bon.get('bonus_min_days', 240)))
            rel_dates = bon.get('religion_dates', {})
            for row in self._religion_rows:
                key = row['religion'].lower()
                if key in rel_dates:
                    row['v_month'].set(rel_dates[key].get('month', 'March'))
                    row['v_day'].set(str(rel_dates[key].get('day', 1)))
                    row['v_label'].set(rel_dates[key].get('label', f"{row['religion']} Bonus"))
            self._toggle_bonus_mode()

            # Advance
            adv = self.fm.get_document('settings', 'advance') or {}
            self.v_adv_day.set(str(adv.get('fixed_advance_day', 0)))
            self.v_adv_max.set(str(adv.get('max_advance_amount', 5000)))
            self.v_adv_multi.set(adv.get('allow_multi_advance', True))
            self.v_adv_deduct.set(adv.get('deduction_timing', 'next_month'))
            adv_rel = adv.get('religion_dates', {})
            for row in self._adv_rel_rows:
                key = row['religion'].lower()
                if key in adv_rel:
                    row['v_month'].set(adv_rel[key].get('month', 'January'))
                    row['v_day'].set(str(adv_rel[key].get('day', 0)))
        except Exception as e:
            messagebox.showerror('Load Error', str(e))
