# RnD CoopGraph

NTIS 국가 R&D 과제 데이터를 기반으로 LightRAG 지식 그래프(KG)를 구축하고,  
FastAPI + React 웹 인터페이스로 기관 간 협력 네트워크를 분석하는 시스템.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| KG 엔진 | LightRAG (lightrag-hku) |
| LLM | Gemini 2.5 Flash Lite (OpenAI 호환) |
| 임베딩 | `intfloat/multilingual-e5-large` (로컬, 1024-dim) |
| 벡터 DB | nano-vectordb (로컬 파일 기반) |
| 백엔드 | FastAPI + uvicorn |
| 프론트엔드 | React 19 + Vite + Tailwind CSS |
| KG 시각화 | pyvis + vis-network |

---

## 프로젝트 구조

```
RnD_CoopGraph/
├── backend/
│   ├── app/                          # FastAPI 애플리케이션
│   │   ├── main.py                   # 앱 초기화, CORS 설정
│   │   └── routers/
│   │       ├── query.py              # POST /api/query  — LightRAG 질의
│   │       └── graph.py              # GET  /api/graph* — KG 시각화
│   └── kg_builder/                   # KG 구축 파이프라인
│       ├── lightrag_init.py          # LightRAG 인스턴스 초기화 (인덱싱/질의 분리)
│       ├── llm_client.py             # Gemini LLM + 로컬 임베딩 클라이언트
│       ├── ntis_prompts.py           # NTIS 도메인 프롬프트 패치 (한국어 KG 최적화)
│       ├── insert_docs.py            # 문서 인덱싱 (KG 구축 실행)
│       └── query_rag.py              # RAG 질의 래퍼 (local / global / hybrid)
├── frontend/                         # React 프론트엔드
│   ├── src/
│   │   ├── App.jsx                   # 메인 UI (3-column 레이아웃)
│   │   └── index.css
│   ├── tailwind.config.js
│   └── package.json
├── processed_data/                   # 전처리된 NTIS 문서 (KG 인덱싱 입력)
│   ├── NPU/                          # NPU 관련 과제·논문·특허 txt
│   └── PIM/                          # PIM 관련 과제·논문·특허 txt
├── kg_storage/                       # LightRAG 자동 생성 (KG 저장소, gitignore)
│   ├── graph_chunk_entity_relation.graphml
│   ├── kv_store_*.json
│   └── vdb_*.json                    # 엔티티·관계·청크 벡터 DB (float32)
├── .env                              # API 키 (gitignore)
└── requirements.txt
```

---

## 전체 파이프라인

```
NTIS 원천 데이터
      │
      ▼
 전처리 (preprocess_ntis)
 과제·논문·특허 → txt 파일 → processed_data/
      │
      ▼
[1] KG 인덱싱   (insert_docs.py)
    LLM 엔티티·관계 추출 + 로컬 임베딩
    → kg_storage/ (graphml + nano-vectordb)
      │
      ▼
[2] 서비스 기동
    ├── FastAPI 백엔드   (backend/)
    └── React 프론트엔드 (frontend/)
      │
      ▼
[3] 질의 응답
    사용자 질문 → 키워드 추출 → VDB 검색 → LLM 답변 생성
    + 관련 엔티티 추출 → KG 서브그래프 시각화
```

---

## 환경 설정

### 1. Python 의존성

```bash
pip install -r requirements.txt
```

> 최초 실행 시 한국어 임베딩 모델(`intfloat/multilingual-e5-large`, ~500 MB)이 자동 다운로드됩니다.

### 2. 프론트엔드 의존성

```bash
cd frontend && npm install
```

### 3. `.env` 설정

프로젝트 루트에 `.env` 파일 생성:

```env
# Google AI Studio API (Gemini, OpenAI 호환 엔드포인트)
API_KEY=your_api_key_here
GATEWAY_URL=https://generativelanguage.googleapis.com/v1beta/openai/
INDEX_MODEL=gemini-2.5-flash-lite
QUERY_MODEL=gemini-2.5-flash-lite

# Neo4j 사용 시 (미설정 시 로컬 파일 스토리지 자동 사용)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=your_password
```

API 키 발급: [Google AI Studio](https://aistudio.google.com) → Get API Key

---

## 실행

### KG 구축 (최초 1회)

```bash
cd backend/kg_builder
python insert_docs.py
```

`kg_storage/`에 graphml 및 VDB 파일이 생성됩니다.

### 백엔드

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 프론트엔드

```bash
cd frontend
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

---

## 화면 구성

```
┌─────────────┬────────────────────────────┬──────────────────────────┐
│  사이드바    │         중앙 메인           │       KG 시각화          │
│             │                            │                          │
│ 질의 모드   │  질문 입력 / 예시 질문     │  질의 전: 전체 그래프    │
│  🔀 Hybrid  │  ─────────────────────     │  (Top 300 노드)          │
│  🔍 Local   │  답변 (Markdown 렌더링)    │                          │
│  🌐 Global  │                            │  질의 후: 핵심 노드      │
│             │                            │  서브그래프만 표시       │
│  [초기화]   │                            │  (25~30 노드)            │
└─────────────┴────────────────────────────┴──────────────────────────┘
```

**질의 연동 KG 시각화**: 답변에서 KG 노드명을 자동 매칭해 관련 노드 + 2개 이상의 핵심 노드를 공유하는 브릿지 노드만 표시

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/api/query` | LightRAG KG 질의 |
| GET | `/api/graph` | 전체 KG 시각화 HTML (Top 300 노드) |
| GET | `/api/graph/highlight?nodes=A,B` | 질의 관련 핵심 노드 서브그래프 HTML |
| GET | `/api/graph/stats` | KG 통계 (노드·엣지 수) |

### POST /api/query

```json
// 요청
{
  "query": "ETRI가 참여한 NPU 과제와 협력 기관은?",
  "mode": "hybrid"
}

// 응답
{
  "answer": "ETRI는 다음과 같은 NPU 과제에 참여했으며...",
  "mode": "hybrid",
  "processing_time": 3.21,
  "entities": ["한국전자통신연구원", "NPU", "삼성전자", "..."]
}
```

### 질의 모드

| 모드 | 동작 | 적합한 질문 유형 |
|------|------|-----------------|
| `local` | 특정 엔티티 주변 탐색 (Entity VDB) | "ETRI가 참여한 과제는?" |
| `global` | 전체 KG 요약 기반 (Relation VDB) | "주요 협력 클러스터 구조는?" |
| `hybrid` | Local + Global 결합 **(기본값)** | "산학연 협력 구조는?" |

---

## KG 구축 결과

| 항목 | 수치 |
|------|------|
| 인덱싱 문서 | NPU 과제·논문·특허 + PIM 과제·논문·특허 |
| 노드 수 | 11,215개 |
| 엣지 수 | 19,925개 |
| 엔티티 타입 | 기관 / 기술분야 / 과제 / 연구자 / 부처 |
| 저장 방식 | 로컬 파일 (graphml + nano-vectordb, float32) |

---

## 주요 구현 내용

- **한국어 KG 최적화**: `ntis_prompts.py`에서 LightRAG 내부 프롬프트를 NTIS 도메인에 맞게 패치 (한국어 키워드 강제 추출, 한국어 예시 추가)
- **VDB 폴백 검색**: 답변 텍스트 매칭으로 엔티티를 못 찾을 경우 임베딩 유사도 검색으로 보완
- **핵심 노드 서브그래프**: 질의 후 전체 그래프 대신 관련 노드 25~30개만 표시 (브릿지 노드 포함)
- **답변 후처리**: LLM 답변에서 References 섹션 자동 제거, 중복 내용 통합 힌트 적용
