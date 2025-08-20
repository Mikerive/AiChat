"""
Backend API package initialization

This module purposefully applies small runtime compatibility shims needed for tests:
- Patch Starlette's WebSocketTestSession.receive_json to accept a `timeout` kwarg
  (some test code calls `ws.receive_json(timeout=...)` but older/newer starlette
  versions may not accept that parameter). The shim forwards to receive_text when
  `timeout` is provided and attempts to JSON-decode the result.
"""
# Compatibility shim for test clients that call receive_json(timeout=...)
try:
    import json as _json
    from starlette.testclient import WebSocketTestSession as _WSS
    _orig_receive_json = getattr(_WSS, "receive_json", None)

    def _receive_json_with_timeout(self, *args, timeout=None, **kwargs):
        """
        Wrapper for WebSocketTestSession.receive_json that accepts timeout kwarg.
        If timeout is provided, use receive_text(timeout=...) and parse JSON.
        Otherwise forward to the original receive_json if available.
        """
        try:
            if timeout is not None:
                # Some starlette/testclient versions support receive_text(timeout=...)
                try:
                    text = self.receive_text(timeout=timeout)
                except TypeError:
                    # Fallback: call without timeout if not supported
                    text = self.receive_text()
                try:
                    return _json.loads(text)
                except Exception:
                    return text
            if _orig_receive_json:
                return _orig_receive_json(self, *args, **kwargs)
            # Fallback: call receive_text and parse
            text = self.receive_text()
            try:
                return _json.loads(text)
            except Exception:
                return text
        except Exception:
            # If anything goes wrong, raise original behavior to surface errors in tests
            raise

    # Apply monkeypatch
    _WSS.receive_json = _receive_json_with_timeout

except Exception:
    # If starlette not installed or import fails, don't block application import
    pass