# 🐠 Plant Chap

**Aquarium tracker for fishkeepers who care about their water.**

![Plant Chap](icon.png)

Track water parameters, schedule maintenance, manage fish inventory, and monitor your aquarium's health — all from a clean, mobile-friendly interface.

## Features

- **Water Parameters** — Log temperature, pH, ammonia, nitrite, nitrate with timestamps and notes
- **Charts** — Visualize parameter trends over 7/30/90 days with multi-axis Chart.js graphs
- **Scheduled Tasks** — Recurring and one-time maintenance reminders
- **Fish Inventory** — Track species with held/planned counts, auto-fetched Wikipedia thumbnails and species info
- **Maintenance Log** — Record water changes, filter cleanings, equipment checks
- **Multi-Aquarium** — Manage multiple tanks from one account
- **CSV Export** — Export parameter data for external analysis
- **PWA** — Install as a standalone app on iOS/Android from the browser
- **Slack Notifications** — Optional DMs for due/overdue tasks and new task alerts

## Screenshots

The UI features a dark ocean theme with animated bubbles, gradient accents, and a responsive layout that works great on phones.

## Tech Stack

- **Backend:** Python 3 / Flask / SQLAlchemy / PostgreSQL
- **Frontend:** Vanilla HTML/CSS/JS / Chart.js
- **Auth:** Flask-Login + bcrypt
- **Deployment:** Gunicorn + Nginx + systemd
- **PWA:** Service worker + Web App Manifest

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL

### Setup

```bash
# Clone
git clone https://github.com/rfcampbell/Waterscribe.git
cd Waterscribe

# Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your database credentials and secret key

# Database setup
createdb plantchap
flask db upgrade

# Run
flask run
```

### Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app
```

See `deploy/` directory for nginx config and systemd service file examples.

### Slack Notifications (Optional)

Add `SLACK_BOT_TOKEN` and `SLACK_NOTIFY_USER` to your `.env` to enable:
- DM notifications when scheduled tasks are created
- Periodic due/overdue task alerts via `check_tasks.py` (run via cron)

```bash
# Example crontab entry (8am, 12pm, 5pm)
0 8,12,17 * * * /path/to/venv/bin/python3 /path/to/check_tasks.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `FLASK_ENV` | No | `development` or `production` |
| `SESSION_COOKIE_SECURE` | No | Set `true` for HTTPS |
| `SLACK_BOT_TOKEN` | No | Slack bot token for notifications |
| `SLACK_NOTIFY_USER` | No | Slack user ID for DM notifications |

## License

MIT
