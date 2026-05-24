"""
processed_data/ 의 txt 파일을 읽어 LightRAG에 삽입·인덱싱

실행:
    cd backend/kg_builder
    python insert_docs.py [--topic NPU|PIM|all]

각 txt 파일에는 여러 과제/논문/특허가 ====...==== 로 구분되어 있음.
하나씩 분리해 개별 삽입 → 엔티티 추출 품질 향상.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 같은 패키지 내 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))
from lightrag_init import get_index_rag

DATA_DIR = Path(__file__).parent.parent.parent / "processed_data"
SEPARATOR = "=" * 60

# 반도체/AI 도메인 키워드 — 하나라도 있으면 관련 문서로 판단
_DOMAIN_KEYWORDS = [
    "반도체", "메모리", "NPU", "PIM", "GPU", "CPU", "SoC", "칩",
    "온디바이스", "인공지능", "딥러닝", "뉴럴", "추론", "학습",
    "양자화", "경량화", "가속기", "프로세서", "회로", "소자",
    "컴퓨팅", "아키텍처", "임베디드", "엣지", "DRAM", "SRAM",
]

def _is_relevant(text: str) -> bool:
    """반도체/AI 무관 문서(예: 생의학 특허) 필터링"""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in _DOMAIN_KEYWORDS)


def load_documents(topic: str) -> list[tuple[str, str]]:
    """
    Returns:
        list of (source_label, document_text)
        source_label : 어떤 파일에서 왔는지 (KG 품질 점검용)
    """
    docs = []

    if topic == "all":
        search_dirs = [DATA_DIR / "NPU", DATA_DIR / "PIM"]
    else:
        search_dirs = [DATA_DIR / topic.upper()]

    for d in search_dirs:
        if not d.exists():
            print(f"[경고] 폴더 없음: {d}")
            continue
        # project → rpaper → patent 순서로 처리 (과제 파일이 텍스트 풍부)
        def sort_key(p):
            if "project" in p.name: return 0
            if "rpaper" in p.name: return 1
            return 2

        for txt_file in sorted(d.glob("*.txt"), key=sort_key):
            raw = txt_file.read_text(encoding="utf-8")
            chunks = [c.strip() for c in raw.split(SEPARATOR) if c.strip()]
            for chunk in chunks:
                if _is_relevant(chunk):
                    docs.append((txt_file.name, chunk))

    return docs


async def insert_all(topic: str = "all", limit: int | None = None) -> None:
    rag = await get_index_rag()
    docs = load_documents(topic)

    if not docs:
        print("[오류] 삽입할 문서가 없습니다. processed_data 경로를 확인하세요.")
        return

    if limit:
        docs = docs[:limit]

    total = len(docs)
    print(f"\n총 {total}개 문서 삽입 시작 (토픽: {topic})\n")

    failed = []
    for i, (label, text) in enumerate(docs, 1):
        preview = text[:40].replace(chr(10), ' ').encode('cp949', errors='replace').decode('cp949')
        print(f"[{i:>3}/{total}] {label} | {preview}...")
        try:
            await rag.ainsert(text)
        except Exception as e:
            print(f"  [실패] {e}")
            failed.append((label, str(e)))

    print(f"\n완료: 성공 {total - len(failed)}개 / 실패 {len(failed)}개")
    if failed:
        print("실패 목록:")
        for label, err in failed:
            print(f"  - {label}: {err}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic",
        choices=["NPU", "PIM", "all"],
        default="all",
        help="삽입할 토픽 선택 (기본값: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="삽입할 문서 수 제한 (예: --limit 10)",
    )
    args = parser.parse_args()
    asyncio.run(insert_all(args.topic, args.limit))
