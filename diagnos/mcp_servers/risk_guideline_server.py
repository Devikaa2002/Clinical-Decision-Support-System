"""
Clinical Risk Guideline MCP Tool Server
Exposes clinical risk scoring tools over HTTP.

Now handles cases where no specific scoring system matches
by doing a general clinical risk assessment using the LLM.

Runs on port 9002.
"""



import json
import os
from fastapi import FastAPI
from pydantic import BaseModel
from common.llm_client import chat_json

app = FastAPI(title="Risk Guideline MCP Server", version="2.0.0")
RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "clinical_rules.json")

def _load_rules() -> dict:
    if not os.path.exists(RULES_PATH):
        return {}
    with open(RULES_PATH) as f:
        return json.load(f)


@app.get("/mcp/tools")
async def list_tools():
    return {"tools": [
        {"name": "get_risk_rules", "description": "Get scoring algorithm for a condition", "inputSchema": {"type": "object", "properties": {"condition": {"type": "string"}}, "required": ["condition"]}},
        {"name": "evaluate_risk", "description": "Evaluate patient risk. ALWAYS returns assessment.", "inputSchema": {"type": "object", "properties": {"patient_data": {"type": "object"}, "condition": {"type": "string"}}, "required": ["patient_data", "condition"]}},
        {"name": "list_available_scores", "description": "List all scoring systems", "inputSchema": {"type": "object", "properties": {}}},
    ]}

class GetRiskRulesRequest(BaseModel):
    condition: str
class EvaluateRiskRequest(BaseModel):
    patient_data: dict
    condition: str

@app.post("/mcp/tools/get_risk_rules")
async def get_risk_rules(req: GetRiskRulesRequest):
    rules = _load_rules()
    condition_lower = req.condition.lower()
    matching = []
    for rule_id, rule in rules.items():
        applicable = [c.lower() for c in rule.get("applicable_conditions", [])]
        if any(cond in condition_lower for cond in applicable):
            matching.append({"rule_id": rule_id, **rule})
    return {"status": "success", "tool": "get_risk_rules", "result": matching}


@app.post("/mcp/tools/evaluate_risk")
async def evaluate_risk(req: EvaluateRiskRequest):
    rules = _load_rules()
    condition_lower = req.condition.lower()

    # Find ALL matching rules, not just the first
    matched_rules = []
    for rule_id, rule in rules.items():
        conditions = [c.lower() for c in rule.get("applicable_conditions", [])]
        if any(c in condition_lower or condition_lower in c for c in conditions):
            matched_rules.append({"rule_id": rule_id, **rule})

    if matched_rules:
        # Run ALL matched scoring systems
        all_scores = []
        highest_risk = "Low"
        risk_order = {"Low": 0, "Low-Moderate": 1, "Moderate": 2, "Moderate-High": 3, "High": 4}

        for rule in matched_rules:
            system_prompt = """You are a clinical decision support system.
CRITICAL: Use ONLY the patient data provided below. NEVER fabricate any information.
Use EXACT numbers. Do NOT change age, name, vitals, or add data not in the input.
If a field is missing, note "not documented" and score it 0. 

Respond with ONLY valid JSON:
{
    "scoring_system": "General Clinical Risk Assessment",
    "assessment_type": "general_assessment",
    "criteria_breakdown": [
        {"criterion": "Age-related risk", "patient_finding": "what you see in the ACTUAL data", "score": 0},
        {"criterion": "Vital signs", "patient_finding": "what you see in the ACTUAL data", "score": 0},
        {"criterion": "Comorbidity burden", "patient_finding": "what you see in the ACTUAL data", "score": 0},
        {"criterion": "Symptom severity", "patient_finding": "what you see in the ACTUAL data", "score": 0},
        {"criterion": "Lab abnormalities", "patient_finding": "what you see in the ACTUAL data", "score": 0},
        {"criterion": "Medication/treatment risk", "patient_finding": "what you see in the ACTUAL data", "score": 0}
    ],
    "total_score": 0,
    "risk_level": "Low/Moderate/High",
    "recommendation": "SPECIFIC actionable recommendations based on ACTUAL findings",
    "reasoning": "clinical reasoning using ONLY provided data",
    "differential_diagnosis": ["condition 1", "condition 2", "condition 3"]
}

Score each 0-2. Total 0-3=Low, 4-7=Moderate, 8-12=High.
Use the patient's ACTUAL data from below — every number must match the input exactly.

"""
            user_message = f"PATIENT DATA:\n{json.dumps(req.patient_data, indent=2)}\n\nSCORING ALGORITHM:\n{json.dumps(rule, indent=2)}\n\nApply this algorithm strictly using the patient's actual data."

            try:
                score_result = chat_json(system_prompt, user_message)
                all_scores.append(score_result)
                result_risk = score_result.get("risk_level", "Low")
                if risk_order.get(result_risk, 0) > risk_order.get(highest_risk, 0):
                    highest_risk = result_risk
            except Exception as e:
                all_scores.append({"scoring_system": rule["name"], "error": str(e)})

        scoring_names = [r["name"] for r in matched_rules]
        combined = {
            "scoring_systems_applied": scoring_names,
            "individual_scores": all_scores,
            "overall_risk_level": highest_risk,
            "assessment_type": "multi_score" if len(all_scores) > 1 else "specific_scoring",
        }
        return {"status": "success", "tool": "evaluate_risk", "scoring_system_used": ", ".join(scoring_names), "result": combined}

    else:
        # No matching rule - say so explicitly, do NOT fabricate a scoring system
        available = [{"name": r["name"], "conditions": r["applicable_conditions"]} for r in rules.values()]
        return {
            "status": "success",
            "tool": "evaluate_risk",
            "scoring_system_used": "none",
            "result": {
                "scoring_system": "none",
                "assessment_type": "no_applicable_scoring",
                "message": f"No validated scoring system in the MCP server matches condition: {req.condition}",
                "available_scoring_systems": available,
                "recommendation": "Clinical judgment required. Consider consulting specialist. Available scoring systems did not match the presenting condition.",
            }
        }


@app.post("/mcp/tools/list_available_scores")
async def list_available_scores():
    rules = _load_rules()
    return {"status": "success", "tool": "list_available_scores", "result": [
        {"rule_id": rid, "name": r["name"], "applicable_conditions": r["applicable_conditions"]} for rid, r in rules.items()
    ]}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "risk-guideline-mcp"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("RISK_GUIDELINE_MCP_PORT", 9002))
    print(f"Risk Guideline MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)