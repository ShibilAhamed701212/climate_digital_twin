from fastapi import FastAPI

app = FastAPI(title="Risk Engine API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "risk-engine", "version": "1.0.0"}
