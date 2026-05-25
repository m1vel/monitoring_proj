from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models, auth, database, dependencies

router = APIRouter(prefix="/api/employees", tags=["employees"])

@router.get("/", response_model=List[schemas.EmployeeOut])
def get_all_employees(
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    if current_user.role == 'admin':
        employees = db.query(models.Employee).all()
    elif current_user.role == 'manager':
        employees = db.query(models.Employee).filter(
            (models.Employee.manager_id == current_user.id) | (models.Employee.id == current_user.id)
        ).all()
    else:
        employees = [current_user]
    return employees

@router.get("/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    return dependencies.get_managed_employee(employee_id, db, current_user)

@router.post("/", response_model=schemas.EmployeeOut)
def create_employee(
    employee: schemas.EmployeeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.require_role('admin'))
):
    if db.query(models.Employee).filter(models.Employee.login == employee.login).first():
        raise HTTPException(status_code=400, detail="Login already exists")
    hashed_pwd = auth.get_password_hash(employee.password)
    emp_data = employee.model_dump(exclude={'password'})
    emp = models.Employee(**emp_data, password_hash=hashed_pwd)
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: int,
    updates: schemas.EmployeeUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.require_role('admin'))
):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404)
    updates_dict = updates.model_dump(exclude_unset=True, exclude={'password'})
    for field, value in updates_dict.items():
        setattr(emp, field, value)
    if updates.password is not None:
        emp.password_hash = auth.get_password_hash(updates.password)
    db.commit()
    db.refresh(emp)
    return emp

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.require_role('admin'))
):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404)
    db.delete(emp)
    db.commit()
    return {"ok": True}