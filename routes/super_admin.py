from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Department, Course, FeeRecord, PlacementDrive, Institution

super_admin_bp = Blueprint('super_admin', __name__)

@super_admin_bp.before_request
@login_required
def check_permission():
    if current_user.role not in ['super_admin', 'principal']:
        flash('Unauthorized access to Executive Super Admin Portal.', 'danger')
        return redirect(url_for('auth.login'))

@super_admin_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    inst = Institution.query.first() or Institution(name="Nitte University", code="NU", address="Mangaluru, Karnataka, India")
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            current_user.phone = request.form.get('phone', current_user.phone)
            current_user.personal_email = request.form.get('personal_email', current_user.personal_email)
            current_user.current_address = request.form.get('current_address', current_user.current_address)
            db.session.commit()
            flash('Executive Admin credentials updated successfully.', 'success')
            return redirect(url_for('super_admin.profile'))
    return render_template('super_admin/profile.html', institution=inst)

@super_admin_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    inst = Institution.query.first()
    if not inst:
        inst = Institution(name="Nitte University", code="NU")
        db.session.add(inst)
        db.session.commit()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_institution':
            inst.name = request.form.get('name', inst.name)
            inst.code = request.form.get('code', inst.code).upper()
            db.session.commit()
            flash(f'University details updated: {inst.name} ({inst.code})', 'success')
            
        elif action == 'add_course':
            c_name = request.form.get('name')
            c_code = request.form.get('code', 'UCA').upper()
            dept = request.form.get('department', 'Computer Science')
            new_c = Course(name=c_name, code=c_code, department=dept)
            db.session.add(new_c)
            db.session.commit()
            flash(f'Course {c_name} ({c_code}) pre-fed into institutional system.', 'success')

    total_students = User.query.filter_by(role='student').count()
    total_faculty = User.query.filter_by(role='faculty').count()
    total_hods = User.query.filter_by(role='hod').count()
    departments = Department.query.all()
    courses = Course.query.all()
    
    total_fees_collected = sum(f.paid_amount for f in FeeRecord.query.all()) if FeeRecord.query.first() else 1450000.0
    placements_count = PlacementDrive.query.filter_by(status='Active').count()
    
    return render_template('super_admin/dashboard.html',
                           institution=inst,
                           total_students=total_students,
                           total_faculty=total_faculty,
                           total_hods=total_hods,
                           departments=departments,
                           courses=courses,
                           total_fees_collected=total_fees_collected,
                           placements_count=placements_count)
