import pytest
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.security import OAuth2PasswordBearer

from server.main import app
from server.core.database import db
from server.core.security import (
    get_password_hash, 
    create_access_token, 
    get_current_user,
    verify_password
)
from server.models.employee import Employee
from server.schemas.employee import EmployeeCreate, EmployeeUpdate


# Fixtures
@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def employee_data():
    """Sample employee data"""
    return {
        "employee_id": 1001,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "department": "Engineering",
        "designation": "Software Engineer",
        "salary": 75000,
        "date_of_joining": "2023-01-15"
    }


@pytest.fixture
def test_token():
    """Create a test JWT token"""
    return create_access_token({"sub": "admin"})


# Database mocking
@pytest.fixture(autouse=True)
def mock_db():
    """Mock database operations"""
    # Mock fetch_one to simulate employee existence check
    async def mock_fetch_one(query, params=None):
        if "WHERE employee_id = " in query and params and params[0] == 1001:
            return (1001, "Existing User", "existing@example.com", "IT", "Developer", 70000, date(2022, 1, 1))
        return None
    
    # Mock fetch_all to return sample data
    async def mock_fetch_all(query, params=None):
        if "FROM employees" in query:
            return [
                (1001, "User 1", "user1@example.com", "Engineering", "Developer", 75000, date(2023, 1, 15), 
                 datetime.now(), datetime.now()),
                (1002, "User 2", "user2@example.com", "Marketing", "Manager", 85000, date(2022, 6, 10), 
                 datetime.now(), datetime.now())
            ]
        elif "FROM departments" in query:
            return [
                ("Engineering", 10),
                ("Marketing", 5)
            ]
        return []
    
    # Mock execute to simulate successful database operations
    async def mock_execute(query, params=None):
        return 1
    
    # Mock execute_many for batch operations
    async def mock_execute_many(query, params_list=None):
        return len(params_list) if params_list else 0
    
    # Create mock db object
    with patch('server.core.database.db') as mock_db:
        mock_db.fetch_one = AsyncMock(side_effect=mock_fetch_one)
        mock_db.fetch_all = AsyncMock(side_effect=mock_fetch_all)
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.execute_many = AsyncMock(side_effect=mock_execute_many)
        yield mock_db


# Authentication mocking
@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication dependencies"""
    # Mock get_current_user to bypass authentication
    with patch('server.api.employee.get_current_active_user') as mock_auth:
        mock_auth.return_value = {"username": "test_user"}
        yield mock_auth


# Tests
def test_security_token_creation():
    """Test JWT token creation"""
    data = {"sub": "test_user"}
    token = create_access_token(data)
    assert token is not None
    assert isinstance(token, str)
    
    # Test with expiration
    token_with_expiry = create_access_token(data, expires_delta=timedelta(minutes=30))
    assert token_with_expiry is not None
    assert isinstance(token_with_expiry, str)
    assert token != token_with_expiry  # Tokens should be different


def test_security_password_hashing():
    """Test password hashing and verification"""
    password = "test_password"
    hashed = get_password_hash(password)
    
    # Hash should be different from original password
    assert hashed != password
    
    # Verification should succeed with correct password
    assert verify_password(password, hashed)
    
    # Verification should fail with incorrect password
    assert not verify_password("wrong_password", hashed)


def test_get_employees(client, test_token, mock_db):
    """Test getting all employees"""
    response = client.get(
        "/api/employees/",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Check first employee
    assert data[0]["employee_id"] == 1001
    assert data[0]["name"] == "User 1"
    assert data[0]["department"] == "Engineering"


def test_get_employee(client, test_token, mock_db):
    """Test getting a specific employee"""
    response = client.get(
        "/api/employees/1001",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == 1001
    assert data["name"] == "Existing User"
    assert data["email"] == "existing@example.com"


def test_get_nonexistent_employee(client, test_token, mock_db):
    """Test getting a non-existent employee"""
    # Override mock for this test to return None
    mock_db.fetch_one.return_value = None
    
    response = client.get(
        "/api/employees/9999",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_employee(client, test_token, employee_data, mock_db):
    """Test creating a new employee"""
    # Override mock for employee existence check
    mock_db.fetch_one.return_value = None
    
    # Add employee created date and modified date
    current_time = datetime.now()
    mock_db.fetch_one.side_effect = None
    mock_db.fetch_one.return_value = (
        employee_data["employee_id"],
        employee_data["name"],
        employee_data["email"],
        employee_data["department"],
        employee_data["designation"],
        employee_data["salary"],
        datetime.strptime(employee_data["date_of_joining"], "%Y-%m-%d").date(),
        current_time,
        current_time
    )
    
    response = client.post(
        "/api/employees/",
        json=employee_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == employee_data["employee_id"]
    assert data["name"] == employee_data["name"]
    assert data["email"] == employee_data["email"]
    
    # Check that database execute was called
    mock_db.execute.assert_called_once()


def test_create_duplicate_employee(client, test_token, employee_data, mock_db):
    """Test creating a duplicate employee"""
    # Mock to simulate employee already exists
    mock_db.fetch_one.side_effect = None
    mock_db.fetch_one.return_value = (employee_data["employee_id"],)
    
    response = client.post(
        "/api/employees/",
        json=employee_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_update_employee(client, test_token, mock_db):
    """Test updating an employee"""
    # Mock to simulate employee exists
    mock_db.fetch_one.side_effect = None
    mock_db.fetch_one.return_value = (1001,)
    
    # Update data
    update_data = {
        "name": "Updated Name",
        "salary": 80000
    }
    
    # After update fetch returns updated employee
    current_time = datetime.now()
    mock_db.fetch_one.side_effect = [
        (1001,),  # First call checks if employee exists
        (         # Second call gets updated employee details
            1001, 
            update_data["name"], 
            "existing@example.com", 
            "IT", 
            "Developer", 
            update_data["salary"], 
            date(2022, 1, 1),
            current_time,
            current_time
        )
    ]
    
    response = client.put(
        "/api/employees/1001",
        json=update_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == 1001
    assert data["name"] == update_data["name"]
    assert data["salary"] == update_data["salary"]
    
    # Check that database execute was called
    mock_db.execute.assert_called_once()


def test_update_nonexistent_employee(client, test_token, mock_db):
    """Test updating a non-existent employee"""
    # Mock to simulate employee doesn't exist
    mock_db.fetch_one.return_value = None
    
    update_data = {
        "name": "Updated Name",
        "salary": 80000
    }
    
    response = client.put(
        "/api/employees/9999",
        json=update_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_employee(client, test_token, mock_db):
    """Test deleting an employee"""
    # Mock to simulate employee exists
    mock_db.fetch_one.return_value = (1001,)
    
    response = client.delete(
        "/api/employees/1001",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "deleted successfully" in data["message"].lower()
    
    # Check that database execute was called
    mock_db.execute.assert_called_once()


def test_delete_nonexistent_employee(client, test_token, mock_db):
    """Test deleting a non-existent employee"""
    # Mock to simulate employee doesn't exist
    mock_db.fetch_one.return_value = None
    
    response = client.delete(
        "/api/employees/9999",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_bulk_create_employees(client, test_token, employee_data, mock_db):
    """Test bulk creation of employees"""
    employees = [
        employee_data,
        {**employee_data, "employee_id": 1002, "name": "Jane Smith", "email": "jane.smith@example.com"}
    ]
    
    response = client.post(
        "/api/employees/bulk",
        json={"employees": employees},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    
    # Check that database execute_many was called
    mock_db.execute_many.assert_called_once()


def test_employee_department_stats(client, test_token, mock_db):
    """Test getting employee counts by department"""
    response = client.get(
        "/api/employees/stats/department",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Check first department
    assert data[0]["department"] == "Engineering"
    assert data[0]["count"] == 10
    
    # Check second department
    assert data[1]["department"] == "Marketing"
    assert data[1]["count"] == 5


def test_authentication_required(client):
    """Test that authentication is required"""
    # Try without authentication token
    response = client.get("/api/employees/")
    assert response.status_code == 401
    
    # Try with invalid token
    response = client.get(
        "/api/employees/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
