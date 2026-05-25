"""
LightRAG 프롬프트 NTIS 도메인 설정

- DEFAULT_ENTITY_TYPES: NTIS 도메인 타입으로 교체
- entity_extraction_examples: 기본 예시 3개를 모두 NTIS 예시로 교체
  (기본 예시의 엔티티가 KG에 오염 노드로 삽입되는 버그 방지)

사용법:
    from ntis_prompts import patch_ntis_prompts
    patch_ntis_prompts()  # LightRAG 초기화 전에 호출
"""

from lightrag.prompt import PROMPTS

NTIS_ENTITY_TYPES = ["기관", "기술분야", "과제", "연구자", "부처"]

# ── 예시 1: PIM 과제 (산학 협력, 복수 기관) ──────────────────────────────
_EXAMPLE_1 = """<Entity_types>
["기관","기술분야","과제","연구자","부처"]

<Input Text>
```
과제번호: 2210000156
과제명: 저전력 고성능 PIM 아키텍처 설계 및 DRAM 기반 연산 가속 연구
주관기관: 삼성전자
참여기관: 서울대학교, 한국전자통신연구원
주무부처: 산업통상자원부
연구책임자: 김민준
연도: 2022
정부출연금: 32억원
키워드: PIM,DRAM,메모리 내 연산,저전력,딥러닝 가속기

[연구목표]
DRAM 내부에 연산 유닛을 통합한 Processing-In-Memory 아키텍처를 설계하고
딥러닝 추론 워크로드에서 데이터 이동 비용을 최소화하는 저전력 가속 기법 개발
```

<Output>
entity{tuple_delimiter}삼성전자{tuple_delimiter}기관{tuple_delimiter}과제 2210000156의 주관기관으로 PIM 아키텍처 설계 및 DRAM 기반 연산 가속 연구를 총괄하는 대기업 반도체 기업.
entity{tuple_delimiter}서울대학교{tuple_delimiter}기관{tuple_delimiter}과제 2210000156에 참여하는 대학 기관으로 PIM 아키텍처 이론 연구 및 알고리즘 개발을 지원.
entity{tuple_delimiter}한국전자통신연구원{tuple_delimiter}기관{tuple_delimiter}과제 2210000156에 참여하는 정부출연연구기관으로 PIM 하드웨어 검증 및 시스템 통합을 담당.
entity{tuple_delimiter}산업통상자원부{tuple_delimiter}부처{tuple_delimiter}과제 2210000156을 관할하는 정부 부처로 32억원의 연구비를 지원.
entity{tuple_delimiter}김민준{tuple_delimiter}연구자{tuple_delimiter}과제 2210000156의 연구책임자로 PIM 아키텍처 설계 연구를 총괄.
entity{tuple_delimiter}과제 2210000156{tuple_delimiter}과제{tuple_delimiter}저전력 고성능 PIM 아키텍처 설계 및 DRAM 기반 연산 가속 연구 과제. 2022년 수행, 정부출연금 32억원. 삼성전자 주관, 서울대·ETRI 참여.
entity{tuple_delimiter}PIM{tuple_delimiter}기술분야{tuple_delimiter}Processing-In-Memory. DRAM 내부에 연산 유닛을 통합해 데이터 이동 비용을 줄이는 차세대 메모리 반도체 기술.
entity{tuple_delimiter}DRAM{tuple_delimiter}기술분야{tuple_delimiter}Dynamic Random Access Memory. 주기억장치용 휘발성 메모리 반도체로 PIM 구현의 기반 소자.
relation{tuple_delimiter}과제 2210000156{tuple_delimiter}삼성전자{tuple_delimiter}주관기관, 연구총괄{tuple_delimiter}삼성전자가 과제 2210000156의 주관기관으로 전체 연구를 총괄.
relation{tuple_delimiter}과제 2210000156{tuple_delimiter}서울대학교{tuple_delimiter}참여기관, 공동연구{tuple_delimiter}서울대학교가 과제 2210000156에 참여기관으로 공동 연구 수행.
relation{tuple_delimiter}과제 2210000156{tuple_delimiter}한국전자통신연구원{tuple_delimiter}참여기관, 공동연구{tuple_delimiter}한국전자통신연구원이 과제 2210000156에 참여기관으로 하드웨어 검증 담당.
relation{tuple_delimiter}산업통상자원부{tuple_delimiter}과제 2210000156{tuple_delimiter}부처감독, 연구비지원{tuple_delimiter}산업통상자원부가 과제를 관할하고 32억원을 지원.
relation{tuple_delimiter}과제 2210000156{tuple_delimiter}김민준{tuple_delimiter}연구책임자, 과제총괄{tuple_delimiter}김민준이 과제 2210000156의 연구책임자로 연구를 총괄.
relation{tuple_delimiter}과제 2210000156{tuple_delimiter}PIM{tuple_delimiter}연구목표, 개발대상{tuple_delimiter}과제의 핵심 목표가 저전력 고성능 PIM 아키텍처 설계.
relation{tuple_delimiter}PIM{tuple_delimiter}DRAM{tuple_delimiter}구현기반, 통합대상{tuple_delimiter}PIM은 DRAM 내부에 연산 유닛을 통합하는 방식으로 구현.
relation{tuple_delimiter}삼성전자{tuple_delimiter}서울대학교{tuple_delimiter}산학협력, 공동연구{tuple_delimiter}삼성전자와 서울대학교가 PIM 연구에서 산학협력 수행.
{completion_delimiter}

"""

# ── 예시 2: NPU 논문 (단일 기관, 연구자 중심) ──────────────────────────────
_EXAMPLE_2 = """<Entity_types>
["기관","기술분야","과제","연구자","부처"]

<Input Text>
```
논문명: 엣지 AI 추론을 위한 저전력 NPU 설계 및 온디바이스 최적화 기법
저자: 박지영, 최현우
소속기관: 한국전자통신연구원
게재연도: 2023
키워드: NPU,엣지 AI,온디바이스,INT8 양자화,스파스 연산,저전력

[초록]
본 논문은 엣지 디바이스에서의 딥러닝 추론을 위한 저전력 NPU 설계 방법론을 제안한다.
INT8 양자화와 스파스 연산을 결합한 하드웨어 아키텍처를 통해 기존 대비 전력 40% 절감,
추론 속도 2.3배 향상을 달성하였다. 제안 구조는 모바일 및 IoT 기기에 적합하다.
```

<Output>
entity{tuple_delimiter}한국전자통신연구원{tuple_delimiter}기관{tuple_delimiter}박지영, 최현우가 소속된 정부출연연구기관으로 NPU 설계 및 엣지 AI 연구를 수행.
entity{tuple_delimiter}박지영{tuple_delimiter}연구자{tuple_delimiter}한국전자통신연구원 소속 연구자로 저전력 NPU 설계 및 온디바이스 최적화 논문의 제1저자.
entity{tuple_delimiter}최현우{tuple_delimiter}연구자{tuple_delimiter}한국전자통신연구원 소속 연구자로 저전력 NPU 설계 논문의 공동저자.
entity{tuple_delimiter}NPU{tuple_delimiter}기술분야{tuple_delimiter}Neural Processing Unit. 딥러닝 추론 연산에 특화된 AI 전용 반도체 가속기 기술.
entity{tuple_delimiter}엣지 AI{tuple_delimiter}기술분야{tuple_delimiter}클라우드 대신 엣지 디바이스(모바일, IoT)에서 AI 추론을 수행하는 온디바이스 컴퓨팅 기술.
entity{tuple_delimiter}스파스 연산{tuple_delimiter}기술분야{tuple_delimiter}신경망의 0에 가까운 가중치를 건너뛰어 연산량과 전력을 절감하는 경량화 기법.
relation{tuple_delimiter}박지영{tuple_delimiter}한국전자통신연구원{tuple_delimiter}소속기관, 연구수행{tuple_delimiter}박지영이 한국전자통신연구원에 소속되어 NPU 연구를 수행.
relation{tuple_delimiter}최현우{tuple_delimiter}한국전자통신연구원{tuple_delimiter}소속기관, 연구수행{tuple_delimiter}최현우가 한국전자통신연구원에 소속되어 NPU 연구에 공동 참여.
relation{tuple_delimiter}박지영{tuple_delimiter}최현우{tuple_delimiter}공동연구, 논문공저{tuple_delimiter}박지영과 최현우가 저전력 NPU 설계 논문을 공동 저술.
relation{tuple_delimiter}NPU{tuple_delimiter}엣지 AI{tuple_delimiter}적용대상, 구현수단{tuple_delimiter}NPU가 엣지 디바이스에서 AI 추론을 가속하는 핵심 하드웨어로 활용.
relation{tuple_delimiter}스파스 연산{tuple_delimiter}NPU{tuple_delimiter}최적화기법, 적용대상{tuple_delimiter}스파스 연산 기법을 NPU 아키텍처에 적용해 전력 40% 절감 달성.
{completion_delimiter}

"""

# ── 예시 3: 양자화 NPU 과제 (KAIST, 과학기술정보통신부) ────────────────────
_EXAMPLE_3 = """<Entity_types>
["기관","기술분야","과제","연구자","부처"]

<Input Text>
```
과제번호: 1711085027
과제명: AI반도체 경량화를 위한 양자화 NPU 개발
주관기관: 한국과학기술원
주무부처: 과학기술정보통신부
연구책임자: 이재욱
연도: 2023
정부출연금: 14억원
키워드: 양자화,NPU,경량화,신경망 추론 가속기

[연구목표]
INT8/INT4 정밀도 양자화 기반 신경망 추론 가속기(NPU) 설계 및 저전력 구현
```

<Output>
entity{tuple_delimiter}한국과학기술원{tuple_delimiter}기관{tuple_delimiter}과제 1711085027의 주관기관으로 양자화 NPU 개발 연구를 수행하는 연구기관.
entity{tuple_delimiter}과학기술정보통신부{tuple_delimiter}부처{tuple_delimiter}과제 1711085027을 관할하는 정부 부처로 연구비를 지원.
entity{tuple_delimiter}이재욱{tuple_delimiter}연구자{tuple_delimiter}과제 1711085027의 연구책임자로 양자화 NPU 개발 연구를 총괄.
entity{tuple_delimiter}과제 1711085027{tuple_delimiter}과제{tuple_delimiter}AI반도체 경량화를 위한 양자화 NPU 개발 국가 R&D 과제. 2023년 수행, 정부출연금 14억원.
entity{tuple_delimiter}NPU{tuple_delimiter}기술분야{tuple_delimiter}Neural Processing Unit. AI 추론 연산 전용 가속기 반도체 기술 분야.
entity{tuple_delimiter}양자화{tuple_delimiter}기술분야{tuple_delimiter}신경망 가중치를 INT8/INT4 정밀도로 압축해 추론 속도와 전력 효율을 개선하는 경량화 기법.
relation{tuple_delimiter}과제 1711085027{tuple_delimiter}한국과학기술원{tuple_delimiter}주관기관, 연구수행{tuple_delimiter}한국과학기술원이 과제 1711085027의 주관기관으로 연구를 수행.
relation{tuple_delimiter}과제 1711085027{tuple_delimiter}이재욱{tuple_delimiter}연구책임자, 과제총괄{tuple_delimiter}이재욱이 과제 1711085027의 연구책임자로 총괄.
relation{tuple_delimiter}과학기술정보통신부{tuple_delimiter}과제 1711085027{tuple_delimiter}부처감독, 연구비지원{tuple_delimiter}과학기술정보통신부가 과제를 감독하고 14억원을 지원.
relation{tuple_delimiter}과제 1711085027{tuple_delimiter}NPU{tuple_delimiter}연구목표, 개발대상{tuple_delimiter}과제의 핵심 개발 목표가 양자화 기반 NPU 설계.
relation{tuple_delimiter}양자화{tuple_delimiter}NPU{tuple_delimiter}핵심기술, 적용기법{tuple_delimiter}양자화 기법을 NPU 설계에 적용해 경량화 달성.
{completion_delimiter}

"""


_patched = False


def patch_ntis_prompts() -> None:
    """LightRAG 초기화 전에 반드시 호출. 중복 호출 무시."""
    global _patched
    if _patched:
        return
    _patched = True

    PROMPTS["DEFAULT_ENTITY_TYPES"] = NTIS_ENTITY_TYPES

    # 기본 예시 3개 전부 NTIS 도메인 예시로 교체
    # 예시 1: PIM 과제 (산학 협력, 복수 기관)
    # 예시 2: NPU 논문 (단일 기관, 연구자 중심)
    # 예시 3: 양자화 NPU 과제 (KAIST, 과기부)
    PROMPTS["entity_extraction_examples"] = [_EXAMPLE_1, _EXAMPLE_2, _EXAMPLE_3]

    # ── 키워드 추출 프롬프트: 모든 키워드 한국어 강제 ──────────────
    # 문제1: LLM이 high_level_keywords를 영어로 번역
    #        ("Industry cluster", "Collaboration") → 한국어 KG 관계 벡터 검색 실패
    # 문제2: low_level_keywords가 너무 포괄적 ("AI", "반도체")
    #        → 협력 관련 엔티티를 찾지 못함
    # 해결: 모든 키워드(high/low 모두)를 한국어로 추출하도록 강제
    PROMPTS["keywords_extraction"] = PROMPTS["keywords_extraction"].replace(
        "5. **Language**: All extracted keywords MUST be in {language}. "
        "Proper nouns (e.g., personal names, place names, organization names) "
        "should be kept in their original language.",
        "5. **Language**: All extracted keywords MUST be in {language}. "
        "**CRITICAL FOR KOREAN QUERIES: ALL keywords (both high_level and low_level) "
        "MUST be in Korean. Do NOT translate any keyword to English. "
        "Examples: '협력 클러스터' NOT 'cooperation cluster', "
        "'AI 반도체' NOT 'AI semiconductor', '기관' NOT 'institution'. "
        "Korean organization names must stay in Korean "
        "(e.g., '한국전자통신연구원' NOT 'ETRI full name in English'). "
        "Short tech abbreviations already in English are OK: NPU, PIM, KAIST, ETRI.**"
    )

    # ── 키워드 추출 예시: 한국어 R&D 예시 추가 ──────────────────────
    # 기존 예시가 모두 영어라 LLM이 한국어 쿼리도 영어로 번역하여 추출함.
    # 한국어 쿼리에 대해 한국어 키워드를 추출하는 예시를 앞에 추가.
    korean_example = (
        'Example (Korean R&D query):\n\n'
        'Query: "AI 반도체 분야 핵심 협력 클러스터를 알려줘"\n\n'
        'Output:\n'
        '{\n'
        '  "high_level_keywords": ["AI 반도체", "협력 클러스터", "산학연 협력"],\n'
        '  "low_level_keywords": ["AI 반도체", "협력", "클러스터", "기관", "과제"]\n'
        '}\n\n'
    )
    PROMPTS["keywords_extraction_examples"] = [korean_example] + PROMPTS["keywords_extraction_examples"]

    print("[NTIS Prompts] LightRAG 프롬프트를 NTIS 한국어 버전으로 교체 완료")
