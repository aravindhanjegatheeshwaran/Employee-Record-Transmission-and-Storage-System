# Employee Record Transmission and Storage System

A high-performance client-server application that processes employee records from a CSV file and stores them in a MySQL database. This solution leverages Python advanced coding techniques, including function decorators, data classes, and concurrency for efficient and scalable design.

## Features

### Server Features
- FastAPI-based HTTP API with JWT authentication
- Asynchronous database operations with connection pooling
- Custom decorators for logging, validation, and rate limiting
- Dataclass representation of employee records
- Bulk insert support for optimized database performance
- Robust error handling and logging

### Client Features
- Asynchronous CSV processing
- Multiple communication modes: HTTP API, Kafka, WebSockets
- Concurrency with controlled parallelism
- Retry mechanism with exponential backoff
- Detailed logging and error tracking
- Batch processing for optimal performance

### Bonus Features
- JWT-based API authentication
- Docker and Docker Compose containerization
- Scalable architecture

## Technical Stack

- **Python**: 3.9+ with async/await
- **Web Framework**: FastAPI
- **Database**: MySQL with aiomysql
- **Authentication**: JWT token-based
- **Concurrency**: asyncio, aiohttp
- **Containerization**: Docker, Docker Compose
- **Additional**: Kafka, WebSockets (optional)

## Project Structure

```
employee_record_system/
├── client/                  # Client application
│   ├── __init__.py
│   ├── config.py            # Client configuration
│   ├── client.py            # Client implementation
│   └── utils.py             # Client utilities
├── server/                  # Server application
│   ├── __init__.py
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── employee.py      # Employee routes
│   │   └── utils.py         # API utilities
│   ├── config.py            # Server configuration
│   ├── core/                # Core server components
│   │   ├── __init__.py
│   │   ├── database.py      # Database connection
│   │   ├── security.py      # Security utilities
│   │   └── decorators.py    # Function decorators
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   └── employee.py      # Employee model
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   └── employee.py      # Employee schemas
│   └── main.py              # Server entry point
├── tests/                   # Unit tests
│   ├── __init__.py
│   ├── test_client.py       # Client tests
│   └── test_server.py       # Server tests
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile.client        # Client Dockerfile
├── Dockerfile.server        # Server Dockerfile
├── requirements-client.txt  # Client dependencies
├── requirements-server.txt  # Server dependencies
└── README.md                # Project documentation
```

## Installation and Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- MySQL 8.0+ (if running without Docker)

### Setting up with Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd employee_record_system
   ```

2. Build and start containers:
   ```bash
   docker-compose up --build
   ```

3. The server will be available at http://localhost:8000 and the client will automatically connect to it.

### Manual Setup

#### Server Setup

1. Install server dependencies:
   ```bash
   pip install -r requirements-server.txt
   ```

2. Set up MySQL database:
   ```sql
   CREATE DATABASE employee_records;
   ```

3. Run the SQL schema creation script:
   ```bash
   mysql -u your_user -p employee_records < sql/init.sql
   ```

4. Set environment variables:
   ```bash
   export DB_HOST=localhost
   export DB_PORT=3306
   export DB_USER=your_user
   export DB_PASSWORD=your_password
   export DB_NAME=employee_records
   export SECRET_KEY=your-secret-key-for-jwt
   ```

5. Start the server:
   ```bash
   cd employee_record_system
   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Client Setup

1. Install client dependencies:
   ```bash
   pip install -r requirements-client.txt
   ```

2. Set environment variables:
   ```bash
   export SERVER_URL=http://localhost:8000
   export CSV_FILE_PATH=./employee_data.csv
   export COMM_MODE=http
   export BATCH_SIZE=50
   export MAX_WORKERS=10
   export AUTH_USERNAME=admin
   export AUTH_PASSWORD=adminpassword
   ```

3. Run the client:
   ```bash
   cd employee_record_system
   python -m client.main
   ```

## Usage

### API Endpoints

#### Authentication
- `POST /token`: Get access token

#### Employee Management
- `GET /api/employees`: List all employees (with pagination)
- `GET /api/employees/{employee_id}`: Get a specific employee
- `POST /api/employees`: Create a new employee
- `POST /api/employees/bulk`: Create multiple employees at once
- `PUT /api/employees/{employee_id}`: Update an employee
- `DELETE /api/employees/{employee_id}`: Delete an employee
- `GET /api/employees/stats/department`: Get employee count by department

### Client Usage

The client application can be run with various command-line arguments:

```bash
python -m client.main --help
```

Example usage:
```bash
python -m client.main --file ./employee_data.csv --mode http --batch-size 50 --workers 10
```

## Advanced Features

### Function Decorators

The system uses several custom decorators:
- `log_execution_time`: Log function execution time
- `log_requests`: Log API request details
- `validate_input`: Validate incoming data
- `rate_limit`: Prevent API abuse
- `retry`: Retry operations on failure

### Concurrency Model

The system leverages asyncio for non-blocking I/O operations:
- Server uses FastAPI's built-in async support
- Client implements controlled parallelism with semaphores
- Database operations use connection pooling

### Error Handling

Comprehensive error handling is implemented:
- Automatic retry with exponential backoff
- Detailed error logging
- Failed records tracking and export

## Testing

Run the test suite:

```bash
pytest
```

For coverage report:
```bash
pytest --cov=client --cov=server
```

## Performance Optimization

- Batch processing for minimal database round-trips
- Connection pooling for database operations
- Asynchronous processing for maximum throughput
- Configurable concurrency parameters

## Security Considerations

- JWT token-based authentication
- Password hashing using bcrypt
- Rate limiting to prevent abuse
- Input validation to prevent injection attacks

## License

This project is licensed under the MIT License - see the LICENSE file for details.
