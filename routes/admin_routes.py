from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, render_template, send_file
from werkzeug.security import check_password_hash
from utils.db import get_db_connection
from datetime import datetime, date
import pdfkit
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# =========================
# Admin Login
# =========================
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE email = %s AND role = 'admin'", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['user_name'] = user['full_name']
                session['role'] = user['role']
                flash("Admin login successful", "success")
                return redirect(url_for('admin.dashboard'))
            else:
                flash("Invalid admin credentials", "danger")
                return redirect(url_for('admin.admin_login'))

        except Exception as e:
            print(f"Database Error: {e}")
            flash("Something went wrong. Please try again.", "danger")
            return redirect(url_for('admin.admin_login'))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('admin/login.html')

# =========================
# Admin Dashboard
# =========================
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.admin_login'))
    return redirect(url_for('reports.reports_dashboard'))

# =========================
# GET: Display all doctors
# =========================
@admin_bp.route('/doctors', methods=['GET'])
def get_doctors():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.admin_login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM doctors ORDER BY doctor_id DESC")
        doctors = cursor.fetchall()
        return render_template('admin/doctors.html', doctors=doctors)
    except Exception as e:
        print("Error loading doctors:", e)
        flash("Failed to load doctors", "danger")
        return render_template('admin/doctors.html', doctors=[])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================
# POST: Add new doctor
# =========================
@admin_bp.route('/add-doctor', methods=['POST'])
def add_doctor():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.get_doctors'))

    full_name = request.form.get('full_name')
    specialization = request.form.get('specialization')
    gender = request.form.get('gender')
    contact_no = request.form.get('contact_no')
    email = request.form.get('email')
    fee = request.form.get('consultation_fee', 0.0)

    if not all([full_name, specialization, gender, contact_no, email]):
        flash("All fields are required.", "warning")
        return redirect(url_for('admin.get_doctors'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO doctors (full_name, specialization, gender, contact_no, email, consultation_fee)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (full_name, specialization, gender, contact_no, email, float(fee)))
        conn.commit()
        flash("Doctor added successfully!", "success")
    except Exception as e:
        print("Error adding doctor:", e)
        flash("Failed to add doctor", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for('admin.get_doctors'))

# =========================
# Toggle Doctor Availability
# =========================
@admin_bp.route('/toggle-doctor/<int:id>', methods=['GET'])
def toggle_doctor(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.admin_login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT availability_status FROM doctors WHERE doctor_id = %s", (id,))
        doctor = cursor.fetchone()
        if doctor:
            new_status = 'available' if doctor.get('availability_status') == 'on_leave' else 'on_leave'
            cursor.execute("UPDATE doctors SET availability_status = %s, updated_at = NOW() WHERE doctor_id = %s", (new_status, id))
            conn.commit()
            flash(f"Doctor status toggled to {new_status}!", "success")
        else:
            flash("Doctor not found.", "danger")
    except Exception as e:
        print("Error toggling doctor:", e)
        flash("Failed to toggle doctor status", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for('admin.get_doctors'))

# =========================
# DELETE Doctor
# =========================
@admin_bp.route('/delete-doctor/<int:id>', methods=['GET'])
def delete_doctor(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.admin_login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM doctors WHERE doctor_id = %s", (id,))
        conn.commit()
        if cursor.rowcount > 0:
            flash("Doctor deleted successfully!", "success")
        else:
            flash("Doctor not found.", "danger")
    except Exception as e:
        print("Error deleting doctor:", e)
        flash("Failed to delete doctor", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for('admin.get_doctors'))

# =========================
# Patients Management
# =========================
@admin_bp.route('/patients', methods=['GET'])
def get_patients():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.admin_login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT user_id, full_name, gender, dob, email, contact_no, address, city, state, postal_code 
            FROM users 
            WHERE role = 'patient' 
            ORDER BY full_name ASC
        """)
        patients = cursor.fetchall()
        return render_template('admin/patients.html', patients=patients)
    except Exception as e:
        print("Error loading patients:", e)
        flash("Failed to load patients", "danger")
        return render_template('admin/patients.html', patients=[])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================
# Admissions CRUD
# =========================
@admin_bp.route('/admissions', methods=['GET', 'POST'])
def get_admissions():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Handle POST actions
    if request.method == 'POST':
        action = request.form.get('_action')
        if action == 'create':
            patient_id = request.form.get('patient_id')
            doctor_id = request.form.get('doctor_id')
            room_id = request.form.get('room_id')
            check_in = request.form.get('check_in_date')
            notes = request.form.get('notes')

            cursor.execute("""
                INSERT INTO patient_admissions (patient_id, doctor_id, room_id, check_in_date, status, notes)
                VALUES (%s, %s, %s, %s, 'admitted', %s)
            """, (patient_id, doctor_id, room_id, check_in, notes))
            cursor.execute("UPDATE rooms SET status = 'occupied' WHERE room_id = %s", (room_id,))
            conn.commit()
            flash("Admission created successfully!", "success")
            return redirect(url_for('admin.get_admissions'))

        elif action == 'update':
            admission_id = request.form.get('admission_id')
            check_out = request.form.get('check_out_date') or None
            status = request.form.get('status')
            notes = request.form.get('notes')

            cursor.execute("""
                UPDATE patient_admissions
                SET check_out_date = %s, status = %s, notes = %s, updated_at = NOW()
                WHERE admission_id = %s
            """, (check_out, status, notes, admission_id))

            # Generate bill automatically on discharge
            if status == 'discharged' and check_out:
                # Check if bill already exists
                cursor.execute("SELECT bill_id FROM bills WHERE admission_id = %s", (admission_id,))
                if cursor.fetchone():
                    flash("Bill already exists for this admission.", "warning")
                else:
                    # Fetch admission details
                    cursor.execute("""
                        SELECT pa.*, u.full_name AS patient_name, d.full_name AS doctor_name, 
                               d.consultation_fee, r.rate_per_day
                        FROM patient_admissions pa
                        JOIN users u ON pa.patient_id = u.user_id
                        JOIN doctors d ON pa.doctor_id = d.doctor_id
                        JOIN rooms r ON pa.room_id = r.room_id
                        WHERE pa.admission_id = %s
                    """, (admission_id,))
                    admission = cursor.fetchone()

                    # Calculate charges
                    check_in = admission['check_in_date'] if isinstance(admission['check_in_date'], date) else datetime.strptime(admission['check_in_date'], '%Y-%m-%d').date()
                    check_out = datetime.strptime(check_out, '%Y-%m-%d').date()

                    # Validate check-out date
                    if check_out < check_in:
                        flash("Check-out date cannot be before check-in date.", "danger")
                        conn.rollback()
                        cursor.close()
                        conn.close()
                        return redirect(url_for('admin.get_admissions'))

                    days = (check_out - check_in).days or 1
                    room_charges = admission['rate_per_day'] * days
                    doctor_fee = admission['consultation_fee']

                    # Fetch inventory usage
                    cursor.execute("""
                        SELECT iu.quantity_used, i.unit_price, i.item_name
                        FROM inventory_usage iu
                        JOIN inventory i ON iu.item_id = i.item_id
                        WHERE iu.admission_id = %s
                    """, (admission_id,))
                    inventory_usage = cursor.fetchall()
                    medicine_charges = sum(item['quantity_used'] * item['unit_price'] for item in inventory_usage)

                    total_amount = room_charges + doctor_fee + medicine_charges

                    # Insert bill
                    cursor.execute("""
                        INSERT INTO bills (admission_id, patient_id, room_charges, doctor_fee, medicine_charges, generated_date)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (admission_id, admission['patient_id'], room_charges, doctor_fee, medicine_charges, datetime.now()))

                    # Update room status
                    cursor.execute("UPDATE rooms SET status = 'available' WHERE room_id = %s", (admission['room_id'],))

                conn.commit()
                flash("Admission updated and bill generated successfully!", "success")
            else:
                conn.commit()
                flash("Admission updated successfully!", "success")
            return redirect(url_for('admin.get_admissions'))

        elif action == 'delete':
            admission_id = request.form.get('admission_id')
            cursor.execute("SELECT room_id FROM patient_admissions WHERE admission_id = %s", (admission_id,))
            room = cursor.fetchone()
            if room:
                cursor.execute("UPDATE rooms SET status = 'available' WHERE room_id = %s", (room['room_id'],))
            cursor.execute("DELETE FROM patient_admissions WHERE admission_id = %s", (admission_id,))
            conn.commit()
            flash("Admission deleted successfully!", "success")
            return redirect(url_for('admin.get_admissions'))

    # GET: load all admissions
    cursor.execute("""
        SELECT pa.*, u.full_name as patient_name, d.full_name as doctor_name, r.room_no
        FROM patient_admissions pa
        JOIN users u ON pa.patient_id = u.user_id
        JOIN doctors d ON pa.doctor_id = d.doctor_id
        JOIN rooms r ON pa.room_id = r.room_id
        ORDER BY pa.check_in_date DESC
    """)
    admissions = cursor.fetchall()

    # Get inventory items for assignment modal
    cursor.execute("SELECT * FROM inventory ORDER BY item_name ASC")
    inventory_items = cursor.fetchall()

    # Get patients, doctors, and rooms for create modal
    cursor.execute("SELECT user_id, full_name FROM users WHERE role = 'patient'")
    patients = cursor.fetchall()
    cursor.execute("SELECT doctor_id, full_name FROM doctors")
    doctors = cursor.fetchall()
    cursor.execute("SELECT room_id, room_no, status FROM rooms ORDER BY room_no ASC")
    rooms = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin/admissions.html', admissions=admissions,
                           inventory=inventory_items, patients=patients,
                           doctors=doctors, rooms=rooms, today=date.today().isoformat())

# ------------------- Inventory Assignment -------------------
@admin_bp.route('/admissions/assign_inventory', methods=['POST'])
def assign_inventory():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('admin.admin_login'))

    admission_id = request.form.get('admission_id')
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity_used', 0))

    if not all([admission_id, item_id, quantity]):
        flash("All fields are required!", "warning")
        return redirect(request.referrer or url_for('admin.get_admissions'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get patient_id for this admission
    cursor.execute("SELECT patient_id FROM patient_admissions WHERE admission_id = %s", (admission_id,))
    result = cursor.fetchone()
    if not result:
        flash("Admission not found!", "danger")
        cursor.close()
        conn.close()
        return redirect(request.referrer or url_for('admin.get_admissions'))
    patient_id = result['patient_id']

    # Check inventory stock
    cursor.execute("SELECT quantity, unit_price FROM inventory WHERE item_id = %s", (item_id,))
    inv = cursor.fetchone()
    if not inv or inv['quantity'] < quantity:
        flash("Insufficient inventory quantity!", "danger")
        cursor.close()
        conn.close()
        return redirect(request.referrer or url_for('admin.get_admissions'))

    # Insert into inventory_usage
    cursor.execute("""
        INSERT INTO inventory_usage (patient_id, admission_id, item_id, quantity_used, usage_date)
        VALUES (%s, %s, %s, %s, CURDATE())
    """, (patient_id, admission_id, item_id, quantity))

    # Update inventory quantity
    cursor.execute("UPDATE inventory SET quantity = quantity - %s WHERE item_id = %s", (quantity, item_id))

    # ---------------- Auto-update medicine_charges in bills if bill exists ----------------
    cursor.execute("SELECT bill_id FROM bills WHERE admission_id = %s", (admission_id,))
    bill_exists = cursor.fetchone()
    if bill_exists:
        # Calculate new medicine_charges
        cursor.execute("""
            SELECT SUM(iu.quantity_used * i.unit_price) AS total_medicine
            FROM inventory_usage iu
            JOIN inventory i ON iu.item_id = i.item_id
            WHERE iu.admission_id = %s
        """, (admission_id,))
        medicine_total = cursor.fetchone()['total_medicine'] or 0
        # cursor.execute("UPDATE bills SET medicine_charges = %s, updated_at = NOW() WHERE admission_id = %s",
        #                (medicine_total, admission_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Inventory assigned successfully!", "success")
    return redirect(request.referrer or url_for('admin.get_admissions'))

# ------------------- View Bill (HTML) -------------------
@admin_bp.route('/bills/view/<int:admission_id>', methods=['GET'])
def view_bill(admission_id):
    if 'user_id' not in session or (session.get('role') not in ['admin', 'patient']):
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch bill details
    cursor.execute("""
        SELECT b.*, pa.check_in_date, pa.check_out_date, pa.patient_id, u.full_name as patient_name,
               d.full_name as doctor_name, r.room_no
        FROM bills b
        JOIN patient_admissions pa ON b.admission_id = pa.admission_id
        JOIN users u ON b.patient_id = u.user_id
        JOIN doctors d ON pa.doctor_id = d.doctor_id
        JOIN rooms r ON pa.room_id = r.room_id
        WHERE b.admission_id = %s
    """, (admission_id,))
    bill = cursor.fetchone()

    if not bill:
        flash("Bill not found. Ensure the admission is discharged.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('admin.get_admissions'))

    # Restrict patients to their own bills
    if session.get('role') == 'patient' and bill['patient_id'] != session.get('user_id'):
        flash("You can only view your own bills.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('auth.login'))

    # Fetch inventory usage
    cursor.execute("""
        SELECT iu.quantity_used, i.unit_price, i.item_name, (iu.quantity_used * i.unit_price) AS subtotal
        FROM inventory_usage iu
        JOIN inventory i ON iu.item_id = i.item_id
        WHERE iu.admission_id = %s
    """, (admission_id,))
    inventory_usage = cursor.fetchall()

    # Auto-calculate total for display (ensures HTML and PDF match)
    total_inventory = sum(item['subtotal'] for item in inventory_usage)
    bill['medicine_charges'] = total_inventory
    bill['total_amount'] = bill['room_charges'] + bill['doctor_fee'] + total_inventory

    cursor.close()
    conn.close()

    return render_template('admin/view_bill.html', bill=bill, inventory_usage=inventory_usage)
# download
@admin_bp.route('/bills/download/<int:admission_id>', methods=['GET'])
def download_bill(admission_id):
    if 'user_id' not in session or (session.get('role') not in ['admin', 'patient']):
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch bill details
    cursor.execute("""
        SELECT b.*, pa.check_in_date, pa.check_out_date, pa.patient_id, u.full_name as patient_name,
               d.full_name as doctor_name, r.room_no
        FROM bills b
        JOIN patient_admissions pa ON b.admission_id = pa.admission_id
        JOIN users u ON b.patient_id = u.user_id
        JOIN doctors d ON pa.doctor_id = d.doctor_id
        JOIN rooms r ON pa.room_id = r.room_id
        WHERE b.admission_id = %s
    """, (admission_id,))
    bill = cursor.fetchone()

    if not bill:
        flash("Bill not found. Ensure the admission is discharged.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('admin.get_admissions'))

    # Restrict patients to their own bills
    if session.get('role') == 'patient' and bill['patient_id'] != session.get('user_id'):
        flash("You can only view your own bills.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('auth.login'))

    # Fetch inventory usage
    cursor.execute("""
        SELECT iu.quantity_used, i.unit_price, i.item_name
        FROM inventory_usage iu
        JOIN inventory i ON iu.item_id = i.item_id
        WHERE iu.admission_id = %s
    """, (admission_id,))
    inventory_usage = cursor.fetchall()

    cursor.close()
    conn.close()

    # Render bill as HTML for PDF
    try:
        html = render_template('admin/bill_pdf.html', bill=bill, inventory_usage=inventory_usage)
        
        # Configure pdfkit with wkhtmltopdf path (adjust if needed)
        config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')  # Update path for your system
        pdf = pdfkit.from_string(html, False, configuration=config, options={'page-size': 'A4', 'encoding': 'UTF-8'})

        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"bill_{bill['bill_id']}_{bill['patient_name'].replace(' ', '_')}.pdf"
        )
    except Exception as e:
        flash(f"Failed to generate bill PDF: {str(e)}", "danger")
        return redirect(url_for('admin.get_admissions'))