# server/schemas/schema.py
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional
from datetime import date, datetime


class EmployeeBase(BaseModel):
    """Base schema for employee data"""
    name: str = Field(..., description="Employee name", example="John Doe")
    email: EmailStr = Field(..., description="Employee email", example="john.doe@example.com")
    department: str = Field(..., description="Employee department", example="Engineering")
    designation: str = Field(..., description="Employee designation", example="Software Engineer")
    salary: int = Field(..., description="Employee salary", example=75000, gt=0)
    date_of_joining: date = Field(..., description="Employee date of joining", example="2023-01-15")


class EmployeeCreate(EmployeeBase):
    """Schema for creating an employee"""
    employee_id: int = Field(..., description="Employee ID", example=1001, gt=0)
    
    @validator('employee_id')
    def validate_employee_id(cls, v):
        if v <= 0:
            raise ValueError("Employee ID must be a positive integer")
        return v


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee"""
    name: Optional[str] = Field(None, description="Employee name", example="John Doe")
    email: Optional[EmailStr] = Field(None, description="Employee email", example="john.doe@example.com")
    department: Optional[str] = Field(None, description="Employee department", example="Engineering")
    designation: Optional[str] = Field(None, description="Employee designation", example="Senior Software Engineer")
    salary: Optional[int] = Field(None, description="Employee salary", example=85000, gt=0)
    date_of_joining: Optional[date] = Field(None, description="Employee date of joining", example="2023-01-15")
    
    @validator('salary')
    def validate_salary(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Salary must be a positive integer")
        return v


class EmployeeResponse(EmployeeBase):
    """Schema for employee response"""
    employee_id: int = Field(..., description="Employee ID", example=1001)
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        orm_mode = True


class EmployeeBulkCreate(BaseModel):
    """Schema for bulk employee creation"""
    employees: List[EmployeeCreate] = Field(..., description="List of employees to create", min_items=1)


class ResponseMessage(BaseModel):
    """Schema for response messages"""
    message: str = Field(..., description="Response message")


class BatchUploadResponse(BaseModel):
    """Schema for batch upload responses"""
    total_records: int = Field(..., description="Total number of records")
    successful: int = Field(..., description="Number of successfully processed records")
    failed: int = Field(..., description="Number of failed records")
    failed_records: List[dict] = Field(..., description="List of failed records with error details")
    message: str = Field(..., description="Response message")


class EmployeeCount(BaseModel):
    """Schema for employee count by group"""
    department: str = Field(..., description="Department name")
    count: int = Field(..., description="Number of employees")
    
    class Config:
        orm_mode = True


class ProcessingLogCreate(BaseModel):
    """Schema for creating a processing log"""
    employee_id: Optional[int] = Field(None, description="Employee ID")
    status: str = Field(..., description="Processing status", example="SUCCESS")
    message: Optional[str] = Field(None, description="Processing message")


class ProcessingLogResponse(ProcessingLogCreate):
    """Schema for processing log response"""
    id: int = Field(..., description="Log ID")
    processed_at: datetime = Field(..., description="Processing timestamp")
    
    class Config:
        orm_mode = True