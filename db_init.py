from app import create_app
from models import db
import os

app = create_app()

def reset_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database dropped and recreated.")

if __name__ == '__main__':
    reset_db()
