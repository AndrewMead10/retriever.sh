#!/bin/bash

# Production Setup Script for retriever.sh
# This script automates the deployment setup with native uvicorn, Docker (databases), Nginx, and SSL

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="retriever.sh"
EMAIL="retriverdotsh@gmail.com"
PROJECT_DIR="/root/retriever.sh"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Retriever.sh Production Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Architecture:"
echo "  - Backend: Native uvicorn with --reload (systemd)"
echo "  - Databases: PostgreSQL + Vespa (Docker)"
echo "  - Frontend: Built into backend static directory"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Step 1: Install prerequisites
echo -e "${YELLOW}[1/9] Installing prerequisites...${NC}"
apt update
apt install -y nginx certbot python3-certbot-nginx ufw docker.io docker-compose-v2 nodejs npm

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Step 2: Enable Docker
echo -e "${YELLOW}[2/9] Enabling Docker...${NC}"
systemctl enable docker
systemctl start docker
echo -e "${GREEN}Docker is ready${NC}"

# Step 3: Configure environment
echo -e "${YELLOW}[3/9] Configuring environment...${NC}"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}Created .env file from template${NC}"

    # Generate secure JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s|JWT_SECRET=change-me-in-production|JWT_SECRET=$JWT_SECRET|g" .env

    # Update URLs for production
    sed -i "s|FRONTEND_URL=http://localhost:3000|FRONTEND_URL=https://$DOMAIN|g" .env
    sed -i "s|CORS_ORIGINS=\[\"\*\"\]|CORS_ORIGINS=[\"https://$DOMAIN\", \"https://www.$DOMAIN\"]|g" .env
    sed -i "s|GOOGLE_REDIRECT_URI=http://localhost:5656/api/auth/google/callback|GOOGLE_REDIRECT_URI=https://$DOMAIN/api/auth/google/callback|g" .env
    sed -i "s|POLAR_SUCCESS_URL=http://localhost:3000/billing/success|POLAR_SUCCESS_URL=https://$DOMAIN/billing/success|g" .env
    sed -i "s|POLAR_CANCEL_URL=http://localhost:3000/billing|POLAR_CANCEL_URL=https://$DOMAIN/billing|g" .env
    sed -i "s|POLAR_PORTAL_RETURN_URL=http://localhost:3000/billing|POLAR_PORTAL_RETURN_URL=https://$DOMAIN/billing|g" .env

    echo -e "${GREEN}Generated secure JWT_SECRET and updated production URLs${NC}"
    echo -e "${YELLOW}IMPORTANT: Review and update .env with your specific values (API keys, etc.)${NC}"
else
    echo -e "${YELLOW}.env file already exists, skipping...${NC}"
fi

# Step 4: Configure firewall
echo -e "${YELLOW}[4/9] Configuring firewall...${NC}"
ufw --force enable
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
echo -e "${GREEN}Firewall configured${NC}"

# Step 5: Start database containers
echo -e "${YELLOW}[5/9] Starting database containers (PostgreSQL + Vespa)...${NC}"
cd "$PROJECT_DIR"
docker compose up -d
echo -e "${GREEN}Database containers started${NC}"

# Wait for postgres to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
until docker exec retrieversh-db-1 pg_isready -U postgres -d rag 2>/dev/null; do
    sleep 2
done
echo -e "${GREEN}PostgreSQL is ready${NC}"

# Step 6: Build frontend
echo -e "${YELLOW}[6/9] Building frontend...${NC}"
cd "$PROJECT_DIR/frontend"
npm install
npm run build
cd "$PROJECT_DIR"
echo -e "${GREEN}Frontend built into backend static directory${NC}"

# Step 7: Setup Nginx (before SSL)
echo -e "${YELLOW}[7/9] Setting up Nginx...${NC}"

# Create temporary HTTP-only config for Certbot
TEMP_NGINX_CONFIG="/etc/nginx/sites-available/retriever.sh.temp"
cat > "$TEMP_NGINX_CONFIG" << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:5656;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Link temporary config
ln -sf "$TEMP_NGINX_CONFIG" /etc/nginx/sites-enabled/retriever.sh

# Test and reload Nginx
nginx -t
systemctl restart nginx
echo -e "${GREEN}Nginx configured with temporary HTTP config${NC}"

# Step 8: Setup systemd service for uvicorn
echo -e "${YELLOW}[8/9] Setting up systemd service...${NC}"
cp "$PROJECT_DIR/retriever.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable retriever.service
systemctl start retriever.service
echo -e "${GREEN}Systemd service configured and started${NC}"

# Wait for backend to be ready
echo -e "${YELLOW}Waiting for backend to start...${NC}"
sleep 5
until curl -s http://127.0.0.1:5656/health > /dev/null 2>&1; do
    sleep 2
done
echo -e "${GREEN}Backend is ready${NC}"

# Step 9: Obtain SSL certificate
echo -e "${YELLOW}[9/9] Obtaining SSL certificate...${NC}"
certbot --nginx \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    -m "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    --redirect

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SSL certificate obtained successfully${NC}"

    # Now replace with the full production Nginx config
    ln -sf "$PROJECT_DIR/nginx.conf" /etc/nginx/sites-available/retriever.sh
    nginx -t && systemctl reload nginx
    echo -e "${GREEN}Updated to production Nginx configuration${NC}"
else
    echo -e "${RED}Failed to obtain SSL certificate${NC}"
    echo -e "${YELLOW}You may need to run this manually:${NC}"
    echo "sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN -m $EMAIL --agree-tos"
fi

# Final status check
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Service Status:${NC}"
systemctl status retriever.service --no-pager -l | head -15

echo ""
echo -e "${GREEN}Docker Containers:${NC}"
docker compose ps

echo ""
echo -e "${GREEN}How Updates Work:${NC}"
echo "  Backend runs uvicorn with --reload flag."
echo "  When you 'git pull', uvicorn auto-restarts."
echo ""
echo "  For backend changes:  git pull"
echo "  For frontend changes: git pull && cd frontend && npm run build"
echo ""
echo -e "${GREEN}Management Commands:${NC}"
echo "  sudo systemctl status retriever    - Check status"
echo "  sudo journalctl -u retriever -f    - View logs"
echo "  sudo systemctl restart retriever   - Manual restart (rarely needed)"
echo ""
echo -e "${GREEN}Access your application:${NC}"
echo "  https://$DOMAIN"
echo ""
echo -e "${YELLOW}Don't forget to:${NC}"
echo "  - Update .env with your actual API keys and secrets"
echo "  - Configure Google OAuth credentials if needed"
echo "  - Configure Polar payment settings if needed"
echo ""
