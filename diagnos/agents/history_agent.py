"""
History Agent (A2A-compliant)
Now searches patients by name if no ID is given.
Creates new patients only when truly not found.
Always returns complete data.

Runs on port 8001.
"""



import os, json, re, httpx
from fastapi import FastAPI
from common.a2a_models import (
    AgentCard, AgentSkill, TaskSendRequest, TaskSendResponse,
    TaskState, Artifact, TextPart, DataPart,
)
from common.llm_client import chat, chat_json
from datetime import datetime

app = FastAPI(title="History Agent", version="2.0.0")
AGENT_PORT = int(os.getenv("HISTORY_AGENT_PORT", 8001))
PATIENT_MCP_URL = f"http://localhost:{os.getenv('PATIENT_WIKI_MCP_PORT', 9001)}"

AGENT_CARD = AgentCard(
    name="History Agent",
    description="Retrieves and summarizes patient medical history. Searches by ID or name. Creates new patients from case descriptions with full data extraction. Always produces complete clinical summaries.",
    url=f"http://localhost:{AGENT_PORT}",
    version="2.0.0",
    skills=[AgentSkill(
        id="patient_history_summary",
        name="Patient History Summary",
        description="Fetches or creates patient records and produces clinical summaries.",
        tags=["clinical", "history", "patient", "create-patient"],
        examples=["Get history for patient P001", "Summarize Rohan Verma's record", "New patient with fever and low platelets"],
    )],
)

@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD.model_dump()


@app.post("/a2a/tasks/send")
async def handle_task(request: TaskSendRequest) -> TaskSendResponse:
    task_text = "".join(p.text for p in request.message.parts if hasattr(p, "text"))

    patient_id = None
    patient_data = None
    wiki_updated = False
    created_new = False

    # STEP 1: Find by ID
    pid = _extract_pid(task_text)
    if pid:
        patient_data = await _fetch(pid)
        if patient_data:
            patient_id = pid

    # STEP 2: Find by Name
    if not patient_data:
        name = _extract_name(task_text)
        if name:
            found = await _search_name(name)
            if found:
                patient_id = found["patient_id"]
                patient_data = found["patient"]

    # STEP 3: Create new patient
    if not patient_data:
        patient_data, patient_id, created_new = await _create_from_case(task_text)
        wiki_updated = True

    if not patient_data:
        return _fail(request.id, "Could not find or create patient record.")

    # STEP 4: Update wiki with follow-up data (runs for BOTH new and existing patients)
    if patient_id and patient_id != "UNKNOWN":
        try:
            new_data = await _extract_updates(task_text)
            if new_data:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    await client.post(f"{PATIENT_MCP_URL}/mcp/tools/update_patient",
                        json={"patient_id": patient_id, "updates": new_data})
                    wiki_updated = True
                patient_data = await _fetch(patient_id) or patient_data
        except:
            pass
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{PATIENT_MCP_URL}/mcp/tools/ingest_record",
                    json={"patient_id": patient_id, "record": {
                        "date": datetime.now().isoformat(), "type": "follow_up",
                        "note": task_text[:800], "source": "history-agent",
                    }})
                wiki_updated = True
        except:
            pass

    # STEP 5: Generate summary
    system_prompt = """You are a clinical documentation specialist creating a patient summary.
    
STRICT RULES — THESE ARE NON-NEGOTIABLE:

1. Use ONLY data from the patient record and case text provided below.
2. NEVER invent or fabricate any patient information.
3. If the patient's name is "Alice" do NOT add a last name like "Smith" or "Johnson".
4. Use the EXACT age from the data. If it says 28, write 28 — not 32 or any other number.
5. Use EXACT vital sign numbers. BP 155/60 stays 155/60. SpO2 98% stays 98%.
6. Do NOT add conditions, travel history, smoking status, family history, or any other details that are not explicitly in the data.
7. For any field not present in the data, write "Not documented" — do NOT make up values.
8. Allergies: report EXACTLY what is stated. "allergic to nuts" means allergic to nuts — do not change this.

Sections:
1. PATIENT OVERVIEW (ONLY name, age, gender from data)
2. CURRENT PRESENTATION (ONLY complaints and vitals from data — exact numbers)
3. MEDICAL HISTORY (ONLY conditions explicitly mentioned)
4. ALLERGIES (EXACTLY as stated in data)
5. LAB FINDINGS (ONLY values from data — if none, say "No labs reported")
6. FAMILY & SOCIAL HISTORY (ONLY if explicitly mentioned)
7. RECENT UPDATES (from clinical notes if any)
8. KEY CLINICAL FLAGS (based ONLY on actual data)

BEFORE WRITING EACH FACT: Ask yourself "Is this exact information in the input?" If NO, do not write it."""
    user_msg = f"Patient record:\n{json.dumps(patient_data, indent=2)}\n\nCurrent case:\n{task_text}"
    try:
        summary = chat(system_prompt, user_msg)
    except:
        summary = f"Patient: {patient_data.get('name')}, Age: {patient_data.get('age')}, Gender: {patient_data.get('gender')}\n\n{json.dumps(patient_data, indent=2)}"

    tools_used = ["create_patient"] if created_new else ["query_patient"]
    if wiki_updated and not created_new:
        tools_used.extend(["update_patient", "ingest_record"])

    artifacts = [Artifact(type="text", parts=[TextPart(text=summary)], metadata={
        "source_agent": "history-agent", "patient_id": patient_id, "mcp_tools_used": tools_used,
        "wiki_updated": wiki_updated, "new_patient_created": created_new, "timestamp": datetime.now().isoformat(),
    })]

    if wiki_updated:
        msg = f"New patient {patient_id} ({patient_data.get('name')}) created." if created_new else f"Patient {patient_id} ({patient_data.get('name')}) wiki updated with follow-up data."
        artifacts.append(Artifact(type="data", parts=[DataPart(data={
            "wiki_update": msg, "patient_id": patient_id, "new_patient": created_new, "storage_location": "data/patients.json",
        })], metadata={"type": "wiki_update_notification"}))

    return TaskSendResponse(id=request.id, state=TaskState.COMPLETED, artifacts=artifacts,
        metadata={"agent": "history-agent", "patient_id": patient_id, "patient_name": patient_data.get("name"),
                   "wiki_updated": wiki_updated, "new_patient_created": created_new})


async def _fetch(pid: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(f"{PATIENT_MCP_URL}/mcp/tools/query_patient", json={"patient_id": pid})
            d = r.json()
            if d.get("status") == "success":
                return d["result"]
    except:
        pass
    return None

async def _search_name(name: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(f"{PATIENT_MCP_URL}/mcp/tools/search_patient", json={"name": name})
            d = r.json()
            if d.get("status") == "success":
                return d["result"]
    except:
        pass
    return None

async def _extract_updates(case_text: str) -> dict | None:
    """Extract new vitals, labs, complaints from follow-up text. These OVERWRITE old values in the wiki."""
    try:
        return chat_json(
            """You are a medical data extractor. Extract ALL new/updated clinical values from this text.
            CRITICAL: NEVER add any information to the json file or anywhere if its not in the data provided or in the file. Leave the fields empty if its not given in the data for new patients.


Return ONLY valid JSON with these fields (include ONLY fields that have new data mentioned):
{
    "vitals_latest": {
        "blood_pressure_systolic": 160,
        "blood_pressure_diastolic": 90,
        "heart_rate": 100,
        "spo2": 92,
        "temperature_fahrenheit": 101,
        "temperature_celsius": 38.3,
        "respiratory_rate": 22,
        "recorded_at": "2026-04-12T10:00:00"
    },
    "lab_results_recent": {
        "Platelet_Count": {"value": 85000, "unit": "/uL", "reference": "150000-400000"}
    },
    "current_complaints": ["complaint 1", "complaint 2"]
}

CRITICAL RULES:
1. Extract EVERY vital sign mentioned: BP, heart rate, SpO2, temperature, respiratory rate.
2. "BP 160/90" means blood_pressure_systolic: 160 and blood_pressure_diastolic: 90.
3. "SpO2 92%" means spo2: 92.
4. Extract ALL lab values with their exact numbers.
5. List ALL current symptoms as current_complaints.
6. These values will OVERWRITE old values in the patient record, so accuracy is critical.
7. If a value is not mentioned in the text, do NOT include it.
8. Return {} if no clinical values are found.""",
            case_text
        )
    except:
        return None

async def _create_from_case(case_text: str) -> tuple:
    prompt = """You are a medical data extraction expert. Extract ALL patient information.
Return ONLY valid JSON:
{
    "name": "Full Name",
    "age": 35,
    "gender": "Male/Female",
    "blood_group": "Unknown",
    "demographics": {},
    "vitals_latest": {
        "temperature_fahrenheit": null, "temperature_celsius": null,
        "blood_pressure_systolic": null, "blood_pressure_diastolic": null,
        "heart_rate": null, "spo2": null, "respiratory_rate": null
    },
    "medical_history": [],
    "allergies": [],
    "surgical_history": [],
    "family_history": [],
    "lab_results_recent": {},
    "current_complaints": [],
    "travel_history": null,
    "social_history": null
}

RULES:
1. AGE: Extract the EXACT number. "35-year-old" means age is 35. NEVER use 0.
2. NAME: Extract the exact full name from the text.
3. GENDER: "male" = "Male", "female" = "Female".
4. VITALS: Extract ALL numbers. "102 F" means temperature_fahrenheit: 102. "110/70" means systolic: 110, diastolic: 70.
5. LABS: Use format {"Test": {"value": 120000, "unit": "/uL", "reference": "150000-400000"}}.
6. COMPLAINTS: List EVERY symptom mentioned.
7. ALLERGIES: If "no known drug allergies" or "NKDA" then use empty list [].
8. Extract EVERYTHING. Do not skip any detail."""

    try:
        data = chat_json(prompt, case_text)
    except:
        data = {"name": "Unknown", "age": "Unknown", "current_complaints": [case_text[:200]]}

    # Hard validation with regex fallbacks
    if data.get("age") in (0, None, "null", "", "Unknown"):
        m = re.search(r'(\d{1,3})[-\s]?year[-\s]?old', case_text.lower())
        if m:
            data["age"] = int(m.group(1))

    if not data.get("gender") or data["gender"] in ("Unknown", "null"):
        tl = case_text.lower()
        if any(x in tl for x in [" male ", "male patient", "-year-old male", " man ", " boy "]):
            data["gender"] = "Male"
        elif any(x in tl for x in [" female ", "female patient", "-year-old female", " woman ", " girl "]):
            data["gender"] = "Female"

    if not data.get("name") or data["name"] in ("Unknown", "Unknown Patient", "null"):
        for pat in [r'named\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:presents|returns|comes|reports)']:
            m = re.search(pat, case_text)
            if m:
                data["name"] = m.group(1)
                break

    print(f"\n--- Extracted: {data.get('name')} | Age: {data.get('age')} | Gender: {data.get('gender')} ---\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(f"{PATIENT_MCP_URL}/mcp/tools/create_patient", json={"patient_data": data})
            d = r.json()
            if d.get("status") == "success":
                data["patient_id"] = d["patient_id"]
                return data, d["patient_id"], True
    except:
        pass
    return data, "UNKNOWN", False


def _fail(tid, msg):
    return TaskSendResponse(id=tid, state=TaskState.FAILED,
        artifacts=[Artifact(type="text", parts=[TextPart(text=msg)])],
        metadata={"agent": "history-agent", "error": msg})

def _extract_pid(text):
    m = re.search(r'\b(P\d{3})\b', text.upper())
    return m.group(1) if m else None

def _extract_name(text):
    for pat in [r'named\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', r'patient\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:presents|returns|comes|reports)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(?:a\s+)?\d{1,3}[-\s]?year']:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "history-agent", "port": AGENT_PORT}

if __name__ == "__main__":
    import uvicorn
    print(f"History Agent on port {AGENT_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)