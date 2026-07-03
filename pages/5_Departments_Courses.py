import streamlit as st
import pandas as pd
from database import (
    add_department, get_all_departments, delete_department,
    add_course, get_all_courses, get_course_by_id, update_course, delete_course,
    get_all_faculty
)

st.set_page_config(page_title="Departments & Courses", page_icon="🏛️", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("🏛️ Departments & Courses")

tab1, tab2 = st.tabs(["🏢 Departments", "📚 Courses"])

# ---------- TAB 1: DEPARTMENTS ----------
with tab1:
    with st.form("add_dept_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            dept_name = st.text_input("Department Name*", placeholder="e.g. Computer Science")
        with c2:
            dept_code = st.text_input("Department Code*", placeholder="e.g. CS")
        submitted = st.form_submit_button("➕ Add Department", use_container_width=True)
        if submitted:
            success, message = add_department(dept_name, dept_code)
            if success:
                st.success(message)
            else:
                st.error(message)

    st.divider()
    departments = get_all_departments()
    if not departments:
        st.info("No departments added yet.")
    else:
        df = pd.DataFrame([dict(row) for row in departments])
        st.dataframe(df[["name", "code"]].rename(columns={"name": "Name", "code": "Code"}),
                     use_container_width=True, hide_index=True)

        st.subheader("Delete a Department")
        dept_options = {f"{row['name']} ({row['code']})": row["id"] for row in departments}
        selected = st.selectbox("Select department to delete", list(dept_options.keys()))
        if st.button("🗑️ Delete Department"):
            success, message = delete_department(dept_options[selected])
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# ---------- TAB 2: COURSES ----------
with tab2:
    departments = get_all_departments()
    faculty = get_all_faculty()

    if not departments:
        st.info("Add at least one department first (in the Departments tab) before adding courses.")
    else:
        dept_options = {row["name"]: row["id"] for row in departments}
        faculty_options = {"None": None}
        faculty_options.update({row["name"]: row["id"] for row in faculty})

        with st.form("add_course_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                course_name = st.text_input("Course Name*", placeholder="e.g. Data Structures")
                course_code = st.text_input("Course Code*", placeholder="e.g. CS201")
                credits = st.number_input("Credits", min_value=0.5, step=0.5, value=3.0)
            with c2:
                dept_select = st.selectbox("Department*", list(dept_options.keys()))
                semester = st.number_input("Semester", min_value=1, max_value=12, step=1, value=1)
                faculty_select = st.selectbox("Assign Faculty (optional)", list(faculty_options.keys()))

            submitted = st.form_submit_button("➕ Add Course", use_container_width=True)
            if submitted:
                success, message = add_course(
                    course_name, course_code, dept_options[dept_select],
                    credits, semester, faculty_options[faculty_select]
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)

        st.divider()
        courses = get_all_courses()
        if not courses:
            st.info("No courses added yet.")
        else:
            df = pd.DataFrame([dict(row) for row in courses])
            display_df = df[["name", "code", "department_name", "credits", "semester", "faculty_name"]].copy()
            display_df.columns = ["Course", "Code", "Department", "Credits", "Semester", "Faculty"]
            display_df["Faculty"] = display_df["Faculty"].fillna("Unassigned")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.subheader("Delete a Course")
            course_options = {f"{row['name']} ({row['code']})": row["id"] for row in courses}
            selected = st.selectbox("Select course to delete", list(course_options.keys()))
            if st.button("🗑️ Delete Course"):
                success, message = delete_course(course_options[selected])
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
