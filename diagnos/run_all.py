"""
Run All Services
Launches all MCP servers, agents, planner, and UI in the correct order.

Usage:
    python run_all.py          # Start everything
    python run_all.py --no-ui  # Start backend only
"""

import subprocess
import sys
import time
import os
import signal
from dotenv import load_dotenv

load_dotenv()

# First, seed the data
print("=" * 60)
print("STEP 0: Seeding data...")
print("=" * 60)
subprocess.run([sys.executable, "seed_data.py"], check=True)
print()

# Services to launch in order
SERVICES = [
    {
        "name": "Patient Wiki MCP Server",
        "cmd": [sys.executable, "-m", "mcp_servers.patient_wiki_server"],
        "port": int(os.getenv("PATIENT_WIKI_MCP_PORT", 9001)),
    },
    {
        "name": "Risk Guideline MCP Server",
        "cmd": [sys.executable, "-m", "mcp_servers.risk_guideline_server"],
        "port": int(os.getenv("RISK_GUIDELINE_MCP_PORT", 9002)),
    },
    {
        "name": "History Agent",
        "cmd": [sys.executable, "-m", "agents.history_agent"],
        "port": int(os.getenv("HISTORY_AGENT_PORT", 8001)),
    },
    {
        "name": "Risk Agent",
        "cmd": [sys.executable, "-m", "agents.risk_agent"],
        "port": int(os.getenv("RISK_AGENT_PORT", 8002)),
    },
    {
        "name": "Report Agent",
        "cmd": [sys.executable, "-m", "agents.report_agent"],
        "port": int(os.getenv("REPORT_AGENT_PORT", 8003)),
    },
    {
        "name": "Planner / Orchestrator",
        "cmd": [sys.executable, "-m", "planner.orchestrator"],
        "port": int(os.getenv("PLANNER_PORT", 8000)),
    },
]

processes = []


def cleanup(signum=None, frame=None):
    print("\n\nShutting down all services...")
    for proc, svc in reversed(processes):
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  Stopped {svc['name']}")
        except:
            proc.kill()
            print(f"  Killed {svc['name']}")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def start_services():
    print("=" * 60)
    print("STEP 1: Starting backend services...")
    print("=" * 60)

    for svc in SERVICES:
        print(f"\n  Starting {svc['name']} on port {svc['port']}...")
        proc = subprocess.Popen(
            svc["cmd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        processes.append((proc, svc))
        time.sleep(1.5)

    print("\nWaiting for services to initialize...")
    time.sleep(3)

    print("\n" + "=" * 60)
    print("All backend services running!")
    print("=" * 60)
    print("\nService endpoints:")
    for svc in SERVICES:
        print(f"   {svc['name']:30s} -> http://localhost:{svc['port']}")

    print(f"\nPlanner API:     http://localhost:{os.getenv('PLANNER_PORT', 8000)}/submit-case")
    print(f"Agent Discovery: http://localhost:{os.getenv('PLANNER_PORT', 8000)}/discover")


def start_ui():
    print("\n" + "=" * 60)
    print("STEP 2: Starting Streamlit UI...")
    print("=" * 60)
    print("   Open: http://localhost:8501")
    print("=" * 60)

    ui_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "ui/app.py",
         "--server.port=8501", "--server.headless=true"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    processes.append((ui_proc, {"name": "Streamlit UI"}))


if __name__ == "__main__":
    start_services()

    if "--no-ui" not in sys.argv:
        start_ui()

    print("\n\n" + "=" * 60)
    print("SYSTEM READY - Press Ctrl+C to stop all services")
    print("=" * 60)

    try:
        while True:
            for proc, svc in processes:
                if proc.poll() is not None:
                    print(f"\n  WARNING: {svc['name']} exited with code {proc.returncode}")
                    stderr = proc.stderr.read().decode() if proc.stderr else ""
                    if stderr:
                        print(f"   Error: {stderr[:500]}")
            time.sleep(5)
    except KeyboardInterrupt:
        cleanup()