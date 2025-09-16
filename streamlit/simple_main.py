from fastapi import FastAPI

app = FastAPI(title="RAG System - Minimal")

@app.get("/")
async def root():
    return {"message": "RAG System API - Working!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)