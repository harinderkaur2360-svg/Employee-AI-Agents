# create_db.py
import os
import sqlite3
import random
from faker import Faker
from pathlib import Path
from dotenv import load_dotenv

fake = Faker()
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./company.db")

def create_company_db():
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop tables if exist
    cursor.executescript("""
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS employees;
    DROP TABLE IF EXISTS departments;
    DROP TABLE IF EXISTS projects;
    DROP TABLE IF EXISTS employee_projects;
    DROP TABLE IF EXISTS clients;
    DROP TABLE IF EXISTS invoices;
    DROP TABLE IF EXISTS audit_log;
    """)

    # Create tables
    cursor.executescript("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        mfa_enabled INTEGER DEFAULT 0,
        mfa_secret TEXT
    );

    CREATE TABLE departments (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_name TEXT,
        manager_id INTEGER,
        location_id TEXT
    );

    CREATE TABLE employees (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone_number TEXT,
        hire_date DATE,
        job_id TEXT,
        salary REAL,
        department_id INTEGER,
        FOREIGN KEY(department_id) REFERENCES departments(department_id)
    );

    CREATE TABLE projects (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT,
        start_date DATE,
        end_date DATE,
        department_id INTEGER,
        FOREIGN KEY(department_id) REFERENCES departments(department_id)
    );

    CREATE TABLE employee_projects (
        employee_id INTEGER,
        project_id INTEGER,
        role TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(employee_id),
        FOREIGN KEY(project_id) REFERENCES projects(project_id)
    );

    CREATE TABLE clients (
        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        contact_email TEXT,
        contact_phone TEXT
    );

    CREATE TABLE invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        amount REAL,
        invoice_date DATE,
        status TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    );

    CREATE TABLE audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,           -- 'INSERT', 'UPDATE', 'DELETE'
        table_name TEXT,
        record_id TEXT,        -- primary key of affected record
        details TEXT,          -- optional JSON of old/new data
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Insert sample departments
    dept_ids = []
    for d in ["HR", "Sales", "IT", "Finance", "R&D", "Marketing"]:
        cursor.execute("INSERT INTO departments (department_name, location_id) VALUES (?, ?)", 
                       (d, fake.city()))
        dept_ids.append(cursor.lastrowid)

    # Insert sample employees
    emp_ids = []
    for i in range(200):
        dept = random.choice(dept_ids)
        cursor.execute("""
            INSERT INTO employees (first_name, last_name, email, phone_number, hire_date, job_id, salary, department_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fake.first_name(), fake.last_name(), fake.email(), fake.phone_number(),
             fake.date_this_decade(), fake.job(), round(random.uniform(40000, 120000), 2), dept))
        emp_ids.append(cursor.lastrowid)

    # Insert sample projects
    proj_ids = []
    for i in range(30):
        dept = random.choice(dept_ids)
        cursor.execute("INSERT INTO projects (project_name, start_date, end_date, department_id) VALUES (?, ?, ?, ?)",
                       (fake.bs().title(), fake.date_this_decade(), fake.date_this_decade(), dept))
        proj_ids.append(cursor.lastrowid)

    # Assign employees to projects
    for i in range(500):
        cursor.execute("INSERT INTO employee_projects (employee_id, project_id, role) VALUES (?, ?, ?)",
                       (random.choice(emp_ids), random.choice(proj_ids), random.choice(["Developer", "Manager", "Tester", "Analyst"])))

    # Insert sample clients
    client_ids = []
    for i in range(50):
        cursor.execute("INSERT INTO clients (client_name, contact_email, contact_phone) VALUES (?, ?, ?)",
                       (fake.company(), fake.email(), fake.phone_number()))
        client_ids.append(cursor.lastrowid)

    # Insert sample invoices
    for i in range(200):
        cursor.execute("INSERT INTO invoices (client_id, amount, invoice_date, status) VALUES (?, ?, ?, ?)",
                       (random.choice(client_ids), round(random.uniform(1000, 50000), 2),
                        fake.date_this_decade(), random.choice(["Paid", "Pending", "Overdue"])))

    conn.commit()
    conn.close()
    print(f"{DB_PATH} created with sample data, users table, and audit_log table")

if __name__ == "__main__":
    create_company_db()
