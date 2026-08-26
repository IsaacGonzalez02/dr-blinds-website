from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, Length

from .. import db
from ..models import STATUS_CHOICES, AdminUser, EstimateRequest

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
