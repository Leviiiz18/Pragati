from app import create_app
from models import db, User, Event, Course, Subject, Specialization, Enrollment, Module, Unit, File
app = create_app()
with app.app_context():
    try:
        db.drop_all()
        db.create_all()
        print("TABLES CREATED SUCCESSFULLY")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
