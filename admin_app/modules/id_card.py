"""
Employee ID Card Generator — Hype HR Management
Redesigned v2: Modern card with gradient header, circular photo, badge ribbon
FIX: company_name fallback chain now checks 6 field names so Security/Supervisor
     users whose employee doc stores the name under a different key still get
     the correct company name on their ID card.
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageFilter
import qrcode, io, os, urllib.request
from utils.firebase_config import get_db, get_bucket
from modules.roles import has_permission

# ── Card dimensions (CR80 business card @ 300 dpi = 1011 x 638)
CARD_W, CARD_H = 1011, 638

# ── Colour palette
C_BG        = "#0d1b2a"
C_HEADER    = "#f77f00"
C_ACCENT    = "#f0c040"
C_WHITE     = "#FFFFFF"
C_MUTED     = "#b0c4d8"
C_DARK      = "#07111c"
C_STRIPE    = "#1a2f45"


def _rgb(hex_: str):
    h = hex_.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _load_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf"  if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)


def _circle_photo(photo: Image.Image, size: int) -> Image.Image:
    photo = photo.resize((size, size), Image.LANCZOS)
    mask  = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(photo, (0, 0), mask)
    return result


def _resolve_company_name(emp: dict, company_info: dict) -> str:
    """
    FIX: When Admin adds a Security Guard or Supervisor their employee doc
    may not have 'company_name' set (only 'company', 'org', etc.).
    Try every known field name before falling back to company_info from settings.
    """
    # 1. Try employee doc first (custom override per card)
    for key in ("company_name", "company", "org", "organisation", "organization"):
        val = emp.get(key, "").strip()
        if val:
            return val
    # 2. Fall back to company settings document
    for key in ("company_name", "name", "company"):
        val = company_info.get(key, "").strip()
        if val:
            return val
    return "HYPE PVT LTD"


def generate_id_card_image(emp: dict, company_info: dict) -> Image.Image:
    """Return a high-quality PIL Image of the ID card (1011 x 638 px)."""
    img  = Image.new("RGB", (CARD_W, CARD_H), _rgb(C_BG))
    draw = ImageDraw.Draw(img)

    # ── 1. Header bar
    HEADER_H = 150
    draw.rectangle([0, 0, CARD_W, HEADER_H], fill=_rgb(C_HEADER))
    draw.polygon([(CARD_W - 320, 0), (CARD_W, 0),
                  (CARD_W, HEADER_H), (CARD_W - 450, HEADER_H)],
                 fill=_rgb(C_DARK))

    # FIX: use _resolve_company_name instead of bare .get()
    company_name = _resolve_company_name(emp, company_info)
    f_company = _load_font(52, bold=True)
    draw.text((36, 22), company_name.upper(), font=f_company, fill=_rgb(C_WHITE))
    f_tagline = _load_font(22)
    addr = company_info.get("address1", company_info.get("address", ""))
    if addr:
        draw.text((38, 90), addr[:60], font=f_tagline, fill=_rgb(C_MUTED))
    f_badge = _load_font(20, bold=True)
    draw.text((CARD_W - 300, 55), "EMPLOYEE", font=f_badge, fill=_rgb(C_ACCENT))
    draw.text((CARD_W - 300, 82), "ID CARD",  font=f_badge, fill=_rgb(C_ACCENT))

    # ── 2. Photo circle
    PHOTO_SIZE = 180
    PHOTO_X    = 36
    PHOTO_Y    = HEADER_H + 30

    ring_pad = 8
    draw.ellipse([
        PHOTO_X - ring_pad, PHOTO_Y - ring_pad,
        PHOTO_X + PHOTO_SIZE + ring_pad, PHOTO_Y + PHOTO_SIZE + ring_pad
    ], fill=_rgb(C_HEADER))

    photo_loaded = False
    photo_url = emp.get("photo_url", "")
    if photo_url:
        try:
            with urllib.request.urlopen(photo_url, timeout=6) as resp:
                pdata = resp.read()
            raw_photo = Image.open(io.BytesIO(pdata)).convert("RGB")
            circ      = _circle_photo(raw_photo, PHOTO_SIZE)
            img.paste(circ, (PHOTO_X, PHOTO_Y), circ)
            photo_loaded = True
        except Exception:
            pass

    if not photo_loaded:
        draw.ellipse([PHOTO_X, PHOTO_Y,
                      PHOTO_X + PHOTO_SIZE, PHOTO_Y + PHOTO_SIZE],
                     fill=_rgb(C_STRIPE))
        initials = "".join(w[0].upper() for w in emp.get("name", "?").split()[:2])
        f_init   = _load_font(64, bold=True)
        draw.text((PHOTO_X + PHOTO_SIZE // 2 - 36,
                   PHOTO_Y + PHOTO_SIZE // 2 - 38),
                  initials, font=f_init, fill=_rgb(C_ACCENT))

    # ── 3. Employee details
    DX     = PHOTO_X + PHOTO_SIZE + 40
    f_name = _load_font(50, bold=True)
    f_info = _load_font(26)
    f_lbl  = _load_font(22)
    f_bold = _load_font(26, bold=True)

    name_y = PHOTO_Y + 8
    draw.text((DX, name_y), emp.get("name", "").upper(),
              font=f_name, fill=_rgb(C_WHITE))

    ID_Y = name_y + 62
    id_text = f"  {emp.get('employee_id', '')}  "
    bbox = draw.textbbox((0, 0), id_text, font=f_bold)
    badge_w = bbox[2] - bbox[0] + 20
    _draw_rounded_rect(draw, [DX, ID_Y, DX + badge_w, ID_Y + 36], radius=10,
                       fill=_rgb(C_HEADER))
    draw.text((DX + 10, ID_Y + 4), id_text.strip(), font=f_bold, fill=_rgb(C_WHITE))

    rows_y = ID_Y + 50
    for icon, value in [
        ("\U0001f4bc", emp.get("designation", "Employee")),
        ("\U0001f3e2", emp.get("department",  "General")),
        ("\U0001f4f1", emp.get("mobile",      "")),
        ("\U0001f4c5", "DOJ: " + emp.get("date_of_join", "")),
    ]:
        if value and value.strip():
            draw.text((DX, rows_y), f"{icon}  {value}",
                      font=f_info, fill=_rgb(C_MUTED))
            rows_y += 38

    # ── 4. Separator
    LINE_Y = CARD_H - 120
    draw.rectangle([30, LINE_Y, CARD_W - 30, LINE_Y + 2], fill=_rgb(C_STRIPE))

    # ── 5. QR code
    # FIX: QR now encodes HYPE_EMP|<id>|<name>|<username>|<company>
    # so Android SecurityScanActivity can parse it correctly.
    QR_SIZE = 160
    QR_X    = CARD_W - QR_SIZE - 36
    QR_Y    = CARD_H - QR_SIZE - 70

    emp_id       = emp.get("employee_id", "UNKNOWN")
    emp_name_qr  = emp.get("name", "").replace("|", " ")
    username_qr  = emp.get("username",
                   emp.get("email", "").split("@")[0]).replace("|", " ")
    company_qr   = company_name.lower().replace(" ", ".").replace("|", "")
    qr_data = f"HYPE_EMP|{emp_id}|{emp_name_qr}|{username_qr}|{company_qr}"

    qr = qrcode.QRCode(box_size=6, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="white",
                            back_color=C_BG).convert("RGB")
    qr_img = qr_img.resize((QR_SIZE, QR_SIZE), Image.LANCZOS)
    img.paste(qr_img, (QR_X, QR_Y))

    f_scan = _load_font(18)
    draw.text((QR_X + 28, QR_Y + QR_SIZE + 4),
              "Scan to verify", font=f_scan, fill=_rgb(C_MUTED))

    # ── 6. Footer
    FOOT_Y = CARD_H - 48
    draw.rectangle([0, FOOT_Y, CARD_W, CARD_H], fill=_rgb(C_HEADER))
    f_foot = _load_font(20)
    email  = company_info.get("email", "")
    phone  = company_info.get("phone", "")
    web    = company_info.get("website", "")
    foot_parts = []
    if email: foot_parts.append(f"\u2709  {email}")
    if phone: foot_parts.append(f"\U0001f4de  {phone}")
    if web:   foot_parts.append(f"\U0001f310  {web}")
    foot_text = "   |   ".join(foot_parts)
    draw.text((36, FOOT_Y + 12), foot_text, font=f_foot, fill=_rgb(C_WHITE))

    import datetime
    valid_year = datetime.datetime.now().year + 1
    draw.text((CARD_W - 200, FOOT_Y + 12),
              f"Valid till: Dec {valid_year}",
              font=f_foot, fill=_rgb(C_WHITE))

    return img


# ───────────────────────────────────────────────────────────────────────
class IdCardModule:
    def __init__(self, parent_frame, current_user):
        self.parent       = parent_frame
        self.current_user = current_user
        self.role         = current_user.get("role", "hr")
        self.db           = get_db()
        self._build_ui()
        self._load_employees()

    def _build_ui(self):
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="\U0001fa9a Employee ID Card Generator",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)

        if has_permission(self.role, "id_card"):
            tk.Button(top, text="\U0001f5a8 Generate Selected",
                      bg="#f77f00", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=12, pady=5, cursor="hand2",
                      command=self._generate_selected).pack(side="right", padx=5)
            tk.Button(top, text="\U0001f4e6 Generate All",
                      bg="#2980b9", fg="white", font=("Arial", 9, "bold"),
                      relief="flat", padx=12, pady=5, cursor="hand2",
                      command=self._generate_all).pack(side="right", padx=5)

        sf = tk.Frame(self.parent, bg="#0d1b2a")
        sf.pack(fill="x", padx=10, pady=5)
        tk.Label(sf, text="Search:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(sf, textvariable=self.search_var, width=25, bg="#1a2740",
                 fg="white", insertbackground="white", relief="flat", bd=4).pack(side="left", padx=5)
        tk.Button(sf, text="Search", bg="#1e6f9f", fg="white", relief="flat",
                  command=self._search).pack(side="left", padx=3)
        tk.Button(sf, text="All", bg="#444", fg="white", relief="flat",
                  command=self._load_employees).pack(side="left", padx=3)

        cols = ("Employee ID", "Name", "Designation", "Department", "Photo", "Status")
        self.tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=18)
        for col, w in [("Employee ID", 110), ("Name", 180), ("Designation", 150),
                       ("Department", 120), ("Photo", 80), ("Status", 70)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", self._preview_card)
        tk.Label(self.parent,
                 text="Double-click to preview  |  Select multiple with Ctrl+Click",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load_employees(self, query: str = ""):
        for row in self.tree.get_children(): self.tree.delete(row)
        try:
            docs = self.db.collection("employees") \
                          .where("status", "==", "active").stream()
            for doc in docs:
                e    = doc.to_dict()
                name = e.get("name", "")
                if query and query.lower() not in name.lower() \
                        and query.lower() not in e.get("employee_id", "").lower():
                    continue
                has_photo = "\u2705" if e.get("photo_url") else "\u274c"
                self.tree.insert("", "end", iid=e["employee_id"], values=(
                    e["employee_id"], name,
                    e.get("designation", ""),
                    e.get("department",  ""),
                    has_photo,
                    e.get("status", "active").title(),
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
            messagebox.showinfo("Info", "Select at least one employee."); return
        company  = self._get_company_info()
        save_dir = filedialog.askdirectory(title="Choose folder to save ID cards")
        if not save_dir: return
        count = 0
        for emp_id in sel:
            doc = self.db.collection("employees").document(emp_id).get()
            if not doc.exists: continue
            card = generate_id_card_image(doc.to_dict(), company)
            card.save(os.path.join(save_dir, f"IDCard_{emp_id}.png"))
            count += 1
        messagebox.showinfo("Done", f"Saved {count} ID card(s) to:\n{save_dir}")

    def _generate_all(self):
        if not messagebox.askyesno("Confirm", "Generate ID cards for ALL active employees?"):
            return
        company  = self._get_company_info()
        save_dir = filedialog.askdirectory(title="Choose folder")
        if not save_dir: return
        count = 0
        try:
            for doc in self.db.collection("employees") \
                               .where("status", "==", "active").stream():
                emp = doc.to_dict()
                generate_id_card_image(emp, company).save(
                    os.path.join(save_dir, f"IDCard_{emp['employee_id']}.png"))
                count += 1
        except Exception as e:
            messagebox.showerror("Error", str(e))
        messagebox.showinfo("Done", f"Saved {count} ID card(s) to:\n{save_dir}")

    def _preview_card(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        emp_id  = sel[0]
        doc     = self.db.collection("employees").document(emp_id).get()
        if not doc.exists: return
        emp     = doc.to_dict()
        company = self._get_company_info()
        card    = generate_id_card_image(emp, company)

        win = tk.Toplevel(self.parent)
        win.title(f"ID Card Preview — {emp.get('name', '')}")
        win.configure(bg="#0d1b2a")
        win.resizable(False, False)

        preview_w = int(CARD_W * 0.6)
        preview_h = int(CARD_H * 0.6)
        card_small = card.resize((preview_w, preview_h), Image.LANCZOS)
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
                card.save(path, dpi=(300, 300))
                messagebox.showinfo("Saved", f"ID card saved:\n{path}", parent=win)

        tk.Button(win, text="\U0001f4be Save HD PNG",
                  bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=15, pady=6, cursor="hand2",
                  command=save).pack(pady=(0, 15))
