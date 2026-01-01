import os
import lancedb
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rag import chat_with_kb

app = FastAPI(title="You-KB GPT")

# Model for chat requests
class ChatRequest(BaseModel):
    kb_name: str
    query: str

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r") as f:
        return f.read()

@app.get("/kbs")
async def list_kbs():
    db_path = ".lancedb"
    if not os.path.exists(db_path):
        return []
    db = lancedb.connect(db_path)
    return db.table_names()

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response, citations = chat_with_kb(request.kb_name, request.query)
        # Parse citations into a more structured format for the UI if possible
        # citations currently looks like: ["[1] https://youtu.be/ID?t=S", ...]
        structured_citations = []
        for c in citations:
            # Simple regex to extract id and time
            import re
            match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})\?t=(\d+)", c)
            if match:
                structured_citations.append({
                    "ref": c.split("]")[0] + "]",
                    "video_id": match.group(1),
                    "time": int(match.group(2)),
                    "url": c.split(" ", 1)[1]
                })
        
        return {
            "response": response,
            "citations": structured_citations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
