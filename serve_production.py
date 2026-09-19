"""
Production Server Runner for Commodity Compliance Scanner.
Serves both the React frontend (compiled SPA) and Flask REST API from a single entrypoint.

Usage:
    # Direct execution (automatic frontend check, multi-threaded):
    python serve_production.py

    # Force rebuild of frontend before starting:
    python serve_production.py --build

    # Specify host and port:
    python serve_production.py --port 8080 --host 0.0.0.0

    # Or run via Gunicorn (Linux / Container):
    gunicorn -w 4 -b 0.0.0.0:5000 serve_production:app
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from flask import send_from_directory, abort

# Set up paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

logger = logging.getLogger("prod_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def ensure_frontend_build(force_build: bool = False):
    """Ensures the frontend is compiled into frontend/dist. Runs npm run build if needed."""
    index_html = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_html) and not force_build:
        return

    logger.info("Frontend distribution directory missing or rebuild requested.")
    npm_path = shutil.which("npm")
    if not npm_path:
        raise RuntimeError("npm was not found on PATH. Please install Node.js and npm.")

    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.exists(node_modules):
        logger.info("Installing frontend dependencies (npm install)...")
        subprocess.run([npm_path, "install"], cwd=FRONTEND_DIR, check=True)

    logger.info("Building frontend production bundle (npm run build)...")
    subprocess.run([npm_path, "run", "build"], cwd=FRONTEND_DIR, check=True)
    logger.info("Frontend build complete: %s", DIST_DIR)


def create_production_app():
    """Initializes Flask app and mounts the SPA / static frontend catch-all handler."""
    from app import create_app

    flask_app = create_app(os.environ.get("FLASK_CONFIG", "default"))

    @flask_app.route("/", defaults={"path": ""})
    @flask_app.route("/<path:path>")
    def serve_frontend(path):
        # Do not intercept unmatched /api routes with HTML
        if path.startswith("api/") or path == "api":
            abort(404)

        # Serve static assets (js, css, images, svgs) if file exists
        target_file = os.path.join(DIST_DIR, path)
        if path and os.path.exists(target_file) and os.path.isfile(target_file):
            return send_from_directory(DIST_DIR, path)

        # Serve index.html for client-side routing (React Router)
        index_file = os.path.join(DIST_DIR, "index.html")
        if os.path.exists(index_file):
            return send_from_directory(DIST_DIR, "index.html")

        return (
            "Frontend build not found. Run 'npm run build' inside frontend/ or run with --build.",
            500,
        )

    return flask_app


def get_app(force_build: bool = False):
    """Builds frontend if needed and returns the production Flask application."""
    ensure_frontend_build(force_build=force_build)
    return create_production_app()


# Expose `app` at module-level for WSGI servers (Gunicorn, uWSGI, etc.)
try:
    app = get_app(force_build=False)
except Exception as _exc:
    # Allows CLI flags to handle build if not already pre-built
    app = None


def main():
    parser = argparse.ArgumentParser(description="Commodity Compliance Scanner - Production Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5000")), help="Port to bind (default: 5000)")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"), help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--build", action="store_true", help="Force rebuild frontend before starting")
    args = parser.parse_args()

    global app
    if app is None or args.build:
        app = get_app(force_build=args.build)

    logger.info("=" * 60)
    logger.info("Commodity Compliance Scanner — Production Server")
    logger.info(f"Serving API and UI at: http://{args.host}:{args.port}")
    logger.info(f"Frontend Static Directory: {DIST_DIR}")
    logger.info("=" * 60)

    # Check if a dedicated production WSGI server is installed
    try:
        import waitress
        logger.info("Using Waitress production WSGI server.")
        waitress.serve(app, host=args.host, port=args.port)
        return
    except ImportError:
        pass

    logger.info("Running multi-threaded server. (Tip: pip install gunicorn or waitress for heavy production loads)")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
