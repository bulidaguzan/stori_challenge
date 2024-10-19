from fastapi import FastAPI, Path, Query
from mangum import Mangum
from dynamo import create_user
from models import UserCreate


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
