import re
import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kg_builder"))

router = APIRouter(prefix="/api", tags=["query"])

# References 섹션 제거: ## References / **References** 이하 전체 + 인라인 reference_id
_REF_SECTION = re.compile(
    r'\n*(\*\*|#{1,4}\s*)References?\**\s*\n.*',
    re.IGNORECASE | re.DOTALL,
)
_REF_INLINE = re.compile(r'[\[\(]reference_id:\s*[^\]\)]*[\]\)]', re.IGNORECASE)


def _strip_references(text: str) -> str:
    text = _REF_SECTION.sub('', text)
    text = _REF_INLINE.sub('', text)
    return text.strip()


class QueryRequest(BaseModel):
    query: str
    mode: Literal["local", "global", "hybrid"] = "hybrid"


class QueryResponse(BaseModel):
    answer: str
    mode: str
    processing_time: float
    entities: list[str] = []


async def _vdb_entity_search(query: str, top_k: int = 20) -> list[str]:
    """쿼리 임베딩으로 entity VDB를 직접 검색해 관련 노드명 반환."""
    import base64, zlib, json
    import numpy as np
    from pathlib import Path as P

    vdb_path = P(__file__).parent.parent.parent.parent / "kg_storage" / "vdb_entities.json"
    if not vdb_path.exists():
        return []

    try:
        from llm_client import local_embedding_func
        q_emb = await local_embedding_func([f"query: {query}"])
        q = q_emb[0].astype(np.float32)

        with open(vdb_path) as f:
            items = json.load(f)["data"]

        def decode(v):
            raw = zlib.decompress(base64.b64decode(v))
            return np.frombuffer(raw, dtype=np.float16).astype(np.float32)

        vectors = np.array([decode(item["vector"]) for item in items])
        sims = vectors @ q
        top_idx = np.argsort(sims)[::-1][:top_k]

        # 유사도 0.84 이상인 노드명만 반환
        return [
            items[i]["entity_name"]
            for i in top_idx
            if float(sims[i]) >= 0.84 and items[i].get("entity_name")
        ]
    except Exception:
        return []


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """LightRAG KG에 질의"""
    try:
        from query_rag import query_once
        from app.routers.graph import extract_entities

        start = time.time()
        answer = await query_once(request.query, mode=request.mode)
        elapsed = round(time.time() - start, 2)

        answer = _strip_references(answer)

        # 1차: 답변 텍스트에서 노드명 직접 매칭
        entities = extract_entities(answer + " " + request.query)

        # 2차: 매칭 결과가 적으면 VDB 유사도 검색으로 보완
        if len(entities) < 3:
            vdb_entities = await _vdb_entity_search(request.query)
            seen = set(entities)
            for e in vdb_entities:
                if e not in seen:
                    entities.append(e)
                    seen.add(e)

        return QueryResponse(
            answer=answer,
            mode=request.mode,
            processing_time=elapsed,
            entities=entities[:30],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
