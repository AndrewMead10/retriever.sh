# Production Deployment Guide for retriever.sh

This guide covers deploying the application with Docker, Nginx, SSL certificates, and systemd management.

## Prerequisites

- Ubuntu/Debian server with root access
- Domain `retriever.sh` pointing to your server's IP address
- Docker and Docker Compose installed
- Nginx installed
- Certbot installed

## Quick Setup Commands

If you just want to get started quickly, run these commands in order:

```bash
# 1. Install prerequisites
sudo apt update
sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

# 2. Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# 3. Navigate to project directory
cd /root/retriever.sh

# 4. Configure environment
cp .env.example .env
nano .env  # Edit with your production values

# 5. Setup Nginx
sudo ln -s /root/retriever.sh/nginx.conf /etc/nginx/sites-available/retriever.sh
sudo ln -s /etc/nginx/sites-available/retriever.sh /etc/nginx/sites-enabled/
sudo nginx -t

# 6. Get SSL certificate (interactive)
sudo certbot --nginx -d retriever.sh -d www.retriever.sh -m retriverdotsh@gmail.com --agree-tos

# 7. Setup systemd service
sudo cp retriever.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable retriever.service
sudo systemctl start retriever.service

# 8. Start Nginx
sudo systemctl restart nginx
```

## Detailed Setup Instructions

### 1. Install Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl start docker

# Install Nginx
sudo apt install -y nginx

# Install Certbot for SSL certificates
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Configure Environment Variables

```bash
cd /root/retriever.sh

# Copy example environment file
cp .env.example .env

# Edit with your production values
nano .env
```

**Important environment variables to configure:**

```bash
# REQUIRED: Generate a secure JWT secret
JWT_SECRET=$(openssl rand -hex 32)

# Frontend URL (your domain)
FRONTEND_URL=https://retriever.sh

# CORS (restrict in production)
CORS_ORIGINS=["https://retriever.sh", "https://www.retriever.sh"]

# Google OAuth (if using)
GOOGLE_REDIRECT_URI=https://retriever.sh/api/auth/google/callback

# Polar URLs (if using)
POLAR_SUCCESS_URL=https://retriever.sh/billing/success
POLAR_CANCEL_URL=https://retriever.sh/billing
POLAR_PORTAL_RETURN_URL=https://retriever.sh/billing

# Email configuration (if using SES)
SES_FROM_EMAIL=noreply@retriever.sh

# Database (default is fine for docker-compose)
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/rag
```

### 3. Setup Nginx Configuration

```bash
# Create symlink to Nginx sites-available
sudo ln -s /root/retriever.sh/nginx.conf /etc/nginx/sites-available/retriever.sh

# Enable the site
sudo ln -s /etc/nginx/sites-available/retriever.sh /etc/nginx/sites-enabled/

# Remove default site if it exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t
```

### 4. Obtain SSL Certificate

Before running this, make sure:
- Your domain `retriever.sh` points to your server's IP
- Port 80 is open in your firewall
- Nginx is running

```bash
# Ensure Nginx is running
sudo systemctl start nginx

# Get SSL certificate (follow prompts)
sudo certbot --nginx \
  -d retriever.sh \
  -d www.retriever.sh \
  -m retriverdotsh@gmail.com \
  --agree-tos \
  --no-eff-email

# Test auto-renewal
sudo certbot renew --dry-run
```

### 5. Setup Systemd Service

```bash
# Copy service file to systemd directory
sudo cp retriever.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable retriever.service

# Start the service
sudo systemctl start retriever.service

# Check status
sudo systemctl status retriever.service
```

### 6. Start and Verify Services

```bash
# Restart Nginx with SSL configuration
sudo systemctl restart nginx

# Verify Nginx is running
sudo systemctl status nginx

# Check Docker containers are running
docker compose ps

# View logs
docker compose logs -f
```

## Management Commands

### Systemd Service Management

```bash
# Start the application
sudo systemctl start retriever.service

# Stop the application
sudo systemctl stop retriever.service

# Restart the application
sudo systemctl restart retriever.service

# Reload (pull latest images and recreate)
sudo systemctl reload retriever.service

# View status
sudo systemctl status retriever.service

# View logs
journalctl -u retriever.service -f
```

### Docker Commands

```bash
# View running containers
docker compose ps

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f backend

# Rebuild containers
docker compose build --no-cache

# Update deployment (use existing script)
./update-deployment.sh
```

### Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload configuration (no downtime)
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx

# View logs
sudo tail -f /var/log/nginx/retriever.sh_access.log
sudo tail -f /var/log/nginx/retriever.sh_error.log
```

## Updating the Application

### Option 1: Using the update script

```bash
cd /root/retriever.sh

# Quick update (uses Docker cache)
./update-deployment.sh

# Full rebuild
./update-deployment.sh --full-rebuild
```

### Option 2: Using systemd

```bash
# Pull latest code
cd /root/retriever.sh
git pull

# Reload the service (rebuilds and restarts)
sudo systemctl reload retriever.service
```

### Option 3: Manual update

```bash
cd /root/retriever.sh

# Pull latest code
git pull

# Pull latest images
docker compose pull

# Rebuild and restart
docker compose up -d --build --force-recreate
```

## Database Backups

The application includes automatic backup functionality. Backups are stored in the PostgreSQL container volume.

### Enable R2 Backups (Optional)

Edit `.env`:

```bash
ENABLE_R2_BACKUP=true
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET=retriever-backups
```

Then restart the service:

```bash
sudo systemctl restart retriever.service
```

## Monitoring

### Check Application Health

```bash
# Check if the application is responding
curl -I https://retriever.sh/health

# Check if backend is running
curl -I http://localhost:5656/health
```

### View Docker Resource Usage

```bash
docker stats
```

### View Logs

```bash
# Application logs
docker compose logs -f

# Nginx access logs
sudo tail -f /var/log/nginx/retriever.sh_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/retriever.sh_error.log

# Systemd service logs
journalctl -u retriever.service -f
```

## Firewall Configuration

Make sure these ports are open:

```bash
# Allow HTTP (for Certbot renewal)
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow SSH (if not already allowed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

## Troubleshooting

### Application won't start

```bash
# Check service status
sudo systemctl status retriever.service

# Check Docker logs
docker compose logs

# Verify .env configuration
cat .env

# Check if ports are available
sudo netstat -tlnp | grep 5656
```

### SSL Certificate Issues

```bash
# Test certificate renewal
sudo certbot renew --dry-run

# Force certificate renewal
sudo certbot renew --force-renewal

# Check certificate status
sudo certbot certificates
```

### Nginx Issues

```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Verify site is enabled
ls -la /etc/nginx/sites-enabled/
```

### Database Issues

```bash
# Access database container
docker compose exec db psql -U postgres -d rag

# Check database logs
docker compose logs db

# Reset database (CAUTION: This deletes all data)
docker compose down -v
docker compose up -d
```

## Security Checklist

- [ ] Changed `JWT_SECRET` to a secure random value
- [ ] Updated `CORS_ORIGINS` to only allow your domain
- [ ] Configured firewall (ufw) to only allow necessary ports
- [ ] SSL certificate is installed and auto-renewing
- [ ] Changed default database password in production
- [ ] Configured proper logging
- [ ] Set up monitoring/alerting
- [ ] Regular backups enabled
- [ ] Kept system and Docker images updated

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Certbot Documentation](https://certbot.eff.org/)
- [Systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

## Support

For issues specific to this deployment, check:
- Application logs: `docker compose logs -f`
- Systemd logs: `journalctl -u retriever.service -f`
- Nginx logs: `/var/log/nginx/retriever.sh_*.log`
