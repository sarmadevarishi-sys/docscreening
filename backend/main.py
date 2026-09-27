"""
SatyaKavach — FastAPI Backend Server
Provides real AI inference endpoints for the frontend website.
Optimized for low-RAM cloud deployment (< 512MB RAM on Render Free Tier).
Run with:  uvicorn main:app --reload --port 8000
"""
import sys
import os
import gc

# Enforce strict single-thread and memory limits for low-RAM cloud environments
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MALLOC_TRIM_THRESHOLD_"] = "65536"
sys.path.insert(0, os.path.dirname(__file__))

try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

try:
    import cv2
    cv2.setNumThreads(1)
except Exception:
    pass

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contextlib import asynccontextmanager
import threading

def _warmup_models():
    """Warm up lightweight document classifier during server launch without spiking RAM."""
    print("[Warmup] Initializing primary document screener...")
    try:
        from models.image_model import _load_indian_id_validator
        _load_indian_id_validator()
        print("[Warmup] ✓ YOLO Layout Screener ready.")
    except Exception as e:
        print(f"[Warmup] YOLO preload warning: {e}")
    gc.collect()
    print("[Warmup] Core engine ready. Lazy loading active for OCR and biometric modules.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run model warmup in a worker thread so uvicorn binds port instantly
    threading.Thread(target=_warmup_models, daemon=True).start()
    yield

app = FastAPI(
    title="SatyaKavach API",
    description="Real AI backend for deepfake and scam detection",
    version="1.0.0",
    lifespan=lifespan
)

# Allow the frontend to call this server from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check — frontend pings this to know if the server is running."""
    return {"status": "ok", "server": "SatyaKavach API v1.0"}


@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze an uploaded Indian Identity Document:
    YOLO Classification + EasyOCR + Govt Rule Validation + Tamper/Forgery Detection.
    """
    try:
        file_bytes = await file.read()
        from models.image_model import analyze_image as run_image
        result = run_image(file_bytes)
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[Error] /analyze/image failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()


@app.post("/verify/face")
async def verify_face(doc_file: UploadFile = File(...), live_file: UploadFile = File(...)):
    """
    Module 4: 1:1 Face Verification
    Compares the face on the ID document against the live booth webcam snapshot.
    """
    try:
        doc_bytes = await doc_file.read()
        live_bytes = await live_file.read()
        from models.face_verifier import verify_1to1_face
        result = verify_1to1_face(doc_bytes, live_bytes)
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[Error] /verify/face failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        gc.collect()


# ─── FRONTEND STATIC HOSTING ────────────────────────────────────────────────
# Allows FastAPI to serve the entire website directly from the root URL /
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SatyaKavach API online"}

# Mount CSS, JS, Assets if available
for static_folder in ["css", "js", "assets"]:
    folder_path = os.path.join(FRONTEND_DIR, static_folder)
    if os.path.exists(folder_path):
        app.mount(f"/{static_folder}", StaticFiles(directory=folder_path), name=static_folder)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
