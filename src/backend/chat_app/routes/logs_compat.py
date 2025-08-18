# Deprecated compatibility router removed.
# This module intentionally raises an ImportError to signal migration to the new logs_app.
raise ImportError("The legacy logs compatibility router has been removed. Use the new 'logs_app' endpoints under /api/logs instead.")