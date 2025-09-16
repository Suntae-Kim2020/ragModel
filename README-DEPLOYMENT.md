# GitHub Actions 자동 배포 설정 가이드

이 문서는 GitHub Actions를 사용하여 RAG Model 애플리케이션을 Google Cloud Run에 자동으로 배포하는 방법을 설명합니다.

## 🚀 자동 배포 시스템 개요

- **트리거**: main 브랜치에 push 또는 pull request 시 자동 실행
- **플랫폼**: Google Cloud Run
- **프로젝트**: ragp-472304
- **지역**: asia-northeast3 (서울)
- **서비스**: 
  - rag-backend (FastAPI 백엔드)
  - rag-frontend (React 프론트엔드)

## 📋 사전 준비사항

1. **Google Cloud 프로젝트 설정**
   - 프로젝트 ID: `ragp-472304`
   - 필수 API 활성화: Cloud Run, Cloud Build, Artifact Registry

2. **서비스 계정 생성 및 설정**
   ```bash
   ./setup-service-account.sh
   ```

## 🔐 GitHub Secrets 설정

GitHub 저장소의 Settings → Secrets and variables → Actions에서 다음 secrets을 추가하세요:

### 필수 Secrets

1. **GCP_SA_KEY**
   ```json
   {
     "type": "service_account",
     "project_id": "ragp-472304",
     "private_key_id": "8dbe87d3023d8179c867875ab3d94f8dc7e0b716",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "github-actions-deploy@ragp-472304.iam.gserviceaccount.com",
     ...
   }
   ```

2. **OPENAI_API_KEY**
   - 값: OpenAI API 키 (예: sk-...)

## 📝 GitHub Secrets 추가 단계별 가이드

1. **GitHub 저장소 접속**
   - https://github.com/[username]/ragModel 이동

2. **Settings 탭 클릭**

3. **왼쪽 메뉴에서 "Secrets and variables" → "Actions" 클릭**

4. **"New repository secret" 버튼 클릭**

5. **GCP_SA_KEY 추가**
   - Name: `GCP_SA_KEY`
   - Secret: `service-account-key.json` 파일의 전체 내용 복사-붙여넣기

6. **OPENAI_API_KEY 추가**
   - Name: `OPENAI_API_KEY`
   - Secret: OpenAI API 키 값

## 🔧 배포 워크플로우

GitHub Actions 워크플로우 파일: `.github/workflows/deploy.yml`

### 배포 단계:
1. **코드 체크아웃**
2. **Google Cloud 인증**
3. **Docker 이미지 빌드 및 푸시**
4. **백엔드 Cloud Run 배포**
5. **프론트엔드 Cloud Run 배포**
6. **배포 결과 요약**

### 환경 변수 설정:
- **백엔드**: 
  - `ENVIRONMENT=production`
  - `OPENSEARCH_HOST=opensearch-service`
  - `OPENAI_API_KEY=[GitHub Secret]`
- **프론트엔드**: 
  - `ENVIRONMENT=production`
  - `REACT_APP_API_URL=[백엔드 URL]`

## 🚀 배포 실행

### 자동 배포 트리거:
1. **main 브랜치에 push**
   ```bash
   git add .
   git commit -m "Update application"
   git push origin main
   ```

2. **Pull Request 생성**
   - Pull Request를 main 브랜치로 생성하면 자동으로 배포 워크플로우 실행

### 수동 배포:
GitHub Actions 탭에서 "Deploy to Cloud Run" 워크플로우를 수동으로 실행할 수 있습니다.

## 📊 배포 모니터링

### GitHub Actions에서 확인:
1. GitHub 저장소 → Actions 탭
2. 최신 워크플로우 실행 상태 확인
3. 각 단계별 로그 확인

### 배포 결과 확인:
- 백엔드 URL: https://rag-backend-[hash]-uc.a.run.app
- 프론트엔드 URL: https://rag-frontend-[hash]-uc.a.run.app

## 🛠️ 트러블슈팅

### 일반적인 문제:

1. **인증 오류**
   ```
   ERROR: gcloud crashed (HttpAccessTokenRefreshError)
   ```
   → GCP_SA_KEY Secret 값 재확인

2. **권한 오류**
   ```
   ERROR: User does not have permission to access project
   ```
   → 서비스 계정 권한 재설정 (`./setup-service-account.sh` 재실행)

3. **빌드 실패**
   ```
   ERROR: build step 0 failed
   ```
   → Dockerfile 구문 및 dependencies 확인

4. **포트 설정 오류**
   ```
   ERROR: Container failed to start
   ```
   → PORT 환경변수 사용 확인

### 로그 확인:
```bash
# Cloud Run 서비스 로그 확인
gcloud logs read --project=ragp-472304 --limit=50
```

## 📚 관련 파일

- `.github/workflows/deploy.yml`: GitHub Actions 워크플로우
- `setup-service-account.sh`: 서비스 계정 설정 스크립트
- `deploy-cloudrun.sh`: 수동 배포 스크립트
- `frontend/Dockerfile`: 프론트엔드 Docker 설정
- `backend/Dockerfile`: 백엔드 Docker 설정

## 🔒 보안 고려사항

1. **서비스 계정 키 보안**
   - `service-account-key.json` 파일을 Git에 커밋하지 마세요
   - 사용 후 로컬 파일 삭제 권장

2. **환경 변수 관리**
   - 민감한 정보는 GitHub Secrets 사용
   - 프로덕션 환경에서만 사용할 환경 변수 분리

3. **접근 권한 최소화**
   - 서비스 계정에 필요한 최소 권한만 부여
   - 정기적으로 권한 검토

## ✨ 다음 단계

1. **모니터링 설정**: Cloud Monitoring, Alerting 구성
2. **SSL 인증서**: 커스텀 도메인 및 SSL 인증서 설정  
3. **환경 분리**: 개발/스테이징/프로덕션 환경 분리
4. **데이터베이스**: Cloud SQL 또는 관리형 OpenSearch 연결
5. **CD 최적화**: Blue-Green 배포, Canary 배포 전략 구현