from flask import Blueprint, request, session, flash, redirect, url_for, render_template
from utils.db import get_db_connection
from datetime import datetime

appointment_bp = Blueprint('appointments', __name__)

# ------------------------------
# Patient: Book Appointment
# ------------------------------
@appointment_bp.route('/book', methods=['POST'])
def book_appointment():
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
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
            VALUES (%s, %s, %s, NULL, %s, 'pending')
        """, (session['user_id'], doctor_id, appointment_date, reason or ''))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Appointment requested successfully! Admin will assign time.", "success")
        return redirect(url_for('patient.appointments'))

    except Exception as e:
        print(f"Error booking appointment: {e}")
        flash("Failed to request appointment", "danger")
        return redirect(url_for('patient.appointments'))

# ------------------------------
# Admin: Render all appointments page
# ------------------------------
@appointment_bp.route('/admin/appointments', methods=['GET'])
def admin_appointments_page():
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('auth.login'))

    appointments = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, u.full_name AS patient_name, d.full_name AS doctor_name, d.specialization
            FROM appointments a
            JOIN users u ON a.patient_id = u.user_id
            JOIN doctors d ON a.doctor_id = d.doctor_id
            ORDER BY a.appointment_date DESC, a.appointment_time ASC
        """)
        appointments = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error loading admin appointments page: {e}")
        flash("Failed to load appointments", "danger")

    return render_template('admin/appointments.html', appointments=appointments)

# ------------------------------
# Admin: Approve appointment (only for pending, assigns time)
# ------------------------------
@appointment_bp.route('/<int:appointment_id>/approve', methods=['POST'])
def approve_appointment(appointment_id):
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('auth.login'))

    appointment_time = request.form.get('appointment_time')
    remarks = request.form.get('remarks')

    if not appointment_time:
        flash("Time is required to approve", "danger")
        return redirect(url_for('appointments.admin_appointments_page'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM appointments WHERE appointment_id = %s", (appointment_id,))
        appt = cursor.fetchone()

        if not appt:
            flash("Appointment not found", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        if appt['status'] != 'pending':
            flash(f"Cannot approve: Appointment is {appt['status']}", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        datetime.strptime(appointment_time, '%H:%M')  # Validate time format

        cursor.execute("""
            UPDATE appointments
            SET status = 'approved',
                appointment_time = %s,
                remarks = %s
            WHERE appointment_id = %s
        """, (appointment_time, remarks or None, appointment_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Appointment approved and time assigned!", "success")
        return redirect(url_for('appointments.admin_appointments_page'))

    except Exception as e:
        print(f"Error approving appointment {appointment_id}: {e}")
        if 'conn' in locals():
            conn.close()
        flash(f"Failed to approve: {str(e)}", "danger")
        return redirect(url_for('appointments.admin_appointments_page'))

# ------------------------------
# Admin: Reject appointment (only for pending)
# ------------------------------
@appointment_bp.route('/<int:appointment_id>/reject', methods=['POST'])
def reject_appointment(appointment_id):
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('auth.login'))

    remarks = request.form.get('remarks')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM appointments WHERE appointment_id = %s", (appointment_id,))
        appt = cursor.fetchone()

        if not appt:
            flash("Appointment not found", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        if appt['status'] != 'pending':
            flash(f"Cannot reject: Appointment is {appt['status']}", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        cursor.execute("""
            UPDATE appointments
            SET status = 'rejected',
                remarks = %s
            WHERE appointment_id = %s
        """, (remarks or None, appointment_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Appointment rejected", "success")
        return redirect(url_for('appointments.admin_appointments_page'))

    except Exception as e:
        print(f"Error rejecting appointment {appointment_id}: {e}")
        if 'conn' in locals():
            conn.close()
        flash(f"Failed to reject: {str(e)}", "danger")
        return redirect(url_for('appointments.admin_appointments_page'))

# ------------------------------
# Admin: Complete appointment (only for approved)
# ------------------------------
@appointment_bp.route('/<int:appointment_id>/complete', methods=['POST'])
def complete_appointment(appointment_id):
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('auth.login'))

    remarks = request.form.get('remarks')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM appointments WHERE appointment_id = %s", (appointment_id,))
        appt = cursor.fetchone()

        if not appt:
            flash("Appointment not found", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        if appt['status'] != 'approved':
            flash(f"Cannot complete: Appointment is {appt['status']}", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        cursor.execute("""
            UPDATE appointments
            SET status = 'completed',
                remarks = %s
            WHERE appointment_id = %s
        """, (remarks or None, appointment_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Appointment marked as completed", "success")
        return redirect(url_for('appointments.admin_appointments_page'))

    except Exception as e:
        print(f"Error completing appointment {appointment_id}: {e}")
        if 'conn' in locals():
            conn.close()
        flash(f"Failed to complete: {str(e)}", "danger")
        return redirect(url_for('appointments.admin_appointments_page'))

# ------------------------------
# Admin: General Update (time/remarks only for approved)
# ------------------------------
@appointment_bp.route('/<int:appointment_id>/update', methods=['POST'])
def update_appointment(appointment_id):
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('auth.login'))

    appointment_time = request.form.get('appointment_time')
    remarks = request.form.get('remarks')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM appointments WHERE appointment_id = %s", (appointment_id,))
        appt = cursor.fetchone()

        if not appt:
            flash("Appointment not found", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        if appt['status'] != 'approved':
            flash(f"Cannot update: Appointment is {appt['status']}", "danger")
            conn.close()
            return redirect(url_for('appointments.admin_appointments_page'))

        if appointment_time:
            datetime.strptime(appointment_time, '%H:%M')  # Validate time format

        cursor.execute("""
            UPDATE appointments
            SET appointment_time = %s,
                remarks = %s
            WHERE appointment_id = %s
        """, (appointment_time or None, remarks or None, appointment_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Appointment updated successfully", "success")
        return redirect(url_for('appointments.admin_appointments_page'))

    except Exception as e:
        print(f"Error updating appointment {appointment_id}: {e}")
        if 'conn' in locals():
            conn.close()
        flash(f"Failed to update: {str(e)}", "danger")
        return redirect(url_for('appointments.admin_appointments_page'))