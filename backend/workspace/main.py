import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .routers import activity, applications, auth, materials, members, reports, shipments

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175",
    ).split(",")
    if origin.strip()
]

app = FastAPI(title="Smart Lagring API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "Smart Lagring API is running"}


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(members.router)
app.include_router(materials.router)
app.include_router(shipments.router)
app.include_router(reports.router)
app.include_router(activity.router)
