import io
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image, ImageDraw, ImageFont
import numpy as np

def create_sample_pan():
    # Create a synthetic PAN Card image
    img = Image.new('RGB', (600, 380), color=(240, 248, 255))
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.text((180, 20), "INCOME TAX DEPARTMENT", fill=(10, 40, 90))
    draw.text((220, 45), "GOVT. OF INDIA", fill=(10, 40, 90))
    
    # PAN Number
    draw.text((50, 100), "Permanent Account Number Card", fill=(50, 50, 50))
    draw.text((50, 130), "ABCDE1234F", fill=(0, 0, 0))
    
    # Holder details
    draw.text((50, 180), "Name: RAJESH KUMAR SHARMA", fill=(0, 0, 0))
    draw.text((50, 220), "Father's Name: RAMESH SHARMA", fill=(0, 0, 0))
    draw.text((50, 260), "Date of Birth: 15/08/1990", fill=(0, 0, 0))
    
    # Photo box
    draw.rectangle([420, 100, 550, 260], fill=(200, 220, 240), outline=(100, 100, 100))
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_pipeline():
    print("Testing Module 1 Document Analysis Pipeline...")
    from models.image_model import analyze_image
    
    img_bytes = create_sample_pan()
    result = analyze_image(img_bytes)
    
    print("\n--- Pipeline Result Output ---")
    print("Risk Score:", result.get("riskScore"))
    print("Verdict Label:", result.get("label"))
    print("Classification:", result.get("document_classification"))
    print("Extracted Fields:", result.get("extracted_fields"))
    print("OCR Engine:", result.get("ocr_engine"))
    print("OCR Lines Count:", len(result.get("ocr_lines", [])))
    print("------------------------------\n")
    
    assert "document_classification" in result, "Missing document_classification"
    assert "extracted_fields" in result, "Missing extracted_fields"
    print("✅ All Module 1 backend tests passed!")

if __name__ == "__main__":
    test_pipeline()
