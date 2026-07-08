from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
import time
import uuid
import re
from config import is_valid_email

# ==========================================
# FASTAPI APP INITIALIZATION
# ==========================================
app = FastAPI(title="Pararobo CRM Universal Backend", description="Backend API for CRM Modules and RBAC Auth")

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
    return hashlib.sha256(password.encode()).hexdigest()



def get_db_connection():
    conn = sqlite3.connect("crm_main.db")
    conn.row_factory = sqlite3.Row  
    return conn

# ==========================================
# DATABASE INITIALIZATION (Run on Startup)
# ==========================================
@app.on_event("startup")
def startup_db_init():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_sessions (token TEXT PRIMARY KEY, username TEXT, email TEXT, role TEXT, login_time REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS interns (intern_id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, contact TEXT, role TEXT, assigned_project TEXT, completed_projects TEXT, mentor TEXT, duration TEXT, status TEXT, college TEXT, branch TEXT, semester TEXT, skills TEXT, photo_data BLOB, interview_process TEXT, internship_type TEXT, password TEXT)''')
    
    try: cursor.execute("ALTER TABLE interns ADD COLUMN password TEXT")
    except sqlite3.OperationalError: pass
    
    # Purana admin hatakar nayi IDs add karna
    cursor.execute("DELETE FROM users WHERE email='admin@pararobo.com'")
    
    # 1. BOSS KI ID
    cursor.execute("SELECT COUNT(*) FROM users WHERE email='info@pararobo.in'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)", 
                       ("superadmin", "Super Admin", "info@pararobo.in", ""))

    # 2. DEVELOPER KI ID
    cursor.execute("SELECT COUNT(*) FROM users WHERE email='admin123@gmail.com'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)", 
                       ("developer", "Developer Admin", "admin123@gmail.com", hash_password("test@1234")))

    # 3.  HR KI ID 
    cursor.execute("SELECT COUNT(*) FROM users WHERE email='hr@pararobo.in'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)", 
                       ("hr_admin", "HR Manager", "hr@pararobo.in", ""))

    # 4.  LEAD DEVELOPER KI ID 
    cursor.execute("SELECT COUNT(*) FROM users WHERE email='aarya@pararobo.in'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)", 
                       ("lead_dev", "Lead Developer", "aarya@pararobo.in", ""))

    conn.commit()
    conn.close()

# ==========================================
# PYDANTIC MODELS (Data Validation)
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str = None  

class PasswordSetupRequest(BaseModel):
    email: str
    password: str

# ==========================================
# API ENDPOINTS: AUTHENTICATION
# ==========================================

@app.post("/api/auth/check-email")
def check_user_email(data: LoginRequest):
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid Email Format")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check in Admin/HR/Developer
    cursor.execute("SELECT username, name, password FROM users WHERE email=?", (data.email,))
    admin = cursor.fetchone()
    if admin:
        conn.close()
        requires_setup = not bool(admin["password"])
        return {"role": "Admin", "name": admin["name"], "requires_setup": requires_setup}

    # Check in Interns
    cursor.execute("SELECT intern_id, name, password FROM interns WHERE email=?", (data.email,))
    intern = cursor.fetchone()
    if intern:
        conn.close()
        requires_setup = not bool(intern["password"])
        return {"role": "Intern", "name": intern["name"], "requires_setup": requires_setup}

    conn.close()
    raise HTTPException(status_code=404, detail="Email not registered in the system.")


@app.post("/api/auth/login")
def login_user(data: LoginRequest):
    if not data.password:
        raise HTTPException(status_code=400, detail="Password is required")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = hash_password(data.password)
    
    # Check Both Admin & Intern
    cursor.execute("SELECT name FROM users WHERE email=? AND password=?", (data.email, hashed_pw))
    admin = cursor.fetchone()
    if admin:
        token = uuid.uuid4().hex
        cursor.execute("INSERT INTO active_sessions (token, username, email, role, login_time) VALUES (?, ?, ?, ?, ?)", (token, admin["name"], data.email, "Admin", time.time()))
        conn.commit(); conn.close()
        return {"status": "success", "token": token, "name": admin["name"], "role": "Admin"}

    cursor.execute("SELECT name FROM interns WHERE email=? AND password=?", (data.email, hashed_pw))
    intern = cursor.fetchone()
    if intern:
        token = uuid.uuid4().hex
        cursor.execute("INSERT INTO active_sessions (token, username, email, role, login_time) VALUES (?, ?, ?, ?, ?)", (token, intern["name"], data.email, "Intern", time.time()))
        conn.commit(); conn.close()
        return {"status": "success", "token": token, "name": intern["name"], "role": "Intern"}

    conn.close()
    raise HTTPException(status_code=401, detail="Incorrect Password")


@app.post("/api/auth/setup-password")
def setup_password(data: PasswordSetupRequest):
    """Admin aur Intern dono yahan se pehli baar password setup karenge"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check Admin First
    cursor.execute("SELECT name, password FROM users WHERE email=?", (data.email,))
    admin = cursor.fetchone()
    if admin:
        if admin["password"]:
            conn.close()
            raise HTTPException(status_code=400, detail="Password already setup. Please login.")
            
        hashed_pw = hash_password(data.password)
        cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed_pw, data.email))
        token = uuid.uuid4().hex
        cursor.execute("INSERT INTO active_sessions (token, username, email, role, login_time) VALUES (?, ?, ?, ?, ?)", (token, admin["name"], data.email, "Admin", time.time()))
        conn.commit(); conn.close()
        return {"status": "success", "token": token, "name": admin["name"], "role": "Admin"}
    
    # Check Intern Second
    cursor.execute("SELECT name, password FROM interns WHERE email=?", (data.email,))
    intern = cursor.fetchone()
    if intern:
        if intern["password"]:
            conn.close()
            raise HTTPException(status_code=400, detail="Password already setup. Please login.")

        hashed_pw = hash_password(data.password)
        cursor.execute("UPDATE interns SET password=? WHERE email=?", (hashed_pw, data.email))
        token = uuid.uuid4().hex
        cursor.execute("INSERT INTO active_sessions (token, username, email, role, login_time) VALUES (?, ?, ?, ?, ?)", (token, intern["name"], data.email, "Intern", time.time()))
        conn.commit(); conn.close()
        return {"status": "success", "token": token, "name": intern["name"], "role": "Intern"}
        
    conn.close()
    raise HTTPException(status_code=404, detail="Email not found")


@app.get("/api/auth/session/{token}")
def verify_session(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, role, login_time FROM active_sessions WHERE token=?", (token,))
    row = cursor.fetchone()
    
    if row:
        if time.time() - row["login_time"] <= 600: 
            cursor.execute("UPDATE active_sessions SET login_time=? WHERE token=?", (time.time(), token))
            conn.commit(); conn.close()
            return {"valid": True, "username": row["username"], "email": row["email"], "role": row["role"]}
        else:
            cursor.execute("DELETE FROM active_sessions WHERE token=?", (token,))
            conn.commit(); conn.close()
            raise HTTPException(status_code=401, detail="Session expired")
            
    conn.close()
    raise HTTPException(status_code=401, detail="Invalid token")

@app.delete("/api/auth/logout/{token}")
def logout_user(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/")
def root():
    return {"message": "Pararobo CRM Backend API is Running Successfully!"}