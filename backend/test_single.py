import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
from services.ocr_service import run_ocr
from services.field_extraction import extract_fields

img_path = sys.argv[1] if len(sys.argv) > 1 else "Test/test1.png"
print(f"Reading image: {img_path}")
img = cv2.imread(img_path)
if img is None:
    print("Could not load image:", img_path)
    sys.exit(1)

print("Image shape:", img.shape)
ocr_res = run_ocr(img)
print("OCR Engine:", ocr_res.get("engine"))
print("Words count:", len(ocr_res.get("words", [])))
print("Mean confidence:", ocr_res.get("mean_confidence"))
print("--- OCR Raw Text ---")
print(ocr_res.get("raw_text"))
print("--------------------")

ext = extract_fields(ocr_res)
print("\n--- Extracted Fields ---")
found = 0
for k, v in ext.items():
    val = v.get("value")
    status = v.get("status")
    reason = v.get("reason")
    conf = v.get("confidence")
    src = v.get("source")
    if val:
        found += 1
        print(f"  [FOUND]   {k:25s}: {val} (status={status}, conf={conf}, src={src})")
    else:
        print(f"  [MISSING] {k:25s}: None (status={status}, reason={reason})")

print(f"\nTotal: {found}/12 ({round(found/12*100, 1)}%)")
