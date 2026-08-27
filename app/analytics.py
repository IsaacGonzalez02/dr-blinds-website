import uuid
from urllib.parse import urlparse

from flask import g, request

from . import db
from .models import PageView

COOKIE_NAME = "dbv_id"
EXCLUDED_PREFIXES = ("/admin", "/static", "/api/")
EXCLUDED_EXACT = {"/favicon.ico", "/robots.txt", "/sitemap.xml", "/apple-touch-icon.png"}


def _should_track(path):
    if request.method != "GET":
        return False
    if path in EXCLUDED_EXACT:
        return False
    for prefix in EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return False
    return True


def register_analytics(app):
    @app.before_request
    def _track_page_view():
        g.pageview_id = None
        try:
            if not _should_track(request.path):
                return
            session_id = request.cookies.get(COOKIE_NAME) or uuid.uuid4().hex
            g.pageview_session_id = session_id

            utm_source = request.args.get("utm_source")
            referrer_host = None
            referrer = request.headers.get("Referer")
            if referrer:
                try:
                    parsed_host = urlparse(referrer).hostname
                    if parsed_host and parsed_host != request.host.split(":")[0]:
                        referrer_host = parsed_host
                except Exception:
                    referrer_host = None

            pv = PageView(
                path=request.path[:255],
                session_id=session_id,
                utm_source=(utm_source[:50] if utm_source else None),
                referrer_host=(referrer_host[:255] if referrer_host else None),
            )
            db.session.add(pv)
            db.session.commit()
            g.pageview_id = pv.id
        except Exception:
            db.session.rollback()
            app.logger.exception("Analytics: failed to record page view (non-fatal)")

    @app.after_request
    def _set_visitor_cookie(response):
        try:
            if getattr(g, "pageview_id", None) and not request.cookies.get(COOKIE_NAME):
                response.set_cookie(
                    COOKIE_NAME,
                    g.pageview_session_id,
                    max_age=60 * 60 * 24 * 365,
                    httponly=True,
                    samesite="Lax",
                )
        except Exception:
            app.logger.exception("Analytics: failed to set visitor cookie (non-fatal)")
        return response

    @app.context_processor
    def _inject_pageview_id():
        return {"pageview_id": getattr(g, "pageview_id", None)}
