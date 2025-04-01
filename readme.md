# Employee Record Transmission and Storage System

A high-performance client-server application for processing employee records from CSV files and storing them in a MySQL database. Built with modern Python async techniques, the system offers multiple communication protocols and efficient data handling.

## System Architecture

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   CSV File  │     │  Client Application  │     │                 │
│  Employee   │────▶│ (Batch Processing)  │────▶│    HTTP API     │
│   Records   │     │                     │     │                 │
└─────────────┘     └─────────────────────┘     └────────┬────────┘
                          │        ▲                     │
                          │        │                     │
                          ▼        │                     ▼
                    ┌─────────────────┐          ┌───────────────┐
                    │    WebSocket    │◀─────────│               │
                    │    Connection   │          │  FastAPI      │
                    └─────────────────┘          │  Server       │
                          │        ▲             │               │
                          │        │             │               │
                          ▼        │             │               │
                    ┌─────────────────┐          │               │
                    │      Kafka      │◀─────────│               │
                    │    Messaging    │          │               │
                    └─────────────────┘          └───────┬───────┘
                                                         │
                                                         │
                                                         ▼
                                                  ┌─────────────┐
                                                  │   MySQL     │
                                                  │  Database   │
                                                  └─────────────┘
```

## Quick Start with Docker (Windows WSL/Linux)

Setting up the environment is the first step for running this application. Docker provides the easiest way to get started.

### System Requirements

- Docker Desktop (Windows with WSL2) or Docker Engine + Docker Compose (Linux)
- Internet connection (for pulling Docker images)
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### 1. Docker Setup Instructions

#### Windows with WSL2:

1. Download and install Docker Desktop from https://www.docker.com/products/docker-desktop
2. During installation, enable WSL 2 when prompted
3. After installation, start Docker Desktop and wait for it to initialize
4. Open PowerShell or Command Prompt and verify installation:
   ```
   docker --version
   docker-compose --version
   ```
5. Set up a WSL2 Linux distribution if you don't have one:
   ```
   wsl --install -d Ubuntu
   ```

#### Linux:

```bash
# Install Docker
sudo apt update
sudo apt install docker.io

# Install Docker Compose
sudo apt install docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

### 2. Running the Application with Docker

1. Clone or download this repository to your local machine
2. Navigate to the project directory:
   ```
   cd "Employee Record Transmission and Storage System"
   ```

3. Start all services with Docker Compose:
   ```
   docker-compose up -d --build
   ```

4. Check if all containers are running correctly:
   ```
   docker-compose ps
   ```

5. View the logs to ensure everything started properly:
   ```
   docker-compose logs -f
   ```

6. Create the Kafka topic if it wasn't automatically created:
   ```
   docker-compose exec kafka kafka-topics --create --topic employee-records --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
   ```

7. The application is now running with:
   - Server API at http://localhost:8000
   - MySQL database at localhost:3306
   - Kafka at localhost:9092
   - Client processing employee data records

8. To stop all services:
   ```
   docker-compose down
   ```

### 3. Running the Database Migrations

The server uses Alembic for database migrations. The migrations are automatically applied when the server starts in Docker, but you can run them manually:

```bash
# When using Docker
docker-compose exec server alembic upgrade head

# When running locally (from server directory with activated virtual env)
cd server
alembic upgrade head
```

### 4. Testing Different Communication Modes

You can run the client with different communication protocols:

```bash
# For HTTP mode (default)
COMM_MODE=http docker-compose up -d client

# For WebSocket mode
COMM_MODE=websocket docker-compose up -d client

# For Kafka mode
COMM_MODE=kafka docker-compose up -d client
```

## Local Development Setup

If you prefer to run the application directly on your machine without Docker for development:

### 1. Prerequisites

- Python 3.8 or 3.9 (recommended for compatibility with aiohttp)
- MySQL Server
- Kafka (optional, for Kafka communication mode)

### 2. Set Up Python Environments

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
```

### 3. Configure the Applications

Client Configuration:
- Modify `/client/config.py` to use appropriate connection settings
- For Kafka, when running locally, use: `KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")`

Server Configuration:
- Update the database connection in `server/core/database.py` and `server/alembic.ini`

### 4. Run the Server

```bash
cd server
source env/bin/activate  # On Windows: env\Scripts\activate

# Apply database migrations
alembic upgrade head

# Start the server
python main.py
```

### 5. Run the Client

```bash
cd client
source env/bin/activate  # On Windows: env\Scripts\activate

# HTTP mode (default and most compatible)
python main.py --mode http

# WebSocket mode
python main.py --mode websocket

# Kafka mode (requires Kafka to be running)
python main.py --mode kafka
```

## Known Issues and Troubleshooting

### Kafka Compatibility Issues

If you encounter Kafka-related errors like "cannot import name 'StaleLeaderEpochCodeError'", ensure you have compatible versions:

```bash
# Recommended versions that work together
pip install kafka-python==2.0.2
pip install aiokafka==0.8.1
```

### WebSocket Connectivity

If you have issues with WebSocket connectivity:
- When running directly on your machine, use `ws://localhost:8000/ws`
- When running in Docker, use `ws://server:8000/ws`

### Python Environment Issues

- aiohttp may have build errors with Python 3.10+. Use Python 3.8 or 3.9 for best compatibility.
- If using Python 3.10+, install with: `pip install aiohttp==3.7.4.post0`

## CSV Data Format

The client expects CSV files with the following columns:
- `employee_id` (required): Unique identifier
- `name` (required): Full employee name
- `email` (required): Valid email address
- `department` (required): Department name
- `designation` (required): Job title
- `salary` (required): Numerical value
- `date_of_joining` (required): Date in YYYY-MM-DD format
- Additional columns will be included but not validated

Example:
```csv
employee_id,name,email,department,designation,salary,date_of_joining
EMP001,John Doe,john.doe@example.com,Engineering,Senior Developer,85000,2020-03-15
EMP002,Jane Smith,jane.smith@example.com,Marketing,Marketing Manager,75000,2019-06-01
```

## API Endpoints

The server provides the following API endpoints:

- `POST /token` - Obtain JWT authentication token
- `POST /api/employees/` - Create new employee record
- `GET /api/employees/` - List all employee records
- `GET /api/employees/{employee_id}` - Get specific employee details
- `PUT /api/employees/{employee_id}` - Update employee record
- `DELETE /api/employees/{employee_id}` - Delete employee record
- `WebSocket /ws` - WebSocket endpoint for real-time data transmission
- Kafka Topic: `employee-records` - Kafka topic for asynchronous data transmission

## Tech Stack

- **Python**: 3.8+ with asyncio
- **Web Framework**: FastAPI
- **Database**: MySQL with SQLAlchemy ORM
- **Communication**: HTTP, WebSockets, Kafka
- **Authentication**: JWT tokens
- **Containerization**: Docker, Docker Compose
- **Migration**: Alembic