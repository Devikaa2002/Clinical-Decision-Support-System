"""
Planner / Orchestrator 
Fixed serialization, wiki updates, audit trail.
Runs on port 8000.
"""

import os, json, asyncio, httpx
from fastapi import FastAPI
from pydantic import BaseModel
from common.a2a_models import AgentCard, TaskState
from common.a2a_client import A2AClient
from common.llm_client import chat_json
from datetime import datetime

app = FastAPI(title="Planner / Orchestrator", version="2.0.0")
PLANNER_PORT = int(os.getenv("PLANNER_PORT", 8000))
AGENT_REGISTRY = [
    f"http://localhost:{os.getenv('HISTORY_AGENT_PORT', 8001)}",
    f"http://localhost:{os.getenv('RISK_AGENT_PORT', 8002)}",
    f"http://localhost:{os.getenv('REPORT_AGENT_PORT', 8003)}",
]

discovered_agents: dict[str, AgentCard] = {}
a2a_client = A2AClient()


async def discover_agents():
    global discovered_agents
    discovered_agents = {}
    for url in AGENT_REGISTRY:
        card = await a2a_client.fetch_agent_card(url)
        if card:
            discovered_agents[card.name] = card
            print(f"  Found: {card.name} at {card.url}")
    return discovered_agents


async def create_plan(case_text, agents):
    descs = [{"name": n, "url": c.url, "description": c.description,
              "skills": [{"id": s.id, "name": s.name, "description": s.description} for s in c.skills]}
             for n, c in agents.items()]
    return chat_json(
        """You are a clinical workflow planner. Create an execution plan.
RULES:
- Use ONLY the listed agents. Use their EXACT names and URLs.
- Assign parallel_group numbers (same group = concurrent).
- Report Agent ALWAYS runs LAST in the highest parallel_group.
- Include ALL available agents in the plan.
- Include patient ID or patient name if mentioned in the case.

Respond with ONLY valid JSON:
{"case_summary": "brief summary", "steps": [{"agent_name": "exact name", "agent_url": "exact URL", "task": "instruction with patient details", "parallel_group": 1, "rationale": "why"}], "execution_order": "flow description"}""",
        f"CASE:\n{case_text}\n\nAVAILABLE AGENTS:\n{json.dumps(descs, indent=2)}"
    )


async def execute_plan(plan):
    steps = plan.get("steps", [])
    if not steps: return {}
    groups = {}
    for s in steps:
        groups.setdefault(s.get("parallel_group", 1), []).append(s)

    all_results = {}
    for gn in sorted(groups.keys()):
        group = groups[gn]
        is_report = any("report" in s.get("agent_name", "").lower() for s in group)

        if is_report:
            for s in group:
                combined = f"Case: {plan.get('case_summary', '')}\n\n=== AGENT OUTPUTS ===\n\n"
                for prev_name, prev in all_results.items():
                    combined += f"--- {prev_name} ---\n"
                    if prev and prev.artifacts:
                        for a in prev.artifacts:
                            for p in a.parts:
                                if hasattr(p, "text"): combined += p.text + "\n"
                                elif hasattr(p, "data"): combined += json.dumps(p.data, indent=2) + "\n"
                    else:
                        combined += "[No response]\n"
                    combined += "\n"
                all_results[s["agent_name"]] = await a2a_client.send_task(s["agent_url"], combined,
                    metadata={"source": "planner", "contributing_agents": list(all_results.keys())})
        else:
            tasks = [a2a_client.send_task(s["agent_url"], s["task"], metadata={"source": "planner"}) for s in group]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for s, r in zip(group, results):
                all_results[s["agent_name"]] = None if isinstance(r, Exception) else r

    # If Risk Agent couldn't find the patient, re-run with History Agent's full output
    history_output = all_results.get("History Agent")
    risk_result = all_results.get("Risk Agent")
    if history_output and history_output.artifacts and risk_result and risk_result.metadata:
        if risk_result.metadata.get("patient_id") == "FROM_CASE":
            history_text = ""
            resolved_pid = None
            for a in history_output.artifacts:
                for p in a.parts:
                    if hasattr(p, "text"):
                        history_text += p.text + "\n"
                    if hasattr(p, "data") and isinstance(p.data, dict):
                        resolved_pid = p.data.get("patient_id", resolved_pid)
                if a.metadata:
                    resolved_pid = a.metadata.get("patient_id", resolved_pid)
            if resolved_pid:
                enriched_task = f"Patient ID: {resolved_pid}\n\n=== HISTORY AGENT OUTPUT ===\n{history_text}\n=== ORIGINAL CASE ===\n{plan.get('case_summary', '')}\n\nPerform clinical risk assessment using the ACTUAL vitals, labs, age, and complaints from the History Agent output above."
                risk_url = None
                for s in steps:
                    if "risk" in s.get("agent_name", "").lower():
                        risk_url = s["agent_url"]
                        break
                if risk_url:
                    retry = await a2a_client.send_task(risk_url, enriched_task, metadata={"source": "planner", "enriched": True, "patient_id": resolved_pid})
                    if retry:
                        all_results["Risk Agent"] = retry

    return all_results


class CaseSubmission(BaseModel):
    case_text: str
    patient_id: str | None = None


@app.post("/submit-case")
async def submit_case(sub: CaseSubmission):
    a2a_client.clear_audit_log()

    agents = await discover_agents()
    if not agents:
        return {"status": "error", "plan": {}, "results": {}, "final_report": "No agents found. Make sure all services are running.", "audit_trail": a2a_client.get_audit_log(), "discovered_agents": [], "wiki_updates": []}

    a2a_client._log("planner", "discovery_complete", {"agents_found": list(agents.keys())})

    case_text = sub.case_text + (f"\nPatient ID: {sub.patient_id}" if sub.patient_id else "")
    try:
        plan = await create_plan(case_text, agents)
    except Exception as e:
        return {"status": "error", "plan": {}, "results": {}, "final_report": f"Planning failed: {e}", "audit_trail": a2a_client.get_audit_log(), "discovered_agents": [], "wiki_updates": []}

    a2a_client._log("planner", "plan_created", {"steps": len(plan.get("steps", [])), "summary": plan.get("case_summary", "")})

    try:
        results = await execute_plan(plan)
    except Exception as e:
        return {"status": "error", "plan": plan, "results": {}, "final_report": f"Execution failed: {e}", "audit_trail": a2a_client.get_audit_log(), "discovered_agents": [], "wiki_updates": []}

    final_report = ""
    results_summary = {}
    wiki_updates = []

    for agent_name, result in results.items():
        if not result or not hasattr(result, 'artifacts'):
            continue
        for artifact in result.artifacts:
            if artifact.metadata and artifact.metadata.get("type") == "wiki_update_notification":
                for p in artifact.parts:
                    if hasattr(p, "data"):
                        wiki_updates.append(p.data)
            for p in artifact.parts:
                if hasattr(p, "text"):
                    if "report" in agent_name.lower():
                        final_report = p.text
                    else:
                        results_summary[agent_name] = p.text[:500]
        if result.metadata:
            if result.metadata.get("wiki_updated"):
                wu = {"agent": agent_name, "patient_id": result.metadata.get("patient_id"), "new_patient": result.metadata.get("new_patient_created", False)}
                if wu not in wiki_updates:
                    wiki_updates.append(wu)
    # Persist results to wiki so repeat queries don't re-run everything
    persist_pid = sub.patient_id
    if not persist_pid:
        for wu in wiki_updates:
            if isinstance(wu, dict) and wu.get("patient_id"):
                persist_pid = wu["patient_id"]
                break
    if persist_pid:
        try:
            wiki_url = f"http://localhost:{os.getenv('PATIENT_WIKI_MCP_PORT', 9001)}"
            diagnosis_record = {
                "date": datetime.now().isoformat(),
                "type": "diagnosis_run",
                "source": "planner-orchestrator",
                "case_summary": plan.get("case_summary", ""),
            }
            if results_summary:
                diagnosis_record["agent_summaries"] = results_summary
            if final_report:
                diagnosis_record["final_report"] = final_report[:3000]
            for agent_name, result in results.items():
                if result and hasattr(result, 'artifacts'):
                    for artifact in result.artifacts:
                        if artifact.metadata and artifact.metadata.get("type") == "raw_risk_scores":
                            for p in artifact.parts:
                                if hasattr(p, "data"):
                                    diagnosis_record["risk_scores"] = p.data
            async with httpx.AsyncClient(timeout=15.0) as _client:
                await _client.post(f"{wiki_url}/mcp/tools/ingest_record",
                    json={"patient_id": persist_pid, "record": diagnosis_record})
            wiki_updates.append({"agent": "planner", "patient_id": persist_pid,
                                 "action": "stored_diagnosis_results"})
        except Exception as e:
            print(f"Wiki persist failed: {e}")

    if not final_report:
        final_report = "=== Combined Outputs ===\n\n"
        for n, r in results.items():
            if r and r.artifacts:
                final_report += f"\n--- {n} ---\n"
                for a in r.artifacts:
                    for p in a.parts:
                        if hasattr(p, "text"): final_report += p.text + "\n"

    a2a_client._log("planner", "execution_complete", {
        "agents_called": list(results.keys()),
        "success": sum(1 for r in results.values() if r and r.state == TaskState.COMPLETED),
        "wiki_updates": len(wiki_updates),
    })

    return {
        "status": "success", "plan": plan, "results": results_summary, "final_report": final_report,
        "audit_trail": a2a_client.get_audit_log(),
        "discovered_agents": [{"name": c.name, "url": c.url, "skills": [s.id for s in c.skills]} for c in agents.values()],
        "wiki_updates": wiki_updates,
    }


@app.get("/discover")
async def discover():
    agents = await discover_agents()
    return {"agents": [{"name": c.name, "url": c.url, "skills": [s.id for s in c.skills]} for c in agents.values()]}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "planner", "port": PLANNER_PORT}

if __name__ == "__main__":
    import uvicorn
    print(f"Planner on port {PLANNER_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PLANNER_PORT)