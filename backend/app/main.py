from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import query, graph

app = FastAPI(
    title="RnD CoopGraph API",
    description="LightRAG 기반 R&D 협력 그래프 질의 시스템",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router)
app.include_router(graph.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "RnD CoopGraph API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
