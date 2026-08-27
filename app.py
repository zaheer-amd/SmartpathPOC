import streamlit as st
import google.generativeai as genai
import json
import requests
from agents.judge_agent import evaluate_assessment
from agents.mentor_agent import get_mentor_response

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="SmartPath - US Claims Adjudication Workstation", layout="wide")

st.title("SmartPath: CSD-N Adjudication Simulator")
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

model = genai.GenerativeModel(selected_model)

# Sidebar Legacy Workstation Session Details
with st.sidebar.expander("🖥️ Active Terminal Session", expanded=False):
    st.text("Station ID: TERM-WS09-AUSTIN\nOperator: OPR-5524 (Trainee - Level 1)\nEnvironment: PROD-US-CENTRAL (Austin DC)\nRegion: REG-05 (Southwest Commercial)\nWorkpool: US-COMM-CSD-MANUAL-02\nQueue Depth: 24 Pending")

# Initialize session state for the chat assistant memory
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. LEGACY WORKSTATION HEADER STATUS BAR ---
st.markdown(
    """
    <div style="background-color: #0f172a; color: #f8fafc; padding: 10px 16px; border-radius: 8px; font-family: monospace; font-size: 0.85rem; margin-bottom: 15px; border-left: 5px solid #0284c7; display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
        <span><strong>SYS:</strong> GLH-ADJUDICATOR-US v9.2.0</span>
        <span><strong>BATCH:</strong> B20260815-US-TX01 (#0118)</span>
        <span><strong>QUEUE:</strong> NON-AUTO CSD-N (US-COMMERCIAL)</span>
        <span><strong>INGEST:</strong> EDI-837P / OCR-SCAN (16-AUG-2026)</span>
        <span><strong>CLAIM ID:</strong> CLM-2026-US-48201</span>
        <span><strong>STATUS:</strong> PENDING ADJUDICATION</span>
    </div>
    """,
    unsafe_allow_html=True
)

# --- 3. LAYOUT: TWO COLUMNS ---
col1, col2 = st.columns([1.6, 1]) 

# --- 4. LEFT COLUMN: THE CLAIM FORM & LEGACY PANELS ---
with col1:
    st.subheader("📋 Claim Adjudication Form (GLH Workstation - US Edition)")

    # 1. Member & Group Information (Legacy File Record)
    with st.expander("👤 Group & Subscriber Information (Eligibility Ledger)", expanded=True):
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.text_input("Employer / Group Sponsor", value="GRP-748201 - 003 (Apex Dynamics Aerospace - Dallas, TX)", disabled=True)
            st.text_input("Subscriber ID / SSN Hash", value="MEM-US-9941820 (SSN: ***-**-6184)", disabled=True)
            st.text_input("Plan Class & Network", value="Class A - CSD N (Non-Network Direct Reimbursement)", disabled=True)
            st.text_input("State / Tax Jurisdiction", value="TX (Texas) - Fed Tax ID: 74-2910482", disabled=True)
        with m_col2:
            st.text_input("Subscriber / Patient Name", value="Vance, Marcus D. (Mr.)", disabled=True)
            st.text_input("Dep Sequence & Relation", value="00 - Primary Cardholder / Subscriber", disabled=True)
            st.text_input("Date of Birth & Gender", value="18-OCT-1985 (Age: 40) / M", disabled=True)
            st.text_input("Coordination of Benefits (COB)", value="00 - PRIMARY (Single Commercial Payor)", disabled=True)
        with m_col3:
            st.text_input("Coverage Status", value="ACTIVE - IN BENEFIT", disabled=True)
            st.text_input("Effective / Expiration Date", value="01-JAN-2019 / 31-DEC-9999", disabled=True)
            st.text_input("Division & Cost Center", value="DIV-08 (Engineering & Avionics R&D)", disabled=True)
            st.text_input("Annual Deductible Accumulator", value="$0.00 Met / $0.00 Required", disabled=True)

    # 2. Claim Line & Provider Details
    with st.expander("📄 Claim Line & Provider Details (Scanned Invoice Data)", expanded=True):
        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1:
            st.text_input("Claim Reference ID", value="CLM-2026-US-48201", disabled=True)
            st.text_input("Provider Facility & Name", value="Lone Star Vision Institute (PRV-US-88214)", disabled=True)
            st.text_input("Provider NPI & State License", value="NPI: 1487920194 | Lic: TX-OD-90218 (Dr. Samuel Hayes, OD)", disabled=True)
            st.text_input("Provider Taxonomy Code", value="152W00000X - Optometrist (Dispensing)", disabled=True)
        with c_col2:
            st.text_input("Date of Service (DOS)", value="15-AUG-2026", disabled=True)
            st.text_input("Receipt / Invoice No", value="INV-TX-2026-99318", disabled=True)
            st.text_input("Billing Code (CPT / HCPCS)", value="V2020 / CPT-92310 (Prescription Frames & Lenses)", disabled=True)
            st.text_input("Diagnosis Code (ICD-10-CM)", value="H52.223 (Regular astigmatism, bilateral)", disabled=True)
        with c_col3:
            st.text_input("Total Receipt / Billed ($)", value="$250.00 USD", disabled=True)
            st.text_input("Benefit Grid Rule", value="GLASS: N 100 $200/24 MON", disabled=True)
            st.text_input("Facility Address", value="Suite 310, 4200 North Lamar Blvd, Austin, TX 78756", disabled=True)
            st.text_input("Payee / Assignment Code", value="SUBSCRIBER_DIRECT (Assignment of Benefits: NO)", disabled=True)

    # 3. System Rule Verifications & Claim History Ledger
    with st.expander("📜 System Rule Checks & Member Claim History", expanded=False):
        st.markdown("**Automated Pre-Adjudication Integrity Matrix:**")
        chk_col1, chk_col2 = st.columns(2)
        with chk_col1:
            st.success("✅ Member Status: Active on DOS (15-AUG-2026)")
            st.success("✅ Provider License: NPI 1487920194 active in NPPES & Texas Optometry Board")
            st.success("✅ Prescription Requirement: Valid optical Rx from licensed OD on file")
        with chk_col2:
            st.success("✅ Frequency Limit: CLEAN (>24 Months elapsed since last optical hardware claim)")
            st.success("✅ Duplicate Check: CLEARED (No matching DOS / NPI in national payer database)")
            st.info("ℹ️ COB Status: Primary Commercial Payor - Direct Subscriber Reimbursement")

        st.markdown("**Prior Claim History for Subscriber `MEM-US-9941820`:**")
        history_data = [
            {"Claim ID": "CLM-2024-US-10291", "DOS": "18-APR-2024", "Service Code": "CPT-92014 (Comprehensive Eye Exam)", "Billed": "$120.00", "Eligible": "$100.00", "Paid": "$100.00", "Status": "PAID - CLOSED"},
            {"Claim ID": "CLM-2022-US-66102", "DOS": "05-JUL-2022", "Service Code": "V2020 (Prescription Glasses)", "Billed": "$240.00", "Eligible": "$200.00", "Paid": "$200.00", "Status": "ARCHIVED (>24m Window)"},
            {"Claim ID": "CLM-2020-US-31084", "DOS": "12-SEP-2020", "Service Code": "V2020 (Prescription Glasses)", "Billed": "$215.00", "Eligible": "$200.00", "Paid": "$200.00", "Status": "ARCHIVED (>24m Window)"}
        ]
        st.table(history_data)

    st.write("---")
    st.markdown("#### ✍️ Trainee Adjudication Work Area")

    # 4. Trainee Input Fields
    inp_col1, inp_col2 = st.columns(2)
    with inp_col1:
        eligible_amount = st.number_input(
            "Enter Eligible Amount ($):",
            min_value=0.0,
            step=10.0,
            help="Amount covered by the insurance policy limit according to CSD-N rules."
        )
        decision = st.selectbox(
            "Adjudication Decision:",
            ["Select...", "Approve", "Deny", "Manual Review"],
            help="Select Approve if calculation complies with policy, Deny if non-covered, or Manual Review if supervisor intervention is needed."
        )
        disbursement_method = st.selectbox(
            "Disbursement Routing / Payee:",
            [
                "01 - Subscriber Direct Deposit / ACH (JPMorgan Chase - Acct: **********7821)",
                "02 - Subscriber Paper Check via USPS Mail",
                "03 - Provider Direct Assignment (NPI: 1487920194)",
                "09 - Hold Payment (Pending Audit Review)"
            ],
            help="Default disbursement method based on subscriber profile."
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
            [
                "Select code...",
                "E01 - Benefit Maximum Reached ($200 Policy Cap)",
                "E00 - Approved as Incurred (100% Covered)",
                "D04 - Exceeds Frequency Limit (Within 24 Months)",
                "R09 - Missing Provider Prescription Details",
                "M02 - Supervisor Manual Override Approved"
            ],
            help="Explanation of Benefits code to print on subscriber statement."
        )
        internal_routing = st.selectbox(
            "Audit & Review Disposition:",
            [
                "NORM - Standard Trainee Auto-Release",
                "AUDIT - Flag for Random Senior Adjudicator QA",
                "SUPV - Escalate to Supervisor Worklist"
            ]
        )

    adjudicator_notes = st.text_input(
        "Adjudicator Internal Notes (Optional):",
        placeholder="e.g. Applied CSD-N $200.00 / 24-month vision benefit maximum. Remainder $50.00 subscriber out-of-pocket."
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
                        "eligible_amount": eligible_amount,
                        "oop_amount": oop_amount,
                        "decision": decision
                    }
                    # Send to Akka!
                    response = requests.post("http://localhost:8080/submit", json=payload)
                    
                    if response.status_code == 200:
                        resp_json = response.json()
                        if resp_json.get("success"):
                            result = json.loads(resp_json.get("data", "{}"))
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
    st.caption("Ask questions about CSD-N policy rules, limit calculations, or legacy codes.")
    
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
                        "message": user_question
                    }
                    response = requests.post("http://localhost:8080/chat", json=payload)
                    
                    if response.status_code == 200:
                        resp_json = response.json()
                        if resp_json.get("success"):
                            mentor_response = resp_json.get("data")
                            st.markdown(mentor_response)
                            st.session_state.chat_history.append(("assistant", mentor_response))
                        else:
                            st.error(f"Mentor error: {resp_json.get('error')}")
                    else:
                        st.error(f"Error from Orchestrator: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Error communicating with Orchestrator: {e}")