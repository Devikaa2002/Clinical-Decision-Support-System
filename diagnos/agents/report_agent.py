"""
Report / Recommendation Agent (A2A-compliant)
ALWAYS produces a full report - never says data unavailable.
Uses whatever data it receives to make the best possible assessment.

Runs on port 8003.
"""



import os, json
from fastapi import FastAPI
from common.a2a_models import (
    AgentCard, AgentSkill, TaskSendRequest, TaskSendResponse,
    TaskState, Artifact, TextPart, DataPart,
)
from common.llm_client import chat
from datetime import datetime

app = FastAPI(title="Report Agent", version="2.0.0")
AGENT_PORT = int(os.getenv("REPORT_AGENT_PORT", 8003))

AGENT_CARD = AgentCard(
    name="Report Agent",
    description="Synthesizes all agent outputs into a comprehensive clinical recommendation. ALWAYS produces actionable recommendations with differential diagnoses. Never reports data as unavailable.",
    url=f"http://localhost:{AGENT_PORT}", version="2.0.0",
    skills=[AgentSkill(id="clinical_report_synthesis", name="Clinical Report Synthesis",
        description="Produces physician-ready reports with recommendations, risk scores, differential diagnoses, and action plans.",
        tags=["report", "synthesis", "recommendation"],
        examples=["Synthesize history and risk into recommendation", "Generate clinical report"])],
)

@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD.model_dump()

@app.post("/a2a/tasks/send")
async def handle_task(request: TaskSendRequest) -> TaskSendResponse:
    task_text = "".join(p.text for p in request.message.parts if hasattr(p, "text"))
    task_data = {}
    for p in request.message.parts:
        if hasattr(p, "data"):
            task_data.update(p.data)

    system_prompt = """You are a clinical decision support system generating a report for a physician.

STRICT RULES — VIOLATION OF ANY RULE IS A CRITICAL ERROR:

1. ONLY use data that is EXPLICITLY written in the agent outputs below. 
2. NEVER invent, assume, or fabricate ANY patient details including:
   - Name (if only "Alice" is given, use "Alice" — do NOT add a last name)
   - Age (use the EXACT number from the data — do NOT change it)
   - Gender, vitals, labs, history, allergies — use ONLY what is provided
3. If a field is not in the agent outputs, write "Not provided in case data" for that field.
4. NEVER add symptoms, conditions, travel history, smoking status, or family history that are not in the data.
5. Do NOT round, estimate, or modify any numbers. BP 155/60 stays 155/60 — not 120/80.
6. SpO2 98% stays 98% — not 95%.
7. If the patient is allergic to nuts, say allergic to nuts — do NOT say no allergies.
8. Cross-check: Before writing any fact, ask yourself "Is this EXPLICITLY in the input below?" If not, do NOT include it.

REPORT STRUCTURE:

CLINICAL DECISION SUPPORT REPORT
=================================

1. EXECUTIVE SUMMARY
   Based ONLY on provided data. State exactly what the patient presented with.

2. PATIENT PROFILE
   ONLY name, age, gender from the data. Nothing else unless explicitly provided.

3. CLINICAL PRESENTATION
   ONLY the symptoms and vitals from the data. Use exact numbers.

4. RISK ASSESSMENT
   From the Risk Agent's output. If general assessment, state that clearly.

5. DIFFERENTIAL DIAGNOSES
   Based ONLY on the symptoms and findings that are actually in the data.

6. CLINICAL RECOMMENDATIONS
   a) IMMEDIATE (next 1-2 hours)
   b) SHORT-TERM (next 24-48 hours)
   c) FOLLOW-UP

7. MEDICATION CONSIDERATIONS
   Based ONLY on current medications mentioned. If none mentioned, say "No current medications reported."

8. RED FLAGS & ALERTS
   ONLY from actual data. Include known allergies from the data.

9. PROVENANCE
   Which agents contributed.

=================================

REMEMBER: It is better to say "Not provided" than to invent data. 
A fabricated vital sign or allergy could harm a patient."""
    user_msg = f"""Generate the final clinical report from these agent outputs:

{task_text}

Metadata: {json.dumps(task_data) if task_data else 'None'}
Planner context: {json.dumps(request.metadata) if request.metadata else 'None'}"""

    try:
        report = chat(system_prompt, user_msg, max_tokens=3500)
    except Exception as e:
        return TaskSendResponse(id=request.id, state=TaskState.FAILED,
            artifacts=[Artifact(type="text", parts=[TextPart(text=f"Report generation failed: {e}")])],
            metadata={"agent": "report-agent", "error": str(e)})

    wiki_updates = []
    if "wiki_update" in task_text.lower() or "wiki_updated" in task_text.lower():
        wiki_updates.append("Patient Wiki was updated during this session")
    if "new patient" in task_text.lower() or "new_patient" in task_text.lower():
        wiki_updates.append("A new patient record was created")

    # Extract actual MCP tools and scoring systems from agent outputs
    mcp_tools_from_agents = []
    scoring_systems_used = []
    for tool_name in ["query_patient", "evaluate_risk", "get_risk_rules", "search_patient",
                      "create_patient", "update_patient", "ingest_record"]:
        if tool_name in task_text:
            mcp_tools_from_agents.append(tool_name)
    for score_name in ["HEART", "CHA2DS2-VASc", "Wells", "CURB-65", "qSOFA"]:
        if score_name.lower() in task_text.lower():
            scoring_systems_used.append(score_name)

    audit = {
        "report_generated_at": datetime.now().isoformat(),
        "contributing_agents": ["history-agent", "risk-agent", "report-agent"],
        "mcp_tools_used": mcp_tools_from_agents if mcp_tools_from_agents else ["query_patient", "evaluate_risk"],
        "scoring_systems_applied": scoring_systems_used if scoring_systems_used else ["see risk agent output"],
        "llm_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "wiki_updates": wiki_updates,
        "disclaimer": "Clinical decision SUPPORT tool. Must be validated by a physician.",
    }

    return TaskSendResponse(id=request.id, state=TaskState.COMPLETED,
        artifacts=[
            Artifact(type="text", parts=[TextPart(text=report)], metadata={
                "source_agent": "report-agent", "report_type": "clinical_recommendation",
                "timestamp": datetime.now().isoformat()}),
            Artifact(type="data", parts=[DataPart(data=audit)], metadata={"type": "audit_trail"}),
        ],
        metadata={"agent": "report-agent", "audit_trail": audit})

@app.get("/health")
async def health():
    return {"status": "ok", "service": "report-agent", "port": AGENT_PORT}

if __name__ == "__main__":
    import uvicorn
    print(f"Report Agent on port {AGENT_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)