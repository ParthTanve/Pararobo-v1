# 1. Importing required tools for the application
import streamlit as st
import pandas as pd
import datetime
import time
import base64
import re 
import pytz
import streamlit.components.v1 as components
from utils import load_global_css

# 🟢 NAYA LOGIC: Firebase Database (db) aur config
from config import is_valid_email, db

# ==========================================
# HELPER FUNCTIONS
# ==========================================



# ==========================================
# DATABASE SECTION (FIREBASE FIRESTORE)
# ==========================================

# Function to create an EMPTY database and table if it doesn't exist
def init_client_db():
    # Firestore mein collections automatically create ho jate hain jab data add hota hai
    pass

# Function to fetch intern names from interns collection to assign them to projects
def get_intern_names():
    try:
        docs = db.collection("interns").get()
        names = [doc.to_dict().get("name") for doc in docs if doc.to_dict().get("name")]
        return names if names else ["No Interns Found"]
    except Exception:
        return ["Database not initialized yet"]

# Function to automatically mark projects as 'Active' if start date arrives, or 'Completed' if end date passes
def auto_update_client_status():
    try:
        # India timezone set kiya taaki time exact match ho
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.datetime.now(ist).date()
        
        docs = db.collection("clients").get()
        
        for doc in docs:
            data = doc.to_dict()
            current_status = data.get("status")
            
            if current_status == "Completed":
                continue
                
            start_date_str = data.get("start_date")
            end_date_str = data.get("end_date")
            new_status = current_status
            
            # 1. Check Onboard/Pipeline -> Active (Agar aaj ki date Start Date ke barabar ya aage hai)
            if current_status in ["Onboard", "Pipeline"] and start_date_str:
                try:
                    sdate = datetime.datetime.strptime(start_date_str, "%d-%b-%Y").date()
                    if sdate <= today:
                        new_status = "Active"
                except Exception:
                    pass
            
            # 2. Check Active -> Completed (Agar aaj ki date End Date se aage nikal gayi hai)
            if new_status == "Active" and end_date_str:
                try:
                    edate = datetime.datetime.strptime(end_date_str, "%d-%b-%Y").date()
                    if edate < today:
                        new_status = "Completed"
                except Exception:
                    pass
                    
            # Agar status change hua hai, toh Database update kar do
            if new_status != current_status:
                doc.reference.update({"status": new_status})
                
                # Project collection mein bhi status sync kar do taaki baaki tabs update rahein
                p_name = data.get("project_name")
                if p_name:
                    p_docs = db.collection("projects").where("project_name", "==", p_name).get()
                    for p_doc in p_docs:
                        p_doc.reference.update({"status": new_status})
    except Exception:
        pass

# Function to update the deadline of a project and store the reason for extension
def update_client_deadline(c_id, new_end_date, reason):
    db.collection("clients").document(c_id).update({
        "end_date": new_end_date,
        "extension_reason": reason,
        "status": "Active"
    })

# Function to delete a client from the database
def delete_client(c_id):
    db.collection("clients").document(c_id).delete()

# Function to get all client details to display in the dashboard
def get_all_clients():
    docs = db.collection("clients").get()
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        
        # Files ko bytes me convert karna UI/download ke liye
        doc_bytes = base64.b64decode(d.get("doc_data")) if d.get("doc_data") else None
        photo_bytes = base64.b64decode(d.get("photo_data")) if d.get("photo_data") else None
        
        data_list.append({
            'Client ID': d.get('client_id', ''),
            'Client Name': d.get('client_name', ''),
            'Email': d.get('email', ''),
            'Project Name': d.get('project_name', ''),
            'Status': d.get('status', ''),
            'Company Information': d.get('company_info', ''),
            'Contacts': d.get('contacts', ''),
            'GST Details': d.get('gst_details', ''),
            'Billing Address': d.get('billing_address', ''),
            'Agreements': d.get('agreements', ''),
            'Start Date': d.get('start_date', ''),
            'End Date': d.get('end_date', ''),
            'Team Lead': d.get('team_lead', ''),
            'Team Members': d.get('team_members', ''),
            'doc_data': doc_bytes,
            'doc_name': d.get('doc_name', ''),
            'Extension Reason': d.get('extension_reason', '-'),
            'photo_data': photo_bytes,
            'Total Revenue': d.get('total_revenue', 0.0)
        })
        
    return pd.DataFrame(data_list)

# Function to securely save a newly added client into the database
def save_new_client(c_id, c_name, email, p_name, status, c_info, contacts, gst, bill_addr, agree, s_date_cli, e_date_cli, t_lead, t_members, file_data, file_name, photo, p_category, p_rev, s_date_proj, e_date_proj):
    
    # Check if the email ID is already registered (Prevents Duplicate Emails)
    if db.collection("clients").where("email", "==", email).get():
        return "duplicate_email"
        
    client_ref = db.collection("clients").document(c_id)
    if client_ref.get().exists:
        return "duplicate_id"
        
    # File aur Photo ko Base64 me encode karna
    doc_b64 = base64.b64encode(file_data).decode('utf-8') if file_data else ""
    photo_b64 = base64.b64encode(photo).decode('utf-8') if photo else ""
        
    # 1. Save all details to clients collection
    client_ref.set({
        "client_id": c_id, "client_name": c_name, "email": email, "project_name": p_name,
        "status": status, "company_info": c_info, "contacts": contacts, "gst_details": gst,
        "billing_address": bill_addr, "agreements": agree, "start_date": s_date_cli,
        "end_date": e_date_cli, "team_lead": t_lead, "team_members": t_members,
        "doc_data": doc_b64, "doc_name": file_name, "extension_reason": "-",
        "photo_data": photo_b64, "total_revenue": float(p_rev)
    })
    
    # 2. Automatically copy project data into projects collection (Cross-DB Sync)
    try:
        # Generating unique ID for the project table
        p_id = f"PRJ-{int(time.time() * 1000)}"
        progress = "10%" if status == "Active" else "0%"
        tools_used = "TBD" 
        
        db.collection("projects").document(p_id).set({
            "project_id": p_id, "project_name": p_name, "project_category": p_category,
            "description": c_info, "client_name": c_name, "revenue": float(p_rev),
            "paid": 0.0, "unpaid": float(p_rev), "tools": tools_used,
            "assigned_employee": t_members, "start_date": s_date_proj, "end_date": e_date_proj,
            "progress": progress, "status": status, "doc_data": doc_b64, "doc_name": file_name,
            "team_lead": t_lead
        })
    except Exception as e:
        print(f"Project DB Sync Error: {e}")
        
    return "success"

# ==========================================
# SAFE MEMORY LOGIC (Prevents Data Loss on Preview)
# ==========================================

# This function locks the data into memory before switching to Preview Mode
def cli_go_preview():
    p = st.session_state
    
    # Get values from input fields
    c_name = p.get("cli_name_in", "")
    email = p.get("cli_email_in", "").strip() # Strip spaces
    p_name = p.get("cli_p_name_in", "")
    c_contact_num = p.get("cli_contact_in", "")
    isd_code = p.get("cli_isd_in", "🇮🇳 India (+91)")
    
    # 1. Check if all required fields are filled
    if c_name and email and p_name and c_contact_num:
        
        # 2. Strict Validation: Sirf alphabets allowed for Client Name
        if not c_name.replace(" ", "").isalpha():
            p.cli_error = "⚠️ Client Name should only contain alphabets (No numbers allowed)."
        # 3. Strict Validation: Sirf alphabets allowed for Project Name
        elif not p_name.replace(" ", "").isalpha():
            p.cli_error = "⚠️ Project Name should only contain alphabets (No numbers allowed)."
        # 4. Check if the email address is in the correct format
        elif not is_valid_email(email):
            p.cli_error = "⚠️ Invalid Email Format! Please enter a valid email ID."
        else:
            # 5. Smart Country-specific Contact Validation
            contact_clean = c_contact_num.replace(" ", "").replace("-", "")
            is_valid_contact = False
            
            if "India (+91)" in isd_code:
                if contact_clean.isdigit() and len(contact_clean) == 10 and int(contact_clean[0]) > 6:
                    is_valid_contact = True
                else:
                    p.cli_error = "⚠️ Indian contact number must be exactly 10 digits and start with 7, 8, or 9."
            else:
                if contact_clean.isdigit() and 7 <= len(contact_clean) <= 15:
                    is_valid_contact = True
                else:
                    p.cli_error = "⚠️ Contact number must contain only digits and be valid length for selected country."
            
            if is_valid_contact:
                start_date = p.get("cli_s_date_in", datetime.date.today())
                end_date = p.get("cli_e_date_in", datetime.date.today())
                
                # 6. Check if end date is logically correct
                if end_date < start_date:
                    p.cli_error = "⚠️ End Date cannot be before Start Date!"
                else:
                    p.cli_step = "preview"
                    p.cli_error = ""
                    
                    # Format the contact info
                    full_contact = f"{isd_code} {c_contact_num}"
                    
                    # Get members from multiselect safely
                    t_members_list = p.get("cli_t_members_in", [])
                    t_members_str = ", ".join(t_members_list) if t_members_list else "None Assigned"
                    
                    # Save to Safe Memory Dictionary
                    p.safe_cli_data = {
                        'c_name': c_name,
                        'email': email,
                        'p_name': p_name,
                        'contact': full_contact,
                        'gst': p.get("cli_gst_in", ""),
                        'agree': p.get("cli_agree_in", ""),
                        'info': p.get("cli_info_in", ""),
                        'bill_addr': p.get("cli_bill_addr_in", ""),
                        'p_category': p.get("cli_p_category_in", "Custom Software"),
                        's_date': start_date,
                        'e_date': end_date,
                        't_lead': p.get("cli_t_lead_in", "Prajatak Sir"),
                        'p_status': p.get("cli_p_status_in", "Active"),
                        'p_rev': p.get("cli_p_rev_in", 0.0),
                        't_members': t_members_str
                    }
                    
                    # Safely store the uploaded photo
                    if p.get("cli_photo_in") is not None:
                        p.cli_photo_data = p.cli_photo_in.getvalue()
                        
                    # Safely store the uploaded document
                    if p.get("cli_doc_in") is not None:
                        p.cli_doc_data = p.cli_doc_in.getvalue()
                        p.cli_doc_name = p.cli_doc_in.name
    else:
        p.cli_error = "⚠️ Please fill all mandatory fields (*)."


# This function switches back to the form so the user can edit
def cli_go_edit():
    st.session_state.cli_step = "form"
    
    # NAYA LOGIC: Forcefully restore all saved data directly into Streamlit's UI keys
    draft = st.session_state.get("safe_cli_data", {})
    if draft:
        st.session_state["cli_name_in"] = draft.get('c_name', '')
        st.session_state["cli_email_in"] = draft.get('email', '')
        st.session_state["cli_contact_in"] = draft.get('contact_num', '')
        st.session_state["cli_isd_in"] = draft.get('isd', '🇮🇳 India (+91)')
        st.session_state["cli_gst_in"] = draft.get('gst', '')
        st.session_state["cli_agree_in"] = draft.get('agree', '')
        st.session_state["cli_info_in"] = draft.get('info', '')
        st.session_state["cli_bill_addr_in"] = draft.get('bill_addr', '')
        st.session_state["cli_p_name_in"] = draft.get('p_name', '')
        st.session_state["cli_p_category_in"] = draft.get('p_category', 'Web App')
        st.session_state["cli_s_date_in"] = draft.get('s_date', datetime.date.today())
        st.session_state["cli_e_date_in"] = draft.get('e_date', datetime.date.today())
        st.session_state["cli_t_lead_in"] = draft.get('t_lead', 'Prajatak Sir')
        st.session_state["cli_p_status_in"] = draft.get('p_status', 'Active')
        st.session_state["cli_p_rev_in"] = float(draft.get('p_rev', 0.0))
        st.session_state["cli_t_members_in"] = draft.get('t_members_list', [])

# This function prepares a completely fresh popup when adding a new client
def prepare_new_client():
    st.session_state.cli_step = "form"
    st.session_state.cli_error = ""
    st.session_state.cli_photo_data = None
    st.session_state.cli_doc_data = None
    st.session_state.cli_doc_name = None
    st.session_state.safe_cli_data = {} 
    
    # 100% Clean reset to prevent duplicate save errors
    keys_to_clear = [
        "cli_name_in", "cli_email_in", "cli_contact_in", "cli_gst_in", "cli_agree_in", 
        "cli_info_in", "cli_bill_addr_in", "cli_p_name_in", "cli_p_category_in", 
        "cli_t_members_in", "cli_isd_in", "cli_t_lead_in", "cli_p_status_in", 
        "cli_p_rev_in", "cli_s_date_in", "cli_e_date_in", "cli_photo_in", "cli_doc_in"
    ]
    for k in keys_to_clear:
        if k in st.session_state: del st.session_state[k]

# ==========================================
# UI DIALOGS & POP-UPS
# ==========================================

# Dialog 1: Show full client profile details
@st.dialog("Client Full Details", width="large")
def show_client_popup(client):
    
    # Setup the display for Client Photo
    img_src = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    photo_val = client.get('photo_data')
    if photo_val is not None and isinstance(photo_val, (bytes, bytearray)) and len(photo_val) > 0:
        b64_img = base64.b64encode(photo_val).decode('utf-8')
        img_src = f"data:image/png;base64,{b64_img}"

    # Photo and Client Name Heading
    st.markdown(f"""
    <div style='text-align: center;'>
        <img src='{img_src}' width='120' height='120' style='margin-bottom: 10px; border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'>
        <h3 style='margin: 0px; color: #ffffff;'>{client['Client Name']}</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(f"**Project Name:** {client['Project Name']}")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown(f"**Start Date:**<br>{client['Start Date']}", unsafe_allow_html=True)
    with col_d2:
        st.markdown(f"**End Date:**<br>{client['End Date']}", unsafe_allow_html=True)
        
    st.markdown("---")
    # Added Email display below Company Name
    st.markdown(f"**Email ID:**<br>{client.get('Email', '-')}", unsafe_allow_html=True)
    st.markdown(f"**Contacts:**<br>{client['Contacts']}", unsafe_allow_html=True)
    st.markdown(f"**Company Information:**<br>{client['Company Information']}", unsafe_allow_html=True)
    st.markdown(f"**GST Details:**<br>{client['GST Details']}", unsafe_allow_html=True)
    st.markdown(f"**Billing Address:**<br>{client['Billing Address']}", unsafe_allow_html=True)
    st.markdown(f"**Agreements:**<br>{client['Agreements']}", unsafe_allow_html=True)
    
    # Only show the extension reason if the project has been delayed
    if client['Extension Reason'] and client['Extension Reason'] != "-":
        st.markdown(f"**Delay / Extension Reason:**<br><span style='color:#ff4b4b;'>{client['Extension Reason']}</span>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Show document download button if a document was uploaded
    if client['doc_name']:
        st.markdown(f"**Uploaded Document:** {client['doc_name']}")
        st.download_button(label=" Download File", data=client['doc_data'], file_name=client['doc_name'], mime="application/pdf", use_container_width=True)
    else:
        st.info("No documentation uploaded for this client.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Feature to extend the project deadline
    with st.expander(" Extend Project Deadline"):
        st.markdown("<p style='font-size:14px; color:#a1a1aa;'>Update deadline if project is delayed. Reason is mandatory.</p>", unsafe_allow_html=True)
        try:
            curr_date = datetime.datetime.strptime(client['End Date'], "%d-%b-%Y").date()
        except Exception:
            curr_date = datetime.date.today()
            
        new_date = st.date_input("Select New Deadline Date", value=curr_date, key=f"date_{client['Client ID']}")
        reason = st.text_area("Reason for Extension *", placeholder="e.g., Client delayed sending raw materials...", key=f"reason_{client['Client ID']}")
        
        if st.button("Update Deadline", type="primary", use_container_width=True, key=f"btn_{client['Client ID']}"):
            if not reason.strip():
                st.error("⚠️ Reason for extension is mandatory!")
            else:
                new_date_str = new_date.strftime("%d-%b-%Y")
                update_client_deadline(client['Client ID'], new_date_str, reason)
                st.success("Deadline extended successfully!")
                time.sleep(1)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Danger Zone: Deleting the client record completely
    with st.expander(" Remove Client (Danger Zone)"):
        st.error("⚠️ Warning: This will permanently delete the client from the database.")
        
        # 1. CSS trick to make the Client Name unselectable (Cannot be highlighted/copied)
        st.markdown(
            f"To confirm, type <span style='user-select: none; -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; pointer-events: none; font-weight: bold; color: #ffffff;'>{client['Client Name']}</span> below:", 
            unsafe_allow_html=True
        )
        
        confirm_input = st.text_input("Type here to confirm:", key=f"del_inp_{client['Client ID']}")
        
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

        if st.button("Permanently Delete", type="primary", use_container_width=True):
            if confirm_input.strip().lower() == client['Client Name'].strip().lower():
                delete_client(client['Client ID'])
                st.success(f"Client {client['Client Name']} has been removed!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.warning("⚠️ Action Cancelled: Please type the client name exactly to delete.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Close Details", use_container_width=True):
        st.rerun()

# Dialog 2: The Add Client Wizard (Form + Preview Mode)
@st.dialog("➕ Add New Client & Project", width="large")
def add_client_dialog():
    
    if "cli_step" not in st.session_state:
        st.session_state.cli_step = "form"
    
    draft = st.session_state.get("safe_cli_data", {})

    # ------------- STEP 1: FORM UI -------------
    if st.session_state.cli_step == "form":
        st.markdown("<p style='color: #a1a1aa;'>Fill out the details below to add a new client to the database.</p>", unsafe_allow_html=True)
        
        st.markdown("#### Client Information")
        st.text_input("Client Name (Company) *", placeholder="e.g. TechCorp Global", value=draft.get('c_name', ''), key="cli_name_in")
        
        # Email input added seamlessly here
        st.text_input("Email ID *", placeholder="client@company.com", value=draft.get('email', ''), key="cli_email_in")
        
        # Phone numbers list setup
        ISD_CODES = [
            "🇦🇫 Afghanistan (+93)", "🇦🇱 Albania (+355)", "🇩🇿 Algeria (+213)", "🇦🇸 American Samoa (+1-684)", 
            "🇦🇩 Andorra (+376)", "🇦🇴 Angola (+244)", "🇦🇮 Anguilla (+1-264)", "🇦🇬 Antigua & Barbuda (+1-268)", 
            "🇦🇷 Argentina (+54)", "🇦🇲 Armenia (+374)", "🇦🇼 Aruba (+297)", "🇦🇺 Australia (+61)", "🇦🇹 Austria (+43)", 
            "🇦🇿 Azerbaijan (+994)", "🇧🇸 Bahamas (+1-242)", "🇧🇭 Bahrain (+973)", "🇧🇩 Bangladesh (+880)", 
            "🇧🇧 Barbados (+1-246)", "🇧🇾 Belarus (+375)", "🇧🇪 Belgium (+32)", "🇧🇿 Belize (+501)", "🇧🇯 Benin (+229)", 
            "🇧🇲 Bermuda (+1-441)", "🇧🇹 Bhutan (+975)", "🇧🇴 Bolivia (+591)", "🇧🇦 Bosnia & Herzegovina (+387)", 
            "🇧🇼 Botswana (+267)", "🇧🇷 Brazil (+55)", "🇮🇴 British Indian Ocean Territory (+246)", 
            "🇻🇬 British Virgin Islands (+1-284)", "🇧🇳 Brunei (+673)", "🇧🇬 Bulgaria (+359)", "🇧🇫 Burkina Faso (+226)", 
            "🇧🇮 Burundi (+257)", "🇰🇭 Cambodia (+855)", "🇨🇲 Cameroon (+237)", "🇨🇦 Canada (+1)", "🇨🇻 Cape Verde (+238)", 
            "🇰🇾 Cayman Islands (+1-345)", "🇨🇫 Central African Republic (+236)", "🇹🇩 Chad (+235)", "🇨🇱 Chile (+56)", 
            "🇨🇳 China (+86)", "🇨🇴 Colombia (+57)", "🇰🇲 Comoros (+269)", "🇨🇬 Congo (+242)", "🇨🇩 DR Congo (+243)", 
            "🇨🇰 Cook Islands (+682)", "🇨🇷 Costa Rica (+506)", "🇨🇮 Cote d'Ivoire (+225)", "🇭🇷 Croatia (+385)", 
            "🇨🇺 Cuba (+53)", "🇨🇾 Cyprus (+357)", "🇨🇿 Czech Republic (+420)", "🇩🇰 Denmark (+45)", "🇩🇯 Djibouti (+253)", 
            "🇩🇲 Dominica (+1-767)", "🇩🇴 Dominican Republic (+1-809)", "🇪🇨 Ecuador (+593)", "🇪🇬 Egypt (+20)", 
            "🇸🇻 El Salvador (+503)", "🇬🇶 Equatorial Guinea (+240)", "🇪🇷 Eritrea (+291)", "🇪🇪 Estonia (+372)", 
            "🇪🇹 Ethiopia (+251)", "🇫🇰 Falkland Islands (+500)", "🇫🇴 Faroe Islands (+298)", "🇫🇯 Fiji (+679)", 
            "🇫🇮 Finland (+358)", "🇫🇷 France (+33)", "🇬🇫 French Guiana (+594)", "🇵🇫 French Polynesia (+689)", 
            "🇬🇦 Gabon (+241)", "🇬🇲 Gambia (+220)", "🇬🇪 Georgia (+995)", "🇩🇪 Germany (+49)", "🇬🇭 Ghana (+233)", 
            "🇬🇮 Gibraltar (+350)", "🇬🇷 Greece (+30)", "🇬🇱 Greenland (+299)", "🇬🇩 Grenada (+1-473)", 
            "🇬🇵 Guadeloupe (+590)", "🇬🇺 Guam (+1-671)", "🇬🇹 Guatemala (+502)", "🇬🇳 Guinea (+224)", 
            "🇬🇼 Guinea-Bissau (+245)", "🇬🇾 Guyana (+592)", "🇭🇹 Haiti (+509)", "🇭🇳 Honduras (+504)", 
            "🇭🇰 Hong Kong (+852)", "🇭🇺 Hungary (+36)", "🇮🇸 Iceland (+354)", "🇮🇳 India (+91)", "🇮🇩 Indonesia (+62)", 
            "🇮🇷 Iran (+98)", "🇮🇶 Iraq (+964)", "🇮🇪 Ireland (+353)", "🇮🇱 Israel (+972)", "🇮🇹 Italy (+39)", 
            "🇯🇲 Jamaica (+1-876)", "🇯🇵 Japan (+81)", "🇯🇴 Jordan (+962)", "🇰🇿 Kazakhstan (+7)", "🇰🇪 Kenya (+254)", 
            "🇰🇮 Kiribati (+686)", "🇰🇼 Kuwait (+965)", "🇰🇬 Kyrgyzstan (+996)", "🇱🇦 Laos (+856)", "🇱🇻 Latvia (+371)", 
            "🇱🇧 Lebanon (+961)", "🇱🇸 Lesotho (+266)", "🇱🇷 Liberia (+231)", "🇱🇾 Libya (+218)", "🇱🇮 Liechtenstein (+423)", 
            "🇱🇹 Lithuania (+370)", "🇱🇺 Luxembourg (+352)", "🇲🇴 Macau (+853)", "🇲🇬 Madagascar (+261)", 
            "🇲🇼 Malawi (+265)", "🇲🇾 Malaysia (+60)", "🇲🇻 Maldives (+960)", "🇲🇱 Mali (+223)", "🇲🇹 Malta (+356)", 
            "🇲🇭 Marshall Islands (+692)", "🇲🇶 Martinique (+596)", "🇲🇷 Mauritania (+222)", "🇲🇺 Mauritius (+230)", 
            "🇾🇹 Mayotte (+262)", "🇲🇽 Mexico (+52)", "🇫🇲 Micronesia (+691)", "🇲🇩 Moldova (+373)", "🇲🇨 Monaco (+377)", 
            "🇲🇳 Mongolia (+976)", "🇲🇪 Montenegro (+382)", "🇲🇸 Montserrat (+1-664)", "🇲🇦 Morocco (+212)", 
            "🇲🇿 Mozambique (+258)", "🇲🇲 Myanmar (+95)", "🇳🇦 Namibia (+264)", "🇳🇷 Nauru (+674)", "🇳🇵 Nepal (+977)", 
            "🇳🇱 Netherlands (+31)", "🇳🇨 New Caledonia (+687)", "🇳🇿 New Zealand (+64)", "🇳🇮 Nicaragua (+505)", 
            "🇳🇪 Niger (+227)", "🇳🇬 Nigeria (+234)", "🇳🇺 Niue (+683)", "🇳🇫 Norfolk Island (+672)", "🇰🇵 North Korea (+850)", 
            "🇲🇵 Northern Mariana Islands (+1-670)", "🇳🇴 Norway (+47)", "🇴🇲 Oman (+968)", "🇵🇰 Pakistan (+92)", 
            "🇵🇼 Palau (+680)", "🇵🇸 Palestine (+970)", "🇵🇦 Panama (+507)", "🇵🇬 Papua New Guinea (+675)", 
            "🇵🇾 Paraguay (+595)", "🇵🇪 Peru (+51)", "🇵🇭 Philippines (+63)", "🇵🇱 Poland (+48)", "🇵🇹 Portugal (+351)", 
            "🇵🇷 Puerto Rico (+1-787)", "🇶🇦 Qatar (+974)", "🇷🇴 Romania (+40)", "🇷🇺 Russia (+7)", "🇷🇼 Rwanda (+250)", 
            "🇷🇪 Reunion (+262)", "🇼🇸 Samoa (+685)", "🇸🇲 San Marino (+378)", "🇸🇹 Sao Tome & Principe (+239)", 
            "🇸🇦 Saudi Arabia (+966)", "🇸🇳 Senegal (+221)", "🇷🇸 Serbia (+381)", "🇸🇨 Seychelles (+248)", 
            "🇸🇱 Sierra Leone (+232)", "🇸🇬 Singapore (+65)", "🇸🇰 Slovakia (+421)", "🇸🇮 Slovenia (+386)", 
            "🇸🇧 Solomon Islands (+677)", "🇸🇴 Somalia (+252)", "🇿🇦 South Africa (+27)", "🇰🇷 South Korea (+82)", 
            "🇪🇸 Spain (+34)", "🇱🇰 Sri Lanka (+94)", "🇸🇩 Sudan (+249)", "🇸🇷 Suriname (+597)", "🇸🇿 Eswatini (+268)", 
            "🇸🇪 Sweden (+46)", "🇨🇭 Switzerland (+41)", "🇸🇾 Syria (+963)", "🇹🇼 Taiwan (+886)", "🇹🇯 Tajikistan (+992)", 
            "🇹🇿 Tanzania (+255)", "🇹🇭 Thailand (+66)", "🇹🇬 Togo (+228)", "🇹🇰 Tokelau (+690)", "🇹🇴 Tonga (+676)", 
            "🇹🇹 Trinidad & Tobago (+1-868)", "🇹🇳 Tunisia (+216)", "🇹🇷 Turkey (+90)", "🇹🇲 Turkmenistan (+993)", 
            "🇹🇨 Turks & Caicos Islands (+1-649)", "🇹🇻 Tuvalu (+688)", "🇺🇬 Uganda (+256)", "🇺🇦 Ukraine (+380)", 
            "🇦🇪 United Arab Emirates (+971)", "🇬🇧 United Kingdom (+44)", "🇺🇸 United States (+1)", "🇺🇾 Uruguay (+598)", 
            "🇺🇿 Uzbekistan (+998)", "🇻🇺 Vanuatu (+678)", "🇻🇪 Venezuela (+58)", "🇻🇳 Vietnam (+84)", 
            "🇻🇮 US Virgin Islands (+1-340)", "🇼🇫 Wallis & Futuna (+681)", "🇾🇪 Yemen (+967)", "🇿🇲 Zambia (+260)", 
            "🇿🇼 Zimbabwe (+263)"
        ]
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            try:
                isd_idx = ISD_CODES.index(draft.get('isd', "🇮🇳 India (+91)"))
            except ValueError:
                isd_idx = 0
            st.selectbox("Country & ISD Code", ISD_CODES, index=isd_idx, key="cli_isd_in")
        with col_c2:
            st.text_input("Phone Number *", placeholder="9876543210", value=draft.get('contact_num', ''), key="cli_contact_in")
            
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.text_input("GST Details", placeholder="27XXXXXXXXXXXXX", value=draft.get('gst', ''), key="cli_gst_in")
            st.text_input("Agreements", placeholder="e.g. NDA Signed, Contract Pending", value=draft.get('agree', ''), key="cli_agree_in")
        with col_g2:
            st.text_area("Company Information", placeholder="Brief description...", value=draft.get('info', ''), key="cli_info_in")
            st.text_area("Billing Address", placeholder="Full physical address...", value=draft.get('bill_addr', ''), key="cli_bill_addr_in")

        # Photo Upload Option for Clients
        st.file_uploader("Upload Client Photo (Optional)", type=['jpg', 'jpeg', 'png'], key="cli_photo_in")

        st.markdown("#### Project & Team Details")
        col3, col4 = st.columns(2)
        with col3:
            st.text_input("Project Name *", value=draft.get('p_name', ''), key="cli_p_name_in")
            
            p_cat_opts = ["Mobile App", "Web App", "Custom Software", "System Integration", "CRM", "Digital Marketing", "Domain and Hosting"]
            p_cat_idx = p_cat_opts.index(draft.get('p_category', "Web App")) if draft.get('p_category') in p_cat_opts else 0
            st.selectbox("Project Category *", p_cat_opts, index=p_cat_idx, key="cli_p_category_in")
            
            st.date_input("Start Date", value=draft.get('s_date', datetime.date.today()), key="cli_s_date_in")
            
            t_lead_opts = ["Prajatak Sir", "Vikrant Sir", "Shahid Sir", "Arya Sir"]
            t_lead_idx = t_lead_opts.index(draft.get('t_lead', "Prajatak Sir")) if draft.get('t_lead') in t_lead_opts else 0
            st.selectbox("Team Lead *", t_lead_opts, index=t_lead_idx, key="cli_t_lead_in")
            
        with col4:
            p_status_opts = ["Active", "Onboard"]
            p_stat_idx = p_status_opts.index(draft.get('p_status', "Active")) if draft.get('p_status') in p_status_opts else 0
            st.selectbox("Project Status *", p_status_opts, index=p_stat_idx, key="cli_p_status_in")
            
            st.number_input("Total Revenue (₹)", min_value=0.0, step=100.0, value=float(draft.get('p_rev', 0.0)), key="cli_p_rev_in")
            
            st.date_input("End Date", value=draft.get('e_date', datetime.date.today()), key="cli_e_date_in")
            
            intern_list = get_intern_names()
            st.multiselect("Team Members (Select Interns)", intern_list, default=draft.get('t_members_list', []), key="cli_t_members_in")
            
        st.markdown("#### Upload Documentation")
        st.file_uploader("Upload PDF Document (Optional)", type=['pdf'], key="cli_doc_in")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("cli_error"):
            st.error(st.session_state.cli_error)
            
        # Trigger the safe lock logic before switching to Preview
        st.button("👁️ Generate Preview", type="primary", use_container_width=True, on_click=cli_go_preview)

    # ------------- STEP 2: PREVIEW UI -------------
    elif st.session_state.cli_step == "preview":
        data = st.session_state.safe_cli_data
        
        st.markdown("<h3 style='color: #ffffff;'>👁️ Preview Client Details</h3>", unsafe_allow_html=True)
        
        # Display Photo if uploaded
        photo_bytes = st.session_state.get('cli_photo_data')
        if photo_bytes is not None:
            b64_p = base64.b64encode(photo_bytes).decode('utf-8')
            st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{b64_p}' width='100' height='100' style='border-radius: 50%; object-fit: cover; border: 2px solid #39FF14;'></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # Summary Display Box
        with st.container(border=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f"**Client Name:** {data['c_name']}")
                st.markdown(f"**Email ID:** {data['email']}")
                st.markdown(f"**Contact:** {data['contact']}")
                st.markdown(f"**GST:** {data['gst'] if data['gst'] else '-'}")
                st.markdown(f"**Project Name:** {data['p_name']}")
                st.markdown(f"**Category:** {data['p_category']}")
                st.markdown(f"**Start Date:** {data['s_date'].strftime('%d-%b-%Y')}")
                st.markdown(f"**Status:** {data['p_status']}")
            with col_p2:
                st.markdown(f"**Team Lead:** {data['t_lead']}")
                st.markdown(f"**Team Members:** {data['t_members']}")
                st.markdown(f"**End Date:** {data['e_date'].strftime('%d-%b-%Y')}")
                st.markdown(f"**Revenue:** ₹{data['p_rev']}")
                st.markdown(f"**Info:** {data['info'] if data['info'] else '-'}")
                st.markdown(f"**Agreements:** {data['agree'] if data['agree'] else '-'}")
                
        if st.session_state.get('cli_doc_name'):
            st.success(f"📎 Attached Document: {st.session_state.cli_doc_name}")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("cli_error"):
            st.error(st.session_state.cli_error)

        # Action Buttons
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.button("✏️ Edit Details", use_container_width=True, on_click=cli_go_edit)
        with col_b2:
            # Confirm and save to database
            if st.button("✅ Confirm & Save", type="primary", use_container_width=True):
                # Generate unique ID and formatted dates (Multiplying by 1000 ensures no duplicate IDs)
                c_id = f"CL-{int(time.time() * 1000)}"
                s_date_cli = data['s_date'].strftime("%d-%b-%Y")
                e_date_cli = data['e_date'].strftime("%d-%b-%Y")
                s_date_proj = data['s_date'].strftime("%Y-%m-%d")
                e_date_proj = data['e_date'].strftime("%Y-%m-%d")
                
                doc_bytes = st.session_state.get('cli_doc_data')
                doc_name = st.session_state.get('cli_doc_name')
                
                status = save_new_client(
                    c_id, data['c_name'], data['email'], data['p_name'], data['p_status'], data['info'], 
                    data['contact'], data['gst'], data['bill_addr'], data['agree'], 
                    s_date_cli, e_date_cli, data['t_lead'], data['t_members'], 
                    doc_bytes, doc_name, photo_bytes, data['p_category'], data['p_rev'], 
                    s_date_proj, e_date_proj
                )
                
                if status == "success":
                    st.success("Added Successfully!")
                    time.sleep(1)
                    st.rerun() 
                elif status == "duplicate_email":
                    st.session_state.cli_error = "⚠️ Email already exists!"
                    st.rerun()
                elif status == "duplicate_id":
                    st.session_state.cli_error = "⚠️ Database error: Duplicate ID or Network Issue."
                    st.rerun()

# Function to generate an HTML table for displaying the teams internally
def create_team_table(df):
    html_table = """
    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px;">
        <thead>
            <tr>
                <th style="padding: 12px;">Project Name</th>
                <th style="padding: 12px;">Status</th>
                <th style="padding: 12px;">Start Date</th>
                <th style="padding: 12px;">End Date</th>
                <th style="padding: 12px;">Team Lead</th>
                <th style="padding: 12px;">Team Members</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in df.iterrows():
        if row['Status'] == 'Completed':
            status_color = "#888888"
        elif row['Status'] == 'Onboard':
            status_color = "#ff9900"
        else:
            status_color = "#39FF14"
            
        html_table += "<tr>"
        html_table += f"<td style='padding: 12px;'><strong>{row['Project Name']}</strong></td>"
        html_table += f"<td style='padding: 12px; color: {status_color}; font-weight: bold;'>{row['Status']}</td>"
        html_table += f"<td style='padding: 12px;'>{row['Start Date']}</td>"
        html_table += f"<td style='padding: 12px;'>{row['End Date']}</td>"
        html_table += f"<td style='padding: 12px; color: #60a5fa; font-weight: bold;'>{row['Team Lead']}</td>"
        html_table += f"<td style='padding: 12px;'>{row['Team Members']}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table>"
    return html_table

# ==========================================
# MAIN PAGE RENDER
# ==========================================
def show_client_page():
    load_global_css() 
    
    # 🟢 100% BULLETPROOF CSS FIX: Force text inside tertiary buttons to strictly left-align (Global impact on page load)
    st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="tertiary"] {
        color: #60a5fa !important; 
        padding: 0px !important;
        font-weight: bold !important;
        background-color: transparent !important;
        justify-content: flex-start !important;
        text-align: left !important;
        display: flex !important;
    }
    div[data-testid="stButton"] button[kind="tertiary"] div {
        justify-content: flex-start !important;
        text-align: left !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] button[kind="tertiary"] p {
        text-align: left !important;
        width: 100% !important;
        margin: 0 !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stButton"] button[kind="tertiary"]:hover {
        color: #39FF14 !important; 
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize the database automatically if the page is loading for the first time
    if "client_db_initialized" not in st.session_state:
        init_client_db()
        st.session_state.client_db_initialized = True
        
    auto_update_client_status()

    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>🤝 Client Management</h1>", unsafe_allow_html=True)
    with head_col2:
        if st.button("➕ Add Client", type="primary", use_container_width=True):
            prepare_new_client() # Prepares a completely fresh memory setup
            add_client_dialog()  # Opens the popup
            
    st.markdown("---")

    client_tab = st.radio("Navigation Menu:", [
        "Client Overview", 
        "Client Timeline"
    ], horizontal=True, label_visibility="collapsed", key="client_main_tab")

    st.markdown("<br>", unsafe_allow_html=True)

    df_clients = get_all_clients()

    if client_tab == "Client Overview":
        st.markdown("<h3 style='color: #ffffff;'>Client Overview</h3>", unsafe_allow_html=True)
        
        df_info = df_clients.copy()

        # Custom message when no LIVE data is present in the database
        if len(df_info) == 0:
            st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
        else:
            st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            
            # Removed the "Pic" Column, updated to exactly 6 columns: Client Name, Project Name, Start Date, Submission Date, Total Revenue, Status
            col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1.5, 1, 1, 1, 1], vertical_alignment="center")
            with col1: st.markdown("<p style='margin: 5px 0px; font-weight: bold;'>Client Name</p>", unsafe_allow_html=True)
            with col2: st.markdown("<p style='margin: 5px 0px; font-weight: bold;'>Project Name</p>", unsafe_allow_html=True)
            with col3: st.markdown("<p style='margin: 5px 0px; font-weight: bold;'>Start Date</p>", unsafe_allow_html=True)
            with col4: st.markdown("<p style='margin: 5px 0px; font-weight: bold;'>Submission Date</p>", unsafe_allow_html=True)
            with col5: st.markdown("<p style='margin: 5px 0px; font-weight: bold;'>Total Revenue</p>", unsafe_allow_html=True)
            with col6: st.markdown("<p style='margin: 5px 0px; font-weight: bold;'>Status</p>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 0px; border-top: 2px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            
            # Loop through the data to render rows without "Pic" column
            for idx, row in df_info.iterrows():
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1, 1, 1, 1], vertical_alignment="center")
                
                with c1:
                    if st.button(f"{row['Client Name']}", key=f"cli_{row['Client ID']}_{idx}", use_container_width=True, type="tertiary"):
                        show_client_popup(row)
                with c2: 
                    st.write(row['Project Name'])
                with c3:
                    st.write(row['Start Date'])
                with c4:
                    st.write(row['End Date'])
                with c5:
                    rev_val = row.get('Total Revenue', 0.0)
                    st.write(f"₹{rev_val}" if pd.notnull(rev_val) else "₹0.0")
                with c6: 
                    status_color = "#39FF14" if row['Status'] == 'Active' else "#ff9900" if row['Status'] == 'Onboard' else "#888888"
                    st.markdown(f"<span style='color:{status_color}; font-weight:bold;'>{row['Status']}</span>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    elif client_tab == "Client Timeline":
        st.markdown("<h3 style='color: #ffffff;'>Filter Projects by Date</h3>", unsafe_allow_html=True)
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            filter_start = st.date_input("Select Start Date", datetime.date(2025, 11, 1))
        with col_date2:
            filter_end = st.date_input("Select End Date", datetime.date(2026, 12, 31))

        df_team = df_clients.copy()
        
        # Check if database is completely empty before filtering timeline
        if len(df_team) == 0:
            st.markdown("<br><h4 style='text-align:center; color:#ff4b4b; padding:20px; border: 1px dashed #ff4b4b; border-radius: 8px;'>NO DATA IS BEEN ENTERED</h4>", unsafe_allow_html=True)
        else:
            df_team['Start_DT'] = pd.to_datetime(df_team['Start Date'], format="%d-%b-%Y", errors='coerce').dt.date
            df_team['End_DT'] = pd.to_datetime(df_team['End Date'], format="%d-%b-%Y", errors='coerce').dt.date
            
            mask = (df_team['Start_DT'] <= filter_end) & (df_team['End_DT'] >= filter_start)
            filtered_df = df_team[mask].copy()
            
            comp_count = len(filtered_df[filtered_df['Status'] == 'Completed'])
            act_count = len(filtered_df[filtered_df['Status'] == 'Active'])
            onb_count = len(filtered_df[filtered_df['Status'] == 'Onboard'])
            
            if "status_filter" not in st.session_state:
                st.session_state.status_filter = "All"
                
            status_filter = st.session_state.status_filter

            act_bg = "rgba(52, 152, 219, 0.2)" if status_filter == "Active" else "rgba(255,255,255,0.05)"
            onb_bg = "rgba(255, 153, 0, 0.2)" if status_filter == "Onboard" else "rgba(255,255,255,0.05)"
            comp_bg = "rgba(136, 136, 136, 0.2)" if status_filter == "Completed" else "rgba(255,255,255,0.05)"

            css = f"""
            <style>
            div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="secondary"] {{
                border-left: 6px solid #3498db !important; background-color: {act_bg} !important; height: 85px !important; border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.1) !important;
            }}
            div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="secondary"] p {{ font-size: 20px !important; font-weight: bold !important; color: #3498db !important; }}
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) button[kind="secondary"] {{
                border-left: 6px solid #ff9900 !important; background-color: {onb_bg} !important; height: 85px !important; border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.1) !important;
            }}
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) button[kind="secondary"] p {{ font-size: 20px !important; font-weight: bold !important; color: #ff9900 !important; }}
            div[data-testid="stHorizontalBlock"] > div:nth-child(3) button[kind="secondary"] {{
                border-left: 6px solid #888888 !important; background-color: {comp_bg} !important; height: 85px !important; border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.1) !important;
            }}
            div[data-testid="stHorizontalBlock"] > div:nth-child(3) button[kind="secondary"] p {{ font-size: 20px !important; font-weight: bold !important; color: #888888 !important; }}
            </style>
            """
            st.markdown(css, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"Active Projects: {act_count}", use_container_width=True):
                    st.session_state.status_filter = "Active" if status_filter != "Active" else "All"
                    st.rerun()
            with col2:
                if st.button(f"Onboard Projects: {onb_count}", use_container_width=True):
                    st.session_state.status_filter = "Onboard" if status_filter != "Onboard" else "All"
                    st.rerun()
            with col3:
                if st.button(f"Completed Projects: {comp_count}", use_container_width=True):
                    st.session_state.status_filter = "Completed" if status_filter != "Completed" else "All"
                    st.rerun()

            st.markdown("<h4 style='color: #ffffff; margin-top: 25px; margin-bottom: 10px;'>Client Projects</h4>", unsafe_allow_html=True)
            
            if status_filter != "All":
                bars_df = filtered_df[filtered_df['Status'] == status_filter]
            else:
                bars_df = filtered_df
            
            active_colors = ["rgba(52, 152, 219, 0.8)", "rgba(46, 204, 113, 0.8)", "rgba(155, 89, 182, 0.8)", "rgba(232, 67, 147, 0.8)", "rgba(0, 206, 201, 0.8)"]
            onboard_colors = ["rgba(255, 153, 0, 0.8)", "rgba(230, 126, 34, 0.8)", "rgba(211, 84, 0, 0.8)", "rgba(243, 156, 18, 0.8)"]
            
            act_idx, onb_idx = 0, 0
            bars_html = '<div style="margin-bottom: 30px;">'
            if len(bars_df) == 0:
                bars_html += f'<p style="color: #a1a1aa; font-size: 16px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px;">No projects available in this date range.</p>'
            else:
                for _, row in bars_df.iterrows():
                    status = row['Status']
                    if status == 'Completed': bg_color = "rgba(136, 136, 136, 0.6)"
                    elif status == 'Active':
                        bg_color = active_colors[act_idx % len(active_colors)]
                        act_idx += 1
                    else:
                        bg_color = onboard_colors[onb_idx % len(onboard_colors)]
                        onb_idx += 1
                    
                    bars_html += f'<div style="background: {bg_color}; border: +1px solid rgba(255,255,255,0.1); color: #ffffff; padding: 14px 18px; margin-bottom: 12px; border-radius: 6px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3); display: flex; justify-content: space-between; align-items: center;">'
                    bars_html += f'<div style=\"font-size: 16px; font-weight: bold;\">{row["Project Name"]} <span style=\"font-size: 12px; font-weight: normal; background: rgba(0,0,0,0.4); padding: 3px 8px; border-radius: 4px; margin-left: 10px;\">{status}</span></div>'
                    bars_html += f'<div style=\"font-size: 15px; font-weight: 500; background: rgba(0,0,0,0.4); padding: 4px 10px; border-radius: 4px;\"> {row["Start Date"]} &nbsp;-&nbsp; {row["End Date"]}</div></div>'
            bars_html += "</div>"
            st.markdown(bars_html, unsafe_allow_html=True)
            
            st.markdown("<h3 style='color: #ffffff;'>Project Teams & Deadlines</h3>", unsafe_allow_html=True)
            st.markdown(create_team_table(filtered_df), unsafe_allow_html=True)