from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure

# Load backend/.env by path, so it is found no matter where or how the server is started.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .database import get_client
from .routers import (
    activity,
    announcements,
    applications,
    auth,
    damage_reports,
    materials,
    members,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if get_client.cache_info().currsize:
        get_client().close()


app = FastAPI(title="Smart Lagring API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # Any port on this machine, so the frontend dev server can run wherever it is started.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ConnectionFailure)
async def database_unavailable(_: Request, __: ConnectionFailure) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Could not connect to MongoDB"})


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "Smart Lagring API is running"}


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(members.router)
app.include_router(damage_reports.router)
app.include_router(materials.router)
app.include_router(announcements.router)
app.include_router(activity.router)
