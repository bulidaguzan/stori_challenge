from fastapi import FastAPI
from mangum import Mangum
import logging
from routes.auth import health_check, login, register

# Configurar el logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def init_lambda():
    app = FastAPI()
    app.include_router(login.router)
    app.include_router(register.router)
    app.include_router(health_check.router)
    return app


handler = Mangum(init_lambda())
