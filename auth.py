# Import required libraries
import streamlit as st
import re
import os
import time
import uuid
import hashlib  
from PIL import Image

# 🟢 NAYA LOGIC: Firebase Database (db) aur email validation config se import kar rahe hain
from config import is_valid_email, db

# ==========================================
# SECURITY: PASSWORD HASHING FUNCTION
# ==========================================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# ==========================================
# UNIVERSAL BACKEND DATABASE INIT (FIREBASE)
# ==========================================
def init_auth_db():
    users_ref = db.collection("users")
    
    # Purana dummy admin delete karna
    dummy_docs = users_ref.where("email", "==", "admin@pararobo.com").get()
    for doc in dummy_docs:
        doc.reference.delete()
    
    # 1. BOSS KI ID
    if not users_ref.where("email", "==", "info@pararobo.in").get():
        users_ref.add({"username": "superadmin", "name": "Super Admin", "email": "info@pararobo.in", "password": ""})

    # 2. DEVELOPER KI ID
    if not users_ref.where("email", "==", "admin123@gmail.com").get():
        users_ref.add({"username": "developer", "name": "Developer Admin", "email": "admin123@gmail.com", "password": hash_password("test@1234")})

    # 3. HR KI ID (Bina password ke, first time khud set karenge)
    if not users_ref.where("email", "==", "hr@pararobo.in").get():
        users_ref.add({"username": "hr_admin", "name": "HR Manager", "email": "hr@pararobo.in", "password": ""})

    # 4. LEAD DEVELOPER KI ID (Bina password ke, first time khud set karenge)
    if not users_ref.where("email", "==", "aarya@pararobo.in").get():
        users_ref.add({"username": "lead_dev", "name": "Lead Developer", "email": "aarya@pararobo.in", "password": ""})

# ==========================================
# BACKEND CORE: MULTI-ROLE VERIFICATION
# ==========================================
def check_user_email(email):
    # Step 1: Check if Email belongs to Admin/HR/Developer
    admin_docs = db.collection("users").where("email", "==", email).get()
    if admin_docs:
        data = admin_docs[0].to_dict()
        return "Admin", {"username": data.get("username"), "name": data.get("name"), "password": data.get("password")}

    # Step 2: Check if Email belongs to an Intern
    intern_docs = db.collection("interns").where("email", "==", email).get()
    if intern_docs:
        data = intern_docs[0].to_dict()
        return "Intern", {"id": data.get("intern_id", ""), "name": data.get("name"), "password": data.get("password", "")}

    return None, None

def set_intern_password(email, password):
    docs = db.collection("interns").where("email", "==", email).get()
    for doc in docs:
        doc.reference.update({"password": hash_password(password)})

def set_admin_password(email, password):
    docs = db.collection("users").where("email", "==", email).get()
    for doc in docs:
        doc.reference.update({"password": hash_password(password)})

# ==========================================
# SESSION MANAGEMENT (10 Min Persistence)
# ==========================================
def create_session(token, username, email, role):
    db.collection("active_sessions").document(token).set({
        "token": token,
        "username": username,
        "email": email,
        "role": role,
        "login_time": time.time()
    })

def check_session(token):
    doc_ref = db.collection("active_sessions").document(token)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        if time.time() - data.get("login_time", 0) <= 600:
            doc_ref.update({"login_time": time.time()})
            return data.get("username"), data.get("email"), data.get("role")
        else:
            doc_ref.delete()
    return None, None, None

def logout_session(token):
    db.collection("active_sessions").document(token).delete()

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
            
            # 🟢 PATH UPDATED: Ab direct main folder se images read karega
            logo_path = os.path.join(current_dir, "pararobo.png")
            text_path = os.path.join(current_dir, "pararobo text .png")
            
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
                            # Admin/Intern First Time Login Setup
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
                            # Standard Login for everyone 
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