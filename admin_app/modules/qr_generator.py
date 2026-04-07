"""
QR Code Generator — Hype HR Management
Generates: Location QR (fixed) and Employee ID Card QR
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import qrcode, json
from PIL import Image, ImageTk
from utils.firebase_config import get_db

LOCATION_TYPES = ["Gate", "Office", "Floor", "Laser Room", "Reception", "Warehouse", "Custom"]


class QRGeneratorModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.db = get_db()
        self._last_location_qr = None
        self._last_employee_qr = None
        self._build_ui()

    def _build_ui(self):
        nb = ttk.Notebook(self.parent)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        loc_f = tk.Frame(nb, bg="#0d1b2a"); nb.add(loc_f, text="📍 Location QR")
        emp_f = tk.Frame(nb, bg="#0d1b2a"); nb.add(emp_f, text="👤 Employee QR")
        self._build_location_tab(loc_f)
        self._build_employee_tab(emp_f)

    def _build_location_tab(self, parent):
        tk.Label(parent, text="Generate Location QR Code",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="white").pack(pady=15)
        form = tk.Frame(parent, bg="#0d1b2a"); form.pack()
        tk.Label(form, text="Location Type:", bg="#0d1b2a", fg="#ccc").grid(row=0, column=0, sticky="w", pady=6)
        self.loc_type_var = tk.StringVar(value="Gate")
        ttk.Combobox(form, textvariable=self.loc_type_var, values=LOCATION_TYPES, width=22).grid(row=0, column=1, padx=10)
        tk.Label(form, text="Location Name:", bg="#0d1b2a", fg="#ccc").grid(row=1, column=0, sticky="w", pady=6)
        self.loc_name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.loc_name_var, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=24).grid(row=1, column=1, padx=10)
        tk.Label(form, text="Company ID:", bg="#0d1b2a", fg="#ccc").grid(row=2, column=0, sticky="w", pady=6)
        self.loc_company_var = tk.StringVar(value=self.current_user.get("company", "hype"))
        tk.Entry(form, textvariable=self.loc_company_var, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=24).grid(row=2, column=1, padx=10)
        tk.Button(parent, text="Generate QR Code", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=15, pady=8,
                  cursor="hand2", command=self._gen_location).pack(pady=15)
        self.loc_qr_label = tk.Label(parent, bg="#0d1b2a"); self.loc_qr_label.pack()
        tk.Button(parent, text="💾 Save QR", bg="#1e6f9f", fg="white", relief="flat",
                  command=lambda: self._save("location")).pack(pady=5)

    def _build_employee_tab(self, parent):
        tk.Label(parent, text="Generate Employee ID Card QR",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="white").pack(pady=15)
        form = tk.Frame(parent, bg="#0d1b2a"); form.pack()
        tk.Label(form, text="Employee ID:", bg="#0d1b2a", fg="#ccc").grid(row=0, column=0, sticky="w", pady=6)
        self.emp_qr_id_var = tk.StringVar()
        tk.Entry(form, textvariable=self.emp_qr_id_var, bg="#1e3a5f", fg="white",
                 insertbackground="white", width=24).grid(row=0, column=1, padx=10)
        tk.Button(parent, text="Generate Employee QR", bg="#f77f00", fg="white",
                  font=("Arial", 11, "bold"), relief="flat", padx=15, pady=8,
                  cursor="hand2", command=self._gen_employee).pack(pady=15)
        self.emp_qr_label = tk.Label(parent, bg="#0d1b2a"); self.emp_qr_label.pack()
        self.emp_info_lbl = tk.Label(parent, bg="#0d1b2a", fg="#ccc", font=("Arial", 10))
        self.emp_info_lbl.pack()
        tk.Button(parent, text="💾 Save QR", bg="#1e6f9f", fg="white", relief="flat",
                  command=lambda: self._save("employee")).pack(pady=5)

    def _make_qr(self, data: str) -> Image.Image:
        qr = qrcode.QRCode(version=1, box_size=10, border=4,
                           error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(data); qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").convert("RGB")

    def _gen_location(self):
        data = {"type": "location", "location_type": self.loc_type_var.get(),
                "location_name": self.loc_name_var.get(),
                "company": self.loc_company_var.get()}
        self._last_location_qr = self._make_qr(json.dumps(data))
        img = ImageTk.PhotoImage(self._last_location_qr.resize((240, 240)))
        self.loc_qr_label.config(image=img); self.loc_qr_label.image = img
        get_db().collection("location_qrs").add(data)

    def _gen_employee(self):
        emp_id = self.emp_qr_id_var.get().strip()
        if not emp_id: messagebox.showerror("Error", "Enter Employee ID."); return
        emp_doc = get_db().collection("employees").document(emp_id).get()
        if not emp_doc.exists: messagebox.showerror("Error", f"{emp_id} not found."); return
        emp = emp_doc.to_dict()
        data = {"type": "employee", "employee_id": emp_id,
                "name": emp.get("name", ""), "company": emp.get("company", "hype")}
        self._last_employee_qr = self._make_qr(json.dumps(data))
        img = ImageTk.PhotoImage(self._last_employee_qr.resize((240, 240)))
        self.emp_qr_label.config(image=img); self.emp_qr_label.image = img
        self.emp_info_lbl.config(text=f"{emp.get('name','')} | {emp_id}")

    def _save(self, qr_type: str):
        img = getattr(self, f"_last_{qr_type}_qr", None)
        if img is None: messagebox.showinfo("Info", "Generate a QR first."); return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png")],
                                            initialfile=f"{qr_type}_qr.png")
        if path: img.save(path); messagebox.showinfo("Saved", f"QR saved to {path}")
