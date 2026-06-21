import asyncio
import faulthandler
import fcntl
import signal
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import get_db_session
from .functions.backups import cleanup_expired_tokens, daily_backup_loop
from .functions.plan_seeding import seed_plans
from .logging_config import setup_logfire
from .middleware.cors import setup_cors
from .middleware.errors import global_exception_handler
from .pages import billing, connect, management_keys, projects, rag_api
from .pages.auth import google, login, logout, register, reset, utils, verify_email

_background_lock_file = None

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
    logfire.instrument_fastapi(
        app,
        excluded_urls=["/livez", "/readyz"]
    )

# Mount all API routes under a common /api prefix to avoid
# collisions with SPA client-side routes like /auth/* when
# running the frontend dev server or refreshing deep links.
app.include_router(login.router, prefix="/api")
app.include_router(register.router, prefix="/api")
app.include_router(utils.router, prefix="/api")
app.include_router(logout.router, prefix="/api")
app.include_router(reset.router, prefix="/api")
app.include_router(verify_email.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(management_keys.router, prefix="/api")
app.include_router(rag_api.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(google.router, prefix="/api")
app.include_router(connect.router, prefix="/api/connect")


@app.get("/livez")
def livez():
    """Liveness check"""
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    """Readiness check"""
    try:
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready",
        )


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


@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    with get_db_session() as db:
        seed_plans(db)

    try:
        faulthandler.register(signal.SIGUSR1, all_threads=True)
    except RuntimeError:
        pass

    if _claim_background_task_lock():
        if settings.enable_backups:
            asyncio.create_task(daily_backup_loop())

        asyncio.create_task(cleanup_expired_tokens())


def _claim_background_task_lock() -> bool:
    global _background_lock_file

    lock_path = Path("/tmp/retriever-background-tasks.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return False

    _background_lock_file = lock_file
    return True
