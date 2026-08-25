import re
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Purane environment variables ko clear karna taaki conflict na ho
for key in ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"]:
    os.environ.pop(key, None)

render_path = "/etc/secrets/firebase_credentials.json"
local_path = "firebase_credentials.json"
file_path = render_path if os.path.exists(render_path) else local_path

# Firebase Admin Initialize karna (Bina kisi extra parameter ke)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(file_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin Initialized!")
    except Exception as e:
        print(f"❌ Firebase Init Error: {e}")

# Client Connect karna
try:
    db = firestore.client()
    print("✅ Firestore Client Connected!")
except Exception as e:
    print(f"❌ Firestore Error: {e}")
    db = None

EMAIL_PATTERN = r"^[a-zA-Z][a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"
def is_valid_email(email):
    return re.match(EMAIL_PATTERN, email) is not None
