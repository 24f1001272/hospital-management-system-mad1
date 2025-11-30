from datetime import datetime, date, timedelta, time, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from common import db
from models import Doctor, Appointment, User, Patient, DoctorAvailability, Treatment, Department
from functools import wraps

bp = Blueprint('patient', __name__, url_prefix='/patient')

def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'patient' or current_user.status != 'active':
            flash('You do not have permission to access this page.')
            return redirect(url_for('home.index'))
        return f(*args, **kwargs)
    return decorated_function

def current_patient_db():
    return Patient.query.filter_by(user_id=current_user.id).first()

@bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    departments = Department.query.order_by(Department.name).all()

    patient = current_patient_db()
    upcoming = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Booked',
        Appointment.date >= date.today()
    ).order_by(Appointment.date, Appointment.time).all()

    return render_template('patient/dashboard.html',
                           departments=departments,
                           upcoming=upcoming)

@bp.route('/department/<int:dept_id>')
@login_required
@patient_required
def department_details(dept_id):
    department = Department.query.get_or_404(dept_id)
    doctors = Doctor.query.filter_by(department_id=dept_id).join(User).filter(User.status == 'active').all()
    return render_template('patient/department_details.html', department=department, doctors=doctors)

@bp.route('/doctor/<int:doctor_id>')
@login_required
@patient_required
def doctor_details(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template('patient/doctor_details.html', doctor=doctor)

@bp.route('/doctor/<int:doctor_id>/availability')
@login_required
@patient_required
def doctor_availability(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    reschedule_id = request.args.get('reschedule_id',None)
    
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(7)]
    
    slots = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= dates[-1],
        DoctorAvailability.available == True
    ).order_by(DoctorAvailability.date, DoctorAvailability.time_slot).all()
    
    slots_by_date = {}
    for slot in slots:
        if slot.date not in slots_by_date:
            slots_by_date[slot.date] = []
        slots_by_date[slot.date].append(slot)
    
    for d in slots_by_date:
        slots_by_date[d].sort(key=lambda x: 0 if x.time_slot == 'morning' else 1)

    available_dates = [d for d in dates if d in slots_by_date]
    
    slot_labels = {
        'morning': '08:00 - 12:00',
        'evening': '14:00 - 18:00'
    }
    
    return render_template('patient/doctor_availability.html', doctor=doctor, dates=available_dates, slots_by_date=slots_by_date, slot_labels=slot_labels, reschedule_id=reschedule_id)

@bp.route('/book/<int:doctor_id>', methods=['POST'])
@login_required
@patient_required
def book_slot(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    patient = current_patient_db()
    
    selected_slot = request.form.get('selected_slot')
    reason = request.form.get('reason', '').strip()
    reschedule_id = request.form.get('reschedule_id')

    if not selected_slot:
        flash('Please select a slot.', 'warning')
        return redirect(url_for('patient.doctor_availability', doctor_id=doctor_id, reschedule_id=reschedule_id))
    
    try:
        date_str, time_slot = selected_slot.split('|')
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        slot_labels = {
            'morning': '08:00 - 12:00',
            'evening': '14:00 - 18:00'
        }
        
        label = slot_labels.get(time_slot, '09:00')
        start_time_str = label.split('-')[0].strip()
        
        try:
            appt_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            appt_time = time(8, 0)

        existing_appt = Appointment.query.filter_by(
            doctor_id=doctor.id,
            date=appt_date,
            time=appt_time
        ).first()


        if existing_appt:
            if existing_appt.status == 'Cancelled':
                if reschedule_id:
                    old_appt = Appointment.query.get(reschedule_id)
                    if old_appt and old_appt.patient_id == patient.id:
                        old_slot_label = None
                        if old_appt.time.hour == 8: old_slot_label = 'morning'
                        elif old_appt.time.hour == 14: old_slot_label = 'evening'
                        
                        if old_slot_label:
                            old_av = DoctorAvailability.query.filter_by(doctor_id=old_appt.doctor_id, date=old_appt.date, time_slot=old_slot_label).first()
                            if old_av: old_av.available = True
                        
                        old_appt.status = 'Cancelled'
                        old_appt.reason = f"Rescheduled to {appt_date} {appt_time}"
                        old_appt.updated_at = datetime.now(timezone.utc)
                existing_appt.patient_id = patient.id
                existing_appt.status = 'Booked'              
                existing_appt.reason = reason or "No reason provided"
                existing_appt.updated_at = datetime.now(timezone.utc)

                if existing_appt.treatment:
                    db.session.delete(existing_appt.treatment)
                
            else:
                flash('Slot is already booked.', 'warning')
                return redirect(url_for('patient.doctor_availability', doctor_id=doctor_id, reschedule_id=reschedule_id))
        else:
            if reschedule_id:
                old_appt = Appointment.query.get(reschedule_id)
                if old_appt and old_appt.patient_id == patient.id:
                    old_slot_label = None
                    if old_appt.time.hour == 8: old_slot_label = 'morning'
                    elif old_appt.time.hour == 14: old_slot_label = 'evening'
                    
                    if old_slot_label:
                        old_av = DoctorAvailability.query.filter_by(doctor_id=old_appt.doctor_id, date=old_appt.date, time_slot=old_slot_label).first()
                        if old_av: old_av.available = True
                    
                    old_appt.doctor_id = doctor.id
                    old_appt.date = appt_date
                    old_appt.time = appt_time
                    old_appt.reason = reason or old_appt.reason
                    old_appt.status = 'Booked'
                    old_appt.updated_at = datetime.now(timezone.utc)
                else:
                    flash('Invalid reschedule request.', 'danger')
                    return redirect(url_for('patient.dashboard'))
            else:
                appt = Appointment(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    date=appt_date,
                    time=appt_time,
                    reason=reason or "No reason provided",
                    status='Booked',
                    updated_at = datetime.now(timezone.utc)
                )
                db.session.add(appt)
        
        availability = DoctorAvailability.query.filter_by(
            doctor_id=doctor.id,
            date=appt_date,
            time_slot=time_slot
        ).first()
        
        if availability:
            availability.available = False
            
        db.session.commit()
        flash('Appointment booked', 'success')
        return redirect(url_for('patient.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error booking appointment: {str(e)}', 'danger')
        return redirect(url_for('patient.doctor_availability', doctor_id=doctor_id, reschedule_id=reschedule_id))

@bp.route('/history')
@login_required
@patient_required
def history():
    patient = current_patient_db()
    history_q = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status.in_(['Completed', 'Cancelled', 'Booked'])
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    return render_template('patient/history.html', history=history_q)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    user = current_user
    patient = current_patient_db()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        dob_str = request.form.get('dob')
        gender = request.form.get('gender')
        blood_group = request.form.get('blood_group')

        user.name = full_name
        user.phone = phone
        
        if patient:
            if dob_str:
                try:
                    patient.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            patient.gender = gender
            patient.blood_group = blood_group

        try:
            db.session.commit()
            flash('Profile updated.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error: ' + str(e), 'danger')
        return redirect(url_for('patient.dashboard'))
    return render_template('patient/profile.html', user=user, patient=patient)

@bp.route('/appointments/<int:appt_id>/cancel', methods=['POST'])
@login_required
@patient_required
def cancel_appointment(appt_id):
    patient = current_patient_db()
    appt = Appointment.query.filter_by(id=appt_id, patient_id=patient.id).first()
    
    appt.status = 'Cancelled'
    appt.updated_at = datetime.now(timezone.utc)
    
    existing_treatment = Treatment.query.filter_by(appointment_id=appt.id).first()
    if not existing_treatment:
        t = Treatment(
            appointment_id=appt.id,
            doctor_id=appt.doctor_id,
            patient_id=patient.id,
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
            doctor_id=appt.doctor_id,
            date=appt.date,
            time_slot=slot_label
        ).first()
        if availability:
            availability.available = True
    
    try:
        db.session.commit()
        flash('Appointment cancelled.', 'info')
    except Exception as e:
        db.session.rollback()
        flash('Error: ' + str(e), 'danger')
    return redirect(url_for('patient.dashboard'))
