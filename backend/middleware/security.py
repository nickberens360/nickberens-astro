"""
Security middleware for adding security headers to all responses.

This middleware ensures consistent security headers are applied across the entire API,
including X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, and Cache-Control.
"""

from fastapi import Request


async def add_security_headers(request: Request, call_next):
    """
    This middleware re-introduces security headers to all outgoing responses,
    ensuring consistent security across the entire API.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-cache"
    return response
