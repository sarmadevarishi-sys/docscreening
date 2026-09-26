"""
Module 3: Tampering & Forgery Detection
========================================
SatyaKavach - Smart India Hackathon 2026
Ministry of Home Affairs | Cybersecurity & Blockchain

Detects:
  1. Photo Replacement / Boundary Splicing
     - Laplacian sharpness variance between face ROI & card background
     - YCbCr chrominance mismatch (colour temperature discontinuity)
     - Sobel edge step-jump magnitude along photo-box perimeter
     - Sensor noise (local standard-deviation) variance mismatch

  2. Text / Font Alteration
     - Stroke width homogeneity (morphological erosion delta)
     - Baseline y-coordinate jitter across text segments
     - Character height standard deviation within each OCR line

All checks are pure OpenCV / NumPy - no model downloads.
"""

import io
import math
import traceback
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _pil_to_bgr(pil_img):
    return np.array(pil_img.convert("RGB"))[:, :, ::-1]


def _roi(arr, x1, y1, x2, y2):
    h, w = arr.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return arr[y1:y2, x1:x2]


def _laplacian_variance(gray):
    import cv2
    if gray is None or gray.size == 0:
        return 0.0
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(np.var(lap))


def _noise_energy(gray):
    import cv2
    if gray is None or gray.size == 0:
        return 0.0
    blurred = cv2.GaussianBlur(gray.astype(np.float32), (3, 3), 0)
    noise = np.abs(gray.astype(np.float32) - blurred)
    return float(np.mean(noise))


def _chrominance_mean(ycbcr):
    if ycbcr is None or ycbcr.size == 0:
        return (128.0, 128.0)
    return float(np.mean(ycbcr[:, :, 1])), float(np.mean(ycbcr[:, :, 2]))


def _sobel_edge_magnitude(gray):
    import cv2
    if gray is None or gray.size == 0:
        return 0.0
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sx ** 2 + sy ** 2)
    return float(np.mean(mag))


# ---------------------------------------------------------------------------
# CHECK 1 - PHOTO REPLACEMENT / BOUNDARY SPLICING
# ---------------------------------------------------------------------------

def analyze_photo_splicing(pil_img, face_bbox=None):
    import cv2

    findings = []
    details  = {}
    penalty  = 0

    try:
        bgr = _pil_to_bgr(pil_img)
        W, H = pil_img.size
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        ycbcr = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)

        if face_bbox is None:
            try:
                if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                    face_cascade = cv2.CascadeClassifier(cascade_path)
                    faces = face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
                    )
                    if len(faces) > 0:
                        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                        pad = int(fw * 0.1)
                        face_bbox = (
                            max(0, fx - pad), max(0, fy - pad),
                            min(W, fx + fw + pad), min(H, fy + fh + pad)
                        )
                    else:
                        face_bbox = (int(W * 0.03), int(H * 0.12),
                                     int(W * 0.42), int(H * 0.75))
                else:
                    face_bbox = (int(W * 0.03), int(H * 0.12),
                                 int(W * 0.42), int(H * 0.75))
            except Exception:
                face_bbox = (int(W * 0.03), int(H * 0.12),
                             int(W * 0.42), int(H * 0.75))

        fx1, fy1, fx2, fy2 = face_bbox
        details["face_bbox"] = [int(fx1), int(fy1), int(fx2), int(fy2)]

        # Extract high quality face crop in base64 for frontend biometric booth
        try:
            import base64
            face_crop_pil = pil_img.crop((fx1, fy1, fx2, fy2))
            buffered = io.BytesIO()
            face_crop_pil.save(buffered, format="JPEG", quality=90)
            details["face_crop_base64"] = base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception:
            details["face_crop_base64"] = None

        face_gray  = _roi(gray, fx1, fy1, fx2, fy2)
        face_ycbcr = _roi(ycbcr, fx1, fy1, fx2, fy2)

        bg_x1, bg_y1 = fx2 + 5, fy1
        bg_x2, bg_y2 = min(W - 5, fx2 + int(W * 0.40)), fy2
        bg_gray      = _roi(gray, bg_x1, bg_y1, bg_x2, bg_y2)
        bg_ycbcr     = _roi(ycbcr, bg_x1, bg_y1, bg_x2, bg_y2)

        if face_gray is None or bg_gray is None:
            return {
                "score": 30, "status": "INCONCLUSIVE",
                "findings": ["Insufficient image regions for photo-splice analysis"],
                "details": {}
            }

        # Metric 1: Laplacian sharpness ratio
        face_lap = _laplacian_variance(face_gray)
        bg_lap   = _laplacian_variance(bg_gray)
        details["laplacian_face"] = round(face_lap, 2)
        details["laplacian_bg"]   = round(bg_lap, 2)

        if bg_lap > 0:
            sharpness_ratio = face_lap / max(bg_lap, 1.0)
            details["sharpness_ratio"] = round(sharpness_ratio, 3)
            if sharpness_ratio > 4.5:
                penalty += 22
                findings.append(
                    "Sharpness mismatch: photo ROI is {:.1f}x sharper than card background - may indicate pasted high-resolution photo".format(sharpness_ratio)
                )
            elif sharpness_ratio > 3.0:
                penalty += 10
                findings.append(
                    "Mild sharpness variance (ratio {:.1f}) between photo and background".format(sharpness_ratio)
                )

        # Metric 2: Sensor noise energy mismatch
        face_noise = _noise_energy(face_gray)
        bg_noise   = _noise_energy(bg_gray)
        details["noise_face"] = round(face_noise, 3)
        details["noise_bg"]   = round(bg_noise, 3)

        noise_delta = abs(face_noise - bg_noise)
        details["noise_delta"] = round(noise_delta, 3)
        if noise_delta > 3.5:
            penalty += 25
            findings.append(
                "Sensor noise discontinuity (delta={:.2f}): photo and card exhibit different imaging sensor characteristics - likely different source devices".format(noise_delta)
            )
        elif noise_delta > 2.0:
            penalty += 10
            findings.append("Moderate noise mismatch (delta={:.2f}) between photo and card body".format(noise_delta))

        # Metric 3: Chrominance mismatch
        if face_ycbcr is not None and bg_ycbcr is not None:
            f_cb, f_cr = _chrominance_mean(face_ycbcr)
            b_cb, b_cr = _chrominance_mean(bg_ycbcr)
            chroma_dist = math.sqrt((f_cb - b_cb) ** 2 + (f_cr - b_cr) ** 2)
            details["chroma_distance"] = round(chroma_dist, 2)
            if chroma_dist > 18:
                penalty += 22
                findings.append(
                    "Chrominance mismatch (dist={:.1f}): significant colour temperature difference - photo may originate from a different scanner/camera".format(chroma_dist)
                )
            elif chroma_dist > 10:
                penalty += 8
                findings.append("Moderate chrominance shift (dist={:.1f}) at photo boundary".format(chroma_dist))

        # Metric 4: Sobel edge seam-jump
        seam_h = max(4, int((fy2 - fy1) * 0.06))
        top_seam_gray = _roi(gray, fx1, fy1, fx2, fy1 + seam_h)
        bot_seam_gray = _roi(gray, fx1, max(0, fy2 - seam_h), fx2, fy2)

        top_edge = _sobel_edge_magnitude(top_seam_gray)
        bot_edge = _sobel_edge_magnitude(bot_seam_gray)
        mid_face_gray = _roi(gray, fx1, fy1 + seam_h, fx2, fy2 - seam_h)
        mid_edge = _sobel_edge_magnitude(mid_face_gray)

        details["seam_top_edge"]   = round(top_edge, 2)
        details["seam_bot_edge"]   = round(bot_edge, 2)
        details["interior_edge"]   = round(mid_edge, 2)

        seam_jump = max(top_edge, bot_edge) / max(mid_edge, 1.0)
        details["seam_jump_ratio"] = round(seam_jump, 3)

        if seam_jump > 3.5:
            penalty += 18
            findings.append(
                "Hard edge seam detected at photo border (seam/interior ratio={:.1f}) - consistent with photo boundary cut-and-paste".format(seam_jump)
            )
        elif seam_jump > 2.0:
            penalty += 7
            findings.append("Mild edge artefact along photo boundary (ratio={:.1f})".format(seam_jump))

        penalty = min(100, penalty)
        if penalty >= 50:
            status = "TAMPERED"
        elif penalty >= 25:
            status = "SUSPICIOUS"
        else:
            status = "CLEAN"

        if not findings:
            findings.append("No statistically significant anomalies detected in photo region")

    except Exception as exc:
        print("[M3/PhotoSplice] Exception: {}".format(exc))
        traceback.print_exc()
        return {
            "score": 20, "status": "INCONCLUSIVE",
            "findings": ["Analysis error: {}".format(str(exc)[:120])],
            "details": {}
        }

    return {"score": penalty, "status": status, "findings": findings, "details": details}


# ---------------------------------------------------------------------------
# CHECK 2 - TEXT / FONT ALTERATION
# ---------------------------------------------------------------------------

def analyze_text_font_alteration(pil_img, ocr_lines):
    import cv2

    findings = []
    details  = {}
    penalty  = 0

    try:
        bgr  = _pil_to_bgr(pil_img)
        W, H = pil_img.size
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        stroke_widths = []
        char_heights  = []
        baselines     = []

        lines_with_bbox = [l for l in ocr_lines if isinstance(l, dict) and "bbox" in l and l.get("text", "").strip()]

        if len(lines_with_bbox) >= 3:
            for line in lines_with_bbox:
                try:
                    bbox = line["bbox"]
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                    row_h = y2 - y1
                    if row_h < 6:
                        continue

                    baselines.append(y2)
                    char_heights.append(row_h)

                    strip = _roi(gray, x1, y1, x2, y2)
                    if strip is None:
                        continue
                    _, bw = cv2.threshold(strip, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    kernel = np.ones((2, 2), np.uint8)
                    eroded = cv2.erode(bw, kernel, iterations=1)
                    fg_orig   = np.sum(bw    == 0)
                    fg_eroded = np.sum(eroded == 0)
                    if fg_orig > 0:
                        sw = (fg_orig - fg_eroded) / fg_orig * row_h
                    else:
                        sw = 0.0
                    stroke_widths.append(sw)
                except Exception:
                    continue

            details["lines_analysed"] = len(stroke_widths)

            # Stroke width homogeneity
            if len(stroke_widths) >= 3:
                sw_arr = np.array(stroke_widths)
                sw_med = float(np.median(sw_arr))
                sw_std = float(np.std(sw_arr))
                sw_cv  = sw_std / max(sw_med, 0.01)

                details["stroke_width_median"] = round(sw_med, 3)
                details["stroke_width_std"]    = round(sw_std, 3)
                details["stroke_cv"]           = round(sw_cv, 3)

                if sw_cv > 0.55:
                    penalty += 30
                    findings.append(
                        "High font stroke inconsistency (CV={:.2f}): multiple typefaces detected - fields likely set in different fonts (forgery indicator)".format(sw_cv)
                    )
                elif sw_cv > 0.30:
                    penalty += 14
                    findings.append("Moderate stroke width variation (CV={:.2f}) across text fields".format(sw_cv))

            # Baseline jitter
            if len(baselines) >= 4 and len(char_heights) >= 4:
                norm_bl = [b / max(h, 1) for b, h in zip(baselines, char_heights)]
                bl_std  = float(np.std(norm_bl))
                details["baseline_jitter_std"] = round(bl_std, 4)

                if bl_std > 0.25:
                    penalty += 20
                    findings.append(
                        "Text baseline misalignment (sigma={:.3f}): lines are not uniformly positioned - may indicate digitally inserted text".format(bl_std)
                    )
                elif bl_std > 0.12:
                    penalty += 8
                    findings.append("Mild baseline jitter (sigma={:.3f}) across text lines".format(bl_std))

            # Character height deviation
            if len(char_heights) >= 3:
                h_arr = np.array(char_heights, dtype=float)
                h_med = float(np.median(h_arr))
                h_cv  = float(np.std(h_arr)) / max(h_med, 1.0)
                details["char_height_cv"] = round(h_cv, 3)

                if h_cv > 0.45:
                    penalty += 18
                    findings.append(
                        "Character height inconsistency (CV={:.2f}): large size variation across fields - possible text substitution".format(h_cv)
                    )
                elif h_cv > 0.25:
                    penalty += 7
                    findings.append("Some character height variation (CV={:.2f}) detected".format(h_cv))

        else:
            details["mode"] = "global_texture_fallback"
            text_zone = _roi(gray, int(W * 0.40), int(H * 0.10), W - 5, H - 5)
            if text_zone is not None and text_zone.size > 0:
                _, bw_zone = cv2.threshold(text_zone, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                row_vars = [float(np.var(bw_zone[r:r+4, :])) for r in range(0, bw_zone.shape[0]-4, 4)]
                if row_vars:
                    rv_cv = float(np.std(row_vars)) / max(float(np.mean(row_vars)), 1.0)
                    details["row_texture_cv"] = round(rv_cv, 3)
                    if rv_cv > 1.5:
                        penalty += 15
                        findings.append(
                            "Text region texture inconsistency (CV={:.2f}) - possible font irregularity (fallback mode)".format(rv_cv)
                        )
            if not findings:
                findings.append("Insufficient OCR bounding-box data for full font analysis (fallback mode)")

        penalty = min(100, penalty)
        if penalty >= 45:
            status = "TAMPERED"
        elif penalty >= 20:
            status = "SUSPICIOUS"
        else:
            status = "CLEAN"

        if not findings:
            findings.append("Font and text metrics within expected variance for authentic document")

    except Exception as exc:
        print("[M3/FontAlt] Exception: {}".format(exc))
        traceback.print_exc()
        return {
            "score": 15, "status": "INCONCLUSIVE",
            "findings": ["Analysis error: {}".format(str(exc)[:120])],
            "details": {}
        }

    return {"score": penalty, "status": status, "findings": findings, "details": details}


# ---------------------------------------------------------------------------
# MASTER ENTRY POINT
# ---------------------------------------------------------------------------

def detect_tampering(image_bytes, doc_type, extracted_fields, ocr_lines):
    """
    Orchestrates both tampering checks and returns a unified report.

    Returns:
    {
        "verdict":         "INTEGRITY_VERIFIED" | "SUSPICIOUS" | "FORGERY_DETECTED",
        "tamper_score":    0-100,
        "photo_splice":    { score, status, findings, details },
        "font_alteration": { score, status, findings, details },
        "summary":         [ "finding1", "finding2", ... ]
    }
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return {
            "verdict": "ERROR",
            "tamper_score": 30,
            "photo_splice":     {"score": 30, "status": "INCONCLUSIVE", "findings": [], "details": {}},
            "font_alteration":  {"score": 30, "status": "INCONCLUSIVE", "findings": [], "details": {}},
            "summary": ["Could not open image for tampering analysis: {}".format(exc)]
        }

    print("[M3] Running photo splice analysis...")
    splice_result = analyze_photo_splicing(pil_img)

    print("[M3] Running font/text alteration analysis...")
    font_result   = analyze_text_font_alteration(pil_img, ocr_lines)

    combined_score = int(round(
        splice_result["score"] * 0.60 +
        font_result["score"]   * 0.40
    ))
    combined_score = max(0, min(100, combined_score))

    if combined_score >= 50:
        verdict = "FORGERY_DETECTED"
    elif combined_score >= 25:
        verdict = "SUSPICIOUS"
    else:
        verdict = "INTEGRITY_VERIFIED"

    summary = []
    for f in splice_result.get("findings", []):
        summary.append("[Photo] {}".format(f))
    for f in font_result.get("findings", []):
        summary.append("[Font] {}".format(f))

    print(
        "[M3] Tampering verdict: {} | Score={} | PhotoSplice={} | FontAlt={}".format(
            verdict, combined_score, splice_result["score"], font_result["score"]
        )
    )

    return {
        "verdict":         verdict,
        "tamper_score":    combined_score,
        "photo_splice":    splice_result,
        "font_alteration": font_result,
        "summary":         summary
    }
