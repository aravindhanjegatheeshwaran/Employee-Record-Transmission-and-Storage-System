import pytest
import asyncio
import aiohttp
import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import sys
import os

# Add parent directory to path to make imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from client.employee_client import EmployeeClient
from client.config import CommunicationMode


# Fixtures
@pytest.fixture
def employee_record():
    """Sample employee record"""
    return {
        "employee_id": 1001,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "department": "Engineering",
        "designation": "Software Engineer",
        "salary": 75000,
        "date_of_joining": datetime(2023, 1, 15).date()
    }


@pytest.fixture
def mock_response():
    """Mock HTTP response"""
    mock = AsyncMock()
    mock.status = 200
    mock.json = AsyncMock(return_value={"status": "success"})
    mock.text = AsyncMock(return_value="Mock response text")
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
async def mock_client(mock_response):
    """Configured client with mocked session"""
    client = EmployeeClient(
        server_url="http://localhost:8000",
        auth_username="test",
        auth_password="test",
        comm_mode=CommunicationMode.HTTP,
        max_workers=5,
        batch_size=10,
        timeout=1.0,
        max_retries=1,
        retry_delay=0.1
    )
    
    # Mock session and auth
    client.session = AsyncMock()
    client.session.post = AsyncMock(return_value=mock_response)
    client.session.close = AsyncMock()
    client.access_token = "mock_token"
    
    return client


# Tests
@pytest.mark.asyncio
async def test_initialize(mock_client):
    """Test client initialization"""
    # Mock authenticate method
    mock_client.authenticate = AsyncMock()
    
    # Call initialize
    await mock_client.initialize()
    
    # Check authenticate was called
    mock_client.authenticate.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate(mock_client, mock_response):
    """Test authentication"""
    # Reset mock to test authenticate
    mock_client.access_token = None
    mock_client.authenticate = EmployeeClient.authenticate
    
    # Mock session.post
    mock_client.session.post.return_value.__aenter__.return_value.json.return_value = {
        "access_token": "test_token",
        "token_type": "bearer"
    }
    
    # Call authenticate
    await mock_client.authenticate(mock_client)
    
    # Check token was set
    assert mock_client.access_token == "test_token"
    
    # Check session.post was called with correct args
    mock_client.session.post.assert_called_once()
    args, kwargs = mock_client.session.post.call_args
    assert args[0] == "http://localhost:8000/token"


@pytest.mark.asyncio
async def test_send_employee_http(mock_client, employee_record, mock_response):
    """Test sending employee via HTTP"""
    # Call send_employee_http
    result = await mock_client.send_employee_http(employee_record)
    
    # Check result
    assert result == {"status": "success"}
    
    # Check session.post was called
    mock_client.session.post.assert_called_once()
    args, kwargs = mock_client.session.post.call_args
    assert args[0] == "http://localhost:8000/api/employees/"
    assert kwargs["headers"] == {"Authorization": "Bearer mock_token"}


@pytest.mark.asyncio
async def test_send_employee_http_retry_on_401(mock_client, employee_record):
    """Test retry on 401 Unauthorized"""
    # First response is 401, second is 200
    unauthorized_response = AsyncMock()
    unauthorized_response.status = 401
    unauthorized_response.__aenter__ = AsyncMock(return_value=unauthorized_response)
    unauthorized_response.__aexit__ = AsyncMock(return_value=None)
    
    success_response = AsyncMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value={"status": "success"})
    success_response.__aenter__ = AsyncMock(return_value=success_response)
    success_response.__aexit__ = AsyncMock(return_value=None)
    
    # Mock session.post to return unauthorized then success
    mock_client.session.post.side_effect = [unauthorized_response, success_response]
    
    # Mock authenticate
    mock_client.authenticate = AsyncMock()
    
    # Call send_employee_http
    result = await mock_client.send_employee_http(employee_record)
    
    # Check authenticate was called
    mock_client.authenticate.assert_called_once()
    
    # Check session.post was called twice
    assert mock_client.session.post.call_count == 2
    
    # Check result
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_send_employees_concurrently(mock_client, employee_record):
    """Test sending multiple employees concurrently"""
    # Create list of employees
    employees = [
        {**employee_record, "employee_id": 1001},
        {**employee_record, "employee_id": 1002},
        {**employee_record, "employee_id": 1003},
    ]
    
    # Mock send_employee to return success
    mock_client.send_employee = AsyncMock(return_value={"status": "success"})
    
    # Call send_employees_concurrently
    successful, failed = await mock_client.send_employees_concurrently(employees)
    
    # Check results
    assert len(successful) == 3
    assert len(failed) == 0
    
    # Check send_employee was called for each employee
    assert mock_client.send_employee.call_count == 3


@pytest.mark.asyncio
async def test_send_employees_concurrently_with_failures(mock_client, employee_record):
    """Test sending multiple employees with some failures"""
    # Create list of employees
    employees = [
        {**employee_record, "employee_id": 1001},
        {**employee_record, "employee_id": 1002},
        {**employee_record, "employee_id": 1003},
    ]
    
    # Mock send_employee to succeed for first two, fail for third
    side_effects = [
        {"status": "success"},
        {"status": "success"},
        Exception("Test error")
    ]
    
    async def mock_send_employee(employee):
        effect = side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect
    
    mock_client.send_employee = mock_send_employee
    
    # Call send_employees_concurrently
    successful, failed = await mock_client.send_employees_concurrently(employees)
    
    # Check results
    assert len(successful) == 2
    assert len(failed) == 1
    assert failed[0]["employee_id"] == 1003
    assert "error" in failed[0]
    assert "Test error" in failed[0]["error"]


@pytest.mark.parametrize("comm_mode", [
    CommunicationMode.HTTP,
    pytest.param(CommunicationMode.KAFKA, marks=pytest.mark.skipif(not hasattr(pytest, "skip_kafka"), reason="Kafka not available")),
    pytest.param(CommunicationMode.WEBSOCKET, marks=pytest.mark.skipif(not hasattr(pytest, "skip_websocket"), reason="WebSockets not available")),
])
@pytest.mark.asyncio
async def test_send_employee_dispatch(mock_client, employee_record, comm_mode):
    """Test send_employee dispatches to correct method based on comm_mode"""
    # Set communication mode
    mock_client.comm_mode = comm_mode
    
    # Mock specific send methods
    mock_client.send_employee_http = AsyncMock(return_value={"status": "success", "mode": "http"})
    mock_client.send_employee_kafka = AsyncMock(return_value={"status": "success", "mode": "kafka"})
    mock_client.send_employee_websocket = AsyncMock(return_value={"status": "success", "mode": "websocket"})
    
    # Call send_employee
    result = await mock_client.send_employee(employee_record)
    
    # Check correct method was called
    if comm_mode == CommunicationMode.HTTP:
        mock_client.send_employee_http.assert_called_once_with(employee_record)
        assert result["mode"] == "http"
    elif comm_mode == CommunicationMode.KAFKA:
        mock_client.send_employee_kafka.assert_called_once_with(employee_record)
        assert result["mode"] == "kafka"
    elif comm_mode == CommunicationMode.WEBSOCKET:
        mock_client.send_employee_websocket.assert_called_once_with(employee_record)
        assert result["mode"] == "websocket"


@pytest.mark.asyncio
async def test_process_csv_file(mock_client, employee_record, tmp_path):
    """Test processing CSV file"""
    # Create temporary CSV file
    csv_path = tmp_path / "test_employees.csv"
    
    with open(csv_path, "w") as f:
        f.write("Employee ID,Name,Email,Department,Designation,Salary,Date of Joining\n")
        for i in range(1, 6):
            f.write(f"{1000+i},Test User {i},user{i}@example.com,Engineering,Developer,75000,2023-01-15\n")
    
    # Mock send_employees_concurrently
    mock_client.send_employees_concurrently = AsyncMock(return_value=(
        # 3 successful, 2 failed
        [{}, {}, {}],
        [{"employee_id": 1004, "error": "Test error"}, {"employee_id": 1005, "error": "Test error"}]
    ))
    
    # Call process_csv_file
    total, successful, failed = await mock_client.process_csv_file(str(csv_path))
    
    # Check results
    assert total == 5
    assert successful == 3
    assert len(failed) == 2
    
    # Check send_employees_concurrently was called once
    mock_client.send_employees_concurrently.assert_called_once()
    
    # Check arguments
    args, kwargs = mock_client.send_employees_concurrently.call_args
    assert len(args[0]) == 5  # 5 employees


@pytest.mark.asyncio
async def test_close(mock_client):
    """Test closing the client"""
    # Mock close methods
    mock_client.kafka_producer = AsyncMock()
    mock_client.kafka_producer.stop = AsyncMock()
    
    mock_client.websocket = AsyncMock()
    mock_client.websocket.close = AsyncMock()
    
    # Call close
    await mock_client.close()
    
    # Check session.close was called
    mock_client.session.close.assert_called_once()
    
    # Check kafka_producer.stop was called
    mock_client.kafka_producer.stop.assert_called_once()
    
    # Check websocket.close was called
    mock_client.websocket.close.assert_called_once()
