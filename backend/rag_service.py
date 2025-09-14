import openai
from typing import List, Dict, Any, Optional
import os
import re
from sentence_transformers import SentenceTransformer
from opensearch_client import OpenSearchClient

class RAGService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.opensearch_client = OpenSearchClient()
    
    def _extract_keywords_from_question(self, question: str) -> List[str]:
        """질문에서 핵심 키워드를 추출합니다."""
        # 불용어 목록 (한국어) - 더 포괄적으로 구성
        stop_words = {
            '은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', '의', '로', '으로', '도',
            '하다', '있다', '되다', '한다', '된다', '한', '할', '해', '하는', '하고', '하며',
            '무엇', '어떤', '어떻게', '왜', '언제', '어디서', '누가', '얼마나', '어디',
            '대해', '대한', '관련', '관하여', '대하여', '무엇인지', '그', '저', '제',
            '알려주세요', '설명해주세요', '가르쳐주세요', '말해주세요', '알려줘', '설명해줘',
            '그리고', '또한', '그런데', '하지만', '그러나', '따라서', '그래서',
            '작성하나요', '작성해주세요', '해주세요', '알고', '싶습니다', '합니다', '인가요',
            '있나요', '있습니까', '합니까', '주세요', '해', '줘'
        }
        
        # 특수문자와 물음표 제거
        cleaned_question = re.sub(r'[?!.,;:]', '', question)
        words = cleaned_question.split()
        
        # 키워드 추출 및 조사 제거
        keywords = []
        for word in words:
            # 불용어가 아니고, 2글자 이상이고, 한글이 포함된 단어
            if (word not in stop_words and 
                len(word) >= 2 and 
                re.search(r'[가-힣]', word)):
                # 조사 제거 ('는', '은', '를', '을', '가', '이' 등)
                cleaned_word = word
                for suffix in ['는', '은', '를', '을', '가', '이', '에서', '에게', '으로', '로', '와', '과']:
                    if word.endswith(suffix) and len(word) > len(suffix):
                        cleaned_word = word[:-len(suffix)]
                        break
                
                if len(cleaned_word) >= 2:
                    keywords.append(cleaned_word)
        
        return keywords
    
    def extract_keywords_with_openai(self, text: str) -> List[str]:
        """OpenAI API를 사용하여 텍스트에서 한국어 키워드를 추출합니다."""
        
        system_prompt = """
당신은 한국의 대학 행정 문서에서 키워드를 추출하는 전문가입니다.

주어진 문서 제목에서 다음과 같은 키워드들을 추출해주세요:
1. 기관명 (예: 전북대학교, 대학원 등)
2. 부서/조직명 (예: 학사운영위원회, 총무처 등)
3. 문서 유형 (예: 규정, 지침, 세칙, 법령 등)
4. 업무 영역 (예: 학사, 입학, 졸업, 장학, 연구 등)
5. 상태/버전 (예: 개정, 제정, 신설, 폐지 등)
6. 핵심 개념어 (예: 학점, 시험, 수업, 등록 등)

규칙:
- 복합어를 단계별로 분해해서 추출 (예: "학사운영위원회" → ["학사운영위원회", "학사운영", "운영위원회", "학사", "위원회"])
- 의미있는 단어만 추출 (조사, 어미 등은 제외)
- 2글자 이상의 단어만 추출
- 중복 제거
- 긴 키워드부터 정렬

응답은 반드시 JSON 배열 형태로만 반환하세요.
예시: ["학사운영위원회", "학사운영", "운영위원회", "학사", "위원회", "규정", "개정"]
"""
        
        user_prompt = f"다음 문서 제목에서 키워드를 추출해주세요:\n\n{text}"
        
        try:
            # Check if OpenAI API key is configured
            if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-proj-your-actual-api-key-here":
                # Fallback to manual extraction
                return self._extract_keywords_from_question(text)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                keywords = json.loads(result)
                if isinstance(keywords, list):
                    # Filter and clean keywords
                    cleaned_keywords = [
                        keyword.strip() 
                        for keyword in keywords 
                        if isinstance(keyword, str) and len(keyword.strip()) >= 2
                    ]
                    return cleaned_keywords[:10]  # Limit to top 10 keywords
                else:
                    # If not a list, fallback to manual extraction
                    return self._extract_keywords_from_question(text)
            except json.JSONDecodeError:
                # If JSON parsing fails, fallback to manual extraction
                return self._extract_keywords_from_question(text)
                
        except Exception as e:
            print(f"OpenAI keyword extraction failed: {e}")
            # Fallback to manual extraction
            return self._extract_keywords_from_question(text)
    
    def _highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """텍스트에서 키워드를 하이라이트합니다. 부분 매치와 유사 단어도 포함."""
        if not keywords:
            return text
        
        highlighted_text = text
        
        for keyword in keywords:
            # 1. 정확한 매치
            if keyword in highlighted_text:
                highlighted_text = re.sub(
                    f'({re.escape(keyword)})', 
                    r'<mark>\1</mark>', 
                    highlighted_text, 
                    flags=re.IGNORECASE
                )
            else:
                # 2. 부분 매치 (2글자 이상일 때)
                if len(keyword) >= 3:
                    for i in range(len(keyword)-1):
                        partial = keyword[i:i+2]
                        if partial in highlighted_text and len(partial) >= 2:
                            highlighted_text = re.sub(
                                f'({re.escape(partial)})', 
                                r'<mark>\1</mark>', 
                                highlighted_text, 
                                flags=re.IGNORECASE
                            )
                            break
                
                # 3. 관련 단어 매치
                related_words = {
                    '재학기간': ['재학', '학기', '기간', '수학'],
                    '연장': ['연장', '연기', '기간'],
                    '신청서': ['신청', '서류', '신청서', '허가']
                }
                
                if keyword in related_words:
                    for related in related_words[keyword]:
                        if related in highlighted_text:
                            highlighted_text = re.sub(
                                f'({re.escape(related)})', 
                                r'<mark>\1</mark>', 
                                highlighted_text, 
                                flags=re.IGNORECASE
                            )
        
        # 중복 마크업 제거
        highlighted_text = re.sub(r'<mark>(<mark>[^<]*</mark>)</mark>', r'\1', highlighted_text)
        highlighted_text = re.sub(r'<mark><mark>([^<]*)</mark></mark>', r'<mark>\1</mark>', highlighted_text)
        
        return highlighted_text
    
    def get_answer(self, question: str, assistant_id: Optional[str] = None) -> Dict[str, Any]:
        # UTF-8 인코딩 문제 해결
        try:
            if isinstance(question, bytes):
                question = question.decode('utf-8')
            # 인코딩이 깨진 경우 복구 시도
            elif 'ì' in question or 'ë' in question:
                # 인코딩이 잘못된 경우 재인코딩
                question = question.encode('latin1').decode('utf-8')
        except:
            pass  # 인코딩 복구 실패시 원본 사용
        
        # 1. 질문에서 키워드 추출
        keywords = self._extract_keywords_from_question(question)
        
        # 2. 질문을 임베딩으로 변환
        question_embedding = self.embedding_model.encode(question).tolist()
        
        # 3. 유사한 문서 청크 검색 (여러 어시스턴트 지원)
        if isinstance(assistant_id, list):
            # 여러 어시스턴트에서 검색
            all_chunks = []
            for aid in assistant_id:
                chunks = self.opensearch_client.search_similar_chunks(
                    question_embedding, 
                    assistant_id=aid,
                    size=3  # 각 어시스턴트당 3개씩
                )
                all_chunks.extend(chunks)
            # 점수순으로 정렬하고 상위 5개 선택
            similar_chunks = sorted(all_chunks, key=lambda x: x['_score'], reverse=True)[:5]
        else:
            # 단일 어시스턴트 또는 전체 검색
            similar_chunks = self.opensearch_client.search_similar_chunks(
                question_embedding, 
                assistant_id=assistant_id,
                size=5
            )
        
        if not similar_chunks:
            return {
                "answer": "죄송합니다. 관련된 문서를 찾을 수 없습니다.",
                "sources": [],
                "confidence": 0.0,
                "keywords": keywords
            }
        
        # 4. 컨텍스트 구성 및 키워드 하이라이트
        context_parts = []
        sources = []
        
        for hit in similar_chunks:
            source = hit['_source']
            score = hit['_score']
            
            # 원본 내용과 하이라이트된 내용 모두 저장
            original_content = source['content']
            highlighted_content = self._highlight_keywords(original_content, keywords)
            
            context_parts.append(f"문서: {source['document_title']}, 페이지: {source['page_number']}\n내용: {original_content}")
            
            sources.append({
                "document_title": source['document_title'],
                "page_number": source['page_number'],
                "chunk_index": source['chunk_index'],
                "content": original_content,
                "highlighted_content": highlighted_content,
                "tags": source['tags'],
                "organization": source['organization'],
                "document_type": source['document_type'],
                "relevance_score": score
            })
        
        context = "\n\n".join(context_parts)
        
        # 4. OpenAI API로 답변 생성
        system_prompt = """
당신은 규정과 지침 문서를 바탕으로 정확한 답변을 제공하는 전문 어시스턴트입니다.

지침:
1. 제공된 문서 내용만을 바탕으로 답변하세요.
2. 답변할 수 없는 내용이라면 솔직히 모른다고 하세요.
3. 답변의 근거가 되는 문서와 페이지를 명시하세요.
4. 명확하고 구체적으로 답변하세요.
5. 한국어로 답변하세요.
"""
        
        user_prompt = f"""
질문: {question}

관련 문서 내용:
{context}

위 문서를 바탕으로 질문에 답변해주세요. 답변의 근거가 되는 문서명과 페이지를 반드시 명시해주세요.
"""
        
        try:
            # Check if OpenAI API key is properly configured
            if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-proj-your-actual-api-key-here":
                # Provide a basic answer using retrieved documents without OpenAI
                answer = f"관련 문서 {len(sources)}개를 찾았습니다.\n\n"
                for i, source in enumerate(sources[:3], 1):
                    answer += f"{i}. {source['document_title']} (페이지 {source['page_number']})\n"
                    answer += f"   내용: {source['content'][:200]}...\n\n"
                
                answer += "더 정확한 답변을 위해서는 OpenAI API 키를 설정해주세요."
                
                return {
                    "answer": answer,
                    "sources": sources,
                    "confidence": min(similar_chunks[0]['_score'] if similar_chunks else 0, 1.0),
                    "total_sources": len(sources),
                    "keywords": keywords
                }
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": min(similar_chunks[0]['_score'] if similar_chunks else 0, 1.0),
                "total_sources": len(sources),
                "keywords": keywords
            }
            
        except Exception as e:
            # Fallback to basic document retrieval if OpenAI fails
            answer = f"OpenAI API 오류로 인해 기본 검색 결과를 제공합니다.\n\n"
            for i, source in enumerate(sources[:3], 1):
                answer += f"{i}. {source['document_title']} (페이지 {source['page_number']})\n"
                answer += f"   내용: {source['content'][:200]}...\n\n"
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": 0.5,
                "keywords": keywords,
                "error": str(e)
            }