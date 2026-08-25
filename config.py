import re
import os
import json
from google.oauth2 import service_account
from google.cloud import firestore

# ==========================================
# FIREBASE SETUP (BYPASSING THE ENCODING BUG)
# ==========================================

# 1. Clean up conflicting env variables
for key in ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"]:
    os.environ.pop(key, None)

# 2. Locate JSON Key
render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# 3. Read Project ID
project_id = None
try:
    with open(file_path, "r") as f:
        key_data = json.load(f)
    project_id = key_data.get("project_id")
except Exception as e:
    print(f"Error reading JSON: {e}")

# 4. 🟢 THE FIX: Direct Google Cloud Client (No database parameter)
try:
    cred = service_account.Credentials.from_service_account_file(file_path)
    
    # Yahan humne database="(default)" jaan-boojh kar HATA diya hai 
    # taaki brackets encode na ho aur bug bypass ho jaye!
    db = firestore.Client(credentials=cred, project=project_id)
    
    print("✅ Firestore Client Connected Properly without encoding bug!")
except Exception as e:
    print(f"❌ Firestore Error: {e}")
    db = None

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None
