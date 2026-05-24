"""
LightRAG 질의 테스트 스크립트

실행:
    cd backend/kg_builder
    python query_rag.py

3가지 모드:
  local  - 특정 기관·기술 단건 질의 (엔티티 주변 탐색)
  global - 전체 트렌드·분야 구조 질의 (전체 KG 요약 기반)
  hybrid - 특정 기술의 기관 간 협력 구조 (두 방식 결합)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lightrag import QueryParam
from lightrag_init import get_query_rag

# ── 테스트 질의 묶음 ──────────────────────────────────────────
QUERIES = {
    "local": [
        "NPU 분야에서 한국전자통신연구원(ETRI)이 참여한 과제와 협력 기관은?",
        "PIM 기술을 연구한 대학 기관 목록과 각 대학의 주요 연구 내용은?",
    ],
    "global": [
        "2022~2025년 NPU 분야의 핵심 협력 클러스터는 어디인가?",
        "PIM 기술 분야에서 기업과 대학 간 협력 패턴은 어떠한가?",
    ],
    "hybrid": [
        "온디바이스 AI 기술에서 기업-대학-출연연 협력 구조는?",
        "국산 NPU 개발에서 산업통상자원부 지원 과제의 주요 참여 기관 네트워크는?",
    ],
}


async def run_queries() -> None:
    rag = await get_query_rag()

    for mode, questions in QUERIES.items():
        print(f"\n{'='*60}")
        print(f"[모드: {mode.upper()}]")
        print("=" * 60)

        for q in questions:
            print(f"\n질문: {q}")
            print("-" * 40)
            try:
                answer = await rag.aquery(q, param=QueryParam(mode=mode, enable_rerank=False))
                print(answer)
            except Exception as e:
                print(f"[오류] {e}")


async def query_once(question: str, mode: str = "hybrid") -> str:
    """단일 질의 (외부에서 호출용)"""
    rag = await get_query_rag()
    return await rag.aquery(question, param=QueryParam(mode=mode, enable_rerank=False))


if __name__ == "__main__":
    asyncio.run(run_queries())
