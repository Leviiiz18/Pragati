"""Public landing page, early-access request flow and activation-key gate."""
import re
import secrets
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import current_user

from models import db, AccessRequest

landing_bp = Blueprint('landing', __name__)

ROLE_CHOICES = ['Student', 'Faculty', 'Head of Department', 'Administrator / Principal', 'Other']
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
KEY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no 0/O/1/I to avoid misreads


# ---------------------------------------------------------------------------
# Helpers shared with other blueprints
# ---------------------------------------------------------------------------
def normalize_key(raw):
    return re.sub(r'[^A-Z0-9-]', '', (raw or '').upper().strip())


def generate_activation_key():
    """PRG-XXXX-XXXX-XXXX, guaranteed unique."""
    while True:
        groups = [''.join(secrets.choice(KEY_ALPHABET) for _ in range(4)) for _ in range(3)]
        key = 'PRG-' + '-'.join(groups)
        if not AccessRequest.query.filter_by(activation_key=key).first():
            return key


def has_platform_access():
    """True when the visitor has unlocked the early-access gate in this browser."""
    if not current_app.config.get('ACCESS_GATE_ENABLED', True):
        return True
    if current_user.is_authenticated:
        return True
    key = session.get('access_key')
    if not key:
        return False
    if key == normalize_key(current_app.config.get('MASTER_ACTIVATION_KEY')):
        return True
    # Re-check on every visit so a revoked key stops working immediately
    return AccessRequest.query.filter_by(activation_key=key, status='approved').first() is not None


def dashboard_url_for(user):
    if user.role in ['super_admin', 'principal']:
        return url_for('super_admin.dashboard')
    if user.role == 'hod':
        return url_for('hod.dashboard')
    if user.role == 'faculty':
        return url_for('faculty.dashboard')
    return url_for('student.dashboard')


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@landing_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))
    return render_template('landing/home.html', has_access=has_platform_access())


@landing_bp.route('/pricing')
def pricing():
    return render_template('landing/pricing.html', has_access=has_platform_access())



@landing_bp.route('/request-access', methods=['GET', 'POST'])
def request_access():
    form = {}
    errors = {}

    if request.method == 'POST':
        form = {
            'full_name': (request.form.get('full_name') or '').strip(),
            'email': (request.form.get('email') or '').strip().lower(),
            'institution': (request.form.get('institution') or '').strip(),
            'role': (request.form.get('role') or '').strip(),
            'phone': (request.form.get('phone') or '').strip(),
            'purpose': (request.form.get('purpose') or '').strip(),
            'consent': request.form.get('consent'),
        }

        # Honeypot field: bots fill hidden inputs, humans don't
        if request.form.get('website'):
            return redirect(url_for('landing.home'))

        if len(form['full_name']) < 2:
            errors['full_name'] = 'Please enter your full name.'
        if not EMAIL_RE.match(form['email']):
            errors['email'] = 'Please enter a valid email address.'
        if len(form['institution']) < 2:
            errors['institution'] = 'Please tell us your institution.'
        if form['role'] not in ROLE_CHOICES:
            errors['role'] = 'Please choose your role.'
        if len(form['purpose']) > 1500:
            errors['purpose'] = 'Please keep this under 1500 characters.'
        if not form['consent']:
            errors['consent'] = 'Please confirm so we can contact you about your request.'

        if not errors:
            existing = AccessRequest.query.filter(
                AccessRequest.email == form['email'],
                AccessRequest.status.in_(['pending', 'approved'])
            ).order_by(AccessRequest.created_at.desc()).first()

            if existing:
                return render_template('landing/request_submitted.html', req=existing, duplicate=True)

            req = AccessRequest(
                full_name=form['full_name'][:150],
                email=form['email'][:150],
                institution=form['institution'][:200],
                role=form['role'],
                phone=form['phone'][:30] or None,
                purpose=form['purpose'] or None,
                status='pending',
            )
            db.session.add(req)
            db.session.commit()
            return render_template('landing/request_submitted.html', req=req, duplicate=False)

    return render_template('landing/request_access.html', form=form, errors=errors, roles=ROLE_CHOICES)


@landing_bp.route('/activate', methods=['GET', 'POST'])
def activate():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    if request.method == 'POST':
        key = normalize_key(request.form.get('activation_key'))
        master = normalize_key(current_app.config.get('MASTER_ACTIVATION_KEY'))

        if key and key == master:
            session.permanent = True
            session['access_key'] = key
            flash('Team access unlocked. You can now sign in.', 'success')
            return redirect(url_for('auth.login'))

        req = AccessRequest.query.filter_by(activation_key=key).first() if key else None
        if not req:
            flash('That activation key was not recognised. Check for typos and try again.', 'danger')
            return render_template('landing/activate.html', entered_key=key), 400
        if req.status != 'approved':
            flash('This activation key is no longer active. Contact the Pragati team for help.', 'danger')
            return render_template('landing/activate.html', entered_key=key), 403

        req.activation_count = (req.activation_count or 0) + 1
        if not req.first_activated_at:
            req.first_activated_at = datetime.utcnow()
        db.session.commit()

        session.permanent = True
        session['access_key'] = key
        flash(f'Welcome, {req.full_name.split()[0]}. Your early access is active. Sign in to continue.', 'success')
        return redirect(url_for('auth.login'))

    if has_platform_access() and session.get('access_key'):
        return redirect(url_for('auth.login'))

    return render_template('landing/activate.html', entered_key=request.args.get('key', ''))
