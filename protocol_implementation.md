# WebSocket and Kafka Implementation Documentation

This document explains how WebSocket and Kafka communication protocols are implemented in the Employee Record Transmission and Storage System.

## WebSocket Implementation

The WebSocket implementation enables real-time bidirectional communication between the client and server.

### Server-Side Implementation

The WebSocket implementation on the server side is in `server/main.py`:

```python
# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_response(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))


manager = ConnectionManager()


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Get authorization token from headers
        headers = dict(websocket.headers)
        auth_header = headers.get("authorization", "")
        
        # Authentication check
        if not auth_header.startswith("Bearer "):
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": "Unauthorized: Missing or invalid token"
            }))
            await websocket.close()
            return
        
        token = auth_header.replace("Bearer ", "")
        
        # Verify token
        try:
            user = await get_current_user(token)
            client_id = f"{user.username}_{id(websocket)}"
        except Exception:
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": "Unauthorized: Invalid token"
            }))
            await websocket.close()
            return
        
        # Register connection
        await manager.connect(websocket, client_id)
        
        # Handle messages
        while True:
            data = await websocket.receive_text()
            try:
                employee_data = json.loads(data)
                logger.info(f"Received WebSocket message: {employee_data}")
                
                # Process employee data
                async with get_db() as db:
                    # Data validation
                    employee_id = employee_data.get("employee_id")
                    if not employee_id:
                        await manager.send_response({
                            "status": "error",
                            "message": "Invalid employee data: missing employee_id"
                        }, websocket)
                        continue
                    
                    # Check for duplicates
                    exists = await employee_repository.exists(db, employee_id)
                    if exists:
                        await manager.send_response({
                            "status": "error",
                            "message": f"Employee ID {employee_id} already exists"
                        }, websocket)
                        continue
                    
                    # Create employee record
                    employee = EmployeeCreate(**employee_data)
                    new_employee = await employee_repository.create(db, employee.dict())
                    
                    # Send confirmation
                    await manager.send_response({
                        "status": "success",
                        "message": f"Employee created: {employee_id}",
                        "employee_id": employee_id
                    }, websocket)
            except Exception as e:
                # Error handling
                await manager.send_response({
                    "status": "error",
                    "message": f"Error: {str(e)}"
                }, websocket)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

### Client-Side Implementation

The WebSocket implementation in the client is in `client/employee_client.py`:

```python
async def initialize_websocket(self):
    logger.info("Opening WebSocket connection")
    
    try:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.websocket = await websockets.connect(
            settings.WS_URL,
            extra_headers=headers
        )
        logger.info("WebSocket connected")
    except Exception as e:
        logger.error(f"WebSocket connection failed: {str(e)}")
        raise

@log_execution_time
@retry(max_retries=3, retry_delay=1.0)
async def send_employee_websocket(self, employee: Dict[str, Any]) -> Dict[str, Any]:
    if not self.websocket:
        raise Exception("WebSocket not connected")
    
    try:
        formatted_employee = format_employee_record(employee)
        await self.websocket.send(json.dumps(formatted_employee))
        
        response = await asyncio.wait_for(self.websocket.recv(), timeout=self.timeout)
        return json.loads(response)
    except Exception as e:
        logger.error(f"WebSocket transmission error: {str(e)}")
        
        if isinstance(e, websockets.exceptions.ConnectionClosed):
            logger.info("Reconnecting WebSocket...")
            await self.initialize_websocket()
        
        raise
```

## Kafka Implementation

Kafka provides an asynchronous message-based communication system that decouples the client and server.

### Server-Side Kafka Implementation

The Kafka consumer is implemented in `server/main.py`:

```python
# Kafka consumer
kafka_consumer = None
kafka_task = None

async def start_kafka_consumer():
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka support not available. Install aiokafka package.")
        return

    try:
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        topic = os.getenv("KAFKA_TOPIC", "employee-records")

        consumer = aiokafka.AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        await consumer.start()
        logger.info(f"Kafka consumer started for topic: {topic}")

        async for msg in consumer:
            try:
                logger.info(f"Received Kafka message: {msg.value}")
                employee_data = msg.value
                
                async with get_db() as db:
                    # Check if employee exists
                    employee_id = employee_data.get("employee_id")
                    if not employee_id:
                        logger.error("Invalid employee data: missing employee_id")
                        continue
                    
                    exists = await employee_repository.exists(db, employee_id)
                    if exists:
                        logger.warning(f"Employee ID {employee_id} already exists")
                        continue
                    
                    # Create employee
                    employee = EmployeeCreate(**employee_data)
                    await employee_repository.create(db, employee.dict())
                    logger.info(f"Employee created via Kafka: {employee_id}")
            except Exception as e:
                logger.error(f"Error processing Kafka message: {str(e)}")
    except Exception as e:
        logger.error(f"Kafka consumer error: {str(e)}")
    finally:
        await consumer.stop()
```

The Kafka consumer is initialized in the application's lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_consumer, kafka_task
    
    logger.info("Starting server...")
    
    # Start Kafka consumer if available
    if KAFKA_AVAILABLE:
        kafka_task = asyncio.create_task(start_kafka_consumer())
    
    yield
    
    logger.info("Shutting down, closing connections...")
    
    # Cancel Kafka consumer task
    if kafka_task:
        kafka_task.cancel()
        try:
            await kafka_task
        except asyncio.CancelledError:
            pass
```

### Client-Side Kafka Implementation

The client-side Kafka implementation is in `client/employee_client.py`:

```python
async def initialize_kafka(self):
    logger.info("Setting up Kafka producer")
    
    try:
        self.kafka_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        await self.kafka_producer.start()
        logger.info("Kafka producer ready")
    except Exception as e:
        logger.error(f"Kafka setup failed: {str(e)}")
        raise

@log_execution_time
@retry(max_retries=3, retry_delay=1.0)
async def send_employee_kafka(self, employee: Dict[str, Any]) -> Dict[str, Any]:
    if not self.kafka_producer:
        raise Exception("Kafka not initialized")
    
    try:
        formatted_employee = format_employee_record(employee)
        await self.kafka_producer.send_and_wait(
            settings.KAFKA_TOPIC,
            formatted_employee
        )
        
        return {
            "status": "success",
            "message": f"Record sent to Kafka topic {settings.KAFKA_TOPIC}"
        }
    except Exception as e:
        logger.error(f"Kafka transmission error: {str(e)}")
        raise
```

## Protocol Comparison

| Feature | HTTP | WebSocket | Kafka |
|---------|------|-----------|-------|
| Connection Type | Stateless | Persistent | Decoupled |
| Communication | Request-Response | Bidirectional | Asynchronous |
| Best For | Standard operations | Real-time updates | High-volume, resilient delivery |
| Error Handling | Immediate feedback | Real-time feedback | Eventual consistency |
| Implementation Complexity | Low | Medium | High |

## Testing WebSocket and Kafka

### Testing WebSocket

Use the provided test_websocket.py script to verify WebSocket connectivity:

```bash
python test_websocket.py --server http://localhost:8000
```

### Testing Kafka

To test Kafka, ensure Kafka and Zookeeper are running, then use:

```bash
# Run the client in Kafka mode
python main.py --mode kafka

# To inspect the Kafka topic
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic employee-records --from-beginning
```

## Troubleshooting

### WebSocket Issues
- 404 Error: Verify the WebSocket URL is correct (ws://localhost:8000/ws for direct connection)
- Authentication errors: Ensure the token is valid and properly included in headers
- Connection closed: Check for network issues or server timeouts

### Kafka Issues
- Connection errors: Verify Kafka and Zookeeper are running
- Missing package: Install aiokafka using `pip install aiokafka==0.8.1`
- Topic not found: Create the topic manually if it doesn't exist

## Performance Considerations

- WebSocket connections are persistent and ideal for real-time updates but consume more server resources
- Kafka offers high throughput but adds complexity and requires additional infrastructure
- For most use cases, the HTTP mode is simpler and more straightforward