import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Configure basic logging
# In a real app, use a more robust logging setup (e.g., structlog, loguru)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Logs incoming requests and outgoing responses.
        """
        start_time = time.time()

        # Log request details
        log_message = (
            f"Request: {request.method} {request.url.path} "
            f"Client: {request.client.host}:{request.client.port}"
        )
        logger.info(log_message)

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time) # Add process time header

            # Log response details
            log_message = (
                f"Response: {response.status_code} "
                f"Method: {request.method} Path: {request.url.path} "
                f"Completed in: {process_time:.4f}s"
            )
            logger.info(log_message)

        except Exception as e:
            process_time = time.time() - start_time
            # Log exceptions if they bubble up to the middleware
            log_message = (
                f"Request Failed: {request.method} {request.url.path} "
                f"Client: {request.client.host}:{request.client.port} "
                f"Error: {e} "
                f"Completed in: {process_time:.4f}s"
            )
            logger.error(log_message, exc_info=True) # Include stack trace
            # Re-raise the exception so FastAPI's exception handlers can process it
            raise e

        return response

# You can add more middleware here as needed (e.g., authentication, CORS)