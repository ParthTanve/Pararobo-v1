# 1. Importing required tools for the application
import streamlit as st
from utils import load_global_css
import time
import urllib.parse
import streamlit.components.v1 as components

# Page configuration must be the first Streamlit command
st.set_page_config(page_title="CRM Dashboard", layout="wide", initial_sidebar_state="expanded")

# Load custom global CSS styles (Dark Theme)
load_global_css()

# Import the Universal Authentication Backend
import auth

# ==========================================
# AUTO LOGIN CHECK (10 MINUTE PERSISTENCE)
# ==========================================
if not st.session_state.get('logged_in', False):
    session_token = st.query_params.get("session")
    if session_token:
        # Checking Token details dynamically
        username, email, role = auth.check_session(session_token)
        if username:
            st.session_state['logged_in'] = True
            st.session_state['current_user_name'] = username
            st.session_state['user_email'] = email
            st.session_state['user_role'] = role
        else:
            if "session" in st.query_params:
                del st.query_params["session"]

if not st.session_state.get('logged_in', False):
    auth.show_auth_page()
    st.stop()

# ==========================================
# EVERYTHING BELOW RUNS ONLY IF LOGGED IN
# ==========================================

import employeeDetail
import internDetail
import projectDetail
import taskDetail
import leadDetail
import clientDetail
import quotationAndProposal

current_page = st.query_params.get("page", "Dashboard")
user_role = st.session_state.get('user_role', 'Admin')

def navigate(page_name):
    st.query_params["page"] = page_name
    st.session_state['collapse_sidebar'] = True 

if st.session_state.get('collapse_sidebar', False):
    unique_id = int(time.time() * 1000) 
    components.html(
        f"""
        <div id="sidebar_trigger_{unique_id}"></div>
        <script>
        setTimeout(function() {{
            const doc = window.parent.document;
            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            if (sidebar) {{
                const openExpanders = sidebar.querySelectorAll('details[open] summary');
                for (let i = 0; i < openExpanders.length; i++) {{ openExpanders[i].click(); }}
            }}
            setTimeout(function() {{
                const buttons = doc.querySelectorAll('button');
                let clicked = false;
                for (let i = 0; i < buttons.length; i++) {{
                    let aria = buttons[i].getAttribute('aria-label');
                    let title = buttons[i].getAttribute('title');
                    if (aria === 'Collapse sidebar' || title === 'Collapse sidebar' || aria === 'Close' || title === 'Close') {{
                        buttons[i].click(); clicked = true; break;
                    }}
                }}
                if (!clicked && sidebar) {{
                    const firstBtn = sidebar.querySelector('button');
                    if (firstBtn) firstBtn.click();
                }}
            }}, 150); 
        }}, 50); 
        </script>
        """, height=0, width=0
    )
    st.session_state['collapse_sidebar'] = False

def create_clickable_kpi_card(title, value, delta, is_negative=False):
    delta_color = "#ff4b4b" if is_negative else "#39FF14" 
    safe_title = urllib.parse.quote(title)
    
    session_token = st.query_params.get("session", "")
    link_url = f"?page={safe_title}&session={session_token}" if session_token else f"?page={safe_title}"
    
    html_code = f"""
    <style>
    .kpi-link {{ text-decoration: none !important; display: block; }}
    .kpi-box {{ cursor: pointer; padding: 20px; border-radius: 10px; background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); transition: all 0.3s ease; height: 150px; display: flex; flex-direction: column; justify-content: space-evenly; box-sizing: border-box; }}
    .kpi-box:hover {{ transform: translateY(-5px); background-color: rgba(255, 255, 255, 0.1); border: 1px solid #3498db; box-shadow: 0px 8px 15px rgba(0, 0, 0, 0.3); }}
    </style>
    <a href="{link_url}" target="_self" class="kpi-link">
        <div class="kpi-box">
            <p style="margin: 0; font-size: 16px; font-weight: bold; color: #a1a1aa; line-height: 1.2;">{title}</p>
            <h2 style="margin: 0; font-size: 32px; color: #ffffff; line-height: 1.2;">{value}</h2>
            <p style="margin: 0; font-size: 16px; font-weight: bold; color: {delta_color}; line-height: 1.2;">{delta}</p>
        </div>
    </a>
    """
    st.markdown(html_code, unsafe_allow_html=True)
    
# ==========================================
# SECURE ROLE-BASED SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<h2>Menu</h2>", unsafe_allow_html=True)
    
    if st.button("📊 Dashboard", use_container_width=True):
        navigate("Dashboard")
        st.rerun()
        
    # Admin sees everything
    if user_role == 'Admin':
        with st.expander("🧑‍💼 Employees Detail"):
            if st.button("View Employees", use_container_width=True):
                navigate("Employees Detail"); st.rerun()
        with st.expander("🧑‍🎓 Interns Detail"):
             if st.button("View Intern", use_container_width=True):
                navigate("Intern Detail"); st.rerun()
        with st.expander("📂 Project Detail"):
            if st.button("View Projects", use_container_width=True):
                navigate("Project Detail"); st.rerun()
        with st.expander("📝 Task"):
            if st.button("View Tasks", use_container_width=True):
                navigate("Task"); st.rerun()
        with st.expander("🎯 Leads"):
            if st.button("View Leads", use_container_width=True):
                navigate("Lead Detail"); st.rerun()
        with st.expander("🤝 Client Management"):
            if st.button("View Clients", use_container_width=True):
                navigate("Client Detail"); st.rerun()
        with st.expander("📄 Quotation & Proposal"):
            if st.button("View Proposals", use_container_width=True):
                navigate("Quotation and Proposal"); st.rerun()
                
    # Intern sees strictly their required modules
    else:
        with st.expander("🧑‍🎓 My Intern Profile"):
             if st.button("View Profile & Logs", use_container_width=True):
                navigate("Intern Detail"); st.rerun()
        with st.expander("📝 My Tasks"):
            if st.button("View Assigned Tasks", use_container_width=True):
                navigate("Task"); st.rerun()

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        session_token = st.query_params.get("session")
        if session_token: auth.logout_session(session_token)
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

kpi_pages = [ "Total Leads", "Qualified Leads", "Active Clients", "Revenue This Month", "Pending Payments", "Ongoing Projects", "Team Utilization %", "Open Support Tickets", "Interns Active", "Proposal Conversion Rate" ]

# ==========================================
# PAGE ROUTING
# ==========================================
if current_page == "Dashboard":
    spacer_left, logo_col, text_col, spacer_right = st.columns([2.5, 1, 4, 2.5], vertical_alignment="center")
    with logo_col:
        try: st.image("image/pararobo.png", width=500)
        except: pass
    with text_col:
        try: st.image("image/pararobo text .png", width=500)
        except: pass

    welcome_name = st.session_state.get('current_user_name', '')
    role_tag = f" ({user_role})" if user_role == 'Intern' else ""
    st.markdown(f"<h3 style='text-align: left; margin-top: 15px;'>👋 Welcome, {welcome_name}{role_tag}! | 📊 Portal Dashboard</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # Hide Financial KPIs from Interns
    if user_role == 'Admin':
        row1_cols = st.columns(5)
        with row1_cols[0]: create_clickable_kpi_card("Total Leads", "1,245", "↑ 12%")
        with row1_cols[1]: create_clickable_kpi_card("Qualified Leads", "842", "↑ 5%")
        with row1_cols[2]: create_clickable_kpi_card("Active Clients", "150", "↑ 3")
        with row1_cols[3]: create_clickable_kpi_card("Revenue This Month", "$45,200", "↑ $2,400")
        with row1_cols[4]: create_clickable_kpi_card("Pending Payments", "$8,400", "↓ -$400", is_negative=True)
        st.markdown("<br>", unsafe_allow_html=True)
        row2_cols = st.columns(5)
        with row2_cols[0]: create_clickable_kpi_card("Ongoing Projects", "24", "↑ 2")
        with row2_cols[1]: create_clickable_kpi_card("Team Utilization %", "85%", "↑ 4%")
        with row2_cols[2]: create_clickable_kpi_card("Open Support Tickets", "12", "↓ -3", is_negative=True)
        with row2_cols[3]: create_clickable_kpi_card("Interns Active", "5", "↑ 1")
        with row2_cols[4]: create_clickable_kpi_card("Proposal Conversion Rate", "68%", "↑ 2.5%")
    else:
        st.info("💡 You are currently logged into the Intern Portal. Please use the sidebar to check your attendance, logs, and assigned tasks.")

elif current_page == "Employees Detail": employeeDetail.show_employee_page()
elif current_page == "Intern Detail": internDetail.show_intern_page()
elif current_page == "Task": taskDetail.show_task_page()
elif current_page == "Project Detail": projectDetail.show_project_page()
elif current_page == "Lead Detail": leadDetail.show_lead_page()
elif current_page == "Client Detail": clientDetail.show_client_page()
elif current_page == "Quotation and Proposal": quotationAndProposal.show_proposal_page()
elif current_page in kpi_pages:
    st.markdown(f"<h1>Welcome to {current_page}</h1>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"<h3>Detailed view and analytics for {current_page} will be displayed here.</h3>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("⬅ Back to Dashboard", use_container_width=False):
        navigate("Dashboard"); st.rerun()