from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Event, Enrollment, Subject
from datetime import datetime

events_bp = Blueprint('events', __name__)

@events_bp.route('/api/events')
@login_required
def get_events():
    role = current_user.role
    dept = current_user.department
    
    query = Event.query
    
    if role == 'hod':
        # HOD sees everything in their department? 
        # Actually user said "HOD: Show all events"
        # But for department-isolated HOD, they should see events they created or events in their dept.
        events = query.filter(
            (Event.created_by == current_user.id) | 
            (Event.target_role == 'all')
        ).all()
        
    elif role == 'faculty':
        # Faculty sees:
        # 1. HOD events (target=faculty/all)
        # 2. Their own personal events
        # 3. Events they created
        events = query.filter(
            ((Event.target_role.in_(['faculty', 'all'])) & (Event.created_by.in_(
                [u.id for u in db.session.query(User.id).filter_by(role='hod', department=dept).all()]
            ))) |
            (Event.created_by == current_user.id) |
            ((Event.target_role == 'personal') & (Event.user_id == current_user.id))
        ).all()
        
    elif role == 'student':
        # Student sees:
        # 1. HOD events (target=student/all)
        # 2. Faculty events (based on enrolled subjects)
        # 3. Their personal events
        enrolled_subject_ids = [e.subject_id for e in current_user.enrollments]
        
        events = query.filter(
            ((Event.target_role.in_(['student', 'all'])) & (Event.created_by.in_(
                [u.id for u in db.session.query(User.id).filter_by(role='hod', department=dept).all()]
            ))) |
            ((Event.subject_id.in_(enrolled_subject_ids)) & (Event.target_role != 'personal')) |
            ((Event.target_role == 'personal') & (Event.user_id == current_user.id))
        ).all()
    
    results = []
    for event in events:
        # Color coding
        color = '#ef4444' # Red for HOD
        if event.creator.role == 'faculty':
            color = '#3b82f6' # Blue for Faculty
        if event.target_role == 'personal':
            color = '#10b981' # Green for Personal
            
        results.append({
            'id': event.id,
            'title': event.title,
            'start': event.date.isoformat(),
            'description': event.description,
            'backgroundColor': color,
            'borderColor': color,
            'allDay': True
        })
        
    return jsonify(results)

# Import User here to avoid circular dependencies if needed, 
# but models is already imported.
from models import User
