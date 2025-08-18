"""
Logs App FastAPI Application

Standalone logs app that can be mounted or run independently
"""

from fastapi import FastAPI
from .routes import router

# Create the FastAPI app for logs app
app = FastAPI(
    title="VTuber Logs App",
    description="Centralized logging application with REST API",
    version="1.0.0",
    docs_url="/logs/docs",
    redoc_url="/logs/redoc",
    openapi_url="/logs/openapi.json"
)

# Include the routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8767)