import streamlit as st
import pandas as pd
from datetime import date
from database import (
    add_fee, record_payment, get_student_fees, get_all_fees,
    delete_fee, get_all_students
)

st.set_page_config(page_title="Fees", page_icon="💰", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("💰 Fees")

tab1, tab2, tab3 = st.tabs(["➕ Add Fee Record", "💳 Record Payment", "📊 All Fee Records"])

students = get_all_students()

# ---------- TAB 1: ADD FEE RECORD ----------
with tab1:
    if not students:
        st.info("No students found. Add students first from the Students page.")
    else:
        student_options = {f"{row['name']} (Roll: {row['roll_no']})": row["id"] for row in students}

        with st.form("add_fee_form", clear_on_submit=True):
            selected_label = st.selectbox("Select Student*", list(student_options.keys()))
            c1, c2, c3 = st.columns(3)
            with c1:
                description = st.text_input("Description*", placeholder="e.g. Semester 1 Tuition Fee")
            with c2:
                amount = st.number_input("Amount*", min_value=0.0, step=100.0)
            with c3:
                due_date = st.date_input("Due Date", value=date.today())

            st.caption("*Required fields")
            submitted = st.form_submit_button("➕ Add Fee Record", use_container_width=True)

            if submitted:
                student_id = student_options[selected_label]
                success, message = add_fee(student_id, description, amount, str(due_date))
                if success:
                    st.success(message)
                else:
                    st.error(message)

# ---------- TAB 2: RECORD PAYMENT ----------
with tab2:
    if not students:
        st.info("No students found.")
    else:
        student_options = {f"{row['name']} (Roll: {row['roll_no']})": row["id"] for row in students}
        selected_label = st.selectbox("Select a student", list(student_options.keys()), key="payment_student")
        selected_id = student_options[selected_label]

        fees = get_student_fees(selected_id)
        unpaid_fees = [f for f in fees if f["status"] != "Paid"]

        if not unpaid_fees:
            st.info("No pending fee records for this student.")
        else:
            fee_options = {
                f"{row['description']} — ₹{row['amount']} (Paid so far: ₹{row['amount_paid']})": row["id"]
                for row in unpaid_fees
            }
            selected_fee_label = st.selectbox("Select fee record", list(fee_options.keys()))
            selected_fee_id = fee_options[selected_fee_label]

            with st.form("record_payment_form"):
                payment_amount = st.number_input("Payment Amount*", min_value=0.01, step=100.0)
                submitted = st.form_submit_button("💳 Record Payment", use_container_width=True)
                if submitted:
                    success, message = record_payment(selected_fee_id, payment_amount)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        st.divider()
        st.subheader("Fee History for this Student")
        if fees:
            df = pd.DataFrame([dict(row) for row in fees])
            display_df = df[["description", "amount", "amount_paid", "status", "due_date", "paid_date"]].copy()
            display_df.columns = ["Description", "Amount", "Paid", "Status", "Due Date", "Paid Date"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No fee records yet for this student.")

# ---------- TAB 3: ALL FEE RECORDS ----------
with tab3:
    all_fees = get_all_fees()

    if not all_fees:
        st.info("No fee records yet.")
    else:
        df = pd.DataFrame([dict(row) for row in all_fees])

        status_filter = st.selectbox("Filter by status", ["All", "Paid", "Unpaid", "Partial", "Overdue"])
        filtered_df = df.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["status"] == status_filter]

        total_amount = filtered_df["amount"].sum()
        total_paid = filtered_df["amount_paid"].sum()
        total_pending = total_amount - total_paid

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Billed", f"₹{total_amount:,.2f}")
        c2.metric("Total Collected", f"₹{total_paid:,.2f}")
        c3.metric("Pending", f"₹{total_pending:,.2f}")

        st.divider()

        display_df = filtered_df[["student_name", "roll_no", "description", "amount", "amount_paid", "status", "due_date"]].copy()
        display_df.columns = ["Student", "Roll No", "Description", "Amount", "Paid", "Status", "Due Date"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv, "fees.csv", "text/csv")

        st.divider()
        st.subheader("Delete a Fee Record")
        fee_options = {
            f"{row['student_name']} — {row['description']} (₹{row['amount']})": row["id"]
            for row in all_fees
        }
        selected = st.selectbox("Select record to delete", list(fee_options.keys()))
        if st.button("🗑️ Delete Fee Record"):
            success, message = delete_fee(fee_options[selected])
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
