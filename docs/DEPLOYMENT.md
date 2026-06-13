# Deployment Guide

## Quick Start (Development)

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/tender-compliance.git
cd tender-compliance

# Install dependencies
pip install -r requirements.txt

# Start server
cd backend
python app/main.py
```

Server starts at `http://localhost:8012`. API docs at `http://localhost:8012/docs`.

---

## Docker Deployment

### Single Container

```bash
docker build -t tender-compliance .
docker run -p 8012:8012 tender-compliance
```

### Docker Compose

```bash
# Development
docker-compose up api

# Production (with Nginx reverse proxy)
docker-compose --profile production up -d
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONUNBUFFERED` | 1 | Unbuffered Python output |
| `TENDER_DB_PATH` | ./tender_compliance.db | SQLite database path |
| `LOG_LEVEL` | info | Logging level |

---

## Production Considerations

### Database

The default SQLite database is suitable for single-instance deployment. For production:

1. **Backup strategy**: Schedule regular backups of the `.db` file
2. **Migration to PostgreSQL**: Replace `sqlite3` calls with `asyncpg` or `SQLAlchemy`
3. **Connection pooling**: Add connection pool for concurrent requests

### Security

1. **Authentication**: Add JWT token authentication
2. **CORS**: Restrict `allow_origins` to specific domains
3. **Rate limiting**: Add request rate limiting middleware
4. **Input validation**: File size limits, content type validation
5. **HTTPS**: Use Nginx or a load balancer with TLS termination

### Scaling

1. **Horizontal scaling**: Use Gunicorn with multiple workers
2. **Caching**: Add Redis for analysis result caching
3. **Queue**: Use Celery for long-running analysis tasks
4. **Object storage**: Store uploaded files in S3/MinIO instead of SQLite

### Monitoring

1. **Health endpoint**: Monitor `/api/health`
2. **Logging**: Configure structured logging with JSON format
3. **Metrics**: Add Prometheus metrics endpoint
4. **Tracing**: Add OpenTelemetry for distributed tracing

---

## Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://api:8012;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration:

1. **Lint**: `ruff check .` for code quality
2. **Test**: `pytest tests/ -v --cov=backend` for test coverage
3. **Build**: Docker image build verification

See `.github/workflows/ci.yml` for the full pipeline configuration.
