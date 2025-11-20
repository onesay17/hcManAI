# hcManAi

AI 마이크로서비스 - Text-to-SQL 및 데이터 요약 서비스

## 개요

`hcManAi`는 `hcMan`(Java)으로부터 요청을 받아 RAG 파이프라인을 실행하고 SQL 생성 및 데이터 요약 등 모든 AI 로직을 처리하는 Python 기반 마이크로서비스입니다.

## 주요 기능

1. **SQL 생성 API** (`POST /generate-sql`)
   - 사용자 질문을 받아 RAG 파이프라인을 통해 MS-SQL 쿼리 생성
   - Vector DB에서 유사한 스키마 힌트 검색
   - LLM을 활용한 SQL 생성

2. **결과 요약 API** (`POST /summarize`)
   - 질문과 DB 조회 결과를 바탕으로 자연스러운 한국어 답변 생성

3. **스키마 적재 스크립트** (`ingest_schema.py`)
   - `schema_guide.txt` 파일을 읽어 Vector DB에 적재
   - 스키마 변경 시 수동 실행하여 Vector DB 최신화

## 설치 및 설정

### 1. 가상 환경 활성화

```bash
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 설정하세요:

```env
# API 서버 설정
API_HOST=0.0.0.0
API_PORT=8001

# ChromaDB 설정
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION_NAME=schema_guide

# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Google Gemini 설정 (선택사항)
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-pro

# LLM 제공자 선택 (openai 또는 gemini)
LLM_PROVIDER=openai

# RAG 설정
TOP_K_RESULTS=3
```

### 4. ChromaDB 서버 실행

별도 터미널에서 ChromaDB 서버를 실행합니다:

```bash
chroma run --path ./chroma_data --port 8000
```

### 5. 스키마 적재

`schema_guide.txt` 파일을 확인하고, Vector DB에 적재합니다:

```bash
python ingest_schema.py
```

## 실행

### API 서버 실행

```bash
python main.py
```

또는 uvicorn을 직접 사용:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

서버가 실행되면 다음 주소에서 접근할 수 있습니다:
- API 문서: http://localhost:8001/docs
- 대체 문서: http://localhost:8001/redoc

## API 사용 예시

### 1. SQL 생성

```bash
curl -X POST "http://localhost:8001/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "지난주 취소된 주문은 몇 건인가요?"
  }'
```

**응답:**
```json
{
  "sql": "SELECT COUNT(*) AS CancelledOrdersCount FROM Orders WHERE Status = 'Cancelled' AND OrderDate >= DATEADD(DAY, -7, GETDATE())"
}
```

### 2. 결과 요약

```bash
curl -X POST "http://localhost:8001/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "지난주 취소된 주문은 몇 건인가요?",
    "data": "[{\"CancelledOrdersCount\": 5}]"
  }'
```

**응답:**
```json
{
  "response": "지난주 취소된 주문은 총 5건입니다."
}
```

## 프로젝트 구조

```
hcManAI/
├── main.py                 # FastAPI 메인 애플리케이션
├── rag_service.py          # RAG 서비스 모듈
├── llm_service.py          # LLM 서비스 모듈
├── config.py               # 설정 파일
├── ingest_schema.py        # 스키마 적재 스크립트
├── schema_guide.txt        # DB 스키마 가이드 문서
├── requirements.txt        # Python 의존성
└── README.md              # 프로젝트 문서
```

## 주요 모듈 설명

### `main.py`
- FastAPI 애플리케이션
- `/generate-sql` 및 `/summarize` 엔드포인트 제공

### `rag_service.py`
- RAG 파이프라인 구현
- 임베딩 생성, Vector DB 검색, SQL 생성 로직

### `llm_service.py`
- OpenAI 및 Google Gemini 통합
- SQL 생성 및 데이터 요약 기능

### `ingest_schema.py`
- `schema_guide.txt` 파일을 읽어 Vector DB에 적재
- 스키마 변경 시 수동 실행

## 주의사항

1. **ChromaDB 서버**: API 서버 실행 전에 ChromaDB 서버가 실행 중이어야 합니다.
2. **API 키**: OpenAI 또는 Google API 키가 필요합니다.
3. **스키마 업데이트**: `schema_guide.txt` 파일을 수정한 후에는 반드시 `ingest_schema.py`를 실행하여 Vector DB를 업데이트해야 합니다.

## 문제 해결

### ChromaDB 연결 오류
- ChromaDB 서버가 실행 중인지 확인하세요.
- `CHROMA_HOST`와 `CHROMA_PORT` 설정을 확인하세요.

### 임베딩 생성 오류
- `OPENAI_API_KEY`가 올바르게 설정되었는지 확인하세요.

### LLM 호출 오류
- 선택한 LLM 제공자(`LLM_PROVIDER`)의 API 키가 설정되었는지 확인하세요.

