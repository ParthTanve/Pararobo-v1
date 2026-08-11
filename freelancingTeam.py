# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import time
import datetime
import pytz
import base64 # 🟢 Added for handling file uploads

# 🟢 NAYA LOGIC: Firebase Database (db) aur config
from config import is_valid_email, db

# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

def init_freelance_db():
    # Firestore mein collections automatically create ho jate hain jab data add hota hai
    pass

@st.cache_data(ttl=3600)
def get_all_freelancers():
    docs = db.collection("freelancers").get()
    
    data_list = []
    for doc in docs:
        data_list.append(doc.to_dict())
        
    df = pd.DataFrame(data_list)
    if not df.empty and "created_at" in df.columns:
        df = df.sort_values(by="created_at", ascending=False)
    return df

def save_new_freelancer(f_id, name, contact, email, domain, experience, rate, created_time, doc_b64, doc_name):
    # Duplicate email check
    if db.collection("freelancers").where("email", "==", email).get():
        return "duplicate_email"
        
    doc_ref = db.collection("freelancers").document(f_id)
    if doc_ref.get().exists:
        return "duplicate_id" 
        
    doc_ref.set({
        "freelancer_id": f_id,
        "name": name,
        "contact": contact,
        "email": email,
        "domain": domain,
        "experience": experience,
        "hourly_rate": rate,
        "created_at": created_time,
        "assigned_project": "-",
        "document_data": doc_b64,  # 🟢 Added Document Data
        "document_name": doc_name  # 🟢 Added Document Name
    })
    get_all_freelancers.clear() # Cache clear karna zaroori hai
    return "success"

def update_freelancer_db(f_id, name, contact, email, domain, experience, rate, doc_b64, doc_name):
    update_data = {
        "name": name,
        "contact": contact,
        "email": email,
        "domain": domain,
        "experience": experience,
        "hourly_rate": rate
    }
    
    # 🟢 Agar naya document upload hua hai tabhi database me update karenge
    if doc_b64 is not None:
        update_data["document_data"] = doc_b64
        update_data["document_name"] = doc_name
        
    db.collection("freelancers").document(f_id).update(update_data)
    get_all_freelancers.clear()

def delete_freelancer(f_id):
    db.collection("freelancers").document(f_id).delete()
    get_all_freelancers.clear()

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

@st.dialog("➕ Add New Freelancer", width="large")
def add_freelancer_dialog():
    st.markdown("<p style='color: #a1a1aa;'>Enter the freelancer details below.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        f_name = st.text_input("Full Name *", placeholder="e.g. John Doe", key="f_name_in")
        f_contact = st.text_input("Contact Number *", placeholder="9876543210", key="f_contact_in")
        
        domain_opts = ["UI/UX Designer", "Frontend Developer", "Backend Developer", "FullStack Developer", "AI/ML Engineer", "Graphic Designer", "Video Editor", "Content Writer", "Digital Marketer"]
        f_domain = st.selectbox("Core Skill / Domain *", domain_opts, key="f_domain_in")
        
        f_rate = st.text_input("Hourly/Project Rate (₹) *", placeholder="e.g. 500/hr or 10000/project", key="f_rate_in")

    with col2:
        f_email = st.text_input("Email ID *", placeholder="john@freelance.com", key="f_email_in")
        
        exp_opts = ["Fresher (0-1 year)", "Intermediate (1-3 years)", "Experienced (3-5 years)", "Expert (5+ years)"]
        f_exp = st.selectbox("Experience Level *", exp_opts, key="f_exp_in")
        
        # 🟢 Status hataya aur uski jagah Document Upload lagaya
        f_doc = st.file_uploader("Upload Document (JPEG, PDF) *", type=['jpeg', 'jpg', 'pdf'], key="f_doc_in")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("✅ Confirm & Add Freelancer", type="primary", use_container_width=True):
        if f_name and f_contact and f_email and f_rate and f_doc:
            if not f_name.replace(" ", "").isalpha():
                st.error("⚠️ Name should only contain alphabets.")
            elif not (f_contact.isdigit() and len(f_contact) == 10):
                st.error("⚠️ Contact number must be exactly 10 digits.")
            elif not is_valid_email(f_email):
                st.error("⚠️ Invalid Email Format!")
            else:
                # 🟢 File Process Logic
                doc_bytes = f_doc.getvalue()
                doc_b64 = base64.b64encode(doc_bytes).decode('utf-8')
                doc_name = f_doc.name
                
                f_id = f"FL-{int(time.time())}"
                ist = pytz.timezone('Asia/Kolkata')
                created_time = datetime.datetime.now(ist).strftime("%Y-%m-%d %I:%M %p")
                
                status = save_new_freelancer(f_id, f_name, f_contact, f_email, f_domain, f_exp, f_rate, created_time, doc_b64, doc_name)
                if status == "success":
                    st.success("New Freelancer successfully added!")
                    time.sleep(1)
                    st.rerun()
                elif status == "duplicate_email":
                    st.error("⚠️ Email already registered as a freelancer!")
        else:
            st.error("⚠️ Please fill all mandatory fields (*), including the document upload.")


@st.dialog("✏️ Edit Freelancer Details", width="large")
def edit_freelancer_dialog(data):
    st.markdown("<p style='color: #a1a1aa;'>Update the freelancer details below.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        e_name = st.text_input("Full Name *", value=data.get('name', ''), key=f"e_name_{data['freelancer_id']}")
        e_contact = st.text_input("Contact Number *", value=data.get('contact', ''), key=f"e_contact_{data['freelancer_id']}")
        
        domain_opts = ["UI/UX Designer", "Frontend Developer", "Backend Developer", "FullStack Developer", "AI/ML Engineer", "Graphic Designer", "Video Editor", "Content Writer", "Digital Marketer"]
        d_idx = domain_opts.index(data.get('domain')) if data.get('domain') in domain_opts else 0
        e_domain = st.selectbox("Core Skill / Domain *", domain_opts, index=d_idx, key=f"e_domain_{data['freelancer_id']}")
        
        e_rate = st.text_input("Hourly/Project Rate (₹) *", value=data.get('hourly_rate', ''), key=f"e_rate_{data['freelancer_id']}")

    with col2:
        e_email = st.text_input("Email ID *", value=data.get('email', ''), key=f"e_email_{data['freelancer_id']}")
        
        exp_opts = ["Fresher (0-1 year)", "Intermediate (1-3 years)", "Experienced (3-5 years)", "Expert (5+ years)"]
        e_idx = exp_opts.index(data.get('experience')) if data.get('experience') in exp_opts else 0
        e_exp = st.selectbox("Experience Level *", exp_opts, index=e_idx, key=f"e_exp_{data['freelancer_id']}")
        
        # 🟢 Status hatakar Document Upload Replace ka option diya
        current_doc = data.get('document_name', 'None')
        st.markdown(f"<span style='font-size:14px; color:#a1a1aa;'>Current Document: <b>{current_doc}</b></span>", unsafe_allow_html=True)
        e_doc = st.file_uploader("Upload New Document to Replace", type=['jpeg', 'jpg', 'pdf'], key=f"e_doc_{data['freelancer_id']}")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("💾 Save Changes", type="primary", use_container_width=True):
        if e_name and e_contact and e_email and e_rate:
            if not e_name.replace(" ", "").isalpha():
                st.error("⚠️ Name should only contain alphabets.")
            elif not (e_contact.isdigit() and len(e_contact) == 10):
                st.error("⚠️ Contact number must be exactly 10 digits.")
            elif not is_valid_email(e_email):
                st.error("⚠️ Invalid Email Format!")
            else:
                doc_b64 = None
                doc_name = None
                
                # 🟢 Agar user naya document dalta hai toh usko process karenge
                if e_doc:
                    doc_bytes = e_doc.getvalue()
                    doc_b64 = base64.b64encode(doc_bytes).decode('utf-8')
                    doc_name = e_doc.name
                    
                update_freelancer_db(data['freelancer_id'], e_name, e_contact, e_email, e_domain, e_exp, e_rate, doc_b64, doc_name)
                st.success("Freelancer details updated successfully!")
                time.sleep(1)
                st.rerun()
        else:
            st.error("⚠️ Please fill all mandatory fields (*).")

# ==========================================
# MAIN PAGE RENDER (Table & UI)
# ==========================================

def show_freelance_page():
    if "fl_db_initialized" not in st.session_state:
        init_freelance_db()
        st.session_state.fl_db_initialized = True

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>🌍 FreeLancing Team Management</h1>", unsafe_allow_html=True)
    with head_col2:
        if st.button("➕ Add Freelancer", type="primary", use_container_width=True):
            add_freelancer_dialog()  
            
    st.markdown("---")

    df = get_all_freelancers()
    
    if len(df) == 0:
        st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO FREELANCERS FOUND IN DATABASE</h4>", unsafe_allow_html=True)
    else:
        st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        # 🟢 Document Button ke hisab se Column width adjust ki
        h_cols = st.columns([0.5, 1.5, 1.2, 1.5, 1.5, 1.0, 1.5, 0.8], vertical_alignment="center")
        with h_cols[0]: st.markdown("**Select**")
        with h_cols[1]: st.markdown("**Name**")
        with h_cols[2]: st.markdown("**Contact**")
        with h_cols[3]: st.markdown("**Email**")
        with h_cols[4]: st.markdown("**Domain / Skill**")
        with h_cols[5]: st.markdown("**Rate**")
        with h_cols[6]: st.markdown("**Document**") # 🟢 Status replaced by Document
        with h_cols[7]: st.markdown("**Edit**")
        st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
        
        to_delete = []
        
        for idx, row in df.iterrows():
            cols = st.columns([0.5, 1.5, 1.2, 1.5, 1.5, 1.0, 1.5, 0.8], vertical_alignment="center")
            
            with cols[0]: 
                if st.checkbox("", key=f"del_chk_{row['freelancer_id']}"):
                    to_delete.append(row['freelancer_id'])
                    
            with cols[1]: st.write(f"**{row['name']}**")
            with cols[2]: st.write(row['contact'])
            with cols[3]: st.write(row['email'])
            with cols[4]: st.write(row['domain'])
            with cols[5]: st.write(f"₹ {row['hourly_rate']}")
            
            # 🟢 Yahan Document Download Button aayega
            with cols[6]: 
                d_name = row.get('document_name', '')
                d_b64 = row.get('document_data', '')
                
                if d_name and d_b64:
                    d_bytes = base64.b64decode(d_b64)
                    mime_type = "application/pdf" if d_name.lower().endswith(".pdf") else "image/jpeg"
                    st.download_button(label="📄 Download", data=d_bytes, file_name=d_name, mime=mime_type, key=f"dl_{row['freelancer_id']}")
                else:
                    st.markdown("<span style='color: #888888;'>No Doc</span>", unsafe_allow_html=True)
            
            with cols[7]:
                if st.button("✏️", key=f"edit_btn_{row['freelancer_id']}", help="Edit details"):
                    edit_freelancer_dialog(row.to_dict())
                
            st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            
        if to_delete:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f" Delete {len(to_delete)} Selected Freelancer(s)", type="primary", use_container_width=True):
                for fid in to_delete:
                    delete_freelancer(fid)
                st.success("Selected freelancers deleted successfully!")
                time.sleep(1)
                st.rerun()