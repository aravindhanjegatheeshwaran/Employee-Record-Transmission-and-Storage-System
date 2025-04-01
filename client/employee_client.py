# client/employee_client.py
import asyncio
import aiohttp
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from config import settings, CommunicationMode
from utils import (
    log_execution_time, 
    retry, 
    parse_csv_file, 
    save_failed_records,
    format_employee_record,
    gather_with_concurrency
)

try:
    import aiokafka
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class EmployeeClient:
    server_url: str = field(default_factory=lambda: settings.SERVER_URL)
    auth_username: str = field(default_factory=lambda: settings.AUTH_USERNAME)
    auth_password: str = field(default_factory=lambda: settings.AUTH_PASSWORD)
    comm_mode: CommunicationMode = field(default_factory=lambda: settings.COMM_MODE)
    max_workers: int = field(default_factory=lambda: settings.MAX_WORKERS)
    batch_size: int = field(default_factory=lambda: settings.BATCH_SIZE)
    timeout: float = field(default_factory=lambda: settings.TIMEOUT)
    max_retries: int = field(default_factory=lambda: settings.MAX_RETRIES)
    retry_delay: float = field(default_factory=lambda: settings.RETRY_DELAY)
    
    access_token: Optional[str] = field(default=None)
    session: Optional[aiohttp.ClientSession] = field(default=None)
    kafka_producer: Optional[Any] = field(default=None)
    websocket: Optional[Any] = field(default=None)
    
    def __post_init__(self):
        if self.comm_mode == CommunicationMode.KAFKA and not KAFKA_AVAILABLE:
            raise ImportError(
                "Kafka support requires aiokafka package. Please install it with:\n"
                "pip install aiokafka==0.8.1\n"
                "Or use HTTP mode with: --mode http"
            )
        
        if self.comm_mode == CommunicationMode.WEBSOCKET and not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "WebSocket support requires websockets package. Please install it with:\n"
                "pip install websockets==11.0.3\n"
                "Or use HTTP mode with: --mode http"
            )
    
    async def initialize(self):
        logger.info(f"Setting up {self.comm_mode} client")
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        
        if self.comm_mode == CommunicationMode.KAFKA:
            await self.initialize_kafka()
        elif self.comm_mode == CommunicationMode.WEBSOCKET:
            await self.initialize_websocket()
        
        logger.info(f"Client ready")
    
    async def close(self):
        logger.info("Cleaning up resources")
        
        if self.comm_mode == CommunicationMode.KAFKA and self.kafka_producer:
            await self.kafka_producer.stop()
        
        if self.comm_mode == CommunicationMode.WEBSOCKET and self.websocket:
            await self.websocket.close()
        
        if self.session:
            await self.session.close()
        
        logger.info("Resources released")
    
    @retry(max_retries=3, retry_delay=1.0)
    async def authenticate(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        logger.info("Getting authentication token")
        
        auth_url = f"{self.server_url}/token"
        form_data = {
            "username": self.auth_username,
            "password": self.auth_password,
        }
        
        try:
            async with self.session.post(auth_url, data=form_data, timeout=self.timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Auth failed: {response.status} - {error_text}")
                
                result = await response.json()
                self.access_token = result.get("access_token")
                
                if not self.access_token:
                    raise Exception("No token received")
                
                logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            raise
    
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
    async def send_employee_http(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session:
            raise Exception("Client not initialized")
        
        if not self.access_token:
            await self.authenticate()
        
        url = f"{self.server_url}/api/employees/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            formatted_employee = format_employee_record(employee)
            
            # Log formatted employee data for debugging
            logger.info(f"Sending employee data: {formatted_employee}")
            
            # Verify required fields are present
            required_fields = ['employee_id', 'name', 'email', 'department', 'designation', 'salary', 'date_of_joining']
            missing_fields = [field for field in required_fields if field not in formatted_employee or formatted_employee[field] is None]
            
            if missing_fields:
                raise Exception(f"Missing required fields: {', '.join(missing_fields)}")
            
            async with self.session.post(
                url, 
                json=formatted_employee,
                headers=headers,
                timeout=self.timeout
            ) as response:
                if response.status == 401:
                    logger.warning("Token expired, renewing...")
                    await self.authenticate()
                    return await self.send_employee_http(employee)
                
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                return await response.json()
        except Exception as e:
            logger.error(f"HTTP transmission error: {str(e)}")
            raise
    
    @log_execution_time
    @retry(max_retries=3, retry_delay=1.0)
    async def send_employee_kafka(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        if not self.kafka_producer:
            raise Exception("Kafka not initialized")
        
        try:
            formatted_employee = format_employee_record(employee)
            
            # Verify required fields are present
            required_fields = ['employee_id', 'name', 'email', 'department', 'designation', 'salary', 'date_of_joining']
            missing_fields = [field for field in required_fields if field not in formatted_employee or formatted_employee[field] is None]
            
            if missing_fields:
                raise Exception(f"Missing required fields: {', '.join(missing_fields)}")
            
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
    
    @log_execution_time
    @retry(max_retries=3, retry_delay=1.0)
    async def send_employee_websocket(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        if not self.websocket:
            raise Exception("WebSocket not connected")
        
        try:
            formatted_employee = format_employee_record(employee)
            
            # Verify required fields are present
            required_fields = ['employee_id', 'name', 'email', 'department', 'designation', 'salary', 'date_of_joining']
            missing_fields = [field for field in required_fields if field not in formatted_employee or formatted_employee[field] is None]
            
            if missing_fields:
                raise Exception(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Send the employee record
            employee_id = formatted_employee.get('employee_id')
            logger.info(f"Sending employee {employee_id} via WebSocket")
            await self.websocket.send(json.dumps(formatted_employee))
            
            # Wait for response with timeout
            response = await asyncio.wait_for(self.websocket.recv(), timeout=self.timeout)
            parsed_response = json.loads(response)
            
            # Add a small delay after each WebSocket message
            await asyncio.sleep(0.1)
            
            return parsed_response
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket connection closed: {str(e)}")
            logger.info("Reconnecting WebSocket...")
            try:
                await self.initialize_websocket()
                # Retry sending after reconnection
                return await self.send_employee_websocket(employee)
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect WebSocket: {str(reconnect_error)}")
                raise
        except Exception as e:
            logger.error(f"WebSocket transmission error: {str(e)}")
            raise
    
    async def send_employee(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        if self.comm_mode == CommunicationMode.HTTP:
            return await self.send_employee_http(employee)
        elif self.comm_mode == CommunicationMode.KAFKA:
            return await self.send_employee_kafka(employee)
        elif self.comm_mode == CommunicationMode.WEBSOCKET:
            return await self.send_employee_websocket(employee)
        else:
            raise ValueError(f"Unsupported mode: {self.comm_mode}")
    
    async def send_employees_concurrently(self, employees: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        tasks = []
        
        # For WebSocket mode, we'll process records one at a time
        if self.comm_mode == CommunicationMode.WEBSOCKET:
            logger.info("Using sequential processing for WebSocket mode")
            successful = []
            failed = []
            
            for employee in employees:
                try:
                    # Process one by one with delay between records
                    result = await self.send_employee(employee)
                    successful.append({
                        **employee,
                        "response": result
                    })
                    # Add extra delay between WebSocket operations
                    await asyncio.sleep(0.2)
                except Exception as e:
                    failed.append({
                        **employee,
                        "error": str(e)
                    })
            
            return successful, failed
        else:
            # For HTTP and Kafka, use concurrent processing
            for employee in employees:
                tasks.append(self.send_employee(employee))
            
            # Adjust concurrency based on communication mode
            max_concurrent = 5 if self.comm_mode == CommunicationMode.HTTP else self.max_workers
            results = await gather_with_concurrency(max_concurrent, *tasks)
            
            successful = []
            failed = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed.append({
                        **employees[i],
                        "error": str(result)
                    })
                else:
                    successful.append({
                        **employees[i],
                        "response": result
                    })
            
            return successful, failed
    
    @log_execution_time
    async def process_csv_file(self, file_path: str) -> Tuple[int, int, List[Dict[str, Any]]]:
        try:
            logger.info(f"Reading CSV file: {file_path}")
            employees = parse_csv_file(
                file_path, 
                delimiter=settings.CSV_DELIMITER,
                encoding=settings.CSV_ENCODING
            )
            
            logger.info(f"Found {len(employees)} employee records")
            
            successful_count = 0
            failed_records = []
            batch_count = (len(employees) + self.batch_size - 1) // self.batch_size
            
            # Use a smaller effective batch size and add delays between batches
            effective_batch_size = min(self.batch_size, 20)  # Limit concurrent requests
            
            for i in range(0, len(employees), effective_batch_size):
                batch = employees[i:i + effective_batch_size]
                batch_num = i // effective_batch_size + 1
                total_batches = (len(employees) + effective_batch_size - 1) // effective_batch_size
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)")
                
                # Limit concurrency by using a max_workers setting
                max_workers = min(self.max_workers, 10)  # Limit concurrent workers
                
                successful, failed = await self.send_employees_concurrently(batch)
                successful_count += len(successful)
                failed_records.extend(failed)
                
                logger.info(f"Batch {batch_num} result: {len(successful)} ok, {len(failed)} failed")
                
                # Add a delay between batches to avoid hitting rate limits
                if i + effective_batch_size < len(employees):
                    delay = 0.5  # Half second delay between batches
                    logger.info(f"Waiting {delay}s before next batch...")
                    await asyncio.sleep(delay)
            
            logger.info(f"CSV processing summary: {successful_count} successful, {len(failed_records)} failed")
            
            return len(employees), successful_count, failed_records
        except Exception as e:
            logger.error(f"CSV processing error: {str(e)}")
            raise
