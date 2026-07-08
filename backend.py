from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import time
import uuid
import re

# 🟢 NAYA LOGIC: Firebase Database (db) aur email validation config se import kar rahe hain
from config import is_valid_email, db

# ==========================================
# FASTAPI APP INITIALIZATION
# ==========================================
app = FastAPI(title="Pararobo CRM Universal Backend", description="Backend API for CRM Modules and RBAC Auth")

# CORS Middleware 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# SECURITY & HELPER FUNCTIONS
# ==========================================
def hash_password(password: str) -> str:
    """Plain text password ko SHA-256 secure hash mein convert karta hai."""
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# DATABASE INITIALIZATION (Run on Startup)
# ==========================================
@app.on_event("startup")
def startup_db_init():
    # Firebase collections automatically exist when documents are added.
    users_ref = db.collection("users")
    
    # Auto-create default Admin if none exists (As per your provided code logic)
    dummy_admin = users_ref.where("email", "==", "admin@pararobo.com").get()
    if not dummy_admin:
        users_ref.add({
            "username": "admin", 
            "name": "Admin User", 
            "email": "admin@pararobo.com", 
            "password": hash_password("admin123")
        })

# ==========================================
# PYDANTIC MODELS (Data Validation)
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str = None  # Optional for first-time intern check

class PasswordSetupRequest(BaseModel):
    email: str
    password: str

# ==========================================
# API ENDPOINTS: AUTHENTICATION
# ==========================================

@app.post("/api/auth/check-email")
def check_user_email(data: LoginRequest):
    """Check karta hai ki email Admin ka hai ya Intern ka, aur password setup hai ya nahi."""
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid Email Format")
        
    # Check in Admin/HR
    admin_docs = db.collection("users").where("email", "==", data.email).get()
    if admin_docs:
        admin_data = admin_docs[0].to_dict()
        return {"role": "Admin", "name": admin_data.get("name"), "requires_setup": False}

    # Check in Interns
    intern_docs = db.collection("interns").where("email", "==", data.email).get()
    if intern_docs:
        intern_data = intern_docs[0].to_dict()
        # Agar password None ya empty hai, toh setup required hoga
        requires_setup = not bool(intern_data.get("password"))
        return {"role": "Intern", "name": intern_data.get("name"), "requires_setup": requires_setup}

    raise HTTPException(status_code=404, detail="Email not registered in the system.")


@app.post("/api/auth/login")
def login_user(data: LoginRequest):
    """Password verify karke session token generate karta hai."""
    if not data.password:
        raise HTTPException(status_code=400, detail="Password is required")
        
    hashed_pw = hash_password(data.password)
    
    # Admin Login Check
    admin_docs = db.collection("users").where("email", "==", data.email).where("password", "==", hashed_pw).get()
    if admin_docs:
        admin_data = admin_docs[0].to_dict()
        token = uuid.uuid4().hex
        db.collection("active_sessions").document(token).set({
            "token": token,
            "username": admin_data.get("name"),
            "email": data.email,
            "role": "Admin",
            "login_time": time.time()
        })
        return {"status": "success", "token": token, "name": admin_data.get("name"), "role": "Admin"}

    # Intern Login Check
    intern_docs = db.collection("interns").where("email", "==", data.email).where("password", "==", hashed_pw).get()
    if intern_docs:
        intern_data = intern_docs[0].to_dict()
        token = uuid.uuid4().hex
        db.collection("active_sessions").document(token).set({
            "token": token,
            "username": intern_data.get("name"),
            "email": data.email,
            "role": "Intern",
            "login_time": time.time()
        })
        return {"status": "success", "token": token, "name": intern_data.get("name"), "role": "Intern"}

    raise HTTPException(status_code=401, detail="Incorrect Password")


@app.post("/api/auth/setup-password")
def setup_intern_password(data: PasswordSetupRequest):
    """Intern pehli baar login karne par naya password set karega."""
    intern_docs = db.collection("interns").where("email", "==", data.email).get()
    
    if not intern_docs:
        raise HTTPException(status_code=404, detail="Intern not found")
        
    doc = intern_docs[0]
    intern_data = doc.to_dict()
    
    if intern_data.get("password"):
        raise HTTPException(status_code=400, detail="Password already setup. Please login.")

    # Save new hashed password
    doc.reference.update({"password": hash_password(data.password)})
    
    # Generate direct login session
    token = uuid.uuid4().hex
    db.collection("active_sessions").document(token).set({
        "token": token,
        "username": intern_data.get("name"),
        "email": data.email,
        "role": "Intern",
        "login_time": time.time()
    })
    
    return {"status": "success", "message": "Password setup complete", "token": token, "name": intern_data.get("name"), "role": "Intern"}


@app.get("/api/auth/session/{token}")
def verify_session(token: str):
    """Streamlit check karega ki token valid hai ya nahi (10 Min persistence)."""
    doc_ref = db.collection("active_sessions").document(token)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        if time.time() - data.get("login_time", 0) <= 600: # 10 Minutes logic
            # Extend time dynamically
            doc_ref.update({"login_time": time.time()})
            return {"valid": True, "username": data.get("username"), "email": data.get("email"), "role": data.get("role")}
        else:
            # Session expired
            doc_ref.delete()
            raise HTTPException(status_code=401, detail="Session expired")
            
    raise HTTPException(status_code=401, detail="Invalid token")


@app.delete("/api/auth/logout/{token}")
def logout_user(token: str):
    """Token delete karke user ko safely logout karta hai."""
    db.collection("active_sessions").document(token).delete()
    return {"status": "success", "message": "Logged out successfully"}

# ==========================================
# MORE CRM ENDPOINTS CAN BE ADDED HERE LATER
# ==========================================
@app.get("/")
def root():
    return {"message": "Pararobo CRM Backend API is Running Successfully (Firebase Version)!"}