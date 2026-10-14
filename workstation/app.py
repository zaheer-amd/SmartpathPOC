"""
SmartPath — US Commercial Claims Adjudication Workstation
Runtime Training Simulation Interface (Streamlit)

Communicates strictly over HTTP with:
- Akka Typed Orchestrator (Port 8080): Session lifecycle, actor dispatch, SQLite audit ledger
- FastAPI AI Gateway (Port 8000): Policy RAG retrieval, Judge & Mentor agent evaluation
"""

import sys
import json
from pathlib import Path
import streamlit as st

# Ensure workstation directory is in sys.path
WORKSTATION_DIR = str(Path(__file__).resolve().parent)
if WORKSTATION_DIR not in sys.path:
    sys.path.insert(0, WORKSTATION_DIR)

from config import SCENARIOS_FILE
from ui.sidebar import render_sidebar
from ui.claim_form import render_claim_form
from ui.trainee_inputs import render_trainee_inputs
from ui.mentor_chat import render_mentor_chat
from ui.telemetry_dashboard import render_telemetry_dashboard


# --- 1. SETUP & PAGE CONFIGURATION ---
st.set_page_config(
    page_title="SmartPath - US Claims Adjudication Workstation",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Tighter padding for screen-recording density */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    
    /* Smaller text input labels and fields */
    div.stTextInput > label { font-size: 0.8rem !important; margin-bottom: 0.1rem; }
    div.stTextInput > div > div > input { 
        font-size: 0.82rem !important; 
        padding: 0.3rem 0.5rem !important;
        height: 2rem !important;
    }
    
    /* Reduce expander spacing */
    div[data-testid="stExpander"] { margin-bottom: 0.3rem; }
    
    /* Tighter subheader */
    h3 { margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
    h4 { margin-top: 0.3rem !important; margin-bottom: 0.2rem !important; }
    
    /* Chat input positioning */
    div[data-testid="stChatInput"] { margin-top: 0.5rem; }
    
    /* Scale down markdown headings inside the policy expander */
    div[data-testid="stExpander"] h1 { font-size: 1.2rem !important; padding-bottom: 0.2rem; margin-bottom: 0.2rem; }
    div[data-testid="stExpander"] h2 { font-size: 1.0rem !important; padding-bottom: 0.2rem; margin-bottom: 0.2rem; }
    div[data-testid="stExpander"] p, div[data-testid="stExpander"] li { font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)

st.title("SmartPath: Adjudication Simulator")
st.caption("GLH Enterprise US Commercial Claims Engine • Workstation Interface • Manual Adjudication Queue")


# --- 2. LOAD SCENARIOS DATA ---
with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
    SCENARIOS = json.load(f)


# --- 3. SIDEBAR CONTROLS & SESSION CONFIG ---
api_key, selected_model, current_scenario, plan_class = render_sidebar(SCENARIOS)


# --- 4. STATUS BAR ---
st.markdown(
    f"""
    <div style="background-color: #0f172a; color: #f8fafc; padding: 10px 16px; border-radius: 8px; font-family: monospace; font-size: 0.85rem; margin-bottom: 15px; border-left: 5px solid #0284c7; display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
        <span><strong>SYS:</strong> GLH-ADJUDICATOR-US v9.2.0</span>
        <span><strong>QUEUE:</strong> NON-AUTO (US-COMMERCIAL)</span>
        <span><strong>PLAN:</strong> {plan_class}</span>
        <span><strong>CLAIM ID:</strong> {current_scenario['provider']['claim_ref']}</span>
        <span><strong>AI TELEMETRY:</strong> ACTIVE (5-LAYER AUDIT)</span>
        <span><strong>STATUS:</strong> PENDING ADJUDICATION</span>
    </div>
    """,
    unsafe_allow_html=True
)


# --- 5. TABS: WORKSTATION & TRANSPARENCY DASHBOARD ---
tab_workstation, tab_transparency = st.tabs([
    "🖥️ Adjudication Workstation",
    "🧠 AI Transparency & Token Telemetry Walkthrough"
])

with tab_workstation:
    col1, col2 = st.columns([3, 2])

    with col1:
        render_claim_form(current_scenario)
        render_trainee_inputs(current_scenario, plan_class, api_key, selected_model)

    with col2:
        render_mentor_chat(current_scenario, plan_class, api_key, selected_model)

with tab_transparency:
    render_telemetry_dashboard()