from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, render_template
from utils.db import get_db_connection
from datetime import datetime, date

billing_bp = Blueprint('bills', __name__, url_prefix='/bills')

@billing_bp.route('/generate/<int:admission_id>', methods=['POST'])
def generate_bill(admission_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get admission details including doctor fee
        cursor.execute("""
            SELECT pa.*, r.rate_per_day, u.user_id as patient_id, d.consultation_fee 
            FROM patient_admissions pa 
            JOIN rooms r ON pa.room_id = r.room_id 
            JOIN users u ON pa.patient_id = u.user_id 
            JOIN doctors d ON pa.doctor_id = d.doctor_id
            WHERE pa.admission_id = %s
        """, (admission_id,))
        admission = cursor.fetchone()
        if not admission:
            flash("Admission not found.", "danger")
            return redirect(request.referrer or url_for('admin.get_admissions'))

        patient_id = admission['patient_id']
        check_in_date = datetime.strptime(admission['check_in_date'], '%Y-%m-%d').date()
        check_out_date = admission.get('check_out_date')
        if check_out_date:
            check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d').date()
        else:
            check_out_date = date.today()  # For ongoing, use today

        # Calculate days
        days = (check_out_date - check_in_date).days + 1  # Inclusive
        if days < 1:
            days = 1

        room_charges = float(admission['rate_per_day']) * days

        # Doctor fee from doctors table
        doctor_fee = float(admission['consultation_fee']) or 0.00

        # Medicine charges from inventory_usage
        cursor.execute("""
            SELECT SUM(iu.quantity_used * i.unit_price) as total 
            FROM inventory_usage iu 
            JOIN inventory i ON iu.item_id = i.item_id 
            WHERE iu.patient_id = %s
        """, (patient_id,))
        medicine_result = cursor.fetchone()
        medicine_charges = medicine_result['total'] or 0.00

        # Insert bill
        cursor.execute("""
            INSERT INTO bills (patient_id, admission_id, room_charges, doctor_fee, medicine_charges) 
            VALUES (%s, %s, %s, %s, %s)
        """, (patient_id, admission_id, room_charges, doctor_fee, medicine_charges))

        conn.commit()
        cursor.close()
        conn.close()
        flash("Bill generated successfully!", "success")
    except Exception as e:
        print("Error generating bill:", e)
        flash("Failed to generate bill", "danger")
    return redirect(request.referrer or url_for('admin.get_admissions'))


@billing_bp.route('/<int:patient_id>', methods=['GET'])
def get_bills(patient_id):
    if 'user_id' not in session or (session.get('role') not in ['patient', 'admin']) or (session.get('role') == 'patient' and session['user_id'] != patient_id):
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, pa.check_in_date, pa.check_out_date, u.full_name as patient_name 
            FROM bills b 
            JOIN patient_admissions pa ON b.admission_id = pa.admission_id 
            JOIN users u ON b.patient_id = u.user_id
            WHERE b.patient_id = %s 
            ORDER BY b.generated_date DESC
        """, (patient_id,))
        bills = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('patient/bills.html', bills=bills)
    except Exception as e:
        print("Error loading bills:", e)
        flash("Failed to load bills", "danger")
        return render_template('patient/bills.html', bills=[])


@billing_bp.route('/details/<int:bill_id>', methods=['GET'])
def get_bill_details(bill_id):
    if 'user_id' not in session or session.get('role') not in ['patient', 'admin']:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, pa.check_in_date, pa.check_out_date, r.room_no, d.full_name as doctor_name 
            FROM bills b 
            JOIN patient_admissions pa ON b.admission_id = pa.admission_id 
            JOIN rooms r ON pa.room_id = r.room_id 
            JOIN doctors d ON pa.doctor_id = d.doctor_id 
            WHERE b.bill_id = %s AND (b.patient_id = %s OR %s = 'admin')
        """, (bill_id, session['user_id'] if session.get('role') == 'patient' else 0, session.get('role')))
        bill = cursor.fetchone()

        if not bill:
            return jsonify({"error": "Bill not found"}), 404

        # Get inventory usage details
        cursor.execute("""
            SELECT iu.quantity_used, i.item_name, i.unit_price, (iu.quantity_used * i.unit_price) as subtotal 
            FROM inventory_usage iu 
            JOIN inventory i ON iu.item_id = i.item_id 
            WHERE iu.patient_id = %s
        """, (bill['patient_id'],))
        usages = cursor.fetchall()

        bill['usages'] = usages
        cursor.close()
        conn.close()
        return jsonify(bill)
    except Exception as e:
        print("Error fetching bill details:", e)
        return jsonify({"error": "Failed to fetch bill details"}), 500