# RnD CoopGraph

NTIS Open API로 국가 R&D 과제·논문·특허 데이터를 수집하고,  
LightRAG 기반 지식 그래프(KG)를 구축해 기관 간 협력 네트워크를 분석하는 프로젝트.

---

## 📁 파일 구조

```
RnD_CoopGraph/
├── backend/
│   ├── data_collection/
│   │   ├── ntis_client.py       # NTIS API 클라이언트
│   │   ├── collect_data.py      # 데이터 수집 스크립트
│   │   └── test_api.py          # API 연결 테스트
│   └── kg_builder/
│       ├── lightrag_init.py     # LightRAG 인스턴스 초기화
│       ├── llm_client.py        # LLM + 로컬 임베딩 클라이언트
│       ├── ntis_prompts.py      # NTIS 도메인 프롬프트 패치
│       ├── insert_docs.py       # 문서 인덱싱 (KG 구축)
│       └── query_rag.py         # RAG 질의 (3모드)
├── processed_data/
│   ├── NPU/                     # NPU 관련 전처리 txt 파일
│   └── PIM/                     # PIM 관련 전처리 txt 파일
├── kg_storage/                  # LightRAG 자동 생성
│   ├── graph_chunk_entity_relation.graphml  ← 최종 KG 파일
│   ├── kv_store_*.json          # RAG 질의용 내부 상태
│   └── vdb_*.json               # 벡터 임베딩 DB
├── remap_entity_types.py        # 엔티티 타입 후처리 스크립트
├── remap_relations.py           # 관계 레이블 후처리 스크립트
├── .env                         # API 키 (gitignore)
└── requirements.txt
```

---

## 🏗️ 전체 파이프라인

```
NTIS API
   │
   ▼
[1] 데이터 수집        collect_data.py          → processed_data/{NPU,PIM}/
   │
   ▼
[2] KG 인덱싱         insert_docs.py            → kg_storage/ (graphml + vdb)
   │  (LLM 엔티티 추출 + 로컬 임베딩)
   ▼
[3] 후처리            remap_entity_types.py      → 엔티티 타입 NTIS 5종으로 정규화
                      remap_relations.py         → 관계 레이블 한국어로 정규화
   │
   ├─▶ [4a] RAG 질의  query_rag.py              → 챗봇 API (local/global/hybrid)
   │
   └─▶ [4b] Neo4j용  graphml 파일            → 그래프 DB 적재·시각화
```

---

## ⚙️ 환경 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

> 최초 실행 시 한국어 임베딩 모델(`intfloat/multilingual-e5-large`, ~500MB)이 자동 다운로드됩니다.

### 2. `.env` 설정

```
# Google AI Studio (gemini) 또는 OpenAI 호환 엔드포인트
API_KEY=your_api_key_here
INDEX_MODEL=gemini-2.5-flash-lite    # 인덱싱용
QUERY_MODEL=gemini-2.5-flash-lite    # 질의용
GATEWAY_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Neo4j 연동 시 추가 (미설정 시 로컬 파일 스토리지 사용)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=your_password
```

---

## 🚀 실행 순서

### Step 1 — 데이터 수집

```bash
python backend/data_collection/collect_data.py
```

수집 결과: `processed_data/NPU/`, `processed_data/PIM/` 아래 txt 파일 생성

---

### Step 2 — KG 인덱싱 (LightRAG)

```bash
cd backend/kg_builder
python insert_docs.py --topic all    # NPU + PIM 전체
# 또는
python insert_docs.py --topic NPU    # NPU만
python insert_docs.py --topic PIM    # PIM만
python insert_docs.py --topic all --limit 10  # 테스트: 10개만
```

- 이미 인덱싱된 문서는 자동 스킵
- LLM API 429/503 오류 시 10→30→60초 재시도 로직 내장
- 결과는 `kg_storage/` 에 자동 저장

---

### Step 3 — 후처리 (엔티티 타입 + 관계 레이블 정규화)

```bash
# 프로젝트 루트에서
python remap_entity_types.py    # UNKNOWN / 영어 타입 → NTIS 5종 한국어로 변환
python remap_relations.py       # 영어 관계 레이블 → 한국어로 변환
```

| 스크립트 | 처리 대상 | 결과 |
|----------|----------|------|
| `remap_entity_types.py` | 노드 타입 오류(UNKNOWN, organization 등) | 1,061개 교정 |
| `remap_relations.py` | 엣지 키워드(related to 등 영어) | 3,444개 교정 |

---

### Step 4a — RAG 질의 테스트

```bash
cd backend/kg_builder
python query_rag.py
```

**3가지 질의 모드:**

| 모드 | 특징 | 적합한 질문 |
|------|------|------------|
| `local` | 특정 엔티티 주변 탐색 | "ETRI가 참여한 과제는?" |
| `global` | 전체 KG 요약 기반 | "2022~2025년 협력 클러스터는?" |
| `hybrid` | 두 방식 결합 | "산학연 협력 구조는?" |

외부에서 단일 질의 호출:
```python
from kg_builder.query_rag import query_once
answer = await query_once("NPU 분야 주요 협력 기관은?", mode="hybrid")
```

---

## 📊 KG 구축 결과

| 항목 | 수치 |
|------|------|
| 인덱싱 문서 수 | NPU 978건 + PIM 818건 |
| 노드 수 | 11,215개 |
| 엣지 수 | 19,925개 |
| 엔티티 타입 | 기관 / 기술분야 / 과제 / 연구자 / 부처 |
| 주요 관계 | 부처감독, 연구비지원, 연구수행, 주관기관, 연구책임자 |