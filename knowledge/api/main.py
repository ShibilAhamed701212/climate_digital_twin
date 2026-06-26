from fastapi import FastAPI

app = FastAPI(title="RAG Knowledge API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "rag-service", "version": "1.0.0"}
