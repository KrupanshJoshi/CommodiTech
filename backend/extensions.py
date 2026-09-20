"""
Shared Flask extension instances.

flask_sqlalchemy / flask_cors are the intended production dependencies
(see requirements.txt). To keep this project runnable even in minimal
sandboxes where those packages have not been installed yet, we fall
back to tiny compatible shims that implement only what this project
uses. When the real packages are installed (pip install -r
requirements.txt), they are used automatically and transparently.
"""
try:
    from flask_sqlalchemy import SQLAlchemy
    HAS_REAL_SQLALCHEMY = True
except ImportError:  # pragma: no cover - exercised only without the dependency
    HAS_REAL_SQLALCHEMY = False
    from utils.sqlite_orm_shim import SQLAlchemy  # minimal fallback ORM

try:
    from flask_cors import CORS
    HAS_REAL_CORS = True
except ImportError:  # pragma: no cover - exercised only without the dependency
    HAS_REAL_CORS = False

    def CORS(app, resources=None, origins="*", supports_credentials=False, **kwargs):
        """Minimal drop-in replacement for flask_cors.CORS."""

        @app.after_request
        def _add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With, Accept"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            )
            return response

        @app.route("/api/<path:_any>", methods=["OPTIONS"])
        def _cors_preflight(_any):
            from flask import Response
            resp = Response("", status=204)
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            resp.headers["Access-Control-Max-Age"] = "86400"
            return resp


db = SQLAlchemy()
