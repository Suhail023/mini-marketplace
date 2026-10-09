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

2. **Generate secrets** (JWT signing key + internal service token, written to the gitignored `secrets/`):
   ```bash
   python scripts/generate_secrets.py
   ```

3. **Start infrastructure services:**
   ```bash
   docker-compose up -d postgres rabbitmq redis
   ```

4. **Run database migrations:**
   ```bash
   # Run migrations for each service
   cd services/user-service && poetry run alembic upgrade head
   cd ../product-service && poetry run alembic upgrade head
   # ... repeat for other services
   ```

5. **Start all services:**
   ```bash
   docker-compose up -d
   ```

6. **Verify health:**
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
├── docker-compose.yml   # Local development setup
└── README.md           # This file
```

## 🔐 Security Considerations

### Authentication & authorization

- **End users** authenticate with the bearer JWT issued by user-service. Every
  service verifies it with `shared/common/auth.py` and takes the caller's
  identity from the `sub` claim — never from the request body or path.
- **Orders and notifications** are scoped to the caller: `GET /orders/`,
  `GET /orders/{id}`, `GET /notifications/` and `GET /notifications/{id}` only
  return the caller's own records (other users' IDs return 404).
- **Product writes** (`POST`, `PATCH`, `DELETE /products...`) require the `admin`
  role. Grant it by listing user IDs in `ADMIN_USER_IDS` (comma-separated) on
  user-service; the role is embedded in tokens issued after that.
- **Service-to-service calls** go to `/internal/*` endpoints
  (`/internal/products/{id}/stock/decrement`, `/internal/payments/*`) and must send
  the shared `X-Internal-Token` header (`INTERNAL_SERVICE_TOKEN`). The gateway
  does not route `/internal` or `/payments`, and strips that header from clients.
- **Secrets** (`JWT_SECRET_KEY`, `INTERNAL_SERVICE_TOKEN`) have no defaults and are
  never committed. Compose mounts them as Docker secrets from `./secrets/`
  (gitignored); generate them with `python scripts/generate_secrets.py` and rotate
  with `--rotate` (rotating the JWT key logs everyone out). Outside Docker, set the
  variable or `<NAME>_FILE`. Services refuse to start if a secret they need is
  missing, shorter than 32 characters, or a known placeholder.

### General

- Service-to-service authentication (shared internal token; mTLS later)
- Secret management (environment variables, Vault)
- Rate limiting at API Gateway
- Input validation in all services

## 🧪 Testing Strategy

- **Unit Tests**: Each service has its own test suite
- **Integration Tests**: Test service interactions
- **Contract Tests**: Ensure API contracts are maintained
- **E2E Tests**: Full workflow testing

## 🤝 Contributing

This is a learning project for microservices architecture patterns. Each phase builds upon the previous one.

## 📄 License

MIT License - This is a demonstration project for learning purposes.
