from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Doctor, Patient, Appointment, Department
from functools import wraps
from sqlalchemy.orm import aliased
from common import db

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
        })
    return render_template('admin/dashboard.html', doctors=doctors, patients=patients, appointments=len(appts), appts=appts)

# Doctors CRUD (ORM-based)
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
            # 'user_id': user.id,
            # 'user': user.username,
            'full_name': user.name,
            'email': user.email,
            'phone': user.phone,
            'department': doc.department.name if doc.department else 'N/A',
            # 'specialization': doc.specialization,
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
        password = request.form.get('password','doctor123')
        if (not(full_name or email or username or password) or department not in [d.name for d in departments]):
            flash('Please fill all required fields.','warning')
        else:
            try:
                user = User(username=username, email=email, name=full_name, phone=phone, role='doctor')
                user.set_password(password)
                db.session.add(user)
                db.session.flush()

                department_id = next((d.id for d in departments if d.name == department), None)
                doctor = Doctor(user_id=user.id, department_id=department_id)
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
        username = request.form['user'].strip()
        phone = request.form.get('phone','').strip()
        department = request.form.get('department').strip()
        if (full_name == "" or email == "" or username == "") or department not in [d.name for d in departments]:
            flash('Please fill all required fields.','warning')
            return redirect(url_for('admin.doctor_edit', doctor_id=doctor_id))
        try:
            user.name = full_name
            user.email = email
            user.username = username
            user.phone = phone
            user.status = 'active' if request.form.get('active') == 'on' else 'inactive'
            doc.department_id = next((d.id for d in departments if d.name == department), None)
            db.session.commit()
            flash('Doctor updated.','success')
            return redirect(url_for('admin.doctors_list'))
        except Exception as e:
            db.session.rollback()
            flash('Error: '+str(e),'danger')
    # pass a simple dict for templates expecting user fields
    doc_info = {
        'id': doc.id,
        'user_id': user.id,
        'user': user.username,
        'full_name': user.name,
        'email': user.email,
        'phone': user.phone,
        'department': doc.department.name if doc.department else 'N/A',
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

# Patients CRUD (ORM-based)
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

# @bp.route('/patients/new', methods=['GET','POST'])
# @login_required
# @admin_required
# def patient_new():
#     if request.method == 'POST':
#         full_name = request.form['full_name'].strip()
#         email = request.form['email'].strip().lower()
#         phone = request.form.get('phone','').strip()
#         password = request.form.get('password','patient123')
#         if not full_name or not email:
#             flash('Name and email are required.','warning')
#         else:
#             try:
#                 user = User(username=email, email=email, name=full_name, phone=phone, role='patient')
#                 user.set_password(password)
#                 db.session.add(user)
#                 db.session.flush()
#                 patient = Patient(user_id=user.id)
#                 db.session.add(patient)
#                 db.session.commit()
#                 flash('Patient created.','success')
#                 return redirect(url_for('admin.patients_list'))
#             except Exception as e:
#                 db.session.rollback()
#                 flash('Error: '+str(e),'danger')
#     return render_template('admin/patient_form.html', mode='new', pat=None)

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
        phone = request.form.get('phone','').strip()
        if (full_name == "" or email == ""):
            flash('Please fill all required fields.','warning')
            return redirect(url_for('admin.patient_edit', patient_id=patient_id))
        try:
            user.name = full_name
            user.email = email
            user.username = email
            user.phone = phone
            user.status = 'active' if request.form.get('active') == 'on' else 'inactive'
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

# Appointments list (ORM-based)
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
            'reason': appt.reason
        })
    return render_template('admin/appointments.html', appts=appts)
