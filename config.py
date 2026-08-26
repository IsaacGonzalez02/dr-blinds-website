import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    _database_url = os.environ.get("DATABASE_URL")
    if _database_url and _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _database_url or f"sqlite:///{os.path.join(basedir, 'instance', 'dr_blinds.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = "Lax"

    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")
    GALLERY_FOLDER = os.path.join(basedir, "app", "static", "gallery")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB

    BUSINESS_NAME = "Dr Blinds Decor & Services LLC"
    BUSINESS_TAGLINE = "Improving the View of Your Surroundings"
    BUSINESS_PHONE = os.environ.get("BUSINESS_PHONE", "(954) 822-7249")
    BUSINESS_PHONE_LINK = os.environ.get("BUSINESS_PHONE_LINK", "+19548227249")
    BUSINESS_EMAIL = os.environ.get("BUSINESS_EMAIL", "drblindsdecorandservices2@gmail.com")
    BUSINESS_ADDRESS = os.environ.get(
        "BUSINESS_ADDRESS", "2719 Hollywood Blvd, Hollywood, FL 33020, United States"
    )
    BUSINESS_INSTAGRAM_HANDLE = os.environ.get("BUSINESS_INSTAGRAM_HANDLE", "drblindsdecorandservic")
    BUSINESS_INSTAGRAM_URL = os.environ.get(
        "BUSINESS_INSTAGRAM_URL", "https://www.instagram.com/drblindsdecorandservic/"
    )
    BUSINESS_FACEBOOK_URL = os.environ.get(
        "BUSINESS_FACEBOOK_URL", "https://www.facebook.com/share/18QbCsDUyt/"
    )
    BUSINESS_CONTACTS = [
        {"name": "", "role": "Immediate Care", "phone": "(954) 822-7249"},
        {"name": "Jonathan Gonzalez", "role": "Technician", "phone": "(561) 574-5503"},
        {"name": "Debora Gonzalez", "role": "Office Administration", "phone": "(954) 588-8106"},
        {"name": "Isaac Gonzalez", "role": "Kendall, FL Assistance", "phone": "(954) 549-7094"},
        {"name": "Benny Gonzalez", "role": "Hollywood, FL Assistance", "phone": "(754) 837-1195"},
        {"name": "Jana Morales", "role": "Orlando, FL Assistance", "phone": "(954) 470-4496"},
    ]

    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.environ.get(
        "RESEND_FROM_EMAIL", "Dr Blinds Decor & Services <notifications@drblindsdecorandservices.com>"
    )
    OWNER_NOTIFY_EMAIL = os.environ.get("OWNER_NOTIFY_EMAIL")
