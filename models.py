from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from common import db, login_manager
from sqlalchemy import UniqueConstraint

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    doctors = db.relationship('Doctor', back_populates='user', passive_deletes=True)
    patients = db.relationship('Patient', back_populates='user', passive_deletes=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return '<User {}>'.format(self.username)

class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    doctors = db.relationship('Doctor', back_populates='department', passive_deletes=True)

class Doctor(db.Model):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    # specialization = db.Column(db.String(64))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='CASCADE'), nullable=True)
    # bio = db.Column(db.Text)

    user = db.relationship('User', back_populates='doctors', passive_deletes=True)
    department = db.relationship('Department', back_populates='doctors', passive_deletes=True)
    
    availabilities = db.relationship('DoctorAvailability', back_populates='doctor', passive_deletes=True, cascade="save-update, merge")
    appointments = db.relationship('Appointment', back_populates='doctor', passive_deletes=True)
    treatments = db.relationship('Treatment', back_populates='doctor', passive_deletes=True)

class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))

    user = db.relationship('User', back_populates='patients', passive_deletes=True)

    appointments = db.relationship('Appointment', back_populates='patient', passive_deletes=True)
    treatments = db.relationship('Treatment', back_populates='patient', passive_deletes=True)

class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(32), nullable=False)
    available = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint('doctor_id', 'date', 'time_slot', name='uq_doctor_date_timeslot'),)

    doctor = db.relationship('Doctor', back_populates='availabilities', passive_deletes=True)

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='Booked')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('doctor_id', 'date', 'time', name='uq_appointment_doctor_date_time'),)

    patient = db.relationship('Patient', back_populates='appointments', passive_deletes=True)
    doctor = db.relationship('Doctor', back_populates='appointments', passive_deletes=True)
    treatment = db.relationship('Treatment', back_populates='appointment', uselist=False, passive_deletes=True)

class Treatment(db.Model):
    __tablename__ = 'treatments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id', ondelete='CASCADE'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id', ondelete='CASCADE'), nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    appointment = db.relationship('Appointment', back_populates='treatment', passive_deletes=True)
    doctor = db.relationship('Doctor', back_populates='treatments', passive_deletes=True)
    patient = db.relationship('Patient', back_populates='treatments', passive_deletes=True)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
