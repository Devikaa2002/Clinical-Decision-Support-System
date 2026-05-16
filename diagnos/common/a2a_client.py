"""
A2A Client - sends task messages to remote agents and fetches agent cards.
"""

import httpx
from common.a2a_models import (
    AgentCard,
    TaskSendRequest,
    TaskSendResponse,
    Message,
    TextPart,
    AuditEntry,
)
from datetime import datetime


class A2AClient:
    """Client for communicating with A2A-compliant agents."""

    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout
        self.audit_log: list[AuditEntry] = []

    async def fetch_agent_card(self, base_url: str) -> AgentCard | None:
        """
        Discover an agent by fetching its Agent Card.
        GET {base_url}/.well-known/agent.json
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/.well-known/agent.json")
                if resp.status_code == 200:
                    card = AgentCard(**resp.json())
                    self._log("discovery", "agent_card_fetched", {
                        "agent": card.name,
                        "url": base_url,
                        "skills": [s.id for s in card.skills],
                    })
                    return card
        except Exception as e:
            self._log("discovery", "agent_card_failed", {
                "url": base_url,
                "error": str(e),
            })
        return None

    async def send_task(
        self,
        agent_url: str,
        task_text: str,
        metadata: dict | None = None,
    ) -> TaskSendResponse | None:
        """
        Send a task to a remote agent.
        POST {agent_url}/a2a/tasks/send
        """
        request = TaskSendRequest(
            message=Message(
                role="user",
                parts=[TextPart(text=task_text)],
                metadata=metadata or {},
            ),
            metadata=metadata or {},
        )

        self._log("planner", "task_sent", {
            "agent_url": agent_url,
            "task_id": request.id,
            "task_preview": task_text[:100],
        })

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{agent_url}/a2a/tasks/send",
                    json=request.model_dump(),
                )
                if resp.status_code == 200:
                    result = TaskSendResponse(**resp.json())
                    self._log("planner", "task_completed", {
                        "task_id": result.id,
                        "state": result.state,
                        "artifacts_count": len(result.artifacts),
                    })
                    return result
                else:
                    self._log("planner", "task_failed", {
                        "status_code": resp.status_code,
                        "body": resp.text[:200],
                    })
        except Exception as e:
            self._log("planner", "task_error", {
                "agent_url": agent_url,
                "error": str(e),
            })
        return None

    def _log(self, agent: str, action: str, details: dict):
        entry = AuditEntry(agent=agent, action=action, details=details)
        self.audit_log.append(entry)

    def get_audit_log(self) -> list[dict]:
        return [e.model_dump() for e in self.audit_log]

    def clear_audit_log(self):
        self.audit_log = []