import streamlit as st
import pandas as pd
from database import (
    add_student, get_all_students, get_student_by_id,
    update_student, delete_student, get_distinct_classes
)

st.set_page_config(page_title="Students", page_icon="🧑‍🎓", layout="wide")

# ---------- LOGIN CHECK ----------
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("🧑‍🎓 Students")

tab1, tab2 = st.tabs(["📋 View / Manage Students", "➕ Add New Student"])

# ---------- TAB 1: VIEW / MANAGE ----------
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Search by name or roll number", placeholder="Type to search...")
    with col2:
        classes = ["All"] + get_distinct_classes()
        class_filter = st.selectbox("Filter by class", classes)

    students = get_all_students(search=search if search else None, class_filter=class_filter)

    if not students:
        st.info("No students found. Add your first student in the 'Add New Student' tab.")
    else:
        st.caption(f"Showing {len(students)} student(s)")

        df = pd.DataFrame([dict(row) for row in students])
        display_df = df[["name", "roll_no", "class", "section", "gender", "contact", "email"]].copy()
        display_df.columns = ["Name", "Roll No", "Class", "Section", "Gender", "Contact", "Email"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Export
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv, "students.csv", "text/csv")

        st.divider()
        st.subheader("Edit or Delete a Student")

        student_options = {f"{row['name']} (Roll: {row['roll_no']}, Class: {row['class']})": row["id"] for row in students}
        selected_label = st.selectbox("Select a student", list(student_options.keys()))
        selected_id = student_options[selected_label]
        student = get_student_by_id(selected_id)

        if student:
            with st.form("edit_student_form"):
                c1, c2 = st.columns(2)
                with c1:
                    name = st.text_input("Full Name*", value=student["name"])
                    roll_no = st.text_input("Roll Number*", value=student["roll_no"])
                    class_ = st.text_input("Class*", value=student["class"])
                    section = st.text_input("Section", value=student["section"] or "")
                with c2:
                    gender = st.selectbox("Gender", ["", "Male", "Female", "Other"],
                                           index=["", "Male", "Female", "Other"].index(student["gender"]) if student["gender"] in ["", "Male", "Female", "Other"] else 0)
                    contact = st.text_input("Contact Number", value=student["contact"] or "")
                    email = st.text_input("Email", value=student["email"] or "")
                    address = st.text_area("Address", value=student["address"] or "")

                col_a, col_b = st.columns(2)
                with col_a:
                    update_clicked = st.form_submit_button("💾 Update Student", use_container_width=True)
                with col_b:
                    delete_clicked = st.form_submit_button("🗑️ Delete Student", use_container_width=True, type="secondary")

                if update_clicked:
                    success, message = update_student(
                        selected_id, name, roll_no, class_, section, gender,
                        student["dob"], contact, email, address
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

                if delete_clicked:
                    st.session_state["confirm_delete_id"] = selected_id
                    st.session_state["confirm_delete_name"] = student["name"]

        # Confirmation step for delete (outside the form, since forms can't nest confirmations)
        if st.session_state.get("confirm_delete_id") == selected_id:
            st.warning(f"⚠️ Are you sure you want to delete **{st.session_state['confirm_delete_name']}**? This will also delete their attendance and grade records. This cannot be undone.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes, delete permanently", use_container_width=True):
                    success, message = delete_student(selected_id)
                    del st.session_state["confirm_delete_id"]
                    del st.session_state["confirm_delete_name"]
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            with c2:
                if st.button("❌ Cancel", use_container_width=True):
                    del st.session_state["confirm_delete_id"]
                    del st.session_state["confirm_delete_name"]
                    st.rerun()

# ---------- TAB 2: ADD NEW STUDENT ----------
with tab2:
    st.subheader("Add a New Student")
    with st.form("add_student_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name*", placeholder="e.g. Priya Sharma")
            roll_no = st.text_input("Roll Number*", placeholder="e.g. 2026-101")
            class_ = st.text_input("Class*", placeholder="e.g. 10")
            section = st.text_input("Section", placeholder="e.g. A")
        with c2:
            gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
            dob = st.date_input("Date of Birth", value=None, min_value=pd.Timestamp("1990-01-01"))
            contact = st.text_input("Contact Number", placeholder="e.g. 9876543210")
            email = st.text_input("Email", placeholder="e.g. priya@email.com")

        address = st.text_area("Address")

        st.caption("*Required fields")
        submitted = st.form_submit_button("➕ Add Student", use_container_width=True)

        if submitted:
            dob_str = str(dob) if dob else None
            success, message = add_student(
                name, roll_no, class_, section, gender, dob_str, contact, email, address
            )
            if success:
                st.success(message)
            else:
                st.error(message)
