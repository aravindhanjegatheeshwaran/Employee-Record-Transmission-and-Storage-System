# server/main.py
import asyncio
import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from contextlib import asynccontextmanager

from core.database import get_db, employee_repository, close_db
from api import api, auth
from api.api import router as employees_orm_router
from core.security import get_current_user
from schemas.schema import EmployeeCreate

# Try to import aiokafka for Kafka consumer 
try:
    import aiokafka
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger(__name__)

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
    
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


app = FastAPI(
    title="Employee Record System API",
    description="API for managing employee records",
    version="1.1.0",
    lifespan=lifespan
)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


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
        
        if not auth_header.startswith("Bearer "):
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": "Unauthorized: Missing or invalid token"
            }))
            await websocket.close()
            return
        
        token = auth_header.replace("Bearer ", "")
        
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
        
        await manager.connect(websocket, client_id)
        
        while True:
            data = await websocket.receive_text()
            try:
                employee_data = json.loads(data)
                logger.info(f"Received WebSocket message: {employee_data}")
                
                # Process employee data
                async with get_db() as db:
                    # Check if employee exists
                    employee_id = employee_data.get("employee_id")
                    if not employee_id:
                        await manager.send_response({
                            "status": "error",
                            "message": "Invalid employee data: missing employee_id"
                        }, websocket)
                        continue
                    
                    exists = await employee_repository.exists(db, employee_id)
                    if exists:
                        await manager.send_response({
                            "status": "error",
                            "message": f"Employee ID {employee_id} already exists"
                        }, websocket)
                        continue
                    
                    # Create employee
                    employee = EmployeeCreate(**employee_data)
                    new_employee = await employee_repository.create(db, employee.dict())
                    
                    # Send success response
                    await manager.send_response({
                        "status": "success",
                        "message": f"Employee created: {employee_id}",
                        "employee_id": employee_id
                    }, websocket)
                    
            except json.JSONDecodeError:
                await manager.send_response({
                    "status": "error",
                    "message": "Invalid JSON data"
                }, websocket)
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await manager.send_response({
                    "status": "error",
                    "message": f"Error: {str(e)}"
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close()
        except:
            pass


app.include_router(auth.router)
app.include_router(api.router)
app.include_router(employees_orm_router)


@app.get("/", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "message": "Server is running",
        "version": "1.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = bool(os.getenv("DEBUG", "True").lower() == "true")
    
    print(f"Starting server on {host}:{port}")
    print("Press CTRL+C to stop")
    
    # Run the application directly
    uvicorn.run(app, host=host, port=port, reload=reload)