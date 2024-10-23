from fastapi import Depends, FastAPI


def init_lambda():
    # Inicializar la aplicación
    app = create_app()
    handler = Mangum(app)

    # Log de inicio
    logger.info("FastAPI application initialized with the following routes:")
    for route in app.routes:
        logger.info(f"Route: {route.path} [{','.join(route.methods)}]")

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
