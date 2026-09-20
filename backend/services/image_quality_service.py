"""
Image Quality Assessment & Validation Service:

Evaluates image suitability BEFORE and DURING optical character recognition:
1. Resolution & Dimension limits
2. Sharpness & Blur via OpenCV Variance of Laplacian
3. Exposure & Brightness analysis (detecting dark/overexposed photos)
4. Dynamic Contrast & Histogram distribution
5. Text contour & edge density (Canny detector)
6. Post-OCR meaningful word count & readability verification
"""
import cv2
import numpy as np


def assess_image_quality(image_bgr):
    """Calculates an image quality assessment score (0-100) and identifies visual defects.

    Returns:
        dict: {
            "quality_score": int,          # 0-100 composite score
            "quality_status": str,         # "CLEAR_IMAGE" | "OCR_PARTIALLY_READABLE" | "UNCLEAR_IMAGE"
            "is_acceptable": bool,         # True if image is clear enough for reliable OCR
            "issues": list[str],           # Specific identified defects
            "tips": list[str],             # Actionable photography guidance
            "metrics": {
                "width": int,
                "height": int,
                "sharpness": float,        # Variance of Laplacian
                "brightness": float,       # Mean pixel intensity (0-255)
                "contrast": float,         # Standard deviation of intensities
                "edge_density": float,     # Percentage of edge pixels
            }
        }
    """
    if image_bgr is None or not hasattr(image_bgr, "shape"):
        return {
            "quality_score": 0,
            "quality_status": "UNCLEAR_IMAGE",
            "is_acceptable": False,
            "issues": ["Image file is corrupted or unreadable."],
            "tips": ["Please re-upload a valid PNG, JPG, or WEBP image."],
            "metrics": {
                "width": 0,
                "height": 0,
                "sharpness": 0.0,
                "brightness": 0.0,
                "contrast": 0.0,
                "edge_density": 0.0,
            },
        }

    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Blur / Sharpness calculation (Variance of Laplacian)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 2. Exposure / Brightness calculation (0 to 255)
    brightness = float(np.mean(gray))

    # 3. Dynamic Contrast (Standard deviation)
    contrast = float(np.std(gray))

    # 4. Text contour and edge presence (Canny)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float((np.count_nonzero(edges) / (h * w)) * 100.0)

    issues = []
    tips = [
        "Keep the camera steady and hold parallel to the label",
        "Avoid glare, shadows, and strong reflections",
        "Make sure the entire commodity label is fully visible and in focus",
        "Capture the photo under even, well-lit conditions",
        "Try taking the photo directly from the front of the packaging",
    ]

    # Individual Sub-Scores (0 to 100)
    # A. Resolution Score
    min_dim = min(h, w)
    if min_dim < 200:
        res_score = 15
        issues.append(f"Image resolution is too low ({w}x{h} px). Minimum recommended is 600x600 px.")
    elif min_dim < 400:
        res_score = 55
        issues.append("Low resolution image may reduce text extraction accuracy.")
    elif min_dim < 700:
        res_score = 80
    else:
        res_score = 100

    # B. Sharpness / Blur Score
    if laplacian_var < 15:
        sharpness_score = 10
        issues.append(f"Image is severely blurry and out of focus (sharpness: {laplacian_var:.1f}).")
    elif laplacian_var < 45:
        sharpness_score = 35
        issues.append("Image appears blurry. Text details cannot be clearly discerned.")
    elif laplacian_var < 80:
        sharpness_score = 65
    elif laplacian_var < 150:
        sharpness_score = 85
    else:
        sharpness_score = 100

    # C. Brightness & Exposure Score
    if brightness < 30:
        bright_score = 10
        issues.append(f"Image is severely underexposed/dark (brightness: {brightness:.1f}/255).")
    elif brightness < 60:
        bright_score = 45
        issues.append("Image is dim or in heavy shadow.")
    elif brightness > 245 and contrast < 25:
        bright_score = 20
        issues.append("Image is overexposed or washed out with strong glare/reflections.")
    elif brightness > 238 and edge_density < 0.5:
        bright_score = 30
        issues.append("Image is overexposed with very low text visibility.")
    elif 65 <= brightness <= 220:
        bright_score = 100
    else:
        bright_score = 80

    # D. Contrast Score
    if contrast < 12:
        contrast_score = 10
        issues.append(f"Image has almost no contrast (contrast: {contrast:.1f}).")
    elif contrast < 25:
        contrast_score = 40
        issues.append("Low contrast makes distinguishing text from packaging background difficult.")
    elif contrast < 40:
        contrast_score = 75
    else:
        contrast_score = 100

    # E. Edge / Visual Content Score
    if edge_density < 0.15:
        edge_score = 5
        issues.append("Almost no readable content, text edges, or label features detected.")
    elif edge_density < 0.6:
        edge_score = 40
    else:
        edge_score = 100

    # Composite Weighted Quality Score (0 to 100)
    composite_score = int(round(
        (sharpness_score * 0.35) +
        (bright_score * 0.25) +
        (contrast_score * 0.20) +
        (res_score * 0.15) +
        (edge_score * 0.05)
    ))
    composite_score = max(5, min(100, composite_score))

    # Critical failure hard gates
    is_hard_fail = (
        laplacian_var < 30 or
        brightness < 35 or
        (brightness > 245 and contrast < 20) or
        min_dim < 180 or
        (edge_density < 0.2 and contrast < 20) or
        composite_score < 40
    )

    if is_hard_fail:
        composite_score = min(composite_score, 38)
        quality_status = "UNCLEAR_IMAGE"
        is_acceptable = False
    elif composite_score >= 65 and laplacian_var >= 70:
        quality_status = "CLEAR_IMAGE"
        is_acceptable = True
    else:
        quality_status = "OCR_PARTIALLY_READABLE"
        is_acceptable = True

    return {
        "quality_score": composite_score,
        "quality_status": quality_status,
        "is_acceptable": is_acceptable,
        "issues": issues,
        "tips": tips,
        "metrics": {
            "width": w,
            "height": h,
            "sharpness": round(laplacian_var, 2),
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "edge_density": round(edge_density, 2),
        },
    }


def verify_ocr_readability(words, raw_text, quality_assessment):
    """Evaluates whether the OCR result contains enough authentic text
    to proceed with statutory compliance analysis.

    Returns:
        dict: {
            "readability_status": "CLEAR_IMAGE" | "OCR_PARTIALLY_READABLE" | "NO_TEXT_DETECTED" | "UNCLEAR_IMAGE",
            "meaningful_word_count": int,
            "mean_confidence": float,
            "can_proceed": bool,
            "rejection_reason": str | None
        }
    """
    if not quality_assessment.get("is_acceptable", False):
        return {
            "readability_status": "UNCLEAR_IMAGE",
            "meaningful_word_count": 0,
            "mean_confidence": -1.0,
            "can_proceed": False,
            "rejection_reason": "Image quality is below acceptable threshold for regulatory inspection.",
        }

    # Count meaningful words (ignoring 1-character noise and punctuation)
    meaningful_words = [
        w for w in (words or [])
        if len(str(w.get("text", "")).strip()) >= 2
        and any(c.isalnum() for c in str(w.get("text", "")))
    ]
    meaningful_count = len(meaningful_words)

    confidences = [float(w.get("confidence", 0)) for w in meaningful_words if float(w.get("confidence", 0)) > 0]
    mean_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    if meaningful_count < 3:
        return {
            "readability_status": "NO_TEXT_DETECTED",
            "meaningful_word_count": meaningful_count,
            "mean_confidence": mean_conf,
            "can_proceed": False,
            "rejection_reason": "No readable label declarations or text found on the uploaded image.",
        }

    if mean_conf < 40.0:
        return {
            "readability_status": "OCR_PARTIALLY_READABLE",
            "meaningful_word_count": meaningful_count,
            "mean_confidence": mean_conf,
            "can_proceed": True,
            "rejection_reason": None,
        }

    return {
        "readability_status": quality_assessment.get("quality_status", "CLEAR_IMAGE"),
        "meaningful_word_count": meaningful_count,
        "mean_confidence": mean_conf,
        "can_proceed": True,
        "rejection_reason": None,
    }
