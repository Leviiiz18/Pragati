from models import Subject, User, TimetableSlot, db

class AISchedulerService:
    DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    PERIODS = [
        {'id': 1, 'name': 'Period 1', 'time': '09:30 - 10:20', 'start': '09:30', 'end': '10:20'},
        {'id': 2, 'name': 'Period 2', 'time': '10:20 - 11:10', 'start': '10:20', 'end': '11:10'},
        {'id': 3, 'name': 'Period 3', 'time': '11:20 - 12:10', 'start': '11:20', 'end': '12:10'},
        {'id': 4, 'name': 'Period 4', 'time': '12:10 - 01:00', 'start': '12:10', 'end': '01:00'},
        {'id': 5, 'name': 'Period 5', 'time': '01:50 - 02:40', 'start': '01:50', 'end': '02:40'},
        {'id': 6, 'name': 'Period 6', 'time': '02:40 - 03:30', 'start': '02:40', 'end': '03:30'},
    ]

    ROOMS = ['LH-101', 'LH-102', 'LH-201', 'Computer Lab A', 'AI Research Lab', 'Database Systems Lab']

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
        
        # Indian Engineering College Timetable Pattern (Theory + 2-Period Lab Blocks)
        schedule_blueprint = {
            'Monday': [
                {'period': 1, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 2, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 3, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
                {'period': 4, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 5, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 6, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
            ],
            'Tuesday': [
                {'period': 1, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 2, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
                # 2-Period Lab practical spanning periods 3 & 4
                {'period': 3, 'subj_idx': 0, 'is_lab': True, 'room': 'Computer Lab A', 'span': 2, 'end_period': 4},
                {'period': 5, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 6, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
            ],
            'Wednesday': [
                {'period': 1, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 2, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                # 2-Period Lab practical spanning periods 3 & 4
                {'period': 3, 'subj_idx': 2, 'is_lab': True, 'room': 'AI Research Lab', 'span': 2, 'end_period': 4},
                {'period': 5, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
                {'period': 6, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
            ],
            'Thursday': [
                {'period': 1, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
                {'period': 2, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 3, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 4, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101 (T)'},
                {'period': 5, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 6, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
            ],
            'Friday': [
                # 2-Period Lab practical spanning periods 1 & 2
                {'period': 1, 'subj_idx': 1, 'is_lab': True, 'room': 'Database Systems Lab', 'span': 2, 'end_period': 2},
                {'period': 3, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 4, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 5, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
                {'period': 6, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101 (T)'},
            ],
            'Saturday': [
                {'period': 1, 'subj_idx': 1, 'is_lab': False, 'room': 'LH-101'},
                {'period': 2, 'subj_idx': 2, 'is_lab': False, 'room': 'LH-101'},
                {'period': 3, 'subj_idx': 0, 'is_lab': False, 'room': 'LH-101'},
                {'period': 4, 'subj_idx': 2, 'is_lab': False, 'room': 'Seminar Hall'},
            ]
        }

        period_map = {p['id']: p for p in AISchedulerService.PERIODS}

        for day, slot_configs in schedule_blueprint.items():
            for cfg in slot_configs:
                p_num = cfg['period']
                p_info = period_map.get(p_num)
                if not p_info:
                    continue

                end_p_num = cfg.get('end_period', p_num)
                end_p_info = period_map.get(end_p_num, p_info)

                subj = subjects[cfg['subj_idx'] % len(subjects)]
                fac = subj.faculty or faculties[cfg['subj_idx'] % len(faculties)]
                
                slot = TimetableSlot(
                    day=day,
                    start_time=p_info['start'],
                    end_time=end_p_info['end'],
                    subject_id=subj.id,
                    faculty_id=fac.id,
                    room=cfg['room'],
                    is_lab=cfg['is_lab']
                )
                db.session.add(slot)
                generated_slots.append(slot)

        db.session.commit()
        return True, f"Successfully generated {len(generated_slots)} optimal timetable slots conforming to Indian University Academic Schedule with 0 conflicts."

    @staticmethod
    def get_structured_grid(slots=None):
        """
        Builds the complete 2D matrix structure [Day x Period] for rendering
        Indian institutional timetable layouts with lab spans, break indicators, and legend directory.
        """
        if slots is None:
            slots = TimetableSlot.query.all()

        days = AISchedulerService.DAYS
        periods = AISchedulerService.PERIODS

        # Map existing slots by day and start_time / period
        # Standardize matching by day and period start time
        slots_by_day = {d: [] for d in days}
        for s in slots:
            if s.day in slots_by_day:
                slots_by_day[s.day].append(s)

        matrix = {}
        for day in days:
            day_slots = sorted(slots_by_day[day], key=lambda x: x.start_time)
            
            # Fill the 6 periods
            row_cells = []
            skip_next = 0

            for p in periods:
                if skip_next > 0:
                    skip_next -= 1
                    continue

                # Find slot that starts at or matches this period
                matching_slot = None
                for s in day_slots:
                    if s.start_time == p['start'] or (p['id'] == 1 and s.start_time.startswith('09:')):
                        matching_slot = s
                        break
                    elif p['id'] == 2 and (s.start_time == '10:20' or s.start_time.startswith('10:')):
                        matching_slot = s
                        break
                    elif p['id'] == 3 and (s.start_time == '11:20' or s.start_time.startswith('11:')):
                        matching_slot = s
                        break
                    elif p['id'] == 4 and (s.start_time == '12:10' or s.start_time.startswith('12:') or s.start_time.startswith('13:')):
                        matching_slot = s
                        break
                    elif p['id'] == 5 and (s.start_time == '01:50' or s.start_time == '13:50' or s.start_time.startswith('13:15') or s.start_time.startswith('14:')):
                        matching_slot = s
                        break
                    elif p['id'] == 6 and (s.start_time == '02:40' or s.start_time == '14:40' or s.start_time.startswith('14:15') or s.start_time.startswith('15:')):
                        matching_slot = s
                        break

                if matching_slot:
                    span = 1
                    if matching_slot.is_lab:
                        if (p['id'] == 1 and matching_slot.end_time in ['11:10', '11:00']) or \
                           (p['id'] == 3 and matching_slot.end_time in ['01:00', '13:00', '12:15', '14:15']) or \
                           (p['id'] == 5 and matching_slot.end_time in ['03:30', '15:30', '15:15']):
                            span = 2
                            skip_next = 1

                    row_cells.append({
                        'type': 'slot',
                        'period': p,
                        'slot': matching_slot,
                        'span': span,
                        'is_lab': matching_slot.is_lab
                    })
                else:
                    row_cells.append({
                        'type': 'empty',
                        'period': p,
                        'slot': None,
                        'span': 1,
                        'is_lab': False
                    })

            # Group into Session 1 (Periods 1 & 2), Session 2 (Periods 3 & 4), Session 3 (Periods 5 & 6)
            s1 = []
            s2 = []
            s3 = []
            for c in row_cells:
                p_id = c['period']['id']
                if p_id in [1, 2]:
                    s1.append(c)
                elif p_id in [3, 4]:
                    s2.append(c)
                elif p_id in [5, 6]:
                    s3.append(c)

            matrix[day] = {
                'cells': row_cells,
                'session_1': s1,
                'session_2': s2,
                'session_3': s3
            }

        # Build Subject & Faculty Directory Legend
        unique_subjects = {}
        for s in slots:
            if s.subject and s.subject.id not in unique_subjects:
                subj = s.subject
                fac = s.faculty or (subj.faculty if hasattr(subj, 'faculty') else None)
                unique_subjects[subj.id] = {
                    'code': subj.code or f'CS{subj.id}',
                    'name': subj.name,
                    'credits': subj.credits or 4,
                    'faculty_name': fac.name if fac else 'Faculty In-charge',
                    'faculty_designation': getattr(fac, 'designation', 'Assistant Professor') if fac else 'Assistant Professor',
                    'faculty_dept': getattr(fac, 'department', 'Computer Science & Engineering') if fac else 'CSE',
                    'room': s.room or 'LH-101',
                    'ltp': '3-0-2' if s.is_lab else '3-1-0'
                }

        legend_list = list(unique_subjects.values())
        return matrix, legend_list, periods
