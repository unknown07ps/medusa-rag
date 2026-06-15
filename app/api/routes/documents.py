import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.rag.ingestion import ingest_file, ingest_text

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_MB = 20


class IngestTextRequest(BaseModel):
    text: str
    source_name: str = "inline_text"


class IngestResponse(BaseModel):
    doc_id: str
    source_hash: str
    chunk_count: int
    filename: str


@router.post("/upload", response_model=IngestResponse)
async def upload_document(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Limit is {MAX_FILE_SIZE_MB} MB.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await ingest_file(tmp_path, metadata={"original_filename": file.filename})
    finally:
        os.unlink(tmp_path)

    return IngestResponse(**result)


@router.post("/text", response_model=IngestResponse)
async def ingest_text_endpoint(body: IngestTextRequest):
    if len(body.text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Text too short to be useful.")
    result = await ingest_text(body.text, source_name=body.source_name)
    return IngestResponse(**result)
