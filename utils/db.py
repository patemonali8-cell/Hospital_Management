import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="suruchi09",
        database="hospital_management"
    )

# Optional: Keep the test here or in app.py
try:
    conn = get_db_connection()
    if conn.is_connected():
        print("✅ Connected to MySQL database!")
    conn.close()
except Exception as e:
    print("❌ Database connection failed:", e)