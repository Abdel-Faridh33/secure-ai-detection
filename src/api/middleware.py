"""
API Middleware
Middleware de sécurité et monitoring
"""

from fastapi import Request
import time

async def security_middleware(request: Request, call_next):
    """Middleware de sécurité"""
    start_time = time.time()
    
    # Vérifications de sécurité
    # À implémenter...
    
    response = await call_next(request)
    
    # Logging
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
