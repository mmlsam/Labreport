import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{os.path.join(app.instance_path, 'labreports.db')}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", os.path.join(app.root_path, "..", "uploads")),
        PROCESSED_FOLDER=os.environ.get("PROCESSED_FOLDER", os.path.join(app.root_path, "..", "processed")),
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,  # 32 MB uploads
        WTF_CSRF_TIME_LIMIT=None,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401
    from .routes import admin_bp, auth_bp, student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp, url_prefix="/student")

    with app.app_context():
        db.create_all()

    return app
