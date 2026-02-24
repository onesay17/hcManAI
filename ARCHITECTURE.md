# hcManAI - 아키텍처 문서

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [아키텍처 다이어그램](#아키텍처-다이어그램)
3. [기술 스택](#기술-스택)
4. [시스템 구성](#시스템-구성)
5. [핵심 컴포넌트](#핵심-컴포넌트)
6. [데이터 플로우](#데이터-플로우)
7. [API 엔드포인트](#api-엔드포인트)
8. [주요 기능](#주요-기능)
9. [설계 특징](#설계-특징)

---

## 시스템 개요

**hcManAI**는 자연어 질문을 SQL 쿼리로 변환하고, 데이터베이스 조회 결과를 분석하여 보고서를 생성하는 AI 기반 마이크로서비스입니다. RAG(Retrieval Augmented Generation) 기술을 활용하여 데이터베이스 스키마 정보를 효과적으로 활용하고, Google Gemini LLM을 통해 고품질의 SQL 및 보고서를 생성합니다.

### 주요 특징
- 🤖 **RAG 기반 SQL 생성**: Vector DB를 활용한 컨텍스트 기반 SQL 생성
- 📊 **자동 보고서 생성**: 데이터 분석 결과를 HTML 형식의 보고서로 자동 생성
- 🔍 **지능형 질문 분류**: SQL, REPORT, GENERAL_CHAT 자동 분류
- 📈 **동적 차트 생성**: 추이/그래프 요청 시 HTML/CSS 기반 차트 자동 생성
- 🔐 **보안 강화**: SQL 보안 검증 (WITH 절 차단 등)

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                         Java Backend                              │
│                    (Spring Boot Application)                      │
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │ ChatService  │────────▶│  WebClient   │                      │
│  └──────────────┘         └──────┬───────┘                      │
│                                   │                               │
└───────────────────────────────────┼───────────────────────────────┘
                                     │ HTTP/REST
                                     │ POST /classify-query
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python AI Service                             │
│                    (FastAPI Application)                          │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Router                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │/classify-query│  │/generate-sql│  │/summarize    │   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │   │
│  │         │                 │                 │           │   │
│  └─────────┼─────────────────┼─────────────────┼───────────┘   │
│            │                 │                 │                 │
│  ┌─────────▼─────────────────▼─────────────────▼───────────┐   │
│  │                    LLMService                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │classify_query│  │generate_sql  │  │summarize     │   │   │
│  │  │              │  │              │  │generate_report│   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │   │
│  │         │                 │                 │           │   │
│  └─────────┼─────────────────┼─────────────────┼───────────┘   │
│            │                 │                 │                 │
│            │                 │                 │                 │
│  ┌─────────▼─────────────────▼─────────────────▼───────────┐   │
│  │                    RAGService                           │   │
│  │  ┌──────────────┐         ┌──────────────┐              │   │
│  │  │generate_     │────────▶│search_similar│              │   │
│  │  │embedding     │         │_schemas      │              │   │
│  │  └──────────────┘         └──────┬───────┘              │   │
│  │                                  │                       │   │
│  └──────────────────────────────────┼───────────────────────┘   │
│                                     │                             │
└─────────────────────────────────────┼─────────────────────────────┘
                                      │
                                      │ HTTP API
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ChromaDB (Vector Database)                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Collection: schema_guide                     │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Schema Documents (Embedded)                       │   │   │
│  │  │  - Pkfl 테이블 스키마                               │   │   │
│  │  │  - sffl 테이블 스키마                               │   │   │
│  │  │  - 컬럼 설명 및 사용 예시                            │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Embedding API
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Google Gemini API                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Text         │  │ Embedding    │  │ HTML Report  │          │
│  │ Generation   │  │ Generation   │  │ Generation   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                      │
                                      │ SQL Execution
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              MS-SQL Database (Java Backend)                       │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │ heechang.    │         │ sffl         │                      │
│  │ heechang.Pkfl│         │ (매출정보)   │                      │
│  └──────────────┘         └──────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 기술 스택

### Backend (Python)
- **Framework**: FastAPI 0.104.1
- **ASGI Server**: Uvicorn 0.24.0
- **LLM**: Google Gemini (gemini-1.5-flash-latest)
- **Embedding**: Google Generative AI Embeddings (text-embedding-004)
- **Vector DB**: ChromaDB 0.4.22
- **LangChain**: 0.1.0 (LLM 통합)
- **Validation**: Pydantic 2.5.0

### Backend (Java)
- **Framework**: Spring Boot
- **HTTP Client**: Spring WebClient (Reactive)
- **Database**: MS-SQL Server

### Infrastructure
- **Vector Database**: ChromaDB (Standalone Server)
- **API Protocol**: REST API (JSON)

---

## 시스템 구성

### 1. Python AI Service (FastAPI)
- **역할**: AI 기반 SQL 생성 및 데이터 분석 서비스
- **포트**: 8001
- **주요 기능**:
  - 질문 분류 (SQL/REPORT/GENERAL_CHAT)
  - RAG 기반 SQL 생성
  - 데이터 요약 및 보고서 생성
  - HTML 차트 생성

### 2. Java Backend (Spring Boot)
- **역할**: 메인 애플리케이션 서버, 데이터베이스 접근
- **포트**: 8080
- **주요 기능**:
  - 사용자 요청 처리
  - SQL 실행 및 결과 조회
  - Python AI Service와 통신
  - SQL 보안 검증

### 3. ChromaDB (Vector Database)
- **역할**: 데이터베이스 스키마 정보의 벡터 저장소
- **포트**: 8000
- **컬렉션**: `schema_guide`
- **데이터**: Pkfl, sffl 테이블 스키마 및 컬럼 설명

### 4. MS-SQL Database
- **역할**: 실제 비즈니스 데이터 저장소
- **테이블**:
  - `heechang.heechang.Pkfl`: 발주 정보
  - `sffl`: 매출 정보

---

## 핵심 컴포넌트

### 1. LLMService (`llm_service.py`)
**책임**: Google Gemini API와의 모든 상호작용 처리

#### 주요 메서드
- `classify_query(query: str) -> Dict`: 질문을 SQL/REPORT/GENERAL_CHAT으로 분류
- `generate_sql(query: str, schema_hints: str) -> str`: 스키마 힌트 기반 SQL 생성
- `summarize(query: str, data: str) -> str`: 데이터 요약 (그래프 포함 가능)
- `generate_report(query: str, data: str) -> Tuple[str, str]`: HTML 보고서 생성
- `chat(question: str) -> str`: 일반 질문 답변

#### 특징
- **동적 차트 생성**: "추이", "그래프", "차트" 키워드 감지 시 HTML/CSS 차트 자동 생성
- **마크다운 변환**: `**bold**` → `<strong>bold</strong>` 자동 변환
- **테이블 선택 로직**: 키워드 기반 테이블 자동 선택 (발주→Pkfl, 매출→sffl)

### 2. RAGService (`rag_service.py`)
**책임**: RAG 파이프라인 구현 (임베딩 생성, Vector DB 검색, SQL 생성)

#### 주요 메서드
- `generate_embedding(text: str) -> List[float]`: 텍스트를 벡터로 변환
- `search_similar_schemas(query: str, top_k: int) -> List[str]`: 유사 스키마 검색
- `generate_sql(query: str) -> str`: RAG 파이프라인을 통한 SQL 생성

#### RAG 파이프라인
```
사용자 질문
    ↓
임베딩 생성 (Google Embedding API)
    ↓
Vector DB 유사 문서 검색 (ChromaDB)
    ↓
스키마 힌트 조합
    ↓
LLM에 SQL 생성 요청 (Gemini)
    ↓
생성된 SQL 반환
```

### 3. FastAPI Router (`main.py`)
**책임**: REST API 엔드포인트 정의 및 요청 라우팅

#### 주요 엔드포인트
- `POST /classify-query`: 통합 질문 분류 및 처리
- `POST /generate-sql`: SQL 생성
- `POST /summarize`: 데이터 요약
- `POST /generate-report`: 보고서 생성
- `POST /chat`: 일반 질문 답변

---

## 데이터 플로우

### 시나리오 1: SQL 질문 처리

```
1. 사용자 질문
   "8월 발주 건수는?"

2. Java Backend
   POST /classify-query
   {"question": "8월 발주 건수는?"}

3. Python AI Service
   ├─ classify_query() → action_type: "SQL"
   ├─ generate_sql() → SQL 생성
   └─ 응답: {action_type: "SQL", sql: "SELECT ...", query: "..."}

4. Java Backend
   ├─ SQL 실행 (MS-SQL)
   ├─ 결과를 JSON으로 변환
   └─ POST /classify-query (data 포함)
      {"question": "8월 발주 건수는?", "data": "[{...}]"}

5. Python AI Service
   ├─ summarize() → 자연어 요약 생성
   └─ 응답: {action_type: "SQL", chat_answer: "8월 발주 건수는 649건입니다."}

6. 사용자에게 답변 표시
```

### 시나리오 2: REPORT 질문 처리

```
1. 사용자 질문
   "8월 거래처별 발주현황 보고서 만들어줘"

2. Java Backend
   POST /classify-query
   {"question": "8월 거래처별 발주현황 보고서 만들어줘"}

3. Python AI Service
   ├─ classify_query() → action_type: "REPORT"
   ├─ generate_sql() → SQL 생성
   └─ 응답: {action_type: "REPORT", sql: "SELECT ...", query: "..."}

4. Java Backend
   ├─ SQL 실행 (MS-SQL)
   ├─ 결과를 JSON으로 변환
   └─ POST /classify-query (data 포함)
      {"question": "...", "data": "[{...}]"}

5. Python AI Service
   ├─ generate_report() → HTML 보고서 생성
   └─ 응답: {
        action_type: "REPORT",
        chat_answer: "요약 텍스트...",
        report_html: "<!DOCTYPE html>..."
      }

6. Java Backend
   └─ HTML 보고서를 사용자에게 표시 (iframe 또는 새 창)
```

### 시나리오 3: 그래프 요청 처리

```
1. 사용자 질문
   "2024년 제품별 매출 추이 그래프 보여줘"

2. SQL 생성 및 실행 (위와 동일)

3. Python AI Service
   ├─ summarize() 호출
   ├─ "추이", "그래프" 키워드 감지
   ├─ Gemini에게 HTML/CSS 차트 생성 요청
   └─ 응답: HTML 형식 (차트 포함)

4. 사용자에게 HTML 차트 표시
```

---

## API 엔드포인트

### POST /classify-query
**통합 질문 분류 및 처리 엔드포인트**

#### 요청
```json
{
  "question": "8월 발주 건수는?",
  "data": "[{...}]"  // 선택사항 (SQL 실행 결과)
}
```

#### 응답 (SQL 타입)
```json
{
  "action_type": "SQL",
  "chat_answer": "8월 발주 건수는 649건입니다.",
  "query": "8월 발주 건수는?",
  "sql": "SELECT COUNT(*) FROM ...",
  "report_html": null
}
```

#### 응답 (REPORT 타입)
```json
{
  "action_type": "REPORT",
  "chat_answer": "보고서 요약...",
  "query": "8월 거래처별 발주현황 보고서 만들어줘",
  "sql": "SELECT ...",
  "report_html": "<!DOCTYPE html>..."
}
```

#### 응답 (GENERAL_CHAT 타입)
```json
{
  "action_type": "GENERAL_CHAT",
  "chat_answer": "파이썬은 프로그래밍 언어입니다...",
  "query": null,
  "sql": null,
  "report_html": null
}
```

### POST /generate-sql
**SQL 생성 전용 엔드포인트**

#### 요청
```json
{
  "query": "8월 발주 건수는?"
}
```

#### 응답
```json
{
  "sql": "SELECT COUNT(*) FROM heechang.heechang.Pkfl WHERE ..."
}
```

### POST /summarize
**데이터 요약 엔드포인트**

#### 요청
```json
{
  "query": "8월 발주 건수는?",
  "data": "[{\"count\": 649}]"
}
```

#### 응답
```json
{
  "response": "8월 발주 건수는 649건입니다."
}
```

### POST /generate-report
**보고서 생성 전용 엔드포인트**

#### 요청
```json
{
  "query": "8월 거래처별 발주현황 보고서",
  "data": "[{...}]"
}
```

#### 응답
```json
{
  "report": "보고서 요약 텍스트...",
  "report_html": "<!DOCTYPE html>..."
}
```

---

## 주요 기능

### 1. 지능형 질문 분류
- **SQL**: 단순 데이터 조회 질문
- **REPORT**: 보고서/차트 생성 요청
- **GENERAL_CHAT**: 일반 대화 질문

### 2. RAG 기반 SQL 생성
- Vector DB에서 유사 스키마 검색
- 컨텍스트 기반 정확한 SQL 생성
- 테이블 자동 선택 (키워드 기반)
- 보안 규칙 준수 (WITH 절 차단)

### 3. 동적 HTML 보고서 생성
- 데이터 기반 인사이트 도출
- HTML/CSS 차트 자동 생성
- 반응형 디자인
- 외부 라이브러리 없이 순수 HTML/CSS

### 4. 그래프 자동 생성
- "추이", "그래프", "차트" 키워드 감지
- 막대 그래프, 선 그래프, 파이 차트 지원
- 데이터 기반 정확한 시각화

### 5. 마크다운 변환
- `**bold**` → `<strong>bold</strong>` 자동 변환
- 제품명, 금액 자동 강조
- 리스트 형식 자동 변환

### 6. 테이블 선택 로직
- **발주 관련**: `heechang.heechang.Pkfl` 테이블
- **매출 관련**: `sffl` 테이블
- 키워드 기반 자동 선택

---

## 설계 특징

### 1. 마이크로서비스 아키텍처
- **Python AI Service**: AI 로직 전담
- **Java Backend**: 비즈니스 로직 및 데이터 접근
- **명확한 책임 분리**: 각 서비스의 역할이 명확

### 2. RAG (Retrieval Augmented Generation)
- **Vector DB 활용**: 스키마 정보의 의미 기반 검색
- **컨텍스트 강화**: 관련 스키마만 LLM에 제공
- **정확도 향상**: 전체 스키마보다 관련 정보만 사용

### 3. 2단계 처리 플로우
- **1단계**: SQL 생성 및 제공
- **2단계**: 데이터 기반 분석/보고서 생성
- **유연성**: 데이터 없이도 SQL만 제공 가능

### 4. 보안 강화
- **SQL 검증**: WITH 절 등 위험한 구문 차단
- **서브쿼리 사용**: 복잡한 쿼리도 안전하게 처리
- **입력 검증**: Pydantic을 통한 엄격한 타입 검증

### 5. 확장 가능한 설계
- **LLM 교체 가능**: Provider 패턴으로 LLM 교체 용이
- **새로운 테이블 추가**: 스키마 가이드만 추가하면 자동 인식
- **새로운 기능 추가**: 모듈화된 구조로 기능 추가 용이

### 6. 에러 처리
- **명확한 에러 메시지**: 사용자 친화적 에러 응답
- **로깅**: 상세한 디버깅 정보 제공
- **Fallback**: Vector DB 검색 실패 시 전체 스키마 사용

### 7. 성능 최적화
- **임베딩 캐싱**: ChromaDB의 내장 캐싱 활용
- **비동기 처리**: FastAPI의 비동기 지원
- **최적화된 검색**: TOP_K 결과로 컨텍스트 크기 제한

---

## 데이터베이스 스키마

### Pkfl 테이블 (발주 정보)
- **경로**: `heechang.heechang.Pkfl`
- **주요 컬럼**:
  - `Pk_date`: 발주일 (YYYYMMDD)
  - `Pk_pdat`: 입고예정일 (YYYYMMDD)
  - `pk_gona`: 거래처명
  - `pk_pona`: 품명
  - `Pk_bqty`: 발주량
  - `pk_amtt`: 금액
  - `pk_stat`: 진행상태

### sffl 테이블 (매출 정보)
- **경로**: `sffl`
- **주요 컬럼**:
  - `sf_date`: 일자 (YYYYMMDD 또는 YYYYMM)
  - `sf_yona`: 지점명
  - `sf_pona`: 제품명
  - `sf_amtt`: 실적 금액
  - `sf_bqty`: 실적 수량
  - `sf_omny`: 목표 금액
  - `sf_oqty`: 목표 수량
  - `sf_msbn`: 목표/실적 구분 (0=목표, 1=실적)

---

## 배포 및 실행

### 환경 변수 설정 (.env)
```env
# API 서버 설정
API_HOST=0.0.0.0
API_PORT=8001

# ChromaDB 설정
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION_NAME=schema_guide

# Google Gemini 설정
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-flash-latest

# LLM 제공자
LLM_PROVIDER=gemini

# RAG 설정
TOP_K_RESULTS=3
```

### 실행 순서
1. **ChromaDB 서버 실행**
   ```bash
   chroma run --path ./chroma_data --port 8000
   ```

2. **스키마 적재** (최초 1회 또는 스키마 변경 시)
   ```bash
   python ingest_schema.py
   ```

3. **Python AI Service 실행**
   ```bash
   python main.py
   ```

4. **Java Backend 실행**
   ```bash
   # Spring Boot 애플리케이션 실행
   ```

---

## 향후 개선 방향

1. **캐싱 전략**: 자주 사용되는 SQL 쿼리 결과 캐싱
2. **멀티 테넌시**: 여러 데이터베이스 스키마 지원
3. **실시간 스트리밍**: 긴 보고서 생성 시 스트리밍 응답
4. **사용자 피드백**: 생성된 SQL의 정확도 피드백 수집
5. **성능 모니터링**: API 응답 시간 및 LLM 호출 비용 모니터링

---

## 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [ChromaDB 공식 문서](https://docs.trychroma.com/)
- [Google Gemini API 문서](https://ai.google.dev/docs)
- [LangChain 공식 문서](https://python.langchain.com/)

---

**작성일**: 2025년 1월  
**버전**: 1.0.0
