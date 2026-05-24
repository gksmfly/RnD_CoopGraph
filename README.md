# RnD CoopGraph

NTIS 국가 R&D 과제 데이터를 기반으로 LightRAG 지식 그래프(KG)를 구축하고,  
FastAPI + React 웹 인터페이스로 기관 간 협력 네트워크를 분석하는 프로젝트.

---

## 📁 프로젝트 구조

```
RnD_CoopGraph/
├── backend/
│   ├── app/                         # FastAPI 백엔드
│   │   ├── main.py                  # 앱 초기화 & CORS
│   │   └── routers/
│   │       ├── query.py             # POST /api/query
│   │       └── graph.py             # GET /api/graph, /api/graph/highlight
│   └── kg_builder/                  # LightRAG KG 구축
│       ├── lightrag_init.py         # LightRAG 인스턴스 초기화
│       ├── llm_client.py            # LLM + 로컬 임베딩 클라이언트
│       ├── ntis_prompts.py          # NTIS 도메인 프롬프트 패치
│       ├── insert_docs.py           # 문서 인덱싱 (KG 구축)
│       └── query_rag.py             # RAG 질의 (local/global/hybrid)
├── frontend/                        # React 프론트엔드
│   ├── src/
│   │   ├── App.jsx                  # 메인 UI (3-column 레이아웃)
│   │   └── index.css
│   └── package.json
├── processed_data/
│   ├── NPU/                         # NPU 관련 전처리 txt 파일
│   └── PIM/                         # PIM 관련 전처리 txt 파일
├── kg_storage/                      # LightRAG 자동 생성 (KG 저장소)
│   ├── graph_chunk_entity_relation.graphml
│   ├── kv_store_*.json
│   └── vdb_*.json
├── .env                             # API 키 (gitignore)
└── requirements.txt
```

---

## 🏗️ 전체 파이프라인

```
NTIS 데이터 (processed_data/)
   │
   ▼
[1] KG 인덱싱      insert_docs.py     → kg_storage/ (graphml + vdb)
   │  (LLM 엔티티 추출 + 로컬 임베딩)
   ▼
[2] 후처리         remap_entity_types.py / remap_relations.py
   │               → 엔티티 타입·관계 레이블 한국어 정규화
   ▼
[3] 서비스
   ├─▶ FastAPI 백엔드   uvicorn app.main:app
   └─▶ React 프론트엔드  npm run dev
```

---

## ⚙️ 환경 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

> 최초 실행 시 한국어 임베딩 모델(`intfloat/multilingual-e5-large`, ~500MB)이 자동 다운로드됩니다.

```bash
cd frontend && npm install
```

### 2. `.env` 설정

```
# Google AI Studio API (Gemini OpenAI 호환)
API_KEY=your_api_key_here
GATEWAY_URL=https://generativelanguage.googleapis.com/v1beta/openai/
INDEX_MODEL=gemini-2.5-flash-lite    # 인덱싱용
QUERY_MODEL=gemini-2.5-flash-lite    # 질의용

# Neo4j 연동 시 추가 (미설정 시 로컬 파일 스토리지 사용)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=your_password
```

API 키 발급: [Google AI Studio](https://aistudio.google.com) → Get API Key

---

## 🚀 실행

### 백엔드 (FastAPI)

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload-dir app
```

### 프론트엔드 (React)

```bash
cd frontend
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

---

## 🖥️ 화면 구성

| 영역 | 내용 |
|------|------|
| 좌측 사이드바 | 질의 모드 선택 (Hybrid / Local / Global) |
| 중앙 | 질문 입력, 예시 질문, 답변 표시 |
| 우측 | KG 시각화 (질의 전: 전체 그래프 / 질의 후: 관련 노드 서브그래프) |

**질의 연동 KG 시각화**: 질의 후 답변에서 관련 엔티티를 자동 추출해 해당 노드와 1-hop 이웃만 표시

---

## 📡 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/api/query` | LightRAG KG 질의 |
| GET | `/api/graph` | 전체 KG 시각화 HTML (top 300 노드) |
| GET | `/api/graph/highlight?nodes=A,B` | 질의 관련 노드 서브그래프 HTML |
| GET | `/api/graph/stats` | KG 통계 (노드/엣지 수) |

### POST /api/query

```json
// 요청
{ "query": "ETRI가 참여한 NPU 과제는?", "mode": "hybrid" }

// 응답
{
  "answer": "...",
  "mode": "hybrid",
  "processing_time": 3.21,
  "entities": ["한국전자통신연구원", "NPU", "...]
}
```

**질의 모드:**

| 모드 | 특징 | 적합한 질문 |
|------|------|------------|
| `local` | 특정 엔티티 주변 탐색 | "ETRI가 참여한 과제는?" |
| `global` | 전체 KG 요약 기반 | "2022~2025년 주요 협력 클러스터는?" |
| `hybrid` | 두 방식 결합 (기본값) | "산학연 협력 구조는?" |

---

## 📊 KG 구축 결과

| 항목 | 수치 |
|------|------|
| 인덱싱 문서 수 | NPU 978건 + PIM 802건 |
| 노드 수 | 11,215개 |
| 엣지 수 | 19,925개 |
| 엔티티 타입 | 기관 / 기술분야 / 과제 / 연구자 / 부처 |
| 주요 관계 | 부처감독, 연구비지원, 연구수행, 주관기관, 연구책임자 |

---

## 🔧 KG 재구축 (선택)

이미 `kg_storage/`가 존재하면 이 단계는 불필요합니다.

```bash
# KG 인덱싱
cd backend/kg_builder
python insert_docs.py --topic all       # NPU + PIM 전체
python insert_docs.py --topic NPU       # NPU만
python insert_docs.py --topic all --limit 10  # 테스트 (10개)

# 후처리
python remap_entity_types.py            # 엔티티 타입 정규화
python remap_relations.py               # 관계 레이블 정규화
```
