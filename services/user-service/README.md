# User Service

User management, authentication, and profile service for Mini Marketplace.

## Features

- User registration and authentication
- JWT-based session management
- Profile management
- Email verification
- Account lockout protection
- Password requirements enforcement

## API Endpoints

### Health & Monitoring
- `GET /health` - Detailed health check with dependency status
- `GET /health/liveness` - Kubernetes liveness probe
- `GET /health/readiness` - Kubernetes readiness probe

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout

### User Management
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile
- `DELETE /api/v1/users/me` - Delete user account

## Running Locally

```bash
# Install dependencies
poetry install

# Run the service
poetry run python -m app.main
```

The service will start on `http://localhost:8001`

## Configuration

Configuration is managed through environment variables. See `.env.example` for available options.

Key configurations:
- `PORT`: Service port (default: 8001)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_HOST`: Redis host for session management
- `JWT_SECRET_KEY`: Secret key for JWT tokens

## Database

The service uses PostgreSQL with Alembic for migrations.

```bash
# Run migrations
poetry run alembic upgrade head

# Create new migration
poetry run alembic revision --autogenerate -m "description"
```

## Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html
```

## Docker

```bash
# Build image
docker build -t user-service:latest .

# Run container
docker run -p 8001:8001 --env-file .env user-service:latest
```
