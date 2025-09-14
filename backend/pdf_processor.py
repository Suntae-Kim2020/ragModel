import pdfplumber
import PyPDF2
from typing import List, Dict, Any
import re
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime

class PDFProcessor:
    def __init__(self):
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    def extract_text_from_pdf(self, pdf_file_path: str) -> Dict[str, Any]:
        """PDF에서 텍스트를 추출하고 머리말/꼬리말을 제거"""
        pages_text = []
        
        with pdfplumber.open(pdf_file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    cleaned_text = self._remove_headers_footers(text, page_num)
                    if cleaned_text.strip():
                        pages_text.append({
                            'page_number': page_num,
                            'content': cleaned_text
                        })
        
        return {
            'pages': pages_text,
            'total_pages': len(pages_text)
        }
    
    def _remove_headers_footers(self, text: str, page_num: int) -> str:
        """머리말과 꼬리말 제거"""
        lines = text.split('\n')
        
        if len(lines) <= 5:
            return text
        
        # 머리말 제거 (상위 2-3줄에서 페이지 번호나 제목이 반복되는 패턴)
        header_patterns = [
            r'^\d+\s*$',  # 페이지 번호만 있는 줄
            r'^페이지\s*\d+',  # "페이지 숫자" 패턴
            r'^- \d+ -',  # "- 숫자 -" 패턴
        ]
        
        # 상위 3줄 검사
        start_idx = 0
        for i in range(min(3, len(lines))):
            line = lines[i].strip()
            if any(re.match(pattern, line) for pattern in header_patterns):
                start_idx = i + 1
            elif len(line) < 50 and i < 2:  # 짧은 제목 줄
                start_idx = i + 1
        
        # 꼬리말 제거 (하위 2-3줄에서 페이지 번호 패턴)
        end_idx = len(lines)
        for i in range(len(lines) - 1, max(len(lines) - 4, 0), -1):
            line = lines[i].strip()
            if any(re.match(pattern, line) for pattern in header_patterns):
                end_idx = i
        
        return '\n'.join(lines[start_idx:end_idx]).strip()
    
    def chunk_text(self, pages_text: List[Dict], chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
        """텍스트를 청크로 분할"""
        chunks = []
        chunk_index = 0
        
        for page_data in pages_text:
            page_num = page_data['page_number']
            content = page_data['content']
            
            if len(content) <= chunk_size:
                chunks.append({
                    'chunk_index': chunk_index,
                    'page_number': page_num,
                    'content': content,
                    'start_char': 0,
                    'end_char': len(content)
                })
                chunk_index += 1
            else:
                start = 0
                while start < len(content):
                    end = min(start + chunk_size, len(content))
                    
                    # 단어 경계에서 자르기
                    if end < len(content):
                        # 뒤로 가면서 공백이나 문장 끝을 찾기
                        for i in range(end, max(start, end - 100), -1):
                            if content[i] in [' ', '\n', '.', '!', '?', '。', '!', '?']:
                                end = i + 1
                                break
                    
                    chunk_content = content[start:end].strip()
                    if chunk_content:
                        chunks.append({
                            'chunk_index': chunk_index,
                            'page_number': page_num,
                            'content': chunk_content,
                            'start_char': start,
                            'end_char': end
                        })
                        chunk_index += 1
                    
                    start = end - overlap if end < len(content) else end
        
        return chunks
    
    def create_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """청크에 대한 임베딩 생성"""
        texts = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts)
        
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i].tolist()
        
        return chunks
    
    def process_pdf_for_storage(
        self, 
        pdf_file_path: str, 
        document_title: str,
        tags: List[str],
        organization: str,
        document_type: str,
        assistant_id: str
    ) -> Dict[str, Any]:
        """PDF를 처리하여 저장 준비"""
        
        document_id = str(uuid.uuid4())
        
        # 1. PDF에서 텍스트 추출
        extracted_data = self.extract_text_from_pdf(pdf_file_path)
        
        # 2. 텍스트 청킹
        chunks = self.chunk_text(extracted_data['pages'])
        
        # 3. 임베딩 생성
        chunks_with_embeddings = self.create_embeddings(chunks)
        
        # 4. 메타데이터 추가
        processed_chunks = []
        for chunk in chunks_with_embeddings:
            chunk_data = {
                'document_id': document_id,
                'document_title': document_title,
                'content': chunk['content'],
                'embedding': chunk['embedding'],
                'page_number': chunk['page_number'],
                'chunk_index': chunk['chunk_index'],
                'tags': tags,
                'organization': organization,
                'document_type': document_type,
                'assistant_id': assistant_id,
                'upload_date': datetime.now().isoformat(),
                'start_char': chunk['start_char'],
                'end_char': chunk['end_char']
            }
            processed_chunks.append(chunk_data)
        
        return {
            'document_id': document_id,
            'total_chunks': len(processed_chunks),
            'total_pages': extracted_data['total_pages'],
            'chunks': processed_chunks
        }