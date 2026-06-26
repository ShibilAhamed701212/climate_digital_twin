from fastapi import FastAPI

app = FastAPI(title="API Gateway", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "fastapi-gateway", "version": "1.0.0"}
