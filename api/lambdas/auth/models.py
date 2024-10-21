# auth_lambda/models.py
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str
    name: str


class User(BaseModel):
    id: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: str
    password: str
