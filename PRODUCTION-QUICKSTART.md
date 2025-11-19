# Production Deployment Quickstart

## One-Command Setup

For a fully automated production deployment with Docker, Nginx, SSL, and systemd:

```bash
sudo ./setup-production.sh
```

This script will:
1. ✅ Install Docker, Docker Compose, Nginx, and Certbot
2. ✅ Configure Docker to start on boot
3. ✅ Create and configure `.env` file with secure defaults
4. ✅ Configure UFW firewall (ports 22, 80, 443)
5. ✅ Setup Nginx as reverse proxy
6. ✅ Start Docker containers
7. ✅ Obtain SSL certificate from Let's Encrypt
8. ✅ Configure systemd service for auto-start on boot

**Domain:** retriever.sh
**SSL Email:** retriverdotsh@gmail.com

## After Setup

### 1. Update Environment Variables

The script creates a `.env` file with secure defaults, but you need to add your API keys:

```bash
nano .env
```

Update these values:
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (if using Google OAuth)
- `SES_FROM_EMAIL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (if using email)
- `POLAR_*` settings (if using Polar payments)
- Any other service credentials

### 2. Restart After Configuration

```bash
sudo systemctl restart retriever.service
```

### 3. Verify Deployment

```bash
# Check service status
sudo systemctl status retriever.service

# Check containers
docker compose ps

# View logs
docker compose logs -f

# Test the application
curl -I https://retriever.sh/health
```

## Management Commands

### Application Control

```bash
# Start
sudo systemctl start retriever.service

# Stop
sudo systemctl stop retriever.service

# Restart
sudo systemctl restart retriever.service

# Status
sudo systemctl status retriever.service

# Logs
journalctl -u retriever.service -f
```

### Updates

```bash
# Option 1: Using the update script
./update-deployment.sh

# Option 2: Using systemd
git pull
sudo systemctl reload retriever.service

# Option 3: Manual
git pull
docker compose up -d --build --force-recreate
```

### View Logs

```bash
# Application logs
docker compose logs -f

# Specific service
docker compose logs -f backend

# Nginx logs
sudo tail -f /var/log/nginx/retriever.sh_access.log
sudo tail -f /var/log/nginx/retriever.sh_error.log
```

## File Structure

```
/root/retriever.sh/
├── setup-production.sh       # Automated setup script (run this)
├── DEPLOYMENT.md             # Detailed deployment guide
├── PRODUCTION-QUICKSTART.md  # This file
├── nginx.conf               # Nginx configuration
├── retriever.service        # Systemd service file
├── docker-compose.yml       # Docker Compose configuration
├── .env                     # Environment variables (created by setup)
└── update-deployment.sh     # Update script
```

## System Services

After setup, your system will have:

- **Nginx** → Reverse proxy on ports 80/443
- **Docker** → Container runtime
- **retriever.service** → Systemd service managing Docker Compose
- **Certbot** → Auto-renews SSL certificates

## Troubleshooting

### Service won't start
```bash
sudo systemctl status retriever.service
docker compose logs
```

### SSL issues
```bash
sudo certbot renew --dry-run
sudo certbot certificates
```

### Nginx issues
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Reset everything
```bash
sudo systemctl stop retriever.service
docker compose down -v
sudo ./setup-production.sh
```

## Security Checklist

- [x] Firewall configured (UFW)
- [x] SSL certificate installed
- [x] JWT_SECRET auto-generated
- [ ] Updated `.env` with production API keys
- [ ] Changed database password (if needed)
- [ ] CORS restricted to your domain
- [ ] Regular backups enabled
- [ ] Monitoring setup

## Next Steps

1. **Configure your services** - Update `.env` with your API keys
2. **Restart** - `sudo systemctl restart retriever.service`
3. **Test** - Visit https://retriever.sh
4. **Monitor** - Setup monitoring and alerts
5. **Backup** - Configure R2 backups (optional)

For detailed documentation, see [DEPLOYMENT.md](./DEPLOYMENT.md)
