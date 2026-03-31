from flask import Blueprint, render_template, session, redirect, url_for
from utils.db import get_db_connection

report_bp = Blueprint('reports', __name__)

@report_bp.route('/', methods=['GET'])
def reports_dashboard():
    # Ensure only admin can access
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('admin.admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ===== OVERVIEW =====
    cursor.execute("SELECT COUNT(*) AS total_patients FROM users WHERE role = 'patient'")
    total_patients = cursor.fetchone()['total_patients']

    cursor.execute("SELECT COUNT(*) AS total_doctors FROM doctors")
    total_doctors = cursor.fetchone()['total_doctors']

    cursor.execute("SELECT COUNT(*) AS total_rooms FROM rooms")
    total_rooms = cursor.fetchone()['total_rooms']

    cursor.execute("SELECT COUNT(*) AS total_appointments FROM appointments")
    total_appointments = cursor.fetchone()['total_appointments']

    # ===== BILLING =====
    cursor.execute("""
        SELECT 
            SUM(total_amount) AS total_revenue,
            COUNT(*) AS bills_generated
        FROM bills
        WHERE DATE(generated_date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """)
    billing_data = cursor.fetchone() or {'total_revenue': 0, 'bills_generated': 0}
    total_revenue = billing_data['total_revenue'] or 0
    bills_generated = billing_data['bills_generated'] or 0

    # ===== TOP DOCTORS =====
    cursor.execute("""
        SELECT d.full_name AS doctor_name, COUNT(a.appointment_id) AS total_appointments
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE DATE(a.appointment_date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY a.doctor_id
        ORDER BY total_appointments DESC
        LIMIT 5
    """)
    top_doctors = cursor.fetchall()

    # ===== INVENTORY =====
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_items,
            SUM(CASE WHEN quantity <= reorder_level THEN 1 ELSE 0 END) AS low_stock_count
        FROM inventory
    """)
    inventory_summary = cursor.fetchone() or {'total_items': 0, 'low_stock_count': 0}

    cursor.execute("""
        SELECT item_id, item_name, category, quantity, reorder_level
        FROM inventory
        WHERE quantity <= reorder_level
        ORDER BY quantity ASC
    """)
    low_stock_items = cursor.fetchall()

    # ===== APPOINTMENTS BY DOCTOR =====
    cursor.execute("""
        SELECT d.full_name AS doctor_name, COUNT(a.appointment_id) AS total_appointments
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE DATE(a.appointment_date) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY a.doctor_id
        ORDER BY total_appointments DESC
    """)
    by_doctor = cursor.fetchall()

    # ===== APPOINTMENTS BY DATE =====
    cursor.execute("""
        SELECT DATE(appointment_date) AS date, COUNT(appointment_id) AS total_appointments
        FROM appointments
        WHERE DATE(appointment_date) >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
        GROUP BY DATE(appointment_date)
        ORDER BY date ASC
    """)
    by_date = cursor.fetchall()

    conn.close()

    # Pass data to frontend
    return render_template('admin/index.html',
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_rooms=total_rooms,
        total_appointments=total_appointments,
        total_revenue_last_30_days=total_revenue,
        bills_generated_last_30_days=bills_generated,
        top_doctors_last_30_days=top_doctors,
        inventory_summary=inventory_summary,
        low_stock_items=low_stock_items,
        appointments_by_doctor_last_30_days=by_doctor,
        appointments_by_date_last_14_days=by_date
    )
