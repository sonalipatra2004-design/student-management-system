import streamlit as st
import pandas as pd
from database import (
    add_faculty, get_all_faculty, get_faculty_by_id,
    update_faculty, delete_faculty, get_all_departments, get_all_courses
)

st.set_page_config(page_title="Faculty", page_icon="👨‍🏫", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("👨‍🏫 Faculty")

tab1, tab2 = st.tabs(["📋 View / Manage Faculty", "➕ Add New Faculty"])

departments = get_all_departments()
dept_options = {"None": None}
dept_options.update({row["name"]: row["id"] for row in departments})

# ---------- TAB 1: VIEW / MANAGE ----------
with tab1:
    faculty_list = get_all_faculty()

    if not faculty_list:
        st.info("No faculty members added yet. Add one in the 'Add New Faculty' tab.")
    else:
        df = pd.DataFrame([dict(row) for row in faculty_list])
        display_df = df[["name", "employee_id", "department_name", "designation", "email", "contact"]].copy()
        display_df.columns = ["Name", "Employee ID", "Department", "Designation", "Email", "Contact"]
        display_df["Department"] = display_df["Department"].fillna("Unassigned")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv, "faculty.csv", "text/csv")

        st.divider()
        st.subheader("Edit or Delete a Faculty Member")

        faculty_options = {f"{row['name']} ({row['employee_id']})": row["id"] for row in faculty_list}
        selected_label = st.selectbox("Select a faculty member", list(faculty_options.keys()))
        selected_id = faculty_options[selected_label]
        faculty_member = get_faculty_by_id(selected_id)

        if faculty_member:
            with st.form("edit_faculty_form"):
                c1, c2 = st.columns(2)
                with c1:
                    name = st.text_input("Full Name*", value=faculty_member["name"])
                    employee_id = st.text_input("Employee ID*", value=faculty_member["employee_id"])
                    designation = st.text_input("Designation", value=faculty_member["designation"] or "")
                with c2:
                    current_dept_name = next((k for k, v in dept_options.items() if v == faculty_member["department_id"]), "None")
                    dept_select = st.selectbox("Department", list(dept_options.keys()),
                                                index=list(dept_options.keys()).index(current_dept_name))
                    email = st.text_input("Email", value=faculty_member["email"] or "")
                    contact = st.text_input("Contact", value=faculty_member["contact"] or "")

                col_a, col_b = st.columns(2)
                with col_a:
                    update_clicked = st.form_submit_button("💾 Update", use_container_width=True)
                with col_b:
                    delete_clicked = st.form_submit_button("🗑️ Delete", use_container_width=True)

                if update_clicked:
                    success, message = update_faculty(
                        selected_id, name, employee_id, dept_options[dept_select], designation, email, contact
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

                if delete_clicked:
                    st.session_state["confirm_delete_faculty_id"] = selected_id
                    st.session_state["confirm_delete_faculty_name"] = faculty_member["name"]

        if st.session_state.get("confirm_delete_faculty_id") == selected_id:
            st.warning(f"⚠️ Are you sure you want to delete **{st.session_state['confirm_delete_faculty_name']}**? This cannot be undone.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes, delete permanently", use_container_width=True, key="confirm_del_fac"):
                    success, message = delete_faculty(selected_id)
                    del st.session_state["confirm_delete_faculty_id"]
                    del st.session_state["confirm_delete_faculty_name"]
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            with c2:
                if st.button("❌ Cancel", use_container_width=True, key="cancel_del_fac"):
                    del st.session_state["confirm_delete_faculty_id"]
                    del st.session_state["confirm_delete_faculty_name"]
                    st.rerun()

        # Courses taught
        st.divider()
        st.subheader(f"Courses Taught by {faculty_member['name'] if faculty_member else ''}")
        all_courses = get_all_courses()
        taught = [c for c in all_courses if c["faculty_id"] == selected_id]
        if taught:
            df_taught = pd.DataFrame([dict(row) for row in taught])
            st.dataframe(df_taught[["name", "code", "semester"]].rename(
                columns={"name": "Course", "code": "Code", "semester": "Semester"}
            ), use_container_width=True, hide_index=True)
        else:
            st.caption("No courses assigned to this faculty member yet.")

# ---------- TAB 2: ADD NEW FACULTY ----------
with tab2:
    st.subheader("Add a New Faculty Member")
    with st.form("add_faculty_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name*", placeholder="e.g. Dr. Ramesh Kumar")
            employee_id = st.text_input("Employee ID*", placeholder="e.g. EMP-001")
            designation = st.text_input("Designation", placeholder="e.g. Associate Professor")
        with c2:
            dept_select = st.selectbox("Department", list(dept_options.keys()))
            email = st.text_input("Email", placeholder="e.g. ramesh@university.edu")
            contact = st.text_input("Contact Number", placeholder="e.g. 9876543210")

        st.caption("*Required fields")
        submitted = st.form_submit_button("➕ Add Faculty", use_container_width=True)

        if submitted:
            success, message = add_faculty(name, employee_id, dept_options[dept_select], designation, email, contact)
            if success:
                st.success(message)
            else:
                st.error(message)
