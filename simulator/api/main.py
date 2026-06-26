from fastapi import FastAPI

app = FastAPI(title="Twin Core API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "twin-core", "version": "1.0.0"}
