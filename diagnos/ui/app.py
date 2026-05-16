"""
Clinical Decision Support UI v2
Dark theme compatible. Wiki updates, audit trail, storage info.
"""

import streamlit as st
import httpx
import json
import time

PLANNER_URL = "http://localhost:8000"
PATIENT_MCP_URL = "http://localhost:9001"

st.set_page_config(page_title="Clinical Decision Support - Philips PoC", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #0B5ED7 0%, #003087 100%); padding: 1.5rem 2rem; border-radius: 10px; color: white; margin-bottom: 1.5rem; }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #B8D4FF; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
    .agent-card { background-color: #0d2847 !important; border-left: 4px solid #3b82f6 !important; padding: 0.8rem 1rem !important; border-radius: 0 8px 8px 0; margin: 0.5rem 0; color: #e2e8f0 !important; }
    .agent-card strong { color: #60a5fa !important; }
    .audit-entry { font-family: monospace; font-size: 0.8rem; padding: 0.5rem 0.8rem; border-left: 3px solid #3b82f6; margin: 0.3rem 0; background-color: #111827 !important; border-radius: 0 4px 4px 0; color: #d1d5db !important; }
    .audit-entry strong { color: #60a5fa !important; }
    .audit-entry code { color: #4ade80 !important; background-color: #1a2332 !important; padding: 1px 5px; border-radius: 3px; }
    .wiki-update { background-color: #1a5d1a !important; border-left: 4px solid #4ade80 !important; padding: 0.8rem 1.2rem !important; border-radius: 0 8px 8px 0; margin: 0.8rem 0; font-size: 0.95rem; color: #ffffff !important; }
    .wiki-update strong { color: #4ade80 !important; }
    .storage-info { background-color: #1e3a5f !important; border-left: 4px solid #60a5fa !important; padding: 0.8rem 1.2rem !important; border-radius: 0 8px 8px 0; margin: 0.8rem 0; font-size: 0.9rem; color: #ffffff !important; }
    .storage-info strong { color: #93c5fd !important; }
    .storage-info code { background-color: #0f2744 !important; color: #60a5fa !important; padding: 2px 6px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="main-header"><h1>🏥 Clinical Decision Support System</h1><p>Multi-Agent Workflow using A2A &amp; MCP Protocols — Philips IT PoC</p></div>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 Agent Discovery")
    if st.button("Discover Agents", use_container_width=True):
        try:
            resp = httpx.get(f"{PLANNER_URL}/discover", timeout=10.0)
            if resp.status_code == 200:
                st.session_state["discovered_agents"] = resp.json().get("agents", [])
                st.success(f"Found {len(st.session_state['discovered_agents'])} agents")
        except Exception as e:
            st.error(f"Cannot reach Planner: {e}")

    for agent in st.session_state.get("discovered_agents", []):
        st.markdown(f"""<div class="agent-card"><strong>🤖 {agent['name']}</strong><br/><span style="color:#93c5fd;">🔗 {agent['url']}</span><br/><span style="color:#a5b4fc;">🛠️ {', '.join(agent['skills'])}</span></div>""", unsafe_allow_html=True)

    st.divider()
    st.header("💾 Data Storage")
    if st.button("Show Storage Info", use_container_width=True):
        try:
            resp = httpx.post(f"{PATIENT_MCP_URL}/mcp/tools/get_storage_info", json={}, timeout=5.0)
            if resp.status_code == 200:
                info = resp.json().get("result", {})
                names = info.get("patient_names", {})
                names_str = "<br/>".join(f"&nbsp;&nbsp;{k}: {v}" for k, v in names.items())
                st.markdown(f"""<div class="storage-info"><strong>📂 Type:</strong> {info.get('storage_type','N/A')}<br/><strong>📄 Path:</strong> <code>{info.get('file_path','N/A')}</code><br/><strong>📊 Total Patients:</strong> {info.get('total_patients',0)}<br/><strong>🆔 Records:</strong><br/>{names_str}</div>""", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Cannot reach Wiki: {e}")

    st.divider()
    st.markdown("""**Protocol Stack:** A2A + MCP + Llama 3.3 70B (Groq)\n\n**Flow:** Discover → Plan → Execute → Report""")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Submit Clinical Case")
    examples = {
        "Select an example...": "",
        "🫀 Chest Pain — P001 (Rajesh Kumar)": "58-year-old male patient P001, Rajesh Kumar, presents with chest tightness on exertion for 2 weeks, occasional breathlessness climbing stairs. Has history of Type 2 Diabetes, Hypertension, and Hyperlipidemia. Father had MI at 55. Please assess cardiac risk and provide clinical recommendation.",
        "💓 Heart Failure — P002 (Lakshmi Devi)": "72-year-old female patient P002, Lakshmi Devi, with known Atrial Fibrillation and CHF NYHA II, presenting with increasing ankle swelling for 1 week, worsening breathlessness at rest, irregular palpitations, and decreased appetite. On Apixaban, Furosemide, Carvedilol. Allergic to Aspirin. Please evaluate stroke risk and overall clinical status.",
        "✅ Routine Checkup — P003 (Arjun Mehta)": "34-year-old male patient P003, Arjun Mehta, here for routine annual health checkup. Reports occasional mild headaches. No significant medical history. All recent labs normal. Please review and provide recommendations.",
    }

    selected = st.selectbox("Quick-load an example:", list(examples.keys()))
    case_text = st.text_area("Clinical Case Description:", value=examples.get(selected, ""), height=200,
        placeholder="Describe the case. Include patient name, age, gender, symptoms, vitals, labs, medications, allergies...")
    patient_id = st.text_input("Patient ID (optional — new patients are auto-registered):", placeholder="e.g., P001 (leave blank for new patients)")
    submit = st.button("🚀 Submit Case", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 Execution Status")
    status_container = st.container()

if submit and case_text.strip():
    with status_container:
        progress = st.progress(0, text="Discovering agents...")
        try:
            start_time = time.time()
            progress.progress(10, text="Sending case to Planner...")
            resp = httpx.post(f"{PLANNER_URL}/submit-case",
                json={"case_text": case_text, "patient_id": patient_id or None}, timeout=180.0)
            elapsed = time.time() - start_time
            progress.progress(100, text=f"Complete in {elapsed:.1f}s")

            if resp.status_code == 200:
                result = resp.json()
                if result["status"] == "success":
                    st.success(f"✅ Completed in {elapsed:.1f} seconds")
                else:
                    st.error("❌ Error occurred")

                wiki_updates = result.get("wiki_updates", [])
                for wu in wiki_updates:
                    if isinstance(wu, dict):
                        msg = wu.get("wiki_update", "")
                        pid = wu.get("patient_id", "")
                        if not msg:
                            if wu.get("new_patient") or wu.get("new_patient_created"):
                                msg = f"🆕 New patient <strong>{pid}</strong> created and stored"
                            elif pid:
                                msg = f"📝 Patient <strong>{pid}</strong> wiki updated"
                            else:
                                msg = "📝 Wiki updated"
                        st.markdown(f'<div class="wiki-update"><strong>📋 Wiki Update:</strong> {msg}<br/><span style="color:#86efac;font-size:0.85rem;">💾 Stored at: data/patients.json</span></div>', unsafe_allow_html=True)

                tab1, tab2, tab3, tab4 = st.tabs(["📋 Final Report", "🗺️ Execution Plan", "🔍 Audit Trail", "📦 Raw Data"])

                with tab1:
                    st.markdown("### Clinical Recommendation Report")
                    st.markdown(result.get("final_report", "No report generated."))

                with tab2:
                    st.markdown("### Dynamic Execution Plan")
                    plan = result.get("plan", {})
                    if plan:
                        st.info(f"**Plan Summary:** {plan.get('case_summary', 'N/A')}")
                        st.markdown(f"**Execution Order:** {plan.get('execution_order', 'N/A')}")
                        for i, step in enumerate(plan.get("steps", []), 1):
                            with st.expander(f"Step {i}: {step.get('agent_name', '?')} (Group {step.get('parallel_group', '?')})"):
                                st.write(f"**Task:** {step.get('task', 'N/A')}")
                                st.write(f"**Rationale:** {step.get('rationale', 'N/A')}")
                                st.write(f"**URL:** `{step.get('agent_url', 'N/A')}`")

                with tab3:
                    st.markdown("### Audit Trail / Provenance")
                    audit = result.get("audit_trail", [])
                    if audit:
                        icons = {"agent_card_fetched": "🔍", "agent_card_failed": "⚠️", "discovery_complete": "✅",
                                 "plan_created": "📋", "task_sent": "📤", "task_completed": "✅",
                                 "task_failed": "❌", "task_error": "💥", "execution_complete": "🏁"}
                        for entry in audit:
                            if isinstance(entry, dict):
                                action = entry.get("action", "unknown")
                                icon = icons.get(action, "📌")
                                ts = entry.get("timestamp", "")[:19]
                                agent = entry.get("agent", "?")
                                details = entry.get("details", {})
                                detail_parts = []
                                if isinstance(details, dict):
                                    for k, v in details.items():
                                        if isinstance(v, list):
                                            detail_parts.append(f"{k}: {', '.join(str(x) for x in v)}")
                                        elif isinstance(v, str) and len(v) > 60:
                                            detail_parts.append(f"{k}: {v[:60]}...")
                                        else:
                                            detail_parts.append(f"{k}: {v}")
                                detail_str = " | ".join(detail_parts) if detail_parts else ""
                                if detail_str:
                                    detail_str = f" | {detail_str}"
                                st.markdown(f'<div class="audit-entry">{icon} <strong>[{ts}]</strong> <strong>{agent}</strong> → <code>{action}</code><span style="color:#9ca3af;">{detail_str}</span></div>', unsafe_allow_html=True)
                    else:
                        st.warning("No audit entries recorded.")

                with tab4:
                    st.json(result)

                agents = result.get("discovered_agents", [])
                if agents:
                    st.session_state["discovered_agents"] = agents
            else:
                st.error(f"Server returned {resp.status_code}: {resp.text}")
        except httpx.TimeoutException:
            st.error("Request timed out. Try again.")
        except httpx.ConnectError:
            st.error("Cannot connect to Planner. Make sure all services are running.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
elif submit:
    st.warning("Please enter a clinical case description.")

st.divider()
st.markdown("""<div style="text-align:center;color:#888;font-size:0.8rem;">Philips IT PoC — A2A + MCP + Llama 3.3 70B (Groq) | April 2026<br/><em>⚠️ For demonstration purposes only. Not for clinical use.</em></div>""", unsafe_allow_html=True)