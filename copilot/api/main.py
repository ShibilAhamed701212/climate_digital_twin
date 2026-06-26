from fastapi import FastAPI

app = FastAPI(title="Climate Copilot API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "copilot-agent", "version": "1.0.0"}
