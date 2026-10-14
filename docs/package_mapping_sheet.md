# SmartPath — Package Mapping Sheet

> **Purpose**: Reference document mapping prototype libraries to enterprise production counterparts.  
> **Format**: Structured architectural readiness assessment.  
> **Scope**: All non-frontend packages — AI Backend, Orchestrator, and Simulation Pipeline only.

---

## Packages Used — Main Table

Copy each row below into your Google Sheet tab.

| # | Packages Used | Java / Akka Equivalent with Same Behavior | Why It Is Used | Expected Quality in This Use Case | Better Library or Future Approach |
|---|---------------|-------------------------------------------|----------------|-----------------------------------|-----------------------------------|
| 1 | **OpenCV Python (opencv-python)** | OpenCV Java / JavaCV | Extracts individual frames from MP4 screen recordings at precise millisecond timestamps. Also powers automated keyframe detection by sampling frames and converting them to grayscale for SSIM comparison. Used in both manual mode (timestamp-based extraction) and auto mode (scene-change detection). | 90% to 95% — frame extraction is deterministic and highly reliable. Keyframe detection accuracy depends on SSIM thresholds (0.92 change / 0.97 stable). | JavaCV with built-in scene-change detection. For production, consider Azure AI Video Indexer for managed keyframe extraction without custom code. |
| 2 | **scikit-image** | BoofCV (Java) or custom SSIM via JavaCV | Provides the SSIM (Structural Similarity Index Measure) metric used in the keyframe detector's two-state finite state machine. Compares consecutive grayscale frames to detect when the UI has changed significantly and when it has stabilized after a transition. | 85% to 95% — SSIM is a well-established perceptual metric. Accuracy depends on threshold tuning; current defaults (change < 0.92, stable > 0.97) work well for Streamlit UI recordings. | BoofCV (pure Java image processing library with SSIM support), or implement SSIM directly via JavaCV matrix operations. For an Azure-native approach, Azure AI Video Indexer handles scene detection without manual SSIM coding. |
| 3 | **OpenAI Whisper** | Vosk (Java), or Azure AI Speech SDK for Java | Transcribes narrator voiceover audio from screen recording videos. Runs locally (no API calls) using the `base` model. Outputs timestamped text segments that are correlated with keyframes to provide narration context (plus/minus 5 second window) for metadata generation. | 85% to 95% — Whisper `base` model is accurate for clear English narration in screen recordings. Quality drops for noisy environments or heavy accents. | **Azure AI Speech (Speech-to-Text)** — production-grade, managed, supports custom models, and provides real-time plus batch transcription with speaker diarization. Eliminates the need to bundle a local ML model. |
| 4 | **FFmpeg** | JavaCV FFmpegFrameGrabber | Extracts the audio track from MP4 videos and converts it to a 16kHz mono PCM WAV file — the required input format for Whisper. Called as a subprocess from the audio transcriber. A bundled `ffmpeg.exe` is included in the simulation module for portability. | 95%+ — FFmpeg is the industry standard for audio/video transcoding. Extraction is deterministic and codec-agnostic. | JavaCV FFmpegFrameGrabber provides the same FFmpeg functionality natively in Java without subprocess calls. For a fully managed approach, **Azure Media Services** can handle media processing at scale. |
| 5 | **google-generativeai (Gemini SDK)** | Akka AI Agent calling **Azure OpenAI Service** via the OpenAI Java SDK | Core LLM integration used in three distinct roles: (1) **Judge Agent** — evaluates trainee claim submissions against policy rules and returns structured JSON verdicts (Pass/Fail, Score, Feedback). (2) **Mentor Agent** — answers trainee questions with policy-grounded guidance without revealing answers. (3) **Metadata Generator** — multimodal vision: uploads keyframe screenshots plus narrator transcript to Gemini, receives structured JSON describing UI elements, action types, bounding boxes, and instructional hints. Also used for model discovery and token usage telemetry extraction. | 80% to 90% — Judge Agent accuracy is high when policy rules are unambiguous. Mentor Agent quality depends on prompt engineering. Metadata Generator accuracy (multimodal vision) is 70% to 85% depending on screenshot complexity and OCR-heavy content. | **Azure OpenAI Service** (GPT-4o, GPT-4o-mini) — provides private endpoints, VNET integration, managed content filtering, Azure AD/Entra ID token auth (no raw API keys), and enterprise SLAs. For the vision/multimodal pipeline, **Azure AI Vision** plus **Azure OpenAI GPT-4o with vision** replaces the Gemini Vision workflow. For gateway/routing, **Azure AI Foundry** or **Azure API Management** in front of Azure OpenAI. |
| 6 | **FastAPI** | **Akka HTTP** (already in use in the orchestrator) | Serves as the Python REST API framework for the AI backend microservice on port 8000. Exposes four endpoints: `POST /evaluate` (Judge Agent), `POST /chat` (Mentor Agent), `POST /search` (mock Azure AI Search / RAG), and `GET /policy/{plan_class}` (policy viewer). Includes a startup event that pre-builds the in-memory policy index on boot. | High — FastAPI is production-grade, async-capable, and auto-validates all requests via Pydantic. | In production, the Python AI backend would either be (a) consolidated into the **Akka HTTP** orchestrator with AI calls made directly from Scala actors via the Azure OpenAI Java SDK, or (b) deployed as an **Azure App Service** or **Azure Container App** behind **Azure API Management**. Either way, FastAPI itself is production-ready. |
| 7 | **Pydantic** | Java Records + Jackson Databind + Jakarta Bean Validation | Validates and deserializes incoming JSON request payloads on the AI backend. Three `BaseModel` subclasses enforce schema contracts: `ClaimRequest` (7 fields including typed floats and Optional strings), `ChatRequest` (5 fields), and `SearchRequest` (3 fields with defaults). Automatically rejects malformed requests with 422 Validation Error before they reach agent logic. | High structural reliability — type coercion, missing field detection, and default value handling are all automatic. | Java Records for data classes, **Jackson Databind** for JSON serialization/deserialization, and **Jakarta Bean Validation** (`@NotNull`, `@Min`, `@Max`) for constraint enforcement. For stronger contract guarantees, add **JSON Schema** validation and business-rule validation layers. In Azure, **Azure API Management** can enforce request schema validation at the gateway level. |
| 8 | **Requests** | **Akka HTTP Client** (already in use in TraineeActor) | Synchronous HTTP client used for inter-service communication. Two use cases: (1) Frontend to Akka orchestrator (`POST /submit`, `/chat`, `/session/start`), and (2) Knowledge Loader to RAG service (`POST /search`). All calls include explicit timeouts (3-5 seconds). Graceful fallback: if the RAG service is unreachable, the loader falls back to direct file reading. | High — HTTP calls are simple and reliable. Timeouts prevent UI hangs. | Already replaced on the Akka side — **Akka HTTP Client** (`Http().singleRequest()`) handles all outbound calls from the orchestrator. In production, inter-service communication should go through **Azure API Management** or **Azure Service Bus** for message-driven patterns with retry, circuit-breaking, and dead-letter support. |
| 9 | **SQLite JDBC** | **Azure SQL Database** or **Azure Cosmos DB** | Embedded file-based relational database (`trainee_sessions.db`) used by the Akka `SessionStore` actor for session persistence. Stores two tables: `sessions` (session_id, trainee_id, plan_class, started_at) and `interactions` (request/response payloads, interaction_type, timestamp, latency_ms). All DB access is serialized through the actor to avoid SQLite's single-writer limitation. | High for POC — single-user, single-file, zero-config. Not suitable for multi-user or multi-instance production deployment. | **Azure SQL Database** (serverless tier) for relational storage with HA, auto-backups, and multi-user concurrency. Alternatively, **Azure Cosmos DB** (NoSQL) for globally distributed, low-latency session storage. Both support Azure AD authentication and VNET integration. |
| 10 | **In-memory Policy Index (policy_index.py)** | **Azure AI Search** (formerly Azure Cognitive Search) | Mock RAG (Retrieval-Augmented Generation) system that simulates Azure AI Search. Reads `.md` policy documents at startup, splits them by H2 headings into sections, and builds an in-memory dict index. Provides a naive keyword-intersection search (`search_policy`) and a full-document retrieval function (`get_full_policy`). Serves `POST /search` and `GET /policy/{plan_class}` endpoints. | 70% to 85% — keyword search is adequate for 3 small policy documents. Would fail at scale or with complex queries requiring semantic understanding. | **Azure AI Search** with vector/hybrid search and semantic ranking. Policy documents stored in **Azure Blob Storage** with automatic indexer pipelines. Provides enterprise-scale search over thousands of documents with relevance tuning, faceted navigation, and integration with Azure OpenAI for RAG patterns via **Azure AI Foundry**. |
| 11 | **Logback Classic** | Already Java / SLF4J (keep as-is) | SLF4J logging backend for Akka orchestrator. All actor logging (`context.log.info/error`) routes through Logback. Captures actor lifecycle events, HTTP request/response tracing, database operations, and error conditions. | High — industry-standard structured logging. | Keep Logback, but pipe logs to **Azure Monitor** and **Azure Application Insights** using the Application Insights Java agent for centralized monitoring, alerting, and distributed tracing across all services. |

---

## Column-by-Column Copy Guide

For quick copy-paste into Google Sheets, here are the columns separated:

### Column A — Packages Used
```
OpenCV Python (opencv-python)
scikit-image
OpenAI Whisper
FFmpeg
google-generativeai (Gemini SDK)
FastAPI
Pydantic
Requests
SQLite JDBC
In-memory Policy Index (policy_index.py)
Logback Classic
```

### Column B — Java / Akka Equivalent
```
OpenCV Java / JavaCV
BoofCV (Java) or custom SSIM via JavaCV
Vosk (Java), or Azure AI Speech SDK for Java
JavaCV FFmpegFrameGrabber
Akka AI Agent calling Azure OpenAI Service via OpenAI Java SDK
Akka HTTP (already in use in orchestrator)
Java Records + Jackson Databind + Jakarta Bean Validation
Akka HTTP Client (already in use in TraineeActor)
Azure SQL Database or Azure Cosmos DB
Azure AI Search (formerly Azure Cognitive Search)
Already Java / SLF4J (keep as-is)
```

### Column C — Why It Is Used
```
Extracts individual frames from MP4 screen recordings at precise millisecond timestamps. Powers automated keyframe detection via grayscale SSIM comparison with a two-state finite state machine.
Provides SSIM (Structural Similarity Index) for perceptual frame comparison. Detects when the UI has changed (score < 0.92) and when it has stabilized (score > 0.97).
Transcribes narrator voiceover from screen recording videos using local Whisper base model. Outputs timestamped segments correlated with keyframes (plus/minus 5s window) for metadata generation.
Extracts audio track from MP4 videos and converts to 16kHz mono PCM WAV for Whisper input. Called as subprocess.
Core LLM integration: (1) Judge Agent evaluates trainee submissions and returns JSON verdicts, (2) Mentor Agent provides policy-grounded guidance, (3) Metadata Generator uses multimodal vision to analyze keyframe screenshots plus narration and produce structured simulation JSON.
Python REST API framework for the AI backend on port 8000. Exposes /evaluate, /chat, /search, and /policy endpoints. Pre-builds policy index on startup.
Validates and deserializes JSON request payloads via BaseModel subclasses. Enforces schema contracts with typed fields and Optional defaults. Auto-rejects malformed requests with 422 errors.
Synchronous HTTP client for inter-service calls (frontend to orchestrator, knowledge loader to RAG service). Includes explicit timeouts and graceful fallback to direct file reading.
Embedded SQLite database for session persistence. Stores sessions and interactions tables with full request/response payloads and latency tracking. Serialized through Akka actor.
Mock RAG system simulating Azure AI Search. Reads .md policy docs, splits into sections by H2, builds in-memory keyword index. Serves search and policy retrieval endpoints.
SLF4J logging backend for Akka orchestrator. Captures actor lifecycle, HTTP tracing, DB operations, and errors via context.log calls.
```

### Column D — Expected Quality
```
90% to 95%
85% to 95%
85% to 95%
95%+
80% to 90%
High
High
High
High (POC only, single-user)
70% to 85%
High
```

### Column E — Better Library or Future Approach
```
JavaCV with scene-change detection. Azure AI Video Indexer for managed keyframe extraction.
BoofCV or JavaCV matrix SSIM. Azure AI Video Indexer for managed scene detection.
Azure AI Speech (Speech-to-Text) — managed, custom models, speaker diarization.
JavaCV FFmpegFrameGrabber. Azure Media Services for managed processing.
Azure OpenAI Service (GPT-4o/4o-mini) with Azure AD auth. Azure AI Vision for multimodal. Azure AI Foundry for gateway/routing.
Consolidate into Akka HTTP, or deploy on Azure App Service / Container Apps behind Azure API Management.
Java Records + Jackson + Jakarta Validation. Azure API Management for gateway-level schema validation.
Akka HTTP Client (already done). Azure API Management or Azure Service Bus for production routing.
Azure SQL Database (serverless) or Azure Cosmos DB with Azure AD auth and VNET integration.
Azure AI Search with vector/hybrid search plus semantic ranking. Azure Blob Storage for document storage. Azure AI Foundry for RAG orchestration.
Keep Logback. Add Azure Monitor plus Application Insights Java agent for centralized monitoring and distributed tracing.
```

---

## LLM Metrics (Matching Hashim's Format)

| Metric | Value |
|--------|-------|
| **LLM Model** | gemini-3.6-flash (Judge + Mentor Agents), gemini-2.5-flash (Metadata Generator) |
| **LLM Requests** | 2 per claim cycle (1 Judge + 1 Mentor), plus N per simulation build (1 per keyframe) |
| **Success Rate** | 100% (with 15s timeout per request) |
| **Prompt Tokens** | ~800-1200 per Judge call, ~700-1000 per Mentor call (varies by policy length) |
| **Completion Tokens** | ~50-100 per Judge call (structured JSON), ~80-150 per Mentor call (natural language) |
| **Total Tokens** | ~900-1300 per interaction |
| **Total LLM Time** | ~2-4 seconds per call (after cold start) |
| **Telemetry Captured** | prompt_token_count, candidates_token_count, total_token_count, retrieval_source |

---

## Azure Production Architecture Summary

For quick reference, here is how the full stack maps to Azure:

| POC Component | Azure Production Service |
|---------------|--------------------------|
| FastAPI (port 8000) | Azure App Service or Azure Container Apps |
| Akka Orchestrator (port 8080) | Azure Kubernetes Service (AKS) or Azure Container Apps |
| Gemini SDK (google-generativeai) | Azure OpenAI Service |
| SQLite (trainee_sessions.db) | Azure SQL Database (serverless) |
| In-memory policy index | Azure AI Search + Azure Blob Storage |
| Whisper (local model) | Azure AI Speech (Speech-to-Text) |
| Logback logs | Azure Monitor + Application Insights |
| API key auth | Azure AD / Entra ID + Managed Identity |
| localhost HTTP calls | Azure API Management + Azure VNET |
