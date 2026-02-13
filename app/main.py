import logging
import uuid
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import ChatRequest, ChatResponse
from app.anthropic_client import upload_file, create_session, analyze_spreadsheet, sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("payroll")

app = FastAPI(title="Payroll Error Checker")

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/health/metrics")
async def health_metrics():
    return {"status": "ok", "active_sessions": len(sessions)}


@app.post("/api/upload")
async def handle_upload(file: UploadFile = File(...)):
    """Upload a spreadsheet, send to Anthropic Files API, return session info."""
    logger.info("POST /api/upload - file=%s size=pending", file.filename)

    if not file.filename or not file.filename.lower().endswith((".xls", ".xlsx")):
        logger.warning("Upload rejected: invalid file type %s", file.filename)
        raise HTTPException(400, "Only .xls and .xlsx files are accepted.")

    content = await file.read()
    logger.info("File read: %s (%.1f KB)", file.filename, len(content) / 1024)

    if len(content) > MAX_FILE_SIZE:
        logger.warning("Upload rejected: file too large (%d bytes)", len(content))
        raise HTTPException(400, "File too large. Maximum size is 25MB.")

    # Save to temp file, upload to Anthropic
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        logger.info("Uploading to Anthropic Files API...")
        file_id = upload_file(tmp_path)
        logger.info("Anthropic upload complete: file_id=%s", file_id)
    finally:
        tmp_path.unlink()

    session_id = str(uuid.uuid4())
    create_session(session_id, file_id)
    logger.info("Session created: session_id=%s", session_id)

    return {"session_id": session_id, "file_id": file_id, "filename": file.filename}


@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(req: ChatRequest):
    """Send a chat message. First message triggers full analysis; subsequent are follow-ups."""
    logger.info("POST /api/chat - session=%s message=%s", req.session_id, req.message[:80])

    if req.session_id not in sessions:
        logger.warning("Chat rejected: unknown session %s", req.session_id)
        raise HTTPException(400, "Invalid session. Please upload a file first.")

    logger.info("Sending to Anthropic API (this may take a while)...")
    reply = analyze_spreadsheet(req.session_id, req.message)
    logger.info("Response received (%d chars)", len(reply))

    return ChatResponse(reply=reply, session_id=req.session_id)
