Employee Record Transmission and Storage System
A high-performance client-server application for processing employee records from CSV files and storing them in a MySQL database. Built with modern Python async techniques, the system offers multiple communication protocols and efficient data handling.
Quick Start with Docker
Setting up the environment is the first step for running this application. Docker provides the easiest way to get started.
System Requirements
- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- Internet connection (for pulling Docker images)
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space
1. Docker Setup Instructions
Windows:
1. Download and install Docker Desktop from https://www.docker.com/products/docker-desktop
2. During installation, enable WSL 2 if prompted
3. After installation, start Docker Desktop and wait for it to initialize
4. Open PowerShell or Command Prompt and verify installation:
    docker --version
    docker-compose --version
Mac:
1. Download Docker Desktop for Mac from https://www.docker.com/products/docker-desktop
2. Install Docker Desktop by dragging to Applications
3. Start Docker Desktop and wait for it to initialize (whale icon in menu bar)
4. Open Terminal and verify installation:
    docker --version
    docker-compose --version
Linux:
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
2. Running the Application with Docker in WSL
1. Clone or download this repository to your local machine
2. Navigate to the project directory:
    cd "Employee Record Transmission and Storage System"

3. Make sure your docker-compose.yml is properly configured:

4. Start all services with Docker Compose (in PowerShell):
    docker-compose up -d --build

5. Check if all containers are running correctly:
    docker-compose ps

6. View the logs to ensure everything started properly:
    docker-compose logs -f

7. Create the Kafka topic if it wasn't automatically created:
    docker-compose exec kafka kafka-topics --create --topic employee-records --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1

8. The application is now running with:
- Server API at http://localhost:8000
- MySQL database at localhost:3306
- Kafka at localhost:9092
- Client processing employee data records

9. To stop all services:
    docker-compose down
3. Testing Different Communication Modes
You can run the client with different communication protocols:

```bash
# For HTTP mode (default)
docker-compose up -d -e COMM_MODE=http client

# For WebSocket mode
docker-compose up -d -e COMM_MODE=websocket client

# For Kafka mode
docker-compose up -d -e COMM_MODE=kafka client
```
Features
Server
- FastAPI-based REST API with JWT authentication
- WebSocket endpoint for real-time communication
- Kafka consumer for message-based integration
- Async database operations with SQLAlchemy ORM
- Rate limiting, validation, and comprehensive logging
Client
- Efficient CSV processing with batching
- Multiple transport protocols (HTTP, WebSocket, Kafka)
- Controlled concurrency with async semaphores
- Auto-retry with exponential backoff
- Detailed error tracking and reporting
Tech Stack
- Python: 3.9+ with asyncio
- Web Framework: FastAPI
- Database: MySQL with SQLAlchemy ORM
- Communication: HTTP, WebSockets, Kafka
- Authentication: JWT tokens
- Containerization: Docker, Docker Compose
Docker Components in Detail
1. Individual Components Setup
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
2. Docker Compose Configuration
Our docker-compose.yml file includes:

- **server**: The FastAPI application
- **client**: The Python client for processing CSV files
- **db**: MySQL database for storing records
- **zookeeper**: Service for Kafka coordination
- **kafka**: Message broker for async communication

All these components are connected with proper networking and volume configuration for persistent storage.
Manual Setup (Alternative to Docker)
1. Create Python Virtual Environments
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
2. Setup MySQL Manually
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
3. Setup Kafka Manually
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
4. Run the Server
```bash
cd server
source env/bin/activate  # On Windows: env\Scripts\activate
python main.py
```
5. Run the Client
```bash
cd client
source env/bin/activate  # On Windows: env\Scripts\activate

# Using command-line options to specify the mode:
python main.py --mode http     # HTTP mode
python main.py --mode websocket  # WebSocket mode
python main.py --mode kafka    # Kafka mode
```
Useful Docker Commands
```bash
# View all running containers
docker ps

# Check logs of a specific container
docker logs [container_name]

# Stop all containers from the composition
docker-compose down

# Restart a specific service
docker-compose restart server
```