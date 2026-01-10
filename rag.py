import os
import lancedb
import pandas as pd
import google.generativeai as genai
import re
import hashlib
import glob
import pyarrow as pa
from typing import List, Dict, Any
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

def create_kb(kb_name: str) -> bool:
    """Create empty knowledge base table with proper schema."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    if kb_name in db.table_names():
        print(f"Knowledge base '{kb_name}' already exists.")
        return False
    
    # Create empty table with sample data to establish schema
    import pyarrow as pa
    
    schema = pa.schema([
        pa.field("vector", pa.list_(pa.float32())),  # Vector field
        pa.field("text", pa.string()), 
        pa.field("video_id", pa.string()),
        pa.field("ts", pa.float64()),
        pa.field("source", pa.string()),
        pa.field("file_type", pa.string()),
        pa.field("file_path", pa.string()), 
        pa.field("file_hash", pa.string())
    ])
    
    # Create with empty data
    empty_data = []
    db.create_table(kb_name, data=empty_data, schema=schema)
    print(f"Knowledge base '{kb_name}' created successfully (empty).")
    return True

def discover_documents(source_paths: List[str], 
                    patterns: List[str] = None,
                    recursive: bool = True) -> List[str]:
    """Discover files matching patterns across multiple source paths."""
    if patterns is None:
        patterns = ["*.vtt", "*.txt", "*.md"]
    
    all_files = []
    for source_path in source_paths:
        if os.path.isfile(source_path):
            all_files.append(source_path)
        elif os.path.isdir(source_path):
            for pattern in patterns:
                if recursive:
                    search_pattern = os.path.join(source_path, "**", pattern)
                    files = glob.glob(search_pattern, recursive=True)
                else:
                    search_pattern = os.path.join(source_path, pattern)
                    files = glob.glob(search_pattern)
                all_files.extend(files)
    
    return list(set(all_files))  # Remove duplicates

def parse_txt(txt_path: str) -> List[Dict]:
    """Parse TXT file into text entries with fake timestamps."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(txt_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    entries = []
    for i, paragraph in enumerate(paragraphs):
        entries.append({
            "ts": 0.0,  # Fake timestamp for non-video content
            "text": paragraph
        })
    return entries

def parse_md(md_path: str) -> List[Dict]:
    """Parse MD file into section-based entries."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(md_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Split by markdown headers
    sections = re.split(r'\n(^#{1,6}\s+.+$)\n', content, flags=re.MULTILINE)
    
    entries = []
    for i in range(1, len(sections), 2):
        if i+1 < len(sections):
            header = sections[i].strip()
            text = sections[i+1].strip()
            if text:  # Skip empty sections
                entries.append({
                    "ts": 0.0,
                    "text": f"{header}\n{text}"
                })
    
    # If no headers found, split into paragraphs
    if not entries:
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        for paragraph in paragraphs:
            entries.append({
                "ts": 0.0,
                "text": paragraph
            })
    
    return entries

def get_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file for change tracking."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    except Exception:
        return ""
    return hash_md5.hexdigest()

def process_document(file_path: str) -> List[Dict]:
    """Process a single document based on file type."""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.vtt':
        return parse_vtt(file_path)
    elif file_ext == '.txt':
        return parse_txt(file_path)
    elif file_ext in ['.md', '.markdown']:
        return parse_md(file_path)
    else:
        print(f"Warning: Unsupported file type {file_ext} - skipping {file_path}")
        return []

def extract_video_id_from_vtt(filename: str) -> str:
    """Extract YouTube video ID from VTT filename."""
    # Look for 11 char ID (common YT format)
    id_match = re.search(r'([a-zA-Z0-9_-]{11})\.([a-z-]{2,5}\.)?vtt$', filename)
    if id_match:
        return id_match.group(1)
    else:
        # Fallback: remove extension
        return os.path.splitext(filename)[0]

def create_content_chunks(entries: List[Dict], 
                        file_type: str,
                        chunk_size: int = 1000) -> List[Dict]:
    """Create chunks from different file types with appropriate metadata."""
    if not entries:
        return []
        
    chunks = []
    current_text = ""
    current_start_ts = entries[0]['ts'] if entries else 0.0
    
    for entry in entries:
        if len(current_text) + len(entry['text']) > chunk_size:
            if current_text.strip():
                chunks.append({
                    "text": current_text.strip(),
                    "ts": current_start_ts
                })
            current_text = entry['text'] + " "
            current_start_ts = entry['ts']
        else:
            current_text += entry['text'] + " "
    
    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
            "ts": current_start_ts
        })
        
    return chunks

def digest_documents(kb_name: str, 
                   source_paths: List[str],
                   patterns: List[str] = None,
                   recursive: bool = True) -> Dict[str, Any]:
    """Process documents and add embeddings to specified KB."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    if kb_name not in db.table_names():
        print(f"Knowledge base '{kb_name}' not found. Create it first with --kb-create.")
        return {"status": "error", "message": "KB not found"}
    
    # Discover documents
    files = discover_documents(source_paths, patterns, recursive)
    if not files:
        print("No documents found matching the specified patterns.")
        return {"status": "error", "message": "No documents found"}
    
    print(f"Found {len(files)} documents to process...")
    
    table = db.open_table(kb_name)
    processed_count = 0
    skipped_count = 0
    total_chunks = 0
    
    for file_path in files:
        try:
            filename = os.path.basename(file_path)
            file_type = os.path.splitext(filename)[1][1:].lower()  # Remove dot
            file_hash = get_file_hash(file_path)
            
            # Skip if already processed (check by file hash)
            existing = table.to_pandas().query(f"file_hash == '{file_hash}'")
            if not existing.empty:
                print(f"Skipping {filename} (already processed)")
                skipped_count += 1
                continue
            
            # Process document
            entries = process_document(file_path)
            if not entries:
                continue
            
            # Create chunks
            chunks = create_content_chunks(entries, file_type)
            if not chunks:
                continue
            
            # Get video ID for VTT files
            video_id = ""
            if file_type == 'vtt':
                video_id = extract_video_id_from_vtt(filename)
            
            # Create data for database
            data = []
            for chunk in chunks:
                embedding = get_embedding(chunk['text'])
                data.append({
                    "vector": embedding,
                    "text": chunk['text'],
                    "video_id": video_id,
                    "ts": chunk['ts'],
                    "source": filename,
                    "file_type": file_type,
                    "file_path": file_path,
                    "file_hash": file_hash
                })
            
            # Add to table
            if data:
                table.add(data)
                processed_count += 1
                total_chunks += len(data)
                print(f"Processed {filename}: {len(data)} chunks")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    result = {
        "status": "success",
        "processed_files": processed_count,
        "skipped_files": skipped_count,
        "total_chunks": total_chunks
    }
    
    print(f"\nDigestion complete:")
    print(f"  Processed: {processed_count} files")
    print(f"  Skipped: {skipped_count} files (already processed)")
    print(f"  Total chunks: {total_chunks}")
    
    return result

def list_knowledge_bases():
    """List all knowledge bases with document counts and file type stats."""
    db_path = ".lancedb"
    if not os.path.exists(db_path):
        print("No knowledge bases found.")
        return
        
    db = lancedb.connect(db_path)
    table_names = db.table_names()
    
    if not table_names:
        print("No knowledge bases found.")
        return
        
    print("Available Knowledge Bases:")
    print("=" * 50)
    for table_name in table_names:
        table = db.open_table(table_name)
        count = table.count_rows()
        # Get file type statistics
        try:
            full_df = table.to_pandas()
            if 'file_type' in full_df.columns:
                file_types = full_df['file_type'].value_counts().to_dict()
                file_types_str = ", ".join([f"{ft}({cnt})" for ft, cnt in file_types.items()])
                print(f"{table_name:20} {count:8} chunks  ({file_types_str})")
            else:
                print(f"{table_name:20} {count:8} chunks")
        except Exception:
            print(f"{table_name:20} {count:8} chunks")

def show_kb_details(kb_name: str):
    """Show detailed information about a knowledge base."""
    db_path = ".lancedb"
    db = lancedb.connect(db_path)
    
    if kb_name not in db.table_names():
        print(f"Knowledge base '{kb_name}' not found.")
        return
        
    table = db.open_table(kb_name)
    
    # Get basic stats
    total_chunks = table.count_rows()
    df = table.to_pandas()
    
    print(f"Knowledge Base: {kb_name}")
    print("=" * 50)
    print(f"Total chunks: {total_chunks}")
    
    # Analyze file types
    if 'file_type' in df.columns:
        file_types = df['file_type'].value_counts().to_dict()
        print(f"File types: {dict(file_types)}")
    
    # Source files
    if 'source' in df.columns:
        source_files = df['source'].nunique()
        print(f"Source files: {source_files}")
        
        print("\nSource Files:")
        for source in sorted(df['source'].unique()):
            count = df[df['source'] == source].shape[0]
            file_type = df[df['source'] == source]['file_type'].iloc[0] if 'file_type' in df.columns else 'unknown'
            print(f"  {source} ({count} chunks, {file_type})")
    
    # Video IDs (for VTT files)
    if 'video_id' in df.columns:
        video_ids = df[df['video_id'] != '']['video_id'].nunique()
        print(f"Videos: {video_ids}")

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
