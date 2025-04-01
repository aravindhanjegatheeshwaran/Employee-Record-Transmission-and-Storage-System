import asyncio
import csv
import time
import random
import statistics
import os
import json
import sys
from datetime import datetime, timedelta
import aiohttp
from typing import List, Dict, Any, Tuple

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "adminpassword")
TEST_RUNS = int(os.getenv("TEST_RUNS", "3"))
CONCURRENT_USERS = int(os.getenv("CONCURRENT_USERS", "10"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
NUM_RECORDS = int(os.getenv("NUM_RECORDS", "1000"))
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "performance_results.json")

# Departments and designations for test data
DEPARTMENTS = ["Engineering", "Marketing", "Finance", "HR", "Operations", "Sales", "Legal", "IT"]
DESIGNATIONS = [
    "Software Engineer", "Marketing Specialist", "Financial Analyst", "HR Manager",
    "Operations Director", "Sales Representative", "Legal Counsel", "IT Support",
    "Product Manager", "Data Scientist", "UX Designer", "Content Writer",
    "Business Analyst", "DevOps Engineer", "QA Engineer", "Frontend Developer"
]


async def generate_test_data(num_records: int, output_path: str) -> None:
    """Generate test employee data"""
    print(f"Generating {num_records} test records...")
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Employee ID", "Name", "Email", "Department", "Designation", "Salary", "Date of Joining"])
        
        for i in range(1, num_records + 1):
            employee_id = 10000 + i
            name = f"Test User {i}"
            email = f"test{i}@example.com"
            department = random.choice(DEPARTMENTS)
            designation = random.choice(DESIGNATIONS)
            salary = random.randint(50000, 150000)
            
            # Generate random date in the last 5 years
            days_ago = random.randint(0, 365 * 5)
            date_of_joining = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            writer.writerow([employee_id, name, email, department, designation, salary, date_of_joining])
    
    print(f"Test data generated at {output_path}")


async def get_auth_token() -> str:
    """Get authentication token"""
    async with aiohttp.ClientSession() as session:
        form_data = {
            "username": AUTH_USERNAME,
            "password": AUTH_PASSWORD
        }
        
        async with session.post(f"{SERVER_URL}/token", data=form_data) as response:
            if response.status != 200:
                raise Exception(f"Authentication failed: {await response.text()}")
            
            data = await response.json()
            return data["access_token"]


async def load_csv_data(file_path: str) -> List[Dict[str, Any]]:
    """Load data from CSV file"""
    records = []
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert to the format expected by the API
            record = {
                "employee_id": int(row["Employee ID"]),
                "name": row["Name"],
                "email": row["Email"],
                "department": row["Department"],
                "designation": row["Designation"],
                "salary": int(row["Salary"]),
                "date_of_joining": row["Date of Joining"]
            }
            records.append(record)
    
    return records


async def send_employee_batch(
    session: aiohttp.ClientSession,
    batch: List[Dict[str, Any]],
    headers: Dict[str, str]
) -> Tuple[int, int, float]:
    """Send a batch of employee records"""
    start_time = time.time()
    
    try:
        async with session.post(
            f"{SERVER_URL}/api/employees/bulk",
            json={"employees": batch},
            headers=headers,
            timeout=60
        ) as response:
            data = await response.json()
            end_time = time.time()
            
            if response.status != 200:
                print(f"Error sending batch: {data}")
                return 0, len(batch), end_time - start_time
            
            return data.get("successful", 0), data.get("failed", 0), end_time - start_time
    except Exception as e:
        end_time = time.time()
        print(f"Exception sending batch: {str(e)}")
        return 0, len(batch), end_time - start_time


async def send_employees_individually(
    session: aiohttp.ClientSession,
    batch: List[Dict[str, Any]],
    headers: Dict[str, str],
    semaphore: asyncio.Semaphore
) -> Tuple[int, int, float]:
    """Send employee records individually with concurrency control"""
    start_time = time.time()
    
    async def send_one(employee: Dict[str, Any]) -> bool:
        try:
            async with semaphore:
                async with session.post(
                    f"{SERVER_URL}/api/employees/",
                    json=employee,
                    headers=headers,
                    timeout=30
                ) as response:
                    return response.status == 201
        except Exception:
            return False
    
    # Send all employees concurrently with semaphore
    tasks = [send_one(employee) for employee in batch]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    successful = sum(1 for r in results if r)
    failed = len(batch) - successful
    
    return successful, failed, end_time - start_time


async def run_performance_test(
    records: List[Dict[str, Any]],
    batch_size: int,
    concurrent_users: int,
    use_bulk: bool
) -> Dict[str, Any]:
    """Run a performance test"""
    print(f"Running performance test with {'bulk API' if use_bulk else 'individual API'}")
    print(f"Records: {len(records)}, Batch size: {batch_size}, Concurrent users: {concurrent_users}")
    
    # Get authentication token
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Prepare batches
    batches = [records[i:i+batch_size] for i in range(0, len(records), batch_size)]
    print(f"Divided into {len(batches)} batches")
    
    # Run the test
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        successful = 0
        failed = 0
        batch_times = []
        
        # Use semaphore to control concurrency
        semaphore = asyncio.Semaphore(concurrent_users)
        
        # Process batches based on the selected method
        if use_bulk:
            # Use bulk API
            for batch in batches:
                s, f, batch_time = await send_employee_batch(session, batch, headers)
                successful += s
                failed += f
                batch_times.append(batch_time)
                print(f"Batch completed: {s} successful, {f} failed, {batch_time:.2f} seconds")
        else:
            # Use individual API with concurrency
            for batch in batches:
                s, f, batch_time = await send_employees_individually(
                    session, batch, headers, semaphore
                )
                successful += s
                failed += f
                batch_times.append(batch_time)
                print(f"Batch completed: {s} successful, {f} failed, {batch_time:.2f} seconds")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate statistics
    results = {
        "method": "bulk" if use_bulk else "individual",
        "batch_size": batch_size,
        "concurrent_users": concurrent_users,
        "total_records": len(records),
        "successful_records": successful,
        "failed_records": failed,
        "total_time_seconds": total_time,
        "records_per_second": len(records) / total_time if total_time > 0 else 0,
        "batch_time_min": min(batch_times) if batch_times else 0,
        "batch_time_max": max(batch_times) if batch_times else 0,
        "batch_time_avg": statistics.mean(batch_times) if batch_times else 0,
        "batch_time_median": statistics.median(batch_times) if batch_times else 0,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Test completed in {total_time:.2f} seconds")
    print(f"Records per second: {results['records_per_second']:.2f}")
    print(f"Success rate: {successful/len(records)*100:.2f}%")
    
    return results


async def main():
    """Main function"""
    # Generate test data
    csv_path = "performance_test_data.csv"
    await generate_test_data(NUM_RECORDS, csv_path)
    
    # Load data
    records = await load_csv_data(csv_path)
    
    # Run tests
    all_results = []
    
    # Test with bulk API
    for _ in range(TEST_RUNS):
        results = await run_performance_test(
            records=records,
            batch_size=BATCH_SIZE,
            concurrent_users=CONCURRENT_USERS,
            use_bulk=True
        )
        all_results.append(results)
    
    # Test with individual API
    for _ in range(TEST_RUNS):
        results = await run_performance_test(
            records=records,
            batch_size=BATCH_SIZE,
            concurrent_users=CONCURRENT_USERS,
            use_bulk=False
        )
        all_results.append(results)
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
