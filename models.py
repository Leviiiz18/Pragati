from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Institution(db.Model):
    __tablename__ = 'institution'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, default="Nitte University")
    code = db.Column(db.String(20), nullable=False, default="NU") # Pre-fed university abbreviation e.g. NU
    address = db.Column(db.String(250), default="Mangaluru, Karnataka, India")

class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    hod_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    budget = db.Column(db.Float, default=1000000.0)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.String(50), unique=True, nullable=True) # Auto-generated e.g. NU23UCA054
    employee_id = db.Column(db.String(50), unique=True, nullable=True) # Auto-generated e.g. NU26FAC001
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # super_admin, principal, hod, faculty, student, staff
    department = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active') # active, suspended
    
    # Section 1: Personal & Identification Details
    first_name = db.Column(db.String(50), nullable=True)
    middle_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    dob = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    gender = db.Column(db.String(20), nullable=True) # Male, Female, Other
    nationality = db.Column(db.String(50), default='Indian')
    category = db.Column(db.String(50), default='General') # General, OBC, SC, ST
    govt_id_type = db.Column(db.String(50), default='Aadhar') # PAN, Aadhar, SSN, Passport
    govt_id_number = db.Column(db.String(50), nullable=True)
    biometric_id = db.Column(db.String(50), nullable=True) # Fingerprint / Facial ID badge
    
    # Section 2: Contact & Emergency Details
    student_phone = db.Column(db.String(20), nullable=True)
    parent_phone = db.Column(db.String(20), nullable=True)
    personal_email = db.Column(db.String(120), nullable=True)
    permanent_address = db.Column(db.Text, nullable=True)
    current_address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    emergency_contact_relation = db.Column(db.String(50), nullable=True)
    
    # Section 3: Academic & Admission Details (Students)
    admission_year = db.Column(db.Integer, default=2026)
    course_code = db.Column(db.String(20), default='UCA')
    previous_school = db.Column(db.String(150), nullable=True)
    previous_board = db.Column(db.String(100), nullable=True)
    previous_passing_year = db.Column(db.Integer, nullable=True)
    previous_marks_percentage = db.Column(db.Float, nullable=True)
    entrance_exam_name = db.Column(db.String(100), nullable=True)
    entrance_exam_score = db.Column(db.String(50), nullable=True)

    # Section 4: Academic & Professional Background (Faculty)
    qualifications = db.Column(db.Text, nullable=True) # Degrees, Diplomas, Certifications
    specialization = db.Column(db.Text, nullable=True) # Research & Subject Specialization
    work_experience_years = db.Column(db.Float, default=0.0) # Years worked
    research_publications = db.Column(db.Text, nullable=True) # Books, Patents, Journal Papers

    # Section 5: College Assignment Details (Faculty)
    designation = db.Column(db.String(100), default='Assistant Professor') # Assistant Professor, Associate Professor, Professor, HOD
    joining_date = db.Column(db.String(20), nullable=True) # YYYY-MM-DD

    # Section 6: Financial & Payroll Details (Faculty)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account_number = db.Column(db.String(50), nullable=True)
    ifsc_code = db.Column(db.String(30), nullable=True)
    basic_salary = db.Column(db.Float, default=85000.0)
    pf_pension_number = db.Column(db.String(50), nullable=True)

    # Extended Student Metrics
    semester = db.Column(db.Integer, default=1)
    cgpa = db.Column(db.Float, nullable=True) # None for Semester 1 students until 1st Sem results published
    attendance_percentage = db.Column(db.Float, default=85.0)
    risk_score = db.Column(db.Float, default=15.0) # 0 to 100%
    risk_reason = db.Column(db.Text, nullable=True)
    placement_status = db.Column(db.String(50), default='Eligible') # Eligible, Placed, Higher Studies
    fee_status = db.Column(db.String(20), default='Clear') # Clear, Pending, Overdue
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    # Relationships
    subjects_taught = db.relationship('Subject', backref='faculty', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    events_created = db.relationship('Event', backref='creator', lazy=True, foreign_keys='Event.created_by')
    personal_reminders = db.relationship('Event', backref='owner', lazy=True, foreign_keys='Event.user_id')
    risk_alerts = db.relationship('AIRiskAlert', backref='student', lazy=True, cascade="all, delete-orphan")
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade="all, delete-orphan")
    exam_results = db.relationship('ExamResult', backref='student', lazy=True, cascade="all, delete-orphan")

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False, default="UCA") # e.g. UCA or CSE
    department = db.Column(db.String(100), nullable=False)
    specializations = db.relationship('Specialization', backref='course', lazy=True, cascade="all, delete-orphan")
    subjects = db.relationship('Subject', backref='course', lazy=True, cascade="all, delete-orphan")

class Specialization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    subjects = db.relationship('Subject', backref='specialization', lazy=True, cascade="all, delete-orphan")

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    specialization_id = db.Column(db.Integer, db.ForeignKey('specialization.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    semester = db.Column(db.Integer, default=1)
    credits = db.Column(db.Integer, default=4)
    syllabus_status = db.Column(db.String(50), default='Approved') # Approved, Pending Review, Revision Requested
    syllabus_summary = db.Column(db.Text, nullable=True)
    completion_percentage = db.Column(db.Float, default=75.0)
    
    modules = db.relationship('Module', backref='subject', lazy=True, cascade="all, delete-orphan")
    enrollments = db.relationship('Enrollment', backref='subject', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='subject', lazy=True, cascade="all, delete-orphan")

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    units = db.relationship('Unit', backref='module', lazy=True, cascade="all, delete-orphan")
    quizzes = db.relationship('Quiz', backref='module', lazy=True, cascade="all, delete-orphan")

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    questions_json = db.Column(db.Text, nullable=False) # JSON array of questions, options, and correct answer

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    files = db.relationship('File', backref='unit', lazy=True, cascade="all, delete-orphan")

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_role = db.Column(db.String(20), nullable=False) # faculty, student, all, personal
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    subject_rel = db.relationship('Subject', foreign_keys=[subject_id], overlaps="events,subject")
    user_rel = db.relationship('User', foreign_keys=[user_id], overlaps="owner,personal_reminders")
    creator_rel = db.relationship('User', foreign_keys=[created_by], overlaps="creator,events_created")

class DocumentChunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.Text, nullable=False)

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False) # present, absent, late
    is_proxy_suspect = db.Column(db.Boolean, default=False)
    proxy_reason = db.Column(db.String(200), nullable=True)

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    max_marks = db.Column(db.Float, default=100.0)
    type = db.Column(db.String(50), default='Internal') # Internal, End-Sem, Quiz
    bloom_level = db.Column(db.String(50), default='Understand') # Remember, Understand, Apply, Analyze, Evaluate, Create
    status = db.Column(db.String(20), default='Scheduled') # Scheduled, Approved, Published
    subject = db.relationship('Subject', backref='exams')

class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), default='A')
    feedback = db.Column(db.Text, nullable=True)
    exam = db.relationship('Exam', backref='results')

class TimetableSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False) # Monday, Tuesday, ...
    start_time = db.Column(db.String(10), nullable=False) # 09:00
    end_time = db.Column(db.String(10), nullable=False) # 10:00
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room = db.Column(db.String(50), default='Lab 101')
    is_lab = db.Column(db.Boolean, default=False)
    subject = db.relationship('Subject', backref='timetable_slots')
    faculty = db.relationship('User', foreign_keys=[faculty_id])

class PlacementDrive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    package_lpa = db.Column(db.Float, nullable=False)
    min_cgpa = db.Column(db.Float, default=7.0)
    drive_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Upcoming') # Upcoming, Active, Completed

class PlacementApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied') # Applied, Shortlisted, Selected, Rejected
    ats_score = db.Column(db.Float, default=85.0)
    drive = db.relationship('PlacementDrive', backref='applications')
    student = db.relationship('User', backref='placements')

class FeeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    semester = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, default=75000.0)
    paid_amount = db.Column(db.Float, default=75000.0)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Paid') # Paid, Pending, Overdue
    risk_flag = db.Column(db.Boolean, default=False)
    student = db.relationship('User', backref='fee_records')

class DocumentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False) # Bonafide, Transcript, Transfer Certificate, Conduct
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Issued
    hash_code = db.Column(db.String(64), nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('User', backref='doc_requests')

class AIRiskAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    risk_score = db.Column(db.Float, nullable=False)
    risk_category = db.Column(db.String(50), nullable=False) # Academic Failure, Dropout, Proxy Attendance, Distress
    reason = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Active') # Active, Resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AICommandLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.Text, nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    result_summary = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class StudentNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='General Notes') # Lecture Notes, Revision, Formula Sheet
    attachment_path = db.Column(db.Text, nullable=True) # File path or Data URL (image, PDF, camera capture, scribble)
    attachment_type = db.Column(db.String(50), default='Text') # Text, Image, PDF, Camera, Scribble
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', backref=db.backref('notes', lazy=True, cascade="all, delete-orphan"))
    subject = db.relationship('Subject', backref='student_notes')

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    max_points = db.Column(db.Float, default=100.0)
    attachment_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    module = db.relationship('Module', backref=db.backref('assignments', lazy=True, cascade="all, delete-orphan"))
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True, cascade="all, delete-orphan")

class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_text = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default='Turned In') # Turned In, Graded, Missing
    points_awarded = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    student = db.relationship('User', backref=db.backref('assignment_submissions', lazy=True, cascade="all, delete-orphan"))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(250), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))
