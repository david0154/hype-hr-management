"""
Role-Based Access Control — Hype HR Management

ROLES & PERMISSIONS:
  super_admin : All permissions (created at first launch)
  admin       : All permissions except creating super_admin accounts
  hr          : Employees view/add/edit, attendance view, salary view, bonus pay
  ca          : Salary generate, bonus pay, salary raise, reports
  manager     : Attendance view, employee view only

SUPER ADMIN DEFAULT CREDENTIALS (change after first login):
  Username : admin.hype
  Password : Hype@2024#SuperAdmin

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""

PERMISSIONS = {
    "super_admin": [
        "dashboard", "employees", "attendance", "salary",
        "bonus", "salary_raise", "qr_generator", "settings",
        "id_card", "manage_users", "reports"
    ],
    "admin": [
        "dashboard", "employees", "attendance", "salary",
        "bonus", "salary_raise", "qr_generator", "settings",
        "id_card", "reports"
    ],
    "hr": [
        "dashboard", "employees", "attendance",
        "salary", "bonus", "id_card", "reports"
    ],
    "ca": [
        "dashboard", "salary", "bonus", "salary_raise",
        "attendance", "reports"
    ],
    "manager": [
        "dashboard", "attendance", "employees"
    ],
]

ROLE_DISPLAY = {
    "super_admin": "Super Admin",
    "admin":       "Admin",
    "hr":          "HR Manager",
    "ca":          "CA / Accountant",
    "manager":     "Manager",
}


def has_permission(role: str, permission: str) -> bool:
    """Return True if role has the given permission."""
    return permission in PERMISSIONS.get(role, [])


def get_role_display(role: str) -> str:
    return ROLE_DISPLAY.get(role, role.title())


def get_all_roles() -> list:
    return list(PERMISSIONS.keys())
