import os
from datetime import datetime

import click
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    csrf.init_app(app)

    from .models import AdminUser

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    from .routes.public import public_bp
    from .routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_globals():
        return {
            "business_name": app.config["BUSINESS_NAME"],
            "business_tagline": app.config["BUSINESS_TAGLINE"],
            "business_phone": app.config["BUSINESS_PHONE"],
            "business_phone_link": app.config["BUSINESS_PHONE_LINK"],
            "business_email": app.config["BUSINESS_EMAIL"],
            "business_address": app.config["BUSINESS_ADDRESS"],
            "business_instagram_handle": app.config["BUSINESS_INSTAGRAM_HANDLE"],
            "business_instagram_url": app.config["BUSINESS_INSTAGRAM_URL"],
            "business_facebook_url": app.config["BUSINESS_FACEBOOK_URL"],
            "business_contacts": app.config["BUSINESS_CONTACTS"],
            "current_year": datetime.utcnow().year,
        }

    @app.cli.command("create-admin")
    def create_admin():
        """Seed or update the single admin user from ADMIN_EMAIL/ADMIN_PASSWORD env vars."""
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        if not email or not password:
            click.echo("Set ADMIN_EMAIL and ADMIN_PASSWORD in your environment first.")
            return
        existing = AdminUser.query.filter_by(email=email.lower()).first()
        if existing:
            existing.set_password(password)
            db.session.commit()
            click.echo(f"Updated password for existing admin: {email}")
            return
        user = AdminUser(email=email.lower(), name="Owner")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created admin user: {email}")

    return app
