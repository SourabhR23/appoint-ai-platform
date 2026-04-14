"""
schemas/graph.py

Pydantic schemas for agent graph CRUD and version management.
The `definition` field contains the full React Flow JSON from the frontend.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeDefinition(BaseModel):
    """A single agent node in the graph."""

    id: str = Field(..., description="UUID string — generated client-side.")
    type: str = Field(..., description="Agent type key from the registry.")
    config: Dict[str, Any] = Field(default_factory=dict)
    # position and label are frontend-only but preserved in JSONB for round-trips
    position: Optional[Dict[str, float]] = None
    label: Optional[str] = None


class EdgeDefinition(BaseModel):
    """A directed connection between two nodes."""

    id: str
    source: str = Field(..., description="Source node ID.")
    target: str = Field(..., description="Target node ID.")
    # condition is non-null for conditional edges (e.g. intent routing)
    condition: Optional[str] = None


class GraphDefinition(BaseModel):
    """Full React Flow JSON payload."""

    nodes: List[NodeDefinition]
    edges: List[EdgeDefinition]


class GraphCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    definition: GraphDefinition


class GraphUpdate(BaseModel):
    """Save a new version of an existing graph."""

    definition: GraphDefinition
    description: Optional[str] = None


class GraphResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str]
    active_version: int
    is_deployed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GraphVersionResponse(BaseModel):
    id: uuid.UUID
    graph_id: uuid.UUID
    version: int
    definition: dict
    is_active: bool
    compiled_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphDeployRequest(BaseModel):
    """Request to activate a specific graph version."""

    version: int = Field(..., ge=1)


class ChatRequest(BaseModel):
    """Incoming chat message to be processed by the deployed graph."""

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(
        ...,
        description="Client-generated session ID for conversation continuity.",
    )
    channel: str = Field(
        default="webchat",
        pattern="^(webchat|whatsapp|sms)$",
    )
    # For WhatsApp/SMS: sender's phone number; for web: anonymous session
    sender_identifier: Optional[str] = None


class ChatResponse(BaseModel):
    """Agent response to a chat message."""

    session_id: str
    response: str
    intent: Optional[str] = None
    appointment_id: Optional[uuid.UUID] = None
    next_action: Optional[str] = None
    error: Optional[str] = None
