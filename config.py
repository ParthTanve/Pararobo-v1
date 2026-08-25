import re
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP
# ==========================================

# 🟢 NAYA FIX: Render ke liye JSON file se Project ID nikal rahe hain 
# taaki "Invalid database id (default)" error kabhi na aaye.
project_id = None
try:
    with open("firebase_credentials.json", "r") as file:
        firebase_data = json.load(file)
        project_id = firebase_data.get("project_id")
except Exception as e:
    print(f"Credentials File Load Error: {e}")

# Ye check karta hai ki Firebase pehle se connect toh nahi hai
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)

# Ab is 'db' variable ko hum poore project me use karenge database ke liye!
# 🟢 NAYA FIX: 'project' parameter explicitly pass kar diya
if project_id:
    db = firestore.client(project=project_id)
else:
    db = firestore.client()

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

# Email validation pattern (Allows .in, .com, and numbers in start)
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None