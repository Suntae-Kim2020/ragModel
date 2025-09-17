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
    
    def search_similar_chunks(self, query_embedding: List[float], assistant_id: str = None, size: int = 5) -> List[Dict]:
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

    def hybrid_search(self, query_text: str, query_embedding: List[float], assistant_id: str = None, size: int = 20) -> List[Dict]:
        """하이브리드 검색: 키워드 검색 + 벡터 검색을 RRF로 결합"""
        
        # 1. 키워드 검색 (BM25)
        keyword_query = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["content^2", "document_title^1.5"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "_source": ["content", "document_title", "page_number", "chunk_index", "tags", "organization", "document_type", "assistant_id"]
        }
        
        # 2. 벡터 검색 (KNN)
        vector_query = {
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
        
        # Assistant ID 필터 추가
        if assistant_id:
            keyword_query["query"]["bool"]["filter"] = [{"term": {"assistant_id": assistant_id}}]
            vector_query["query"]["bool"]["filter"] = [{"term": {"assistant_id": assistant_id}}]
        
        # 두 검색 실행
        try:
            keyword_response = self.client.search(index=self.index_name, body=keyword_query)
            vector_response = self.client.search(index=self.index_name, body=vector_query)
            
            keyword_hits = keyword_response['hits']['hits']
            vector_hits = vector_response['hits']['hits']
            
            # RRF (Reciprocal Rank Fusion) 적용
            return self._apply_rrf(keyword_hits, vector_hits, size)
            
        except Exception as e:
            print(f"하이브리드 검색 오류: {e}")
            # 실패시 벡터 검색만 수행
            if assistant_id:
                vector_query["query"]["bool"]["filter"] = [{"term": {"assistant_id": assistant_id}}]
            response = self.client.search(index=self.index_name, body=vector_query)
            return response['hits']['hits']
    
    def _apply_rrf(self, keyword_hits: List[Dict], vector_hits: List[Dict], final_size: int, k: int = 60) -> List[Dict]:
        """Reciprocal Rank Fusion 알고리즘 적용"""
        scores = {}
        
        # 키워드 검색 결과에 RRF 점수 할당
        for rank, hit in enumerate(keyword_hits, 1):
            doc_id = f"{hit['_source']['document_title']}_{hit['_source']['page_number']}_{hit['_source']['chunk_index']}"
            scores[doc_id] = scores.get(doc_id, {'hit': hit, 'score': 0})
            scores[doc_id]['score'] += 1 / (k + rank)
        
        # 벡터 검색 결과에 RRF 점수 할당
        for rank, hit in enumerate(vector_hits, 1):
            doc_id = f"{hit['_source']['document_title']}_{hit['_source']['page_number']}_{hit['_source']['chunk_index']}"
            scores[doc_id] = scores.get(doc_id, {'hit': hit, 'score': 0})
            scores[doc_id]['score'] += 1 / (k + rank)
        
        # 점수순 정렬하고 상위 결과 반환
        sorted_results = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
        
        # 결과에 RRF 점수 추가
        final_results = []
        for item in sorted_results[:final_size]:
            hit = item['hit']
            hit['_score'] = item['score']  # RRF 점수로 대체
            final_results.append(hit)
        
        return final_results
    
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