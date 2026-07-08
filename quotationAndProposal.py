# 1. Importing required libraries for the application
import streamlit as st
import sqlite3
import base64
import time

# ==========================================
# DATABASE SECTION (Handles Document Storage)
# ==========================================

# Function to create an EMPTY database and table for storing proposals
def init_db():
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # Creating a table with Proposal Name as the primary key
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            proposal_name TEXT PRIMARY KEY,
            file_data BLOB,
            file_name TEXT
        )
    ''')
    
    # NEW TABLE: For storing custom proposal names added by HR
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_proposals (
            proposal_name TEXT PRIMARY KEY
        )
    ''')
    
    # NOTE: No dummy data is added here. Ready for LIVE deployment.
    conn.commit()
    conn.close()

# Function to save a newly added custom proposal name
def save_custom_proposal(name):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO custom_proposals (proposal_name) VALUES (?)', (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # If name already exists
    finally:
        conn.close()

# Function to fetch all proposals (Default + Custom added by user)
def get_all_proposals():
    # Default list
    base_proposals = [
        "Real Estate", "FMCG", "Political", "Software", "AI Automation", 
        "Website", "Salons", "Cafes", "Resorts", "School and Colleges", 
        "MSEB", "Banks", "Hospitals and clinic", "Insurance"
    ]
    
    try:
        conn = sqlite3.connect("crm_main.db")
        cursor = conn.cursor()
        cursor.execute('SELECT proposal_name FROM custom_proposals')
        custom_props = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Add custom proposals to the base list without duplicates
        for cp in custom_props:
            if cp not in base_proposals:
                base_proposals.append(cp)
    except Exception:
        pass
        
    return base_proposals

# Function to securely save the uploaded PDF file into the database
def save_file_to_db(proposal_name, file_data, file_name):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    
    # INSERT OR REPLACE ensures that if we upload a new file for the same proposal, it overwrites the old one
    cursor.execute('''
        INSERT OR REPLACE INTO documents (proposal_name, file_data, file_name)
        VALUES (?, ?, ?)
    ''', (proposal_name, file_data, file_name))
    
    conn.commit()
    conn.close()

# Function to fetch the saved PDF file from the database to view or download
def get_file_from_db(proposal_name):
    conn = sqlite3.connect("crm_main.db")
    cursor = conn.cursor()
    cursor.execute('SELECT file_data, file_name FROM documents WHERE proposal_name = ?', (proposal_name,))
    row = cursor.fetchone() # Fetch only one matching record
    conn.close()
    return row

# ==========================================
# POPUP DIALOGS (Preview & View Documents)
# ==========================================

# 1. Dialog for adding a new Proposal Name
@st.dialog("➕ Add New Proposal Name", width="small")
def add_proposal_dialog():
    st.markdown("<p style='color: #a1a1aa;'>Enter the name of the new proposal category you want to add.</p>", unsafe_allow_html=True)
    new_prop = st.text_input("Proposal Name *", placeholder="e.g. Healthcare")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ Save Proposal", type="primary", use_container_width=True):
        if not new_prop.strip():
            st.error("⚠️ Please enter a valid proposal name.")
        else:
            success = save_custom_proposal(new_prop.strip())
            if success:
                st.success(f"'{new_prop}' added successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("⚠️ This proposal name already exists in the list.")

# 2. Dialog for Previewing and Confirming before saving
@st.dialog("👁️ Preview and Confirm Document", width="large")
def preview_and_confirm_dialog(proposal_name, file_data, file_name):
    st.markdown(f"<h3 style='color: #ffffff;'>Previewing: {proposal_name}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #a1a1aa;'>File Name: {file_name}</p>", unsafe_allow_html=True)
    
    # Convert the binary PDF data into a Base64 string to show in browser
    base64_pdf = base64.b64encode(file_data).decode('utf-8')
    
    # HTML code to embed and show the PDF inside the popup
    pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px" type="application/pdf">'
    st.markdown(pdf_display, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Action Buttons (Cancel or Save)
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        # Closes the dialog without saving
        if st.button("✏️ Cancel / Edit", use_container_width=True):
            st.rerun() 
            
    with col_b2:
        # Saves the document to the database
        if st.button("✅ Confirm & Save", type="primary", use_container_width=True):
            save_file_to_db(proposal_name, file_data, file_name)
            st.success(f"Document saved successfully for {proposal_name}!")
            time.sleep(1.5)
            st.rerun() # Refresh the page to update

# 3. Dialog to view already saved documents
@st.dialog("📂 View Document", width="large")
def view_pdf_dialog(proposal_name):
    # Get the file from the database
    row = get_file_from_db(proposal_name)
    
    if row:
        file_data, file_name = row
        
        # Convert the binary PDF data into a Base64 string so the browser can read it
        base64_pdf = base64.b64encode(file_data).decode('utf-8')
        
        # HTML code to embed and show the PDF inside the popup
        pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf">'
        
        # Display the file name and the PDF viewer
        st.markdown(f"<h4 style='color: #ffffff;'>{file_name}</h4>", unsafe_allow_html=True)
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Provide a button to download the PDF to the user's computer
        st.download_button(label="📥 Download File", data=file_data, file_name=file_name, mime="application/pdf", use_container_width=True)
    else:
        # Show an error if no document has been uploaded yet
        st.error("No document found in database for this proposal. Please upload and submit first.")

# ==========================================
# MAIN PAGE UI (Renders the Page)
# ==========================================
def show_proposal_page():
    
    # Initialize the database when the page loads
    init_db()

    # CSS to hide unnecessary Streamlit default styling for file uploaders
    st.markdown("""
    <style>
    div[data-testid="stFileUploader"] {
        padding: 0px;
    }
    div[data-testid="stFileUploader"] > div {
        padding: 0px;
        min-height: 40px;
    }
    div[data-testid="stFileUploader"] > div > div > div {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    # Main Page Heading (White for Dark Theme) and Add Proposal Button
    head_col1, head_col2 = st.columns([4, 1], vertical_alignment="center")
    with head_col1:
        st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>📄 Quotation & Proposal</h1>", unsafe_allow_html=True)
    with head_col2:
        if st.button("➕ Add Proposal", type="primary", use_container_width=True):
            add_proposal_dialog()
            
    st.markdown("---")

    # Fetch all proposals (Defaults + Customs)
    proposals = get_all_proposals()

    # Custom Table Header matching the Dark Theme (Translucent background, White text)
    st.markdown("""
    <div style="display: flex; font-weight: bold; font-size: 18px; background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); color: #ffffff;">
        <div style="flex: 2; color: #ffffff !important;">Proposal Name</div>
        <div style="flex: 2; color: #ffffff !important;">Upload Document</div>
        <div style="flex: 1; text-align: center; color: #ffffff !important;">Save Data</div>
        <div style="flex: 1; text-align: center; color: #ffffff !important;">View Document</div>
    </div>
    """, unsafe_allow_html=True)

    # Loop through the list of proposals and create a row for each one
    for idx, p in enumerate(proposals):
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1], vertical_alignment="center")
        
        # Column 1: Display the Proposal Name (White color)
        with col1:
            st.markdown(f"<p style='font-size: 16px; font-weight: 600; color: #ffffff; margin: 10px 0px 10px 15px;'>{p}</p>", unsafe_allow_html=True)
            
        # Column 2: File uploader box
        with col2:
            uploaded_file = st.file_uploader("Upload", type=['pdf'], key=f"up_{idx}", label_visibility="collapsed")
            
        # Column 3: Preview Button (Triggers the Preview Dialog before saving)
        with col3:
            if st.button("👁️ Preview", key=f"prev_{idx}", use_container_width=True):
                if uploaded_file is not None:
                    # Extract the binary data from the uploaded file
                    file_data = uploaded_file.getvalue()
                    # Open the preview and confirm dialog
                    preview_and_confirm_dialog(p, file_data, uploaded_file.name)
                else:
                    st.warning("Upload First!")
                    
        # Column 4: View Button to open the popup viewer for saved documents
        with col4:
            if st.button("📂 View", key=f"view_{idx}", use_container_width=True):
                # Call the dialog function to show the saved PDF
                view_pdf_dialog(p)
                    
        # A thin divider line between rows (Dark Theme compatible)
        st.markdown("<hr style='margin: 0px; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)