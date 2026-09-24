from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, User, Subject, Enrollment, Module, Unit, File, Event, AttendanceRecord, ExamResult, FeeRecord, PlacementDrive, DocumentRequest, TimetableSlot, Exam, Course, StudentNote, Quiz, Assignment, AssignmentSubmission, Notification, Institution
from services.ai_engine import AIEngine
from services.career_service import CareerService
from services.risk_analytics import RiskAnalyticsService
import os
from datetime import datetime, date
from werkzeug.utils import secure_filename

student_bp = Blueprint('student', __name__)

@student_bp.before_request
@login_required
def check_student():
    if current_user.role != 'student':
        flash('Access restricted to Student portal.', 'danger')
        return redirect(url_for('auth.login'))

@student_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    inst = Institution.query.first() or Institution(name="Nitte University", code="NU", address="Mangaluru, Karnataka, India")
    course_info = Course.query.filter_by(code=current_user.course_code or 'UCA').first()
    mentor = User.query.get(current_user.mentor_id) if current_user.mentor_id else None
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_contact':
            current_user.student_phone = request.form.get('student_phone', current_user.student_phone)
            current_user.parent_phone = request.form.get('parent_phone', current_user.parent_phone)
            current_user.personal_email = request.form.get('personal_email', current_user.personal_email)
            current_user.current_address = request.form.get('current_address', current_user.current_address)
            current_user.permanent_address = request.form.get('permanent_address', current_user.permanent_address)
            current_user.emergency_contact_name = request.form.get('emergency_contact_name', current_user.emergency_contact_name)
            current_user.emergency_contact_phone = request.form.get('emergency_contact_phone', current_user.emergency_contact_phone)
            current_user.emergency_contact_relation = request.form.get('emergency_contact_relation', current_user.emergency_contact_relation)
            db.session.commit()
            flash('Contact & Emergency records updated successfully in your student dossier.', 'success')
            return redirect(url_for('student.profile'))
            
    return render_template('student/profile.html', institution=inst, course_info=course_info, mentor=mentor)

def auto_enroll_student_if_needed():
    """Ensure student is enrolled in all subjects matching their semester and course."""
    existing = Enrollment.query.filter_by(student_id=current_user.id).all()
    if not existing:
        course = Course.query.filter_by(code=current_user.course_code or 'UCA').first()
        subjects = []
        if course:
            subjects = Subject.query.filter_by(course_id=course.id, semester=current_user.semester).all()
        if not subjects:
            subjects = Subject.query.all()
            
        for s in subjects:
            db.session.add(Enrollment(student_id=current_user.id, subject_id=s.id))
        db.session.commit()

@student_bp.route('/dashboard')
def dashboard():
    auto_enroll_student_if_needed()
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subjects = [e.subject for e in enrollments]
    subj_ids = [e.subject_id for e in enrollments]
    
    # Fetch all modules and assignments for enrolled subjects
    enrolled_modules = Module.query.filter(Module.subject_id.in_(subj_ids)).all() if subj_ids else []
    mod_ids = [m.id for m in enrolled_modules]
    assignments = Assignment.query.filter(Assignment.module_id.in_(mod_ids)).order_by(Assignment.due_date.asc()).all() if mod_ids else []
    
    # Submissions by this student
    submissions = AssignmentSubmission.query.filter_by(student_id=current_user.id).all()
    submitted_assignment_ids = {s.assignment_id: s for s in submissions}
    
    today = date.today()
    
    # Structured deadlines list with status, days left, urgency
    deadlines = []
    for a in assignments:
        sub = submitted_assignment_ids.get(a.id)
        days_left = (a.due_date - today).days if a.due_date else 999
        status = 'Graded' if (sub and sub.status == 'Graded') else ('Submitted' if sub else ('Overdue' if days_left < 0 else ('Urgent' if days_left <= 2 else 'Pending')))
        deadlines.append({
            'type': 'Assignment',
            'id': a.id,
            'title': a.title,
            'subject_code': a.module.subject.code if (a.module and a.module.subject) else 'COURSE',
            'subject_name': a.module.subject.name if (a.module and a.module.subject) else '',
            'subject_id': a.module.subject_id if a.module else None,
            'due_date': a.due_date,
            'days_left': days_left,
            'points': int(a.max_points or 100),
            'status': status,
            'submission': sub,
            'instructions': a.instructions or ''
        })
    
    # Upcoming exams
    upcoming_exams = Exam.query.filter(Exam.subject_id.in_(subj_ids)).filter(Exam.date >= today).order_by(Exam.date.asc()).limit(5).all() if subj_ids else []
    for ex in upcoming_exams:
        days_left = (ex.date - today).days
        deadlines.append({
            'type': 'Exam',
            'id': ex.id,
            'title': ex.title,
            'subject_code': ex.subject.code if ex.subject else 'EXAM',
            'subject_name': ex.subject.name if ex.subject else '',
            'subject_id': ex.subject_id,
            'due_date': ex.date,
            'days_left': days_left,
            'points': int(ex.max_marks or 100),
            'status': 'Urgent' if days_left <= 3 else 'Scheduled',
            'submission': None,
            'instructions': f"Max Marks: {int(ex.max_marks)} | Type: {ex.type} | Bloom: {ex.bloom_level}"
        })
        
    # Sort all deadlines chronologically
    deadlines.sort(key=lambda d: d['days_left'])
    
    # Today's timetable slots
    day_name = datetime.now().strftime('%A')
    today_slots = TimetableSlot.query.filter(TimetableSlot.subject_id.in_(subj_ids)).filter_by(day=day_name).order_by(TimetableSlot.start_time.asc()).all() if subj_ids else []
    if not today_slots and subj_ids:
        # Show timetable preview if no slots specifically for today
        today_slots = TimetableSlot.query.filter(TimetableSlot.subject_id.in_(subj_ids)).order_by(TimetableSlot.day.asc(), TimetableSlot.start_time.asc()).limit(4).all()
        
    # Calculate classes needed to reach 75% attendance
    att_pct = current_user.attendance_percentage
    classes_needed = 0
    if att_pct < 75:
        classes_needed = int((75 * 40 - att_pct * 40 / 100) / 25) + 3

    fee_rec = FeeRecord.query.filter_by(student_id=current_user.id).first()
    placements = PlacementDrive.query.filter_by(status='Active').all()
    events = Event.query.filter(
        (Event.target_role == 'all') | 
        (Event.target_role == 'student') | 
        (Event.user_id == current_user.id)
    ).all()

    return render_template('student/dashboard.html',
                           subjects=subjects,
                           classes_needed=classes_needed,
                           fee_rec=fee_rec,
                           placements=placements,
                           events=events,
                           deadlines=deadlines,
                           today_slots=today_slots,
                           today_date=today,
                           day_name=day_name,
                           upcoming_assignments=assignments)

@student_bp.route('/courses')
def courses():
    auto_enroll_student_if_needed()
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subjects = [e.subject for e in enrollments]
    course_info = Course.query.filter_by(code=current_user.course_code or 'UCA').first()
    
    return render_template('student/courses.html', subjects=subjects, course_info=course_info)

@student_bp.route('/course/<int:subject_id>')
def course_detail(subject_id):
    subj = Subject.query.get_or_404(subject_id)
    modules = Module.query.filter_by(subject_id=subj.id).all()
    student_notes = StudentNote.query.filter_by(student_id=current_user.id, subject_id=subj.id).order_by(StudentNote.created_at.desc()).all()
    
    return render_template('student/course_detail.html', subject=subj, modules=modules, notes=student_notes)

@student_bp.route('/module/<int:module_id>', methods=['GET', 'POST'])
def module_detail(module_id):
    mod = Module.query.get_or_404(module_id)
    subj = mod.subject
    student_notes = StudentNote.query.filter_by(student_id=current_user.id, subject_id=subj.id).order_by(StudentNote.created_at.desc()).all()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'submit_assignment':
            assignment_id = request.form.get('assignment_id', type=int)
            submission_text = request.form.get('submission_text', '')
            
            file_path = None
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'submissions')
                os.makedirs(upload_folder, exist_ok=True)
                full_path = os.path.join(upload_folder, filename)
                uploaded_file.save(full_path)
                file_path = f"/static/uploads/submissions/{filename}"

            existing_sub = AssignmentSubmission.query.filter_by(assignment_id=assignment_id, student_id=current_user.id).first()
            if existing_sub:
                existing_sub.submission_text = submission_text
                if file_path:
                    existing_sub.file_path = file_path
                existing_sub.submitted_at = datetime.utcnow()
                existing_sub.status = 'Turned In'
            else:
                new_sub = AssignmentSubmission(
                    assignment_id=assignment_id,
                    student_id=current_user.id,
                    submission_text=submission_text,
                    file_path=file_path,
                    status='Turned In'
                )
                db.session.add(new_sub)

            db.session.commit()
            flash('Assignment successfully turned in!', 'success')
            return redirect(url_for('student.module_detail', module_id=mod.id))

    return render_template('student/module_detail.html', module=mod, subject=subj, notes=student_notes)

@student_bp.route('/notes', methods=['GET', 'POST'])
def notes():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_note':
            title = request.form.get('title')
            content = request.form.get('content', '')
            category = request.form.get('category', 'General Notes')
            subject_id = request.form.get('subject_id', type=int)
            attachment_type = request.form.get('attachment_type', 'Text')
            attachment_path = None

            # 1. File Upload (Image / PDF / File)
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'student_notes')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                uploaded_file.save(file_path)
                attachment_path = f"/static/uploads/student_notes/{filename}"
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                    attachment_type = 'Image'
                elif filename.lower().endswith('.pdf'):
                    attachment_type = 'PDF'
                else:
                    attachment_type = 'Document'

            # 2. Base64 Drawing or Camera Data
            drawing_data = request.form.get('drawing_data')
            if drawing_data and drawing_data.startswith('data:image'):
                attachment_path = drawing_data
                attachment_type = 'Camera Snapshot' if 'camera' in category.lower() or 'photo' in category.lower() else 'Whiteboard Scribble'

            new_note = StudentNote(
                student_id=current_user.id,
                subject_id=subject_id,
                title=title,
                content=content,
                category=category,
                attachment_path=attachment_path,
                attachment_type=attachment_type
            )
            db.session.add(new_note)
            db.session.commit()
            flash('Personal Note saved successfully to your Vault!', 'success')
            
            next_url = request.form.get('next_url')
            if next_url:
                return redirect(next_url)
            
        elif action == 'delete_note':
            note_id = request.form.get('note_id', type=int)
            note = StudentNote.query.get(note_id)
            if note and note.student_id == current_user.id:
                db.session.delete(note)
                db.session.commit()
                flash('Personal Note deleted.', 'warning')

    all_notes = StudentNote.query.filter_by(student_id=current_user.id).order_by(StudentNote.created_at.desc()).all()
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subjects = [e.subject for e in enrollments]
    
    return render_template('student/notes.html', notes=all_notes, subjects=subjects)

@student_bp.route('/grades')
def grades():
    exam_results = ExamResult.query.filter_by(student_id=current_user.id).all()
    upcoming_exams = Exam.query.filter_by(status='Scheduled').all()
    
    return render_template('student/grades.html', exam_results=exam_results, upcoming_exams=upcoming_exams)

@student_bp.route('/schedule')
def schedule():
    auto_enroll_student_if_needed()
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subj_ids = [e.subject_id for e in enrollments]
    
    slots = TimetableSlot.query.filter(TimetableSlot.subject_id.in_(subj_ids)).order_by(TimetableSlot.day, TimetableSlot.start_time).all() if subj_ids else TimetableSlot.query.all()
    upcoming_exams = Exam.query.filter(Exam.subject_id.in_(subj_ids)).all() if subj_ids else Exam.query.all()
    
    from services.scheduler import AISchedulerService
    import datetime
    matrix, legend, periods = AISchedulerService.get_structured_grid(slots)
    today_name = datetime.datetime.now().strftime('%A')
    
    return render_template('student/schedule.html', slots=slots, matrix=matrix, legend=legend, periods=periods, today_name=today_name, upcoming_exams=upcoming_exams)

@student_bp.route('/fees', methods=['GET', 'POST'])
def fees():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'pay_fee':
            fee_rec = FeeRecord.query.filter_by(student_id=current_user.id).first()
            if fee_rec:
                fee_rec.paid_amount = fee_rec.total_amount
                fee_rec.status = 'Paid'
                current_user.fee_status = 'Clear'
                db.session.commit()
                flash('Fee payment recorded successfully! Official receipt generated.', 'success')

    fee_rec = FeeRecord.query.filter_by(student_id=current_user.id).first()
    if not fee_rec:
        fee_rec = FeeRecord(student_id=current_user.id, semester=current_user.semester, total_amount=75000.0, paid_amount=75000.0, due_date=current_user.dob or '2026-08-31', status='Paid')
        db.session.add(fee_rec)
        db.session.commit()
        
    return render_template('student/fees.html', fee_rec=fee_rec)

@student_bp.route('/documents', methods=['GET', 'POST'])
def documents():
    if request.method == 'POST':
        doc_type = request.form.get('doc_type', 'Bonafide Certificate')
        new_req = DocumentRequest(student_id=current_user.id, doc_type=doc_type, status='Pending')
        db.session.add(new_req)
        db.session.commit()
        flash(f'Request for "{doc_type}" submitted to HOD office. Request ID: #{new_req.id}', 'success')

    requests_list = DocumentRequest.query.filter_by(student_id=current_user.id).order_by(DocumentRequest.requested_at.desc()).all()
    return render_template('student/documents.html', requests_list=requests_list)

@student_bp.route('/ai-tutor', methods=['GET', 'POST'])
def ai_tutor():
    auto_enroll_student_if_needed()
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subjects = [e.subject for e in enrollments]
    
    if request.method == 'POST':
        user_query = request.form.get('query', '')
        subj_id = request.form.get('subject_id', type=int)
        
        system_prompt = f"You are an institution-specific AI Tutor for student {current_user.name}. Answer using curriculum notes, textbook principles, and academic rigor."
        response_text = AIEngine.generate_completion(user_query, system_message=system_prompt)
        return jsonify({'status': 'success', 'answer': response_text})

    return render_template('student/ai_tutor.html', subjects=subjects)

@student_bp.route('/attendance')
def attendance():
    auto_enroll_student_if_needed()
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subject_attendance = []
    
    for e in enrollments:
        records = AttendanceRecord.query.filter_by(student_id=current_user.id, subject_id=e.subject_id).all()
        total = len(records)
        present = sum(1 for r in records if r.status == 'present')
        pct = round((present / max(1, total)) * 100, 1) if total > 0 else 85.0
        subject_attendance.append({
            'subject_name': e.subject.name,
            'code': e.subject.code,
            'total': total or 20,
            'present': present or 17,
            'percentage': pct
        })
        
    return render_template('student/attendance.html', subject_attendance=subject_attendance)

@student_bp.route('/career', methods=['GET', 'POST'])
def career():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'analyze_ats':
            target_role = request.form.get('role', 'Software Engineer')
            ats_result = CareerService.analyze_resume_ats(current_user, target_role)
            return jsonify(ats_result)

    drives = PlacementDrive.query.all()
    ats_data = CareerService.analyze_resume_ats(current_user)
    mock_questions = CareerService.generate_mock_interview_questions()
    return render_template('student/career.html', drives=drives, ats_data=ats_data, mock_questions=mock_questions)

@student_bp.route('/wellness')
def wellness():
    return render_template('student/wellness.html')

@student_bp.route('/calendar')
def calendar():
    enrolled_subject_ids = [e.subject_id for e in current_user.enrollments]
    subjects = Subject.query.filter(Subject.id.in_(enrolled_subject_ids)).all()
    upcoming_exams = Exam.query.filter(Exam.subject_id.in_(enrolled_subject_ids)).order_by(Exam.date.asc()).limit(5).all()
    my_reminders = Event.query.filter_by(user_id=current_user.id, target_role='personal').order_by(Event.date.asc()).all()
    
    total_att = AttendanceRecord.query.filter_by(student_id=current_user.id).count()
    present_att = AttendanceRecord.query.filter_by(student_id=current_user.id, status='present').count()
    absent_att = AttendanceRecord.query.filter_by(student_id=current_user.id, status='absent').count()
    att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 85.0

    return render_template(
        'student/calendar.html',
        subjects=subjects,
        upcoming_exams=upcoming_exams,
        my_reminders=my_reminders,
        total_att=total_att,
        present_att=present_att,
        absent_att=absent_att,
        att_pct=att_pct
    )

@student_bp.route('/calendar/create-reminder', methods=['POST'])
@student_bp.route('/create_personal_event', methods=['POST'])
def create_personal_event():
    title = request.form.get('title')
    description = request.form.get('description', '')
    date_str = request.form.get('date')
    subject_id = request.form.get('subject_id')

    if not title or not date_str:
        flash('Reminder title and date are required.', 'danger')
        return redirect(url_for('student.calendar'))

    try:
        ev_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('student.calendar'))

    new_event = Event(
        title=title,
        description=description,
        date=ev_date,
        created_by=current_user.id,
        target_role='personal',
        user_id=current_user.id,
        subject_id=int(subject_id) if subject_id and subject_id.isdigit() else None
    )
    db.session.add(new_event)
    db.session.commit()
    flash(f'Personal reminder "{title}" added to your private calendar!', 'success')
    return redirect(url_for('student.calendar'))

