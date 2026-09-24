import streamlit as st
import pandas as pd
import os
import re
import base64
import requests
import pypdf
from google import genai

# Explicitly collapsing sidebar on initial app load
st.set_page_config(
    page_title="AI Routine & Seat Plan Portal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📚 Student Exam Routine & Seat Plan Portal")

EXCEL_FILE = "Summer_2026_Final_Exam_Draft shared with teachers.xlsm"
SEAT_PLAN_PDF = "seat_plan.pdf"

# Updated Admin Credentials
ADMIN_EMAIL = "nazmulpolok80@gmail.com"
ADMIN_PASSWORD = "adminpasspolok76"

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")

# Configure Gemini Client
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        pass

def upload_to_github(file_bytes, target_path, commit_message):
    """Directly uploads/updates file in GitHub Repository via API"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GitHub Token or Repo Name missing in Secrets!"
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{target_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    # Check if file exists to get current sha
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, headers=headers, json=payload)
    if put_res.status_code in [200, 201]:
        return True, "Successfully committed to GitHub!"
    else:
        return False, f"GitHub Error: {put_res.json().get('message')}"

@st.cache_data
def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df.columns = df.columns.astype(str).str.strip()
        return df
    return None

# ==================== SIDEBAR ADMIN PANEL ====================
st.sidebar.title("🔐 Admin Panel")

# Session state initialization for login status
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    admin_email_input = st.sidebar.text_input("Enter Admin Email:")
    admin_pass_input = st.sidebar.text_input("Enter Admin Password:", type="password")
    login_btn = st.sidebar.button("Login")

    if login_btn:
        if admin_email_input.strip().lower() == ADMIN_EMAIL.lower() and admin_pass_input == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.sidebar.success("Logged In as Admin!")
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid Email or Password")
else:
    st.sidebar.success(f"Logged In: {ADMIN_EMAIL}")
    if st.sidebar.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()
        
    st.sidebar.subheader("📤 Upload to GitHub Repo")
    
    # 1. Routine File Upload
    uploaded_excel = st.sidebar.file_uploader("New Routine (.xlsx/.xlsm)", type=["xlsx", "xlsm"])
    if uploaded_excel and st.sidebar.button("Push Routine to GitHub"):
        with st.sidebar.spinner("Pushing to GitHub..."):
            file_bytes = uploaded_excel.getbuffer().tobytes()
            success, msg = upload_to_github(file_bytes, EXCEL_FILE, "Update Exam Routine Excel via Admin")
            if success:
                st.sidebar.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.sidebar.error(msg)

    # 2. Seat Plan PDF Upload
    uploaded_pdf = st.sidebar.file_uploader("New Seat Plan (.pdf)", type=["pdf"])
    if uploaded_pdf and st.sidebar.button("Push Seat Plan to GitHub"):
        with st.sidebar.spinner("Pushing to GitHub..."):
            file_bytes = uploaded_pdf.getbuffer().tobytes()
            success, msg = upload_to_github(file_bytes, SEAT_PLAN_PDF, "Update Seat Plan PDF via Admin")
            if success:
                st.sidebar.success(msg)
                st.rerun()
            else:
                st.sidebar.error(msg)

# ==================== MAIN SECTION ====================
tab1, tab2 = st.tabs(["🔍 Search Exam Routine", "🪑 Search Seat Plan"])

# ---------------- TAB 1: EXAM ROUTINE ----------------
with tab1:
    df = load_data()
    if df is not None:
        required_cols = ["NHR", "Date", "Starting Time", "Ending Time", "Course Code", "Course Title", "Student Count", "Faculty"]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            st.error(f"⚠️ Missing columns: {', '.join(missing_cols)}")
        else:
            search_input = st.text_input("🔍 Search Course Code/Name (comma separated):").strip()

            if search_input:
                queries = [q.strip() for q in search_input.split(",") if q.strip()]

                if queries:
                    mask = pd.Series(False, index=df.index)
                    for q in queries:
                        escaped_q = re.escape(q)
                        pattern = rf"(?i)\b{escaped_q}(?!\d)"
                        mask |= (
                            df["Course Code"].astype(str).str.contains(pattern, regex=True, na=False) |
                            df["Course Title"].astype(str).str.contains(q, case=False, na=False)
                        )
                    
                    results = df[mask][required_cols]

                    if not results.empty:
                        st.success(f"Total {len(results)} record(s) found:")
                        st.dataframe(results, use_container_width=True)

                        # Clash Detection
                        clashes = results[results.duplicated(subset=['Date', 'Starting Time'], keep=False)]
                        if not clashes.empty:
                            st.error("🚨 Exam Clash Detected!")
                            st.dataframe(clashes[['Date', 'Starting Time', 'Ending Time', 'Course Code', 'Course Title']], use_container_width=True)

                        # --- AI ROUTINE ASSISTANT SECTION ---
                        st.divider()
                        st.subheader("🤖 AI Routine Assistant")
                        if st.button("Generate AI Insights & Summary"):
                            if client:
                                with st.spinner("AI analyzing..."):
                                    prompt = f"Analyze exam routine and summarize:\n{results.to_string(index=False)}"
                                    try:
                                        interaction = client.interactions.create(
                                            model="gemini-3.6-flash",
                                            input=prompt
                                        )
                                        if interaction and interaction.output_text:
                                            st.info(interaction.output_text)
                                        else:
                                            st.error("AI returned empty response.")
                                    except Exception as err:
                                        st.error(f"AI Error: {err}")
                            else:
                                st.warning("⚠️ GEMINI_API_KEY is not configured in Streamlit Secrets!")
                    else:
                        st.warning("❌ No matching records found.")
    else:
        st.error(f"⚠️ Excel routine file '{EXCEL_FILE}' not found.")

# ---------------- TAB 2: SEAT PLAN PDF ----------------
with tab2:
    st.subheader("🪑 Find Your Exam Seat")
    if os.path.exists(SEAT_PLAN_PDF):
        seat_query = st.text_input("🔍 Enter Student ID (13-digit) or Name:").strip()
        
        if seat_query:
            if st.button("Search Seat Location"):
                with st.spinner("Searching seat plan PDF..."):
                    found_results = []
                    reader = pypdf.PdfReader(SEAT_PLAN_PDF)
                    
                    for page_num, page in enumerate(reader.pages, start=1):
                        text = page.extract_text()
                        if text and seat_query.lower() in text.lower():
                            lines = text.split("\n")
                            for line in lines:
                                if seat_query.lower() in line.lower():
                                    found_results.append((page_num, line))

                    if found_results:
                        st.success(f"✅ Matching records found for '{seat_query}':")
                        for page_no, details in found_results:
                            st.info(f"📍 **PDF Page {page_no}:** {details}")
                    else:
                        st.warning("❌ No seat record found for this ID/Name.")
    else:
        st.info("ℹ️ Seat plan PDF is not available yet.")
