# Hype HR — Security Module Setup Guide

## Firestore Security Rules (REQUIRED)

Paste these rules in **Firebase Console → Firestore → Rules**.
Without these, the Security Login will fail with `PERMISSION_DENIED`.

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Employees — read own doc, write own limited fields
    match /employees/{empId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.uid == resource.data.uid;
    }

    // Security users (created by Python admin app via service account)
    // Each doc ID = Firebase Auth UID of the security/supervisor user
    match /security_users/{uid} {
      allow read: if request.auth != null && request.auth.uid == uid;
      allow write: if false; // only admin service account writes here
    }

    // Admin users collection (legacy) — allow authenticated read
    match /admin_users/{docId} {
      allow read: if request.auth != null;
      allow write: if false; // only admin service account
    }

    // Attendance logs — any authenticated user can read/write
    match /attendance_logs/{logId} {
      allow read, write: if request.auth != null;
    }

    // Salary slips — employee reads own, hr/admin reads all
    match /salary_slips/{slipId} {
      allow read: if request.auth != null;
      allow write: if false; // only admin
    }
  }
}
```

## Python Admin App — Creating Security Users

When you create a security/supervisor user in the Python admin app,
make sure it writes a document to **`security_users`** collection
(in addition to or instead of `admin_users`) with this structure:

```json
{
  "uid": "<firebase-auth-uid>",
  "display_name": "Guard Name",
  "email": "guard@company.com",
  "role": "security",
  "employee_id": "SEC-001",
  "company": "Hype Pvt Ltd"
}
```

The document ID should be the Firebase Auth UID.

## QR Code Format (Employee ID Card)

The QR code on each employee ID card must contain:

```
HYPE_EMP|EMP-0001|Employee Full Name|username|CompanyName
```

Example:
```
HYPE_EMP|EMP-0042|Ravi Kumar|ravikumar|HYPE
```

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `PERMISSION_DENIED` on login | Firestore rules not set | Add rules above |
| "Account not found" after correct login | User doc not in any collection | Add doc to `security_users` via admin app |
| QR scanner opens but never detects | Wrong QR format | QR must start with `HYPE_EMP|` |
| `Unauthorized` when opening scanner | Role not saved in session | Re-login via Security Login screen |
| Camera permission denied | User denied camera | Go to App Settings → grant Camera |
