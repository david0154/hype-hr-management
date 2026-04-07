"""
Role-Based Access Control — Hype HR Management
Roles: admin, hr, ca, manager, security
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""

ROLES = {
    "admin": {
        "label": "Admin",
        "permissions": [
            "dashboard", "employees", "attendance", "salary", "salary_view",
            "qr_generator", "settings", "manage_users", "manage_roles",
            "delete_records", "reports"
        ]
    },
    "hr": {
        "label": "HR Manager",
        "permissions": ["dashboard", "employees", "attendance", "salary_view"]
    },
    "ca": {
        "label": "CA / Accountant",
        "permissions": ["dashboard", "salary", "salary_view", "reports"]
    },
    "manager": {
        "label": "Manager",
        "permissions": ["dashboard", "attendance", "employees_view"]
    },
    "security": {
        "label": "Security",
        "permissions": ["qr_scanner"]
    }
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLES.get(role.lower(), {}).get("permissions", [])


def get_role_label(role: str) -> str:
    return ROLES.get(role.lower(), {}).get("label", role.title())


def get_accessible_modules(role: str) -> list:
    return ROLES.get(role.lower(), {}).get("permissions", [])
