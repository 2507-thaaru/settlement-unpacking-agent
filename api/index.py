"""
Vercel Serverless Function entry point for FastAPI backend.
"""

from api.main import app

# Export the FastAPI instance for Vercel
# Vercel's Python runtime automatically locates `app` inside api/index.py
__all__ = ["app"]
