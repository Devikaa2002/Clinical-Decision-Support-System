"""
A2A Protocol Models (Simplified for PoC)
Based on Google's Agent2Agent Protocol Specification.

Key concepts:
- AgentCard: Discovery document at /.well-known/agent.json
- Task: Unit of work with lifecycle (submitted -> working -> completed)
- Message: Communication between agents with typed Parts
- Artifact: Output produced by a task
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime
import uuid


# --- Task Lifecycle ---

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


# --- Message Parts ---

class TextPart(BaseModel):
    type: str = "text"
    text: str


class DataPart(BaseModel):
    type: str = "data"
    data: dict


Part = TextPart | DataPart


# --- Messages ---

class Message(BaseModel):
    role: str = "user"
    parts: list[Part]
    metadata: Optional[dict] = None


# --- Task ---

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.SUBMITTED
    message: Message
    artifacts: list[Artifact] = []
    metadata: Optional[dict] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Artifact(BaseModel):
    type: str = "text"
    parts: list[Part]
    metadata: Optional[dict] = None


# --- Task Request / Response (JSON-RPC style) ---

class TaskSendRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: Message
    metadata: Optional[dict] = None


class TaskSendResponse(BaseModel):
    id: str
    state: TaskState
    artifacts: list[Artifact] = []
    metadata: Optional[dict] = None


# --- Agent Card ---

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = []
    examples: list[str] = []


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    skills: list[AgentSkill] = []
    capabilities: dict = Field(default_factory=lambda: {
        "streaming": False,
        "pushNotifications": False,
    })
    defaultInputModes: list[str] = ["text"]
    defaultOutputModes: list[str] = ["text"]


# --- Audit Trail Entry ---

class AuditEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    agent: str
    action: str
    details: dict = {}


# Rebuild Task model since Artifact is defined after Task
Task.model_rebuild()