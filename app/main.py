from fastapi import FastAPI
from mangum import Mangum
import logging
from routes.auth import health_check, login, register

# Configurar el logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def init_lambda():
    app = FastAPI()
    app.include_router(
        login.router,
        prefix="/login",
        tags=["User"],
    )
    app.include_router(
        register.router,
        prefix="/register",
        tags=["User"],
    )
    app.include_router(
        health_check.router,
        prefix="/health",
        tags=["Heakth"],
    )

    routes = app.routes
    # Log de rutas
    logger.info("FastAPI application initialized with the following routes:")
    for route in routes:
        logger.info(f"Route: {route.path} [{','.join(route.methods)}]")

    return app


handler = Mangum(init_lambda())
