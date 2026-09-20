import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from config import CONFIG_MAP
from extensions import db, CORS


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP.get(config_name, CONFIG_MAP["default"]))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)
    if app.config.get("DATABASE_DIR"):
        os.makedirs(app.config["DATABASE_DIR"], exist_ok=True)

    # The production Docker image serves the SPA and API from one origin, so
    # CORS is only needed for a separately hosted frontend or Vite development.
    # Keep it scoped to the API and use an environment-controlled allowlist.
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=86400,
    )
    db.init_app(app)

    # Import models so they are registered with the ORM before create_all()
    from models import User, Scan, Report  # noqa: F401

    with app.app_context():
        db.create_all()
        # Auto-migrate columns only for the legacy SQLite database.
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            try:
                with db.engine.connect() as conn:
                    res = conn.execute(db.text("PRAGMA table_info(scans)"))
                    existing_cols = {row[1] for row in res.fetchall()}
                    if "image_quality_score" not in existing_cols:
                        conn.execute(db.text("ALTER TABLE scans ADD COLUMN image_quality_score INTEGER"))
                    if "image_quality_status" not in existing_cols:
                        conn.execute(db.text("ALTER TABLE scans ADD COLUMN image_quality_status VARCHAR(30)"))
                    conn.commit()
            except Exception as mig_err:
                app.logger.warning(f"Schema migration check: {mig_err}")

    from services.ocr_service import configure_tesseract
    configure_tesseract(app.config.get("TESSERACT_CMD"))

    register_blueprints(app)
    register_error_handlers(app)

    return app


def register_blueprints(app):
    from routes.auth import auth_bp
    from routes.scans import scans_bp
    from routes.ocr import ocr_bp
    from routes.compliance import compliance_bp
    from routes.reports import reports_bp
    from routes.dashboard import dashboard_bp
    from routes.rules import rules_bp
    from routes.settings import settings_bp
    from routes.health import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(scans_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rules_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(health_bp)


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "error": "Bad request", "detail": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Resource not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"success": False, "error": "Uploaded file is too large"}), 413

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "error": "Method not allowed"}), 405

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({"success": False, "error": e.name, "detail": e.description}), e.code

    @app.errorhandler(Exception)
    def handle_unexpected(e):  # pragma: no cover - safety net
        app.logger.exception("Unhandled exception")
        return jsonify({"success": False, "error": "Internal server error"}), 500
