# server/main.py
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
from contextlib import asynccontextmanager

# Import the database connection, but not initialization functions
from core.database import close_db
from api import api, auth
from api.api import router as employees_orm_router

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to database
    logger.info("Connecting to database...")
    # No database initialization needed - the database should exist and be migrated
    
    yield
    
    # Shutdown: close database connections
    logger.info("Closing database connections...")
    try:
        # Close the SQLAlchemy ORM database connection
        await close_db()
        logger.info("Database connection closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="Employee Record System API",
    description="API for managing employee records with SQLAlchemy ORM",
    version="1.1.0",
    lifespan=lifespan
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(employees_orm_router)  # Add the ORM routes


@app.get("/", tags=["health"])
async def health_check():
    """
    Health check endpoint
    """
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