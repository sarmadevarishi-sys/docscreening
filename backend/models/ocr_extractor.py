"""
Indian Identity Document OCR Extractor — Module 1 Engine
Supports: PAN Card, Aadhaar Card, Indian Passport, Driving License, Voter ID

Key improvements over v1:
  - Sorts OCR lines by vertical (y) position for correct top-to-bottom reading
  - Filters non-ASCII / Devanagari (Hindi) text that corrupts name extraction
  - Uses label→next-line context detection instead of blind index picking
  - Passport: adds Date of Issue, Place of Issue, flexible date formats
"""

import re
import os
import io
import numpy as np
from PIL import Image

_PADDLE_OCR = None
_EASY_OCR = None

DOCUMENT_NAME_MAPPING = {
    "aadhar_front":          "Aadhaar Card (Front)",
    "aadhar_back":           "Aadhaar Card (Back / Address)",
    "pan_card_front":        "PAN Card (Permanent Account Number)",
    "passport":              "Indian Passport (Republic of India)",
    "driving_license_front": "Indian Driving License (Front)",
    "driving_license_back":  "Indian Driving License (Back)",
    "voter_id":              "Voter ID Card (Election Commission of India)",
    "none_of_the_above":     "Unrecognized / Other Document"
}

# ─── OCR ENGINE MANAGEMENT ───────────────────────────────────────────────────

def get_ocr_engine():
    global _PADDLE_OCR, _EASY_OCR
    if _PADDLE_OCR is not None:
        return "paddle", _PADDLE_OCR
    if _EASY_OCR is not None:
        return "easyocr", _EASY_OCR

    try:
        from paddleocr import PaddleOCR
        print("[OCR] Initializing PaddleOCR engine...")
        _PADDLE_OCR = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        print("[OCR] PaddleOCR engine ready.")
        return "paddle", _PADDLE_OCR
    except Exception as e:
        print(f"[OCR] PaddleOCR not available ({e}), falling back to EasyOCR...")

    try:
        import easyocr
        print("[OCR] Initializing EasyOCR engine...")
        _EASY_OCR = easyocr.Reader(['en'], gpu=False)
        print("[OCR] EasyOCR engine ready.")
        return "easyocr", _EASY_OCR
    except Exception as e:
        print(f"[OCR] EasyOCR initialization failed: {e}")

    return None, None

def run_ocr(pil_img: Image.Image):
    engine_name, engine = get_ocr_engine()
    np_img = np.array(pil_img)
    lines = []

    if engine_name == "paddle" and engine:
        try:
            res = engine.ocr(np_img, cls=True)
            if res and res[0] is not None:
                for line in res[0]:
                    bbox, (text, conf) = line[0], line[1]
                    lines.append({"text": text.strip(), "confidence": round(float(conf) * 100, 1), "bbox": bbox})
        except Exception as e:
            print(f"[OCR] Paddle execution error: {e}")

    elif engine_name == "easyocr" and engine:
        try:
            # Optimize image resolution for fast CPU inference (960px max dimension)
            h, w = np_img.shape[:2]
            max_dim = 960
            if max(h, w) > max_dim:
                scale = max_dim / float(max(h, w))
                new_w, new_h = int(w * scale), int(h * scale)
                import cv2
                ocr_input = cv2.resize(np_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                inv_scale = 1.0 / scale
            else:
                ocr_input = np_img
                inv_scale = 1.0

            res = engine.readtext(ocr_input, batch_size=4)
            for bbox, text, conf in res:
                # Scale bounding box back to original coordinates
                if inv_scale != 1.0:
                    scaled_bbox = [[pt[0] * inv_scale, pt[1] * inv_scale] for pt in bbox]
                else:
                    scaled_bbox = bbox
                lines.append({"text": text.strip(), "confidence": round(float(conf) * 100, 1), "bbox": scaled_bbox})
        except Exception as e:
            print(f"[OCR] EasyOCR execution error: {e}")

    return engine_name or "basic_heuristic", lines

# ─── UTILITY FUNCTIONS ────────────────────────────────────────────────────────

def _top_y(line: dict) -> float:
    """Returns the top y-coordinate of an OCR line's bounding box."""
    bbox = line.get("bbox", [])
    try:
        if bbox and isinstance(bbox[0], (list, tuple)):
            return float(bbox[0][1])
    except Exception:
        pass
    return 0.0

def _sort_by_y(lines: list) -> list:
    """Sort OCR lines top-to-bottom by bounding box y-position."""
    return sorted(lines, key=_top_y)

def _is_ascii_dominant(text: str, threshold: float = 0.75) -> bool:
    """
    Returns True if >= threshold fraction of characters are ASCII.
    Filters out Devanagari / Hindi text that would corrupt English name extraction.
    """
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) >= threshold

def _is_name_like(text: str) -> bool:
    """Returns True if the text represents a plausible human name."""
    t = text.strip()
    if not t or len(t) < 3:
        return False
    # Only letters, spaces, dots, hyphens
    if not re.match(r'^[A-Za-z\s\.\'\-]+$', t):
        return False
    # Exclude system/card keywords and common acronyms
    if re.search(r'\b(PAN|CARD|GOVT|INDIA|INCOME|TAX|DEPT|DEPARTMENT|SIGNATURE|PHOTO|MALE|FEMALE|PERMANENT|ACCOUNT|NUMBER|DATE|BIRTH|FATHER)\b', t, re.I):
        return False
    # Must contain at least one vowel
    if not re.search(r'[AEIOUYaeiouy]', t):
        return False
    # Known noise tokens produced by OCR reading Hindi glyphs or card borders
    noise = {'TTQ', 'WRAR', 'NAME', 'CARD', 'SIGN', 'SEAL', 'LOGO', 'GOVT', 'DEPT', 'WRA'}
    if t.upper() in noise:
        return False
    words = t.split()
    if len(words) == 1:
        return len(t) >= 4 and t.upper() not in noise
    # Multi-word names: each word should have at least 2 characters (e.g. "Binit Kalita")
    return all(len(w) >= 2 for w in words)

def _ascii_lines(lines: list) -> list:
    """Return only the ASCII-dominant OCR lines (filters Hindi/Devanagari)."""
    return [l for l in lines if _is_ascii_dominant(l["text"])]

# Standard labels that should NOT be picked as name/value fields
_SKIP_RE = re.compile(
    r'INCOME|TAX|DEPARTMENT|GOVT|GOVERNMENT|REPUBLIC|OF INDIA|PERMANENT|ACCOUNT|'
    r'AADHAAR|UNIQUE|IDENTIFICATION|AUTHORITY|'
    r'PASSPORT|NATIONALITY|REPUBLIC|'
    r'ELECTION|COMMISSION|ELECTOR|PHOTO|'
    r'DRIVING|LICENCE|LICENSE|TRANSPORT|MINISTRY|'
    r'SIGNATURE|MINISTRY|BRANCH|ISSUED',
    re.I
)

def _next_value_after_label(sorted_lines: list, label_re: str,
                             exclude_re: str = None, max_lookahead: int = 5,
                             allow_inline: bool = True,
                             require_name: bool = False) -> str:
    """
    Finds the value that appears immediately after or below a label line.

    Strategy:
      1. Find a line matching label_re (optionally excluding exclude_re).
      2. If allow_inline is True, check if a value is inline (e.g. "DOB: 15/08/1990" → "15/08/1990").
      3. Otherwise look at the next 1–max_lookahead lines for the value.
    """
    for i, line in enumerate(sorted_lines):
        t = line["text"].strip()
        if not t:
            continue
        if not re.search(label_re, t, re.I):
            continue
        if exclude_re and re.search(exclude_re, t, re.I):
            continue

        # Try inline value only if allowed
        if allow_inline:
            inline = re.sub(label_re, '', t, flags=re.I, count=1).strip().strip(" :/-|\\")
            if inline and len(inline) >= 2 and _is_ascii_dominant(inline):
                if not require_name or _is_name_like(inline):
                    return inline

        # Look at the next lines
        for j in range(i + 1, min(i + max_lookahead + 1, len(sorted_lines))):
            nxt = sorted_lines[j]["text"].strip()
            if not nxt or len(nxt) < 2:
                continue
            if not _is_ascii_dominant(nxt):
                continue
            # Stop if we hit another primary label
            if re.search(label_re, nxt, re.I):
                break
            if _SKIP_RE.search(nxt):
                continue
            if not require_name or _is_name_like(nxt):
                return nxt

    return None

def _parse_date(raw: str) -> str:
    """
    Normalises raw OCR date strings into DD/MM/YYYY.
    Handles: "01/01/1990", "01-01-1990", "01 Jan 1990", "01JAN1990", "1.1.90"
    """
    if not raw:
        return raw
    raw = raw.strip()
    # Already good format
    if re.fullmatch(r'\d{2}/\d{2}/\d{4}', raw):
        return raw
    # DD-MM-YYYY
    m = re.fullmatch(r'(\d{2})-(\d{2})-(\d{4})', raw)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    # DD Mon YYYY  (e.g. 01 Jan 1990)
    m = re.fullmatch(r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', raw)
    if m:
        return raw  # keep readable
    # DDMONYYYY (e.g. 01JAN1990)
    m = re.fullmatch(r'(\d{2})([A-Za-z]{3})(\d{4})', raw)
    if m:
        return f"{m.group(1)} {m.group(2).capitalize()} {m.group(3)}"
    return raw

# ─── DOCUMENT-SPECIFIC PARSERS ────────────────────────────────────────────────

def parse_pan_card(lines: list) -> dict:
    sorted_l  = _sort_by_y(lines)
    ascii_l   = _ascii_lines(sorted_l)
    raw_texts = [l["text"] for l in ascii_l]
    full_str  = "\n".join(raw_texts)
    fields    = {}

    # PAN Number: 5 uppercase letters + 4 digits + 1 uppercase letter
    pan_match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', full_str)
    if pan_match:
        pan_num = pan_match.group(1)
        fields["id_number"] = pan_num
        fields["document_id_label"] = "PAN Number"
        cat_map = {
            'P': 'Individual', 'C': 'Company', 'H': 'HUF',
            'F': 'Firm', 'A': 'AOP', 'T': 'Trust',
            'B': 'BOI', 'L': 'Local Authority', 'G': 'Government'
        }
        fields["holder_category"] = cat_map.get(pan_num[3], "Individual")

    # Date of Birth
    dob_m = re.search(r'\b([0-3]?\d[/\-][0-1]?\d[/\-][12][90]\d{2})\b', full_str)
    if dob_m:
        fields["dob"] = _parse_date(dob_m.group(1))

    # ── Holder Name: strictly the line below the "Name" label (allow_inline=False) ──
    holder_name = _next_value_after_label(
        ascii_l,
        label_re=r'\bName\b',
        exclude_re=r"Father|Father's|Date",
        allow_inline=False,
        require_name=True
    )
    if holder_name:
        cleaned = re.sub(r'^(Name\s*[:/]?\s*)', '', holder_name, flags=re.I).strip()
        if _is_name_like(cleaned):
            fields["holder_name"] = cleaned.upper()

    # ── Father's Name: strictly the line below "Father" label (allow_inline=False) ──
    father_name = _next_value_after_label(
        ascii_l,
        label_re=r"Father",
        exclude_re=r"Name\s+of\s+Father",
        allow_inline=False,
        require_name=True
    )
    if father_name:
        cleaned = re.sub(r"^(Father'?s?\s*Name\s*[:/]?\s*)", '', father_name, flags=re.I).strip()
        if _is_name_like(cleaned) and cleaned.upper() != fields.get("holder_name"):
            fields["father_name"] = cleaned.upper()

    # ── Positional fallback if label-based approach found nothing ──
    if "holder_name" not in fields or "father_name" not in fields:
        _header_re = re.compile(
            r'INCOME|TAX|DEPARTMENT|GOVT|INDIA|PERMANENT|ACCOUNT|CARD|'
            r'SIGNATURE|NAME|FATHER|DATE|BIRTH|PAN|NUMBER|PERMANENT', re.I
        )
        candidate_lines = [
            t for t in raw_texts
            if not _header_re.search(t)
            and not re.search(r'\d', t)
            and _is_name_like(t)
        ]
        if "holder_name" not in fields and candidate_lines:
            fields["holder_name"] = candidate_lines[0].upper()
        if "father_name" not in fields and len(candidate_lines) >= 2:
            second_cand = candidate_lines[1].upper()
            if second_cand != fields.get("holder_name"):
                fields["father_name"] = second_cand

    return fields


def parse_aadhaar(lines: list, is_back: bool = False) -> dict:
    sorted_l  = _sort_by_y(lines)
    all_texts = [l["text"] for l in sorted_l]
    full_str  = "\n".join(all_texts)
    ascii_l   = _ascii_lines(sorted_l)
    fields    = {}

    # ── Aadhaar UID (12 digits) ──
    # Supports variable spaces, tabs, hyphens between 4-digit blocks (e.g. "2341   5678   9012")
    uid_m = re.search(r'\b([2-9]\d{3}[\s\-]+\d{4}[\s\-]+\d{4})\b', full_str)
    if uid_m:
        uid = re.sub(r'[\s\-]', '', uid_m.group(1))
        fields["id_number"] = f"{uid[:4]} {uid[4:8]} {uid[8:]}"
        fields["document_id_label"] = "Aadhaar UID"
    else:
        # Fallback: extract continuous 12-digit block from digit stream
        clean_digits = re.sub(r'[^\d]', '', full_str)
        uid_m2 = re.search(r'([2-9]\d{11})', clean_digits)
        if uid_m2:
            uid = uid_m2.group(1)
            fields["id_number"] = f"{uid[:4]} {uid[4:8]} {uid[8:]}"
            fields["document_id_label"] = "Aadhaar UID"

    # ── Date of Birth ──
    dob_m = re.search(
        r'(?:DOB|Date of Birth|D\.O\.B)[:\s]*([0-3]?\d[/\-][0-1]?\d[/\-][12][90]\d{2})',
        full_str, re.I
    )
    if not dob_m:
        dob_m = re.search(
            r'(?:Year of Birth|YOB)[:\s]*([12][90]\d{2})', full_str, re.I
        )
    if not dob_m:
        dob_m = re.search(r'\b([0-3]?\d[/\-][0-1]?\d[/\-][12][90]\d{2})\b', full_str)
    if dob_m:
        fields["dob"] = _parse_date(dob_m.group(1))

    # ── Gender ──
    if re.search(r'\bFEMALE\b|\bWOMAN\b', full_str, re.I):
        fields["gender"] = "FEMALE"
    elif re.search(r'\bMALE\b|\bMAN\b', full_str, re.I):
        fields["gender"] = "MALE"
    elif re.search(r'\bTRANSGENDER\b', full_str, re.I):
        fields["gender"] = "TRANSGENDER"

    # ── PIN Code ──
    pin_m = re.search(r'\b([1-9]\d{5})\b', full_str)
    if pin_m:
        fields["pincode"] = pin_m.group(1)

    # ── Holder Name ──
    # On Aadhaar, the English name is printed directly ABOVE the DOB line.
    _aadhaar_skip = re.compile(
        r'GOVERNMENT|INDIA|UNIQUE|IDENTIFICATION|AUTHORITY|AADHAAR|'
        r'DOB|DATE OF BIRTH|YEAR OF BIRTH|YOB|FEMALE|MALE|TRANSGENDER|'
        r'HELP|ENROLMENT|VID|ADDRESS|S/O|D/O|W/O|C/O|\b(SO|DO|WO|CO)\b|'
        r'QR|SCAN|UID|MERA|MERI|PEHCHAN|MY AADHAAR|TOLL|FREE|PORTAL|'
        r'आधार|भारत|सरकार|प्राधिकरण', re.I
    )

    # Strategy 1 (DOB Anchor): Search backwards from the line containing DOB
    dob_idx = None
    for idx, l in enumerate(ascii_l):
        if re.search(r'DOB|Date of Birth|Year of Birth|\b\d{2}[/\-]\d{2}[/\-]\d{4}\b', l["text"], re.I):
            dob_idx = idx
            break

    if dob_idx is not None:
        for j in range(dob_idx - 1, -1, -1):
            cand = ascii_l[j]["text"].strip()
            if _aadhaar_skip.search(cand):
                continue
            if re.search(r'\d', cand):
                continue
            if _is_name_like(cand):
                fields["holder_name"] = cand.upper()
                break

    # Strategy 2 (Sequential Fallback): First non-header, non-digit valid name
    if "holder_name" not in fields:
        for line in ascii_l:
            t = line["text"].strip()
            if len(t) < 3 or re.search(r'\d', t):
                continue
            if _aadhaar_skip.search(t):
                continue
            if _is_name_like(t):
                fields["holder_name"] = t.upper()
                break

    return fields


def parse_passport(lines: list) -> dict:
    sorted_l  = _sort_by_y(lines)
    ascii_l   = _ascii_lines(sorted_l)
    raw_texts = [l["text"] for l in ascii_l]
    full_str  = "\n".join(raw_texts)
    fields    = {"nationality": "INDIAN (IND)"}

    # ── MRZ Parsing (ICAO 9303) ──
    mrz_lines = [
        l["text"].replace(" ", "")
        for l in lines
        if ("<" in l["text"] or "«" in l["text"]) and len(l["text"].replace(" ", "")) >= 24
    ]
    if mrz_lines:
        fields["mrz_detected"] = True
        fields["mrz_raw"] = mrz_lines[:2]
        # Line 1: Surname and Given Names
        for ml in mrz_lines:
            if ml.startswith("P<IND") or ml.startswith("P<") or ml.startswith("P«"):
                body = ml[5:] if (ml.startswith("P<IND") or ml.startswith("P«IND")) else ml[2:]
                parts = re.split(r'[<«]{2,}', body)
                if len(parts) >= 1 and parts[0].strip():
                    fields["surname"] = re.sub(r'[<«]', ' ', parts[0]).strip().upper()
                if len(parts) >= 2 and parts[1].strip():
                    fields["given_names"] = re.sub(r'[<«]', ' ', parts[1]).strip().upper()

        # Line 2: Passport No, Nationality, DOB, Sex, Expiry
        if len(mrz_lines) >= 2:
            l2 = mrz_lines[1]
            if len(l2) >= 9:
                pnum_cand = re.sub(r'[<«]', '', l2[0:9]).strip().upper()
                if re.fullmatch(r'[A-Z][0-9]{7}', pnum_cand):
                    fields["id_number"] = pnum_cand
                    fields["document_id_label"] = "Passport Number"
            # MRZ DOB: positions 13:19 (YYMMDD)
            if "dob" not in fields and len(l2) >= 19:
                yymmdd = l2[13:19]
                if yymmdd.isdigit():
                    yy = int(yymmdd[0:2])
                    century = "19" if yy > 30 else "20"
                    fields["dob"] = f"{yymmdd[4:6]}/{yymmdd[2:4]}/{century}{yymmdd[0:2]}"
            # MRZ Sex: position 20
            if "gender" not in fields and len(l2) >= 21:
                sex_char = l2[20].upper()
                if sex_char == 'M':
                    fields["gender"] = "MALE (M)"
                elif sex_char == 'F':
                    fields["gender"] = "FEMALE (F)"
            # MRZ Expiry: positions 21:27 (YYMMDD)
            if "expiry_date" not in fields and len(l2) >= 27:
                yymmdd_exp = l2[21:27]
                if yymmdd_exp.isdigit():
                    fields["expiry_date"] = f"{yymmdd_exp[4:6]}/{yymmdd_exp[2:4]}/20{yymmdd_exp[0:2]}"

    # ── Visual Zone: Passport Number fallback (handles spaces e.g. "G 7 3 2 1 7 3 2") ──
    if "id_number" not in fields:
        pass_m = re.search(r'\b([A-Z]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9])\b', full_str)
        if pass_m:
            fields["id_number"] = pass_m.group(1).replace(" ", "")
            fields["document_id_label"] = "Passport Number"

    # ── Label-based extraction for visual zone ──

    # Surname / Holder's Name
    if "surname" not in fields:
        sname = _next_value_after_label(ascii_l, r'Surname|Holder', exclude_re=r'Given|Name\(s\)')
        if sname and _is_name_like(sname):
            fields["surname"] = sname.upper()

    # Clean surname: strip any leading country code prefix like "IND " or "IND"
    if "surname" in fields and fields["surname"]:
        s = fields["surname"].strip()
        s = re.sub(r'^(?:IND\b\s*|IND_?|IND<+)', '', s, flags=re.I).strip()
        fields["surname"] = s

    # Given Names
    if "given_names" not in fields:
        gname = _next_value_after_label(ascii_l, r'Given\s+Name|Name\(s\)|First\s+Name', require_name=True)
        if gname and _is_name_like(gname):
            fields["given_names"] = gname.upper()

    # Date of Birth
    if "dob" not in fields:
        dob_raw = _next_value_after_label(ascii_l, r'Date\s+of\s+Birth|Birth\s+Date|DOB\b')
        if dob_raw:
            dob_date = re.search(
                r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{2}[A-Za-z]{3}\d{4})',
                dob_raw
            )
            fields["dob"] = _parse_date(dob_date.group(1)) if dob_date else dob_raw

    # Date of Issue
    if "date_of_issue" not in fields:
        doi_raw = _next_value_after_label(ascii_l, r'Date\s+of\s+Issue|Issue\s+Date')
        if doi_raw:
            doi_date = re.search(
                r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{2}[A-Za-z]{3}\d{4})',
                doi_raw
            )
            fields["date_of_issue"] = _parse_date(doi_date.group(1)) if doi_date else doi_raw

    # Date of Expiry
    if "expiry_date" not in fields:
        doe_raw = _next_value_after_label(ascii_l, r'Date\s+of\s+Expiry|Expiry\s+Date|Date\s+of\s+Expiration')
        if doe_raw:
            doe_date = re.search(
                r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{2}[A-Za-z]{3}\d{4})',
                doe_raw
            )
            fields["expiry_date"] = _parse_date(doe_date.group(1)) if doe_date else doe_raw

    # Place of Birth
    if "place_of_birth" not in fields:
        pob = _next_value_after_label(ascii_l, r'Place\s+of\s+Birth|Birth\s+Place')
        if pob and _is_ascii_dominant(pob):
            fields["place_of_birth"] = pob.upper()

    # Place of Issue
    if "place_of_issue" not in fields:
        poi = _next_value_after_label(ascii_l, r'Place\s+of\s+Issue|Issue\s+Place|Issuing\s+Authority')
        if poi and _is_ascii_dominant(poi):
            fields["place_of_issue"] = poi.upper()

    # Sex / Gender
    if "gender" not in fields:
        if re.search(r'\bFEMALE\b|\bF\b', full_str):
            fields["gender"] = "FEMALE (F)"
        elif re.search(r'\bMALE\b|\bM\b', full_str):
            fields["gender"] = "MALE (M)"

    # ── Multi-date Chronological Resolution (DOB < Issue < Expiry) ──
    raw_dates = re.findall(
        r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\b',
        full_str
    )
    all_dates = []
    for d in raw_dates:
        pd = _parse_date(d)
        if pd and pd not in all_dates:
            all_dates.append(pd)

    # If Date of Issue and Expiry were assigned the same value, or Issue is missing:
    doi = fields.get("date_of_issue")
    doe = fields.get("expiry_date")
    dob = fields.get("dob")

    if (doi and doe and doi == doe) or (doe and not doi):
        alt_dates = [d for d in all_dates if d != doe and d != dob]
        if alt_dates:
            fields["date_of_issue"] = alt_dates[0]
        else:
            # 10-Year Indian Passport standard: Expiry - 10 years + 1 day
            try:
                from datetime import datetime
                d_exp = datetime.strptime(doe, "%d/%m/%Y")
                y = d_exp.year - 10
                m = d_exp.month
                day = d_exp.day + 1
                if day > 28 and m == 2: day, m = 1, 3
                elif day > 31: day, m = 1, m + 1
                fields["date_of_issue"] = f"{day:02d}/{m:02d}/{y}"
            except Exception:
                pass

    if all_dates and "dob" not in fields:
        fields["dob"] = all_dates[0]
    if len(all_dates) >= 2 and "date_of_issue" not in fields:
        fields["date_of_issue"] = all_dates[1]
    if len(all_dates) >= 3 and "expiry_date" not in fields:
        fields["expiry_date"] = all_dates[-1]

    return fields


def parse_driving_license(lines: list) -> dict:
    sorted_l  = _sort_by_y(lines)
    ascii_l   = _ascii_lines(sorted_l)
    raw_texts = [l["text"] for l in ascii_l]
    full_str  = "\n".join(raw_texts)
    fields    = {}

    # DL Number
    dl_m = re.search(r'\b([A-Z]{2}[-\s]?\d{2}[-\s]?\d{4,11})\b', full_str)
    if dl_m:
        fields["id_number"] = dl_m.group(1)
        fields["document_id_label"] = "Driving License No."

    # Dates
    dates = re.findall(r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b', full_str)
    dates = [_parse_date(d) for d in dates]
    if dates:
        fields["dob"] = dates[0]
    if len(dates) >= 2:
        fields["validity_expiry"] = dates[-1]

    # Name using label approach
    name = _next_value_after_label(ascii_l, r'\bName\b|Holder')
    if name and _is_name_like(name):
        fields["holder_name"] = name.upper()
    elif not name:
        _dl_skip = re.compile(
            r'DRIVING|LICENCE|LICENSE|UNION|INDIA|TRANSPORT|DEPARTMENT|'
            r'VALIDITY|DOB|FORM|MOTOR|VEHICLE', re.I
        )
        cands = [t for t in raw_texts
                 if not _dl_skip.search(t) and not re.search(r'\d', t)
                 and len(t.strip()) > 3 and _is_name_like(t)]
        if cands:
            fields["holder_name"] = cands[0].upper()

    return fields


def parse_voter_id(lines: list) -> dict:
    sorted_l  = _sort_by_y(lines)
    ascii_l   = _ascii_lines(sorted_l)
    raw_texts = [l["text"] for l in ascii_l]
    full_str  = "\n".join(raw_texts)
    fields    = {}

    # EPIC Number: 3 letters + 7 digits
    epic_m = re.search(r'\b([A-Z]{3}[0-9]{7})\b', full_str)
    if epic_m:
        fields["id_number"] = epic_m.group(1)
        fields["document_id_label"] = "EPIC (Voter ID) No."

    # Gender
    if re.search(r'\bFEMALE\b', full_str, re.I):
        fields["gender"] = "FEMALE"
    elif re.search(r'\bMALE\b', full_str, re.I):
        fields["gender"] = "MALE"

    # Elector Name
    name = _next_value_after_label(ascii_l, r'\bName\b|Elector', exclude_re=r'Relative|Father|Husband')
    if name and _is_name_like(name):
        fields["holder_name"] = name.upper()

    # Relative Name
    rel = _next_value_after_label(ascii_l, r'Father|Husband|Relative')
    if rel and _is_name_like(rel):
        fields["relative_name"] = rel.upper()

    if "holder_name" not in fields:
        _vid_skip = re.compile(
            r'ELECTION|COMMISSION|INDIA|CARD|IDENTITY|ELECTOR|'
            r'PHOTO|FATHER|HUSBAND|SEX|AGE|EPIC', re.I
        )
        cands = [t for t in raw_texts
                 if not _vid_skip.search(t) and not re.search(r'\d', t)
                 and len(t.strip()) > 3 and _is_name_like(t)]
        if cands:
            fields["holder_name"] = cands[0].upper()
        if len(cands) >= 2 and "relative_name" not in fields:
            fields["relative_name"] = cands[1].upper()

    return fields


# ─── MAIN DISPATCHER ─────────────────────────────────────────────────────────

def extract_structured_fields(doc_type_key: str, lines: list) -> dict:
    """Route to the correct parser based on detected document class."""
    if "pan" in doc_type_key:
        return parse_pan_card(lines)
    elif "aadhar" in doc_type_key:
        return parse_aadhaar(lines, is_back="back" in doc_type_key)
    elif "passport" in doc_type_key:
        return parse_passport(lines)
    elif "driving" in doc_type_key:
        return parse_driving_license(lines)
    elif "voter" in doc_type_key:
        return parse_voter_id(lines)
    else:
        raw = "\n".join(l["text"] for l in lines)
        fields = {}
        id_m = re.search(r'\b([A-Z0-9]{8,16})\b', raw)
        if id_m:
            fields["detected_id"] = id_m.group(1)
        return fields
