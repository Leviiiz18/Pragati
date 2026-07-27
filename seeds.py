from app import create_app
from models import db, User, Course, Specialization, Subject, Enrollment, Module, Unit, File, Event, Department, PlacementDrive, PlacementApplication, FeeRecord, DocumentRequest, TimetableSlot, Exam, Institution, Quiz
from flask_bcrypt import Bcrypt
from datetime import date, datetime, timedelta
import json

app = create_app()
bcrypt = Bcrypt()

def seed_db():
    with app.app_context():
        # Clear existing tables
        db.drop_all()
        db.create_all()
        print("Database schema reset cleanly.")

        pw_hash = bcrypt.generate_password_hash('password123').decode('utf-8')
        admin_pw_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')

        # 0. Institution (Pre-fed University Setup)
        nitte_univ = Institution(name="Nitte University", code="NU", address="Mangaluru, Karnataka, India")
        db.session.add(nitte_univ)
        db.session.commit()

        # 1. Departments
        cs_dept = Department(name="Computer Science & Engineering", code="CSE", budget=1500000.0)
        ece_dept = Department(name="Electronics & Communication", code="ECE", budget=1200000.0)
        db.session.add_all([cs_dept, ece_dept])
        db.session.commit()

        # 2. Users (5-Tier Role Hierarchy)
        super_admin = User(
            name="Dr. Vikram Sarabhai",
            email="superadmin@studysync.pro",
            password=admin_pw_hash,
            role="super_admin",
            department="Executive"
        )

        principal = User(
            name="Prof. APJ Abdul Kalam",
            email="principal@studysync.pro",
            password=admin_pw_hash,
            role="principal",
            department="Executive"
        )

        hod = User(
            name="Dr. Alan Turing",
            email="hod@studysync.pro",
            password=admin_pw_hash,
            role="hod",
            department="Computer Science & Engineering"
        )

        faculty1 = User(
            name="Prof. Grace Hopper",
            employee_id="NU26FAC001",
            first_name="Grace",
            last_name="Hopper",
            email="faculty@studysync.pro",
            personal_email="grace.hopper@gmail.com",
            phone="+91 98765 11223",
            student_phone="+91 98765 11223",
            dob="1982-12-09",
            gender="Female",
            nationality="Indian",
            category="General",
            govt_id_type="PAN",
            govt_id_number="ABCDE1234F",
            biometric_id="BIO-FAC-8891",
            permanent_address="15 Cambridge Layout, Bengaluru",
            current_address="Faculty Quarters Block 2, Campus",
            emergency_contact_name="Charles Hopper",
            emergency_contact_phone="+91 98765 99991",
            emergency_contact_relation="Spouse",
            qualifications="Ph.D. in Computer Science (Yale), M.Tech",
            specialization="Compiler Design & Programming Languages",
            work_experience_years=14.5,
            research_publications="18 IEEE Journals, 3 US Patents, 2 Textbooks",
            designation="Professor",
            joining_date="2018-07-01",
            bank_name="HDFC Bank",
            bank_account_number="50100456789012",
            ifsc_code="HDFC0000123",
            basic_salary=145000.0,
            pf_pension_number="PF/KA/54321/9876",
            password=pw_hash,
            role="faculty",
            department="Computer Science & Engineering"
        )

        faculty2 = User(
            name="Dr. Claude Shannon",
            employee_id="NU26FAC002",
            first_name="Claude",
            last_name="Shannon",
            email="shannon@studysync.pro",
            personal_email="claude.shannon@gmail.com",
            phone="+91 98765 11224",
            student_phone="+91 98765 11224",
            dob="1985-04-30",
            gender="Male",
            nationality="Indian",
            category="General",
            govt_id_type="PAN",
            govt_id_number="XYZPS9876K",
            biometric_id="BIO-FAC-8892",
            permanent_address="42 Information Way, Mysuru",
            current_address="Faculty Quarters Block 4, Campus",
            emergency_contact_name="Betty Shannon",
            emergency_contact_phone="+91 98765 99992",
            emergency_contact_relation="Spouse",
            qualifications="Ph.D. in Information Theory (MIT)",
            specialization="Information Theory, Cryptography & Data Structures",
            work_experience_years=11.0,
            research_publications="14 ACM Papers, 1 International Patent",
            designation="Associate Professor",
            joining_date="2020-01-10",
            bank_name="State Bank of India",
            bank_account_number="309876543210",
            ifsc_code="SBIN0004321",
            basic_salary=125000.0,
            pf_pension_number="PF/KA/54321/9877",
            password=pw_hash,
            role="faculty",
            department="Computer Science & Engineering"
        )

        student1 = User(
            name="Alex Mercer",
            registration_id="NU23UCA001",
            first_name="Alex",
            last_name="Mercer",
            email="student@studysync.pro",
            personal_email="alex.mercer@gmail.com",
            student_phone="+91 98765 43210",
            parent_phone="+91 98765 00001",
            dob="2004-05-14",
            gender="Male",
            nationality="Indian",
            category="General",
            govt_id_type="Aadhar",
            govt_id_number="1234-5678-9012",
            permanent_address="12 Park Avenue, Bengaluru, Karnataka",
            current_address="Hostel Block A, Room 204, Campus",
            emergency_contact_name="Robert Mercer",
            emergency_contact_phone="+91 98765 00001",
            admission_year=2023,
            course_code="UCA",
            previous_school="National Public School",
            previous_board="CBSE",
            previous_passing_year=2022,
            previous_marks_percentage=94.5,
            entrance_exam_name="KCET",
            entrance_exam_score="Rank 1200",
            password=pw_hash,
            role="student",
            department="Computer Science & Engineering",
            semester=4,
            cgpa=8.5,
            attendance_percentage=88.5,
            risk_score=12.0,
            risk_reason="On track for distinction.",
            placement_status="Eligible"
        )

        # High-Risk Student
        student_rahul = User(
            name="Rahul Sharma",
            registration_id="NU23UCA054",
            first_name="Rahul",
            last_name="Sharma",
            email="rahul@studysync.pro",
            personal_email="rahul.sharma@gmail.com",
            student_phone="+91 98765 43211",
            parent_phone="+91 98765 00002",
            dob="2004-08-20",
            gender="Male",
            nationality="Indian",
            category="General",
            govt_id_type="Aadhar",
            govt_id_number="2345-6789-0123",
            permanent_address="45 M.G. Road, Mangaluru, Karnataka",
            current_address="Hostel Block B, Room 102, Campus",
            emergency_contact_name="Suresh Sharma",
            emergency_contact_phone="+91 98765 00002",
            admission_year=2023,
            course_code="UCA",
            previous_school="St. Aloysius High School",
            previous_board="State Board",
            previous_passing_year=2022,
            previous_marks_percentage=82.0,
            entrance_exam_name="KCET",
            entrance_exam_score="Rank 4500",
            password=pw_hash,
            role="student",
            department="Computer Science & Engineering",
            semester=4,
            cgpa=5.9,
            attendance_percentage=62.0,
            risk_score=89.0,
            risk_reason="Attendance dropped below 65%, missing 3 assignments, internal test scores declining.",
            placement_status="At-Risk"
        )

        student_priya = User(
            name="Priya Patel",
            registration_id="NU23UCA055",
            first_name="Priya",
            last_name="Patel",
            email="priya@studysync.pro",
            personal_email="priya.patel@gmail.com",
            student_phone="+91 98765 43212",
            parent_phone="+91 98765 00003",
            dob="2004-11-05",
            gender="Female",
            nationality="Indian",
            category="General",
            govt_id_type="Aadhar",
            govt_id_number="3456-7890-1234",
            permanent_address="88 Residency Road, Mysuru, Karnataka",
            current_address="Hostel Block C, Room 301, Campus",
            emergency_contact_name="Mahesh Patel",
            emergency_contact_phone="+91 98765 00003",
            admission_year=2023,
            course_code="UCA",
            previous_school="Delhi Public School",
            previous_board="CBSE",
            previous_passing_year=2022,
            previous_marks_percentage=97.0,
            entrance_exam_name="KCET",
            entrance_exam_score="Rank 250",
            password=pw_hash,
            role="student",
            department="Computer Science & Engineering",
            semester=4,
            cgpa=9.3,
            attendance_percentage=96.0,
            risk_score=5.0,
            risk_reason="Top 1% department performer.",
            placement_status="Placed"
        )

        db.session.add_all([super_admin, principal, hod, faculty1, faculty2, student1, student_rahul, student_priya])
        db.session.commit()

        # Update HOD ID on Department
        cs_dept.hod_id = hod.id
        db.session.commit()

        # 3. Pre-Fed Courses & Subjects
        course_bca = Course(name="Bachelor of Computer Applications", code="UCA", department="Computer Science & Engineering")
        course_btech = Course(name="B.Tech Computer Science", code="CSE", department="Computer Science & Engineering")
        db.session.add_all([course_bca, course_btech])
        db.session.commit()

        spec_ai = Specialization(name="Artificial Intelligence & Data Science", course_id=course_btech.id)
        db.session.add(spec_ai)
        db.session.commit()

        sub_dsa = Subject(name="Data Structures & Algorithms", code="CS201", course_id=course_btech.id, specialization_id=spec_ai.id, faculty_id=faculty1.id, semester=4, credits=4, completion_percentage=80.0)
        sub_dbms = Subject(name="Database Management Systems", code="CS202", course_id=course_btech.id, specialization_id=spec_ai.id, faculty_id=faculty2.id, semester=4, credits=4, completion_percentage=75.0)
        sub_ai = Subject(name="Artificial Intelligence", code="CS203", course_id=course_btech.id, specialization_id=spec_ai.id, faculty_id=faculty1.id, semester=4, credits=4, completion_percentage=70.0)
        
        db.session.add_all([sub_dsa, sub_dbms, sub_ai])
        db.session.commit()

        # 4. STRICT 5-MODULE HIERARCHY FOR EACH SUBJECT
        module_titles = [
            "Module 1: Foundational Principles & Core Concepts",
            "Module 2: Architectural Frameworks & Data Structures",
            "Module 3: Advanced Algorithms & Optimization Pipelines",
            "Module 4: Applied Practical Implementations & Lab Projects",
            "Module 5: Emerging Innovations & Capstone Applications"
        ]

        sample_quiz_questions = json.dumps([
            {
                "question": "What is the time complexity of searching in a Balanced Binary Search Tree?",
                "options": ["O(1)", "O(log N)", "O(N)", "O(N^2)"],
                "answer": "O(log N)"
            },
            {
                "question": "Which data structure follows the Last-In-First-Out (LIFO) principle?",
                "options": ["Queue", "Stack", "Array", "Graph"],
                "answer": "Stack"
            }
        ])

        for sub in [sub_dsa, sub_dbms, sub_ai]:
            for i, m_title in enumerate(module_titles, start=1):
                mod = Module(subject_id=sub.id, title=m_title)
                db.session.add(mod)
                db.session.commit()

                # Unit & Resources
                u1 = Unit(module_id=mod.id, title=f"Unit {i}.1: Theoretical Foundations & Lecture Notes")
                u2 = Unit(module_id=mod.id, title=f"Unit {i}.2: Laboratory Exercises & Code Repositories")
                db.session.add_all([u1, u2])
                db.session.commit()

                # Resources / Files
                f1 = File(unit_id=u1.id, filename=f"{sub.code}_Mod{i}_Lecture_Notes.pdf", filepath=f"/uploads/{sub.code}_mod{i}.pdf", filetype="PDF Document")
                f2 = File(unit_id=u2.id, filename=f"{sub.code}_Mod{i}_Lab_Manual.pdf", filepath=f"/uploads/{sub.code}_lab{i}.pdf", filetype="PDF Document")
                db.session.add_all([f1, f2])

                # Quiz for each Module
                qz = Quiz(module_id=mod.id, title=f"{sub.code} - Module {i} Mastery Quiz", questions_json=sample_quiz_questions)
                db.session.add(qz)
                db.session.commit()

        # 5. Enrollments
        for st in [student1, student_rahul, student_priya]:
            db.session.add(Enrollment(student_id=st.id, subject_id=sub_dsa.id))
            db.session.add(Enrollment(student_id=st.id, subject_id=sub_dbms.id))
            db.session.add(Enrollment(student_id=st.id, subject_id=sub_ai.id))
        db.session.commit()

        # 6. Placement Drives
        drive1 = PlacementDrive(company_name="Google Cloud India", role="Software Development Engineer", package_lpa=24.5, min_cgpa=8.0, drive_date=date.today() + timedelta(days=15), status="Active")
        drive2 = PlacementDrive(company_name="Microsoft Research", role="AI Platform Engineer", package_lpa=28.0, min_cgpa=8.5, drive_date=date.today() + timedelta(days=25), status="Upcoming")
        db.session.add_all([drive1, drive2])
        db.session.commit()

        # 7. Fee Records
        fee1 = FeeRecord(student_id=student1.id, semester=4, total_amount=75000.0, paid_amount=75000.0, due_date=date.today(), status="Paid")
        fee2 = FeeRecord(student_id=student_rahul.id, semester=4, total_amount=75000.0, paid_amount=35000.0, due_date=date.today() - timedelta(days=10), status="Overdue", risk_flag=True)
        db.session.add_all([fee1, fee2])
        db.session.commit()

        # 8. Document Requests
        doc1 = DocumentRequest(student_id=student1.id, doc_type="Bonafide Certificate", status="Approved", hash_code="A87F90B1C2")
        doc2 = DocumentRequest(student_id=student_rahul.id, doc_type="Conduct Certificate", status="Pending")
        db.session.add_all([doc1, doc2])
        db.session.commit()

        # 9. Timetable Slots
        slot1 = TimetableSlot(day="Monday", start_time="09:00", end_time="10:00", subject_id=sub_dsa.id, faculty_id=faculty1.id, room="Room 101")
        slot2 = TimetableSlot(day="Monday", start_time="10:00", end_time="11:00", subject_id=sub_dbms.id, faculty_id=faculty2.id, room="Computer Lab A", is_lab=True)
        db.session.add_all([slot1, slot2])
        db.session.commit()

        # 10. Google Classroom Style Assignments inside Modules
        from models import Assignment, AssignmentSubmission, Notification
        mod1_dsa = Module.query.filter_by(subject_id=sub_dsa.id).first()
        if mod1_dsa:
            assign1 = Assignment(
                module_id=mod1_dsa.id,
                title="Lab Assignment 1: Binary Search Tree Implementation & Performance Analysis",
                instructions="Implement a balanced Binary Search Tree in Python or C++. Include methods for insert, delete, and in-order traversal. Submit your code file (.py/.cpp) and a 2-page PDF analysis report on time complexities.",
                due_date=date.today() + timedelta(days=7),
                max_points=100.0,
                attachment_path="/static/uploads/assignment_1_instructions.pdf"
            )
            db.session.add(assign1)
            db.session.commit()

            # Seed a submission for student1
            sub1 = AssignmentSubmission(
                assignment_id=assign1.id,
                student_id=student1.id,
                submission_text="Completed Binary Search Tree implementation with O(log N) search benchmark report.",
                file_path="/static/uploads/alex_mercer_bst_assignment.pdf",
                status="Turned In"
            )
            db.session.add(sub1)

            # Notifications for enrolled students
            for st in [student1, student_rahul, student_priya]:
                notif = Notification(
                    user_id=st.id,
                    title="New Assignment Posted: CS201 Module 1",
                    message="Prof. Grace Hopper posted 'Lab Assignment 1: Binary Search Tree Implementation'. Due in 7 days.",
                    link=f"/student/course/{sub_dsa.id}"
                )
                db.session.add(notif)
            db.session.commit()

        print("Strict 5-Module Curriculum Hierarchy, Assignments & Notifications successfully seeded!")

if __name__ == '__main__':
    seed_db()
