"""
Manage Admin & Security Users — Hype HR Management
Admin can create / edit / deactivate admin users from this panel.
Security Guard role: logs into the SAME admin app — only sees Security tab.
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from utils.firebase_config import get_db
from modules.roles import get_all_roles, get_role_display, ROLE_DISPLAY
import hashlib


def _hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def _bind_scroll(canvas):
    def _mw(e): canvas.yview_scroll(int(-1*(e.delta/120)), "units")
    def _up(e): canvas.yview_scroll(-1, "units")
    def _dn(e): canvas.yview_scroll( 1, "units")
    canvas.bind_all("<MouseWheel>", _mw)
    canvas.bind_all("<Button-4>",   _up)
    canvas.bind_all("<Button-5>",   _dn)


class ManageUsersPanel(tk.Frame):
    """
    Embedded panel shown inside Settings tab.
    Lists all admin_users from Firestore, allows create/edit/deactivate.
    """
    def __init__(self, parent, current_user):
        super().__init__(parent, bg="#0d1b2a")
        self.current_user = current_user
        self.db           = get_db()
        self._build_ui()
        self._load()

    def _build_ui(self):
        bar = tk.Frame(self, bg="#1a2740", pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="👮 Manage Admin & Security Users",
                 font=("Arial",13,"bold"), bg="#1a2740", fg="#f0c040").pack(side="left", padx=12)
        tk.Button(bar, text="+ Create User",
                  command=self._add_dialog,
                  bg="#27ae60", fg="white", padx=12, relief="flat",
                  font=("Arial",9,"bold"), pady=5, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bar, text="🔄 Refresh",
                  command=self._load,
                  bg="#555", fg="white", padx=10, relief="flat").pack(side="right", padx=4)

        info = tk.Frame(self, bg="#132030", padx=12, pady=8)
        info.pack(fill="x", padx=6, pady=(4,0))
        tk.Label(info,
                 text="ℹ️  Security Guard role: logs into THIS SAME admin app — only sees the 🛡️ Security tab.",
                 bg="#132030", fg="#f0c040", font=("Arial",9)).pack(anchor="w")
        tk.Label(info,
                 text="    Share the Username + Password you create here with the security guard.",
                 bg="#132030", fg="#aaa", font=("Arial",8)).pack(anchor="w")

        cols = ("username","display_name","role","active")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col, lbl, w in [
            ("username",     "Username",     160),
            ("display_name", "Display Name", 180),
            ("role",         "Role",         140),
            ("active",       "Status",        80),
        ]:
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree.bind("<Double-1>", self._edit_selected)
        tk.Label(self, text="Double-click to edit / reset password",
                 bg="#0d1b2a", fg="#555", font=("Arial",8)).pack(anchor="w", padx=10)

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        self.users = {}
        try:
            for doc in self.db.collection("admin_users").stream():
                u = doc.to_dict()
                self.users[u.get("username","")] = u
                self.tree.insert("", "end", values=(
                    u.get("username",""),
                    u.get("display_name",""),
                    get_role_display(u.get("role","")),
                    "✅ Active" if u.get("active") else "❌ Inactive",
                ))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _add_dialog(self):
        AdminUserDialog(self, mode="add", on_save=self._load)

    def _edit_selected(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        uname = self.tree.item(sel[0])["values"][0]
        user  = self.users.get(uname)
        if user:
            AdminUserDialog(self, mode="edit", user=user, on_save=self._load)


class AdminUserDialog(tk.Toplevel):
    def __init__(self, parent, mode="add", user=None, on_save=None):
        super().__init__(parent)
        self.mode    = mode
        self.user    = user or {}
        self.on_save = on_save
        self.db      = get_db()
        self.title("Create Admin / Security User" if mode=="add"
                   else f"Edit User — {user.get('username','')}")
        self.geometry("460x540")
        self.resizable(False, True)
        self.configure(bg="#0d1b2a")
        self.grab_set()
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg="#0d1b2a", highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frm    = tk.Frame(canvas, bg="#0d1b2a", padx=28, pady=20)
        win    = canvas.create_window((0,0), window=frm, anchor="nw")
        frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        _bind_scroll(canvas)

        u = self.user
        tk.Label(frm, text="👮 Admin / Security User",
                 font=("Arial",13,"bold"), bg="#0d1b2a", fg="#f0c040").pack(anchor="w", pady=(0,12))

        def field(label, key, default="", show=""):
            row = tk.Frame(frm, bg="#0d1b2a"); row.pack(fill="x", pady=4)
            tk.Label(row, text=label+":", width=18, anchor="w",
                     bg="#0d1b2a", fg="#ccc").pack(side="left")
            var = tk.StringVar(value=u.get(key, default))
            tk.Entry(row, textvariable=var, width=24, show=show,
                     bg="#1e3a5f", fg="white", insertbackground="white",
                     relief="flat", bd=4).pack(side="left")
            return var

        self.v_username     = field("Username",     "username")
        self.v_display_name = field("Display Name", "display_name")

        # Role dropdown
        role_row = tk.Frame(frm, bg="#0d1b2a"); role_row.pack(fill="x", pady=4)
        tk.Label(role_row, text="Role:", width=18, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_role = tk.StringVar(value=u.get("role","security"))
        role_cb = ttk.Combobox(role_row, textvariable=self.v_role,
                               values=get_all_roles(), width=20, state="readonly")
        role_cb.pack(side="left")
        self.v_role.trace_add("write", self._update_role_hint)

        self.role_hint = tk.Label(frm, text="",
                                  bg="#0d1b2a", fg="#aaa", font=("Arial",8),
                                  wraplength=380, justify="left")
        self.role_hint.pack(anchor="w", pady=(0,8))
        self._update_role_hint()

        # Password
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)
        tk.Label(frm, text="Password",
                 fg="#f0c040", bg="#0d1b2a",
                 font=("Arial",9,"bold")).pack(anchor="w", pady=(0,4))

        if self.mode == "add":
            self.v_password = field("Password",        "password")
            self.v_confirm  = field("Confirm Password", "confirm",  show="")
            tk.Label(frm,
                     text="Min 6 characters. Share this password with the user.",
                     bg="#0d1b2a", fg="#7f8c8d", font=("Arial",8)).pack(anchor="w")
        else:
            tk.Label(frm, text="Leave blank to keep existing password.",
                     bg="#0d1b2a", fg="#aaa", font=("Arial",8)).pack(anchor="w")
            self.v_password = field("New Password",    "new_pass")
            self.v_confirm  = field("Confirm Password", "confirm")

        # Active toggle
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=6)
        act_row = tk.Frame(frm, bg="#0d1b2a"); act_row.pack(fill="x", pady=4)
        tk.Label(act_row, text="Active:", width=18, anchor="w",
                 bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.v_active = tk.BooleanVar(value=u.get("active", True))
        tk.Checkbutton(act_row, variable=self.v_active,
                       bg="#0d1b2a", fg="white",
                       selectcolor="#1e3a5f",
                       activebackground="#0d1b2a").pack(side="left")

        # Save button
        tk.Frame(frm, height=1, bg="#2c3e50").pack(fill="x", pady=8)
        br = tk.Frame(frm, bg="#0d1b2a"); br.pack(fill="x", pady=4)
        tk.Button(br, text="✔ Save User",
                  command=self._save,
                  bg="#f77f00", fg="white",
                  font=("Arial",10,"bold"),
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="left", padx=(0,10))
        tk.Button(br, text="Cancel",
                  command=self.destroy,
                  padx=14, relief="flat").pack(side="left")

    def _update_role_hint(self, *_):
        role = self.v_role.get()
        hints = {
            "super_admin": "Full access to all modules.",
            "admin":       "Full access except creating Super Admin.",
            "hr":          "Employees, Attendance, Salary, ID cards.",
            "ca":          "Salary, Bonus, Raise, Reports.",
            "manager":     "Dashboard, Attendance, Employees, Security.",
            "security":    "🛡️ Security tab ONLY — marks IN/OUT for employees without phones.",
        }
        self.role_hint.config(text=f"  ℹ️  {hints.get(role,'')}", fg="#f0c040" if role=="security" else "#aaa")

    def _save(self):
        username     = self.v_username.get().strip().lower()
        display_name = self.v_display_name.get().strip()
        role         = self.v_role.get()
        password     = self.v_password.get().strip()
        confirm      = self.v_confirm.get().strip()
        active       = self.v_active.get()

        if not username or not display_name:
            messagebox.showerror("Error","Username and Display Name required.",parent=self); return

        if self.mode == "add":
            if len(password) < 6:
                messagebox.showerror("Error","Password must be at least 6 characters.",parent=self); return
            if password != confirm:
                messagebox.showerror("Error","Passwords do not match.",parent=self); return
            pw_hash = _hash(password)
        else:
            if password:   # changing password
                if len(password) < 6:
                    messagebox.showerror("Error","Password must be at least 6 characters.",parent=self); return
                if password != confirm:
                    messagebox.showerror("Error","Passwords do not match.",parent=self); return
                pw_hash = _hash(password)
            else:
                pw_hash = self.user.get("password_hash","")

        data = {
            "username":             username,
            "display_name":         display_name,
            "role":                 role,
            "password_hash":        pw_hash,
            "active":               active,
            "must_change_password": False,
        }
        try:
            self.db.collection("admin_users").document(username).set(data)
            msg = f"✅ User '{username}' saved!\n\nRole: {get_role_display(role)}"
            if self.mode == "add":
                msg += f"\nPassword: {password}\n\nShare these credentials with the user."
            messagebox.showinfo("Saved", msg, parent=self)
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)
