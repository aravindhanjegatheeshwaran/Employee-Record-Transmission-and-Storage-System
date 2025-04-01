# server/core/decorators.py
import functools
import time
import logging
import json
from datetime import datetime
from fastapi import HTTPException, status, Request
import asyncio
import traceback

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
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"{func.__name__} took {elapsed:.4f}s")
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
            logger.info(f"{func.__name__} took {elapsed:.4f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.4f}s: {str(e)}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def log_requests(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = None
        for arg in args:
            if hasattr(arg, "method") and hasattr(arg, "url"):
                request = arg
                break
        
        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        if request:
            client_ip = request.client.host if hasattr(request, "client") else "unknown"
            request_data = "Not logged"
            try:
                if hasattr(request, "json"):
                    request_data = await request.json() if asyncio.iscoroutinefunction(request.json) else request.json()
                    request_data = json.dumps(request_data, default=str)
            except:
                pass
            
            logger.info(f"REQ {request_id}: {request.method} {request.url} from {client_ip}")
        else:
            logger.info(f"FUNC {request_id}: {func.__name__} called")
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            logger.info(f"DONE {request_id}: completed in {elapsed:.4f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            
            logger.error(f"FAIL {request_id}: error after {elapsed:.4f}s - {str(e)}")
            raise
    
    return wrapper

def validate_input(validator_class):
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            request_body = None
            
            for key, value in list(kwargs.items()):
                if not isinstance(value, Request) and value is not None:
                    request_body = value
                    break
            
            if request_body is None:
                for arg in args:
                    if not isinstance(arg, Request) and arg is not None:
                        request_body = arg
                        break
            
            if not request_body:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="No request body found"
                )
            
            try:
                if isinstance(request_body, dict):
                    validator_class(**request_body)
                else:
                    request_dict = request_body
                    if hasattr(request_body, "__dict__"):
                        request_dict = request_body.__dict__
                    validator_class(**request_dict)
                
            except Exception as e:
                logger.error(f"Validation error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validation failed: {str(e)}"
                )
            
            return await func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def rate_limit(calls=60, period=60):
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if hasattr(arg, "client") and hasattr(arg.client, "host"):
                    request = arg
                    break
            
            client_ip = "unknown"
            if request and hasattr(request, "client"):
                client_ip = request.client.host
            
            current_time = time.time()
            
            if client_ip not in cache:
                cache[client_ip] = []
            
            cache[client_ip] = [ts for ts in cache[client_ip] if current_time - ts < period]
            
            if len(cache[client_ip]) >= calls:
                logger.warning(f"Rate limit exceeded: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Try again in {period} seconds."
                )
            
            cache[client_ip].append(current_time)
            
            return await func(*args, **kwargs)
        
        return async_wrapper
    
    return decorator
