"""
Entry point for the Commodity Compliance Scanner backend.

Usage:
    python run.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_CONFIG", "default"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = app.config.get("DEBUG", False)
    print(f"Commodity Compliance Scanner API starting on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
