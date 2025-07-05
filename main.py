import fitz  # PyMuPDF
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import io
import json
from typing import List, Dict
import uvicorn
import os

app = FastAPI(title="PDF Redaction Service", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-redaction"}

@app.post("/redact-pdf")
async def redact_pdf(
    pdf_file: UploadFile = File(...),
    redaction_items: str = Form(...)
):
    """
    Redact a PDF file based on provided redaction items.
    
    Args:
        pdf_file: The original PDF file to redact
        redaction_items: JSON string containing list of redaction items with bounding boxes
    
    Returns:
        The redacted PDF file
    """
    try:
        # Parse redaction items
        items = json.loads(redaction_items)
        print(f"Received {len(items)} redaction items")
        
        # Read PDF file
        pdf_bytes = await pdf_file.read()
        print(f"PDF file size: {len(pdf_bytes)} bytes")
        
        # Open PDF with PyMuPDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"PDF has {pdf_doc.page_count} pages")
        
        # Group redaction items by page
        items_by_page = {}
        for item in items:
            page_num = item.get('page', 1) - 1  # Convert to 0-based indexing
            if page_num not in items_by_page:
                items_by_page[page_num] = []
            items_by_page[page_num].append(item)
        
        # Apply redactions page by page
        for page_num, page_items in items_by_page.items():
            if page_num >= pdf_doc.page_count:
                print(f"Warning: Page {page_num + 1} does not exist in PDF")
                continue
                
            page = pdf_doc[page_num]
            print(f"Processing page {page_num + 1} with {len(page_items)} redactions")
            
            # Create redaction rectangles
            for item in page_items:
                bbox = item.get('bbox', {})
                if not bbox:
                    print(f"Warning: No bbox found for item {item.get('id', 'unknown')}")
                    continue
                
                # Convert bbox to PyMuPDF rectangle
                # Note: PDF coordinates start from bottom-left, but our detection might be top-left
                x = bbox.get('x', 0)
                y = bbox.get('y', 0)
                width = bbox.get('width', 0)
                height = bbox.get('height', 0)
                
                # Create rectangle for redaction
                rect = fitz.Rect(x, y, x + width, y + height)
                
                # Add redaction annotation
                redact_annot = page.add_redact_annot(rect)
                redact_annot.set_info(content=f"Redacted: {item.get('type', 'sensitive')}")
                
                print(f"Added redaction at ({x}, {y}, {x + width}, {y + height}) for {item.get('type', 'unknown')}")
        
        # Apply all redactions
        for page in pdf_doc:
            page.apply_redactions()
        
        # Save redacted PDF to bytes
        redacted_pdf_bytes = pdf_doc.write()
        pdf_doc.close()
        
        print(f"Redaction complete. Output size: {len(redacted_pdf_bytes)} bytes")
        
        # Return the redacted PDF
        return Response(
            content=redacted_pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=redacted_document.pdf"
            }
        )
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in redaction_items: {str(e)}")
    except Exception as e:
        print(f"Error during redaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Redaction failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
