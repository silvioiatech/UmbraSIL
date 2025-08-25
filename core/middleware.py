from fastapi import Request
import time
import logging

class RequestMiddleware:
    """Request logging and rate limiting"""
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logging.info(
            f"Method: {request.method} Path: {request.url.path} "
            f"Time: {process_time:.2f}s Status: {response.status_code}"
        )
        
        return response
