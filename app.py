from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, bcrypt, ensure_schema_updates
import os

load_dotenv()

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="statics",
        static_url_path="/static",
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://127.0.0.1:5500",
                    "http://localhost:5500",
                    "http://127.0.0.1:3000",
                    "http://localhost:3000",
                ]
            }
        },
        supports_credentials=False,
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    )

    db.init_app(app)
    bcrypt.init_app(app)
    JWTManager(app)

    from routes.auth import auth_bp
    from routes.splits import splits_bp
    from routes.logs import logs_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(splits_bp, url_prefix="/api/splits")
    app.register_blueprint(logs_bp, url_prefix="/api/logs")

    # Frontend page routes for template-based serving.
    @app.route("/")
    @app.route("/index")
    @app.route("/index.html")
    def index_page():
        return render_template("index.html")

    @app.route("/dashboard")
    @app.route("/dashboard.html")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.route("/splits")
    @app.route("/splits.html")
    def splits_page():
        return render_template("splits.html")

    @app.route("/analytics")
    @app.route("/analytics.html")
    def analytics_page():
        return render_template("analytics.html")

    @app.route("/profile")
    @app.route("/profile.html")
    def profile_page():
        return render_template("profile.html")

    @app.route("/settings")
    @app.route("/settings.html")
    def settings_page():
        return render_template("settings.html")

    @app.route("/about")
    @app.route("/about.html")
    def about_page():
        return render_template("about.html")

    @app.route("/terms")
    @app.route("/terms.html")
    def terms_page():
        return render_template("terms.html")

    @app.route("/privacy")
    @app.route("/privacy.html")
    def privacy_page():
        return render_template("privacy.html")

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        ensure_schema_updates()
    app.run(debug=True)
