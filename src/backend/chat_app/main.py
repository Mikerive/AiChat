"""
Main FastAPI application setup and configuration
"""

import logging
import sys
from typing import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings
from database import get_db, DatabaseManager
from event_system import get_event_system, EventType, EventSeverity
from backend.chat_app.routes import voice, system, chat, websocket
from backend.chat_app.utils.logging_config import setup_logging
from logs_app.routes import router as logs_router

logger = logging.getLogger(__name__)


async def get_db_manager() -> AsyncGenerator[DatabaseManager, None]:
    """Database manager dependency"""
    db_manager = get_db()
    try:
        yield db_manager
    finally:
        pass


async def get_event_system_instance() -> AsyncGenerator[None, None]:
    """Event system dependency"""
    event_system = get_event_system()
    try:
        yield event_system
    finally:
        pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Setup improved logging first
    setup_logging("INFO")
    
    settings = get_settings()
    event_system = get_event_system()
    
    # Create FastAPI app
    app = FastAPI(
        title="VTuber Backend API",
        description="REST API for VTuber streaming backend with voice cloning and real-time chat",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        await event_system.emit(
            EventType.ERROR_OCCURRED,
            f"Unhandled exception: {exc}",
            {"request": str(request)},
            EventSeverity.ERROR
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Include routers
    # Mount routers under logical subpaths (e.g., /api/chat, /api/voice)
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    app.include_router(logs_router, prefix="/api", tags=["logs"])
    app.include_router(websocket.router, prefix="/api")
    
    # Startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        """Application startup event"""
        logger.info("VTuber Backend API starting up...")
        
        # Initialize database if available; fail gracefully in test environments without aiosqlite.
        db_manager = get_db()
        try:
            await db_manager.initialize()
            logger.info("Database initialized during startup")
        except Exception as e:
            logger.warning(f"Database initialization skipped or failed during startup: {e}")
        
        # Emit startup event but don't let failures here prevent the app from starting
        try:
            await event_system.emit(
                EventType.SERVICE_STARTED,
                "Backend API started",
                {
                    "host": settings.api_host,
                    "port": settings.api_port,
                    "debug": settings.debug
                }
            )
            logger.info("Backend API startup complete")
        except Exception as e:
            logger.warning(f"Event system emit failed during startup: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event"""
        logger.info("VTuber Backend API shutting down...")
        
        try:
            # Emit shutdown event
            await event_system.emit(
                EventType.SERVICE_STOPPED,
                "Backend API stopped"
            )
            
            # Close database connections
            db_manager = get_db()
            await db_manager.close()
            
            logger.info("Backend API shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "VTuber Backend API",
            "version": "1.0.0",
            "status": "running"
        }
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            # Check database connection
            db_manager = get_db()
            async with db_manager.get_session() as session:
                # Simple query to test database connection
                await session.execute("SELECT 1")
            
            return {
                "status": "healthy",
                "database": "connected",
                "event_system": "active"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    return app