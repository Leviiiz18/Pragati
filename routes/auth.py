import random
import time
from collections import defaultdict
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from models import db, User
from flask_bcrypt import Bcrypt

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# Brute-force protection: IP-based tracking of failed attempts
_login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 25
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes

def is_ip_rate_limited(ip):
    now = time.time()
    # Retain attempts only within the lockout window
    recent = [t for t in _login_attempts[ip] if now - t < LOCKOUT_WINDOW_SECONDS]
    _login_attempts[ip] = recent
    return len(recent) >= MAX_LOGIN_ATTEMPTS

def record_failed_attempt(ip):
    _login_attempts[ip].append(time.time())

def clear_attempts(ip):
    if ip in _login_attempts:
        del _login_attempts[ip]

from sqlalchemy import func

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
    if request.method == 'POST':
        # If user is already authenticated and submits a new login, log out previous session
        if current_user.is_authenticated:
            logout_user()

        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        is_local = (
            not client_ip or 
            client_ip in ['127.0.0.1', '::1', 'localhost', 'testclient'] or
            client_ip.startswith(('10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.'))
        )

        # Check for active rate limit (skip for local and internal developer traffic)
        if not is_local and is_ip_rate_limited(client_ip):
            flash('Too many failed attempts. For security, access from your network is temporarily paused for 5 minutes.', 'danger')
            return render_template('login.html'), 429

        login_input = (
            request.form.get('campus_id') or 
            request.form.get('email') or 
            request.form.get('login_id') or 
            request.form.get('username') or 
            ''
        ).strip()
        password = (request.form.get('password') or '').strip()
        clean_input = login_input.lower()
        
        # 1. Flexible case-insensitive query across email, registration ID, employee ID, and personal email
        user = User.query.filter(
            (func.lower(User.email) == clean_input) | 
            (func.lower(User.registration_id) == clean_input) | 
            (func.lower(User.employee_id) == clean_input) |
            (func.lower(User.personal_email) == clean_input)
        ).first()

        # 2. Helpful alias fallback (e.g. typing "student", "faculty", "hod", "admin")
        if not user and clean_input:
            if clean_input == 'student':
                user = User.query.filter_by(role='student').first()
            elif clean_input == 'faculty':
                user = User.query.filter_by(role='faculty').first()
            elif clean_input == 'hod':
                user = User.query.filter_by(role='hod').first()
            elif clean_input in ['admin', 'superadmin', 'super_admin']:
                user = User.query.filter(User.role == 'super_admin').first() or User.query.filter(User.role.in_(['principal', 'hod'])).first()
            elif '@' not in clean_input:
                user = User.query.filter(
                    (func.lower(User.email).like(f"{clean_input}@%")) |
                    (func.lower(User.name) == clean_input)
                ).first()
        
        # 3. Robust password verification (bcrypt with plaintext fallback & auto-upgrade)
        is_valid_pw = False
        if user and user.password and password:
            try:
                if user.password.startswith(('$2b$', '$2a$', '$2y$')):
                    is_valid_pw = bcrypt.check_password_hash(user.password, password)
                else:
                    is_valid_pw = (user.password == password)
                    if is_valid_pw:
                        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
                        db.session.commit()
            except Exception:
                is_valid_pw = (user.password == password)
        
        if user and is_valid_pw:
            if user.status and user.status.lower() == 'suspended':
                flash('Your account has been deactivated or suspended. Please contact institutional administration.', 'danger')
                return render_template('login.html', entered_id=login_input)

            if client_ip:
                clear_attempts(client_ip)

            remember = bool(request.form.get('remember'))
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/') and not next_page.startswith('/login'):
                return redirect(next_page)
            return redirect(get_role_redirect(user.role))
        else:
            if client_ip and not is_local:
                record_failed_attempt(client_ip)
                attempts_made = len(_login_attempts[client_ip])
                remaining = MAX_LOGIN_ATTEMPTS - attempts_made
                if remaining > 0:
                    flash(f'Invalid credentials. Please verify your Email or Campus ID and password. ({remaining} attempts left)', 'danger')
                else:
                    flash('Invalid credentials. Maximum attempts exceeded. Access paused for 5 minutes.', 'danger')
            else:
                flash('Invalid credentials. Please verify your Email or Campus ID and password.', 'danger')
            
            return render_template('login.html', entered_id=login_input)
            
    # GET request handling
    if current_user.is_authenticated:
        return redirect(get_role_redirect(current_user.role))

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

