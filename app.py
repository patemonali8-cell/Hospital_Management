from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import get_db_connection  # Assuming this is set up correctly

app = Flask(__name__)
app.secret_key = "hospital_management" 

# Import blueprints
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.patient_routes import patient_bp
from routes.appointment_routes import appointment_bp
from routes.room_routes import room_bp
from routes.inventory_routes import inventory_bp
from routes.billing_routes import billing_bp
from routes.report_routes import report_bp
from routes.chat_routes import chat_bp

# Register blueprints with appropriate prefixes
app.register_blueprint(auth_bp)  # For /login, /register, /logout
app.register_blueprint(admin_bp, url_prefix='/admin')  # For /admin/dashboard, /admin/patients
app.register_blueprint(patient_bp, url_prefix='/patient')  # For /patient/dashboard
app.register_blueprint(appointment_bp)  # Adjust if routes need a prefix
app.register_blueprint(room_bp, url_prefix='/rooms')  # For /rooms/available
app.register_blueprint(inventory_bp, url_prefix='/inventory')  # For /inventory/add
app.register_blueprint(billing_bp, url_prefix='/bills')  # For /bills/generate/<id>
app.register_blueprint(report_bp, url_prefix='/reports')  # For /reports/overview
app.register_blueprint(chat_bp, url_prefix='/chat')  # For /reports/overview
# Root route
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))
    return render_template('index.html')

# Debug route to clear session
@app.route('/clear_session')
def clear_session():
    session.clear()
    flash("✅ Session cleared", "success")
    return redirect(url_for('auth.login'))

# Debug route to check template folder
@app.route('/debug_templates')
def debug_templates():
    import os
    template_dir = app.jinja_loader.searchpath[0] if app.jinja_loader else app.template_folder
    templates = os.listdir(template_dir)
    patient_templates = os.listdir(os.path.join(template_dir, 'patient')) if os.path.exists(os.path.join(template_dir, 'patient')) else []
    return f"Template folder: {template_dir}<br>All templates: {templates}<br>Patient templates: {patient_templates}"

if __name__ == '__main__':
    app.run(debug=True)