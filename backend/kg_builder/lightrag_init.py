"""
LightRAG 인스턴스 초기화

인덱싱용 / 질의용을 분리해 모델 교체:
  get_index_rag() → Flash (크레딧 절약, 엔티티 추출)
  get_query_rag() → Sonnet (고품질 멀티홉 추론)

두 인스턴스는 같은 working_dir를 공유 → KG 재사용
"""

import os
from dotenv import load_dotenv
from lightrag import LightRAG

from ntis_prompts import patch_ntis_prompts
from llm_client import index_llm_func, query_llm_func, embedding_func

load_dotenv()

WORKING_DIR = os.path.join(os.path.dirname(__file__), "../../kg_storage")
USE_NEO4J = bool(os.getenv("NEO4J_URI"))


async def _make_rag(llm_func) -> LightRAG:
    os.makedirs(WORKING_DIR, exist_ok=True)
    patch_ntis_prompts()

    kwargs = dict(
        working_dir=WORKING_DIR,
        llm_model_func=llm_func,
        embedding_func=embedding_func,
        llm_model_max_async=1,   # Gemini 무료 분당 15회 한도 → 순차 처리로 초과 방지
    )
    if USE_NEO4J:
        kwargs["graph_storage"] = "Neo4JStorage"
        print(f"[LightRAG] Neo4j: {os.getenv('NEO4J_URI')}")
    else:
        print("[LightRAG] 로컬 파일 스토리지 (Neo4j 미설정)")

    rag = LightRAG(**kwargs)
    await rag.initialize_storages()
    return rag


async def get_index_rag() -> LightRAG:
    """인덱싱용: Flash 모델 — 엔티티·관계 추출"""
    return await _make_rag(index_llm_func)


async def get_query_rag() -> LightRAG:
    """질의용: Sonnet 모델 — 멀티홉 추론 답변 생성"""
    return await _make_rag(query_llm_func)
