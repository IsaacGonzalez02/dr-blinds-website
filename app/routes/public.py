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


PRODUCT_COLORS = [
    {"name": "Pure White", "hex": "#f7f5f0"},
    {"name": "Ivory", "hex": "#ede4d1"},
    {"name": "Natural Linen", "hex": "#d8cbb3"},
    {"name": "Warm Greige", "hex": "#b7a891"},
    {"name": "Taupe", "hex": "#9c8b76"},
    {"name": "Espresso", "hex": "#4a3324"},
    {"name": "Charcoal", "hex": "#3f3b36"},
    {"name": "Navy", "hex": "#2b3b52"},
]

PRODUCTS = [
    {"category": "blinds", "name": "Wood Blinds", "description": "Warm, natural wood slats for a classic, upscale look in any room."},
    {"category": "blinds", "name": "Faux Wood Blinds", "description": "Durable, moisture-resistant slats that mimic real wood — ideal for kitchens and baths."},
    {"category": "blinds", "name": "Vertical Blinds", "description": "Practical coverage for sliding doors and large windows."},
    {"category": "blinds", "name": "Mini Blinds", "description": "Slim aluminum slats for precise light control at a great value."},
    {"category": "shades", "name": "Roller Shades", "description": "Clean, modern shades that roll up flush against the window."},
    {"category": "shades", "name": "Cellular (Honeycomb) Shades", "description": "Energy-efficient shades that trap air for better insulation."},
    {"category": "shades", "name": "Roman Shades", "description": "Soft fabric folds that add texture and warmth to a room."},
    {"category": "shades", "name": "Solar Shades", "description": "Block UV and glare while preserving your outdoor view."},
    {"category": "curtains", "name": "Sheer Curtains", "description": "Light, airy fabric that softens a room while letting daylight through."},
    {"category": "curtains", "name": "Blackout Curtains", "description": "Heavy fabric panels for total light and privacy control — perfect for bedrooms."},
    {"category": "curtains", "name": "Drapery Panels", "description": "Floor-length panels that add a tailored, elevated finish to any space."},
    {"category": "motorized", "name": "Motorized Roller Shades", "description": "Raise and lower your shades with a remote or app — no cords required."},
    {"category": "motorized", "name": "Motorized Cellular Shades", "description": "Smart insulating shades you can schedule and control from your phone."},
    {"category": "motorized", "name": "Smart Blinds", "description": "App and voice-control-ready blinds for a fully automated home."},
]


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


CATEGORY_PHOTOS = {
    "blinds": "blinds.jpg",
    "shades": "shades.jpg",
    "curtains": "curtains.jpg",
    "motorized": "motorized.jpg",
}


@public_bp.route("/products")
def products():
    return render_template(
        "products.html", products=PRODUCTS, colors=PRODUCT_COLORS, category_photos=CATEGORY_PHOTOS
    )


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
