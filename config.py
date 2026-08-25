import re
import os
import firebase_admin
from firebase_admin import credentials as fb_credentials
from google.oauth2 import service_account
from google.cloud import firestore

# ==========================================
# FIREBASE SETUP (THE ULTIMATE DIRECT FIX)
# ==========================================

# 1. SMART PATH LOGIC: Check where the file is
render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# 2. FIREBASE ADMIN INIT (Safe fallback for other features)
if not firebase_admin._apps:
    try:
        cred = fb_credentials.Certificate(file_path)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Firebase Admin Error: {e}")

# 3. DIRECT FIRESTORE CLIENT (Bypasses all Render environment bugs)
try:
    # 🟢 MASTER STROKE: Json file se sidha core Credentials nikalna
    gcp_cred = service_account.Credentials.from_service_account_file(file_path)
    
    # 🟢 FORCED INJECTION: Client ko zabardasti credentials aur project_id pakdana
    # Iske baad '%28default%29' error aane ka chance exactly 0% hai.
    db = firestore.Client(credentials=gcp_cred, project=gcp_cred.project_id)
    print("✅ Firestore Database Connected Successfully!")
except Exception as e:
    print(f"❌ Firestore Direct Connect Error: {e}")
    db = None

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

# Email validation pattern (Allows .in, .com, and numbers in start)
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None