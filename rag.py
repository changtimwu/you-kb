import os
import lancedb
import pandas as pd
import google.generativeai as genai
import re
from transcribe import get_api_key

# Configure Gemini
api_key = get_api_key()
if api_key:
    genai.configure(api_key=api_key)

def get_embedding(text, model="models/text-embedding-004"):
    """Generate embedding for a piece of text using Gemini."""
    result = genai.embed_content(
        model=model,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def parse_vtt(vtt_path):
    """Simple VTT parser to extract text content."""
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove WEBVTT header
    content = re.sub(r'^WEBVTT\n+', '', content)
    
    # Remove timestamps and metadata
    # Format: 00:00:00.000 --> 00:00:00.000
    content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\n', '', content)
    
    # Remove blank lines and join
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    return " ".join(lines)

def chunk_text(text, chunk_size=1000, overlap=200):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

def create_kb(kb_name, downloads_dir="downloads"):
    """Create or update a LanceDB knowledge base from VTT files."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    data = []
    
    if not os.path.exists(downloads_dir):
        print(f"Directory {downloads_dir} not found.")
        return

    vtt_files = [f for f in os.listdir(downloads_dir) if f.endswith('.vtt')]
    if not vtt_files:
        print("No .vtt files found in downloads directory.")
        return

    print(f"Indexing {len(vtt_files)} transcriptions...")
    
    for vtt_file in vtt_files:
        path = os.path.join(downloads_dir, vtt_file)
        text = parse_vtt(path)
        chunks = chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} for {vtt_file}...")
            embedding = get_embedding(chunk)
            data.append({
                "vector": embedding,
                "text": chunk,
                "source": vtt_file
            })
    
    # Create or overwrite table
    table_name = kb_name
    if table_name in db.table_names():
        db.drop_table(table_name)
    
    db.create_table(table_name, data=data)
    print(f"Knowledge base '{kb_name}' created successfully with {len(data)} chunks.")

def chat_with_kb(kb_name, query):
    """Search KB and generate response using Gemini."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    if kb_name not in db.table_names():
        print(f"Knowledge base '{kb_name}' not found.")
        return
    
    table = db.open_table(kb_name)
    
    # 1. Embed query
    query_embedding = get_embedding(query, model="models/text-embedding-004")
    
    # 2. Search LanceDB
    results = table.search(query_embedding).limit(5).to_pandas()
    context = "\n\n".join(results['text'].tolist())
    
    # 3. Generate response
    model = genai.GenerativeModel("gemini-3-flash-preview")
    prompt = f"""
You are a helpful assistant. Use the following pieces of context from YouTube transcripts to answer the user's question.
If you don't know the answer based on the context, just say that you don't know. Don't try to make up an answer.

Context:
{context}

Question: {query}

Answer:
"""
    response = model.generate_content(prompt)
    return response.text, results['source'].unique().tolist()

if __name__ == "__main__":
    # Test
    # create_kb("test_kb")
    # print(chat_with_kb("test_kb", "What is this video about?"))
    pass
