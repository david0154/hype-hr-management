"""
Firebase Admin SDK Configuration — Hype HR Management
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import sys

_db = None
_bucket = None

# Get the correct path for the credentials file
def _get_credentials_path():
    cred_filename = "hype-hr-firebase-adminsdk-fbsvc-69b24d697e.json"
    
    # If running from PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    cred_path = os.path.join(base_path, cred_filename)
    
    # Also check current directory as fallback
    if not os.path.exists(cred_path):
        cred_path = cred_filename
    
    return cred_path


def init_firebase(service_account_path: str = None):
    global _db, _bucket
    if service_account_path is None:
        service_account_path = _get_credentials_path()
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', 'hype-hr.firebasestorage.app')
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
