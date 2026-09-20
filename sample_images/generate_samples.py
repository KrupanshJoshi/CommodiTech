"""
Generates three synthetic commodity label images used as demo data:

  1. label_compliant.png      -> expected result: PASS
  2. label_partial.png        -> expected result: WARNING
  3. label_missing_invalid.png-> expected result: FAIL

These are rendered with Pillow (not photographed), so OCR accuracy on
them is high — they are meant to reliably demonstrate the full
pipeline (OCR -> extraction -> validation -> compliance) end to end,
not to stress-test OCR robustness on noisy real-world photos.

Run: python sample_images/generate_samples.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def _font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_label(filename, lines, size=(900, 1100)):
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    y = 40
    for text, font_size, bold_gap in lines:
        draw.text((40, y), text, fill="black", font=_font(font_size))
        y += bold_gap
    # simple border, like a printed label
    draw.rectangle([10, 10, size[0] - 10, size[1] - 10], outline="black", width=3)
    img.save(os.path.join(OUT_DIR, filename))
    print(f"wrote {filename}")


def main():
    # 1. Mostly compliant label -> expected PASS
    render_label("label_compliant.png", [
        ("Product Name: Organic Wheat Flour", 30, 55),
        ("Commodity Category: Food Grains", 24, 45),
        ("Manufactured By: Sunrise Foods Pvt Ltd", 24, 45),
        ("Manufacturer Address: Plot 12, MIDC Industrial Area, Pune, 411019", 20, 45),
        ("Batch No: SF2026A114", 24, 45),
        ("Net Quantity: 1 kg", 24, 45),
        ("Mfg Date: 01/03/2026", 24, 45),
        ("Exp Date: 01/03/2027", 24, 45),
        ("Best Before: 12 months from packaging", 20, 45),
        ("Ingredients: Whole wheat, Vitamin B1, Vitamin B2, Iron", 20, 45),
        ("FSSAI Lic No: 12345678901234", 24, 45),
        ("Country of Origin: India", 24, 45),
    ])

    # 2. Partially compliant -> expected WARNING
    render_label("label_partial.png", [
        ("Product Name: Classic Butter Cookies", 30, 55),
        ("Manufactured By: Golden Bake Industries", 24, 45),
        ("Manufacturer Address: 45 Industrial Estate, Nashik, 422010", 20, 45),
        ("Batch No: GB19", 24, 45),
        ("Net Quantity: 200 g", 24, 45),
        ("Exp Date: 15/11/2026", 24, 45),
        ("FSSAI Lic No: 22334455667788", 24, 45),
        # missing: commodity category, manufacturing date, ingredients,
        # country of origin -> several warnings, no blocking failure
    ])

    # 3. Missing/invalid required info -> expected FAIL
    render_label("label_missing_invalid.png", [
        ("Product Name: x", 30, 55),
        ("Net Wt: ???", 24, 45),
        ("Batch: ---", 24, 45),
        ("Exp Date: 01/01/2020", 24, 45),
        # expired, garbage product name, no manufacturer, no address,
        # no license number, invalid net quantity, invalid batch
    ])


if __name__ == "__main__":
    main()
