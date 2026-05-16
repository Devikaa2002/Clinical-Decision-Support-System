
# Clinical Decision Support System using A2A & MCP

An AI-powered multi-agent Clinical Decision Support System built using FastAPI, Groq Llama 3.3, Streamlit, A2A (Agent-to-Agent) Protocol, and MCP (Model Context Protocol).

The system dynamically plans and executes clinical workflows using multiple collaborating AI agents without hardcoded orchestration logic.

---

# Features

- Multi-Agent AI Architecture
- Dynamic LLM-Based Planning
- A2A Protocol Communication
- MCP Tool Integration
- Clinical Risk Assessment
- Automated Clinical Report Generation
- Persistent Patient Wiki
- Async Parallel Execution
- Full Audit Trail & Provenance
- Streamlit Dashboard UI

---

# System Architecture

## Agents
- History Agent
- Risk Assessment Agent
- Report Generation Agent

## MCP Servers
- Patient Wiki MCP
- Risk Guideline MCP

## Planner / Orchestrator
- Discovers agents dynamically
- Generates execution plan using LLM
- Executes tasks asynchronously

---

# Tech Stack

- Python 3.11
- FastAPI
- Streamlit
- Groq Llama 3.3 70B
- AsyncIO
- HTTPX
- Pydantic
- SQLite / JSON Storage
- A2A Protocol
- MCP Protocol

---

# Project Structure

```bash
agents/             # AI agents
common/             # Shared models and utilities
data/               # Patient and clinical rule data
mcp_servers/        # MCP tool servers
planner/            # Planner and orchestration logic
ui/                 # Streamlit frontend

run_all.py          # Starts all services
requirements.txt    # Python dependencies
README.md           # Project documentation
```

---

# Workflow

1. User submits clinical case
2. Planner discovers available agents
3. LLM generates execution plan dynamically
4. Agents communicate using A2A protocol
5. Agents retrieve data via MCP tools
6. Risk scores and summaries generated
7. Report Agent creates structured report
8. Audit trail and provenance stored

---

# Clinical Scoring Systems

- HEART Score
- CHA₂DS₂-VASc Score
- Wells DVT Score

---

# Demo Scenarios

## Existing Patient
Retrieves patient history and performs HEART score assessment.

## New Patient Auto-Registration
Automatically creates new patient records from free-text clinical input.

## Follow-up Visit
Deep merges updated vitals and lab results into persistent patient wiki.

---

# Installation

## Clone Repository

```bash
git clone https://github.com/Devikaa2002/Clinical-Decision-Support-System.git
cd Clinical-Decision-Support-System
```

---

# Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

## Windows

```bash
venv\Scripts\activate
```

## Linux / Mac

```bash
source venv/bin/activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Add Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_api_key_here
```

---

# Run Project

```bash
python run_all.py
```

---

# Streamlit Dashboard

Open browser:

```bash
http://localhost:8501
```

---

# API Services

| Service | Port |
|---|---|
| Planner | 8000 |
| History Agent | 8001 |
| Risk Agent | 8002 |
| Report Agent | 8003 |
| Patient Wiki MCP | 9001 |
| Risk Guideline MCP | 9002 |
| Streamlit UI | 8501 |

---

# Key Innovations

- Zero hardcoded workflow execution
- Runtime agent discovery
- Dynamic LLM orchestration
- Parallel async agent execution
- Standardized agent communication
- Persistent self-updating patient wiki

---

# Future Improvements

- Docker Deployment
- Kubernetes Scaling
- OAuth2 Authentication
- PostgreSQL Integration
- FHIR / HL7 Support
- Multi-LLM Provider Support
- Real EHR Integration

---

# Contributors

- Devika K
- Sai Sri Harine C

---

# License

This project is developed for academic and research purposes.
