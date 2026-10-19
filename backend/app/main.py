from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.meetings import router as meetings_router
from app.api.recordings import router as recordings_router
from app.core.settings import settings

app = FastAPI(title="AI Meeting Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings_router)
app.include_router(recordings_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
