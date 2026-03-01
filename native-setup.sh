#!/bin/bash
# Plant Chap v2 Native Setup Script
# Run this script with sudo: sudo ./native-setup.sh

set -e

echo "=== Plant Chap v2 Native Setup ==="
echo "This script will install PostgreSQL, nginx, and configure systemd services."
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo ./native-setup.sh)" 
   exit 1
fi

# Variables
DB_PASSWORD="8umQ915fFLNxvIBTi4zwRa4y"
APP_USER="rcampbell"
APP_DIR="/home/rcampbell/aquarium-tracker/aquarium-tracker"

# Install PostgreSQL if not already installed
echo "=== Checking PostgreSQL installation ==="
if ! command -v psql &> /dev/null; then
    echo "Installing PostgreSQL..."
    apt update
    apt install -y postgresql postgresql-contrib
    systemctl enable postgresql
    systemctl start postgresql
else
    echo "PostgreSQL is already installed."
    systemctl enable postgresql || true
    systemctl start postgresql || true
fi

# Install nginx if not already installed
echo "=== Checking nginx installation ==="
if ! command -v nginx &> /dev/null; then
    echo "Installing nginx..."
    apt install -y nginx
    systemctl enable nginx
else
    echo "nginx is already installed."
    systemctl enable nginx || true
fi

# Create PostgreSQL database and user
echo "=== Setting up PostgreSQL database ==="
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'plantchap'" | grep -q 1 || \
    sudo -u postgres createdb plantchap

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'plantchap'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER plantchap WITH PASSWORD '$DB_PASSWORD';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE plantchap TO plantchap;"
sudo -u postgres psql -c "ALTER USER plantchap CREATEDB;"

echo "Database 'plantchap' and user 'plantchap' configured."

# Create systemd service file
echo "=== Creating systemd service ==="
cat > /etc/systemd/system/plantchap.service << EOF
[Unit]
Description=Plant Chap Gunicorn
After=network.target postgresql.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration
echo "=== Creating nginx configuration ==="
cat > /etc/nginx/sites-available/plantchap << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static {
        alias $APP_DIR/app/static;
        expires 30d;
    }
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/plantchap /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Fix Docker daemon configuration (optional - don't fail if Docker not installed)
echo "=== Fixing Docker daemon configuration (if Docker is installed) ==="
if [ -d /etc/docker ]; then
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << EOF
{
    "iptables": false,
    "ip-forward": false,
    "bridge": "none",
    "storage-driver": "vfs"
}
EOF
    systemctl restart docker || echo "Note: Docker service restart failed, but continuing..."
else
    echo "Docker not installed, skipping daemon configuration."
fi

# Reload systemd and enable services
systemctl daemon-reload
systemctl enable plantchap
systemctl restart nginx

echo
echo "=== Setup Complete ==="
echo "PostgreSQL database: plantchap"
echo "PostgreSQL user: plantchap"
echo "PostgreSQL password: $DB_PASSWORD"
echo
echo "Next steps:"
echo "1. Run ./deploy.sh to set up the Python environment and start the service"
echo "2. Test the application at http://localhost or the server's IP address"
echo