# client/utils.py
import csv
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime, date
import functools
import traceback
import os
import sys
from dataclasses import asdict

logger = logging.getLogger(__name__)

def log_execution_time(func):
    """Decorator to log function execution time"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"Function {func.__name__} failed after {end_time - start_time:.4f} seconds. Error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"Function {func.__name__} executed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"Function {func.__name__} failed after {end_time - start_time:.4f} seconds. Error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def retry(max_retries: int = 3, retry_delay: float = 1.0, 
          backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorator to retry functions on failure"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            retries = 0
            current_delay = retry_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {str(e)}")
                    logger.warning(f"Waiting {current_delay:.2f} seconds before retry...")
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            retries = 0
            current_delay = retry_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {str(e)}")
                    logger.warning(f"Waiting {current_delay:.2f} seconds before retry...")
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


async def process_in_batches(items: List[Any], batch_size: int, 
                             process_func: Callable[[List[Any]], Any]) -> List[Any]:
    """
    Process items in batches
    
    Args:
        items: List of items to process
        batch_size: Size of each batch
        process_func: Function to process each batch
        
    Returns:
        List of results from each batch
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(items) + batch_size - 1)//batch_size} "
                    f"with {len(batch)} items")
        
        batch_result = await process_func(batch)
        results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
    
    return results


def parse_csv_file(file_path: str, delimiter: str = ',', encoding: str = 'utf-8', 
                   convert_date: bool = True) -> List[Dict[str, Any]]:
    """
    Parse CSV file to list of dictionaries
    
    Args:
        file_path: Path to CSV file
        delimiter: CSV delimiter
        encoding: File encoding
        convert_date: Whether to convert date strings to datetime objects
        
    Returns:
        List of dictionaries, one for each row in the CSV
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            rows = []
            
            for i, row in enumerate(reader, 1):
                # Convert empty strings to None
                processed_row = {k: (v if v else None) for k, v in row.items()}
                
                # Convert string values to appropriate types
                for key, value in processed_row.items():
                    if value is None:
                        continue
                    
                    # Convert numeric fields
                    if key in ['Employee ID', 'Salary']:
                        try:
                            processed_row[key] = int(value)
                        except ValueError:
                            logger.warning(f"Failed to convert {key}='{value}' to int in row {i}")
                    
                    # Convert date fields
                    if convert_date and key == 'Date of Joining':
                        try:
                            # Try different date formats
                            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                                try:
                                    processed_row[key] = datetime.strptime(value, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            else:
                                logger.warning(f"Failed to parse date '{value}' in row {i}")
                        except Exception as e:
                            logger.warning(f"Error parsing date: {str(e)}")
                
                # Map CSV column names to camelCase for API
                mapped_row = {
                    'employee_id': processed_row.get('Employee ID'),
                    'name': processed_row.get('Name'),
                    'email': processed_row.get('Email'),
                    'department': processed_row.get('Department'),
                    'designation': processed_row.get('Designation'),
                    'salary': processed_row.get('Salary'),
                    'date_of_joining': processed_row.get('Date of Joining'),
                }
                
                rows.append(mapped_row)
            
            logger.info(f"Successfully parsed {len(rows)} rows from {file_path}")
            return rows
    except Exception as e:
        logger.error(f"Error parsing CSV file {file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def save_failed_records(records: List[Dict[str, Any]], output_path: str):
    """
    Save failed records to a CSV file
    
    Args:
        records: List of failed records
        output_path: Path to save the CSV file
    """
    if not records:
        logger.info("No failed records to save")
        return
    
    try:
        # Determine all possible fields
        fieldnames = set()
        for record in records:
            for key in record.keys():
                fieldnames.add(key)
        
        fieldnames = sorted(list(fieldnames))
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                # Convert any non-serializable types
                serializable_record = {}
                for key, value in record.items():
                    if isinstance(value, (datetime, date)):
                        serializable_record[key] = value.isoformat()
                    else:
                        serializable_record[key] = value
                
                writer.writerow(serializable_record)
        
        logger.info(f"Saved {len(records)} failed records to {output_path}")
    except Exception as e:
        logger.error(f"Error saving failed records to {output_path}: {str(e)}")
        logger.error(traceback.format_exc())


def format_employee_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format employee record for API request
    
    Args:
        record: Raw employee record
        
    Returns:
        Formatted employee record
    """
    formatted = {}
    
    # Copy all fields
    for key, value in record.items():
        if value is not None:  # Skip None values
            # Convert date objects to string format
            if isinstance(value, date):
                formatted[key] = value.isoformat()
            else:
                formatted[key] = value
    
    return formatted

async def gather_with_concurrency(n: int, *tasks):
    """Run tasks with a concurrency limit"""
    semaphore = asyncio.Semaphore(n)
    
    async def sem_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*(sem_task(task) for task in tasks))
