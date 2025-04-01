# Employee Record Transmission and Storage System

A high-performance client-server system that processes employee records from CSV files and stores them in a MySQL database. The system demonstrates modern Python async programming techniques with a focus on reliability and performance.

## Features

### Server
- FastAPI-based RESTful API with JWT authentication
- Async database operations with SQLAlchemy ORM
- Request validation with Pydantic
- Rate limiting, logging, and error handling
- Custom decorators for cross-cutting concerns

### Client
- Async CSV processing with batching
- Multiple transport options (HTTP, Kafka, WebSocket)
- Controlled concurrency with semaphores
- Automatic retries with exponential backoff
- Comprehensive error handling and reporting

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, SQLAlchemy, MySQL
- **Authentication**: JWT tokens
- **Async**: asyncio, aiohttp
- **Data Validation**: Pydantic
- **Containers**: Docker, Docker Compose
- **Optional**: Kafka, WebSockets

## Project Structure

```
.
├── client/                # Client application
│   ├── config.py          # Client configuration
│   ├── employee_client.py # Client implementation
│   ├── main.py            # Client entry point 
│   └── utils.py           # Utility functions
├── server/                # Server application
│   ├── api/               # API endpoints
│   │   ├── api.py         # Main API routes
│   │   └── auth.py        # Auth routes
│   ├── core/              # Core components
│   │   ├── database.py    # Database connection
│   │   ├── decorators.py  # Function decorators
│   │   └── security.py    # Security utilities
│   ├── models/            # Database models
│   │   └── model.py       # SQLAlchemy models
│   ├── schemas/           # Data schemas
│   │   └── schema.py      # Pydantic schemas
│   └── main.py            # Server entry point
├── dockerfile-client      # Client Dockerfile
├── dockerfile-server      # Server Dockerfile
└── docker-compose.yml     # Docker Compose configuration
```

## Setup

### Prerequisites
- Python 3.9+
- MySQL
- Docker (optional)

### Running with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Setup

#### Server Setup

1. Install server dependencies:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. Setup environment variables:
   ```bash
   export DB_HOST=localhost
   export DB_PORT=3306
   export DB_USER=root
   export DB_PASSWORD=password
   export DB_NAME=employee_records
   export SECRET_KEY=your-secret-key
   ```

3. Start the server:
   ```bash
   cd server
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Client Setup

1. Install client dependencies:
   ```bash
   cd client
   pip install -r requirements.txt
   ```

2. Setup environment variables:
   ```bash
   export SERVER_URL=http://localhost:8000
   export COMM_MODE=http
   export BATCH_SIZE=50
   export MAX_WORKERS=10
   ```

3. Run the client:
   ```bash
   cd client
   python main.py --file employee_data.csv
   ```

## Usage

### Client

The client accepts several command-line options:

```bash
python main.py --help
```

Example usage:
```bash
python main.py --file data.csv --mode http --batch-size 100 --workers 20
```

### Server API Endpoints

- `POST /token`: Authentication (get JWT token)
- `GET /api/employees/`: List all employees
- `GET /api/employees/{id}`: Get employee by ID
- `POST /api/employees/`: Create a new employee
- `POST /api/employees/bulk`: Bulk create employees
- `PUT /api/employees/{id}`: Update an employee
- `DELETE /api/employees/{id}`: Delete an employee
- `GET /api/employees/stats/department`: Get employee counts by department

## Performance Optimization

- Batch processing for database operations
- Connection pooling for db connections
- Async processing for I/O bound operations
- Configurable parallelism
- Bulk inserts for high throughput