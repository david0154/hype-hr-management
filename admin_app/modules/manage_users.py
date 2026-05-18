"""
Manage Admin, Security & Supervisor Users — Hype HR Management

FIX v2:
  1. Added Email field — required for Security/Supervisor Android login.
  2. Added Employee ID field — used for ID card generation + QR.
  3. On Save, writes BOTH admin_users doc (Python app login) AND
     employees doc (Android Firebase Auth lookup) in Firestore.
  4. company_name auto-read from settings/company and stored in both docs
     so ID card and Android dashboard show it correctly.
  5. supervisor role added with proper hint + permissions.
  6. After save, shows popup with Android login credentials (email + password).

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from utils.firebase_config import get_db
from modules.roles import get_all_roles, get_role_display
import hashlib

# Roles that use the Android app — need email for Firebase Auth
ANDROID_ROLES = {"security", "supervisor", "manager", "hr"}


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _bind_scroll(canvas):
    def _mw(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    def _up(e): canvas.yview_scroll(-1, "units")
    def _dn(e): canvas.yview_scroll(1, "units")
    canvas.bind_all("<MouseWheel>", _mw)
    canvas.bind_all("<Button-4>", _up)
    canvas.bind_all("<Button-5>", _dn)


def _get_company_name(db) -> str:
    """Read company name from settings/company Firestore document."""
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
        tk.Label(bar, text="👮 Manage Admin, Security & Supervisor Users",
                 font=("Arial", 13, "bold"), bg="#1a2740", fg="#f0c040").pack(side="left", padx=12)
        tk.Button(bar, text="+ Create User", command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bar, text="🔄 Refresh", command=self._load,
                  bg="#555", fg="white", padx=10, relief="flat").pack(side="right", padx=4)

        info = tk.Frame(self, bg="#132030", padx=12, pady=8)
        info.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(info,
                 text="ℹ️  Security / Supervisor → login on Android app (Email + Password).",
                 bg="#132030", fg="#f0c040", font=("Arial", 9)).pack(anchor="w")
        tk.Label(info,
                 text="    Admin / HR / CA → login on this Python admin app (Username + Password).",
                 bg="#132030", fg="#aaa", font=("Arial", 8)).pack(anchor="w")
        tk.Label(info,
                 text="    ⚠️  After saving Security/Supervisor, also create their Firebase Auth account"
                      " in Firebase Console (Auth → Add User) with the same Email + Password.",
                 bg="#132030", fg="#e74c3c", font=("Arial", 8), wraplength=640,
                 justify="left").pack(anchor="w")

        cols = ("username", "display_name", "email", "emp_id", "role", "active")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col, lbl, w in [
            ("username",     "Username",     130),
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
        self.title("Create User" if mode == "add" else f"Edit User — {user.get('username', '')}")
        self.geometry("500x660")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        canvas = tk.Canvas(self, bg="#0d1b2a", highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frm = tk.Frame(canvas, bg="#0d1b2a", padx=28, pady=20)
        win = canvas.create_window((0, 0), window=frm, anchor="nw")
        frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        _bind_scroll(canvas)

        u = self.user
        tk.Label(frm, text="👮 Admin / Security / Supervisor User",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w", pady=(0, 14))

        def row_field(label, key, default="", show="", colour="#ccc"):
            row = tk.Frame(frm, bg="#0d1b2a")
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label + ":", width=20, anchor="w",
                     bg="#0d1b2a", fg=colour).pack(side="left")
            var = tk.StringVar(value=u.get(key, default))
            tk.Entry(row, textvariable=var, width=26, show=show,
                     bg="#1e3a5f", fg="white", insertbackground="white",
                     relief="flat", bd=4).pack(side="left")
            return var

        # ── Basic info ─────────────────────────────────────────────
        self.v_username = row_field("Username", "username")
        self.v_display_name = row_field("Display Name (Name)", "display_name")

        # Email — required for Android roles
        self.v_email = row_field("Email *", "email", colour="#f0c040")
        tk.Label(frm, text="  ⬆ Required for Security/Supervisor Android login",
                 bg="#0d1b2a", fg="#e74c3c", font=("Arial", 8)).pack(anchor="w", pady=(0, 4))

        # Employee ID
        self.v_emp_id = row_field("Employee ID", "employee_id")
        tk.Label(frm, text="  ⬆ e.g. EMP-0025  — used for ID card, QR, attendance",
                 bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w", pady=(0, 4))

        # Department
        self.v_department = row_field("Department", "department", default="Security")

        # ── Role dropdown ─────────────────────────────────────────────
        role_row = tk.Frame(frm, bg="#0d1b2a")
        role_row.pack(fill="x", pady=4)
        tk.Label(role_row, text="Role:", width=20, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_role = tk.StringVar(value=u.get("role", "security"))
        ttk.Combobox(role_row, textvariable=self.v_role,
                     values=get_all_roles(), width=22,
                     state="readonly").pack(side="left")
        self.v_role.trace_add("write", self._update_hint)

        self.lbl_hint = tk.Label(frm, text="", bg="#0d1b2a", fg="#aaa",
                                 font=("Arial", 8), wraplength=420, justify="left")
        self.lbl_hint.pack(anchor="w", pady=(0, 8))
        self._update_hint()

        # ── Company (auto-filled, read-only display) ────────────────────
        cname_row = tk.Frame(frm, bg="#0d1b2a")
        cname_row.pack(fill="x", pady=4)
        tk.Label(cname_row, text="Company:", width=20, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        tk.Label(cname_row, text=self._company_name, bg="#0d1b2a",
                 fg="#27ae60", font=("Arial", 9, "bold")).pack(side="left")

        # ── Password ─────────────────────────────────────────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        tk.Label(frm, text="Password", fg="#f0c040", bg="#0d1b2a",
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 4))

        if self.mode == "add":
            self.v_password = row_field("Password", "password")
            self.v_confirm = row_field("Confirm Password", "confirm")
            tk.Label(frm, text="Min 6 chars. Share Email + Password with the user.",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w")
        else:
            tk.Label(frm, text="Leave blank to keep existing password.",
                     bg="#0d1b2a", fg="#aaa", font=("Arial", 8)).pack(anchor="w")
            self.v_password = row_field("New Password", "new_pass")
            self.v_confirm = row_field("Confirm Password", "confirm")

        # ── Active toggle ─────────────────────────────────────────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        act_row = tk.Frame(frm, bg="#0d1b2a")
        act_row.pack(fill="x", pady=4)
        tk.Label(act_row, text="Active:", width=20, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_active = tk.BooleanVar(value=u.get("active", True))
        tk.Checkbutton(act_row, variable=self.v_active, bg="#0d1b2a",
                       fg="white", selectcolor="#1e3a5f",
                       activebackground="#0d1b2a").pack(side="left")

        # ── Save / Cancel buttons ──────────────────────────────────────
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        br = tk.Frame(frm, bg="#0d1b2a")
        br.pack(fill="x", pady=4)
        tk.Button(br, text="✔ Save User", command=self._save,
                  bg="#f77f00", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(br, text="Cancel", command=self.destroy,
                  padx=14, relief="flat").pack(side="left")

    def _update_hint(self, *_):
        role = self.v_role.get()
        hints = {
            "super_admin": "Full access. Python admin app only.",
            "admin":       "Full access except Super Admin. Python admin app only.",
            "hr":          "Employees, Attendance, Salary, ID cards.",
            "ca":          "Salary, Bonus, Raise, Reports.",
            "manager":     "Dashboard, Attendance, Employees, Security.",
            "supervisor":  "🛡️ Can scan employee QR on Android app + view attendance/employees.",
            "security":    "🛡️ Android QR scanner ONLY — marks IN/OUT for employees without phones.",
        }
        colour = "#f0c040" if role in ("security", "supervisor") else "#aaa"
        self.lbl_hint.config(text=f"  ℹ️  {hints.get(role, '')}", fg=colour)

    # ---------------------------------------------------------------- Save
    def _save(self):
        username     = self.v_username.get().strip().lower()
        display_name = self.v_display_name.get().strip()
        email        = self.v_email.get().strip().lower()
        emp_id       = self.v_emp_id.get().strip().upper()
        department   = self.v_department.get().strip() or "Security"
        role         = self.v_role.get()
        password     = self.v_password.get().strip()
        confirm      = self.v_confirm.get().strip()
        active       = self.v_active.get()

        # ─ Validate basics
        if not username or not display_name:
            messagebox.showerror("Error", "Username and Display Name are required.", parent=self)
            return

        # Email required for Android roles
        if role in ANDROID_ROLES and not email:
            messagebox.showerror(
                "Email Required",
                f"Role '{role}' uses the Android app.\n"
                "You MUST enter an Email so they can sign in on Android.",
                parent=self)
            return

        # Employee ID required for security/supervisor (for QR, ID card)
        if role in ("security", "supervisor") and not emp_id:
            messagebox.showerror(
                "Employee ID Required",
                "Security / Supervisor users need an Employee ID\n"
                "so their ID card and QR code can be generated.",
                parent=self)
            return

        # ─ Password
        if self.mode == "add":
            if len(password) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters.", parent=self)
                return
            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match.", parent=self)
                return
            pw_hash = _hash(password)
        else:
            if password:
                if len(password) < 6:
                    messagebox.showerror("Error", "Password must be at least 6 characters.", parent=self)
                    return
                if password != confirm:
                    messagebox.showerror("Error", "Passwords do not match.", parent=self)
                    return
                pw_hash = _hash(password)
            else:
                pw_hash = self.user.get("password_hash", "")

        # ── 1. Write to admin_users (Python admin app login) ───────────────
        admin_doc = {
            "username":             username,
            "display_name":         display_name,
            "name":                 display_name,   # alias used by some modules
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

        # ── 2. Write to employees (Android Firebase Auth post-login lookup) ──
        # After Firebase Auth succeeds, SecurityLoginActivity calls
        # getEmployeeByUid(uid) which queries the employees collection.
        # We write a doc here (keyed by employee_id) so Android finds it.
        # The 'uid' field will be updated automatically once the guard logs
        # in for the first time via Android (handled in SecurityLoginActivity).
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
                messagebox.showwarning(
                    "Partial Save",
                    f"Saved to admin_users but employees doc failed:\n{ex}\n\n"
                    "Android login may not work. Please fix Firestore permissions.",
                    parent=self)

        # ── Success popup ────────────────────────────────────────────────
        msg = f"✅ User '{display_name}' saved!\n" \
              f"Role: {get_role_display(role)}\n" \
              f"Company: {self._company_name}\n"

        if self.mode == "add" and role in ANDROID_ROLES:
            msg += (
                f"\n📱 Android Login Credentials:"
                f"\n  Email:    {email}"
                f"\n  Password: {password}"
                f"\n\n⚠️ IMPORTANT: Also go to Firebase Console"
                f"\n  Authentication → Users → Add User"
                f"\n  Use the same Email + Password above."
                f"\n  This activates Android sign-in for this user."
            )
        elif self.mode == "add":
            msg += f"Username: {username}\nPassword: {password}"

        messagebox.showinfo("User Saved", msg, parent=self)
        if self.on_save:
            self.on_save()
        self.destroy()
