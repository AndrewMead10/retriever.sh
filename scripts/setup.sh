#!/bin/bash

# Service Template Setup Script

set -e

echo "🚀 Setting up Service Template..."

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Aborting." >&2; exit 1; }

# Setup environment
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing!"
    echo "   Especially set JWT_SECRET to a secure random string."
    echo ""
fi

# Backend setup
echo "🐍 Setting up backend..."
cd backend

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    pip install uv
fi

echo "Installing Python dependencies..."
uv sync

echo "Setting up database..."
if uv run alembic upgrade head; then
    echo "✅ Database ready"
else
    echo "❌ Failed to run database migrations. Ensure PostgreSQL is running and DATABASE_URL is correct."
    exit 1
fi

cd ..

# Frontend setup
echo "⚛️  Setting up frontend..."
cd frontend

echo "Installing Node.js dependencies..."
npm install

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔧 Development commands:"
echo "   Backend:  cd backend && uv run uvicorn app.main:app --reload"
echo "   Frontend: cd frontend && npm run dev"
echo ""
echo "🚀 Deployment (no Docker):"
echo "   cd frontend && npm run build"
echo "   cd ../backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5656"
echo ""
echo "📖 See CLAUDE.md for detailed documentation"
