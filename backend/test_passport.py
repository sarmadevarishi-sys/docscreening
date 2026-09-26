import sys
sys.path.insert(0, '.')
from models.ocr_extractor import parse_passport
from models.document_validator import validate_document

# Test 1: Normal extraction with 10-year validation
mock_passport_lines = [
    {'text': 'REPUBLIC OF INDIA', 'bbox': [[0, 20], [0, 40]]},
    {'text': 'Passport No. G 7 3 2 1 7 3 2', 'bbox': [[0, 50], [0, 70]]},
    {'text': 'Surname: IND JHAJJ', 'bbox': [[0, 80], [0, 100]]},  # Testing "IND JHAJJ" prefix
    {'text': 'Given Names: DALJEET SINGH', 'bbox': [[0, 110], [0, 130]]},
    {'text': 'Date of Birth: 01/01/1989', 'bbox': [[0, 140], [0, 160]]},
    {'text': 'Place of Birth: LUDHIANA', 'bbox': [[0, 170], [0, 190]]},
    {'text': 'Place of Issue: CHANDIGARH', 'bbox': [[0, 200], [0, 220]]},
    {'text': 'Date of Issue: 01/02/2008', 'bbox': [[0, 230], [0, 250]]},
    {'text': 'Date of Expiry: 31/01/2018', 'bbox': [[0, 260], [0, 280]]},
    {'text': 'P<INDJHAJJ<<DALJEET<SINGH<<<<<<<<<<<<<<<<<<<', 'bbox': [[0, 300], [0, 320]]},
    {'text': 'G7321732<7IND8901011M1801318<<<<<<<<<<<<<<<2', 'bbox': [[0, 330], [0, 350]]}
]

fields = parse_passport(mock_passport_lines)
print('--- Extracted Passport Fields ---')
for k, v in fields.items():
    print(f'  {k}: {v}')

val = validate_document('passport', fields)
print('\n--- Validation Checks ---')
print('Verdict:', val['verdict'])
for c in val['checks']:
    print(f"  [{c['status']}] {c['rule']} -> {c['detail']}")

# Assertions
assert fields.get('surname') == 'JHAJJ', f"Country code IND not stripped! Got: {fields.get('surname')}"
assert fields.get('date_of_issue') != fields.get('expiry_date'), "Issue and Expiry dates are identical!"

ten_year_check = [c for c in val['checks'] if '10-Year' in c['rule']]
assert ten_year_check and ten_year_check[0]['status'] == 'PASS', f"10-Year check failed: {ten_year_check}"

# Test 2: Conflict resolution when OCR assigns identical dates
mock_identical_dates = [
    {'text': 'P<INDJHAJJ<<DALJEET<SINGH<<<<<<<<<<<<<<<<<<<', 'bbox': [[0, 20], [0, 40]]},
    {'text': 'G7321732<7IND8901011M1801318<<<<<<<<<<<<<<<2', 'bbox': [[0, 50], [0, 70]]},
    {'text': 'Date of Expiry: 31/01/2018', 'bbox': [[0, 80], [0, 100]]},
    {'text': 'Date of Issue: 31/01/2018', 'bbox': [[0, 110], [0, 130]]}  # Duplicate date in OCR
]
fields_dupe = parse_passport(mock_identical_dates)
print('\n--- Duplicate Date Resolution Test ---')
print('Date of Issue:', fields_dupe.get('date_of_issue'))
print('Date of Expiry:', fields_dupe.get('expiry_date'))
assert fields_dupe.get('date_of_issue') != fields_dupe.get('expiry_date'), "Failed to resolve duplicate dates!"

print('\n[SUCCESS] All passport surname cleanup, 10-year validity, and duplicate resolution tests PASSED!')
