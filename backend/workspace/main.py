from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .routers import applications, auth, members

app = FastAPI(title="Smart Lagring API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
