from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Appointment, Treatment, Patient, Doctor, DoctorAvailability
from common import db
from functools import wraps

bp = Blueprint('doctor', __name__, url_prefix='/doctor')

def get_doctor_db():
    return Doctor.query.filter_by(user_id=current_user.id).first()

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'doctor' or current_user.status != 'active':
            flash('You do not have permission to access this page.')
            return redirect(url_for('home.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    doctor = get_doctor_db()
    if not doctor:
        flash('Doctor profile not found.','warning')
        return redirect(url_for('home.index'))

    today = date.today()
    week_end = today + timedelta(days=7)
    upcoming = (
        Appointment.query
        .filter(Appointment.doctor_id == doctor.id,
                Appointment.date >= today,
                Appointment.date < week_end,
                Appointment.status == 'Booked')
        .order_by(Appointment.date, Appointment.time)
        .all()
    )

    assigned_patients_query = (
        Patient.query
        .join(Appointment, Appointment.patient_id == Patient.id)
        .filter(Appointment.doctor_id == doctor.id)
        .distinct()
        .order_by(Patient.id)
        .all()
    )
    
    assigned_patients = []
    for p in assigned_patients_query:
        assigned_patients.append({
            'id': p.id,
            'full_name': p.user.name
        })

    return render_template('doctor/dashboard.html', appointments=upcoming, assigned_patients=assigned_patients)

@bp.route('/appointments')
@login_required
@doctor_required
def appointments():
    doctor = get_doctor_db()
    if not doctor:
        flash('Doctor profile not found.','warning')
        return redirect(url_for('home.index'))

    rows = (
        Appointment.query
        .filter_by(doctor_id=doctor.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )

    appts = []
    for appt in rows:
        patient = appt.patient
        appts.append({
            'id': appt.id,
            'date': appt.date,
            'time': appt.time,
            'patient_name': patient.user.name if patient and patient.user else None,
            'status': appt.status,
            'reason': appt.reason
        })

    return render_template('doctor/appointments.html', appts=appts)

@bp.route('/appointments/<int:appt_id>/status', methods=['POST'])
@login_required
@doctor_required
def update_status(appt_id):
    doctor = get_doctor_db()
    if not doctor:
        flash('Doctor profile not found.','warning')
        return redirect(url_for('home.index'))

    status = request.form.get('status')
    if status not in ('Booked', 'Completed', 'Cancelled'):
        flash('Invalid status','warning')
        return redirect(url_for('doctor.appointments'))

    appt = Appointment.query.get(appt_id)
    if not appt or appt.doctor_id != doctor.id:
        flash('Appointment not found.','warning')
        return redirect(url_for('doctor.appointments'))

    try:
        appt.status = status
        appt.updated_at = datetime.now(timezone.utc)
        
        if status == 'Cancelled':
            existing_treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
            if not existing_treatment:
                t = Treatment(
                    appointment_id=appt.id,
                    doctor_id=doctor.id,
                    patient_id=appt.patient_id,
                    diagnosis='cancelled',
                    medicines='cancelled',
                    tests_done='cancelled',
                    visit_type='cancelled',
                    notes='cancelled'
                )
                db.session.add(t)
            
            slot_label = None
            if appt.time.hour == 8:
                slot_label = 'morning'
            elif appt.time.hour == 14:
                slot_label = 'evening'
            
            if slot_label:
                availability = DoctorAvailability.query.filter_by(
                    doctor_id=doctor.id,
                    date=appt.date,
                    time_slot=slot_label
                ).first()
                if availability:
                    availability.available = True
        
        elif status == 'Completed':
            existing_treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
            if not existing_treatment:
                t = Treatment(
                    appointment_id=appt.id,
                    doctor_id=doctor.id,
                    patient_id=appt.patient_id,
                    diagnosis='NA',
                    medicines='NA',
                    tests_done='NA',
                    visit_type='NA',
                    notes='NA'
                )
                db.session.add(t)

        db.session.commit()
        flash('Status updated.','success')
    except Exception as e:
        db.session.rollback()
        flash('Error: ' + str(e), 'danger')

    return redirect(url_for('doctor.appointments'))

@bp.route('/appointments/<int:appt_id>/treatment', methods=['GET', 'POST'])
@login_required
@doctor_required
def treatment(appt_id):
    doctor = get_doctor_db()
    if not doctor:
        flash('Doctor profile not found.','warning')
        return redirect(url_for('home.index'))

    appt = (
        Appointment.query
        .filter_by(id=appt_id, doctor_id=doctor.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .first()
    )
    if not appt:
        flash('Appointment not found.','warning')
        return redirect(url_for('doctor.appointments'))

    existing_treatment = Treatment.query.filter_by(appointment_id=appt.id).first()

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis','').strip()
        medicines = request.form.get('medicines','').strip()
        tests_done = request.form.get('tests_done','').strip()
        visit_type = request.form.get('visit_type','In-person').strip()
        notes = request.form.get('notes','').strip()
        try:
            if existing_treatment:
                existing_treatment.diagnosis = diagnosis
                existing_treatment.medicines = medicines
                existing_treatment.tests_done = tests_done
                existing_treatment.visit_type = visit_type
                existing_treatment.notes = notes
                flash('Treatment updated.','success')
            else:
                t = Treatment(
                    appointment_id=appt.id,
                    doctor_id=doctor.id,
                    patient_id=appt.patient_id,
                    diagnosis=diagnosis,
                    medicines=medicines,
                    tests_done=tests_done,
                    visit_type=visit_type,
                    notes=notes
                )
                db.session.add(t)
                flash('Treatment saved and appointment marked completed.','success')
            
            appt.status = 'Completed'
            appt.updated_at = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('doctor.appointments'))
        except Exception as e:
            db.session.rollback()
            flash('Error: ' + str(e), 'danger')

    history = Treatment.query.filter_by(patient_id=appt.patient_id).order_by(Treatment.created_at.desc()).all()
    return render_template('doctor/treatment_form.html', appt=appt, history=history, treatment=existing_treatment)

@bp.route('/availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def availability():
    doctor = get_doctor_db()
    if not doctor:
        flash('Doctor profile not found.','warning')
        return redirect(url_for('home.index'))

    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]

    slot_types = ['morning', 'evening']
    slot_labels = {
        'morning': '08:00 - 12:00',
        'evening': '14:00 - 18:00'
    }

    if request.method == 'POST':
        try:
            start = days[0]
            end = days[-1]
            
            DoctorAvailability.query.filter(
                DoctorAvailability.doctor_id == doctor.id,
                DoctorAvailability.date >= start,
                DoctorAvailability.date <= end,
                DoctorAvailability.available == True
            ).delete(synchronize_session=False)

            booked_rows = DoctorAvailability.query.filter(
                DoctorAvailability.doctor_id == doctor.id,
                DoctorAvailability.date >= start,
                DoctorAvailability.date <= end,
                DoctorAvailability.available == False
            ).all()
            booked_slots = {(r.date, r.time_slot) for r in booked_rows}

            data = []
            for d in days:
                for st in slot_types:
                    if (d, st) in booked_slots:
                        continue
                        
                    field = f"av_{d.isoformat()}_{st}"
                    if request.form.get(field) == 'on':
                        data.append(DoctorAvailability(doctor_id=doctor.id, date=d, time_slot=st, available=True))

            if data:
                db.session.add_all(data)

            db.session.commit()
            flash('Availability updated.','success')
            return redirect(url_for('doctor.availability'))
        except Exception as e:
            db.session.rollback()
            flash('Error: ' + str(e), 'danger')

    existing_rows = DoctorAvailability.query.with_entities(DoctorAvailability.date, DoctorAvailability.time_slot, DoctorAvailability.available).filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= days[0],
        DoctorAvailability.date <= days[-1]
    ).all()
    existing = {(r.date.isoformat(), r.time_slot): r.available for r in existing_rows}

    return render_template('doctor/availability.html',
                           days=days,
                           slot_types=slot_types,
                           slot_labels=slot_labels,
                           existing=existing)

@bp.route('/patients/<int:patient_id>/history')
@login_required
@doctor_required
def patient_history(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        flash('Patient not found.','warning')
        return redirect(url_for('doctor.dashboard'))

    doctor = get_doctor_db()
    history = Treatment.query.filter_by(patient_id=patient_id).order_by(Treatment.created_at.desc()).all()
    return render_template('doctor/patient_history.html', patient=patient, history=history, doctor=doctor)
