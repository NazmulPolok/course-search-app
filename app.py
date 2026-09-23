import streamlit as st
import pandas as pd
import os
import re
import google.generativeai as genai

st.set_page_config(page_title="AI-Powered Course Search", layout="wide")
st.title("📚 AI-Powered Exam Routine & Course Search App")

EXCEL_FILE = "Summer_2026_Final_Exam_Draft shared with teachers.xlsm"

# Configure Gemini AI API
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@st.cache_data
def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df.columns = df.columns.astype(str).str.strip()
        return df
    return None

df = load_data()

if df is not None:
    required_cols = ["NHR", "Date", "Starting Time", "Ending Time", "Course Code", "Course Title", "Student Count", "Faculty"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"⚠️ These columns are missing in the file: {', '.join(missing_cols)}")
    else:
        search_input = st.text_input("🔍 Search by Course Name or Code using comma (,) as separator (e.g. CSE110, CSE361.1):").strip()

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

                    # --- FEATURE 1: AI EXAM CLASH DETECTOR ---
                    clashes = results[results.duplicated(subset=['Date', 'Starting Time'], keep=False)]
                    if not clashes.empty:
                        st.error("🚨 **AI Alert: Exam Clash Detected!** You have multiple exams scheduled on the exact same date and time slot:")
                        st.dataframe(clashes[['Date', 'Starting Time', 'Ending Time', 'Course Code', 'Course Title']], use_container_width=True)

                    # --- FEATURE 2: AI ROUTINE ANALYZER & ASSISTANT ---
                    if GEMINI_API_KEY:
                        st.divider()
                        st.subheader("🤖 AI Routine Assistant")
                        if st.button("Generate AI Insights & Summary"):
                            with st.spinner("AI is analyzing your exam schedule..."):
                                try:
                                    # Fallback list for model aliases
                                    available_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
                                    response = None
                                    
                                    prompt = f"""
                                    Analyze this exam routine data for a student and provide a clear, encouraging summary in English:
                                    Data:
                                    {results.to_string(index=False)}

                                    Please include:
                                    1. Total number of exams.
                                    2. Exam start and end date range.
                                    3. Highlight any tight schedules or back-to-back exams.
                                    4. A brief exam preparation tip.
                                    """

                                    for model_name in available_models:
                                        try:
                                            model = genai.GenerativeModel(model_name)
                                            response = model.generate_content(prompt)
                                            if response:
                                                break
                                        except Exception:
                                            continue

                                    if response and response.text:
                                        st.info(response.text)
                                    else:
                                        st.error("Could not fetch response from Gemini API models.")

                                except Exception as e:
                                    st.error(f"AI Service Error: {e}")
                else:
                    st.warning("❌ No matching records found.")
        else:
            st.info("💡 Enter a Course Code or Title in the search box above.")
else:
    st.error(f"⚠️ Excel file '{EXCEL_FILE}' not found! Please make sure the file is placed in the same folder as app.py.")
