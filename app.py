import streamlit as st
import pandas as pd
import os
import re
import pypdf
from google import genai

st.set_page_config(page_title="AI Routine & Seat Plan Portal", layout="wide")
st.title("📚 Student Exam Routine & Seat Plan Portal")

EXCEL_FILE = "Summer_2026_Final_Exam_Draft shared with teachers.xlsm"
SEAT_PLAN_PDF = "seat_plan.pdf"
ADMIN_PASSWORD = "admin123"  # Ekhane apnar pochondo moto password din

# Configure Gemini Client
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        pass

@st.cache_data
def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df.columns = df.columns.astype(str).str.strip()
        return df
    return None

# ==================== SIDEBAR: ADMIN PANEL ====================
st.sidebar.title("🔐 Admin Panel")
admin_pass = st.sidebar.text_input("Enter Admin Password:", type="password")

if admin_pass == ADMIN_PASSWORD:
    st.sidebar.success("Admin Logged In!")
    
    st.sidebar.subheader("📤 Update Files")
    
    # 1. Update Routine Excel File
    uploaded_excel = st.sidebar.file_drop_target if hasattr(st.sidebar, "file_drop_target") else st.sidebar.file_uploader("Upload New Exam Routine (.xlsx/.xlsm)", type=["xlsx", "xlsm"])
    if uploaded_excel is not None:
        if st.sidebar.button("Save New Routine"):
            with open(EXCEL_FILE, "wb") as f:
                f.write(uploaded_excel.getbuffer())
            st.cache_data.clear()
            st.sidebar.success("✅ Exam Routine Updated Successfully!")
            st.rerun()

    # 2. Update Seat Plan PDF File
    uploaded_pdf = st.sidebar.file_uploader("Upload New Seat Plan (.pdf)", type=["pdf"])
    if uploaded_pdf is not None:
        if st.sidebar.button("Save New Seat Plan"):
            with open(SEAT_PLAN_PDF, "wb") as f:
                f.write(uploaded_pdf.getbuffer())
            st.sidebar.success("✅ Seat Plan PDF Updated Successfully!")
            st.rerun()

# ==================== MAIN SECTION: TABS ====================
tab1, tab2 = st.tabs(["🔍 Search Exam Routine", "🪑 Search Seat Plan"])

# ---------------- TAB 1: EXAM ROUTINE ----------------
with tab1:
    df = load_data()
    if df is not None:
        required_cols = ["NHR", "Date", "Starting Time", "Ending Time", "Course Code", "Course Title", "Student Count", "Faculty"]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            st.error(f"⚠️ These columns are missing in the file: {', '.join(missing_cols)}")
        else:
            search_input = st.text_input("🔍 Search by Course Name or Code (comma separated):").strip()

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

                        # Clash Detector
                        clashes = results[results.duplicated(subset=['Date', 'Starting Time'], keep=False)]
                        if not clashes.empty:
                            st.error("🚨 **Exam Clash Detected!** Multiple exams on same date & time slot:")
                            st.dataframe(clashes[['Date', 'Starting Time', 'Ending Time', 'Course Code', 'Course Title']], use_container_width=True)

                        # AI Routine Assistant
                        if client:
                            st.divider()
                            st.subheader("🤖 AI Routine Assistant")
                            if st.button("Generate AI Insights & Summary"):
                                with st.spinner("AI is analyzing schedule..."):
                                    prompt = f"Analyze this exam routine for a student and provide a concise summary:\nData:\n{results.to_string(index=False)}"
                                    try:
                                        interaction = client.interactions.create(
                                            model="gemini-3.6-flash",
                                            input=prompt
                                        )
                                        if interaction and interaction.output_text:
                                            st.info(interaction.output_text)
                                    except Exception as err:
                                        st.error(f"AI Error: {err}")
                    else:
                        st.warning("❌ No matching records found.")
    else:
        st.error(f"⚠️ Excel routine file not found! Upload it via Admin Panel.")

# ---------------- TAB 2: SEAT PLAN PDF ----------------
with tab2:
    st.subheader("🪑 Find Your Exam Seat")
    if os.path.exists(SEAT_PLAN_PDF):
        seat_query = st.text_input("🔍 Enter Student ID (13-digit) or Student Name:").strip()
        
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
        st.info("ℹ️ Seat plan PDF is not available yet. Admin can upload it from the left sidebar.")
