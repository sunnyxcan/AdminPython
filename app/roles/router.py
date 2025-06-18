# app/roles/router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.roles import schemas, crud, models

router = APIRouter(
    prefix="/api/roles",
    tags=["Roles"],
    responses={404: {"deskripsi": "Not found"}},
)

# Pastikan tabel dibuat saat aplikasi dimulai
@router.on_event("startup")
async def create_roles_table():
    from app.core.database import engine, Base
    Base.metadata.create_all(bind=engine)
    print("Tabel 'roles' dipastikan ada atau dibuat.")


@router.post("/", response_model=schemas.RoleInDB)
def create_new_role(role: schemas.RoleCreate, db: Session = Depends(get_db)):
    db_role = crud.get_role_by_name(db, role_name=role.name)
    if db_role:
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    return crud.create_role(db=db, role=role)

@router.get("/", response_model=List[schemas.RoleInDB])
def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    roles = crud.get_roles(db, skip=skip, limit=limit)
    return roles

@router.get("/{role_id}", response_model=schemas.RoleInDB)
def read_role(role_id: int, db: Session = Depends(get_db)):
    db_role = crud.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role

@router.put("/{role_id}", response_model=schemas.RoleInDB)
def update_existing_role(role_id: int, role: schemas.RoleUpdate, db: Session = Depends(get_db)):
    db_role = crud.update_role(db, role_id=role_id, role=role)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role

@router.delete("/{role_id}", response_model=schemas.RoleInDB)
def delete_existing_role(role_id: int, db: Session = Depends(get_db)):
    db_role = crud.delete_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role