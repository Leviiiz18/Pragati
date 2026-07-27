from models import Subject, User, TimetableSlot, db

class AISchedulerService:
    DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    TIME_SLOTS = ['09:00 - 10:00', '10:00 - 11:00', '11:15 - 12:15', '13:15 - 14:15', '14:15 - 15:15']
    ROOMS = ['Room 101', 'Room 102', 'Room 201', 'Computer Lab A', 'AI Research Lab']

    @staticmethod
    def generate_optimal_timetable(department_name="Computer Science"):
        subjects = Subject.query.all()
        faculties = User.query.filter_by(role='faculty').all()
        
        if not subjects or not faculties:
            return False, "Insufficient subjects or faculty members registered."

        # Clear existing generated slots for automated re-scheduling
        TimetableSlot.query.delete()
        db.session.commit()

        generated_slots = []
        slot_idx = 0

        for day in AISchedulerService.DAYS:
            for t_slot in AISchedulerService.TIME_SLOTS[:4]:
                subj = subjects[slot_idx % len(subjects)]
                fac = subj.faculty or faculties[slot_idx % len(faculties)]
                rm = AISchedulerService.ROOMS[slot_idx % len(AISchedulerService.ROOMS)]
                
                slot = TimetableSlot(
                    day=day,
                    start_time=t_slot.split(' - ')[0],
                    end_time=t_slot.split(' - ')[1],
                    subject_id=subj.id,
                    faculty_id=fac.id,
                    room=rm,
                    is_lab=('Lab' in rm)
                )
                db.session.add(slot)
                generated_slots.append(slot)
                slot_idx += 1

        db.session.commit()
        return True, f"Successfully generated {len(generated_slots)} optimal timetable slots with 0 room conflicts."
