from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .router import router
from .utils.config import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_name)
app.mount(
    "/artifacts",
    StaticFiles(directory=settings.artifacts_root),
    name="artifacts",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
async def on_startup() -> None:
    # Import lazily to avoid requiring DB packages during simple imports/tests
    try:
        from .utils.db import init_db  # noqa: WPS433
    except Exception:  # pragma: no cover - allow health to work without DB
        init_db = None

    if init_db is not None:
        await init_db()


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
