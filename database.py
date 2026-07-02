import sqlite3
import logging
from contextlib import contextmanager
from datetime import date, datetime

DB_NAME = "school.db"

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("school_db")


# ---------- CONNECTION MANAGEMENT ----------

@contextmanager
def get_connection():
    """
    Provides a safe database connection that always closes,
    even if an error happens inside the 'with' block.
    Also enables foreign key enforcement (OFF by default in SQLite).
    """
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["name"]
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Creates all tables and indexes if they don't already exist."""
    with get_connection() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT UNIQUE NOT NULL,
                class TEXT NOT NULL,
                section TEXT,
                gender TEXT,
                dob TEXT,
                contact TEXT,
                email TEXT,
                address TEXT,
                admission_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late', 'Excused')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE(student_id, date)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                exam_type TEXT NOT NULL,
                marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
                max_marks REAL NOT NULL CHECK(max_marks > 0),
                date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        """)

        # Indexes for faster search/filter/lookup
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_no)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_class ON students(class)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id)")

        logger.info("Database initialized successfully.")


# ---------- VALIDATION HELPERS ----------

def _clean(value):
    """Strips whitespace, converts empty strings to None."""
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def validate_student_input(name, roll_no, class_):
    """Returns (is_valid, error_message)."""
    if not _clean(name):
        return False, "Name cannot be empty."
    if not _clean(roll_no):
        return False, "Roll number cannot be empty."
    if not _clean(class_):
        return False, "Class cannot be empty."
    if len(name) > 100:
        return False, "Name is too long (max 100 characters)."
    return True, ""


# ---------- STUDENT FUNCTIONS ----------

def add_student(name, roll_no, class_, section=None, gender=None, dob=None,
                 contact=None, email=None, address=None):
    is_valid, error = validate_student_input(name, roll_no, class_)
    if not is_valid:
        return False, error

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO students (name, roll_no, class, section, gender, dob, contact, email, address, admission_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (_clean(name), _clean(roll_no), _clean(class_), _clean(section), _clean(gender),
                  _clean(dob), _clean(contact), _clean(email), _clean(address), str(date.today())))
            return True, "Student added successfully."
    except sqlite3.IntegrityError:
        return False, f"Roll number '{roll_no}' already exists. Please use a unique roll number."
    except Exception as e:
        logger.error(f"add_student failed: {e}")
        return False, "Something went wrong while adding the student. Please try again."


def get_all_students(search=None, class_filter=None):
    """Returns list of student rows. Supports optional search by name/roll_no and class filter."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            query = "SELECT * FROM students WHERE 1=1"
            params = []

            if search:
                query += " AND (name LIKE ? OR roll_no LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            if class_filter and class_filter != "All":
                query += " AND class = ?"
                params.append(class_filter)

            query += " ORDER BY class, roll_no"
            c.execute(query, params)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_students failed: {e}")
        return []


def get_student_by_id(student_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"get_student_by_id failed: {e}")
        return None


def get_distinct_classes():
    """Used to populate class filter dropdowns."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT DISTINCT class FROM students ORDER BY class")
            return [row["class"] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"get_distinct_classes failed: {e}")
        return []


def update_student(student_id, name, roll_no, class_, section=None, gender=None,
                    dob=None, contact=None, email=None, address=None):
    is_valid, error = validate_student_input(name, roll_no, class_)
    if not is_valid:
        return False, error

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE students
                SET name=?, roll_no=?, class=?, section=?, gender=?, dob=?, contact=?, email=?, address=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (_clean(name), _clean(roll_no), _clean(class_), _clean(section), _clean(gender),
                  _clean(dob), _clean(contact), _clean(email), _clean(address), student_id))
            if c.rowcount == 0:
                return False, "Student not found."
            return True, "Student updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Roll number '{roll_no}' is already used by another student."
    except Exception as e:
        logger.error(f"update_student failed: {e}")
        return False, "Something went wrong while updating the student."


def delete_student(student_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM students WHERE id=?", (student_id,))
            if c.rowcount == 0:
                return False, "Student not found."
            return True, "Student deleted successfully (along with their attendance and grade records)."
    except Exception as e:
        logger.error(f"delete_student failed: {e}")
        return False, "Something went wrong while deleting the student."


# ---------- ATTENDANCE FUNCTIONS ----------

def mark_attendance(student_id, att_date, status):
    valid_statuses = ("Present", "Absent", "Late", "Excused")
    if status not in valid_statuses:
        return False, f"Status must be one of: {', '.join(valid_statuses)}"

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO attendance (student_id, date, status)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, date) DO UPDATE SET status=excluded.status
            """, (student_id, att_date, status))
            return True, "Attendance saved."
    except Exception as e:
        logger.error(f"mark_attendance failed: {e}")
        return False, "Something went wrong while saving attendance."


def get_attendance_by_date(att_date, class_filter=None):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            query = """
                SELECT s.id, s.name, s.roll_no, s.class, a.status
                FROM students s
                LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
                WHERE 1=1
            """
            params = [att_date]
            if class_filter and class_filter != "All":
                query += " AND s.class = ?"
                params.append(class_filter)
            query += " ORDER BY s.class, s.roll_no"
            c.execute(query, params)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_attendance_by_date failed: {e}")
        return []


def get_student_attendance(student_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT date, status FROM attendance WHERE student_id=? ORDER BY date", (student_id,))
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_student_attendance failed: {e}")
        return []


def get_attendance_summary(student_id):
    """Returns dict with counts of each status."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT status, COUNT(*) as count
                FROM attendance WHERE student_id=?
                GROUP BY status
            """, (student_id,))
            rows = c.fetchall()
            return {row["status"]: row["count"] for row in rows}
    except Exception as e:
        logger.error(f"get_attendance_summary failed: {e}")
        return {}


# ---------- GRADES FUNCTIONS ----------

def add_grade(student_id, subject, exam_type, marks_obtained, max_marks):
    if not _clean(subject) or not _clean(exam_type):
        return False, "Subject and exam type cannot be empty."
    try:
        marks_obtained = float(marks_obtained)
        max_marks = float(max_marks)
    except (TypeError, ValueError):
        return False, "Marks must be numeric."

    if max_marks <= 0:
        return False, "Maximum marks must be greater than 0."
    if marks_obtained < 0:
        return False, "Marks obtained cannot be negative."
    if marks_obtained > max_marks:
        return False, "Marks obtained cannot exceed maximum marks."

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO grades (student_id, subject, exam_type, marks_obtained, max_marks, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, _clean(subject), _clean(exam_type), marks_obtained, max_marks, str(date.today())))
            return True, "Grade added successfully."
    except Exception as e:
        logger.error(f"add_grade failed: {e}")
        return False, "Something went wrong while adding the grade."


def get_student_grades(student_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, subject, exam_type, marks_obtained, max_marks, date
                FROM grades WHERE student_id=? ORDER BY date DESC
            """, (student_id,))
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_student_grades failed: {e}")
        return []


def get_all_grades():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT g.id, s.name, s.class, g.subject, g.exam_type, g.marks_obtained, g.max_marks
                FROM grades g JOIN students s ON g.student_id = s.id
                ORDER BY g.date DESC
            """)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_grades failed: {e}")
        return []


def delete_grade_entry(grade_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM grades WHERE id=?", (grade_id,))
            if c.rowcount == 0:
                return False, "Grade entry not found."
            return True, "Grade deleted successfully."
    except Exception as e:
        logger.error(f"delete_grade_entry failed: {e}")
        return False, "Something went wrong while deleting the grade."
