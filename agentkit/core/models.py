from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone # Import timezone
import uuid

# --- API Response Models ---

class ApiResponse(BaseModel):
    """Standard API response structure."""
    status: str = Field(..., description="Status of the response ('success' or 'error')")
    message: Optional[str] = Field(None, description="Optional message providing details about the response")
    data: Optional[Any] = Field(None, description="Optional data payload")
    error_code: Optional[str] = Field(None, description="Specific error code if status is 'error'")

# --- Agent Registration Models ---

class AgentMetadata(BaseModel):
    """Custom metadata for an agent."""
    description: Optional[str] = Field(None, description="Optional description of the agent")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional agent-specific configuration")
    # Add other relevant metadata fields as needed

class AgentRegistrationPayload(BaseModel):
    """Payload for registering a new agent."""
    agentName: str = Field(..., description="Unique name for the agent")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities the agent possesses")
    version: str = Field(..., description="Version string for the agent")
    contactEndpoint: HttpUrl = Field(..., description="URL endpoint where the agent can be reached")
    metadata: Optional[AgentMetadata] = Field(None, description="Optional structured metadata about the agent")

class AgentInfo(BaseModel):
    """Information stored about a registered agent."""
    agentId: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier assigned to the agent")
    agentName: str
    capabilities: List[str]
    version: str
    contactEndpoint: HttpUrl
    metadata: Optional[AgentMetadata] = None
    registration_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- Messaging Models ---

class SessionContext(BaseModel):
    """Contextual information for a message within a session."""
    sessionId: Optional[str] = Field(None, description="Identifier for the ongoing session or conversation")
    priorMessages: Optional[List[str]] = Field(default_factory=list, description="History of recent messages in the session (optional)")
    # Add other relevant context fields

class MessagePayload(BaseModel):
    """Payload for sending a message to an agent."""
    senderId: str = Field(..., description="Agent ID of the sender")
    # receiverId is implicit in the endpoint path /agents/{agentId}/run
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the message was created")
    messageType: str = Field(..., description="Type of message (e.g., 'intent_query', 'data_response', 'tool_invocation', 'error_notification')")
    payload: Dict[str, Any] = Field(..., description="The actual content/data of the message")
    sessionContext: Optional[SessionContext] = Field(None, description="Optional session context")
    # --- Ops-Core Specific Fields (Optional) ---
    task_name: Optional[str] = Field(None, description="Specific task name provided by the caller (e.g., Ops-Core)")
    opscore_session_id: Optional[str] = Field(None, description="Correlation ID for the Ops-Core session, if provided")
    opscore_task_id: Optional[str] = Field(None, description="Correlation ID for the specific Ops-Core task, if provided")

# --- Tool Integration Models ---

class ToolDefinition(BaseModel):
    """Information stored about an available tool."""
    toolId: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the tool")
    name: str = Field(..., description="Human-readable name of the tool")
    description: Optional[str] = Field(None, description="Description of what the tool does")
    interface_details: Dict[str, Any] = Field(..., description="Details on how to invoke the tool (e.g., parameters, authentication)")
    # Example interface_details: {"type": "api", "endpoint": "...", "method": "POST", "params": [...]}
    # Example interface_details: {"type": "python_function", "module": "...", "function": "..."}