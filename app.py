import os
import re
import time
import random
import pandas as pd
import streamlit as st
from rag_model import llm_sql
from utils import execute_sql_query, log_db_action, create_backup, restore_backup

#  Session & Timeout 
SESSION_TIMEOUT = 900  # 15 minutes

if "last_activity" in st.session_state:
    if time.time() - st.session_state["last_activity"] > SESSION_TIMEOUT:
        st.session_state["authenticated"] = False
        st.warning("Session expired. Please log in again.")
st.session_state["last_activity"] = time.time()


#  Authentication 
USERS = {
    "HARINDER": "H@rinder123",
    "HARJOT": "HAR123",
    "EKAM": "EKAM123",
    "HARDEEP": "DEEP123"
}

def login():
    st.title("Login to IT Company Database Assistant")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and password == USERS[username]:
            # Generate demo OTP
            otp = str(random.randint(100000, 999999))
            st.session_state["otp"] = otp
            st.session_state["pending_user"] = username
            st.warning(f"Enter OTP sent to your registered email/phone. (Demo OTP: {otp})")
        else:
            st.error("Invalid username or password")


def verify_otp():
    entered_otp = st.text_input("Enter OTP", type="default")
    if st.button("Verify OTP"):
        if entered_otp == st.session_state.get("otp"):
            st.session_state["authenticated"] = True
            st.session_state["username"] = st.session_state["pending_user"]
            st.success("MFA Verified! You are logged in.")
            del st.session_state["otp"]
            del st.session_state["pending_user"]
        else:
            st.error("Invalid OTP. Try again.")


# Query Preprocessing 
def preprocess_query(user_question: str) -> str:
    """Clean user input before sending to LLM"""
    user_question = re.sub(r"```.*?```", "", user_question, flags=re.DOTALL)
    user_question = re.sub(r"^\s*(SQL:|SQL Query:)", "", user_question, flags=re.IGNORECASE).strip()
    return user_question


#  Cached Query Execution 
def cached_execute_sql_query(query: str):
    return execute_sql_query(query)


#  Main App 
def main_app():
    st.title("IT Company Database Assistant")

    #  Backup & Restore 
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Backup Database"):
            result = create_backup()
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])

    with col2:
        backup_files = os.listdir("backups") if os.path.exists("backups") else []
        backup_file = st.selectbox("Select backup to restore", options=[""] + backup_files)
        if st.button("Restore Database"):
            if backup_file:
                backup_file_path = os.path.join("backups", backup_file)
                result = restore_backup(backup_file_path)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])
            else:
                st.error("Select a backup file to restore.")

    # User SQL / NL Question 
    user_question = st.text_input("Ask your question about the company database:")

    if st.button("Get Answer") and user_question:
        cleaned_question = preprocess_query(user_question)

        # Generate SQL query via LLM
        response = llm_sql.run(cleaned_question, user=st.session_state.get("username", "system"))

        sql_query = response.get("sql")
        results = response.get("results")

        # Display SQL query
        if sql_query:
            st.write("**Generated SQL Query:**")
            st.code(sql_query, language="sql")

            # Execute SQL and log changes
            if sql_query.strip().upper().startswith("SELECT"):
                result = cached_execute_sql_query(sql_query)
            else:
                result = execute_sql_query(sql_query)
                query_type = sql_query.split()[0].upper()
                table_name = "unknown"
                try:
                    if query_type == "INSERT":
                        table_name = sql_query.split()[2]
                    elif query_type == "UPDATE":
                        table_name = sql_query.split()[1]
                except IndexError:
                    pass
                log_db_action(
                    user=st.session_state.get("username", "unknown"),
                    action=query_type,
                    table_name=table_name,
                    record_id="N/A",
                    details=sql_query
                )

            # Show results in table form
            if isinstance(result, dict) and "rows" in result and "columns" in result:
                if result["rows"]:
                    df_result = pd.DataFrame(result["rows"], columns=result["columns"])
                    st.dataframe(df_result)
                else:
                    st.info("No data found.")
            else:
                st.error(result)
        else:
            # Non-SQL response
            st.write("**Answer:**")
            st.write(results)

    #  Recent Alerts 
    st.subheader("Recent Alerts")
    alerts = cached_execute_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 5;")
    if isinstance(alerts, dict) and "rows" in alerts and "columns" in alerts:
        if alerts["rows"]:
            df_alerts = pd.DataFrame(alerts["rows"], columns=alerts["columns"])
            st.table(df_alerts)
        else:
            st.info("No recent alerts found.")
    else:
        st.error("Error fetching alerts from database.")


#  App Controller 
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    if "otp" in st.session_state and "pending_user" in st.session_state:
        verify_otp()
    else:
        login()
else:
    main_app()
