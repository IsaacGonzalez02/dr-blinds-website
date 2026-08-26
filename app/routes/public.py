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
    {"category": "blinds", "name": "Wood Blinds", "description": "Warm, natural wood slats for a classic, upscale look in any room.", "photo": "blinds.jpg", "tint_clip": None},
    {"category": "blinds", "name": "Faux Wood Blinds", "description": "Durable, moisture-resistant slats that mimic real wood — ideal for kitchens and baths.", "photo": "blinds-faux.jpg", "tint_clip": None},
    {"category": "blinds", "name": "Vertical Blinds", "description": "Practical coverage for sliding doors and large windows.", "photo": "blinds-vertical.jpg", "tint_clip": None},
    {"category": "blinds", "name": "Mini Blinds", "description": "Slim aluminum slats for precise light control at a great value.", "photo": "blinds-mini.jpg", "tint_clip": None},
    {"category": "shades", "name": "Roller Shades", "description": "Clean, modern shades that roll up flush against the window.", "photo": "shades.jpg", "tint_clip": "polygon(5.5% 25.5%, 83% 25.5%, 83% 49.5%, 5.5% 49.5%)"},
    {"category": "shades", "name": "Cellular (Honeycomb) Shades", "description": "Energy-efficient shades that trap air for better insulation.", "photo": "shades-cellular.jpg", "tint_clip": "inset(0% 18% 8% 15%)"},
    {"category": "shades", "name": "Roman Shades", "description": "Soft fabric folds that add texture and warmth to a room.", "photo": "shades-roman.jpg", "tint_clip": "inset(22% 5% 34% 9%)"},
    {"category": "shades", "name": "Solar Shades", "description": "Block UV and glare while preserving your outdoor view.", "photo": "shades-solar.jpg", "tint_clip": "inset(24% 0% 4% 0%)"},
    {"category": "curtains", "name": "Sheer Curtains", "description": "Light, airy fabric that softens a room while letting daylight through.", "photo": "curtains.jpg", "tint_clip": "polygon(7% 13%, 78% 13%, 78% 88%, 7% 88%)"},
    {"category": "curtains", "name": "Blackout Curtains", "description": "Heavy fabric panels for total light and privacy control — perfect for bedrooms.", "photo": "curtains-blackout.jpg", "tint_clip": "inset(0% 0% 10% 0%)"},
    {"category": "curtains", "name": "Drapery Panels", "description": "Floor-length panels that add a tailored, elevated finish to any space.", "photo": "curtains-drapery.jpg", "tint_clip": "inset(15% 0% 0% 40%)"},
    {"category": "motorized", "name": "Motorized Roller Shades", "description": "Raise and lower your shades with a remote or app — no cords required.", "photo": "motorized.jpg", "tint_clip": "polygon(42% 0%, 100% 0%, 100% 30%, 42% 30%)"},
    {"category": "motorized", "name": "Motorized Cellular Shades", "description": "Smart insulating shades you can schedule and control from your phone.", "photo": "motorized-cellular.jpg", "tint_clip": None},
    {"category": "motorized", "name": "Smart Blinds", "description": "App and voice-control-ready blinds for a fully automated home.", "photo": "motorized-smart.jpg", "tint_clip": "inset(8% 10% 15% 15%)"},
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


@public_bp.route("/products")
def products():
    return render_template("products.html", products=PRODUCTS, colors=PRODUCT_COLORS)


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
