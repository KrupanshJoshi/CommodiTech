import os
import sys
import glob
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
from services.ocr_service import run_ocr
from services.field_extraction import extract_fields

test_images = sorted(glob.glob("Test/*.*") + glob.glob("sample_images/*.png"))
print(f"Found {len(test_images)} test images.\n")

for img_path in test_images:
    print("=" * 70)
    print(f"IMAGE: {img_path}")
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        print("Could not load image.")
        continue

    ocr_res = run_ocr(img_bgr)
    words = ocr_res.get("words", [])
    raw_text = ocr_res.get("raw_text", "")
    print(f"Engine: {ocr_res.get('engine')}, Words: {len(words)}, Mean Conf: {ocr_res.get('mean_confidence')}%")
    print(f"OCR Text:\n{raw_text}\n")

    extracted = extract_fields(ocr_res)
    found_count = 0
    print("--- Extracted Results ---")
    for field_name, detail in extracted.items():
        val = detail.get("value")
        status = detail.get("status")
        reason = detail.get("reason")
        conf = detail.get("confidence")
        if val is not None:
            found_count += 1
            print(f"  [FOUND] {field_name:25s}: {val} (status={status}, conf={conf})")
        else:
            print(f"  [MISSING] {field_name:23s}: None (status={status}, reason={reason})")

    rate = (found_count / 12.0) * 100.0
    print(f"\nScore: {found_count}/12 fields detected ({rate:.1f}%)\n")
