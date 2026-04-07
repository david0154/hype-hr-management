"""
Input Validators — Hype HR Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import re


def validate_aadhaar(aadhaar: str) -> bool:
    clean = re.sub(r'[\s\-]', '', aadhaar)
    return bool(re.fullmatch(r'[2-9]\d{11}', clean))


def validate_pan(pan: str) -> bool:
    return bool(re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]', pan.upper()))


def validate_mobile(mobile: str) -> bool:
    clean = re.sub(r'[\s\+\-]', '', mobile)
    return bool(re.fullmatch(r'[6-9]\d{9}', clean))


def validate_email(email: str) -> bool:
    return bool(re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email))


def validate_salary(salary_str: str) -> bool:
    try:
        return float(salary_str) > 0
    except (ValueError, TypeError):
        return False


def format_aadhaar(aadhaar: str) -> str:
    clean = re.sub(r'\D', '', aadhaar)
    return f"{clean[:4]}-{clean[4:8]}-{clean[8:]}" if len(clean) == 12 else aadhaar


def generate_username(name: str, company: str) -> str:
    first = re.sub(r'[^a-z0-9]', '', name.strip().split()[0].lower())
    comp  = re.sub(r'[^a-z0-9]', '', company.lower())
    return f"{first}.{comp}"


def generate_employee_id(sequence: int) -> str:
    return f"EMP-{sequence:04d}"
