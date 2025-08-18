"""
Main entry point for VTuber backend - delegates to chat_app
"""

import logging
from backend.chat_app.main import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app using chat_app's main
app = create_app()

if __name__ == "__main__":
    import uvicorn
    from config import get_settings, validate_config
    
    settings = get_settings()
    
    # Validate configuration
    if not validate_config():
        logger.warning("Configuration validation failed - some features may not work properly")
    
    # Run the application
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )