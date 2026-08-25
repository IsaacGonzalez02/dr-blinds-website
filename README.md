# Dr Blinds Decor & Services LLC — Website

Public marketing site + "Schedule Your Free Estimate" request form, with a simple owner-only
admin page to see and manage submitted requests.

## Running it

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env: set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
flask --app run create-admin   # creates/updates the one owner login
python run.py
```

Visit http://127.0.0.1:5000 — the site itself needs no login. Owner-only request management is at
http://127.0.0.1:5000/admin (also linked at the bottom of every page footer).

## What's here (Phase 1)

- **Public site**: Home, Services, About, Contact — built around the real Dr Blinds logo colors
  (black + gold) and the actual business contact info/Instagram.
- **Request a Free Estimate**: the core conversion form. Submissions are saved to the database and,
  if email is configured, notify the owner and confirm to the customer.
- **Admin (single login)**: view all submitted requests, filter by status (New / Contacted /
  Scheduled / Completed), add notes, and update status. This route is protected server-side — it's
  not just hidden navigation.

## Turning on email notifications (optional)

By default, requests are saved and visible in `/admin` even with no email configured — nothing is
ever lost. To also get an email when someone submits a request, fill in the `SMTP_*` and
`OWNER_NOTIFY_EMAIL` values in `.env` (any standard SMTP provider works, e.g. Gmail with an App
Password, or a transactional provider like Postmark/SendGrid's SMTP endpoint).

## Notes for whoever deploys this

- This runs on Flask's built-in dev server (`python run.py`) — fine for local use, but a real
  deployment should run it behind a production WSGI server (gunicorn/uWSGI) and a real web server
  (nginx/Caddy), and use Postgres instead of SQLite if traffic grows.
- `SECRET_KEY` and `ADMIN_PASSWORD` in `.env` are unique to this machine — generate new ones for
  any other environment (e.g. `python3 -c "import secrets; print(secrets.token_hex(24))"`).
- The logo in the header/footer is a hand-recreated SVG in the brand's black/gold palette (no image
  file was available at build time). To swap in the real logo file, drop it into
  `app/static/img/` and update the `<svg>` block in `app/templates/base.html` (and the two admin
  templates) to an `<img>` tag pointing at it.
- Uploaded estimate-request photos are saved to `app/static/uploads/` (gitignored) — back this up
  or move it to real object storage (S3, etc.) before any real deployment.

## Roadmap (not built yet, intentionally)

This is the lean, lead-generation version of the site. A separate, much larger internal operations
platform (customers, jobs, measurements, quotes, invoices, payments, Google Calendar, SMS, roles)
was scoped but deliberately deferred — see conversation history / `.claude/plans/` for that spec if
it's ever needed later.
