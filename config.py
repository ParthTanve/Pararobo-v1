import re
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP (THE SILVER BULLET FIX)
# ==========================================

# 1. SMART PATH LOGIC: File kahan hai?
render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# 2. GOOGLE CLOUD KO ZABARDASTI FILE PAKDANA (Ye error ko jad se khatam karega)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = file_path

# 3. JSON File se Project ID nikalna
project_id = None
try:
    with open(file_path, "r") as f:
        data = json.load(f)
        project_id = data.get("project_id")
except Exception as e:
    print(f"File load error: {e}")

# 4. App Initialize karna (Bina kisi error ke)
if not firebase_admin._apps:
    cred = credentials.Certificate(file_path)
    
    if project_id:
        # 🟢 FINAL FIX: Project ID yahin set kar diya! Ab firestore.client() kabhi fail nahi hoga.
        firebase_admin.initialize_app(cred, {'projectId': project_id})
    else:
        firebase_admin.initialize_app(cred)

# Ab is 'db' variable ko hum poore project me use karenge
db = firestore.client()

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

# Email validation pattern
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None