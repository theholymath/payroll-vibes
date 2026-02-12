import uuid
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import ChatRequest, ChatResponse
from app.anthropic_client import upload_file, create_session, analyze_spreadsheet, sessions

app = FastAPI(title="Payroll Error Checker")

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/upload")
async def handle_upload(file: UploadFile = File(...)):
    """Upload a spreadsheet, send to Anthropic Files API, return session info."""
    if not file.filename or not file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(400, "Only .xls and .xlsx files are accepted.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large. Maximum size is 25MB.")

    # Save to temp file, upload to Anthropic
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        file_id = upload_file(tmp_path)
    finally:
        tmp_path.unlink()

    session_id = str(uuid.uuid4())
    create_session(session_id, file_id)

    return {"session_id": session_id, "file_id": file_id, "filename": file.filename}


@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(req: ChatRequest):
    """Send a chat message. First message triggers full analysis; subsequent are follow-ups."""
    if req.session_id not in sessions:
        raise HTTPException(400, "Invalid session. Please upload a file first.")

    reply = analyze_spreadsheet(req.session_id, req.message)

    return ChatResponse(reply=reply, session_id=req.session_id)
