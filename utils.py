import streamlit as st

def load_global_css(file_name="style.css"):
    try:
        with open(file_name, "r") as f:
            css_code = f.read()
            st.markdown(f"<style>{css_code}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file '{file_name}' not found! Please check the file name and path.")