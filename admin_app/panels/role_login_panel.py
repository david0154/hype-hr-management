"""
Hype HR Management — Admin App: Role-Based Login Panel
Roles: super_admin, admin, hr, manager, ca, security
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import messagebox

# Role permission map — keys are roles, values are allowed panels
ROLE_PERMISSIONS = {
    'super_admin': [
        'dashboard', 'employees', 'attendance', 'salary',
        'qr_generator', 'settings', 'roles'
    ],
    'admin': [
        'dashboard', 'employees', 'attendance', 'salary',
        'qr_generator', 'settings'
    ],
    'hr': [
        'dashboard', 'employees', 'attendance', 'salary'
    ],
    'manager': [
        'dashboard', 'employees', 'attendance'
    ],
    'ca': [
        'dashboard', 'salary'
    ],
    'security': [
        'dashboard', 'attendance'
    ],
}


class RoleLoginPanel(tk.Frame):
    """
    Login panel that checks admin credentials from Firestore and
    enforces role-based access to app panels.
    """

    def __init__(self, master, firebase_manager, on_login_success, **kwargs):
        super().__init__(master, bg='#1A2740', **kwargs)
        self.fm               = firebase_manager
        self.on_login_success = on_login_success
        self._build_ui()

    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # Logo / Title
        tk.Label(self, text='HYPE HR', font=('Arial', 36, 'bold'),
                 bg='#1A2740', fg='#F77F00').pack(pady=(60, 2))
        tk.Label(self, text='Management System — Admin Portal',
                 font=('Arial', 12), bg='#1A2740', fg='#aaaaaa').pack(pady=(0, 40))

        # Card
        card = tk.Frame(self, bg='white', padx=30, pady=30, relief='flat')
        card.pack(padx=80, pady=10, fill=tk.X)

        tk.Label(card, text='Admin Login', font=('Arial', 14, 'bold'),
                 bg='white').pack(anchor='w', pady=(0, 16))

        # Username
        tk.Label(card, text='Username:', bg='white', anchor='w').pack(fill=tk.X)
        self.v_username = tk.StringVar()
        tk.Entry(card, textvariable=self.v_username, font=('Arial', 11),
                 bd=1, relief='solid').pack(fill=tk.X, pady=(2, 10), ipady=4)

        # Password
        tk.Label(card, text='Password:', bg='white', anchor='w').pack(fill=tk.X)
        self.v_password = tk.StringVar()
        tk.Entry(card, textvariable=self.v_password, show='*',
                 font=('Arial', 11), bd=1, relief='solid').pack(
            fill=tk.X, pady=(2, 10), ipady=4)

        # Role selector
        tk.Label(card, text='Login as:', bg='white', anchor='w').pack(fill=tk.X)
        self.v_role = tk.StringVar(value='admin')
        role_cb = tk.OptionMenu(card, self.v_role, *ROLE_PERMISSIONS.keys())
        role_cb.config(width=30)
        role_cb.pack(fill=tk.X, pady=(2, 16))

        tk.Button(card, text='Login', command=self._do_login,
                  bg='#F77F00', fg='white', font=('Arial', 12, 'bold'),
                  pady=8, bd=0).pack(fill=tk.X)

        self.lbl_error = tk.Label(card, text='', fg='red', bg='white')
        self.lbl_error.pack(pady=(8, 0))

        tk.Label(self, text='Developed by David | Nexuzy Lab | nexuzylab@gmail.com',
                 bg='#1A2740', fg='#555555', font=('Arial', 9)).pack(
            side=tk.BOTTOM, pady=12)

    def _do_login(self):
        username = self.v_username.get().strip()
        password = self.v_password.get().strip()
        role     = self.v_role.get()

        if not username or not password:
            self.lbl_error.config(text='Username and password are required.')
            return

        self.lbl_error.config(text='Authenticating…')
        self.update()

        try:
            # Look up admin user in Firestore: admins/{username}
            doc = self.fm.get_document('admins', username)
            if not doc:
                self.lbl_error.config(text='Invalid credentials.')
                return

            stored_hash = doc.get('password_hash', '')
            import hashlib
            pw_hash = hashlib.sha256(password.encode()).hexdigest()

            if pw_hash != stored_hash:
                self.lbl_error.config(text='Invalid credentials.')
                return

            user_role = doc.get('role', 'admin')
            if user_role != role and user_role != 'super_admin':
                self.lbl_error.config(
                    text=f'Your role is "{user_role}", not "{role}".')
                return

            if not doc.get('is_active', True):
                self.lbl_error.config(text='Your account is deactivated.')
                return

            allowed_panels = ROLE_PERMISSIONS.get(user_role, [])
            self.on_login_success(
                username=username,
                role=user_role,
                allowed_panels=allowed_panels
            )
        except Exception as e:
            self.lbl_error.config(text=f'Error: {e}')
