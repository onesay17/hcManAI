"""
LLM 서비스 모듈
Google Gemini를 사용하여 LLM 호출을 처리합니다.
"""
from typing import Optional, Dict, Any, Tuple
import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from config import settings


class LLMService:
    """LLM 서비스 클래스"""
    
    def __init__(self):
        """LLM 서비스 초기화"""
        self.provider = settings.LLM_PROVIDER.lower()
        
        if self.provider == "gemini":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
            self.model = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.1
            )
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
    
    def generate_sql(self, query: str, schema_hints: str) -> str:
        """
        SQL 생성
        
        Args:
            query: 사용자 질문
            schema_hints: Vector DB에서 검색된 스키마 힌트
            
        Returns:
            생성된 SQL 쿼리
        """
        prompt = f"""당신은 MS-SQL (T-SQL) 전문가입니다. 반드시 아래 제공된 스키마 정보만 사용하여 SQL 쿼리를 생성해주세요.

=== 데이터베이스 스키마 정보 (반드시 이 정보만 사용) ===
{schema_hints}
===============================================

사용자 질문: {query}

중요 규칙 (반드시 준수):
1. 위에 제공된 스키마 정보에 있는 테이블명과 컬럼명만 사용하세요.
2. 스키마에 없는 테이블명(예: Orders, Order, OrderTable 등)을 절대 사용하지 마세요.
3. 스키마에 없는 컬럼명(예: OrderDate, Order_Date, pkDate 등)을 절대 사용하지 마세요.
4. 테이블명은 반드시 전체 경로 형식으로 사용하세요: "heechang.heechang.Pkfl" (단순히 "Pkfl"만 사용하면 안 됩니다!)
   - 단, sffl 테이블은 스키마 경로 없이 "sffl"만 사용하세요.
5. 컬럼명은 정확히 스키마에 명시된 실제 필드명을 사용하세요:
   - 발주일: Pk_date (pkDate 아님!)
   - 입고예정일: Pk_pdat (pkPdat 아님!)
   - 실입고일: Pk_ldat (pkLdat 아님!)
   - 등록일: Pk_bdat (pkBdat 아님!)
   - 기타 모든 필드도 스키마에 명시된 실제 필드명을 정확히 사용하세요.
6. MS-SQL (T-SQL) 문법을 사용하세요.
7. **보안 규칙 (매우 중요):**
   - WITH 절(CTE, Common Table Expression)을 절대 사용하지 마세요. 보안 검증에서 차단됩니다.
   - 복잡한 쿼리가 필요한 경우 서브쿼리(Subquery)나 JOIN을 사용하세요.
   - 예시: WITH 절 대신 서브쿼리 사용
     - 잘못된 예: 
       WITH Top10Products AS (SELECT TOP 10 sf_pona, SUM(sf_amtt) AS ProductSales FROM sffl GROUP BY sf_pona ORDER BY ProductSales DESC)
       SELECT ...
     - 올바른 예:
       SELECT 
         T.sf_pona AS ProductName,
         T.ProductSales,
         (T.ProductSales / (SELECT SUM(sf_amtt) FROM sffl WHERE sf_yona = '부산지점' AND sf_msbn = '1')) * 100 AS SalesProportion
       FROM (
         SELECT TOP 10 sf_pona, SUM(sf_amtt) AS ProductSales
         FROM sffl
         WHERE sf_yona = '부산지점' AND sf_msbn = '1'
         GROUP BY sf_pona
         ORDER BY SUM(sf_amtt) DESC
       ) AS T
       ORDER BY T.ProductSales DESC
8. 날짜 처리 규칙:
   - 날짜 필드(Pk_date, Pk_pdat 등)는 YYYYMMDD 형식입니다 (예: 20240815).
   - 사용자가 년도를 명시하지 않으면 현재 년도를 사용하세요: YEAR(GETDATE())
   - 예시: "8월 발주 건수" → SUBSTRING(Pk_date, 1, 4) = CAST(YEAR(GETDATE()) AS VARCHAR(4)) AND SUBSTRING(Pk_date, 5, 2) = '08'
   - 예시: "2024년 8월 발주 건수" → SUBSTRING(Pk_date, 1, 4) = '2024' AND SUBSTRING(Pk_date, 5, 2) = '08'
   - 년도만 명시된 경우: "2024년 발주 건수" → SUBSTRING(Pk_date, 1, 4) = '2024'
   - 월만 명시된 경우: "8월 발주 건수" → 현재 년도 + 해당 월
9. COUNT 사용 규칙:
   - 사용자가 명시적으로 "중복 제거", "고유한", "유니크" 등의 표현을 사용하지 않는 한, COUNT(*)를 사용하세요.
   - COUNT(DISTINCT 컬럼명)은 사용자가 명시적으로 요청한 경우에만 사용하세요.
   - 단순히 "건수", "개수", "몇 개"를 물어보는 경우에는 COUNT(*)를 사용하세요.
10. SQL 쿼리만 반환하세요. 설명, 주석, 마크다운 코드 블록은 포함하지 마세요.
11. 테이블명과 컬럼명은 대소문자를 구분하여 정확히 사용하세요 (예: Pk_date, Pk_pdat 등).

SQL 쿼리:"""

        if self.provider == "gemini":
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            sql = response.content.strip() if hasattr(response, 'content') else str(response)
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
        
        # SQL만 추출 (마크다운 코드 블록 제거)
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1]) if len(lines) > 2 else sql
        if sql.startswith("```sql"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1]) if len(lines) > 2 else sql
        
        return sql
    
    def summarize(self, query: str, data: str) -> str:
        """
        데이터 요약
        
        Args:
            query: 원본 질문
            data: DB 조회 결과 JSON 문자열
            
        Returns:
            요약된 응답 (그래프가 필요한 경우 HTML 포함)
        """
        # 그래프가 필요한지 확인 (추이, 그래프, 차트 등의 키워드)
        needs_graph = any(keyword in query.lower() for keyword in ["추이", "그래프", "차트", "chart", "trend"])
        
        if needs_graph:
            # 그래프 포함 HTML 응답 생성
            prompt = f"""다음 질문과 데이터를 바탕으로 HTML 형식의 답변을 작성해주세요.

질문: {query}

데이터:
{data}

요구사항:
1. 데이터를 바탕으로 질문에 대한 답변을 작성하세요.
2. 자연스러운 한국어로 답변하세요.
3. **중요**: 답변은 HTML 형식으로 작성하되, 다음을 포함하세요:
   - 텍스트 설명
   - 데이터를 시각화한 HTML/CSS 그래프 (추이 그래프, 막대 그래프, 파이 차트 등 질문에 맞는 형태)
   - 그래프는 순수 HTML/CSS로 작성 (외부 라이브러리 사용 금지)
   - 그래프는 <div> 태그와 CSS 스타일을 사용하여 시각적으로 표현
   - 데이터 값은 실제 데이터를 기반으로 정확하게 표시
4. 마크다운 형식(**굵게**)을 사용하여 중요한 숫자나 통계를 강조하세요.
5. HTML 태그는 이스케이프하지 말고 그대로 포함하세요.

답변 형식:
- HTML 형식으로 작성
- <div> 태그로 그래프 영역 구분
- CSS 스타일을 <style> 태그나 inline style로 포함
- 예시: 막대 그래프는 <div>의 width나 height로 표현, 추이 그래프는 점과 선으로 표현

답변:"""
        else:
            # 일반 텍스트 응답
            prompt = f"""다음 질문과 데이터를 바탕으로 자연스럽고 명확한 답변을 작성해주세요.

질문: {query}

데이터:
{data}

요구사항:
1. 데이터를 바탕으로 질문에 대한 답변을 작성하세요.
2. 자연스러운 한국어로 답변하세요.
3. 불필요한 설명은 생략하고 핵심 내용만 전달하세요.
4. 숫자나 통계가 있다면 마크다운 형식(**굵게**)으로 강조하세요.

답변:"""

        if self.provider == "gemini":
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            summary = response.content.strip() if hasattr(response, 'content') else str(response)
            
            # 마크다운을 HTML로 변환
            if needs_graph:
                summary = self._normalize_text_with_html(summary)
            else:
                summary = self._normalize_text_with_html(summary)
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
        
        return summary
    
    def is_schema_related_query(self, query: str) -> bool:
        """
        질문이 스키마 관련 질문인지 판단
        
        Args:
            query: 사용자 질문
            
        Returns:
            True: 스키마 관련 질문, False: 일반 질문
        """
        prompt = f"""다음 질문이 데이터베이스 스키마(발주, 입고, 품목, 거래처 등)와 관련된 질문인지 판단해주세요.

질문: {query}

판단 기준:
- 데이터베이스의 테이블, 컬럼, 데이터를 조회하는 질문이면 "YES"
- 발주, 입고, 품목, 거래처, 건수, 조회, 데이터 등과 관련된 질문이면 "YES"
- 일반적인 지식 질문(프로그래밍, 날씨, 역사 등)이면 "NO"
- 단순히 개념을 묻는 질문이면 "NO"

답변은 반드시 "YES" 또는 "NO"만 반환하세요."""

        if self.provider == "gemini":
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            answer = response.content.strip() if hasattr(response, 'content') else str(response)
            
            # YES/NO 판단
            answer_upper = answer.upper()
            if "YES" in answer_upper:
                return True
            elif "NO" in answer_upper:
                return False
            else:
                # 명확하지 않으면 키워드 기반 판단
                query_lower = query.lower()
                schema_keywords = ["발주", "입고", "품목", "거래처", "건수", "조회", "데이터", "pkfl", "pk_date", "pk_pdat", "pk_ldat"]
                return any(keyword in query_lower for keyword in schema_keywords)
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
    
    def chat(self, question: str) -> str:
        """
        일반 질문에 대한 답변 생성
        
        Args:
            question: 사용자 질문
            
        Returns:
            생성된 답변
        """
        prompt = f"""다음 질문에 대해 자연스럽고 명확한 답변을 작성해주세요.

질문: {question}

요구사항:
1. 질문에 정확하고 유용한 답변을 제공하세요.
2. 자연스러운 한국어로 답변하세요.
3. 불필요한 설명은 생략하고 핵심 내용만 전달하세요.
4. 모르는 내용이면 솔직하게 모른다고 답변하세요.

답변:"""

        if self.provider == "gemini":
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            answer = response.content.strip() if hasattr(response, 'content') else str(response)
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
        
        return answer
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        질문을 분류하여 필요한 행동 유형을 결정
        
        Args:
            query: 사용자 질문
            
        Returns:
            분류 결과 딕셔너리:
                - action_type: "SQL", "REPORT", "GENERAL_CHAT" 중 하나
                - chat_answer: action_type이 GENERAL_CHAT일 경우 답변
                - query: action_type이 SQL 또는 REPORT일 경우 원본/정제된 질문
        """
        # JSON Schema 정의
        json_schema = {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["SQL", "REPORT", "GENERAL_CHAT"],
                    "description": "질문의 유형. SQL: 단순 데이터 조회 질문, REPORT: 분석/보고서가 필요한 복합 질문, GENERAL_CHAT: 일반 대화 질문"
                },
                "chat_answer": {
                    "type": "string",
                    "description": "action_type이 GENERAL_CHAT일 경우 Gemini가 생성한 답변"
                },
                "query": {
                    "type": "string",
                    "description": "action_type이 SQL 또는 REPORT일 경우 원본 질문 또는 정제된 질문"
                }
            },
            "required": ["action_type"]
        }
        
        prompt = f"""다음 사용자 질문을 분석하여 필요한 행동 유형을 결정하고, 아래 JSON 형식으로만 응답하세요.

사용자 질문: {query}

판단 기준:
1. **SQL**: 데이터 조회 질문 (예: "8월 발주 건수는?", "거래처 목록 보여줘", "발주 현황 분석해줘", "월별 발주 추이 비교", "거래처별 발주 패턴 분석")
   - 단순 조회 질문
   - 분석, 비교, 트렌드, 요약 등의 질문이지만 **문서/보고서/차트 생성 요청이 없는 경우**
   - "분석해줘", "비교해줘", "현황 알려줘", "추이 보여줘" 등 → 일반 텍스트로 답변
   
2. **REPORT**: **명시적으로 문서/보고서/차트 생성 요청**이 있는 질문
   - "보고서를 만들어줘", "차트를 만들어줘", "문서로 만들어줘", "HTML로 만들어줘"
   - "보고서 작성해줘", "차트 작성해줘", "문서 작성해줘"
   - "보고서로 정리해줘", "차트로 보여줘", "문서 형태로 만들어줘"
   - **중요**: 단순히 "분석해줘", "비교해줘", "현황 알려줘"만 있으면 SQL 타입으로 분류 (일반 텍스트 답변)
   
3. **GENERAL_CHAT**: 데이터베이스와 무관한 일반 질문 (예: "파이썬이 뭐야?", "날씨 알려줘")
   - 스키마, 발주, 입고, 품목 등과 무관한 질문
   - 이 경우 chat_answer에 직접 답변을 생성하세요

중요 규칙:
- 반드시 아래 JSON 형식으로만 응답하세요.
- action_type이 GENERAL_CHAT인 경우에만 chat_answer를 작성하세요.
- action_type이 SQL 또는 REPORT인 경우 query에 원본 질문을 그대로 반환하세요.
- JSON 외의 다른 텍스트는 포함하지 마세요.
- **REPORT는 반드시 "보고서/차트/문서 만들기" 같은 명시적 요청이 있을 때만 사용하세요.**

응답 형식 (JSON):
{{
    "action_type": "SQL" | "REPORT" | "GENERAL_CHAT",
    "chat_answer": "GENERAL_CHAT인 경우에만 답변",
    "query": "SQL 또는 REPORT인 경우 원본 질문"
}}"""

        if self.provider == "gemini":
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            content = response.content.strip() if hasattr(response, 'content') else str(response)
            
            # JSON 추출 (마크다운 코드 블록 제거)
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            if content.startswith("```json"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            # JSON 파싱
            try:
                result = json.loads(content)
                # 필수 필드 검증
                if "action_type" not in result:
                    raise ValueError("action_type 필드가 없습니다.")
                
                # action_type 검증
                if result["action_type"] not in ["SQL", "REPORT", "GENERAL_CHAT"]:
                    raise ValueError(f"잘못된 action_type: {result['action_type']}")
                
                return result
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON 파싱 오류: {e}")
                print(f"응답 내용: {content}")
                # JSON 파싱 실패 시 기본값 반환
                return {
                    "action_type": "GENERAL_CHAT",
                    "chat_answer": "죄송합니다. 질문을 이해하는데 문제가 발생했습니다. 다시 질문해주세요.",
                    "query": None
                }
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
    
    def generate_report(self, query: str, data: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Gemini에게 HTML 기반 보고서를 요청
        
        Args:
            query: 사용자 질문
            data: DB 조회 결과 데이터 (JSON 문자열, 선택사항)
            
        Returns:
            Tuple(summary_text, html_report)
        """
        print(f"📝 generate_report 호출: query={query[:50]}..., data={data is not None}")
        
        try:
            base_instructions = """
응답은 반드시 아래 JSON 형식을 따르세요:
{
  "summary": "<자연어 요약 (마크다운 허용)>",
  "html_report": "<!DOCTYPE html>로 시작하는 완전한 HTML 문서 문자열>",
  "notes": "<선택 사항>"
}

HTML 규칙:
- 완전한 HTML 문서 구조를 포함하세요 (<html>, <head>, <body>).
- 기본 스타일을 위해 inline CSS를 head에 포함하세요 (폰트, 색상, 카드 스타일 등).
- 최소 1개의 데이터 요약 표를 포함하세요.
- 가능하면 간단한 막대/bar 스타일 차트를 CSS로 표현하세요 (예: div 막대).
- 외부 라이브러리는 사용하지 마세요. 순수 HTML/CSS만 사용하세요.
- 데이터가 없으면 합리적인 가상 수치를 사용하지만, 가상의 값임을 명시하세요.
"""
            if data:
                print("📝 데이터 기반 보고서 프롬프트 생성 중...")
                prompt = f"""다음 질문과 데이터를 바탕으로 HTML 보고서를 작성해주세요.

질문: {query}

데이터:
{data}

{base_instructions}
"""
            else:
                print("📝 텍스트 기반 보고서 프롬프트 생성 중...")
                prompt = f"""다음 질문에 대한 HTML 보고서를 작성해주세요.

질문: {query}

{base_instructions}
"""

            print("📝 Gemini API 호출 중...")
            if self.provider != "gemini":
                raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
            
            messages = [HumanMessage(content=prompt)]
            response = self.model.invoke(messages)
            raw_output = response.content.strip() if hasattr(response, 'content') else str(response)
            print(f"✅ Gemini API 응답 수신: 길이={len(raw_output)} 문자")
            
            # 코드 블록 제거
            if raw_output.startswith("```"):
                lines = raw_output.split("\n")
                raw_output = "\n".join(lines[1:-1]) if len(lines) > 2 else raw_output
            if raw_output.startswith("```json"):
                lines = raw_output.split("\n")
                raw_output = "\n".join(lines[1:-1]) if len(lines) > 2 else raw_output
            
            summary_text = ""
            html_report: Optional[str] = None
            
            try:
                report_data = json.loads(raw_output)
                summary_text = report_data.get("summary", "").strip()
                html_report = report_data.get("html_report")
                notes = report_data.get("notes")
                
                if notes:
                    summary_text = f"{summary_text}\n\n[추가 안내]\n{notes}"
                
                print("✅ JSON 파싱 완료")
            except json.JSONDecodeError:
                print("⚠️  JSON 파싱 실패, 원문을 그대로 사용합니다.")
                summary_text = raw_output
            
            if not html_report:
                print("⚠️  html_report 없음, 기본 HTML 템플릿 생성")
                html_report = self._build_basic_html(summary_text)
            else:
                html_report = self._normalize_html(html_report)
            
            print(f"✅ generate_report 완료: 요약 길이={len(summary_text)} 문자, HTML 길이={len(html_report)} 문자")
            return summary_text, html_report
        except Exception as e:
            import traceback
            print(f"❌ generate_report 오류: {e}")
            print(f"❌ 상세 오류: {traceback.format_exc()}")
            raise

    def _build_basic_html(self, summary: str) -> str:
        """요약 텍스트 기반 기본 HTML 템플릿 생성"""
        safe_summary = summary.replace("\n", "<br>")
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>AI 보고서</title>
  <style>
    body {{
      font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
      margin: 0;
      padding: 32px;
      background: #f4f6fb;
      color: #1f2a44;
      line-height: 1.6;
    }}
    .card {{
      background: #ffffff;
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 20px 60px rgba(15, 23, 42, 0.15);
      max-width: 960px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 2rem;
      margin-bottom: 1rem;
    }}
  </style>
</head>
<body>
  <main class="card">
    <h1>AI 생성 보고서</h1>
    <p>{safe_summary}</p>
  </main>
</body>
</html>"""

    def _normalize_text_with_html(self, text: str) -> str:
        """일반 텍스트 응답의 마크다운 스타일(**bold**)을 HTML 태그로 치환"""
        if not text:
            return text
        
        # 1. 리스트 형식의 제품명과 금액 강조: "1. **제품명**: 금액원" -> "1. <strong>제품명</strong>: <strong>금액원</strong>"
        def repl_list_item(match):
            num = match.group(1)  # 숫자.
            product = match.group(2)  # 제품명
            amount = match.group(3)  # 금액
            return f"{num}<strong>{product}</strong>: <strong>{amount}</strong>"
        
        # 패턴: 숫자. **제품명**: 금액원 (금액은 숫자와 쉼표, 원 포함)
        text = re.sub(
            r"(\d+\.\s+)\*\*(.+?)\*\*:\s+([\d,]+원)",
            repl_list_item,
            text,
            flags=re.MULTILINE
        )
        
        # 2. 리스트 형식의 월별 데이터 강조: "*   **1월:** 32,400.0" -> "*   <strong>1월:</strong> 32,400.0"
        def repl_month_item(match):
            month = match.group(1)  # 월
            value = match.group(2)  # 값
            return f"*   <strong>{month}:</strong> {value}"
        
        # 패턴: *   **월:** 값
        text = re.sub(
            r"\*\s+\*\*(\d+월):\*\*\s+([\d,\.]+)",
            repl_month_item,
            text,
            flags=re.MULTILINE
        )
        
        # 3. 일반 **bold** -> <strong>bold</strong>
        def repl(match):
            return f"<strong>{match.group(1)}</strong>"
        text = re.sub(r"\*\*(.+?)\*\*", repl, text, flags=re.DOTALL)
        
        # 4. 줄바꿈을 <br>로 변환 (HTML이 아닌 경우)
        if "<html" not in text.lower() and "<div" not in text.lower():
            text = text.replace("\n", "<br>")
        
        return text
    
    def _normalize_html(self, html: str) -> str:
        """HTML 보고서의 마크다운 스타일(**bold**)을 HTML 태그로 치환"""
        if not html:
            return html
        
        # 1. 리스트 형식의 제품명과 금액 강조: "1. **제품명**: 금액원" -> "1. <strong>제품명</strong>: <strong>금액원</strong>"
        def repl_list_item(match):
            num = match.group(1)  # 숫자.
            product = match.group(2)  # 제품명
            amount = match.group(3)  # 금액
            return f"{num}<strong>{product}</strong>: <strong>{amount}</strong>"
        
        # 패턴: 숫자. **제품명**: 금액원 (금액은 숫자와 쉼표, 원 포함)
        html = re.sub(
            r"(\d+\.\s+)\*\*(.+?)\*\*:\s+([\d,]+원)",
            repl_list_item,
            html,
            flags=re.MULTILINE
        )
        
        # 2. 일반 **bold** -> <strong>bold</strong>
        def repl(match):
            return f"<strong>{match.group(1)}</strong>"
        html = re.sub(r"\*\*(.+?)\*\*", repl, html, flags=re.DOTALL)
        
        return html

