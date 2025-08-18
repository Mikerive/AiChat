"""
Logs App Implementation

Core business logic for logs management
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class LogsService:
    """Service class for logs management"""
    
    def __init__(self, log_file_path: Path):
        """Initialize logs service with log file path"""
        self.log_file_path = Path(log_file_path)
        
    def parse_log_line(self, line: str) -> Dict[str, str]:
        """Parse a log line into structured components"""
        # Pattern: YYYY-MM-DD HH:MM:SS,mmm - module.name - LEVEL - message
        pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - ([^-]+) - (\w+) - (.+)$'
        match = re.match(pattern, line.strip())
        
        if match:
            timestamp, module, severity, message = match.groups()
            return {
                "timestamp": timestamp.strip(),
                "module": module.strip(),
                "severity": severity.strip(),
                "message": message.strip()
            }
        else:
            # Fallback for lines that don't match the expected format
            return {
                "timestamp": "",
                "module": "system",
                "severity": "INFO",
                "message": line.strip()
            }
    
    def get_logs(self, limit: int = 100, severity: Optional[str] = None, 
                 module: Optional[str] = None) -> List[Dict[str, str]]:
        """Get logs with optional filtering"""
        log_entries = []
        
        try:
            if self.log_file_path.exists():
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Get last 'limit' lines first, then filter
                    recent_lines = lines[-limit*2:] if len(lines) > limit*2 else lines
                    
                    for line in recent_lines:
                        if line.strip():
                            parsed_log = self.parse_log_line(line)
                            
                            # Apply filters
                            if severity and parsed_log.get("severity") != severity:
                                continue
                            if module and module.lower() not in parsed_log.get("module", "").lower():
                                continue
                                
                            log_entries.append(parsed_log)
                    
                    # Return last 'limit' entries after filtering
                    log_entries = log_entries[-limit:]
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            log_entries = [self.parse_log_line(f"Error reading log file: {e}")]
        
        return log_entries
    
    def create_log_entry(self, message: str, severity: str = "INFO", 
                        module: str = "api", timestamp: Optional[str] = None) -> Dict[str, str]:
        """Create a new log entry"""
        # Set timestamp if not provided
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format log entry according to our logging format
        milliseconds = datetime.now().microsecond // 1000
        formatted_entry = f"{timestamp},{milliseconds:03d} - {module} - {severity} - {message}"
        
        # Ensure log directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to log file
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(formatted_entry + '\n')
        
        # Also log through Python logging system
        log_level = getattr(logging, severity, logging.INFO)
        logger.log(log_level, f"[{module}] {message}")
        
        return {
            "timestamp": timestamp,
            "module": module,
            "severity": severity,
            "message": message
        }
    
    def clear_logs(self) -> bool:
        """Clear all logs"""
        try:
            if self.log_file_path.exists():
                # Clear the log file
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                
                # Log the clear operation
                logger.info("System logs cleared via API")
                return True
            return True
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return False
    
    def get_log_statistics(self) -> Dict:
        """Get statistics about system logs"""
        stats = {
            "total_entries": 0,
            "severity_counts": {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0},
            "module_counts": {},
            "file_size": 0,
            "oldest_entry": None,
            "newest_entry": None
        }
        
        try:
            if self.log_file_path.exists():
                stats["file_size"] = self.log_file_path.stat().st_size
                
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    stats["total_entries"] = len([l for l in lines if l.strip()])
                    
                    for line in lines:
                        if line.strip():
                            parsed = self.parse_log_line(line)
                            severity = parsed.get("severity", "INFO")
                            module = parsed.get("module", "unknown")
                            timestamp = parsed.get("timestamp", "")
                            
                            # Count severities
                            if severity in stats["severity_counts"]:
                                stats["severity_counts"][severity] += 1
                            
                            # Count modules
                            stats["module_counts"][module] = stats["module_counts"].get(module, 0) + 1
                            
                            # Track oldest and newest
                            if timestamp:
                                if not stats["oldest_entry"]:
                                    stats["oldest_entry"] = timestamp
                                stats["newest_entry"] = timestamp
        except Exception as e:
            logger.error(f"Error getting log statistics: {e}")
        
        return stats