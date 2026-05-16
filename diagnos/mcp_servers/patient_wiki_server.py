"""
Patient Wiki MCP Tool Server
Data stored at: data/patients.json
Exposes patient data as MCP-style tools over HTTP.

Tools:
  - query_patient(patient_id) -> Full patient record
  - list_patients() -> Available patient IDs with summaries
  - ingest_record(patient_id, record) -> Add new record to patient history
  - create_patient(patient_data) -> Create a brand new patient record

Runs on port 9001.
"""




import json
import os
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Patient Wiki MCP Server", version="2.0.0")
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "patients.json")


def _load_patients() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH) as f:
        return json.load(f)

def _save_patients(data: dict):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)

def _get_next_patient_id(patients: dict) -> str:
    existing_ids = [int(pid[1:]) for pid in patients.keys() if pid.startswith("P") and pid[1:].isdigit()]
    return f"P{max(existing_ids, default=0) + 1:03d}"

# Fields where new values should ALWAYS overwrite old ones
OVERWRITE_FIELDS = {"vitals_latest", "lab_results_recent", "current_complaints"}

def _deep_merge(base: dict, updates: dict, force_overwrite: bool = False) -> dict:
    merged = base.copy()
    for key, value in updates.items():
        if value is None or value == "null":
            continue

        should_overwrite = force_overwrite or key in OVERWRITE_FIELDS

        if key in merged:
            if should_overwrite and not isinstance(value, dict):
                # For vitals, labs, complaints — new data replaces old
                merged[key] = value
            elif isinstance(merged[key], dict) and isinstance(value, dict):
                # For nested dicts like vitals_latest, overwrite individual values
                if key in OVERWRITE_FIELDS:
                    # Overwrite each sub-field that has a real value
                    for subkey, subval in value.items():
                        if subval is not None and subval != "null" and subval != "":
                            merged[key][subkey] = subval
                else:
                    merged[key] = _deep_merge(merged[key], value)
            elif isinstance(merged[key], list) and isinstance(value, list):
                if key in OVERWRITE_FIELDS:
                    # For complaints, replace entirely with new ones
                    merged[key] = value
                else:
                    # For history, allergies etc — append new items
                    existing = [json.dumps(i, sort_keys=True) if isinstance(i, dict) else str(i) for i in merged[key]]
                    for item in value:
                        s = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
                        if s not in existing:
                            merged[key].append(item)
            elif value != "" and value != 0 and value != "Unknown":
                merged[key] = value
        else:
            merged[key] = value
    return merged


@app.get("/mcp/tools")
async def list_tools():
    return {"tools": [
        {"name": "query_patient", "description": "Get patient by ID", "inputSchema": {"type": "object", "properties": {"patient_id": {"type": "string"}}, "required": ["patient_id"]}},
        {"name": "search_patient", "description": "Find patient by name", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "list_patients", "description": "List all patients", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "create_patient", "description": "Create new patient", "inputSchema": {"type": "object", "properties": {"patient_data": {"type": "object"}}, "required": ["patient_data"]}},
        {"name": "update_patient", "description": "Merge new data into patient", "inputSchema": {"type": "object", "properties": {"patient_id": {"type": "string"}, "updates": {"type": "object"}}, "required": ["patient_id", "updates"]}},
        {"name": "ingest_record", "description": "Add clinical note", "inputSchema": {"type": "object", "properties": {"patient_id": {"type": "string"}, "record": {"type": "object"}}, "required": ["patient_id", "record"]}},
        {"name": "get_storage_info", "description": "Show storage location", "inputSchema": {"type": "object", "properties": {}}},
    ]}


class QueryPatientRequest(BaseModel):
    patient_id: str
class SearchPatientRequest(BaseModel):
    name: str
class CreatePatientRequest(BaseModel):
    patient_data: dict
class UpdatePatientRequest(BaseModel):
    patient_id: str
    updates: dict
class IngestRecordRequest(BaseModel):
    patient_id: str
    record: dict


@app.post("/mcp/tools/query_patient")
async def query_patient(req: QueryPatientRequest):
    patients = _load_patients()
    patient = patients.get(req.patient_id)
    if patient:
        return {"status": "success", "tool": "query_patient", "result": patient}
    return {"status": "not_found", "tool": "query_patient", "error": f"Patient {req.patient_id} not found.", "available_patients": list(patients.keys())}


@app.post("/mcp/tools/search_patient")
async def search_patient(req: SearchPatientRequest):
    patients = _load_patients()
    name_lower = req.name.lower().strip()
    search_parts = [p for p in name_lower.split() if len(p) > 2]
    for pid, p in patients.items():
        pname = p.get("name", "").lower()
        if name_lower in pname or pname in name_lower:
            return {"status": "success", "tool": "search_patient", "result": {"patient_id": pid, "patient": p}}
        pname_parts = pname.split()
        for sp in search_parts:
            for pp in pname_parts:
                if sp in pp or pp in sp:
                    return {"status": "success", "tool": "search_patient", "result": {"patient_id": pid, "patient": p}}
    return {"status": "not_found", "tool": "search_patient", "error": f"No patient matching '{req.name}'."}


@app.post("/mcp/tools/list_patients")
async def list_patients():
    patients = _load_patients()
    return {"status": "success", "tool": "list_patients", "result": [
        {"patient_id": pid, "name": p.get("name", "?"), "age": p.get("age", "?"), "gender": p.get("gender", "?")} for pid, p in patients.items()
    ], "total_patients": len(patients)}


@app.post("/mcp/tools/create_patient")
async def create_patient(req: CreatePatientRequest):
    patients = _load_patients()
    new_id = _get_next_patient_id(patients)
    record = dict(req.patient_data)
    record["patient_id"] = new_id
    if not record.get("name") or record["name"] in ("null", None, ""):
        record["name"] = "Unknown Patient"
    if record.get("age") is None or record.get("age") == "null" or record.get("age") == "":
        record["age"] = "Unknown"
    if "clinical_notes" not in record:
        record["clinical_notes"] = []
    record["_created_at"] = datetime.now().isoformat()
    record["_last_updated"] = datetime.now().isoformat()
    patients[new_id] = record
    _save_patients(patients)
    print(f"\n=== NEW PATIENT: {new_id} | {record.get('name')} | Age: {record.get('age')} | Gender: {record.get('gender')} ===\n")
    return {"status": "success", "tool": "create_patient", "patient_id": new_id, "result": record, "storage_path": os.path.abspath(DATA_PATH), "wiki_updated": True}


@app.post("/mcp/tools/update_patient")
async def update_patient(req: UpdatePatientRequest):
    patients = _load_patients()
    if req.patient_id not in patients:
        return {"status": "error", "tool": "update_patient", "error": f"Patient {req.patient_id} not found."}
    patients[req.patient_id] = _deep_merge(patients[req.patient_id], req.updates)
    patients[req.patient_id]["_last_updated"] = datetime.now().isoformat()
    _save_patients(patients)
    return {"status": "success", "tool": "update_patient", "result": patients[req.patient_id], "wiki_updated": True}


@app.post("/mcp/tools/ingest_record")
async def ingest_record(req: IngestRecordRequest):
    patients = _load_patients()
    if req.patient_id not in patients:
        return {"status": "error", "tool": "ingest_record", "error": f"Patient {req.patient_id} not found."}
    if "clinical_notes" not in patients[req.patient_id]:
        patients[req.patient_id]["clinical_notes"] = []
    req.record["_ingested_at"] = datetime.now().isoformat()
    patients[req.patient_id]["clinical_notes"].append(req.record)
    patients[req.patient_id]["_last_updated"] = datetime.now().isoformat()
    _save_patients(patients)
    return {"status": "success", "tool": "ingest_record", "result": f"Note added to {req.patient_id}.", "wiki_updated": True}


@app.post("/mcp/tools/get_storage_info")
async def get_storage_info():
    patients = _load_patients()
    return {"status": "success", "tool": "get_storage_info", "result": {
        "storage_type": "JSON file (Karpathy LLM-Wiki pattern)",
        "file_path": os.path.abspath(DATA_PATH),
        "file_size_bytes": os.path.getsize(DATA_PATH) if os.path.exists(DATA_PATH) else 0,
        "total_patients": len(patients),
        "patient_names": {pid: p.get("name", "?") for pid, p in patients.items()},
    }}


@app.get("/health")
async def health():
    p = _load_patients()
    return {"status": "ok", "service": "patient-wiki-mcp", "total_patients": len(p), "storage_path": os.path.abspath(DATA_PATH)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PATIENT_WIKI_MCP_PORT", 9001))
    print(f"Patient Wiki MCP Server on port {port} | Data: {os.path.abspath(DATA_PATH)}")
    uvicorn.run(app, host="0.0.0.0", port=port)