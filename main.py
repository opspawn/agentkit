from fastapi import FastAPI
from agentkit.api.endpoints import registration, messaging
from agentkit.api.middleware import LoggingMiddleware

app = FastAPI(
    title="AgentKit API",
    description="API for managing autonomous AI agents within the Opspawn ecosystem.",
    version="0.1.0",
)

# Add Middleware
app.add_middleware(LoggingMiddleware)

@app.get("/")
async def read_root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to AgentKit API"}

# Include API Routers
app.include_router(registration.router, prefix="/v1", tags=["Registration"])
app.include_router(messaging.router, prefix="/v1", tags=["Messaging"])

if __name__ == "__main__":
    # This block is for running locally without uvicorn command if needed,
    # but typically uvicorn command is used (as in Dockerfile CMD).
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)