from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/redact-pdf")
async def redact_pdf(request: Request):
    data = await request.json()
    print("Received request:", data)

    job_id = data.get("jobId")
    supabase_url = data.get("supabase_url")
    supabase_key = data.get("supabase_key")

    if not job_id or not supabase_url or not supabase_key:
        return JSONResponse(status_code=400, content={"error": "Missing required fields"})

    # Simulate PDF redaction for now
    return {"success": True, "jobId": job_id, "message": "Redaction complete (mocked)"}
