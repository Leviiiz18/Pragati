from flask import Blueprint, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Event, Enrollment, Subject, Assignment, Exam, AttendanceRecord, Module, Course
from datetime import datetime, date

events_bp = Blueprint('events', __name__)

@events_bp.route('/api/events')
@login_required
def get_events():
    role = current_user.role
    dept = current_user.department
    results = []

    # -------------------------------------------------------------
    # 1. EXPLICIT EVENTS & BROADCASTS (Event Table)
    # -------------------------------------------------------------
    event_query = Event.query

    if role in ['super_admin', 'principal']:
        events = event_query.all()
    elif role == 'hod':
        # HOD sees:
        # - Events they created
        # - Events broadcast to all
        # - Events created by faculty in their department
        # - Their personal reminders
        dept_faculty_ids = [u.id for u in User.query.filter_by(department=dept, role='faculty').all()]
        events = event_query.filter(
            (Event.created_by == current_user.id) |
            (Event.target_role == 'all') |
            (Event.created_by.in_(dept_faculty_ids)) |
            ((Event.target_role == 'personal') & (Event.user_id == current_user.id))
        ).all()
    elif role == 'faculty':
        # Faculty sees:
        # 1. HOD events (broadcast to faculty or all by HOD in department)
        # 2. Events created by this faculty (deadlines, quizzes, announcements)
        # 3. Faculty's own personal reminders (strictly private)
        dept_hod_ids = [u.id for u in User.query.filter_by(department=dept, role='hod').all()]
        events = event_query.filter(
            ((Event.target_role.in_(['faculty', 'all'])) & (Event.created_by.in_(dept_hod_ids))) |
            (Event.created_by == current_user.id) |
            ((Event.target_role == 'personal') & (Event.user_id == current_user.id))
        ).all()
    elif role == 'student':
        # Student sees:
        # 1. HOD events (broadcast to student or all by HOD in department)
        # 2. Faculty events/deadlines for subjects student is ENROLLED in
        # 3. Student's OWN personal reminders (strictly private, user_id == current_user.id)
        dept_hod_ids = [u.id for u in User.query.filter_by(department=dept, role='hod').all()]
        enrolled_subject_ids = [e.subject_id for e in current_user.enrollments]

        events = event_query.filter(
            ((Event.target_role.in_(['student', 'all'])) & (Event.created_by.in_(dept_hod_ids))) |
            ((Event.subject_id.in_(enrolled_subject_ids)) & (Event.target_role.in_(['student', 'all']))) |
            ((Event.target_role == 'personal') & (Event.user_id == current_user.id))
        ).all()
    else:
        events = []

    for ev in events:
        creator_role = ev.creator.role if ev.creator else 'unknown'
        creator_name = ev.creator.name if ev.creator else 'System'
        
        # Sleek modern pastel color coding & dot tagging
        if ev.target_role == 'personal':
            bg_color = '#ecfdf5' # Emerald Tint
            border_color = '#a7f3d0'
            text_color = '#065f46'
            dot_color = '#10b981'
            ev_type = 'Personal Reminder'
            prefix = '📌 '
        elif creator_role in ['hod', 'super_admin']:
            bg_color = '#fff1f2' # Rose Tint
            border_color = '#fecdd3'
            text_color = '#9f1239'
            dot_color = '#e11d48'
            ev_type = 'HOD / Department Broadcast'
            prefix = '🏛️ '
        else:
            bg_color = '#eff6ff' # Blue Tint
            border_color = '#bfdbfe'
            text_color = '#1e40af'
            dot_color = '#2563eb'
            ev_type = 'Faculty Course Notice'
            prefix = '👨‍🏫 '

        results.append({
            'id': f"event_{ev.id}",
            'db_id': ev.id,
            'title': f"{prefix}{ev.title}",
            'start': ev.date.isoformat(),
            'description': ev.description or 'No extra notes provided.',
            'backgroundColor': bg_color,
            'borderColor': border_color,
            'textColor': text_color,
            'allDay': True,
            'extendedProps': {
                'source': 'event',
                'type': ev_type,
                'creator': creator_name,
                'creator_role': creator_role,
                'dot_color': dot_color,
                'can_delete': (ev.created_by == current_user.id or ev.user_id == current_user.id or role in ['hod', 'super_admin']),
                'subject': ev.subject_rel.name if ev.subject_rel else None,
                'target': ev.target_role
            }
        })

    # -------------------------------------------------------------
    # 2. ASSIGNMENT DEADLINES (Assignment Table)
    # -------------------------------------------------------------
    assign_query = Assignment.query.join(Module).join(Subject)

    if role == 'student':
        enrolled_sub_ids = [e.subject_id for e in current_user.enrollments]
        assignments = assign_query.filter(Subject.id.in_(enrolled_sub_ids)).all()
    elif role == 'faculty':
        assignments = assign_query.filter(Subject.faculty_id == current_user.id).all()
    elif role in ['hod', 'super_admin']:
        assignments = assign_query.join(Course, Subject.course_id == Course.id).filter(Course.department == dept).all()
    else:
        assignments = []

    for a in assignments:
        subj = a.module.subject if a.module else None
        code = subj.code if subj else 'COURSE'
        results.append({
            'id': f"assign_{a.id}",
            'title': f"⏳ Due: {a.title} ({code})",
            'start': a.due_date.isoformat(),
            'description': f"Assignment Due Date\nInstructions: {a.instructions or 'None'}\nMax Points: {int(a.max_points)}",
            'backgroundColor': '#fffbeb', # Amber Tint
            'borderColor': '#fde68a',
            'textColor': '#92400e',
            'allDay': True,
            'extendedProps': {
                'source': 'assignment',
                'type': 'Assignment Deadline',
                'subject': subj.name if subj else code,
                'dot_color': '#d97706',
                'can_delete': False
            }
        })

    # -------------------------------------------------------------
    # 3. SCHEDULED EXAMS (Exam Table)
    # -------------------------------------------------------------
    exam_query = Exam.query.join(Subject)

    if role == 'student':
        enrolled_sub_ids = [e.subject_id for e in current_user.enrollments]
        exams = exam_query.filter(Subject.id.in_(enrolled_sub_ids)).all()
    elif role == 'faculty':
        exams = exam_query.filter(Subject.faculty_id == current_user.id).all()
    elif role in ['hod', 'super_admin']:
        exams = exam_query.join(Course, Subject.course_id == Course.id).filter(Course.department == dept).all()
    else:
        exams = []

    for ex in exams:
        code = ex.subject.code if ex.subject else 'COURSE'
        results.append({
            'id': f"exam_{ex.id}",
            'title': f"📝 Exam: {ex.title} ({code})",
            'start': ex.date.isoformat(),
            'description': f"{ex.type} Examination | Max Marks: {int(ex.max_marks)} | Bloom: {ex.bloom_level} | Status: {ex.status}",
            'backgroundColor': '#f5f3ff', # Purple Tint
            'borderColor': '#ddd6fe',
            'textColor': '#5b21b6',
            'allDay': True,
            'extendedProps': {
                'source': 'exam',
                'type': 'Academic Examination',
                'subject': ex.subject.name if ex.subject else code,
                'dot_color': '#7c3aed',
                'can_delete': False
            }
        })

    # -------------------------------------------------------------
    # 4. ATTENDANCE INTEGRATION
    # -------------------------------------------------------------
    if role == 'student':
        # Show Student's attendance records by date
        att_records = AttendanceRecord.query.filter_by(student_id=current_user.id).order_by(AttendanceRecord.date.desc()).all()
        for att in att_records:
            sub_code = att.subject.code if hasattr(att, 'subject') and att.subject else f"SUB{att.subject_id}"
            
            if att.status.lower() == 'present':
                att_bg = '#f0fdf4' # Soft Mint Green
                att_border = '#bbf7d0'
                att_text = '#166534'
                att_dot = '#10b981'
                att_title = f"✅ Present: {sub_code}"
            elif att.status.lower() == 'absent':
                att_bg = '#fef2f2' # Soft Rose
                att_border = '#fecaca'
                att_text = '#991b1b'
                att_dot = '#f43f5e'
                att_title = f"❌ Absent: {sub_code}"
            else:
                att_bg = '#fffbeb' # Soft Amber Late
                att_border = '#fde68a'
                att_text = '#92400e'
                att_dot = '#f59e0b'
                att_title = f"⚠️ Late: {sub_code}"

            results.append({
                'id': f"att_{att.id}",
                'title': att_title,
                'start': att.date.isoformat(),
                'description': f"Subject: {att.subject.name if hasattr(att, 'subject') and att.subject else sub_code}\nStatus: {att.status.capitalize()}{' (Proxy Suspect)' if att.is_proxy_suspect else ''}",
                'backgroundColor': att_bg,
                'borderColor': att_border,
                'textColor': att_text,
                'allDay': True,
                'extendedProps': {
                    'source': 'attendance',
                    'type': 'Attendance Record',
                    'status': att.status,
                    'dot_color': att_dot,
                    'can_delete': False
                }
            })

    elif role == 'faculty':
        # Show distinct dates where faculty marked attendance
        faculty_subject_ids = [s.id for s in current_user.subjects_taught]
        if faculty_subject_ids:
            # Group attendance sessions
            recent_logs = db.session.query(
                AttendanceRecord.date,
                AttendanceRecord.subject_id,
                db.func.count(AttendanceRecord.id).label('total_records')
            ).filter(
                AttendanceRecord.subject_id.in_(faculty_subject_ids)
            ).group_by(AttendanceRecord.date, AttendanceRecord.subject_id).all()

            for log in recent_logs:
                subj = Subject.query.get(log.subject_id)
                code = subj.code if subj else f"SUB{log.subject_id}"
                results.append({
                    'id': f"fac_att_{log.date}_{log.subject_id}",
                    'title': f"📋 Marked: {code} ({log.total_records} students)",
                    'start': log.date.isoformat(),
                    'description': f"Attendance registered for {subj.name if subj else code} with {log.total_records} student records.",
                    'backgroundColor': '#f0f9ff', # Sky Tint
                    'borderColor': '#bae6fd',
                    'textColor': '#075985',
                    'allDay': True,
                    'extendedProps': {
                        'source': 'attendance_faculty',
                        'type': 'Attendance Registry',
                        'dot_color': '#0284c7',
                        'can_delete': False
                    }
                })

    return jsonify(results)


@events_bp.route('/api/events/delete/<int:event_id>', methods=['POST', 'DELETE'])
@login_required
def delete_event(event_id):
    ev = Event.query.get_or_404(event_id)
    
    # Permission check: creator, owner, or HOD/admin
    if ev.created_by == current_user.id or ev.user_id == current_user.id or current_user.role in ['hod', 'super_admin']:
        db.session.delete(ev)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Event deleted successfully.'})
    
    return jsonify({'success': False, 'message': 'Unauthorized to delete this event.'}), 403
