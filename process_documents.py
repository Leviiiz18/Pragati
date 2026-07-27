import os
import json
from app import create_app
from models import db, File, DocumentChunk
from rag_utils import extract_text, chunk_text, get_embedding

app = create_app()

def process_documents():
    with app.app_context():
        # Clear existing chunks to avoid duplicates during dev
        db.session.query(DocumentChunk).delete()
        
        files = File.query.all()
        print(f"Processing {len(files)} files...")
        
        for file_rec in files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_rec.filepath)
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                continue
                
            print(f"Indexing: {file_rec.filename}")
            text = extract_text(filepath)
            if not text:
                continue
                
            chunks = chunk_text(text)
            for chunk_content in chunks:
                embedding = get_embedding(chunk_content)
                new_chunk = DocumentChunk(
                    module_id=file_rec.unit.module_id,
                    file_id=file_rec.id,
                    content=chunk_content,
                    embedding=json.dumps(embedding)
                )
                db.session.add(new_chunk)
            
            db.session.commit()
        
        print("Indexing complete!")

if __name__ == '__main__':
    process_documents()
