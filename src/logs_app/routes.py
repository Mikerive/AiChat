"""
Logs App REST API Routes
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional

from .models import LogEntry, LogResponse, LogStats
from .service import LogsService


def get_logs_service() -> LogsService:
    """Dependency to get logs service instance"""
    from config import get_settings
    settings = get_settings()
    return LogsService(settings.log_file)


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=LogResponse)
async def get_logs(
    limit: int = Query(100, description="Number of recent log entries to return"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    logs_service: LogsService = Depends(get_logs_service)
):
    """
    Get recent system log entries as structured objects
    
    Query Parameters:
    - limit: Number of recent entries to return (default: 100)
    - severity: Filter by severity level (INFO, WARNING, ERROR, CRITICAL)
    - module: Filter by module name
    """
    try:
        log_entries = logs_service.get_logs(limit=limit, severity=severity, module=module)
        
        return LogResponse(
            logs=log_entries,
            count=len(log_entries),
            log_file=str(logs_service.log_file_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e}")


@router.post("/")
async def create_log_entry(
    log_entry: LogEntry,
    logs_service: LogsService = Depends(get_logs_service)
):
    """
    Create a new log entry
    
    Request Body:
    {
        "message": "Log message content",
        "severity": "INFO|WARNING|ERROR|CRITICAL",
        "module": "module_name",
        "timestamp": "2025-01-01 12:00:00" (optional, current time if not provided)
    }
    """
    try:
        entry = logs_service.create_log_entry(
            message=log_entry.message,
            severity=log_entry.severity,
            module=log_entry.module,
            timestamp=log_entry.timestamp,
            http_code=log_entry.http_code,
            source=log_entry.source,
            error_code=log_entry.error_code,
            params=log_entry.params
        )
        
        return {
            "status": "success",
            "message": "Log entry created",
            "entry": entry
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create log entry: {e}")


@router.delete("/")
async def clear_logs(logs_service: LogsService = Depends(get_logs_service)):
    """Clear all system logs"""
    try:
        success = logs_service.clear_logs()
        
        if success:
            return {
                "status": "success",
                "message": "System logs cleared",
                "log_file": str(logs_service.log_file_path)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear logs")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {e}")


@router.get("/stats", response_model=LogStats)
async def get_log_statistics(logs_service: LogsService = Depends(get_logs_service)):
    """Get statistics about system logs"""
    try:
        stats = logs_service.get_log_statistics()
        return LogStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log statistics: {e}")


@router.get("/health")
async def logs_health():
    """Health check endpoint for logs app"""
    return {"status": "healthy", "service": "logs"}