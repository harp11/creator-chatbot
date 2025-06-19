# 🚀 Scalable YouTube Creator Chatbot System

A production-ready, horizontally scalable chatbot system designed for YouTube creators. Built with microservices architecture, this system can handle thousands of concurrent users while maintaining high performance and reliability.

## 🏗️ Architecture Overview

### Microservices Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway    │    │  Load Balancer  │
│   (React)       │◄──►│  (FastAPI)       │◄──►│    (Nginx)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼──────┐   │   ┌───────▼──────┐
            │ Chat Service │   │   │Retrieval Svc │
            │ (3 instances)│   │   │(2 instances) │
            └──────────────┘   │   └──────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼──────┐    ┌─────────▼────────┐    ┌───────▼──────┐
│  PostgreSQL  │    │      Redis       │    │   Weaviate   │
│  (Primary)   │    │   (Cache/Rate)   │    │  (Vectors)   │
└──────────────┘    └──────────────────┘    └──────────────┘
```

### Key Features
- **🔄 Horizontal Scaling**: Auto-scaling microservices
- **⚡ High Performance**: Sub-second response times
- **🛡️ Production Ready**: Rate limiting, circuit breakers, monitoring
- **🎯 Multi-Creator**: Support for multiple YouTube creators
- **📊 Real-time Analytics**: Comprehensive monitoring and metrics
- **🔒 Secure**: JWT authentication, input validation, CORS protection

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Google AI API Key
- 8GB+ RAM recommended

### 1. Clone and Setup
```bash
git clone <repository-url>
cd scalable_chatbot
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` file:
```bash
# Required
GOOGLE_API_KEY=your_google_ai_api_key_here

# Optional (defaults provided)
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
JWT_SECRET_KEY=your_jwt_secret
```

### 3. Start the System
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

### 4. Access the System
- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Monitoring**: http://localhost:3001 (Grafana)
- **Metrics**: http://localhost:9090 (Prometheus)

## 📋 Service Details

### API Gateway (Port 8000)
- **Purpose**: Single entry point, load balancing, rate limiting
- **Features**: Circuit breakers, authentication, request routing
- **Endpoints**: `/api/v1/chat`, `/api/v1/creators`, `/health`

### Chat Service (Ports 8001-8003)
- **Purpose**: Process chat messages, manage conversations
- **Instances**: 3 for load balancing
- **Features**: User profiles, conversation history, AI integration

### Retrieval Service (Ports 8010-8011)
- **Purpose**: Context retrieval from vector database
- **Instances**: 2 for redundancy
- **Features**: Semantic search, query analysis, context ranking

### Database Services
- **PostgreSQL**: User data, conversations, profiles
- **Redis**: Caching, rate limiting, session storage
- **Weaviate**: Vector embeddings, semantic search

## 🔧 Development Setup

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
python -m alembic upgrade head

# Run individual services
cd chat_service && python main.py
cd retrieval_service && python main.py
cd api_gateway && python main.py
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific service tests
pytest chat_service/tests/
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .
```

## 📊 Monitoring & Observability

### Health Checks
```bash
# Check all services
curl http://localhost:8000/health

# Individual service health
curl http://localhost:8001/health  # Chat Service
curl http://localhost:8010/health  # Retrieval Service
```

### Metrics & Monitoring
- **Grafana Dashboard**: http://localhost:3001
  - Username: `admin`
  - Password: `admin123`
- **Prometheus Metrics**: http://localhost:9090
- **Service Metrics**: Available at `/metrics` endpoint on each service

### Key Metrics Tracked
- Request latency and throughput
- Error rates and success rates
- Database connection pools
- Memory and CPU usage
- Rate limiting statistics
- Circuit breaker states

## 🔒 Security Features

### Authentication & Authorization
- JWT token-based authentication
- User tier-based rate limiting (Free/Premium/Enterprise)
- Request validation and sanitization

### Rate Limiting
- **Free Tier**: 50 requests/hour
- **Premium Tier**: 500 requests/hour
- **Enterprise Tier**: 5000 requests/hour

### Security Headers
- CORS protection
- Request ID tracking
- Input validation
- SQL injection prevention

## 🎯 API Usage Examples

### Chat with Creator
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer user123:premium" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I grow my YouTube channel?",
    "creator_id": "hawa_singh",
    "user_id": "user123"
  }'
```

### Get Conversation History
```bash
curl "http://localhost:8000/api/v1/conversations/{conversation_id}/messages" \
  -H "Authorization: Bearer user123:premium"
```

### List Available Creators
```bash
curl "http://localhost:8000/api/v1/creators"
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google AI API key | Required |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `WEAVIATE_URL` | Weaviate URL | http://localhost:8080 |
| `LOG_LEVEL` | Logging level | INFO |
| `DEBUG` | Debug mode | false |

### Service Configuration
Each service can be configured via environment variables or the `config/settings.py` file.

## 📈 Scaling Guidelines

### Horizontal Scaling
```bash
# Scale chat service to 5 instances
docker-compose up -d --scale chat-service=5

# Scale retrieval service to 3 instances
docker-compose up -d --scale retrieval-service=3
```

### Performance Optimization
- **Database**: Use read replicas for heavy read workloads
- **Caching**: Implement Redis clustering for high availability
- **Load Balancing**: Use external load balancer (AWS ALB, GCP Load Balancer)
- **CDN**: Serve static assets via CDN

### Resource Requirements
| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| API Gateway | 0.5 cores | 512MB | - |
| Chat Service | 1 core | 1GB | - |
| Retrieval Service | 1 core | 2GB | - |
| PostgreSQL | 2 cores | 4GB | 50GB |
| Redis | 0.5 cores | 1GB | 10GB |
| Weaviate | 2 cores | 4GB | 100GB |

## 🐛 Troubleshooting

### Common Issues

**Service Won't Start**
```bash
# Check logs
docker-compose logs service-name

# Check health
curl http://localhost:port/health
```

**Database Connection Issues**
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U chatbot_user -d chatbot -c "SELECT 1;"

# Check Redis
docker-compose exec redis redis-cli ping
```

**High Memory Usage**
```bash
# Monitor resource usage
docker stats

# Restart services
docker-compose restart service-name
```

### Performance Issues
- Check Grafana dashboards for bottlenecks
- Monitor database query performance
- Review rate limiting logs
- Check circuit breaker states

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

### Development Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
pytest
black .
flake8 .

# Commit and push
git commit -m "Add new feature"
git push origin feature/new-feature
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` endpoint on each service
- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions

## 🎉 Acknowledgments

- Built with FastAPI, PostgreSQL, Redis, and Weaviate
- Monitoring powered by Prometheus and Grafana
- AI capabilities via Google Gemini API
- Containerized with Docker and Docker Compose

---

**Ready to scale your creator chatbot to thousands of users? 🚀** 