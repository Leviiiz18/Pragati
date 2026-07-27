import os
import json
import numpy as np
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer

# Load model locally
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    text = ""
    try:
        if ext == '.pdf':
            reader = PdfReader(filepath)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + " "
        elif ext == '.docx':
            doc = Document(filepath)
            for para in doc.paragraphs:
                text += para.text + " "
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
    return text.strip()

def chunk_text(text, chunk_size=400, overlap=50):
    if not text:
        return []
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks

def get_embedding(text):
    embedding = model.encode(text)
    return embedding.tolist()

def get_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
