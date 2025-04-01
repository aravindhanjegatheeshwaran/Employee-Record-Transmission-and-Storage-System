# server/main.py
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from contextlib import asynccontextmanager

from core.database import close_db
from api import api, auth
from api.api import router as employees_orm_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting server...")
    yield
    
    logger.info("Shutting down, closing connections...")
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


app = FastAPI(
    title="Employee Record System API",
    description="API for managing employee records",
    version="1.1.0",
    lifespan=lifespan
)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(auth.router)
app.include_router(api.router)
app.include_router(employees_orm_router)


@app.get("/", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "message": "Server is running",
        "version": "1.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=bool(os.getenv("DEBUG", "True").lower() == "true")
    )