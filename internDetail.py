# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import datetime
import sqlite3
import time
import base64
import re  
import calendar 
import streamlit.components.v1 as components
from utils import load_global_css
from config import is_valid_email

# ==========================================
# HELPER FUNCTIONS
# ==========================================



# ==========================================
# DATABASE SECTION (Handles Data Storage)
# ==========================================

def init_intern_db():
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS interns (intern_id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE, contact TEXT, role TEXT, assigned_project TEXT, completed_projects TEXT, mentor TEXT, duration TEXT, status TEXT, college TEXT, branch TEXT, semester TEXT, skills TEXT, photo_data BLOB, interview_process TEXT, internship_type TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS intern_attendance (date TEXT, intern_name TEXT, check_in TEXT, check_out TEXT, status TEXT, photo_data BLOB)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS intern_daily_tasks (date TEXT, day TEXT, intern_name TEXT, task TEXT, outcome TEXT, extra_curriculum TEXT)''')
    
    try: cursor.execute("ALTER TABLE interns ADD COLUMN photo_data BLOB")
    except sqlite3.OperationalError: pass
    try: cursor.execute("ALTER TABLE interns ADD COLUMN interview_process TEXT")
    except sqlite3.OperationalError: pass
    try: cursor.execute("ALTER TABLE interns ADD COLUMN internship_type TEXT")
    except sqlite3.OperationalError: pass
    try: cursor.execute("ALTER TABLE interns ADD COLUMN password TEXT")
    except sqlite3.OperationalError: pass
    
    # HR/Boss/Lead Dev Comment store karne ke liye column
    try: cursor.execute("ALTER TABLE intern_attendance ADD COLUMN hr_comment TEXT")
    except sqlite3.OperationalError: pass
    
    conn.commit()
    conn.close()

def sync_intern_projects():
    try:
        conn_proj = sqlite3.connect("crm_main.db")
        cursor_proj = conn_proj.cursor()
        cursor_proj.execute("SELECT project_name FROM projects WHERE status = 'Completed'")
        completed_projects = [row[0] for row in cursor_proj.fetchall()]
        conn_proj.close()

        if not completed_projects: return

        conn_int = sqlite3.connect("crm_main.db")
        cursor_int = conn_int.cursor()
        cursor_int.execute("SELECT intern_id, assigned_project, completed_projects FROM interns WHERE assigned_project != '-' AND assigned_project IS NOT NULL")
        interns = cursor_int.fetchall()

        updates = []
        for i_id, assigned, comp in interns:
            if assigned in completed_projects:
                new_comp = assigned if comp in ["-", "", None] else f"{comp}, {assigned}"
                new_assigned = "-" 
                updates.append((new_comp, new_assigned, i_id))

        if updates:
            cursor_int.executemany("UPDATE interns SET completed_projects = ?, assigned_project = ? WHERE intern_id = ?", updates)
            conn_int.commit()
        conn_int.close()
    except Exception:
        pass 

def get_all_interns(role="Admin", email=""):
    conn = sqlite3.connect("crm_main.db")
    if role == "Intern":
        query = f"SELECT intern_id AS 'Intern ID', name AS 'Name', email AS 'Email', contact AS 'Contact', role AS 'Role', assigned_project AS 'Assigned Project', completed_projects AS 'Completed Projects', mentor AS 'Mentor', duration AS 'Duration', status AS 'Status', college AS 'College', branch AS 'Branch', semester AS 'Semester', skills AS 'Skills', photo_data, interview_process AS 'Interview Process', internship_type AS 'Internship Type' FROM interns WHERE email='{email}' ORDER BY intern_id ASC"
    else:
        query = "SELECT intern_id AS 'Intern ID', name AS 'Name', email AS 'Email', contact AS 'Contact', role AS 'Role', assigned_project AS 'Assigned Project', completed_projects AS 'Completed Projects', mentor AS 'Mentor', duration AS 'Duration', status AS 'Status', college AS 'College', branch AS 'Branch', semester AS 'Semester', skills AS 'Skills', photo_data, interview_process AS 'Interview Process', internship_type AS 'Internship Type' FROM interns ORDER BY intern_id ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_active_onboard_projects():
    try:
        conn = sqlite3.connect("crm_main.db")
        cursor = conn.cursor()
        cursor.execute("SELECT project_name, status FROM projects WHERE status IN ('Active', 'Onboard')")
        projects = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return projects
    except sqlite3.OperationalError:
        return {}

def add_new_intern(i_id, name, email, contact, role, project, comp_proj, mentor, duration, status, college, branch, sem, skills, photo, process, i_type):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM interns WHERE email = ?", (email,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return "duplicate_email"
    try:
        cursor.execute('''INSERT INTO interns (intern_id, name, email, contact, role, assigned_project, completed_projects, mentor, duration, status, college, branch, semester, skills, photo_data, interview_process, internship_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (i_id, name, email, contact, role, project, comp_proj, mentor, duration, status, college, branch, sem, skills, photo, process, i_type))
        conn.commit()
        return "success"
    except sqlite3.IntegrityError:
        return "duplicate_id"  
    finally:
        conn.close()

def delete_intern(i_id):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interns WHERE intern_id = ?", (i_id,))
    conn.commit()
    conn.close()

def update_intern_profile_db(intern_id, role, project, mentor, status):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE interns SET role=?, assigned_project=?, mentor=?, status=? WHERE intern_id=?", (role, project, mentor, status, intern_id))
    conn.commit()
    conn.close()

# ==========================================
# ADVANCED ATTENDANCE & LOG DB FUNCTIONS
# ==========================================

def get_month_stats(intern_name):
    now = datetime.datetime.now()
    current_month = now.month
    current_year = now.year
    today = now.date()
    
    conn = sqlite3.connect("crm_main.db")
    c = conn.cursor()
    c.execute("SELECT date, status FROM intern_attendance WHERE intern_name=?", (intern_name,))
    records = c.fetchall()
    conn.close()
    
    att_dict = {row[0]: row[1] for row in records}
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
    conn = sqlite3.connect("crm_main.db")
    c = conn.cursor()
    c.execute("SELECT date, status FROM intern_attendance WHERE intern_name=?", (intern_name,))
    records = c.fetchall()
    conn.close()
    
    att_dict = {row[0]: row[1] for row in records}
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
    today = datetime.datetime.now().date()
    
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
    conn = sqlite3.connect("crm_main.db")
    c = conn.cursor()
    c.execute("SELECT * FROM intern_attendance WHERE date=? AND intern_name=?", (date_str, intern_name))
    if c.fetchone():
        conn.close(); return False 
    c.execute("INSERT INTO intern_attendance (date, intern_name, check_in, check_out, status, photo_data) VALUES (?, ?, ?, ?, ?, ?)", (date_str, intern_name, time_str, "-", "Pending Check-In", photo_bytes))
    conn.commit(); conn.close(); return True

def mark_checkout_db(date_str, intern_name, time_str):
    conn = sqlite3.connect("crm_main.db")
    c = conn.cursor()
    c.execute("SELECT check_in FROM intern_attendance WHERE date=? AND intern_name=?", (date_str, intern_name))
    row = c.fetchone()
    if not row:
        conn.close(); return "not_checked_in"
    c.execute("UPDATE intern_attendance SET check_out=?, status='Pending Check-Out' WHERE date=? AND intern_name=?", (time_str, date_str, intern_name))
    conn.commit(); conn.close(); return "success"

# 🟢 NAYA LOGIC: Manual Override Database Function (Handles both Present and Absent)
def manual_override_attendance_db(date_str, intern_name, status, comment):
    conn = sqlite3.connect("crm_main.db")
    c = conn.cursor()
    c.execute("SELECT rowid FROM intern_attendance WHERE date=? AND intern_name=?", (date_str, intern_name))
    row = c.fetchone()
    time_str = datetime.datetime.now().strftime('%I:%M %p')
    if row:
        c.execute("UPDATE intern_attendance SET status=?, check_in=?, check_out=?, hr_comment=? WHERE rowid=?", (status, time_str, time_str, comment, row[0]))
    else:
        c.execute("INSERT INTO intern_attendance (date, intern_name, check_in, check_out, status, photo_data, hr_comment) VALUES (?, ?, ?, ?, ?, NULL, ?)", (date_str, intern_name, time_str, time_str, status, comment))
    conn.commit()
    conn.close()

def get_today_attendance_db(date_str, intern_name=None, role="Admin"):
    conn = sqlite3.connect("crm_main.db")
    if role == "Intern":
        query = f"SELECT date AS Date, intern_name AS 'Intern Name', check_in AS 'Check-In', check_out AS 'Check-Out', status AS Status, hr_comment AS Comment FROM intern_attendance WHERE date='{date_str}' AND intern_name='{intern_name}' ORDER BY rowid DESC"
    else:
        query = f"SELECT date AS Date, intern_name AS 'Intern Name', check_in AS 'Check-In', check_out AS 'Check-Out', status AS Status, hr_comment AS Comment FROM intern_attendance WHERE date='{date_str}' ORDER BY rowid DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_pending_attendances():
    conn = sqlite3.connect("crm_main.db")
    query = "SELECT rowid, date, intern_name, check_in, check_out, status, photo_data FROM intern_attendance WHERE status IN ('Pending Check-In', 'Pending Check-Out') ORDER BY rowid DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_attendance_status(rowid, new_status):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE intern_attendance SET status=? WHERE rowid=?", (new_status, rowid))
    conn.commit()
    conn.close()

def save_task_log_db(date_str, day_str, intern_name, task, outcome, extra):
    conn = sqlite3.connect("crm_main.db")
    c = conn.cursor()
    c.execute("INSERT INTO intern_daily_tasks (date, day, intern_name, task, outcome, extra_curriculum) VALUES (?, ?, ?, ?, ?, ?)", (date_str, day_str, intern_name, task, outcome, extra))
    conn.commit()
    conn.close()

def get_all_task_logs_db(intern_name=None, role="Admin"):
    conn = sqlite3.connect("crm_main.db")
    if role == "Intern":
        query = f"SELECT intern_name AS Name, date AS Date, day AS Day, task AS 'Today''s Task', outcome AS Outcome, extra_curriculum AS 'Extra Curriculum' FROM intern_daily_tasks WHERE intern_name='{intern_name}' ORDER BY rowid DESC"
    else:
        query = "SELECT intern_name AS Name, date AS Date, day AS Day, task AS 'Today''s Task', outcome AS Outcome, extra_curriculum AS 'Extra Curriculum' FROM intern_daily_tasks ORDER BY rowid DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ==========================================
# SAFE MEMORY LOGIC 
# ==========================================
def int_go_preview():
    p = st.session_state
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
    start, end = p.get("i_start_in", datetime.date.today()), p.get("i_end_in", datetime.date.today())

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
    try:
        s_str = duration_val.split(" to ")[0]
        s_dt = datetime.datetime.strptime(s_str, '%d-%b-%Y').date()
        t_end = s_dt + datetime.timedelta(days=7)
        train_disp = f"{s_str} to {t_end.strftime('%d-%b-%Y')}"
        project_disabled = datetime.date.today() <= t_end
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
            components.html("<script>setTimeout(function() { const inputs = window.parent.document.querySelectorAll('input[aria-label=\"Type here to confirm:\"]'); for (let i = 0; i < inputs.length; i++) { inputs[i].onpaste = function(e) { e.preventDefault(); return false; }; inputs[i].ondrop = function(e) { e.preventDefault(); return false; }; } }, 100); </script>", height=0, width=0)

            if st.button(" Permanently Delete", type="primary", use_container_width=True):
                if confirm_input.strip().lower() == intern['Name'].strip().lower():
                    delete_intern(intern['Intern ID']); st.success("Removed successfully!"); time.sleep(1.5); st.rerun() 
                else: st.warning("⚠️ Type name exactly to delete.")

    if st.button("Close Profile", use_container_width=True, key="close_intern_profile"): st.rerun() 

@st.dialog("➕ Add New Intern", width="large")
def add_intern_dialog():
    if "safe_int_data" not in st.session_state: st.session_state.safe_int_data = {}
    draft = st.session_state.safe_int_data

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
            s_date = d_col1.date_input("Start Date *", value=draft.get('start', datetime.date.today()), key="i_start_in")
            d_col2.date_input("End Date *", value=draft.get('end', datetime.date.today()), key="i_end_in")
            m_opts = ["Prajatak sir", "Vikrant sir", "Shahid sir", "Arya sir"]
            st.selectbox("Assigned Mentor *", m_opts, index=m_opts.index(draft.get('mentor', "Prajatak sir")) if draft.get('mentor') in m_opts else 0, key="i_mentor_in")
            st.file_uploader("Upload Photo (Optional)", type=['jpg', 'jpeg', 'png'], key="i_photo_in")

        with col5:
            r_opts = ["AI/ML Developer", "FullStack Developer", "Word Press Developer", "Frontend Developer", "Backend Developer", "Digital Marketing"]
            st.selectbox("Internship Role *", r_opts, index=r_opts.index(draft.get('role', "AI/ML Developer")) if draft.get('role') in r_opts else 0, key="i_role_in")
            
            train_end = s_date + datetime.timedelta(days=7)
            train_str = f"{s_date.strftime('%d-%b-%Y')} to {train_end.strftime('%d-%b-%Y')}"
            st.text_input("Compulsory Training Session (7 Days)", value=train_str, disabled=True)
            
            project_disabled = datetime.date.today() <= train_end
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
    for col in ["Name", "Date", "Day", "Today's Task", "Outcome", "Extra Curriculum"]: html_table += f"<th style='padding: 12px;'>{col}</th>"
    html_table += "</tr>"
    for _, row in df.iterrows(): 
        task_val = row["Today's Task"]
        html_table += f"<tr><td style='padding: 12px;'><strong>{row['Name']}</strong></td><td style='padding: 12px;'>{row['Date']}</td><td style='padding: 12px;'>{row['Day']}</td><td style='padding: 12px;'>{task_val}</td><td style='padding: 12px;'>{row['Outcome']}</td><td style='padding: 12px;'>{row['Extra Curriculum']}</td></tr>"
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

    # 🟢 2 SECTIONS ADDED HERE AS REQUESTED
    elif main_tab == "✅ Attendance Approvals":
        st.markdown("<h3 style='color: #ffffff;'>✅ HR Attendance Management</h3>", unsafe_allow_html=True)
        
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
                        if row['photo_data']:
                            b64_img = base64.b64encode(row['photo_data']).decode('utf-8')
                            st.markdown(f"<img src='data:image/png;base64,{b64_img}' width='100' height='100' style='border-radius: 8px; object-fit: cover; border: 2px solid #ff9900;'>", unsafe_allow_html=True)
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
                        bc1, bc2 = st.columns(2)
                        with bc1:
                            if st.button("✅ Approve", key=f"app_{row['rowid']}", use_container_width=True):
                                new_stat = "Working" if row['status'] == "Pending Check-In" else "Present"
                                update_attendance_status(row['rowid'], new_stat)
                                st.success(f"Approved {row['intern_name']}!")
                                time.sleep(1)
                                st.rerun()
                        with bc2:
                            if st.button("❌ Reject", key=f"rej_{row['rowid']}", use_container_width=True):
                                update_attendance_status(row['rowid'], "Rejected")
                                st.error("Rejected!")
                                time.sleep(1)
                                st.rerun()
                                
        st.markdown("<hr style='border-color: rgba(57, 255, 20, 0.3); margin-top: 40px; margin-bottom: 40px;'>", unsafe_allow_html=True)

        # --- SECTION 2: Manual Override (Present / Absent) ---
        st.markdown("<h4 style='color: #39FF14;'>2️⃣ Manual Attendance Override</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #a1a1aa;'>If an intern forgot to check-in/out or lied, mark them Present/Absent directly with a mandatory reason.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                man_intern = st.selectbox("Select Intern", intern_names_list, key="man_override_intern")
                man_date = st.date_input("Select Date", datetime.date.today(), key="man_override_date")
            with m_col2:
                man_comment = st.text_area("Reason / Comment (Mandatory) *", placeholder="E.g., Forgot to check-in, system issue, absent without notice...", height=110, key="man_override_comment")
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("✅ Mark as Present", type="primary", use_container_width=True, key="btn_man_present"):
                    if not man_comment.strip():
                        st.error("⚠️ Please enter a reason (comment) before marking present!")
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
                with col5: att_action = st.selectbox("Action", ["Check-In", "Check-Out"], key="att_action_sel")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if not st.session_state.camera_active:
                    if st.button(" TURN ON CAMERA TO VERIFY", use_container_width=True, type="primary", key="btn_camera_on"): st.session_state.camera_active = True; st.rerun()
                else:
                    if st.button(" Turn Off Camera", use_container_width=True, key="btn_camera_off"): st.session_state.camera_active = False; st.rerun()
                        
                photo = st.camera_input("Take a picture for verification", key="att_camera_input") if st.session_state.camera_active else None
                
                if photo:
                    now = datetime.datetime.now()
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
                            checkin_start, checkin_end, checkout_start, checkout_end = datetime.time(13, 50), datetime.time(14, 10), datetime.time(17, 50), datetime.time(18, 30)
                            time_msg_in, time_msg_out = " Check-In is only allowed between 01:50 PM and 02:10 PM for Slot 2.", " Check-Out is only allowed between 05:50 PM and 06:30 PM for Slot 2."
                    else: 
                        checkin_start, checkin_end, checkout_start, checkout_end = datetime.time(9, 50), datetime.time(10, 10), datetime.time(17, 50), datetime.time(18, 30)
                        time_msg_in, time_msg_out = " Check-In is only allowed between 09:50 AM and 10:10 AM.", " Check-Out is only allowed between 05:50 PM and 06:30 PM."
                    
                    if att_action == "Check-In" and not (checkin_start <= current_time <= checkin_end):
                        is_disabled = True; time_msg = time_msg_in
                    elif att_action == "Check-Out" and not (checkout_start <= current_time <= checkout_end):
                        is_disabled = True; time_msg = time_msg_out
                    
                    if is_disabled: st.warning(time_msg)
                        
                    if st.button(f" Confirm {att_action}", use_container_width=True, disabled=is_disabled, key="btn_confirm_att"):
                        date_str, time_str = now.strftime('%d-%b-%Y'), now.strftime('%I:%M %p')
                        photo_bytes = photo.getvalue()
                        
                        if att_action == "Check-In":
                            if mark_checkin_db(date_str, sel_intern, time_str, photo_bytes):
                                st.success(f"Check-In requested. Sent for HR Approval!")
                                st.session_state.camera_active = False; st.rerun()
                            else:
                                st.warning("You have already Checked-In today!")
                        else:
                            status = mark_checkout_db(date_str, sel_intern, time_str)
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
            with cal_col1:
                month_opts = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                current_m_idx = datetime.datetime.now().month - 1
                sel_month_name = st.selectbox("Select Month", month_opts, index=current_m_idx, key="cal_month_sel")
                sel_month = month_opts.index(sel_month_name) + 1
            with cal_col2:
                current_y = datetime.datetime.now().year
                year_opts = [current_y - 1, current_y, current_y + 1]
                sel_year = st.selectbox("Select Year", year_opts, index=1, key="cal_year_sel")
                
            cal_html = generate_calendar_html(sel_intern, sel_year, sel_month)
            st.markdown(cal_html, unsafe_allow_html=True)

            st.markdown("<h4 style='color: #ffffff; margin-top: 20px;'>📋 Today's Attendance Records</h4>", unsafe_allow_html=True)
            today_str = datetime.datetime.now().strftime('%d-%b-%Y')
            df_att = get_today_attendance_db(today_str, intern_name=sel_intern, role=user_role)
            if len(df_att) == 0: st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No attendance records available today.</p>", unsafe_allow_html=True)
            else: st.markdown(create_attendance_table(df_att), unsafe_allow_html=True)

        elif log_type == "📋 Daily Task Log":
            now = datetime.datetime.now()
            today_date, today_day = now.strftime('%d-%b-%Y'), now.strftime('%A')
            
            with st.container(border=True):
                col_name, col_date, col_day = st.columns(3)
                with col_name: sel_intern_task = st.selectbox("Select Name", intern_names_list, key="task_name_sel", disabled=(user_role == "Intern"))
                with col_date: st.text_input("Date", value=today_date, disabled=True, key="task_date_input")
                with col_day: st.text_input("Day", value=today_day, disabled=True, key="task_day_input")
                st.markdown("<span style='font-size:14px; color:#ff4b4b;'>* Mandatory Fields</span>", unsafe_allow_html=True)
                task_input = st.text_area("Today's Tasks *", height=100, key="task_desc_input")
                outcome_input = st.text_area("Outcome *", height=100, key="task_out_input")
                extra_input = st.text_area("Extra Curriculum (Optional)", height=80, key="task_extra_input")
                
                if st.button(" Submit Task Log", use_container_width=True, type="primary", key="btn_submit_task"):
                    if not task_input.strip() or not outcome_input.strip(): st.error("Please fill the mandatory fields before submitting.")
                    else:
                        save_task_log_db(today_date, today_day, sel_intern_task, task_input, outcome_input, extra_input if extra_input.strip() else "-")
                        st.success(f"Task log submitted successfully for {sel_intern_task}!"); st.rerun()

            st.markdown("<h4 style='color: #ffffff; margin-top: 35px;'>📂 Filter & Download Task Logs</h4>", unsafe_allow_html=True)
            log_col1, log_col2, log_col3 = st.columns(3)
            with log_col1:
                log_month_opts = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                current_m_idx = datetime.datetime.now().month - 1
                sel_log_month = st.selectbox("Select Month", log_month_opts, index=current_m_idx, key="log_month_sel")
                sel_log_month_abbr = sel_log_month[:3]
            with log_col2:
                current_y = datetime.datetime.now().year
                year_opts = [current_y - 1, current_y, current_y + 1]
                sel_log_year = st.selectbox("Select Year", year_opts, index=1, key="log_year_sel")
            with log_col3:
                if user_role == "Admin":
                    log_intern_opts = ["All"] + intern_names_list
                    sel_log_intern = st.selectbox("Select Intern", log_intern_opts, key="log_intern_sel")
                else:
                    sel_log_intern = st.selectbox("Select Intern", intern_names_list, disabled=True, key="log_intern_sel")

            df_logs = get_all_task_logs_db(intern_name=sel_log_intern, role=user_role)
            
            if len(df_logs) > 0:
                df_logs = df_logs[df_logs['Date'].str.contains(f"-{sel_log_month_abbr}-") & df_logs['Date'].str.contains(str(sel_log_year))]
                if sel_log_intern != "All" and user_role == "Admin":
                    df_logs = df_logs[df_logs['Name'] == sel_log_intern]

            if len(df_logs) == 0: 
                st.markdown("<p style='color: #a1a1aa; font-size: 16px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: center;'>No task logs found for selected month and year.</p>", unsafe_allow_html=True)
            else: 
                csv_data = df_logs.to_csv(index=False).encode('utf-8')
                st.download_button(label=" Download Logs as CSV", data=csv_data, file_name=f"Task_Logs_{sel_log_month}_{sel_log_year}.csv", mime="text/csv", use_container_width=True)
                st.markdown(create_task_log_table(df_logs), unsafe_allow_html=True)