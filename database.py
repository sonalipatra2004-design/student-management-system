import sqlite3
import hashlib
import logging
from contextlib import contextmanager
from datetime import date, datetime

DB_NAME = "school.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("school_db")


# ---------- CONNECTION MANAGEMENT ----------

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
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
    with get_connection() as conn:
        c = conn.cursor()

        # ---------- DEPARTMENTS ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                code TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---------- FACULTY ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_id TEXT UNIQUE NOT NULL,
                department_id INTEGER,
                designation TEXT,
                email TEXT,
                contact TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE SET NULL
            )
        """)

        # ---------- COURSES ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                department_id INTEGER,
                credits REAL NOT NULL DEFAULT 3,
                semester INTEGER,
                faculty_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE SET NULL,
                FOREIGN KEY (faculty_id) REFERENCES faculty (id) ON DELETE SET NULL
            )
        """)

        # ---------- STUDENTS ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT UNIQUE NOT NULL,
                class TEXT NOT NULL,
                department_id INTEGER,
                semester INTEGER,
                section TEXT,
                gender TEXT,
                dob TEXT,
                contact TEXT,
                email TEXT,
                address TEXT,
                admission_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE SET NULL
            )
        """)

        # ---------- ENROLLMENTS (student <-> course) ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                academic_year TEXT NOT NULL,
                enrolled_on TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
                UNIQUE(student_id, course_id, academic_year)
            )
        """)

        # ---------- ATTENDANCE ----------
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

        # ---------- GRADES ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                course_id INTEGER,
                subject TEXT NOT NULL,
                exam_type TEXT NOT NULL,
                marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
                max_marks REAL NOT NULL CHECK(max_marks > 0),
                date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE SET NULL
            )
        """)

        # ---------- EXAMS (scheduling) ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                exam_name TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                start_time TEXT,
                max_marks REAL NOT NULL DEFAULT 100,
                room TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)

        # ---------- FEES ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                due_date TEXT,
                paid_date TEXT,
                status TEXT NOT NULL DEFAULT 'Unpaid' CHECK(status IN ('Paid', 'Unpaid', 'Partial', 'Overdue')),
                amount_paid REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        """)

        # ---------- USERS (login roles) ----------
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Admin', 'Faculty', 'Student')),
                linked_faculty_id INTEGER,
                linked_student_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (linked_faculty_id) REFERENCES faculty (id) ON DELETE SET NULL,
                FOREIGN KEY (linked_student_id) REFERENCES students (id) ON DELETE SET NULL
            )
        """)

        # ---------- INDEXES ----------
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_no)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_class ON students(class)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_fees_student ON fees(student_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_exams_course ON exams(course_id)")

        # ---------- DEFAULT ADMIN USER ----------
        c.execute("SELECT COUNT(*) as cnt FROM users WHERE role='Admin'")
        if c.fetchone()["cnt"] == 0:
            default_hash = hash_password("admin123")
            c.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, 'Admin')
            """, ("admin", default_hash))
            logger.info("Default admin user created: username='admin', password='admin123'")

        logger.info("Database initialized successfully.")


# ---------- VALIDATION / UTILITY HELPERS ----------

def _clean(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, password_hash):
    return hash_password(password) == password_hash


def validate_student_input(name, roll_no, class_):
    if not _clean(name):
        return False, "Name cannot be empty."
    if not _clean(roll_no):
        return False, "Roll number cannot be empty."
    if not _clean(class_):
        return False, "Class cannot be empty."
    if len(name) > 100:
        return False, "Name is too long (max 100 characters)."
    return True, ""


# ---------- USER / AUTH FUNCTIONS ----------

def create_user(username, password, role, linked_faculty_id=None, linked_student_id=None):
    if not _clean(username) or not _clean(password):
        return False, "Username and password cannot be empty."
    if role not in ("Admin", "Faculty", "Student"):
        return False, "Invalid role."

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (username, password_hash, role, linked_faculty_id, linked_student_id)
                VALUES (?, ?, ?, ?, ?)
            """, (_clean(username), hash_password(password), role, linked_faculty_id, linked_student_id))
            return True, "User account created successfully."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists."
    except Exception as e:
        logger.error(f"create_user failed: {e}")
        return False, "Something went wrong while creating the user."


def authenticate_user(username, password):
    """Returns (success, user_row_or_None, message)."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=?", (_clean(username),))
            user = c.fetchone()
            if not user:
                return False, None, "User not found."
            if not verify_password(password, user["password_hash"]):
                return False, None, "Incorrect password."
            return True, user, "Login successful."
    except Exception as e:
        logger.error(f"authenticate_user failed: {e}")
        return False, None, "Something went wrong during login."


def get_all_users():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id, username, role, linked_faculty_id, linked_student_id, created_at FROM users ORDER BY role, username")
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_users failed: {e}")
        return []


def delete_user(user_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE id=?", (user_id,))
            if c.rowcount == 0:
                return False, "User not found."
            return True, "User deleted successfully."
    except Exception as e:
        logger.error(f"delete_user failed: {e}")
        return False, "Something went wrong while deleting the user."


# ---------- DEPARTMENT FUNCTIONS ----------

def add_department(name, code):
    if not _clean(name) or not _clean(code):
        return False, "Department name and code cannot be empty."
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO departments (name, code) VALUES (?, ?)", (_clean(name), _clean(code)))
            return True, "Department added successfully."
    except sqlite3.IntegrityError:
        return False, "Department name or code already exists."
    except Exception as e:
        logger.error(f"add_department failed: {e}")
        return False, "Something went wrong while adding the department."


def get_all_departments():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM departments ORDER BY name")
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_departments failed: {e}")
        return []


def delete_department(department_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM departments WHERE id=?", (department_id,))
            if c.rowcount == 0:
                return False, "Department not found."
            return True, "Department deleted successfully."
    except Exception as e:
        logger.error(f"delete_department failed: {e}")
        return False, "Something went wrong while deleting the department."


# ---------- FACULTY FUNCTIONS ----------

def add_faculty(name, employee_id, department_id=None, designation=None, email=None, contact=None):
    if not _clean(name) or not _clean(employee_id):
        return False, "Name and employee ID cannot be empty."
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO faculty (name, employee_id, department_id, designation, email, contact)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (_clean(name), _clean(employee_id), department_id, _clean(designation), _clean(email), _clean(contact)))
            return True, "Faculty member added successfully."
    except sqlite3.IntegrityError:
        return False, f"Employee ID '{employee_id}' already exists."
    except Exception as e:
        logger.error(f"add_faculty failed: {e}")
        return False, "Something went wrong while adding the faculty member."


def get_all_faculty():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT f.*, d.name as department_name
                FROM faculty f LEFT JOIN departments d ON f.department_id = d.id
                ORDER BY f.name
            """)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_faculty failed: {e}")
        return []


def get_faculty_by_id(faculty_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM faculty WHERE id=?", (faculty_id,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"get_faculty_by_id failed: {e}")
        return None


def update_faculty(faculty_id, name, employee_id, department_id=None, designation=None, email=None, contact=None):
    if not _clean(name) or not _clean(employee_id):
        return False, "Name and employee ID cannot be empty."
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE faculty SET name=?, employee_id=?, department_id=?, designation=?, email=?, contact=?
                WHERE id=?
            """, (_clean(name), _clean(employee_id), department_id, _clean(designation), _clean(email), _clean(contact), faculty_id))
            if c.rowcount == 0:
                return False, "Faculty member not found."
            return True, "Faculty member updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Employee ID '{employee_id}' is already used."
    except Exception as e:
        logger.error(f"update_faculty failed: {e}")
        return False, "Something went wrong while updating the faculty member."


def delete_faculty(faculty_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM faculty WHERE id=?", (faculty_id,))
            if c.rowcount == 0:
                return False, "Faculty member not found."
            return True, "Faculty member deleted successfully."
    except Exception as e:
        logger.error(f"delete_faculty failed: {e}")
        return False, "Something went wrong while deleting the faculty member."


# ---------- COURSE FUNCTIONS ----------

def add_course(name, code, department_id=None, credits=3, semester=None, faculty_id=None):
    if not _clean(name) or not _clean(code):
        return False, "Course name and code cannot be empty."
    try:
        credits = float(credits)
    except (TypeError, ValueError):
        return False, "Credits must be numeric."

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO courses (name, code, department_id, credits, semester, faculty_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (_clean(name), _clean(code), department_id, credits, semester, faculty_id))
            return True, "Course added successfully."
    except sqlite3.IntegrityError:
        return False, f"Course code '{code}' already exists."
    except Exception as e:
        logger.error(f"add_course failed: {e}")
        return False, "Something went wrong while adding the course."


def get_all_courses(department_id=None):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            query = """
                SELECT c.*, d.name as department_name, f.name as faculty_name
                FROM courses c
                LEFT JOIN departments d ON c.department_id = d.id
                LEFT JOIN faculty f ON c.faculty_id = f.id
                WHERE 1=1
            """
            params = []
            if department_id:
                query += " AND c.department_id = ?"
                params.append(department_id)
            query += " ORDER BY c.semester, c.name"
            c.execute(query, params)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_courses failed: {e}")
        return []


def get_course_by_id(course_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM courses WHERE id=?", (course_id,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"get_course_by_id failed: {e}")
        return None


def update_course(course_id, name, code, department_id=None, credits=3, semester=None, faculty_id=None):
    if not _clean(name) or not _clean(code):
        return False, "Course name and code cannot be empty."
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE courses SET name=?, code=?, department_id=?, credits=?, semester=?, faculty_id=?
                WHERE id=?
            """, (_clean(name), _clean(code), department_id, credits, semester, faculty_id, course_id))
            if c.rowcount == 0:
                return False, "Course not found."
            return True, "Course updated successfully."
    except sqlite3.IntegrityError:
        return False, f"Course code '{code}' is already used."
    except Exception as e:
        logger.error(f"update_course failed: {e}")
        return False, "Something went wrong while updating the course."


def delete_course(course_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM courses WHERE id=?", (course_id,))
            if c.rowcount == 0:
                return False, "Course not found."
            return True, "Course deleted successfully."
    except Exception as e:
        logger.error(f"delete_course failed: {e}")
        return False, "Something went wrong while deleting the course."
# ---------- ENROLLMENT FUNCTIONS ----------

def enroll_student(student_id, course_id, academic_year):
    if not _clean(academic_year):
        return False, "Academic year cannot be empty."
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO enrollments (student_id, course_id, academic_year)
                VALUES (?, ?, ?)
            """, (student_id, course_id, _clean(academic_year)))
            return True, "Student enrolled successfully."
    except sqlite3.IntegrityError:
        return False, "Student is already enrolled in this course for this academic year."
    except Exception as e:
        logger.error(f"enroll_student failed: {e}")
        return False, "Something went wrong while enrolling the student."


def get_student_enrollments(student_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT e.id, c.name as course_name, c.code, c.credits, e.academic_year, f.name as faculty_name
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                LEFT JOIN faculty f ON c.faculty_id = f.id
                WHERE e.student_id = ?
                ORDER BY e.academic_year DESC
            """, (student_id,))
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_student_enrollments failed: {e}")
        return []


def get_course_enrollments(course_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT e.id, s.name as student_name, s.roll_no, e.academic_year
                FROM enrollments e
                JOIN students s ON e.student_id = s.id
                WHERE e.course_id = ?
                ORDER BY s.roll_no
            """, (course_id,))
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_course_enrollments failed: {e}")
        return []


def unenroll_student(enrollment_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM enrollments WHERE id=?", (enrollment_id,))
            if c.rowcount == 0:
                return False, "Enrollment record not found."
            return True, "Student unenrolled successfully."
    except Exception as e:
        logger.error(f"unenroll_student failed: {e}")
        return False, "Something went wrong while unenrolling the student."

# ---------- STUDENT FUNCTIONS ----------

def add_student(name, roll_no, class_, department_id=None, semester=None, section=None,
                 gender=None, dob=None, contact=None, email=None, address=None):
    is_valid, error = validate_student_input(name, roll_no, class_)
    if not is_valid:
        return False, error

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO students (name, roll_no, class, department_id, semester, section, gender, dob, contact, email, address, admission_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (_clean(name), _clean(roll_no), _clean(class_), department_id, semester, _clean(section),
                  _clean(gender), _clean(dob), _clean(contact), _clean(email), _clean(address), str(date.today())))
            return True, "Student added successfully."
    except sqlite3.IntegrityError:
        return False, f"Roll number '{roll_no}' already exists. Please use a unique roll number."
    except Exception as e:
        logger.error(f"add_student failed: {e}")
        return False, "Something went wrong while adding the student. Please try again."


def get_all_students(search=None, class_filter=None, department_id=None):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            query = """
                SELECT s.*, d.name as department_name
                FROM students s
                LEFT JOIN departments d ON s.department_id = d.id
                WHERE 1=1
            """
            params = []

            if search:
                query += " AND (s.name LIKE ? OR s.roll_no LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            if class_filter and class_filter != "All":
                query += " AND s.class = ?"
                params.append(class_filter)

            if department_id:
                query += " AND s.department_id = ?"
                params.append(department_id)

            query += " ORDER BY s.class, s.roll_no"
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
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT DISTINCT class FROM students ORDER BY class")
            return [row["class"] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"get_distinct_classes failed: {e}")
        return []


def update_student(student_id, name, roll_no, class_, department_id=None, semester=None, section=None,
                    gender=None, dob=None, contact=None, email=None, address=None):
    is_valid, error = validate_student_input(name, roll_no, class_)
    if not is_valid:
        return False, error

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE students
                SET name=?, roll_no=?, class=?, department_id=?, semester=?, section=?, gender=?, dob=?, contact=?, email=?, address=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (_clean(name), _clean(roll_no), _clean(class_), department_id, semester, _clean(section),
                  _clean(gender), _clean(dob), _clean(contact), _clean(email), _clean(address), student_id))
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
            return True, "Student deleted successfully (along with their attendance, grade, enrollment, and fee records)."
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

def add_grade(student_id, subject, exam_type, marks_obtained, max_marks, course_id=None):
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
                INSERT INTO grades (student_id, course_id, subject, exam_type, marks_obtained, max_marks, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (student_id, course_id, _clean(subject), _clean(exam_type), marks_obtained, max_marks, str(date.today())))
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


def calculate_cgpa(student_id):
    """Calculates CGPA using a 10-point scale based on percentage per course."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT g.marks_obtained, g.max_marks, COALESCE(c.credits, 1) as credits
                FROM grades g
                LEFT JOIN courses c ON g.course_id = c.id
                WHERE g.student_id = ?
            """, (student_id,))
            rows = c.fetchall()
            if not rows:
                return None

            total_points = 0
            total_credits = 0
            for row in rows:
                pct = (row["marks_obtained"] / row["max_marks"]) * 100
                grade_point = min(10, round(pct / 10, 2))
                total_points += grade_point * row["credits"]
                total_credits += row["credits"]

            if total_credits == 0:
                return None
            return round(total_points / total_credits, 2)
    except Exception as e:
        logger.error(f"calculate_cgpa failed: {e}")
        return None

# ---------- EXAM SCHEDULING FUNCTIONS ----------

def add_exam(course_id, exam_name, exam_date, start_time=None, max_marks=100, room=None):
    if not _clean(exam_name):
        return False, "Exam name cannot be empty."
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO exams (course_id, exam_name, exam_date, start_time, max_marks, room)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (course_id, _clean(exam_name), exam_date, start_time, max_marks, _clean(room)))
            return True, "Exam scheduled successfully."
    except Exception as e:
        logger.error(f"add_exam failed: {e}")
        return False, "Something went wrong while scheduling the exam."


def get_all_exams(upcoming_only=False):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            query = """
                SELECT e.*, c.name as course_name, c.code as course_code
                FROM exams e JOIN courses c ON e.course_id = c.id
                WHERE 1=1
            """
            params = []
            if upcoming_only:
                query += " AND e.exam_date >= ?"
                params.append(str(date.today()))
            query += " ORDER BY e.exam_date, e.start_time"
            c.execute(query, params)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_exams failed: {e}")
        return []


def delete_exam(exam_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM exams WHERE id=?", (exam_id,))
            if c.rowcount == 0:
                return False, "Exam not found."
            return True, "Exam deleted successfully."
    except Exception as e:
        logger.error(f"delete_exam failed: {e}")
        return False, "Something went wrong while deleting the exam."

# ---------- FEE FUNCTIONS ----------

def add_fee(student_id, description, amount, due_date=None):
    if not _clean(description):
        return False, "Description cannot be empty."
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "Amount must be numeric."
    if amount < 0:
        return False, "Amount cannot be negative."

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO fees (student_id, description, amount, due_date, status)
                VALUES (?, ?, ?, ?, 'Unpaid')
            """, (student_id, _clean(description), amount, due_date))
            return True, "Fee record added successfully."
    except Exception as e:
        logger.error(f"add_fee failed: {e}")
        return False, "Something went wrong while adding the fee record."


def record_payment(fee_id, amount_paid):
    try:
        amount_paid = float(amount_paid)
    except (TypeError, ValueError):
        return False, "Amount must be numeric."

    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT amount, amount_paid FROM fees WHERE id=?", (fee_id,))
            row = c.fetchone()
            if not row:
                return False, "Fee record not found."

            new_paid = row["amount_paid"] + amount_paid
            status = "Paid" if new_paid >= row["amount"] else "Partial"
            paid_date = str(date.today()) if status == "Paid" else None

            c.execute("""
                UPDATE fees SET amount_paid=?, status=?, paid_date=?
                WHERE id=?
            """, (new_paid, status, paid_date, fee_id))
            return True, f"Payment recorded. Status: {status}"
    except Exception as e:
        logger.error(f"record_payment failed: {e}")
        return False, "Something went wrong while recording the payment."


def get_student_fees(student_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM fees WHERE student_id=? ORDER BY due_date
            """, (student_id,))
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_student_fees failed: {e}")
        return []


def get_all_fees():
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT f.*, s.name as student_name, s.roll_no
                FROM fees f JOIN students s ON f.student_id = s.id
                ORDER BY f.due_date
            """)
            return c.fetchall()
    except Exception as e:
        logger.error(f"get_all_fees failed: {e}")
        return []


def delete_fee(fee_id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM fees WHERE id=?", (fee_id,))
            if c.rowcount == 0:
                return False, "Fee record not found."
            return True, "Fee record deleted successfully."
    except Exception as e:
        logger.error(f"delete_fee failed: {e}")
        return False, "Something went wrong while deleting the fee record."
