# models.py
from typing import Optional, List
from datetime import datetime


class UserBase:
    print("Creando User base")
    email: str
    name: str


class UserCreate(UserBase):
    print("Creando UserCreate")
    password: str


class User(UserBase):
    print("Creando User")
    id: str
    created_at: str
    updated_at: Optional[str] = None
