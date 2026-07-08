# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import time

# 🟢 NAYA LOGIC: Firebase Database (db) config se import kar rahe hain
from config import db

# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

# This function creates an EMPTY database for LIVE usage
def init_task_db():
    # Firestore mein collections automatically create ho jate hain jab data add hota hai
    pass

# This function fetches all tasks from the database
def get_all_tasks():
    docs = db.collection("tasks").get()
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            'Employees Names': d.get('emp_name', ''),
            'Related Project': d.get('project', ''),
            'Task': d.get('task_desc', ''),
            'Priority': d.get('priority', ''),
            'Result': d.get('result', ''),
            'Outcome': d.get('outcome', ''),
            'Task ID': d.get('task_id', '')
        })
        
    df = pd.DataFrame(data_list)
    return df

# This function securely saves a new task into the database
def save_new_task(t_id, emp, proj, desc, prio, res, out):
    doc_ref = db.collection("tasks").document(t_id)
    
    if doc_ref.get().exists:
        return False
        
    doc_ref.set({
        "task_id": t_id,
        "emp_name": emp,
        "project": proj,
        "task_desc": desc,
        "priority": prio,
        "result": res,
        "outcome": out
    })
    return True

# ==========================================
# SAFE MEMORY LOGIC (Fixes the Data Loss Bug)
# ==========================================

# This function safely locks the data before moving to the Preview screen
def tsk_go_preview():
    p = st.session_state
    
    # Fetch data from the input boxes using safe keys
    emp = p.get("t_emp_in", "")
    proj = p.get("t_proj_in", "")
    prio = p.get("t_prio_in", "High")
    res = p.get("t_res_in", "Pending")
    desc = p.get("t_desc_in", "")
    out = p.get("t_out_in", "")

    # 1. Check if all required fields are filled
    if emp and proj and desc:
        # 2. Strict Validation: Sirf alphabets allowed for Employee Name
        if not emp.replace(" ", "").isalpha():
            p.tsk_error = "⚠️ Employee Name should only contain alphabets (No numbers allowed)."
        # 3. Strict Validation: Sirf alphabets allowed for Project Name
        elif not proj.replace(" ", "").isalpha():
            p.tsk_error = "⚠️ Project Name should only contain alphabets (No numbers allowed)."
        else:
            p.tsk_step = "preview"
            p.tsk_error = ""
            
            # Save data to a safe dictionary so it does not get deleted on refresh
            p.safe_tsk_data = {
                'emp': emp,
                'proj': proj,
                'prio': prio,
                'res': res,
                'desc': desc,
                'out': out
            }
    else:
        p.tsk_error = "⚠️ Please fill all mandatory fields (*)."

# This function switches the screen back to Edit mode
def tsk_go_edit():
    st.session_state.tsk_step = "form"

# This function resets old data when adding a brand new task
def prepare_new_task():
    st.session_state.tsk_step = "form"
    st.session_state.tsk_error = ""
    st.session_state.safe_tsk_data = {}
    
    # Delete old inputs from memory
    keys_to_clear = ["t_emp_in", "t_proj_in", "t_desc_in", "t_out_in"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

# Dialog: Add New Task Wizard (Form + Preview Mode)
@st.dialog("➕ Add New Task", width="large")
def add_task_dialog():
    
    # Check if the step variable is initialized
    if "tsk_step" not in st.session_state:
        st.session_state.tsk_step = "form"
        
    # Get safely stored drafts
    draft = st.session_state.get("safe_tsk_data", {})

    # ------------- STEP 1: FORM UI -------------
    if st.session_state.tsk_step == "form":
        st.markdown("<p style='color: #555;'>Fill out the details below to assign a new task.</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Employee Name *", value=draft.get('emp', ''), key="t_emp_in")
            st.text_input("Project Name *", value=draft.get('proj', ''), key="t_proj_in")
            
            prio_opts = ["High", "Medium", "Low"]
            p_idx = prio_opts.index(draft.get('prio', "High")) if draft.get('prio') in prio_opts else 0
            st.selectbox("Priority", prio_opts, index=p_idx, key="t_prio_in")
            
        with col2:
            res_opts = ["Pending", "In Progress", "Completed"]
            r_idx = res_opts.index(draft.get('res', "Pending")) if draft.get('res') in res_opts else 0
            st.selectbox("Result Status", res_opts, index=r_idx, key="t_res_in")
            
        st.text_area("Task Description *", value=draft.get('desc', ''), key="t_desc_in")
        st.text_area("Outcome", value=draft.get('out', ''), key="t_out_in")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Display validation errors
        if st.session_state.get("tsk_error"):
            st.error(st.session_state.tsk_error)
            
        # This button triggers the memory save logic
        st.button("👁️ Generate Preview", type="primary", use_container_width=True, on_click=tsk_go_preview)

    # ------------- STEP 2: PREVIEW UI -------------
    elif st.session_state.tsk_step == "preview":
        data = st.session_state.safe_tsk_data
        
        st.markdown("<h3 style='color: #333;'>👁️ Preview Task Details</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666;'>Please review the details before saving to the database.</p>", unsafe_allow_html=True)
        
        # Summary Display Box
        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f"**Employee Name:** {data['emp']}")
                st.markdown(f"**Project Name:** {data['proj']}")
                st.markdown(f"**Priority:** {data['prio']}")
            with col_p2:
                st.markdown(f"**Result Status:** {data['res']}")
                
        st.markdown(f"**Task Description:** {data['desc']}")
        st.markdown(f"**Outcome:** {data['out'] if data['out'] else '-'}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Action Buttons
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            # Send the user back to the form
            st.button("✏️ Edit Details", use_container_width=True, on_click=tsk_go_edit)
            
        with col_b2:
            # Confirm and save to database
            if st.button("✅ Confirm & Save Task", type="primary", use_container_width=True):
                # Generate unique ID for task
                t_id = f"TSK-{int(time.time())}"
                
                success = save_new_task(t_id, data['emp'], data['proj'], data['desc'], data['prio'], data['res'], data['out'])
                
                if success:
                    st.success("Task successfully assigned!")
                    time.sleep(1)
                    st.rerun() # Refresh dashboard
                else:
                    st.error("⚠️ Error saving task.")

# ==========================================
# MAIN PAGE RENDER (Table & UI)
# ==========================================

# Function to generate an HTML table for displaying the tasks
def create_task_table(df):
    # Check if database is empty - LIVE STATE MESSAGE
    if len(df) == 0:
        return "<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>"
        
    html_table = "<style>"
    html_table += ".task-table { width: 100%; border-collapse: collapse; background-color: #FFFFFF; color: #000000; margin-top: 15px; }"
    html_table += ".task-table th, .task-table td { border: 2px solid #000000; padding: 12px; text-align: left; }"
    html_table += ".task-table th { font-weight: bold; font-size: 16px; background-color: #F8F9FA; }"
    html_table += "</style>"
    html_table += "<table class='task-table'>"
    html_table += "<thead>"
    html_table += "<tr>"
    html_table += "<th>Employees Names</th>"
    html_table += "<th>Project Name</th>"
    html_table += "<th>Task</th>"
    html_table += "<th>Priority</th>"
    html_table += "<th>Result</th>"
    html_table += "<th>Outcome</th>"
    html_table += "</tr>"
    html_table += "</thead>"
    html_table += "<tbody>"
    
    # Loop through data and build rows
    for _, row in df.iterrows():
        priority_color = "#000000"
        if row['Priority'] == 'High':
            priority_color = "#ff0000"
        elif row['Priority'] == 'Medium':
            priority_color = "#ff9900"
        elif row['Priority'] == 'Low':
            priority_color = "#00b300"
            
        result_color = "#000000"
        if row['Result'] == 'Completed':
            result_color = "#00b300"
        elif row['Result'] == 'Pending':
            result_color = "#ff0000"
        elif row['Result'] == 'In Progress':
            result_color = "#0000EE"

        html_table += "<tr>"
        html_table += f"<td><strong>{row['Employees Names']}</strong></td>"
        html_table += f"<td><strong>{row['Related Project']}</strong></td>"
        html_table += f"<td>{row['Task']}</td>"
        html_table += f"<td style='color: {priority_color}; font-weight: bold;'>{row['Priority']}</td>"
        html_table += f"<td style='color: {result_color}; font-weight: bold;'>{row['Result']}</td>"
        html_table += f"<td>{row['Outcome']}</td>"
        html_table += "</tr>"
        
    html_table += "</tbody></table>"
    return html_table

# Main function to show the Task Details page
def show_task_page():
    # Start the database automatically on startup
    if "task_db_initialized" not in st.session_state:
        init_task_db()
        st.session_state.task_db_initialized = True

    # Header section
    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #000000; margin-bottom: 0px;'>📝 Task Details</h1>", unsafe_allow_html=True)
    with head_col2:
        # Button to open the Add Task form
        if st.button("➕ Add Task", type="primary", use_container_width=True):
            prepare_new_task() # Clean up memory for a fresh form
            add_task_dialog()  # Open the popup
            
    st.markdown("---")
    
    # Get data from database and render the table
    df = get_all_tasks()
    st.markdown(create_task_table(df), unsafe_allow_html=True)