from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False, default="Owner")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


STATUS_CHOICES = ["new", "contacted", "scheduled", "completed"]


class EstimateRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(500), nullable=False)
    preferred_date = db.Column(db.String(50), nullable=True)
    preferred_time = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="new")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PageView(db.Model):
    """A single anonymous page visit. session_id is a random id stored in a
    first-party cookie - no IP address, user agent, or other identifying
    data is stored anywhere."""

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    session_id = db.Column(db.String(36), nullable=False, index=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    utm_source = db.Column(db.String(50), nullable=True)
    referrer_host = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
