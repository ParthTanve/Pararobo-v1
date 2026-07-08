# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import tempfile
import os
import sqlite3
import base64
import time
import datetime
import streamlit.components.v1 as components

# Importing PDF library for report generation
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# ==========================================
# DATABASE SECTION (Handles Data Storage)
# ==========================================

# This function creates an EMPTY database for LIVE usage
def init_project_db():
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # Create the projects table with all required columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT,
            project_category TEXT,
            description TEXT,
            client_name TEXT,
            revenue REAL,
            paid REAL,
            unpaid REAL,
            tools TEXT,
            assigned_employee TEXT,
            start_date TEXT,
            end_date TEXT,
            progress TEXT,
            status TEXT,
            doc_data BLOB,
            doc_name TEXT,
            team_lead TEXT
        )
    ''')
    
    # Safely add team_lead column for older database structures
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN team_lead TEXT")
    except sqlite3.OperationalError:
        pass
    
    # DUMMY DATA COMPLETELY REMOVED FOR LIVE DEPLOYMENT
    
    conn.commit()
    conn.close()

# Function to fetch intern names from database
def get_intern_names():
    try:
        conn = sqlite3.connect("crm_main.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM interns")
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names if names else ["No Interns Found"]
    except sqlite3.OperationalError:
        return ["Database not initialized yet"]

# This function fetches all projects from the database
def get_all_projects():
    conn = sqlite3.connect("crm_main.db")
    # ORDER BY project_id DESC ensures that the newest projects always show at the top!
    query = """
        SELECT 
            project_id AS 'Project ID', project_name AS 'Project Name', project_category AS 'Project Category',
            revenue AS 'Revenue', paid AS 'Paid', unpaid AS 'Unpaid', progress AS 'Progress of Project',
            end_date AS 'Deadline Date', start_date AS 'Start Date', description AS 'Description',
            client_name AS 'Client Name', tools AS 'Tools and Language', 
            team_lead AS 'Team Lead', assigned_employee AS 'Assigned Intern',
            status AS 'Status', doc_data, doc_name
        FROM projects
        ORDER BY project_id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# This function securely saves a new project into the database
def save_new_project(p_id, name, category, desc, client, rev, tools, emp, s_date, e_date, status, file_data, file_name, t_lead):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    paid = 0.0
    unpaid = float(rev)
    progress = "0%"
    try:
        # Insert the data into the projects table
        cursor.execute('''
            INSERT INTO projects (project_id, project_name, project_category, description, client_name, revenue, paid, unpaid, tools, assigned_employee, start_date, end_date, progress, status, doc_data, doc_name, team_lead)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (p_id, name, category, desc, client, rev, paid, unpaid, tools, emp, s_date, e_date, progress, status, file_data, file_name, t_lead))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# This function deletes a project permanently
def delete_project(p_id):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE project_id = ?", (p_id,))
    conn.commit()
    conn.close()

# ==========================================
# SAFE MEMORY LOGIC (Fixes Data Loss Bug)
# ==========================================

# This function safely locks data before moving to the Preview screen
def prj_go_preview():
    p = st.session_state
    
    # Fetch required details from the inputs
    name = p.get("p_name_in", "")
    client = p.get("p_client_in", "")
    
    # 1. Check if mandatory fields are filled
    if name and client:
        # 2. Strict Validation: Sirf alphabets allowed for names
        if not name.replace(" ", "").isalpha():
            p.prj_error = "⚠️ Project Name should only contain alphabets (No numbers allowed)."
        elif not client.replace(" ", "").isalpha():
            p.prj_error = "⚠️ Client Name should only contain alphabets (No numbers allowed)."
        else:
            p.prj_step = "preview"
            p.prj_error = ""
            
            # Save all details safely to a dictionary so they don't get deleted
            p.safe_prj_data = {
                'category': p.get("p_category_in", "Mobile App"),
                'name': name,
                'desc': p.get("p_desc_in", ""),
                'client': client,
                'status': p.get("p_status_in", "Active"),  # DEFAULT changed to Active to show immediately
                'rev': p.get("p_rev_in", 0.0),
                'tools': p.get("p_tools_in", ""),
                't_lead': p.get("p_t_lead_in", "Prajatak sir"),
                'emp': p.get("p_emp_in", "None"),
                's_date': p.get("p_s_date_in", datetime.date.today()),
                'e_date': p.get("p_e_date_in", datetime.date.today())
            }
            
            # Save the uploaded document safely
            doc = p.get("p_doc_in")
            if doc is not None:
                p.prj_doc_data = doc.getvalue()
                p.prj_doc_name = doc.name
            elif "prj_doc_data" not in p:
                p.prj_doc_data = None
                p.prj_doc_name = None
    else:
        p.prj_error = "⚠️ Please fill all mandatory fields (*)."

# This function switches back to the form so the user can edit
def prj_go_edit():
    st.session_state.prj_step = "form"

# This function clears the memory when adding a brand new project
def prepare_new_project():
    st.session_state.prj_step = "form"
    st.session_state.prj_error = ""
    st.session_state.safe_prj_data = {}
    st.session_state.prj_doc_data = None
    st.session_state.prj_doc_name = None
    
    # Clean previous input variables
    keys_to_clear = ["p_category_in", "p_name_in", "p_desc_in", "p_client_in", "p_status_in", "p_rev_in", "p_tools_in", "p_t_lead_in", "p_emp_in", "p_s_date_in", "p_e_date_in", "p_doc_in"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

# Dialog 1: Show full project details
@st.dialog("Project Full Details", width="large")
def show_project_popup(project):
    st.markdown(f"<h3 style='text-align: center; color: #ffffff; margin-top:0px;'>{project['Project Name']}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(f"**Project Category:** {project['Project Category']}", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**Project Description:** {project['Description']}", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Project Client Name:**<br>{project['Client Name']}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        rev_label = "Estimated Revenue" if project['Status'] in ["Onboard", "Pipeline"] else "Total Revenue"
        st.markdown(f"**{rev_label}:**<br>₹{project['Revenue']}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        s_date = project['Start Date'].strftime('%d:%m:%Y') if pd.notnull(project['Start Date']) else "-"
        st.markdown(f"**Start Date:**<br>{s_date}", unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"**Tools Used:**<br>{project['Tools and Language']}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # New Display Fields for Team Lead and Intern
        st.markdown(f"**Assigned Team Lead:**<br>{project.get('Team Lead', '-')}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"**Assigned Intern:**<br>{project['Assigned Intern']}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        e_date = project['Deadline Date'].strftime('%d:%m:%Y') if pd.notnull(project['Deadline Date']) else "-"
        st.markdown(f"**End Date:**<br>{e_date}", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # Document Download logic
    if project['doc_name']:
        st.markdown(f"**Uploaded Document:** {project['doc_name']}")
        st.download_button(label=" Download File", data=project['doc_data'], file_name=project['doc_name'], mime="application/pdf", use_container_width=True)
    else:
        st.info("No documentation uploaded for this project.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("Close Details", use_container_width=True):
        st.rerun()

    # Danger Zone: Deleting the project permanently
    with st.expander(" Remove Project (Danger Zone)"):
        st.error("⚠️ Warning: This will permanently delete the project from the database.")
        
        # Unselectable text for Project Name
        st.markdown(
            f"To confirm, type <span style='user-select: none; -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; pointer-events: none; font-weight: bold; color: #ffffff;'>{project['Project Name']}</span> below:", 
            unsafe_allow_html=True
        )
        
        confirm_input = st.text_input("Type here to confirm:", key=f"del_prj_{project['Project ID']}")
        
        # JS block to disable Paste and Drop action on the text input
        components.html(
            """
            <script>
            setTimeout(function() {
                const parentDoc = window.parent.document;
                const inputs = parentDoc.querySelectorAll('input[aria-label="Type here to confirm:"]');
                for (let i = 0; i < inputs.length; i++) {
                    inputs[i].onpaste = function(e) {
                        e.preventDefault();
                        return false;
                    };
                    inputs[i].ondrop = function(e) {
                        e.preventDefault();
                        return false;
                    };
                }
            }, 100);
            </script>
            """,
            height=0, width=0
        )

        if st.button("Permanently Delete", type="primary", use_container_width=True):
            if confirm_input.strip().lower() == project['Project Name'].strip().lower():
                delete_project(project['Project ID'])
                st.success(f"Project '{project['Project Name']}' removed successfully!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.warning("⚠️ Action Cancelled: You must type the project name exactly to delete the record.")

# Dialog 2: Add New Project Wizard (Form + Preview Mode)
@st.dialog("➕ Add New Project", width="large")
def add_project_dialog():
    
    # Check if step is initialized
    if "prj_step" not in st.session_state:
        st.session_state.prj_step = "form"
        
    draft = st.session_state.get("safe_prj_data", {})

    # ------------- STEP 1: FORM UI -------------
    if st.session_state.prj_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Fill out the details below to add a new project to the database.</p>", unsafe_allow_html=True)
        
        cat_opts = ["Mobile App", "Web App", "Custom Software", "System Integration", "CRM", "Digital Marketing", "Domain and Hosting"]
        c_idx = cat_opts.index(draft.get('category', "Mobile App")) if draft.get('category') in cat_opts else 0
        st.selectbox("Project Category", cat_opts, index=c_idx, key="p_category_in")
        
        st.text_input("Project Name *", value=draft.get('name', ''), key="p_name_in")
        st.text_area("Project Description", value=draft.get('desc', ''), key="p_desc_in")
        
        col1, col2 = st.columns(2)
        with col1:
            # Reverted back to Text Input for Client Name
            st.text_input("Project Client Name *", value=draft.get('client', ''), key="p_client_in")
            
        with col2:
            status_opts = ["Active", "Onboard"]
            s_idx = status_opts.index(draft.get('status', "Active")) if draft.get('status') in status_opts else 0
            st.selectbox("Initial Status", status_opts, index=s_idx, key="p_status_in")
            
        col3, col4 = st.columns(2)
        with col3:
            # Change revenue label dynamically based on project status
            current_status = st.session_state.get("p_status_in", draft.get('status', "Active"))
            rev_label = "Estimated Revenue (₹)" if current_status in ["Onboard", "Pipeline"] else "Total Revenue (₹)"
            st.number_input(rev_label, min_value=0.0, step=100.0, value=float(draft.get('rev', 0.0)), key="p_rev_in")
        with col4:
            st.text_input("Tools Used", value=draft.get('tools', ''), key="p_tools_in")
            
        # Updated Section for Team Lead and Intern assignments
        col5, col6 = st.columns(2)
        with col5:
            t_lead_opts = ["Prajatak sir", "Vikrant sir", "Shahid sir", "Arya sir","Sameer sir","Sumit sir"]
            t_idx = t_lead_opts.index(draft.get('t_lead', "Prajatak sir")) if draft.get('t_lead') in t_lead_opts else 0
            st.selectbox("Assigned Team Lead *", t_lead_opts, index=t_idx, key="p_t_lead_in")
        with col6:
            intern_list = get_intern_names()
            st.multiselect("Team Members (Select Interns)", intern_list, default=draft.get('t_members_list', []), key="p_emp_in")
            
        # Dates Section    
        col7, col8 = st.columns(2)
        with col7:
            st.date_input("Start Date", value=draft.get('s_date', datetime.date.today()), key="p_s_date_in")
        with col8:
            st.date_input("End Date", value=draft.get('e_date', datetime.date.today()), key="p_e_date_in")
            
        st.markdown("### Upload Documentation")
        st.file_uploader("Upload PDF Document (Optional)", type=['pdf'], key="p_doc_in")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Display validation errors
        if st.session_state.get("prj_error"):
            st.error(st.session_state.prj_error)
            
        # Triggers the memory save and changes to preview
        st.button("👁️ Generate Preview", type="primary", use_container_width=True, on_click=prj_go_preview)

    # ------------- STEP 2: PREVIEW UI -------------
    elif st.session_state.prj_step == "preview":
        data = st.session_state.safe_prj_data
        
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Project Details</h3>", unsafe_allow_html=True)
        
        # Summary Display Box
        with st.container(border=True):
            st.markdown(f"**Project Name:** {data['name']}")
            st.markdown(f"**Category:** {data['category']}")
            st.markdown(f"**Description:** {data['desc'] if data['desc'] else '-'}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Client Name:** {data['client']}")
                st.markdown(f"**Revenue:** ₹{data['rev']}")
                st.markdown(f"**Start Date:** {data['s_date'].strftime('%d-%b-%Y')}")
                st.markdown(f"**Assigned Team Lead:** {data['t_lead']}")
            with c2:
                st.markdown(f"**Status:** {data['status']}")
                st.markdown(f"**Tools Used:** {data['tools'] if data['tools'] else '-'}")
                st.markdown(f"**End Date:** {data['e_date'].strftime('%d-%b-%Y')}")
                st.markdown(f"**Assigned Intern:** {data['emp'] if data['emp'] else '-'}")
                
        # Show uploaded document details
        if st.session_state.get('prj_doc_name'):
            st.success(f"📎 Attached Document: {st.session_state.prj_doc_name}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Action Buttons
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.button("✏️ Edit Details", use_container_width=True, on_click=prj_go_edit)
            
        with col_b2:
            # Confirm and save to database
            if st.button("✅ Confirm & Save Project", type="primary", use_container_width=True):
                # Generates a safer ID so back-to-back saves don't clash
                p_id = f"PRJ-{int(time.time() * 1000)}"
                s_date_str = data['s_date'].strftime("%Y-%m-%d")
                e_date_str = data['e_date'].strftime("%Y-%m-%d")
                
                doc_bytes = st.session_state.get('prj_doc_data')
                doc_name = st.session_state.get('prj_doc_name')
                
                success = save_new_project(
                    p_id, data['name'], data['category'], data['desc'], data['client'], 
                    data['rev'], data['tools'], data['emp'], s_date_str, e_date_str, 
                    data['status'], doc_bytes, doc_name, data['t_lead']
                )
                
                if success:
                    st.success(f"Project '{data['name']}' successfully added!")
                    time.sleep(1)
                    st.rerun() # Refresh dashboard
                else:
                    st.error("⚠️ Error saving project.")

# ==========================================
# MAIN PAGE RENDER & GRID DISPLAY
# ==========================================

# This function displays the list of projects in a grid format
def display_project_grid(df, columns_to_show, key_prefix="default", is_onboard=False, show_checkboxes=False):
    # LIVE STATE MESSAGE for Empty Tables
    if len(df) == 0:
        st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
        return []

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
        
    weights = []
    if show_checkboxes:
        weights.append(0.5)
        
    for col in columns_to_show:
        if col == "Project Name": weights.append(2.5)
        elif col == "Description": weights.append(2.5)
        elif col == "Client Name": weights.append(1.5)
        elif col == "Project Category": weights.append(1.5)
        else: weights.append(1.2)
        
    st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    header_cols = st.columns(weights, vertical_alignment="center")
    
    c_idx = 0
    if show_checkboxes:
        header_cols[c_idx].markdown("<p style='margin: 5px 0px; font-weight: bold; color: #ffffff;'>Select</p>", unsafe_allow_html=True)
        c_idx += 1
        
    for col in columns_to_show:
        display_name = col
        if col == "Deadline Date": 
            display_name = "Submission Date"
        elif col == "Revenue": 
            display_name = "Estimated Revenue" if is_onboard else "Total Revenue"
            
        header_cols[c_idx].markdown(f"<p style='margin: 5px 0px; font-weight: bold; color: #ffffff;'>{display_name}</p>", unsafe_allow_html=True)
        c_idx += 1
        
    st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    selected_projects = []
    
    for idx, row in df.iterrows():
        row_cols = st.columns(weights, vertical_alignment="center")
        
        c_idx = 0
        if show_checkboxes:
            is_checked = row_cols[c_idx].checkbox("", key=f"chk_{row['Project ID']}_{idx}_{key_prefix}")
            if is_checked:
                selected_projects.append(row)
            c_idx += 1
            
        for col in columns_to_show:
            if col == "Project Name":
                if row_cols[c_idx].button(f"{row['Project Name']}", key=f"prj_{row['Project ID']}_{idx}_{key_prefix}", use_container_width=True, type="tertiary"):
                    show_project_popup(row)
            elif col in ["Start Date", "Deadline Date"]:
                if pd.notnull(row[col]):
                    row_cols[c_idx].write(row[col].strftime('%d:%m:%Y'))
                else:
                    row_cols[c_idx].write("-")
            elif col == "Unpaid":
                row_cols[c_idx].markdown(f"<span style='color:#ff4b4b; font-weight:bold;'>₹{row[col]}</span>", unsafe_allow_html=True)
            elif col in ["Paid", "Revenue"]:
                row_cols[c_idx].markdown(f"<span style='color:#39FF14; font-weight:bold;'>₹{row[col]}</span>", unsafe_allow_html=True)
            else:
                row_cols[c_idx].write(str(row[col]))
            c_idx += 1
                
        st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    return selected_projects

# Main function to show the Project Details page
def show_project_page():
    if "project_db_initialized" not in st.session_state:
        init_project_db()
        st.session_state.project_db_initialized = True
    
    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>Project Detail</h1>", unsafe_allow_html=True)
    with head_col2:
        # Opens the Add Project Popup
        if st.button("➕ Add Project", type="primary", use_container_width=True):
            prepare_new_project() # Clean up memory for a fresh form
            add_project_dialog()  # Open the popup
            
    st.markdown("---")

    df = get_all_projects()
    
    df["Deadline Date"] = pd.to_datetime(df["Deadline Date"], errors='coerce')
    df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce')

    # Top Navigation Menu
    project_tab = st.radio("Navigation Menu:", [
        "Projects Active", 
        "Projects Deadlines", 
        "Projects Completed", 
        "Projects Onboard", 
        "Categorized View", 
        "Final Reports"
    ], horizontal=True, label_visibility="collapsed", key="project_main_tab")

    st.markdown("<br>", unsafe_allow_html=True)

    if project_tab == "Projects Active":
        st.markdown("<h3 style='color:#ffffff; margin-top:0px;'>Projects Active</h3>", unsafe_allow_html=True)
        display_project_grid(df[df["Status"]=="Active"], ["Project Name", "Project Category", "Revenue", "Progress of Project", "Deadline Date"], "tab1_active")
        
    elif project_tab == "Projects Deadlines":
        st.markdown("<h3 style='color:#ffffff; margin-top:0px;'>Project Deadlines</h3>", unsafe_allow_html=True)
        df_sorted = df.sort_values(by=["Deadline Date", "Revenue"], ascending=[True, False])
        display_project_grid(df_sorted, ["Project Name", "Project Category", "Deadline Date", "Revenue"], "tab2_deadline")
        
    elif project_tab == "Projects Completed":
        st.markdown("<h3 style='color:#ffffff; margin-top:0px;'>Projects Completed </h3>", unsafe_allow_html=True)
        comp_df = df[df["Status"] == "Completed"].sort_values(by="Unpaid", ascending=False)
        display_project_grid(comp_df, ["Project Name", "Project Category", "Deadline Date", "Revenue", "Paid", "Unpaid"], "tab3_completed")
        
    elif project_tab == "Projects Onboard":
        st.markdown("<h3 style='color:#ffffff; margin-top:0px;'>Projects Onboard</h3>", unsafe_allow_html=True)
        pipe_df = df[df["Status"].isin(["Pipeline", "Onboard"])]
        display_project_grid(pipe_df, ["Client Name", "Project Name", "Project Category", "Description", "Revenue", "Start Date"], "tab4_Onboard", is_onboard=True)
        
    elif project_tab == "Categorized View":
        st.markdown("<h3 style='color:#ffffff; margin-top:0px;'>Filter by Category & Status</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: selected_category = st.selectbox("Select Project Category", ["All", "Digital Marketing", "Web App", "Mobile App", "CRM", "Custom Software", "System Integration", "Domain and Hosting"])
        with col2: selected_status = st.selectbox("Select Status", ["All", "Active", "Onboard", "Completed", "Pipeline"])
        
        filtered_df = df.copy()
        if selected_category != "All": filtered_df = filtered_df[filtered_df["Project Category"] == selected_category]
        if selected_status != "All": filtered_df = filtered_df[filtered_df["Status"] == selected_status]
        filtered_df = filtered_df.sort_values(by="Deadline Date", ascending=True)
        
        display_project_grid(filtered_df, ["Project Name", "Project Category", "Status", "Start Date", "Deadline Date"], "tab5_category")

    elif project_tab == "Final Reports":
        st.markdown("<h3 style='color: #ffffff; margin-top:0px;'>Download Detailed Project Report</h3>", unsafe_allow_html=True)
        
        
        report_cols_to_show = ["Project Category", "Project Name", "Status", "Start Date", "Deadline Date"]
        report_df = df.copy() 
        report_df = report_df.sort_values(by=["Project Category", "Project Name"])
        
        selected_rows = display_project_grid(report_df, report_cols_to_show, "tab6_report", show_checkboxes=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if len(selected_rows) > 0:
            selected_df = pd.DataFrame(selected_rows)
            
            st.success(f"✅ {len(selected_df)} Project(s) Selected for Detailed Report")
            col_ex, col_pdf = st.columns(2)
            
            # Export to CSV
            csv_export_df = selected_df.drop(columns=['doc_data', 'doc_name'], errors='ignore')
            csv_export_df["Start Date"] = pd.to_datetime(csv_export_df["Start Date"], errors='coerce').dt.strftime('%d-%b-%Y')
            csv_export_df["Deadline Date"] = pd.to_datetime(csv_export_df["Deadline Date"], errors='coerce').dt.strftime('%d-%b-%Y')
            csv = csv_export_df.to_csv(index=False).encode('utf-8')
            
            with col_ex:
                st.download_button(label="📥 Download Detailed CSV", data=csv, file_name="Detailed_Projects_Report.csv", mime="text/csv", use_container_width=True)
                
            with col_pdf:
                if FPDF is None: 
                    st.error("Library 'fpdf' install nahi hai. Terminal mein `pip install fpdf` run karein.")
                else:
                    # PDF Generation Code with Full Details
                    pdf = FPDF(orientation='P', unit='mm', format='A4')
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 18)
                    pdf.cell(0, 10, "Detailed Project Report", ln=True, align='C')
                    pdf.ln(5)
                    
                    def safe_text(val):
                        return str(val).encode('latin-1', 'replace').decode('latin-1') if pd.notnull(val) else "-"
                    
                    for _, row in selected_df.iterrows():
                        pdf.set_font("Arial", 'B', 14)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 10, f"Project Name: {safe_text(row['Project Name'])}", ln=True)
                        
                        pdf.set_font("Arial", '', 11)
                        pdf.set_text_color(50, 50, 50)
                        
                        sd = pd.to_datetime(row['Start Date'], errors='coerce').strftime('%d-%b-%Y') if pd.notnull(row['Start Date']) else "-"
                        ed = pd.to_datetime(row['Deadline Date'], errors='coerce').strftime('%d-%b-%Y') if pd.notnull(row['Deadline Date']) else "-"
                        
                        pdf.cell(0, 8, f"Category: {safe_text(row['Project Category'])}   |   Status: {safe_text(row['Status'])}", ln=True)
                        pdf.cell(0, 8, f"Client Name: {safe_text(row['Client Name'])}", ln=True)
                        pdf.cell(0, 8, f"Estimated/Total Revenue: INR {safe_text(row['Revenue'])}", ln=True)
                        pdf.cell(0, 8, f"Start Date: {sd}   |   Deadline Date: {ed}", ln=True)
                        pdf.cell(0, 8, f"Tools & Language: {safe_text(row['Tools and Language'])}", ln=True)
                        pdf.cell(0, 8, f"Assigned Team Lead: {safe_text(row.get('Team Lead', '-'))}   |   Assigned Intern: {safe_text(row['Assigned Intern'])}", ln=True)
                        
                        pdf.ln(2)
                        pdf.multi_cell(0, 6, f"Description: {safe_text(row['Description'])}")
                        
                        pdf.ln(8)
                        pdf.set_draw_color(200, 200, 200)
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(5)
                        
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp: tmp_name = tmp.name
                    pdf.output(tmp_name)
                    with open(tmp_name, "rb") as f: pdf_bytes = f.read()
                    os.remove(tmp_name)
                    
                    st.download_button(label="📄 Download Detailed PDF", data=pdf_bytes, file_name="Detailed_Projects_Report.pdf", mime="application/pdf", use_container_width=True)
    