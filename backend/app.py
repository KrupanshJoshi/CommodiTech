import os
from flask import Flask, jsonify, request
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

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    db.init_app(app)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            return response

    # Import models so they are registered with the ORM before create_all()
    from models import User, Scan, Report  # noqa: F401

    with app.app_context():
        db.create_all()
        # Auto-migrate SQLite schema for newly added columns
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

        # Seed default inspector demo account if not exists
        try:
            demo_user = User.query.filter_by(email="inspector@fssai.gov.in").first()
            if not demo_user:
                demo_user = User(
                    full_name="Senior Inspector Ramesh Rao",
                    email="inspector@fssai.gov.in",
                    organization="Legal Metrology Division",
                    role="inspector",
                )
                demo_user.set_password("demo123456")
                db.session.add(demo_user)
                db.session.commit()
                app.logger.info("Seeded default demo inspector: inspector@fssai.gov.in")
        except Exception as seed_err:
            app.logger.warning(f"Demo user seed check: {seed_err}")

    from services.ocr_service import configure_tesseract
    configure_tesseract(app.config.get("TESSERACT_CMD"))

    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/")
    def index():
        return jsonify({
            "success": True,
            "status": "online",
            "service": "Commodity Compliance Scanner Backend API",
            "endpoints": "/api"
        }), 200

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
