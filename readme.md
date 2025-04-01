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

## Quick Start with Docker

The easiest way to run the complete system is with Docker Compose:

```bash
# Build and start all services
docker-compose up -d --build

# Check logs
docker-compose logs -f
```

### Testing Different Communication Modes

The client supports three communication modes which can be specified through the COMM_MODE environment variable:

```bash
# For HTTP mode (default)
docker-compose up -d -e COMM_MODE=http client

# For WebSocket mode
docker-compose up -d -e COMM_MODE=websocket client 

# For Kafka mode
docker-compose up -d -e COMM_MODE=kafka client
```

## Manual Setup (if needed)

If you prefer to run without Docker, follow these steps:

### 1. Create Python Virtual Environments

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
pip install aiohttp==3.8.6  # Install aiohttp explicitly
deactivate
```

### 2. Setup External Dependencies

- **MySQL**: Install and run MySQL server
- **Kafka**: Install and run Kafka and Zookeeper (required for Kafka mode)

### 3. Run the Server

```bash
cd server
source env/bin/activate  # On Windows: env\Scripts\activate
python main.py
```

### 4. Run the Client

```bash
cd client
source env/bin/activate  # On Windows: env\Scripts\activate

# Using command-line options to specify the mode:
python main.py --mode http     # HTTP mode
python main.py --mode websocket  # WebSocket mode
python main.py --mode kafka    # Kafka mode
```

## Docker Services Overview

The Docker setup includes the following services:

- **server**: FastAPI application that provides the API endpoints, WebSocket connection, and Kafka consumer
- **client**: Python application that processes the CSV file and sends records to the server
- **db**: MySQL database for storing employee records
- **zookeeper**: Zookeeper service for Kafka
- **kafka**: Kafka message broker for asynchronous communication

## Running Specific Components

```bash
# Run just the server with database and messaging
docker-compose up -d server db zookeeper kafka

# Run just the client (with a specific mode)
docker-compose up -d -e COMM_MODE=kafka client
```

## Client Command-Line Options

When running the client manually, the following options are available:

```
--file, -f        Path to CSV file with employee data (default: employee_data.csv)
--mode, -m        Communication mode: http, websocket, kafka (default: http)
--batch-size, -b  Number of records to process in each batch (default: 50)
--workers, -w     Number of concurrent workers (default: 10)
--server, -s      Server URL (default: http://localhost:8000)
--output, -o      Output file for failed records
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