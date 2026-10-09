import os
import secrets
from datetime import timedelta

db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

class Config:
    # Deterministic fallback secret key ensures sessions persist across multiple Gunicorn workers & cloud restarts
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pragati-production-cloud-secret-key-kalpkrats-2026-v1'
    SQLALCHEMY_DATABASE_URI = db_url or 'sqlite:///studysync.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'ppt', 'pptx', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'zip'}

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # SESSION_COOKIE_SECURE: Set to True via env var only when strict HTTPS-only cookie is desired
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('true', '1')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('true', '1')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max payload

    # Early-access gate: visitors must activate with a key before reaching the login
    ACCESS_GATE_ENABLED = os.environ.get('ACCESS_GATE_ENABLED', 'true').lower() in ('true', '1')
    # Internal team key that always unlocks the gate (override in production via env var)
    MASTER_ACTIVATION_KEY = os.environ.get('MASTER_ACTIVATION_KEY', 'PRG-TEAM-CORE-2026')
