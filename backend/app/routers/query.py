import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kg_builder"))

router = APIRouter(prefix="/api", tags=["query"])


class QueryRequest(BaseModel):
    query: str
    mode: Literal["local", "global", "hybrid"] = "hybrid"


class QueryResponse(BaseModel):
    answer: str
    mode: str
    processing_time: float
    entities: list[str] = []


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """LightRAG KG에 질의"""
    try:
        from query_rag import query_once
        from app.routers.graph import extract_entities

        start = time.time()
        answer = await query_once(request.query, mode=request.mode)
        elapsed = round(time.time() - start, 2)

        entities = extract_entities(answer)

        return QueryResponse(
            answer=answer,
            mode=request.mode,
            processing_time=elapsed,
            entities=entities,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
