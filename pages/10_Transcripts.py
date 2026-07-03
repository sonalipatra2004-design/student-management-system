import streamlit as st
from datetime import date
from database import get_all_students, get_student_grades, calculate_cgpa, get_student_by_id
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
import io

st.set_page_config(page_title="Transcripts", page_icon="📜", layout="wide")

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Please log in from the Home page first.")
    st.stop()

st.title("📜 CGPA & Transcripts")

students = get_all_students()

if not students:
    st.info("No students found. Add students first from the Students page.")
    st.stop()

student_options = {f"{row['name']} (Roll: {row['roll_no']})": row["id"] for row in students}
selected_label = st.selectbox("Select a student", list(student_options.keys()))
selected_id = student_options[selected_label]

student = get_student_by_id(selected_id)
grades = get_student_grades(selected_id)
cgpa = calculate_cgpa(selected_id)

col1, col2, col3 = st.columns(3)
col1.metric("Total Exam Records", len(grades))
col2.metric("CGPA (out of 10)", cgpa if cgpa is not None else "N/A")
col3.metric("Class", student["class"] if student else "N/A")

if not grades:
    st.info("No grade records yet — CGPA cannot be calculated until grades are added.")
else:
    st.divider()
    st.subheader("Generate Transcript PDF")

    if st.button("📄 Generate Transcript", use_container_width=True):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=20, textColor=colors.HexColor("#1e3a8a"))
        heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], textColor=colors.HexColor("#334155"))
        normal_style = styles['Normal']

        story = []
        story.append(Paragraph("Academic Transcript", title_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Student Management System", normal_style))
        story.append(Spacer(1, 20))

        info_data = [
            ["Student Name:", student["name"]],
            ["Roll Number:", student["roll_no"]],
            ["Class:", student["class"]],
            ["Date Issued:", str(date.today())],
        ]
        info_table = Table(info_data, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))

        story.append(Paragraph("Grade Record", heading_style))
        story.append(Spacer(1, 10))

        table_data = [["Subject", "Exam Type", "Marks Obtained", "Max Marks", "Percentage", "Date"]]
        for g in grades:
            pct = round((g["marks_obtained"] / g["max_marks"]) * 100, 1)
            table_data.append([
                g["subject"], g["exam_type"], str(g["marks_obtained"]),
                str(g["max_marks"]), f"{pct}%", g["date"] or "-"
            ])

        grade_table = Table(table_data, colWidths=[3.5*cm, 3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        grade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(grade_table)
        story.append(Spacer(1, 24))

        cgpa_display = cgpa if cgpa is not None else "N/A"
        story.append(Paragraph(f"<b>Overall CGPA: {cgpa_display} / 10</b>", heading_style))
        story.append(Spacer(1, 40))

        story.append(Paragraph("This is a system-generated transcript.", normal_style))

        doc.build(story)
        buffer.seek(0)

        st.download_button(
            "⬇️ Download Transcript PDF",
            data=buffer,
            file_name=f"transcript_{student['roll_no']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.success("Transcript generated. Click above to download.")

    st.divider()
    st.subheader("Grade Details")
    import pandas as pd
    df = pd.DataFrame([dict(row) for row in grades])
    df["Percentage"] = (df["marks_obtained"] / df["max_marks"] * 100).round(1)
    display_df = df[["subject", "exam_type", "marks_obtained", "max_marks", "Percentage", "date"]].copy()
    display_df.columns = ["Subject", "Exam Type", "Marks", "Max Marks", "Percentage (%)", "Date"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
