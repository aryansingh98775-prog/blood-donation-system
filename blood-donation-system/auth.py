from functools import wraps
from flask import session, redirect, url_for, flash
from datetime import datetime, date
from database import get_db_connection

# Blood Compatibility Rules
COMPATIBILITY_MATRIX = {
    'O-': {
        'can_donate_to': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
        'can_receive_from': ['O-']
    },
    'O+': {
        'can_donate_to': ['O+', 'A+', 'B+', 'AB+'],
        'can_receive_from': ['O+', 'O-']
    },
    'A-': {
        'can_donate_to': ['A-', 'A+', 'AB-', 'AB+'],
        'can_receive_from': ['A-', 'O-']
    },
    'A+': {
        'can_donate_to': ['A+', 'AB+'],
        'can_receive_from': ['A+', 'A-', 'O+', 'O-']
    },
    'B-': {
        'can_donate_to': ['B-', 'B+', 'AB-', 'AB+'],
        'can_receive_from': ['B-', 'O-']
    },
    'B+': {
        'can_donate_to': ['B+', 'AB+'],
        'can_receive_from': ['B+', 'B-', 'O+', 'O-']
    },
    'AB-': {
        'can_donate_to': ['AB-', 'AB+'],
        'can_receive_from': ['AB-', 'A-', 'B-', 'O-']
    },
    'AB+': {
        'can_donate_to': ['AB+'],
        'can_receive_from': ['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-']
    }
}

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin authentication required.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def check_eligibility(user):
    """
    Check if a donor user meets the health and timing criteria for blood donation.
    Standard criteria:
    - Age: 18 - 65
    - Weight: >= 50 kg (110 lbs)
    - Minimum interval since last donation: 56 days (8 weeks)
    """
    reasons = []
    is_eligible = True
    days_left = 0

    if not user:
        return {'eligible': False, 'reasons': ['User not found'], 'days_left': 0}

    age = user['age']
    if age is not None:
        if age < 18:
            is_eligible = False
            reasons.append("Donor must be at least 18 years old.")
        elif age > 65:
            is_eligible = False
            reasons.append("Regular donor age ceiling is 65 years.")

    weight = user['weight']
    if weight is not None and weight < 50.0:
        is_eligible = False
        reasons.append(f"Minimum required weight is 50.0 kg (Current: {weight} kg).")

    last_donation = user['last_donation_date']
    if last_donation:
        try:
            last_date = datetime.strptime(last_donation, '%Y-%m-%d').date()
            today = date.today()
            days_diff = (today - last_date).days
            if days_diff < 56:
                is_eligible = False
                days_left = 56 - days_diff
                reasons.append(f"Cool-down period active: {days_left} days remaining before next safe donation.")
        except Exception:
            pass

    if is_eligible:
        reasons.append("All health and timing benchmarks met. You are currently eligible to donate blood!")

    return {
        'eligible': is_eligible,
        'reasons': reasons,
        'days_left': days_left
    }
