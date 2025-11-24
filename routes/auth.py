from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from common import db
from models import User, Patient
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home.index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        ph_no = request.form['ph_no']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email, role='patient', name=name, phone=ph_no)
        user.set_password(password)
        
        dob_str = request.form.get('dob')
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
        gender = request.form.get('gender')
        blood_group = request.form.get('blood_group')
        
        patient = Patient(user=user, dob=dob, gender=gender, blood_group=blood_group)
        
        db.session.add(user)
        db.session.add(patient)
        db.session.commit()
        flash('Congratulations, you are now a registered patient!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('home.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        if user.status != 'active':
            flash('Account is inactive. Please contact support.')
            return redirect(url_for('auth.login'))
        login_user(user)
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif user.role == 'patient':
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('home.index'))
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home.index'))
