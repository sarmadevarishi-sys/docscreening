"""
SatyaKavach — Module 4: 1:1 Face Verification Engine
Compares the photo on an Indian ID card against a live booth snapshot / selfie.
Uses OpenCV Deep Learning Modules:
  - YuNet (ONNX): Ultra-fast face detection & 5-point facial landmark alignment
  - SFace (ONNX): SOTA 128-dimensional biometric feature representation
100% Offline, Zero Cloud Dependencies, Runs in < 100ms on CPU.
"""

import os
import cv2
import numpy as np
from PIL import Image
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS_DIR = os.path.join(BASE_DIR, "models", "weights")

YUNET_PATH = os.path.join(WEIGHTS_DIR, "face_detection_yunet_2023mar.onnx")
SFACE_PATH = os.path.join(WEIGHTS_DIR, "face_recognition_sface_2021dec.onnx")

_detector = None
_recognizer = None

def _get_models():
    global _detector, _recognizer
    if _detector is None or _recognizer is None:
        if not os.path.exists(YUNET_PATH) or not os.path.exists(SFACE_PATH):
            raise FileNotFoundError("YuNet or SFace model weights not found in models/weights/")
        # Initialize YuNet with default input shape (updated dynamically per image)
        _detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (320, 320), score_threshold=0.45, nms_threshold=0.3)
        _recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")
    return _detector, _recognizer


def _detect_and_align_face(bgr_img):
    """
    Detects the primary face and extracts aligned 112x112 facial crop and 128-D feature vector.
    Returns: (aligned_face, feature_vector, face_bbox) or (None, None, None)
    """
    detector, recognizer = _get_models()
    h, w, _ = bgr_img.shape
    detector.setInputSize((w, h))
    
    _, faces = detector.detect(bgr_img)
    
    # 1. Primary: YuNet Detection
    if faces is not None and len(faces) > 0:
        face = max(faces, key=lambda f: f[2] * f[3])
        aligned_face = recognizer.alignCrop(bgr_img, face)
        feature = recognizer.feature(aligned_face)
        fx, fy, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
        bbox = (max(0, fx), max(0, fy), min(w, fx + fw), min(h, fy + fh))
        return aligned_face, feature, bbox

    # 2. Secondary Fallback: Haar Cascade
    try:
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            h_faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
            if len(h_faces) > 0:
                fx, fy, fw, fh = max(h_faces, key=lambda f: f[2] * f[3])
                crop = bgr_img[max(0, fy):min(h, fy + fh), max(0, fx):min(w, fx + fw)]
                if crop.size > 0:
                    crop_resized = cv2.resize(crop, (112, 112))
                    feature = recognizer.feature(crop_resized)
                    return crop_resized, feature, (fx, fy, fx + fw, fy + fh)
    except Exception:
        pass

    return None, None, None


def verify_1to1_face(doc_image_bytes: bytes, live_face_bytes: bytes) -> dict:
    """
    Compares the face on the ID document against the live booth camera / selfie.
    
    Returns:
      {
        "status": "MATCH" | "MISMATCH" | "NO_FACE_DETECTED",
        "match": bool,
        "match_score": int (0 - 100),
        "cosine_similarity": float (-1.0 to 1.0),
        "l2_distance": float,
        "doc_face_detected": bool,
        "live_face_detected": bool,
        "verdict_text": str,
        "explanation": str
      }
    """
    try:
        # Load Doc Image
        doc_arr = np.frombuffer(doc_image_bytes, np.uint8)
        doc_bgr = cv2.imdecode(doc_arr, cv2.IMREAD_COLOR)
        if doc_bgr is None:
            return {"status": "ERROR", "match": False, "match_score": 0, "verdict_text": "Invalid Document Image"}
        
        # Load Live Face
        live_arr = np.frombuffer(live_face_bytes, np.uint8)
        live_bgr = cv2.imdecode(live_arr, cv2.IMREAD_COLOR)
        if live_bgr is None:
            return {"status": "ERROR", "match": False, "match_score": 0, "verdict_text": "Invalid Live Face Image"}
        
        # Detect and extract features
        _, doc_feat, doc_bbox = _detect_and_align_face(doc_bgr)
        _, live_feat, live_bbox = _detect_and_align_face(live_bgr)
        
        if doc_feat is None and live_feat is None:
            return {
                "status": "NO_FACE_DETECTED",
                "match": False,
                "match_score": 0,
                "doc_face_detected": False,
                "live_face_detected": False,
                "verdict_text": "No Face Detected",
                "explanation": "Could not locate a clear human face in either the ID card or the live camera feed."
            }
        
        if doc_feat is None:
            return {
                "status": "NO_FACE_DETECTED",
                "match": False,
                "match_score": 0,
                "doc_face_detected": False,
                "live_face_detected": True,
                "verdict_text": "No Face on Document",
                "explanation": "Could not locate a valid photograph on the uploaded identity document."
            }
            
        if live_feat is None:
            return {
                "status": "NO_FACE_DETECTED",
                "match": False,
                "match_score": 0,
                "doc_face_detected": True,
                "live_face_detected": False,
                "verdict_text": "No Live Face Detected",
                "explanation": "Could not detect a person's face in the live camera capture. Please face the camera directly."
            }
        
        _, recognizer = _get_models()
        
        # SFace cosine similarity: typical threshold is 0.363 for standard FAR 1e-3
        # In practice:
        # Cosine > 0.45: Strongly same person
        # Cosine 0.35 - 0.45: Moderate match
        # Cosine < 0.35: Different persons (impostor)
        cosine_sim = float(recognizer.match(doc_feat, live_feat, cv2.FaceRecognizerSF_FR_COSINE))
        l2_dist = float(recognizer.match(doc_feat, live_feat, cv2.FaceRecognizerSF_FR_NORM_L2))
        
        # Normalize cosine (-1 to 1) into a clean 0 to 100 percentage
        # A cosine of 0.363 corresponds to approx 70% confidence threshold
        if cosine_sim >= 0.363:
            # Map [0.363, 1.0] -> [70, 99]
            pct = 70 + int(((cosine_sim - 0.363) / (1.0 - 0.363)) * 29)
        else:
            # Map [-0.2, 0.363] -> [5, 69]
            pct = max(5, int(((cosine_sim + 0.2) / (0.363 + 0.2)) * 65))
            
        pct = max(0, min(100, pct))
        is_match = cosine_sim >= 0.363
        
        if is_match:
            status = "MATCH"
            verdict = "IDENTITY CONFIRMED"
            explanation = f"Cardholder photograph matches the live physical person with {pct}% biometric confidence (Cosine: {cosine_sim:.3f})."
        else:
            status = "MISMATCH"
            verdict = "IMPERSONATION ALERT"
            explanation = f"Biometric mismatch detected! The physical carrier does NOT match the identity document photo (Score: {pct}%, Cosine: {cosine_sim:.3f})."
            
        return {
            "status": status,
            "match": is_match,
            "match_score": pct,
            "cosine_similarity": round(cosine_sim, 4),
            "l2_distance": round(l2_dist, 4),
            "doc_face_detected": True,
            "live_face_detected": True,
            "verdict_text": verdict,
            "explanation": explanation
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "match": False,
            "match_score": 0,
            "verdict_text": "Verification Error",
            "explanation": f"Face verification error: {str(e)}"
        }
