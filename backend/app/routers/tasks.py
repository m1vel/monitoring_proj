from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, models, database, dependencies

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Проверка доступа к задаче
def get_accessible_task(task_id: int, db: Session, user: models.Employee) -> models.Task:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user.role == 'admin':
        return task
    if user.role == 'manager':
        # Менеджер видит задачи своих подчинённых (включая задачи проектов, где он участник? Упростим: все задачи, где исполнитель подчинённый)
        subordinate = db.query(models.Employee).filter(
            models.Employee.id == task.assignee_id,
            models.Employee.manager_id == user.id
        ).first()
        if subordinate or task.assignee_id == user.id:
            return task
        raise HTTPException(status_code=403, detail="Not your subordinate's task")
    # employee: только свои задачи
    if task.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="Access only to your own tasks")
    return task

@router.get("/", response_model=List[schemas.TaskOut])
def list_tasks(
    status_filter: Optional[str] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    query = db.query(models.Task)
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'manager':
        # задачи, где исполнитель подчинённый или сам менеджер
        subordinate_ids = db.query(models.Employee.id).filter(
            models.Employee.manager_id == current_user.id
        ).all()
        subordinate_ids = [s[0] for s in subordinate_ids] + [current_user.id]
        query = query.filter(models.Task.assignee_id.in_(subordinate_ids))
    else:  # employee
        query = query.filter(models.Task.assignee_id == current_user.id)

    if status_filter:
        query = query.filter(models.Task.status == status_filter)
    if project_id:
        query = query.filter(models.Task.project_id == project_id)

    tasks = query.all()
    return tasks

@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    return get_accessible_task(task_id, db, current_user)

@router.post("/", response_model=schemas.TaskOut)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    # Создавать могут admin и manager (назначать своих подчинённых)
    if current_user.role not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Only admin or manager can create tasks")
    if current_user.role == 'manager':
        # Проверим, что assignee_id — подчинённый или сам менеджер
        assignee = db.query(models.Employee).filter(models.Employee.id == task.assignee_id).first()
        if not assignee or (assignee.manager_id != current_user.id and assignee.id != current_user.id):
            raise HTTPException(status_code=403, detail="Assignee must be your subordinate")
    new_task = models.Task(**task.dict())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    updates: schemas.TaskUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    task = get_accessible_task(task_id, db, current_user)
    # employee может обновлять только статус и фактические часы у своих задач
    if current_user.role == 'employee':
        allowed_fields = {'status', 'actual_hours'}
        for field in updates.dict(exclude_unset=True):
            if field not in allowed_fields:
                raise HTTPException(status_code=403, detail=f"You can only update status and actual_hours")
    # admin и manager могут всё
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    task = get_accessible_task(task_id, db, current_user)
    if current_user.role not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Only admin or manager can delete tasks")
    db.delete(task)
    db.commit()
    return {"ok": True}