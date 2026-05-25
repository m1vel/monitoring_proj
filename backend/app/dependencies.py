from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from . import auth, models, database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.Employee).filter(models.Employee.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(required_role: str):
    def role_dependency(user: models.Employee = Depends(get_current_user)):
        if user.role != required_role and user.role != 'admin':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user
    return role_dependency

def get_managed_employee(employee_id: int, db: Session = Depends(database.get_db),
                         user: models.Employee = Depends(get_current_user)):
    if user.role == 'admin':
        return db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    elif user.role == 'manager':
        sub = db.query(models.Employee).filter(
            (models.Employee.id == employee_id) &
            ((models.Employee.manager_id == user.id) | (models.Employee.id == user.id))  # самого себя видит
        ).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Employee not found or not your subordinate")
        return sub
    else:  # employee
        if employee_id == user.id:
            return user
        raise HTTPException(status_code=403, detail="You can only access your own data")