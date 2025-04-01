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

logger = logging.getLogger(__name__)

def log_execution_time(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"{func.__name__} completed in {elapsed:.4f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.4f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"{func.__name__} completed in {elapsed:.4f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.4f}s: {str(e)}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0, exceptions=(Exception,)):
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
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} after error: {str(e)}")
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
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} after error: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def parse_csv_file(file_path, delimiter=',', encoding='utf-8', convert_date=True):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            rows = []
            
            for i, row in enumerate(reader, 1):
                processed_row = {k: (v.strip() if v else None) for k, v in row.items()}
                
                for key, value in processed_row.items():
                    if value is None:
                        continue
                    
                    if key in ['Employee ID', 'Salary']:
                        try:
                            processed_row[key] = int(value)
                        except ValueError:
                            logger.warning(f"Invalid {key} value '{value}' in row {i}")
                    
                    if convert_date and key == 'Date of Joining':
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                            try:
                                processed_row[key] = datetime.strptime(value, fmt).date()
                                break
                            except ValueError:
                                continue
                        else:
                            logger.warning(f"Invalid date format '{value}' in row {i}")
                
                mapped_row = {
                    'employee_id': processed_row.get('Employee ID'),
                    'name': processed_row.get('Name'),
                    'email': processed_row.get('Email'),
                    'department': processed_row.get('Department'),
                    'designation': processed_row.get('Designation'),
                    'salary': processed_row.get('Salary'),
                    'date_of_joining': processed_row.get('Date of Joining'),
                }
                
                # Skip rows with missing required fields
                required_fields = ['employee_id', 'name', 'email', 'department', 'designation', 'salary', 'date_of_joining']
                missing_fields = [field for field in required_fields if field not in mapped_row or mapped_row[field] is None]
                
                if missing_fields:
                    logger.warning(f"Row {i} is missing required fields: {', '.join(missing_fields)}")
                    continue
                
                logger.debug(f"Parsed row {i}: {mapped_row}")
                rows.append(mapped_row)
            
            return rows
    except Exception as e:
        logger.error(f"CSV parsing error: {str(e)}")
        raise


def save_failed_records(records, output_path):
    if not records:
        logger.info("No failed records to save")
        return
    
    try:
        fieldnames = set()
        for record in records:
            fieldnames.update(record.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                serializable_record = {}
                for key, value in record.items():
                    if isinstance(value, (datetime, date)):
                        serializable_record[key] = value.isoformat()
                    else:
                        serializable_record[key] = value
                
                writer.writerow(serializable_record)
        
        logger.info(f"Saved {len(records)} failed records to {output_path}")
    except Exception as e:
        logger.error(f"Error saving failed records: {str(e)}")


def format_employee_record(record):
    formatted = {}
    
    for key, value in record.items():
        if value is not None:
            if isinstance(value, date):
                formatted[key] = value.isoformat()
            else:
                formatted[key] = value
    
    # Add debug logging for formatted record
    logger.debug(f"Formatted employee record: {formatted}")
    
    return formatted


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)
    
    async def limited_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*(limited_task(task) for task in tasks))
