#!/bin/bash
# Plant Chap v2 Deployment Script
# Run this script as regular user: ./deploy.sh

set -e

echo "=== Plant Chap v2 Deployment ==="

# Variables
APP_DIR="/home/rcampbell/aquarium-tracker/aquarium-tracker"
SECRET_KEY="df1516653db7edb9236086a7e647a45a9100a70ce937c5ba8874c3e51338f1be"
DB_PASSWORD="8umQ915fFLNxvIBTi4zwRa4y"

cd "$APP_DIR"

echo "=== Setting up Python virtual environment ==="
# Create/update virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created new virtual environment"
else
    echo "Using existing virtual environment"
fi

# Activate virtual environment and install/upgrade packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Creating .env file ==="
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
DATABASE_URL=postgresql://plantchap:$DB_PASSWORD@localhost/plantchap
EOF

echo "=== Running Flask database migrations ==="
export FLASK_APP=wsgi.py
export DATABASE_URL=postgresql://plantchap:$DB_PASSWORD@localhost/plantchap

# Initialize migrations if they don't exist
if [ ! -d "migrations/versions" ] || [ -z "$(ls -A migrations/versions)" ]; then
    echo "Initializing Flask migrations..."
    flask db init || true  # Don't fail if already initialized
    flask db migrate -m "Initial migration" || true
fi

# Run migrations
flask db upgrade

echo "=== Migrating data from SQLite ==="
if [ -f "aquarium.db" ] && [ -f "migrate_from_sqlite.py" ]; then
    echo "Running SQLite to PostgreSQL migration..."
    python migrate_from_sqlite.py
else
    echo "No SQLite database found or migration script missing, skipping data migration."
fi

echo "=== Testing gunicorn startup ==="
# Test that gunicorn can start (run for 5 seconds then kill)
timeout 5s venv/bin/gunicorn --workers 1 --bind 127.0.0.1:5000 wsgi:app || echo "Gunicorn test completed"

echo "=== Starting/restarting Plant Chap service ==="
# Check if systemd service exists before trying to restart it
if systemctl list-unit-files | grep -q "plantchap.service"; then
    sudo systemctl restart plantchap
    sudo systemctl status plantchap --no-pager -l
else
    echo "Warning: plantchap.service not found. Make sure to run native-setup.sh first with sudo."
    echo "You can test manually with: venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app"
fi

echo
echo "=== Deployment Complete ==="
echo "Application should be available at:"
echo "- http://localhost (via nginx)"
echo "- http://localhost:5000 (direct to gunicorn, if nginx not configured)"
echo
echo "To check status:"
echo "- systemctl status plantchap"
echo "- systemctl status nginx"
echo "- systemctl status postgresql"
echo
echo "Logs:"
echo "- journalctl -u plantchap -f"
echo "- tail -f /var/log/nginx/access.log"
echo "- tail -f /var/log/nginx/error.log"
echo