# Production Deployment Guide for retriever.sh

This guide covers deploying the application with native uvicorn, Docker (for databases), Nginx, SSL certificates, and systemd management.

## Architecture Overview

- **Backend**: FastAPI running via native uvicorn with `--reload` (managed by systemd)
- **Databases**: PostgreSQL and Vespa run in Docker containers
- **Frontend**: Built into backend static directory, served by FastAPI
- **Reverse Proxy**: Nginx with SSL termination

The key benefit of running uvicorn with `--reload` is that **code changes trigger automatic restart**. When you `git pull`, uvicorn detects the file changes and restarts automatically.

## Prerequisites

- Ubuntu/Debian server with root access
- Domain pointing to your server's IP address
- Docker and Docker Compose installed
- Nginx installed
- Certbot installed
- Python 3.11+ and UV installed

## Quick Setup

```bash
# 1. Install prerequisites
sudo apt update
sudo apt install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx

# 2. Install UV (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# 4. Navigate to project and configure
cd <project-dir>
cp .env.example .env
nano .env  # Edit with production values

# 5. Start database containers
docker compose up -d

# 6. Build frontend
cd frontend
npm install
npm run build
cd ..

# 7. Setup systemd service (edit paths in retriever.service first)
sudo cp retriever.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable retriever
sudo systemctl start retriever

# 8. Setup Nginx
sudo ln -sf $(pwd)/nginx.conf /etc/nginx/sites-available/retriever.sh
sudo ln -sf /etc/nginx/sites-available/retriever.sh /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# 9. Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com --agree-tos
```

## Updating Production

### Backend Code Changes Only

Because uvicorn runs with `--reload`, backend file changes trigger automatic restart:

```bash
git pull
```

That's it. Uvicorn detects the changes and restarts automatically.

### Backend Changes with New Migrations

If the update includes new Alembic migrations, you need to restart the service:

```bash
git pull
sudo systemctl restart retriever
```

Migrations run automatically on service start via `ExecStartPre`. Uvicorn's auto-reload doesn't trigger migration runs, so a manual restart is required when there are new migrations.

**How to know if there are new migrations:** Check if `backend/alembic/versions/` has new files in the pull, or run `uv run alembic current` vs `uv run alembic heads` to compare.

### Frontend Changes

Frontend changes require rebuilding the static assets:

```bash
git pull
cd frontend && npm run build
```

### Manual Migration Run (if needed)

To run migrations manually without restarting the service:

```bash
cd backend
uv run alembic upgrade head
```

## Service Management

### Systemd Commands

```bash
# Check status
sudo systemctl status retriever

# View logs (live)
sudo journalctl -u retriever -f

# View recent logs
sudo journalctl -u retriever -n 100

# Restart (only needed for .env changes or manual restart)
sudo systemctl restart retriever

# Stop
sudo systemctl stop retriever

# Start
sudo systemctl start retriever
```

### Docker Commands (Databases)

```bash
# Check container status
docker compose ps

# View database logs
docker compose logs -f db
docker compose logs -f vespa

# Restart databases (rarely needed)
docker compose restart
```

### Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload (no downtime)
sudo systemctl reload nginx

# View logs
sudo tail -f /var/log/nginx/retriever.sh_access.log
sudo tail -f /var/log/nginx/retriever.sh_error.log
```

## The retriever.service File

The systemd service file manages the uvicorn process:

```ini
[Unit]
Description=Retriever.sh Backend Service
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=<project-dir>/backend
EnvironmentFile=<project-dir>/.env
ExecStart=uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5656
Restart=always
RestartSec=5

# Wait for postgres to be ready
ExecStartPre=/bin/bash -c 'until docker exec <db-container> pg_isready -U postgres -d rag; do sleep 2; done'

# Run database migrations
ExecStartPre=uv run alembic upgrade head

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=retriever

[Install]
WantedBy=multi-user.target
```

**Note:** Replace `<project-dir>` with your absolute project path (e.g., `/root/retriever.sh`) and `<db-container>` with your postgres container name. Use absolute paths for `uv` if it's not in the system PATH.

Key points:
- `--reload` flag enables file watching for auto-restart on code changes
- First `ExecStartPre` waits for PostgreSQL to be ready
- Second `ExecStartPre` runs Alembic migrations automatically on every service start
- `Restart=always` ensures the service restarts if it crashes
- Logs go to journald (view with `journalctl -u retriever`)

## Environment Configuration

Key variables to configure in `.env`:

```bash
# Required
JWT_SECRET=your-secure-random-secret  # Generate with: openssl rand -hex 32

# URLs
FRONTEND_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com"]

# Database (matches docker-compose.yml)
DATABASE_URL=postgresql+psycopg://postgres:your-password@localhost:5432/rag

# OAuth (if using)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/google/callback

# Billing (if using Polar)
POLAR_ACCESS_TOKEN=...
POLAR_WEBHOOK_SECRET=...
POLAR_SUCCESS_URL=https://yourdomain.com/billing/success
POLAR_CANCEL_URL=https://yourdomain.com/billing
```

## Monitoring

### Health Checks

```bash
# Check if backend is responding
curl http://localhost:5656/health

# Check via Nginx (with SSL)
curl -I https://yourdomain.com/health
```

### Log Monitoring

```bash
# Application logs
sudo journalctl -u retriever -f

# Nginx access logs
sudo tail -f /var/log/nginx/retriever.sh_access.log

# Database logs
docker compose logs -f db
```

## Troubleshooting

### Backend Won't Start

```bash
# Check service status
sudo systemctl status retriever

# Check if postgres is ready
docker exec <db-container> pg_isready -U postgres -d rag

# Check port availability
sudo netstat -tlnp | grep 5656
```

### Auto-Restart Not Working

Verify uvicorn has the `--reload` flag:

```bash
systemctl cat retriever | grep ExecStart
# Should show: --reload
```

If missing, update the service file and reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart retriever
```

### SSL Certificate Issues

```bash
# Test renewal
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal

# Check certificate status
sudo certbot certificates
```

## Security Checklist

- [ ] `JWT_SECRET` set to a secure random value
- [ ] `CORS_ORIGINS` restricted to your domain only
- [ ] Database password changed from default
- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] SSL certificate installed and auto-renewing
- [ ] Regular backups configured
