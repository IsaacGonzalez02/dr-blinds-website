import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from werkzeug.utils import secure_filename
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

from .. import db
from ..email import confirm_customer_request, notify_owner_new_request
from ..models import EstimateRequest

public_bp = Blueprint("public", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
GALLERY_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
GALLERY_VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}


def _gallery_items():
    folder = current_app.config["GALLERY_FOLDER"]
    if not os.path.isdir(folder):
        return []

    items = []
    for name in os.listdir(folder):
        if name.startswith("."):
            continue
        full_path = os.path.join(folder, name)
        if not os.path.isfile(full_path):
            continue
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in GALLERY_IMAGE_EXTENSIONS and ext not in GALLERY_VIDEO_EXTENSIONS:
            continue
        base = name.rsplit(".", 1)[0]
        title = base.replace("-", " ").replace("_", " ").strip().title()
        is_video = ext in GALLERY_VIDEO_EXTENSIONS
        poster_filename = None
        if is_video:
            candidate = os.path.join(folder, "posters", base + ".jpg")
            if os.path.isfile(candidate):
                poster_filename = f"posters/{base}.jpg"
        items.append(
            {
                "filename": name,
                "title": title or "Dr Blinds Project",
                "type": "video" if is_video else "image",
                "poster": poster_filename,
                "mtime": os.path.getmtime(full_path),
            }
        )
    items.sort(key=lambda item: item["mtime"], reverse=True)
    return items


class EstimateRequestForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=255)])
    phone = StringField("Phone Number", validators=[DataRequired(), Length(max=50)])
    email = StringField("Email (optional)", validators=[Optional(), Email(), Length(max=255)])
    address = StringField("Property Address", validators=[DataRequired(), Length(max=500)])
    preferred_date = StringField("Preferred Date", validators=[Optional(), Length(max=50)])
    preferred_time = StringField("Preferred Time", validators=[Optional(), Length(max=50)])
    description = TextAreaField(
        "Tell us about your project", validators=[Optional(), Length(max=4000)]
    )
    photo = FileField(
        "Photo (optional)",
        validators=[FileAllowed(list(ALLOWED_EXTENSIONS), "Images only (png, jpg, webp).")],
    )


@public_bp.route("/")
def home():
    return render_template("home.html")


@public_bp.route("/services")
def services():
    return render_template("services.html")


@public_bp.route("/about")
def about():
    return render_template("about.html")


@public_bp.route("/contact")
def contact():
    return render_template("contact.html")


@public_bp.route("/gallery")
def gallery():
    return render_template("gallery.html", items=_gallery_items())


@public_bp.route("/request-estimate", methods=["GET", "POST"])
def request_estimate():
    form = EstimateRequestForm()
    if form.validate_on_submit():
        photo_filename = None
        photo = form.photo.data
        if photo and getattr(photo, "filename", ""):
            ext = photo.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXTENSIONS:
                stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                photo_filename = f"{stamp}_{secure_filename(photo.filename)}"
                photo.save(os.path.join(current_app.config["UPLOAD_FOLDER"], photo_filename))

        est = EstimateRequest(
            name=form.name.data.strip(),
            phone=form.phone.data.strip(),
            email=(form.email.data or "").strip() or None,
            address=form.address.data.strip(),
            preferred_date=(form.preferred_date.data or "").strip() or None,
            preferred_time=(form.preferred_time.data or "").strip() or None,
            description=(form.description.data or "").strip() or None,
            photo_filename=photo_filename,
        )
        try:
            db.session.add(est)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed to save estimate request")
            flash("We couldn't submit your request. Please try again or call us directly.", "error")
            return render_template("request_estimate.html", form=form)

        notify_owner_new_request(est)
        if est.email:
            confirm_customer_request(est)

        return redirect(url_for("public.request_confirmation"))

    return render_template("request_estimate.html", form=form)


@public_bp.route("/request-estimate/confirmation")
def request_confirmation():
    return render_template("request_confirmation.html")
