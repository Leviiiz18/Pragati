import sys
import os

# Ensure pragati directory is in sys.path
PRAGATI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PRAGATI_DIR not in sys.path:
    sys.path.insert(0, PRAGATI_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app
from models import db, User, Event, AttendanceRecord, Subject, Exam

app = create_app()

def run_tests():
    with app.test_client() as client:
        # 1. Test Student Login & Calendar
        print("--- Testing Student ---")
        login_res = client.post('/login', data={'campus_id': 'student@studysync.pro', 'password': 'password123'}, follow_redirects=True)
        assert login_res.status_code == 200, f"Student login failed: {login_res.status_code}"
        
        cal_res = client.get('/student/calendar')
        assert cal_res.status_code == 200, f"Student calendar view failed: {cal_res.status_code}"
        print("Student calendar page loads: OK (200)")

        # Post a personal reminder
        rem_res = client.post('/student/calendar/create-reminder', data={
            'title': 'Test Private Study Reminder',
            'date': '2026-09-25',
            'description': 'Only visible to this student'
        }, follow_redirects=True)
        assert rem_res.status_code == 200, f"Create reminder failed: {rem_res.status_code}"
        print("Student personal reminder creation: OK (200)")

        # Check /api/events for student
        ev_res = client.get('/api/events')
        assert ev_res.status_code == 200, f"/api/events failed: {ev_res.status_code}"
        events = ev_res.get_json()
        print(f"Student /api/events count: {len(events)}")
        student_personal = [e for e in events if e.get('extendedProps', {}).get('type') == 'Personal Reminder']
        attendance_events = [e for e in events if e.get('extendedProps', {}).get('source') == 'attendance']
        print(f"  - Student personal reminders found: {len(student_personal)}")
        print(f"  - Attendance events found: {len(attendance_events)}")
        assert len(student_personal) > 0, "Personal reminder should be in student's events!"

        client.get('/logout')

        # 2. Test Faculty Login & Calendar
        print("\n--- Testing Faculty ---")
        login_fac = client.post('/login', data={'campus_id': 'faculty@studysync.pro', 'password': 'password123'}, follow_redirects=True)
        assert login_fac.status_code == 200, "Faculty login failed"

        cal_fac = client.get('/faculty/calendar')
        assert cal_fac.status_code == 200, f"Faculty calendar page failed: {cal_fac.status_code}"
        print("Faculty calendar page loads: OK (200)")

        # Check that Student's private reminder is NOT in Faculty's events
        fac_ev_res = client.get('/api/events')
        fac_events = fac_ev_res.get_json()
        student_private_in_fac = [e for e in fac_events if e.get('title') == '📌 Test Private Study Reminder']
        assert len(student_private_in_fac) == 0, "CRITICAL: Student private reminder leaked to Faculty!"
        print("Privacy verified: Student personal reminder is INVISIBLE to Faculty: OK")

        # Post a course deadline
        subj = Subject.query.first()
        subj_id = subj.id if subj else 1
        dead_res = client.post('/faculty/calendar/create', data={
            'title': 'Phase 1 Project Submission',
            'date': '2026-09-28',
            'target_role': 'student',
            'event_type': 'deadline',
            'subject_id': subj_id,
            'description': 'Submit via GitHub repository link'
        }, follow_redirects=True)
        assert dead_res.status_code == 200
        print("Faculty course deadline creation: OK (200)")

        client.get('/logout')

        # 3. Test HOD Login & Calendar
        print("\n--- Testing HOD ---")
        login_hod = client.post('/login', data={'campus_id': 'hod@studysync.pro', 'password': 'admin123'}, follow_redirects=True)
        assert login_hod.status_code == 200, "HOD login failed"

        cal_hod = client.get('/hod/calendar')
        assert cal_hod.status_code == 200, f"HOD calendar page failed: {cal_hod.status_code}"
        print("HOD calendar page loads: OK (200)")

        # Post an exam
        exam_res = client.post('/hod/calendar/create', data={
            'title': 'Mid-Term Department Examination',
            'date': '2026-09-30',
            'target_role': 'all',
            'event_type': 'exam',
            'subject_id': subj_id,
            'description': 'Main Auditorium, 10:00 AM'
        }, follow_redirects=True)
        assert exam_res.status_code == 200
        print("HOD exam broadcast creation: OK (200)")

        client.get('/logout')

        # 4. Re-check Student - verify HOD exam AND Faculty deadline are visible!
        print("\n--- Re-verifying Student receives HOD Exam & Faculty Deadline ---")
        client.post('/login', data={'campus_id': 'student@studysync.pro', 'password': 'password123'}, follow_redirects=True)
        re_ev = client.get('/api/events').get_json()
        titles = [e.get('title') for e in re_ev]
        print(f"Events visible to student: {titles}")
        has_exam = any('[EXAM]' in t or 'Mid-Term' in t for t in titles)
        has_deadline = any('[DEADLINE]' in t or 'Phase 1' in t for t in titles)
        print(f"HOD Exam visible to student: {has_exam}")
        print(f"Faculty Deadline visible to student: {has_deadline}")
        assert has_exam, "HOD Exam must be visible to student!"
        assert has_deadline, "Faculty Deadline must be visible to student!"

    print("\n🎉 ALL HIERARCHY & CALENDAR TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
