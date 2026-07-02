import streamlit as st
import pandas as pd
from datetime import date
from database import (
    mark_attendance, get_attendance_by_date, get_all_students,
    get_student_attendance, get_attendance_summary, get_distinct_classes
)

st.set_page_config(page_title="Attendance", page_icon="📅", layout="wide")

# ---------- LOGIN CHECK ----------
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("📅 Attendance")

tab1, tab2 = st.tabs(["✅ Mark Attendance", "📊 Student Attendance History"])

# ---------- TAB 1: MARK ATTENDANCE ----------
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_date = st.date_input("Select date", value=date.today())
    with col2:
        classes = ["All"] + get_distinct_classes()
        class_filter = st.selectbox("Filter by class", classes)

    records = get_attendance_by_date(str(selected_date), class_filter=class_filter)

    if not records:
        st.info("No students found. Add students first from the Students page.")
    else:
        st.caption(f"Marking attendance for {len(records)} student(s) on {selected_date}")

        status_options = ["Present", "Absent", "Late", "Excused"]

        with st.form("attendance_form"):
            responses = {}
            for row in records:
                current_status = row["status"] if row["status"] else "Present"
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"**{row['name']}** — Roll: {row['roll_no']}, Class: {row['class']}")
                with col_b:
                    responses[row["id"]] = st.selectbox(
                        "Status",
                        status_options,
                        index=status_options.index(current_status) if current_status in status_options else 0,
                        key=f"att_{row['id']}",
                        label_visibility="collapsed"
                    )
                st.divider()

            submitted = st.form_submit_button("💾 Save Attendance", use_container_width=True)

            if submitted:
                error_count = 0
                for student_id, status in responses.items():
                    success, message = mark_attendance(student_id, str(selected_date), status)
                    if not success:
                        error_count += 1
                        st.error(f"Failed for student ID {student_id}: {message}")

                if error_count == 0:
                    st.success(f"Attendance saved for {len(responses)} student(s) on {selected_date}.")
                else:
                    st.warning(f"Saved with {error_count} error(s). See above.")

        # Quick bulk actions
        st.divider()
        st.caption("Quick actions")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Mark All Present", use_container_width=True):
                for row in records:
                    mark_attendance(row["id"], str(selected_date), "Present")
                st.success("All students marked Present.")
                st.rerun()
        with c2:
            if st.button("❌ Mark All Absent", use_container_width=True):
                for row in records:
                    mark_attendance(row["id"], str(selected_date), "Absent")
                st.success("All students marked Absent.")
                st.rerun()

# ---------- TAB 2: STUDENT ATTENDANCE HISTORY ----------
with tab2:
    students = get_all_students()

    if not students:
        st.info("No students found. Add students first from the Students page.")
    else:
        student_options = {f"{row['name']} (Roll: {row['roll_no']})": row["id"] for row in students}
        selected_label = st.selectbox("Select a student", list(student_options.keys()))
        selected_id = student_options[selected_label]

        summary = get_attendance_summary(selected_id)
        history = get_student_attendance(selected_id)

        if not history:
            st.info("No attendance records yet for this student.")
        else:
            total = sum(summary.values())
            present = summary.get("Present", 0)
            attendance_pct = round((present / total) * 100, 1) if total > 0 else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Days", total)
            c2.metric("Present", summary.get("Present", 0))
            c3.metric("Absent", summary.get("Absent", 0))
            c4.metric("Late", summary.get("Late", 0))
            c5.metric("Attendance %", f"{attendance_pct}%")

            st.divider()

            df = pd.DataFrame([dict(row) for row in history])
            df.columns = ["Date", "Status"]
            df = df.sort_values("Date", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download History as CSV", csv, f"attendance_{selected_label}.csv", "text/csv")
