# server/schemas/schema.py
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional
from datetime import date, datetime


class EmployeeBase(BaseModel):
    name: str = Field(..., example="John Doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    department: str = Field(..., example="Engineering")
    designation: str = Field(..., example="Software Engineer")
    salary: int = Field(..., example=75000, gt=0)
    date_of_joining: date = Field(..., example="2023-01-15")


class EmployeeCreate(EmployeeBase):
    employee_id: int = Field(..., example=1001, gt=0)
    
    @validator('employee_id')
    def validate_employee_id(cls, v):
        if v <= 0:
            raise ValueError("Employee ID must be positive")
        return v


class EmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, example="John Doe")
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com")
    department: Optional[str] = Field(None, example="Engineering")
    designation: Optional[str] = Field(None, example="Senior Software Engineer")
    salary: Optional[int] = Field(None, example=85000, gt=0)
    date_of_joining: Optional[date] = Field(None, example="2023-01-15")
    
    @validator('salary')
    def validate_salary(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Salary must be positive")
        return v


class EmployeeResponse(EmployeeBase):
    employee_id: int = Field(...)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EmployeeBulkCreate(BaseModel):
    employees: List[EmployeeCreate] = Field(..., min_items=1)


class ResponseMessage(BaseModel):
    message: str


class BatchUploadResponse(BaseModel):
    total_records: int
    successful: int
    failed: int
    failed_records: List[dict]
    message: str


class EmployeeCount(BaseModel):
    department: str
    count: int
    
    class Config:
        from_attributes = True


class ProcessingLogCreate(BaseModel):
    employee_id: Optional[int] = None
    status: str = Field(..., example="SUCCESS")
    message: Optional[str] = None


class ProcessingLogResponse(ProcessingLogCreate):
    id: int
    processed_at: datetime
    
    class Config:
        from_attributes = True