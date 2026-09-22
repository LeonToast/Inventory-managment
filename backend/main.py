"""Compatibility entry point. Run from the project root with `uvicorn backend.main:app`."""

if __package__:
    from .workspace.main import app
else:  # Keep `uvicorn main:app` working when launched inside backend/.
    from workspace.main import app

__all__ = ["app"]
