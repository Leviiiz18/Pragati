from app import create_app
from models import db, User, Course, Specialization, Subject, Enrollment, Module, Unit, File, Event
from flask_bcrypt import Bcrypt
from datetime import date
import os

app = create_app()
bcrypt = Bcrypt()

def seed_data():
    with app.app_context():
        # Drop and recreate for total refresh
        db.drop_all()
        db.create_all()
        print("TABLES CREATED")
        
        # Passwords
        admin_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
        pass_pw = bcrypt.generate_password_hash('password123').decode('utf-8')

        # 1. HODs
        hods = [
            User(name='Dr. BCA HOD', email='hod@studysync.pro', password=admin_pw, role='hod', department='Computer Science'),
            User(name='Dr. BBA HOD', email='bba.hod@studysync.com', password=admin_pw, role='hod', department='Management'),
            User(name='Dr. Anil Verma', email='anil.hod@studysync.com', password=admin_pw, role='hod', department='Science')
        ]
        db.session.add_all(hods)
        db.session.commit()
        
        # 2. Faculty
        faculties = [
            User(name='Prof. Jane Doe', email='faculty@studysync.pro', password=pass_pw, role='faculty', department='Computer Science'),
            User(name='Finance Prof', email='fin.fac@studysync.com', password=pass_pw, role='faculty', department='Management'),
            User(name='Riya Nair', email='riya.ds@studysync.com', password=pass_pw, role='faculty', department='Science'),
            User(name='Neha Kapoor', email='neha.se@studysync.com', password=pass_pw, role='faculty', department='Science')
        ]
        db.session.add_all(faculties)
        db.session.commit()
        
        # 3. Students
        students = [
            User(name='John Student', email='student@studysync.pro', password=pass_pw, role='student', department='Computer Science'),
            User(name='BBA Student', email='bba.std@studysync.com', password=pass_pw, role='student', department='Management'),
            User(name='Rahul Sharma', email='rahul@studysync.com', password=pass_pw, role='student', department='Science'),
            User(name='Priya Das', email='priya@studysync.com', password=pass_pw, role='student', department='Science')
        ]
        db.session.add_all(students)
        db.session.commit()
        
        # 4. Courses config
        courses_config = {
            'BCA': {
                'dept': 'Computer Science', 
                'fac_email': 'faculty@studysync.pro',
                'std_emails': ['student@studysync.pro'],
                'specs': {
                    'AIML': [('AIML101', 'Introduction to AI'), ('AIML102', 'Machine Learning Basics')],
                    'Cyber Security': [('CY101', 'Network Security'), ('CY102', 'Ethical Hacking')]
                }
            },
            'BBA': {
                'dept': 'Management', 
                'fac_email': 'fin.fac@studysync.com',
                'std_emails': ['bba.std@studysync.com'],
                'specs': {
                    'Finance': [('FIN101', 'Business Finance'), ('FIN102', 'Corporate Accounting')],
                    'HR': [('HR101', 'HR Management'), ('HR102', 'Industrial Relations')]
                }
            },
            'BSc Computer Science': {
                'dept': 'Science',
                'std_emails': ['rahul@studysync.com', 'priya@studysync.com'],
                'specs': {
                    'Data Science': [
                        ('DS101', 'Introduction to Data Science', 'riya.ds@studysync.com', 'Insights from data.'),
                        ('DS102', 'Data Analysis with Python', 'riya.ds@studysync.com', 'Python is key.')
                    ],
                    'Software Engineering': [
                        ('SE101', 'Software Development Life Cycle', 'neha.se@studysync.com', 'SDLC basics.'),
                        ('SE102', 'Web Development Basics', 'neha.se@studysync.com', 'Web fundamentals.')
                    ]
                }
            }
        }

        for c_name, c_info in courses_config.items():
            course = Course(name=c_name, department=c_info['dept'])
            db.session.add(course)
            db.session.commit()
            
            for spec_name, subjects in c_info['specs'].items():
                spec = Specialization(name=spec_name, course_id=course.id)
                db.session.add(spec)
                db.session.commit()
                
                for sub_info in subjects:
                    if len(sub_info) == 2:
                        sub_code, sub_name = sub_info
                        sub_fac_email = c_info['fac_email']
                        sub_content = "Study notes."
                    else:
                        sub_code, sub_name, sub_fac_email, sub_content = sub_info
                    
                    fac_user = User.query.filter_by(email=sub_fac_email).first()
                    subject = Subject(name=sub_name, code=sub_code, course_id=course.id, specialization_id=spec.id, faculty_id=fac_user.id)
                    db.session.add(subject)
                    db.session.commit()
                    
                    for std_email in c_info['std_emails']:
                        std_user = User.query.filter_by(email=std_email).first()
                        db.session.add(Enrollment(student_id=std_user.id, subject_id=subject.id))
                    
                    for m_idx, m_title in enumerate(['Module 1', 'Module 2'], 1):
                        module = Module(title=m_title, subject_id=subject.id)
                        db.session.add(module)
                        db.session.commit()
                        
                        for u_idx in range(1, 3):
                            unit = Unit(title=f'Unit {u_idx}', module_id=module.id)
                            db.session.add(unit)
                            db.session.commit()
                            
                            filename = f"{sub_code}_M{m_idx}_U{u_idx}.txt"
                            sub_dir = sub_name.replace(' ', '_')
                            full_dir = os.path.join(app.config['UPLOAD_FOLDER'], sub_dir)
                            if not os.path.exists(full_dir): os.makedirs(full_dir)
                            with open(os.path.join(full_dir, filename), 'w') as f:
                                f.write(sub_content)
                            
                            db_file = File(unit_id=unit.id, filename=filename, filepath=os.path.join(sub_dir, filename), filetype='txt')
                            db.session.add(db_file)
        
        db.session.commit()
        print("DATABASE SEEDED")

if __name__ == '__main__':
    seed_data()
