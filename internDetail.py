# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import datetime
import time
import base64
import re  
import calendar 
import streamlit.components.v1 as components
from utils import load_global_css
import pytz

# 🟢 NAYA LOGIC: Firebase Database (db) aur config
from config import is_valid_email, db

# ==========================================
# HELPER FUNCTIONS
# ==========================================

# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

def init_intern_db():
    # Firestore mein collections automatically create ho jate hain jab data add hota hai
    pass

def sync_intern_projects():
    try:
        completed_projects = []
        proj_docs = db.collection("projects").where("status", "==", "Completed").get()
        for doc in proj_docs:
            completed_projects.append(doc.to_dict().get("project_name"))

        if not completed_projects: return

        intern_docs = db.collection("interns").get()
        for doc in intern_docs:
            data = doc.to_dict()
            assigned = data.get("assigned_project")
            comp = data.get("completed_projects", "")
            
            if assigned in completed_projects:
                new_comp = assigned if comp in ["-", "", None] else f"{comp}, {assigned}"
                doc.reference.update({"completed_projects": new_comp, "assigned_project": "-"})
    except Exception:
        pass 

def get_all_interns(role="Admin", email=""):
    if role == "Intern":
        docs = db.collection("interns").where("email", "==", email).get()
    else:
        docs = db.collection("interns").get()
        
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        photo_bytes = base64.b64decode(d.get("photo_data")) if d.get("photo_data") else None
        
        data_list.append({
            'Intern ID': d.get('intern_id', ''), 'Name': d.get('name', ''), 
            'Email': d.get('email', ''), 'Contact': d.get('contact', ''), 
            'Role': d.get('role', ''), 'Assigned Project': d.get('assigned_project', ''), 
            'Completed Projects': d.get('completed_projects', ''), 'Mentor': d.get('mentor', ''), 
            'Duration': d.get('duration', ''), 'Status': d.get('status', ''), 
            'College': d.get('college', ''), 'Branch': d.get('branch', ''), 
            'Semester': d.get('semester', ''), 'Skills': d.get('skills', ''), 
            'photo_data': photo_bytes, 'Interview Process': d.get('interview_process', ''), 
            'Internship Type': d.get('internship_type', '')
        })
        
    df = pd.DataFrame(data_list)
    if not df.empty:
        df = df.sort_values(by='Intern ID')
    return df

def get_active_onboard_projects():
    try:
        docs = db.collection("projects").where("status", "in", ["Active", "Onboard"]).get()
        projects = {doc.to_dict().get("project_name"): doc.to_dict().get("status") for doc in docs}
        return projects
    except Exception:
        return {}

def add_new_intern(i_id, name, email, contact, role, project, comp_proj, mentor, duration, status, college, branch, sem, skills, photo, process, i_type):
    # Check duplicate email
    if db.collection("interns").where("email", "==", email).get():
        return "duplicate_email"
        
    doc_ref = db.collection("interns").document(i_id)
    if doc_ref.get().exists:
        return "duplicate_id"  

    photo_b64 = base64.b64encode(photo).decode('utf-8') if photo else ""
    
    doc_ref.set({
        "intern_id": i_id, "name": name, "email": email, "contact": contact, 
        "role": role, "assigned_project": project, "completed_projects": comp_proj, 
        "mentor": mentor, "duration": duration, "status": status, "college": college, 
        "branch": branch, "semester": sem, "skills": skills, "photo_data": photo_b64, 
        "interview_process": process, "internship_type": i_type, "password": ""
    })
    return "success"

def delete_intern(i_id):
    db.collection("interns").document(i_id).delete()

def update_intern_profile_db(intern_id, role, project, mentor, status):
    db.collection("interns").document(intern_id).update({
        "role": role, "assigned_project": project, "mentor": mentor, "status": status
    })

# ==========================================
# ADVANCED ATTENDANCE & LOG DB FUNCTIONS
# ==========================================

def get_month_stats(intern_name):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    current_month = now.month
    current_year = now.year
    today = now.date()
    
    docs = db.collection("intern_attendance").where("intern_name", "==", intern_name).get()
    att_dict = {doc.to_dict().get("date"): doc.to_dict().get("status") for doc in docs}
    
    present, absent, off = 0, 0, 0
    for day in range(1, today.day + 1):
        d = datetime.date(current_year, current_month, day)
        d_str = d.strftime('%d-%b-%Y')
        
        if d.weekday() >= 5: 
            off += 1
            continue
        
        status = att_dict.get(d_str)
        if status == 'Present': present += 1
        elif status in ['Working', 'Pending Check-In', 'Pending Check-Out'] and d < today: absent += 1
        elif status in ['Working', 'Pending Check-In', 'Pending Check-Out'] and d == today: pass
        else: absent += 1
            
    return present, absent, off

def generate_calendar_html(intern_name, year, month):
    docs = db.collection("intern_attendance").where("intern_name", "==", intern_name).get()
    att_dict = {doc.to_dict().get("date"): doc.to_dict().get("status") for doc in docs}
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
                elif i >= 5: display_status, badge_class = "Off", "status-off"
                else:
                    if status == 'Present': display_status, badge_class = "Present", "status-present"
                    elif status in ['Pending Check-In', 'Pending Check-Out']: display_status, badge_class = "Pending HR", "status-pending"
                    elif status == 'Working' and d < today: display_status, badge_class = "Absent", "status-absent"
                    elif status == 'Working' and d == today: display_status, badge_class = "Working", "status-working"
                    else: display_status, badge_class = "Absent", "status-absent"
                        
                badge_html = f"<div class='status-badge {badge_class}'>{display_status}</div>" if display_status else ""
                html += f"<td><div class='day-num'>{day}</div>{badge_html}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def mark_checkin_db(date_str, intern_name, time_str, photo_bytes):
    docs = db.collection("intern_attendance").where("date", "==", date_str).where("intern_name", "==", intern_name).get()
    if docs: return False 
    
    photo_b64 = base64.b64encode(photo_bytes).decode('utf-8') if photo_bytes else ""
    db.collection("intern_attendance").add({
        "date": date_str, "intern_name": intern_name, "check_in": time_str, 
        "check_out": "-", "status": "Pending Check-In", "photo_data": photo_b64, "hr_comment": ""
    })
    return True

def mark_checkout_db(date_str, intern_name, time_str, photo_bytes):
    docs = db.collection("intern_attendance").where("date", "==", date_str).where("intern_name", "==", intern_name).get()
    if not docs: return "not_checked_in"
    
    photo_b64 = base64.b64encode(photo_bytes).decode('utf-8') if photo_bytes else ""
    docs[0].reference.update({"check_out": time_str, "status": "Pending Check-Out", "checkout_photo_data": photo_b64})
    return "success"

def manual_override_attendance_db(date_str, intern_name, status, comment):
    docs = db.collection("intern_attendance").where("date", "==", date_str).where("intern_name", "==", intern_name).get()
    ist = pytz.timezone('Asia/Kolkata')
    time_str = datetime.datetime.now(ist).strftime('%I:%M %p')
    
    if docs:
        docs[0].reference.update({
            "status": status, "check_in": time_str, "check_out": time_str, "hr_comment": comment
        })
    else:
        db.collection("intern_attendance").add({
            "date": date_str, "intern_name": intern_name, "check_in": time_str, 
            "check_out": time_str, "status": status, "photo_data": "", "hr_comment": comment
        })

def get_today_attendance_db(date_str, intern_name=None, role="Admin"):
    if role == "Intern":
        docs = db.collection("intern_attendance").where("date", "==", date_str).where("intern_name", "==", intern_name).get()
    else:
        docs = db.collection("intern_attendance").where("date", "==", date_str).get()
        
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            "Date": d.get("date"), "Intern Name": d.get("intern_name"), 
            "Check-In": d.get("check_in"), "Check-Out": d.get("check_out"), 
            "Status": d.get("status"), "Comment": d.get("hr_comment", "-")
        })
    df = pd.DataFrame(data_list)
    return df

def get_pending_attendances():
    # Firestore doesnt support OR queries directly in Python easily without multiple calls
    docs1 = db.collection("intern_attendance").where("status", "==", "Pending Check-In").get()
    docs2 = db.collection("intern_attendance").where("status", "==", "Pending Check-Out").get()
    docs = docs1 + docs2
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        photo_bytes = base64.b64decode(d.get("photo_data")) if d.get("photo_data") else None
        checkout_photo_bytes = base64.b64decode(d.get("checkout_photo_data")) if d.get("checkout_photo_data") else None
        
        data_list.append({
            "rowid": doc.id, "date": d.get("date"), "intern_name": d.get("intern_name"), 
            "check_in": d.get("check_in"), "check_out": d.get("check_out"), 
            "status": d.get("status"), "photo_data": photo_bytes, "checkout_photo_data": checkout_photo_bytes
        })
    return pd.DataFrame(data_list)

def update_attendance_status(rowid, new_status):
    db.collection("intern_attendance").document(rowid).update({"status": new_status})

def save_task_log_db(date_str, day_str, intern_name, task, result, outcome, extra, submit_time):
    db.collection("intern_daily_tasks").add({
        "date": date_str, "day": day_str, "intern_name": intern_name, "task": task,
        "result": result, "outcome": outcome, "extra_curriculum": extra, "submit_time": submit_time
    })

def get_all_task_logs_db(intern_name=None, role="Admin"):
    if role == "Intern":
        docs = db.collection("intern_daily_tasks").where("intern_name", "==", intern_name).get()
    else:
        docs = db.collection("intern_daily_tasks").get()
        
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            "Name": d.get("intern_name"), "Date": d.get("date"), "Day": d.get("day"), 
            "Today's Task": d.get("task"), "Result": d.get("result", "-"), 
            "Outcome": d.get("outcome"), "Extra Curriculum": d.get("extra_curriculum"),
            "Submit Time": d.get("submit_time", "-")
        })
        
    df = pd.DataFrame(data_list)
    # 🟢 NAYA LOGIC: Tasks ko Hamesha Newest Date First Order mein sort karega (e.g. 16, 15, 14...)
    if not df.empty:
        df['Sort_Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y', errors='coerce')
        df = df.sort_values(by=['Sort_Date', 'Submit Time'], ascending=[False, False]).drop(columns=['Sort_Date'])
    return df

def check_daily_task_exists_db(date_str, intern_name):
    docs = db.collection("intern_daily_tasks").where("date", "==", date_str).where("intern_name", "==", intern_name).get()
    return len(docs) > 0

# ==========================================
# SAFE MEMORY LOGIC 
# ==========================================
def int_go_preview():
    p = st.session_state
    ist = pytz.timezone('Asia/Kolkata')
    today_ist = datetime.datetime.now(ist).date()
    
    name = p.get("i_name_in", "")
    email = p.get("i_email_in", "").strip() 
    contact = p.get("i_contact_in", "")
    num = p.get("i_num_in", "")
    process = p.get("i_process_in", "Walk in interview")
    i_type = p.get("i_type_in", "Full time")
    
    if process == "College Through":
        college, branch, sem = p.get("i_college_in", ""), p.get("i_branch_in", ""), p.get("i_sem_in", "1st Semester")
        valid_college = bool(college and branch) 
    else:
        college, branch, sem = "-", "-", "-" 
        valid_college = True
        
    role = p.get("i_role_in", "AI/ML Developer")
    skills = "-" 
    project = p.get("i_project_in", "")
    mentor = p.get("i_mentor_in", "Prajatak sir")
    start, end = p.get("i_start_in", today_ist), p.get("i_end_in", today_ist)

    if name and email and contact and num and valid_college:
        if not name.replace(" ", "").isalpha(): p.int_error = "⚠️ Name should only contain alphabets (No numbers or symbols allowed)."
        elif not (contact.isdigit() and len(contact) == 10 and int(contact[0]) > 6): p.int_error = "⚠️ Contact number must be exactly 10 digits and start with a number greater than 6."
        elif not is_valid_email(email): p.int_error = "⚠️ Invalid Email Format! Please enter a valid email ID."
        elif len(num) != 3 or not num.isdigit(): p.int_error = "⚠️ ID Number must be exactly 3 digits (e.g. 001)."
        elif end < start: p.int_error = "⚠️ End Date cannot be before Start Date!"
        else:
            p.int_step = "preview"; p.int_error = ""
            p.safe_int_data = {'name': name, 'email': email, 'contact': contact, 'num': num, 'process': process, 'type': i_type, 'college': college, 'branch': branch, 'sem': sem, 'role': role, 'skills': skills, 'project': project, 'mentor': mentor, 'start': start, 'end': end}
            if p.get("i_photo_in") is not None: p.int_photo_data = p.i_photo_in.getvalue()
    else:
        p.int_error = "⚠️ Please fill all mandatory fields (*)."

def int_go_edit(): st.session_state.int_step = "form"

def prepare_new_intern():
    st.session_state.int_step = "form"; st.session_state.int_error = ""; st.session_state.int_photo_data = None; st.session_state.safe_int_data = {} 
    for k in ["i_name_in", "i_contact_in", "i_college_in", "i_branch_in", "i_skills_in", "i_email_in", "i_num_in", "i_project_in", "i_photo_in"]:
        if k in st.session_state: del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================
@st.dialog("Intern Profile")
def show_intern_profile(intern):
    user_role = st.session_state.get('user_role', 'Admin')
    img_src = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    photo_val = intern.get('photo_data')
    if photo_val is not None and isinstance(photo_val, (bytes, bytearray)) and len(photo_val) > 0:
        b64_img = base64.b64encode(photo_val).decode('utf-8')
        img_src = f"data:image/png;base64,{b64_img}"

    st.markdown(f"<div style='text-align: center;'><img src='{img_src}' width='120' height='120' style='margin-bottom: 10px; border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'><h3 style='margin: 0px; color: #ffffff;'>{intern['Name']}</h3></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Name:** {intern['Name']}\n\n**Email:** {intern['Email']}\n\n**Contact:** {intern['Contact']}\n\n**Interview Process:** {intern['Interview Process']}\n\n**Internship Type:** {intern['Internship Type']}")
    with col_b:
        st.markdown(f"**Intern ID:** {intern['Intern ID']}\n\n**Role:** {intern['Role']}\n\n**Mentor:** {intern['Mentor']}\n\n**College:** {intern['College']}\n\n**Branch/Sem:** {intern['Branch']} ({intern['Semester']})")
        
    st.markdown("---")
    
    duration_val = intern['Duration']
    ist = pytz.timezone('Asia/Kolkata')
    today_ist = datetime.datetime.now(ist).date()
    try:
        s_str = duration_val.split(" to ")[0]
        s_dt = datetime.datetime.strptime(s_str, '%d-%b-%Y').date()
        t_end = s_dt + datetime.timedelta(days=7)
        train_disp = f"{s_str} to {t_end.strftime('%d-%b-%Y')}"
        project_disabled = today_ist <= t_end
    except:
        train_disp = "-"
        project_disabled = False

    st.markdown(f"**Training Session (7 Days):** {train_disp}\n\n**Assigned Project:** {intern['Assigned Project']}\n\n**Completed Projects:** {intern['Completed Projects']}\n\n**Duration:** {intern['Duration']}")
    
    status_color = "#39FF14" if intern['Status'] in ['Active', 'Completed'] else "#ff9900"
    st.markdown(f"**Status:** <span style='color: {status_color}; font-weight: bold;'>{intern['Status']}</span>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if user_role == 'Admin':
        with st.expander("✏️ Edit Profile (HR Only)"):
            st.markdown("<p style='font-size:14px; color:#a1a1aa;'>Update the professional details for this intern below.</p>", unsafe_allow_html=True)
            r_opts = ["AI/ML Developer", "FullStack Developer", "Word Press Developer", "Frontend Developer", "Backend Developer", "Digital Marketing"]
            e_role = st.selectbox("Internship Role", r_opts, index=r_opts.index(intern['Role']) if intern['Role'] in r_opts else 0, key=f"e_role_{intern['Intern ID']}")
            if project_disabled: st.warning("⚠️ Training is still active. Project assignment will unlock after 7 days.")
                
            proj_dict = get_active_onboard_projects()
            avail_projs = ["-"] + list(proj_dict.keys())
            if intern['Assigned Project'] not in avail_projs and intern['Assigned Project'] != "": avail_projs.insert(0, intern['Assigned Project'])
                
            e_proj_idx = avail_projs.index(intern['Assigned Project']) if intern['Assigned Project'] in avail_projs else 0
            def format_proj_edit(p): return f"{p} ({proj_dict[p]})" if (p != "-" and p in proj_dict) else p
                
            e_proj = st.selectbox("Assigned Project", avail_projs, index=e_proj_idx, disabled=project_disabled, format_func=format_proj_edit, key=f"e_proj_{intern['Intern ID']}")
            m_opts = ["Prajatak sir", "Vikrant sir", "Shahid sir", "Arya sir"]
            e_mentor = st.selectbox("Assigned Mentor", m_opts, index=m_opts.index(intern['Mentor']) if intern['Mentor'] in m_opts else 0, key=f"e_mentor_{intern['Intern ID']}")
            s_opts = ["Active", "Completed", "Inactive"]
            e_status = st.selectbox("Status", s_opts, index=s_opts.index(intern['Status']) if intern['Status'] in s_opts else 0, key=f"e_status_{intern['Intern ID']}")
            
            if st.button("Save Changes", type="primary", use_container_width=True, key=f"save_{intern['Intern ID']}"):
                update_intern_profile_db(intern['Intern ID'], e_role, e_proj, e_mentor, e_status)
                st.success("Profile Updated Successfully!"); time.sleep(1); st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(" Remove Intern (Danger Zone)"):
            st.error("⚠️ Warning: This will permanently delete the intern.")
            st.markdown(f"To confirm, type <span style='user-select: none; pointer-events: none; font-weight: bold; color: #ffffff;'>{intern['Name']}</span> below:", unsafe_allow_html=True)
            confirm_input = st.text_input("Type here to confirm:", key=f"del_{intern['Intern ID']}")

            if st.button(" Permanently Delete", type="primary", use_container_width=True):
                # Extra spacing fix for Name Confirmation
                if ' '.join(confirm_input.split()).lower() == ' '.join(intern['Name'].split()).lower():
                    delete_intern(intern['Intern ID']); st.success("Removed successfully!"); time.sleep(1.5); st.rerun() 
                else: st.warning("⚠️ Type name exactly to delete.")

    if st.button("Close Profile", use_container_width=True, key="close_intern_profile"): st.rerun() 

@st.dialog("➕ Add New Intern", width="large")
def add_intern_dialog():
    if "safe_int_data" not in st.session_state: st.session_state.safe_int_data = {}
    draft = st.session_state.safe_int_data

    ist = pytz.timezone('Asia/Kolkata')
    today_ist = datetime.datetime.now(ist).date()

    if st.session_state.int_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Fill out the form below. Fields marked with * are mandatory.</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name *", value=draft.get('name', ''), key="i_name_in")
            st.text_input("Contact Number *", value=draft.get('contact', ''), key="i_contact_in")
            p_opts = ["Walk in interview", "College Through"]
            st.selectbox("Interview Process *", p_opts, index=p_opts.index(draft.get('process', "Walk in interview")) if draft.get('process') in p_opts else 0, key="i_process_in")
        with col2:
            st.text_input("Email ID *", value=draft.get('email', ''), key="i_email_in")
            c_id1, c_id2 = st.columns([1, 3])
            c_id1.text_input("Prefix", value="INT-", disabled=True)
            c_id2.text_input("ID Number (3 digits) *", placeholder="001", value=draft.get('num', ''), key="i_num_in")
            t_opts = ["Full time", "Half time"]
            st.selectbox("Internship Type *", t_opts, index=t_opts.index(draft.get('type', "Full time")) if draft.get('type') in t_opts else 0, key="i_type_in")

        if st.session_state.get("i_process_in", "Walk in interview") == "College Through":
            st.markdown("---")
            st.markdown("<p style='color: #39FF14; font-size: 14px; font-weight: bold;'>College Details</p>", unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            with col3:
                st.text_input("College / University *", value=draft.get('college', ''), key="i_college_in")
                sem_opts = ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "5th Semester", "6th Semester", "7th Semester", "8th Semester", "9th Semester"]
                st.selectbox("Semester *", sem_opts, index=sem_opts.index(draft.get('sem', "1st Semester")) if draft.get('sem') in sem_opts else 0, key="i_sem_in")
            with col4:
                st.text_input("Branch *", value=draft.get('branch', ''), key="i_branch_in")
                st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown("---")
        col5, col6 = st.columns(2)
        
        with col6:
            d_col1, d_col2 = st.columns(2)
            s_date = d_col1.date_input("Start Date *", value=draft.get('start', today_ist), key="i_start_in")
            d_col2.date_input("End Date *", value=draft.get('end', today_ist), key="i_end_in")
            m_opts = ["Prajatak sir", "Vikrant sir", "Shahid sir", "Arya sir"]
            st.selectbox("Assigned Mentor *", m_opts, index=m_opts.index(draft.get('mentor', "Prajatak sir")) if draft.get('mentor') in m_opts else 0, key="i_mentor_in")
            st.file_uploader("Upload Photo (Optional)", type=['jpg', 'jpeg', 'png'], key="i_photo_in")

        with col5:
            r_opts = ["AI/ML Developer", "FullStack Developer", "Word Press Developer", "Frontend Developer", "Backend Developer", "Digital Marketing"]
            st.selectbox("Internship Role *", r_opts, index=r_opts.index(draft.get('role', "AI/ML Developer")) if draft.get('role') in r_opts else 0, key="i_role_in")
            
            train_end = s_date + datetime.timedelta(days=7)
            train_str = f"{s_date.strftime('%d-%b-%Y')} to {train_end.strftime('%d-%b-%Y')}"
            st.text_input("Compulsory Training Session (7 Days)", value=train_str, disabled=True)
            
            project_disabled = today_ist <= train_end
            proj_dict = get_active_onboard_projects()
            avail_projs = ["-"] + list(proj_dict.keys())
            curr_proj = draft.get('project', '-')
            if curr_proj not in avail_projs and curr_proj != "": avail_projs.insert(0, curr_proj)
            proj_idx = avail_projs.index(curr_proj) if curr_proj in avail_projs else 0
            
            def format_proj_add(p): return f"{p} ({proj_dict[p]})" if (p != "-" and p in proj_dict) else p
            st.selectbox("Assigned Project (After 7 Days)", avail_projs, index=proj_idx, format_func=format_proj_add, key="i_project_in", disabled=project_disabled)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("int_error"): st.error(st.session_state.int_error)
        st.button("👁️ Preview Details", type="primary", use_container_width=True, on_click=int_go_preview)

    elif st.session_state.int_step == "preview":
        data = st.session_state.safe_int_data
        full_id = f"INT-{data['num']}"
        i_duration_str = f"{data['start'].strftime('%d-%b-%Y')} to {data['end'].strftime('%d-%b-%Y')}"
        
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Intern Details</h3>", unsafe_allow_html=True)
        photo_bytes = st.session_state.get('int_photo_data')
        if photo_bytes is not None:
            b64_p = base64.b64encode(photo_bytes).decode('utf-8')
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{b64_p}' width='100' height='100' style='border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1: st.markdown(f"**Full Name:** {data['name']}\n\n**Email ID:** {data['email']}\n\n**Contact Number:** {data['contact']}\n\n**Interview Process:** {data['process']}\n\n**Internship Type:** {data['type']}\n\n**Intern ID:** <span style='color:#39FF14;'>{full_id}</span>", unsafe_allow_html=True)
            with col_p2: 
                train_end_prev = data['start'] + datetime.timedelta(days=7)
                train_prev_str = f"{data['start'].strftime('%d-%b-%Y')} to {train_end_prev.strftime('%d-%b-%Y')}"
                st.markdown(f"**Role:** {data['role']}\n\n**Training Session:** {train_prev_str}\n\n**Assigned Project:** {data['project'] if data['project'] else '-'}\n\n**Assigned Mentor:** {data['mentor']}\n\n**Duration:** {i_duration_str}")
                
        if data['process'] == "College Through": st.markdown(f"**College Details:** {data['college']} | Branch: {data['branch']} | Sem: {data['sem']}")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("int_error"): st.error(st.session_state.int_error)

        col_b1, col_b2 = st.columns(2)
        with col_b1: st.button("✏️ Edit Details", use_container_width=True, on_click=int_go_edit)
        with col_b2:
            if st.button("✅ Confirm & Save", type="primary", use_container_width=True):
                status = add_new_intern(full_id, data['name'], data['email'], data['contact'], data['role'], data['project'], "-", data['mentor'], i_duration_str, "Active", data['college'], data['branch'], data['sem'], data['skills'], photo_bytes, data['process'], data['type'])
                if status == "success": st.success("Added Successfully!"); time.sleep(1); st.rerun() 
                elif status == "duplicate_email": st.session_state.int_error = "⚠️ Email already exists!"; st.rerun()
                else: st.session_state.int_error = "⚠️ Intern ID already exists!"; st.rerun()

def create_task_log_table(df):
    html_table = "<table style='width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px;'><tr>"
    for col in ["Name", "Date", "Day", "Today's Task", "Result", "Outcome", "Extra Curriculum", "Submit Time"]: 
        html_table += f"<th style='padding: 12px;'>{col}</th>"
    html_table += "</tr>"
    for _, row in df.iterrows(): 
        task_val = row["Today's Task"]
        res_val = row.get("Result", "-") 
        submit_t = row.get("Submit Time", "-")
        html_table += f"<tr><td style='padding: 12px;'><strong>{row['Name']}</strong></td><td style='padding: 12px;'>{row['Date']}</td><td style='padding: 12px;'>{row['Day']}</td><td style='padding: 12px;'>{task_val}</td><td style='padding: 12px;'>{res_val}</td><td style='padding: 12px;'>{row['Outcome']}</td><td style='padding: 12px;'>{row['Extra Curriculum']}</td><td style='padding: 12px; color: #39FF14; font-weight: bold;'>{submit_t}</td></tr>"
    return html_table + "</table>"

def create_attendance_table(df):
    html_table = "<table style='width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px;'><tr>"
    for col in ["Date", "Intern Name", "Check-In Time", "Check-Out Time", "Attendance Status", "Admin Comment"]: 
        html_table += f"<th style='padding: 12px;'>{col}</th>"
    html_table += "</tr>"
    for _, row in df.iterrows():
        status_val = row['Status']
        comment_val = row['Comment'] if pd.notna(row['Comment']) and str(row['Comment']).strip() != "None" else "-"
        color = "#39FF14" if status_val == 'Present' else "#ff4b4b" if status_val in ['Absent', 'Rejected'] else "#3498db" if status_val == 'Working' else "#ff9900"
        html_table += f"<tr><td style='padding: 12px;'>{row['Date']}</td><td style='padding: 12px;'><strong>{row['Intern Name']}</strong></td><td style='padding: 12px;'>{row['Check-In']}</td><td style='padding: 12px;'>{row['Check-Out']}</td><td style='padding: 12px; color: {color}; font-weight: bold;'>{status_val}</td><td style='padding: 12px; color: #a1a1aa;'>{comment_val}</td></tr>"
    return html_table + "</table>"

# ==========================================
# MAIN PAGE RENDER
# ==========================================
def show_intern_page():
    load_global_css() 
    user_role = st.session_state.get('user_role', 'Admin')
    user_email = st.session_state.get('user_email', '')
    
    st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="tertiary"] { color: #60a5fa !important; padding: 0px !important; font-weight: bold !important; background-color: transparent !important; justify-content: flex-start !important; text-align: left !important; }
    div[data-testid="stButton"] button[kind="tertiary"] div[data-testid="stMarkdownContainer"] { justify-content: flex-start !important; text-align: left !important; width: 100% !important; }
    div[data-testid="stButton"] button[kind="tertiary"] p { text-align: left !important; width: 100% !important; margin: 0 !important; }
    div[data-testid="stButton"] button[kind="tertiary"]:hover { color: #39FF14 !important; text-decoration: underline !important; }
    </style>
    """, unsafe_allow_html=True)
    
    if "intern_db_initialized" not in st.session_state:
        init_intern_db()
        st.session_state.intern_db_initialized = True
        
    sync_intern_projects()
    
    df_interns = get_all_interns(role=user_role, email=user_email)
    
    if user_role == "Admin":
        intern_names_list = df_interns['Name'].tolist() if not df_interns.empty else ["No Interns Found"]
    else:
        current_name = st.session_state.get('current_user_name', 'Unknown')
        intern_names_list = [current_name]

    if 'camera_active' not in st.session_state: st.session_state.camera_active = False

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1: st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>🎓 Intern Management</h1>", unsafe_allow_html=True)
    with head_col2:
        if user_role == "Admin":
            if st.button("➕ Add Intern", type="primary", use_container_width=True): prepare_new_intern(); add_intern_dialog()  
            
    st.markdown("---")

    tabs = ["🧑‍🎓 Interns Information", "📝 Intern Log"]
    if user_role == "Admin":
        tabs.append("✅ Attendance Approvals")
        
    main_tab = st.radio("Navigation Menu:", tabs, horizontal=True, label_visibility="collapsed", key="main_intern_navigation")
    st.markdown("<br>", unsafe_allow_html=True)

    if main_tab == "🧑‍🎓 Interns Information":
        st.markdown("<h3 style='color: #ffffff;'>🧑‍🎓 Current Interns Details</h3>", unsafe_allow_html=True)
        
        if len(df_interns) == 0:
            st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
        else:
            st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1, 1.5, 1])
            with col1: st.markdown("**ID**")
            with col2: st.markdown("**Name**")
            with col3: st.markdown("**Role**")
            with col4: st.markdown("**Process**")
            with col5: st.markdown("**Type**")
            with col6: st.markdown("**Mentor**")
            with col7: st.markdown("**Duration**")
            with col8: st.markdown("**Status**")
            st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            
            for idx, row in df_interns.iterrows():
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1, 1.5, 1], vertical_alignment="center")
                with c1: st.write(row['Intern ID'])
                with c2:
                    if st.button(f"🎓 {row['Name']}", key=f"int_{row['Intern ID']}", use_container_width=True, type="tertiary"): show_intern_profile(row)
                with c3: st.write(row['Role'])
                with c4: st.write(row['Interview Process'])
                with c5: st.write(row['Internship Type'])
                with c6: st.write(row['Mentor'])
                with c7: st.write(row['Duration'])
                with c8:
                    color = "#39FF14" if row['Status'] in ['Active', 'Completed'] else "#ff9900"
                    st.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['Status']}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    elif main_tab == "✅ Attendance Approvals":
        st.markdown("<h3 style='color: #ffffff;'>✅ HR Attendance Management</h3>", unsafe_allow_html=True)
        
        # 🟢 ANTI-COPY-PASTE SECURITY INJECTION
        components.html(
            """
            <script>
            setTimeout(function() {
                const inputs = window.parent.document.querySelectorAll('input[aria-label="Confirm Name"]');
                for (let i = 0; i < inputs.length; i++) {
                    inputs[i].onpaste = function(e) { e.preventDefault(); return false; };
                    inputs[i].oncopy = function(e) { e.preventDefault(); return false; };
                    inputs[i].ondrop = function(e) { e.preventDefault(); return false; };
                    inputs[i].oncontextmenu = function(e) { e.preventDefault(); return false; };
                    inputs[i].onselectstart = function(e) { e.preventDefault(); return false; };
                    inputs[i].onkeydown = function(e) { 
                        if (e.ctrlKey && (e.key === 'v' || e.key === 'c' || e.key === 'x')) { e.preventDefault(); return false; } 
                    };
                }
            }, 200);
            </script>
            """, height=0, width=0
        )
        
        # --- SECTION 1: Daily Check-in / Check-out Approvals ---
        st.markdown("<h4 style='color: #39FF14; margin-top: 20px;'>1️⃣ Daily Check-In/Out Approvals</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #a1a1aa;'>Review and verify daily attendance proofs manually.</p>", unsafe_allow_html=True)
        
        df_pending = get_pending_attendances()
        if len(df_pending) == 0:
            st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No pending attendance records to approve.</p>", unsafe_allow_html=True)
        else:
            for idx, row in df_pending.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 3, 2], vertical_alignment="center")
                    with c1:
                        # 🟢 NAYA LOGIC: Show Check-Out photo if it's a checkout request, otherwise Check-In photo
                        is_checkout = (row['status'] == "Pending Check-Out")
                        if is_checkout and isinstance(row.get('checkout_photo_data'), bytes):
                            display_photo = row['checkout_photo_data']
                            lbl = "Check-Out Photo"
                        elif isinstance(row.get('photo_data'), bytes):
                            display_photo = row['photo_data']
                            lbl = "Check-In Photo"
                        else:
                            display_photo = None
                            
                        if display_photo:
                            b64_img = base64.b64encode(display_photo).decode('utf-8')
                            st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{b64_img}' width='100' height='100' style='border-radius: 8px; object-fit: cover; border: 2px solid #ff9900;'><br><span style='font-size:11px; color:#a1a1aa;'>{lbl}</span></div>", unsafe_allow_html=True)
                        else:
                            st.markdown("📷 No Photo")
                    with c2:
                        st.markdown(f"**Intern:** {row['intern_name']}")
                        st.markdown(f"**Date:** {row['date']}")
                        st.markdown(f"**Request For:** <span style='color:#ff9900; font-weight:bold;'>{row['status']}</span>", unsafe_allow_html=True)
                        if row['status'] == "Pending Check-In":
                            st.markdown(f"**Submitted Time:** {row['check_in']}")
                        else:
                            st.markdown(f"**Check-Out Time:** {row['check_out']} (Check-In was at {row['check_in']})")
                    with c3:
                        st.markdown(f"<span style='font-size:12px; color:#a1a1aa;'>Type <b>{row['intern_name']}</b> to confirm:</span>", unsafe_allow_html=True)
                        conf_input = st.text_input("Confirm Name", key=f"conf_{row['rowid']}", label_visibility="collapsed")
                        bc1, bc2 = st.columns(2)
                        with bc1:
                            if st.button("✅ Approve", key=f"app_{row['rowid']}", use_container_width=True):
                                # Smart Validation: Handles extra internal spaces
                                if ' '.join(conf_input.split()).lower() == ' '.join(row['intern_name'].split()).lower():
                                    new_stat = "Working" if row['status'] == "Pending Check-In" else "Present"
                                    update_attendance_status(row['rowid'], new_stat)
                                    st.success(f"Approved {row['intern_name']}!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("⚠️ Type name exactly to approve.")
                        with bc2:
                            if st.button("❌ Reject", key=f"rej_{row['rowid']}", use_container_width=True):
                                # Smart Validation: Handles extra internal spaces
                                if ' '.join(conf_input.split()).lower() == ' '.join(row['intern_name'].split()).lower():
                                    update_attendance_status(row['rowid'], "Rejected")
                                    st.error("Rejected!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("⚠️ Type name exactly to reject.")
                                
        st.markdown("<hr style='border-color: rgba(57, 255, 20, 0.3); margin-top: 40px; margin-bottom: 40px;'>", unsafe_allow_html=True)

        # --- SECTION 2: Manual Override (Present / Absent) ---
        st.markdown("<h4 style='color: #39FF14;'>2️⃣ Manual Attendance Override</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #a1a1aa;'>If an intern forgot to check-in/out or lied, mark them Present/Absent directly with a mandatory reason.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                man_intern = st.selectbox("Select Intern", intern_names_list, key="man_override_intern")
                ist = pytz.timezone('Asia/Kolkata')
                man_date = st.date_input("Select Date", datetime.datetime.now(ist).date(), key="man_override_date")
                
                st.markdown(f"<span style='font-size:16px; color:#a1a1aa;'>Type <b>{man_intern}</b> to confirm action:</span>", unsafe_allow_html=True)
                man_conf_input = st.text_input("Confirm Name", key="man_override_conf", label_visibility="collapsed")
                
            with m_col2:
                man_comment = st.text_area("Reason / Comment (Mandatory) *", placeholder="E.g., Forgot to check-in, system issue, absent without notice...", height=110, key="man_override_comment")
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("✅ Mark as Present", type="primary", use_container_width=True, key="btn_man_present"):
                    if not man_comment.strip():
                        st.error("⚠️ Please enter a reason (comment) before marking present!")
                    # Smart Validation: Handles extra internal spaces
                    elif ' '.join(man_conf_input.split()).lower() != ' '.join(man_intern.split()).lower():
                        st.error("⚠️ Type intern name exactly to confirm.")
                    else:
                        man_date_str = man_date.strftime('%d-%b-%Y')
                        manual_override_attendance_db(man_date_str, man_intern, 'Present', man_comment.strip())
                        st.success(f"Successfully marked {man_intern} as Present for {man_date_str}!")
                        time.sleep(1)
                        st.rerun()
            with b_col2:
                if st.button("❌ Mark as Absent", use_container_width=True, key="btn_man_absent"):
                    if not man_comment.strip():
                        st.error("⚠️ Please enter a reason (comment) before marking absent!")
                    # Smart Validation: Handles extra internal spaces
                    elif ' '.join(man_conf_input.split()).lower() != ' '.join(man_intern.split()).lower():
                        st.error("⚠️ Type intern name exactly to confirm.")
                    else:
                        man_date_str = man_date.strftime('%d-%b-%Y')
                        manual_override_attendance_db(man_date_str, man_intern, 'Absent', man_comment.strip())
                        st.success(f"Successfully marked {man_intern} as Absent for {man_date_str}!")
                        time.sleep(1)
                        st.rerun()

    elif main_tab == "📝 Intern Log":
        st.markdown("<h3 style='color: #ffffff; margin-bottom: 5px;'>📝 Logs Overview</h3>", unsafe_allow_html=True)
        log_type = st.radio("Select Log View:", ["📅 Attendance Log", "📋 Daily Task Log"], horizontal=True, label_visibility="collapsed", key="log_type_radio")
        st.markdown("<br>", unsafe_allow_html=True)

        if log_type == "📅 Attendance Log":
            with st.container(border=True):
                st.markdown("**📸 Capture Photo & Mark Attendance**")
                col1, col2, col3 = st.columns(3)
                
                with col1: sel_intern = st.selectbox("Select Intern Name", intern_names_list, key="att_name_sel", disabled=(user_role == "Intern"))
                
                default_type_idx = 0
                if len(df_interns) > 0:
                    matching_intern = df_interns[df_interns['Name'] == sel_intern]
                    if not matching_intern.empty:
                        db_type = matching_intern['Internship Type'].iloc[0]
                        if db_type == "Half time":
                            default_type_idx = 1
                
                with col2: internship_type = st.selectbox("Internship Type", ["Full-Time Internship", "Part-Time Internship"], index=default_type_idx, key="att_type_sel", disabled=(user_role == "Intern"))
                
                with col3:
                    if internship_type == "Part-Time Internship": duration = st.selectbox("Duration", ["Full Day"], key="att_dur_pt_sel")
                    else: duration = st.selectbox("Duration", ["Full Day", "Half Day"], key="att_dur_ft_sel")

                col4, col5 = st.columns(2)
                with col4:
                    if internship_type == "Full-Time Internship" and duration == "Half Day": slot = st.selectbox("Slots available", ["10:00 AM to 1:30 PM", "2:00 PM to 6:00 PM"], key="att_slot_sel")
                    else: slot = None; st.markdown("<br>", unsafe_allow_html=True)
                
                # Check-In / Check-Out Dropdown Dynamic Logic
                ist_check = pytz.timezone('Asia/Kolkata')
                today_str_check = datetime.datetime.now(ist_check).strftime('%d-%b-%Y')
                att_check_docs = db.collection("intern_attendance").where("date", "==", today_str_check).where("intern_name", "==", sel_intern).get()
                
                allowed_actions = []
                is_att_disabled = False
                
                if not att_check_docs:
                    allowed_actions = ["Check-In"]
                else:
                    att_data = att_check_docs[0].to_dict()
                    if att_data.get("check_out") != "-":
                        allowed_actions = ["Already Checked-Out"]
                        is_att_disabled = True
                    else:
                        allowed_actions = ["Check-Out"]

                with col5: 
                    att_action = st.selectbox("Action", allowed_actions, key="att_action_sel", disabled=is_att_disabled)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if not st.session_state.camera_active:
                    if st.button(" TURN ON CAMERA TO VERIFY", use_container_width=True, type="primary", key="btn_camera_on"): st.session_state.camera_active = True; st.rerun()
                else:
                    if st.button(" Turn Off Camera", use_container_width=True, key="btn_camera_off"): st.session_state.camera_active = False; st.rerun()
                        
                photo = st.camera_input("Take a picture for verification", key="att_camera_input") if st.session_state.camera_active else None
                
                if photo:
                    ist = pytz.timezone('Asia/Kolkata')
                    now = datetime.datetime.now(ist)
                    current_time = now.time()
                    is_disabled = False
                    time_msg = ""
                    
                    if internship_type == "Part-Time Internship":
                        checkin_start, checkin_end, checkout_start, checkout_end = datetime.time(10, 50), datetime.time(11, 10), datetime.time(14, 50), datetime.time(15, 30)
                        time_msg_in, time_msg_out = " Check-In is only allowed between 10:50 AM and 11:10 AM for Part-Time.", " Check-Out is only allowed between 02:50 PM and 03:30 PM for Part-Time."
                    elif duration == "Half Day":
                        if slot == "10:00 AM to 1:30 PM":
                            checkin_start, checkin_end, checkout_start, checkout_end = datetime.time(9, 50), datetime.time(10, 10), datetime.time(13, 20), datetime.time(13, 40)
                            time_msg_in, time_msg_out = " Check-In is only allowed between 09:50 AM and 10:10 AM for Slot 1.", " Check-Out is only allowed between 01:20 PM and 01:40 PM for Slot 1."
                        else: 
                            checkin_start, checkin_end, checkout_start, checkout_end = datetime.time(13, 50), datetime.time(14, 10), datetime.time(18,20), datetime.time(18, 30)
                            time_msg_in, time_msg_out = " Check-In is only allowed between 01:50 PM and 02:10 PM for Slot 2.", " Check-Out is only allowed between 06:20 PM and 06:30 PM for Slot 2."
                    else: 
                        checkin_start, checkin_end, checkout_start, checkout_end = datetime.time(9, 50), datetime.time(10, 10), datetime.time(18,20), datetime.time(18, 30)
                        time_msg_in, time_msg_out = " Check-In is only allowed between 09:50 AM and 10:10 AM.", " Check-Out is only allowed between 06:20 PM and 06:30 PM."
                    
                    if att_action == "Check-In" and not (checkin_start <= current_time <= checkin_end):
                        is_disabled = True; time_msg = time_msg_in
                    elif att_action == "Check-Out" and not (checkout_start <= current_time <= checkout_end):
                        is_disabled = True; time_msg = time_msg_out
                    
                    if is_disabled or is_att_disabled: 
                        if time_msg: st.warning(time_msg)
                        
                    if st.button(f" Confirm {att_action}", use_container_width=True, disabled=(is_disabled or is_att_disabled), key="btn_confirm_att"):
                        date_str, time_str = now.strftime('%d-%b-%Y'), now.strftime('%I:%M %p')
                        photo_bytes = photo.getvalue()
                        
                        if att_action == "Check-In":
                            if mark_checkin_db(date_str, sel_intern, time_str, photo_bytes):
                                st.success(f"Check-In requested. Sent for HR Approval!")
                                st.session_state.camera_active = False; st.rerun()
                            else:
                                st.warning("You have already Checked-In today!")
                        elif att_action == "Check-Out":
                            status = mark_checkout_db(date_str, sel_intern, time_str, photo_bytes)
                            if status == "success":
                                st.success(f"Check-Out requested. Sent for HR Approval!")
                                st.session_state.camera_active = False; st.rerun()
                            else:
                                st.warning("Please Check-In first before Checking-Out!")

            st.markdown("<h4 style='color: #ffffff; margin-top: 25px;'>📊 Current Month Stats</h4>", unsafe_allow_html=True)
            present, absent, off = get_month_stats(sel_intern)
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            stat_col1.markdown(f"<div style='background:rgba(57, 255, 20, 0.1); border:1px solid #39FF14; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#39FF14; margin:0;'>{present}</h3><p style='color:#ffffff; margin:0;'>Present</p></div>", unsafe_allow_html=True)
            stat_col2.markdown(f"<div style='background:rgba(255, 75, 75, 0.1); border:1px solid #ff4b4b; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#ff4b4b; margin:0;'>{absent}</h3><p style='color:#ffffff; margin:0;'>Absent</p></div>", unsafe_allow_html=True)
            stat_col3.markdown(f"<div style='background:rgba(136, 136, 136, 0.1); border:1px solid #888888; padding:15px; border-radius:8px; text-align:center;'><h3 style='color:#888888; margin:0;'>{off}</h3><p style='color:#ffffff; margin:0;'>Off (Sat/Sun)</p></div>", unsafe_allow_html=True)
            
            st.markdown("<h4 style='color: #ffffff; margin-top: 35px;'>🗓️ Monthly Attendance Calendar</h4>", unsafe_allow_html=True)
            cal_col1, cal_col2 = st.columns(2)
            
            ist_now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
            with cal_col1:
                month_opts = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                current_m_idx = ist_now.month - 1
                sel_month_name = st.selectbox("Select Month", month_opts, index=current_m_idx, key="cal_month_sel")
                sel_month = month_opts.index(sel_month_name) + 1
            with cal_col2:
                current_y = ist_now.year
                year_opts = [current_y - 1, current_y, current_y + 1]
                sel_year = st.selectbox("Select Year", year_opts, index=1, key="cal_year_sel")
                
            cal_html = generate_calendar_html(sel_intern, sel_year, sel_month)
            st.markdown(cal_html, unsafe_allow_html=True)

            st.markdown("<h4 style='color: #ffffff; margin-top: 20px;'>📋 Today's Attendance Records</h4>", unsafe_allow_html=True)
            today_str = ist_now.strftime('%d-%b-%Y')
            df_att = get_today_attendance_db(today_str, intern_name=sel_intern, role=user_role)
            if len(df_att) == 0: st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No attendance records available today.</p>", unsafe_allow_html=True)
            else: st.markdown(create_attendance_table(df_att), unsafe_allow_html=True)

        elif log_type == "📋 Daily Task Log":
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(ist)
            today_date, today_day = now.strftime('%d-%b-%Y'), now.strftime('%A')
            submit_time_str = now.strftime('%I:%M %p')
            current_hour = now.hour
            
            # Logic: Task Submit button is active ONLY from 6 PM (18) to 9 AM (0-8)
            is_task_time = (current_hour >= 18) or (current_hour < 9)
            
            with st.container(border=True):
                col_name, col_date, col_day = st.columns(3)
                with col_name: sel_intern_task = st.selectbox("Select Name", intern_names_list, key="task_name_sel", disabled=(user_role == "Intern"))
                with col_date: st.text_input("Date", value=today_date, disabled=True, key="task_date_input")
                with col_day: st.text_input("Day", value=today_day, disabled=True, key="task_day_input")
                
                has_submitted_today = check_daily_task_exists_db(today_date, sel_intern_task)
                
                if has_submitted_today:
                    st.info(f"you have already submit the task")
                else:
                    if not is_task_time:
                        st.warning("⚠️ Submit Task button is only active from 6:00 PM to 9:00 AM.")
                        
                    st.markdown("<span style='font-size:14px; color:#ff4b4b;'>* Mandatory Fields</span>", unsafe_allow_html=True)
                    task_input = st.text_area("Today's Tasks *", height=100, key="task_desc_input")
                    result_input = st.text_area("Result *", height=100, key="task_result_input", help="What was the result of today's task?")
                    outcome_input = st.text_area("Outcome *", height=100, key="task_out_input")
                    extra_input = st.text_area("Extra Curriculum (Optional)", height=80, key="task_extra_input")
                    
                    if st.button(" Submit Task Log", use_container_width=True, type="primary", key="btn_submit_task", disabled=not is_task_time):
                        if not task_input.strip() or not result_input.strip() or not outcome_input.strip(): 
                            st.error("Please fill all the mandatory fields before submitting.")
                        else:
                            save_task_log_db(today_date, today_day, sel_intern_task, task_input, result_input, outcome_input, extra_input if extra_input.strip() else "-", submit_time_str)
                            st.success(f"Task log submitted successfully for {sel_intern_task}!"); time.sleep(1); st.rerun()

            st.markdown("<h4 style='color: #ffffff; margin-top: 35px;'>📅 View Past Tasks by Date</h4>", unsafe_allow_html=True)
            view_date_col, view_intern_col = st.columns(2)
            
            with view_date_col:
                selected_view_date = st.date_input("Select Date (Calendar Picker)", now.date(), key="view_task_date")
                selected_date_str = selected_view_date.strftime('%d-%b-%Y')
            
            with view_intern_col:
                if user_role == "Admin":
                    view_intern_opts = ["All"] + intern_names_list
                    sel_view_intern = st.selectbox("Select Intern", view_intern_opts, key="view_task_intern")
                else:
                    sel_view_intern = st.selectbox("Select Intern", intern_names_list, disabled=True, key="view_task_intern")
                    
            df_all_logs = get_all_task_logs_db(intern_name=sel_view_intern if sel_view_intern != "All" else None, role=user_role)
            
            if not df_all_logs.empty:
                df_day_logs = df_all_logs[df_all_logs['Date'] == selected_date_str]
                if sel_view_intern != "All" and user_role == "Admin":
                    df_day_logs = df_day_logs[df_day_logs['Name'] == sel_view_intern]
                    
                if len(df_day_logs) > 0:
                    st.markdown(create_task_log_table(df_day_logs), unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='color: #a1a1aa; font-size: 16px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;'>No task logs found for {selected_date_str}.</p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;'>No task logs found.</p>", unsafe_allow_html=True)

            st.markdown("<hr style='border-color: rgba(57, 255, 20, 0.3); margin-top: 40px;'>", unsafe_allow_html=True)

            st.markdown("<h4 style='color: #ffffff; margin-top: 10px;'>📂 Filter & Download Monthly Task Logs</h4>", unsafe_allow_html=True)
            log_col1, log_col2, log_col3 = st.columns(3)
            with log_col1:
                log_month_opts = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                current_m_idx = now.month - 1
                sel_log_month = st.selectbox("Select Month", log_month_opts, index=current_m_idx, key="log_month_sel")
                sel_log_month_abbr = sel_log_month[:3]
            with log_col2:
                current_y = now.year
                year_opts = [current_y - 1, current_y, current_y + 1]
                sel_log_year = st.selectbox("Select Year", year_opts, index=1, key="log_year_sel")
            with log_col3:
                if user_role == "Admin":
                    log_intern_opts = ["All"] + intern_names_list
                    sel_log_dl_intern = st.selectbox("Select Intern", log_intern_opts, key="log_dl_intern_sel")
                else:
                    sel_log_dl_intern = st.selectbox("Select Intern", intern_names_list, disabled=True, key="log_dl_intern_sel")

            if len(df_all_logs) > 0:
                df_monthly_logs = df_all_logs[df_all_logs['Date'].str.contains(f"-{sel_log_month_abbr}-") & df_all_logs['Date'].str.contains(str(sel_log_year))]
                if sel_log_dl_intern != "All" and user_role == "Admin":
                    df_monthly_logs = df_monthly_logs[df_monthly_logs['Name'] == sel_log_dl_intern]

                if len(df_monthly_logs) == 0: 
                    st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No task logs found for selected month and year.</p>", unsafe_allow_html=True)
                else: 
                    csv_data = df_monthly_logs.to_csv(index=False).encode('utf-8')
                    st.download_button(label=" Download Logs as CSV", data=csv_data, file_name=f"Task_Logs_{sel_log_month}_{sel_log_year}.csv", mime="text/csv", use_container_width=True)
                    st.markdown(create_task_log_table(df_monthly_logs), unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No data available.</p>", unsafe_allow_html=True)