# GCP Cloud Run 배포 가이드

## 사전 준비사항

### 1. Google Cloud Console에서 프로젝트 설정
1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 프로젝트 ID를 기록해두세요 (예: ragmodel-project-2024)

### 2. 필요한 API 활성화
Google Cloud Console에서 다음 API들을 활성화하세요:
- Cloud Run API
- Cloud Build API  
- Artifact Registry API
- Container Registry API

### 3. 환경 변수 설정
배포 전 다음 환경 변수들을 설정해야 합니다:

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="asia-northeast3"  # Seoul region
export OPENAI_API_KEY="your-openai-api-key"
```

## 자동 배포 스크립트 실행

```bash
# 1. 환경 변수 설정
export PROJECT_ID="ragmodel-project-2024"
export REGION="asia-northeast3"
export OPENAI_API_KEY="your-openai-api-key"

# 2. 배포 스크립트 실행
chmod +x deploy-cloudrun.sh
./deploy-cloudrun.sh
```

## 수동 배포 단계별 가이드

### 1. gcloud CLI 인증
```bash
gcloud auth login
gcloud config set project $PROJECT_ID
```

### 2. Artifact Registry 설정
```bash
gcloud artifacts repositories create rag-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="RAG Model Application"

gcloud auth configure-docker $REGION-docker.pkg.dev
```

### 3. 백엔드 배포
```bash
cd backend
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/rag-backend:latest

gcloud run deploy rag-backend \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/rag-backend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --port 8000 \
    --set-env-vars "ENVIRONMENT=production,OPENAI_API_KEY=$OPENAI_API_KEY"
```

### 4. 프론트엔드 배포
```bash
cd ../frontend

# 백엔드 URL 가져오기
BACKEND_URL=$(gcloud run services describe rag-backend --region=$REGION --format="value(status.url)")

# 프론트엔드 환경 설정
cat > .env.production << EOF
REACT_APP_API_URL=$BACKEND_URL
GENERATE_SOURCEMAP=false
EOF

gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/rag-frontend:latest

gcloud run deploy rag-frontend \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/rag-frontend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 3000 \
    --set-env-vars "ENVIRONMENT=production,REACT_APP_API_URL=$BACKEND_URL"
```

## 배포 후 확인사항

1. **서비스 URL 확인**
```bash
echo "Backend URL: $(gcloud run services describe rag-backend --region=$REGION --format='value(status.url)')"
echo "Frontend URL: $(gcloud run services describe rag-frontend --region=$REGION --format='value(status.url)')"
```

2. **환경 변수 업데이트 (필요시)**
```bash
gcloud run services update rag-backend \
    --region=$REGION \
    --set-env-vars OPENAI_API_KEY=your-new-api-key
```

3. **로그 확인**
```bash
gcloud run services logs read rag-backend --region=$REGION
gcloud run services logs read rag-frontend --region=$REGION
```

## 문제 해결

### OpenSearch 서비스 설정
Cloud Run에서는 OpenSearch를 별도로 설정해야 합니다:
1. Google Cloud의 Elasticsearch Service 사용
2. 또는 외부 OpenSearch 서비스 사용
3. 환경 변수로 OpenSearch 연결 정보 설정

### 환경 변수 확인
```bash
# 현재 설정된 환경 변수 확인
gcloud run services describe rag-backend --region=$REGION --format="export" | grep env
```

## 비용 최적화

1. **트래픽이 없을 때 0으로 스케일링**
```bash
gcloud run services update rag-backend --region=$REGION --min-instances=0
gcloud run services update rag-frontend --region=$REGION --min-instances=0
```

2. **최대 인스턴스 수 제한**
```bash
gcloud run services update rag-backend --region=$REGION --max-instances=10
gcloud run services update rag-frontend --region=$REGION --max-instances=5
```