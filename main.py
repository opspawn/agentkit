import os
from fastapi import FastAPI
from agentkit.api.endpoints import registration, messaging
from agentkit.api.middleware import LoggingMiddleware
from agentkit.tools.registry import tool_registry # Import the registry

# --- Environment Variables (Optional: For configurable mock tool URL) ---
MOCK_TOOL_URL = os.environ.get("MOCK_TOOL_ENDPOINT_URL", "http://mock_tool:9001/invoke")

# --- FastAPI App Setup ---
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

# --- Tool Registration (Example: Register mock tool at startup) ---
# In a real application, this might load from config or a database
try:
    tool_registry.register_external_tool(
        name="mock_tool_adder",
        description="A mock tool that adds two numbers (simulated).",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "First number"},
                "y": {"type": "number", "description": "Second number"}
            },
            "required": ["x", "y"]
        },
        endpoint_url=MOCK_TOOL_URL
    )
except ValueError as e:
     print(f"Warning: Could not register mock_tool_adder. Maybe already registered? Error: {e}")
except Exception as e:
     print(f"Error registering mock_tool_adder: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    # This block is for running locally without uvicorn command if needed,
    # but typically uvicorn command is used (as in Dockerfile CMD).
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)