from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db, User, Course, Specialization, Subject, Enrollment, Exam, ExamResult, TimetableSlot, PlacementDrive, FeeRecord, DocumentRequest, AIRiskAlert, Institution, Department, PlacementApplication, AttendanceRecord, Module, Unit, Event, Notification
from services.risk_analytics import RiskAnalyticsService
from services.scheduler import AISchedulerService
from services.command_center import CommandCenterService
from flask_bcrypt import Bcrypt
import hashlib
from datetime import datetime

hod_bp = Blueprint('hod', __name__)
bcrypt = Bcrypt()

def generate_registration_id(course_code="UCA", admission_year=2026):
    inst = Institution.query.first()
    univ_code = inst.code if inst else "NU"
    yy = str(admission_year)[-2:]
    prefix = f"{univ_code.upper()}{yy}{course_code.upper()}"
    
    count = User.query.filter(User.registration_id.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:03d}"

def generate_employee_id(dept_code="CSE", joining_year=2026):
    inst = Institution.query.first()
    univ_code = inst.code if inst else "NU"
    yy = str(joining_year)[-2:]
    prefix = f"{univ_code.upper()}{yy}FAC"
    
    count = User.query.filter(User.employee_id.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:03d}"

@hod_bp.before_request
@login_required
def check_hod():
    if current_user.role not in ['hod', 'super_admin', 'principal']:
        flash('Access restricted to Department Admin and HOD.', 'danger')
        return redirect(url_for('auth.login'))

@hod_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    inst = Institution.query.first() or Institution(name="Nitte University", code="NU", address="Mangaluru, Karnataka, India")
    dept = Department.query.filter_by(name=current_user.department).first() if current_user.department else None
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            current_user.phone = request.form.get('phone', current_user.phone)
            current_user.personal_email = request.form.get('personal_email', current_user.personal_email)
            current_user.current_address = request.form.get('current_address', current_user.current_address)
            current_user.specialization = request.form.get('specialization', current_user.specialization)
            current_user.qualifications = request.form.get('qualifications', current_user.qualifications)
            current_user.research_publications = request.form.get('research_publications', current_user.research_publications)
            current_user.emergency_contact_name = request.form.get('emergency_contact_name', current_user.emergency_contact_name)
            current_user.emergency_contact_phone = request.form.get('emergency_contact_phone', current_user.emergency_contact_phone)
            db.session.commit()
            flash('Executive HOD profile records updated successfully.', 'success')
            return redirect(url_for('hod.profile'))
            
    return render_template('hod/profile.html', institution=inst, department_obj=dept)

@hod_bp.route('/dashboard')
def dashboard():
    dept_name = current_user.department or 'Computer Science'
    students = User.query.filter_by(role='student').all()
    faculties = User.query.filter_by(role='faculty').all()
    subjects = Subject.query.all()
    
    # Calculate Department Health Metrics
    total_students = len(students)
    avg_attendance = round(sum(s.attendance_percentage for s in students) / max(1, total_students), 1)
    
    cgpa_list = [s.cgpa for s in students if s.cgpa is not None and s.semester > 1]
    avg_cgpa = round(sum(cgpa_list) / max(1, len(cgpa_list)), 2) if cgpa_list else "N/A"
    
    at_risk_students = [s for s in students if s.risk_score >= 50 or s.attendance_percentage < 75]
    placement_ready = sum(1 for s in students if s.semester > 1 and s.cgpa and s.cgpa >= 7.5 and s.attendance_percentage >= 75)
    
    pending_docs = DocumentRequest.query.filter_by(status='Pending').count()
    upcoming_exams = Exam.query.filter_by(status='Scheduled').count()
    
    return render_template('hod/dashboard.html',
                           dept_name=dept_name,
                           total_students=total_students,
                           total_faculties=len(faculties),
                           total_subjects=len(subjects),
                           avg_attendance=avg_attendance,
                           avg_cgpa=avg_cgpa,
                           at_risk_students=at_risk_students,
                           placement_ready=placement_ready,
                           pending_docs=pending_docs,
                           upcoming_exams=upcoming_exams)

@hod_bp.route('/students', methods=['GET', 'POST'])
def student_management():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            # Section 1: Personal & Identification Details
            first_name = request.form.get('first_name', '')
            middle_name = request.form.get('middle_name', '')
            last_name = request.form.get('last_name', '')
            full_name = f"{first_name} {middle_name} {last_name}".replace("  ", " ").strip() or request.form.get('name', 'Student')
            
            dob = request.form.get('dob')
            gender = request.form.get('gender', 'Male')
            nationality = request.form.get('nationality', 'Indian')
            category = request.form.get('category', 'General')
            govt_id_type = request.form.get('govt_id_type', 'Aadhar')
            govt_id_number = request.form.get('govt_id_number')
            
            # Section 2: Contact & Address Details
            student_phone = request.form.get('student_phone')
            parent_phone = request.form.get('parent_phone')
            personal_email = request.form.get('personal_email')
            inst_email = request.form.get('email') or request.form.get('institutional_email')
            permanent_address = request.form.get('permanent_address')
            current_address = request.form.get('current_address')
            emergency_contact_name = request.form.get('emergency_contact_name')
            emergency_contact_phone = request.form.get('emergency_contact_phone')
            
            # Section 3: Academic & Admission Details
            previous_school = request.form.get('previous_school')
            previous_board = request.form.get('previous_board')
            previous_passing_year = request.form.get('previous_passing_year', type=int)
            previous_marks_percentage = request.form.get('previous_marks_percentage', type=float)
            entrance_exam_name = request.form.get('entrance_exam_name')
            entrance_exam_score = request.form.get('entrance_exam_score')
            
            dept = request.form.get('department', 'Computer Science')
            sem = int(request.form.get('semester', 1))
            adm_year = int(request.form.get('admission_year', 2026))
            course_code = request.form.get('course_code', 'UCA').upper()
            
            # Silent System Automatic Registration ID Generation (e.g. NU23UCA054)
            reg_id = generate_registration_id(course_code=course_code, admission_year=adm_year)
            hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
            
            cgpa_val = None if sem == 1 else request.form.get('cgpa', type=float, default=None)

            new_student = User(
                name=full_name,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=inst_email,
                password=hashed_pw,
                role='student',
                department=dept,
                semester=sem,
                cgpa=cgpa_val,
                registration_id=reg_id,
                dob=dob,
                gender=gender,
                nationality=nationality,
                category=category,
                govt_id_type=govt_id_type,
                govt_id_number=govt_id_number,
                student_phone=student_phone,
                parent_phone=parent_phone,
                personal_email=personal_email,
                permanent_address=permanent_address,
                current_address=current_address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                admission_year=adm_year,
                course_code=course_code,
                previous_school=previous_school,
                previous_board=previous_board,
                previous_passing_year=previous_passing_year,
                previous_marks_percentage=previous_marks_percentage,
                entrance_exam_name=entrance_exam_name,
                entrance_exam_score=entrance_exam_score
            )
            
            db.session.add(new_student)
            db.session.commit()
            flash(f'Student {full_name} enrolled successfully! System Generated Registration ID: {reg_id}', 'success')
            
        elif action == 'delete':
            student_id = request.form.get('student_id')
            student = User.query.get(student_id)
            if student and student.role == 'student':
                # Delete associated records
                Enrollment.query.filter_by(student_id=student.id).delete()
                FeeRecord.query.filter_by(student_id=student.id).delete()
                DocumentRequest.query.filter_by(student_id=student.id).delete()
                PlacementApplication.query.filter_by(student_id=student.id).delete()
                AttendanceRecord.query.filter_by(student_id=student.id).delete()
                ExamResult.query.filter_by(student_id=student.id).delete()
                AIRiskAlert.query.filter_by(student_id=student.id).delete()
                
                disp_id = student.registration_id or f"ID #{student.id}"
                disp_name = student.name
                db.session.delete(student)
                db.session.commit()
                flash(f'Student {disp_name} ({disp_id}) has been permanently deleted.', 'warning')

        elif action == 'suspend':
            student_id = request.form.get('student_id')
            student = User.query.get(student_id)
            if student:
                student.status = 'suspended' if student.status == 'active' else 'active'
                db.session.commit()
                flash(f'Student {student.name} status updated to {student.status}.', 'info')
                
        elif action == 'promote':
            student_id = request.form.get('student_id')
            student = User.query.get(student_id)
            if student:
                student.semester = min(8, student.semester + 1)
                db.session.commit()
                flash(f'Student {student.name} promoted to Semester {student.semester}.', 'success')
                
    students = User.query.filter_by(role='student').all()
    courses = Course.query.all()
    departments = Department.query.all()
    institution = Institution.query.first()
    return render_template('hod/students.html', students=students, courses=courses, departments=departments, institution=institution)

@hod_bp.route('/faculties', methods=['GET', 'POST'])
def faculty_management():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            # Section 1: Personal & Identification Details
            first_name = request.form.get('first_name', '')
            middle_name = request.form.get('middle_name', '')
            last_name = request.form.get('last_name', '')
            full_name = f"{first_name} {middle_name} {last_name}".replace("  ", " ").strip() or request.form.get('name', 'Faculty Member')
            
            dob = request.form.get('dob')
            gender = request.form.get('gender', 'Male')
            nationality = request.form.get('nationality', 'Indian')
            category = request.form.get('category', 'General')
            govt_id_type = request.form.get('govt_id_type', 'PAN')
            govt_id_number = request.form.get('govt_id_number')
            biometric_id = request.form.get('biometric_id')
            
            # Section 2: Contact & Emergency Details
            phone = request.form.get('phone') or request.form.get('student_phone')
            personal_email = request.form.get('personal_email')
            official_email = request.form.get('email')
            permanent_address = request.form.get('permanent_address')
            current_address = request.form.get('current_address')
            emergency_contact_name = request.form.get('emergency_contact_name')
            emergency_contact_phone = request.form.get('emergency_contact_phone')
            emergency_contact_relation = request.form.get('emergency_contact_relation')
            
            # Section 3: Academic & Professional Background
            qualifications = request.form.get('qualifications')
            specialization = request.form.get('specialization')
            work_experience_years = request.form.get('work_experience_years', type=float, default=0.0)
            research_publications = request.form.get('research_publications')
            
            # Section 4: College Assignment Details
            designation = request.form.get('designation', 'Assistant Professor')
            dept = request.form.get('department', 'Computer Science & Engineering')
            joining_date = request.form.get('joining_date', '2026-01-15')
            joining_year = int(joining_date[:4]) if joining_date and len(joining_date) >= 4 else 2026
            
            # Auto-generate Employee ID e.g. NU26FAC001
            emp_id = generate_employee_id(dept_code='FAC', joining_year=joining_year)
            hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
            
            # Section 5: Financial & Payroll Details
            bank_name = request.form.get('bank_name')
            bank_account_number = request.form.get('bank_account_number')
            ifsc_code = request.form.get('ifsc_code')
            basic_salary = request.form.get('basic_salary', type=float, default=85000.0)
            pf_pension_number = request.form.get('pf_pension_number')
            
            new_fac = User(
                name=full_name,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=official_email,
                password=hashed_pw,
                role='faculty',
                department=dept,
                employee_id=emp_id,
                dob=dob,
                gender=gender,
                nationality=nationality,
                category=category,
                govt_id_type=govt_id_type,
                govt_id_number=govt_id_number,
                biometric_id=biometric_id,
                student_phone=phone,
                phone=phone,
                personal_email=personal_email,
                permanent_address=permanent_address,
                current_address=current_address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                emergency_contact_relation=emergency_contact_relation,
                qualifications=qualifications,
                specialization=specialization,
                work_experience_years=work_experience_years,
                research_publications=research_publications,
                designation=designation,
                joining_date=joining_date,
                bank_name=bank_name,
                bank_account_number=bank_account_number,
                ifsc_code=ifsc_code,
                basic_salary=basic_salary,
                pf_pension_number=pf_pension_number
            )
            
            db.session.add(new_fac)
            db.session.commit()
            flash(f'Faculty member {full_name} onboarded successfully! System Employee ID: {emp_id}', 'success')
            
        elif action == 'suspend':
            fac_id = request.form.get('faculty_id')
            fac = User.query.get(fac_id)
            if fac and fac.role == 'faculty':
                fac.status = 'suspended' if fac.status == 'active' else 'active'
                db.session.commit()
                flash(f'Faculty {fac.name} status updated to {fac.status}.', 'info')
                
        elif action == 'delete':
            fac_id = request.form.get('faculty_id')
            fac = User.query.get(fac_id)
            if fac and fac.role == 'faculty':
                # Unlink subjects & slots
                Subject.query.filter_by(faculty_id=fac.id).update({'faculty_id': None})
                TimetableSlot.query.filter_by(faculty_id=fac.id).delete()
                
                disp_emp_id = fac.employee_id or f"ID #{fac.id}"
                disp_name = fac.name
                db.session.delete(fac)
                db.session.commit()
                flash(f'Faculty member {disp_name} ({disp_emp_id}) permanently removed.', 'warning')
            
    faculties = User.query.filter_by(role='faculty').all()
    subjects = Subject.query.all()
    departments = Department.query.all()
    institution = Institution.query.first()
    return render_template('hod/faculties.html', faculties=faculties, subjects=subjects, departments=departments, institution=institution)

@hod_bp.route('/curriculum', methods=['GET', 'POST'])
def curriculum():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_subject':
            name = request.form.get('name')
            code = request.form.get('code').upper()
            course_id = request.form.get('course_id', type=int)
            sem = request.form.get('semester', type=int, default=1)
            faculty_id = request.form.get('faculty_id', type=int)
            credits_val = request.form.get('credits', type=int, default=4)
            summary_val = request.form.get('syllabus_summary', 'Covers core principles and lab exercises.')
            
            new_sub = Subject(
                name=name,
                code=code,
                course_id=course_id,
                faculty_id=faculty_id,
                semester=sem,
                credits=credits_val,
                syllabus_summary=summary_val,
                syllabus_status='Approved',
                completion_percentage=0.0
            )
            db.session.add(new_sub)
            db.session.commit()
            
            # Automatically create standard 5-module curriculum structure
            module_titles = [
                f"Module 1: Foundational Principles of {name}",
                f"Module 2: Architectural Frameworks & Core Theory",
                f"Module 3: Advanced Optimization & Algorithms",
                f"Module 4: Applied Implementations & Lab Projects",
                f"Module 5: Emerging Innovations & Capstone Applications"
            ]

            for m_title in module_titles:
                mod = Module(subject_id=new_sub.id, title=m_title)
                db.session.add(mod)
                db.session.commit()
                
                u1 = Unit(module_id=mod.id, title=f"Unit: Lecture Notes & Resources")
                db.session.add(u1)
                db.session.commit()
            
            flash(f'Subject {name} ({code}) added to curriculum with 5 standard modules.', 'success')

        elif action == 'review_syllabus':
            subject_id = request.form.get('subject_id')
            status_val = request.form.get('syllabus_status')
            feedback = request.form.get('feedback', '')
            
            subj = Subject.query.get(subject_id)
            if subj:
                subj.syllabus_status = status_val
                if feedback:
                    subj.syllabus_summary = feedback
                db.session.commit()
                flash(f'Syllabus review for {subj.name} updated to "{status_val}".', 'info')

        elif action == 'add_module':
            subject_id = request.form.get('subject_id', type=int)
            title = request.form.get('title')
            if subject_id and title:
                mod = Module(subject_id=subject_id, title=title)
                db.session.add(mod)
                db.session.commit()
                flash(f'Syllabus module "{title}" added successfully.', 'success')

        elif action == 'delete_subject':
            subject_id = request.form.get('subject_id')
            subj = Subject.query.get(subject_id)
            if subj:
                code_disp = subj.code
                db.session.delete(subj)
                db.session.commit()
                flash(f'Subject {code_disp} removed from curriculum.', 'warning')

    subjects = Subject.query.all()
    courses = Course.query.all()
    faculties = User.query.filter_by(role='faculty').all()
    return render_template('hod/curriculum.html', subjects=subjects, courses=courses, faculties=faculties)

@hod_bp.route('/attendance-analytics')
def attendance_analytics():
    students = User.query.filter_by(role='student').all()
    proxy_anomalies = sum(1 for s in students if s.attendance_percentage < 70)
    return render_template('hod/attendance_analytics.html', students=students, proxy_anomalies=proxy_anomalies)

@hod_bp.route('/timetable', methods=['GET', 'POST'])
def timetable():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'auto_generate':
            success, msg = AISchedulerService.generate_optimal_timetable()
            flash(msg, 'success' if success else 'danger')
            
    slots = TimetableSlot.query.order_by(TimetableSlot.day, TimetableSlot.start_time).all()
    subjects = Subject.query.all()
    faculties = User.query.filter_by(role='faculty').all()
    matrix, legend, periods = AISchedulerService.get_structured_grid(slots)
    import datetime
    today_name = datetime.datetime.now().strftime('%A')
    return render_template('hod/timetable.html', slots=slots, matrix=matrix, legend=legend, periods=periods, today_name=today_name, subjects=subjects, faculties=faculties)

@hod_bp.route('/placement')
def placement():
    drives = PlacementDrive.query.all()
    students = User.query.filter_by(role='student').all()
    return render_template('hod/placement.html', drives=drives, students=students)

@hod_bp.route('/documents', methods=['GET', 'POST'])
def documents():
    if request.method == 'POST':
        req_id = request.form.get('request_id')
        doc_req = DocumentRequest.query.get(req_id)
        if doc_req:
            doc_req.status = 'Approved'
            doc_req.hash_code = hashlib.sha256(f"{doc_req.id}-{doc_req.student_id}-{doc_req.doc_type}".encode()).hexdigest()[:16].upper()
            db.session.commit()
            flash(f'Document request approved. Verification Hash: {doc_req.hash_code}', 'success')
            
    requests_list = DocumentRequest.query.all()
    return render_template('hod/documents.html', requests_list=requests_list)

@hod_bp.route('/reports')
def reports():
    total_students = User.query.filter_by(role='student').count()
    return render_template('hod/reports.html', total_students=total_students)

@hod_bp.route('/calendar')
@login_required
def calendar():
    subjects = Subject.query.join(Course).filter(Course.department == current_user.department).all()
    upcoming_exams = Exam.query.join(Subject).join(Course).filter(Course.department == current_user.department).order_by(Exam.date.asc()).limit(8).all()
    return render_template('hod/calendar.html', subjects=subjects, upcoming_exams=upcoming_exams)

@hod_bp.route('/calendar/create', methods=['POST'])
@hod_bp.route('/create_event', methods=['POST'])
@login_required
def create_event():
    title = request.form.get('title')
    description = request.form.get('description', '')
    date_str = request.form.get('date')
    target_role = request.form.get('target_role', 'all')
    event_type = request.form.get('event_type', 'announcement')
    subject_id = request.form.get('subject_id')

    if not title or not date_str:
        flash('Event title and date are required.', 'danger')
        return redirect(url_for('hod.calendar'))

    try:
        ev_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('hod.calendar'))

    event_title = f"[EXAM] {title}" if event_type == 'exam' and not title.startswith('[EXAM]') else title

    new_event = Event(
        title=event_title,
        description=description,
        date=ev_date,
        created_by=current_user.id,
        target_role=target_role,
        subject_id=int(subject_id) if subject_id and subject_id.isdigit() else None,
        user_id=current_user.id if target_role == 'personal' else None
    )
    db.session.add(new_event)

    # If tagged as exam with a subject, also add to Exam table
    if event_type == 'exam' and subject_id and subject_id.isdigit():
        new_exam = Exam(
            title=title,
            subject_id=int(subject_id),
            date=ev_date,
            max_marks=float(request.form.get('max_marks', 100)),
            type=request.form.get('exam_category', 'Internal'),
            status='Scheduled'
        )
        db.session.add(new_exam)

    # Dispatch Notifications across dashboards
    if target_role != 'personal':
        if event_type == 'exam':
            notif_title = f"📢 Exam Scheduled: {title}"
        else:
            notif_title = f"🏛️ Department Notice: {title}"

        detail_snippet = f" - {description}" if description else ""
        notif_msg = f"HOD {current_user.name} posted for {ev_date.strftime('%b %d, %Y')}: {title}{detail_snippet}"

        # 1. Notify Faculty
        if target_role in ['all', 'faculty']:
            fac_query = User.query.filter_by(role='faculty').filter(User.id != current_user.id)
            if current_user.department:
                fac_recipients = fac_query.filter(
                    (User.department == current_user.department) | (User.department.is_(None))
                ).all()
                if not fac_recipients:
                    fac_recipients = fac_query.all()
            else:
                fac_recipients = fac_query.all()

            for fac in fac_recipients:
                db.session.add(Notification(
                    user_id=fac.id,
                    title=notif_title,
                    message=notif_msg,
                    link=url_for('faculty.calendar')
                ))

        # 2. Notify Students
        if target_role in ['all', 'student']:
            stu_query = User.query.filter_by(role='student')
            if current_user.department:
                stu_recipients = stu_query.filter(
                    (User.department == current_user.department) | (User.department.is_(None))
                ).all()
                if not stu_recipients:
                    stu_recipients = stu_query.all()
            else:
                stu_recipients = stu_query.all()

            # If subject specified, ensure enrolled students are included
            if subject_id and subject_id.isdigit():
                enrolled_students = User.query.join(Enrollment, Enrollment.student_id == User.id).filter(Enrollment.subject_id == int(subject_id)).all()
                all_students = {s.id: s for s in (stu_recipients + enrolled_students)}.values()
            else:
                all_students = stu_recipients

            for stu in all_students:
                db.session.add(Notification(
                    user_id=stu.id,
                    title=notif_title,
                    message=notif_msg,
                    link=url_for('student.calendar')
                ))

    db.session.commit()
    flash(f'Department event "{event_title}" published and notifications dispatched successfully!', 'success')
    return redirect(url_for('hod.calendar'))

