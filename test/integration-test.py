import pytest
import asyncio
import os
import subprocess
import time
import json
import aiohttp
import csv
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Path to docker-compose.yml
DOCKER_COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")

# Test configuration
TEST_CSV_PATH = os.path.join(os.path.dirname(__file__), "test_data", "test_employees.csv")
SERVER_URL = "http://localhost:8000"
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "adminpassword"

# Test employee data
TEST_EMPLOYEES = [
    {
        "employee_id": 5001,
        "name": "Test User 1",
        "email": "test1@example.com",
        "department": "Engineering",
        "designation": "Software Engineer",
        "salary": 75000,
        "date_of_joining": "2023-01-15"
    },
    {
        "employee_id": 5002,
        "name": "Test User 2",
        "email": "test2@example.com",
        "department": "Marketing",
        "designation": "Marketing Manager",
        "salary": 85000,
        "date_of_joining": "2023-02-20"
    },
    {
        "employee_id": 5003,
        "name": "Test User 3",
        "email": "test3@example.com",
        "department": "Finance",
        "designation": "Financial Analyst",
        "salary": 65000,
        "date_of_joining": "2023-03-10"
    }
]


# Fixtures
@pytest.fixture(scope="module")
def create_test_csv():
    """Create a test CSV file"""
    # Create test_data directory if it doesn't exist
    os.makedirs(os.path.dirname(TEST_CSV_PATH), exist_ok=True)
    
    # Write test data to CSV
    with open(TEST_CSV_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Employee ID", "Name", "Email", "Department", "Designation", "Salary", "Date of Joining"])
        
        for employee in TEST_EMPLOYEES:
            writer.writerow([
                employee["employee_id"],
                employee["name"],
                employee["email"],
                employee["department"],
                employee["designation"],
                employee["salary"],
                employee["date_of_joining"]
            ])
    
    yield TEST_CSV_PATH
    
    # Cleanup
    if os.path.exists(TEST_CSV_PATH):
        os.remove(TEST_CSV_PATH)


@pytest.fixture(scope="module")
def docker_compose_up(create_test_csv):
    """Start Docker Compose environment"""
    print("Starting Docker Compose environment...")
    subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "up", "-d", "--build"])
    
    # Wait for services to be ready
    max_retries = 30
    retry_delay = 2
    retries = 0
    
    while retries < max_retries:
        try:
            # Check if the server is ready
            subprocess.run(
                ["curl", "-s", f"{SERVER_URL}/"],
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            print("Docker Compose environment is ready")
            break
        except subprocess.CalledProcessError:
            retries += 1
            print(f"Waiting for services to be ready ({retries}/{max_retries})...")
            time.sleep(retry_delay)
    
    if retries >= max_retries:
        subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "logs"])
        pytest.fail("Docker Compose services failed to start")
    
    yield
    
    # Cleanup
    print("Stopping Docker Compose environment...")
    subprocess.run(["docker-compose", "-f", DOCKER_COMPOSE_FILE, "down", "-v"])


@pytest.fixture
async def auth_token(docker_compose_up):
    """Get authentication token"""
    async with aiohttp.ClientSession() as session:
        form_data = {
            "username": AUTH_USERNAME,
            "password": AUTH_PASSWORD
        }
        
        async with session.post(f"{SERVER_URL}/token", data=form_data) as response:
            assert response.status == 200, f"Authentication failed: {await response.text()}"
            data = await response.json()
            assert "access_token" in data, "No access token in response"
            return data["access_token"]


@pytest.mark.asyncio
async def test_server_health(docker_compose_up):
    """Test server health endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "ok"
            assert "version" in data


@pytest.mark.asyncio
async def test_authentication(docker_compose_up):
    """Test authentication flow"""
    async with aiohttp.ClientSession() as session:
        # Test successful authentication
        form_data = {
            "username": AUTH_USERNAME,
            "password": AUTH_PASSWORD
        }
        
        async with session.post(f"{SERVER_URL}/token", data=form_data) as response:
            assert response.status == 200
            data = await response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
        
        # Test failed authentication
        form_data = {
            "username": "wrong_user",
            "password": "wrong_password"
        }
        
        async with session.post(f"{SERVER_URL}/token", data=form_data) as response:
            assert response.status == 401


@pytest.mark.asyncio
async def test_employee_crud_operations(docker_compose_up, auth_token):
    """Test employee CRUD operations"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create employee
        employee_data = TEST_EMPLOYEES[0].copy()
        
        async with session.post(
            f"{SERVER_URL}/api/employees/",
            json=employee_data,
            headers=headers
        ) as response:
            assert response.status == 201
            data = await response.json()
            assert data["employee_id"] == employee_data["employee_id"]
            assert data["name"] == employee_data["name"]
            assert data["email"] == employee_data["email"]
        
        # Get employee
        async with session.get(
            f"{SERVER_URL}/api/employees/{employee_data['employee_id']}",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data["employee_id"] == employee_data["employee_id"]
            assert data["name"] == employee_data["name"]
        
        # Update employee
        update_data = {
            "name": "Updated Name",
            "salary": 80000
        }
        
        async with session.put(
            f"{SERVER_URL}/api/employees/{employee_data['employee_id']}",
            json=update_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data["employee_id"] == employee_data["employee_id"]
            assert data["name"] == update_data["name"]
            assert data["salary"] == update_data["salary"]
        
        # Delete employee
        async with session.delete(
            f"{SERVER_URL}/api/employees/{employee_data['employee_id']}",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "success"
        
        # Verify deletion
        async with session.get(
            f"{SERVER_URL}/api/employees/{employee_data['employee_id']}",
            headers=headers
        ) as response:
            assert response.status == 404


@pytest.mark.asyncio
async def test_bulk_operations(docker_compose_up, auth_token):
    """Test bulk operations"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Bulk create employees
        bulk_data = {
            "employees": TEST_EMPLOYEES[1:]  # Use the last two test employees
        }
        
        async with session.post(
            f"{SERVER_URL}/api/employees/bulk",
            json=bulk_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data["total_records"] == 2
            assert data["successful"] >= 1
        
        # Get all employees
        async with session.get(
            f"{SERVER_URL}/api/employees/",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, list)
            
            # Find our test employees
            test_ids = {emp["employee_id"] for emp in TEST_EMPLOYEES[1:]}
            found_employees = [emp for emp in data if emp["employee_id"] in test_ids]
            
            assert len(found_employees) > 0


@pytest.mark.asyncio
async def test_department_statistics(docker_compose_up, auth_token):
    """Test department statistics"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get department statistics
        async with session.get(
            f"{SERVER_URL}/api/employees/stats/department",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, list)
            
            # Check that departments from our test data are present
            departments = {dep["department"] for dep in data}
            test_departments = {emp["department"] for emp in TEST_EMPLOYEES[1:]}
            
            # At least some of our test departments should be present
            assert any(dep in departments for dep in test_departments)


@pytest.mark.asyncio
async def test_rate_limiting(docker_compose_up, auth_token):
    """Test rate limiting"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Make many requests in quick succession
        tasks = []
        for _ in range(60):  # More than the default rate limit
            task = session.get(
                f"{SERVER_URL}/api/employees/",
                headers=headers
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count responses
        success_count = 0
        rate_limited_count = 0
        
        for resp in responses:
            if isinstance(resp, Exception):
                continue
            
            if resp.status == 200:
                success_count += 1
            elif resp.status == 429:
                rate_limited_count += 1
        
        # Some requests should be rate limited
        assert rate_limited_count > 0, "No requests were rate limited"
