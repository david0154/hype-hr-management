"""
Role-Based Access Control — Hype HR Management

ROLES:
  super_admin : Full access
  admin       : Full except creating super_admin
  hr          : Employees, attendance, salary view, bonus
  ca          : Salary, bonus, raise, reports
  manager     : Attendance, employee view
  supervisor  : Security scanner + employee view (same as security but more access)
  security    : Security scanner only (mark IN/OUT for employees without phones)

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""

PERMISSIONS = {
    "super_admin": [
        "dashboard", "employees", "attendance", "salary",
        "bonus", "salary_raise", "qr_generator", "settings",
        "id_card", "manage_users", "reports", "mark_attendance",
        "security"
    ],
    "admin": [
        "dashboard", "employees", "attendance", "salary",
        "bonus", "salary_raise", "qr_generator", "settings",
        "id_card", "reports", "mark_attendance", "security"
    ],
    "hr": [
        "dashboard", "employees", "attendance",
        "salary", "bonus", "id_card", "reports",
        "mark_attendance", "security"
    ],
    "ca": [
        "dashboard", "salary", "bonus", "salary_raise",
        "attendance", "reports"
    ],
    "manager": [
        "dashboard", "attendance", "employees",
        "mark_attendance", "security"
    ],
    "supervisor": [
        "dashboard", "attendance", "employees",
        "mark_attendance", "security"
    ],
    "security": [
        "security"
    ],
}

ROLE_DISPLAY = {
    "super_admin": "Super Admin",
    "admin":       "Admin",
    "hr":          "HR Manager",
    "ca":          "CA / Accountant",
    "manager":     "Manager",
    "supervisor":  "Supervisor",
    "security":    "Security Guard",
}


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, [])


def get_role_display(role: str) -> str:
    return ROLE_DISPLAY.get(role, role.title())


def get_all_roles() -> list:
    return list(PERMISSIONS.keys())
