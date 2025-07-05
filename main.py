from fastapi import FastAPI, Request
from pydantic import BaseModel
import fitz  # PyMuPDF
import requests
import os
from supabase import create_client, Client
from uuid import uuid4

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "documents")
REDACTED_BUCKET = os.getenv("REDACTED_BUCKET", "redacted")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class RedactionItem(BaseModel):
    page: int
    bbox: BBox

class RedactionRequest(BaseModel):
    supabase_pdf_path: str
    items: list[RedactionItem]

@app.post("/redact")
def redact_pdf(req: RedactionRequest):
    print("Redacting PDF:", req.supabase_pdf_path)
    response = supabase.storage.from_(SUPABASE_BUCKET).download(req.supabase_pdf_path)
    if response is None:
        return {"status": "error", "message": "PDF not found"}

    file_bytes = response
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    for item in req.items:
        rect = fitz.Rect(item.bbox.x0, item.bbox.y0, item.bbox.x1, item.bbox.y1)
        page = doc[item.page]
        page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    output_path = f"{uuid4().hex}.pdf"
    doc.save(output_path)
    with open(output_path, "rb") as f:
        redacted_bytes = f.read()

    redacted_filename = f"redacted_{uuid4().hex}.pdf"
    supabase.storage.from_(REDACTED_BUCKET).upload(redacted_filename, redacted_bytes, {"content-type": "application/pdf"})

    return {"status": "ok", "redacted_file_path": f"{REDACTED_BUCKET}/{redacted_filename}"}
