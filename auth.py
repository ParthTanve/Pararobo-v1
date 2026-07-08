# Import required libraries
import streamlit as st
import sqlite3
import re
import os
import time
import uuid
import hashlib  
from PIL import Image
from config import is_valid_email

# ==========================================
# SECURITY: PASSWORD HASHING FUNCTION
# ==========================================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# ==========================================
# UNIVERSAL BACKEND DATABASE INIT
# ==========================================
def init_auth_db():
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # 1. Admin/HR Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # 2. Session Table (Updated for roles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            token TEXT PRIMARY KEY,
            username TEXT,
            email TEXT,
            role TEXT,
            login_time REAL
        )
    ''')

    # FIX: Purani table me naye columns safely add karne ka logic
    try: 
        cursor.execute("ALTER TABLE active_sessions ADD COLUMN email TEXT")
    except sqlite3.OperationalError: 
        pass
        
    try: 
        cursor.execute("ALTER TABLE active_sessions ADD COLUMN role TEXT")
    except sqlite3.OperationalError: 
        pass

    # 3. Ensure Interns table has a password column for their backend login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interns (
            intern_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')
    try: 
        cursor.execute("ALTER TABLE interns ADD COLUMN password TEXT")
    except sqlite3.OperationalError: 
        pass
    
    # Purana dummy admin delete karna
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

    # 3.  HR KI ID (Bina password ke, first time khud set karenge)
    cursor.execute("SELECT COUNT(*) FROM users WHERE email='hr@pararobo.in'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)", 
                       ("hr_admin", "HR Manager", "hr@pararobo.in", ""))

    # 4.  LEAD DEVELOPER KI ID (Bina password ke, first time khud set karenge)
    cursor.execute("SELECT COUNT(*) FROM users WHERE email='aarya@pararobo.in'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, name, email, password) VALUES (?, ?, ?, ?)", 
                       ("lead_dev", "Lead Developer", "aarya@pararobo.in", ""))

    conn.commit()
    conn.close()



# ==========================================
# BACKEND CORE: MULTI-ROLE VERIFICATION
# ==========================================
def check_user_email(email):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # Step 1: Check if Email belongs to Admin/HR/Developer
    cursor.execute("SELECT username, name, password FROM users WHERE email=?", (email,))
    admin = cursor.fetchone()
    if admin:
        conn.close()
        return "Admin", {"username": admin[0], "name": admin[1], "password": admin[2]}

    # Step 2: Check if Email belongs to an Intern
    cursor.execute("SELECT intern_id, name, password FROM interns WHERE email=?", (email,))
    intern = cursor.fetchone()
    if intern:
        conn.close()
        return "Intern", {"id": intern[0], "name": intern[1], "password": intern[2]}

    conn.close()
    return None, None

def set_intern_password(email, password):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE interns SET password=? WHERE email=?", (hash_password(password), email))
    conn.commit()
    conn.close()

def set_admin_password(email, password):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password=? WHERE email=?", (hash_password(password), email))
    conn.commit()
    conn.close()

# ==========================================
# SESSION MANAGEMENT (10 Min Persistence)
# ==========================================
def create_session(token, username, email, role):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO active_sessions (token, username, email, role, login_time) VALUES (?, ?, ?, ?, ?)", 
                   (token, username, email, role, time.time()))
    conn.commit()
    conn.close()

def check_session(token):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, role, login_time FROM active_sessions WHERE token=?", (token,))
    row = cursor.fetchone()
    if row:
        username, email, role, login_time = row
        if time.time() - login_time <= 600:
            cursor.execute("UPDATE active_sessions SET login_time=? WHERE token=?", (time.time(), token))
            conn.commit()
            conn.close()
            return username, email, role
        else:
            cursor.execute("DELETE FROM active_sessions WHERE token=?", (token,))
            conn.commit()
    conn.close()
    return None, None, None

def logout_session(token):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()

# ==========================================
# SMART LOGIN UI ROUTER
# ==========================================
def show_auth_page():
    if "auth_db_initialized" not in st.session_state:
        init_auth_db()
        st.session_state.auth_db_initialized = True
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.5, 3, 1.5])
    
    with col2:
        with st.container(border=True):
            spacer1, logo_col, text_col, spacer2 = st.columns([0.5, 1, 3, 0.5], vertical_alignment="center")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            logo_path = os.path.join(current_dir, "assest", "Image", "pararobo.png")
            text_path = os.path.join(current_dir, "assest", "Image", "pararobo text .png")
            
            with logo_col:
                if os.path.exists(logo_path):
                    st.image(Image.open(logo_path), use_container_width=True)
            with text_col:
                if os.path.exists(text_path):
                    st.image(Image.open(text_path), use_container_width=True)
                else:
                    st.markdown("<h2 style='text-align: left; color: #ffffff; margin-bottom: 0px;'>Pararobo CRM</h2>", unsafe_allow_html=True)
                
            st.markdown("<p style='text-align: center; color: #a1a1aa; font-size: 14px; margin-top: -10px;'>Secure Login Portal</p>", unsafe_allow_html=True)
            st.markdown("---")
            
            # SMART LOGIN FLOW
            email_input = st.text_input("Enter your Email ID", key="log_email", placeholder="e.g. user@pararobo.com")
            
            if email_input:
                if not is_valid_email(email_input):
                    st.error("Invalid Email Format!")
                else:
                    role, user_data = check_user_email(email_input)
                    
                    if role in ["Admin", "Intern"]:
                        if not user_data["password"]:
                            # Admin/Intern First Time Login Setup (Boss, HR & Lead Dev yaha setup karenge)
                            st.info(f"👋 Welcome {user_data['name']}! Set up your account password to continue.")
                            p1 = st.text_input("Create New Password", type="password", key="new_p1")
                            p2 = st.text_input("Confirm Password", type="password", key="new_p2")
                            
                            if st.button("Set Password & Login", use_container_width=True, type="primary"):
                                if p1 and p1 == p2:
                                    if role == "Admin":
                                        set_admin_password(email_input, p1)
                                    else:
                                        set_intern_password(email_input, p1)
                                        
                                    token = uuid.uuid4().hex
                                    create_session(token, user_data['name'], email_input, role)
                                    st.session_state.update({'logged_in': True, 'current_user_name': user_data['name'], 'user_email': email_input, 'user_role': role})
                                    st.query_params["session"] = token
                                    st.success("Password saved! Redirecting...")
                                    st.rerun()
                                else:
                                    st.error("Passwords do not match or cannot be empty!")
                        else:
                            # Standard Login for everyone (Developer seedha yaha se login karenge)
                            pw = st.text_input("Enter Password", type="password", key="login_pw")
                            if st.button("Login", use_container_width=True, type="primary"):
                                if hash_password(pw) == user_data["password"]:
                                    token = uuid.uuid4().hex
                                    create_session(token, user_data['name'], email_input, role)
                                    st.session_state.update({'logged_in': True, 'current_user_name': user_data['name'], 'user_email': email_input, 'user_role': role})
                                    st.query_params["session"] = token
                                    st.success(f"Welcome back, {user_data['name']}!")
                                    st.rerun()
                                else:
                                    st.error("Incorrect Password!")
                    else:
                        st.error("⚠️ Email not registered in the system. Please contact HR.")