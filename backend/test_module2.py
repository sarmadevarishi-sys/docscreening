import sys
sys.path.insert(0, '.')
from models.document_validator import validate_document

def show(label, doc_key, fields):
    print(f"--- {label} ---")
    r = validate_document(doc_key, fields)
    print(f"Verdict: {r['verdict']} | PASS:{r['pass_count']} FAIL:{r['fail_count']} WARN:{r['warn_count']}")
    for c in r['checks']:
        print(f"  [{c['status']}] {c['rule']}")
        print(f"        -> {c['detail']}")
    print()

# PAN Card - valid
show("PAN Card (valid)",
     "pan_card_front",
     {"id_number": "ABCDE1234F", "holder_name": "RAJESH KUMAR SHARMA", "dob": "15/08/1990"})

# PAN Card - tampered (bad format)
show("PAN Card (TAMPERED format)",
     "pan_card_front",
     {"id_number": "12345ABCDE", "holder_name": "X", "dob": "99/99/9999"})

# Aadhaar - Verhoeff checksum check
show("Aadhaar Front (real UID with Verhoeff check)",
     "aadhar_front",
     {"id_number": "234123412346", "gender": "MALE", "dob": "01/01/1985"})

# Passport - format check
show("Indian Passport",
     "passport",
     {"id_number": "A1234567", "dob": "10/05/1988", "expiry_date": "10/05/2030",
      "mrz_raw": []})

# Voter ID
show("Voter ID",
     "voter_id",
     {"id_number": "ABC1234567", "holder_name": "PRIYA SHARMA", "gender": "FEMALE"})

# Driving License
show("Driving License (Maharashtra)",
     "driving_license_front",
     {"id_number": "MH1220180012345", "dob": "22/03/1995", "validity_expiry": "22/03/2030"})

print("All Module 2 tests completed.")
