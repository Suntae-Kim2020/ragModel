# RAG 문서 관리 시스템

PDF 문서를 업로드하고 벡터화하여 질의응답을 제공하는 시스템입니다.

## 주요 기능

### 관리자 기능
- PDF 문서 업로드 (머리말/꼬리말 자동 제거)
- 문서 태그 및 메타데이터 관리
- 기관별, 문서유형별 분류
- 어시스턴트(벡터스토어) 지정

### 사용자 기능
- 어시스턴트 선택
- 자연어 질의
- AI 답변 생성 (OpenAI GPT)
- 출처 정보 제공
- 원본 내용 확인 (스플릿 스크린)

## 시스템 구성

```
├── backend/          # FastAPI 백엔드
├── frontend/         # React 프론트엔드
├── docker-compose.yml # OpenSearch 설정
└── start.sh          # 시작 스크립트
```

## 설치 및 실행

### 1. 환경 설정
```bash
# .env 파일 생성
cp backend/.env.example backend/.env

# OpenAI API 키 설정
# backend/.env 파일에서 OPENAI_API_KEY 값 입력
```

### 2. 시스템 시작
```bash
./start.sh
```

### 3. 수동 실행 (개발용)
```bash
# OpenSearch 시작
docker-compose up -d

# 백엔드 시작
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 프론트엔드 시작
cd frontend
npm install
npm start
```

## 접속 주소

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **OpenSearch**: http://localhost:9200
- **OpenSearch Dashboard**: http://localhost:5601

## 사용 방법

### 문서 업로드 (관리자)
1. 관리자 페이지 접속
2. PDF 파일 선택
3. 문서 제목, 태그, 기관명 입력
4. 문서 유형 선택
5. 어시스턴트 ID 지정
6. 업로드 실행

### 질의응답 (사용자)
1. 사용자 페이지 접속
2. 어시스턴트 선택 (선택사항)
3. 질문 입력
4. 답변 확인
5. 우측 패널에서 출처 원본 확인

## API 엔드포인트

- `POST /upload-document` - 문서 업로드
- `GET /assistants` - 어시스턴트 목록
- `POST /query` - 질의응답
- `GET /health` - 헬스체크

## 기술 스택

- **Backend**: FastAPI, OpenSearch, SentenceTransformers
- **Frontend**: React, Material-UI
- **Database**: OpenSearch (벡터 검색)
- **LLM**: OpenAI GPT-4
- **PDF Processing**: pdfplumber, PyPDF2

## 특징

- **머리말/꼬리말 제거**: PDF에서 본문만 추출
- **스마트 청킹**: 문맥을 고려한 텍스트 분할
- **벡터 검색**: 의미적 유사도 기반 검색
- **정확한 출처 제공**: 페이지 및 원본 내용 표시
- **태그 시스템**: 문서 분류 및 필터링
- **스플릿 UI**: 답변과 출처를 동시에 확인

## 문제 해결

### OpenSearch 연결 오류
```bash
# OpenSearch 상태 확인
docker-compose ps

# 재시작
docker-compose restart
```

### Python 의존성 오류
```bash
cd backend
pip install -r requirements.txt --upgrade
```

### Node.js 의존성 오류
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```# Deployment Status Check - Tue Sep 16 20:25:23 KST 2025
## Deployment Status Check - Tue Sep 16 20:56:29 KST 2025
