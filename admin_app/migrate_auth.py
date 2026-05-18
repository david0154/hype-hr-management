#!/usr/bin/env python3
"""
migrate_auth.py — One-time migration script.

For every employee already in Firestore that does NOT have a Firebase Auth account:
  1. Creates a Firebase Auth user (email + app_password_plain or default password)
  2. Re-saves the Firestore document under the Auth UID as document ID
  3. Deletes the old document (if it was keyed by employee_id)

Run ONCE from the admin_app directory:
    cd admin_app
    python migrate_auth.py

Developed by David | Nexuzy Lab
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.firebase_config import get_db
from firebase_admin import auth as fb_auth
import hashlib

db = get_db()

def _hash(p): return hashlib.sha256(p.encode()).hexdigest()

def default_password(mobile, name):
    first = name.strip().split()[0].title() if name.strip() else "Emp"
    last4 = mobile.strip()[-4:] if len(mobile.strip()) >= 4 else "0000"
    return f"{first}{last4}@123"

docs = list(db.collection("employees").stream())
print(f"Found {len(docs)} employee documents.\n")

for doc in docs:
    data = doc.to_dict()
    email = data.get("email", "").strip()
    name  = data.get("name", "Employee")
    mobile= data.get("mobile", "0000")
    emp_id= data.get("employee_id", doc.id)
    plain = data.get("app_password_plain", "").strip() or default_password(mobile, name)

    if not email:
        print(f"  SKIP {emp_id} — no email set")
        continue

    # Get or create Firebase Auth user
    try:
        existing = fb_auth.get_user_by_email(email)
        uid = existing.uid
        print(f"  EXISTS {emp_id} -> UID {uid} ({email})")
    except fb_auth.UserNotFoundError:
        try:
            user = fb_auth.create_user(
                email=email,
                password=plain,
                display_name=name,
            )
            uid = user.uid
            print(f"  CREATED {emp_id} -> UID {uid} ({email}) pass={plain}")
        except Exception as ex:
            print(f"  ERROR creating {email}: {ex}")
            continue

    # If doc ID != uid, re-save under uid and delete old
    if doc.id != uid:
        data["uid"] = uid
        data["app_password_hash"]  = _hash(plain)
        data["app_password_plain"] = plain
        db.collection("employees").document(uid).set(data)
        db.collection("employees").document(doc.id).delete()
        print(f"    Moved doc {doc.id} -> {uid}")
    else:
        # Just make sure uid field is set
        db.collection("employees").document(uid).update({"uid": uid})

print("\nMigration complete!")
