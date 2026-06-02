"""Vercel serverless entry point for the Zoetis RIE backend.

Vercel's Python runtime serves an ASGI application exported as ``app``. The
FastAPI app lives in the ``backend/app`` package; we put it on the path and
re-export it here. The committed seed files travel with the function bundle
(see ``includeFiles`` in vercel.json), so the provider reads them directly and
never needs to write to the read-only serverless filesystem.
"""
import os
import sys

# Make the backend package importable from this function's bundle.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.main import app  # noqa: E402  (ASGI app Vercel will serve)

__all__ = ["app"]
