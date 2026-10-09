from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
import os
from config import Config
from models import db, User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ProxyFix ensures correct client IP and HTTPS protocol behind Render's reverse proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # OWASP Security Headers
    @app.after_request
    def apply_security_headers(response):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if request.is_secure or os.environ.get('RENDER') == 'true':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    db.init_app(app)
    bcrypt = Bcrypt(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_notifications():
        if current_user.is_authenticated:
            from models import Notification
            try:
                notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
                unread_count = sum(1 for n in notifs if not n.is_read)
                return {'user_notifications': notifs, 'unread_notif_count': unread_count}
            except Exception:
                pass
        return {'user_notifications': [], 'unread_notif_count': 0}

    # Register blueprints
    from routes.auth import auth_bp
    from routes.super_admin import super_admin_bp
    from routes.hod import hod_bp
    from routes.faculty import faculty_bp
    from routes.student import student_bp
    from routes.events import events_bp
    from routes.ai_api import ai_api_bp
    from routes.landing import landing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(super_admin_bp, url_prefix='/super_admin')
    app.register_blueprint(hod_bp, url_prefix='/hod')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(events_bp)
    app.register_blueprint(ai_api_bp)
    # Public hero page lives at "/" (logged-in users are sent to their dashboard)
    app.register_blueprint(landing_bp)

    if not os.path.exists(app.config.get('UPLOAD_FOLDER', 'uploads')):
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'))

    def ensure_default_accounts():
        try:
            from models import Department, Course, Institution
            
            # 1. Ensure Institution exists
            inst = Institution.query.first()
            if not inst:
                inst = Institution(name="Nitte University", code="NU", address="Mangaluru, Karnataka, India")
                db.session.add(inst)
                db.session.commit()

            # 2. Ensure basic Departments exist
            depts_data = [
                ("Computer Science", "CSE"),
                ("Management", "MGT"),
                ("Science", "SCI")
            ]
            for d_name, d_code in depts_data:
                if not Department.query.filter_by(name=d_name).first():
                    db.session.add(Department(name=d_name, code=d_code))
            db.session.commit()

            # 3. Ensure basic Courses exist
            courses_data = [
                ("BCA", "UCA", "Computer Science"),
                ("B.Tech Computer Science", "CSE", "Computer Science"),
                ("BBA", "BBA", "Management")
            ]
            for c_name, c_code, c_dept in courses_data:
                if not Course.query.filter_by(code=c_code).first():
                    db.session.add(Course(name=c_name, code=c_code, department=c_dept))
            db.session.commit()

            admin_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            pass_pw = bcrypt.generate_password_hash('password123').decode('utf-8')

            # 4. Super Admin
            admin = User.query.filter(User.role.in_(['super_admin', 'principal'])).first()
            if not admin:
                admin = User(
                    name='System Administrator',
                    email='admin@studysync.pro',
                    password=admin_pw,
                    role='super_admin',
                    department='Administration',
                    status='active'
                )
                db.session.add(admin)

            # 5. HOD
            hod = User.query.filter_by(role='hod').first()
            if not hod:
                hod = User(
                    name='Dr. BCA HOD',
                    email='hod@studysync.pro',
                    employee_id='NU26HOD001',
                    password=admin_pw,
                    role='hod',
                    department='Computer Science',
                    status='active'
                )
                db.session.add(hod)
                db.session.flush()
                cs_dept = Department.query.filter_by(name='Computer Science').first()
                if cs_dept:
                    cs_dept.hod_id = hod.id

            # 6. Faculty
            faculty = User.query.filter_by(role='faculty').first()
            if not faculty:
                faculty = User(
                    name='Prof. Jane Doe',
                    email='faculty@studysync.pro',
                    employee_id='NU26FAC001',
                    password=pass_pw,
                    role='faculty',
                    department='Computer Science',
                    designation='Assistant Professor',
                    status='active'
                )
                db.session.add(faculty)

            # 7. Student
            student = User.query.filter_by(role='student').first()
            if not student:
                student = User(
                    name='John Student',
                    email='student@studysync.pro',
                    registration_id='NU23UCA001',
                    password=pass_pw,
                    role='student',
                    department='Computer Science',
                    course_code='UCA',
                    semester=3,
                    cgpa=8.85,
                    status='active'
                )
                db.session.add(student)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[Notice] Auto-seed status: {e}")

    with app.app_context():
        try:
            db.create_all()
            ensure_default_accounts()
        except Exception:
            pass

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
