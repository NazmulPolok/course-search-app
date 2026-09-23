import streamlit as st
import pandas as pd
import os
import re

st.set_page_config(page_title="Course Information Search", layout="wide")
st.title("📚 Exam Routine & Course Search App")

EXCEL_FILE = "Summer_2026_Final_Exam_Draft shared with teachers.xlsm"

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
        st.info(f"Available columns in the file: {', '.join(df.columns.tolist())}")
    else:
        search_input = st.text_input("🔍 Search by Course Name or Code using comma (,) as separator (e.g. CSE110, CSE361.1):").strip()

        if search_input:
            queries = [q.strip() for q in search_input.split(",") if q.strip()]

            if queries:
                mask = pd.Series(False, index=df.index)
                for q in queries:
                    # Escape special characters like '.' in course codes
                    escaped_q = re.escape(q)
                    # Pattern ensures the course code doesn't match extra digits at the end
                    pattern = rf"(?i)\b{escaped_q}(?!\d)"
                    
                    mask |= (
                        df["Course Code"].astype(str).str.contains(pattern, regex=True, na=False) |
                        df["Course Title"].astype(str).str.contains(q, case=False, na=False)
                    )
                
                results = df[mask][required_cols]

                if not results.empty:
                    st.success(f"Total {len(results)} record(s) found:")
                    st.dataframe(results, use_container_width=True)
                else:
                    st.warning("❌ No matching records found.")
        else:
            st.info("💡 Enter a Course Code or Title in the search box above.")
else:
    st.error(f"⚠️ Excel file '{EXCEL_FILE}' not found! Please make sure the file is placed in the same folder as app.py.")
