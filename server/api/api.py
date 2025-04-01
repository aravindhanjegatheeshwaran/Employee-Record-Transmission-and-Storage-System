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

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/employees",
    tags=["employees"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
@log_execution_time
@log_requests
@rate_limit(calls=1000, period=60)
async def create_employee(
    employee: EmployeeCreate,
    db: AsyncSession = Depends(get_db)
):
    logger.debug(f"Received employee data: {employee.dict()}")
    logger.debug(f"DB session type: {type(db)}")
    
    employee_id = employee.employee_id
    
    try:
        exists = await employee_repository.exists(db, employee_id)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee ID {employee_id} already exists"
            )
        
        employee_data = employee.dict()
        new_employee = await employee_repository.create(db, employee_data)
        
        return new_employee
    except Exception as e:
        logger.error(f"Error in create_employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee: {str(e)}"
        )

@router.post("/bulk", response_model=BatchUploadResponse)
@log_requests
@log_execution_time
@rate_limit(calls=100, period=60)
async def create_employees_bulk(
    request: Request,
    employees: EmployeeBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        if not employees.employees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No employee records provided"
            )
        
        successful_count = 0
        failed_records = []
        valid_employee_data = []
        
        for employee in employees.employees:
            try:
                exists = await employee_repository.exists(db, employee.employee_id)
                
                if exists:
                    failed_records.append({
                        "employee_id": employee.employee_id,
                        "error": f"ID {employee.employee_id} already exists"
                    })
                    continue
                
                valid_employee_data.append(employee.dict())
                
            except Exception as e:
                logger.error(f"Error processing employee in bulk upload: {str(e)}")
                failed_records.append({
                    "employee_id": getattr(employee, "employee_id", "unknown"),
                    "error": str(e)
                })
        
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
        logger.error(f"Bulk upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk upload failed: {str(e)}"
        )

@router.get("/", response_model=List[EmployeeResponse])
@log_requests
@log_execution_time
@rate_limit(calls=1000, period=60)
async def get_employees(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        filters = {}
        if department:
            filters["department"] = department
        
        employees = await employee_repository.get_all(db, skip, limit, filters)
        return [EmployeeResponse.from_orm(employee) for employee in employees]
    except Exception as e:
        logger.error(f"Employee retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve employees"
        )

@router.get("/{employee_id}", response_model=EmployeeResponse)
@log_requests
@log_execution_time
@rate_limit(calls=2000, period=60)
async def get_employee(
    request: Request,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    try:
        employee = await employee_repository.get(db, employee_id)
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee ID {employee_id} not found"
            )
        
        return EmployeeResponse.from_orm(employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Employee lookup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve employee"
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
    exists = await employee_repository.exists(db, employee_id)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee ID {employee_id} not found"
        )
    
    try:
        employee_data = employee.dict(exclude_unset=True)
        
        if not employee_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        updated_employee = await employee_repository.update(db, employee_id, employee_data)
        
        if not updated_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee ID {employee_id} not found after update"
            )
        
        return EmployeeResponse.from_orm(updated_employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Employee update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update employee"
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
    exists = await employee_repository.exists(db, employee_id)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee ID {employee_id} not found"
        )
    
    try:
        deleted = await employee_repository.delete(db, employee_id)
        
        if deleted:
            return ResponseMessage(
                message=f"Employee ID {employee_id} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete employee"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Employee deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete employee"
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
    try:
        department_counts = await get_employee_count_by_department(db)
        return [EmployeeCount(**count) for count in department_counts]
    except Exception as e:
        logger.error(f"Department stats failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve department statistics"
        )