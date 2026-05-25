from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models, database, dependencies

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

@router.get("/", response_model=List[schemas.ReviewOut])
def list_reviews(
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    if current_user.role == 'admin':
        reviews = db.query(models.TaskReview).all()
    elif current_user.role == 'manager':
        reviews = db.query(models.TaskReview).join(models.Task).join(
            models.Employee, models.Task.assignee_id == models.Employee.id
        ).filter(
            (models.TaskReview.reviewer_id == current_user.id) |
            (models.Employee.manager_id == current_user.id)
        ).all()
    else:
        reviews = db.query(models.TaskReview).join(models.Task).filter(
            models.Task.assignee_id == current_user.id
        ).all()
    return reviews

@router.post("/", response_model=schemas.ReviewOut)
def create_review(
    review: schemas.ReviewCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.get_current_user)
):
    if current_user.role not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Only admin or manager can review")
    task = db.query(models.Task).filter(models.Task.id == review.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == 'manager':
        assignee = db.query(models.Employee).filter(models.Employee.id == task.assignee_id).first()
        if not assignee or assignee.manager_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only review your subordinates' tasks")
    existing = db.query(models.TaskReview).filter(models.TaskReview.task_id == review.task_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Task already reviewed")
    new_review = models.TaskReview(**review.dict())
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Employee = Depends(dependencies.require_role('admin'))
):
    review = db.query(models.TaskReview).filter(models.TaskReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404)
    db.delete(review)
    db.commit()
    return {"ok": True}