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
        from flask import request

        if resources:
            resource_options = next(iter(resources.values()))
            origins = resource_options.get("origins", origins)
        allowed_origins = {origins} if isinstance(origins, str) else set(origins)
        max_age = kwargs.get("max_age")

        @app.after_request
        def _add_cors_headers(response):
            # A browser accepts one origin here, never a comma-separated list.
            origin = request.headers.get("Origin")
            if not request.path.startswith("/api/") or not origin:
                return response
            if "*" not in allowed_origins and origin not in allowed_origins:
                return response

            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers.add("Vary", "Origin")
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            if supports_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            if max_age is not None:
                response.headers["Access-Control-Max-Age"] = str(max_age)
            return response


db = SQLAlchemy()
