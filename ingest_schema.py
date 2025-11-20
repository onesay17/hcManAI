"""
스키마 적재 스크립트 (Gemini 임베딩 사용)
schema_guide.txt 파일을 읽어 Vector DB에 적재합니다.
"""
import os

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import chromadb


def main():
    """
    schema_guide.txt 파일의 내용을 읽어 ChromaDB 서버에 적재(Ingestion)합니다.
    (Gemini 임베딩 모델 사용 버전)
    """
    print("Vector DB 적재 스크립트 시작 (Gemini 모델 사용)...")

    # 0. .env 파일에서 Google API 키 로드
    load_dotenv()
    if "GOOGLE_API_KEY" not in os.environ:
        print("오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("`.env` 파일에 Gemini API 키를 설정하세요.")
        return

    # 1. 설정 변수
    from config import settings
    SOURCE_DOCUMENT_PATH = "./schema_guide.txt"
    CHROMA_DB_HOST = settings.CHROMA_HOST
    CHROMA_DB_PORT = settings.CHROMA_PORT
    COLLECTION_NAME = settings.CHROMA_COLLECTION_NAME

    try:
        # 2. ChromaDB 서버에 연결
        # chromadb 1.x에서는 HttpClient 대신 Client를 사용하고 host/port를 설정합니다
        client = chromadb.HttpClient(
            host=CHROMA_DB_HOST,
            port=CHROMA_DB_PORT
        )
        print(f"ChromaDB 서버 ({CHROMA_DB_HOST}:{CHROMA_DB_PORT})에 연결 시도...")
        client.heartbeat()
        print("ChromaDB 서버 연결 성공.")
    except Exception as e:
        print("오류: ChromaDB 서버에 연결할 수 없습니다. (서버가 실행 중인지 확인하세요)")
        print(f"에러 상세: {e}")
        return

    # 3. [업데이트 로직] 기존 컬렉션이 있다면 삭제
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"기존 '{COLLECTION_NAME}' 컬렉션을 삭제했습니다. (업데이트를 위해)")
    except Exception:
        print(f"'{COLLECTION_NAME}' 컬렉션이 존재하지 않거나 삭제 중 오류 발생. 새로 생성합니다.")

    # 4. 문서 로드 및 분할
    try:
        loader = TextLoader(SOURCE_DOCUMENT_PATH, encoding="utf-8")
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)

        print(f"'{SOURCE_DOCUMENT_PATH}' 로드 및 분할 완료. 총 {len(splits)}개 조각 생성.")
    except Exception as e:
        print(f"오류: 문서 로드 중 예외 발생 - {e}")
        return

    # 5. Gemini 임베딩 모델 준비 (최신 모델 사용)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    # 6. LangChain Chroma 래퍼를 사용하여 Vector DB에 적재
    print(f"'{COLLECTION_NAME}' 컬렉션에 데이터 적재 시작...")
    try:
        Chroma.from_documents(
            client=client,
            documents=splits,
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
        )
        print("=" * 50)
        print("성공: Vector DB에 스키마 정보 적재가 완료되었습니다. (Gemini)")
        print(f"총 {len(splits)}개의 문서 조각이 '{COLLECTION_NAME}'에 저장되었습니다.")
        print("=" * 50)
    except Exception as e:
        print(f"오류: Vector DB 데이터 적재 중 예외 발생 - {e}")


if __name__ == "__main__":
    main()

