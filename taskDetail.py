# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import time
import datetime
import pytz

# 🟢 NAYA LOGIC: Firebase Database (db) config se import kar rahe hain
from config import db

# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

def init_task_db():
    # Firestore mein collections automatically create ho jate hain jab data add hota hai
    pass

# Helper to fetch active/onboard projects
def get_active_onboard_projects():
    try:
        docs = db.collection("projects").where("status", "in", ["Active", "Onboard"]).get()
        return {doc.to_dict().get("project_name"): doc.to_dict().get("status") for doc in docs}
    except Exception:
        return {}

# Helper to fetch intern names
def get_intern_names():
    try:
        docs = db.collection("interns").get()
        return [doc.to_dict().get("name", "") for doc in docs if doc.to_dict().get("name")]
    except Exception:
        return []

def get_all_tasks():
    docs = db.collection("tasks").get()
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            'Task ID': d.get('task_id', ''),
            'Employees Names': d.get('emp_name', ''),
            'Related Project': d.get('project', ''),
            'Task': d.get('task_desc', ''),
            'Priority': d.get('priority', ''),
            'Status': d.get('status', 'Active'),
            'Outcome': d.get('outcome', ''),
            'Assign Date': d.get('assign_date', ''),
            'Submission Date': d.get('sub_date', '')
        })
        
    df = pd.DataFrame(data_list)
    return df

def save_new_task(t_id, emp, proj, desc, prio, status, out, assign_date, sub_date):
    doc_ref = db.collection("tasks").document(t_id)
    if doc_ref.get().exists: return False
        
    doc_ref.set({
        "task_id": t_id, "emp_name": emp, "project": proj, "task_desc": desc,
        "priority": prio, "status": status, "outcome": out,
        "assign_date": assign_date, "sub_date": sub_date
    })
    return True

def update_task_db(t_id, emp, proj, desc, prio, status, out, assign_date, sub_date):
    db.collection("tasks").document(t_id).update({
        "emp_name": emp, "project": proj, "task_desc": desc,
        "priority": prio, "status": status, "outcome": out,
        "assign_date": assign_date, "sub_date": sub_date
    })

def update_task_status_only(t_id, status):
    db.collection("tasks").document(t_id).update({"status": status})

# ==========================================
# SAFE MEMORY LOGIC 
# ==========================================

def tsk_go_preview():
    p = st.session_state
    
    emp_list = p.get("t_emp_in", [])
    proj = p.get("t_proj_in", "")
    prio = p.get("t_prio_in", "High")
    status = p.get("t_status_in", "Active")
    desc = p.get("t_desc_in", "")
    out = p.get("t_out_in", "")
    assign_d = p.get("t_assign_in", datetime.date.today())
    sub_d = p.get("t_sub_in", datetime.date.today())

    if emp_list and proj and desc:
        if sub_d < assign_d:
            p.tsk_error = "⚠️ Submission Date cannot be before Assign Date!"
        else:
            p.tsk_step = "preview"
            p.tsk_error = ""
            p.safe_tsk_data = {
                'emp_list': emp_list, 'emp': ", ".join(emp_list), 'proj': proj,
                'prio': prio, 'status': status, 'desc': desc, 'out': out,
                'assign_date': assign_d, 'sub_date': sub_d
            }
    else:
        p.tsk_error = "⚠️ Please fill all mandatory fields (*)."

def tsk_go_edit():
    st.session_state.tsk_step = "form"

def prepare_new_task():
    st.session_state.tsk_step = "form"
    st.session_state.tsk_error = ""
    st.session_state.safe_tsk_data = {}
    
    keys_to_clear = ["t_emp_in", "t_proj_in", "t_desc_in", "t_out_in", "t_prio_in", "t_status_in", "t_assign_in", "t_sub_in"]
    for k in keys_to_clear:
        if k in st.session_state: del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

@st.dialog("✏️ Edit Task", width="large")
def edit_task_dialog(task):
    interns = get_intern_names()
    curr_emp_list = [e.strip() for e in task['Employees Names'].split(",")] if task['Employees Names'] else []
    valid_curr_emp = [e for e in curr_emp_list if e in interns]

    proj_dict = get_active_onboard_projects()
    avail_projs = list(proj_dict.keys()) if proj_dict else ["No Active Projects"]
    def format_proj(p): return f"{p} ({proj_dict[p]})" if p in proj_dict else p
    if task['Related Project'] not in avail_projs and task['Related Project'] != "":
        avail_projs.insert(0, task['Related Project'])

    col1, col2 = st.columns(2)
    with col1:
        e_emp = st.multiselect("Assign To Interns *", interns, default=valid_curr_emp)
        e_proj = st.selectbox("Project Name *", avail_projs, index=avail_projs.index(task['Related Project']) if task['Related Project'] in avail_projs else 0, format_func=format_proj)
        prio_opts = ["High", "Medium", "Low"]
        e_prio = st.selectbox("Priority", prio_opts, index=prio_opts.index(task['Priority']) if task['Priority'] in prio_opts else 0)

    with col2:
        try:
            curr_assign = datetime.datetime.strptime(task['Assign Date'], '%d-%b-%Y').date() if task['Assign Date'] else datetime.date.today()
            curr_sub = datetime.datetime.strptime(task['Submission Date'], '%d-%b-%Y').date() if task['Submission Date'] else datetime.date.today()
        except:
            curr_assign, curr_sub = datetime.date.today(), datetime.date.today()

        e_assign = st.date_input("Assign Date", value=curr_assign)
        e_sub = st.date_input("Submission Date", value=curr_sub)

        stat_opts = ["Active", "Completed", "Incomplete"]
        e_stat = st.selectbox("Status", stat_opts, index=stat_opts.index(task['Status']) if task['Status'] in stat_opts else 0)

    e_desc = st.text_area("Task Description *", value=task['Task'])
    e_out = st.text_area("Outcome", value=task['Outcome'])

    if st.button("💾 Update Task", type="primary", use_container_width=True):
        if e_emp and e_proj and e_desc:
            update_task_db(task['Task ID'], ", ".join(e_emp), e_proj, e_desc, e_prio, e_stat, e_out, e_assign.strftime('%d-%b-%Y'), e_sub.strftime('%d-%b-%Y'))
            st.success("Task Updated Successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Please fill mandatory fields!")

@st.dialog("➕ Add New Task", width="large")
def add_task_dialog():
    if "tsk_step" not in st.session_state: st.session_state.tsk_step = "form"
    draft = st.session_state.get("safe_tsk_data", {})
    ist = pytz.timezone('Asia/Kolkata')
    today_ist = datetime.datetime.now(ist).date()

    if st.session_state.tsk_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Fill out the details below to assign a new task.</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            interns = get_intern_names()
            st.multiselect("Assign To Interns *", interns, default=draft.get('emp_list', []), key="t_emp_in")
            
            proj_dict = get_active_onboard_projects()
            avail_projs = list(proj_dict.keys()) if proj_dict else ["No Active Projects"]
            def format_proj(p): return f"{p} ({proj_dict[p]})" if p in proj_dict else p
            
            p_idx = avail_projs.index(draft.get('proj')) if draft.get('proj') in avail_projs else 0
            st.selectbox("Project Name *", avail_projs, index=p_idx, format_func=format_proj, key="t_proj_in")
            
            prio_opts = ["High", "Medium", "Low"]
            prio_idx = prio_opts.index(draft.get('prio', "High")) if draft.get('prio') in prio_opts else 0
            st.selectbox("Priority", prio_opts, index=prio_idx, key="t_prio_in")
            
        with col2:
            st.date_input("Assign Date *", value=draft.get('assign_date', today_ist), key="t_assign_in")
            st.date_input("Submission Date *", value=draft.get('sub_date', today_ist), key="t_sub_in")
            
            stat_opts = ["Active", "Completed", "Incomplete"]
            s_idx = stat_opts.index(draft.get('status', "Active")) if draft.get('status') in stat_opts else 0
            st.selectbox("Current Status", stat_opts, index=s_idx, key="t_status_in")
            
        st.text_area("Task Description *", value=draft.get('desc', ''), key="t_desc_in")
        st.text_area("Outcome", value=draft.get('out', ''), key="t_out_in")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("tsk_error"): st.error(st.session_state.tsk_error)
        st.button("👁️ Generate Preview", type="primary", use_container_width=True, on_click=tsk_go_preview)

    elif st.session_state.tsk_step == "preview":
        data = st.session_state.safe_tsk_data
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Task Details</h3>", unsafe_allow_html=True)
        
        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f"**Assigned Interns:** {data['emp']}")
                st.markdown(f"**Project Name:** {data['proj']}")
                st.markdown(f"**Priority:** {data['prio']}")
            with col_p2:
                st.markdown(f"**Dates:** {data['assign_date'].strftime('%d-%b-%Y')} to {data['sub_date'].strftime('%d-%b-%Y')}")
                st.markdown(f"**Status:** {data['status']}")
                
        st.markdown(f"**Task Description:** {data['desc']}")
        st.markdown(f"**Outcome:** {data['out'] if data['out'] else '-'}")
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_b1, col_b2 = st.columns(2)
        with col_b1: st.button("✏️ Edit Details", use_container_width=True, on_click=tsk_go_edit)
        with col_b2:
            if st.button("✅ Confirm & Assign Task", type="primary", use_container_width=True):
                t_id = f"TSK-{int(time.time())}"
                success = save_new_task(t_id, data['emp'], data['proj'], data['desc'], data['prio'], data['status'], data['out'], data['assign_date'].strftime('%d-%b-%Y'), data['sub_date'].strftime('%d-%b-%Y'))
                if success:
                    st.success("Task successfully assigned!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⚠️ Error saving task.")

# ==========================================
# MAIN PAGE RENDER (Table & UI)
# ==========================================

def render_task_ui(df, user_role):
    if len(df) == 0:
        st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO TASKS FOUND</h4>", unsafe_allow_html=True)
        return

    st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 2, 1.5, 1, 1, 1.5])
    with col1: st.markdown("**Assigned To**")
    with col2: st.markdown("**Project Name**")
    with col3: st.markdown("**Task**")
    with col4: st.markdown("**Dates (Asgn - Sub)**")
    with col5: st.markdown("**Priority**")
    with col6: st.markdown("**Status**")
    with col7: st.markdown("**Action**")
    st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)

    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.datetime.now(ist).date()

    for idx, row in df.iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 1.5, 2, 1.5, 1, 1, 1.5], vertical_alignment="center")
        with c1: st.write(row['Employees Names'])
        with c2: st.write(row['Related Project'])
        with c3: st.write(row['Task'])
        with c4: st.markdown(f"<span style='font-size:14px;'>{row['Assign Date']}<br>to<br>{row['Submission Date']}</span>", unsafe_allow_html=True)
        with c5:
            p_color = "#ff4b4b" if row['Priority'] == 'High' else "#ff9900" if row['Priority'] == 'Medium' else "#39FF14"
            st.markdown(f"<span style='color:{p_color}; font-weight:bold;'>{row['Priority']}</span>", unsafe_allow_html=True)
        with c6:
            s_color = "#39FF14" if row['Status'] == 'Completed' else "#ff4b4b" if row['Status'] == 'Incomplete' else "#60a5fa"
            st.markdown(f"<span style='color:{s_color}; font-weight:bold;'>{row['Status']}</span>", unsafe_allow_html=True)

        with c7:
            # Deadline Calculation Logic
            try:
                sub_date_obj = datetime.datetime.strptime(row['Submission Date'], '%d-%b-%Y').date()
                days_late = (today - sub_date_obj).days
            except:
                days_late = 0

            # Only Admin/HR/Boss can Edit
            if user_role in ["Admin", "Lead", "HR", "Boss"]:
                if st.button("✏️ Edit Task", key=f"edit_{row['Task ID']}", use_container_width=True):
                    edit_task_dialog(row.to_dict())

            # Only Interns can Complete their own tasks
            elif user_role == "Intern":
                if row['Status'] == 'Active':
                    if days_late == 1:
                        st.markdown("<p style='color:#ff9900; font-size:11px; margin-bottom:5px; font-weight:bold;'>⚠️ Submit your task early as soon as possible!</p>", unsafe_allow_html=True)

                    if st.button("✅ Yes, Complete", key=f"comp_{row['Task ID']}", use_container_width=True):
                        # Strict rule check: >1 day late = Incomplete
                        if days_late > 1:
                            update_task_status_only(row['Task ID'], "Incomplete")
                            st.error("Marked as Incomplete (Late Submission)!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            update_task_status_only(row['Task ID'], "Completed")
                            st.success("Task Completed Successfully!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.markdown(f"<span style='color:{s_color}; font-size:14px; font-weight:bold;'>{row['Status']}</span>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

def show_task_page():
    if "task_db_initialized" not in st.session_state:
        init_task_db()
        st.session_state.task_db_initialized = True

    user_role = st.session_state.get('user_role', 'Admin')
    current_user = st.session_state.get('current_user_name', '')

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1: st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>📝 Task Details</h1>", unsafe_allow_html=True)
    with head_col2:
        if user_role in ["Admin", "Lead", "HR", "Boss"]:
            if st.button("➕ Add Task", type="primary", use_container_width=True):
                prepare_new_task() 
                add_task_dialog()  
            
    st.markdown("---")
    
    df = get_all_tasks()

    # Filter tasks specific to the logged-in intern
    if user_role == "Intern":
        df = df[df['Employees Names'].str.contains(current_user, na=False, regex=False)]

    render_task_ui(df, user_role)