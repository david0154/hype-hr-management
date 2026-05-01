"""
Hype HR Management — Admin App: QR Generator Panel
Generates:
  1. Location QR codes (Gate, Office, Floor, Laser Room, etc.)
  2. Employee ID Card with embedded QR code
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
try:
    import qrcode
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class QRGeneratorPanel(tk.Frame):
    """QR code and ID card generator for admin app."""

    def __init__(self, master, firebase_manager, **kwargs):
        super().__init__(master, bg='#f0f2f5', **kwargs)
        self.fm         = firebase_manager
        self._preview   = None
        self._build_ui()
        self._load_locations()

    def _build_ui(self):
        tk.Label(self, text='QR Code & ID Card Generator',
                 font=('Arial', 16, 'bold'), bg='#1A2740', fg='white',
                 pady=10).pack(fill=tk.X)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Location QR
        loc_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(loc_frame, text='Location QR')
        self._build_location_tab(loc_frame)

        # Tab 2: Employee ID Card
        id_frame = tk.Frame(notebook, bg='#f0f2f5')
        notebook.add(id_frame, text='Employee ID Card')
        self._build_idcard_tab(id_frame)

    # ── Location QR ───────────────────────────────────────────────────────────
    def _build_location_tab(self, frame):
        tk.Label(frame, text='Select or add a location to generate its QR code.',
                 bg='#f0f2f5', fg='gray').pack(pady=6, padx=12, anchor='w')

        top = tk.Frame(frame, bg='#f0f2f5')
        top.pack(fill=tk.X, padx=12)

        tk.Label(top, text='Location Name:', bg='#f0f2f5').grid(row=0, column=0, padx=4)
        self.v_loc_name = tk.StringVar()
        tk.Entry(top, textvariable=self.v_loc_name, width=24).grid(row=0, column=1, padx=4)

        tk.Label(top, text='Type:', bg='#f0f2f5').grid(row=0, column=2, padx=4)
        self.v_loc_type = tk.StringVar(value='gate')
        tk.OptionMenu(top, self.v_loc_type,
                      'gate', 'office', 'floor', 'laser_room', 'warehouse', 'other'
                      ).grid(row=0, column=3, padx=4)

        tk.Button(top, text='Generate QR', command=self._gen_location_qr,
                  bg='#1A2740', fg='white').grid(row=0, column=4, padx=8)

        # Saved locations list
        self.loc_listbox = tk.Listbox(frame, height=8)
        self.loc_listbox.pack(fill=tk.X, padx=12, pady=8)
        self.loc_listbox.bind('<<ListboxSelect>>', self._on_loc_select)

        # Preview
        self.loc_preview = tk.Label(frame, bg='#f0f2f5')
        self.loc_preview.pack(pady=6)

        tk.Button(frame, text='Save QR to Firebase + Download PNG',
                  command=self._save_location_qr,
                  bg='#F77F00', fg='white', padx=10).pack(pady=4)

    def _load_locations(self):
        """Load saved locations from Firestore."""
        try:
            docs = self.fm.get_collection('locations') or []
            self.loc_listbox.delete(0, tk.END)
            self._locations = []
            for doc in docs:
                name = doc.get('name', '')
                loc_type = doc.get('type', '')
                self.loc_listbox.insert(tk.END, f"{name} ({loc_type})")
                self._locations.append(doc)
        except Exception as e:
            print(f'Location load error: {e}')

    def _on_loc_select(self, event):
        sel = self.loc_listbox.curselection()
        if not sel:
            return
        loc = self._locations[sel[0]]
        self.v_loc_name.set(loc.get('name', ''))
        self.v_loc_type.set(loc.get('type', 'gate'))

    def _gen_location_qr(self):
        if not PIL_AVAILABLE:
            messagebox.showerror('Missing', 'Install: pip install qrcode pillow')
            return
        name     = self.v_loc_name.get().strip()
        loc_type = self.v_loc_type.get()
        if not name:
            messagebox.showwarning('Required', 'Enter location name.')
            return
        qr_data = f'LOC:{name.upper().replace(" ", "_")}:{loc_type.upper()}'
        self._current_qr_image = self._make_qr(qr_data, label=name)
        tk_img = ImageTk.PhotoImage(self._current_qr_image.resize((200, 200)))
        self.loc_preview.config(image=tk_img)
        self.loc_preview.image = tk_img

    def _save_location_qr(self):
        if not hasattr(self, '_current_qr_image'):
            messagebox.showwarning('Generate First', 'Generate a QR code first.')
            return
        name     = self.v_loc_name.get().strip()
        loc_type = self.v_loc_type.get()
        # Save to Firestore
        try:
            doc_id = name.lower().replace(' ', '_')
            self.fm.set_document('locations', doc_id, {
                'name': name, 'type': loc_type,
                'qr_data': f'LOC:{name.upper().replace(" ", "_")}:{loc_type.upper()}'
            })
        except Exception as e:
            messagebox.showerror('Firestore', str(e))

        # Download PNG
        path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG', '*.png')],
            initialfile=f'QR_{name.replace(" ", "_")}.png'
        )
        if path:
            self._current_qr_image.save(path)
            messagebox.showinfo('Saved', f'QR saved to {path}')
        self._load_locations()

    # ── Employee ID Card ───────────────────────────────────────────────────────
    def _build_idcard_tab(self, frame):
        tk.Label(frame,
                 text='Select an employee to print / download their ID card with embedded QR code.',
                 bg='#f0f2f5', fg='gray', wraplength=500).pack(pady=6, padx=12, anchor='w')

        top = tk.Frame(frame, bg='#f0f2f5')
        top.pack(fill=tk.X, padx=12)

        tk.Label(top, text='Search Employee:', bg='#f0f2f5').grid(row=0, column=0, padx=4)
        self.v_emp_search = tk.StringVar()
        self.v_emp_search.trace('w', self._filter_employees)
        tk.Entry(top, textvariable=self.v_emp_search, width=28).grid(row=0, column=1, padx=4)

        tk.Button(top, text='Generate ID Card', command=self._gen_id_card,
                  bg='#1A2740', fg='white').grid(row=0, column=2, padx=8)

        self.emp_listbox = tk.Listbox(frame, height=8)
        self.emp_listbox.pack(fill=tk.X, padx=12, pady=8)

        self.id_preview = tk.Label(frame, bg='#f0f2f5')
        self.id_preview.pack(pady=6)

        tk.Button(frame, text='Download ID Card PNG',
                  command=self._download_id_card,
                  bg='#F77F00', fg='white', padx=10).pack(pady=4)

        self._employees = []
        self._load_employees()

    def _load_employees(self):
        try:
            docs = self.fm.get_collection('employees') or []
            self._employees = [d for d in docs if d.get('is_active', True)]
            self._refresh_emp_list(self._employees)
        except Exception as e:
            print(f'Employee load error: {e}')

    def _refresh_emp_list(self, employees):
        self.emp_listbox.delete(0, tk.END)
        for e in employees:
            self.emp_listbox.insert(tk.END,
                f"{e.get('employee_id', '')}  {e.get('name', '')}")

    def _filter_employees(self, *_):
        q = self.v_emp_search.get().lower()
        filtered = [e for e in self._employees
                    if q in e.get('name', '').lower()
                    or q in e.get('employee_id', '').lower()]
        self._refresh_emp_list(filtered)

    def _gen_id_card(self):
        if not PIL_AVAILABLE:
            messagebox.showerror('Missing', 'Install: pip install pillow qrcode')
            return
        sel = self.emp_listbox.curselection()
        if not sel:
            messagebox.showwarning('Select', 'Select an employee first.')
            return
        q = self.v_emp_search.get().lower()
        filtered = [e for e in self._employees
                    if q in e.get('name', '').lower()
                    or q in e.get('employee_id', '').lower()] if q else self._employees
        emp = filtered[sel[0]]

        # Get company name
        try:
            company = self.fm.get_document('settings', 'company') or {}
            company_name = company.get('name', 'Hype Pvt Ltd')
        except Exception:
            company_name = 'Hype Pvt Ltd'

        self._current_id_card = self._make_id_card(emp, company_name)
        tk_img = ImageTk.PhotoImage(self._current_id_card.resize((400, 250)))
        self.id_preview.config(image=tk_img)
        self.id_preview.image = tk_img
        self._current_emp = emp

    def _download_id_card(self):
        if not hasattr(self, '_current_id_card'):
            messagebox.showwarning('Generate First', 'Generate an ID card first.')
            return
        emp_id = self._current_emp.get('employee_id', 'emp')
        path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG', '*.png')],
            initialfile=f'IDCard_{emp_id}.png'
        )
        if path:
            self._current_id_card.save(path)
            messagebox.showinfo('Saved', f'ID Card saved to {path}')

    # ── Helpers ───────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _make_qr(data: str, label: str = '', size: int = 300) -> 'Image.Image':
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color='#1A2740',
                             back_color='white').convert('RGB')

    @staticmethod
    def _make_id_card(emp: dict, company_name: str) -> 'Image.Image':
        w, h = 800, 500
        img  = Image.new('RGB', (w, h), '#1A2740')
        draw = ImageDraw.Draw(img)

        # Orange left strip
        draw.rectangle([0, 0, 12, h], fill='#F77F00')
        # Orange footer strip
        draw.rectangle([0, h - 60, w, h], fill='#F77F00')

        # Company name
        draw.text((30, 30), company_name.upper(), fill='white')
        draw.line([(30, 75), (w - 30, 75)], fill='#F77F00', width=2)

        # Employee info
        name        = emp.get('name', 'N/A')
        emp_id      = emp.get('employee_id', 'N/A')
        designation = emp.get('designation', 'Employee')
        aadhaar     = emp.get('aadhaar', '')
        masked      = f'XXXX-XXXX-{aadhaar[-4:]}' if len(aadhaar) >= 4 else '—'

        draw.text((30, 100), f'Name:        {name}',        fill='white')
        draw.text((30, 135), f'Employee ID: {emp_id}',     fill='white')
        draw.text((30, 170), f'Designation: {designation}', fill='white')
        draw.text((30, 205), f'Aadhaar:     {masked}',      fill='#cccccc')

        # QR code
        qr_content = f'EMP:{emp_id}'
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=5, border=2)
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='#1A2740',
                               back_color='white').convert('RGB').resize((160, 160))
        img.paste(qr_img, (w - 190, 80))

        # Footer
        draw.text((30, h - 40), 'Hype HR Management | Nexuzy Lab', fill='white')
        draw.text((30, h - 20), f'ID: {emp_id}', fill='#F77F00')

        return img
