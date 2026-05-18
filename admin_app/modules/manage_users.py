"""
Manage Admin, Security & Supervisor Users — Hype HR Management

USERNAME DOMAIN RULES:
  Every role has a fixed domain suffix. The username is auto-generated
  as  <name_slug>.<domain>  e.g.:

    super_admin  →  admin.hype          (e.g. admin.hype)
    admin        →  admin.hype          (e.g. david.hype)
    hr           →  hr.hype             (e.g. priya.hr.hype)
    ca           →  ca.hype             (e.g. ravi.ca.hype)
    manager      →  manager.hype
    supervisor   →  supervisor.hype
    security     →  security.hype

  Employee Android login uses:  <name>.emp.hype  (handled by employees module)
  Super admin hardcoded:        admin.hype

Fix v3 (this file):
  1. Username field is now AUTO-FILLED based on Display Name + Role domain.
  2. Domain suffix is shown and locked per role — user can only edit the
     name prefix part.
  3. On save, username is re-assembled as  slug.domain  and validated.
  4. Email, Employee ID, company_name, department all saved correctly.
  5. Both admin_users and employees Firestore docs written for Android roles.

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox
from utils.firebase_config import get_db
from modules.roles import get_all_roles, get_role_display
import hashlib

# Roles that also use the Android app — require email
ANDROID_ROLES = {"security", "supervisor", "manager", "hr"}

# Domain suffix per role  ────────────────────────────────────────────
ROLE_DOMAIN = {
    "super_admin": "hype",          # admin.hype
    "admin":       "hype",          # david.hype
    "hr":          "hr.hype",       # priya.hr.hype
    "ca":          "ca.hype",       # ravi.ca.hype
    "manager":     "manager.hype",  # john.manager.hype
    "supervisor":  "supervisor.hype",
    "security":    "security.hype",
}


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _slugify(name: str) -> str:
    """Convert 'Priya Sharma' → 'priya' (first word, lowercase, alphanum only)."""
    first = name.strip().split()[0] if name.strip() else "user"
    return re.sub(r"[^a-z0-9]", "", first.lower()) or "user"


def _build_username(name_slug: str, role: str) -> str:
    domain = ROLE_DOMAIN.get(role, "hype")
    return f"{name_slug}.{domain}"


def _bind_scroll(canvas):
    def _mw(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    def _up(e): canvas.yview_scroll(-1, "units")
    def _dn(e): canvas.yview_scroll(1, "units")
    canvas.bind_all("<MouseWheel>", _mw)
    canvas.bind_all("<Button-4>", _up)
    canvas.bind_all("<Button-5>", _dn)


def _get_company_name(db) -> str:
    try:
        doc = db.collection("settings").document("company").get()
        if doc.exists:
            data = doc.to_dict()
            for key in ("company_name", "name", "company"):
                val = (data.get(key) or "").strip()
                if val:
                    return val
    except Exception:
        pass
    return "Hype Pvt Ltd"


class ManageUsersPanel(tk.Frame):
    """Embedded panel shown inside Settings tab."""

    def __init__(self, parent, current_user):
        super().__init__(parent, bg="#0d1b2a")
        self.current_user = current_user
        self.db = get_db()
        self._build_ui()
        self._load()

    def _build_ui(self):
        bar = tk.Frame(self, bg="#1a2740", pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="👮 Manage Users",
                 font=("Arial", 13, "bold"), bg="#1a2740", fg="#f0c040").pack(side="left", padx=12)
        tk.Button(bar, text="+ Create User", command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bar, text="🔄 Refresh", command=self._load,
                  bg="#555", fg="white", padx=10, relief="flat").pack(side="right", padx=4)

        # Domain legend
        info = tk.Frame(self, bg="#132030", padx=12, pady=8)
        info.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(info, text="🌐  Username Domains:",
                 bg="#132030", fg="#f0c040", font=("Arial", 9, "bold")).pack(anchor="w")
        domains_text = (
            "  admin.hype   →  Super Admin / Admin    │   "
            "hr.hype  →  HR     │   ca.hype  →  CA / Accountant\n"
            "  manager.hype →  Manager               │   "
            "supervisor.hype  →  Supervisor    │   security.hype  →  Security"
        )
        tk.Label(info, text=domains_text,
                 bg="#132030", fg="#aaa", font=("Courier", 8),
                 justify="left").pack(anchor="w")
        tk.Label(info,
                 text="   Employee Android login uses:  john.emp.hype  (auto-assigned when employee is created)",
                 bg="#132030", fg="#27ae60", font=("Arial", 8)).pack(anchor="w")

        cols = ("username", "display_name", "email", "emp_id", "role", "active")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col, lbl, w in [
            ("username",     "Username",     170),
            ("display_name", "Display Name", 150),
            ("email",        "Email",        180),
            ("emp_id",       "Emp ID",        90),
            ("role",         "Role",         110),
            ("active",       "Status",        80),
        ]:
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree.bind("<Double-1>", self._edit_selected)
        tk.Label(self, text="Double-click to edit / reset password",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        self.users = {}
        try:
            for doc in self.db.collection("admin_users").stream():
                u = doc.to_dict()
                self.users[u.get("username", "")] = u
                self.tree.insert("", "end", values=(
                    u.get("username", ""),
                    u.get("display_name", ""),
                    u.get("email", ""),
                    u.get("employee_id", ""),
                    get_role_display(u.get("role", "")),
                    "✅ Active" if u.get("active") else "❌ Inactive",
                ))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _add_dialog(self):
        AdminUserDialog(self, mode="add", on_save=self._load)

    def _edit_selected(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        uname = self.tree.item(sel[0])["values"][0]
        user = self.users.get(uname)
        if user:
            AdminUserDialog(self, mode="edit", user=user, on_save=self._load)


class AdminUserDialog(tk.Toplevel):
    def __init__(self, parent, mode="add", user=None, on_save=None):
        super().__init__(parent)
        self.mode = mode
        self.user = user or {}
        self.on_save = on_save
        self.db = get_db()
        self._company_name = _get_company_name(self.db)
        title = "Create User" if mode == "add" else f"Edit User — {user.get('username', '')}"
        self.title(title)
        self.geometry("520x700")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg="#0d1b2a", highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.frm = tk.Frame(canvas, bg="#0d1b2a", padx=28, pady=20)
        win = canvas.create_window((0, 0), window=self.frm, anchor="nw")
        self.frm.bind("<Configure>",
                      lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        _bind_scroll(canvas)
        self._populate()

    def _populate(self):
        frm = self.frm
        u = self.user

        tk.Label(frm, text="👮 Create / Edit User",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w", pady=(0, 14))

        def lbl_entry(label, key, default="", colour="#ccc"):
            row = tk.Frame(frm, bg="#0d1b2a")
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label + ":", width=22, anchor="w",
                     bg="#0d1b2a", fg=colour).pack(side="left")
            var = tk.StringVar(value=u.get(key, default))
            tk.Entry(row, textvariable=var, width=26,
                     bg="#1e3a5f", fg="white", insertbackground="white",
                     relief="flat", bd=4).pack(side="left")
            return var

        # ── Display Name (triggers username preview) ────────────────────
        self.v_display_name = lbl_entry("Display Name (Full Name)", "display_name")
        self.v_display_name.trace_add("write", self._refresh_username_preview)

        # ── Role dropdown (also triggers username preview) ─────────────
        role_row = tk.Frame(frm, bg="#0d1b2a")
        role_row.pack(fill="x", pady=4)
        tk.Label(role_row, text="Role:", width=22, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_role = tk.StringVar(value=u.get("role", "security"))
        ttk.Combobox(role_row, textvariable=self.v_role,
                     values=get_all_roles(), width=24,
                     state="readonly").pack(side="left")
        self.v_role.trace_add("write", self._refresh_username_preview)
        self.v_role.trace_add("write", self._update_hint)

        self.lbl_hint = tk.Label(frm, text="", bg="#0d1b2a", fg="#aaa",
                                 font=("Arial", 8), wraplength=440, justify="left")
        self.lbl_hint.pack(anchor="w", pady=(0, 6))
        self._update_hint()

        # ── Username — auto-generated, user can tweak prefix only ────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=4)
        uname_row = tk.Frame(frm, bg="#0d1b2a")
        uname_row.pack(fill="x", pady=4)
        tk.Label(uname_row, text="Username (auto):", width=22, anchor="w",
                 bg="#0d1b2a", fg="#f0c040").pack(side="left")

        # Prefix entry box
        self.v_uname_prefix = tk.StringVar()
        tk.Entry(uname_row, textvariable=self.v_uname_prefix, width=14,
                 bg="#1e3a5f", fg="white", insertbackground="white",
                 relief="flat", bd=4).pack(side="left")
        # Domain label (changes with role)
        self.lbl_domain = tk.Label(uname_row, text=".security.hype",
                                   bg="#0d1b2a", fg="#27ae60",
                                   font=("Arial", 10, "bold"))
        self.lbl_domain.pack(side="left", padx=(4, 0))

        tk.Label(frm,
                 text="  ⬆ Prefix auto-filled from name. Edit if you need (e.g. to avoid duplicates).",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", pady=(0, 6))

        # Seed from existing user on edit mode
        if self.mode == "edit":
            existing = u.get("username", "")
            domain   = ROLE_DOMAIN.get(u.get("role", ""), "hype")
            suffix   = "." + domain
            prefix   = existing[: -len(suffix)] if existing.endswith(suffix) else existing
            self.v_uname_prefix.set(prefix)
        self._refresh_username_preview()

        # ── Email ───────────────────────────────────────────────────
        self.v_email = lbl_entry("Email *", "email", colour="#f0c040")
        tk.Label(frm, text="  ⬆ Required for Security/Supervisor Android login",
                 bg="#0d1b2a", fg="#e74c3c", font=("Arial", 8)).pack(anchor="w", pady=(0, 4))

        # ── Employee ID ──────────────────────────────────────────────
        self.v_emp_id = lbl_entry("Employee ID", "employee_id")
        tk.Label(frm, text="  ⬆ e.g. EMP-0025  (ID card, QR code, attendance)",
                 bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w", pady=(0, 4))

        # ── Department ───────────────────────────────────────────────
        self.v_department = lbl_entry("Department", "department", default="Security")

        # ── Company (auto, read-only display) ──────────────────────────
        cname_row = tk.Frame(frm, bg="#0d1b2a")
        cname_row.pack(fill="x", pady=4)
        tk.Label(cname_row, text="Company (auto):", width=22, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        tk.Label(cname_row, text=self._company_name,
                 bg="#0d1b2a", fg="#27ae60", font=("Arial", 9, "bold")).pack(side="left")

        # ── Password ───────────────────────────────────────────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        tk.Label(frm, text="Password", fg="#f0c040", bg="#0d1b2a",
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 4))
        if self.mode == "add":
            self.v_password = lbl_entry("Password", "password")
            self.v_confirm  = lbl_entry("Confirm Password", "confirm")
            tk.Label(frm, text="Min 6 chars. Share Username + Password with user.",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w")
        else:
            tk.Label(frm, text="Leave blank to keep existing password.",
                     bg="#0d1b2a", fg="#aaa", font=("Arial", 8)).pack(anchor="w")
            self.v_password = lbl_entry("New Password", "new_pass")
            self.v_confirm  = lbl_entry("Confirm Password", "confirm")

        # ── Active toggle ───────────────────────────────────────────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        act_row = tk.Frame(frm, bg="#0d1b2a")
        act_row.pack(fill="x", pady=4)
        tk.Label(act_row, text="Active:", width=22, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_active = tk.BooleanVar(value=self.user.get("active", True))
        tk.Checkbutton(act_row, variable=self.v_active, bg="#0d1b2a",
                       fg="white", selectcolor="#1e3a5f",
                       activebackground="#0d1b2a").pack(side="left")

        # ── Save / Cancel ───────────────────────────────────────────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        br = tk.Frame(frm, bg="#0d1b2a")
        br.pack(fill="x", pady=4)
        tk.Button(br, text="✔ Save User", command=self._save,
                  bg="#f77f00", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(br, text="Cancel", command=self.destroy,
                  padx=14, relief="flat").pack(side="left")

    # ---------------------------------------------------------------- helpers
    def _refresh_username_preview(self, *_):
        """Auto-fill username prefix from Display Name and update domain label."""
        role   = self.v_role.get()
        domain = ROLE_DOMAIN.get(role, "hype")
        # Only auto-fill prefix in add mode when user hasn't manually changed it
        if self.mode == "add":
            slug = _slugify(self.v_display_name.get())
            self.v_uname_prefix.set(slug)
        self.lbl_domain.config(text=f".{domain}")

    def _update_hint(self, *_):
        role = self.v_role.get()
        domain = ROLE_DOMAIN.get(role, "hype")
        hints = {
            "super_admin": f"Full access. Login: name.{domain}",
            "admin":       f"Full access (no super admin create). Login: name.{domain}",
            "hr":          f"Employees, Attendance, Salary, ID cards. Login: name.{domain}",
            "ca":          f"Salary, Bonus, Raise, Reports. Login: name.{domain}",
            "manager":     f"Dashboard, Attendance, Employees. Login: name.{domain}",
            "supervisor":  f"🛡️ Can scan employee QR on Android. Login: name.{domain}",
            "security":    f"🛡️ Android QR scanner only — mark IN/OUT. Login: name.{domain}",
        }
        colour = "#f0c040" if role in ("security", "supervisor") else "#aaa"
        self.lbl_hint.config(text=f"  ℹ️  {hints.get(role, '')}", fg=colour)

    # ----------------------------------------------------------------- save
    def _save(self):
        display_name = self.v_display_name.get().strip()
        role         = self.v_role.get()
        prefix       = re.sub(r"[^a-z0-9]", "",
                              self.v_uname_prefix.get().strip().lower())
        domain       = ROLE_DOMAIN.get(role, "hype")
        username     = f"{prefix}.{domain}" if prefix else ""
        email        = self.v_email.get().strip().lower()
        emp_id       = self.v_emp_id.get().strip().upper()
        department   = self.v_department.get().strip() or "Security"
        password     = self.v_password.get().strip()
        confirm      = self.v_confirm.get().strip()
        active       = self.v_active.get()

        # Validate
        if not display_name:
            messagebox.showerror("Error", "Display Name is required.", parent=self)
            return
        if not username:
            messagebox.showerror("Error",
                "Username prefix is empty. Please enter at least the person's first name.",
                parent=self)
            return

        if role in ANDROID_ROLES and not email:
            messagebox.showerror("Email Required",
                f"Role '{role}' uses the Android app.\n"
                "Enter an Email so they can sign in on Android.",
                parent=self)
            return

        if role in ("security", "supervisor") and not emp_id:
            messagebox.showerror("Employee ID Required",
                "Security/Supervisor need an Employee ID for ID card and QR.",
                parent=self)
            return

        # Password
        if self.mode == "add":
            if len(password) < 6:
                messagebox.showerror("Error", "Password must be ≥6 characters.", parent=self)
                return
            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match.", parent=self)
                return
            pw_hash = _hash(password)
        else:
            if password:
                if len(password) < 6:
                    messagebox.showerror("Error", "Password must be ≥6 characters.", parent=self)
                    return
                if password != confirm:
                    messagebox.showerror("Error", "Passwords do not match.", parent=self)
                    return
                pw_hash = _hash(password)
            else:
                pw_hash = self.user.get("password_hash", "")

        # Write admin_users doc
        admin_doc = {
            "username":             username,
            "display_name":         display_name,
            "name":                 display_name,
            "email":                email,
            "employee_id":          emp_id,
            "department":           department,
            "role":                 role,
            "password_hash":        pw_hash,
            "active":               active,
            "must_change_password": False,
            "company_name":         self._company_name,
            "company":              self._company_name,
        }
        try:
            self.db.collection("admin_users").document(username).set(admin_doc)
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to save admin user:\n{ex}", parent=self)
            return

        # Write employees doc (Android post-auth lookup)
        if role in ANDROID_ROLES and emp_id:
            emp_doc = {
                "name":          display_name,
                "employee_id":   emp_id,
                "role":          role,
                "email":         email,
                "username":      username,
                "department":    department,
                "designation":   get_role_display(role),
                "company_name":  self._company_name,
                "company":       self._company_name,
                "status":        "active" if active else "inactive",
                "is_management": True,
                "photo_url":     "",
            }
            try:
                self.db.collection("employees").document(emp_id).set(emp_doc)
            except Exception as ex:
                messagebox.showwarning("Partial Save",
                    f"admin_users saved but employees doc failed:\n{ex}",
                    parent=self)

        # Success message
        msg = (
            f"✅ User saved!\n"
            f"Name:     {display_name}\n"
            f"Username: {username}\n"
            f"Role:     {get_role_display(role)}\n"
            f"Company:  {self._company_name}\n"
        )
        if self.mode == "add" and role in ANDROID_ROLES:
            msg += (
                f"\n📱 Android Login Credentials:"
                f"\n  Email:    {email}"
                f"\n  Password: {password}"
                f"\n\n⚠️ Firebase Console → Authentication → Add User"
                f"\n  with the same Email + Password to activate Android login."
            )
        elif self.mode == "add":
            msg += f"Password: {password}"

        messagebox.showinfo("User Saved", msg, parent=self)
        if self.on_save:
            self.on_save()
        self.destroy()
