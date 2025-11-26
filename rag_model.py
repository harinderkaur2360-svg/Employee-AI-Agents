import os
import re
from langchain_core.prompts import PromptTemplate

from dotenv import load_dotenv
from groq import Groq
from utils import execute_sql_query, extract_sql_from_llm

# Load API key
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

#  Synonyms / Fuzzy Mapping 
SYNONYMS = {
    "staff": "employees",
    "worker": "employees",
    "projcts": "projects",
    "assignment": "projects",
    "dept": "departments",
    "customer": "clients"
}

def normalize_query(user_query: str) -> str:
    """Clean user input: lowercase, fix spelling, replace synonyms."""
    q = user_query
    for word, actual in SYNONYMS.items():
        q = re.sub(rf"\b{word}\b", actual, q, flags=re.IGNORECASE)
    return q

#  UPDATED SQL PROMPT (REPLACED COMPLETELY)
SQL_PROMPT = """
You are an advanced SQL generation AI agent for an IT company database.

Your responsibilities:
- Convert ANY natural language question into a valid SQL query.
- Understand spelling mistakes, short forms, synonyms, and fuzzy language.
- Identify which table(s) the question refers to, even if user words don't match.
- Always use existing columns exactly as in the database schema.

DATABASE SCHEMA (very important, follow EXACT columns):
--------------------------------------------------------
TABLE: employees
    employee_id, first_name, last_name, email, phone_number,
    hire_date, job_id, salary, department_id

TABLE: departments
    department_id, department_name, manager_id, location_id

TABLE: projects
    project_id, project_name, start_date, end_date, department_id

TABLE: employee_projects
    employee_id, project_id, role

TABLE: clients
    client_id, client_name, contact_email, contact_phone

TABLE: invoices
    invoice_id, client_id, amount, invoice_date, status

TABLE: users
    id, username, password_hash, mfa_enabled, mfa_secret

TABLE: audit_log
    id, user, action, table_name, record_id, details, timestamp
--------------------------------------------------------

FUZZY SYNONYMS (apply automatically):
- phone_number → phone, mobile, mob, cell, contact, phone no, mobile no
- salary → income, pay, earnings
- first_name → fname, firstname
- last_name → lname, lastname, sirname
- department → dept, dpt, dep
- client → customer, buyer
- project → task, assignment
- hire_date → joining date, join date
- email → mail, email id

RULES:
1. ALWAYS output a valid SQL query ONLY. No explanation.
2. If user spelling is wrong, auto-correct it.
3. If user uses synonyms, map them correctly.
4. If user asks something impossible (column not in schema):
      → Replace with the closest correct column.
5. If the user question is NOT related to database → respond in normal English.
6. Use simple SELECT queries unless update/insert/delete is clearly requested.
7. For ambiguous questions → choose the MOST logical interpretation.

EXAMPLES:
- "show mobile numbr of workers" → phone_number from employees
- "give me earning of staff" → salary from employees
- "customer phon no" → contact_phone from clients

NOW CONVERT THE USER QUESTION TO SQL.

User Question: {question}
"""

# Prompt template
sql_prompt_template = PromptTemplate(
    input_variables=["question"],
    template=SQL_PROMPT
)

#  Groq LLM Wrapper 
class GroqLangChainSQL:
    def __init__(self):
        self.model_name = "llama-3.3-70b-versatile"

    def run(self, user_question: str, user: str = "system") -> dict:
        """Generate SQL from question and execute it on DB"""
        normalized_q = normalize_query(user_question)
        prompt = SQL_PROMPT.format(question=normalized_q)

        response = groq_client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        llm_output = response.choices[0].message.content.strip()

        sql_query = extract_sql_from_llm(llm_output)

        if sql_query and sql_query.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            result = execute_sql_query(sql_query)
            if isinstance(result, list) and result and isinstance(result[0], dict):
                columns = list(result[0].keys())
                rows = [list(r.values()) for r in result]
                result = {"columns": columns, "rows": rows}
        else:
            sql_query = None
            result = {"columns": ["Answer"], "rows": [[llm_output]]}

        result.setdefault("columns", [])
        result.setdefault("rows", [])

        return {"sql": sql_query, "results": result}

llm_sql = GroqLangChainSQL()
