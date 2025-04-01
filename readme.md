# Employee Record Transmission and Storage System

A high-performance client-server application for processing employee records from CSV files and storing them in a MySQL database. Built with modern Python async techniques, the system offers multiple communication protocols and efficient data handling.

## Features

### Server
- FastAPI-based REST API with JWT authentication
- WebSocket endpoint for real-time communication
- Kafka consumer for message-based integration
- Async database operations with SQLAlchemy ORM
- Rate limiting, validation, and comprehensive logging

### Client
- Efficient CSV processing with batching
- Multiple transport protocols (HTTP, WebSocket, Kafka)
- Controlled concurrency with async semaphores
- Auto-retry with exponential backoff
- Detailed error tracking and reporting

## Tech Stack

- **Python**: 3.9+ with asyncio
- **Web Framework**: FastAPI
- **Database**: MySQL with SQLAlchemy ORM
- **Communication**: HTTP, WebSockets, Kafka
- **Authentication**: JWT tokens
- **Containerization**: Docker, Docker Compose

## Getting Started

### Prerequisites
- Python 3.9+
- MySQL database
- Kafka (for Kafka mode)
- Docker and Docker Compose (for containerized deployment)

### Manual Setup (venv)

If you want to run without Docker, set up virtual environments for both client and server:

```bash
# Setup Server Environment
cd server
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
deactivate

# Setup Client Environment
cd ../client
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
# Enable aiohttp manually (it's commented in requirements.txt)
pip install aiohttp==3.8.6
deactivate
```

### Running the Application Manually

#### Running the Server

1. Configure environment variables (if needed):
   ```bash
   # Database connection
   export DB_HOST=localhost
   export DB_PORT=3306
   export DB_USER=root
   export DB_PASSWORD=your-password
   export DB_NAME=employee_records
   
   # Security
   export SECRET_KEY=your-secret-key
   
   # For Kafka mode
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   export KAFKA_TOPIC=employee-records
   ```

2. Start the server:
   ```bash
   cd server
   source env/bin/activate  # On Windows: env\Scripts\activate
   python main.py
   ```

#### Running the Client

1. In a separate terminal window, run the client:
   ```bash
   cd client
   source env/bin/activate  # On Windows: env\Scripts\activate
   
   # HTTP mode
   python main.py --file employee_data.csv --mode http
   
   # WebSocket mode
   python main.py --file employee_data.csv --mode websocket
   
   # Kafka mode (requires Kafka server)
   python main.py --file employee_data.csv --mode kafka
   ```

#### Client Command-Line Options

```
--file, -f        Path to CSV file with employee data (default: employee_data.csv)
--mode, -m        Communication mode: http, websocket, kafka (default: http)
--batch-size, -b  Number of records to process in each batch (default: 50)
--workers, -w     Number of concurrent workers (default: 10)
--server, -s      Server URL (default: http://localhost:8000)
--output, -o      Output file for failed records
```

### Docker Setup (Recommended)

Run the complete system with Docker and Docker Compose:

```bash
# Build and start all services (server, client, database, kafka)
docker-compose up -d --build

# Check logs
docker-compose logs -f

# To run just the server components without the client
docker-compose up -d --build server db zookeeper kafka

# To run just the client with a specific mode
docker-compose up -d --build client
```

#### Testing Different Communication Modes

You can change the communication mode for the client in Docker by setting the COMM_MODE environment variable:

```bash
# For HTTP mode
docker-compose up -d -e COMM_MODE=http client

# For WebSocket mode
docker-compose up -d -e COMM_MODE=websocket client 

# For Kafka mode
docker-compose up -d -e COMM_MODE=kafka client
```

## Communication Modes

The client supports three communication protocols:

### HTTP Mode
- RESTful API communication
- Standard request-response pattern
- Ideal for most use cases
- Run with: `python main.py --file employee_data.csv --mode http`

### WebSocket Mode
- Real-time bidirectional communication
- Persistent connection
- Great for streaming data
- Run with: `python main.py --file employee_data.csv --mode websocket`

### Kafka Mode
- Message-based asynchronous communication
- High throughput, resilient delivery
- Excellent for distributed systems
- Run with: `python main.py --file employee_data.csv --mode kafka`
- Note: Requires a running Kafka server

## Client Command-Line Options

```
--file, -f        Path to CSV file with employee data
--mode, -m        Communication mode (http, websocket, kafka)
--batch-size, -b  Records per batch
--workers, -w     Concurrent worker count
--server, -s      Server URL
--output, -o      Failed records output file
```

## API Endpoints

- `POST /token`: Get JWT authentication token
- `GET /api/employees/`: List employees (with pagination)
- `GET /api/employees/{id}`: Get employee by ID
- `POST /api/employees/`: Create employee
- `POST /api/employees/bulk`: Bulk create employees
- `PUT /api/employees/{id}`: Update employee
- `DELETE /api/employees/{id}`: Delete employee
- `GET /api/employees/stats/department`: Get department statistics
- `WebSocket /ws`: WebSocket connection for real-time data transmission

## Performance Features

- Batch processing with optimized batch sizes
- Connection pooling for database efficiency
- Controlled parallelism with semaphores
- Async I/O for non-blocking operations
- Exponential backoff for resilient connections