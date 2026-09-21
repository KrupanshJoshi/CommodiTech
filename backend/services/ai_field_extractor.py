"""
AI-Assisted Field Extraction Service:

Uses Large Language Models (Google Gemini / OpenAI / OpenRouter) to semantically
extract the 12 statutory regulatory parameters from normalized dual OCR outputs.

Strict Constraints:
- Extract ONLY what is supported by the OCR text.
- NEVER invent missing information or hallucinate unreadable digits.
- Normalize dates to YYYY-MM-DD; return null on incomplete dates.
- Distinguish between Manufacturing Date, Expiry Date, and Best Before.
- Output strictly validated JSON.
"""

import os
import json
import re
import requests


SYSTEM_INSTRUCTION = """You are an expert regulatory compliance auditor specialized in Indian Packaged Commodity Regulations (Legal Metrology Packaged Commodities Rules & FSSAI Labelling Standards).

Your task is to extract exactly 12 statutory declarations from the provided Optical Character Recognition (OCR) text of a product packaging label.

CRITICAL EXTRACTION RULES:
1. Extract ONLY information explicitly present in or directly supported by the OCR text.
2. NEVER invent missing information, names, addresses, or numbers.
3. NEVER guess unreadable or truncated characters. If a field or date is partially cut off (e.g. "12/05/2?"), return null.
4. Return null for any field that is absent or cannot be reliably identified.
5. Do NOT confuse product descriptions, promotional slogans, or certifications with the actual Product Name or Commodity Category.
6. Understand common abbreviations:
   - Manufacturer / Packer / Marketer: MFD BY, MFG BY, MFR BY, MANUFACTURED BY, MARKETED BY, PACKED BY, PKD BY, CO-PACKED BY, PRODUCED BY. Extract the actual company or legal corporate entity name (e.g. 'LT Foods Limited', 'ITC Limited') into `manufacturer_name` and the physical location/factory details into `manufacturer_address`. Do NOT extract brand slogans or descriptor phrases like 'A Brand of', 'A Product of', 'A Unit of', 'Brand Owned By', 'TM' as the manufacturer name.
   - Manufacturing: MFG, MFD, MANF, MANUFACTURED, PACKED ON, PKD, DATE OF PACKING, DOM, DOP
   - Expiry: EXP, EXPIRY, EXP DATE, USE BY, DOE
   - Best Before: BEST BEFORE, CONSUME WITHIN
   - Batch/Lot: BATCH, LOT, B.NO, LOT NO
   - Net Quantity: NET WT, NET WEIGHT, NET QTY, NET MASS, CONTENTS
   - License: FSSAI, LIC NO, REG NO, REGISTRATION
   - Origin: MADE IN, PRODUCT OF, COUNTRY OF ORIGIN
7. DATE NORMALIZATION:
   - Convert valid full dates (e.g. DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD, DD Month YYYY, or compact/unspaced dates like '09AUG2026', '12JAN2024', '11JAN2026', '19MAR26') strictly into ISO format "YYYY-MM-DD".
   - If a date only has Month and Year (e.g. "03/2026", "AUG2024", "AUG 2024"), format as "YYYY-MM-01" (e.g. "2024-08-01").
   - Do NOT confuse manufacturing date with expiry date.
   - "Best Before" can be a relative duration (e.g. "12 months from manufacture") or a date. If it is a relative duration, preserve the text.
8. RETURN STRICT JSON MATCHING THIS EXACT SCHEMA ONLY:
{
  "product_name": string or null,
  "commodity_category": string or null,
  "manufacturer_name": string or null,
  "manufacturer_address": string or null,
  "batch_number": string or null,
  "net_quantity": string or null,
  "manufacturing_date": "YYYY-MM-DD" or null,
  "expiry_date": "YYYY-MM-DD" or null,
  "best_before": string or null,
  "ingredients": string or null,
  "license_number": string or null,
  "country_of_origin": string or null
}
"""


def _get_ai_config():
    provider = os.environ.get("AI_PROVIDER", "").strip().lower()

    api_key = (
        os.environ.get("AI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )

    model = os.environ.get("AI_MODEL", "").strip()

    timeout = int(os.environ.get("AI_TIMEOUT_SECONDS", "10"))

    if not provider:
        if "AI_API_KEY" in os.environ or "GEMINI_API_KEY" in os.environ:
            provider = "gemini"
        elif "OPENAI_API_KEY" in os.environ:
            provider = "openai"
        else:
            provider = "none"

    if provider == "gemini" and not model:
        model = "gemini-3.5-flash"

    elif provider == "openai" and not model:
        model = "gpt-4o-mini"

    return {
        "provider": provider,
        "api_key": api_key.strip(),
        "model": model,
        "timeout": min(timeout, 12) if timeout > 12 else timeout,
    }


def extract_with_gemini(ocr_text, config):
    """Calls Google Gemini REST API using GenerateContent JSON mode."""

    api_key = config["api_key"]

    primary_model = config["model"] or "gemini-3.5-flash"

    fallback_models = [
        "gemini-3.5-flash-lite",
    ]

    models_to_try = [
        primary_model
    ] + [
        model for model in fallback_models
        if model != primary_model
    ]

    prompt_content = (
        f'OCR TEXT FROM PACKAGING LABEL:\n'
        f'"""\n'
        f'{ocr_text}\n'
        f'"""\n\n'
        f'Extract all 12 statutory regulatory parameters according to instructions.'
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": SYSTEM_INSTRUCTION
                    },
                    {
                        "text": prompt_content
                    },
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
        },
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    last_error = None

    for model in models_to_try:

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
        )

        try:

            print(
                f"[AI Extractor] Calling Gemini model: {model}"
            )

            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=config["timeout"],
            )

            if resp.status_code == 200:

                data = resp.json()

                candidates = data.get("candidates", [])

                if not candidates:
                    last_error = "Gemini returned no candidates."
                    continue

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                if not parts:
                    last_error = "Gemini returned no content parts."
                    continue

                text_resp = parts[0].get("text", "")

                if not text_resp:
                    last_error = "Gemini returned empty response text."
                    continue

                try:
                    return json.loads(text_resp)

                except json.JSONDecodeError as exc:
                    last_error = (
                        f"Gemini returned invalid JSON: {exc}"
                    )
                    continue

            elif resp.status_code in (404, 429, 503):

                print(
                    f"[AI Extractor] Model {model} returned "
                    f"{resp.status_code}, trying fallback..."
                )

                last_error = (
                    f"Gemini API {resp.status_code}: "
                    f"{resp.text}"
                )

                continue

            else:

                last_error = (
                    f"Gemini API {resp.status_code}: "
                    f"{resp.text}"
                )

                break

        except requests.Timeout:

            print(
                f"[AI Extractor] Gemini model {model} timed out."
            )

            last_error = (
                f"Gemini request timed out after "
                f"{config['timeout']} seconds."
            )

            continue

        except requests.RequestException as exc:

            print(
                f"[AI Extractor] Network error on "
                f"{model}: {exc}"
            )

            last_error = str(exc)

            continue

        except Exception as exc:

            print(
                f"[AI Extractor] Error on "
                f"{model}: {exc}"
            )

            last_error = str(exc)

            continue

    raise RuntimeError(
        f"All Gemini models failed. Last error: {last_error}"
    )


def extract_with_openai(ocr_text, config):
    """Calls OpenAI-compatible REST API using JSON mode."""

    api_key = config["api_key"]

    model = config["model"]

    base_url = os.environ.get(
        "OPENAI_BASE_URL",
        "https://api.openai.com/v1"
    ).rstrip("/")

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt_content = (
        f'OCR TEXT FROM PACKAGING LABEL:\n'
        f'"""\n'
        f'{ocr_text}\n'
        f'"""\n\n'
        f'Extract all 12 statutory regulatory parameters according to instructions.'
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION
            },
            {
                "role": "user",
                "content": prompt_content
            },
        ],
        "response_format": {
            "type": "json_object"
        },
        "temperature": 0.0,
    }

    resp = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=config["timeout"],
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenAI API error "
            f"{resp.status_code}: {resp.text}"
        )

    data = resp.json()

    text_resp = (
        data["choices"][0]["message"]["content"]
    )

    return json.loads(text_resp)


def run_ai_field_extraction(ocr_payload):
    """Executes AI semantic field extraction on the normalized OCR payload.

    Args:
        ocr_payload:
            dict containing:
            "raw_text",
            "words",
            "tesseract_text",
            "rapidocr_text"

    Returns:
        dict:
        {
            "success": bool,
            "raw_ai_fields": dict,
            "provider": str,
            "error": str or None
        }
    """

    raw_text = ocr_payload.get(
        "raw_text",
        ""
    )

    if not raw_text or not raw_text.strip():

        return {
            "success": False,
            "raw_ai_fields": None,
            "provider": "none",
            "error": "Empty OCR text provided",
        }

    formatted_ocr = raw_text

    tess_text = ocr_payload.get(
        "tesseract_text",
        ""
    )

    rapid_text = ocr_payload.get(
        "rapidocr_text",
        ""
    )

    if (
        tess_text
        and rapid_text
        and tess_text != rapid_text
    ):

        formatted_ocr = (
            "=== PRIMARY OCR VIEW ===\n"
            f"{raw_text}\n\n"
            "=== TESSERACT VIEW ===\n"
            f"{tess_text}\n\n"
            "=== RAPIDOCR VIEW ===\n"
            f"{rapid_text}"
        )

    config = _get_ai_config()

    provider = config["provider"]

    if (
        not config["api_key"]
        and provider not in (
            "mock_testing",
            "none",
        )
    ):

        return {
            "success": False,
            "raw_ai_fields": None,
            "provider": "unconfigured",
            "error": (
                "No AI API key configured "
                "(AI_API_KEY or GEMINI_API_KEY)"
            ),
        }

    try:

        if provider == "gemini":

            extracted = extract_with_gemini(
                formatted_ocr,
                config
            )

        elif provider == "openai":

            extracted = extract_with_openai(
                formatted_ocr,
                config
            )

        elif provider == "mock_testing":

            mock_json_str = os.environ.get(
                "MOCK_AI_RESPONSE"
            )

            if mock_json_str:

                extracted = json.loads(
                    mock_json_str
                )

            else:

                return {
                    "success": False,
                    "raw_ai_fields": None,
                    "provider": "mock_testing",
                    "error": (
                        "No MOCK_AI_RESPONSE set"
                    ),
                }

        else:

            return {
                "success": False,
                "raw_ai_fields": None,
                "provider": "none",
                "error": (
                    "AI provider disabled "
                    "or not configured"
                ),
            }

        if not isinstance(
            extracted,
            dict
        ):

            raise ValueError(
                "AI response did not return "
                f"a JSON object: {type(extracted)}"
            )

        return {
            "success": True,
            "raw_ai_fields": extracted,
            "provider": provider,
            "error": None,
        }

    except Exception as exc:

        print(
            f"[AI Extractor] AI extraction failed "
            f"({provider}): {exc}"
        )

        return {
            "success": False,
            "raw_ai_fields": None,
            "provider": provider,
            "error": str(exc),
        }
