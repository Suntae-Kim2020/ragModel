import openai
from typing import List, Dict, Any, Optional
import os
import re
from sentence_transformers import SentenceTransformer
from opensearch_client import OpenSearchClient

class RAGService:
    def __init__(self):
        # OpenAI API 키가 있는 경우에만 클라이언트 초기화
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "sk-proj-your-actual-api-key-here":
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            self.openai_client = None
        
        # SentenceTransformer 초기화 (키워드 추출에는 OpenSearch 불필요)
        try:
            self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        except Exception as e:
            print(f"Warning: Embedding model initialization failed: {e}")
            self.embedding_model = None
        
        # OpenSearch 클라이언트는 선택적으로 초기화
        try:
            self.opensearch_client = OpenSearchClient()
        except Exception as e:
            print(f"Warning: OpenSearch client initialization failed: {e}")
            self.opensearch_client = None
    
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
    
    def _extract_keywords_from_filename(self, filename: str) -> List[str]:
        """파일명에서 키워드를 추출합니다."""
        # 파일 확장자 제거
        clean_filename = re.sub(r'\.(pdf|hwp|docx?|txt)$', '', filename, flags=re.IGNORECASE)
        
        # 날짜 패턴 제거 (2025.08.01 형식)
        clean_filename = re.sub(r'\d{4}\.\d{1,2}\.\d{1,2}', '', clean_filename)
        
        # 특수문자를 공백으로 변경
        clean_filename = re.sub(r'[_\-\(\)\[\]{}]', ' ', clean_filename)
        
        keywords = []
        
        # 미리 정의된 패턴 매칭
        patterns = {
            '학사운영위원회': ['학사운영위원회', '학사운영', '운영위원회', '학사', '위원회'],
            '규정': ['규정'],
            '개정': ['개정'],
            '제정': ['제정'],
            '지침': ['지침'],
            '세칙': ['세칙'],
            '학사': ['학사'],
            '입학': ['입학'],
            '졸업': ['졸업'],
            '장학': ['장학'],
            '연구': ['연구'],
            '총무': ['총무'],
            '교무': ['교무'],
            '학생': ['학생'],
            '대학원': ['대학원'],
            '전북대': ['전북대학교', '전북대'],
            '전북대학교': ['전북대학교', '전북대'],
        }
        
        # 패턴 매칭으로 키워드 추출
        for pattern, related_keywords in patterns.items():
            if pattern in clean_filename:
                keywords.extend(related_keywords)
        
        # 추가로 2글자 이상의 한글 단어들 추출
        words = clean_filename.split()
        for word in words:
            word = word.strip()
            if len(word) >= 2 and re.search(r'[가-힣]', word):
                if word not in keywords:
                    keywords.append(word)
        
        # 중복 제거 및 길이순 정렬
        unique_keywords = list(set(keywords))
        unique_keywords.sort(key=len, reverse=True)
        
        return unique_keywords[:8]  # 상위 8개만 반환
    
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
                # Fallback to filename extraction
                return self._extract_keywords_from_filename(text)
            
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
                    # If not a list, fallback to filename extraction
                    return self._extract_keywords_from_filename(text)
            except json.JSONDecodeError:
                # If JSON parsing fails, fallback to filename extraction
                return self._extract_keywords_from_filename(text)
                
        except Exception as e:
            print(f"OpenAI keyword extraction failed: {e}")
            # Fallback to filename extraction
            return self._extract_keywords_from_filename(text)
    
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
    
    def get_individual_answers(self, question: str, assistant_ids: List[str], summary_mode: bool = False) -> Dict[str, Any]:
        """각 assistant별로 개별 응답을 생성하여 비교할 수 있도록 합니다."""
        individual_responses = []
        all_keywords = set()
        
        # 비교 질문인 경우 개별 어시스턴트용 질문으로 변환
        comparison_keywords = ["비교", "차이", "다른점", "구별", "표", "분석", "대조", "vs", "versus", "비교분석", "항목별로", "항목별", "항목으로", "구분하여", "나누어"]
        is_comparison_question = any(keyword in question for keyword in comparison_keywords)
        
        for assistant_id in assistant_ids:
            try:
                # 비교 질문인 경우 개별 검색용 질문으로 변환
                if is_comparison_question:
                    # "휴학 규정을 항목별로 비교해줘" -> "휴학 규정에 대해 알려줘"
                    individual_question = self._convert_to_individual_question(question)
                else:
                    individual_question = question
                    
                response = self.get_answer(individual_question, assistant_id, summary_mode)
                individual_responses.append({
                    'assistant_id': assistant_id,
                    'assistant_name': assistant_id,  # TODO: Get actual assistant name from DB
                    'answer': response['answer'],
                    'sources': response['sources'],
                    'confidence': response['confidence'],
                    'keywords': response['keywords']
                })
                # Collect all keywords
                if 'keywords' in response:
                    all_keywords.update(response['keywords'])
            except Exception as e:
                individual_responses.append({
                    'assistant_id': assistant_id,
                    'assistant_name': assistant_id,
                    'answer': f"죄송합니다. 이 어시스턴트에서 답변을 생성하는 중 오류가 발생했습니다: {str(e)}",
                    'sources': [],
                    'confidence': 0.0,
                    'keywords': [],
                    'error': str(e)
                })
        
        # 비교 키워드 확인 및 자동 비교표 생성
        comparison_keywords = ["비교", "차이", "다른점", "구별", "표", "분석", "대조", "vs", "versus", "비교분석", "항목별로", "항목별", "항목으로", "구분하여", "나누어"]
        has_comparison = any(keyword in question for keyword in comparison_keywords)
        
        result = {
            'response_type': 'individual',
            'individual_responses': individual_responses,
            'total_assistants': len(assistant_ids),
            'keywords': list(all_keywords)
        }
        
        # 비교 키워드가 있고 2개 이상의 어시스턴트가 있으면 비교표 생성
        if has_comparison and len(assistant_ids) >= 2 and len(individual_responses) >= 2:
            try:
                comparison_table = self._generate_comparison_table(question, individual_responses)
                if comparison_table:
                    result['comparison_table'] = comparison_table
            except Exception as e:
                print(f"비교표 생성 중 오류: {str(e)}")
        
        return result
    
    def _convert_to_individual_question(self, question: str) -> str:
        """비교 질문을 개별 검색용 질문으로 변환합니다."""
        # 비교 관련 키워드 제거하고 핵심 주제만 추출
        comparison_patterns = [
            r'을?\s*항목별로\s*비교해?[달라|줘]?',
            r'를?\s*항목별로\s*비교해?[달라|줘]?',
            r'을?\s*비교해?[달라|줘]?',
            r'를?\s*비교해?[달라|줘]?',
            r'항목별로\s*',
            r'비교해?[달라|줘]?',
            r'차이점?을?\s*',
            r'다른점?을?\s*',
            r'구별해?[달라|줘]?',
            r'분석해?[달라|줘]?',
            r'대조해?[달라|줘]?'
        ]
        
        import re
        converted_question = question
        
        # 패턴별로 제거
        for pattern in comparison_patterns:
            converted_question = re.sub(pattern, '', converted_question)
        
        # 공백 정리
        converted_question = re.sub(r'\s+', ' ', converted_question).strip()
        
        # 기본 질문 형태로 변환
        if not converted_question.endswith(('에 대해', '에 대해서', '에 관해', '에 관해서', '은?', '는?', '을?', '를?')):
            if converted_question:
                converted_question += '에 대해 알려줘'
            else:
                converted_question = question  # 변환 실패시 원본 사용
        else:
            converted_question += ' 알려줘'
            
        return converted_question
    
    def _expand_short_query(self, question: str) -> str:
        """짧은 질의를 확장하여 검색 품질 향상"""
        # 일반적인 학사 관련 짧은 질의 확장 패턴
        expansion_patterns = {
            # 학사 관련
            '휴학': '휴학 신청 방법 절차 조건',
            '복학': '복학 신청 방법 절차 조건',
            '등록': '등록금 납부 방법 기간',
            '수강': '수강신청 방법 절차 기간',
            '졸업': '졸업 요건 조건 절차',
            '학점': '학점 이수 요건 조건',
            '성적': '성적 평가 기준 방법',
            '장학금': '장학금 신청 방법 조건',
            '전과': '전과 신청 방법 조건',
            '부전공': '부전공 신청 방법 조건',
            '복수전공': '복수전공 신청 방법 조건',
            '학사경고': '학사경고 기준 조치',
            '계절학기': '계절학기 신청 방법',
            '교환학생': '교환학생 신청 방법',
            
            # 행정 관련
            '등록증명서': '등록증명서 발급 방법',
            '재학증명서': '재학증명서 발급 방법',
            '성적증명서': '성적증명서 발급 방법',
            '졸업증명서': '졸업증명서 발급 방법',
            
            # 기타
            '기숙사': '기숙사 신청 방법 조건',
            '도서관': '도서관 이용 방법 시간'
        }
        
        # 키워드가 포함된 경우 확장
        for keyword, expansion in expansion_patterns.items():
            if keyword in question:
                return f"{question} {expansion}"
        
        # 패턴에 없는 경우 일반적인 확장
        if '?' in question or '무엇' in question or '어떻게' in question:
            return f"{question} 방법 절차 조건"
        else:
            return f"{question}에 대해 자세히 알려주세요"
    
    def _generate_comparison_table(self, question: str, individual_responses: List[Dict]) -> str:
        """개별 응답들을 분석하여 비교표를 생성합니다."""
        try:
            # 어시스턴트별 답변 내용 정리 (길이 제한)
            assistant_data = {}
            for response in individual_responses:
                assistant_id = response['assistant_id']
                answer = response['answer']
                # 답변을 200자로 제한해서 토큰 절약
                truncated_answer = answer[:200] + "..." if len(answer) > 200 else answer
                assistant_data[assistant_id] = truncated_answer
            
            # OpenAI를 통해 비교표 생성
            if not self.openai_client:
                return None
                
            # 비교표 생성을 위한 강화된 프롬프트 (컬럼 정렬 개선)
            assistant_names = list(assistant_data.keys())
            comparison_prompt = f"""질문: {question}

각 어시스턴트의 답변:
{chr(10).join([f"어시스턴트 {aid}: {answer}" for aid, answer in assistant_data.items()])}

위 답변들을 분석하여 비교표를 생성해주세요. 다음 지침을 정확히 따라주세요:

1. 각 답변에서 관련 내용을 적극적으로 찾아 추출하세요
2. "구체적인 내용이 없다"거나 "나와있지 않다"는 답변이 있어도, 유사한 내용이나 관련 규정이 있다면 포함하세요
3. HTML 표 형식으로 구성하세요:
   - 첫 번째 열: 비교항목 (예: 신청 절차, 승인 조건, 기간 제한 등)
   - 이후 열들: 각 어시스턴트 ({', '.join(assistant_names)})
4. 각 셀은 간결하게 40자 이내로 요약하세요
5. 내용이 없는 경우에만 "명시되지 않음"으로 표시하세요

정확한 HTML 테이블 형식:
<table style="border-collapse: collapse; width: 100%; border: 1px solid #ddd;">
<thead>
<tr style="background-color: #f8f9fa;">
<th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">비교항목</th>
{chr(10).join([f'<th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">{aid}</th>' for aid in assistant_names])}
</tr>
</thead>
<tbody>
각 비교 항목별로 <tr> 행을 추가하세요
</tbody>
</table>

비교표를 위 형식으로 정확히 작성해주세요."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "간결한 비교표를 만드는 전문가입니다."},
                    {"role": "user", "content": comparison_prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"비교표 생성 실패: {str(e)}")
            return None
    
    def get_answer(self, question: str, assistant_id: Optional[str] = None, summary_mode: bool = False) -> Dict[str, Any]:
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
        
        # 0. 짧은 질의 확장 (3단어 이하인 경우)
        if len(question.split()) <= 3:
            question = self._expand_short_query(question)
        
        # 1. 질문에서 키워드 추출
        keywords = self._extract_keywords_from_question(question)
        
        # 2. 비교 모드 및 어시스턴트 조건 확인 (변수 초기화)
        comparison_keywords = ["비교", "차이", "다른점", "구별", "표", "분석", "대조", "vs", "versus", "비교분석"]
        has_comparison = any(keyword in question for keyword in comparison_keywords)
        multiple_assistants = isinstance(assistant_id, list) and len(assistant_id) > 1
        
        # 컨텍스트 길이 제한 설정 (비교 모드에서는 토큰 절약)
        content_limit = 300 if (summary_mode and has_comparison and multiple_assistants) else 1500
        
        # 3. 질문을 임베딩으로 변환
        question_embedding = self.embedding_model.encode(question).tolist()
        
        # 3. 하이브리드 검색으로 문서 청크 검색 (키워드 + 벡터 검색 with RRF)
        # top_k=5로 조정하여 관련성 높은 문서만 선별
        # 비교 모드에서는 컨텍스트 길이 제한을 고려하여 더 적은 청크 사용
        if summary_mode and has_comparison and multiple_assistants:
            search_size = 6  # 비교 모드 (8->6)
            assistant_search_size = 3  # 각 어시스턴트당 (4->3)
        else:
            search_size = 5 if summary_mode else 5  # 통일된 크기로 조정 (20->5, 10->5)
            assistant_search_size = 5 if summary_mode else 3  # 각 어시스턴트당 (10->5, 6->3)
        
        if isinstance(assistant_id, list):
            # 여러 어시스턴트에서 검색
            all_chunks = []
            for aid in assistant_id:
                # 하이브리드 검색 사용
                chunks = self.opensearch_client.hybrid_search(
                    question, 
                    question_embedding,
                    assistant_id=aid,
                    size=assistant_search_size  # 각 어시스턴트당 개수
                )
                all_chunks.extend(chunks)
            # 점수순으로 정렬하고 선택
            similar_chunks = sorted(all_chunks, key=lambda x: x['_score'], reverse=True)[:search_size]
        else:
            # 단일 어시스턴트 또는 전체 검색 - 하이브리드 검색 사용
            similar_chunks = self.opensearch_client.hybrid_search(
                question,
                question_embedding, 
                assistant_id=assistant_id,
                size=search_size
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
        
        # 4. OpenAI API로 답변 생성
        # Summary mode와 비교 질문에 따른 프롬프트 선택
        
        if summary_mode and (has_comparison or multiple_assistants):
            print(f"DEBUG: 비교 모드 진입 - summary_mode: {summary_mode}, has_comparison: {has_comparison}, multiple_assistants: {multiple_assistants}")
            # 어시스턴트별 문서 정리 - similar_chunks에서 직접 가져옴
            assistant_docs = {}
            for i, chunk in enumerate(similar_chunks):
                print(f"DEBUG: 청크 {i} 구조: {list(chunk.keys())}")
                print(f"DEBUG: _source 키들: {list(chunk['_source'].keys()) if '_source' in chunk else 'No _source'}")
                assistant = chunk['_source'].get('assistant_id', 'Unknown')
                print(f"DEBUG: 청크 {i} - assistant: {assistant}")
                if assistant not in assistant_docs:
                    assistant_docs[assistant] = []
                # sources에서 해당하는 source 찾기
                if i < len(sources):
                    assistant_docs[assistant].append(sources[i])
            
            print(f"DEBUG: assistant_docs keys: {list(assistant_docs.keys())}")
            
            assistant_list = list(assistant_docs.keys())
            context_by_assistant = ""
            
            for assistant, docs in assistant_docs.items():
                context_by_assistant += f"\n\n=== {assistant} 관련 문서 ===\n"
                for doc in docs:
                    content = doc.get('content', '').strip()
                    if content:  # 내용이 있을 때만 추가
                        context_by_assistant += f"[{doc.get('document_title', 'Unknown')} - 페이지 {doc.get('page_number', 'Unknown')}]\n"
                        # 비교 모드에서는 각 문서 내용을 더 짧게 제한
                        truncated_content = content[:content_limit]
                        if len(content) > content_limit:
                            truncated_content += "..."
                        context_by_assistant += f"{truncated_content}\n\n"
            
            # 표 헤더 생성
            table_headers = '<th style="border: 1px solid #ddd; padding: 8px;">비교항목</th>'
            for assistant in assistant_list:
                table_headers += f'<th style="border: 1px solid #ddd; padding: 8px;">{assistant}</th>'
            
            # 예시 행 생성
            example_row = '<td style="border: 1px solid #ddd; padding: 8px;">비교기준</td>'
            for _ in assistant_list:
                example_row += '<td style="border: 1px solid #ddd; padding: 8px;">해당 내용</td>'
            
            system_prompt = f"""
당신은 규정과 지침 문서를 바탕으로 정확한 답변을 제공하는 전문 어시스턴트입니다.

지침:
1. 제공된 어시스턴트별 문서 내용을 바탕으로 비교 분석하세요.
2. 각 어시스턴트별로 차이점을 반드시 HTML 표 형태로 정리해서 답변하세요.
3. 표는 다음과 같은 형태로 작성하세요 (어시스턴트 ID가 컬럼, 비교항목이 행):
   <table style="border-collapse: collapse; width: 100%;">
   <thead><tr style="background-color: #f0f0f0;">{table_headers}</tr></thead>
   <tbody>
   <tr>{example_row}</tr>
   </tbody>
   </table>
4. 표의 각 셀에는 해당 어시스턴트의 관련 내용을 구체적으로 기재하세요.
5. 표 작성 시 다음 사항을 준수하세요:
   - 첫 번째 컬럼은 비교항목(기준)이고, 나머지 컬럼은 각 어시스턴트 ID입니다.
   - 각 행은 하나의 비교기준을 나타냅니다.
   - 동일한 항목에 대한 각 어시스턴트의 내용을 비교할 수 있도록 구성하세요.
6. 표 외에도 핵심 차이점과 공통점을 요약해서 설명하세요.
7. 답변의 근거가 되는 문서와 페이지를 명시하세요.
8. 한국어로 답변하세요.

어시스턴트별 문서 내용:
{context_by_assistant}
"""
        elif summary_mode:
            system_prompt = """
당신은 규정과 지침 문서를 바탕으로 정확한 답변을 제공하는 전문 어시스턴트입니다.

지침:
1. 제공된 문서 내용만을 바탕으로 답변하세요.
2. 내용을 체계적으로 요약하여 답변하세요.
3. 중요한 포인트들을 정리해서 제시하세요.
4. 답변의 근거가 되는 문서와 페이지를 명시하세요.
5. 명확하고 구체적으로 답변하세요.
6. 한국어로 답변하세요.
"""
        else:
            system_prompt = """
당신은 규정과 지침 문서를 바탕으로 정확한 답변을 제공하는 전문 어시스턴트입니다.

지침:
1. 제공된 문서 내용만을 바탕으로 답변하세요.
2. 답변할 수 없는 내용이라면 솔직히 모른다고 하세요.
3. 답변의 근거가 되는 문서와 페이지를 명시하세요.
4. 명확하고 구체적으로 답변하세요.
5. 한국어로 답변하세요.
"""
        
        # 모든 모드에서 동일한 방식으로 컨텍스트 생성
        context = ""
        
        for source in sources:
            source_data = source.get('_source', source)
            content = source_data.get('content', '').strip()
            if content:  # 내용이 있을 때만 컨텍스트에 추가
                context += f"[{source_data.get('document_title', 'Unknown')} - 페이지 {source_data.get('page_number', 'Unknown')}]\n"
                # 컨텍스트 길이 제한 적용
                truncated_content = content[:content_limit]
                if len(content) > content_limit:
                    truncated_content += "..."
                context += f"{truncated_content}\n\n"
        
        user_prompt = f"""
질문: {question}

관련 문서 내용:
{context}

위 문서를 바탕으로 질문에 답변해주세요. 답변의 근거가 되는 문서명과 페이지를 반드시 명시해주세요.
"""
        
        try:
            # Check if OpenAI API key is properly configured
            if not self.openai_client:
                # Provide a basic answer using retrieved documents without OpenAI
                answer = f"관련 문서 {len(sources)}개를 찾았습니다.\n\n"
                for i, source in enumerate(sources[:3], 1):
                    source_data = source.get('_source', source)
                    content = source_data.get('content', '').strip()
                    if content:  # 내용이 있을 때만 표시
                        answer += f"{i}. {source_data.get('document_title', 'Unknown')} (페이지 {source_data.get('page_number', 'Unknown')})\n"
                        answer += f"   내용: {content[:200]}...\n\n"
                
                
                return {
                    "response_type": "integrated",
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
                "response_type": "integrated",
                "answer": answer,
                "sources": sources,
                "confidence": min(similar_chunks[0]['_score'] if similar_chunks else 0, 1.0),
                "total_sources": len(sources),
                "keywords": keywords
            }
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"OpenAI API Error Details: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            # Provide helpful fallback when OpenAI is unavailable
            answer = f"💡 **검색된 관련 문서 정보**\n\n"
            for i, source in enumerate(sources[:3], 1):
                answer += f"**{i}. {source['document_title']}** (페이지 {source['page_number']})\n"
                content_preview = source['content'][:300] + "..." if len(source['content']) > 300 else source['content']
                answer += f"{content_preview}\n\n"
            
            if len(sources) > 3:
                answer += f"📄 총 {len(sources)}개의 관련 문서를 찾았습니다.\n\n"
            
            return {
                "response_type": "integrated",
                "answer": answer,
                "sources": sources,
                "confidence": 0.5,
                "keywords": keywords,
                "error": str(e)
            }