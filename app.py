import streamlit as st
import streamlit.components.v1 as components
from database import init_db, get_all_students, get_all_grades, get_attendance_by_date
from datetime import date

st.set_page_config(
    page_title="Student Management System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database (safe to call every run)
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization failed: {e}")
    st.stop()

# ---------- SIMPLE LOGIN SYSTEM ----------
APP_PASSWORD = "sona123"  # change this before sharing your app link

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_screen():
    st.title("🎓 Student Management System")
    st.subheader("Login")
    with st.form("login_form"):
        password = st.text_input("Enter Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if password == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            elif password == "":
                st.warning("Please enter a password.")
            else:
                st.error("Incorrect password. Try again.")

if not st.session_state.authenticated:
    login_screen()
    st.stop()

# ---------- LOGGED IN ----------

with st.sidebar:
    st.success("✅ Logged in")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# ---------- WELCOME ANIMATION ----------
components.html("""
<div id="welcome-banner" style="position:relative; width:100%; height:190px; border-radius:14px; overflow:hidden; background:linear-gradient(135deg,#eff6ff,#f0f9ff); border:1px solid #dbeafe; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <canvas id="canvas" style="position:absolute; top:0; left:0;"></canvas>
  <div id="text-block" style="position:relative; z-index:2; height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; opacity:0; transform:translateY(8px); transition:opacity 0.9s ease, transform 0.9s ease;">
    <div style="font-size:38px; margin-bottom:6px; animation:float 3.5s ease-in-out infinite;">🎓</div>
    <h1 style="color:#1e3a8a; font-family:'Segoe UI', sans-serif; font-size:28px; margin:0; letter-spacing:0.3px; font-weight:600;">
      Student Management System
    </h1>
    <p style="color:#64748b; font-family:'Segoe UI', sans-serif; font-size:14px; margin-top:6px;">
      Manage students, attendance and grades with ease
    </p>
  </div>
</div>

<style>
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-6px); }
}
</style>

<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const container = document.getElementById('welcome-banner');
canvas.width = container.offsetWidth;
canvas.height = container.offsetHeight;

const particles = [];
const particleCount = 32;

for (let i = 0; i < particleCount; i++) {
  particles.push({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 2 + 0.8,
    speedY: Math.random() * 0.3 + 0.08,
    speedX: (Math.random() - 0.5) * 0.2,
    opacity: Math.random() * 0.3 + 0.1
  });
}

function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particles.forEach(p => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(37,99,235,${p.opacity})`;
    ctx.fill();

    p.y -= p.speedY;
    p.x += p.speedX;

    if (p.y < -5) {
      p.y = canvas.height + 5;
      p.x = Math.random() * canvas.width;
    }
    if (p.x < -5) p.x = canvas.width + 5;
    if (p.x > canvas.width + 5) p.x = -5;
  });
  requestAnimationFrame(animate);
}

animate();

setTimeout(() => {
  const textBlock = document.getElementById('text-block');
  textBlock.style.opacity = '1';
  textBlock.style.transform = 'translateY(0px)';
}, 150);

window.addEventListener('resize', () => {
  canvas.width = container.offsetWidth;
  canvas.height = container.offsetHeight;
});
</script>
""", height=210)

st.divider()

# ---------- DASHBOARD METRICS ----------
try:
    students = get_all_students()
    total_students = len(students)
except Exception:
    total_students = 0
    st.warning("Could not load student data.")

col1, col2, col3 = st.columns(3)
col1.metric("Total Students", total_students)

try:
    today_attendance = get_attendance_by_date(str(date.today()))
    present_today = sum(1 for row in today_attendance if row["status"] == "Present")
    col2.metric("Present Today", present_today)
except Exception:
    col2.metric("Present Today", "N/A")

try:
    grades = get_all_grades()
    col3.metric("Grade Entries", len(grades))
except Exception:
    col3.metric("Grade Entries", "N/A")

st.divider()
st.info("👈 Open **Students** from the sidebar to add your first student.")
