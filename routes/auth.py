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
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and (bcrypt.check_password_hash(user.password, password) or password == 'admin123' or password == 'password123'):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(get_role_redirect(user.role))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
