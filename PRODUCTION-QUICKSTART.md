# Production Deployment Quickstart

## Architecture

- **Backend**: Native uvicorn with `--reload` (managed by systemd)
- **Databases**: PostgreSQL + Vespa in Docker
- **Frontend**: Built into backend static directory

The `--reload` flag means **backend auto-restarts when files change**. Just `git pull` to deploy backend updates.

## Quick Setup

```bash
# 1. Start database containers
docker compose up -d

# 2. Build frontend
cd frontend && npm install && npm run build && cd ..

# 3. Install systemd service
sudo cp retriever.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable retriever
sudo systemctl start retriever
```

## Updating Production

### Backend Code Only

```bash
git pull
# That's it - uvicorn auto-restarts
```

### Backend + New Migrations

```bash
git pull
sudo systemctl restart retriever
# Migrations run automatically on service start
```

### Frontend Changes

```bash
git pull
cd frontend && npm run build
```

## Common Commands

```bash
# Status & logs
sudo systemctl status retriever
sudo journalctl -u retriever -f

# Restart (only if needed)
sudo systemctl restart retriever

# Database containers
docker compose ps
docker compose logs -f db
```

## Files

```
retriever.service    # Systemd service (uvicorn with --reload)
docker-compose.yml   # PostgreSQL + Vespa containers
nginx.conf           # Reverse proxy config
.env                 # Environment variables
```

## Troubleshooting

**Auto-restart not working?** Check for `--reload` flag:
```bash
systemctl cat retriever | grep ExecStart
```

**Backend won't start?** Check postgres is ready:
```bash
docker exec <db-container> pg_isready -U postgres -d rag
```

For detailed docs, see [DEPLOYMENT.md](./DEPLOYMENT.md)
