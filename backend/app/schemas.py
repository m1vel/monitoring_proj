from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime

#employee
class EmployeeBase(BaseModel):
    login: str
    full_name: str
    position: str
    department: Optional[str] = None
    email: EmailStr
    hire_date: date
    role: str
    manager_id: Optional[int] = None

class EmployeeCreate(EmployeeBase):
    password: str

class EmployeeUpdate(BaseModel):
    login: Optional[str] = None
    full_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    email: Optional[EmailStr] = None
    hire_date: Optional[date] = None
    role: Optional[str] = None
    manager_id: Optional[int] = None
    password: Optional[str] = None

class EmployeeOut(EmployeeBase):
    id: int
    class Config:
        from_attributes = True

#project
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    status: str = 'active'
    manager_id: int

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    manager_id: Optional[int] = None

class ProjectOut(ProjectBase):
    id: int
    class Config:
        from_attributes = True

#tasks
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: int
    assignee_id: int
    priority: str = 'medium'
    status: str = 'new'
    deadline: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

class TaskOut(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

#review
class ReviewBase(BaseModel):
    task_id: int
    reviewer_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewOut(ReviewBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True
#auth
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int
    role: str