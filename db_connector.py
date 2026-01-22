import mysql.connector
from mysql.connector import Error

def get_db_connection():
    """Establishes a connection to the college_rag_db database."""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='college_rag_db',
            user='root',
            password='AryanPandey@1'    # <--- Your Password
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def execute_query(query):
    """Executes a Read-Only SQL query and returns the results as a list of dictionaries."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True) 
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            return f"SQL Error: {e}"
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    return "Connection Error"

def get_all_faculty_names():
    """Fetches all unique faculty names from both schedule and project tables."""
    conn = get_db_connection()
    names = set()
    
    if conn:
        cursor = conn.cursor()
        try:
            # 1. Get names from Schedule
            cursor.execute("SELECT DISTINCT faculty_name FROM faculty_schedule")
            for row in cursor.fetchall():
                if row[0]: # Check if not None
                    names.add(row[0])
            
            # 2. Get names from Projects
            cursor.execute("SELECT DISTINCT mentor_name FROM final_year_project")
            for row in cursor.fetchall():
                if row[0]: # Check if not None
                    names.add(row[0])
                    
        except Error as e:
            print(f"Error fetching names: {e}")
            
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
                
    return list(names)