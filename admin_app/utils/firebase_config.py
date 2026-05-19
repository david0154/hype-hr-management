"""
Firebase Admin SDK Configuration — Hype HR Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os

_db = None
_bucket = None

# Always look for the key next to this file (admin_app/utils/../serviceAccountKey.json)
_DEFAULT_KEY = os.path.join(os.path.dirname(__file__), "..", "serviceAccountKey.json")


def init_firebase(service_account_path: str = None):
    global _db, _bucket
    if service_account_path is None:
        service_account_path = _DEFAULT_KEY

    key_path = os.path.abspath(service_account_path)
    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"serviceAccountKey.json not found at:\n{key_path}\n\n"
            "Download it from Firebase Console → Project Settings → Service Accounts "
            "and place it in the admin_app/ folder."
        )

    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', 'hype-hr.appspot.com')
        })
    _db = firestore.client()
    _bucket = storage.bucket()
    return _db


def get_db():
    global _db
    if _db is None:
        init_firebase()
    return _db


def get_bucket():
    global _bucket
    if _bucket is None:
        init_firebase()
    return _bucket
