# Docker Deployment Guide

Deploy JC Icons Management System using Docker and Docker Compose.

## Prerequisites

- Docker installed (https://docs.docker.com/get-docker/)
- Docker Compose installed (https://docs.docker.com/compose/install/)

## Quick Start - Development with Docker

1. **Build and start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Initialize the database:**
   ```bash
   docker-compose exec app python scripts/init_db.py init
   ```

3. **Access the application:**
   - Open http://localhost:5000
   - Login with username `admin` and password `admin123`

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

## Production Deployment with Docker

### 1. Prepare Environment Variables

Create a `.env.prod` file:

```bash
# Core
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
FLASK_DEBUG=false

# Database
DB_USER=jc_icons_prod
DB_PASSWORD=<strong-password>
DB_NAME=jc_icons_v2

# Admin
ADMIN_PASSWORD=<strong-password>
```

### 2. Build the Application Image

```bash
docker build -t jc-icons:latest .
```

### 3. Deploy with docker-compose-prod.yml

```bash
docker-compose -f docker-compose-prod.yml --env-file .env.prod up -d
```

### 4. Initialize the Database

```bash
docker-compose -f docker-compose-prod.yml exec app python scripts/init_db.py init
```

### 5. Verify Health Check

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "healthy", "message": "Application is running"}
```

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
```

### Execute Commands in Container

```bash
# Create a new user
docker-compose exec app python scripts/init_db.py create-user

# Open interactive Python shell
docker-compose exec app python

# Run database query
docker-compose exec postgres psql -U jc_icons -d jc_icons_v2
```

### Database Operations

```bash
# Backup database
docker-compose exec postgres pg_dump -U jc_icons jc_icons_v2 > backup.sql

# Restore database
docker-compose exec -T postgres psql -U jc_icons jc_icons_v2 < backup.sql

# Reset development database
docker-compose exec app python scripts/init_db.py reset
```

### Update Application

```bash
# Stop and remove old containers
docker-compose down

# Rebuild image
docker build -t jc-icons:latest .

# Start with new image
docker-compose up -d
```

## Environment Variables (docker-compose)

### Development (docker-compose.yml)

```
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=postgresql://jc_icons:jc_icons_dev_password@postgres:5432/jc_icons_v2
ADMIN_PASSWORD=admin123
```

### Production (docker-compose-prod.yml)

Variables are read from `.env.prod` file:
- SECRET_KEY (required)
- DB_USER (required)
- DB_PASSWORD (required)
- DB_NAME (optional, defaults to jc_icons_v2)
- ADMIN_PASSWORD (required for initial setup)

## Docker Image Details

### Base Image
- Python 3.11 slim (optimized for size)

### Exposed Ports
- 5000 - Flask application

### Health Check
- Endpoint: `http://localhost:5000/health`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

### Volumes

**Development:**
- `.` → `/app` - Live code reloading

**Production:**
- `./logs` → `/app/logs` - Application logs
- `postgres_data` → `/var/lib/postgresql/data` - Database persistence

## Deployment Platforms

### Azure Container Instances

```bash
# Create resource group
az group create --name jc-icons-rg --location eastus

# Create container registry
az acr create --name jciconsr --resource-group jc-icons-rg --sku Basic

# Build image
docker build -t jciconsr.azurecr.io/jc-icons:latest .

# Push to registry
docker push jciconsr.azurecr.io/jc-icons:latest

# Create container instance
az container create \
  --resource-group jc-icons-rg \
  --name jc-icons-app \
  --image jciconsr.azurecr.io/jc-icons:latest \
  --cpu 2 \
  --memory 2 \
  --port 5000 \
  --environment-variables FLASK_ENV=production
```

### Google Cloud Run

```bash
# Configure gcloud
gcloud config set project PROJECT_ID

# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/jc-icons

# Deploy to Cloud Run
gcloud run deploy jc-icons \
  --image gcr.io/PROJECT_ID/jc-icons \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --set-env-vars FLASK_ENV=production
```

### AWS ECS

```bash
# Create ECR repository
aws ecr create-repository --repository-name jc-icons

# Build and push image
docker tag jc-icons:latest ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/jc-icons:latest
docker push ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/jc-icons:latest

# Create ECS task definition
# (Use AWS console or CloudFormation)
```

## Troubleshooting

### Port Already in Use

```bash
# Change port in docker-compose.yml
# ports:
#   - "8000:5000"

docker-compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U jc_icons -c "SELECT 1"
```

### Application Won't Start

```bash
# Check app logs
docker-compose logs app

# Rebuild image
docker-compose down
docker build --no-cache -t jc-icons:latest .
docker-compose up -d
```

### Permission Errors

```bash
# Ensure docker daemon is running
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
```

## Security Best Practices

### Image Security

1. **Use specific base image versions** (not `latest`)
2. **Scan for vulnerabilities:**
   ```bash
   docker scan jc-icons:latest
   ```
3. **Use minimal base images** (slim/alpine)
4. **Don't run as root** in production
5. **Keep secrets out of images** (use environment variables)

### Container Security

1. **Use .dockerignore** to exclude sensitive files
2. **Run with minimal privileges**
3. **Use read-only filesystems where possible**
4. **Enable resource limits:**
   ```yaml
   services:
     app:
       deploy:
         limits:
           cpus: '1'
           memory: 512M
   ```

### Secret Management

1. **Never commit .env files**
2. **Use Docker secrets for swarm mode**
3. **Use environment variables for configuration**
4. **Rotate credentials regularly**

## Performance Tuning

### Gunicorn Workers

In production Dockerfile:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "sync"]
```

Adjust worker count:
- **CPU-bound**: workers = (2 × CPU cores) + 1
- **I/O-bound**: workers = (4 × CPU cores) + 1

### Database Connection Pooling

Set in postgres service:
```yaml
environment:
  POSTGRES_MAX_CONNECTIONS: 100
```

## Monitoring

### Prometheus Metrics (Optional)

Add to your application for monitoring:
```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
```

### Logging

All logs are available via Docker:
```bash
docker-compose logs -f --tail=100
```

For persistent logging, configure log drivers in docker-compose.yml:
```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Getting Help

- Docker documentation: https://docs.docker.com/
- Docker Compose docs: https://docs.docker.com/compose/
- Check application logs: `docker-compose logs app`

---

**Last Updated:** February 2026
