import random
from datetime import date
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import (
    db, User, Department, Course, FeeRecord, PlacementDrive, Institution,
    Enrollment, AttendanceRecord, DocumentRequest, PlacementApplication,
    ExamResult, AIRiskAlert, Subject, StudentNote, Notification
)
from flask_bcrypt import Bcrypt

super_admin_bp = Blueprint('super_admin', __name__)
bcrypt = Bcrypt()

@super_admin_bp.before_request
@login_required
def check_permission():
    if current_user.role not in ['super_admin', 'principal']:
        flash('Unauthorized access to Executive Super Admin Portal.', 'danger')
        return redirect(url_for('auth.login'))

def generate_registration_id(course_code="UCA", admission_year=2026):
    inst = Institution.query.first()
    univ_code = inst.code if inst else "NU"
    yy = str(admission_year)[-2:]
    prefix = f"{univ_code.upper()}{yy}{course_code.upper()}"
    
    existing_students = User.query.filter(User.registration_id.like(f"{prefix}%")).all()
    max_num = 0
    for s in existing_students:
        if s.registration_id and s.registration_id.startswith(prefix):
            suffix = s.registration_id[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"

def generate_employee_id(dept_code="CSE", joining_year=2026, role="faculty"):
    inst = Institution.query.first()
    univ_code = inst.code if inst else "NU"
    yy = str(joining_year)[-2:]
    tag = "HOD" if role == "hod" else "FAC"
    prefix = f"{univ_code.upper()}{yy}{tag}"
    
    existing_staff = User.query.filter(User.employee_id.like(f"{prefix}%")).all()
    max_num = 0
    for staff in existing_staff:
        if staff.employee_id and staff.employee_id.startswith(prefix):
            suffix = staff.employee_id[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"

def delete_user_cascading(user_id):
    user = User.query.get(user_id)
    if not user:
        return False, "User not found"
    
    # 1. Clean up student associations
    if user.role == 'student':
        Enrollment.query.filter_by(student_id=user.id).delete()
        FeeRecord.query.filter_by(student_id=user.id).delete()
        DocumentRequest.query.filter_by(student_id=user.id).delete()
        PlacementApplication.query.filter_by(student_id=user.id).delete()
        AttendanceRecord.query.filter_by(student_id=user.id).delete()
        ExamResult.query.filter_by(student_id=user.id).delete()
        AIRiskAlert.query.filter_by(student_id=user.id).delete()
        StudentNote.query.filter_by(student_id=user.id).delete()
        
    # 2. Clean up notifications
    Notification.query.filter_by(user_id=user.id).delete()

    # 3. Clean up faculty / HOD associations
    if user.role in ['faculty', 'hod']:
        subjects = Subject.query.filter_by(faculty_id=user.id).all()
        for subj in subjects:
            subj.faculty_id = None
        dept = Department.query.filter_by(hod_id=user.id).first()
        if dept:
            dept.hod_id = None
            
    name = user.name
    reg_id = user.registration_id or user.employee_id or f"User {user.id}"
    db.session.delete(user)
    db.session.commit()
    return True, f"{name} ({reg_id}) deleted successfully"

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

        # -----------------------------------------------------------------
        # STUDENT MANAGEMENT: ADD STUDENT
        # -----------------------------------------------------------------
        if action == 'add_student':
            first_name = (request.form.get('first_name') or '').strip()
            last_name = (request.form.get('last_name') or '').strip()
            full_name = f"{first_name} {last_name}".strip() or request.form.get('name', 'Student')

            dept = request.form.get('department', 'Computer Science')
            course_code = request.form.get('course_code', 'UCA').upper()
            sem = int(request.form.get('semester', 1))
            adm_year = int(request.form.get('admission_year', 2026))

            reg_id = generate_registration_id(course_code=course_code, admission_year=adm_year)
            inst_email = (request.form.get('email') or f"{reg_id.lower()}@studysync.pro").strip().lower()

            # Check duplicate email
            if User.query.filter_by(email=inst_email).first():
                inst_email = f"{reg_id.lower()}.student@studysync.pro"

            hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
            cgpa_val = None if sem == 1 else request.form.get('cgpa', type=float, default=None)

            new_student = User(
                name=full_name,
                first_name=first_name,
                last_name=last_name,
                email=inst_email,
                password=hashed_pw,
                role='student',
                department=dept,
                semester=sem,
                cgpa=cgpa_val,
                registration_id=reg_id,
                course_code=course_code,
                admission_year=adm_year,
                gender=request.form.get('gender', 'Male'),
                dob=request.form.get('dob'),
                student_phone=request.form.get('student_phone'),
                parent_phone=request.form.get('parent_phone'),
                personal_email=request.form.get('personal_email'),
                permanent_address=request.form.get('permanent_address'),
                current_address=request.form.get('current_address'),
                category=request.form.get('category', 'General'),
                status='active'
            )
            db.session.add(new_student)
            db.session.commit()
            flash(f'Student {full_name} enrolled successfully! System Generated Registration ID: {reg_id}', 'success')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # STUDENT MANAGEMENT: EDIT STUDENT
        # -----------------------------------------------------------------
        elif action == 'edit_student':
            student_id = request.form.get('student_id') or request.form.get('user_id')
            student = User.query.get(student_id)
            if student and student.role == 'student':
                student.name = request.form.get('name', student.name).strip()
                student.email = request.form.get('email', student.email).strip().lower()
                student.department = request.form.get('department', student.department)
                student.course_code = request.form.get('course_code', student.course_code or 'UCA').upper()
                student.semester = int(request.form.get('semester', student.semester or 1))
                if request.form.get('cgpa'):
                    student.cgpa = float(request.form.get('cgpa'))
                student.student_phone = request.form.get('student_phone', student.student_phone)
                student.status = request.form.get('status', student.status)
                db.session.commit()
                flash(f'Student records for {student.name} ({student.registration_id}) updated successfully.', 'success')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # STUDENT MANAGEMENT: DELETE STUDENT
        # -----------------------------------------------------------------
        elif action == 'delete_student':
            student_id = request.form.get('student_id') or request.form.get('user_id')
            success, msg = delete_user_cascading(student_id)
            flash(msg, 'warning' if success else 'danger')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # STUDENT MANAGEMENT: SUSPEND / ACTIVATE
        # -----------------------------------------------------------------
        elif action == 'suspend_student':
            student_id = request.form.get('student_id') or request.form.get('user_id')
            student = User.query.get(student_id)
            if student and student.role == 'student':
                student.status = 'suspended' if student.status == 'active' else 'active'
                db.session.commit()
                flash(f'Student {student.name} status updated to {student.status.upper()}.', 'info')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # STUDENT MANAGEMENT: PROMOTE SEMESTER
        # -----------------------------------------------------------------
        elif action == 'promote_student':
            student_id = request.form.get('student_id') or request.form.get('user_id')
            student = User.query.get(student_id)
            if student and student.role == 'student':
                student.semester = min(8, (student.semester or 1) + 1)
                db.session.commit()
                flash(f'Student {student.name} promoted to Semester {student.semester}.', 'success')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # FACULTY MANAGEMENT: ADD FACULTY / HOD
        # -----------------------------------------------------------------
        elif action == 'add_faculty':
            name = (request.form.get('name') or 'Faculty Member').strip()
            role = request.form.get('role', 'faculty').lower()
            dept = request.form.get('department', 'Computer Science')
            email = (request.form.get('email') or '').strip().lower()
            phone = request.form.get('phone', '')
            spec = request.form.get('specialization', '')

            emp_id = generate_employee_id(dept_code="FAC", joining_year=2026, role=role)
            if not email:
                email = f"{emp_id.lower()}@studysync.pro"

            default_pw = 'admin123' if role == 'hod' else 'password123'
            hashed_pw = bcrypt.generate_password_hash(default_pw).decode('utf-8')

            new_fac = User(
                name=name,
                email=email,
                password=hashed_pw,
                role=role,
                department=dept,
                employee_id=emp_id,
                phone=phone,
                specialization=spec,
                status='active'
            )
            db.session.add(new_fac)
            db.session.commit()

            # If new HOD, associate with Department
            if role == 'hod':
                d_obj = Department.query.filter_by(name=dept).first()
                if d_obj:
                    d_obj.hod_id = new_fac.id
                    db.session.commit()

            flash(f'{role.upper()} {name} onboarded! Employee ID: {emp_id}', 'success')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # FACULTY MANAGEMENT: DELETE FACULTY
        # -----------------------------------------------------------------
        elif action == 'delete_faculty':
            faculty_id = request.form.get('faculty_id') or request.form.get('user_id')
            success, msg = delete_user_cascading(faculty_id)
            flash(msg, 'warning' if success else 'danger')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # FACULTY MANAGEMENT: SUSPEND FACULTY
        # -----------------------------------------------------------------
        elif action == 'suspend_faculty':
            faculty_id = request.form.get('faculty_id') or request.form.get('user_id')
            fac = User.query.get(faculty_id)
            if fac:
                fac.status = 'suspended' if fac.status == 'active' else 'active'
                db.session.commit()
                flash(f'Faculty member {fac.name} status updated to {fac.status.upper()}.', 'info')
            return redirect(url_for('super_admin.dashboard'))

        # -----------------------------------------------------------------
        # INSTITUTION & COURSE MANAGEMENT
        # -----------------------------------------------------------------
        elif action == 'update_institution':
            inst.name = request.form.get('name', inst.name)
            inst.code = request.form.get('code', inst.code).upper()
            inst.address = request.form.get('address', inst.address)
            db.session.commit()
            flash(f'University details updated: {inst.name} ({inst.code})', 'success')
            return redirect(url_for('super_admin.dashboard'))

        elif action == 'add_course':
            c_name = request.form.get('name')
            c_code = request.form.get('code', 'UCA').upper()
            dept = request.form.get('department', 'Computer Science')
            new_c = Course(name=c_name, code=c_code, department=dept)
            db.session.add(new_c)
            db.session.commit()
            flash(f'Course {c_name} ({c_code}) pre-fed into institutional system.', 'success')
            return redirect(url_for('super_admin.dashboard'))

        elif action == 'post_notice':
            title = (request.form.get('title') or '').strip()
            message = (request.form.get('message') or '').strip()
            target_role = request.form.get('target_role', 'all')
            if title and message:
                recipients = []
                if target_role == 'all':
                    recipients = User.query.all()
                else:
                    recipients = User.query.filter_by(role=target_role).all()
                for r in recipients:
                    notif = Notification(user_id=r.id, title=title, message=message, notif_type='announcement')
                    db.session.add(notif)
                db.session.commit()
                flash(f'Institutional notice "{title}" broadcasted successfully.', 'success')
            return redirect(url_for('super_admin.dashboard'))

    # Load all entities for unified dashboard
    students = User.query.filter_by(role='student').order_by(User.id.desc()).all()
    faculties = User.query.filter(User.role.in_(['faculty', 'hod'])).order_by(User.name.asc()).all()
    departments = Department.query.all()
    courses = Course.query.all()

    total_students = len(students)
    active_students = sum(1 for s in students if (s.status or 'active') == 'active')
    suspended_students = sum(1 for s in students if s.status == 'suspended')

    total_faculty = sum(1 for f in faculties if f.role == 'faculty')
    total_hods = sum(1 for f in faculties if f.role == 'hod')

    total_fees_collected = sum(f.paid_amount for f in FeeRecord.query.all()) if FeeRecord.query.first() else 1450000.0
    placements_count = PlacementDrive.query.filter_by(status='Active').count()

    avg_attendance = round(sum((s.attendance_percentage or 85.0) for s in students) / len(students), 1) if students else 88.5
    at_risk_students = [s for s in students if (s.attendance_percentage or 85.0) < 75.0 or s.status == 'suspended']
    placement_ready = sum(1 for s in students if (s.cgpa or 0) >= 7.5 and (s.attendance_percentage or 85.0) >= 75)
    total_subjects = Subject.query.count()

    return render_template(
        'super_admin/dashboard.html',
        institution=inst,
        students=students,
        faculties=faculties,
        departments=departments,
        courses=courses,
        total_students=total_students,
        active_students=active_students,
        suspended_students=suspended_students,
        total_faculty=total_faculty,
        total_hods=total_hods,
        total_fees_collected=total_fees_collected,
        placements_count=placements_count,
        today_date=date.today(),
        avg_attendance=avg_attendance,
        at_risk_students=at_risk_students,
        placement_ready=placement_ready,
        total_subjects=total_subjects
    )

@super_admin_bp.route('/students')
def students_redirect():
    return redirect(url_for('super_admin.dashboard'))

@super_admin_bp.route('/faculty')
def faculty_redirect():
    return redirect(url_for('super_admin.dashboard'))


# ---------------------------------------------------------------------------
# Early-access onboarding: review requests and issue activation keys
# ---------------------------------------------------------------------------
@super_admin_bp.route('/access-requests')
def access_requests():
    from models import AccessRequest
    status_filter = request.args.get('status', 'pending')
    query = AccessRequest.query
    if status_filter in ['pending', 'approved', 'rejected', 'revoked']:
        query = query.filter_by(status=status_filter)
    requests_list = query.order_by(AccessRequest.created_at.desc()).all()

    counts = {s: AccessRequest.query.filter_by(status=s).count()
              for s in ['pending', 'approved', 'rejected', 'revoked']}
    counts['all'] = sum(counts.values())

    return render_template('super_admin/access_requests.html',
                           requests_list=requests_list,
                           status_filter=status_filter,
                           counts=counts)


@super_admin_bp.route('/access-requests/<int:req_id>/<action>', methods=['POST'])
def access_request_action(req_id, action):
    from datetime import datetime
    from models import AccessRequest
    from routes.landing import generate_activation_key

    req = AccessRequest.query.get_or_404(req_id)
    note = (request.form.get('note') or '').strip()[:300] or None
    back_to = request.form.get('back', 'pending')

    if action == 'approve':
        if not req.activation_key:
            req.activation_key = generate_activation_key()
        req.status = 'approved'
        flash(f'{req.full_name} approved. Activation key: {req.activation_key}', 'success')
    elif action == 'regenerate':
        req.activation_key = generate_activation_key()
        req.status = 'approved'
        flash(f'New key issued for {req.full_name}: {req.activation_key}. The old key no longer works.', 'success')
    elif action == 'reject':
        req.status = 'rejected'
        flash(f'Request from {req.full_name} rejected.', 'info')
    elif action == 'revoke':
        req.status = 'revoked'
        flash(f'Access revoked for {req.full_name}. Their key stops working immediately.', 'info')
    else:
        flash('Unknown action.', 'danger')
        return redirect(url_for('super_admin.access_requests', status=back_to))

    req.review_note = note or req.review_note
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('super_admin.access_requests', status=back_to))

