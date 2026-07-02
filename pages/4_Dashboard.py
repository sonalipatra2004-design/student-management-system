import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from database import get_all_students, get_all_grades, get_attendance_by_date, get_distinct_classes

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# ---------- LOGIN CHECK ----------
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("📊 Dashboard")

students = get_all_students()

if not students:
    st.info("No data yet. Add students from the Students page to see insights here.")
    st.stop()

# ---------- TOP METRICS ----------
all_grades = get_all_grades()
today_attendance = get_attendance_by_date(str(date.today()))
present_today = sum(1 for row in today_attendance if row["status"] == "Present")
total_today = len(today_attendance)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Students", len(students))
c2.metric("Classes", len(get_distinct_classes()))
c3.metric("Present Today", f"{present_today}/{total_today}" if total_today else "N/A")
c4.metric("Total Grade Entries", len(all_grades))

st.divider()

# ---------- CLASS-WISE STUDENT DISTRIBUTION ----------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Students by Class")
    df_students = pd.DataFrame([dict(row) for row in students])
    class_counts = df_students["class"].value_counts().reset_index()
    class_counts.columns = ["Class", "Count"]
    fig1 = px.bar(class_counts, x="Class", y="Count", color_discrete_sequence=["#2563eb"])
    fig1.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Gender Distribution")
    if "gender" in df_students.columns and df_students["gender"].notna().any():
        gender_counts = df_students["gender"].fillna("Not specified").value_counts().reset_index()
        gender_counts.columns = ["Gender", "Count"]
        fig2 = px.pie(gender_counts, names="Gender", values="Count", hole=0.4,
                      color_discrete_sequence=px.colors.sequential.Blues_r)
        fig2.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No gender data recorded yet.")

st.divider()

# ---------- ATTENDANCE TREND (LAST 7 DAYS) ----------
st.subheader("Attendance Trend (Last 7 Days)")

trend_data = []
for i in range(6, -1, -1):
    check_date = date.today() - timedelta(days=i)
    records = get_attendance_by_date(str(check_date))
    present = sum(1 for r in records if r["status"] == "Present")
    absent = sum(1 for r in records if r["status"] == "Absent")
    trend_data.append({"Date": str(check_date), "Present": present, "Absent": absent})

trend_df = pd.DataFrame(trend_data)
if trend_df[["Present", "Absent"]].sum().sum() == 0:
    st.info("No attendance records in the last 7 days yet.")
else:
    fig3 = px.line(trend_df, x="Date", y=["Present", "Absent"], markers=True,
                    color_discrete_map={"Present": "#16a34a", "Absent": "#dc2626"})
    fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------- GRADE PERFORMANCE ----------
st.subheader("Average Performance by Subject")

if not all_grades:
    st.info("No grade records yet. Add grades from the Grades page to see performance charts.")
else:
    df_grades = pd.DataFrame([dict(row) for row in all_grades])
    df_grades["Percentage"] = (df_grades["marks_obtained"] / df_grades["max_marks"] * 100).round(1)

    subject_avg = df_grades.groupby("subject")["Percentage"].mean().round(1).reset_index()
    subject_avg.columns = ["Subject", "Average %"]
    subject_avg = subject_avg.sort_values("Average %", ascending=False)

    fig4 = px.bar(subject_avg, x="Subject", y="Average %", color="Average %",
                  color_continuous_scale="Blues", range_y=[0, 100])
    fig4.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("Top Performers")
    top_df = df_grades.groupby("name")["Percentage"].mean().round(1).reset_index()
    top_df.columns = ["Name", "Average %"]
    top_df = top_df.sort_values("Average %", ascending=False).head(5)
    st.dataframe(top_df, use_container_width=True, hide_index=True)
