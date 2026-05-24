"""
LLM 클라이언트 (OpenAI 호환 엔드포인트) + 한국어 로컬 임베딩

구성:
  LLM      → .env의 GATEWAY_URL + API_KEY 기반 (OpenAI 호환)
  임베딩   → 로컬 한국어 모델 intfloat/multilingual-e5-large

.env 설정 예시는 .env.example 참고
"""

import asyncio
import os
import re
from typing import Literal

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError, InternalServerError
from pydantic import BaseModel, field_validator
from sentence_transformers import SentenceTransformer
from lightrag.utils import EmbeddingFunc

load_dotenv()

# ── 게이트웨이 설정 ────────────────────────────────────────────
# GATEWAY_URL 미설정 시 OpenAI 기본값 사용
_gateway = AsyncOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("GATEWAY_URL"),
    max_retries=0,   # 내부 재시도 비활성화 → _call_gateway에서 직접 제어
)

INDEX_MODEL = os.getenv("INDEX_MODEL", "gemini-2.0-flash")   # 인덱싱: Flash (저렴)
QUERY_MODEL = os.getenv("QUERY_MODEL", "gemini-2.0-flash")   # 질의: .env로 고품질 모델 교체 가능


# ── Pydantic 기반 엔티티 타입 교정 ────────────────────────────
NtisType = Literal["기관", "기술분야", "과제", "연구자", "부처"]

# 영어 타입 → NTIS 기본 매핑
_EN_TO_NTIS: dict[str, NtisType] = {
    "person":       "연구자",
    "concept":      "기술분야",
    "artifact":     "기술분야",
    "category":     "기술분야",
    "product":      "기술분야",
    "method":       "기술분야",
    "technology":   "기술분야",
    "equipment":    "기술분야",
    "data":         "기술분야",
    "organization": "기관",
    "institution":  "기관",
    "event":        "기관",
    "location":     "기관",
    "other":        "기관",
    "unknown":      "기관",
}

# 이름에 포함 시 "부처"로 오버라이드
_MINISTRY_KEYWORDS = [
    "과학기술정보통신부", "산업통상자원부", "중소벤처기업부",
    "기획재정부", "교육부", "국방부", "고용노동부", "보건복지부",
    "환경부", "국토교통부", "해양수산부", "농림축산식품부",
    "문화체육관광부", "외교부", "법무부", "행정안전부", "과학기술부",
]
_MINISTRY_SUFFIX = re.compile(r"(부|청|처|위원회)$")
_PROJECT_PATTERN = re.compile(r"^\d{10,13}$")


class NtisEntity(BaseModel):
    """LightRAG entity 한 줄을 파싱 & 타입 교정하는 Pydantic 모델"""
    name:        str
    entity_type: str
    description: str

    @field_validator("entity_type", mode="before")
    @classmethod
    def fix_entity_type(cls, v: str, info) -> NtisType:
        v = (v or "").strip().lower()

        # 이미 NTIS 5종이면 그대로
        if v in {"기관", "기술분야", "과제", "연구자", "부처"}:
            return v

        # 영어 → 기본 NTIS 매핑
        base_type: NtisType = _EN_TO_NTIS.get(v, "기술분야")

        # 이름 기반 오버라이드 (organization → 기관 vs 부처 구분)
        name = (info.data.get("name") or "")
        if base_type == "기관":
            if any(kw in name for kw in _MINISTRY_KEYWORDS) or \
               _MINISTRY_SUFFIX.search(name):
                return "부처"
            if _PROJECT_PATTERN.match(name.replace(" ", "")):
                return "과제"

        return base_type


# entity 한 줄 파싱 패턴
_ENTITY_LINE = re.compile(
    r"^entity\<\|#\|\>(.+?)\<\|#\|\>(.+?)\<\|#\|\>(.+)$",
    re.MULTILINE,
)

def _fix_entity_types_in_response(response: str) -> str:
    """
    LightRAG LLM 응답에서 entity 라인의 타입을 Pydantic으로 검증·교정.
    형식: entity<|#|>이름<|#|>타입<|#|>설명
    """
    def fix_line(m: re.Match) -> str:
        name, etype, desc = m.group(1), m.group(2), m.group(3)
        try:
            corrected = NtisEntity(
                name=name, entity_type=etype, description=desc
            )
            if corrected.entity_type != etype.strip().lower():
                return f"entity<|#|>{name}<|#|>{corrected.entity_type}<|#|>{desc}"
        except Exception:
            pass
        return m.group(0)

    return _ENTITY_LINE.sub(fix_line, response)


_RATE_LIMIT_WAITS = [10, 30, 60]  # Groq: 짧게 / Gemini: 길게 필요 시 60초까지


async def _call_gateway(prompt: str, system_prompt: str | None, model: str) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # 429 시 최대 3회 재시도 (10→30→60초)
    # Groq 분당 30 RPM: 10초면 충분 / Gemini 분당 15 RPM: 30~60초 필요
    # 대기 합계 최대 100초 < LightRAG 함수 타임아웃(180초)
    for attempt in range(4):
        try:
            resp = await _gateway.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=8192,
            )
            content = resp.choices[0].message.content
            # Pydantic 기반 entity_type 교정 (영어 → NTIS 한국어 5종)
            return _fix_entity_types_in_response(content)
        except RateLimitError as e:
            err_str = str(e)
            # 일일 한도 소진(PerDay quota, limit:0) → 재시도 무의미, 즉시 종료
            if "PerDay" in err_str and "limit: 0" in err_str:
                print(f"[Rate Limit] 일일 한도 소진 — 재시도 중단. 내일 자정(UTC) 이후 재실행하세요.")
                raise
            if "spending cap" in err_str or "monthly spending" in err_str:
                print(f"[Rate Limit] 월 지출 한도 초과 — 재시도 중단. AI Studio에서 한도를 올려주세요.")
                raise
            if attempt == 3:
                raise
            wait = _RATE_LIMIT_WAITS[attempt]
            print(f"[Rate Limit] {wait}초 대기 후 재시도 ({attempt+1}/3)... | {e}")
            await asyncio.sleep(wait)
        except InternalServerError as e:
            # 503 서버 과부하 → 재시도
            if attempt == 3:
                raise
            wait = _RATE_LIMIT_WAITS[attempt]
            print(f"[503 과부하] {wait}초 대기 후 재시도 ({attempt+1}/3)... | {e}")
            await asyncio.sleep(wait)


async def index_llm_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list = [],
    **kwargs,
) -> str:
    """인덱싱 단계 LLM: Flash 모델 사용 (크레딧 절약)"""
    return await _call_gateway(prompt, system_prompt, INDEX_MODEL)


async def query_llm_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list = [],
    **kwargs,
) -> str:
    """질의 단계 LLM: Sonnet 모델 사용 (멀티홉 추론 고품질)"""
    return await _call_gateway(prompt, system_prompt, QUERY_MODEL)


# ── 한국어 로컬 임베딩 ─────────────────────────────────────────
# 최초 실행 시 모델 자동 다운로드 (~500MB), 이후 캐시 사용
_embed_model: SentenceTransformer | None = None
EMBED_DIM = 1024


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        print("[임베딩] 한국어 모델 로딩 중... (최초 1회만)")
        _embed_model = SentenceTransformer("intfloat/multilingual-e5-large")
    return _embed_model


async def local_embedding_func(texts: list[str]) -> np.ndarray:
    model = _get_embed_model()
    # multilingual-e5는 passage: 접두사 사용 시 검색 성능 향상
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False),
    )
    return np.array(embeddings, dtype=np.float32)


embedding_func = EmbeddingFunc(
    embedding_dim=EMBED_DIM,
    max_token_size=512,
    func=local_embedding_func,
)


# ── 사용 가능 모델 조회 ────────────────────────────────────────
async def list_models() -> None:
    models = await _gateway.models.list()
    print("\n사용 가능한 모델 목록:")
    for m in models.data:
        print(f"  {m.id}")


if __name__ == "__main__":
    asyncio.run(list_models())
