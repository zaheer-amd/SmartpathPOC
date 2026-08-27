# SmartPath POC - US Claims Adjudication Workstation

Welcome to the **SmartPath POC**, a proof-of-concept application that demonstrates an AI-augmented environment for manual health insurance claims adjudication. The system acts as a legacy workstation simulator where claims adjusters (trainees) evaluate claims while being evaluated and assisted by intelligent AI agents.

## 🎯 Purpose and Goal
The primary goal of this project is to explore how Large Language Models (LLMs), specifically **Gemini 3.6 Flash**, can be seamlessly integrated into a complex enterprise workflow to provide real-time evaluation and mentorship. 

By simulating a legacy UI, the application allows users to adjudicate a mock claim against a specific policy (CSD-N). Behind the scenes, the system uses a robust message-driven architecture to route requests to AI agents that grade the trainee's work (Judge Agent) and provide interactive, policy-grounded hints (Mentor Agent).

## 🏗️ Architecture
The architecture is designed to decouple the frontend from the AI logic, using an actor model for orchestration:

1. **Frontend (Streamlit)**: 
   - `app.py` serves as the user interface, mimicking a legacy GLH Enterprise US Commercial Claims Engine. 
   - It captures the trainee's input (Eligible Amount, OOP Amount, Decision) and chat queries.
2. **Orchestration Layer (Scala / Akka HTTP)**: 
   - Found in the `akka-orchestrator/` directory, this acts as the middleman.
   - `UserRoutes.scala` receives incoming POST requests (`/submit` and `/chat`) from the frontend.
   - `TraineeActor.scala` encapsulates the business logic, receiving commands via the Akka Ask pattern, translating them into HTTP calls to the backend, and piping the responses back.
3. **AI Backend (Python / FastAPI)**: 
   - `ai_service.py` runs on port 8000 and exposes endpoints that invoke the Google Gemini models.
   - **Judge Agent**: Evaluates the trainee's final submitted numbers against the ground-truth policy.
   - **Mentor Agent**: Loads the Markdown-based knowledge layer (`CSD_policy.md`) and grounds its responses in the actual policy to provide accurate hints to the trainee.

## 🚀 Steps Taken & Development Journey
During the development of this POC, several key integrations and refactors were made to ensure a resilient pipeline:
1. **Frontend to Orchestrator Hookup**: Replaced direct Python function calls in Streamlit with network calls (`requests.post`) to the Akka server (`localhost:8080`).
2. **Akka Orchestration Implementation**: 
   - Initially bypassed the `TraineeActor` as a direct HTTP proxy, but subsequently refactored it to the pure "Actor Way."
   - `TraineeActor` now handles `SubmitClaim` and `SubmitChat` messages, managing the asynchronous HTTP lifecycle with FastAPI.
3. **Dependency Stabilization**: Resolved SBT resolution errors by standardizing the build configuration to stable Apache 2.0 open-source releases of Akka (`2.6.20`), Akka HTTP (`10.2.10`), and Scala (`2.13.14`).
4. **Knowledge Layer Reconnection**: Fixed an issue where the Mentor Agent was hallucinating by ensuring the FastAPI `/chat` endpoint explicitly loaded the `CSD_policy.md` context into the LLM prompt.

## 💡 Key Observations
- **Asynchronous Timeouts**: LLM generation can sometimes exceed standard microservice timeouts (especially on cold starts). We encountered 500 Internal Server Errors due to Akka's `AskTimeoutException`. Increasing the `ask-timeout` in `application.conf` from `5s` to `30s` completely stabilized the pipeline.
- **Model Selection**: We standardized the entire application to use the `gemini-3.6-flash` model for optimal speed and reasoning capability.

## 💻 How to Run Locally

To run the full stack, you will need three terminal windows:

**1. Start the AI Backend (FastAPI)**
```bash
uvicorn ai_service:app --port 8000 --reload
```

**2. Start the Orchestrator (Akka/Scala)**
```bash
cd akka-orchestrator
sbt run
```

**3. Start the UI (Streamlit)**
```bash
streamlit run app.py
```
