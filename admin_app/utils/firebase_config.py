"""
Firebase Admin SDK Configuration — Hype HR Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os

_db = None
_bucket = None


def init_firebase(service_account_path: str = "serviceAccountKey.json"):
    global _db, _bucket
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_path)
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
