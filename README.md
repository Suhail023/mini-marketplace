# Mini Marketplace - Microservices Architecture

A microservices-based e-commerce platform demonstrating modern distributed system patterns and best practices.

## 🏗️ Architecture Overview

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────────┐
│  API Gateway    │  ← Request routing, auth validation
└────┬─┬─┬─┬──────┘
     │ │ │ │
     ├─┴─┴─┴────────────────────┐
     │      │        │           │
┌────▼──┐ ┌▼──────┐┌▼────────┐ ┌▼────────┐
│ User  │ │Product││ Order   │ │ Payment │
│Service│ │Service││ Service │ │ Service │
└───┬───┘ └───┬───┘└─────┬───┘ └────┬────┘
    │         │          │           │
┌───▼───┐ ┌───▼───┐  ┌───▼───┐  ┌───▼────┐
│UserDB │ │ProdDB │  │OrderDB│  │PaymentDB│
└───────┘ └───────┘  └───────┘  └────────┘
                          │
                     ┌────▼────────┐
                     │Message Queue│
                     └─────┬───────┘
                           │
                     ┌─────▼─────────┐
                     │ Notification  │
                     │   Service     │
                     └───────────────┘
```

## 📦 Services

### Core Services
- **API Gateway** (Port 8000) - Central entry point, request routing, authentication
- **User Service** (Port 8001) - User management, authentication, profiles
- **Product Service** (Port 8002) - Product catalog, inventory management
- **Order Service** (Port 8003) - Order processing, orchestration
- **Payment Service** (Port 8004) - Payment processing, idempotent transactions
- **Notification Service** (Port 8005) - Email/SMS notifications (event-driven)

### Infrastructure
- **Message Queue** - RabbitMQ for async communication
- **Databases** - PostgreSQL per service (database per service pattern)
- **Cache** - Redis for distributed caching
- **Service Discovery** - Consul (optional, for production)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Poetry (Python package manager)

### Initial Setup

1. **Clone and navigate:**
   ```bash
   cd "D:\test\Mini Marketplace"
   ```

2. **Start infrastructure services:**
   ```bash
   docker-compose up -d postgres rabbitmq redis
   ```

3. **Run database migrations:**
   ```bash
   # Run migrations for each service
   cd services/user-service && poetry run alembic upgrade head
   cd ../product-service && poetry run alembic upgrade head
   # ... repeat for other services
   ```

4. **Start all services:**
   ```bash
   docker-compose up -d
   ```

5. **Verify health:**
   ```bash
   curl http://localhost:8000/health  # API Gateway
   curl http://localhost:8001/health  # User Service
   curl http://localhost:8002/health  # Product Service
   ```

## 🛠️ Development

### Running Individual Services

Each service can be run independently:

```bash
cd services/user-service
poetry install
poetry run python -m app.main
```

### Project Structure

```
Mini Marketplace/
├── services/
│   ├── api-gateway/       # API Gateway service
│   ├── user-service/      # User management
│   ├── product-service/   # Product catalog
│   ├── order-service/     # Order processing
│   ├── payment-service/   # Payment handling
│   └── notification-service/ # Notifications
├── shared/                # Shared libraries
│   ├── common/           # Common utilities
│   ├── events/           # Event schemas
│   └── proto/            # gRPC proto files (optional)
├── infrastructure/       # Infrastructure as code
│   ├── docker/          # Dockerfiles
│   ├── k8s/             # Kubernetes manifests
│   └── terraform/       # Terraform configs
├── docs/                # Documentation
├── docker-compose.yml   # Local development setup
└── README.md           # This file
```

## 📋 Development Progress

For detailed development roadmap and implementation guide, see [docs/DEVELOPMENT_PLAN.md](./docs/DEVELOPMENT_PLAN.md)

## 🔐 Security Considerations

- JWT-based authentication
- Service-to-service authentication (API keys or mTLS)
- Secret management (environment variables, Vault)
- Rate limiting at API Gateway
- Input validation in all services

## 🧪 Testing Strategy

- **Unit Tests**: Each service has its own test suite
- **Integration Tests**: Test service interactions
- **Contract Tests**: Ensure API contracts are maintained
- **E2E Tests**: Full workflow testing

## 📚 Documentation

- [API Documentation](./docs/api/) - OpenAPI/Swagger specs
- [Architecture Decisions](./docs/architecture/) - ADRs
- [Development Guide](./docs/development/) - Development workflows
- [Deployment Guide](./docs/deployment/) - Deployment instructions

## 🤝 Contributing

This is a learning project for microservices architecture patterns. Each phase builds upon the previous one.

## 📄 License

MIT License - This is a demonstration project for learning purposes.

---

**Status**: 🚀 Active Development - User Service complete, building remaining services

For detailed development plan, see [docs/DEVELOPMENT_PLAN.md](./docs/DEVELOPMENT_PLAN.md)
