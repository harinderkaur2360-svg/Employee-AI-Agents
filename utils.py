import sqlite3
import difflib
import re
import os
import shutil
import time
import hashlib
import pyotp      # MFA
import jwt        # JWT session tokens
from functools import lru_cache

# ------------------- CONFIG ------------------- #
DB_PATH = "company.db"
BACKUP_DIR = "backups"
SECRET_KEY = "supersecretkey123"     # change in production
ALGORITHM = "HS256"

os.makedirs(BACKUP_DIR, exist_ok=True)

# ------------------- DB SCHEMA ------------------- #
def get_db_schema(db_path=DB_PATH):
    """Fetch schema info for all tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = ""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for t in tables:
        tname = t[0]
        cursor.execute(f"PRAGMA table_info({tname});")
        cols = cursor.fetchall()
        schema += f"\nTable: {tname}\n"
        schema += ", ".join([f"{c[1]} ({c[2]})" for c in cols]) + "\n"

    conn.close()
    return schema


# ------------------- MAIN SQL EXECUTION ------------------- #
@lru_cache(maxsize=50)
def cached_query(query: str):
    """Cached SELECT queries"""
    return execute_sql_query(query)


def execute_sql_query(query: str, db_path=DB_PATH, user="system"):
    """
    Execute SQL safely with:
    - Allowed commands only
    - Fuzzy matching help
    - Audit logging
    - Returns dict always
    """
    allowed_keywords = ("SELECT", "INSERT", "UPDATE", "DELETE")
    keyword = query.strip().split()[0].upper()

    if keyword not in allowed_keywords:
        return {"error": "Only SELECT, INSERT, UPDATE, DELETE queries are allowed."}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(query)
        except sqlite3.OperationalError as e:
            error_message = str(e)

            # Attempt fuzzy matching suggestions
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]

            suggestions = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [col[1] for col in cursor.fetchall()]
                matches = difflib.get_close_matches(query, columns, n=2, cutoff=0.6)
                if matches:
                    suggestions[table] = matches

            return {
                "error": error_message,
                "suggestions": suggestions if suggestions else None
            }

        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.commit()

        # Log non-select actions
        if keyword in ("INSERT", "UPDATE", "DELETE"):
            log_db_action(user, keyword, "unknown", "N/A", f"Query: {query}")

        conn.close()

        return {"columns": cols, "rows": rows}

    except Exception as e:
        return {"error": str(e)}


# ------------------- LLM SQL EXTRACTION ------------------- #
def extract_sql_from_llm(llm_output: str) -> str:
    """Extract SQL query from LLM response"""
    match = re.search(r"```sql(.*?)```", llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE).*", llm_output, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(0).strip()

    return llm_output.strip()


# ------------------- AUDIT LOG ------------------- #
def log_db_action(user, action, table_name, record_id="", details="", db_path=DB_PATH):
    """Log DB changes"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (user, action, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?)
        """, (user, action, table_name, record_id, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUDIT ERROR] {e}")


# ------------------- BACKUP & RESTORE ------------------- #
def create_backup():
    """Create timestamped backup of the DB"""
    try:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"company_{timestamp}.db")
        shutil.copy(DB_PATH, backup_file)
        return {"success": True, "message": f"Backup created: {backup_file}"}
    except Exception as e:
        return {"success": False, "message": f"Backup failed: {e}"}


def restore_backup(backup_file: str):
    """Restore the DB"""
    try:
        shutil.copy(backup_file, DB_PATH)
        return {"success": True, "message": f"Database restored from {backup_file}"}
    except Exception as e:
        return {"success": False, "message": f"Restore failed: {e}"}


# ------------------- MFA (2FA) ------------------- #
def generate_mfa_secret():
    return pyotp.random_base32()


def get_mfa_token(secret):
    totp = pyotp.TOTP(secret)
    return totp.now()


def verify_mfa_token(secret, token):
    totp = pyotp.TOTP(secret)
    return totp.verify(token)


# ------------------- SESSION TOKENS ------------------- #
def create_session_token(user_id: str, expiry_minutes=15):
    payload = {
        "user_id": user_id,
        "exp": time.time() + (expiry_minutes * 60)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_session_token(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "user_id": decoded.get("user_id")}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Session expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"}
