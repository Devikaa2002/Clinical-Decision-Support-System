"""
Risk Agent (A2A-compliant)
Now searches patients by name if no ID is given.
Falls back to general risk assessment if no specific scoring system matches.

Runs on port 8002.
"""

import os
import json
import httpx
from fastapi import FastAPI
from common.a2a_models import (
    AgentCard, AgentSkill, TaskSendRequest, TaskSendResponse,
    TaskState, Artifact, TextPart, DataPart,
)
from common.llm_client import chat
from datetime import datetime

app = FastAPI(title="Risk Agent", version="1.0.0")

AGENT_PORT = int(os.getenv("RISK_AGENT_PORT", 8002))
PATIENT_MCP_URL = f"http://localhost:{os.getenv('PATIENT_WIKI_MCP_PORT', 9001)}"
RISK_MCP_URL = f"http://localhost:{os.getenv('RISK_GUIDELINE_MCP_PORT', 9002)}"


AGENT_CARD = AgentCard(
    name="Risk Agent",
    description="Performs clinical risk assessment using evidence-based scoring algorithms (HEART Score, CHA2DS2-VASc, Wells DVT) or general clinical assessment. Searches patients by ID or name. Always produces a risk evaluation with actionable recommendations.",
    url=f"http://localhost:{AGENT_PORT}",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="clinical_risk_assessment",
            name="Clinical Risk Assessment",
            description="Evaluates a patient's clinical risk using standardized scoring systems or general assessment. Searches by patient ID or name.",
            tags=["risk", "clinical", "scoring", "HEART", "CHA2DS2-VASc", "Wells"],
            examples=[
                "Assess cardiac risk for patient P001 with chest pain",
                "Evaluate risk for Rohan Verma with dengue symptoms",
                "What is the risk level for this patient",
            ],
        ),
    ],
)


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD.model_dump()


@app.post("/a2a/tasks/send")
async def handle_task(request: TaskSendRequest) -> TaskSendResponse:
    task_text = ""
    for part in request.message.parts:
        if hasattr(part, "text"):
            task_text += part.text

    # 1. Find the patient - by ID first, then by name
    patient_id = _extract_patient_id(task_text)
    patient_data = None

    if patient_id:
        patient_data = await _fetch_patient(patient_id)

    if not patient_data:
        patient_name = _extract_patient_name(task_text)
        if patient_name:
            found_id = await _search_patient_by_name(patient_name)
            if found_id:
                patient_id = found_id
                patient_data = await _fetch_patient(patient_id)

    # If still no patient data, use the case text itself for risk assessment
    if not patient_data:
        # Build a minimal patient data dict from the case text for risk evaluation
        patient_data = {
            "name": _extract_patient_name(task_text) or "Unknown",
            "source": "extracted_from_case_text",
            "case_description": task_text,
        }
        patient_id = "FROM_CASE"

    # 2. Determine the condition to assess
    condition = _extract_condition(task_text)
    if not condition:
        complaints = patient_data.get("current_complaints", [])
        if complaints:
            condition = " ".join(complaints).lower()
        else:
            condition = task_text[:200]

    # 3. Evaluate risk using Risk Guideline MCP
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{RISK_MCP_URL}/mcp/tools/evaluate_risk",
                json={
                    "patient_data": patient_data,
                    "condition": condition,
                },
            )
            risk_result = resp.json()
    except Exception as e:
        return _fail(request.id, f"Cannot reach Risk Guideline MCP: {e}")

    mcp_tools_used = ["query_patient", "evaluate_risk"]

    if risk_result.get("status") == "success":
        # Get raw rules for transparency
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{RISK_MCP_URL}/mcp/tools/get_risk_rules",
                    json={"condition": condition},
                )
                mcp_tools_used.append("get_risk_rules")
        except:
            pass

        # Create readable risk report
        system_prompt = """You are a clinical risk assessment specialist. Given the risk evaluation results,
create a clear, actionable risk report for a physician.

CRITICAL RULES:
- Use the EXACT patient name and age from the data. Never say age is 0 or unknown if it exists.
- ALWAYS provide specific, condition-appropriate recommendations with medication names and doses.
- Report EXACTLY which MCP scoring systems were applied (e.g. "HEART Score", "CHA2DS2-VASc", "CURB-65").
- If multiple scoring systems were applied, report EACH with its own breakdown and score.
- If no scoring system matched, state: "No applicable validated scoring system in MCP server for this condition."
- The overall risk level is the HIGHEST risk from any individual scoring system.
- Never say "data not available". Use whatever data exists.
- NEVER fabricate or invent scoring system names. Only report systems that were actually applied by the MCP tools.

Include:
1. SCORING SYSTEMS APPLIED (list each by exact name from MCP, or state none matched)
2. SCORE BREAKDOWN per system - each criterion with patient's actual finding and assigned score
3. TOTAL SCORES and OVERALL RISK LEVEL (highest of all systems)
4. CLINICAL RECOMMENDATION - specific next steps including medications with doses, tests, disposition
5. IMPORTANT CAVEATS - what the scoring systems do NOT capture about this patient"""

        user_message = f"""Patient: {patient_data.get('name', 'Unknown')} (ID: {patient_id})
Condition assessed: {condition}

Risk Evaluation Result:
{json.dumps(risk_result.get('result', {}), indent=2)}

Scoring System: {risk_result.get('scoring_system_used', 'General Assessment')}

Original case context:
{task_text}"""

        try:
            report = chat(system_prompt, user_message)
        except:
            report = f"Risk Score Result:\n{json.dumps(risk_result.get('result', {}), indent=2)}"

        return TaskSendResponse(
            id=request.id,
            state=TaskState.COMPLETED,
            artifacts=[
                Artifact(
                    type="text",
                    parts=[TextPart(text=report)],
                    metadata={
                        "source_agent": "risk-agent",
                        "scoring_system": risk_result.get("scoring_system_used"),
                        "mcp_tools_used": mcp_tools_used,
                        "patient_id": patient_id,
                        "condition": condition,
                        "timestamp": datetime.now().isoformat(),
                    },
                ),
                Artifact(
                    type="data",
                    parts=[DataPart(data=risk_result.get("result", {}))],
                    metadata={"type": "raw_risk_scores"},
                ),
            ],
            metadata={
                "agent": "risk-agent",
                "patient_id": patient_id,
                "condition": condition,
                "scoring_system": risk_result.get("scoring_system_used"),
                "mcp_calls": mcp_tools_used,
            },
        )
    else:
        return _fail(request.id, f"Risk evaluation failed: {risk_result.get('error', 'Unknown')}")


# --- Helper Functions ---

async def _fetch_patient(patient_id: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{PATIENT_MCP_URL}/mcp/tools/query_patient",
                json={"patient_id": patient_id},
            )
            result = resp.json()
            if result.get("status") == "success":
                return result["result"]
    except:
        pass
    return None


async def _search_patient_by_name(name: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{PATIENT_MCP_URL}/mcp/tools/list_patients",
                json={},
            )
            result = resp.json()
            if result.get("status") == "success":
                name_lower = name.lower()
                for patient in result["result"]:
                    patient_name = patient.get("name", "").lower()
                    if name_lower in patient_name or patient_name in name_lower:
                        return patient["patient_id"]
                    name_parts = name_lower.split()
                    patient_parts = patient_name.split()
                    for np in name_parts:
                        if len(np) > 2 and any(np in pp for pp in patient_parts):
                            return patient["patient_id"]
    except:
        pass
    return None


def _fail(task_id: str, message: str) -> TaskSendResponse:
    return TaskSendResponse(
        id=task_id,
        state=TaskState.FAILED,
        artifacts=[Artifact(type="text", parts=[TextPart(text=message)])],
        metadata={"agent": "risk-agent", "error": message},
    )


def _extract_patient_id(text: str) -> str | None:
    import re
    match = re.search(r'\b(P\d{3})\b', text.upper())
    if match:
        return match.group(1)
    return None


def _extract_patient_name(text: str) -> str | None:
    import re
    patterns = [
        r'named\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'patient\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+presents',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+returns',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+comes',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(?:a\s+)?\d{1,3}[-\s]?year',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _extract_condition(text: str) -> str | None:
    """Returns ALL matching conditions so evaluate_risk can try multiple scoring systems."""
    text_lower = text.lower()
    condition_keywords = {
        "chest pain": "chest pain",
        "chest tightness": "chest pain",
        "cardiac": "chest pain",
        "angina": "chest pain",
        "heart failure": "heart failure",
        "decompensated": "heart failure",
        "ankle swelling": "heart failure",
        "atrial fibrillation": "atrial fibrillation",
        "af ": "atrial fibrillation",
        "a-fib": "atrial fibrillation",
        "stroke": "atrial fibrillation",
        "dvt": "DVT",
        "deep vein": "DVT",
        "leg swelling": "leg swelling",
        "pneumonia": "pneumonia",
        "lung infection": "pneumonia",
        "productive cough": "pneumonia",
        "cough": "cough",
        "sepsis": "sepsis",
        "infection": "suspected infection",
        "dengue": "dengue fever",
        "fever": "fever",
        "breathlessness": "breathlessness",
        "dyspnea": "breathlessness",
        "bleeding": "hemorrhagic risk",
        "platelet": "thrombocytopenia risk",
    }
    found = []
    seen = set()
    for keyword, condition in condition_keywords.items():
        if keyword in text_lower and condition not in seen:
            found.append(condition)
            seen.add(condition)
    return " ".join(found) if found else None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "risk-agent", "port": AGENT_PORT}


if __name__ == "__main__":
    import uvicorn
    print(f"Risk Agent starting on port {AGENT_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)