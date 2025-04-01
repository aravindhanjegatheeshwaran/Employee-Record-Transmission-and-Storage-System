# server/api/api.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from core.database import get_db, employee_repository, get_employee_count_by_department
from schemas.schema import (
    EmployeeCreate, 
    EmployeeResponse, 
    EmployeeUpdate, 
    EmployeeBulkCreate,
    ResponseMessage,
    EmployeeCount,
    BatchUploadResponse
)
from core.decorators import log_execution_time, log_requests, validate_input, rate_limit
from core.security import get_current_active_user

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/employees",
    tags=["employees"],
    responses={404: {"description": "Not found"}},
)


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
@log_execution_time
@log_requests
@rate_limit(calls=100, period=60)
@validate_input(EmployeeCreate)  # This adds the validated_data parameter
async def create_employee(
    employee: EmployeeCreate,
    validated_data: EmployeeCreate,  # Add this parameter
    session: AsyncSession = Depends(get_db)
):
    """Create a new employee"""
    # Use validated_data instead of employee
    employee_id = validated_data.employee_id
    
    # Check if employee ID already exists
    exists = await employee_repository.exists(session, employee_id)
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with ID {employee_id} already exists"
        )
    
    # Create employee
    employee_data = validated_data.dict()
    new_employee = await employee_repository.create(session, employee_data)
    
    return new_employee

@router.post("/bulk", response_model=BatchUploadResponse)
@log_requests
@log_execution_time
@rate_limit(calls=10, period=60)
async def create_employees_bulk(
    request: Request,
    employees: EmployeeBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Create multiple employee records in bulk using ORM"""
    if not employees.employees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No employee records provided"
        )
    
    successful_count = 0
    failed_records = []
    
    # Process each employee
    valid_employee_data = []
    
    for employee in employees.employees:
        try:
            # Check if employee already exists
            exists = await employee_repository.exists(db, employee.employee_id)
            
            if exists:
                failed_records.append({
                    "employee_id": employee.employee_id,
                    "error": f"Employee with ID {employee.employee_id} already exists"
                })
                continue
            
            # Validate the employee data
            employee_data = employee.dict()
            valid_employee_data.append(employee_data)
            
        except Exception as e:
            failed_records.append({
                "employee_id": getattr(employee, "employee_id", "unknown"),
                "error": str(e)
            })
    
    try:
        # Bulk create valid employees
        if valid_employee_data:
            created_employees = await employee_repository.create_many(db, valid_employee_data)
            successful_count = len(created_employees)
        
        return BatchUploadResponse(
            total_records=len(employees.employees),
            successful=successful_count,
            failed=len(failed_records),
            failed_records=failed_records,
            message="Bulk upload completed"
        )
    except Exception as e:
        logger.error(f"Failed to process bulk upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process bulk upload: {str(e)}"
        )


@router.get("/", response_model=List[EmployeeResponse])
@log_requests
@log_execution_time
@rate_limit(calls=100, period=60)
async def get_employees(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of employees with pagination and optional department filter using ORM"""
    try:
        # Set up filters
        filters = {}
        if department:
            filters["department"] = department
        
        # Get employees
        employees = await employee_repository.get_all(db, skip, limit, filters)
        
        return [EmployeeResponse.from_orm(employee) for employee in employees]
    except Exception as e:
        logger.error(f"Failed to retrieve employees: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve employees: {str(e)}"
        )


@router.get("/{employee_id}", response_model=EmployeeResponse)
@log_requests
@log_execution_time
@rate_limit(calls=200, period=60)
async def get_employee(
    request: Request,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Get employee by ID using ORM"""
    try:
        employee = await employee_repository.get(db, employee_id)
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )
        
        return EmployeeResponse.from_orm(employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve employee: {str(e)}"
        )


@router.put("/{employee_id}", response_model=EmployeeResponse)
@log_requests
@log_execution_time
@validate_input(EmployeeUpdate)
@rate_limit(calls=100, period=60)
async def update_employee(
    request: Request,
    employee_id: int,
    employee: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Update employee by ID using ORM"""
    # Check if employee exists
    exists = await employee_repository.exists(db, employee_id)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
    
    try:
        # Update employee
        employee_data = employee.dict(exclude_unset=True)
        
        # If no fields to update
        if not employee_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        updated_employee = await employee_repository.update(db, employee_id, employee_data)
        
        if not updated_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found after update"
            )
        
        return EmployeeResponse.from_orm(updated_employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update employee: {str(e)}"
        )


@router.delete("/{employee_id}", response_model=ResponseMessage)
@log_requests
@log_execution_time
@rate_limit(calls=50, period=60)
async def delete_employee(
    request: Request,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete employee by ID using ORM"""
    # Check if employee exists
    exists = await employee_repository.exists(db, employee_id)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
    
    try:
        # Delete employee
        deleted = await employee_repository.delete(db, employee_id)
        
        if deleted:
            return ResponseMessage(
                message=f"Employee with ID {employee_id} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete employee with ID {employee_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete employee: {str(e)}"
        )


@router.get("/stats/department", response_model=List[EmployeeCount])
@log_requests
@log_execution_time
@rate_limit(calls=50, period=60)
async def get_employee_count_by_department_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Get employee count by department using ORM"""
    try:
        department_counts = await get_employee_count_by_department(db)
        return [EmployeeCount(**count) for count in department_counts]
    except Exception as e:
        logger.error(f"Failed to retrieve department statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve department statistics: {str(e)}"
        )