import streamlit as st
import pandas as pd
from datetime import date, time
from database import add_exam, get_all_exams, delete_exam, get_all_courses

st.set_page_config(page_title="Exams", page_icon="🗓️", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("🗓️ Exam Scheduling")

tab1, tab2 = st.tabs(["📅 Timetable", "➕ Schedule New Exam"])

courses = get_all_courses()

# ---------- TAB 1: TIMETABLE ----------
with tab1:
    view_filter = st.radio("Show", ["Upcoming", "All"], horizontal=True)
    exams = get_all_exams(upcoming_only=(view_filter == "Upcoming"))

    if not exams:
        st.info("No exams scheduled yet." if view_filter == "All" else "No upcoming exams scheduled.")
    else:
        df = pd.DataFrame([dict(row) for row in exams])
        display_df = df[["exam_name", "course_name", "course_code", "exam_date", "start_time", "room", "max_marks"]].copy()
        display_df.columns = ["Exam", "Course", "Code", "Date", "Time", "Room", "Max Marks"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Timetable as CSV", csv, "exam_timetable.csv", "text/csv")

        st.divider()
        st.subheader("Cancel / Delete an Exam")
        exam_options = {
            f"{row['exam_name']} — {row['course_name']} on {row['exam_date']}": row["id"]
            for row in exams
        }
        selected = st.selectbox("Select exam to delete", list(exam_options.keys()))
        if st.button("🗑️ Delete Exam"):
            success, message = delete_exam(exam_options[selected])
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# ---------- TAB 2: SCHEDULE NEW EXAM ----------
with tab2:
    if not courses:
        st.info("No courses found. Add courses first from the Departments & Courses page.")
    else:
        course_options = {f"{row['name']} ({row['code']})": row["id"] for row in courses}

        with st.form("add_exam_form", clear_on_submit=True):
            course_select = st.selectbox("Course*", list(course_options.keys()))
            c1, c2 = st.columns(2)
            with c1:
                exam_name = st.text_input("Exam Name*", placeholder="e.g. Mid-Semester Exam")
                exam_date = st.date_input("Exam Date*", value=date.today())
            with c2:
                start_time = st.time_input("Start Time", value=time(9, 0))
                max_marks = st.number_input("Maximum Marks", min_value=1.0, value=100.0, step=1.0)

            room = st.text_input("Room / Venue", placeholder="e.g. Room 204")

            st.caption("*Required fields")
            submitted = st.form_submit_button("➕ Schedule Exam", use_container_width=True)

            if submitted:
                course_id = course_options[course_select]
                success, message = add_exam(
                    course_id, exam_name, str(exam_date), str(start_time), max_marks, room
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)
