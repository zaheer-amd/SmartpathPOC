"use strict";

/**
 * SmartPath Visual Calibration Tool
 * 
 * Renders each state's frame with a draggable/resizable bounding box overlay.
 * The user adjusts each box to match the actual UI element position, then
 * exports corrected coordinates back to raw_metadata.json format.
 */

const GRAPH_URL = "scenario_graph.json";

let graph = null;
let overlayData = {}; // state_id -> { ymin, xmin, ymax, xmax } on 0-1000 scale
let originalTimestamps = {}; // state_id -> timestamp string (preserved for export)

// ── Initialization ────────────────────────────────────────────

async function initCalibrator() {
    try {
        const resp = await fetch(GRAPH_URL);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        graph = await resp.json();

        graph.states.forEach(state => {
            // Convert css_coordinates back to 0-1000 scale for editing
            const c = state.css_coordinates;
            overlayData[state.state_id] = {
                ymin: Math.round((c.top / 100) * 1000),
                xmin: Math.round((c.left / 100) * 1000),
                ymax: Math.round(((c.top + c.height) / 100) * 1000),
                xmax: Math.round(((c.left + c.width) / 100) * 1000),
            };
        });

        // Try to load original timestamps from raw_metadata.json
        await loadOriginalTimestamps();

        renderCards();
    } catch (err) {
        document.getElementById("cal-grid").innerHTML =
            `<p style="color:#ef4444;padding:40px;">Error: ${err.message}</p>`;
    }
}

async function loadOriginalTimestamps() {
    // Try multiple paths since we don't know how the server is set up
    const paths = ["../inputs/raw_metadata.json", "raw_metadata_source.json"];
    for (const path of paths) {
        try {
            const resp = await fetch(path);
            if (resp.ok) {
                const original = await resp.json();
                original.forEach(s => {
                    originalTimestamps[s.state_id] = s.timestamp_in_video;
                });
                console.log("Loaded original timestamps from:", path);
                return;
            }
        } catch (e) { /* continue */ }
    }
    console.warn("Could not load original timestamps — exports will use '00:00'");
}

// ── Render State Cards ────────────────────────────────────────

function renderCards() {
    const grid = document.getElementById("cal-grid");
    grid.innerHTML = "";

    graph.states.forEach(state => {
        const card = document.createElement("div");
        card.className = "cal-card";
        card.id = `card-${state.state_id}`;

        const actionClass = state.action_type === "click" ? "click" : "input";
        const od = overlayData[state.state_id];

        card.innerHTML = `
            <div class="cal-card-header">
                <div class="cal-card-title">
                    <span class="cal-state-badge">${state.state_id}</span>
                    <span class="cal-element-name">${state.ui_element_name}</span>
                </div>
                <span class="cal-action-badge ${actionClass}">${state.action_type}</span>
            </div>
            <div class="cal-coords" id="coords-${state.state_id}">
                <span class="label">bbox_1000:</span>
                <span id="coord-val-${state.state_id}">[${od.ymin}, ${od.xmin}, ${od.ymax}, ${od.xmax}]</span>
            </div>
            <div class="cal-image-wrapper" id="wrapper-${state.state_id}">
                <img src="${state.frame_image}" alt="${state.state_id}" draggable="false">
            </div>
        `;

        grid.appendChild(card);

        // After the image loads, inject the overlay
        const img = card.querySelector("img");
        const wrapper = card.querySelector(".cal-image-wrapper");

        const injectOverlay = () => {
            createOverlay(state.state_id, wrapper, img);
        };

        img.addEventListener("load", injectOverlay);
        if (img.complete && img.naturalWidth > 0) {
            injectOverlay();
        }
    });
}

// ── Create Draggable Overlay ──────────────────────────────────

function createOverlay(stateId, wrapper, img) {
    // Remove existing overlay if any
    const existing = wrapper.querySelector(".cal-overlay");
    if (existing) existing.remove();

    const od = overlayData[stateId];
    const overlay = document.createElement("div");
    overlay.className = "cal-overlay";
    overlay.dataset.stateId = stateId;

    // Add resize handles
    ["nw", "ne", "sw", "se"].forEach(corner => {
        const handle = document.createElement("div");
        handle.className = `cal-handle cal-handle-${corner}`;
        handle.dataset.corner = corner;
        overlay.appendChild(handle);
    });

    wrapper.appendChild(overlay);

    // Position the overlay based on current coordinates
    positionOverlay(overlay, od, img);

    // Set up drag and resize
    setupDrag(overlay, stateId, wrapper, img);
    setupResize(overlay, stateId, wrapper, img);

    // Reposition on window resize
    const observer = new ResizeObserver(() => {
        positionOverlay(overlay, overlayData[stateId], img);
    });
    observer.observe(wrapper);
}

function positionOverlay(overlay, od, img) {
    const imgW = img.clientWidth;
    const imgH = img.clientHeight;

    const topPx = (od.ymin / 1000) * imgH;
    const leftPx = (od.xmin / 1000) * imgW;
    const widthPx = ((od.xmax - od.xmin) / 1000) * imgW;
    const heightPx = ((od.ymax - od.ymin) / 1000) * imgH;

    overlay.style.top = `${topPx}px`;
    overlay.style.left = `${leftPx}px`;
    overlay.style.width = `${widthPx}px`;
    overlay.style.height = `${heightPx}px`;
}

// ── Drag Logic ────────────────────────────────────────────────

function setupDrag(overlay, stateId, wrapper, img) {
    let isDragging = false;
    let startX, startY, origLeft, origTop;

    overlay.addEventListener("mousedown", (e) => {
        // Don't drag if clicking a resize handle
        if (e.target.classList.contains("cal-handle")) return;

        isDragging = true;
        overlay.classList.add("dragging");
        startX = e.clientX;
        startY = e.clientY;
        origLeft = overlay.offsetLeft;
        origTop = overlay.offsetTop;
        e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
        if (!isDragging) return;

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        let newLeft = origLeft + dx;
        let newTop = origTop + dy;

        // Clamp within image bounds
        const imgW = img.clientWidth;
        const imgH = img.clientHeight;
        const oW = overlay.offsetWidth;
        const oH = overlay.offsetHeight;

        newLeft = Math.max(0, Math.min(newLeft, imgW - oW));
        newTop = Math.max(0, Math.min(newTop, imgH - oH));

        overlay.style.left = `${newLeft}px`;
        overlay.style.top = `${newTop}px`;

        updateCoords(stateId, overlay, img);
    });

    document.addEventListener("mouseup", () => {
        if (isDragging) {
            isDragging = false;
            overlay.classList.remove("dragging");
        }
    });
}

// ── Resize Logic ──────────────────────────────────────────────

function setupResize(overlay, stateId, wrapper, img) {
    const handles = overlay.querySelectorAll(".cal-handle");

    handles.forEach(handle => {
        let isResizing = false;
        let startX, startY, origRect;

        handle.addEventListener("mousedown", (e) => {
            isResizing = true;
            overlay.classList.add("dragging");
            startX = e.clientX;
            startY = e.clientY;
            origRect = {
                left: overlay.offsetLeft,
                top: overlay.offsetTop,
                width: overlay.offsetWidth,
                height: overlay.offsetHeight,
            };
            e.preventDefault();
            e.stopPropagation();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            const corner = handle.dataset.corner;
            const imgW = img.clientWidth;
            const imgH = img.clientHeight;

            let newLeft = origRect.left;
            let newTop = origRect.top;
            let newWidth = origRect.width;
            let newHeight = origRect.height;

            if (corner.includes("e")) {
                newWidth = Math.max(20, origRect.width + dx);
            }
            if (corner.includes("w")) {
                newWidth = Math.max(20, origRect.width - dx);
                newLeft = origRect.left + (origRect.width - newWidth);
            }
            if (corner.includes("s")) {
                newHeight = Math.max(20, origRect.height + dy);
            }
            if (corner.includes("n")) {
                newHeight = Math.max(20, origRect.height - dy);
                newTop = origRect.top + (origRect.height - newHeight);
            }

            // Clamp within image
            newLeft = Math.max(0, newLeft);
            newTop = Math.max(0, newTop);
            if (newLeft + newWidth > imgW) newWidth = imgW - newLeft;
            if (newTop + newHeight > imgH) newHeight = imgH - newTop;

            overlay.style.left = `${newLeft}px`;
            overlay.style.top = `${newTop}px`;
            overlay.style.width = `${newWidth}px`;
            overlay.style.height = `${newHeight}px`;

            updateCoords(stateId, overlay, img);
        });

        document.addEventListener("mouseup", () => {
            if (isResizing) {
                isResizing = false;
                overlay.classList.remove("dragging");
            }
        });
    });
}

// ── Coordinate Update ─────────────────────────────────────────

function updateCoords(stateId, overlay, img) {
    const imgW = img.clientWidth;
    const imgH = img.clientHeight;

    const ymin = Math.round((overlay.offsetTop / imgH) * 1000);
    const xmin = Math.round((overlay.offsetLeft / imgW) * 1000);
    const ymax = Math.round(((overlay.offsetTop + overlay.offsetHeight) / imgH) * 1000);
    const xmax = Math.round(((overlay.offsetLeft + overlay.offsetWidth) / imgW) * 1000);

    overlayData[stateId] = { ymin, xmin, ymax, xmax };

    // Update the live readout
    const coordEl = document.getElementById(`coord-val-${stateId}`);
    if (coordEl) {
        coordEl.textContent = `[${ymin}, ${xmin}, ${ymax}, ${xmax}]`;
    }
}

// ── Export ─────────────────────────────────────────────────────

function exportCorrectedJSON() {
    // Not used anymore — exportWithTimestamps is the primary export
    exportWithTimestamps();
}

async function exportWithTimestamps() {
    const output = graph.states.map(state => {
        const od = overlayData[state.state_id];
        // Use cached timestamps (loaded during init), fallback to "00:00"
        const timestamp = originalTimestamps[state.state_id] || "00:00";

        return {
            state_id: state.state_id,
            timestamp_in_video: timestamp,
            action_type: state.action_type,
            ui_element_name: state.ui_element_name,
            expected_input_value: state.expected_input_value || null,
            bounding_box_1000: [od.ymin, od.xmin, od.ymax, od.xmax],
            instructional_hint: state.instructional_hint,
        };
    });

    const blob = new Blob([JSON.stringify(output, null, 4)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "raw_metadata_corrected.json";
    a.click();
    URL.revokeObjectURL(url);

    showToast("Exported raw_metadata_corrected.json — rename and drop it into inputs/, then re-run the pipeline.");
}

// ── Toast ─────────────────────────────────────────────────────

function showToast(msg) {
    const toast = document.getElementById("cal-toast");
    toast.textContent = msg;
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 4000);
}

// ── Boot ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", initCalibrator);
