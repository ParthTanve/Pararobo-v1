import re
import os
import json
import firebase_admin
from firebase_admin import credentials
from google.oauth2 import service_account
from google.cloud import firestore

# ==========================================
# FIREBASE SETUP (ULTIMATE AND FINAL FIX)
# ==========================================

# Clean up conflicting env variables
for key in ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"]:
    os.environ.pop(key, None)

render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

project_id = None
key_data = None
try:
    with open(file_path, "r") as f:
        key_data = json.load(f)
    project_id = key_data.get("project_id")
except Exception as e:
    print(f"Error reading JSON: {e}")

# 1. Initialize Firebase Admin
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(file_path)
        firebase_admin.initialize_app(cred, {'projectId': project_id})
    except Exception as e:
        print(f"Firebase Init Error: {e}")

# 2. 🟢 THE ACTUAL FIX: Pass CREDENTIALS explicitly to the Client
try:
    # JSON file se Google Cloud Credentials load kar rahe hain
    gcp_cred = service_account.Credentials.from_service_account_file(file_path)
    
    # Ab Client ko sab kuch de rahe hain: Credentials (Chabhi), Project (Ghar), aur Database (Kamra)
    db = firestore.Client(credentials=gcp_cred, project=project_id, database="(default)")
    print("✅ Firestore Client Connected Perfectly!")
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