"""
RAG 서비스 모듈
임베딩 생성, Vector DB 검색, SQL 생성 파이프라인을 처리합니다.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List
from config import settings
from llm_service import LLMService


class RAGService:
    """RAG 서비스 클래스"""
    
    def __init__(self):
        """RAG 서비스 초기화"""
        # ChromaDB 클라이언트 연결
        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        
        # 컬렉션 가져오기 또는 생성
        try:
            self.collection = self.chroma_client.get_collection(
                name=settings.CHROMA_COLLECTION_NAME
            )
        except Exception:
            # 컬렉션이 없으면 생성
            self.collection = self.chroma_client.create_collection(
                name=settings.CHROMA_COLLECTION_NAME
            )
        
        # LLM 서비스 초기화
        self.llm_service = LLMService()
        
        # 임베딩 모델 초기화
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """임베딩 모델 초기화 (Gemini 사용)"""
        if not settings.GOOGLE_API_KEY:
            raise ValueError("임베딩 모델을 사용하기 위해 GOOGLE_API_KEY가 필요합니다.")
        
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GOOGLE_API_KEY
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터
        """
        return self.embeddings.embed_query(text)
    
    def search_similar_schemas(self, query: str, top_k: int = None) -> List[str]:
        """
        Vector DB에서 유사한 스키마 힌트 검색
        
        Args:
            query: 사용자 질문
            top_k: 가져올 결과 개수
            
        Returns:
            유사한 스키마 힌트 리스트
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        # 쿼리 임베딩 생성
        query_embedding = self.generate_embedding(query)
        
        # Vector DB에서 유사 문서 검색 (더 많은 결과 가져오기)
        try:
            # 컬렉션의 전체 문서 수 확인
            collection_count = self.collection.count()
            print(f"📊 Vector DB 컬렉션 총 문서 수: {collection_count}")
            
            # 검색할 개수를 컬렉션 크기에 맞게 조정
            search_k = min(top_k * 2, max(collection_count, top_k))
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=search_k
            )
            
            # 검색 결과에서 문서 텍스트 추출
            documents = results.get('documents', [])
            print(f"🔍 Vector DB 검색 결과: {len(documents)}개 문서 발견")
            
            if documents and len(documents) > 0:
                found_docs = documents[0]  # 첫 번째 쿼리의 결과 리스트
                print(f"📄 검색된 스키마 힌트 개수: {len(found_docs)}")
                if len(found_docs) > 0:
                    print(f"📝 첫 번째 힌트 미리보기: {found_docs[0][:300]}...")
                    # 모든 검색 결과를 반환 (더 많은 컨텍스트 제공)
                    return found_docs
            else:
                # 검색 결과가 없으면 전체 컬렉션에서 가져오기
                print("⚠️  검색 결과가 없어 전체 스키마를 가져옵니다.")
                all_results = self.collection.get()
                if all_results and 'documents' in all_results:
                    all_docs = all_results['documents']
                    print(f"📚 전체 스키마 문서 수: {len(all_docs)}")
                    return all_docs[:top_k] if all_docs else []
        except Exception as e:
            print(f"❌ Vector DB 검색 오류: {e}")
            # 오류 발생 시 전체 컬렉션에서 가져오기
            try:
                all_results = self.collection.get()
                if all_results and 'documents' in all_results:
                    all_docs = all_results['documents']
                    print(f"📚 전체 스키마 문서 수: {len(all_docs)}")
                    return all_docs[:top_k] if all_docs else []
            except Exception as e2:
                print(f"❌ 전체 스키마 가져오기 오류: {e2}")
        
        print("⚠️  검색 결과가 없습니다.")
        return []
    
    def generate_sql(self, query: str) -> str:
        """
        RAG 파이프라인을 통해 SQL 생성
        
        Args:
            query: 사용자 질문
            
        Returns:
            생성된 SQL 쿼리
        """
        print(f"📥 사용자 질문: {query}")
        
        # 1. Vector DB에서 유사한 스키마 힌트 검색
        similar_schemas = self.search_similar_schemas(query)
        
        # 2. 스키마 힌트 조합
        schema_hints = "\n\n".join(similar_schemas) if similar_schemas else "스키마 정보를 찾을 수 없습니다."
        print(f"📋 전달된 스키마 힌트 길이: {len(schema_hints)} 문자")
        if len(schema_hints) > 500:
            print(f"📋 스키마 힌트 미리보기: {schema_hints[:500]}...")
        else:
            print(f"📋 스키마 힌트: {schema_hints}")
        
        # 3. LLM에 SQL 생성 요청
        sql = self.llm_service.generate_sql(query, schema_hints)
        print(f"✅ 생성된 SQL: {sql}")
        
        return sql

