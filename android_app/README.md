# Hype HR Android App

> **Developer:** David | **Organization:** Nexuzy Lab | **Email:** nexuzylab@gmail.com | **GitHub:** https://github.com/david0154

## Package
`com.nexuzylab.hypehr`

## Screens & Flow

| Screen | Description |
|---|---|
| `LoginActivity` | Username + password login (first time only) |
| `PinSetupActivity` | Set 4-digit PIN after first login |
| `PinEntryActivity` | Fast daily access via PIN |
| `DashboardActivity` | Employee summary, present/absent/OT, scan + salary buttons |
| `ScanActivity` | QR scan for self check-in / check-out |
| `SalaryListActivity` | Last 12 months salary slips, download PDF |
| `SecurityDashboardActivity` | Security/supervisor mode: scan employee ID-card QR to mark IN/OUT |

## Setup

1. Add `google-services.json` from Firebase Console → Project Settings → Your Apps → Android.
2. Place it in `android_app/app/`.
3. Open in Android Studio → Sync → Run.

## Salary Slip Auto-Generation

On the 1st of each month the app checks if a salary slip exists.
If not, it calls your hosted PHP backend webhook:
```
https://yourdomain.com/webhook.php?action=generate_salary&employee_id=EMP-0001&month_key=2026-04
```
Store `webhook_url` in Firebase → `settings/company` → `webhook_url`.

## Security Mode

Employees with `role: security` or `role: supervisor` are routed to `SecurityDashboardActivity` after login.
They can scan any employee's ID-card QR to mark attendance without the employee needing a phone.
