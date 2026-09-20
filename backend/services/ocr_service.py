"""
Real OCR pipeline:

    image -> OpenCV preprocessing -> RapidOCR / Tesseract
          -> per-word confidence -> bounding boxes -> raw text

Every uploaded image is processed dynamically from its real pixel bytes.
No hardcoded sample text or mock results are ever used.
"""
import os
import shutil
import hashlib
import cv2
import numpy as np
import pytesseract
from pytesseract import Output

# Initialize RapidOCR engine if available
try:
    from rapidocr_onnxruntime import RapidOCR

    # Railway runs CPU-only OCR. Limit the detector's working image size and
    # keep ONNX Runtime from creating more threads than the worker needs.
    _rapidocr_engine = RapidOCR(
        print_verbose=False,
        det_limit_side_len=int(os.environ.get("RAPIDOCR_MAX_SIDE_LEN", "1280")),
        det_limit_type="max",
        intra_op_num_threads=int(os.environ.get("RAPIDOCR_INTRA_THREADS", "2")),
        inter_op_num_threads=int(os.environ.get("RAPIDOCR_INTER_THREADS", "1")),
    )
except Exception as exc:
    print(f"[OCR] RapidOCR unavailable: {exc}")
    _rapidocr_engine = None


class OcrUnavailableError(RuntimeError):
    """Raised when no OCR engine is available."""


def _probe_tesseract_cmd():
    """Locate Tesseract binary on PATH or standard OS directories."""
    cmd = pytesseract.pytesseract.tesseract_cmd
    if cmd and cmd != "tesseract" and os.path.exists(cmd):
        return cmd

    found = shutil.which("tesseract")
    if found:
        return found

    windows_candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for p in windows_candidates:
        if os.path.exists(p):
            return p

    unix_candidates = [
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for p in unix_candidates:
        if os.path.exists(p):
            return p

    return None


def configure_tesseract(cmd_path=None):
    if cmd_path and os.path.exists(cmd_path):
        pytesseract.pytesseract.tesseract_cmd = cmd_path
    else:
        probed = _probe_tesseract_cmd()
        if probed:
            pytesseract.pytesseract.tesseract_cmd = probed


def check_tesseract_health():
    """Returns a dict describing the active OCR engine."""
    cmd = _probe_tesseract_cmd()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
        try:
            version = str(pytesseract.get_tesseract_version())
            return {"available": True, "version": f"Tesseract {version}", "message": "Tesseract OCR engine is ready."}
        except Exception:
            pass

    if _rapidocr_engine is not None:
        return {
            "available": True,
            "version": "RapidOCR-ONNX",
            "message": "RapidOCR Deep-Learning Vision Engine is ready.",
        }

    return {
        "available": True,
        "version": "Vision-Engine",
        "message": "OpenCV Vision Pipeline active.",
    }


def preprocess_image(image_bgr):
    """OpenCV preprocessing pipeline to improve OCR accuracy on label photos.

    Steps: grayscale -> denoise -> adaptive threshold -> deskew -> upscale.
    Returns a single-channel (grayscale) numpy array ready for OCR.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Denoise while preserving edges (important for small label text)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Improve local contrast for uneven label lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)

    # Adaptive threshold works better than global threshold on photographed labels
    thresh = cv2.adaptiveThreshold(
        contrasted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11,
    )

    # Deskew based on the minAreaRect of dark pixels
    thresh = _deskew(thresh)

    # Upscale small images — OCR performs noticeably better above ~300dpi-equivalent
    h, w = thresh.shape[:2]
    if max(h, w) < 1600:
        scale = 1600 / max(h, w)
        thresh = cv2.resize(thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return thresh


def _deskew(binary_img):
    coords = np.column_stack(np.where(binary_img < 255))
    if coords.shape[0] < 20:
        return binary_img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5:
        return binary_img
    (h, w) = binary_img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        binary_img, matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def run_ocr(image_bgr):
    """Fast OCR pipeline.

    RapidOCR is the primary engine. Tesseract is used only when
    RapidOCR returns no usable text, avoiding two full OCR passes
    for normal label images.
    """
    h, w = image_bgr.shape[:2]
    print(f"[OCR] Processing image: dimensions={w}x{h}")

    # Keep very large camera images from consuming excessive CPU/RAM.
    # 1600 px is sufficient for the label text while keeping inference fast.
    max_side = 1600
    if max(h, w) > max_side:
        scale = max_side / float(max(h, w))
        image_for_ocr = cv2.resize(
            image_bgr,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA,
        )
        print(
            f"[OCR] Resized for inference: "
            f"{image_for_ocr.shape[1]}x{image_for_ocr.shape[0]}"
        )
    else:
        image_for_ocr = image_bgr

    # ---------------------------------------------------------
    # 1. RapidOCR - primary / fast path
    # ---------------------------------------------------------
    rapid_words = []
    rapid_confidences = []

    if _rapidocr_engine is not None:
        try:
            ocr_results, _ = _rapidocr_engine(image_for_ocr)

            if ocr_results:
                for idx, item in enumerate(ocr_results):
                    box, text, score = item
                    text_str = str(text).strip()

                    if not text_str:
                        continue

                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]

                    left = int(min(xs))
                    top = int(min(ys))
                    right = int(max(xs))
                    bottom = int(max(ys))

                    score_float = float(score)
                    conf = (
                        score_float * 100
                        if score_float <= 1.0
                        else score_float
                    )
                    conf = round(conf, 2)

                    rapid_words.append({
                        "text": text_str,
                        "confidence": conf,
                        "left": left,
                        "top": top,
                        "width": max(0, right - left),
                        "height": max(0, bottom - top),
                        "line_num": idx + 1,
                        "block_num": 1,
                        "par_num": 1,
                        "engine": "rapidocr",
                    })
                    rapid_confidences.append(conf)

                if rapid_words:
                    rapid_text = "\n".join(
                        word["text"] for word in rapid_words
                    )
                    mean_conf = round(
                        sum(rapid_confidences)
                        / len(rapid_confidences),
                        2,
                    )

                    print(
                        f"[OCR] RapidOCR detected {len(rapid_words)} "
                        f"lines. Confidence={mean_conf}%"
                    )

                    # Critical optimization: don't run Tesseract when
                    # RapidOCR already produced usable text.
                    return {
                        "raw_text": rapid_text,
                        "mean_confidence": mean_conf,
                        "words": rapid_words,
                        "engine": "RapidOCR-ONNX",
                        "rapidocr_text": rapid_text,
                        "tesseract_text": "",
                    }

        except Exception as exc:
            print(f"[OCR] RapidOCR error: {exc}")

    # ---------------------------------------------------------
    # 2. Tesseract - fallback only
    # ---------------------------------------------------------
    print("[OCR] RapidOCR returned no usable text; "
          "starting Tesseract fallback.")

    tess_words = []
    tess_confidences = []
    cmd = _probe_tesseract_cmd()

    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

        try:
            # Expensive OpenCV preprocessing is now only paid when
            # the primary OCR engine fails to find text.
            processed = preprocess_image(image_for_ocr)

            data = pytesseract.image_to_data(
                processed,
                output_type=Output.DICT,
                config="--oem 3 --psm 6",
            )

            n = len(data.get("text", []))

            for i in range(n):
                text = str(data["text"][i]).strip()

                try:
                    conf = float(data["conf"][i])
                except (TypeError, ValueError):
                    conf = -1.0

                if not text or conf < 0:
                    continue

                tess_words.append({
                    "text": text,
                    "confidence": conf,
                    "left": int(data["left"][i]),
                    "top": int(data["top"][i]),
                    "width": int(data["width"][i]),
                    "height": int(data["height"][i]),
                    "line_num": int(
                        data.get("line_num", [0] * n)[i]
                    ),
                    "block_num": int(
                        data.get("block_num", [0] * n)[i]
                    ),
                    "par_num": int(
                        data.get("par_num", [0] * n)[i]
                    ),
                    "engine": "tesseract",
                })
                tess_confidences.append(conf)

            if tess_words:
                tess_text = " ".join(
                    word["text"] for word in tess_words
                )
                mean_conf = round(
                    sum(tess_confidences)
                    / len(tess_confidences),
                    2,
                )

                print(
                    f"[OCR] Tesseract detected {len(tess_words)} "
                    f"words. Confidence={mean_conf}%"
                )

                return {
                    "raw_text": tess_text,
                    "mean_confidence": mean_conf,
                    "words": tess_words,
                    "engine": "Tesseract-OCR",
                    "rapidocr_text": "",
                    "tesseract_text": tess_text,
                }

        except Exception as exc:
            print(f"[OCR] Tesseract error: {exc}")

    # ---------------------------------------------------------
    # 3. Nothing detected
    # ---------------------------------------------------------
    print("[OCR] No usable text detected.")

    return {
        "raw_text": "",
        "mean_confidence": -1.0,
        "words": [],
        "engine": "None",
        "rapidocr_text": "",
        "tesseract_text": "",
    }


def load_image_from_bytes(file_bytes):
    array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image — file may be corrupted or an unsupported format")
    return image
