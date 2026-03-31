# inventory.py
from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, render_template
from utils.db import get_db_connection

inventory_bp = Blueprint('inventory', __name__, url_prefix='/admin/inventory')

@inventory_bp.route('/add', methods=['POST'])
def add_inventory():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    item_name = request.form.get('item_name')
    category = request.form.get('category')
    quantity = request.form.get('quantity', 0)
    unit_price = request.form.get('unit_price', 0.00)
    reorder_level = request.form.get('reorder_level', 10)

    if not item_name:
        flash("Item name is required.", "warning")
        return redirect(url_for('inventory.get_inventory'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory (item_name, category, quantity, unit_price, reorder_level) 
            VALUES (%s, %s, %s, %s, %s)
        """, (item_name, category, int(quantity), float(unit_price), int(reorder_level)))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Inventory item added successfully!", "success")
    except Exception as e:
        print("Error adding inventory:", e)
        flash("Failed to add inventory item", "danger")
    return redirect(url_for('inventory.get_inventory'))


@inventory_bp.route('/', methods=['GET'])
def get_inventory():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventory ORDER BY item_name ASC")
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/inventory.html', items=items)
    except Exception as e:
        print("Error loading inventory:", e)
        flash("Failed to load inventory", "danger")
        return render_template('admin/inventory.html', items=[])


@inventory_bp.route('/update/<int:id>', methods=['POST'])
def update_inventory(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    item_name = request.form.get('item_name')
    category = request.form.get('category')
    quantity = request.form.get('quantity', 0)
    unit_price = request.form.get('unit_price', 0.00)
    reorder_level = request.form.get('reorder_level', 10)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE inventory 
            SET item_name = %s, category = %s, quantity = %s, unit_price = %s, reorder_level = %s, updated_at = NOW() 
            WHERE item_id = %s
        """, (item_name, category, int(quantity), float(unit_price), int(reorder_level), id))
        conn.commit()
        if cursor.rowcount > 0:
            flash("Inventory item updated successfully!", "success")
        else:
            flash("Item not found.", "danger")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error updating inventory:", e)
        flash("Failed to update inventory item", "danger")
    return redirect(url_for('inventory.get_inventory'))


@inventory_bp.route('/delete/<int:id>', methods=['POST'])
def delete_inventory(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE item_id = %s", (id,))
        conn.commit()
        if cursor.rowcount > 0:
            flash("Inventory item deleted successfully!", "success")
        else:
            flash("Item not found.", "danger")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error deleting inventory:", e)
        flash("Failed to delete inventory item", "danger")
    return redirect(url_for('inventory.get_inventory'))


@inventory_bp.route('/orders/create', methods=['POST'])
def create_order():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    item_id = request.form.get('item_id')
    order_type = request.form.get('order_type')  # 'INCOMING' or 'OUTGOING'
    quantity = request.form.get('quantity')
    remarks = request.form.get('remarks')

    if not all([item_id, order_type, quantity]):
        flash("Item ID, order type, and quantity are required.", "warning")
        return redirect(url_for('inventory.get_orders'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (item_id, ordered_by, order_type, quantity, remarks) 
            VALUES (%s, %s, %s, %s, %s)
        """, (item_id, session['user_id'], order_type, int(quantity), remarks))
        # Trigger will handle inventory update and notifications
        conn.commit()
        cursor.close()
        conn.close()
        flash("Order created successfully! Inventory updated automatically.", "success")
    except Exception as e:
        print("Error creating order:", e)
        flash("Failed to create order", "danger")
    return redirect(url_for('inventory.get_orders'))


@inventory_bp.route('/orders', methods=['GET'])
def get_orders():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.*, i.item_name, u.full_name as ordered_by_name 
            FROM orders o 
            JOIN inventory i ON o.item_id = i.item_id 
            LEFT JOIN users u ON o.ordered_by = u.user_id 
            ORDER BY o.order_date DESC
        """)
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/orders.html', orders=orders)
    except Exception as e:
        print("Error loading orders:", e)
        flash("Failed to load orders", "danger")
        return render_template('admin/orders.html', orders=[])


@inventory_bp.route('/assign', methods=['POST'])
def assign_to_admission():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    admission_id = request.form.get('admission_id')
    item_id = request.form.get('item_id')
    quantity_used = request.form.get('quantity_used')

    if not all([admission_id, item_id, quantity_used]):
        flash("Admission ID, item ID, and quantity are required.", "warning")
        return redirect(request.referrer or url_for('admin.get_admissions'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get patient_id from admission
        cursor.execute("SELECT patient_id FROM patient_admissions WHERE admission_id = %s", (admission_id,))
        result = cursor.fetchone()
        if not result:
            flash("Admission not found.", "danger")
            return redirect(request.referrer or url_for('admin.get_admissions'))
        patient_id = result[0]

        # Check inventory quantity
        cursor.execute("SELECT quantity FROM inventory WHERE item_id = %s", (item_id,))
        result = cursor.fetchone()
        if not result or result[0] < int(quantity_used):
            flash("Insufficient inventory quantity.", "danger")
            return redirect(request.referrer or url_for('admin.get_admissions'))

        # Insert usage
        cursor.execute("""
            INSERT INTO inventory_usage (patient_id, item_id, quantity_used) 
            VALUES (%s, %s, %s)
        """, (patient_id, item_id, int(quantity_used)))

        # Deduct from inventory (manual, as it's usage, not order)
        cursor.execute("UPDATE inventory SET quantity = quantity - %s, updated_at = NOW() WHERE item_id = %s", (int(quantity_used), item_id))

        conn.commit()
        cursor.close()
        conn.close()
        flash("Inventory assigned to admission successfully!", "success")
    except Exception as e:
        print("Error assigning inventory:", e)
        flash("Failed to assign inventory", "danger")
    return redirect(request.referrer or url_for('admin.get_admissions'))