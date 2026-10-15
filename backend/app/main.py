from fastapi import FastAPI

app = FastAPI(title="AI Meeting Agent API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
