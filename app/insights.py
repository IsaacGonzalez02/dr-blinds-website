"""Insights: richer, still private, analytics for the owner dashboard.

The site's tracker (static/js/insights.js) sends small batches of anonymous events to POST /api/e: page views,
time actually spent, scroll depth, Call/Text/Email taps, social clicks, gallery video plays and the estimate form.
No cookies are added, no IP address is stored, and location is only a rough guess from the browser's time zone.
The owner's own visits are skipped while they're logged in. Analytics must never break the real site, so the
collector swallows bad input and always answers fast.
"""
import hashlib, json, re, time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, make_response, render_template, request
from flask_login import current_user, login_required

from . import csrf, db
from .models import EstimateRequest

insights_bp = Blueprint("insights", __name__)
LOCAL_TZ = ZoneInfo("America/New_York")
KINDS = {"view", "time", "scroll", "click", "call", "text", "email", "outbound", "video", "form_start", "form_error", "form_submit"}
BOT = re.compile(r"bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit|pingdom|uptime|monitor|curl|wget|python|httpclient", re.I)


class InsightEvent(db.Model):
    __tablename__ = "insight_events"
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, index=True, nullable=False)  # UTC
    vid = db.Column(db.String(24), index=True)  # anonymous visitor id kept in the visitor's browser
    sid = db.Column(db.String(24), index=True)  # visit id (new after 30 min of inactivity)
    kind = db.Column(db.String(16), index=True)
    path = db.Column(db.String(200))
    label = db.Column(db.String(200))
    value = db.Column(db.Float)
    src = db.Column(db.String(40))
    device = db.Column(db.String(10))
    browser = db.Column(db.String(20))
    os = db.Column(db.String(20))
    country = db.Column(db.String(40))
    region = db.Column(db.String(48))
    lang = db.Column(db.String(12))
    new = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------- helpers
def clip(v, n):
    return (str(v) if v is not None else "")[:n] or None


def parse_ua(ua):
    ua = ua or ""
    device = "tablet" if re.search(r"iPad|Tablet|(Android(?!.*Mobile))", ua) else "mobile" if re.search(r"Mobi|iPhone|Android", ua) else "desktop"
    os_ = ("iOS" if re.search(r"iPhone|iPad|iPod", ua) else "Android" if "Android" in ua else "Windows" if "Windows" in ua
           else "macOS" if "Mac OS X" in ua else "ChromeOS" if "CrOS" in ua else "Linux" if "Linux" in ua else "Other")
    br = ("Edge" if "Edg/" in ua else "Samsung" if "SamsungBrowser" in ua else "Instagram" if "Instagram" in ua
          else "Facebook" if re.search(r"FBAN|FBAV", ua) else "TikTok" if re.search(r"musical_ly|TikTok|BytedanceWebview", ua)
          else "Chrome" if re.search(r"Chrome|CriOS", ua) else "Firefox" if re.search(r"Firefox|FxiOS", ua) else "Safari" if "Safari" in ua else "Other")
    return device, br, os_


US_ZONES = {"New_York": "Eastern", "Detroit": "Eastern", "Indiana": "Eastern", "Kentucky": "Eastern", "Chicago": "Central", "Denver": "Mountain",
            "Phoenix": "Arizona", "Los_Angeles": "Pacific", "Anchorage": "Alaska", "Boise": "Mountain", "Honolulu": "Hawaii"}
TZ_COUNTRY = {"Toronto": "Canada", "Vancouver": "Canada", "Montreal": "Canada", "Mexico_City": "Mexico", "Cancun": "Mexico", "Bogota": "Colombia",
              "Lima": "Peru", "Caracas": "Venezuela", "Santiago": "Chile", "Sao_Paulo": "Brazil", "Buenos_Aires": "Argentina", "Havana": "Cuba",
              "Puerto_Rico": "Puerto Rico", "Santo_Domingo": "Dominican Rep.", "Panama": "Panama", "Jamaica": "Jamaica", "London": "United Kingdom",
              "Madrid": "Spain", "Paris": "France", "Berlin": "Germany", "Rome": "Italy", "Lisbon": "Portugal", "Dubai": "UAE"}


def place(tz):
    """Rough location from the browser's time zone (no IP address is ever stored)."""
    if not tz or "/" not in tz:
        return "Unknown", "Unknown"
    area, city = tz.split("/", 1)
    key = city.split("/")[0]
    if area == "America" and key in US_ZONES:
        return "United States", f"US · {US_ZONES[key]}"
    if key in TZ_COUNTRY:
        return TZ_COUNTRY[key], city.replace("_", " ")
    return area, city.replace("_", " ")


NAMED = {"google": "Google", "bing": "Bing", "duckduckgo": "DuckDuckGo", "yahoo": "Yahoo", "instagram": "Instagram", "facebook": "Facebook",
         "fb.": "Facebook", "tiktok": "TikTok", "t.co": "X / Twitter", "x.com": "X / Twitter", "youtube": "YouTube", "nextdoor": "Nextdoor",
         "yelp": "Yelp", "pinterest": "Pinterest", "linkedin": "LinkedIn", "whatsapp": "WhatsApp"}


def source(ref, utm, browser):
    if utm:
        name = utm.split("|")[0]
        return "QR Code" if name.lower().startswith("qr") else clip(name.replace("-", " ").replace("_", " ").title(), 40)
    host = (urlparse(ref).hostname or "") if ref else ""
    if host and host.removeprefix("www.") != request.host.split(":")[0].removeprefix("www."):
        for k, v in NAMED.items():
            if k in host:
                return v
        return clip(host.removeprefix("www."), 40)
    if browser in ("Instagram", "Facebook", "TikTok"):
        return browser  # in-app browsers usually send no referrer
    return "Direct"


HITS = defaultdict(list)


def rate_ok(key, limit, window):
    now = time.time()
    HITS[key] = [t for t in HITS[key] if now - t < window]
    if len(HITS[key]) >= limit:
        return False
    HITS[key].append(now)
    return True


# ---------------------------------------------------------------- collector
@insights_bp.route("/api/e", methods=["POST"])
@csrf.exempt
def collect():
    try:
        ua = request.headers.get("User-Agent", "")
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
        origin = request.headers.get("Origin")
        same_site = not origin or urlparse(origin).hostname == request.host.split(":")[0]
        if current_user.is_authenticated or not same_site or BOT.search(ua) or not rate_ok(hashlib.sha256(ip.encode()).hexdigest(), 400, 600):
            return make_response("", 204)
        body = json.loads(request.get_data(as_text=True)[:60000] or "{}")
        ctx, events = body.get("c") or {}, (body.get("e") or [])[:60]
        device, br, os_ = parse_ua(ua)
        country, region = place(clip(ctx.get("tz"), 48))
        src = source(clip(ctx.get("ref"), 300), clip(ctx.get("utm"), 120), br)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        rows = []
        for ev in events:
            if ev.get("k") not in KINDS:
                continue
            ago = min(max(float(ev.get("a") or 0), 0), 86400 * 7)  # seconds since it happened (events queued while offline)
            val = ev.get("v")
            rows.append(InsightEvent(ts=now - timedelta(seconds=ago), vid=clip(ctx.get("vid"), 24), sid=clip(ctx.get("sid"), 24), kind=ev["k"],
                                     path=clip(ev.get("p") or ctx.get("p"), 200), label=clip(ev.get("l"), 200),
                                     value=float(val) if isinstance(val, (int, float)) else None, src=src, device=device, browser=br, os=os_,
                                     country=country, region=region, lang=clip(ctx.get("lang"), 12), new=bool(ctx.get("new"))))
        if rows:
            db.session.add_all(rows)
            db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.warning("Insights: collect failed (non-fatal): %s", exc)
    return make_response("", 204)


# ---------------------------------------------------------------- dashboard
@insights_bp.route("/admin/analytics")
@login_required
def dashboard():
    return render_template("admin/insights.html")


RANGES = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "all": 3650}
PAGES = [("/", "Home"), ("/services", "Services"), ("/products", "Products"), ("/gallery", "Gallery"), ("/about", "About"),
         ("/contact", "Contact"), ("/request-estimate", "Estimate form"), ("/request-estimate/confirmation", "Sent a request")]
BROWSE = {"/services", "/products", "/gallery", "/about"}


def window(rng):
    now = datetime.now(timezone.utc)
    if rng == "today":
        start = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    else:
        start = now - timedelta(days=RANGES.get(rng, 7))
    return start.replace(tzinfo=None), now.replace(tzinfo=None)


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def summarize(rows, start, end):
    sessions = defaultdict(lambda: {"views": 0, "time": 0.0, "kinds": set(), "paths": set(), "first": None})
    for r in rows:
        s = sessions[r.sid]
        if r.kind == "view":
            s["views"] += 1
            s["paths"].add(r.path)
            if s["first"] is None or r.ts < s["first"][0]:
                s["first"] = (r.ts, r.src, r.path)
        elif r.kind == "time":
            s["time"] += r.value or 0
        s["kinds"].add(r.kind)
    sess = {k: v for k, v in sessions.items() if v["views"]}
    n = len(sess)
    bounces = sum(1 for s in sess.values() if s["views"] <= 1 and s["time"] < 10 and not (s["kinds"] - {"view", "time", "scroll"}))
    requests_ = EstimateRequest.query.filter(EstimateRequest.created_at >= start, EstimateRequest.created_at <= end).count()
    return sess, {
        "visitors": len({r.vid for r in rows if r.kind == "view"}),
        "pageviews": sum(1 for r in rows if r.kind == "view"),
        "avg_time": round(sum(s["time"] for s in sess.values()) / n, 1) if n else 0,
        "bounce": pct(bounces, n),
        "requests": requests_,  # real submissions saved in the database
        "calls": sum(1 for r in rows if r.kind in ("call", "text")),
    }


@insights_bp.route("/admin/analytics/stats")
@login_required
def stats():
    rng = request.args.get("range", "7d")
    start, end = window(rng)
    rows = InsightEvent.query.filter(InsightEvent.ts >= start, InsightEvent.ts <= end).all()
    views = [r for r in rows if r.kind == "view"]
    sess, cur = summarize(rows, start, end)
    old = {}
    if rng != "all":
        prev_rows = InsightEvent.query.filter(InsightEvent.ts >= start - (end - start), InsightEvent.ts < start).all()
        _, old = summarize(prev_rows, start - (end - start), start)
    deltas = {k: (round(100 * (cur[k] - old[k]) / old[k], 1) if old.get(k) else None) for k in cur}
    to_local = lambda ts: ts.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)

    # time series: hourly for today / 24h, daily otherwise
    hourly = rng in ("today", "24h")
    fmt = "%Y-%m-%d %H:00" if hourly else "%Y-%m-%d"
    t = to_local(min((r.ts for r in rows), default=start) if rng == "all" else start).replace(minute=0, second=0, microsecond=0)
    if not hourly:
        t = t.replace(hour=0)
    keys = []
    while t <= to_local(end):
        keys.append(t.strftime(fmt))
        t += timedelta(hours=1) if hourly else timedelta(days=1)
    series = {k: {"v": set(), "pv": 0, "conv": 0} for k in keys}
    for r in rows:
        b = series.get(to_local(r.ts).strftime(fmt))
        if b is None:
            continue
        if r.kind == "view":
            b["v"].add(r.vid)
            b["pv"] += 1
        elif r.kind in ("form_submit", "call", "text", "email"):
            b["conv"] += 1

    n = len(sess)
    browsed = sum(1 for s in sess.values() if s["paths"] & BROWSE)
    opened = sum(1 for s in sess.values() if "/request-estimate" in s["paths"] or "form_start" in s["kinds"])
    sent = sum(1 for s in sess.values() if "form_submit" in s["kinds"])
    called = sum(1 for s in sess.values() if s["kinds"] & {"call", "text"})

    maxdepth = defaultdict(float)
    for r in rows:
        if r.kind == "scroll":
            maxdepth[(r.sid, r.path)] = max(maxdepth[(r.sid, r.path)], r.value or 0)
    depth = Counter("100%" if v >= 95 else "75%" if v >= 75 else "50%" if v >= 50 else "25%" if v >= 25 else "<25%" for v in maxdepth.values())
    buckets = [("< 10s", 0, 10), ("10–30s", 10, 30), ("30s–1m", 30, 60), ("1–3 min", 60, 180), ("3–10 min", 180, 600), ("10+ min", 600, 1e12)]

    def by_visitor(attr, n=8):
        g = defaultdict(set)
        for r in views:
            if getattr(r, attr) not in (None, "Unknown"):  # imported classic visits have no device/location
                g[getattr(r, attr)].add(r.vid)
        return [{"label": k or "Unknown", "n": len(v)} for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))[:n]]

    src_sess, src_act = Counter(), Counter()
    for s in sess.values():
        if s["first"]:
            src_sess[s["first"][1]] += 1
            if s["kinds"] & {"form_submit", "call", "text", "email"}:
                src_act[s["first"][1]] += 1
    pages = defaultdict(lambda: {"views": 0, "time": 0.0})
    for r in rows:
        if r.kind == "view":
            pages[r.path]["views"] += 1
        elif r.kind == "time":
            pages[r.path]["time"] += r.value or 0
    heat = [[0] * 24 for _ in range(7)]
    for r in views:
        lt = to_local(r.ts)
        heat[lt.weekday()][lt.hour] += 1
    new_vids = {r.vid for r in views if r.new}
    top = lambda c, k=8: [{"label": a or "Unknown", "n": b} for a, b in c.most_common(k)]
    live_cut = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    feed = (InsightEvent.query.filter(InsightEvent.kind.in_(["view", "call", "text", "email", "outbound", "video", "form_start", "form_error", "form_submit"]))
            .order_by(InsightEvent.ts.desc()).limit(40).all())

    return jsonify({
        "range": rng, "kpis": cur, "deltas": deltas if rng != "all" else {},
        "series": {"labels": keys, "visitors": [len(series[k]["v"]) for k in keys], "pageviews": [series[k]["pv"] for k in keys],
                   "conversions": [series[k]["conv"] for k in keys], "hourly": hourly},
        "funnel": [{"step": "Visited the site", "n": n}, {"step": "Browsed services, products or gallery", "n": browsed},
                   {"step": "Opened the estimate form", "n": opened}, {"step": "Sent an estimate request", "n": sent}],
        "called": called,
        "reach": [{"label": lab, "pct": pct(sum(1 for s in sess.values() if p in s["paths"]), n)} for p, lab in PAGES],
        "depth": [{"label": k, "n": depth[k]} for k in ("<25%", "25%", "50%", "75%", "100%")],
        "time_dist": [{"label": l, "n": sum(1 for s in sess.values() if a <= s["time"] < b)} for l, a, b in buckets],
        "sources": [{"label": k, "n": v, "conv": src_act[k]} for k, v in src_sess.most_common(10)],
        "pages": sorted(({"path": p, "views": d["views"], "avg": round(d["time"] / d["views"], 1)} for p, d in pages.items() if d["views"]),
                        key=lambda x: -x["views"])[:10],
        "devices": by_visitor("device"), "browsers": by_visitor("browser"), "os": by_visitor("os"),
        "countries": by_visitor("country", 10), "regions": by_visitor("region", 10), "langs": by_visitor("lang", 6), "heat": heat,
        "newret": {"new": len(new_vids), "returning": max(0, cur["visitors"] - len(new_vids))},
        "contact": {"calls": sum(1 for r in rows if r.kind == "call"), "texts": sum(1 for r in rows if r.kind == "text"),
                    "emails": sum(1 for r in rows if r.kind == "email"), "social": top(Counter(r.label for r in rows if r.kind == "outbound"), 6)},
        "videos": top(Counter(r.label for r in rows if r.kind == "video"), 8),
        "clicks": top(Counter(r.label for r in rows if r.kind == "click"), 10),
        "form": {"opened": opened, "started": sum(1 for s in sess.values() if "form_start" in s["kinds"]), "sent": sent,
                 "errors": sum(1 for r in rows if r.kind == "form_error"), "rate": pct(sent, opened),
                 "fields": top(Counter(f for r in rows if r.kind == "form_error" for f in (r.label or "").split(",") if f))},
        "live": len({r.vid for r in InsightEvent.query.filter(InsightEvent.ts >= live_cut).all()}),
        "feed": [{"ts": r.ts.replace(tzinfo=timezone.utc).isoformat(), "kind": r.kind, "path": r.path, "label": r.label, "region": r.region,
                  "device": r.device, "os": r.os, "src": r.src} for r in feed],
    })


# ---------------------------------------------------------------- one-time import of the classic page views
IMPORTED = "(classic)"  # label on imported page views, so the import knows it already ran


def import_classic():
    """Copy the older PageView history into the new analytics, once.

    Only visits from before the new tracker's first event are copied (the classic logger keeps running, so later
    visits would otherwise be counted twice). The old data has no device, browser or location, so those show as
    Unknown; visits are rebuilt from each visitor's cookie id with the usual 30-minute gap.
    """
    from .models import PageView

    if InsightEvent.query.filter_by(kind="view", label=IMPORTED).first():
        return 0
    first_new = db.session.query(db.func.min(InsightEvent.ts)).scalar()
    q = PageView.query
    if first_new:
        q = q.filter(PageView.created_at < first_new)
    rows, last, seen = [], {}, set()
    for pv in q.order_by(PageView.session_id, PageView.created_at).all():
        vid = (pv.session_id or "anon")[:24]
        prev = last.get(vid)
        if not prev or (pv.created_at - prev["t"]).total_seconds() > 1800:
            sid = hashlib.sha256(f"{vid}{pv.created_at.isoformat()}".encode()).hexdigest()[:24]
            utm = pv.utm_source or ""
            ref = pv.referrer_host or ""
            src = ("QR Code" if utm.lower().startswith("qr") else clip(utm.replace("-", " ").replace("_", " ").title(), 40) if utm
                   else next((v for k, v in NAMED.items() if k in ref), None) or (clip(ref.removeprefix("www."), 40) if ref else "Direct"))
            prev = last[vid] = {"sid": sid, "src": src}
        prev["t"] = pv.created_at
        base = dict(vid=vid, sid=prev["sid"], src=prev["src"], path=(pv.path or "/")[:200], device="Unknown", browser="Unknown", os="Unknown",
                    country="Unknown", region="Unknown", new=vid not in seen)
        seen.add(vid)
        rows.append(InsightEvent(ts=pv.created_at, kind="view", label=IMPORTED, **base))
        if pv.duration_seconds:
            rows.append(InsightEvent(ts=pv.created_at + timedelta(seconds=min(pv.duration_seconds, 3600)), kind="time",
                                     value=float(min(pv.duration_seconds, 3600)), **base))
    db.session.add_all(rows)
    db.session.commit()
    return sum(1 for r in rows if r.kind == "view")
