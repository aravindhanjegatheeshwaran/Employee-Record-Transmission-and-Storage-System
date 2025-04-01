# client/employee_client.py
import asyncio
import aiohttp
import json
import logging
import time
import sys
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from config import settings, CommunicationMode
from utils import (
    log_execution_time, 
    retry, 
    process_in_batches, 
    parse_csv_file, 
    save_failed_records,
    format_employee_record,
    gather_with_concurrency
)

# For Kafka support if needed
try:
    import aiokafka
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

# For WebSockets support if needed
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class EmployeeClient:
    """Client for sending employee records to the server"""
    server_url: str = field(default_factory=lambda: settings.SERVER_URL)
    auth_username: str = field(default_factory=lambda: settings.AUTH_USERNAME)
    auth_password: str = field(default_factory=lambda: settings.AUTH_PASSWORD)
    comm_mode: CommunicationMode = field(default_factory=lambda: settings.COMM_MODE)
    max_workers: int = field(default_factory=lambda: settings.MAX_WORKERS)
    batch_size: int = field(default_factory=lambda: settings.BATCH_SIZE)
    timeout: float = field(default_factory=lambda: settings.TIMEOUT)
    max_retries: int = field(default_factory=lambda: settings.MAX_RETRIES)
    retry_delay: float = field(default_factory=lambda: settings.RETRY_DELAY)
    
    # Runtime state
    access_token: Optional[str] = field(default=None)
    session: Optional[aiohttp.ClientSession] = field(default=None)
    kafka_producer: Optional[Any] = field(default=None)
    websocket: Optional[Any] = field(default=None)
    
    def __post_init__(self):
        # Validate communication mode
        if self.comm_mode == CommunicationMode.KAFKA and not KAFKA_AVAILABLE:
            raise ImportError("Kafka support requires aiokafka package. "
                              "Install it with 'pip install aiokafka'")
        
        if self.comm_mode == CommunicationMode.WEBSOCKET and not WEBSOCKETS_AVAILABLE:
            raise ImportError("WebSocket support requires websockets package. "
                              "Install it with 'pip install websockets'")
    
    async def initialize(self):
        """Initialize the client"""
        logger.info(f"Initializing {self.comm_mode} client...")
        
        # Create HTTP session
        self.session = aiohttp.ClientSession()
        
        # Authenticate and get token
        await self.authenticate()
        
        # Initialize specific communication mode
        if self.comm_mode == CommunicationMode.KAFKA:
            await self.initialize_kafka()
        elif self.comm_mode == CommunicationMode.WEBSOCKET:
            await self.initialize_websocket()
        
        logger.info(f"{self.comm_mode} client initialized successfully")
    
    async def close(self):
        """Close the client"""
        logger.info("Closing client...")
        
        # Close specific communication mode resources
        if self.comm_mode == CommunicationMode.KAFKA and self.kafka_producer:
            await self.kafka_producer.stop()
        
        if self.comm_mode == CommunicationMode.WEBSOCKET and self.websocket:
            await self.websocket.close()
        
        # Close HTTP session
        if self.session:
            await self.session.close()
        
        logger.info("Client closed successfully")
    
    @retry(max_retries=3, retry_delay=1.0)
    async def authenticate(self):
        """Authenticate with the server and get access token"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        logger.info("Authenticating with server...")
        
        auth_url = f"{self.server_url}/token"
        form_data = {
            "username": self.auth_username,
            "password": self.auth_password,
        }
        
        try:
            async with self.session.post(auth_url, data=form_data, timeout=self.timeout) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: {response.status} - {error_text}")
                
                result = await response.json()
                self.access_token = result.get("access_token")
                
                if not self.access_token:
                    raise Exception("No access token received from server")
                
                logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise
    
    async def initialize_kafka(self):
        """Initialize Kafka producer"""
        if not KAFKA_AVAILABLE:
            raise ImportError("Kafka support requires aiokafka package")
        
        logger.info("Initializing Kafka producer...")
        
        try:
            self.kafka_producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            await self.kafka_producer.start()
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            raise
    
    async def initialize_websocket(self):
        """Initialize WebSocket connection"""
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("WebSocket support requires websockets package")
        
        logger.info("Initializing WebSocket connection...")
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.websocket = await websockets.connect(
                settings.WS_URL,
                extra_headers=headers
            )
            logger.info("WebSocket connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket connection: {str(e)}")
            raise
    
    @log_execution_time
    @retry(max_retries=3, retry_delay=1.0)
    async def send_employee_http(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """Send an employee record via HTTP API"""
        if not self.session:
            raise Exception("Client not initialized. Call initialize() first.")
        
        if not self.access_token:
            await self.authenticate()
        
        url = f"{self.server_url}/api/employees/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            formatted_employee = format_employee_record(employee)
            
            async with self.session.post(
                url, 
                json=formatted_employee,
                headers=headers,
                timeout=self.timeout
            ) as response:
                # Check for unauthorized and re-authenticate if needed
                if response.status == 401:
                    logger.warning("Authentication token expired, re-authenticating...")
                    await self.authenticate()
                    return await self.send_employee_http(employee)
                
                # Handle other error responses
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"Error {response.status}: {error_text}")
                
                # Parse response
                result = await response.json()
                return result
        except Exception as e:
            logger.error(f"Error sending employee via HTTP: {str(e)}")
            raise
    
    @log_execution_time
    @retry(max_retries=3, retry_delay=1.0)
    async def send_employee_kafka(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """Send an employee record via Kafka"""
        if not self.kafka_producer:
            raise Exception("Kafka producer not initialized")
        
        try:
            formatted_employee = format_employee_record(employee)
            
            # Send the message to Kafka
            await self.kafka_producer.send_and_wait(
                settings.KAFKA_TOPIC,
                formatted_employee
            )
            
            # Return a success response
            return {
                "status": "success",
                "message": f"Employee record sent to Kafka topic {settings.KAFKA_TOPIC}"
            }
        except Exception as e:
            logger.error(f"Error sending employee via Kafka: {str(e)}")
            raise
    
    @log_execution_time
    @retry(max_retries=3, retry_delay=1.0)
    async def send_employee_websocket(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """Send an employee record via WebSocket"""
        if not self.websocket:
            raise Exception("WebSocket connection not initialized")
        
        try:
            formatted_employee = format_employee_record(employee)
            
            # Send the message via WebSocket
            await self.websocket.send(json.dumps(formatted_employee))
            
            # Wait for acknowledgement from server
            response = await asyncio.wait_for(self.websocket.recv(), timeout=self.timeout)
            result = json.loads(response)
            
            return result
        except Exception as e:
            logger.error(f"Error sending employee via WebSocket: {str(e)}")
            
            # Try to reconnect if WebSocket is closed
            if isinstance(e, websockets.exceptions.ConnectionClosed):
                logger.info("Reconnecting WebSocket...")
                await self.initialize_websocket()
            
            raise
    
    async def send_employee(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """Send an employee record using the configured communication mode"""
        if self.comm_mode == CommunicationMode.HTTP:
            return await self.send_employee_http(employee)
        elif self.comm_mode == CommunicationMode.KAFKA:
            return await self.send_employee_kafka(employee)
        elif self.comm_mode == CommunicationMode.WEBSOCKET:
            return await self.send_employee_websocket(employee)
        else:
            raise ValueError(f"Unsupported communication mode: {self.comm_mode}")
    
    async def send_employees_concurrently(self, employees: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Send multiple employee records concurrently"""
        tasks = []
        for employee in employees:
            tasks.append(self.send_employee(employee))
        
        # Use semaphore to limit concurrency
        results = await gather_with_concurrency(self.max_workers, *tasks)
        
        # Process results
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
        """Process CSV file and send all employee records to server"""
        try:
            # Parse CSV file
            logger.info(f"Parsing CSV file: {file_path}")
            employees = parse_csv_file(
                file_path, 
                delimiter=settings.CSV_DELIMITER,
                encoding=settings.CSV_ENCODING
            )
            
            logger.info(f"Found {len(employees)} employee records in CSV file")
            
            # Process employees in batches
            successful_count = 0
            failed_records = []
            
            for i in range(0, len(employees), self.batch_size):
                batch = employees[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(employees) + self.batch_size - 1)//self.batch_size}")
                
                successful, failed = await self.send_employees_concurrently(batch)
                successful_count += len(successful)
                failed_records.extend(failed)
                
                logger.info(f"Batch {i//self.batch_size + 1} completed: {len(successful)} successful, {len(failed)} failed")
            
            # Log summary
            logger.info(f"CSV processing completed: {successful_count} successful, {len(failed_records)} failed")
            
            return len(employees), successful_count, failed_records
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            raise
