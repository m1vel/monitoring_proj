from sqlalchemy import Column, Integer, String, Date, Numeric, Text, TIMESTAMP, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    position = Column(String(100), nullable=False)
    department = Column(String(100))
    email = Column(String(100), unique=True, nullable=False)
    hire_date = Column(Date, nullable=False)
    role = Column(String(20), nullable=False)
    manager_id = Column(Integer, ForeignKey('employees.id', ondelete='SET NULL'))
    manager = relationship('Employee', remote_side='Employee.id', backref='subordinates')
    tasks = relationship('Task', foreign_keys='Task.assignee_id', back_populates='assignee')
    reviews_given = relationship('TaskReview', back_populates='reviewer')
    kpi_records = relationship('KpiRecord', back_populates='employee', cascade='all, delete-orphan')
    lead_projects = relationship('Project', back_populates='manager')

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    status = Column(String(20), nullable=False, default='active')
    manager_id = Column(Integer, ForeignKey('employees.id', ondelete='RESTRICT'), nullable=False)
    manager = relationship('Employee', back_populates='lead_projects')
    tasks = relationship('Task', back_populates='project')
    members = relationship('ProjectMember', back_populates='project')

class ProjectMember(Base):
    __tablename__ = 'project_members'
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete='CASCADE'), primary_key=True)
    project = relationship('Project', back_populates='members')
    employee = relationship('Employee')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='RESTRICT'), nullable=False)
    assignee_id = Column(Integer, ForeignKey('employees.id', ondelete='RESTRICT'), nullable=False)
    priority = Column(String(10), nullable=False, default='medium')
    status = Column(String(20), nullable=False, default='new')
    deadline = Column(Date)
    estimated_hours = Column(Numeric(5,1))
    actual_hours = Column(Numeric(5,1))
    created_at = Column(TIMESTAMP, default='now()')
    updated_at = Column(TIMESTAMP, default='now()')
    assignee = relationship('Employee', foreign_keys=[assignee_id], back_populates='tasks')
    project = relationship('Project', back_populates='tasks')
    review = relationship('TaskReview', back_populates='task', uselist=False)  # один-к-одному

class TaskReview(Base):
    __tablename__ = 'task_reviews'
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), unique=True, nullable=False)
    reviewer_id = Column(Integer, ForeignKey('employees.id', ondelete='RESTRICT'), nullable=False)
    rating = Column(Integer, CheckConstraint('rating BETWEEN 1 AND 5'), nullable=False)
    comment = Column(Text)
    created_at = Column(TIMESTAMP, default='now()')
    task = relationship('Task', back_populates='review')
    reviewer = relationship('Employee', back_populates='reviews_given')

class KpiRecord(Base):
    __tablename__ = 'kpi_records'
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    period = Column(Date, nullable=False)
    tasks_completed = Column(Integer, nullable=False, default=0)
    avg_quality_rating = Column(Numeric(3,2))
    on_time_completion_rate = Column(Numeric(5,2))
    productivity_score = Column(Numeric(6,2))
    employee = relationship('Employee', back_populates='kpi_records')
    __table_args__ = (UniqueConstraint('employee_id', 'period'),)