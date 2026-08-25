import re
import os
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP
# ==========================================

# 🟢 SMART PATH LOGIC: Render ke liye alag path, Localhost ke liye alag
render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"

# Check karega ki file kahan rakhi hai
file_path = render_path if os.path.exists(render_path) else local_path

# Ye check karta hai ki Firebase pehle se connect toh nahi hai
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(file_path)  # 🟢 JSON file se Project ID automatic uthega
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Firebase Init Error: {e}")

# 🟢 FIX: 'project' argument hata diya. Ab ye bina kisi error ke makkhan chalega!
db = firestore.client()

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

# Email validation pattern (Allows .in, .com, and numbers in start)
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None