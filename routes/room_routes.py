from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template, session
from utils.db import get_db_connection

room_bp = Blueprint('rooms', __name__)

# =====================================================
# MANAGE ROOMS (Single Route for Admin: View, Add, Update, Delete, Status Change)
# =====================================================
@room_bp.route('/', methods=['GET', 'POST'])
def admin_rooms():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        _action = request.form.get('_action')
        room_id = request.form.get('room_id')
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if _action == 'add':
                room_no = request.form['room_no']
                room_type = request.form['room_type']
                rate_per_day = request.form['rate_per_day']

                if not room_no:
                    flash("Room number is required.", "warning")
                else:
                    cursor.execute("SELECT room_id FROM rooms WHERE room_no = %s", (room_no,))
                    if cursor.fetchone():
                        flash("Room number already exists.", "warning")
                    else:
                        cursor.execute(
                            "INSERT INTO rooms (room_no, room_type, rate_per_day) VALUES (%s, %s, %s)",
                            (room_no, room_type, rate_per_day)
                        )
                        conn.commit()
                        flash("Room added successfully!", "success")

            elif _action == 'update':
                if not room_id:
                    flash("Room ID is required.", "danger")
                else:
                    room_no = request.form['room_no']
                    room_type = request.form['room_type']
                    rate_per_day = request.form['rate_per_day']
                    status = request.form['status']

                    # Check if room exists and get old room_no
                    cursor.execute("SELECT room_no FROM rooms WHERE room_id = %s", (room_id,))
                    old_data = cursor.fetchone()
                    if not old_data:
                        flash("Room not found.", "danger")
                    else:
                        old_room_no = old_data[0]
                        if old_room_no != room_no:
                            cursor.execute("SELECT room_id FROM rooms WHERE room_no = %s AND room_id != %s", (room_no, room_id))
                            if cursor.fetchone():
                                flash("Room number already exists.", "warning")
                            else:
                                cursor.execute(
                                    "UPDATE rooms SET room_no = %s, room_type = %s, rate_per_day = %s, status = %s, updated_at = NOW() WHERE room_id = %s",
                                    (room_no, room_type, rate_per_day, status, room_id)
                                )
                                conn.commit()
                                flash("Room updated successfully!", "success")
                        else:
                            cursor.execute(
                                "UPDATE rooms SET room_no = %s, room_type = %s, rate_per_day = %s, status = %s, updated_at = NOW() WHERE room_id = %s",
                                (room_no, room_type, rate_per_day, status, room_id)
                            )
                            conn.commit()
                            flash("Room updated successfully!", "success")

            elif _action == 'delete':
                if not room_id:
                    flash("Room ID is required.", "danger")
                else:
                    cursor.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
                    conn.commit()
                    if cursor.rowcount > 0:
                        flash("Room deleted successfully!", "success")
                    else:
                        flash("Room not found.", "danger")

            elif _action == 'status':
                new_status = request.form.get('new_status')
                if not room_id or not new_status:
                    flash("Invalid status change request.", "danger")
                else:
                    cursor.execute(
                        "UPDATE rooms SET status = %s, updated_at = NOW() WHERE room_id = %s",
                        (new_status, room_id)
                    )
                    conn.commit()
                    if cursor.rowcount > 0:
                        flash(f"Status changed to {new_status} successfully!", "success")
                    else:
                        flash("Room not found.", "danger")

            else:
                flash("Invalid action.", "danger")

        except Exception as e:
            print(f"Database Error: {str(e)}")
            flash("Something went wrong.", "danger")
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
        return redirect(url_for('rooms.admin_rooms'))

    # GET: Fetch and render rooms
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rooms ORDER BY room_no ASC")
        rooms = cursor.fetchall()
    except Exception as e:
        print(f"Database Error: {str(e)}")
        flash("Something went wrong while fetching rooms.", "danger")
        rooms = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('admin/rooms.html', rooms=rooms)


# =====================================================
# AVAILABLE ROOMS (for patients/admins)
# =====================================================
@room_bp.route('/available', methods=['GET'])
def available_rooms():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rooms WHERE status = 'available'")
        rooms = cursor.fetchall()
        return render_template('available_rooms.html', rooms=rooms)
    except Exception as e:
        print(f"Database Error: {str(e)}")
        flash("Something went wrong while fetching rooms.", "danger")
        return redirect(url_for('patient.dashboard'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# =====================================================
# ALLOCATE ROOM (Admin only)
# =====================================================
@room_bp.route('/allocate', methods=['POST'])
def allocate_room():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    room_id = data.get('room_id')
    admission_id = data.get('admission_id')

    if not room_id or not admission_id:
        return jsonify({"error": "room_id and admission_id are required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE rooms SET status = 'occupied' WHERE room_id = %s", (room_id,))
        cursor.execute("UPDATE admissions SET room_id = %s WHERE admission_id = %s", (room_id, admission_id))
        conn.commit()

        return jsonify({"message": "Room allocated successfully!"}), 200
    except Exception as e:
        print(f"Database Error: {str(e)}")
        return jsonify({"error": "Something went wrong"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()