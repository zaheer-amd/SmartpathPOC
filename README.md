# SmartPath — Enterprise Claims Training & Simulation Platform

SmartPath decouples health insurance claims adjudication training into two distinct, high-performance systems:
1. **Build-Time Simulation Authoring Engine** (`simulation/`): Converts expert screen recordings into interactive browser simulations using **RapidOCR Ground-Truth Anchors** and **Gemini Vision spatial reasoning**.
2. **Runtime Training Workstation** (`workstation/`): An AI-augmented manual claims adjudication simulator where trainees practice adjudicating claims while being evaluated by **Judge Agent** and mentored by **Mentor Agent**, orchestrated through an **Akka Typed Actor Model**.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       OBJECTIVE A: BUILD-TIME PIPELINE                      │
│                                                                             │
│  MP4 Video ──▶ SSIM Keyframes ──▶ Whisper Audio ──▶ RapidOCR Anchors       │
│                                                            │                │
│  Interactive Browser Sim ◀── scenario_graph.json ◀── Gemini Spatial Reasoning
│  (simulation/webview)                               (s5_metadata_generator)│
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      OBJECTIVE B: RUNTIME WORKSTATION                       │
│                                                                             │
│  Trainee UI (Port 8501)                                                     │
│  Streamlit Modular Client                                                   │
│       │                                                                     │
│       │ HTTP POST /submit, /chat                                            │
│       ▼                                                                     │
│  Akka Orchestrator (Port 8080)                                              │
│  Scala 2.13 • Akka Typed • TraineeActor • SessionStore (SQLite Ledger)     │
│       │                                                                     │
│       │ HTTP POST /evaluate, /chat                                          │
│       ▼                                                                     │
│  AI Gateway (Port 8000)                                                     │
│  FastAPI • Pydantic Contracts • Lifespan Manager                            │
│       ├── RAG Knowledge Layer: Mock Azure AI Search (CSD, Dental, Rx)       │
│       ├── Judge Agent: Submission evaluation & token savings scoring        │
│       └── Mentor Agent: Context-aware pedagogical guidance                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Repository Layout

```
c:\SmartPath\
│
├── workstation/                        ← Runtime Training Workstation
│   ├── app.py                          ← Lean Streamlit entry point (~100 lines)
│   ├── config.py                       ← Centralized URLs, ports, timeouts, models
│   ├── requirements.txt                ← Streamlit, FastAPI, Uvicorn, Pydantic, etc.
│   ├── ui/                             ← Modular UI components
│   │   ├── sidebar.py                  ← Session config, queue navigation
│   │   ├── claim_form.py               ← Member eligibility, invoice & claim viewer
│   │   ├── trainee_inputs.py           ← Calculation fields & assessment submission
│   │   ├── mentor_chat.py              ← AI mentor dialogue & policy viewer
│   │   └── telemetry_dashboard.py      ← 7-stage AI transparency & audit walkthrough
│   ├── gateway/                        ← FastAPI AI Gateway (Port 8000)
│   │   ├── main.py                     ← Lifespan manager, CORS, router mounts
│   │   ├── models.py                   ← Pydantic request/response schemas
│   │   └── routes/                     ← /evaluate, /chat, /search, /policy routes
│   ├── agents/                         ← AI Agent implementations
│   │   ├── base_agent.py               ← Shared telemetry & token calculation
│   │   ├── judge_agent.py              ← Inherits BaseAgent (Assessment evaluator)
│   │   └── mentor_agent.py             ← Inherits BaseAgent (Trainee mentor)
│   ├── knowledge/                      ← RAG Knowledge Layer
│   │   ├── loader.py                   ← Policy loader & mock Azure search fallback
│   │   ├── policy_index.py             ← In-memory section parser & semantic search
│   │   └── policies/                   ← Source policy markdown documents
│   └── data/                           ← Runtime claim scenarios & invoice images
│
├── simulation/                         ← Build-Time Simulation Authoring Engine
│   ├── build.py                        ← Unified CLI pipeline orchestrator
│   ├── requirements.txt                ← OpenCV, scikit-image, Whisper, RapidOCR
│   ├── pipeline/                       ← Numbered pipeline stages
│   │   ├── s1_frame_extractor.py       ← Video frame extraction (OpenCV)
│   │   ├── s2_keyframe_detector.py     ← SSIM keyframe detection
│   │   ├── s3_audio_transcriber.py     ← Local Whisper speech-to-text
│   │   ├── s4_ocr_engine.py            ← RapidOCR text & coordinate anchor extraction
│   │   ├── s5_metadata_generator.py    ← Gemini Vision with OCR anchor prompting
│   │   ├── s6_coordinate_transformer.py← 0-1000 to CSS percentage coordinates
│   │   └── s7_graph_compiler.py        ← scenario_graph.json assembler
│   ├── tools/                          ← Authoring Tools
│   │   └── calibrator/                 ← HITL QA Studio (calibrate.html, calibrator.js)
│   ├── inputs/                         ← Source prompt templates & raw metadata
│   ├── outputs/                        ← Intermediate frames, keyframes, transcripts
│   └── webview/                        ← Browser runtime simulation player
│
├── orchestrator/                       ← Akka Typed Orchestrator (Scala, Port 8080)
│   ├── build.sbt                       ← SBT build configuration
│   ├── src/main/scala/com/example/
│   │   ├── QuickstartApp.scala         ← HTTP server entry point
│   │   ├── UserRoutes.scala            ← /submit, /chat, /session routes
│   │   ├── TraineeActor.scala          ← Actor with typed Spray-JSON AST
│   │   ├── SessionStore.scala          ← SQLite persistence
│   │   └── JsonFormats.scala           ← Spray-JSON formats
│   └── src/main/resources/application.conf
│
└── docs/                               ← Architecture and mapping documentation
```

---

## 🔍 Key Architectural Enhancements

### 1. OCR-First Anchor Strategy (Fixing the "Label vs. Input Box" Trap)
- **Problem**: When text labels (e.g., `"Enter Eligible Amount ($):"`) sit next to empty input fields, running OCR after Gemini and overwriting bounding boxes causes simulations to target the text label rather than the input rectangle.
- **Solution**: Run **Stage 4 (`s4_ocr_engine.py`)** first. RapidOCR extracts all on-screen text with exact pixel coordinates. This anchor table is passed into **Stage 5 (`s5_metadata_generator.py`)** prompt. Gemini snaps directly to button text, but for input boxes, it calculates the bounding rectangle relative to the adjacent label anchor.
- **Zero Fuzzy Matching**: Gemini semantically matches its intent to the anchor ID, eliminating post-hoc string fuzzy matching (`thefuzz`/`rapidfuzz`).

### 2. Lightweight RapidOCR
- Replaced heavyweight EasyOCR/PyTorch (~2.5GB) with `rapidocr-onnxruntime` (<50MB, CPU ONNX runtime). Runs in ~50-100ms per frame.

### 3. Human-in-the-Loop (HITL) Authoring Studio
- Deleted hardcoded coordinate hacking (`patch_json.py`).
- Demoted `calibrate.html` to `simulation/tools/calibrator/` as an optional HITL QA verification studio for icon-only edge cases.

### 4. Strict Workstation Decoupling
- `workstation/app.py` communicates strictly over HTTP with Port 8080 (Akka) and Port 8000 (Gateway) via `workstation/config.py`.
- No direct imports between UI and backend agents/knowledge layers.

---

## 💻 Quickstart Guide

### 1. Start the AI Gateway (FastAPI, Port 8000)
```powershell
uvicorn workstation.gateway.main:app --port 8000 --reload
```

### 2. Start the Orchestrator (Akka/Scala, Port 8080)
```powershell
cd orchestrator
sbt run
```

### 3. Start the Workstation UI (Streamlit, Port 8501)
```powershell
streamlit run workstation/app.py
```

### 4. Run the Simulation Authoring Pipeline (CLI)
```powershell
# Automated pipeline: SSIM -> Whisper -> RapidOCR -> Gemini Vision -> Graph
python simulation/build.py --auto --gemini-key YOUR_API_KEY

# Serve the compiled interactive simulation player:
cd simulation/webview
python -m http.server 9000
```
Open `http://localhost:9000` in your browser to experience the compiled interactive simulation.
