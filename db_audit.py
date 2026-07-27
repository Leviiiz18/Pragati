from app import create_app
from models import db, File

app = create_app()

def check_files():
    with app.app_context():
        files = File.query.all()
        print(f"Total Files in DB: {len(files)}")
        for f in files[:10]:
            print(f"ID: {f.id}, Name: {f.filename}, Path: {f.filepath}")

if __name__ == '__main__':
    check_files()
