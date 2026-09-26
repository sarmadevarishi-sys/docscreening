import sys
sys.path.insert(0, '.')
from models.document_validator import _verhoeff_validate, validate_document
from models.ocr_extractor import parse_aadhaar

# 1. Test Official Verhoeff Checksum vectors
print("--- Testing Official Verhoeff Vectors ---")
assert _verhoeff_validate("2363"), "Verhoeff failed on standard vector 2363"
assert _verhoeff_validate("1429"), "Verhoeff failed on standard vector 1429"
assert _verhoeff_validate("123451"), "Verhoeff failed on standard vector 123451"
print("[PASS] Official Verhoeff test vectors verified!")

# 2. Test Real 12-digit Aadhaar UID Validation
# Valid 12-digit Aadhaar UID (11 digits: 23415678901 -> check digit 4)
valid_aadhaar = "234156789014"
assert _verhoeff_validate(valid_aadhaar), f"Valid Aadhaar {valid_aadhaar} failed Verhoeff!"
print(f"[PASS] Authentic Aadhaar UID {valid_aadhaar} PASSED Verhoeff!")

# Test with spaces: "2341 5678 9014"
assert _verhoeff_validate("2341 5678 9014"), "Failed to validate Aadhaar with spaces!"
print("[PASS] Spaced Aadhaar '2341 5678 9014' PASSED Verhoeff!")

# Altered UID test (changing last digit to 5):
altered_aadhaar = "234156789015"
assert not _verhoeff_validate(altered_aadhaar), f"Altered Aadhaar {altered_aadhaar} should have failed!"
print(f"[PASS] Altered Aadhaar {altered_aadhaar} was correctly CAUGHT as invalid!")

# 3. Test Aadhaar OCR parsing with DOB anchor & multi-space UID
mock_aadhaar_lines = [
    {'text': 'GOVERNMENT OF INDIA', 'bbox': [[0, 20], [0, 40]]},
    {'text': 'Unique Identification Authority of India', 'bbox': [[0, 45], [0, 65]]},
    {'text': 'सुरेश कुमार शर्मा', 'bbox': [[0, 80], [0, 100]]},
    {'text': 'SURESH KUMAR SHARMA', 'bbox': [[0, 105], [0, 125]]},
    {'text': 'जन्म तिथि / DOB: 15/08/1992', 'bbox': [[0, 135], [0, 155]]},
    {'text': 'पुरुष / MALE', 'bbox': [[0, 165], [0, 185]]},
    {'text': '2341   5678   9014', 'bbox': [[0, 220], [0, 240]]}  # wide spacing between blocks
]

fields = parse_aadhaar(mock_aadhaar_lines)
print("\n--- Extracted Aadhaar Fields ---")
for k, v in fields.items():
    print(f"  {k}: {v}")

assert fields.get("holder_name") == "SURESH KUMAR SHARMA", f"Expected SURESH KUMAR SHARMA, got {fields.get('holder_name')}"
assert fields.get("id_number") == "2341 5678 9014", f"Expected '2341 5678 9014', got {fields.get('id_number')}"
assert fields.get("dob") == "15/08/1992", f"Expected '15/08/1992', got {fields.get('dob')}"
assert fields.get("gender") == "MALE", f"Expected 'MALE', got {fields.get('gender')}"

val = validate_document("aadhar_front", fields)
print("\n--- Aadhaar Document Validation ---")
print("Verdict:", val["verdict"])
for c in val["checks"]:
    print(f"  [{c['status']}] {c['rule']} -> {c['detail']}")

verhoeff_check = [c for c in val["checks"] if "Verhoeff" in c["rule"]]
assert verhoeff_check and verhoeff_check[0]["status"] == "PASS", f"Verhoeff check failed: {verhoeff_check}"

print("\n[ALL TESTS PASSED] Aadhaar Verhoeff tables & Name Anchor Extraction Verified Successfully!")
