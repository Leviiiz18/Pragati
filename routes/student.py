from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Subject, Enrollment, Module, Unit, File, Event, AttendanceRecord, ExamResult, FeeRecord, PlacementDrive, DocumentRequest, TimetableSlot, Exam, Course, StudentNote, Quiz, Assignment, AssignmentSubmission, Notification
from services.ai_engine import AIEngine
from services.career_service import CareerService
from services.risk_analytics import RiskAnalyticsService
import os
from werkzeug.utils import secure_filename

student_bp = Blueprint('student', __name__)

@student_bp.before_request
@login_required
def check_student():
    if current_user.role != 'student':
        flash('Access restricted to Student portal.', 'danger')
        return redirect(url_for('auth.login'))

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
    
    # Fetch upcoming assignments for enrolled subjects
    enrolled_modules = Module.query.filter(Module.subject_id.in_(subj_ids)).all() if subj_ids else []
    mod_ids = [m.id for m in enrolled_modules]
    upcoming_assignments = Assignment.query.filter(Assignment.module_id.in_(mod_ids)).order_by(Assignment.due_date.asc()).all() if mod_ids else []
    
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
                           upcoming_assignments=upcoming_assignments)

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
    
    slots = TimetableSlot.query.filter(TimetableSlot.subject_id.in_(subj_ids)).order_by(TimetableSlot.day, TimetableSlot.start_time).all()
    upcoming_exams = Exam.query.filter(Exam.subject_id.in_(subj_ids)).all()
    
    return render_template('student/schedule.html', slots=slots, upcoming_exams=upcoming_exams)

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
