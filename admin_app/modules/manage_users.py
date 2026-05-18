"""
Manage Admin, Security & Supervisor Users — Hype HR Management

FIX v4:
  Added DELETE USER:
  - Removes admin_users Firestore document.
  - Removes employees docs (both uid-keyed and emp_id-keyed).
  - Deletes Firebase Auth account (if auth_uid present).
  - Cannot delete yourself (logged-in user).
  - Cannot delete super_admin unless current user is also super_admin.
  - Shows confirmation dialog listing exactly what will be deleted.

Previous fixes:
  v3: Auto-create Firebase Auth, employees doc with auth_uid key,
      password_hash + display_name in employees doc.
  v2: Email field, Employee ID, employees doc, Android credentials popup.

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from utils.firebase_config import get_db
from modules.roles import get_all_roles, get_role_display
import hashlib

try:
    from firebase_admin import auth as fb_auth
except ImportError:
    fb_auth = None

ANDROID_ROLES = {"security", "supervisor", "manager", "hr"}


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _create_or_get_firebase_auth(email: str, password: str, display_name: str) -> str:
    if fb_auth is None:
        return None
    if not email:
        return None
    try:
        existing = fb_auth.get_user_by_email(email)
        if password:
            fb_auth.update_user(existing.uid, password=password, display_name=display_name)
        return existing.uid
    except fb_auth.UserNotFoundError:
        pass
    user = fb_auth.create_user(
        email=email,
        password=password,
        display_name=display_name,
        email_verified=False,
    )
    return user.uid


def _delete_firebase_auth(uid: str):
    """Delete a Firebase Auth account by UID. Silently ignores errors."""
    if fb_auth is None or not uid:
        return
    try:
        fb_auth.delete_user(uid)
    except Exception:
        pass


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
        tk.Label(bar, text="\U0001f46e Manage Admin, Security & Supervisor Users",
                 font=("Arial", 13, "bold"), bg="#1a2740", fg="#f0c040").pack(side="left", padx=12)

        # Buttons right-to-left
        tk.Button(bar, text="+ Create User", command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bar, text="\U0001f5d1 Delete User", command=self._delete_user,
                  bg="#8b0000", fg="white", padx=10, relief="flat",
                  font=("Arial", 9, "bold"), pady=5, cursor="hand2").pack(side="right", padx=4)
        tk.Button(bar, text="\U0001f504 Refresh", command=self._load,
                  bg="#555", fg="white", padx=10, relief="flat").pack(side="right", padx=4)

        info = tk.Frame(self, bg="#132030", padx=12, pady=8)
        info.pack(fill="x", padx=6, pady=(4, 0))
        sdk_status = "\u2705 firebase_admin ready" if fb_auth else "\u26a0\ufe0f firebase_admin not installed \u2014 Auth auto-create/delete disabled"
        sdk_color  = "#27ae60" if fb_auth else "#e74c3c"
        tk.Label(info,
                 text="\u2139\ufe0f  Security / Supervisor / Manager / HR \u2192 Android app (Email + Password).",
                 bg="#132030", fg="#f0c040", font=("Arial", 9)).pack(anchor="w")
        tk.Label(info,
                 text="    Firebase Auth account is created/deleted AUTOMATICALLY on save/delete.",
                 bg="#132030", fg="#27ae60", font=("Arial", 8)).pack(anchor="w")
        tk.Label(info, text=f"    {sdk_status}",
                 bg="#132030", fg=sdk_color, font=("Arial", 8)).pack(anchor="w")

        cols = ("username", "display_name", "email", "emp_id", "role", "active", "auth_uid")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col, lbl, w in [
            ("username",     "Username",     120),
            ("display_name", "Display Name", 140),
            ("email",        "Email",        170),
            ("emp_id",       "Emp ID",        90),
            ("role",         "Role",         110),
            ("active",       "Status",        80),
            ("auth_uid",     "Firebase UID", 130),
        ]:
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree.bind("<Double-1>", self._edit_selected)
        tk.Label(self,
                 text="Double-click to edit / reset password  \u2502  Select row \u2192 \U0001f5d1 Delete User",
                 bg="#0d1b2a", fg="#555", font=("Arial", 8)).pack(anchor="w", padx=10)

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        self.users = {}
        try:
            for doc in self.db.collection("admin_users").stream():
                u = doc.to_dict()
                self.users[u.get("username", "")] = u
                auth_uid = u.get("auth_uid", "")
                uid_disp = (auth_uid[:14] + "\u2026") if len(auth_uid) > 14 else auth_uid
                self.tree.insert("", "end", values=(
                    u.get("username", ""),
                    u.get("display_name", ""),
                    u.get("email", ""),
                    u.get("employee_id", ""),
                    get_role_display(u.get("role", "")),
                    "\u2705 Active" if u.get("active") else "\u274c Inactive",
                    uid_disp or "(none)",
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

    # ---------------------------------------------------------------- DELETE
    def _delete_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select User", "Please select a user to delete.", parent=self)
            return

        uname = self.tree.item(sel[0])["values"][0]
        user  = self.users.get(uname)
        if not user:
            return

        display_name = user.get("display_name", uname)
        role         = user.get("role", "")
        auth_uid     = user.get("auth_uid", "")
        emp_id       = user.get("employee_id", "")
        current_un   = self.current_user.get("username", "") if self.current_user else ""
        current_role = self.current_user.get("role", "")    if self.current_user else ""

        # ─ Guard: cannot delete yourself
        if uname == current_un:
            messagebox.showwarning(
                "Cannot Delete",
                "You cannot delete your own account while logged in.",
                parent=self)
            return

        # ─ Guard: only super_admin can delete other super_admins
        if role == "super_admin" and current_role != "super_admin":
            messagebox.showwarning(
                "Permission Denied",
                "Only a Super Admin can delete another Super Admin account.",
                parent=self)
            return

        # ─ Build what-will-be-deleted summary
        will_delete = [
            f"  \u2022 admin_users/{uname}  (Python app login)",
        ]
        if role in ANDROID_ROLES:
            if auth_uid:
                will_delete.append(f"  \u2022 employees/{auth_uid}  (Android profile doc)")
            if emp_id:
                will_delete.append(f"  \u2022 employees/{emp_id}  (QR / ID card doc)")
            if auth_uid and fb_auth:
                will_delete.append(f"  \u2022 Firebase Auth account  ({user.get('email','')})") 
            elif auth_uid and not fb_auth:
                will_delete.append(f"  \u2022 Firebase Auth: \u26a0\ufe0f firebase_admin not installed \u2014 Auth account NOT deleted")

        confirm_msg = (
            f"Permanently delete user:\n"
            f"  {display_name}  ({uname})  \u2014  {get_role_display(role)}\n\n"
            f"This will remove:\n"
            + "\n".join(will_delete) +
            f"\n\n\u26a0\ufe0f  This CANNOT be undone."
        )

        if not messagebox.askyesno("Confirm Delete", confirm_msg,
                                   icon="warning", parent=self):
            return

        errors = []

        # ─ 1. Delete admin_users doc
        try:
            self.db.collection("admin_users").document(uname).delete()
        except Exception as ex:
            errors.append(f"admin_users: {ex}")

        # ─ 2. Delete employees docs (uid-keyed + emp_id-keyed)
        if role in ANDROID_ROLES:
            for key in {auth_uid, emp_id} - {""}:
                try:
                    self.db.collection("employees").document(key).delete()
                except Exception as ex:
                    errors.append(f"employees/{key}: {ex}")

        # ─ 3. Delete Firebase Auth account
        if auth_uid:
            try:
                _delete_firebase_auth(auth_uid)
            except Exception as ex:
                errors.append(f"Firebase Auth: {ex}")

        # ─ Result
        self._load()
        if errors:
            messagebox.showwarning(
                "Deleted with warnings",
                f"{display_name} deleted.\nSome steps had errors:\n" + "\n".join(errors),
                parent=self)
        else:
            messagebox.showinfo(
                "\u2705 Deleted",
                f"{display_name} ({uname}) completely removed.",
                parent=self)


class AdminUserDialog(tk.Toplevel):
    def __init__(self, parent, mode="add", user=None, on_save=None):
        super().__init__(parent)
        self.mode = mode
        self.user = user or {}
        self.on_save = on_save
        self.db = get_db()
        self._company_name = _get_company_name(self.db)
        self.title("Create User" if mode == "add" else f"Edit User \u2014 {user.get('username', '')}")
        self.geometry("500x680")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

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
        tk.Label(frm, text="\U0001f46e Admin / Security / Supervisor User",
                 font=("Arial", 13, "bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w", pady=(0, 14))

        if self.mode == "edit":
            existing_uid = u.get("auth_uid", "")
            uid_text  = f"Firebase UID: {existing_uid}" if existing_uid else "Firebase UID: (not created yet)"
            uid_color = "#27ae60" if existing_uid else "#e74c3c"
            tk.Label(frm, text=uid_text, bg="#0d1b2a", fg=uid_color,
                     font=("Arial", 8)).pack(anchor="w", pady=(0, 8))

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

        self.v_username     = row_field("Username",            "username")
        self.v_display_name = row_field("Display Name (Name)", "display_name")
        self.v_email        = row_field("Email *",              "email",  colour="#f0c040")
        tk.Label(frm, text="  \u2b06 Required for Android login. Firebase Auth auto-created on Save.",
                 bg="#0d1b2a", fg="#27ae60", font=("Arial", 8)).pack(anchor="w", pady=(0, 4))

        self.v_emp_id     = row_field("Employee ID",  "employee_id")
        tk.Label(frm, text="  \u2b06 e.g. EMP-0025  \u2014 used for ID card, QR, attendance",
                 bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w", pady=(0, 4))
        self.v_department = row_field("Department",   "department", default="Security")

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

        cname_row = tk.Frame(frm, bg="#0d1b2a")
        cname_row.pack(fill="x", pady=4)
        tk.Label(cname_row, text="Company:", width=20, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        tk.Label(cname_row, text=self._company_name, bg="#0d1b2a",
                 fg="#27ae60", font=("Arial", 9, "bold")).pack(side="left")

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        tk.Label(frm, text="Password", fg="#f0c040", bg="#0d1b2a",
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 4))

        if self.mode == "add":
            self.v_password = row_field("Password",         "password")
            self.v_confirm  = row_field("Confirm Password", "confirm")
            tk.Label(frm, text="Min 6 chars. Firebase Auth account auto-created on Save.",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial", 8)).pack(anchor="w")
        else:
            tk.Label(frm, text="Leave blank to keep existing password.",
                     bg="#0d1b2a", fg="#aaa", font=("Arial", 8)).pack(anchor="w")
            self.v_password = row_field("New Password",     "new_pass")
            self.v_confirm  = row_field("Confirm Password", "confirm")

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        act_row = tk.Frame(frm, bg="#0d1b2a")
        act_row.pack(fill="x", pady=4)
        tk.Label(act_row, text="Active:", width=20, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_active = tk.BooleanVar(value=u.get("active", True))
        tk.Checkbutton(act_row, variable=self.v_active, bg="#0d1b2a",
                       fg="white", selectcolor="#1e3a5f",
                       activebackground="#0d1b2a").pack(side="left")

        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        br = tk.Frame(frm, bg="#0d1b2a")
        br.pack(fill="x", pady=4)
        tk.Button(br, text="\u2714 Save User", command=self._save,
                  bg="#f77f00", fg="white", font=("Arial", 10, "bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(br, text="Cancel", command=self.destroy,
                  padx=14, relief="flat").pack(side="left")

    def _update_hint(self, *_):
        role = self.v_role.get()
        hints = {
            "super_admin": "Full access. Python admin app only.",
            "admin":       "Full access except Super Admin. Python admin app only.",
            "hr":          "\U0001f4f1 Android app. Employees, Attendance, Salary, ID cards.",
            "ca":          "Salary, Bonus, Raise, Reports.",
            "manager":     "\U0001f4f1 Android app. Dashboard, Attendance, Employees, Security.",
            "supervisor":  "\U0001f6e1\ufe0f Android QR scanner + view attendance/employees.",
            "security":    "\U0001f6e1\ufe0f Android QR scanner ONLY \u2014 marks IN/OUT for employees.",
        }
        colour = "#f0c040" if role in ANDROID_ROLES else "#aaa"
        self.lbl_hint.config(text=f"  \u2139\ufe0f  {hints.get(role, '')}", fg=colour)

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

        if not username or not display_name:
            messagebox.showerror("Error", "Username and Display Name are required.", parent=self)
            return
        if role in ANDROID_ROLES and not email:
            messagebox.showerror(
                "Email Required",
                f"Role '{role}' uses the Android app.\n"
                "You MUST enter an Email so they can sign in on Android.",
                parent=self)
            return
        if role in ("security", "supervisor") and not emp_id:
            messagebox.showerror(
                "Employee ID Required",
                "Security / Supervisor users need an Employee ID\n"
                "for ID card and QR code generation.",
                parent=self)
            return

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
                pw_hash  = self.user.get("password_hash", "")
                password = ""

        auth_uid = self.user.get("auth_uid", "")
        firebase_error   = None
        firebase_created = False

        if role in ANDROID_ROLES and email:
            if fb_auth is None:
                firebase_error = (
                    "firebase_admin not installed.\n"
                    "Install: pip install firebase-admin\n"
                    "SHA-256 fallback auth still works on Android."
                )
            else:
                try:
                    uid = _create_or_get_firebase_auth(
                        email, password if password else None, display_name)
                    if uid:
                        auth_uid = uid
                        firebase_created = True
                except Exception as ex:
                    firebase_error = str(ex)

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
            "auth_uid":             auth_uid,
        }
        try:
            self.db.collection("admin_users").document(username).set(admin_doc)
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to save admin user:\n{ex}", parent=self)
            return

        if role in ANDROID_ROLES:
            emp_doc = {
                "name":                 display_name,
                "display_name":         display_name,
                "employee_id":          emp_id,
                "role":                 role,
                "email":                email,
                "username":             username,
                "department":           department,
                "designation":          get_role_display(role),
                "company_name":         self._company_name,
                "company":              self._company_name,
                "status":               "active" if active else "inactive",
                "is_management":        True,
                "photo_url":            "",
                "password_hash":        pw_hash,
                "must_change_password": True,
            }
            if auth_uid:
                emp_doc["uid"] = auth_uid
            try:
                primary_key = auth_uid if auth_uid else emp_id
                self.db.collection("employees").document(primary_key).set(emp_doc)
                if auth_uid and emp_id and auth_uid != emp_id:
                    self.db.collection("employees").document(emp_id).set(emp_doc)
            except Exception as ex:
                messagebox.showwarning(
                    "Partial Save",
                    f"Saved to admin_users but employees doc failed:\n{ex}\n\n"
                    "Android login may not work. Fix Firestore permissions.",
                    parent=self)

        msg = f"\u2705 User '{display_name}' saved!\nRole: {get_role_display(role)}\nCompany: {self._company_name}\n"
        if role in ANDROID_ROLES and self.mode == "add":
            if firebase_created:
                msg += (
                    f"\n\U0001f4f1 Android Login:\n"
                    f"  Email:    {email}\n"
                    f"  Password: {password}\n"
                    f"  Firebase UID: {auth_uid}\n\n"
                    f"\u2705 Firebase Auth account created automatically."
                )
            elif firebase_error:
                msg += (
                    f"\n\U0001f4f1 Android Credentials:\n"
                    f"  Email: {email}  |  Password: {password}\n\n"
                    f"\u26a0\ufe0f Firebase Auth auto-create failed:\n  {firebase_error}\n"
                    f"SHA-256 fallback active \u2014 Android login still works."
                )
        elif self.mode == "add":
            msg += f"Username: {username}\nPassword: {password}"

        messagebox.showinfo("User Saved", msg, parent=self)
        if self.on_save:
            self.on_save()
        self.destroy()
