# server/models/model.py
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    department = Column(String(50), nullable=False, index=True)
    designation = Column(String(50), nullable=False, index=True)
    salary = Column(Integer, nullable=False)
    date_of_joining = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Employee(id={self.employee_id}, name='{self.name}')>"


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False)
    message = Column(Text, nullable=True)
    processed_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ProcessingLog(id={self.id}, status='{self.status}')>"