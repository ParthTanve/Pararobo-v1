import re
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# FIREBASE SETUP
# ==========================================
# Ye check karta hai ki Firebase pehle se connect toh nahi hai
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)

# Ab is 'db' variable ko hum poore project me use karenge database ke liye!
db = firestore.client()

# ==========================================
# UNIVERSAL CONFIGURATIONS
# ==========================================

# Email validation pattern (Allows .in, .com, and numbers in start)
EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,4}$"

def is_valid_email(email):
    """Checks if the provided email matches the universal pattern."""
    return re.match(EMAIL_PATTERN, email) is not None




