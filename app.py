import streamlit as st
import google.generativeai as genai
import json
import requests
import os

# Load scenarios
with open("data/scenarios.json", "r") as f:
    SCENARIOS = json.load(f)

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="SmartPath - US Claims Adjudication Workstation", layout="wide")

st.title("SmartPath: Adjudication Simulator")
st.caption("GLH Enterprise US Commercial Claims Engine • Workstation Interface • Manual Adjudication Queue")

# Ask for the API key directly in the UI!
st.sidebar.header("⚙️ System & Session Config")
api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")

if not api_key:
    st.warning("👈 Please enter your free Gemini API key in the sidebar to start the simulation.")
    st.stop()

# Configure Gemini
genai.configure(api_key=api_key)

try:
    available_models = [m.name.replace("models/", "") for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
    st.sidebar.success("API Key accepted!")
    selected_model = st.sidebar.selectbox("Select Model:", available_models)
except Exception as e:
    st.sidebar.error(f"Error checking API key: {e}")
    selected_model = 'gemini-3.6-flash'

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "telemetry_logs" not in st.session_state:
    st.session_state.telemetry_logs = []
if "current_scenario_index" not in st.session_state:
    st.session_state.current_scenario_index = 0

# Sidebar Queue Controls
st.sidebar.markdown("---")
st.sidebar.header("🔄 Queue Management")
if st.sidebar.button("⏭️ Next Claim in Queue", use_container_width=True, type="primary"):
    st.session_state.current_scenario_index = (st.session_state.current_scenario_index + 1) % len(SCENARIOS)
    st.session_state.chat_history = [] # clear chat for new claim
    st.rerun()

current_scenario = SCENARIOS[st.session_state.current_scenario_index]
plan_class = current_scenario["plan_class"]

# Sidebar Legacy Workstation Session Details
with st.sidebar.expander("🖥️ Active Terminal Session", expanded=False):
    st.text(f"Station ID: TERM-WS09-AUSTIN\nOperator: OPR-5524 (Trainee - Level 1)\nEnvironment: PROD-US-CENTRAL (Austin DC)\nWorkpool: US-COMM-CSD-MANUAL-02\nActive Plan Class: {plan_class}")

# --- 2. LEGACY WORKSTATION HEADER STATUS BAR ---
st.markdown(
    f"""
    <div style="background-color: #0f172a; color: #f8fafc; padding: 10px 16px; border-radius: 8px; font-family: monospace; font-size: 0.85rem; margin-bottom: 15px; border-left: 5px solid #0284c7; display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
        <span><strong>SYS:</strong> GLH-ADJUDICATOR-US v9.2.0</span>
        <span><strong>QUEUE:</strong> NON-AUTO (US-COMMERCIAL)</span>
        <span><strong>PLAN:</strong> {plan_class}</span>
        <span><strong>CLAIM ID:</strong> {current_scenario['provider']['claim_ref']}</span>
        <span><strong>STATUS:</strong> PENDING ADJUDICATION</span>
    </div>
    """,
    unsafe_allow_html=True
)

# --- 3. LAYOUT: TABS ---
tab_workstation, tab_telemetry = st.tabs(["🖥️ Adjudication Workstation", "📊 Backend Telemetry & Logs"])

with tab_workstation:
    col1, col2 = st.columns([1.6, 1]) 

    # --- 4. LEFT COLUMN: THE CLAIM FORM & LEGACY PANELS ---
    with col1:
        st.subheader("📋 Claim Adjudication Form (GLH Workstation - US Edition)")

        # 1. Member & Group Information
        with st.expander("👤 Group & Subscriber Information (Eligibility Ledger)", expanded=True):
            m = current_scenario["member"]
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.text_input("Employer / Group Sponsor", value=m["employer"], disabled=True)
                st.text_input("Subscriber ID / SSN Hash", value=m["subscriber_id"], disabled=True)
                st.text_input("Plan Class & Network", value=m["plan_network"], disabled=True)
                st.text_input("State / Tax Jurisdiction", value=m["state_tax"], disabled=True)
            with m_col2:
                st.text_input("Subscriber / Patient Name", value=m["name"], disabled=True)
                st.text_input("Dep Sequence & Relation", value=m["relation"], disabled=True)
                st.text_input("Date of Birth & Gender", value=m["dob_gender"], disabled=True)
                st.text_input("Coordination of Benefits (COB)", value=m["cob"], disabled=True)
            with m_col3:
                st.text_input("Coverage Status", value=m["status"], disabled=True)
                st.text_input("Effective / Expiration Date", value=m["effective_dates"], disabled=True)
                st.text_input("Division & Cost Center", value=m["division"], disabled=True)
                st.text_input("Annual Deductible Accumulator", value=m["deductible"], disabled=True)

        # 2. Claim Line & Provider Details
        with st.expander("📄 Claim Line & Provider Details (Scanned Invoice Data)", expanded=True):
            p = current_scenario["provider"]
            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                st.text_input("Claim Reference ID", value=p["claim_ref"], disabled=True)
                st.text_input("Provider Facility & Name", value=p["facility"], disabled=True)
                st.text_input("Provider NPI & State License", value=p["license"], disabled=True)
                st.text_input("Provider Taxonomy Code", value=p["taxonomy"], disabled=True)
            with c_col2:
                st.text_input("Date of Service (DOS)", value=p["dos"], disabled=True)
                st.text_input("Receipt / Invoice No", value=p["invoice_no"], disabled=True)
                st.text_input("Billing Code (CPT / HCPCS)", value=p["cpt"], disabled=True)
                st.text_input("Diagnosis Code (ICD-10-CM)", value=p["icd"], disabled=True)
            with c_col3:
                st.text_input("Total Receipt / Billed ($)", value=f"${p['billed']:.2f} USD", disabled=True)
                st.text_input("Benefit Grid Rule", value=p["rule"], disabled=True)
                st.text_input("Facility Address", value=p["address"], disabled=True)
                st.text_input("Payee / Assignment Code", value=p["payee"], disabled=True)

        # 3. System Rule Verifications & Claim History Ledger
        with st.expander("📜 System Rule Checks & Member Claim History", expanded=False):
            if current_scenario["history"]:
                st.table(current_scenario["history"])
            else:
                st.info("No prior claims on file for this subscriber.")

        # 4. Invoice Image Viewer
        with st.expander("📸 View Scanned Document (Invoice/Receipt)", expanded=True):
            if os.path.exists(current_scenario["invoice_image"]):
                st.image(current_scenario["invoice_image"], caption="Original Scanned Submission")
            else:
                st.error("Document image missing or not found.")

        st.write("---")
        st.markdown("#### ✍️ Trainee Adjudication Work Area")

        # 5. Trainee Input Fields
        inp_col1, inp_col2 = st.columns(2)
        with inp_col1:
            eligible_amount = st.number_input(
                "Enter Eligible Amount ($):",
                min_value=0.0,
                step=10.0,
                help="Amount covered by the insurance policy limit."
            )
            decision = st.selectbox(
                "Adjudication Decision:",
                ["Select...", "Approve", "Deny", "Manual Review"],
                help="Select Approve if calculation complies with policy, Deny if non-covered."
            )
        with inp_col2:
            oop_amount = st.number_input(
                "Enter Out-of-Pocket Amount ($):",
                min_value=0.0,
                step=10.0,
                help="Amount the patient must pay out of pocket (Receipt Total minus Eligible Amount)."
            )
            eob_code = st.selectbox(
                "EOB / Explanation Code:",
                ["Select code...", "E00 - Approved as Incurred", "E01 - Benefit Maximum Reached", "D04 - Exceeds Frequency Limit", "R09 - Missing Provider Prescription Details"]
            )
    
        submit_button = st.button("Submit Assessment", type="primary")
    
        # Trigger the Judge Agent when submitted
        if submit_button:
            if decision == "Select...":
                st.error("Please select an Adjudication Decision.")
            else:
                with st.spinner("🤖 Sending assessment to Orchestrator..."):
                    try:
                        payload = {
                            "api_key": api_key,
                            "plan_class": plan_class,
                            "eligible_amount": eligible_amount,
                            "oop_amount": oop_amount,
                            "decision": decision,
                            "model": selected_model
                        }
                        response = requests.post("http://localhost:8080/submit", json=payload)
                    
                        if response.status_code == 200:
                            resp_json = response.json()
                            if resp_json.get("success"):
                                result = resp_json.get("data", {})
                                telemetry = resp_json.get("telemetry", {})
                                st.session_state.telemetry_logs.append({"agent": "Judge Agent", "action": "Assessment", "telemetry": telemetry})
                                
                                st.write("### Assessment Result")
                                if result.get("Status") == "Pass":
                                    st.success(f"**Score:** {result.get('Score')}% | **Status:** {result.get('Status')}\n\n**Feedback:** {result.get('Feedback')}")
                                else:
                                    st.error(f"**Score:** {result.get('Score')}% | **Status:** {result.get('Status')}\n\n**Feedback:** {result.get('Feedback')}")
                            else:
                                st.error(f"Evaluator error: {resp_json.get('error')}")
                        else:
                            st.error(f"Error from Orchestrator: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Error communicating with Orchestrator: {e}")

    # --- 5. RIGHT COLUMN: THE LIVE ASSISTANT ---
    with col2:
        st.subheader("💬 Live Assistant (Mentor Agent)")
        st.caption(f"Ask questions about the current **{plan_class}** policy rules or limit calculations.")
    
        for role, message in st.session_state.chat_history:
            with st.chat_message(role):
                st.markdown(message)
            
        user_question = st.chat_input("Ask for help with the claim policy or calculation...")
    
        if user_question:
            st.session_state.chat_history.append(("user", user_question))
            with st.chat_message("user"):
                st.markdown(user_question)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        payload = {
                            "api_key": api_key,
                            "plan_class": plan_class,
                            "message": user_question,
                            "model": selected_model
                        }
                        response = requests.post("http://localhost:8080/chat", json=payload)
                    
                        if response.status_code == 200:
                            resp_json = response.json()
                            if resp_json.get("success"):
                                mentor_response = resp_json.get("data")
                                telemetry = resp_json.get("telemetry", {})
                                st.session_state.telemetry_logs.append({"agent": "Mentor Agent", "action": "Chat", "telemetry": telemetry})
                                
                                st.markdown(mentor_response)
                                st.session_state.chat_history.append(("assistant", mentor_response))
                            else:
                                st.error(f"Mentor error: {resp_json.get('error')}")
                        else:
                            st.error(f"Error from Orchestrator: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"Error communicating with Orchestrator: {e}")

with tab_telemetry:
    st.subheader("📊 Agent Telemetry & Log Stream")
    if not st.session_state.telemetry_logs:
        st.info("No telemetry logs yet. Submit an assessment or ask the Mentor Agent a question to generate logs.")
    else:
        for log in reversed(st.session_state.telemetry_logs):
            with st.expander(f"Log: {log['agent']} ({log.get('action', 'Interaction')})", expanded=True):
                st.json(log['telemetry'])
