from opensearchpy import OpenSearch
import os
from typing import List, Dict, Any
import json

class OpenSearchClient:
    def __init__(self):
        self.host = os.getenv("OPENSEARCH_HOST", "localhost")
        self.port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        self.index_name = os.getenv("OPENSEARCH_INDEX", "rag_documents")
        
        self.client = OpenSearch(
            hosts=[{'host': self.host, 'port': self.port}],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )
        
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        if not self.client.indices.exists(index=self.index_name):
            index_body = {
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 384,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "lucene"
                            }
                        },
                        "document_id": {"type": "keyword"},
                        "document_title": {"type": "text"},
                        "page_number": {"type": "integer"},
                        "chunk_index": {"type": "integer"},
                        "tags": {"type": "keyword"},
                        "organization": {"type": "keyword"},
                        "document_type": {"type": "keyword"},
                        "upload_date": {"type": "date"},
                        "assistant_id": {"type": "keyword"}
                    }
                },
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                }
            }
            
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Created index: {self.index_name}")
    
    def add_document_chunk(self, chunk_data: Dict[str, Any]) -> str:
        # 매번 인덱스 존재 확인 및 생성 (올바른 매핑 보장)
        self._create_index_if_not_exists()
        
        response = self.client.index(
            index=self.index_name,
            body=chunk_data
        )
        return response['_id']
    
    def search_similar_chunks(self, query_embedding: List[float], assistant_id: str = None, size: int = 20) -> List[Dict]:
        query = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding,
                                    "k": size
                                }
                            }
                        }
                    ]
                }
            },
            "_source": ["content", "document_title", "page_number", "chunk_index", "tags", "organization", "document_type", "assistant_id"]
        }
        
        if assistant_id:
            query["query"]["bool"]["filter"] = [{"term": {"assistant_id": assistant_id}}]
        
        response = self.client.search(index=self.index_name, body=query)
        return response['hits']['hits']

    
    def get_assistants(self, organization: str = None) -> List[str]:
        query = {
            "aggs": {
                "assistants": {
                    "terms": {
                        "field": "assistant_id",
                        "size": 100
                    }
                }
            },
            "size": 0
        }
        
        # 조직별 필터 추가
        if organization:
            query["query"] = {
                "term": {
                    "organization": organization
                }
            }
        
        response = self.client.search(index=self.index_name, body=query)
        assistants = []
        if 'aggregations' in response and 'assistants' in response['aggregations']:
            for bucket in response['aggregations']['assistants']['buckets']:
                assistants.append(bucket['key'])
        
        return assistants