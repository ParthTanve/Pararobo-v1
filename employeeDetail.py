# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import sqlite3
import time
import base64
import re  # Added for email validation
import streamlit.components.v1 as components
from utils import load_global_css 
from config import is_valid_email

# ==========================================
# HELPER FUNCTIONS
# ==========================================



# ==========================================
# DATABASE SECTION (Handles Data Storage)
# ==========================================

# Function to create an EMPTY database and table if it doesn't exist
def init_employee_db():
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # Create employees table with all required columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            contact TEXT,
            role TEXT,
            project TEXT,
            skills TEXT,
            certification TEXT,
            photo_data BLOB
        )
    ''')
    
    # Add photo_data column if it's missing from older databases
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN photo_data BLOB")
    except sqlite3.OperationalError:
        pass # Ignore error if the column is already there
    
    # DUMMY DATA COMPLETELY REMOVED FOR LIVE DEPLOYMENT
    
    conn.commit()
    conn.close()

# Function to read all employee data for the dashboard table
def get_all_employees():
    conn = sqlite3.connect("crm_main.db")
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()
    return df

# Function to save a new employee into the database securely
def add_new_employee(emp_id, name, email, contact, role, project, skills, cert, photo):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # Check if the email ID is already registered (Prevents Duplicate Emails)
    cursor.execute("SELECT COUNT(*) FROM employees WHERE email = ?", (email,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return "duplicate_email"
        
    try:
        # Save the new details into the database
        cursor.execute('''
            INSERT INTO employees (emp_id, name, email, contact, role, project, skills, certification, photo_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (emp_id, name, email, contact, role, project, skills, cert, photo))
        conn.commit()
        return "success"
    except sqlite3.IntegrityError:
        return "duplicate_emp_id"  # Triggers if the ID number is already used
    finally:
        conn.close()

# Function to delete an employee record permanently
def delete_employee(emp_id):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE emp_id = ?", (emp_id,))
    conn.commit()
    conn.close()

# ==========================================
# SAFE MEMORY LOGIC (Fixes the Data Loss Bug)
# ==========================================

# This function safely locks the data before moving to the Preview screen
def emp_go_preview():
    p = st.session_state
    
    name = p.get("emp_name_in", "")
    email = p.get("emp_email_in", "")
    contact = p.get("emp_contact_in", "")
    num = p.get("emp_num_in", "")
    role = p.get("emp_role_in", "")
    project = p.get("emp_project_in", "")
    skills = p.get("emp_skills_in", "")
    cert = p.get("emp_cert_in", "")
    
    if name and email and contact and num and role:
        # 1. Name Validation: Sirf alphabets aur spaces allowed hain (No numbers/special characters)
        if not name.replace(" ", "").isalpha():
            p.emp_error = "⚠️ Name should only contain alphabets (No numbers or symbols allowed)."
            
        # 2. Contact Validation: Sirf digits honge, 10 digit lamba hoga aur pehla number 6 se bada (7, 8, ya 9) hoga
        elif not (contact.isdigit() and len(contact) == 10 and int(contact[0]) > 6):
            p.emp_error = "⚠️ Contact number must be 10 digits and start with a number greater than 6 (e.g., 7, 8, or 9)."
            
        # 3. Validating Email Format
        elif not is_valid_email(email):
            p.emp_error = "⚠️ Invalid Email Format! Please enter a valid email ID."
            
        # 4. ID Number Validation
        elif len(num) != 3 or not num.isdigit():
            p.emp_error = "⚠️ ID Number must be exactly 3 digits (e.g. 011)."
            
        # Agar sab theek hai toh preview mein bhejo
        else:
            p.emp_step = "preview"
            p.emp_error = ""
            
            p.safe_emp_data = {
                'name': name, 'email': email, 'contact': contact, 'num': num,
                'role': role, 'project': project, 'skills': skills, 'cert': cert
            }
            
            if p.get("emp_photo_in") is not None:
                p.emp_photo_data = p.emp_photo_in.getvalue()
    else:
        p.emp_error = "⚠️ Please fill all mandatory fields (*)."

# This function switches the screen back to Edit mode
def emp_go_edit():
    st.session_state.emp_step = "form"

# This function resets old data when adding a brand new employee
def prepare_new_employee():
    st.session_state.emp_step = "form"
    st.session_state.emp_error = ""
    st.session_state.emp_photo_data = None
    st.session_state.safe_emp_data = {} 
    
    keys_to_clear = ["emp_name_in", "emp_contact_in", "emp_role_in", "emp_skills_in", "emp_email_in", "emp_num_in", "emp_project_in", "emp_cert_in", "emp_photo_in"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

@st.dialog("Employee Profile")
def show_profile(employee):
    img_src = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    photo_val = employee.get('photo_data')
    if photo_val is not None and isinstance(photo_val, (bytes, bytearray)) and len(photo_val) > 0:
        b64_img = base64.b64encode(photo_val).decode('utf-8')
        img_src = f"data:image/png;base64,{b64_img}"

    st.markdown(f"""
    <div style='text-align: center;'>
        <img src='{img_src}' width='120' height='120' style='margin-bottom: 10px; border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'>
        <h3 style='margin: 0px; color: #ffffff;'>{employee['name']}</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(f"**Name:**<br>{employee['name']}", unsafe_allow_html=True)
    st.markdown(f"**Email ID:**<br>{employee['email']}", unsafe_allow_html=True)
    st.markdown(f"**Contact:**<br>{employee['contact']}", unsafe_allow_html=True)
    st.markdown(f"**Employee ID:**<br>{employee['emp_id']}", unsafe_allow_html=True)
    st.markdown(f"**Role:**<br>{employee['role']}", unsafe_allow_html=True)
    st.markdown(f"**Project:**<br>{employee['project']}", unsafe_allow_html=True)
    st.markdown(f"**Skills:**<br>{employee['skills']}", unsafe_allow_html=True)
    st.markdown(f"**Certification:**<br>{employee['certification']}", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("Close Profile", use_container_width=True):
        st.rerun() 
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander(" Remove Employee (Danger Zone)"):
        st.error("⚠️ Warning: This will permanently delete the employee.")
        
        # 1. CSS trick to make the Employee Name unselectable (Cannot be highlighted/copied)
        st.markdown(
            f"To confirm, type <span style='user-select: none; -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; pointer-events: none; font-weight: bold; color: #ffffff;'>{employee['name']}</span> below:", 
            unsafe_allow_html=True
        )
        
        confirm_input = st.text_input("Type here to confirm:", key=f"del_{employee['emp_id']}")
        
        # 2. JavaScript code to completely disable Copy-Paste and Drag-Drop in this input box
        components.html(
            """
            <script>
            setTimeout(function() {
                const parentDoc = window.parent.document;
                const inputs = parentDoc.querySelectorAll('input[aria-label="Type here to confirm:"]');
                for (let i = 0; i < inputs.length; i++) {
                    inputs[i].onpaste = function(e) { e.preventDefault(); return false; };
                    inputs[i].ondrop = function(e) { e.preventDefault(); return false; };
                }
            }, 100);
            </script>
            """,
            height=0, width=0
        )

        if st.button(" Permanently Delete", type="primary", use_container_width=True):
            if confirm_input.strip().lower() == employee['name'].strip().lower():
                delete_employee(employee['emp_id'])
                st.success("Removed successfully!")
                time.sleep(1)  
                st.rerun() 
            else:
                st.warning("⚠️ Action Cancelled: Type name exactly to delete.")

@st.dialog("➕ Add New Employee", width="large")
def add_employee_dialog():
    if "safe_emp_data" not in st.session_state:
        st.session_state.safe_emp_data = {}
    draft = st.session_state.safe_emp_data

    # ------------- STEP 1: FORM UI -------------
    if st.session_state.emp_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Fill out the form below. Fields marked with * are mandatory.</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("Full Name *", value=draft.get('name', ''), key="emp_name_in")
            st.text_input("Contact Number *", value=draft.get('contact', ''), key="emp_contact_in")
            st.text_input("Employee Role *", value=draft.get('role', ''), key="emp_role_in")
            st.text_input("Skills", value=draft.get('skills', ''), key="emp_skills_in")
            st.file_uploader("Upload Photo (Optional)", type=['jpg', 'jpeg', 'png'], key="emp_photo_in")
            
        with col2:
            st.text_input("Email ID *", value=draft.get('email', ''), key="emp_email_in")
            c1, c2 = st.columns([1, 3])
            c1.text_input("Prefix", value="EMP", disabled=True)
            c2.text_input("ID Number (3 digits) *", placeholder="011", value=draft.get('num', ''), key="emp_num_in")
            st.text_input("Current Project", value=draft.get('project', ''), key="emp_project_in")
            st.text_input("Certifications", value=draft.get('cert', ''), key="emp_cert_in")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.emp_error:
            st.error(st.session_state.emp_error)
        st.button("👁️ Generate Preview", type="primary", use_container_width=True, on_click=emp_go_preview)

    # ------------- STEP 2: PREVIEW UI -------------
    elif st.session_state.emp_step == "preview":
        data = st.session_state.safe_emp_data
        full_emp_id = f"EMP{data['num']}"
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Employee Details</h3>", unsafe_allow_html=True)
        
        photo_bytes = st.session_state.get('emp_photo_data')
        if photo_bytes is not None:
            b64_p = base64.b64encode(photo_bytes).decode('utf-8')
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{b64_p}' width='100' height='100' style='border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f"**Full Name:** {data['name']}")
                st.markdown(f"**Email ID:** {data['email']}")
                st.markdown(f"**Contact Number:** {data['contact']}")
                st.markdown(f"**Employee ID:** <span style='color:#39FF14;'>{full_emp_id}</span>", unsafe_allow_html=True)
            with col_p2:
                st.markdown(f"**Role:** {data['role']}")
                st.markdown(f"**Current Project:** {data['project'] if data['project'] else '-'}")
                st.markdown(f"**Skills:** {data['skills'] if data['skills'] else '-'}")
                st.markdown(f"**Certifications:** {data['cert'] if data['cert'] else '-'}")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.emp_error:
            st.error(st.session_state.emp_error)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.button("✏️ Edit Details", use_container_width=True, on_click=emp_go_edit)
        with col_b2:
            if st.button("✅ Confirm & Save", type="primary", use_container_width=True):
                status = add_new_employee(
                    full_emp_id, data['name'], data['email'], data['contact'], 
                    data['role'], data['project'], data['skills'], data['cert'], photo_bytes
                )
                if status == "success":
                    st.success("Added Successfully!")
                    time.sleep(1)
                    st.rerun()
                elif status == "duplicate_email":
                    st.session_state.emp_error = "⚠️ Email already exists!"
                    st.rerun()
                else:
                    st.session_state.emp_error = "⚠️ Employee ID already exists! Please click Edit Details."
                    st.rerun()

# ==========================================
# MAIN PAGE RENDER (Table & Directory)
# ==========================================
def show_employee_page():
    if "employee_db_initialized" not in st.session_state:
        init_employee_db()
        st.session_state.employee_db_initialized = True
    
    load_global_css()

    st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="tertiary"] {
        color: #60a5fa !important; 
        padding: 0px !important;
        font-weight: bold !important;
        background-color: transparent !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stButton"] button[kind="tertiary"]:hover {
        color: #39FF14 !important; 
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>🧑‍💼 Employees Detail</h1>", unsafe_allow_html=True)
    with head_col2:
        if st.button("➕ Add Employee", type="primary", use_container_width=True):
            prepare_new_employee() 
            add_employee_dialog()  
            
    st.markdown("---")
    
    df = get_all_employees()
    st.markdown("<h3 style='color: #ffffff;'>Employee Directory</h3>", unsafe_allow_html=True)
    
    # Check if database is empty - LIVE STATE MESSAGE
    if len(df) == 0:
        st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
    else:
        st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 1.5, 2, 1.5, 1, 1.5, 1.5])
        with col1: st.markdown("**Sr.No**")
        with col2: st.markdown("**Name**")
        with col3: st.markdown("**Email**")
        with col4: st.markdown("**Contact**")
        with col5: st.markdown("**Emp ID**")
        with col6: st.markdown("**Employee Role**")
        with col7: st.markdown("**Current Project**")
        st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        
        for idx, row in df.iterrows():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([0.5, 1.5, 2, 1.5, 1, 1.5, 1.5], vertical_alignment="center")
            with c1: st.write(str(idx + 1))  
            with c2: 
                if st.button(f"👤 {row['name']}", key=f"emp_{row['emp_id']}", use_container_width=True, type="tertiary"):
                    show_profile(row)
            with c3: st.write(row['email'])
            with c4: st.write(row['contact'])
            with c5: st.write(row['emp_id'])
            with c6: st.write(row['role'])
            with c7: st.write(row['project'])
            st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)