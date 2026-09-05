import streamlit as st
import pandas as pd
import datetime
import time
import base64
import re  
import calendar 
import smtplib 
from email.message import EmailMessage 
import streamlit.components.v1 as components
from utils import load_global_css
import pytz
import os 
from dotenv import load_dotenv 

from config import is_valid_email, db

load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

def init_employee_db():
    pass

def refresh_employee_cache():
    try: get_all_employees.clear()
    except: pass

def refresh_attendance_cache():
    try:
        get_month_stats.clear()
        generate_calendar_html.clear()
        get_today_attendance_db.clear()
        get_pending_attendances.clear()
    except: pass

def refresh_task_cache():
    try:
        get_all_task_logs_db.clear()
        get_daily_task_db.clear()
    except: pass

@st.cache_data(ttl=3600)
def get_all_employees(role="Admin", email=""):
    if role == "Employee":
        docs = db.collection("employees").where("email", "==", email).get()
    else:
        docs = db.collection("employees").get()
        
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        photo_bytes = base64.b64decode(d.get("photo_data")) if d.get("photo_data") else None
        
        data_list.append({
            'Emp ID': d.get('emp_id', ''), 'Name': d.get('name', ''), 
            'Email': d.get('email', ''), 'Contact': d.get('contact', ''), 
            'Role': d.get('role', ''), 'Project': d.get('project', ''), 
            'Skills': d.get('skills', ''), 'Certification': d.get('certification', ''), 
            'Employment Type': d.get('employment_type', 'Full time'),
            'Joining Date': d.get('joining_date', '-'),
            'photo_data': photo_bytes, 'Status': d.get('status', 'Active')
        })
        
    df = pd.DataFrame(data_list)
    if not df.empty:
        df = df.sort_values(by='Emp ID')
    return df

def add_new_employee(emp_id, name, email, contact, role, project, skills, cert, photo, emp_type, joining_date):
    if db.collection("employees").where("email", "==", email).get():
        return "duplicate_email"
        
    doc_ref = db.collection("employees").document(emp_id)
    if doc_ref.get().exists:
        return "duplicate_id"  

    photo_b64 = base64.b64encode(photo).decode('utf-8') if photo else ""
    
    doc_ref.set({
        "emp_id": emp_id, "name": name, "email": email, "contact": contact, 
        "role": role, "project": project, "skills": skills, "certification": cert,
        "employment_type": emp_type, "joining_date": joining_date, "photo_data": photo_b64, "status": "Active", "password": ""
    })
    refresh_employee_cache() 
    return "success"

def delete_employee(emp_id):
    db.collection("employees").document(emp_id).delete()
    refresh_employee_cache()

def update_employee_profile_db(emp_id, role, project, status):
    db.collection("employees").document(emp_id).update({
        "role": role, "project": project, "status": status
    })
    refresh_employee_cache()

# ==========================================
# ADVANCED ATTENDANCE & LOG DB FUNCTIONS
# ==========================================

@st.cache_data(ttl=3600)
def get_month_stats(emp_name, target_month, target_year):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    today = now.date()
    
    emp_docs = db.collection("employees").where("name", "==", emp_name).get()
    start_date = None
    if emp_docs:
        j_str = emp_docs[0].to_dict().get("joining_date", "")
        try: start_date = datetime.datetime.strptime(j_str, '%d-%b-%Y').date()
        except: pass
            
    docs = db.collection("employee_attendance").where("emp_name", "==", emp_name).get()
    
    att_dict = {}
    late_checkins = 0
    
    for doc in docs:
        data = doc.to_dict()
        att_dict[data.get("date")] = data.get("status")
        try:
            doc_date_str = data.get("date")
            doc_date = datetime.datetime.strptime(doc_date_str, '%d-%b-%Y').date()
            if doc_date.month == target_month and doc_date.year == target_year:
                if data.get("is_late") == True:
                    late_checkins += 1
        except: pass
    
    present, absent, off, half_day = 0, 0, 0, 0
    
    if target_year == today.year and target_month == today.month: days_to_check = today.day
    elif target_year < today.year or (target_year == today.year and target_month < today.month): days_to_check = calendar.monthrange(target_year, target_month)[1]
    else: days_to_check = 0 
        
    for day in range(1, days_to_check + 1):
        d = datetime.date(target_year, target_month, day)
        
        if start_date and d < start_date: continue
            
        d_str = d.strftime('%d-%b-%Y')
        if d.weekday() >= 5: 
            off += 1; continue
        
        status = att_dict.get(d_str)
        if status == 'Present': present += 1
        elif status == 'Half Day': half_day += 1  
        elif status in ['Working', 'Pending Check-In', 'Pending Check-Out'] and d < today: absent += 1
        elif status in ['Working', 'Pending Check-In', 'Pending Check-Out'] and d == today: pass
        else: absent += 1
            
    return present, absent, off, half_day, late_checkins

@st.cache_data(ttl=3600)
def generate_calendar_html(emp_name, year, month):
    docs = db.collection("employee_attendance").where("emp_name", "==", emp_name).get()
    att_dict = {doc.to_dict().get("date"): doc.to_dict().get("status") for doc in docs}
    
    emp_docs = db.collection("employees").where("name", "==", emp_name).get()
    start_date = None
    if emp_docs:
        j_str = emp_docs[0].to_dict().get("joining_date", "")
        try: start_date = datetime.datetime.strptime(j_str, '%d-%b-%Y').date()
        except: pass
            
    cal = calendar.monthcalendar(year, month)
    
    html = """
    <style>
    .cal-table { width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }
    .cal-table th { background-color: rgba(255,255,255,0.05); color: #ffffff; padding: 10px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
    .cal-table td { height: 80px; vertical-align: top; padding: 8px; border: 1px solid rgba(255,255,255,0.1); background-color: rgba(0,0,0,0.2); }
    .cal-table td.empty { background-color: transparent; border: none; }
    .day-num { font-weight: bold; color: #a1a1aa; margin-bottom: 5px; }
    .status-badge { padding: 4px; border-radius: 4px; text-align: center; font-size: 12px; font-weight: bold; }
    .status-present { background-color: rgba(57, 255, 20, 0.1); color: #39FF14; border: 1px solid #39FF14; }
    .status-absent { background-color: rgba(255, 75, 75, 0.1); color: #ff4b4b; border: 1px solid #ff4b4b; }
    .status-off { background-color: rgba(136, 136, 136, 0.1); color: #aaaaaa; border: 1px solid #aaaaaa; }
    .status-working { background-color: rgba(52, 152, 219, 0.1); color: #3498db; border: 1px solid #3498db; }
    .status-pending { background-color: rgba(255, 153, 0, 0.1); color: #ff9900; border: 1px solid #ff9900; }
    .status-halfday { background-color: rgba(52, 152, 219, 0.1); color: #3498db; border: 1px solid #3498db; } 
    </style>
    <table class="cal-table">
        <tr><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th></tr>
    """
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.datetime.now(ist).date()
    
    for week in cal:
        html += "<tr>"
        for i, day in enumerate(week):
            if day == 0: html += "<td class='empty'></td>"
            else:
                d = datetime.date(year, month, day)
                d_str = d.strftime('%d-%b-%Y')
                status = att_dict.get(d_str)
                display_status, badge_class = "", ""
                
                if d > today: display_status = ""
                elif start_date and d < start_date: display_status = "" 
                elif i >= 5: display_status, badge_class = "Off", "status-off"
                else:
                    if status == 'Present': display_status, badge_class = "Present", "status-present"
                    elif status == 'Half Day': display_status, badge_class = "Half Day", "status-halfday" 
                    elif status in ['Pending Check-In', 'Pending Check-Out']: display_status, badge_class = "Pending HR", "status-pending"
                    elif status == 'Working' and d < today: display_status, badge_class = "Absent", "status-absent"
                    elif status == 'Working' and d == today: display_status, badge_class = "Working", "status-working"
                    else: display_status, badge_class = "Absent", "status-absent"
                        
                badge_html = f"<div class='status-badge {badge_class}'>{display_status}</div>" if display_status else ""
                html += f"<td><div class='day-num'>{day}</div>{badge_html}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def mark_checkin_db(date_str, emp_name, time_str, photo_bytes, is_late=False, is_half_day_intent=False):
    docs = db.collection("employee_attendance").where("date", "==", date_str).where("emp_name", "==", emp_name).get()
    if docs: return False 
    
    status = "Pending Check-In"
    comment = ""
    late_count = 0
    
    if is_late:
        past_lates = db.collection("employee_attendance").where("emp_name", "==", emp_name).where("is_late", "==", True).get()
        late_count = len(past_lates)
        if late_count == 0: comment = "System Note: Late Check-In (1st Offense - Half Day Penalty)"
        else: comment = f"System Note: Late Check-In ({late_count + 1} Offenses - Absent Penalty)"
            
    photo_b64 = base64.b64encode(photo_bytes).decode('utf-8') if photo_bytes else ""
    db.collection("employee_attendance").add({
        "date": date_str, "emp_name": emp_name, "check_in": time_str, 
        "check_out": "-", "status": status, "photo_data": photo_b64, "hr_comment": comment,
        "is_late": is_late, "late_count": (late_count + 1) if is_late else 0,
        "is_half_day_intent": is_half_day_intent
    })
    refresh_attendance_cache()
    return "success"

def mark_checkout_db(date_str, emp_name, time_str, photo_bytes):
    docs = db.collection("employee_attendance").where("date", "==", date_str).where("emp_name", "==", emp_name).get()
    if not docs: return "not_checked_in"
    photo_b64 = base64.b64encode(photo_bytes).decode('utf-8') if photo_bytes else ""
    docs[0].reference.update({"check_out": time_str, "status": "Pending Check-Out", "checkout_photo_data": photo_b64})
    refresh_attendance_cache()
    return "success"

def manual_override_attendance_db(date_str, emp_name, status, comment):
    docs = db.collection("employee_attendance").where("date", "==", date_str).where("emp_name", "==", emp_name).get()
    ist = pytz.timezone('Asia/Kolkata')
    time_str = datetime.datetime.now(ist).strftime('%I:%M %p')
    
    if docs:
        docs[0].reference.update({"status": status, "check_in": time_str, "check_out": time_str, "hr_comment": comment})
    else:
        db.collection("employee_attendance").add({
            "date": date_str, "emp_name": emp_name, "check_in": time_str, "check_out": time_str, "status": status, 
            "photo_data": "", "hr_comment": comment, "is_late": False, "late_count": 0, "is_half_day_intent": False
        })
    refresh_attendance_cache()

@st.cache_data(ttl=3600)
def get_today_attendance_db(date_str, emp_name=None, role="Admin"):
    if role == "Employee":
        docs = db.collection("employee_attendance").where("date", "==", date_str).where("emp_name", "==", emp_name).get()
    else:
        docs = db.collection("employee_attendance").where("date", "==", date_str).get()
        
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            "Date": d.get("date"), "Employee Name": d.get("emp_name"), 
            "Check-In": d.get("check_in"), "Check-Out": d.get("check_out"), 
            "Status": d.get("status"), "Comment": d.get("hr_comment", "-")
        })
    return pd.DataFrame(data_list)

@st.cache_data(ttl=3600)
def get_pending_attendances():
    docs1 = db.collection("employee_attendance").where("status", "==", "Pending Check-In").get()
    docs2 = db.collection("employee_attendance").where("status", "==", "Pending Check-Out").get()
    docs = docs1 + docs2
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        photo_bytes = base64.b64decode(d.get("photo_data")) if d.get("photo_data") else None
        checkout_photo_bytes = base64.b64decode(d.get("checkout_photo_data")) if d.get("checkout_photo_data") else None
        
        data_list.append({
            "rowid": doc.id, "date": d.get("date"), "emp_name": d.get("emp_name"), 
            "check_in": d.get("check_in"), "check_out": d.get("check_out"), 
            "status": d.get("status"), "photo_data": photo_bytes, "checkout_photo_data": checkout_photo_bytes,
            "is_late": d.get("is_late", False), "late_count": d.get("late_count", 0),
            "is_half_day_intent": d.get("is_half_day_intent", False)
        })
    return pd.DataFrame(data_list)

def update_attendance_status(rowid, new_status):
    db.collection("employee_attendance").document(rowid).update({"status": new_status})
    refresh_attendance_cache()

def save_planned_task_db(date_str, day_str, emp_name, task):
    db.collection("employee_daily_tasks").add({
        "date": date_str, "day": day_str, "emp_name": emp_name, "task": task,
        "result": "-", "outcome": "-", "extra_curriculum": "-", "submit_time": "-", "status": "Pending" 
    })
    refresh_task_cache()

def update_actual_task_db(date_str, emp_name, result, outcome, extra, status, submit_time):
    docs = db.collection("employee_daily_tasks").where("date", "==", date_str).where("emp_name", "==", emp_name).get()
    if docs:
        docs[0].reference.update({
            "result": result, "outcome": outcome, "extra_curriculum": extra, "submit_time": submit_time, "status": status
        })
        refresh_task_cache()

@st.cache_data(ttl=3600)
def get_all_task_logs_db(emp_name=None, role="Admin"):
    if role == "Employee":
        docs = db.collection("employee_daily_tasks").where("emp_name", "==", emp_name).get()
    else:
        docs = db.collection("employee_daily_tasks").get()
        
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            "Name": d.get("emp_name"), "Date": d.get("date"), "Day": d.get("day"), 
            "Today's Task": d.get("task"), "Result": d.get("result", "-"), 
            "Outcome": d.get("outcome"), "Extra Curriculum": d.get("extra_curriculum"),
            "Status": d.get("status", "Completed"), "Submit Time": d.get("submit_time", "-")
        })
        
    df = pd.DataFrame(data_list)
    if not df.empty:
        df['Sort_Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y', errors='coerce')
        df = df.sort_values(by=['Sort_Date', 'Submit Time'], ascending=[False, False]).drop(columns=['Sort_Date'])
    return df

@st.cache_data(ttl=3600)
def get_daily_task_db(date_str, emp_name):
    docs = db.collection("employee_daily_tasks").where("date", "==", date_str).where("emp_name", "==", emp_name).get()
    return docs[0].to_dict() if docs else None

def emp_go_preview():
    p = st.session_state
    name = p.get("e_name_in", "")
    email = p.get("e_email_in", "").strip() 
    contact = p.get("e_contact_in", "")
    num = p.get("e_num_in", "")
    e_type = p.get("e_type_in", "Full time")
    role = p.get("e_role_in", "AI/ML Developer")
    jdate = p.get("e_jdate_in", datetime.datetime.now(pytz.timezone('Asia/Kolkata')).date())
    skills = p.get("e_skills_in", "") 
    project = p.get("e_project_in", "")
    cert = p.get("e_cert_in", "")

    if name and email and contact and num:
        if not name.replace(" ", "").isalpha(): p.e_error = "⚠️ Name should only contain alphabets."
        elif not (contact.isdigit() and len(contact) == 10 and int(contact[0]) > 6): p.e_error = "⚠️ Contact must be exactly 10 digits."
        elif not is_valid_email(email): p.e_error = "⚠️ Invalid Email Format!"
        elif len(num) != 3 or not num.isdigit(): p.e_error = "⚠️ ID Number must be exactly 3 digits."
        else:
            p.e_step = "preview"; p.e_error = ""
            p.safe_e_data = {'name': name, 'email': email, 'contact': contact, 'num': num, 'type': e_type, 'role': role, 'joining_date': jdate, 'skills': skills, 'project': project, 'cert': cert}
            if p.get("e_photo_in") is not None: p.e_photo_data = p.e_photo_in.getvalue()
    else:
        p.e_error = "⚠️ Please fill all mandatory fields (*)."

def emp_go_edit(): st.session_state.e_step = "form"

def prepare_new_employee():
    st.session_state.e_step = "form"; st.session_state.e_error = ""; st.session_state.e_photo_data = None; st.session_state.safe_e_data = {} 
    for k in ["e_name_in", "e_contact_in", "e_skills_in", "e_email_in", "e_num_in", "e_project_in", "e_photo_in", "e_cert_in", "e_role_in", "e_jdate_in"]:
        if k in st.session_state: del st.session_state[k]

@st.dialog("Employee Profile")
def show_employee_profile(emp):
    user_role = st.session_state.get('user_role', 'Admin')
    img_src = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    photo_val = emp.get('photo_data')
    if photo_val is not None and isinstance(photo_val, (bytes, bytearray)) and len(photo_val) > 0:
        b64_img = base64.b64encode(photo_val).decode('utf-8')
        img_src = f"data:image/png;base64,{b64_img}"

    st.markdown(f"<div style='text-align: center;'><img src='{img_src}' width='120' height='120' style='margin-bottom: 10px; border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'><h3 style='margin: 0px; color: #ffffff;'>{emp['Name']}</h3></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Name:** {emp['Name']}\n\n**Email:** {emp['Email']}\n\n**Contact:** {emp['Contact']}\n\n**Type:** {emp['Employment Type']}\n\n**Joining Date:** {emp.get('Joining Date', '-')}")
    with col_b:
        st.markdown(f"**Emp ID:** {emp['Emp ID']}\n\n**Role:** {emp['Role']}\n\n**Project:** {emp['Project']}\n\n**Skills:** {emp['Skills']}")
        
    st.markdown("---")
    st.markdown(f"**Certifications:** {emp['Certification']}")
    status_color = "#39FF14" if emp['Status'] == 'Active' else "#ff9900"
    st.markdown(f"**Status:** <span style='color: {status_color}; font-weight: bold;'>{emp['Status']}</span>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if user_role == 'Admin':
        with st.expander("✏️ Edit Profile (HR Only)"):
            st.markdown("<p style='font-size:14px; color:#a1a1aa;'>Update the professional details for this employee below.</p>", unsafe_allow_html=True)
            
            emp_roles = ["AI/ML Developer", "FullStack Developer", "Word Press Developer", "Frontend Developer", "Backend Developer", "Digital Marketing", "Sales & Marketing", "Manager"]
            e_role = st.selectbox("Role", emp_roles, index=emp_roles.index(emp['Role']) if emp['Role'] in emp_roles else 0, key=f"e_role_{emp['Emp ID']}")
            
            e_proj = st.text_input("Project", value=emp['Project'], key=f"e_proj_{emp['Emp ID']}")
            s_opts = ["Active", "Inactive"]
            e_status = st.selectbox("Status", s_opts, index=s_opts.index(emp['Status']) if emp['Status'] in s_opts else 0, key=f"e_status_{emp['Emp ID']}")
            
            if st.button("Save Changes", type="primary", use_container_width=True, key=f"save_{emp['Emp ID']}"):
                update_employee_profile_db(emp['Emp ID'], e_role, e_proj, e_status)
                st.success("Profile Updated Successfully!"); time.sleep(1); st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(" Remove Employee (Danger Zone)"):
            st.error("⚠️ Warning: This will permanently delete the employee.")
            st.markdown(f"To confirm, type <span style='user-select: none; pointer-events: none; font-weight: bold; color: #ffffff;'>{emp['Name']}</span> below:", unsafe_allow_html=True)
            confirm_input = st.text_input("Type here to confirm:", key=f"del_{emp['Emp ID']}")
            if st.button(" Permanently Delete", type="primary", use_container_width=True):
                if ' '.join(confirm_input.split()).lower() == ' '.join(emp['Name'].split()).lower():
                    delete_employee(emp['Emp ID']); st.success("Removed successfully!"); time.sleep(1.5); st.rerun() 
                else: st.warning("⚠️ Type name exactly to delete.")

    if st.button("Close Profile", use_container_width=True, key="close_emp_profile"): st.rerun() 

@st.dialog("➕ Add New Employee", width="large")
def add_employee_dialog():
    if "safe_e_data" not in st.session_state: st.session_state.safe_e_data = {}
    draft = st.session_state.safe_e_data

    ist = pytz.timezone('Asia/Kolkata')
    today_ist = datetime.datetime.now(ist).date()

    if st.session_state.e_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Fill out the form below. Fields marked with * are mandatory.</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name *", value=draft.get('name', ''), key="e_name_in")
            st.text_input("Contact Number *", value=draft.get('contact', ''), key="e_contact_in")
            
            emp_roles = ["AI/ML Developer", "FullStack Developer", "Word Press Developer", "Frontend Developer", "Backend Developer", "Digital Marketing", "Sales & Marketing", "Manager"]
            st.selectbox("Employee Role *", emp_roles, index=emp_roles.index(draft.get('role', "AI/ML Developer")) if draft.get('role') in emp_roles else 0, key="e_role_in")
            
            st.text_input("Skills", value=draft.get('skills', ''), key="e_skills_in")
            st.file_uploader("Upload Photo (Optional)", type=['jpg', 'jpeg', 'png'], key="e_photo_in")
        with col2:
            st.text_input("Email ID *", value=draft.get('email', ''), key="e_email_in")
            c_id1, c_id2 = st.columns([1, 3])
            c_id1.text_input("Prefix", value="EMP-", disabled=True)
            c_id2.text_input("ID Number (3 digits) *", placeholder="001", value=draft.get('num', ''), key="e_num_in")
            t_opts = ["Full time", "Half time"]
            st.selectbox("Employment Type *", t_opts, index=t_opts.index(draft.get('type', "Full time")) if draft.get('type') in t_opts else 0, key="e_type_in")
            
            st.date_input("Joining Date *", value=draft.get('joining_date', today_ist), key="e_jdate_in")
            
            st.text_input("Current Project", value=draft.get('project', ''), key="e_project_in")
            st.text_input("Certifications", value=draft.get('cert', ''), key="e_cert_in")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("e_error"): st.error(st.session_state.e_error)
        st.button("👁️ Preview Details", type="primary", use_container_width=True, on_click=emp_go_preview)

    elif st.session_state.e_step == "preview":
        data = st.session_state.safe_e_data
        full_id = f"EMP-{data['num']}"
        j_date_str = data['joining_date'].strftime('%d-%b-%Y') if isinstance(data['joining_date'], datetime.date) else data['joining_date']
        
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Employee Details</h3>", unsafe_allow_html=True)
        photo_bytes = st.session_state.get('e_photo_data')
        if photo_bytes is not None:
            b64_p = base64.b64encode(photo_bytes).decode('utf-8')
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{b64_p}' width='100' height='100' style='border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1: st.markdown(f"**Full Name:** {data['name']}\n\n**Email ID:** {data['email']}\n\n**Contact Number:** {data['contact']}\n\n**Emp ID:** <span style='color:#39FF14;'>{full_id}</span>", unsafe_allow_html=True)
            with col_p2: st.markdown(f"**Role:** {data['role']}\n\n**Joining Date:** {j_date_str}\n\n**Type:** {data['type']}\n\n**Assigned Project:** {data['project'] if data['project'] else '-'}\n\n**Skills:** {data['skills']}")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("e_error"): st.error(st.session_state.e_error)

        col_b1, col_b2 = st.columns(2)
        with col_b1: st.button("✏️ Edit Details", use_container_width=True, on_click=emp_go_edit)
        with col_b2:
            if st.button("✅ Confirm & Save", type="primary", use_container_width=True):
                status = add_new_employee(full_id, data['name'], data['email'], data['contact'], data['role'], data['project'], data['skills'], data['cert'], photo_bytes, data['type'], j_date_str)
                if status == "success": st.success("Added Successfully!"); time.sleep(1); st.rerun() 
                elif status == "duplicate_email": st.session_state.e_error = "⚠️ Email already exists!"; st.rerun()
                else: st.session_state.e_error = "⚠️ Employee ID already exists!"; st.rerun()

def create_task_log_table(df):
    html_table = "<table style='width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px;'><tr>"
    for col in ["Name", "Date", "Day", "Today's Task", "Result", "Outcome", "Extra Curriculum", "Task Status", "Submit Time"]: 
        html_table += f"<th style='padding: 12px;'>{col}</th>"
    html_table += "</tr>"
    for _, row in df.iterrows(): 
        task_val = row["Today's Task"]
        res_val = row.get("Result", "-") 
        submit_t = row.get("Submit Time", "-")
        status_val = row.get("Status", "Completed")
        status_color = "#39FF14" if status_val == "Completed" else "#ff4b4b" if status_val == "Incomplete" else "#ff9900"
        
        html_table += f"<tr><td style='padding: 12px;'><strong>{row['Name']}</strong></td><td style='padding: 12px;'>{row['Date']}</td><td style='padding: 12px;'>{row['Day']}</td><td style='padding: 12px;'>{task_val}</td><td style='padding: 12px;'>{res_val}</td><td style='padding: 12px;'>{row['Outcome']}</td><td style='padding: 12px;'>{row['Extra Curriculum']}</td><td style='padding: 12px; color: {status_color}; font-weight: bold;'>{status_val}</td><td style='padding: 12px; color: #a1a1aa;'>{submit_t}</td></tr>"
    return html_table + "</table>"

def create_attendance_table(df):
    html_table = "<table style='width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px;'><tr>"
    for col in ["Date", "Employee Name", "Check-In Time", "Check-Out Time", "Attendance Status", "Admin Comment"]: 
        html_table += f"<th style='padding: 12px;'>{col}</th>"
    html_table += "</tr>"
    for _, row in df.iterrows():
        status_val = row['Status']
        comment_val = row['Comment'] if pd.notna(row['Comment']) and str(row['Comment']).strip() != "None" else "-"
        color = "#39FF14" if status_val == 'Present' else "#ff4b4b" if status_val in ['Absent', 'Rejected'] else "#3498db" if status_val in ['Working', 'Half Day'] else "#ff9900"
        html_table += f"<tr><td style='padding: 12px;'>{row['Date']}</td><td style='padding: 12px;'><strong>{row['Employee Name']}</strong></td><td style='padding: 12px;'>{row['Check-In']}</td><td style='padding: 12px;'>{row['Check-Out']}</td><td style='padding: 12px; color: {color}; font-weight: bold;'>{status_val}</td><td style='padding: 12px; color: #a1a1aa;'>{comment_val}</td></tr>"
    return html_table + "</table>"

def show_employee_page():
    load_global_css() 
    user_role = st.session_state.get('user_role', 'Admin')
    user_email = st.session_state.get('user_email', '')
    
    st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="tertiary"] { color: #60a5fa !important; padding: 0px !important; font-weight: bold !important; background-color: transparent !important; justify-content: flex-start !important; text-align: left !important; display: flex !important; }
    div[data-testid="stButton"] button[kind="tertiary"] div { justify-content: flex-start !important; text-align: left !important; width: 100% !important; }
    div[data-testid="stButton"] button[kind="tertiary"] p { text-align: left !important; width: 100% !important; margin: 0 !important; display: flex !important; justify-content: flex-start !important; }
    div[data-testid="stButton"] button[kind="tertiary"]:hover { color: #39FF14 !important; text-decoration: underline !important; }
    </style>
    """, unsafe_allow_html=True)
    
    if "employee_db_initialized" not in st.session_state:
        init_employee_db()
        st.session_state.employee_db_initialized = True
        
    df_emps = get_all_employees(role=user_role, email=user_email)
    
    if user_role == "Admin":
        emp_names_list = df_emps['Name'].tolist() if not df_emps.empty else ["No Employees Found"]
    else:
        current_name = st.session_state.get('current_user_name', 'Unknown')
        emp_names_list = [current_name]

    if 'camera_active' not in st.session_state: st.session_state.camera_active = False

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1: st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>🧑‍💼 Employee Management</h1>", unsafe_allow_html=True)
    with head_col2:
        if user_role == "Admin":
            if st.button("➕ Add Employee", type="primary", use_container_width=True): prepare_new_employee(); add_employee_dialog()  
            
    st.markdown("---")

    tabs = ["🧑‍💼 Employee Information", "📝 Employee Log", "📧 Send Mail"]
    if user_role == "Admin":
        tabs.append("✅ Attendance Approvals")
        
    main_tab = st.radio("Navigation Menu:", tabs, horizontal=True, label_visibility="collapsed", key="main_emp_navigation")
    st.markdown("<br>", unsafe_allow_html=True)

    if main_tab == "🧑‍💼 Employee Information":
        st.markdown("<h3 style='color: #ffffff;'>🧑‍💼 Current Employees Details</h3>", unsafe_allow_html=True)
        if len(df_emps) == 0:
            st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
        else:
            st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 2, 1.5, 1.5, 1.5, 1])
            with col1: st.markdown("**ID**")
            with col2: st.markdown("**Name**")
            with col3: st.markdown("**Email**")
            with col4: st.markdown("**Contact**")
            with col5: st.markdown("**Role**")
            with col6: st.markdown("**Project**")
            with col7: st.markdown("**Status**")
            st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            for idx, row in df_emps.iterrows():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 1.5, 2, 1.5, 1.5, 1.5, 1], vertical_alignment="center")
                with c1: st.write(row['Emp ID'])
                with c2:
                    if st.button(f"👤 {row['Name']}", key=f"emp_{row['Emp ID']}", use_container_width=True, type="tertiary"): show_employee_profile(row)
                with c3: st.write(row['Email'])
                with c4: st.write(row['Contact'])
                with c5: st.write(row['Role'])
                with c6: st.write(row['Project'])
                with c7:
                    color = "#39FF14" if row['Status'] == 'Active' else "#ff9900"
                    st.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['Status']}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    elif main_tab == "✅ Attendance Approvals":
        st.markdown("<h3 style='color: #ffffff;'>✅ HR Attendance Management</h3>", unsafe_allow_html=True)
        components.html("""<script>setTimeout(function(){const inputs=window.parent.document.querySelectorAll('input[aria-label="Confirm Name"]');for(let i=0;i<inputs.length;i++){inputs[i].onpaste=function(e){e.preventDefault();return false;};}},200);</script>""", height=0, width=0)
        
        st.markdown("<h4 style='color: #39FF14; margin-top: 20px;'>1️⃣ Daily Check-In/Out Approvals</h4>", unsafe_allow_html=True)
        df_pending = get_pending_attendances()
        if len(df_pending) == 0:
            st.markdown("<p style='color: #a1a1aa; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No pending attendance records to approve.</p>", unsafe_allow_html=True)
        else:
            for idx, row in df_pending.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 3, 2], vertical_alignment="center")
                    is_checkin = (row['status'] == "Pending Check-In")
                    is_checkout = (row['status'] == "Pending Check-Out")
                    is_late = row.get('is_late', False)
                    late_count = row.get('late_count', 0)
                    is_half_day_intent = row.get('is_half_day_intent', False)
                    
                    approve_btn_text = "✅ Approve"
                    target_status = "Working" if is_checkin else "Present"
                    
                    if is_half_day_intent: approve_btn_text, target_status = "✅ Approve (Half Day)", "Half Day"
                    elif is_late:
                        if late_count > 1: approve_btn_text, target_status = "❌ Approve (Mark Absent)", "Absent"
                        else: approve_btn_text, target_status = "✅ Approve (Half Day Penalty)", "Working" if is_checkin else "Half Day"
                                
                    with c1:
                        display_photo = row.get('checkout_photo_data') if is_checkout and isinstance(row.get('checkout_photo_data'), bytes) else row.get('photo_data') if isinstance(row.get('photo_data'), bytes) else None
                        if display_photo:
                            b64_img = base64.b64encode(display_photo).decode('utf-8')
                            st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{b64_img}' width='100' height='100' style='border-radius: 8px; object-fit: cover; border: 2px solid #ff9900;'></div>", unsafe_allow_html=True)
                        else: st.markdown("📷 No Photo")
                    with c2:
                        st.markdown(f"**Employee:** {row['emp_name']}\n\n**Date:** {row['date']}")
                        req_color = "#ff4b4b" if (is_late or is_half_day_intent) else "#ff9900"
                        st.markdown(f"**Request For:** <span style='color:{req_color}; font-weight:bold;'>{row['status']}</span>", unsafe_allow_html=True)
                        if is_checkin: st.markdown(f"**Submitted Time:** {row['check_in']}")
                        else: st.markdown(f"**Check-Out Time:** {row['check_out']} (Check-In: {row['check_in']})")
                        if is_half_day_intent: st.markdown("<span style='color:#3498db; font-size: 13px;'>ℹ️ Note: Selected Half Day slot.</span>", unsafe_allow_html=True)
                        elif is_late:
                            if late_count > 1: st.markdown(f"<span style='color:#ff4b4b; font-size: 13px;'>⚠️ {late_count} Late Offenses. Will be marked Absent.</span>", unsafe_allow_html=True)
                            else: st.markdown("<span style='color:#ff9900; font-size: 13px;'>⚠️ 1st Late Offense. Penalized as Half Day.</span>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<span style='font-size:12px; color:#a1a1aa;'>Type <b>{row['emp_name']}</b> to confirm:</span>", unsafe_allow_html=True)
                        conf_input = st.text_input("Confirm Name", key=f"conf_{row['rowid']}", label_visibility="collapsed")
                        bc1, bc2 = st.columns(2)
                        with bc1:
                            if st.button(approve_btn_text, key=f"app_{row['rowid']}", use_container_width=True):
                                if ' '.join(conf_input.split()).lower() == ' '.join(row['emp_name'].split()).lower():
                                    update_attendance_status(row['rowid'], target_status); st.success("Approved!"); time.sleep(1); st.rerun()
                                else: st.error("⚠️ Type name exactly.")
                        with bc2:
                            if st.button("❌ Reject", key=f"rej_{row['rowid']}", use_container_width=True):
                                if ' '.join(conf_input.split()).lower() == ' '.join(row['emp_name'].split()).lower():
                                    update_attendance_status(row['rowid'], "Rejected"); st.error("Rejected!"); time.sleep(1); st.rerun()
                                else: st.error("⚠️ Type name exactly.")

        st.markdown("<hr style='border-color: rgba(57, 255, 20, 0.3); margin-top: 40px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #39FF14;'>2️⃣ Manual Attendance Override</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                man_emp = st.selectbox("Select Employee", emp_names_list, key="man_override_emp")
                ist = pytz.timezone('Asia/Kolkata')
                man_date = st.date_input("Select Date", datetime.datetime.now(ist).date(), key="man_override_date")
                st.markdown(f"<span style='font-size:16px; color:#a1a1aa;'>Type <b>{man_emp}</b> to confirm action:</span>", unsafe_allow_html=True)
                man_conf_input = st.text_input("Confirm Name", key="man_override_conf", label_visibility="collapsed")
            with m_col2:
                man_comment = st.text_area("Reason / Comment (Mandatory) *", height=110, key="man_override_comment")
            b_col1, b_col2, b_col3 = st.columns(3)
            with b_col1:
                if st.button("✅ Mark as Present", type="primary", use_container_width=True):
                    if not man_comment.strip(): st.error("⚠️ Reason mandatory!")
                    elif ' '.join(man_conf_input.split()).lower() != ' '.join(man_emp.split()).lower(): st.error("⚠️ Type name exactly.")
                    else: manual_override_attendance_db(man_date.strftime('%d-%b-%Y'), man_emp, 'Present', man_comment.strip()); st.success("Marked Present!"); time.sleep(1); st.rerun()
            with b_col2:
                if st.button("🌗 Mark as Half Day", use_container_width=True):
                    if not man_comment.strip(): st.error("⚠️ Reason mandatory!")
                    elif ' '.join(man_conf_input.split()).lower() != ' '.join(man_emp.split()).lower(): st.error("⚠️ Type name exactly.")
                    else: manual_override_attendance_db(man_date.strftime('%d-%b-%Y'), man_emp, 'Half Day', man_comment.strip()); st.success("Marked Half Day!"); time.sleep(1); st.rerun()
            with b_col3:
                if st.button("❌ Mark as Absent", use_container_width=True):
                    if not man_comment.strip(): st.error("⚠️ Reason mandatory!")
                    elif ' '.join(man_conf_input.split()).lower() != ' '.join(man_emp.split()).lower(): st.error("⚠️ Type name exactly.")
                    else: manual_override_attendance_db(man_date.strftime('%d-%b-%Y'), man_emp, 'Absent', man_comment.strip()); st.success("Marked Absent!"); time.sleep(1); st.rerun()

    elif main_tab == "📝 Employee Log":
        log_type = st.radio("Select Log View:", ["📅 Attendance Log", "📋 Daily Task Log"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        if log_type == "📅 Attendance Log":
            with st.container(border=True):
                st.markdown("**📸 Capture Photo & Mark Attendance**")
                col1, col2, col3 = st.columns(3)
                with col1: sel_emp = st.selectbox("Select Employee", emp_names_list, key="att_name_sel", disabled=(user_role == "Employee"))
                
                default_type_idx = 0
                if len(df_emps) > 0:
                    matching_emp = df_emps[df_emps['Name'] == sel_emp]
                    if not matching_emp.empty and matching_emp['Employment Type'].iloc[0] == "Half time": default_type_idx = 1
                
                with col2: e_type = st.selectbox("Employment Type", ["Full-Time", "Part-Time"], index=default_type_idx, disabled=(user_role == "Employee"))
                with col3: duration = st.selectbox("Duration", ["Full Day"] if e_type == "Part-Time" else ["Full Day", "Half Day"])

                col4, col5 = st.columns(2)
                with col4:
                    if e_type == "Full-Time" and duration == "Half Day": slot = st.selectbox("Slots available", ["10:00 AM to 1:30 PM", "2:00 PM to 6:00 PM"])
                    else: slot = None; st.markdown("<br>", unsafe_allow_html=True)
                
                ist_check = pytz.timezone('Asia/Kolkata')
                now = datetime.datetime.now(ist_check)
                att_check_docs = db.collection("employee_attendance").where("date", "==", now.strftime('%d-%b-%Y')).where("emp_name", "==", sel_emp).get()
                allowed_actions, is_att_disabled = ["Check-In"], False
                if att_check_docs:
                    if att_check_docs[0].to_dict().get("check_out") != "-": allowed_actions, is_att_disabled = ["Already Checked-Out"], True
                    else: allowed_actions = ["Check-Out"]

                with col5: att_action = st.selectbox("Action", allowed_actions, disabled=is_att_disabled)
                
                if not st.session_state.camera_active:
                    if st.button(" TURN ON CAMERA", use_container_width=True, type="primary"): st.session_state.camera_active = True; st.rerun()
                else:
                    if st.button(" Turn Off Camera", use_container_width=True): st.session_state.camera_active = False; st.rerun()
                        
                photo = st.camera_input("Take a picture", key="att_camera_input") if st.session_state.camera_active else None
                
                if photo:
                    current_time = now.time()
                    is_disabled, is_late_checkin, time_msg = False, False, ""
                    
                    if e_type == "Part-Time":
                        c_in_s, c_in_e, c_out_s, c_out_e = datetime.time(10, 50), datetime.time(11, 10), datetime.time(14, 50), datetime.time(15, 30)
                        msg_in, msg_out = "Check-In hasn't started.", "Check-Out only allowed 02:50 PM - 03:30 PM."
                    elif duration == "Half Day":
                        if slot == "10:00 AM to 1:30 PM":
                            c_in_s, c_in_e, c_out_s, c_out_e = datetime.time(9, 50), datetime.time(10, 10), datetime.time(14,00), datetime.time(14,30)
                            msg_in, msg_out = "Check-In hasn't started.", "Check-Out only allowed 02:00 PM - 2:30 PM."
                        else: 
                            c_in_s, c_in_e, c_out_s, c_out_e = datetime.time(13, 50), datetime.time(14, 10), datetime.time(18,25), datetime.time(19, 00)
                            msg_in, msg_out = "Check-In hasn't started.", "Check-Out only allowed 06:25 PM - 07:00 PM."
                    else: 
                        c_in_s, c_in_e, c_out_s, c_out_e = datetime.time(9, 50), datetime.time(10, 10), datetime.time(18,25), datetime.time(19, 00)
                        msg_in, msg_out = "Check-In hasn't started.", "Check-Out only allowed 06:25 PM - 07:00 PM."
                    
                    if att_action == "Check-In":
                        if current_time < c_in_s: is_disabled, time_msg = True, msg_in
                        elif current_time > c_in_e: is_late_checkin, time_msg = True, "Note: You are late. HR Approval required."
                    elif att_action == "Check-Out" and not (c_out_s <= current_time <= c_out_e):
                        is_disabled, time_msg = True, msg_out
                    
                    if is_disabled or is_att_disabled: 
                        if time_msg: st.warning(time_msg)
                    elif is_late_checkin: st.warning(time_msg)
                        
                    if st.button(f" Confirm {att_action}", use_container_width=True, disabled=(is_disabled or is_att_disabled)):
                        photo_bytes = photo.getvalue()
                        try:
                            from PIL import Image; import io
                            img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
                            img.thumbnail((500, 500))
                            out_buffer = io.BytesIO()
                            img.save(out_buffer, format="JPEG", quality=60)
                            photo_bytes = out_buffer.getvalue()
                        except: pass
                        
                        if att_action == "Check-In":
                            if mark_checkin_db(now.strftime('%d-%b-%Y'), sel_emp, now.strftime('%I:%M %p'), photo_bytes, is_late_checkin, (duration=="Half Day")):
                                st.success("Check-In requested. Sent for HR Approval!"); st.session_state.camera_active = False; st.rerun()
                            else: st.warning("Already Checked-In today!")
                        elif att_action == "Check-Out":
                            if mark_checkout_db(now.strftime('%d-%b-%Y'), sel_emp, now.strftime('%I:%M %p'), photo_bytes) == "success":
                                st.success("Check-Out requested!"); st.session_state.camera_active = False; st.rerun()
                            else: st.warning("Please Check-In first!")

            st.markdown("<h4 style='color: #ffffff; margin-top: 35px;'>🗓️ Select Month & Year</h4>", unsafe_allow_html=True)
            cal_col1, cal_col2 = st.columns(2)
            ist_now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
            with cal_col1:
                month_opts = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                sel_month_name = st.selectbox("Select Month", month_opts, index=ist_now.month - 1)
                sel_month = month_opts.index(sel_month_name) + 1
            with cal_col2:
                sel_year = st.selectbox("Select Year", [ist_now.year - 1, ist_now.year, ist_now.year + 1], index=1)

            st.markdown(f"<h4 style='color: #ffffff; margin-top: 25px;'>📊 {sel_month_name} {sel_year} Stats</h4>", unsafe_allow_html=True)
            present, absent, off, half_day, late_count = get_month_stats(sel_emp, sel_month, sel_year)
            stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
            stat_col1.markdown(f"<div style='background:rgba(57, 255, 20, 0.1); border:1px solid #39FF14; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#39FF14; margin:0;'>{present}</h3><p style='color:#ffffff; margin:0; font-size:14px;'>Present</p></div>", unsafe_allow_html=True)
            stat_col2.markdown(f"<div style='background:rgba(52, 152, 219, 0.1); border:1px solid #3498db; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#3498db; margin:0;'>{half_day}</h3><p style='color:#ffffff; margin:0; font-size:14px;'>Half Day</p></div>", unsafe_allow_html=True)
            stat_col3.markdown(f"<div style='background:rgba(255, 75, 75, 0.1); border:1px solid #ff4b4b; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#ff4b4b; margin:0;'>{absent}</h3><p style='color:#ffffff; margin:0; font-size:14px;'>Absent</p></div>", unsafe_allow_html=True)
            stat_col4.markdown(f"<div style='background:rgba(255, 153, 0, 0.1); border:1px solid #ff9900; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#ff9900; margin:0;'>{late_count}</h3><p style='color:#ffffff; margin:0; font-size:14px;'>Late</p></div>", unsafe_allow_html=True)
            stat_col5.markdown(f"<div style='background:rgba(136, 136, 136, 0.1); border:1px solid #888888; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#888888; margin:0;'>{off}</h3><p style='color:#ffffff; margin:0; font-size:14px;'>Off</p></div>", unsafe_allow_html=True)
            
            st.markdown(generate_calendar_html(sel_emp, sel_year, sel_month), unsafe_allow_html=True)

        elif log_type == "📋 Daily Task Log":
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(ist)
            
            log_date_obj = now - datetime.timedelta(days=1) if now.hour < 9 else now
            log_date, log_day = log_date_obj.strftime('%d-%b-%Y'), log_date_obj.strftime('%A')
            is_task_time = (now.hour > 18) or (now.hour == 18 and now.minute >= 25) or (now.hour < 9)
            
            with st.container(border=True):
                col_name, col_date, col_day = st.columns(3)
                with col_name: sel_emp_task = st.selectbox("Select Name", emp_names_list, disabled=(user_role == "Employee"))
                with col_date: st.text_input("Date", value=log_date, disabled=True)
                with col_day: st.text_input("Day", value=log_day, disabled=True)
                
                current_task_data = get_daily_task_db(log_date, sel_emp_task)
                
                if not current_task_data:
                    st.markdown("<h4 style='color: #39FF14;'>Morning Phase: Plan Your Task</h4>", unsafe_allow_html=True)
                    task_input = st.text_area("What are your planned tasks for today? *", height=100)
                    if st.button(" Submit Planned Task", use_container_width=True, type="primary"):
                        if task_input.strip(): save_planned_task_db(log_date, log_day, sel_emp_task, task_input); st.success("Submitted!"); time.sleep(1); st.rerun()
                        else: st.error("Please enter tasks.")
                elif current_task_data.get("status") == "Pending":
                    st.markdown("<h4 style='color: #ff9900;'> Evening Phase: Task Log Update</h4>", unsafe_allow_html=True)
                    st.info(f"**Your Planned Task:** {current_task_data.get('task')}")
                    if not is_task_time: st.warning("⚠️ Evening Task Update is only active from 6:25 PM to 9:00 AM.")
                    
                    res_in = st.text_area("Result *", height=80)
                    out_in = st.text_area("Outcome *", height=80)
                    ext_in = st.text_area("Extra Curriculum (Optional)", height=60)
                    
                    col_y, col_n = st.columns(2)
                    with col_y: btn_yes = st.button("✅ Yes (Completed)", use_container_width=True, type="primary", disabled=not is_task_time)
                    with col_n: btn_no = st.button("❌ No (Incomplete)", use_container_width=True, disabled=not is_task_time)

                    if btn_yes or btn_no:
                        if not res_in.strip() or not out_in.strip(): st.error("Fill Result and Outcome.")
                        else:
                            update_actual_task_db(log_date, sel_emp_task, res_in, out_in, ext_in if ext_in.strip() else "-", "Completed" if btn_yes else "Incomplete", now.strftime('%I:%M %p'))
                            st.success("Task updated!"); time.sleep(1); st.rerun()
                else: st.success(f"✅ You have marked today's task as **{current_task_data.get('status')}**.")

            st.markdown("<h4 style='color: #ffffff; margin-top: 35px;'>📅 View Past Tasks</h4>", unsafe_allow_html=True)
            view_date_col, view_emp_col = st.columns(2)
            with view_date_col:
                selected_view_date = st.date_input("Select Date", now.date(), key="view_task_date")
            with view_emp_col:
                sel_view_emp = st.selectbox("Select Employee", ["All"] + emp_names_list if user_role == "Admin" else emp_names_list, disabled=(user_role == "Employee"))
                    
            df_all_logs = get_all_task_logs_db(emp_name=sel_view_emp if sel_view_emp != "All" else None, role=user_role)
            if not df_all_logs.empty:
                df_day_logs = df_all_logs[df_all_logs['Date'] == selected_view_date.strftime('%d-%b-%Y')]
                if sel_view_emp != "All" and user_role == "Admin": df_day_logs = df_day_logs[df_day_logs['Name'] == sel_view_emp]
                if len(df_day_logs) > 0: st.markdown(create_task_log_table(df_day_logs), unsafe_allow_html=True)
                else: st.markdown("<p style='color:#a1a1aa;'>No logs found for this date.</p>", unsafe_allow_html=True)

    elif main_tab == "📧 Send Mail":
        st.markdown("<h3 style='color: #ffffff;'>📧 Send Mail to HR</h3>", unsafe_allow_html=True)
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1: st.text_input("From (Your Email)", value=user_email, disabled=True)
            with c2: st.text_input("To (HR Email)", value="hr@pararobo.in", disabled=True)
            mail_subject = st.text_input("Subject *")
            mail_body = st.text_area("Message / Remarks", height=120)
            mail_attachment = st.file_uploader("Attach CSV File *", type=['csv'])
            
            if st.button("📤 Send Mail", type="primary", use_container_width=True):
                if not mail_attachment: st.error("⚠️ Attach CSV!")
                else:
                    with st.spinner("Sending..."):
                        try:
                            msg = EmailMessage()
                            msg['Subject'] = mail_subject if mail_subject.strip() else f"Task Logs - {st.session_state.get('current_user_name', 'Employee')}"
                            msg['From'] = f"Alpha CRM <{SMTP_EMAIL}>"
                            msg['To'] = "hr@pararobo.in"
                            msg.set_content(f"Remarks:\n{mail_body}\n\nBest Regards,\n{st.session_state.get('current_user_name', 'Employee')}")
                            msg.add_attachment(mail_attachment.getvalue(), maintype='text', subtype='csv', filename="TaskLogs.csv")
                            
                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls(); server.login(SMTP_EMAIL, SMTP_PASSWORD)
                            server.send_message(msg); server.quit()
                            st.success("✅ Mail sent successfully!")
                        except Exception as e: st.error(f"⚠️ Error: {e}")