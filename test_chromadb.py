"""
ChromaDB 연결 테스트 스크립트
"""
import chromadb
from config import settings

def test_chromadb_connection():
    """ChromaDB 연결 및 컬렉션 상태 확인"""
    print("=" * 50)
    print("ChromaDB 연결 테스트")
    print("=" * 50)
    
    try:
        # ChromaDB 서버 연결
        print(f"\n1. ChromaDB 서버 연결 시도...")
        print(f"   호스트: {settings.CHROMA_HOST}")
        print(f"   포트: {settings.CHROMA_PORT}")
        
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        
        # 서버 상태 확인
        heartbeat = client.heartbeat()
        print(f"   ✅ 연결 성공! (heartbeat: {heartbeat})")
        
        # 컬렉션 목록 확인
        print(f"\n2. 컬렉션 목록 확인...")
        collections = client.list_collections()
        print(f"   총 {len(collections)}개의 컬렉션 발견:")
        for col in collections:
            print(f"   - {col.name} (id: {col.id})")
        
        # 타겟 컬렉션 확인
        collection_name = settings.CHROMA_COLLECTION_NAME
        print(f"\n3. 타겟 컬렉션 확인: '{collection_name}'")
        
        try:
            collection = client.get_collection(name=collection_name)
            count = collection.count()
            print(f"   ✅ 컬렉션 존재함")
            print(f"   📊 총 문서 수: {count}")
            
            # 샘플 데이터 확인
            if count > 0:
                print(f"\n4. 샘플 데이터 확인...")
                sample = collection.get(limit=3)
                if sample and 'documents' in sample:
                    print(f"   📄 샘플 문서 {len(sample['documents'])}개:")
                    for i, doc in enumerate(sample['documents'][:3], 1):
                        preview = doc[:200] + "..." if len(doc) > 200 else doc
                        print(f"   {i}. {preview}")
                else:
                    print("   ⚠️  문서 데이터가 없습니다.")
            else:
                print(f"   ⚠️  컬렉션이 비어있습니다. ingest_schema.py를 실행하세요.")
        except Exception as e:
            print(f"   ❌ 컬렉션을 찾을 수 없습니다: {e}")
            print(f"   💡 ingest_schema.py를 실행하여 스키마를 적재하세요.")
        
        print("\n" + "=" * 50)
        print("테스트 완료!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 연결 실패: {e}")
        print(f"\n확인 사항:")
        print(f"1. ChromaDB 서버가 실행 중인지 확인하세요.")
        print(f"2. 호스트({settings.CHROMA_HOST})와 포트({settings.CHROMA_PORT})가 올바른지 확인하세요.")
        print(f"3. 서버 실행 명령: chroma run --path ./chroma_data --port {settings.CHROMA_PORT}")

if __name__ == "__main__":
    test_chromadb_connection()

