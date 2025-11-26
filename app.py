# app.py — Soft Gradient Website style (complete)
import os
import re
import time
import random
import pandas as pd
import streamlit as st
from rag_model import llm_sql
from utils import execute_sql_query, log_db_action, create_backup, restore_backup

# ---------------- page config ----------------
st.set_page_config(
    page_title="Employee AI Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- style (soft gradients + pastel) ----------------
def apply_soft_gradient_theme():
    st.markdown(
        """
    <style>
    :root{
      --bg1: #f7fbff;
      --bg2: #fff7fb;
      --card: #ffffff;
      --accent: #4f46e5;      /* Indigo */
      --accent-2: #06b6d4;    /* Teal */
      --muted: #6b7280;
    }

    /* page background gradient */
    .stApp {
      background: linear-gradient(180deg, var(--bg1) 0%, var(--bg2) 100%);
      color: #0f172a;
    }

    /* hero header */
    .hero {
      background: linear-gradient(90deg, rgba(79,70,229,0.12), rgba(6,182,212,0.08));
      border-radius: 14px;
      padding: 28px;
      margin-bottom: 18px;
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
    }

    .hero h1 {
      margin:0;
      font-size:34px;
      color: #0f172a;
      letter-spacing: -0.5px;
    }
    .hero p { margin:4px 0 0 0; color: var(--muted); }

    /* card */
    .card {
      background: var(--card);
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 6px 18px rgba(15,23,42,0.04);
      transition: transform .18s ease, box-shadow .18s ease;
      border: 1px solid rgba(15,23,42,0.03);
    }
    .card:hover { transform: translateY(-6px); box-shadow: 0 12px 30px rgba(15,23,42,0.06); }

    /* big action buttons (cards clickable) */
    .action-btn {
      display:flex;
      align-items:center;
      gap:14px;
      font-size:16px;
      font-weight:600;
      color: #08244a;
    }
    .action-badge {
      min-width:46px;
      min-height:46px;
      border-radius:10px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      color:white;
      font-weight:700;
    }
    .badge-indigo { background: linear-gradient(180deg,#7c3aed,#4f46e5); }
    .badge-teal { background: linear-gradient(180deg,#06b6d4,#0ea5a1); }
    .badge-rose { background: linear-gradient(180deg,#fb7185,#f43f5e); }
    .badge-amber { background: linear-gradient(180deg,#f59e0b,#f97316); }

    /* styled inputs & buttons */
    .stButton>button {
      background: linear-gradient(90deg,#7c3aed,#06b6d4) !important;
      color: white !important;
      border-radius: 10px !important;
      padding: 8px 16px !important;
      font-weight:600;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
      border-radius: 10px !important;
      padding: 10px !important;
      border: 1px solid rgba(15,23,42,0.06) !important;
      background: linear-gradient(180deg, white, #fbfbff) !important;
    }
    .stSelectbox>div>div>div {
      border-radius: 10px !important;
      border: 1px solid rgba(15,23,42,0.06) !important;
    }

    /* small helpers */
    .muted { color: var(--muted); font-size:14px; }
    .sql-box { background: linear-gradient(180deg,#fff7fb,#f7fbff); padding:12px; border-radius:8px; border-left:4px solid #4f46e5; font-family: monospace; white-space: pre-wrap; }
    </style>
    """,
        unsafe_allow_html=True,
    )


# ---------------- session timeout ----------------
SESSION_TIMEOUT = 900  # 15 minutes
if "last_activity" in st.session_state:
    if time.time() - st.session_state["last_activity"] > SESSION_TIMEOUT:
        st.session_state["authenticated"] = False
        st.warning("Session expired. Please log in again.")
st.session_state["last_activity"] = time.time()

# ---------------- auth users (keep your usernames & passwords) ----------------
USERS = {
    "HARINDER": "123",
    "HARJOT": "HAR123",
    "EKAM": "EKAM123",
    "HARDEEP": "DEEP123"
}

# ---------------- navigation state ----------------
if "page" not in st.session_state:
    st.session_state["page"] = "login"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ---------------- helpers ----------------
def go_to(page_name):
    st.session_state["page"] = page_name

def preprocess_query(user_question: str) -> str:
    user_question = re.sub(r"```.*?```", "", user_question, flags=re.DOTALL)
    user_question = re.sub(r"^\s*(SQL:|SQL Query:)", "", user_question, flags=re.IGNORECASE).strip()
    return user_question

# ---------------- login screen ----------------
def login_screen():
    apply_soft_gradient_theme()
    st.markdown("<div class='hero card'> <h1>Employee AI Agent</h1> <p class='muted'>Secure access to the company database — login & verify with OTP to continue.</p> </div>", unsafe_allow_html=True)

    # center login card
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("🔐 Sign in")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Sign in"):
            if username in USERS and password == USERS[username]:
                otp = str(random.randint(100000, 999999))
                st.session_state["otp"] = otp
                st.session_state["pending_user"] = username
                st.session_state["authenticated"] = False
                go_to("otp")
                st.success("Credentials accepted — enter OTP to continue.")
                # show demo OTP as warning (demo only)
                st.warning(f"(Demo OTP shown here) OTP: {otp}")
            else:
                st.error("Invalid username or password")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- otp screen ----------------
def otp_screen():
    apply_soft_gradient_theme()
    st.markdown("<div class='card'> <h3>📱 One-Time Password (OTP)</h3> <p class='muted'>Enter the 6-digit code sent to your registered device (demo OTP is displayed for testing).</p> </div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        entered = st.text_input("Enter OTP", key="otp_input")
        if st.button("Verify OTP"):
            if entered == st.session_state.get("otp"):
                st.session_state["authenticated"] = True
                st.session_state["username"] = st.session_state.get("pending_user", "unknown")
                # clear temp
                if "otp" in st.session_state: del st.session_state["otp"]
                if "pending_user" in st.session_state: del st.session_state["pending_user"]
                st.success("OTP verified — access granted.")
                go_to("home")
            else:
                st.error("Invalid OTP. Try again.")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- HOME DASHBOARD (colorful cards) ----------------
def home_screen():
    apply_soft_gradient_theme()
    # header hero
    st.markdown("<div class='hero'><h1>Welcome back — {}</h1><p class='muted'>Choose an action below to manage the company database.</p></div>".format(st.session_state.get("username","User")), unsafe_allow_html=True)

    # action cards (two rows)
    r1c1, r1c2, r1c3 = st.columns([1.2,1.2,1.2])
    with r1c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if st.button("❓ Ask Question"):
            go_to("ask")
        st.markdown("<p class='muted'>Use AI to convert natural language to SQL and run queries.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r1c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if st.button("📦 Create Backup"):
            go_to("backup")
        st.markdown("<p class='muted'>Make a timestamped copy of the company database.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r1c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if st.button("📂 Restore Backup"):
            go_to("restore")
        st.markdown("<p class='muted'>Restore a previous backup if needed.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    r2c1, r2c2 = st.columns([1.2,1.2])
    with r2c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if st.button("🔔 Recent Alerts"):
            go_to("alerts")
        st.markdown("<p class='muted'>View recent audit logs and database changes.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r2c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if st.button("🔓 Logout"):
            st.session_state["authenticated"] = False
            go_to("login")
        st.markdown("<p class='muted'>Log out safely from the dashboard.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- ASK SCREEN ----------------
def ask_screen():
    apply_soft_gradient_theme()
    st.header("❓ Ask the Database (Natural Language → SQL)")
    question = st.text_input("Type your question here:", key="ask_input")

    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("Run Query"):
            if not question.strip():
                st.warning("Please type a question first.")
            else:
                cleaned = preprocess_query(question)
                response = llm_sql.run(cleaned, user=st.session_state.get("username","system"))
                sql_query = response.get("sql")
                results = response.get("results")
                if sql_query:
                    st.markdown("**Generated SQL:**")
                    st.markdown(f"<div class='sql-box'>{sql_query}</div>", unsafe_allow_html=True)
                    # run SQL
                    execution = execute_sql_query(sql_query)
                    if isinstance(execution, dict) and execution.get("rows") is not None:
                        if execution["rows"]:
                            df = pd.DataFrame(execution["rows"], columns=execution["columns"])
                            st.dataframe(df)
                        else:
                            st.info("Query executed but no rows returned.")
                    else:
                        st.error(execution)
                else:
                    st.write("**Answer:**")
                    st.write(results)

    with col2:
        st.markdown("<div class='card'><h4>Tips</h4><ul><li>Ask in plain language</li><li>Try: \"List active employees in HR\"</li><li>Use filters like \"salary > 50000\"</li></ul></div>", unsafe_allow_html=True)

    if st.button("⬅ Back to Home"):
        go_to("home")

# ---------------- BACKUP SCREEN ----------------
def backup_screen():
    apply_soft_gradient_theme()
    st.header("📦 Create a Backup")
    st.markdown("<div class='card'><p class='muted'>Backups are stored in the <code>backups/</code> folder. Keep only necessary backups to save disk space.</p></div>", unsafe_allow_html=True)

    if st.button("Create Backup Now"):
        result = create_backup()
        if isinstance(result, dict):
            if result.get("success"):
                st.success(result.get("message"))
            else:
                st.error(result.get("message"))
        else:
            st.success(str(result))

    if st.button("⬅ Back to Home"):
        go_to("home")

# ---------------- RESTORE SCREEN ----------------
def restore_screen():
    apply_soft_gradient_theme()
    st.header("📂 Restore from Backup")
    backup_files = os.listdir("backups") if os.path.exists("backups") else []

    if not backup_files:
        st.warning("No backups found in the backups/ folder.")
    else:
        sel = st.selectbox("Choose a backup to restore", options=[""] + backup_files)
        if st.button("Restore Selected Backup"):
            if not sel:
                st.error("Select a backup first.")
            else:
                result = restore_backup(os.path.join("backups", sel))
                if isinstance(result, dict) and result.get("success"):
                    st.success(result.get("message"))
                else:
                    st.error(result)

    if st.button("⬅ Back to Home"):
        go_to("home")

# ---------------- ALERTS SCREEN ----------------
def alerts_screen():
    apply_soft_gradient_theme()
    st.header("🔔 Recent Alerts / Audit Log")
    logs = execute_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;")
    if isinstance(logs, dict) and logs.get("rows") is not None:
        rows = logs.get("rows")
        cols = logs.get("columns", [])
        if rows:
            df = pd.DataFrame(rows, columns=cols)
            st.dataframe(df)
        else:
            st.info("No recent alerts found.")
    else:
        st.error("Unable to fetch audit logs.")

    if st.button("⬅ Back to Home"):
        go_to("home")

# ---------------- router ----------------
if st.session_state["page"] == "login":
    login_screen()
elif st.session_state["page"] == "otp":
    otp_screen()
else:
    if st.session_state.get("authenticated"):
        if st.session_state["page"] == "home":
            home_screen()
        elif st.session_state["page"] == "ask":
            ask_screen()
        elif st.session_state["page"] == "backup":
            backup_screen()
        elif st.session_state["page"] == "restore":
            restore_screen()
        elif st.session_state["page"] == "alerts":
            alerts_screen()
    else:
        # force login if not authenticated
        go_to("login")
        login_screen()
