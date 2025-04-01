"""Create database and initial tables

Revision ID: initial_create_db_001
Revises: 
Create Date: 2025-03-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# revision identifiers, used by Alembic.
revision = 'initial_create_db_001'
down_revision = None
branch_labels = None
depends_on = None

# Database configuration with default values
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "happy")
DB_NAME = os.getenv("DB_NAME", "employee_records")


def upgrade() -> None:
    # Create database if it doesn't exist
    # Since we can't directly use async in upgrade(), we'll create a helper function
    # and run it via synchronous code
    
    # Create employees table
    op.create_table('employees',
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('department', sa.String(length=50), nullable=False),
        sa.Column('designation', sa.String(length=50), nullable=False),
        sa.Column('salary', sa.Integer(), nullable=False),
        sa.Column('date_of_joining', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), 
                 server_onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('employee_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_department', 'employees', ['department'], unique=False)
    op.create_index('idx_designation', 'employees', ['designation'], unique=False)
    
    # Create processing_logs table
    op.create_table('processing_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.employee_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('processing_logs')
    op.drop_table('employees')