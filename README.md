# RnD CoopGraph

NTIS Open API를 사용해 국가 R&D 과제 데이터(과제, 논문, 특허) 자동 수집

## 📁 파일 구조

```
RnD_CoopGraph/
├── backend/data_collection/
│   ├── ntis_client.py        # NTIS API 클라이언트
│   └── collect_data.py       # 수집 스크립트 ← 이것만 실행!
├── data/raw/                 # 수집 결과 저장
├── .env                      # API 키
└── requirements.txt          # 의존성
```

## 🚀 빠른 시작 (3단계)

### 1️⃣ 의존성 설치

```bash
pip install -r requirements.txt
```

### 2️⃣ 데이터 수집 실행

```bash
python backend/data_collection/collect_data.py
```

### 3️⃣ 결과 확인

```bash
ls data/raw/
# project_*.csv, rpaper_*.csv, rpatent_*.csv 생성됨
```

## 📊 수집되는 데이터

**3개 컬렉션**:
- `project` - 과제검색 (ProjectID, Name, Organization, Budget, TechnologyClassification, Abstract, Goal)
- `rpaper` - 논문검색 (ProjectID, Title, Authors, Year, Abstract)
- `rpatent` - 특허검색 (ProjectID, Title, Number, Inventor, Abstract)
