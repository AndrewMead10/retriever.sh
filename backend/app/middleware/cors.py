from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response
from urllib.parse import urlparse

from ..config import settings


def _canonical_origin(value: str) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw == "*":
        return "*"

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _with_www_alias(origin: str) -> str | None:
    parsed = urlparse(origin)
    host = parsed.hostname
    if not host or host in {"localhost", "127.0.0.1"}:
        return None

    if host.startswith("www."):
        alias_host = host[4:]
    else:
        alias_host = f"www.{host}"

    netloc = alias_host if parsed.port is None else f"{alias_host}:{parsed.port}"
    return f"{parsed.scheme}://{netloc}"


def _expanded_cors_origins() -> list[str]:
    configured = [_canonical_origin(origin) for origin in settings.cors_origins]
    origins = [origin for origin in configured if origin]

    frontend_origin = _canonical_origin(settings.frontend_url)
    if frontend_origin:
        origins.append(frontend_origin)

    if "*" in origins:
        return ["*"]

    expanded: list[str] = []
    seen: set[str] = set()
    for origin in origins:
        if origin in seen:
            continue
        seen.add(origin)
        expanded.append(origin)

        alias = _with_www_alias(origin)
        if alias and alias not in seen:
            seen.add(alias)
            expanded.append(alias)
    return expanded


def setup_cors(app):
    """Configure CORS middleware"""
    @app.middleware("http")
    async def allow_all_preflight(request: Request, call_next):
        if request.method == "OPTIONS":
            origin = request.headers.get("origin") or "*"
            requested_headers = request.headers.get("access-control-request-headers") or "*"
            requested_method = request.headers.get("access-control-request-method") or "*"
            response = Response(status_code=204)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = requested_method
            response.headers["Access-Control-Allow-Headers"] = requested_headers
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin, Access-Control-Request-Method, Access-Control-Request-Headers"
            return response
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_expanded_cors_origins(),
        allow_origin_regex=".*",
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
