from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from models import db, User, Course, Subject, Module, Unit, File, AttendanceRecord, Exam, ExamResult, Enrollment, Event, Quiz, Assignment, AssignmentSubmission, Notification, Institution
from services.grading_service import GradingService
from services.ai_engine import AIEngine
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.before_request
@login_required
def check_faculty():
    if current_user.role not in ['faculty', 'hod', 'super_admin']:
        flash('Access restricted to Faculty portal.', 'danger')
        return redirect(url_for('auth.login'))

@faculty_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    inst = Institution.query.first() or Institution(name="Nitte University", code="NU", address="Mangaluru, Karnataka, India")
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    
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
            flash('Faculty credentials & contact records updated successfully.', 'success')
            return redirect(url_for('faculty.profile'))
            
    return render_template('faculty/profile.html', institution=inst, subjects=subjects)

@faculty_bp.route('/dashboard')
def dashboard():
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    if not subjects:
        subjects = Subject.query.all()
    today_date = date.today()
    my_events = Event.query.filter_by(created_by=current_user.id).all()
    
    enrolled_students_count = 0
    for s in subjects:
        enrolled_students_count += Enrollment.query.filter_by(subject_id=s.id).count()
        
    return render_template('faculty/dashboard.html',
                           subjects=subjects,
                           my_events=my_events,
                           enrolled_students_count=enrolled_students_count,
                           today_date=today_date)

@faculty_bp.route('/attendance', methods=['GET', 'POST'])
def attendance():
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    if not subjects:
        subjects = Subject.query.all()
    selected_subject_id = request.args.get('subject_id', type=int) or (subjects[0].id if subjects else None)
    
    students = []
    if selected_subject_id:
        enrollments = Enrollment.query.filter_by(subject_id=selected_subject_id).all()
        students = [e.student for e in enrollments]
        
    if request.method == 'POST':
        subject_id = int(request.form.get('subject_id'))
        attendance_data = request.form.getlist('present_students')
        att_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date() if request.form.get('date') else date.today()
        subject = Subject.query.get(subject_id)
        notifications_sent = 0
        
        enrollments = Enrollment.query.filter_by(subject_id=subject_id).all()
        for e in enrollments:
            is_present = str(e.student_id) in attendance_data
            status = 'present' if is_present else 'absent'
            
            existing = AttendanceRecord.query.filter_by(student_id=e.student_id, subject_id=subject_id, date=att_date).first()
            if existing:
                existing.status = status
            else:
                rec = AttendanceRecord(student_id=e.student_id, subject_id=subject_id, date=att_date, status=status)
                db.session.add(rec)
                
            all_records = AttendanceRecord.query.filter_by(student_id=e.student_id).all()
            if all_records:
                p_count = sum(1 for r in all_records if r.status == 'present')
                e.student.attendance_percentage = round((p_count / len(all_records)) * 100, 1)

            # Calculate subject-level attendance percentage
            subj_records = AttendanceRecord.query.filter_by(student_id=e.student_id, subject_id=subject_id).all()
            subj_present = sum(1 for r in subj_records if r.status == 'present')
            subj_total = len(subj_records)
            subj_pct = round((subj_present / subj_total) * 100, 1) if subj_total > 0 else 100.0

            # Real-Time Notification Dispatch to Student Station
            if not is_present or e.student.attendance_percentage < 75 or subj_pct < 75:
                if e.student.attendance_percentage < 75 or subj_pct < 75:
                    notif_title = f"⚠️ CRITICAL: Attendance Low in {subject.name if subject else 'Course'}"
                    notif_msg = (
                        f"Your attendance in {subject.name if subject else 'Subject'} is at {subj_pct}% "
                        f"(Overall: {e.student.attendance_percentage}%). This is below the mandatory 75% threshold "
                        f"for end-semester exam eligibility. Immediate makeup attendance required!"
                    )
                else:
                    notif_title = f"Absent Recorded: {subject.name if subject else 'Subject'}"
                    notif_msg = (
                        f"You were marked absent in {subject.name if subject else 'Subject'} on {att_date.strftime('%b %d, %Y')}. "
                        f"Your overall attendance is currently {e.student.attendance_percentage}%."
                    )

                new_notif = Notification(
                    user_id=e.student_id,
                    title=notif_title,
                    message=notif_msg,
                    link=url_for('student.attendance'),
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_notif)
                notifications_sent += 1
                
        db.session.commit()
        if notifications_sent > 0:
            flash(f'Attendance recorded. {notifications_sent} real-time low attendance / absence notifications dispatched to student stations.', 'info')
        else:
            flash('Attendance submitted successfully. Student percentages updated.', 'success')
        return redirect(url_for('faculty.attendance', subject_id=subject_id))

    return render_template('faculty/attendance.html', subjects=subjects, selected_subject_id=selected_subject_id, students=students)

@faculty_bp.route('/courses', methods=['GET', 'POST'])
def courses():
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    if not subjects:
        subjects = Subject.query.all()
    return render_template('faculty/courses.html', subjects=subjects)

@faculty_bp.route('/course/<int:subject_id>')
def course_detail(subject_id):
    subj = Subject.query.get_or_404(subject_id)
    modules = Module.query.filter_by(subject_id=subj.id).all()
    return render_template('faculty/course_detail.html', subject=subj, modules=modules)

@faculty_bp.route('/module/<int:module_id>', methods=['GET', 'POST'])
def module_detail(module_id):
    mod = Module.query.get_or_404(module_id)
    subj = mod.subject
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'upload_file':
            uploaded_file = request.files.get('file')
            
            if uploaded_file and uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                uploaded_file.save(file_path)
                
                unit = Unit.query.filter_by(module_id=mod.id).first()
                if not unit:
                    unit = Unit(module_id=mod.id, title="Unit Materials")
                    db.session.add(unit)
                    db.session.commit()
                    
                new_file = File(
                    unit_id=unit.id,
                    filename=filename,
                    filepath=f"/static/uploads/{filename}",
                    filetype="PDF / Lecture File"
                )
                db.session.add(new_file)
                db.session.commit()
                flash(f'File "{filename}" successfully uploaded to module!', 'success')
                return redirect(url_for('faculty.module_detail', module_id=mod.id))

        elif action == 'delete_file':
            file_id = request.form.get('file_id', type=int)
            file_obj = File.query.get(file_id)
            if file_obj:
                filename = file_obj.filename
                full_path = os.path.join(current_app.root_path, file_obj.filepath.lstrip('/'))
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except Exception:
                        pass
                db.session.delete(file_obj)
                db.session.commit()
                flash(f'File "{filename}" removed from module.', 'warning')
                return redirect(url_for('faculty.module_detail', module_id=mod.id))

        elif action == 'create_assignment':
            title = request.form.get('title')
            instructions = request.form.get('instructions')
            due_date_str = request.form.get('due_date')
            max_points = request.form.get('max_points', type=float) or 100.0
            
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else (date.today() + timedelta(days=7))
            
            attachment_path = None
            uploaded_file = request.files.get('attachment')
            if uploaded_file and uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'assignments')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                uploaded_file.save(file_path)
                attachment_path = f"/static/uploads/assignments/{filename}"

            new_assignment = Assignment(
                module_id=mod.id,
                title=title,
                instructions=instructions,
                due_date=due_date,
                max_points=max_points,
                attachment_path=attachment_path
            )
            db.session.add(new_assignment)
            db.session.commit()

            enrollments = Enrollment.query.filter_by(subject_id=subj.id).all()
            for e in enrollments:
                notif = Notification(
                    user_id=e.student_id,
                    title=f"New Assignment: {subj.code}",
                    message=f"Prof. {current_user.name} posted assignment '{title}' in {mod.title} (Due: {due_date.strftime('%b %d')}).",
                    link=f"/student/module/{mod.id}"
                )
                db.session.add(notif)
            db.session.commit()

            flash(f'Assignment "{title}" successfully created!', 'success')
            return redirect(url_for('faculty.module_detail', module_id=mod.id))

        elif action == 'delete_assignment':
            assignment_id = request.form.get('assignment_id', type=int)
            assign_obj = Assignment.query.get(assignment_id)
            if assign_obj:
                title = assign_obj.title
                db.session.delete(assign_obj)
                db.session.commit()
                flash(f'Assignment "{title}" deleted.', 'warning')
                return redirect(url_for('faculty.module_detail', module_id=mod.id))

        elif action == 'grade_submission':
            submission_id = request.form.get('submission_id', type=int)
            points_awarded = request.form.get('points_awarded', type=float)
            feedback = request.form.get('feedback', '')
            
            sub_obj = AssignmentSubmission.query.get(submission_id)
            if sub_obj:
                sub_obj.points_awarded = points_awarded
                sub_obj.feedback = feedback
                sub_obj.status = 'Graded'
                
                notif = Notification(
                    user_id=sub_obj.student_id,
                    title=f"Assignment Graded: {sub_obj.assignment.title}",
                    message=f"Your assignment submission was graded: {points_awarded}/{sub_obj.assignment.max_points}. Feedback: '{feedback}'",
                    link=f"/student/module/{mod.id}"
                )
                db.session.add(notif)
                db.session.commit()
                flash(f'Submission graded successfully!', 'success')
                return redirect(url_for('faculty.module_detail', module_id=mod.id))

    return render_template('faculty/module_detail.html', module=mod, subject=subj)

@faculty_bp.route('/evaluation', methods=['GET', 'POST'])
def evaluation():
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    if not subjects:
        subjects = Subject.query.all()
    if request.method == 'POST':
        submission = request.form.get('submission_text', '')
        assign_title = request.form.get('title', 'Assignment 1')
        result = GradingService.evaluate_submission(submission, assign_title)
        return jsonify(result)
        
    return render_template('faculty/evaluation.html', subjects=subjects)

@faculty_bp.route('/research')
def research():
    return render_template('faculty/research.html')

@faculty_bp.route('/calendar')
def calendar():
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    if not subjects:
        subjects = Subject.query.join(Course).filter(Course.department == current_user.department).all()
    upcoming_exams = Exam.query.join(Subject).filter(Subject.faculty_id == current_user.id).order_by(Exam.date.asc()).limit(5).all()
    return render_template('faculty/calendar.html', subjects=subjects, upcoming_exams=upcoming_exams)

@faculty_bp.route('/calendar/create', methods=['POST'])
@faculty_bp.route('/create_event', methods=['POST'])
def create_event():
    title = request.form.get('title')
    description = request.form.get('description', '')
    date_str = request.form.get('date')
    target_role = request.form.get('target_role', 'student')
    event_type = request.form.get('event_type', 'deadline')
    subject_id = request.form.get('subject_id')

    if not title or not date_str:
        flash('Title and date are required.', 'danger')
        return redirect(url_for('faculty.calendar'))

    try:
        ev_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('faculty.calendar'))

    subj_id = int(subject_id) if subject_id and subject_id.isdigit() else None
    
    prefix = ""
    if event_type == 'deadline':
        prefix = "[DEADLINE] "
    elif event_type == 'quiz':
        prefix = "[QUIZ] "
    elif event_type == 'exam':
        prefix = "[EXAM] "

    event_title = f"{prefix}{title}" if prefix and not title.startswith(prefix) else title

    new_event = Event(
        title=event_title,
        description=description,
        date=ev_date,
        created_by=current_user.id,
        target_role='personal' if target_role == 'personal' else 'student',
        subject_id=subj_id,
        user_id=current_user.id if target_role == 'personal' else None
    )
    db.session.add(new_event)

    # Notify enrolled students and department HOD
    if target_role == 'student':
        if subj_id:
            enrolled = Enrollment.query.filter_by(subject_id=subj_id).all()
            recipient_ids = list(set([e.student_id for e in enrolled]))
            subj = Subject.query.get(subj_id)
            subj_name = subj.code if subj else "Course"
        else:
            enrolled = Enrollment.query.join(Subject).filter(Subject.faculty_id == current_user.id).all()
            recipient_ids = list(set([e.student_id for e in enrolled]))
            if not recipient_ids and current_user.department:
                recipient_ids = [u.id for u in User.query.filter_by(role='student', department=current_user.department).all()]
            subj_name = "Department"

        for sid in recipient_ids:
            notif = Notification(
                user_id=sid,
                title=f"New Academic {event_type.capitalize()}: {title}",
                message=f"Prof. {current_user.name} posted '{title}' ({subj_name}) scheduled for {ev_date.strftime('%b %d, %Y')}.",
                link=url_for('student.calendar')
            )
            db.session.add(notif)

        # Notify HOD
        if current_user.department:
            hods = User.query.filter_by(role='hod', department=current_user.department).all()
            for h in hods:
                if h.id != current_user.id:
                    db.session.add(Notification(
                        user_id=h.id,
                        title=f"Faculty {event_type.capitalize()}: {title}",
                        message=f"Prof. {current_user.name} posted '{title}' for {ev_date.strftime('%b %d, %Y')}.",
                        link=url_for('hod.calendar')
                    ))

    db.session.commit()
    flash(f'Event "{event_title}" published and synced to enrolled students!', 'success')
    return redirect(url_for('faculty.calendar'))

