import io
import os
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SIH 2026 Advanced Indian ID Authentication Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared memory model cache
_yolo_classifier = None

M2_REPO = "logasanjeev/indian-id-validator"

# =====================================================================
# 1. APPLICATION ENGINE LOADERS
# =====================================================================

def _load_indian_id_validator():
    global _yolo_classifier
    if _yolo_classifier is None:
        try:
            from ultralytics import YOLO
            local_path = os.path.join(os.path.dirname(__file__), "weights", "Id_Classifier.pt")
            if os.path.exists(local_path):
                print(f"[IM] Loading local Main Document Screener from {local_path}...")
                _yolo_classifier = YOLO(local_path)
            else:
                from huggingface_hub import hf_hub_download
                print(f"[IM] Fetching Main Document Screener from HF ({M2_REPO})...")
                model_path = hf_hub_download(repo_id=M2_REPO, filename="models/Id_Classifier.pt")
                _yolo_classifier = YOLO(model_path)
            print(f"[IM] Main document screener online.")
        except Exception as e:
            print(f"[IM] failed initializing {M2_REPO}: {e}")
    return _yolo_classifier

# =====================================================================
# 2. RUNTIME PIPELINE ARCHITECTURE
# =====================================================================

def _run_main_document_screener(img):
    """STEP 1: Runs whole layout checks to catch structural anomalies."""
    model = _load_indian_id_validator()
    if model is None:
        return None, 50
    try:
        results = model(img, verbose=False)
        result = results[0] if isinstance(results, list) else results
            
        if hasattr(result, 'probs') and result.probs is not None:
            top_idx = result.probs.top1
            top_label = result.names[top_idx]
            top_conf = float(result.probs.top1conf)
            
            print(f"[IM] Screener Result: Document Type='{top_label}' | Confidence: {top_conf:.4f}")
            
            # Smooth proportional risk calculation (high confidence -> low risk)
            structural_risk = int(round(max(10, min(80, (1.0 - top_conf) * 100))))
            
            return {
                "detected_document_type": top_label,
                "structural_confidence": round(top_conf * 100, 2)
            }, structural_risk
        else:
            return {"note": "Unidentified Document Structure"}, 50
    except Exception as e:
        print(f"[IM] Main Screener Error: {e}")
        return None, 50


def _exif(img):
    try:
        ex = img._getexif()
    except Exception:
        ex = None
    if ex is None:
        # Scanned documents, e-PANs, and crops typically do not preserve EXIF camera tags.
        return 15, {"exifPresent": False, "note": "Standard scanned document (no camera EXIF tags)"}
    risk = 20
    info = {"exifPresent": True}
    if ex.get(271): risk -= 10; info["make"]  = str(ex.get(271))
    if ex.get(272): risk -= 10; info["model"] = str(ex.get(272))
    return max(0, risk), info

# =====================================================================
# 3. CORE ANALYZER RUN ROUTING
# =====================================================================

def analyze_image(fb: bytes) -> dict:
    pil_img = Image.open(io.BytesIO(fb)).convert("RGB")
    W, H  = pil_img.size
    rows  = []
    raw   = {}

    # 1. Main Document Structural Screener
    screener_meta, screener_risk = _run_main_document_screener(pil_img)
    raw["document_screener"] = {"risk": screener_risk, "meta": screener_meta}

    # Run OCR Extraction & Field Parsing
    top_label = screener_meta.get("detected_document_type", "unknown") if screener_meta else "unknown"
    doc_conf = screener_meta.get("structural_confidence", 50.0) if screener_meta else 50.0
    
    try:
        from models.ocr_extractor import run_ocr, extract_structured_fields, DOCUMENT_NAME_MAPPING
        ocr_engine, ocr_lines = run_ocr(pil_img)
        extracted_fields = extract_structured_fields(top_label, ocr_lines)
    except Exception as err:
        print(f"[IM] OCR Extraction exception: {err}")
        ocr_engine = "fallback"
        ocr_lines = []
        extracted_fields = {}
        DOCUMENT_NAME_MAPPING = {}

    doc_display_name = DOCUMENT_NAME_MAPPING.get(top_label, top_label.replace("_", " ").title())

    # Module 2: Document Standard & Rule Validation
    try:
        from models.document_validator import validate_document
        validation_report = validate_document(top_label, extracted_fields)
        print(f"[M2] Validation verdict: {validation_report.get('verdict')} | "
              f"PASS={validation_report.get('pass_count')} "
              f"FAIL={validation_report.get('fail_count')} "
              f"WARN={validation_report.get('warn_count')}")
    except Exception as err:
        print(f"[M2] Validation error: {err}")
        validation_report = {"verdict": "ERROR", "checks": [], "pass_count": 0, "fail_count": 0, "warn_count": 0}

    # Map Validation Report to Risk Contribution
    verdict = validation_report.get("verdict", "INCONCLUSIVE")
    if verdict == "VALIDATED":
        val_risk = 5
    elif verdict == "SUSPICIOUS":
        val_risk = 60
    elif verdict == "INVALID":
        val_risk = 95
    elif verdict == "UNVERIFIABLE":
        val_risk = 45
    else:
        val_risk = 25

    # 1. Document Standard & Rule Validation (Weight: 40% - Official Govt Rule Compliance)
    rows.append((val_risk, 0.40, "Govt Document Rule Compliance"))
    raw["document_validation"] = {"risk": val_risk, "verdict": verdict, "report": validation_report}

    # 2. Main Document Structural Screener (Weight: 15% - Layout & Model Confidence)
    rows.append((screener_risk, 0.15, M2_REPO))

    # 3. Module 3: Tampering & Forgery Detection (Weight: 40%)
    tamper_report = {}
    tamper_risk = 30  # default neutral
    try:
        from models.tamper_detector import detect_tampering
        tamper_report = detect_tampering(fb, top_label, extracted_fields, ocr_lines)
        tamper_risk = tamper_report.get("tamper_score", 30)
        print(f"[M3] Tamper verdict={tamper_report.get('verdict')} | risk={tamper_risk}")
    except Exception as tamper_err:
        print(f"[M3] Tamper detection error: {tamper_err}")
        tamper_report = {
            "verdict": "ERROR", "tamper_score": 30,
            "photo_splice": {}, "font_alteration": {},
            "summary": [f"Module 3 error: {str(tamper_err)[:120]}"]
        }
    rows.append((tamper_risk, 0.40, "Tampering & Forgery Detection"))
    raw["tamper_detection"] = {"risk": tamper_risk, "report": tamper_report}

    # 4. Metadata Integrity (Weight: 2%)
    es, ed = _exif(pil_img)
    rows.append((es, 0.02, "EXIF"))
    raw["exif_integrity"] = ed

    # Multi-weighted ensemble summary calculation
    tw = sum(w for s, w, name in rows)
    final = min(100, max(0, round(sum(s * w for s, w, name in rows) / tw))) if tw > 0 else 50

    return {
        "riskScore":  final,
        "label":      "HIGH_RISK" if final > 60 else ("MEDIUM_RISK" if final > 30 else "GENUINE_ID"),
        "method":     "AI Document Screening: YOLO Classification + OCR Parsing + Tamper Detection",
        "resolution": f"{W}x{H}",
        "document_classification": {
            "code": top_label,
            "name": doc_display_name,
            "confidence": doc_conf
        },
        "extracted_fields":  extracted_fields,
        "validation_report": validation_report,
        "tamper_report":     tamper_report,
        "ocr_engine": ocr_engine,
        "ocr_lines": [l["text"] for l in ocr_lines[:20]],
        "breakdown":  raw
    }

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "architecture": "Rule Validation + YOLO Screener + Tamper Detection",
        "screener": M2_REPO,
        "tamper_engine": "OpenCV/NumPy (Photo Splice + Font Alteration)"
    }

@app.post("/analyze/image")
async def process_image_upload(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        return analyze_image(contents)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=51559)
