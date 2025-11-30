from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Doctor, Patient, Appointment, Department, Treatment
from functools import wraps
from sqlalchemy.orm import aliased
from common import db
from datetime import date

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin' or current_user.status != 'active':
            flash('You do not have permission to access this page.')
            return redirect(url_for('home.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    doctors = Doctor.query.count()
    patients = Patient.query.count()
    p_user = aliased(User)
    d_user = aliased(User)
    rows = (
        db.session.query(Appointment, p_user.name.label('patient_name'), d_user.name.label('doctor_name'))
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(p_user, Patient.user_id == p_user.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(d_user, Doctor.user_id == d_user.id)
        .filter(Appointment.date >= date.today())
        .order_by(Appointment.date, Appointment.time)
        .limit(10)
        .all()
    )
    appts = []
    for appt, patient_name, doctor_name in rows:
        appts.append({
            'date': appt.date,
            'time': appt.time,
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'status': appt.status,
            'patient_id': appt.patient_id,
            'doctor_id': appt.doctor_id,
            'department': appt.doctor.department.name if appt.doctor.department else 'N/A'
        })
    return render_template('admin/dashboard.html', doctors=doctors, patients=patients, appointments=len(appts), appts=appts)

# Doctors
@bp.route('/doctors')
@login_required
@admin_required
def doctors_list():
    q = request.args.get('q', '').strip()
    query = Doctor.query.join(User, Doctor.user).join(Department, Doctor.department, isouter=True)
    if q:
        ilike_q = f"%{q}%"
        query = query.filter(
            (User.name.ilike(ilike_q)) |
            (Department.name.ilike(ilike_q))
        )
    doctors = []
    for doc in query.order_by(User.name).all():
        user = doc.user
        doctors.append({
            'id': doc.id,
            'full_name': user.name,
            'email': user.email,
            'phone': user.phone,
            'department': doc.department.name if doc.department else 'N/A',
            'active' : user.status == 'active'
        })
    return render_template('admin/doctors_list.html', doctors=doctors, q=q)

@bp.route('/doctors/new', methods=['GET','POST'])
@login_required
@admin_required
def doctor_new():
    departments = Department.query.order_by(Department.id).all()
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        username = request.form['user'].strip()
        phone = request.form.get('phone','').strip()
        department = request.form.get('department').strip()
        password = request.form.get('password')
        if (not(full_name or email or username or password) or department not in [d.name for d in departments]):
            flash('Please fill all required fields.','warning')
        else:
            try:
                user = User(username=username, email=email, name=full_name, phone=phone, role='doctor')
                user.set_password(password)
                db.session.add(user)
                db.session.flush()

                department_id = next((d.id for d in departments if d.name == department), None)
                info = request.form.get('info', '')
                doctor = Doctor(user_id=user.id, department_id=department_id, info=info)
                db.session.add(doctor)
                db.session.commit()
                flash('Doctor created.','success')
                return redirect(url_for('admin.doctors_list'))
            except Exception as e:
                db.session.rollback()
                flash('Error: '+str(e),'danger')
    return render_template('admin/doctor_form.html', mode='new', departments = departments)

@bp.route('/doctors/<int:doctor_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def doctor_edit(doctor_id):
    departments = Department.query.order_by(Department.id).all()
    doc = Doctor.query.join(Department, Doctor.department, isouter=True).filter(Doctor.id == doctor_id).first()
    if not doc:
        flash('Doctor not found.','warning')
        return redirect(url_for('admin.doctors_list'))
    user = doc.user
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form.get('phone','').strip()
        department = request.form.get('department').strip()
        if (full_name == "" or email == "") or department not in [d.name for d in departments]:
            flash('Please fill all required fields.','warning')
            return redirect(url_for('admin.doctor_edit', doctor_id=doctor_id))
        try:
            user.name = full_name
            user.email = email
            user.phone = phone
            user.status = 'active' if request.form.get('active') == 'on' else 'inactive'
            doc.department_id = next((d.id for d in departments if d.name == department), None)
            doc.info = request.form.get('info', '')
            db.session.commit()
            flash('Doctor updated.','success')
            return redirect(url_for('admin.doctors_list'))
        except Exception as e:
            db.session.rollback()
            flash('Error: '+str(e),'danger')
    doc_info = {
        'id': doc.id,
        'user_id': user.id,
        'full_name': user.name,
        'email': user.email,
        'phone': user.phone,
        'department': doc.department.name if doc.department else 'N/A',
        'info': doc.info,
        'active' : user.status == 'active'
    }
    return render_template('admin/doctor_form.html', mode='edit', doc=doc_info, departments = departments)

@bp.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@login_required
@admin_required
def doctor_delete(doctor_id):
    doc = Doctor.query.get(doctor_id)
    if not doc:
        flash('Doctor not found.','warning')
        return redirect(url_for('admin.doctors_list'))
    try:
        user = doc.user
        db.session.delete(user)
        db.session.commit()
        flash('Doctor removed.','info')
    except Exception as e:
        db.session.rollback()
        flash('Error: '+str(e),'danger')
    return redirect(url_for('admin.doctors_list'))

# Patients
@bp.route('/patients')
@login_required
@admin_required
def patients_list():
    q = request.args.get('q', '').strip()
    query = Patient.query.join(User, Patient.user)
    if q:
        ilike_q = f"%{q}%"
        query = query.filter(
            (User.name.ilike(ilike_q)) |
            (User.email.ilike(ilike_q)) |
            (User.phone.ilike(ilike_q))
        )
    patients = []
    for pat in query.order_by(User.name).all():
        user = pat.user
        patients.append({
            'id': pat.id,
            'user_id': user.id,
            'full_name': user.name,
            'email': user.email,
            'phone': user.phone,
            'active' : user.status == 'active'
        })
    return render_template('admin/patients_list.html', patients=patients, q=q)

@bp.route('/patients/<int:patient_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def patient_edit(patient_id):
    pat = Patient.query.get(patient_id)
    if not pat:
        flash('Patient not found.','warning')
        return redirect(url_for('admin.patients_list'))
    user = pat.user
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        dob_str = request.form.get('dob')
        gender = request.form.get('gender').strip()
        blood_group = request.form.get('blood_group').strip()
        phone = request.form.get('phone','').strip()

        if (full_name == "" or email == ""):
            flash('Please fill all required fields.','warning')
            return redirect(url_for('admin.patient_edit', patient_id=patient_id))
        try:
            user.name = full_name
            user.email = email
            user.phone = phone
            user.status = 'active' if request.form.get('active') == 'on' else 'inactive'
            
            if dob_str:
                pat.dob = date.fromisoformat(dob_str)
            pat.gender = gender
            pat.blood_group = blood_group

            db.session.commit()
            flash('Patient updated.','success')
            return redirect(url_for('admin.patients_list'))
        except Exception as e:
            db.session.rollback()
            flash('Error: '+str(e),'danger')
    pat_info = {
        'id': pat.id,
        'user_id': user.id,
        'full_name': user.name,
        'email': user.email,
        'phone': user.phone,
        'dob': pat.dob,
        'gender': pat.gender,
        'blood_group': pat.blood_group,
        'active' : user.status == 'active'
    }
    return render_template('admin/patient_form.html', pat=pat_info)

@bp.route('/patients/<int:patient_id>/delete', methods=['POST'])
@login_required
@admin_required
def patient_delete(patient_id):
    pat = Patient.query.get(patient_id)
    if not pat:
        flash('Patient not found.','warning')
        return redirect(url_for('admin.patients_list'))
    try:
        user = pat.user
        db.session.delete(user)
        db.session.commit()
        flash('Patient removed.','info')
    except Exception as e:
        db.session.rollback()
        flash('Error: '+str(e),'danger')
    return redirect(url_for('admin.patients_list'))

@bp.route('/patient_history/<int:patient_id>/<int:doctor_id>')
@login_required
@admin_required
def patient_history(patient_id, doctor_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = Doctor.query.get_or_404(doctor_id)
    
    treatments = Treatment.query.filter_by(patient_id=patient_id, doctor_id=doctor_id).order_by(Treatment.created_at).all()
    
    history = []
    for i, t in enumerate(treatments, 1):
        history.append({
            'visit_no': i,
            'visit_type': t.visit_type,
            'tests_done': t.tests_done,
            'diagnosis': t.diagnosis,
            'medicines': t.medicines
        })
        
    return render_template('admin/patient_history.html', patient=patient, doctor=doctor, history=history)

# Appointments
@bp.route('/appointments')
@login_required
@admin_required
def appointments():
    p_user = aliased(User)
    d_user = aliased(User)
    rows = (
        db.session.query(Appointment, p_user.name.label('patient_name'), d_user.name.label('doctor_name'))
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(p_user, Patient.user_id == p_user.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(d_user, Doctor.user_id == d_user.id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    appts = []
    for appt, patient_name, doctor_name in rows:
        appts.append({
            'id': appt.id,
            'date': appt.date,
            'time': appt.time,
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'status': appt.status,
            'reason': appt.reason,
            'patient_id': appt.patient_id,
            'doctor_id': appt.doctor_id,
            'department': appt.doctor.department.name if appt.doctor.department else 'N/A'
        })
    return render_template('admin/appointments.html', appts=appts)
