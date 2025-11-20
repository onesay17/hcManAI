# hcManAI API 구조 문서

## POST /classify-query

### 요청 (Request)

**엔드포인트:** `POST http://localhost:8001/classify-query`

**Content-Type:** `application/json`

**요청 본문 (Request Body):**

Python은 다음 필드명을 모두 지원합니다 (우선순위: `question` > `query` > `message`):

```json
{
  "question": "8월달 발주 건수는"
}
```

또는

```json
{
  "query": "8월달 발주 건수는"
}
```

또는

```json
{
  "message": "8월달 발주 건수는"
}
```

**필드 설명:**

- `question` (권장): 백엔드에서 주로 사용하는 필드명
- `query`: 대체 필드명
- `message`: 대체 필드명
- **주의:** 위 세 필드 중 **최소 하나는 필수**입니다.

---

### 응답 (Response)

**성공 응답 (200 OK):**

응답 형식은 `action_type`에 따라 다릅니다:

#### 1. SQL 타입 (단순 데이터 조회)

```json
{
  "action_type": "SQL",
  "chat_answer": null,
  "query": "8월달 발주 건수는"
}
```

**필드 설명:**

- `action_type`: `"SQL"` - 단순 데이터 조회 질문
- `chat_answer`: `null` - SQL 타입은 답변이 없음
- `query`: 원본 질문 (백엔드에서 SQL 생성 API 호출 시 사용)

**백엔드 처리:**

1. `action_type`이 `"SQL"`인 경우
2. `/generate-sql` 엔드포인트를 호출하여 SQL 생성
3. SQL 실행 후 결과를 `/summarize` 엔드포인트로 전달하여 최종 답변 생성

---

#### 2. REPORT 타입 (분석/보고서 필요)

```json
{
  "action_type": "REPORT",
  "chat_answer": "보고서를 생성하려면 아래 SQL을 먼저 실행하여 데이터를 전달해주세요.",
  "query": "발주 현황 분석해줘",
  "sql": "SELECT ...",
  "report_html": null
}
```

**필드 설명:**

- `action_type`: `"REPORT"` - 분석/보고서가 필요한 복합 질문
- `chat_answer`: 데이터가 없으면 안내 문구, 있으면 실제 보고서 요약
- `query`: 원본 질문
- `sql`: Python이 제안한 SQL (Java에서 실행)
- `report_html`: 데이터가 제공된 경우 HTML 보고서 문자열

**백엔드 처리:**

1. `action_type`이 `"REPORT"`인 경우
2. `sql`을 실행하여 얻은 JSON 데이터를 `data` 필드에 담아 다시 호출하면 `chat_answer`/`report_html`에 실제 보고서가 담겨 반환됨
3. 필요시 `/generate-report` 엔드포인트를 사용하여 동일한 흐름으로 보고서 생성 가능

---

#### 3. GENERAL_CHAT 타입 (일반 대화)

```json
{
  "action_type": "GENERAL_CHAT",
  "chat_answer": "답변 내용...",
  "query": null,
  "sql": null,
  "report_html": null
}
```

**필드 설명:**

- `action_type`: `"GENERAL_CHAT"` - 일반 대화 질문
- `chat_answer`: Gemini가 생성한 답변 (바로 사용 가능)
- `query`: `null` - SQL 생성 불필요
- `sql`, `report_html`: 항상 `null`

**백엔드 처리:**

1. `action_type`이 `"GENERAL_CHAT"`인 경우
2. `chat_answer`를 그대로 사용자에게 전달 (추가 처리 없음)

---

### 오류 응답

#### 422 Unprocessable Entity (요청 형식 오류)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, question, query 또는 message 필드 중 하나는 필수입니다.",
      "input": {}
    }
  ]
}
```

**원인:**

- `question`, `query`, `message` 필드가 모두 없음

---

#### 500 Internal Server Error (서버 오류)

```json
{
  "detail": "질문 분류 중 오류 발생: [오류 메시지]"
}
```

---

## 백엔드 통합 가이드

### 1. 기본 사용법

```java
// 요청 DTO
public class ClassifyQueryRequest {
    private String question;  // 또는 query, message
    // getter, setter
}

// 응답 DTO
public class QueryClassificationResponse {
    private String actionType;      // "SQL", "REPORT", "GENERAL_CHAT"
    private String chatAnswer;      // null 또는 답변/보고서
    private String query;           // null 또는 원본 질문
    private String reportUrl;       // REPORT일 때 HTML 경로, GENERAL_CHAT일 때 안내 문자열
    // getter, setter
}
```

### 2. 처리 플로우

```java
// 1. 질문 분류 요청
QueryClassificationResponse response = webClient.post()
    .uri("http://localhost:8001/classify-query")
    .bodyValue(new ClassifyQueryRequest(question))
    .retrieve()
    .bodyToMono(QueryClassificationResponse.class)
    .block();

// 2. action_type에 따른 분기 처리
switch (response.getActionType()) {
    case "SQL":
        // SQL 생성 → 실행 → 요약
        String sql = generateSql(response.getQuery());
        String data = executeSql(sql);
        String answer = summarize(response.getQuery(), data);
        break;

    case "REPORT":
        // 보고서는 이미 생성되어 있음
        String report = response.getChatAnswer();
        break;

    case "GENERAL_CHAT":
        // 답변은 이미 생성되어 있음
        String answer = response.getChatAnswer();
        break;
}
```

---

## 요약

### 요청 형식

- **필드명:** `question` (권장), `query`, `message` 중 하나
- **타입:** `String`
- **필수:** 예 (세 필드 중 최소 하나)

### 응답 형식

- **action_type:** `"SQL"` | `"REPORT"` | `"GENERAL_CHAT"`
- **chat_answer:** `String | null` (GENERAL_CHAT 또는 REPORT일 때 답변/보고서)
- **query:** `String | null` (SQL 또는 REPORT일 때 원본 질문)
- **sql:** `String | null` (SQL/REPORT일 때 생성된 SQL)
- **report_html:** `String | null`
  - REPORT: 데이터가 제공된 경우 HTML 보고서
  - SQL/GENERAL_CHAT: `null`

### 백엔드 수정 필요사항

**없음!** 현재 백엔드에서 `{"question": "..."}` 형식으로 보내고 있으므로 그대로 사용 가능합니다.

---

---

## HTML 보고서 전략

- REPORT 타입: Python이 SQL을 제공하고, Java가 실행한 데이터(JSON)를 다시 전달하면 HTML 보고서를 문자열로 반환합니다.
- SQL 타입: SQL 실행 결과를 `data`로 다시 보내면 요약 텍스트를 제공하며, HTML 보고서는 생성하지 않습니다.
- GENERAL_CHAT 타입: 단순 답변만 반환합니다.
