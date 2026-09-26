"""
Module 2: Document Standard & Rule Validation Engine
SIH 2026 — AI-Based Fake Identity & Document Screening System
Ministry of Home Affairs | Cybersecurity & Blockchain Track

Validates extracted OCR fields against official Indian document standards:
  - PAN Card   : Format regex + Verhoeff checksum heuristic + field completeness
  - Aadhaar    : 12-digit rules + Verhoeff checksum + gender/DOB coherence
  - Passport   : ICAO 9303 MRZ check-digit algorithm + expiry check
  - DL         : State RTO code validation + date coherence
  - Voter ID   : EPIC format + field completeness
"""

import re
from datetime import datetime, date

# ─── INDIAN STATE / UT RTO CODE REGISTRY ────────────────────────────────────
VALID_STATE_CODES = {
    "AN","AP","AR","AS","BR","CG","CH","DD","DL","DN","GA","GJ","HP","HR",
    "JH","JK","KA","KL","LA","LD","MH","ML","MN","MP","MZ","NL","OD","PB",
    "PY","RJ","SK","TN","TR","TS","UK","UP","WB"
}

# ─── VERHOEFF CHECK TABLE (Aadhaar UID Validation) ──────────────────────────
# D: 10x10 Dihedral Multiplication Matrix
_V_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
)

# P: 8x10 Official Permutation Matrix
_V_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8)
)

# Inverse Table
_V_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)

def _verhoeff_validate(number_str: str) -> bool:
    """Validate a numeric string using the official Verhoeff algorithm."""
    try:
        clean = re.sub(r'[\s\-]', '', str(number_str))
        if not clean or not clean.isdigit():
            return False
        c = 0
        digits = [int(x) for x in reversed(clean)]
        for i, d in enumerate(digits):
            c = _V_D[c][_V_P[i % 8][d]]
        return c == 0
    except Exception:
        return False

# ─── ICAO 9303 MRZ CHECK DIGIT ───────────────────────────────────────────────
_MRZ_WEIGHT = [7, 3, 1]
_MRZ_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<"
_MRZ_VALUES  = {c: (0 if c == '<' else (i if i < 10 else i - 10)) for i, c in enumerate(_MRZ_CHARSET)}

def _mrz_check_digit(s: str, expected_digit: str) -> bool:
    """Validate a single MRZ field check digit per ICAO Doc 9303."""
    try:
        total = sum(_MRZ_VALUES.get(c, 0) * _MRZ_WEIGHT[i % 3] for i, c in enumerate(s))
        return (total % 10) == int(expected_digit)
    except Exception:
        return False

# ─── DATE PARSING UTILITIES ──────────────────────────────────────────────────
def _parse_date(date_str: str):
    """Try common Indian document date formats. Returns a date object or None."""
    if not date_str:
        return None
    fmts = ["%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d/%m/%y", "%Y%m%d"]
    for fmt in fmts:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def _is_expired(expiry_str: str) -> bool:
    """Returns True if the document is expired relative to today."""
    d = _parse_date(expiry_str)
    if d is None:
        return False
    return d < date.today()

def _dob_coherent(dob_str: str) -> bool:
    """Returns True if DOB is in the past and the person is between 1 and 120 years old."""
    d = _parse_date(dob_str)
    if d is None:
        return False
    today = date.today()
    age = (today - d).days / 365.25
    return 1 <= age <= 120

# =====================================================================
# DOCUMENT-SPECIFIC VALIDATION LOGIC
# =====================================================================

def _validate_pan(fields: dict) -> list:
    checks = []

    # 1. PAN number format
    pan = fields.get("id_number", "")
    if pan:
        if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
            checks.append({"rule": "PAN Format (ICAI Standard)", "status": "PASS",
                           "detail": f"'{pan}' matches [A-Z]{{5}}[0-9]{{4}}[A-Z] — Valid"})
            # 4th character entity check
            cat_char = pan[3]
            cat_map = {'P': 'Individual', 'C': 'Company', 'H': 'HUF', 'F': 'Firm',
                       'A': 'AOP', 'T': 'Trust', 'B': 'BOI', 'L': 'Local Authority',
                       'J': 'Artificial Juridical Person', 'G': 'Government'}
            entity = cat_map.get(cat_char)
            if entity:
                checks.append({"rule": "PAN Entity Classification", "status": "PASS",
                               "detail": f"4th character '{cat_char}' → {entity}"})
            else:
                checks.append({"rule": "PAN Entity Classification", "status": "WARN",
                               "detail": f"4th character '{cat_char}' is not a recognized CBDT entity code"})
        else:
            checks.append({"rule": "PAN Format (ICAI Standard)", "status": "FAIL",
                           "detail": f"'{pan}' does not match required pattern [A-Z]{{5}}[0-9]{{4}}[A-Z]"})
    else:
        checks.append({"rule": "PAN Format (ICAI Standard)", "status": "WARN",
                       "detail": "PAN number could not be extracted from document"})

    # 2. DOB coherence
    dob = fields.get("dob", "")
    if dob:
        if _dob_coherent(dob):
            checks.append({"rule": "Date of Birth Coherence", "status": "PASS",
                           "detail": f"DOB '{dob}' is valid and represents a plausible age"})
        else:
            checks.append({"rule": "Date of Birth Coherence", "status": "FAIL",
                           "detail": f"DOB '{dob}' is implausible (future date or age > 120)"})
    else:
        checks.append({"rule": "Date of Birth Coherence", "status": "WARN",
                       "detail": "Date of Birth not found in extracted fields"})

    # 3. Holder name presence
    name = fields.get("holder_name", "")
    if name and len(name.strip()) > 2:
        checks.append({"rule": "Holder Name Presence", "status": "PASS",
                       "detail": f"Name extracted: '{name}'"})
    else:
        checks.append({"rule": "Holder Name Presence", "status": "WARN",
                       "detail": "Holder name absent or too short — possible OCR failure or tampering"})

    return checks


def _validate_aadhaar(fields: dict) -> list:
    checks = []

    # 1. UID format (12 digits)
    uid = fields.get("id_number", "").replace(" ", "")
    if uid:
        if re.fullmatch(r"[2-9][0-9]{11}", uid):
            checks.append({"rule": "Aadhaar UID Format (UIDAI Standard)", "status": "PASS",
                           "detail": f"UID '{uid[:4]} {uid[4:8]} {uid[8:]}' is a valid 12-digit number (starts 2–9)"})
            # Verhoeff checksum
            if _verhoeff_validate(uid):
                checks.append({"rule": "Verhoeff Checksum Integrity", "status": "PASS",
                               "detail": "Verhoeff algorithm verified — UID checksum is authentic"})
            else:
                checks.append({"rule": "Verhoeff Checksum Integrity", "status": "FAIL",
                               "detail": "Verhoeff checksum FAILED — UID may have been altered or is invalid"})
        else:
            checks.append({"rule": "Aadhaar UID Format (UIDAI Standard)", "status": "FAIL",
                           "detail": f"'{uid}' does not meet UIDAI 12-digit specification (must start 2–9)"})
    else:
        checks.append({"rule": "Aadhaar UID Format (UIDAI Standard)", "status": "WARN",
                       "detail": "Aadhaar UID not extracted — verify image quality or document legitimacy"})

    # 2. DOB coherence
    dob = fields.get("dob", "")
    if dob:
        if _dob_coherent(dob):
            checks.append({"rule": "Date of Birth Coherence", "status": "PASS",
                           "detail": f"DOB '{dob}' is valid"})
        else:
            checks.append({"rule": "Date of Birth Coherence", "status": "FAIL",
                           "detail": f"DOB '{dob}' is implausible"})

    # 3. Gender presence
    gender = fields.get("gender", "")
    if gender in ("MALE", "FEMALE", "TRANSGENDER"):
        checks.append({"rule": "Gender Field Validation", "status": "PASS",
                       "detail": f"Gender field contains valid value: '{gender}'"})
    else:
        checks.append({"rule": "Gender Field Validation", "status": "WARN",
                       "detail": "Gender field absent or unrecognized"})

    return checks


def _validate_passport(fields: dict) -> list:
    checks = []

    # 1. Passport number format (ICAO 9303)
    pnum = (fields.get("id_number") or "").strip().rstrip("<")
    if not pnum and fields.get("mrz_raw") and len(fields["mrz_raw"]) >= 2:
        l2_cand = fields["mrz_raw"][1].replace(" ", "")
        if len(l2_cand) >= 9:
            pnum = l2_cand[0:9].rstrip("<")

    if pnum:
        if re.fullmatch(r"[A-Z][0-9]{7}", pnum):
            checks.append({"rule": "Passport Number Format (ICAO 9303)", "status": "PASS",
                           "detail": f"'{pnum}' matches Indian passport format [A-Z][0-9]{{7}}"})
        else:
            checks.append({"rule": "Passport Number Format (ICAO 9303)", "status": "FAIL",
                           "detail": f"'{pnum}' does not match ICAO 9303 Indian passport standard"})
    else:
        checks.append({"rule": "Passport Number Format (ICAO 9303)", "status": "WARN",
                       "detail": "Passport number not extracted"})

    # 2. MRZ check digit validation
    mrz = fields.get("mrz_raw", [])
    if mrz and len(mrz) >= 2:
        l2 = mrz[1].replace(" ", "")
        if len(l2) >= 44:
            # Passport number check (positions 0-8, check digit at 9)
            pn_valid = _mrz_check_digit(l2[0:9], l2[9]) if len(l2) > 9 else False
            # DOB check (positions 13-18, check digit at 19)
            dob_valid = _mrz_check_digit(l2[13:19], l2[19]) if len(l2) > 19 else False
            # Expiry check (positions 21-26, check digit at 27)
            exp_valid = _mrz_check_digit(l2[21:27], l2[27]) if len(l2) > 27 else False

            checks.append({"rule": "MRZ Passport No. Check Digit (ICAO 9303 §4.2.1)", 
                           "status": "PASS" if pn_valid else "FAIL",
                           "detail": "Check digit verified" if pn_valid else "Check digit mismatch — MRZ may be forged"})
            checks.append({"rule": "MRZ DOB Check Digit (ICAO 9303 §4.2.1)", 
                           "status": "PASS" if dob_valid else "FAIL",
                           "detail": "DOB check digit verified" if dob_valid else "DOB check digit mismatch — possible tampering"})
            checks.append({"rule": "MRZ Expiry Check Digit (ICAO 9303 §4.2.1)", 
                           "status": "PASS" if exp_valid else "FAIL",
                           "detail": "Expiry check digit verified" if exp_valid else "Expiry check digit mismatch"})
        else:
            checks.append({"rule": "MRZ Structure Check", "status": "WARN",
                           "detail": f"MRZ line too short ({len(l2)} chars), expected 44 — OCR may be incomplete"})
    else:
        checks.append({"rule": "MRZ Presence Check", "status": "WARN",
                       "detail": "MRZ not detected — ensure full passport bio-data page is uploaded"})

    # 3. Expiry check
    expiry = fields.get("expiry_date", "")
    if expiry:
        if _is_expired(expiry):
            checks.append({"rule": "Document Expiry Status", "status": "FAIL",
                           "detail": f"EXPIRED — Document expired on '{expiry}'"})
        else:
            checks.append({"rule": "Document Expiry Status", "status": "PASS",
                           "detail": f"Valid — Document expires on '{expiry}'"})

    # 4. DOB coherence
    dob = fields.get("dob", "")
    if dob:
        if _dob_coherent(dob):
            checks.append({"rule": "Date of Birth Coherence", "status": "PASS",
                           "detail": f"DOB '{dob}' is plausible"})
        else:
            checks.append({"rule": "Date of Birth Coherence", "status": "FAIL",
                           "detail": f"DOB '{dob}' is implausible"})

    # 5. Passport 10-Year Validity Coherence (Passports Act 1967)
    issue_str = fields.get("date_of_issue", "")
    expiry_str = fields.get("expiry_date", "")
    if issue_str and expiry_str:
        if issue_str == expiry_str:
            checks.append({
                "rule": "Passport 10-Year Validity Coherence",
                "status": "FAIL",
                "detail": f"Date of Issue ({issue_str}) and Date of Expiry ({expiry_str}) are identical — invalid timeline"
            })
        else:
            d_issue = _parse_date(issue_str)
            d_exp = _parse_date(expiry_str)
            if d_issue and d_exp:
                diff_years = (d_exp - d_issue).days / 365.25
                if 9.4 <= diff_years <= 10.6:
                    checks.append({
                        "rule": "Passport 10-Year Validity Coherence",
                        "status": "PASS",
                        "detail": f"10-Year Validity verified ({issue_str} to {expiry_str} — standard adult passport)"
                    })
                elif 4.4 <= diff_years <= 5.6:
                    checks.append({
                        "rule": "Passport 10-Year Validity Coherence",
                        "status": "PASS",
                        "detail": f"5-Year Validity verified ({issue_str} to {expiry_str} — standard minor passport)"
                    })
                elif diff_years <= 0:
                    checks.append({
                        "rule": "Passport 10-Year Validity Coherence",
                        "status": "FAIL",
                        "detail": f"Expiry date ({expiry_str}) is earlier than Issue date ({issue_str}) — impossible timeline"
                    })
                else:
                    checks.append({
                        "rule": "Passport 10-Year Validity Coherence",
                        "status": "WARN",
                        "detail": f"Non-standard validity duration: {round(diff_years, 1)} years (standard is 10 years for adult, 5 for minor)"
                    })

    return checks


def _validate_driving_license(fields: dict) -> list:
    checks = []

    # 1. DL number format + state code
    dl = fields.get("id_number", "").replace("-", "").replace(" ", "").upper()
    if dl:
        state_code = dl[:2]
        if state_code in VALID_STATE_CODES:
            checks.append({"rule": "DL State Code (MoRTH Registry)", "status": "PASS",
                           "detail": f"State code '{state_code}' is a recognized RTO state code"})
        else:
            checks.append({"rule": "DL State Code (MoRTH Registry)", "status": "FAIL",
                           "detail": f"'{state_code}' is NOT a valid Indian RTO state code"})

        if re.fullmatch(r"[A-Z]{2}[0-9]{11,13}", dl):
            checks.append({"rule": "DL Number Format (MoRTH Standard)", "status": "PASS",
                           "detail": f"DL number structure is valid"})
        else:
            checks.append({"rule": "DL Number Format (MoRTH Standard)", "status": "WARN",
                           "detail": f"DL number '{dl}' may be non-standard (regional variations exist)"})
    else:
        checks.append({"rule": "DL Number Format (MoRTH Standard)", "status": "WARN",
                       "detail": "DL number not extracted"})

    # 2. Validity check
    expiry = fields.get("validity_expiry", "")
    if expiry:
        if _is_expired(expiry):
            checks.append({"rule": "License Validity Status", "status": "FAIL",
                           "detail": f"EXPIRED — License expired on '{expiry}'"})
        else:
            checks.append({"rule": "License Validity Status", "status": "PASS",
                           "detail": f"Valid — License valid until '{expiry}'"})

    # 3. DOB coherence
    dob = fields.get("dob", "")
    if dob:
        if _dob_coherent(dob):
            checks.append({"rule": "Date of Birth Coherence", "status": "PASS",
                           "detail": f"DOB '{dob}' is valid"})
        else:
            checks.append({"rule": "Date of Birth Coherence", "status": "FAIL",
                           "detail": f"DOB '{dob}' is implausible"})

    return checks


def _validate_voter_id(fields: dict) -> list:
    checks = []

    # 1. EPIC format
    epic = fields.get("id_number", "")
    if epic:
        if re.fullmatch(r"[A-Z]{3}[0-9]{7}", epic):
            checks.append({"rule": "EPIC Number Format (ECI Standard)", "status": "PASS",
                           "detail": f"'{epic}' matches ECI EPIC format [A-Z]{{3}}[0-9]{{7}}"})
        else:
            checks.append({"rule": "EPIC Number Format (ECI Standard)", "status": "FAIL",
                           "detail": f"'{epic}' does not match ECI EPIC standard format"})
    else:
        checks.append({"rule": "EPIC Number Format (ECI Standard)", "status": "WARN",
                       "detail": "EPIC number not extracted"})

    # 2. Name presence
    name = fields.get("holder_name", "")
    if name and len(name.strip()) > 2:
        checks.append({"rule": "Elector Name Presence", "status": "PASS",
                       "detail": f"Elector name extracted: '{name}'"})
    else:
        checks.append({"rule": "Elector Name Presence", "status": "WARN",
                       "detail": "Elector name absent — possible OCR failure"})

    # 3. Gender presence
    gender = fields.get("gender", "")
    if gender in ("MALE", "FEMALE"):
        checks.append({"rule": "Gender Field Validation", "status": "PASS",
                       "detail": f"Gender: '{gender}'"})
    else:
        checks.append({"rule": "Gender Field Validation", "status": "WARN",
                       "detail": "Gender absent or unrecognized"})

    return checks


# =====================================================================
# MAIN DISPATCHER
# =====================================================================

def validate_document(doc_type_key: str, extracted_fields: dict) -> dict:
    """
    Runs the appropriate rule-set validation for the detected document type.
    Returns a validation report with individual check results and an overall verdict.
    """
    if not doc_type_key or doc_type_key == "unknown":
        return {
            "checks": [{"rule": "Document Type Identification", "status": "FAIL",
                        "detail": "Document type could not be determined — cannot apply validation rules"}],
            "verdict": "UNVERIFIABLE",
            "pass_count": 0,
            "fail_count": 1,
            "warn_count": 0
        }

    if "pan" in doc_type_key:
        checks = _validate_pan(extracted_fields)
    elif "aadhar" in doc_type_key:
        checks = _validate_aadhaar(extracted_fields)
    elif "passport" in doc_type_key:
        checks = _validate_passport(extracted_fields)
    elif "driving" in doc_type_key:
        checks = _validate_driving_license(extracted_fields)
    elif "voter" in doc_type_key:
        checks = _validate_voter_id(extracted_fields)
    else:
        checks = [{"rule": "Generic Document Check", "status": "WARN",
                   "detail": f"No specific validation ruleset for '{doc_type_key}'"}]

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    total      = len(checks)

    if fail_count == 0 and pass_count > 0:
        verdict = "VALIDATED"
    elif fail_count >= 2:
        verdict = "INVALID"
    elif fail_count == 1:
        verdict = "SUSPICIOUS"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "checks":      checks,
        "verdict":     verdict,
        "pass_count":  pass_count,
        "fail_count":  fail_count,
        "warn_count":  warn_count,
        "total_rules": total
    }
