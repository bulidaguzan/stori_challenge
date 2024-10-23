from fastapi import FastAPI

print("llego")


def init_lambda():
    # Log de inicio
    logger.info("FastAPI application initialized with the following routes:")
    for route in app.routes:
        logger.info(f"Route: {route.path} [{','.join(route.methods)}]")
    app = FastAPI()
    app.include_router(
        admin.router,
        prefix="/login",
        tags=["User"],
    )
    app.include_router(
        admin.router,
        prefix="/register",
        tags=["User"],
    )
    app.include_router(
        admin.router,
        prefix="/upload",
        tags=["Transaction"],
    )
    # Log de rutas
    logger.info("FastAPI application initialized with the following routes:")
    for route in app.routes:
        logger.info(f"Route: {route.path} [{','.join(route.methods)}]")

    return app


print("Llego")
app = init_lambda()
handler = Mangum(app)
