# server/core/database.py
import os
import logging
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.sql import delete, update, text
from sqlalchemy import func, inspect

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import SQLAlchemy models
from models.model import Base, Employee, ProcessingLog

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic repository
T = TypeVar('T')

# Database configuration with default values
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "happy")
DB_NAME = os.getenv("DB_NAME", "employee_records")

# SQLAlchemy async connection string
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = create_async_engine(
    DATABASE_URL,
    echo=bool(os.getenv("SQL_ECHO", "False").lower() == "true"),
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
)

# Session factory
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


# Create a context manager for database sessions
@asynccontextmanager
async def get_db():
    """Async context manager for database sessions"""
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        await session.close()


# Generic repository class for database operations
class Repository(Generic[T]):
    """Generic repository for database operations"""
    
    def __init__(self, model_class):
        """Initialize repository with model class"""
        self.model_class = model_class
    
    async def create(self, session: AsyncSession, obj_data: Dict[str, Any]) -> T:
        """Create a new object in the database"""
        db_obj = self.model_class(**obj_data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def create_many(self, session: AsyncSession, obj_data_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple objects in the database"""
        db_objs = [self.model_class(**obj_data) for obj_data in obj_data_list]
        session.add_all(db_objs)
        await session.flush()
        for obj in db_objs:
            await session.refresh(obj)
        return db_objs
    
    async def get(self, session: AsyncSession, id_value: Any) -> Optional[T]:
        """Get object by ID"""
        result = await session.execute(
            select(self.model_class).filter_by(employee_id=id_value)
        )
        return result.scalars().first()
    
    async def get_all(
        self, 
        session: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get all objects with pagination and optional filters"""
        query = select(self.model_class)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    query = query.filter(getattr(self.model_class, key) == value)
        
        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def update(
        self, 
        session: AsyncSession, 
        id_value: Any, 
        obj_data: Dict[str, Any]
    ) -> Optional[T]:
        """Update object by ID"""
        # Remove None values from update data
        update_data = {k: v for k, v in obj_data.items() if v is not None}
        
        if not update_data:
            return None
        
        # Update the object
        await session.execute(
            update(self.model_class)
            .where(self.model_class.employee_id == id_value)
            .values(**update_data)
        )
        
        # Get the updated object
        return await self.get(session, id_value)
    
    async def delete(self, session: AsyncSession, id_value: Any) -> bool:
        """Delete object by ID"""
        result = await session.execute(
            delete(self.model_class)
            .where(self.model_class.employee_id == id_value)
        )
        return result.rowcount > 0
    
    async def count(
        self, 
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count objects with optional filters"""
        query = select(func.count(self.model_class.employee_id))
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    query = query.filter(getattr(self.model_class, key) == value)
        
        result = await session.execute(query)
        return result.scalar()
    
    async def exists(self, session: AsyncSession, id_value: Any) -> bool:
        """Check if object exists by ID"""
        result = await session.execute(
            select(func.count(self.model_class.employee_id))
            .where(self.model_class.employee_id == id_value)
        )
        return result.scalar() > 0


async def create_database():
    """Create the database if it doesn't exist"""
    # Create a temporary engine to connect to MySQL server without a specific database
    temp_engine = create_async_engine(
        f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}",
        echo=False
    )
    
    try:
        async with temp_engine.begin() as conn:
            # Check if database exists
            result = await conn.execute(text(f"SHOW DATABASES LIKE '{DB_NAME}'"))
            database_exists = result.scalar() is not None
            
            if not database_exists:
                # Create database
                await conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
                logger.info(f"Database '{DB_NAME}' created successfully")
            else:
                logger.info(f"Database '{DB_NAME}' already exists")
    finally:
        await temp_engine.dispose()


# Database initialization and cleanup
async def init_db(create_db: bool = True):
    """Initialize database and create tables"""
    try:
        if create_db:
            # Create database if it doesn't exist
            await create_database()
        
        # Create tables
        async with engine.begin() as conn:
            # Get existing tables
            existing_tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
            
            if 'employees' not in existing_tables or 'processing_logs' not in existing_tables:
                # Create all tables defined in the models
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully")
            else:
                logger.info("Database tables already exist")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    
    logger.info("Database initialized with all tables")


async def close_db():
    """Close database connection"""
    await engine.dispose()
    logger.info("Database connection closed")


# Create repositories for models
employee_repository = Repository(Employee)
processing_log_repository = Repository(ProcessingLog)


# Custom query for department statistics
async def get_employee_count_by_department(session: AsyncSession) -> List[Dict[str, Any]]:
    """Get employee count by department"""
    query = select(
        Employee.department,
        func.count(Employee.employee_id).label("count")
    ).group_by(Employee.department).order_by(text("count DESC"))
    
    result = await session.execute(query)
    return [{"department": dept, "count": count} for dept, count in result.all()]


# This function can be used directly by Alembic to get the database configuration
def get_database_url():
    """Get database URL for Alembic"""
    # For Alembic, convert aiomysql to pymysql
    return DATABASE_URL.replace('+aiomysql', '+pymysql')