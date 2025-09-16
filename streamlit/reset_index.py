from opensearch_client import OpenSearchClient
import os

def reset_opensearch_index():
    """OpenSearch 인덱스를 삭제하고 새로 생성"""
    client = OpenSearchClient()
    
    try:
        # 기존 인덱스 삭제
        if client.client.indices.exists(index=client.index_name):
            response = client.client.indices.delete(index=client.index_name)
            print(f"기존 인덱스 '{client.index_name}' 삭제 완료: {response}")
        else:
            print(f"인덱스 '{client.index_name}'가 존재하지 않습니다.")
        
        # 새 인덱스 생성 (OpenSearchClient의 __init__에서 자동으로 생성됨)
        new_client = OpenSearchClient()
        print(f"새로운 인덱스 '{new_client.index_name}' 생성 완료")
        
        return True
        
    except Exception as e:
        print(f"인덱스 리셋 실패: {e}")
        return False

if __name__ == "__main__":
    success = reset_opensearch_index()
    if success:
        print("✅ OpenSearch 인덱스 리셋 완료!")
        print("이제 모든 PDF 문서를 새로운 1500자 청크 설정으로 재업로드하세요.")
    else:
        print("❌ 인덱스 리셋 실패!")