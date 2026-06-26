from fastapi import FastAPI

app = FastAPI(title="Scenario Engine API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "scenario-engine", "version": "1.0.0"}
