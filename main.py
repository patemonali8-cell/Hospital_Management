from werkzeug.security import generate_password_hash
import mysql.connector

# DB connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="suruchi09",
    database="hospital_management"
)
cursor = conn.cursor()

# Admin data
full_name = "Admin User"
email = "admin@admin.com"
password = "pass@123"  # Choose a strong password
password_hash = generate_password_hash(password)
role = "admin"
gender = "Male"
dob = "1990-01-01"
contact_no = "1234567890"
address = "Admin Address"
city = "City"
state = "State"
postal_code = "000000"

# Insert query
insert_query = """
INSERT INTO users 
(full_name, gender, dob, email, password_hash, role, contact_no, address, city, state, postal_code)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""
cursor.execute(insert_query, (full_name, gender, dob, email, password_hash, role,
                              contact_no, address, city, state, postal_code))
conn.commit()
cursor.close()
conn.close()

print("✅ Admin user inserted successfully!")
