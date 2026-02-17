# AI Health Trainer - 배포 가이드

> **이 문서의 목적:** Docker 환경 구성 및 GCP/AWS VM 배포 가이드.  
> **관리:** Claude Opus 4.6 (설계/수정), Codex 5.3 (구현)

---

## 1. 로컬 개발 환경 (Docker Compose)

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    container_name: health_trainer_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: health_trainer
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: health_trainer_redis
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: health_trainer_api
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - uploads:/data/uploads
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  pgdata:
  redisdata:
  uploads:
```

### backend/Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### backend/requirements.txt (초기 버전)

```
# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.30.0
alembic>=1.14.0
pgvector>=0.3.0

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Validation
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.9
email-validator>=2.0.0

# AI
google-generativeai>=0.8.0

# Cache
redis>=5.0.0

# HTTP Client (for testing)
httpx>=0.27.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-cov>=5.0.0
```

---

## 2. 프로덕션 배포 (GCP/AWS VM)

### 아키텍처

```
[인터넷]
    │
    ▼
[VM 인스턴스 (e2-medium 이상)]
    │
    ├── Nginx (:80, :443)
    │     ├── / → Flutter 빌드 정적 파일 (웹 버전, 선택사항)
    │     ├── /api → FastAPI (:8000)
    │     └── /uploads → 업로드 이미지
    │
    ├── FastAPI (:8000)
    ├── PostgreSQL+pgvector (:5432)
    └── Redis (:6379)
```

### docker-compose.prod.yml (프로덕션)

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redisdata:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    env_file:
      - .env.prod
    volumes:
      - uploads:/data/uploads
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./certbot/conf:/etc/letsencrypt
      - uploads:/data/uploads:ro
    depends_on:
      - backend

volumes:
  pgdata:
  redisdata:
  uploads:
```

### nginx/nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # Let's Encrypt 인증
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # HTTPS 리다이렉트
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

        # API 프록시
        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 파일 업로드 크기 제한
            client_max_body_size 10M;
        }

        # Swagger 문서
        location /docs {
            proxy_pass http://backend;
        }

        location /openapi.json {
            proxy_pass http://backend;
        }

        # 업로드 이미지 서빙
        location /uploads {
            alias /data/uploads;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## 3. VM 배포 절차

```bash
# 1. VM 접속
ssh user@your-vm-ip

# 2. Docker 설치 (Ubuntu)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER

# 3. 프로젝트 클론
git clone https://github.com/your-repo/AI_Health-Trainer.git
cd AI_Health-Trainer

# 4. 환경변수 설정
cp .env.example .env.prod
nano .env.prod  # API 키, DB 비밀번호 등 설정

# 5. SSL 인증서 (Let's Encrypt)
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d your-domain.com

# 6. 배포
docker compose -f docker-compose.prod.yml up -d

# 7. DB 마이그레이션
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 8. 상태 확인
docker compose -f docker-compose.prod.yml ps
curl https://your-domain.com/api/v1/docs
```

---

## 4. CI/CD (GitHub Actions)

### .github/workflows/test.yml

```yaml
name: Test

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
          JWT_SECRET_KEY: test-secret
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml
```

---

## 5. 추천 VM 스펙

| 클라우드 | 인스턴스 타입 | vCPU | RAM | 월 예상 비용 |
|---------|-------------|------|-----|-------------|
| GCP | e2-medium | 2 | 4GB | ~$25 |
| AWS | t3.medium | 2 | 4GB | ~$30 |

> 포트폴리오 규모에서는 위 스펙으로 충분합니다.
> Docker Compose로 PostgreSQL + Redis + FastAPI + Nginx를 모두 운영 가능합니다.
