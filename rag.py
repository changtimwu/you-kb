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

def vtt_timestamp_to_seconds(ts):
    """Convert HH:MM:SS.mmm to total seconds."""
    try:
        parts = ts.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
    except:
        return 0
    return 0

def parse_vtt(vtt_path):
    """Parse VTT file into a list of dictionaries with text and start timestamp."""
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove WEBVTT header
    content = re.sub(r'^WEBVTT\n+', '', content)
    
    # Split by blocks (usually separated by empty lines)
    blocks = content.split('\n\n')
    entries = []
    
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue
            
        # Check if first line is a timestamp
        ts_match = re.match(r'(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3}) -->', lines[0])
        if ts_match:
            start_ts_str = ts_match.group(1)
            seconds = vtt_timestamp_to_seconds(start_ts_str)
            text = " ".join(lines[1:])
            entries.append({"ts": seconds, "text": text})
        elif len(lines) > 1 and re.match(r'(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3}) -->', lines[1]):
            # Sometimes there's a sequence number before the timestamp
            ts_match = re.match(r'(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3}) -->', lines[1])
            start_ts_str = ts_match.group(1)
            seconds = vtt_timestamp_to_seconds(start_ts_str)
            text = " ".join(lines[2:])
            entries.append({"ts": seconds, "text": text})

    return entries

def chunk_entries(entries, chunk_size=1000, overlap_size=200):
    """Group VTT entries into larger chunks."""
    chunks = []
    if not entries:
        return chunks
        
    current_text = ""
    current_start_ts = entries[0]['ts']
    
    for entry in entries:
        if len(current_text) + len(entry['text']) > chunk_size:
            chunks.append({
                "text": current_text.strip(),
                "ts": current_start_ts
            })
            # Start new chunk
            # For simplicity, we don't do complex text overlap here to keep timestamps clean
            current_text = entry['text'] + " "
            current_start_ts = entry['ts']
        else:
            current_text += entry['text'] + " "
            
    if current_text:
        chunks.append({
            "text": current_text.strip(),
            "ts": current_start_ts
        })
        
    return chunks

def create_kb(kb_name, downloads_dir="downloads"):
    """Create or update a LanceDB knowledge base from VTT files."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    data = []
    
    if not os.path.exists(downloads_dir):
        print(f"Directory {downloads_dir} not found.")
        return

    # Find all VTT files recursively if needed, but for now just downloads_dir
    vtt_files = []
    for root, dirs, files in os.walk(downloads_dir):
        for f in files:
            if f.endswith('.vtt'):
                vtt_files.append(os.path.join(root, f))

    if not vtt_files:
        print("No .vtt files found.")
        return

    print(f"Indexing {len(vtt_files)} transcriptions...")
    
    for vtt_path in vtt_files:
        filename = os.path.basename(vtt_path)
        # Assuming filename is VIDEO_ID.vtt or Title-VIDEO_ID.en.vtt
        # Standard yt-dlp might be different. Let's try to extract 11-char ID
        video_id = ""
        # Look for 11 char ID (common YT format)
        id_match = re.search(r'([a-zA-Z0-9_-]{11})\.([a-z-]{2,5}\.)?vtt$', filename)
        if id_match:
            video_id = id_match.group(1)
        else:
            # Fallback: remove extension
            video_id = os.path.splitext(filename)[0]

        entries = parse_vtt(vtt_path)
        chunks = chunk_entries(entries)
        
        print(f"Processing {len(chunks)} chunks for {filename}...")
        for chunk in chunks:
            embedding = get_embedding(chunk['text'])
            data.append({
                "vector": embedding,
                "text": chunk['text'],
                "video_id": video_id,
                "ts": chunk['ts'],
                "source": filename
            })
    
    # Create or overwrite table
    table_name = kb_name
    if table_name in db.table_names():
        db.drop_table(table_name)
    
    db.create_table(table_name, data=data)
    print(f"Knowledge base '{kb_name}' created successfully with {len(data)} chunks.")

def chat_with_kb(kb_name, query):
    """Search KB and generate response with YouTube timestamp citations."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    if kb_name not in db.table_names():
        print(f"Knowledge base '{kb_name}' not found.")
        return "KB not found", []
    
    table = db.open_table(kb_name)
    
    # 1. Embed query
    query_embedding = get_embedding(query, model="models/text-embedding-004")
    
    # 2. Search LanceDB
    results = table.search(query_embedding).limit(5).to_pandas()
    
    # Construct context with unique identifiers for citations
    context_lines = []
    citations = []
    
    for i, row in results.iterrows():
        video_id = row['video_id']
        ts = int(row['ts'])
        url = f"https://youtu.be/{video_id}?t={ts}"
        ref_id = i + 1
        context_lines.append(f"[{ref_id}] (Source: {url})\n{row['text']}")
        citations.append(f"[{ref_id}] {url}")
    
    context = "\n\n".join(context_lines)
    
    # 3. Generate response
    model = genai.GenerativeModel("gemini-3-flash-preview")
    prompt = f"""
You are a helpful assistant. Use the following pieces of context from YouTube transcripts to answer the user's question.
Every time you use information from a context block, you MUST cite it using the format [N], where N is the reference number.

Context:
{context}

Question: {query}

Answer (including citations like [1], [2], etc.):
"""
    response = model.generate_content(prompt)
    return response.text, citations

if __name__ == "__main__":
    # Test
    # create_kb("test_kb")
    # print(chat_with_kb("test_kb", "What is this video about?"))
    pass
