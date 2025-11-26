from utils import execute_sql_query, log_db_action

# 1. Delete the employee with ID 10
delete_sql = "DELETE FROM employees WHERE employee_id = 2;"
result = execute_sql_query(delete_sql)

# 2. Log this action in audit_log
log_db_action(
    user="TestUser",
    action="DELETE",
    table_name="employees",
    record_id="2",
    details="Deleted employee with ID 2 for testing alert"
)

print("Employee deleted and alert logged successfully!")
