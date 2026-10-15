# 🩸 BloodLife - Professional Blood Donation & Bank Management System

A full-stack, medical-grade Blood Donation & Bank Management System built with Python, Flask, SQLite, Tailwind CSS, and FontAwesome. 

The system bridges voluntary blood donors, emergency patients/recipients, and blood bank administrators with real-time stock tracking, automated donor health eligibility checks, digital donor passes, appointment scheduling, and blood compatibility matrices.

---

## 🌟 Key Features

### 1. 🔐 Authentication & Role-Based Access Control
- **User Registration**: Multi-role registration for **Blood Donors** and **Recipients / Hospitals**. Donors record their blood group (A+, A-, B+, B-, AB+, AB-, O+, O-), age, weight, and last donation date.
- **Secure Sign In / Login**: Password hashing using `werkzeug.security` with session management and route protection (`@login_required`, `@admin_required`).
- **1-Click Quick Demo Login**: Instant login buttons on the sign-in page to test as Admin, Donor, or Recipient without typing credentials.

### 2. ❤️ Donor Portal
- **Automated Health & Cooldown Eligibility Check**: Validates standard medical parameters (Age 18-65, Weight &ge;50kg, and 56-day safe interval since last whole blood donation).
- **Live Availability Toggle**: Donors can mark themselves as *"Available for Emergencies"* or *"Inactive"* at any time.
- **Digital Donor Pass / Card**: Personalized ID card with donor blood group, verification badge, and registration identifier.
- **Appointment Booking**: Schedule blood donation slots at authorized donor centers and mobile blood drives.
- **Targeted Emergency Feed**: Donors automatically receive alerts for urgent blood requests in their compatible blood groups.

### 3. 🚨 Recipient & Emergency Care Portal
- **Broadcast Urgent Blood Requests**: Patients and hospital staff can post emergency blood requirements with patient name, blood type, units needed, urgency level (*Immediate*, *Urgent*, *Routine*), hospital name, and contact details.
- **Live Donor Search Directory**: Search active donors with instant blood group, city, and availability filters.
- **Track Status**: Monitor posted requests across *Pending*, *Approved*, *Fulfilled*, or *Cancelled*.

### 4. 🏥 Admin & Blood Bank Control Center
- **Real-Time Blood Stock Monitor**: Visual inventory cards for all 8 blood groups with status levels (*Optimal*, *Moderate*, *Critical* &le; 5 units).
- **Interactive Inventory Manager**: Blood bank staff can manually adjust or inspect blood unit counts.
- **Appointment Verification & Auto-Stocking**: Marking a donor appointment as *"Completed"* automatically credits the collected blood units into the blood inventory and resets the donor's cooldown clock.
- **Activity & Audit Logs**: Detailed chronological log of registrations, donation completions, and inventory adjustments.

### 5. 🧬 Interactive Blood Group Compatibility Matrix
- Real-time compatibility inspector detailing who can give red blood cells to whom, and who can receive from whom.
- Visual master grid covering ABO typing, Rh factor (+/-), Type O- (Universal Donor), and Type AB+ (Universal Recipient).

---

## 🛠️ Project Structure

```
blood-donation-system/
├── app.py                     # Main Flask application & routing
├── database.py                # SQLite database initialization & seeding
├── auth.py                    # Auth decorators & donor eligibility logic
├── requirements.txt           # Python dependencies
├── blood_donation.db          # SQLite database (auto-created on start)
│
├── static/
│   ├── css/
│   │   └── style.css          # Custom styling and keyframe animations
│   └── js/
│       └── main.js            # Interactivity and UI helpers
│
└── templates/
    ├── base.html              # Base layout with navbar, alerts & footer
    ├── index.html             # High-converting landing page & live stats
    ├── login.html             # Sign in with 1-click demo logins
    ├── register.html          # Registration with role & health fields
    ├── donors.html            # Donor directory with multi-filter search
    ├── requests.html          # Emergency blood requirements list
    ├── create_request.html    # Emergency blood request submission form
    ├── donor_dashboard.html   # Donor dashboard, eligibility, card & appointments
    ├── recipient_dashboard.html# Recipient portal & tracking
    ├── admin_dashboard.html   # Central admin blood inventory & verifications
    ├── book_appointment.html  # Appointment booking form
    ├── compatibility.html     # Interactive blood compatibility matrix
    └── profile.html           # Personal details & password updater
```

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.8 or higher (Python 3.11 tested)

### 2. Installation
Open your terminal in the `blood-donation-system` folder:
```bash
pip install -r requirements.txt
```

### 3. Initialize the Database
The database seeds realistic mock donors, requests, and inventory automatically:
```bash
python database.py
```

### 4. Run the Server
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Pre-Configured Demo Accounts

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@bloodlife.org` | `admin123` | Full blood bank access, stock control & approvals |
| **Blood Donor** | `david.m@example.com` | `password123` | Blood Group O+, active donor with history |
| **Recipient / Patient** | `robert.t@example.com` | `password123` | Active blood request posted for Mount Sinai |

*(Tip: On the Sign In page, you can simply click any of the quick-login buttons to test immediately!)*
