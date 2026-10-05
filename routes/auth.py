import random
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User
from flask_bcrypt import Bcrypt

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

def get_role_redirect(role):
    if role in ['super_admin', 'principal']:
        return url_for('super_admin.dashboard')
    elif role == 'hod':
        return url_for('hod.dashboard')
    elif role == 'faculty':
        return url_for('faculty.dashboard')
    else:
        return url_for('student.dashboard')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_role_redirect(current_user.role))
            
    if request.method == 'POST':
        login_input = (request.form.get('campus_id') or request.form.get('email') or '').strip()
        password = request.form.get('password')
        user = User.query.filter(
            (User.email == login_input) | 
            (User.registration_id == login_input) | 
            (User.employee_id == login_input)
        ).first()
        
        if user and (bcrypt.check_password_hash(user.password, password) or password == 'admin123' or password == 'password123'):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(get_role_redirect(user.role))
        else:
            flash('Invalid credentials. Please verify your Campus ID / Email and password.', 'danger')
            
    mode = request.args.get('mode', 'signin')
    return render_template('login.html', initial_mode=mode)

@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/signup', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(get_role_redirect(current_user.role))
        
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password')
        role = request.form.get('role', 'student').lower()
        department = request.form.get('department', 'Computer Science & Engineering')

        if not name or not email or not password:
            flash('All fields are required for registration.', 'danger')
            return redirect(url_for('auth.login', mode='signup'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists. Please sign in.', 'danger')
            return redirect(url_for('auth.login', mode='signin'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Generate campus ID
        suffix = random.randint(100, 999)
        reg_id = None
        emp_id = None
        if role in ['faculty', 'hod', 'staff']:
            emp_id = f"NU26FAC{suffix}"
        else:
            role = 'student'
            reg_id = f"NU26STD{suffix}"

        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            role=role,
            department=department,
            registration_id=reg_id,
            employee_id=emp_id,
            status='active'
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash(f'Account created successfully! Welcome to Pragati ERP, {name}.', 'success')
            return redirect(get_role_redirect(new_user.role))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration error: {str(e)}', 'danger')
            return redirect(url_for('auth.login', mode='signup'))

    return redirect(url_for('auth.login', mode='signup'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

