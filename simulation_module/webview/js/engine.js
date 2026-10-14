"use strict";

/**
 * SmartPath Simulation Engine v2
 * 
 * A dependency-free state machine that renders an interactive
 * training simulation from a compiled scenario_graph.json.
 * 
 * Features:
 * - Start screen with API key input
 * - Interactive state machine with click/input zones
 * - Collapsible AI Guide sidebar powered by Gemini 2.0 Flash
 * - Feedback toasts and completion overlay
 */

const GRAPH_URL = "scenario_graph.json";
const GEMINI_MODEL = "gemini-flash-lite-latest";
const GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models";

// ── State ─────────────────────────────────────────────────────
let graph = null;
let stateIndex = {};
let currentStateId = null;
let attemptCount = 0;
let totalAttempts = 0;
let statesCompleted = 0;
let viewingIndex = 0;

// ── AI Guide State ────────────────────────────────────────────
let geminiApiKey = null;
let chatHistory = [];       // Array of { role: "user"|"model", parts: [{ text }] }
let guideEnabled = false;
let isGuideGenerating = false;

// ── DOM References ────────────────────────────────────────────
// (Resolved lazily after DOM is ready and simulation starts)
let frameImage, container, hintText, progressFill, progressText;
let feedbackToast, feedbackIcon, feedbackMsg;
let completionOverlay, completionStats;
let guidePanel, guideMessages, guideInput, toggleGuideBtn;


// ══════════════════════════════════════════════════════════════
//  START SCREEN
// ══════════════════════════════════════════════════════════════

function beginSimulation() {
    const apiKeyInput = document.getElementById("api-key-input");
    geminiApiKey = apiKeyInput.value.trim();
    guideEnabled = geminiApiKey.length > 0;

    // Fade out start screen
    const startScreen = document.getElementById("start-screen");
    startScreen.classList.add("fade-out");

    setTimeout(() => {
        startScreen.style.display = "none";

        // Show simulation wrapper
        const wrapper = document.getElementById("simulation-wrapper");
        wrapper.classList.remove("hidden");

        // Show/hide guide toggle button
        toggleGuideBtn = document.getElementById("toggle-guide-btn");
        if (guideEnabled) {
            toggleGuideBtn.style.display = "flex";
        }

        // Resolve DOM references now that the simulation is visible
        resolveDOMRefs();

        // Load the graph and start
        init();
    }, 500);
}

// Make beginSimulation available globally
window.beginSimulation = beginSimulation;

function resolveDOMRefs() {
    frameImage      = document.getElementById("frame-image");
    container       = document.getElementById("simulation-container");
    hintText        = document.getElementById("hint-text");
    progressFill    = document.getElementById("progress-fill");
    progressText    = document.getElementById("progress-text");
    feedbackToast   = document.getElementById("feedback-toast");
    feedbackIcon    = document.getElementById("feedback-icon");
    feedbackMsg     = document.getElementById("feedback-message");
    completionOverlay = document.getElementById("completion-overlay");
    completionStats   = document.getElementById("completion-stats");
    guidePanel      = document.getElementById("ai-guide-panel");
    guideMessages   = document.getElementById("guide-messages");
    guideInput      = document.getElementById("guide-input");
}


// ══════════════════════════════════════════════════════════════
//  AI GUIDE SIDEBAR
// ══════════════════════════════════════════════════════════════

function toggleGuide() {
    if (!guidePanel) return;
    const isCollapsed = guidePanel.classList.contains("collapsed");

    if (isCollapsed) {
        guidePanel.classList.remove("collapsed");
        toggleGuideBtn.classList.add("active");
    } else {
        guidePanel.classList.add("collapsed");
        toggleGuideBtn.classList.remove("active");
    }
}

window.toggleGuide = toggleGuide;

// ── Invoice Modal ─────────────────────────────────────────────

function openInvoiceModal() {
    const modal = document.getElementById("invoice-modal");
    if (modal) modal.classList.remove("hidden");
}

function closeInvoiceModal(event) {
    // If event is provided, only close if clicking the backdrop or close button
    if (event && event.target.id !== "invoice-modal" && event.target.id !== "invoice-close-btn") {
        return;
    }
    const modal = document.getElementById("invoice-modal");
    if (modal) modal.classList.add("hidden");
}

window.openInvoiceModal = openInvoiceModal;
window.closeInvoiceModal = closeInvoiceModal;

// ── Guide Chat ────────────────────────────────────────────────

function addGuideMessage(text, role) {
    if (!guideMessages) return;

    const msg = document.createElement("div");
    msg.className = `guide-msg ${role}`;

    const label = document.createElement("span");
    label.className = "msg-label";
    label.textContent = role === "mentor" ? "Mentor" : role === "user" ? "You" : "System";

    const content = document.createElement("span");
    content.textContent = text;

    msg.appendChild(label);
    msg.appendChild(content);
    guideMessages.appendChild(msg);

    // Auto-scroll to bottom
    guideMessages.scrollTop = guideMessages.scrollHeight;
}

function showTypingIndicator() {
    const typing = document.createElement("div");
    typing.className = "guide-msg typing";
    typing.id = "guide-typing";
    typing.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    guideMessages.appendChild(typing);
    guideMessages.scrollTop = guideMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typing = document.getElementById("guide-typing");
    if (typing) typing.remove();
}


// ── Gemini API Call ───────────────────────────────────────────

async function callGemini(userMessage, systemContext) {
    if (!geminiApiKey) return null;

    // Build the system instruction
    const systemInstruction = buildSystemPrompt(systemContext);

    // Add user message to history
    chatHistory.push({
        role: "user",
        parts: [{ text: userMessage }]
    });

    const requestBody = {
        system_instruction: {
            parts: [{ text: systemInstruction }]
        },
        contents: chatHistory,
        generationConfig: {
            temperature: 0.7,
            maxOutputTokens: 800,
            topP: 0.9,
        }
    };

    try {
        const url = `${GEMINI_API_BASE}/${GEMINI_MODEL}:generateContent?key=${geminiApiKey}`;
        const resp = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.error?.message || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "I couldn't generate a response.";

        // Add model response to history
        chatHistory.push({
            role: "model",
            parts: [{ text }]
        });

        return text;

    } catch (err) {
        console.error("Gemini API error:", err);
        return `[Error: ${err.message}]`;
    }
}

function buildSystemPrompt(context) {
    return `You are the SmartPath Training Mentor, an AI guide helping a trainee learn claims adjudication.

SIMULATION CONTEXT:
- This is an interactive training simulation for a US commercial claims adjudication workstation.
- The claim is CLM-2026-US-48201 under the Vision CSD-N plan (Class A - CSD N, Non-Network Direct Reimbursement).
- The member is Vance, Marcus D. (Mr.), subscriber MEM-US-9941820.
- The trainee is stepping through ${graph ? graph.total_states : 11} sequential workflow actions.

CURRENT STATE:
${context}

RULES:
1. Be concise (2-3 sentences max unless asked for detail).
2. Be encouraging and professional. Use a warm, mentor-like tone.
3. Explain WHY this step matters in the context of claims processing.
4. If the trainee made an error, gently guide them without directly giving the answer.
5. Reference relevant policy concepts (eligible amounts, EOB codes, adjudication decisions) when appropriate.
6. NEVER directly reveal the expected input value or exact answer. Guide the trainee to discover it.
7. If the trainee asks a question, answer it helpfully using the simulation context.`;
}


// ── Auto-prompt on state transitions ──────────────────────────

async function autoPromptGuide(state, trigger) {
    if (!guideEnabled || isGuideGenerating) return;

    isGuideGenerating = true;
    showTypingIndicator();

    let contextMsg = "";

    if (trigger === "state_enter") {
        contextMsg = `The trainee just arrived at step ${state.sequence_index + 1} of ${graph.total_states}.
Action required: ${state.action_type} on "${state.ui_element_name}".
Hint: ${state.instructional_hint}
Progress: ${statesCompleted}/${graph.total_states} completed, ${totalAttempts} total attempts so far.
Generate a brief, contextual tip for this step.`;

    } else if (trigger === "error") {
        contextMsg = `The trainee made an INCORRECT attempt on step ${state.sequence_index + 1}.
They are trying to: ${state.action_type} on "${state.ui_element_name}".
This was attempt #${attemptCount} on this step.
Total attempts across all steps: ${totalAttempts}.
Give gentle, encouraging guidance without revealing the answer.`;

    } else if (trigger === "success") {
        contextMsg = `The trainee CORRECTLY completed step ${state.sequence_index + 1}: ${state.ui_element_name}.
It took them ${attemptCount} attempt(s) on this step.
Give brief positive reinforcement (1 sentence).`;

    } else if (trigger === "completion") {
        const accuracy = Math.round((graph.total_states / totalAttempts) * 100);
        contextMsg = `The trainee has COMPLETED the entire simulation!
Total steps: ${graph.total_states}
Total attempts: ${totalAttempts}
First-try accuracy: ${accuracy}%
Generate a personalized performance summary and encouragement.`;
    }

    const response = await callGemini(contextMsg, contextMsg);
    removeTypingIndicator();

    if (response) {
        addGuideMessage(response, "mentor");
    }

    isGuideGenerating = false;
}


// ── User chat input ───────────────────────────────────────────

async function sendGuideMessage() {
    if (!guideInput || !guideEnabled) return;

    const text = guideInput.value.trim();
    if (!text || isGuideGenerating) return;

    guideInput.value = "";
    addGuideMessage(text, "user");

    isGuideGenerating = true;
    showTypingIndicator();

    const state = currentStateId ? stateIndex[currentStateId] : null;
    const context = state
        ? `Current step: ${state.sequence_index + 1}/${graph.total_states} — "${state.ui_element_name}" (${state.action_type}). Trainee's question follows.`
        : "The trainee is asking a general question.";

    const response = await callGemini(text, context);
    removeTypingIndicator();

    if (response) {
        addGuideMessage(response, "mentor");
    }

    isGuideGenerating = false;
}

window.sendGuideMessage = sendGuideMessage;


// ══════════════════════════════════════════════════════════════
//  SIMULATION ENGINE
// ══════════════════════════════════════════════════════════════

async function init() {
    try {
        const response = await fetch(GRAPH_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        graph = await response.json();
        
        graph.states.forEach(state => {
            stateIndex[state.state_id] = state;
        });
        
        currentStateId = graph.initial_state_id;

        // If AI Guide is enabled, open it and send welcome
        if (guideEnabled) {
            toggleGuide(); // Open the sidebar
            addGuideMessage("Welcome! I'm your AI Training Mentor. I'll guide you through each step of this claims adjudication simulation. Let's begin!", "mentor");
        }

        renderState(currentStateId);
        
    } catch (err) {
        if (hintText) hintText.textContent = `Error loading simulation: ${err.message}`;
        console.error("Failed to load scenario_graph.json:", err);
    }
}


// ── Render a State ────────────────────────────────────────────

function renderState(stateId) {
    const state = stateIndex[stateId];
    if (!state) {
        console.error(`State not found: ${stateId}`);
        return;
    }
    
    currentStateId = stateId;
    attemptCount = 0;
    viewingIndex = state.sequence_index;
    
    // 1. Update the background frame image
    frameImage.src = state.frame_image;
    frameImage.alt = `Step ${state.sequence_index + 1}: ${state.ui_element_name}`;
    
    // 2. Update the hint bar
    hintText.textContent = state.instructional_hint;
    
    // 3. Update progress bar and buttons
    const progress = ((state.sequence_index) / graph.total_states) * 100;
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${state.sequence_index + 1} / ${graph.total_states}`;
    
    const prevBtn = document.getElementById("prev-step-btn");
    const nextBtn = document.getElementById("next-step-btn");
    if (prevBtn) prevBtn.disabled = state.sequence_index === 0;
    if (nextBtn) nextBtn.disabled = true;
    
    // 4. Remove any existing interaction zone
    const existingZone = container.querySelector(".interaction-zone");
    if (existingZone) existingZone.remove();
    
    // 5. Wait for the image to load, THEN inject the interaction zone
    frameImage.onload = () => injectInteractionZone(state);
    
    if (frameImage.complete && frameImage.naturalWidth > 0) {
        injectInteractionZone(state);
    }

    // 6. Auto-prompt AI Guide
    autoPromptGuide(state, "state_enter");
}


// ── Inject Interaction Zone ───────────────────────────────────

function injectInteractionZone(state) {
    const existingZone = container.querySelector(".interaction-zone");
    if (existingZone) existingZone.remove();
    
    const coords = state.css_coordinates;
    let zone;
    
    if (state.action_type === "click") {
        zone = document.createElement("div");
        zone.className = "interaction-zone click-zone";
        zone.setAttribute("role", "button");
        zone.setAttribute("aria-label", state.ui_element_name);
        zone.setAttribute("tabindex", "0");
        
        zone.addEventListener("click", () => handleAction(state, null));
        zone.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleAction(state, null);
            }
        });
        
    } else if (state.action_type === "input") {
        zone = document.createElement("input");
        zone.type = "text";
        zone.className = "interaction-zone input-zone";
        zone.placeholder = `Type here...`;
        zone.setAttribute("aria-label", state.ui_element_name);
        zone.autocomplete = "off";
        zone.spellcheck = false;
        
        zone.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                handleAction(state, zone.value);
            }
        });
        
        setTimeout(() => zone.focus(), 100);
    }
    
    zone.style.top    = `${coords.top}%`;
    zone.style.left   = `${coords.left}%`;
    zone.style.width  = `${coords.width}%`;
    zone.style.height = `${coords.height}%`;
    
    container.appendChild(zone);
}


// ── Review Mode ─────────────────────────────────────────────────

function reviewPreviousStep() {
    if (viewingIndex > 0) {
        viewingIndex--;
        updateReviewUI();
    }
}

function reviewNextStep() {
    if (viewingIndex < statesCompleted) {
        viewingIndex++;
        updateReviewUI();
    }
}

function updateReviewUI() {
    const reviewState = graph.states[viewingIndex];
    
    // Update frame image
    frameImage.src = reviewState.frame_image;
    progressText.textContent = `${viewingIndex + 1} / ${graph.total_states}`;

    const prevBtn = document.getElementById("prev-step-btn");
    const nextBtn = document.getElementById("next-step-btn");
    const zone = container.querySelector(".interaction-zone");

    // Enable/disable buttons based on bounds
    prevBtn.disabled = viewingIndex === 0;
    nextBtn.disabled = viewingIndex === statesCompleted;

    if (viewingIndex < statesCompleted) {
        // We are in review mode looking at a past state
        if (zone) zone.style.display = "none";
        hintText.textContent = `[REVIEW MODE] Step ${viewingIndex + 1}: ${reviewState.ui_element_name}`;
        hintText.style.color = "#94a3b8";
    } else {
        // We are back at the active state
        if (zone) zone.style.display = "block";
        const activeState = stateIndex[currentStateId];
        hintText.textContent = activeState.instructional_hint;
        hintText.style.color = "#e2e8f0";
    }
}

window.reviewPreviousStep = reviewPreviousStep;
window.reviewNextStep = reviewNextStep;

// ── Handle User Action ────────────────────────────────────────

function handleAction(state, inputValue) {
    totalAttempts++;
    attemptCount++;
    
    let isCorrect = false;
    
    if (state.action_type === "click") {
        isCorrect = true;
        
    } else if (state.action_type === "input") {
        const expected = (state.expected_input_value || "").trim().toLowerCase();
        const actual   = (inputValue || "").trim().toLowerCase();
        isCorrect = (actual === expected);
    }
    
    if (isCorrect) {
        statesCompleted++;
        showFeedback(true, "Correct! Moving to next step...");
        // Removed autoPromptGuide(state, "success") to save API quota
        
        setTimeout(() => {
            if (state.next_state_id) {
                renderState(state.next_state_id);
            } else {
                showCompletion();
            }
        }, 800);
        
    } else {
        showFeedback(false, `Incorrect. Expected "${state.expected_input_value}" - try again.`);
        autoPromptGuide(state, "error");
        
        const zone = container.querySelector(".interaction-zone");
        if (zone) {
            zone.classList.add("shake");
            setTimeout(() => zone.classList.remove("shake"), 400);
            
            if (zone.tagName === "INPUT") {
                zone.value = "";
                zone.focus();
            }
        }
    }
}


// ── Feedback Toast ────────────────────────────────────────────

function showFeedback(success, message) {
    feedbackIcon.textContent = success ? "+" : "x";
    feedbackMsg.textContent  = message;
    feedbackToast.className  = success ? "toast-success" : "toast-error";
    
    clearTimeout(feedbackToast._hideTimer);
    feedbackToast._hideTimer = setTimeout(() => {
        feedbackToast.className = "hidden";
    }, 2000);
}


// ── Completion Screen ─────────────────────────────────────────

function showCompletion() {
    const accuracy = Math.round((graph.total_states / totalAttempts) * 100);
    
    completionStats.innerHTML = `
        Steps completed: <strong>${graph.total_states} / ${graph.total_states}</strong><br>
        Total attempts: <strong>${totalAttempts}</strong><br>
        First-try accuracy: <strong>${accuracy}%</strong>
    `;
    
    progressFill.style.width = "100%";
    progressText.textContent = `${graph.total_states} / ${graph.total_states}`;
    
    completionOverlay.classList.remove("hidden");

    // AI Guide completion summary
    autoPromptGuide(null, "completion");
}


// ── Guide input Enter key ─────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    const gi = document.getElementById("guide-input");
    if (gi) {
        gi.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                sendGuideMessage();
            }
        });
    }
});
