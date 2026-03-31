from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        full_name = f"{first_name} {last_name}"
        gender = request.form['gender']
        dob = request.form['dob']
        email = request.form['email']
        contact_no = request.form['contact_no']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        postal_code = request.form['postal_code']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('auth.register'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered. Please login.", "warning")
                return redirect(url_for('auth.login'))

            hashed_password = generate_password_hash(password)
            insert_query = """
                INSERT INTO users 
                (full_name, gender, dob, email, password_hash, role, contact_no, address, city, state, postal_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                full_name, gender, dob, email, hashed_password, 'patient',
                contact_no, address, city, state, postal_code
            ))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"Database Error: {str(e)}")  # Improved error logging
            flash("Something went wrong.", "danger")
            return redirect(url_for('auth.register'))

        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print(f"DEBUG: Login attempt with email: {email}")  # Debug

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s AND role = 'patient'", (email,))
            user = cursor.fetchone()
            print(f"DEBUG: User fetched: {user}")  # Debug

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['user_name'] = user['full_name']
                session['role'] = user['role']
                print(f"DEBUG: Session set: {session}")  # Debug
                print(f"DEBUG: Redirecting to: {url_for('patient.dashboard')}")  # Debug
                flash("Login successful!", "success")
                return redirect(url_for('patient.dashboard'))
            else:
                print("DEBUG: Invalid email or password")
                flash("Invalid email or password", "danger")
                return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"DEBUG: Database Error: {str(e)}")  # Debug
            flash("Something went wrong", "danger")
            return redirect(url_for('auth.login'))

        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    return render_template('login.html')

@auth_bp.route('/logout', methods=['GET'])
def logout():
    role = session.get('role')
    session.clear()
    flash("You have been logged out", "success")
    if role == 'admin':
        return redirect(url_for('admin.admin_login'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            return render_template('profile.html', user=user)
        else:
            flash("User not found", "danger")
            return redirect(url_for('auth.login'))
    except Exception as e:
        print(f"Database Error: {str(e)}")
        flash("Something went wrong", "danger")
        return redirect(url_for('auth.login'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@auth_bp.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_query = """
            UPDATE users SET full_name = %s, contact_no = %s, address = %s, city = %s, state = %s, postal_code = %s
            WHERE user_id = %s
        """
        cursor.execute(update_query, (
            data.get('full_name'), data.get('contact_no'), data.get('address'),
            data.get('city'), data.get('state'), data.get('postal_code'), user_id
        ))
        conn.commit()
        flash("Profile updated successfully", "success")
        return jsonify({"message": "Profile updated"}), 200
    except Exception as e:
        print(f"Database Error: {str(e)}")
        return jsonify({"error": "Something went wrong"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()