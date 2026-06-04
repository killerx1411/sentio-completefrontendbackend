from flask import Flask, jsonify
from flask_cors import CORS
from config import get_config
from db.connection import init_db
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    config = get_config()
    app.config.from_object(config)

    CORS(
        app,
        origins=config.CORS_ORIGINS,
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
    )

    from routes.auth_routes import auth_bp
    from routes.role_routes import role_bp
    from routes.audit_routes import audit_bp
    from routes.user_routes import user_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    if config.DATABASE_URL:
        init_db()
    else:
        logger.warning("DATABASE_URL is not set. Database connection test skipped.")

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "service": "Sentio Auth API"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
