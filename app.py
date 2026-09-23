import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Course Information Search", layout="wide")
st.title("📚 Exam Routine & Course Search App")

# Excel file path (Make sure the excel file is in the same folder in GitHub)
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
        st.error(f"⚠️ File-e ei column-gulo pawa jayni: {', '.join(missing_cols)}")
        st.info(f"File-e ekhon je column-gulo ache: {', '.join(df.columns.tolist())}")
    else:
        search_input = st.text_input("🔍 Course Name ba Code comma (,) diye search korun (e.g. CSE110, MAT120):").strip()

        if search_input:
            queries = [q.strip() for q in search_input.split(",") if q.strip()]

            if queries:
                mask = pd.Series(False, index=df.index)
                for q in queries:
                    mask |= (
                        df["Course Code"].astype(str).str.contains(q, case=False, na=False) |
                        df["Course Title"].astype(str).str.contains(q, case=False, na=False)
                    )
                
                results = df[mask][required_cols]

                if not results.empty:
                    st.success(f"Mot {len(results)} ti record pawa geche:")
                    st.dataframe(results, use_container_width=True)
                else:
                    st.warning("❌ Kono match pawa jayni.")
        else:
            st.info("💡 Uporer box-e Course Code ba Title likhe search korun.")
else:
    st.error(f"⚠️ Excel file '{EXCEL_FILE}' pawa jayni! Onugroho kore file-ti app.py er shathe ek-i folder-e rakhun.")