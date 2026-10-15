import sqlite3
import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blood_donation.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'donor', -- 'donor', 'recipient', 'admin'
            blood_group TEXT,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            weight REAL,
            is_available INTEGER DEFAULT 1,
            last_donation_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Blood Requests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blood_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            patient_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            units_needed INTEGER NOT NULL DEFAULT 1,
            hospital_name TEXT NOT NULL,
            city TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'Urgent', -- 'Immediate', 'Urgent', 'Routine'
            status TEXT NOT NULL DEFAULT 'Pending', -- 'Pending', 'Approved', 'Fulfilled', 'Cancelled'
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 3. Donation Appointments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donation_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            blood_bank_center TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            units INTEGER DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Scheduled', -- 'Scheduled', 'Completed', 'Cancelled'
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (donor_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 4. Blood Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blood_inventory (
            blood_group TEXT PRIMARY KEY,
            units_available INTEGER NOT NULL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. Activity Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # Check if database has initial seed data
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        seed_data(cursor, conn)

    conn.close()

def seed_data(cursor, conn):
    print("Seeding initial demo data...")
    # Seed Inventory for all 8 blood groups
    blood_groups = [
        ('A+', 24),
        ('A-', 8),
        ('B+', 32),
        ('B-', 6),
        ('AB+', 14),
        ('AB-', 4),
        ('O+', 45),
        ('O-', 12)
    ]
    for bg, units in blood_groups:
        cursor.execute('''
            INSERT OR REPLACE INTO blood_inventory (blood_group, units_available, last_updated)
            VALUES (?, ?, ?)
        ''', (bg, units, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Seed Admin User
    admin_pass = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO users (full_name, email, password_hash, role, blood_group, phone, city, age, gender, weight, is_available)
        VALUES (?, ?, ?, 'admin', 'O+', '+1 (555) 019-2834', 'Central Medical City', 35, 'Other', 70.0, 1)
    ''', ('System Administrator', 'admin@bloodlife.org', admin_pass))

    # Seed Demo Donors
    donors = [
        ('David Miller', 'david.m@example.com', 'password123', 'donor', 'O+', '+1 (555) 234-5678', 'New York', 28, 'Male', 74.5, 1, '2026-06-15'),
        ('Sarah Jenkins', 'sarah.j@example.com', 'password123', 'donor', 'A+', '+1 (555) 345-6789', 'Los Angeles', 24, 'Female', 58.0, 1, '2026-05-10'),
        ('Michael Chang', 'michael.c@example.com', 'password123', 'donor', 'B+', '+1 (555) 456-7890', 'Chicago', 32, 'Male', 80.0, 1, '2026-01-20'),
        ('Elena Rostova', 'elena.r@example.com', 'password123', 'donor', 'O-', '+1 (555) 567-8901', 'Houston', 29, 'Female', 62.0, 1, '2026-07-01'),
        ('Marcus Vance', 'marcus.v@example.com', 'password123', 'donor', 'AB+', '+1 (555) 678-9012', 'Phoenix', 38, 'Male', 84.0, 1, '2025-11-12'),
        ('Priya Patel', 'priya.p@example.com', 'password123', 'donor', 'A-', '+1 (555) 789-0123', 'Philadelphia', 26, 'Female', 54.0, 1, '2026-04-18'),
        ('James Wilson', 'james.w@example.com', 'password123', 'donor', 'B-', '+1 (555) 890-1234', 'San Antonio', 31, 'Male', 76.0, 0, '2026-09-02'),
        ('Chloe Bennett', 'chloe.b@example.com', 'password123', 'donor', 'AB-', '+1 (555) 901-2345', 'San Diego', 27, 'Female', 59.0, 1, '2026-03-14')
    ]

    for name, email, pwd, role, bg, phone, city, age, gender, weight, avail, last_don in donors:
        cursor.execute('''
            INSERT INTO users (full_name, email, password_hash, role, blood_group, phone, city, age, gender, weight, is_available, last_donation_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, generate_password_hash(pwd), role, bg, phone, city, age, gender, weight, avail, last_don))

    # Seed Demo Recipients
    recipients = [
        ('Robert Taylor', 'robert.t@example.com', 'password123', 'recipient', 'B+', '+1 (555) 111-2233', 'New York', 45, 'Male', 78.0, 0),
        ('Amanda Hughes', 'amanda.h@example.com', 'password123', 'recipient', 'O-', '+1 (555) 222-3344', 'Chicago', 34, 'Female', 65.0, 0)
    ]
    for name, email, pwd, role, bg, phone, city, age, gender, weight, avail in recipients:
        cursor.execute('''
            INSERT INTO users (full_name, email, password_hash, role, blood_group, phone, city, age, gender, weight, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, generate_password_hash(pwd), role, bg, phone, city, age, gender, weight, avail))

    # Seed Demo Blood Requests
    requests = [
        (10, 'Robert Taylor', 'B+', 2, 'Mount Sinai Hospital', 'New York', '+1 (555) 111-2233', 'Immediate', 'Pending', 'Urgent surgery scheduled. Platelet/RBC units required urgently.'),
        (11, 'Emily Hughes', 'O-', 3, 'Northwestern Memorial Hospital', 'Chicago', '+1 (555) 222-3344', 'Immediate', 'Approved', 'Emergency trauma care patient in ICU. Negative blood types critical.'),
        (None, 'Grace Kelly', 'A+', 1, 'Cedars-Sinai Medical Center', 'Los Angeles', '+1 (555) 444-5566', 'Urgent', 'Approved', 'Anemia treatment, required within 24 hours.'),
        (None, 'Lucas Scott', 'AB-', 2, 'Methodist Hospital', 'Houston', '+1 (555) 777-8899', 'Routine', 'Fulfilled', 'Scheduled orthopedic procedure replenishment.')
    ]
    for uid, pname, bg, units, hosp, city, phone, urg, stat, det in requests:
        cursor.execute('''
            INSERT INTO blood_requests (user_id, patient_name, blood_group, units_needed, hospital_name, city, contact_phone, urgency, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uid, pname, bg, units, hosp, city, phone, urg, stat, det))

    # Seed Demo Donation Appointments
    appointments = [
        (2, 'Metropolitan Red Cross Donor Center', '2026-10-20', '10:30 AM', 1, 'Scheduled', 'Regular voluntary whole blood donation.'),
        (3, 'Downtown LifeShare Blood Bank', '2026-10-22', '02:00 PM', 1, 'Scheduled', 'First time donating at downtown facility.'),
        (4, 'City Health Memorial Blood Drive', '2026-10-10', '11:15 AM', 1, 'Completed', 'Donation successful. 450ml collected.')
    ]
    for did, center, adate, atime, units, stat, notes in appointments:
        cursor.execute('''
            INSERT INTO donation_appointments (donor_id, blood_bank_center, appointment_date, appointment_time, units, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (did, center, adate, atime, units, stat, notes))

    # Seed Activity Logs
    logs = [
        ('INVENTORY_UPDATE', 'Initial blood reserve stocked: 145 total units across all types.'),
        ('REQUEST_CREATED', 'Emergency blood request created for patient Emily Hughes (O-).'),
        ('DONATION_COMPLETED', 'Donor Michael Chang completed donation of 1 unit B+ blood.'),
        ('SYSTEM_INIT', 'Blood Donation Management System database initialized successfully.')
    ]
    for act, desc in logs:
        cursor.execute('''
            INSERT INTO activity_logs (action_type, description)
            VALUES (?, ?)
        ''', (act, desc))

    conn.commit()
    print("Database seeding completed.")

if __name__ == '__main__':
    init_db()
