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

    app.register_blueprint(auth_bp)
    app.register_blueprint(super_admin_bp, url_prefix='/super_admin')
    app.register_blueprint(hod_bp, url_prefix='/hod')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(events_bp)
    app.register_blueprint(ai_api_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role in ['super_admin', 'principal']:
                return redirect(url_for('super_admin.dashboard'))
            elif current_user.role == 'hod':
                return redirect(url_for('hod.dashboard'))
            elif current_user.role == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    if not os.path.exists(app.config.get('UPLOAD_FOLDER', 'uploads')):
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'))

    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
