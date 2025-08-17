"""
Main entry point for the VTuber application
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.main import create_app
from backend.api.routes.websocket import websocket_router
from config import get_settings
from database import get_db
from event_system import get_event_system, emit_system_status

# Configure logging
logging.basicConfig(
    level=get_settings().log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_settings().log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class Application:
    """Main application class"""
    
    def __init__(self):
        self.settings = get_settings()
        self.event_system = get_event_system()
        self.db_manager = get_db()
        self.app = None
        self.server = None
    
    async def initialize(self) -> None:
        """Initialize the application"""
        logger.info("Initializing VTuber application...")
        
        try:
            # Initialize database
            await self.db_manager.initialize()
            
            # Create FastAPI app
            self.app = await create_app()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> None:
        """Start the application"""
        if not self.app:
            await self.initialize()
        
        try:
            # Emit system status event
            await emit_system_status("Application starting", {
                "host": self.settings.api_host,
                "port": self.settings.api_port,
                "debug": self.settings.debug
            })
            
            logger.info(f"Starting VTuber application on {self.settings.api_host}:{self.settings.api_port}")
            
            # Start server
            config = uvicorn.Config(
                app=self.app,
                host=self.settings.api_host,
                port=self.settings.api_port,
                log_level=self.settings.log_level.lower(),
                reload=self.settings.debug
            )
            
            self.server = uvicorn.Server(config)
            await self.server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the application gracefully"""
        logger.info("Shutting down application...")
        
        try:
            # Emit system status event
            await emit_system_status("Application shutting down")
            
            # Close database connections
            await self.db_manager.close()
            
            # Close server
            if self.server:
                self.server.should_exit = True
                await self.server.shutdown()
            
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point"""
    app = Application()
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        sys.exit(1)