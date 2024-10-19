from fastapi import FastAPI, Path, Query
from mangum import Mangum
from typing import Optional, List

app = FastAPI()
handler = Mangum(app)


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the FastAPI demo!"}
