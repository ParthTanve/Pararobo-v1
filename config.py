import re
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP (THE CLEAN NATIVE FIX)
# ==========================================

# Clean up conflicting environment variables
for key in ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"]:
    os.environ.pop(key, None)

# 1. SMART PATH LOGIC
render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# 2. READ PROJECT ID & CREDENTIALS
project_id = None
key_data = None
try:
    with open(file_path, "r") as f:
        key_data = json.load(f)
    project_id = key_data.get("project_id")
except Exception as e:
    print(f"Error reading JSON: {e}")

# 3. INITIALIZE FIREBASE ADMIN
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(file_path)
        firebase_admin.initialize_app(cred)
        print(f"✅ Firebase Admin Initialized for Project: {project_id}")
    except Exception as e:
        print(f"Firebase Init Error: {e}")

# 4. 🟢 THE NATIVE CLIENT: Koi extra argument nahi, seedha default client!
# Jab hum koi database_id pass nahi karte, toh ye JSON file ki credentials ke hisab se 
# automatically sahi database utha leta hai.
db = firestore.client()
print("✅ Firestore Client Connected Successfully!")

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None