# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import base64
import os
import time
import datetime
import re
import pytz

# 🟢 NAYA LOGIC: Firebase Database (db) aur config
from config import is_valid_email, db

# ==========================================
# HELPER FUNCTIONS
# ==========================================


# This function loads real platform icons from your local folder
def get_image_html(platform_name):
    # Mapping platform names to their respective image files
    platform_map = {
        "LinkedIn": "linkedin.png",
        "WhatsApp": "whatsapp.png",
        "Facebook": "facebook.png",
        "Instagram": "social.png",
        "Email": "email.png",
        "Cold Call": "coldcall.png",
        "Walkin": "walkin.png"  # New added fallback image for Walkin
    }
    
    image_name = platform_map.get(platform_name, "default.png")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 🟢 PATH UPDATED: Ab direct main folder se images read karega
    image_path = os.path.join(current_dir, image_name)
    
    # Agar image mil gayi toh usko real icon ki tarah load karega
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        return f'<img src="data:image/png;base64,{encoded_string}" width="20" style="vertical-align: middle; margin-right: 8px;"> {platform_name}'
    else:
        # Failsafe logic just in case image is missing
        icon_emoji = "🚶" if platform_name == "Walkin" else "🌐"
        return f'<span style="font-size: 18px; margin-right: 8px;">{icon_emoji}</span> {platform_name}'

# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

def init_lead_db():
    # Firestore mein collections automatically create ho jate hain jab data add hota hai
    pass

def get_all_leads():
    docs = db.collection("leads").get()
    
    data_list = []
    for doc in docs:
        data_list.append(doc.to_dict())
        
    df = pd.DataFrame(data_list)
    # Sort by created_at manually to keep the newest leads on top
    if not df.empty and "created_at" in df.columns:
        df = df.sort_values(by="created_at", ascending=False)
        
    return df

def save_new_lead(l_id, name, contact, email, platform, purpose, l_type, created_time):
    doc_ref = db.collection("leads").document(l_id)
    
    if doc_ref.get().exists:
        return False 
        
    doc_ref.set({
        "lead_id": l_id,
        "lead_name": name,
        "contact": contact,
        "email": email,
        "platform": platform,
        "purpose": purpose,
        "lead_type": l_type,
        "created_at": created_time,
        "not_connected": False  # Independent flag added so checkboxes start empty
    })
    return True

# 🟢 NAYA LOGIC: Table Checkbox se Direct Status Update karne ke liye function
def update_lead_status_db(lead_id, new_type, is_not_connected):
    db.collection("leads").document(lead_id).update({
        "lead_type": new_type,
        "not_connected": is_not_connected
    })

# Lead Delete karne ke liye
def delete_lead(lead_id):
    db.collection("leads").document(lead_id).delete()

# ==========================================
# SAFE MEMORY LOGIC 
# ==========================================

def ld_go_preview():
    p = st.session_state
    
    name = p.get("ld_name_in", "")
    contact = p.get("ld_contact_in", "")
    platform = p.get("ld_platform_in", "WhatsApp")
    email = p.get("ld_email_in", "").strip() 
    purpose = p.get("ld_purpose_in", "")
    
    # By default status 'Cold' rahega
    l_type = p.get("ld_type_in", "Cold")

    # Date and Time fetching
    sel_date = p.get("ld_date_in", datetime.date.today())
    ist = pytz.timezone('Asia/Kolkata')
    curr_time = datetime.datetime.now(ist).strftime("%I:%M %p")
    # Date + Time mila ke final creation time banaya
    final_datetime = f"{sel_date.strftime('%Y-%m-%d')} {curr_time}"

    if name and contact and email and purpose:
        if not name.replace(" ", "").isalpha(): p.ld_error = "⚠️ Lead Name should only contain alphabets (No numbers allowed)."
        elif not (contact.isdigit() and len(contact) == 10 and int(contact[0]) > 6): p.ld_error = "⚠️ Contact number must be exactly 10 digits and start with a number greater than 6 (e.g., 7, 8, or 9)."
        elif not is_valid_email(email): p.ld_error = "⚠️ Invalid Email Format! Please enter a valid email ID."
        else:
            p.ld_step = "preview"
            p.ld_error = ""
            p.safe_ld_data = {
                'name': name, 'contact': contact, 'email': email,
                'platform': platform, 'type': l_type, 'purpose': purpose,
                'datetime': final_datetime
            }
    else:
        p.ld_error = "⚠️ Please fill all mandatory fields (*)."

def ld_go_edit():
    st.session_state.ld_step = "form"

def prepare_new_lead():
    st.session_state.ld_step = "form"
    st.session_state.ld_error = ""
    st.session_state.safe_ld_data = {} 
    keys_to_clear = ["ld_name_in", "ld_contact_in", "ld_email_in", "ld_purpose_in", "ld_platform_in", "ld_date_in", "ld_type_in"]
    for k in keys_to_clear:
        if k in st.session_state: del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

@st.dialog("➕ Add New Lead", width="large")
def add_lead_dialog():
    if "ld_step" not in st.session_state: st.session_state.ld_step = "form"
    draft = st.session_state.get("safe_ld_data", {})
    ist = pytz.timezone('Asia/Kolkata')

    if st.session_state.ld_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Enter the new lead details below.</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Lead Name *", placeholder="e.g. John Doe", value=draft.get('name', ''), key="ld_name_in")
            st.text_input("Contact Number *", placeholder="9876543210", value=draft.get('contact', ''), key="ld_contact_in")
            # "Walkin" option added in platform
            p_opts = ["WhatsApp", "Facebook", "Instagram", "Email", "Cold Call", "LinkedIn", "Walkin"]
            p_idx = p_opts.index(draft.get('platform', "WhatsApp")) if draft.get('platform') in p_opts else 0
            st.selectbox("Source Platform *", p_opts, index=p_idx, key="ld_platform_in")
            
        with col2:
            st.text_input("Email ID *", placeholder="john@pararobo.com", value=draft.get('email', ''), key="ld_email_in")
            # Date Selector
            curr_d = draft.get('date_obj', datetime.datetime.now(ist).date())
            st.date_input("Select Lead Date *", value=curr_d, key="ld_date_in")
            
            # Type is strictly defaulted to Cold initially
            t_opts = ["Hot", "Warm", "Cold", "Not Connected"]
            t_idx = t_opts.index(draft.get('type', "Cold")) if draft.get('type') in t_opts else 2
            st.selectbox("Initial Lead Status *", t_opts, index=t_idx, key="ld_type_in")
            
        st.text_area("Lead Purpose / Requirement *", placeholder="Briefly describe what the client needs...", value=draft.get('purpose', ''), key="ld_purpose_in", height=100)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.get("ld_error"): st.error(st.session_state.ld_error)
        st.button("👁️ Generate Preview", type="primary", use_container_width=True, on_click=ld_go_preview)

    elif st.session_state.ld_step == "preview":
        data = st.session_state.safe_ld_data
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Lead Details</h3>", unsafe_allow_html=True)
        
        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f"**Lead Name:** {data['name']}")
                st.markdown(f"**Email ID:** {data['email']}")
                st.markdown(f"**Contact Number:** {data['contact']}")
            with col_p2:
                st.markdown(f"**Source Platform:** {data['platform']}")
                st.markdown(f"**Determined Status:** <span style='color:#39FF14;'>{data['type']}</span>", unsafe_allow_html=True)
                st.markdown(f"**Date & Time:** {data['datetime']}")
        st.markdown(f"**Purpose / Requirement:** {data['purpose']}")
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_b1, col_b2 = st.columns(2)
        with col_b1: st.button("✏️ Edit Details", use_container_width=True, on_click=ld_go_edit)
        with col_b2:
            if st.button("✅ Confirm & Save Lead", type="primary", use_container_width=True):
                l_id = f"LD-{int(time.time())}"
                status = save_new_lead(l_id, data['name'], data['contact'], data['email'], data['platform'], data['purpose'], data['type'], data['datetime'])
                if status:
                    st.success("New lead successfully added!")
                    time.sleep(1)
                    st.rerun() 
                else:
                    st.error("⚠️ Error saving lead. Please try again.")
                    st.rerun()

# ==========================================
# MAIN PAGE RENDER (Table & UI)
# ==========================================

def show_lead_page():
    if "lead_db_initialized" not in st.session_state:
        init_lead_db()
        st.session_state.lead_db_initialized = True

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>🎯 Leads Detail</h1>", unsafe_allow_html=True)
    with head_col2:
        if st.button("➕ Add Lead", type="primary", use_container_width=True):
            prepare_new_lead() 
            add_lead_dialog()  
            
    st.markdown("---")

    df = get_all_leads()
    
    if len(df) == 0:
        st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
    else:
        # 🟢 Email aur Date ko separate columns mein divide kar diya
        st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        h_cols = st.columns([0.5, 1.2, 1.2, 1.5, 1.0, 1.2, 1.5, 1.0, 0.8, 0.8], vertical_alignment="center")
        with h_cols[0]: st.markdown("**Select**")
        with h_cols[1]: st.markdown("**Lead Name**")
        with h_cols[2]: st.markdown("**Contact**")
        with h_cols[3]: st.markdown("**Email**")
        with h_cols[4]: st.markdown("**Date & Time**")
        with h_cols[5]: st.markdown("**Platform**")
        with h_cols[6]: st.markdown("**Purpose**")
        with h_cols[7]: st.markdown("**Lead Type**")
        with h_cols[8]: st.markdown("**Conn.**")
        with h_cols[9]: st.markdown("**Not Conn.**")
        st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        
        leads_to_delete = []
        
        for idx, row in df.iterrows():
            cols = st.columns([0.5, 1.2, 1.2, 1.5, 1.0, 1.2, 1.5, 1.0, 0.8, 0.8], vertical_alignment="center")
            
            with cols[0]: 
                if st.checkbox("", key=f"del_chk_{row['lead_id']}"):
                    leads_to_delete.append(row['lead_id'])
                    
            with cols[1]: st.write(f"{row['lead_name']}")
            with cols[2]: st.write(row['contact'])
            with cols[3]: st.write(row['email'])
            # 🟢 FIXED: Inline CSS removed to inherit default font styling
            with cols[4]: st.write(row['created_at'])
            with cols[5]: st.markdown(get_image_html(row['platform']), unsafe_allow_html=True)
            with cols[6]: st.write(row['purpose'])
            with cols[7]: 
                l_type = row['lead_type']
                lead_color = "#ffffff"
                if l_type == 'Hot': lead_color = "#ff4b4b"
                elif l_type == 'Warm': lead_color = "#ff9900"
                elif l_type == 'Cold': lead_color = "#3498db"
                elif l_type == 'Not Connected': lead_color = "#888888"
                st.markdown(f"<span style='color: {lead_color}; font-weight: bold;'>{l_type}</span>", unsafe_allow_html=True)
            
            # 🟢 Connected Checkbox (Smart toggle)
            with cols[8]:
                conn_val = (l_type == 'Warm')
                conn_check = st.checkbox("✅ Yes", value=conn_val, key=f"conn_{row['lead_id']}")
                if conn_check and not conn_val:
                    update_lead_status_db(row['lead_id'], "Warm", False)
                    st.rerun()
                elif not conn_check and conn_val:
                    update_lead_status_db(row['lead_id'], "Cold", False)
                    st.rerun()
                    
            # 🟢 Not Connected Checkbox (Smart toggle with Cold fallback)
            with cols[9]:
                notconn_val = row['not_connected'] if 'not_connected' in row else False
                notconn_check = st.checkbox("❌ No", value=notconn_val, key=f"notconn_{row['lead_id']}")
                if notconn_check and not notconn_val:
                    update_lead_status_db(row['lead_id'], "Cold", True)
                    st.rerun()
                elif not notconn_check and notconn_val:
                    update_lead_status_db(row['lead_id'], "Cold", False)
                    st.rerun()
                
            st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            
        if leads_to_delete:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f" Delete {len(leads_to_delete)} Selected Lead(s)", type="primary", use_container_width=True):
                for lid in leads_to_delete:
                    delete_lead(lid)
                st.success("Selected leads have been deleted successfully!")
                time.sleep(1)
                st.rerun()