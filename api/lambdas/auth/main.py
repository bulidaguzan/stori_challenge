from fastapi import FastAPI, Path, Query
from mangum import Mangum
from dynamo import create_user, get_user
from models import UserCreate, User
from passlib.apps import custom_app_context as pwd_context


app = FastAPI()
handler = Mangum(app)


@app.get("/", tags=["Register"])
def read_root():
    print("Iniciando")
    us = UserCreate()
    us.name = "tito"
    us.email = "tito@tito.t"
    password = "1234567"
    print("Enviando user a crear")
    create_user(us, password)
    return {"message": "Welcome to the FastAPI demo!"}


@app.post("/register", response_model=UserCreate)
async def register(user: UserCreate):
    # TODO poner dentro de un try catch, y parsear bien el error
    print("Starting new user...")
    #  TODO que no permita duplicados
    if get_user(user.email):
        print("Hashing password...")
        hashed_password = pwd_context.hash(user.password)
        print("Saving into db...")
        user.password = hashed_password
        create_user(user)
        return {
            "email": user.email,
            "password": "Save into database, and encrypt for your security.",
            "name": user.name,
        }
    else:
        msg = "User already exist"
        print(msg)
        return {"message": msg}
