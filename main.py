"""
hcManAi - AI 마이크로서비스
FastAPI를 사용한 REST API 서버
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
import uvicorn
import json
from rag_service import RAGService
from llm_service import LLMService
from config import settings


app = FastAPI(
    title="hcManAi",
    description="AI 마이크로서비스 - Text-to-SQL 및 데이터 요약",
    version="1.0.0"
)

# 전역 서비스 인스턴스
rag_service: Optional[RAGService] = None
llm_service: Optional[LLMService] = None


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    global rag_service, llm_service
    try:
        rag_service = RAGService()
        llm_service = LLMService()
        print("✅ 서비스 초기화 완료")
    except Exception as e:
        print(f"❌ 서비스 초기화 실패: {e}")
        raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 유효성 검증 오류 핸들러"""
    print(f"❌ 요청 유효성 검증 실패:")
    print(f"   URL: {request.url}")
    print(f"   Method: {request.method}")
    try:
        body = await request.body()
        print(f"   요청 본문: {body.decode('utf-8')}")
    except Exception as e:
        print(f"   요청 본문 읽기 실패: {e}")
    print(f"   오류 상세: {exc.errors()}")
    
    # 오류 메시지를 JSON 직렬화 가능한 형태로 변환
    errors = []
    for error in exc.errors():
        error_dict = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": error.get("input")
        }
        # ctx에 있는 error 객체는 문자열로 변환
        if "ctx" in error and "error" in error["ctx"]:
            error_dict["ctx"] = {"error": str(error["ctx"]["error"])}
        errors.append(error_dict)
    
    return JSONResponse(
        status_code=422,
        content={"detail": errors}
    )


# Request/Response 모델
class GenerateSQLRequest(BaseModel):
    query: str


class GenerateSQLResponse(BaseModel):
    sql: str


class SummarizeRequest(BaseModel):
    query: str
    data: str


class SummarizeResponse(BaseModel):
    response: str


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


class QueryRequest(BaseModel):
    """통합 질문 요청 모델"""
    question: str


class QueryResponse(BaseModel):
    """통합 질문 응답 모델"""
    question_type: str  # "schema" 또는 "general"
    sql: Optional[str] = None  # 스키마 질문인 경우 SQL
    answer: Optional[str] = None  # 일반 질문인 경우 답변


class ClassifyQueryRequest(BaseModel):
    """질문 분류 요청 모델
    
    백엔드 호환성을 위해 다음 필드들을 모두 지원합니다:
    - question: 백엔드에서 주로 사용하는 필드명
    - query: 대체 필드명
    - message: 대체 필드명
    - data: SQL 실행 결과 데이터 (JSON 문자열, 선택사항)
    """
    question: Optional[str] = None
    query: Optional[str] = None
    message: Optional[str] = None
    data: Optional[str] = None  # SQL 실행 결과 데이터 (REPORT 타입일 때 사용)
    
    @model_validator(mode='after')
    def validate_query_or_message(self):
        """question, query, message 중 하나는 필수"""
        if not self.question and not self.query and not self.message:
            raise ValueError("question, query 또는 message 필드 중 하나는 필수입니다.")
        return self
    
    def get_query(self) -> str:
        """question, query 또는 message 필드에서 질문을 가져옴 (우선순위: question > query > message)"""
        if self.question:
            return self.question
        if self.query:
            return self.query
        if self.message:
            return self.message
        raise ValueError("question, query 또는 message 필드가 필요합니다.")
    
    class Config:
        # 추가 필드 허용 (백엔드 호환성)
        extra = "allow"


class QueryClassificationResponse(BaseModel):
    """질문 분류 응답 모델"""
    action_type: str  # "SQL", "REPORT", "GENERAL_CHAT" 중 하나
    chat_answer: Optional[str] = None  # action_type이 GENERAL_CHAT일 경우 답변
    query: Optional[str] = None  # action_type이 SQL 또는 REPORT일 경우 원본/정제된 질문
    sql: Optional[str] = None  # 생성된 SQL (SQL/REPORT 타입에 활용)
    report_html: Optional[str] = None  # Gemini가 생성한 HTML 보고서 또는 추가 안내


class GenerateReportRequest(BaseModel):
    """보고서 생성 요청 모델"""
    query: str
    data: str  # DB 조회 결과 데이터 (JSON 문자열)


class GenerateReportResponse(BaseModel):
    """보고서 생성 응답 모델"""
    report: str  # 생성된 보고서
    report_html: Optional[str] = None  # 생성된 HTML 보고서


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "hcManAi",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


@app.post("/generate-sql", response_model=GenerateSQLResponse)
async def generate_sql(request: GenerateSQLRequest):
    """
    SQL 생성 API
    
    RAG 파이프라인을 통해 사용자 질문을 SQL 쿼리로 변환합니다.
    
    - 질문 유형 판단 (스키마 관련 질문인지 확인)
    - 입력된 query를 임베딩으로 변환
    - Vector DB에서 유사한 스키마 힌트 검색
    - LLM에 MS-SQL 생성 요청
    """
    if rag_service is None or llm_service is None:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")
    
    try:
        # 1. 질문 유형 판단 (스키마 관련 질문인지 확인)
        is_schema_query = llm_service.is_schema_related_query(request.query)
        print(f"🔍 질문 유형 판단: {'스키마 관련 질문' if is_schema_query else '일반 질문'}")
        
        if not is_schema_query:
            # 일반 질문이면 특별한 HTTP 상태 코드 반환 (Java에서 감지 가능하도록)
            print(f"ℹ️  일반 질문으로 판단됨. /chat 엔드포인트 사용을 권장합니다.")
            raise HTTPException(
                status_code=400, 
                detail="GENERAL_QUESTION: 이 질문은 일반 질문입니다. /chat 엔드포인트를 사용해주세요."
            )
        
        # 2. 스키마 관련 질문이면 SQL 생성
        sql = rag_service.generate_sql(request.query)
        return GenerateSQLResponse(sql=sql)
    except HTTPException:
        # HTTPException은 그대로 전달
        raise
    except Exception as e:
        import traceback
        error_detail = f"SQL 생성 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ 에러 상세: {error_detail}")
        raise HTTPException(status_code=500, detail=f"SQL 생성 중 오류 발생: {str(e)}")


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    """
    결과 요약 API
    
    질문과 DB 조회 결과를 바탕으로 자연스러운 답변을 생성합니다.
    
    - LLM에게 질문과 데이터를 전달
    - 자연스러운 한국어 답변 생성
    """
    if llm_service is None:
        raise HTTPException(status_code=500, detail="LLM 서비스가 초기화되지 않았습니다.")
    
    try:
        response = llm_service.summarize(request.query, request.data)
        return SummarizeResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 생성 중 오류 발생: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    일반 질문 답변 API
    
    스키마와 관련 없는 일반적인 질문에 대해 Gemini를 활용하여 답변을 생성합니다.
    
    - LLM에게 질문을 전달
    - 자연스러운 한국어 답변 생성
    """
    if llm_service is None:
        raise HTTPException(status_code=500, detail="LLM 서비스가 초기화되지 않았습니다.")
    
    try:
        answer = llm_service.chat(request.question)
        return ChatResponse(answer=answer)
    except Exception as e:
        import traceback
        error_detail = f"일반 질문 답변 생성 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ 에러 상세: {error_detail}")
        raise HTTPException(status_code=500, detail=f"일반 질문 답변 생성 중 오류 발생: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    통합 질문 API
    
    백엔드에서 하나의 호출로 질문을 보내면, 자동으로 질문 유형을 판단하여
    적절한 응답을 반환합니다.
    
    - 스키마 관련 질문: SQL 쿼리 생성
    - 일반 질문: 자연어 답변 생성
    
    Returns:
        QueryResponse:
            - question_type: "schema" 또는 "general"
            - sql: 스키마 질문인 경우 생성된 SQL (일반 질문이면 None)
            - answer: 일반 질문인 경우 생성된 답변 (스키마 질문이면 None)
    """
    if rag_service is None or llm_service is None:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")
    
    try:
        # 1. 질문 유형 판단
        is_schema_query = llm_service.is_schema_related_query(request.question)
        print(f"🔍 질문 유형 판단: {'스키마 관련 질문' if is_schema_query else '일반 질문'}")
        
        if is_schema_query:
            # 2-1. 스키마 관련 질문이면 SQL 생성
            sql = rag_service.generate_sql(request.question)
            return QueryResponse(
                question_type="schema",
                sql=sql,
                answer=None
            )
        else:
            # 2-2. 일반 질문이면 답변 생성
            answer = llm_service.chat(request.question)
            return QueryResponse(
                question_type="general",
                sql=None,
                answer=answer
            )
    except Exception as e:
        import traceback
        error_detail = f"질문 처리 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ 에러 상세: {error_detail}")
        raise HTTPException(status_code=500, detail=f"질문 처리 중 오류 발생: {str(e)}")


@app.post("/classify-query", response_model=QueryClassificationResponse)
async def classify_query(request: ClassifyQueryRequest):
    """
    질문 분류 API
    
    사용자의 질문을 분석하여 필요한 행동 유형을 결정하고,
    적절한 응답을 반환합니다.
    
    - SQL: 단순 데이터 조회 질문 → query에 원본 질문 반환
    - REPORT: 분석/보고서가 필요한 복합 질문 → 보고서 생성 후 chat_answer에 반환
    - GENERAL_CHAT: 일반 대화 질문 → chat_answer에 답변 반환
    
    Returns:
        QueryClassificationResponse:
            - action_type: "SQL", "REPORT", "GENERAL_CHAT" 중 하나
            - chat_answer: action_type이 GENERAL_CHAT 또는 REPORT일 경우 답변/보고서
            - query: action_type이 SQL 또는 REPORT일 경우 원본/정제된 질문
    """
    if rag_service is None or llm_service is None:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")
    
    try:
        # query 또는 message 필드에서 질문 추출
        user_query = request.get_query()
        print(f"📥 classify-query 요청 수신: query={user_query}")
        
        # 1. 질문 분류
        classification = llm_service.classify_query(user_query)
        action_type = classification.get("action_type", "GENERAL_CHAT")
        print(f"🔍 질문 분류 결과: {action_type}")
        
        # 2. action_type에 따른 처리
        if action_type == "GENERAL_CHAT":
            # 일반 대화 질문: 이미 chat_answer가 포함되어 있음
            chat_answer = classification.get("chat_answer")
            if not chat_answer:
                # chat_answer가 없으면 생성
                chat_answer = llm_service.chat(user_query)
            
            return QueryClassificationResponse(
                action_type=action_type,
                chat_answer=chat_answer,
                query=None
            )
        
        elif action_type == "SQL":
            query_text = classification.get("query", user_query)
            print("📝 SQL 질문 처리 중...")
            generated_sql = rag_service.generate_sql(query_text)
            data = request.data
            
            if data:
                print(f"📊 SQL 결과 데이터 제공됨 (길이: {len(data)}). 요약 생성 중...")
                summary = llm_service.summarize(query_text, data)
                print("✅ SQL 결과 요약 생성 완료")
                return QueryClassificationResponse(
                    action_type=action_type,
                    chat_answer=summary,
                    query=query_text,
                    sql=generated_sql
                )
            else:
                guidance = (
                    "SQL을 생성했습니다. 먼저 아래 SQL을 실행하여 얻은 결과를 JSON 형태로 "
                    "'data' 필드에 담아 다시 요청해주시면 요약을 제공할 수 있습니다."
                )
                return QueryClassificationResponse(
                    action_type=action_type,
                    chat_answer=guidance,
                    query=query_text,
                    sql=generated_sql
                )
        
        elif action_type == "REPORT":
            # REPORT 질문: 먼저 SQL을 제공하고, 데이터가 있으면 HTML 보고서 생성
            query_text = classification.get("query", user_query)
            
            print(f"📊 보고서 생성을 위한 SQL 생성 중...")
            sql = rag_service.generate_sql(query_text)
            print(f"📝 생성된 SQL: {sql}")
            
            data = request.data
            print(f"🔍 데이터 확인: data 제공 여부={data is not None}")
            if data:
                print(f"📊 데이터 기반 보고서 생성 중... (데이터 크기: {len(data)} 문자)")
                report_text, html_report = llm_service.generate_report(query_text, data)
                print(f"✅ 보고서 생성 완료: 보고서 길이={len(report_text)} 문자")
                print(f"🔍 보고서 미리보기: {report_text[:200]}...")
                
                response = QueryClassificationResponse(
                    action_type=action_type,
                    chat_answer=report_text,
                    query=query_text,
                    sql=sql,
                    report_html=html_report
                )
                print(f"🔍 응답 객체 생성 완료: HTML 길이={len(html_report) if html_report else 0}")
                return response
            else:
                guidance = (
                    "보고서를 생성하려면 아래 SQL을 먼저 실행하여 결과를 JSON으로 만든 뒤 "
                    "'data' 필드에 담아 다시 요청해주세요."
                )
                return QueryClassificationResponse(
                    action_type=action_type,
                    chat_answer=guidance,
                    query=query_text,
                    sql=sql
                )
        
        else:
            # 예상치 못한 action_type
            raise ValueError(f"알 수 없는 action_type: {action_type}")
            
    except Exception as e:
        import traceback
        error_detail = f"질문 분류 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ 에러 상세: {error_detail}")
        raise HTTPException(status_code=500, detail=f"질문 분류 중 오류 발생: {str(e)}")


@app.post("/generate-report", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest):
    """
    보고서 생성 API
    
    질문과 DB 조회 결과 데이터를 바탕으로 Gemini 분석 도구를 활용하여
    상세한 분석 보고서를 생성합니다.
    
    - 질문과 데이터를 분석하여 인사이트 도출
    - 트렌드, 패턴, 비교 분석 포함
    - 자연스러운 한국어 보고서 생성
    - Gemini에게 Google Slides URL 요청 (실제 파일이 아닐 수 있음)
    
    Returns:
        GenerateReportResponse:
            - report: 생성된 요약 텍스트
            - report_html: Gemini가 생성한 HTML 보고서 (선택사항)
    """
    if llm_service is None:
        raise HTTPException(status_code=500, detail="LLM 서비스가 초기화되지 않았습니다.")
    
    try:
        print(f"📊 보고서 생성 중...")
        print(f"📝 질문: {request.query}")
        print(f"📊 데이터 크기: {len(request.data)} 문자")
        
        report, html_report = llm_service.generate_report(request.query, request.data)
        print(f"✅ 보고서 생성 완료: 길이={len(report)} 문자")
        
        return GenerateReportResponse(report=report, report_html=html_report)
    except Exception as e:
        import traceback
        error_detail = f"보고서 생성 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ 에러 상세: {error_detail}")
        raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )

