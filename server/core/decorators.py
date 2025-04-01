# server/core/decorator.py
import functools
import time
import logging
import json
from typing import Callable, Any, Dict, List, Optional, Type, Union
from datetime import datetime
import inspect
from fastapi import HTTPException, status, Request
import asyncio
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
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
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

def log_requests(func):
    """Decorator to log API requests"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the request object from the arguments
        request = None
        for arg in args:
            if hasattr(arg, "method") and hasattr(arg, "url"):
                request = arg
                break
        
        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        # Log the request details
        if request:
            client_ip = request.client.host if hasattr(request, "client") else "unknown"
            request_data = "Not logged"
            try:
                if hasattr(request, "json"):
                    request_data = await request.json() if asyncio.iscoroutinefunction(request.json) else request.json()
                    request_data = json.dumps(request_data, default=str)
            except:
                pass
            
            logger.info(f"Request {request_id} started: {request.method} {request.url} from {client_ip} - Data: {request_data}")
        else:
            logger.info(f"Function {func.__name__} called with request ID {request_id}")
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            
            logger.info(f"Request {request_id} completed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            
            logger.error(f"Request {request_id} failed after {end_time - start_time:.4f} seconds with error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    return wrapper

def validate_input(validator_class):
    """Decorator to validate input using a specified validator class"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract request body from kwargs or args
            request_body = None
            
            # Check in kwargs first
            for key, value in list(kwargs.items()):
                if not isinstance(value, Request) and value is not None:
                    request_body = value
                    break
            
            # If not found in kwargs, check in args
            if request_body is None:
                for i, arg in enumerate(args):
                    if not isinstance(arg, Request) and arg is not None:
                        request_body = arg
                        break
            
            if not request_body:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="No request body found"
                )
            
            # Validate the request body
            try:
                if isinstance(request_body, dict):
                    validator_instance = validator_class(**request_body)
                else:
                    # If already an instance of a class, convert to dict first
                    request_dict = request_body
                    if hasattr(request_body, "__dict__"):
                        request_dict = request_body.__dict__
                    validator_instance = validator_class(**request_dict)
                
                # Here's the fix: we don't add the validated_data to kwargs
                # Just validate and continue
                
            except Exception as e:
                logger.error(f"Validation error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Input validation failed: {str(e)}"
                )
            
            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

def rate_limit(calls: int, period: int = 60):
    """
    Rate limiting decorator to prevent abuse
    
    Args:
        calls: Maximum number of calls allowed in the period
        period: Time period in seconds
    """
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get client IP from request
            request = None
            for arg in args:
                if hasattr(arg, "client") and hasattr(arg.client, "host"):
                    request = arg
                    break
            
            client_ip = "unknown"
            if request and hasattr(request, "client"):
                client_ip = request.client.host
            
            current_time = time.time()
            
            # Initialize or clean expired entries
            if client_ip not in cache:
                cache[client_ip] = []
            
            # Remove timestamps older than the period
            cache[client_ip] = [ts for ts in cache[client_ip] if current_time - ts < period]
            
            # Check if rate limit exceeded
            if len(cache[client_ip]) >= calls:
                logger.warning(f"Rate limit exceeded for IP {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please try again in {period} seconds."
                )
            
            # Add current timestamp to the cache
            cache[client_ip].append(current_time)
            
            return await func(*args, **kwargs)
        
        return async_wrapper
    
    return decorator
