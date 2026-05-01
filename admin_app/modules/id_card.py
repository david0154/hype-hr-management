"""
Employee ID Card Generator — Hype HR Management
Generates a printable ID card PNG with:
  - Company name + logo placeholder
  - Employee photo (if available from Firebase Storage)
  - Name, Employee ID, Designation, Mobile
  - QR code (employee_id)
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import qrcode, io, os, tempfile, urllib.request
from utils.firebase_config import get_db, get_bucket
from modules.roles import has_permission

CARD_W, CARD_H = 640, 380   # pixels (85mm x 54mm at 200dpi approx)
BG_COLOR       = "#0d1b2a"
ACCENT         = "#f77f00"
TEXT_WHITE     = "#FFFFFF"
TEXT_MUTED     = "#AAAAAA"


def _load_font(size: int, bold: bool = False):
    """Try to load a nice font, fall back to default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()


def generate_id_card_image(emp: dict, company_info: dict) -> Image.Image:
    """Return a PIL Image of the ID card."""
    img  = Image.new("RGB", (CARD_W, CARD_H), color="#0d1b2a")
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, CARD_W, 70], fill=ACCENT)
    company_name = company_info.get("name", "HYPE PVT LTD")
    f_company = _load_font(22, bold=True)
    draw.text((20, 12), company_name.upper(), font=f_company, fill=TEXT_WHITE)
    f_tagline = _load_font(12)
    draw.text((20, 46), company_info.get("address", ""), font=f_tagline, fill=TEXT_WHITE)

    # Employee photo area
    PHOTO_X, PHOTO_Y, PHOTO_SIZE = 20, 90, 120
    draw.rectangle([PHOTO_X, PHOTO_Y, PHOTO_X+PHOTO_SIZE, PHOTO_Y+PHOTO_SIZE],
                   outline="#ffffff", width=2, fill="#1a2740")
    photo_url = emp.get("photo_url", "")
    if photo_url:
        try:
            with urllib.request.urlopen(photo_url, timeout=5) as resp:
                photo_data = resp.read()
            photo = Image.open(io.BytesIO(photo_data)).convert("RGB")
            photo = photo.resize((PHOTO_SIZE, PHOTO_SIZE))
            img.paste(photo, (PHOTO_X, PHOTO_Y))
        except Exception:
            draw.text((PHOTO_X+30, PHOTO_Y+50), "NO\nPHOTO", font=_load_font(14), fill="#555")
    else:
        draw.text((PHOTO_X+30, PHOTO_Y+50), "NO\nPHOTO", font=_load_font(14), fill="#555")

    # Employee details
    DX = PHOTO_X + PHOTO_SIZE + 20
    f_name = _load_font(20, bold=True)
    f_info = _load_font(14)
    f_label= _load_font(11)

    draw.text((DX, 92),  emp.get("name", ""),          font=f_name,  fill=TEXT_WHITE)
    draw.text((DX, 122), f"ID: {emp.get('employee_id','')}",  font=f_info, fill=ACCENT)
    draw.text((DX, 148), emp.get("designation", "Employee"),  font=f_info, fill=TEXT_MUTED)
    draw.text((DX, 172), f"Mob: {emp.get('mobile', '')}",     font=f_info, fill=TEXT_MUTED)
    draw.text((DX, 196), f"Dept: {emp.get('department', 'General')}", font=f_info, fill=TEXT_MUTED)

    # QR code — encodes employee_id
    qr_data = emp.get("employee_id", "UNKNOWN")
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="white", back_color="#0d1b2a").convert("RGB")
    qr_img = qr_img.resize((120, 120))
    img.paste(qr_img, (CARD_W - 140, PHOTO_Y))
    draw.text((CARD_W - 140, PHOTO_Y + 124), "Scan to verify",
              font=_load_font(10), fill=TEXT_MUTED)

    # Footer
    draw.rectangle([0, CARD_H - 36, CARD_W, CARD_H], fill=ACCENT)
    f_footer = _load_font(10)
    draw.text((20, CARD_H - 26),
              f"Email: {company_info.get('email','')}  |  Ph: {company_info.get('phone','')}  |  Valid till: Dec {tk.IntVar().get() or '2026'}",
              font=f_footer, fill=TEXT_WHITE)

    return img


class IdCardModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.role = current_user.get("role", "hr")
        self.db = get_db()
        self._build_ui()
        self._load_employees()

    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="🪪 Employee ID Card Generator",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

        if has_permission(self.role, "id_card"):
            tk.Button(top, text="🖨 Generate Selected", bg="#f77f00", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._generate_selected).pack(side="right", padx=5)
            tk.Button(top, text="📦 Generate All", bg="#2980b9", fg="white",
                      font=("Arial", 10, "bold"), relief="flat", padx=12, pady=5,
                      cursor="hand2", command=self._generate_all).pack(side="right", padx=5)

        # Search
        sf = tk.Frame(self.parent, bg="#0d1b2a")
        sf.pack(fill="x", padx=10, pady=5)
        tk.Label(sf, text="Search:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(sf, textvariable=self.search_var, width=25, bg="#1a2740",
                 fg="white", insertbackground="white", relief="flat", bd=4).pack(
                 side="left", padx=5)
        tk.Button(sf, text="Search", bg="#1e6f9f", fg="white", relief="flat",
                  command=self._search).pack(side="left", padx=3)
        tk.Button(sf, text="All", bg="#444", fg="white", relief="flat",
                  command=self._load_employees).pack(side="left", padx=3)

        cols = ("✓", "Employee ID", "Name", "Designation", "Department", "Status")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=16)
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.column("✓",           width=40,  anchor="center")
        self.tree.column("Employee ID", width=100, anchor="center")
        self.tree.column("Name",        width=160)
        self.tree.column("Designation", width=140)
        self.tree.column("Department",  width=120)
        self.tree.column("Status",      width=80,  anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", self._preview_card)

        tk.Label(self.parent,
                 text="Double-click to preview card | Use checkboxes to select multiple",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load_employees(self, query: str = ""):
        for row in self.tree.get_children(): self.tree.delete(row)
        try:
            docs = self.db.collection("employees").where("status", "==", "active").stream()
            for doc in docs:
                e = doc.to_dict()
                name = e.get("name", "")
                if query and query.lower() not in name.lower() \
                        and query.lower() not in e.get("employee_id", "").lower():
                    continue
                self.tree.insert("", "end", iid=e["employee_id"], values=(
                    "☐", e["employee_id"], name,
                    e.get("designation", "Employee"),
                    e.get("department", "General"),
                    e.get("status", "active").title()
                ))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _search(self):
        self._load_employees(self.search_var.get().strip())

    def _get_company_info(self) -> dict:
        doc = self.db.collection("settings").document("company").get()
        return doc.to_dict() if doc.exists else {}

    def _generate_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Please select at least one employee.")
            return
        company = self._get_company_info()
        save_dir = filedialog.askdirectory(title="Choose folder to save ID cards")
        if not save_dir: return
        count = 0
        for emp_id in sel:
            doc = self.db.collection("employees").document(emp_id).get()
            if not doc.exists: continue
            emp = doc.to_dict()
            card_img = generate_id_card_image(emp, company)
            path = os.path.join(save_dir, f"IDCard_{emp_id}.png")
            card_img.save(path)
            count += 1
        messagebox.showinfo("Done", f"Saved {count} ID card(s) to:\n{save_dir}")

    def _generate_all(self):
        if not messagebox.askyesno("Confirm", "Generate ID cards for ALL active employees?"):
            return
        company = self._get_company_info()
        save_dir = filedialog.askdirectory(title="Choose folder to save ID cards")
        if not save_dir: return
        count = 0
        try:
            docs = self.db.collection("employees").where("status", "==", "active").stream()
            for doc in docs:
                emp = doc.to_dict()
                card_img = generate_id_card_image(emp, company)
                path = os.path.join(save_dir, f"IDCard_{emp['employee_id']}.png")
                card_img.save(path)
                count += 1
        except Exception as e:
            messagebox.showerror("Error", str(e))
        messagebox.showinfo("Done", f"Saved {count} ID card(s) to:\n{save_dir}")

    def _preview_card(self, event):
        sel = self.tree.selection()
        if not sel: return
        emp_id  = sel[0]
        doc     = self.db.collection("employees").document(emp_id).get()
        if not doc.exists: return
        emp     = doc.to_dict()
        company = self._get_company_info()
        card    = generate_id_card_image(emp, company)

        win = tk.Toplevel(self.parent)
        win.title(f"ID Card Preview — {emp.get('name','')}")
        win.configure(bg="#0d1b2a")
        card_small = card.resize((540, 320))
        photo = ImageTk.PhotoImage(card_small)
        lbl   = tk.Label(win, image=photo, bg="#0d1b2a")
        lbl.image = photo
        lbl.pack(padx=20, pady=15)

        def save():
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"IDCard_{emp_id}.png",
                filetypes=[("PNG Image", "*.png")])
            if path:
                card.save(path)
                messagebox.showinfo("Saved", f"ID card saved to:\n{path}", parent=win)

        tk.Button(win, text="💾 Save PNG", bg="#27ae60", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", padx=15, pady=6,
                  cursor="hand2", command=save).pack(pady=(0, 15))
