import re
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP (THE RENDER OVERRIDE FIX)
# ==========================================

# 🟢 HACK: Render ke kachre wale default variables ko delete kar rahe hain
# Yehi wo villain hai jo Project ID ko chura raha tha!
for key in ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"]:
    os.environ.pop(key, None)

# 1. SMART PATH LOGIC
render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# 2. FORCE PROJECT ID EXTRACTION
project_id = None
try:
    with open(file_path, "r") as f:
        key_data = json.load(f)
    project_id = key_data.get("project_id")
except Exception as e:
    print(f"Error reading JSON: {e}")

# 3. INITIALIZE FIREBASE WITH STRICT PROJECT ID OVERRIDE
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(key_data) # Direct dictionary pass
        
        # 🟢 THE MAGIC FIX: Zabardasti projectId inject karna! 
        firebase_admin.initialize_app(cred, {
            'projectId': project_id
        })
        print(f"✅ Firebase Admin Initialized strictly for Project: {project_id}")
    except Exception as e:
        print(f"Firebase Init Error: {e}")

# 4. GET DB CLIENT
db = firestore.client()

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

# Email validation pattern (Allows .in, .com, and numbers in start)
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None