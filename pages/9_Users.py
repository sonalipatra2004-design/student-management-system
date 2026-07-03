import streamlit as st
import pandas as pd
from database import create_user, get_all_users, delete_user, get_all_faculty, get_all_students

st.set_page_config(page_title="Users", page_icon="🔐", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

if st.session_state.user_role != "Admin":
    st.error("Only Admin accounts can manage users.")
    st.stop()

st.title("🔐 Manage User Accounts")

tab1, tab2 = st.tabs(["📋 All Users", "➕ Create New User"])

with tab1:
    users = get_all_users()
    if not users:
        st.info("No users found.")
    else:
        df = pd.DataFrame([dict(row) for row in users])
        display_df = df[["username", "role", "created_at"]].copy()
        display_df.columns = ["Username", "Role", "Created On"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Delete a User")
        user_options = {f"{row['username']} ({row['role']})": row["id"] for row in users if row["username"] != "admin"}
        if user_options:
            selected = st.selectbox("Select user to delete", list(user_options.keys()))
            if st.button("🗑️ Delete User"):
                success, message = delete_user(user_options[selected])
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.caption("No deletable users (default admin account is protected).")

with tab2:
    st.subheader("Create a New Login")
    role = st.selectbox("Role*", ["Admin", "Faculty", "Student"])

    linked_faculty_id = None
    linked_student_id = None

    if role == "Faculty":
        faculty_list = get_all_faculty()
        if faculty_list:
            faculty_options = {row["name"]: row["id"] for row in faculty_list}
            selected_faculty = st.selectbox("Link to Faculty Record", list(faculty_options.keys()))
            linked_faculty_id = faculty_options[selected_faculty]
        else:
            st.warning("No faculty records exist yet. Add one from the Faculty page first.")

    if role == "Student":
        student_list = get_all_students()
        if student_list:
            student_options = {f"{row['name']} (Roll: {row['roll_no']})": row["id"] for row in student_list}
            selected_student = st.selectbox("Link to Student Record", list(student_options.keys()))
            linked_student_id = student_options[selected_student]
        else:
            st.warning("No student records exist yet. Add one from the Students page first.")

    with st.form("create_user_form", clear_on_submit=True):
        username = st.text_input("Username*", placeholder="e.g. rkumar")
        password = st.text_input("Password*", type="password", placeholder="Choose a password")
        confirm_password = st.text_input("Confirm Password*", type="password")

        submitted = st.form_submit_button("➕ Create User", use_container_width=True)

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                success, message = create_user(username, password, role, linked_faculty_id, linked_student_id)
                if success:
                    st.success(message)
                else:
                    st.error(message)
