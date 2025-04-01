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

### 2. Setup MySQL and Kafka with Docker (Individual Components)

You can run MySQL and Kafka as individual Docker containers for development or testing.

#### Setup MySQL:

1. Pull the MySQL Docker image:
   ```
   docker pull mysql:8.0
   ```

2. Create and run a MySQL container:
   ```
   docker run --name mysql-container -e MYSQL_ROOT_PASSWORD=happy -e MYSQL_DATABASE=employee_records -p 3306:3306 -d mysql:8.0
   ```

3. Verify the MySQL container is running:
   ```
   docker ps
   ```

4. Test connection to MySQL:
   ```
   docker exec -it mysql-container mysql -uroot -phappy -e "SHOW DATABASES;"
   ```

#### Setup Kafka with Zookeeper:

1. Pull the required Docker images:
   ```
   docker pull confluentinc/cp-zookeeper:7.3.2
   docker pull confluentinc/cp-kafka:7.3.2
   ```

2. Create a Docker network for Kafka and Zookeeper:
   ```
   docker network create kafka-network
   ```

3. Start Zookeeper container:
   ```
   docker run --name zookeeper-container --network kafka-network -p 2181:2181 -d confluentinc/cp-zookeeper:7.3.2 -e ZOOKEEPER_CLIENT_PORT=2181 -e ZOOKEEPER_TICK_TIME=2000
   ```

4. Start Kafka container:
   ```
   docker run --name kafka-container --network kafka-network -p 9092:9092 -d confluentinc/cp-kafka:7.3.2 -e KAFKA_BROKER_ID=1 -e KAFKA_ZOOKEEPER_CONNECT=zookeeper-container:2181 -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka-container:9092,PLAINTEXT_HOST://localhost:9092 -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT -e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 -e KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
   ```

5. Verify Kafka and Zookeeper containers are running:
   ```
   docker ps
   ```

6. Create a Kafka topic for employee records:
   ```
   docker exec -it kafka-container kafka-topics --create --topic employee-records --bootstrap-server kafka-container:9092 --partitions 1 --replication-factor 1
   ```

7. List the created topics to verify:
   ```
   docker exec -it kafka-container kafka-topics --list --bootstrap-server kafka-container:9092
   ```

### 3. Running the Complete System with Docker Compose

Docker Compose simplifies managing multiple containers. Follow these steps to run the entire application stack:

1. Create a new directory for your project and navigate to it:
   ```
   mkdir employee-system
   cd employee-system
   ```

2. Download or copy all project files to this directory, including:
   - docker-compose.yml
   - dockerfile-client
   - dockerfile-server
   - client/ directory
   - server/ directory

3. Build and start all services with a single command:
   ```
   docker-compose up -d --build
   ```
   This will:
   - Build the server image
   - Build the client image
   - Start MySQL database
   - Start Zookeeper
   - Start Kafka
   - Connect all services together

4. Check if all containers are running:
   ```
   docker-compose ps
   ```

5. View the logs to ensure everything is working:
   ```
   docker-compose logs -f
   ```

6. To stop all services:
   ```
   docker-compose down
   ```

### 4. Testing Different Communication Modes

To test the client with different communication protocols:

1. For HTTP mode (default):
   ```
   docker-compose up -d -e COMM_MODE=http client
   ```

2. For WebSocket mode:
   ```
   docker-compose up -d -e COMM_MODE=websocket client
   ```

3. For Kafka mode:
   ```
   docker-compose up -d -e COMM_MODE=kafka client
   ```

### 5. Running Specific Components

You can run just certain parts of the system if needed:

1. Run just the server with database and messaging:
   ```
   docker-compose up -d server db zookeeper kafka
   ```

2. Run only the data infrastructure (without applications):
   ```
   docker-compose up -d db zookeeper kafka
   ```

### 6. Useful Docker Commands

Here are some helpful Docker commands for managing your containers:

```
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

# Check resource usage of containers
docker stats

# Clean up unused resources
docker system prune

# View networks
docker network ls

# Inspect a container
docker inspect [container_name]
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