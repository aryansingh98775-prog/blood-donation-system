import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, init_db
from auth import (
    login_required, admin_required, get_current_user,
    check_eligibility, COMPATIBILITY_MATRIX
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'blood-donation-secure-secret-key-2026-xyz')

# Inject current user and compatibility matrix into all templates
@app.context_processor
def inject_global_data():
    user = get_current_user()
    return {
        'current_user': user,
        'COMPATIBILITY_MATRIX': COMPATIBILITY_MATRIX,
        'current_year': datetime.now().year
    }

# -------------------------------------------------------------
# Public & Landing Routes
# -------------------------------------------------------------

@app.route('/')
def index():
    conn = get_db_connection()
    # Stats
    total_donors = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'donor'").fetchone()[0]
    total_requests = conn.execute("SELECT COUNT(*) FROM blood_requests").fetchone()[0]
    active_requests = conn.execute("SELECT COUNT(*) FROM blood_requests WHERE status IN ('Pending', 'Approved')").fetchone()[0]
    total_units = conn.execute("SELECT SUM(units_available) FROM blood_inventory").fetchone()[0] or 0
    total_completed = conn.execute("SELECT COUNT(*) FROM donation_appointments WHERE status = 'Completed'").fetchone()[0]

    # Inventory overview
    inventory = conn.execute("SELECT * FROM blood_inventory ORDER BY blood_group ASC").fetchall()

    # Recent urgent requests
    urgent_requests = conn.execute('''
        SELECT * FROM blood_requests 
        WHERE status IN ('Pending', 'Approved')
        ORDER BY CASE urgency WHEN 'Immediate' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC 
        LIMIT 4
    ''').fetchall()

    # Available donors preview
    recent_donors = conn.execute('''
        SELECT full_name, blood_group, city, is_available 
        FROM users 
        WHERE role = 'donor' AND is_available = 1 
        ORDER BY created_at DESC 
        LIMIT 6
    ''').fetchall()

    conn.close()

    return render_template(
        'index.html',
        total_donors=total_donors,
        total_requests=total_requests,
        active_requests=active_requests,
        total_units=total_units,
        lives_saved=total_completed * 3, # 1 blood unit can save up to 3 lives
        inventory=inventory,
        urgent_requests=urgent_requests,
        recent_donors=recent_donors
    )

# -------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'donor') # 'donor' or 'recipient'
        blood_group = request.form.get('blood_group', '')
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        age = request.form.get('age')
        gender = request.form.get('gender', 'Other')
        weight = request.form.get('weight')
        last_donation_date = request.form.get('last_donation_date', '').strip()

        # Validation
        if not full_name or not email or not password or not phone or not city:
            flash('All primary fields (Name, Email, Password, Phone, City) are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('An account with this email address already exists. Please sign in.', 'warning')
            return redirect(url_for('login'))

        age_val = int(age) if age and age.isdigit() else None
        weight_val = float(weight) if weight else None
        last_don_val = last_donation_date if last_donation_date else None

        password_hash = generate_password_hash(password)
        conn.execute('''
            INSERT INTO users (full_name, email, password_hash, role, blood_group, phone, city, age, gender, weight, is_available, last_donation_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ''', (full_name, email, password_hash, role, blood_group, phone, city, age_val, gender, weight_val, last_don_val))

        # Log activity
        conn.execute('''
            INSERT INTO activity_logs (action_type, description)
            VALUES (?, ?)
        ''', ('USER_REGISTERED', f"New {role.capitalize()} registered: {full_name} ({blood_group}) in {city}."))

        conn.commit()
        conn.close()

        flash('Registration successful! Please sign in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['role'] = user['role']
            session['blood_group'] = user['blood_group']

            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# -------------------------------------------------------------
# Role-Based Routing & Dashboards
# -------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'donor':
        return redirect(url_for('donor_dashboard'))
    elif role == 'recipient':
        return redirect(url_for('recipient_dashboard'))
    return redirect(url_for('index'))

@app.route('/donor/dashboard')
@login_required
def donor_dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    eligibility = check_eligibility(user)

    conn = get_db_connection()
    # Donor's appointments
    appointments = conn.execute('''
        SELECT * FROM donation_appointments 
        WHERE donor_id = ? 
        ORDER BY appointment_date DESC, created_at DESC
    ''', (user['id'],)).fetchall()

    # Compatible urgent requests for this donor's blood group
    compatible_groups = COMPATIBILITY_MATRIX.get(user['blood_group'], {}).get('can_donate_to', [user['blood_group']])
    placeholders = ','.join(['?'] * len(compatible_groups))
    
    matching_requests = conn.execute(f'''
        SELECT * FROM blood_requests 
        WHERE blood_group IN ({placeholders}) AND status IN ('Pending', 'Approved')
        ORDER BY created_at DESC 
        LIMIT 5
    ''', compatible_groups).fetchall()

    conn.close()

    return render_template(
        'donor_dashboard.html',
        user=user,
        eligibility=eligibility,
        appointments=appointments,
        matching_requests=matching_requests
    )

@app.route('/donor/toggle-availability', methods=['POST'])
@login_required
def toggle_donor_availability():
    user = get_current_user()
    new_status = 0 if user['is_available'] == 1 else 1

    conn = get_db_connection()
    conn.execute('UPDATE users SET is_available = ? WHERE id = ?', (new_status, user['id']))
    conn.commit()
    conn.close()

    status_str = "Available" if new_status == 1 else "Unavailable"
    flash(f"Your donation status has been updated to '{status_str}'.", 'success')
    return redirect(url_for('donor_dashboard'))

@app.route('/recipient/dashboard')
@login_required
def recipient_dashboard():
    user = get_current_user()
    conn = get_db_connection()
    # Blood requests created by this user
    my_requests = conn.execute('''
        SELECT * FROM blood_requests 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user['id'],)).fetchall()

    # Compatible blood groups they can receive
    compatible_donors = COMPATIBILITY_MATRIX.get(user['blood_group'], {}).get('can_receive_from', [user['blood_group']])
    placeholders = ','.join(['?'] * len(compatible_donors))
    
    matching_donors = conn.execute(f'''
        SELECT id, full_name, blood_group, city, phone, is_available 
        FROM users 
        WHERE role = 'donor' AND is_available = 1 AND blood_group IN ({placeholders})
        LIMIT 6
    ''', compatible_donors).fetchall()

    conn.close()

    return render_template(
        'recipient_dashboard.html',
        user=user,
        my_requests=my_requests,
        matching_donors=matching_donors
    )

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    # Stats
    total_donors = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'donor'").fetchone()[0]
    total_recipients = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'recipient'").fetchone()[0]
    pending_requests = conn.execute("SELECT COUNT(*) FROM blood_requests WHERE status = 'Pending'").fetchone()[0]
    total_units = conn.execute("SELECT SUM(units_available) FROM blood_inventory").fetchone()[0] or 0

    # Blood Inventory
    inventory = conn.execute("SELECT * FROM blood_inventory ORDER BY blood_group ASC").fetchall()

    # All Requests
    all_requests = conn.execute('''
        SELECT r.*, u.full_name as requester_name 
        FROM blood_requests r 
        LEFT JOIN users u ON r.user_id = u.id 
        ORDER BY r.created_at DESC
    ''').fetchall()

    # All Appointments
    all_appointments = conn.execute('''
        SELECT a.*, u.full_name as donor_name, u.blood_group, u.phone 
        FROM donation_appointments a 
        JOIN users u ON a.donor_id = u.id 
        ORDER BY a.created_at DESC
    ''').fetchall()

    # Activity Logs
    logs = conn.execute("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 15").fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_donors=total_donors,
        total_recipients=total_recipients,
        pending_requests=pending_requests,
        total_units=total_units,
        inventory=inventory,
        all_requests=all_requests,
        all_appointments=all_appointments,
        logs=logs
    )

# -------------------------------------------------------------
# Blood Requests Management
# -------------------------------------------------------------

@app.route('/requests')
def list_requests():
    bg_filter = request.args.get('blood_group', '').strip()
    city_filter = request.args.get('city', '').strip()
    status_filter = request.args.get('status', '').strip()

    conn = get_db_connection()
    query = "SELECT * FROM blood_requests WHERE 1=1"
    params = []

    if bg_filter:
        query += " AND blood_group = ?"
        params.append(bg_filter)
    if city_filter:
        query += " AND city LIKE ?"
        params.append(f"%{city_filter}%")
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    else:
        # Default show pending & approved
        query += " AND status IN ('Pending', 'Approved')"

    query += " ORDER BY CASE urgency WHEN 'Immediate' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC"
    requests_list = conn.execute(query, params).fetchall()

    # Cities for dropdown filter
    cities = [row[0] for row in conn.execute("SELECT DISTINCT city FROM blood_requests WHERE city IS NOT NULL AND city != ''").fetchall()]

    conn.close()

    return render_template(
        'requests.html',
        requests_list=requests_list,
        selected_bg=bg_filter,
        selected_city=city_filter,
        selected_status=status_filter,
        cities=cities
    )

@app.route('/requests/create', methods=['GET', 'POST'])
def create_request():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        units_needed = request.form.get('units_needed', '1')
        hospital_name = request.form.get('hospital_name', '').strip()
        city = request.form.get('city', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        urgency = request.form.get('urgency', 'Urgent')
        details = request.form.get('details', '').strip()

        if not patient_name or not blood_group or not hospital_name or not city or not contact_phone:
            flash('Please fill in all mandatory fields.', 'danger')
            return render_template('create_request.html')

        user_id = session.get('user_id') # Can be None if guest
        units = int(units_needed) if units_needed.isdigit() else 1

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO blood_requests (user_id, patient_name, blood_group, units_needed, hospital_name, city, contact_phone, urgency, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        ''', (user_id, patient_name, blood_group, units, hospital_name, city, contact_phone, urgency, details))

        conn.execute('''
            INSERT INTO activity_logs (action_type, description)
            VALUES (?, ?)
        ''', ('REQUEST_CREATED', f"New Blood Request ({blood_group}, {units} unit(s)) at {hospital_name}, {city} for {patient_name}."))

        conn.commit()
        conn.close()

        flash('Emergency blood request posted successfully! Verified donors in your area will be alerted.', 'success')
        if user_id:
            return redirect(url_for('recipient_dashboard'))
        return redirect(url_for('list_requests'))

    return render_template('create_request.html')

@app.route('/requests/<int:req_id>/update-status', methods=['POST'])
@login_required
def update_request_status(req_id):
    new_status = request.form.get('status')
    user = get_current_user()

    if new_status not in ['Pending', 'Approved', 'Fulfilled', 'Cancelled']:
        flash('Invalid status provided.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    conn = get_db_connection()
    req = conn.execute('SELECT * FROM blood_requests WHERE id = ?', (req_id,)).fetchone()

    if not req:
        conn.close()
        flash('Request not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Only admin or creator can modify
    if user['role'] != 'admin' and req['user_id'] != user['id']:
        conn.close()
        flash('Unauthorized permission to update this request.', 'danger')
        return redirect(url_for('dashboard'))

    conn.execute('UPDATE blood_requests SET status = ? WHERE id = ?', (new_status, req_id))
    conn.execute('''
        INSERT INTO activity_logs (action_type, description)
        VALUES (?, ?)
    ''', ('REQUEST_UPDATED', f"Blood request #{req_id} for {req['patient_name']} updated to '{new_status}'."))
    conn.commit()
    conn.close()

    flash(f"Blood request #{req_id} status updated to '{new_status}'.", 'success')
    return redirect(request.referrer or url_for('dashboard'))

# -------------------------------------------------------------
# Donor Search & Directory
# -------------------------------------------------------------

@app.route('/donors')
def list_donors():
    bg_filter = request.args.get('blood_group', '').strip()
    city_filter = request.args.get('city', '').strip()
    avail_filter = request.args.get('availability', '').strip()

    conn = get_db_connection()
    query = "SELECT id, full_name, blood_group, city, phone, is_available, age, gender, last_donation_date FROM users WHERE role = 'donor'"
    params = []

    if bg_filter:
        query += " AND blood_group = ?"
        params.append(bg_filter)
    if city_filter:
        query += " AND city LIKE ?"
        params.append(f"%{city_filter}%")
    if avail_filter == 'available':
        query += " AND is_available = 1"
    elif avail_filter == 'unavailable':
        query += " AND is_available = 0"

    query += " ORDER BY is_available DESC, created_at DESC"
    donors_list = conn.execute(query, params).fetchall()

    # Distinct cities
    cities = [row[0] for row in conn.execute("SELECT DISTINCT city FROM users WHERE role = 'donor' AND city IS NOT NULL").fetchall()]

    conn.close()

    return render_template(
        'donors.html',
        donors_list=donors_list,
        selected_bg=bg_filter,
        selected_city=city_filter,
        selected_avail=avail_filter,
        cities=cities
    )

# -------------------------------------------------------------
# Donation Appointments
# -------------------------------------------------------------

@app.route('/appointments/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    user = get_current_user()
    if user['role'] != 'donor' and user['role'] != 'admin':
        flash('Only registered donors can book blood donation appointments.', 'warning')
        return redirect(url_for('dashboard'))

    eligibility = check_eligibility(user)

    if request.method == 'POST':
        center = request.form.get('center', '').strip()
        appointment_date = request.form.get('appointment_date', '').strip()
        appointment_time = request.form.get('appointment_time', '').strip()
        notes = request.form.get('notes', '').strip()

        if not center or not appointment_date or not appointment_time:
            flash('Please select blood bank center, appointment date, and time slot.', 'danger')
            return render_template('book_appointment.html', eligibility=eligibility)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO donation_appointments (donor_id, blood_bank_center, appointment_date, appointment_time, units, status, notes)
            VALUES (?, ?, ?, ?, 1, 'Scheduled', ?)
        ''', (user['id'], center, appointment_date, appointment_time, notes))

        conn.execute('''
            INSERT INTO activity_logs (action_type, description)
            VALUES (?, ?)
        ''', ('APPOINTMENT_BOOKED', f"Donor {user['full_name']} ({user['blood_group']}) scheduled donation appointment on {appointment_date}."))

        conn.commit()
        conn.close()

        flash('Your donation appointment has been successfully booked! Thank you for being a lifesaver.', 'success')
        return redirect(url_for('donor_dashboard'))

    return render_template('book_appointment.html', eligibility=eligibility)

@app.route('/appointments/<int:apt_id>/update-status', methods=['POST'])
@login_required
def update_appointment_status(apt_id):
    new_status = request.form.get('status')
    user = get_current_user()

    if new_status not in ['Scheduled', 'Completed', 'Cancelled']:
        flash('Invalid appointment status.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    conn = get_db_connection()
    apt = conn.execute('SELECT * FROM donation_appointments WHERE id = ?', (apt_id,)).fetchone()
    if not apt:
        conn.close()
        flash('Appointment not found.', 'danger')
        return redirect(url_for('dashboard'))

    # If marked as Completed by admin:
    # 1. Update appointment status
    # 2. Add units to blood_inventory for that donor's blood group
    # 3. Update donor's last_donation_date to today
    if new_status == 'Completed' and user['role'] == 'admin':
        donor = conn.execute('SELECT * FROM users WHERE id = ?', (apt['donor_id'],)).fetchone()
        if donor and donor['blood_group']:
            # Increment inventory
            conn.execute('''
                UPDATE blood_inventory 
                SET units_available = units_available + ?, last_updated = ?
                WHERE blood_group = ?
            ''', (apt['units'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), donor['blood_group']))

            # Update donor last donation date
            conn.execute('UPDATE users SET last_donation_date = ? WHERE id = ?', (date.today().strftime('%Y-%m-%d'), donor['id']))

            # Log
            conn.execute('''
                INSERT INTO activity_logs (action_type, description)
                VALUES (?, ?)
            ''', ('DONATION_COMPLETED', f"Donation #{apt_id} completed. Added {apt['units']} unit(s) of {donor['blood_group']} blood to inventory."))

    conn.execute('UPDATE donation_appointments SET status = ? WHERE id = ?', (new_status, apt_id))
    conn.commit()
    conn.close()

    flash(f"Appointment #{apt_id} marked as '{new_status}'.", 'success')
    return redirect(request.referrer or url_for('dashboard'))

# -------------------------------------------------------------
# Admin Inventory Adjustments
# -------------------------------------------------------------

@app.route('/admin/inventory/update', methods=['POST'])
@admin_required
def update_inventory():
    blood_group = request.form.get('blood_group')
    units = request.form.get('units')

    if not blood_group or not units:
        flash('Missing blood group or unit values.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        units_val = max(0, int(units))
    except ValueError:
        flash('Units must be an integer.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO blood_inventory (blood_group, units_available, last_updated)
        VALUES (?, ?, ?)
    ''', (blood_group, units_val, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.execute('''
        INSERT INTO activity_logs (action_type, description)
        VALUES (?, ?)
    ''', ('INVENTORY_MANUAL_UPDATE', f"Admin updated inventory for {blood_group} to {units_val} units."))

    conn.commit()
    conn.close()

    flash(f"Inventory for {blood_group} updated to {units_val} units.", 'success')
    return redirect(url_for('admin_dashboard'))

# -------------------------------------------------------------
# Blood Compatibility Guide Page
# -------------------------------------------------------------

@app.route('/compatibility')
def compatibility():
    return render_template('compatibility.html')

# -------------------------------------------------------------
# Profile & Settings
# -------------------------------------------------------------

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        age = request.form.get('age')
        weight = request.form.get('weight')
        new_password = request.form.get('new_password', '').strip()

        conn = get_db_connection()
        age_val = int(age) if age and age.isdigit() else user['age']
        weight_val = float(weight) if weight else user['weight']

        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return render_template('profile.html', user=user)
            pwd_hash = generate_password_hash(new_password)
            conn.execute('''
                UPDATE users SET phone = ?, city = ?, age = ?, weight = ?, password_hash = ?
                WHERE id = ?
            ''', (phone, city, age_val, weight_val, pwd_hash, user['id']))
        else:
            conn.execute('''
                UPDATE users SET phone = ?, city = ?, age = ?, weight = ?
                WHERE id = ?
            ''', (phone, city, age_val, weight_val, user['id']))

        conn.commit()
        conn.close()

        flash('Your profile details have been successfully updated.', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

# -------------------------------------------------------------
# JSON API (For dynamic widgets / charts)
# -------------------------------------------------------------

@app.route('/api/inventory')
def api_inventory():
    conn = get_db_connection()
    rows = conn.execute("SELECT blood_group, units_available FROM blood_inventory ORDER BY blood_group ASC").fetchall()
    conn.close()
    data = {row['blood_group']: row['units_available'] for row in rows}
    return jsonify(data)

# -------------------------------------------------------------
# Initialization
# -------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print(" Blood Donation Management System (BloodLife)")
    print(" Server running at: http://127.0.0.1:5000")
    print(" Demo Admin: admin@bloodlife.org | admin123")
    print(" Demo Donor: david.m@example.com  | password123")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
