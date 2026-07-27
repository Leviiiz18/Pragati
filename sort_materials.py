import os
import shutil
from app import create_app
from models import db, Subject, Module, Unit, File

app = create_app()

def sort_materials():
    with app.app_context():
        source_dir = os.path.join(app.root_path, 'FILES')
        upload_base = app.config['UPLOAD_FOLDER']
        
        if not os.path.exists(source_dir):
            print(f"Source directory {source_dir} not found.")
            return

        files = os.listdir(source_dir)
        print(f"Found {len(files)} files to sort.")

        for filename in files:
            # Extract subject code (e.g., AIML101 from AIML101.pdf)
            code = filename.split('.')[0]
            ext = filename.split('.')[-1]
            
            subject = Subject.query.filter_by(code=code).first()
            if not subject:
                print(f"No subject found for code: {code} (File: {filename})")
                continue
            
            # Use First Module and Unit as destination (or create if missing)
            module = Module.query.filter_by(subject_id=subject.id).first()
            if not module:
                module = Module(title="Main Module", subject_id=subject.id)
                db.session.add(module)
                db.session.commit()
            
            unit = Unit.query.filter_by(module_id=module.id).first()
            if not unit:
                unit = Unit(title="Resource Unit", module_id=module.id)
                db.session.add(unit)
                db.session.commit()
            
            # Destination Path
            subject_dir_name = subject.name.replace(' ', '_')
            dest_dir = os.path.join(upload_base, subject_dir_name)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            dest_path = os.path.join(dest_dir, filename)
            rel_path = os.path.join(subject_dir_name, filename)
            
            # Copy file
            src_path = os.path.join(source_dir, filename)
            shutil.copy2(src_path, dest_path)
            
            # Check if file record already exists
            existing_file = File.query.filter_by(unit_id=unit.id, filename=filename).first()
            if not existing_file:
                new_file = File(
                    unit_id=unit.id,
                    filename=filename,
                    filepath=rel_path,
                    filetype=ext
                )
                db.session.add(new_file)
                print(f"Added {filename} to {subject.name}")
            else:
                print(f"File {filename} already exists in DB.")
        
        db.session.commit()
        print("Sorting and DB update complete!")

if __name__ == '__main__':
    sort_materials()
