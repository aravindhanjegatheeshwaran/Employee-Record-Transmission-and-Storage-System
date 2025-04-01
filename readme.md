# Employee Record Transmission and Storage System

A high-performance client-server application for processing employee records from CSV files and storing them in a MySQL database. Built with modern Python async techniques, the system offers multiple communication protocols and efficient data handling.

## Quick Start with Docker

Setting up the environment is the first step for running this application. Docker provides the easiest way to get started.

### System Requirements

- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- Internet connection (for pulling Docker images)
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### 1. Docker Setup Instructions

#### Windows:

1. Download and install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)
2. During installation, enable WSL 2 if prompted
3. After installation, start Docker Desktop and wait for it to initialize
4. Open PowerShell or Command Prompt and verify installation:
   ```
   docker --version
   docker-compose --version
   ```

#### Mac:

1. Download Docker Desktop for Mac from [docker.com](https://www.docker.com/products/docker-desktop)
2. Install Docker Desktop by dragging to Applications
3. Start Docker Desktop and wait for it to initialize (whale icon in menu bar)
4. Open Terminal and verify installation:
   ```
   docker --version
   docker-compose --version
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

### 2. Running the Application

1. Clone or download this repository to your local machine
2. Navigate to the project directory:
   ```
   cd "Employee Record Transmission and storage System"
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

6. The application is now running with:
   - Server API at http://localhost:8000
   - MySQL database at localhost:3306
   - Kafka at localhost:9092
   - Client processing employee data records

7. To stop all services:
   ```
   docker-compose down
   ```

### 3. Testing Different Communication Modes

You can run the client with different communication protocols:

```bash
# For HTTP mode (default)
docker-compose up -d -e COMM_MODE=http client

# For WebSocket mode
docker-compose up -d -e COMM_MODE=websocket client 

# For Kafka mode
docker-compose up -d -e COMM_MODE=kafka client
```

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

## Docker Components in Detail

### 1. Individual Components Setup

If you prefer to understand or run individual components:

#### MySQL Database:

```bash
# Pull the MySQL 8.0 image
docker pull mysql:8.0

# Create and run MySQL container
docker run --name mysql-database -e MYSQL_ROOT_PASSWORD=happy \
  -e MYSQL_DATABASE=employee_records -p 3306:3306 -d mysql:8.0

# Verify it's running
docker logs mysql-database
```

#### Kafka and Zookeeper:

```bash
# Create a network for Kafka components
docker network create kafka-net

# Run Zookeeper
docker run --name zookeeper --network kafka-net -p 2181:2181 -d \
  confluentinc/cp-zookeeper:7.3.2 \
  -e ZOOKEEPER_CLIENT_PORT=2181 -e ZOOKEEPER_TICK_TIME=2000

# Run Kafka
docker run --name kafka --network kafka-net -p 9092:9092 -d \
  confluentinc/cp-kafka:7.3.2 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:9092 \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT \
  -e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1

# Create the employee-records topic
docker exec -it kafka kafka-topics --create --topic employee-records \
  --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
```

### 2. Docker Compose Configuration

Our docker-compose.yml file includes:

- **server**: The FastAPI application
- **client**: The Python client for processing CSV files
- **db**: MySQL database for storing records
- **zookeeper**: Service for Kafka coordination
- **kafka**: Message broker for async communication

All these components are connected with proper networking and volume configuration for persistent storage.

## Manual Setup (Alternative to Docker)

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

### 2. Setup MySQL Manually

```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Log in and create database
sudo mysql -u root
```

Inside MySQL prompt:
```sql
CREATE DATABASE employee_records;
CREATE USER 'root'@'localhost' IDENTIFIED BY 'happy';
GRANT ALL PRIVILEGES ON employee_records.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Setup Kafka Manually

```bash
# Download Kafka
wget https://downloads.apache.org/kafka/3.4.0/kafka_2.13-3.4.0.tgz
tar -xzf kafka_2.13-3.4.0.tgz
cd kafka_2.13-3.4.0

# Start Zookeeper (in terminal 1)
bin/zookeeper-server-start.sh config/zookeeper.properties

# Start Kafka (in terminal 2)
bin/kafka-server-start.sh config/server.properties

# Create a topic (in terminal 3)
bin/kafka-topics.sh --create --topic employee-records --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### 4. Run the Server

```bash
cd server
source env/bin/activate  # On Windows: env\Scripts\activate
python main.py
```

### 5. Run the Client

```bash
cd client
source env/bin/activate  # On Windows: env\Scripts\activate

# Using command-line options to specify the mode:
python main.py --mode http     # HTTP mode
python main.py --mode websocket  # WebSocket mode
python main.py --mode kafka    # Kafka mode
```

## Useful Docker Commands

```bash
# View all running containers
docker ps

# Check logs of a specific container
docker logs [container_name]

# Stop all containers from the composition
docker-compose down

# Restart a specific service
docker-compose restart [service_name]

# Execute a command inside a container (e.g., MySQL)
docker exec -it db mysql -uroot -phappy

# Check resource usage
docker stats

# Clean up unused resources
docker system prune
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