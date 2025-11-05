from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
import asyncio

from .middleware.cors import setup_cors
from .middleware.errors import global_exception_handler
from .pages.auth import login, register, logout, reset, google, utils
from .pages import billing, projects, rag_api, connect
from .functions.backups import daily_backup_loop, cleanup_expired_tokens
from .functions.plan_seeding import seed_plans
from .database import get_db_session
from .config import settings
from .logging_config import setup_logfire

app = FastAPI(
    title="Retriever.sh",
    description="Cheap, easy to use hybrid search engine",
    version="1.0.0"
)

# Setup LogFire first
setup_logfire()

setup_cors(app)

app.add_exception_handler(Exception, global_exception_handler)

# Instrument FastAPI with LogFire
if settings.logfire_enabled:
    import logfire
    logfire.instrument_fastapi(app)

# Mount all API routes under a common /api prefix to avoid
# collisions with SPA client-side routes like /auth/* when
# running the frontend dev server or refreshing deep links.
app.include_router(login.router, prefix="/api")
app.include_router(register.router, prefix="/api")
app.include_router(utils.router, prefix="/api")
app.include_router(logout.router, prefix="/api")
app.include_router(reset.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(rag_api.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(google.router, prefix="/api")
app.include_router(connect.router, prefix="/api/connect")


class SPAStaticFiles(StaticFiles):
    """Static files handler with SPA fallback to index.html.

    If a static file is not found and the request accepts HTML, return index.html
    so the client-side router can handle deep links like /auth/login.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:  # type: ignore
            if exc.status_code != 404:
                raise

            # Only fallback for GET/HEAD requests that accept HTML
            method = scope.get("method", "GET")
            accepts_html = False
            for k, v in scope.get("headers", []):
                if k == b"accept" and b"text/html" in v:
                    accepts_html = True
                    break

            if method in ("GET", "HEAD") and accepts_html:
                return await super().get_response("index.html", scope)

            raise

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="static")


@app.get("/livez")
def livez():
    """Liveness check"""
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    """Readiness check"""
    try:
        with get_db_session() as db:
            db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    with get_db_session() as db:
        seed_plans(db)

    if settings.enable_backups:
        asyncio.create_task(daily_backup_loop())
    
    asyncio.create_task(cleanup_expired_tokens())
