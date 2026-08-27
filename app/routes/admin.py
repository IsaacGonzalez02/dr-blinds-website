from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, Length

from .. import db
from ..models import STATUS_CHOICES, AdminUser, EstimateRequest, PageView

admin_bp = Blueprint("admin", __name__)


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired()])


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.requests_list"))

    form = LoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin.requests_list"))
        flash("Invalid email or password.", "error")

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "error")
        elif form.new_password.data != form.confirm_password.data:
            flash("New passwords don't match.", "error")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("admin.requests_list"))
    return render_template("admin/account.html", form=form)


@admin_bp.route("/")
@login_required
def requests_list():
    status_filter = request.args.get("status")
    query = EstimateRequest.query
    if status_filter in STATUS_CHOICES:
        query = query.filter_by(status=status_filter)
    requests_ = query.order_by(EstimateRequest.created_at.desc()).all()
    counts = {s: EstimateRequest.query.filter_by(status=s).count() for s in STATUS_CHOICES}
    return render_template(
        "admin/requests.html",
        requests=requests_,
        statuses=STATUS_CHOICES,
        active_status=status_filter,
        counts=counts,
        total_count=EstimateRequest.query.count(),
    )


@admin_bp.route("/requests/<int:request_id>/update", methods=["POST"])
@login_required
def update_request(request_id):
    est = EstimateRequest.query.get_or_404(request_id)
    new_status = request.form.get("status")
    notes = request.form.get("notes", "")
    if new_status in STATUS_CHOICES:
        est.status = new_status
    est.notes = notes
    db.session.commit()
    flash("Request updated.", "success")
    return redirect(url_for("admin.requests_list"))


@admin_bp.route("/analytics")
@login_required
def analytics():
    days = request.args.get("days", "30")
    days = int(days) if days.isdigit() and int(days) in (7, 30, 90) else 30
    since = datetime.utcnow() - timedelta(days=days)

    base_q = PageView.query.filter(PageView.created_at >= since)
    total_views = base_q.count()
    unique_visitors = db.session.query(func.count(func.distinct(PageView.session_id))).filter(
        PageView.created_at >= since
    ).scalar() or 0
    avg_duration = db.session.query(func.avg(PageView.duration_seconds)).filter(
        PageView.created_at >= since, PageView.duration_seconds.isnot(None)
    ).scalar()
    avg_duration = int(avg_duration) if avg_duration else 0

    top_pages = (
        db.session.query(PageView.path, func.count(PageView.id).label("views"))
        .filter(PageView.created_at >= since)
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    traffic_sources = _traffic_sources_breakdown(since)

    return render_template(
        "admin/analytics.html",
        days=days,
        total_views=total_views,
        unique_visitors=unique_visitors,
        avg_duration=avg_duration,
        top_pages=top_pages,
        traffic_sources=traffic_sources,
    )


SEARCH_HOSTS = ("google.", "bing.", "yahoo.", "duckduckgo.")
SOCIAL_HOSTS = ("instagram.", "facebook.", "tiktok.", "twitter.", "x.com", "t.co")


def _traffic_sources_breakdown(since):
    """Classify each unique visitor's first page view in the window into a
    traffic source bucket, based on the utm_source query param (used on the
    QR codes) or the browser's Referer header."""
    first_seen_subq = (
        db.session.query(
            PageView.session_id.label("session_id"),
            func.min(PageView.created_at).label("first_seen"),
        )
        .filter(PageView.created_at >= since)
        .group_by(PageView.session_id)
        .subquery()
    )
    first_rows = (
        db.session.query(PageView.utm_source, PageView.referrer_host)
        .join(
            first_seen_subq,
            db.and_(
                PageView.session_id == first_seen_subq.c.session_id,
                PageView.created_at == first_seen_subq.c.first_seen,
            ),
        )
        .all()
    )

    sources = {"QR Code": 0, "Search": 0, "Social": 0, "Referral": 0, "Direct": 0}
    for utm_source, referrer_host in first_rows:
        if utm_source and utm_source.startswith("qr"):
            sources["QR Code"] += 1
        elif referrer_host and any(h in referrer_host for h in SEARCH_HOSTS):
            sources["Search"] += 1
        elif referrer_host and any(h in referrer_host for h in SOCIAL_HOSTS):
            sources["Social"] += 1
        elif referrer_host:
            sources["Referral"] += 1
        else:
            sources["Direct"] += 1
    return sources
