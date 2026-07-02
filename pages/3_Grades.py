import streamlit as st
import pandas as pd
from database import (
    add_grade, get_student_grades, get_all_grades,
    delete_grade_entry, get_all_students
)

st.set_page_config(page_title="Grades", page_icon="📝", layout="wide")

# ---------- LOGIN CHECK ----------
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("📝 Grades")

tab1, tab2, tab3 = st.tabs(["➕ Add Grade", "📄 Student Report", "📊 All Grades"])

# ---------- TAB 1: ADD GRADE ----------
with tab1:
    students = get_all_students()

    if not students:
        st.info("No students found. Add students first from the Students page.")
    else:
        student_options = {f"{row['name']} (Roll: {row['roll_no']}, Class: {row['class']})": row["id"] for row in students}

        with st.form("add_grade_form", clear_on_submit=True):
            selected_label = st.selectbox("Select Student*", list(student_options.keys()))
            c1, c2 = st.columns(2)
            with c1:
                subject = st.text_input("Subject*", placeholder="e.g. Mathematics")
                exam_type = st.selectbox("Exam Type*", ["Unit Test", "Mid-Term", "Final Exam", "Quiz", "Assignment"])
            with c2:
                marks_obtained = st.number_input("Marks Obtained*", min_value=0.0, step=0.5)
                max_marks = st.number_input("Maximum Marks*", min_value=1.0, step=0.5, value=100.0)

            st.caption("*Required fields")
            submitted = st.form_submit_button("➕ Add Grade", use_container_width=True)

            if submitted:
                student_id = student_options[selected_label]
                success, message = add_grade(student_id, subject, exam_type, marks_obtained, max_marks)
                if success:
                    st.success(message)
                else:
                    st.error(message)

# ---------- TAB 2: STUDENT REPORT ----------
with tab2:
    students = get_all_students()

    if not students:
        st.info("No students found. Add students first from the Students page.")
    else:
        student_options = {f"{row['name']} (Roll: {row['roll_no']})": row["id"] for row in students}
        selected_label = st.selectbox("Select a student", list(student_options.keys()), key="report_student")
        selected_id = student_options[selected_label]

        grades = get_student_grades(selected_id)

        if not grades:
            st.info("No grade records yet for this student.")
        else:
            df = pd.DataFrame([dict(row) for row in grades])
            df["Percentage"] = (df["marks_obtained"] / df["max_marks"] * 100).round(1)

            avg_pct = df["Percentage"].mean().round(1)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Exams", len(df))
            c2.metric("Average %", f"{avg_pct}%")
            c3.metric(
                "Grade",
                "A" if avg_pct >= 90 else "B" if avg_pct >= 75 else "C" if avg_pct >= 60 else "D" if avg_pct >= 40 else "F"
            )

            st.divider()

            display_df = df[["subject", "exam_type", "marks_obtained", "max_marks", "Percentage", "date"]].copy()
            display_df.columns = ["Subject", "Exam Type", "Marks Obtained", "Max Marks", "Percentage (%)", "Date"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Report as CSV", csv, f"grades_{selected_label}.csv", "text/csv")

            st.divider()
            st.subheader("Delete a Grade Entry")
            grade_options = {
                f"{row['subject']} - {row['exam_type']} ({row['marks_obtained']}/{row['max_marks']}) on {row['date']}": row["id"]
                for row in grades
            }
            selected_grade_label = st.selectbox("Select entry to delete", list(grade_options.keys()))
            if st.button("🗑️ Delete This Entry"):
                grade_id = grade_options[selected_grade_label]
                success, message = delete_grade_entry(grade_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

# ---------- TAB 3: ALL GRADES (CLASS-WIDE VIEW) ----------
with tab3:
    all_grades = get_all_grades()

    if not all_grades:
        st.info("No grade records yet.")
    else:
        df = pd.DataFrame([dict(row) for row in all_grades])
        df["Percentage"] = (df["marks_obtained"] / df["max_marks"] * 100).round(1)

        col1, col2 = st.columns(2)
        with col1:
            class_options = ["All"] + sorted(df["class"].unique().tolist())
            class_filter = st.selectbox("Filter by class", class_options)
        with col2:
            subject_options = ["All"] + sorted(df["subject"].unique().tolist())
            subject_filter = st.selectbox("Filter by subject", subject_options)

        filtered_df = df.copy()
        if class_filter != "All":
            filtered_df = filtered_df[filtered_df["class"] == class_filter]
        if subject_filter != "All":
            filtered_df = filtered_df[filtered_df["subject"] == subject_filter]

        display_df = filtered_df[["name", "class", "subject", "exam_type", "marks_obtained", "max_marks", "Percentage"]].copy()
        display_df.columns = ["Name", "Class", "Subject", "Exam Type", "Marks Obtained", "Max Marks", "Percentage (%)"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv, "all_grades.csv", "text/csv")
