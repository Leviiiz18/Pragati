from app import create_app
from models import db, User, Subject, TimetableSlot, AttendanceRecord
from datetime import date, timedelta, datetime

app = create_app()

def seed_timetable_and_attendance():
    with app.app_context():
        # Get demo student
        student = User.query.filter_by(role='student').first()
        if not student:
            print("No student found!")
            return
        
        # Get enrolled subjects
        subjects = [e.subject for e in student.enrollments]
        if not subjects:
            subjects = Subject.query.all()[:4]
            
        faculty = User.query.filter_by(role='faculty').first()
        faculty_id = faculty.id if faculty else 1

        print(f"Setting up timetable & attendance for {student.name} ({student.email}) with {len(subjects)} subjects")

        # 1. Clear existing slots & records for clean seed
        TimetableSlot.query.delete()
        AttendanceRecord.query.filter_by(student_id=student.id).delete()
        db.session.commit()

        # 2. Create structured Timetable Slots (2 per subject per week)
        # Schedule:
        # Mon: Period 2 (10:00 - 11:00) Subj 0, Period 4 (14:00 - 15:00) Subj 3
        # Tue: Period 2 (10:00 - 11:00) Subj 1
        # Wed: Period 1 (09:00 - 10:00) Subj 2
        # Thu: Period 2 (10:00 - 11:00) Subj 3, Period 4 (14:00 - 15:00) Subj 0
        # Fri: Period 3 (11:00 - 12:00) Subj 1, Period 4 (14:00 - 15:00) Subj 2

        slot_defs = [
            # Subj 0 (e.g. AIML101)
            {'subject': subjects[0], 'day': 'Monday', 'start': '10:00', 'end': '11:00', 'room': 'Room 201', 'is_lab': False},
            {'subject': subjects[0], 'day': 'Thursday', 'start': '14:00', 'end': '15:00', 'room': 'Room 201', 'is_lab': False},
            # Subj 1 (e.g. AIML102)
            {'subject': subjects[1], 'day': 'Tuesday', 'start': '10:00', 'end': '11:00', 'room': 'Lab 101', 'is_lab': True},
            {'subject': subjects[1], 'day': 'Friday', 'start': '11:00', 'end': '12:00', 'room': 'Lab 101', 'is_lab': True},
            # Subj 2 (e.g. CY101)
            {'subject': subjects[2], 'day': 'Wednesday', 'start': '09:00', 'end': '10:00', 'room': 'Room 304', 'is_lab': False},
            {'subject': subjects[2], 'day': 'Friday', 'start': '14:00', 'end': '15:00', 'room': 'Room 304', 'is_lab': False},
            # Subj 3 (e.g. CY102)
            {'subject': subjects[3], 'day': 'Monday', 'start': '14:00', 'end': '15:00', 'room': 'Lab 202', 'is_lab': True},
            {'subject': subjects[3], 'day': 'Thursday', 'start': '10:00', 'end': '11:00', 'room': 'Lab 202', 'is_lab': True},
        ]

        created_slots = {}
        for sdef in slot_defs:
            slot = TimetableSlot(
                day=sdef['day'],
                start_time=sdef['start'],
                end_time=sdef['end'],
                subject_id=sdef['subject'].id,
                faculty_id=sdef['subject'].faculty_id or faculty_id,
                room=sdef['room'],
                is_lab=sdef['is_lab']
            )
            db.session.add(slot)
            db.session.flush()
            created_slots[(sdef['subject'].id, sdef['day'])] = slot

        db.session.commit()
        print(f"Created {len(slot_defs)} timetable slots.")

        # 3. Generate Class-by-Class Attendance Records from Aug 17, 2026 to Sep 30, 2026 (6 weeks)
        start_date = date(2026, 8, 17) # Monday
        end_date = date(2026, 9, 30)   # Wednesday

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Specific planned absent dates for realistic variation
        # Subj 0 (AIML101): Absent on 2026-09-03, 2026-09-24 (has pending concern)
        # Subj 1 (AIML102): Absent on 2026-09-15
        # Subj 2 (CY101): Absent on 2026-08-28, 2026-09-16 (resolved concern), 2026-09-25
        # Subj 3 (CY102): Absent on 2026-08-24, 2026-09-03, 2026-09-14, 2026-09-21, 2026-09-28 (shortage)

        absent_map = {
            subjects[0].id: [date(2026, 9, 3), date(2026, 9, 24)],
            subjects[1].id: [date(2026, 9, 15)],
            subjects[2].id: [date(2026, 8, 28), date(2026, 9, 16), date(2026, 9, 25)],
            subjects[3].id: [date(2026, 8, 24), date(2026, 9, 3), date(2026, 9, 14), date(2026, 9, 21), date(2026, 9, 28)],
        }

        total_records_created = 0
        curr = start_date
        while curr <= end_date:
            d_name = day_names[curr.weekday()]
            
            # Check which slots occur on this day of week
            for (sub_id, slot_day), slot in created_slots.items():
                if slot_day == d_name:
                    is_absent = (curr in absent_map.get(sub_id, []))
                    status = 'absent' if is_absent else 'present'
                    
                    concern_status = None
                    concern_reason = None
                    concern_created_at = None

                    # Set example concern statuses as requested
                    if sub_id == subjects[0].id and curr == date(2026, 9, 24):
                        concern_status = 'Pending'
                        concern_reason = 'Hospital visit for viral fever. Submitted doctor discharge slip to academic desk.'
                        concern_created_at = datetime(2026, 9, 24, 16, 30)
                    elif sub_id == subjects[2].id and curr == date(2026, 9, 16):
                        concern_status = 'Resolved'
                        concern_reason = 'Represented college at State Hackathon 2026. On-duty attendance approved by HOD.'
                        concern_created_at = datetime(2026, 9, 17, 10, 15)

                    rec = AttendanceRecord(
                        student_id=student.id,
                        subject_id=sub_id,
                        slot_id=slot.id,
                        date=curr,
                        status=status,
                        concern_status=concern_status,
                        concern_reason=concern_reason,
                        concern_created_at=concern_created_at
                    )
                    db.session.add(rec)
                    total_records_created += 1

            curr += timedelta(days=1)

        db.session.commit()
        print(f"Created {total_records_created} class-by-class attendance records.")

        # Update student overall attendance percentage
        total_all = AttendanceRecord.query.filter_by(student_id=student.id).count()
        present_all = AttendanceRecord.query.filter_by(student_id=student.id, status='present').count()
        overall_pct = round((present_all / total_all) * 100, 1) if total_all > 0 else 85.0
        student.attendance_percentage = overall_pct
        db.session.commit()
        print(f"Updated student overall attendance percentage to: {overall_pct}% ({present_all}/{total_all})")

if __name__ == '__main__':
    seed_timetable_and_attendance()
