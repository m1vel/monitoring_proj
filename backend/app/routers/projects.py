from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models, database, dependencies

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Проверка доступа к проекту: admin — любой, manager — если руководитель или участник, employee — только свои проекты
def get_accessible_project(project_id: int, db: Session, user: models.Employee) -> models.Project:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.role == 'admin':
        return project
    if user.role == 'manager':
        # менеджер видит проекты, где он руководитель, или где он участник
        if project.manager_id == user.id:
            return project
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.employee_id == user.id
        ).first()
        if is_member:
            return project
        raise HTTPException(status_code=403, detail="Not your project")
    # employee
    is_member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.employee_id == user.id
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Access only to your projects")
    return project

@router.get("/", response_model=List[schemas.ProjectOut])
def list_projects(
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    if current_user.role == 'admin':
        projects = db.query(models.Project).all()
    elif current_user.role == 'manager':
        # проекты, где он руководитель или участник
        projects = db.query(models.Project).outerjoin(models.ProjectMember).filter(
            (models.Project.manager_id == current_user.id) |
            (models.ProjectMember.employee_id == current_user.id)
        ).distinct().all()
    else:
        # employee: только проекты, в которых он участвует
        projects = db.query(models.Project).join(models.ProjectMember).filter(
            models.ProjectMember.employee_id == current_user.id
        ).all()
    return projects

@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    return get_accessible_project(project_id, db, current_user)

@router.post("/", response_model=schemas.ProjectOut)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(database.get_db),
                   current_user: models.Employee = Depends(dependencies.require_role('admin'))):
    if project.manager_id is None:
        raise HTTPException(status_code=400, detail="manager_id is required")
    proj = models.Project(**project.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj

@router.put("/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: int, updates: schemas.ProjectUpdate,
                   db: Session = Depends(database.get_db),
                   current_user: models.Employee = Depends(dependencies.get_current_user)):
    project = get_accessible_project(project_id, db, current_user)
    if current_user.role != 'admin' and project.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only admin or project manager can edit")
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    project = get_accessible_project(project_id, db, current_user)
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admin can delete projects")
    db.delete(project)
    db.commit()
    return {"ok": True}