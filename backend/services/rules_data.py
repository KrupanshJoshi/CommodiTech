"""
Demo regulatory ruleset for the Commodity Compliance Scanner.

These 15 rules are loosely modeled on commodity/food labelling
requirements (e.g. India's Legal Metrology (Packaged Commodities)
Rules and FSSAI labelling requirements) for demonstration purposes
for SIH 2026. They are simplified and NOT a substitute for legal
compliance advice.

Each rule is JSON-serializable metadata; the actual pass/fail
LOGIC lives in compliance_engine.py as plain deterministic Python
functions — an LLM never decides PASS/FAIL.
"""

RULES = [
    {
        "id": "R01",
        "code": "PRODUCT_NAME_PRESENT",
        "title": "Product name declared",
        "description": "The label must clearly declare the common/generic name of the commodity.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["product_name"],
    },
    {
        "id": "R02",
        "code": "CATEGORY_PRESENT",
        "title": "Commodity category declared",
        "description": "The commodity category/type should be identifiable for classification purposes.",
        "severity": "warning",
        "weight": 5,
        "blocking": False,
        "fields": ["commodity_category"],
    },
    {
        "id": "R03",
        "code": "MANUFACTURER_NAME_PRESENT",
        "title": "Manufacturer name declared",
        "description": "Name of the manufacturer/packer/marketer must be declared on the label.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["manufacturer_name"],
    },
    {
        "id": "R04",
        "code": "MANUFACTURER_ADDRESS_PRESENT",
        "title": "Manufacturer address declared",
        "description": "Complete address of the manufacturer/packer/marketer must be declared.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["manufacturer_address"],
    },
    {
        "id": "R05",
        "code": "BATCH_NUMBER_VALID",
        "title": "Batch/Lot number present and valid",
        "description": "A batch or lot number is required for traceability and recalls.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["batch_number"],
    },
    {
        "id": "R06",
        "code": "NET_QUANTITY_VALID",
        "title": "Net quantity declared with valid unit",
        "description": "Net quantity must be declared in standard units (g/kg/ml/l/pcs etc).",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["net_quantity"],
    },
    {
        "id": "R07",
        "code": "MANUFACTURING_DATE_VALID",
        "title": "Manufacturing date present and valid",
        "description": "Date of manufacture/packing should be declared in a recognizable date format.",
        "severity": "warning",
        "weight": 5,
        "blocking": False,
        "fields": ["manufacturing_date"],
    },
    {
        "id": "R08",
        "code": "EXPIRY_OR_BEST_BEFORE_PRESENT",
        "title": "Expiry date or best-before period present",
        "description": "At least one of expiry date / best-before must be declared for consumer safety.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["expiry_date", "best_before"],
    },
    {
        "id": "R09",
        "code": "DATE_ORDER_LOGICAL",
        "title": "Manufacturing date precedes expiry date",
        "description": "When both dates are present, manufacturing date must be before the expiry date.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["manufacturing_date", "expiry_date"],
    },
    {
        "id": "R10",
        "code": "NOT_ALREADY_EXPIRED",
        "title": "Product is not already expired",
        "description": "The declared expiry date must not be earlier than the scan date.",
        "severity": "critical",
        "weight": 15,
        "blocking": True,
        "fields": ["expiry_date"],
    },
    {
        "id": "R11",
        "code": "INGREDIENTS_PRESENT",
        "title": "Ingredients list declared",
        "description": "A list of ingredients should be declared, most food/cosmetic commodities require this.",
        "severity": "warning",
        "weight": 5,
        "blocking": False,
        "fields": ["ingredients"],
    },
    {
        "id": "R12",
        "code": "LICENSE_NUMBER_VALID",
        "title": "License/registration number present and valid",
        "description": "A regulatory license or registration number (e.g. FSSAI) must be present and numeric.",
        "severity": "critical",
        "weight": 10,
        "blocking": True,
        "fields": ["license_number"],
    },
    {
        "id": "R13",
        "code": "COUNTRY_OF_ORIGIN_PRESENT",
        "title": "Country of origin declared",
        "description": "Country of origin must be declared per Legal Metrology labelling rules.",
        "severity": "warning",
        "weight": 5,
        "blocking": False,
        "fields": ["country_of_origin"],
    },
    {
        "id": "R14",
        "code": "BATCH_NUMBER_LENGTH",
        "title": "Batch number meets minimum traceability length",
        "description": "Batch/lot codes shorter than 4 characters offer weak traceability.",
        "severity": "warning",
        "weight": 3,
        "blocking": False,
        "fields": ["batch_number"],
    },
    {
        "id": "R15",
        "code": "INGREDIENTS_NOT_TRUNCATED",
        "title": "Ingredients list is not obviously truncated",
        "description": "A very short ingredients string usually indicates an incomplete OCR read or label.",
        "severity": "warning",
        "weight": 3,
        "blocking": False,
        "fields": ["ingredients"],
    },
]

RULES_BY_ID = {r["id"]: r for r in RULES}
