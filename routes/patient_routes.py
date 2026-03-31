from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from utils.db import get_db_connection
from datetime import datetime

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

# ---------------------------
# Dashboard
# ---------------------------
@patient_bp.route('/', methods=['GET'])
def dashboard():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Please log in to access the dashboard", "danger")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id=%s AND role='patient'", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            flash("User not found", "danger")
            return redirect(url_for('auth.login'))

        return render_template('patient/index.html', user=user)

    except Exception as e:
        print("Error loading dashboard:", e)
        flash("Something went wrong", "danger")
        return redirect(url_for('auth.login'))

# ---------------------------
# View Appointments
# ---------------------------
@patient_bp.route('/appointments', methods=['GET'])
def appointments():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Please login first", "warning")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT a.*, d.full_name AS doctor_name, d.specialization
            FROM appointments a
            LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
            WHERE a.patient_id=%s
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """, (session['user_id'],))
        appointments = cursor.fetchall()

        cursor.execute("SELECT doctor_id, full_name, specialization FROM doctors WHERE availability_status='available'")
        doctors = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('patient/appointments.html', appointments=appointments, doctors=doctors, user_name=session.get('user_name'))

    except Exception as e:
        print("Error loading appointments:", e)
        flash("Failed to load appointments", "danger")
        return render_template('patient/appointments.html', appointments=[], doctors=[], user_name=session.get('user_name'))

# ---------------------------
# Create Appointment
# ---------------------------
@patient_bp.route('/appointments/create', methods=['POST'])
def create_appointment():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Please login first", "warning")
        return redirect(url_for('auth.login'))

    doctor_id = request.form.get('doctor_id')
    appointment_date = request.form.get('appointment_date')
    reason = request.form.get('reason')

    if not doctor_id or not appointment_date:
        flash("Please select doctor and date", "warning")
        return redirect(url_for('patient.appointments'))

    try:
        datetime.strptime(appointment_date, '%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, reason, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (session['user_id'], doctor_id, appointment_date, reason))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Appointment requested successfully! Admin will confirm time.", "success")
        return redirect(url_for('patient.appointments'))

    except Exception as e:
        print("Error creating appointment:", e)
        flash("Failed to request appointment", "danger")
        return redirect(url_for('patient.appointments'))

# ---------------------------
# Bills
# ---------------------------
@patient_bp.route('/bills', methods=['GET'])
def bills():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Please login first", "warning")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bills WHERE patient_id=%s ORDER BY generated_date DESC", (session['user_id'],))
        bills = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('patient/bills.html', bills=bills, user_name=session.get('user_name'))

    except Exception as e:
        print("Error loading bills:", e)
        flash("Failed to load bills", "danger")
        return render_template('patient/bills.html', bills=[], user_name=session.get('user_name'))

@patient_bp.route('/bills/<int:bill_id>', methods=['GET'])
def view_bill(bill_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Please login first", "warning")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bills WHERE bill_id=%s AND patient_id=%s", (bill_id, session['user_id']))
        bill = cursor.fetchone()
        cursor.close()
        conn.close()

        if not bill:
            flash("Bill not found", "danger")
            return redirect(url_for('patient.bills'))

        return render_template('patient/view_bill.html', bill=bill, user_name=session.get('user_name'))

    except Exception as e:
        print("Error loading bill:", e)
        flash("Failed to load bill", "danger")
        return redirect(url_for('patient.bills'))

# ------------------- PATIENT: My Admissions -------------------
@patient_bp.route('/admissions', methods=['GET'])
def my_admissions():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch patient's admissions
    cursor.execute("""
        SELECT pa.*, d.full_name AS doctor_name, r.room_no
        FROM patient_admissions pa
        JOIN doctors d ON pa.doctor_id = d.doctor_id
        JOIN rooms r ON pa.room_id = r.room_id
        WHERE pa.patient_id = %s
        ORDER BY pa.check_in_date DESC
    """, (session['user_id'],))
    admissions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('patient/admissions.html', admissions=admissions)
