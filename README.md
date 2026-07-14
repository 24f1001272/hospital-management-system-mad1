# Hospital Management System (MAD 1 Project)

A comprehensive Hospital Management System built using Flask, designed as a project for the MAD 1 course in the IITM BS online degree program. This web application streamlines hospital operations by providing dedicated portals and functionalities for Admins, Doctors, and Patients.

## 🚀 Features

### Role-Based Access Control
- **Admin**: Has full control over the system. Can manage doctors, departments, and oversee hospital operations.
- **Doctor**: Can view their appointments, manage their availability, and add treatment details/prescriptions for patients.
- **Patient**: Can book appointments, view their appointment history, and access their treatment records and prescriptions.

### Core Modules
- **User Authentication**: Secure login and registration system using `Flask-Login` and password hashing with `Werkzeug`.
- **Department Management**: Organize doctors into specialized departments (e.g., Neurology, Cardiology, Gastroenterology, Oncology).
- **Appointment Booking**: Patients can book appointments based on doctor availability.
- **Treatment Records**: Doctors can record diagnoses, medicines prescribed, tests done, and general notes for each appointment.
- **Doctor Availability**: Doctors can set their available time slots for appointments.

## 🛠️ Technologies Used

- **Backend Framework**: [Flask](https://flask.palletsprojects.com/)
- **Database**: [SQLite](https://www.sqlite.org/index.html)
- **ORM**: [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- **Authentication**: [Flask-Login](https://flask-login.readthedocs.io/)
- **Frontend**: HTML, CSS, Jinja2 Templates (Flask's default templating engine)

## 📁 Project Structure

```text
hospital-management-system-mad1/
├── app.py                 # Main application factory and configuration
├── models.py              # SQLAlchemy database models
├── common.py              # Shared instances (db, login_manager)
├── requirements.txt       # Python dependencies
├── routes/                # Blueprint routes for different modules
│   ├── admin.py
│   ├── auth.py
│   ├── doctor.py
│   ├── home.py
│   └── patient.py
└── templates/             # HTML templates for the application
```

## ⚙️ Installation & Setup

Follow these steps to run the project locally on your machine.

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hospital-management-system-mad1.git
   cd hospital-management-system-mad1
   ```

2. **Create a virtual environment (Recommended)**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```
   *Note: On the first run, the SQLite database (`hms.sqlite3`) will be automatically created along with default departments and an initial admin account.*

5. **Access the application**
   Open your web browser and navigate to `http://localhost:5000`

## 🔐 Default Credentials

An initial admin account is created automatically upon the first run:
- **Username**: `admin`
- **Password**: `adminpass`

It is highly recommended to change these credentials after your first login in a production environment.