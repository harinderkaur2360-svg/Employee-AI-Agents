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
    "assignment": "assignments",
    "dept": "department",
    "customer": "clients"
}

def normalize_query(user_query: str) -> str:
    """Clean user input: lowercase, fix spelling, replace synonyms."""
    q = user_query
    for word, actual in SYNONYMS.items():
        q = re.sub(rf"\b{word}\b", actual, q, flags=re.IGNORECASE)
    return q

#  SQL Prompt 
SQL_PROMPT = """
You are an expert AI agent for SQL and reasoning. 
Your job is to convert user questions into valid SQL queries 
for the IT company database, even if:

- The user has spelling mistakes (e.g., "pendng" → "Pending").  
- The user uses broken English or incomplete words.  
- The user asks in puzzle/logical/natural language form.  

Guidelines:
1. Always return a valid SQL query if the request is database-related.
   - Use fuzzy matching for possible column values.
   - Suggest closest matching field or value if exact match is not found.
2. If the question is NOT SQL-related, answer in plain text.
3. Do NOT include explanations or markdown in SQL responses — only the SQL query.

Question: {question}
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

        # Call Groq LLM
        response = groq_client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        llm_output = response.choices[0].message.content.strip()

        # Extract SQL if present
        sql_query = extract_sql_from_llm(llm_output)

        # Execute SQL if valid
        if sql_query and sql_query.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            result = execute_sql_query(sql_query)
            # Convert list of dicts to rows/columns if needed
            if isinstance(result, list) and result and isinstance(result[0], dict):
                columns = list(result[0].keys())
                rows = [list(r.values()) for r in result]
                result = {"columns": columns, "rows": rows}
        else:
            # Non-SQL answer → wrap in table format
            sql_query = None
            result = {"columns": ["Answer"], "rows": [[llm_output]]}

        # Ensure dictionary structure
        result.setdefault("columns", [])
        result.setdefault("rows", [])

        return {"sql": sql_query, "results": result}

# Instance
llm_sql = GroqLangChainSQL()
