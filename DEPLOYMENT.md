# Plant Chap v2 Native Deployment Guide

This document covers the native deployment of Plant Chap v2 on Ubuntu without Docker.

## Quick Start

The deployment is handled by two scripts:

1. **`native-setup.sh`** - Requires sudo, handles system-level setup
2. **`deploy.sh`** - Regular user, handles application setup

### Step 1: System Setup (Run Once)

```bash
sudo ./native-setup.sh
```

This script will:
- Install PostgreSQL and nginx (if not already installed)
- Create PostgreSQL database `plantchap` and user `plantchap`
- Create systemd service file `/etc/systemd/system/plantchap.service`
- Configure nginx reverse proxy in `/etc/nginx/sites-available/plantchap`
- Fix Docker daemon.json to prevent crash-loops (if Docker is installed)

### Step 2: Application Deployment

```bash
./deploy.sh
```

This script will:
- Set up Python virtual environment with all dependencies
- Create `.env` file with proper PostgreSQL connection
- Run Flask database migrations
- Import existing SQLite data (if `aquarium.db` exists)
- Test gunicorn startup
- Start/restart the systemd service

## Accessing the Application

After successful deployment:

- **Main URL**: http://localhost (via nginx)
- **Direct**: http://localhost:5000 (directly to gunicorn)

## Database Configuration

- **Database**: `plantchap`
- **User**: `plantchap`
- **Password**: `8umQ915fFLNxvIBTi4zwRa4y` (auto-generated)
- **Connection**: PostgreSQL on localhost:5432

## Service Management

```bash
# Check service status
systemctl status plantchap
systemctl status nginx
systemctl status postgresql

# Restart services
sudo systemctl restart plantchap
sudo systemctl restart nginx

# View logs
journalctl -u plantchap -f
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## File Structure

```
/home/rcampbell/aquarium-tracker/aquarium-tracker/
├── native-setup.sh     # System setup script (requires sudo)
├── deploy.sh          # Application deployment script
├── wsgi.py           # WSGI entry point for gunicorn
├── .env              # Environment configuration
├── venv/             # Python virtual environment
├── migrations/       # Flask-Migrate database versions
└── app/             # Application code
```

## Environment Variables

The `.env` file contains:

```bash
SECRET_KEY=df1516653db7edb9236086a7e647a45a9100a70ce937c5ba8874c3e51338f1be
FLASK_ENV=production
DATABASE_URL=postgresql://plantchap:8umQ915fFLNxvIBTi4zwRa4y@localhost/plantchap
```

## Data Migration

If you have existing data in `aquarium.db` (SQLite), it will be automatically migrated to PostgreSQL when running `./deploy.sh`.

The migration creates a default user:
- **Email**: admin@plantchap.local  
- **Password**: plantchap123 (change this!)

## Troubleshooting

### Port 5000 in use
If you get "Connection in use: ('127.0.0.1', 5000)", kill any existing processes:
```bash
pkill -f "python.*app\.py"
# or
lsof -i :5000
kill <PID>
```

### PostgreSQL connection issues
Check if PostgreSQL is running:
```bash
sudo systemctl status postgresql
pg_isready
```

### Nginx configuration issues
Test nginx configuration:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Flask migration issues
Reset migrations if needed:
```bash
cd /home/rcampbell/aquarium-tracker/aquarium-tracker
source venv/bin/activate
export FLASK_APP=wsgi.py
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Security Notes

- Change the default user password after first login
- The PostgreSQL password is auto-generated but stored in plain text in scripts
- Consider setting up SSL/HTTPS for production use
- The SECRET_KEY is auto-generated and suitable for production

## Architecture

```
[nginx :80] → [gunicorn :5000] → [Flask App] → [PostgreSQL :5432]
        ↓
   [systemd service]
```

- **nginx**: Reverse proxy, serves static files
- **gunicorn**: WSGI server with 3 workers  
- **systemd**: Service management and auto-restart
- **PostgreSQL**: Database backend