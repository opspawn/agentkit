import asyncio
import os
import logging
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from dotenv import load_dotenv
from pydantic import BaseModel, HttpUrl

# Assuming the SDK client is now async
from agentkit.sdk.client import AgentKitClient, AgentKitError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
AGENT_NAME = "OpsCoreAwareAgent_001"
AGENT_VERSION = "0.1.0"
# The endpoint where this agent will listen for messages from AgentKit
# Make sure the port is unique if running multiple agents locally
AGENT_CONTACT_ENDPOINT = HttpUrl("http://localhost:8001") # Example port
AGENT_CAPABILITIES = ["process_workflow_task", "report_status"]

# AgentKit API URL (usually localhost if running service locally)
AGENTKIT_API_URL = os.getenv("AGENTKIT_API_URL", "http://localhost:8000")
# Ops-Core details (REQUIRED for this agent)
OPSCORE_API_URL = os.getenv("OPSCORE_API_URL")
OPSCORE_API_KEY = os.getenv("OPSCORE_API_KEY")

# --- Agent State ---
# Simple in-memory state for demonstration
agent_state = "initializing"
agent_id: Optional[str] = None
sdk_client: Optional[AgentKitClient] = None

# --- FastAPI App ---
app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION)

class IncomingMessage(BaseModel):
    """Structure matching the message sent by AgentKit's dispatcher"""
    senderId: str
    messageType: str
    payload: Dict[str, Any]
    sessionContext: Optional[Dict[str, Any]] = None

async def report_state(new_state: str, details: Optional[dict] = None):
    """Helper function to report state to Ops-Core via SDK"""
    global agent_state, agent_id, sdk_client
    if sdk_client and agent_id and OPSCORE_API_URL and OPSCORE_API_KEY:
        try:
            logger.info(f"Reporting state '{new_state}' to Ops-Core...")
            await sdk_client.report_state_to_opscore(
                agent_id=agent_id,
                state=new_state,
                details=details
            )
            agent_state = new_state
            logger.info(f"State successfully reported. Current state: {agent_state}")
        except AgentKitError as e:
            logger.error(f"Failed to report state '{new_state}' to Ops-Core: {e}", exc_info=True)
            # Decide how to handle failure - maybe retry? For now, just log.
        except Exception as e:
            logger.error(f"Unexpected error reporting state '{new_state}': {e}", exc_info=True)
    else:
        logger.warning(f"Cannot report state '{new_state}'. SDK not initialized or Ops-Core config missing.")
        # Update local state anyway? Or keep it as is? Let's update locally for demo.
        agent_state = new_state


@app.post("/")
async def handle_message(message: IncomingMessage, background_tasks: BackgroundTasks):
    """Endpoint to receive messages from AgentKit"""
    logger.info(f"Received message: Type='{message.messageType}', Sender='{message.senderId}'")
    logger.debug(f"Payload: {message.payload}")
    logger.debug(f"Context: {message.sessionContext}")

    # Report 'active' state when starting to process
    background_tasks.add_task(report_state, "active")

    response_payload = {"status": "received", "message": "Acknowledged"}
    error_details = None

    try:
        if message.messageType == "workflow_task": # Example task type from Ops-Core
            logger.info("Processing hypothetical workflow task...")
            # Simulate work
            await asyncio.sleep(2)
            task_result = f"Processed task '{message.payload.get('task_name', 'unknown')}' successfully."
            logger.info(task_result)
            response_payload = {"status": "completed", "result": task_result}
            # Report 'idle' after successful processing
            background_tasks.add_task(report_state, "idle")
        else:
            logger.warning(f"Unhandled message type: {message.messageType}")
            response_payload = {"status": "ignored", "reason": f"Unhandled message type: {message.messageType}"}
            # Report 'idle' as we didn't do anything specific
            background_tasks.add_task(report_state, "idle")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        error_details = {"error_code": "PROCESSING_ERROR", "message": str(e)}
        # Report 'error' state
        background_tasks.add_task(report_state, "error", details=error_details)
        # Return error response to AgentKit (which might forward it)
        raise HTTPException(status_code=500, detail=error_details)

    return response_payload


@app.on_event("startup")
async def startup_event():
    """Register agent on startup"""
    global agent_id, sdk_client
    logger.info("Agent starting up...")

    if not OPSCORE_API_URL or not OPSCORE_API_KEY:
        logger.error("FATAL: OPSCORE_API_URL or OPSCORE_API_KEY environment variables not set.")
        # In a real app, you might exit or prevent startup here
        # For the example, we'll allow it to run but state reporting will fail.
        print("\n" + "="*50)
        print("ERROR: Ops-Core URL/Key not configured. State reporting will fail.")
        print("Please set OPSCORE_API_URL and OPSCORE_API_KEY in your .env file.")
        print("="*50 + "\n")


    sdk_client = AgentKitClient(base_url=AGENTKIT_API_URL)
    await report_state("initializing") # Report initial state

    try:
        logger.info(f"Registering agent '{AGENT_NAME}' with AgentKit at {AGENTKIT_API_URL}...")
        agent_id = await sdk_client.register_agent(
            agent_name=AGENT_NAME,
            capabilities=AGENT_CAPABILITIES,
            version=AGENT_VERSION,
            contact_endpoint=AGENT_CONTACT_ENDPOINT,
            metadata={"description": "Example agent demonstrating Ops-Core integration"}
        )
        logger.info(f"Agent registered successfully with ID: {agent_id}")
        # Report 'idle' state after successful registration
        await report_state("idle")

    except AgentKitError as e:
        logger.error(f"Failed to register agent: {e}", exc_info=True)
        await report_state("error", details={"error_code": "REGISTRATION_FAILED", "message": str(e)})
        # Optionally shut down the agent if registration fails critically
        # For example: raise SystemExit("Agent registration failed")
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}", exc_info=True)
        await report_state("error", details={"error_code": "UNEXPECTED_STARTUP_ERROR", "message": str(e)})
        # raise SystemExit("Unexpected startup error")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global sdk_client
    logger.info("Agent shutting down...")
    # Optionally report 'offline' state or deregister? Ops-Core might handle timeouts.
    # await report_state("offline") # Requires Ops-Core to handle this state
    if sdk_client:
        await sdk_client.close()
        logger.info("AgentKit SDK client closed.")


if __name__ == "__main__":
    host, port_str = str(AGENT_CONTACT_ENDPOINT).split(":")[-2:]
    host = host.split("//")[-1] # Extract host from URL
    port = int(port_str)

    logger.info(f"Starting agent server at {host}:{port}")
    uvicorn.run(app, host=host, port=port)

    # Note: Uvicorn runs the startup/shutdown events.