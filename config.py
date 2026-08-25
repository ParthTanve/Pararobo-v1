import re
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP (CLEAN SDK INITIALIZATION)
# ==========================================

# Clean up conflicting env variables
for key in ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"]:
    os.environ.pop(key, None)

render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# 1. INITIALIZE FIREBASE ADMIN (NO FORCED STRINGS)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(file_path)
        # Nayi library bina explicit database id ke automatically sahi database dhoondh legi
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin Initialized Successfully!")
    except Exception as e:
        print(f"❌ Firebase Init Error: {e}")

# 2. CONNECT FIRESTORE CLIENT
try:
    db = firestore.client()
    print("✅ Firestore Client Connected Properly!")
except Exception as e:
    print(f"❌ Firestore Client Error: {e}")
    db = None

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None