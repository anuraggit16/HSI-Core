const state = {
  connected: false,
  page: "overview",
  mode: "LIVE",
  processingActive: false,
  liveProcessingEnabled: false,
  mockMode: true,
  scan: { state: "IDLE", percent: 0, nx: 0, ny: 0, session: "" },
  heatmap: [],
  tempHistory: Array(80).fill(22.5),
  spectrum: { wavelengths: [], intensity: [] },
  datasets: [],
  errors: [],
  selectedDataset: null,
  cubePhase: 0,
  cubeView: {
    yaw: -0.62,
    pitch: -0.42,
    zoom: 1,
    panX: 0,
    panY: 0,
    dragging: false,
    dragMode: "rotate",
    lastX: 0,
    lastY: 0,
    probe: { x: 0.42, y: 0.7, l: 680, intensity: 0 },
  },
  uploadedImage: null,
  analysisCube: null,
  analysisSettings: {
    brightness: 1,
    contrast: 1,
    opacity: 1,
    gamma: 1,
    palette: "inferno",
    band: 1,
  },
  analysisView: {
    zoom: 1,
    panX: 0,
    panY: 0,
    dragging: false,
    lastX: 0,
    lastY: 0,
  },
  stage: {
    x: 0,
    y: 0,
    movingUntil: 0,
    activeJog: "",
    busy: false,
  },
};

const $ = (id) => document.getElementById(id);
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
const bindIf = (id, event, handler) => {
  const el = $(id);
  if (el) el.addEventListener(event, handler);
};

document.addEventListener("DOMContentLoaded", () => {
  document.body.dataset.page = state.page;
  bindClientErrorLogging();
  initClock();
  initCanvasSizing();
  bindControls();
  initCubeInteraction();
  initImageAnalysis();
  connectWebSocket();
  refreshStatus();
  fetchDatasets();
  fetchStorageConfig();
  fetchSpectralRange();
  fetchErrors();
  updateImageCount();
  updateModeUi();
  setInterval(() => !state.connected && refreshStatus(), 5000);
  setInterval(fetchErrors, 10000);
  setInterval(fetchDatasets, 9000);
  setInterval(() => state.processingActive && fetchSpectrum(), 1800);
  requestAnimationFrame(drawLoop);
});

function initClock() {
  setInterval(() => {
    $("clock").textContent = new Date().toLocaleTimeString("en-GB");
  }, 1000);
}

function initCanvasSizing() {
  const resize = () => {
    document.querySelectorAll("canvas").forEach((canvas) => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(1, Math.floor(rect.width * dpr));
      const height = Math.max(1, Math.floor(rect.height * dpr));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
    });
    drawStaticCanvases();
  };
  window.addEventListener("resize", resize);
  setTimeout(resize, 60);
}

function bindControls() {
  document.querySelectorAll(".page-tab[data-page]").forEach((button) => {
    button.addEventListener("click", () => setPage(button.dataset.page));
  });

  document.querySelectorAll(".mode-btn[data-mode]").forEach((button) => {
    button.addEventListener("click", () => setControlMode(button.dataset.mode));
  });
  $("btn-refresh").addEventListener("click", fetchDatasets);
  $("btn-browse-folder").addEventListener("click", browseSaveFolder);
  $("btn-apply-folder").addEventListener("click", applySaveFolder);
  $("btn-open-folder").addEventListener("click", openSaveFolder);
  $("dataset-search").addEventListener("input", renderDatasets);
  $("btn-start").addEventListener("click", startScan);
  $("btn-pause").addEventListener("click", pauseOrResumeScan);
  $("btn-stop").addEventListener("click", stopScan);
  $("btn-emergency").addEventListener("click", emergencyStop);
  $("btn-home").addEventListener("click", homeStage);
  $("btn-goto").addEventListener("click", gotoStage);
  $("btn-detect").addEventListener("click", detectHardware);
  $("btn-capture").addEventListener("click", () => toast("Live frame held in acquisition buffer", "info"));
  $("btn-apply-camera").addEventListener("click", applyCameraSettings);
  $("live-processing").addEventListener("change", () => setLiveProcessing($("live-processing").checked));

  document.querySelectorAll("[data-jog]").forEach((button) => {
    button.addEventListener("click", () => {
      const [axis, direction] = button.dataset.jog.split(":");
      jog(axis, Number(direction));
    });
  });

  ["wl-min", "wl-max", "scan-wl-min", "scan-wl-max"].forEach((id) => {
    $(id).addEventListener("input", updateWavelengthReadout);
  });

  ["x-start", "x-end", "x-step", "settling-s", "image-count", "auto-count", "scan-pattern"].forEach((id) => {
    $(id).addEventListener("input", () => {
      updateImageCount();
      drawScanMap();
    });
  });

  $("analysis-zoom").addEventListener("input", () => {
    state.analysisView.zoom = Number($("analysis-zoom").value);
    if (state.uploadedImage && state.uploadedImage.img) {
      renderImageAnalysis(state.uploadedImage.img, state.uploadedImage.analysis);
    }
  });

  bindIf("analysis-file-large", "change", () => {
    const file = $("analysis-file-large").files && $("analysis-file-large").files[0];
    if (!file) return;
    $("analysis-file-name-large").textContent = file.name;
    $("analysis-file-name").textContent = file.name;
    setPage("analysis");
    analyzeUploadedImage(file);
  });

  bindIf("analysis-zoom-large", "input", () => {
    state.analysisView.zoom = Number($("analysis-zoom-large").value);
    $("analysis-zoom").value = state.analysisView.zoom;
    rerenderUploadedImage();
  });

  ["analysis-opacity", "analysis-brightness", "analysis-contrast-ctrl", "analysis-gamma", "analysis-band"].forEach((id) => {
    bindIf(id, "input", () => {
      state.analysisSettings.opacity = Number($("analysis-opacity")?.value || 1);
      state.analysisSettings.brightness = Number($("analysis-brightness")?.value || 1);
      state.analysisSettings.contrast = Number($("analysis-contrast-ctrl")?.value || 1);
      state.analysisSettings.gamma = Number($("analysis-gamma")?.value || 1);
      state.analysisSettings.band = Number($("analysis-band")?.value || 1);
      rerenderUploadedImage();
    });
  });

  bindIf("analysis-palette", "change", () => {
    state.analysisSettings.palette = $("analysis-palette").value;
    rerenderUploadedImage();
  });

  bindIf("btn-reset-analysis", "click", resetAnalysisView);
  bindIf("btn-apply-camera-large", "click", applyCameraSettingsFromLarge);
  bindIf("btn-detect-large", "click", detectHardware);
  bindIf("btn-refresh-errors", "click", fetchErrors);
  bindIf("btn-home-diagnostics", "click", homeStage);
  bindIf("btn-detect-diagnostics", "click", detectHardware);

  ["slice-x", "slice-y", "slice-l"].forEach((id) => {
    $(id).addEventListener("input", updateCubeProbeFromControls);
  });
}

function setPage(page) {
  state.page = page || "overview";
  document.body.dataset.page = state.page;
  document.querySelectorAll(".page-tab[data-page]").forEach((button) => {
    button.classList.toggle("active", button.dataset.page === state.page);
  });
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
    drawStaticCanvases();
    rerenderUploadedImage();
  }, 40);
}

function resetAnalysisView() {
  state.analysisView = { zoom: 1, panX: 0, panY: 0, dragging: false, lastX: 0, lastY: 0 };
  state.analysisSettings = { brightness: 1, contrast: 1, opacity: 1, gamma: 1, palette: "inferno", band: 1 };
  ["analysis-zoom", "analysis-zoom-large"].forEach((id) => {
    const el = $(id);
    if (el) el.value = "1";
  });
  [
    ["analysis-opacity", "1"],
    ["analysis-brightness", "1"],
    ["analysis-contrast-ctrl", "1"],
    ["analysis-gamma", "1"],
    ["analysis-band", "1"],
  ].forEach(([id, value]) => {
    const el = $(id);
    if (el) el.value = value;
  });
  const palette = $("analysis-palette");
  if (palette) palette.value = "inferno";
  rerenderUploadedImage();
}

function rerenderUploadedImage() {
  if (state.uploadedImage && state.uploadedImage.img) {
    renderImageAnalysis(state.uploadedImage.img, state.uploadedImage.analysis);
  } else {
    drawEmptyAnalysis();
  }
}

function initCubeInteraction() {
  const canvas = $("cube-canvas");
  const wrap = $("cube-wrap");

  canvas.addEventListener("contextmenu", (event) => event.preventDefault());
  canvas.addEventListener("pointerdown", (event) => {
    state.cubeView.dragging = true;
    state.cubeView.dragMode = event.button === 2 || event.shiftKey ? "pan" : "rotate";
    state.cubeView.lastX = event.clientX;
    state.cubeView.lastY = event.clientY;
    wrap.classList.add("grabbing");
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (state.cubeView.dragging) {
      const dx = event.clientX - state.cubeView.lastX;
      const dy = event.clientY - state.cubeView.lastY;
      state.cubeView.lastX = event.clientX;
      state.cubeView.lastY = event.clientY;
      if (state.cubeView.dragMode === "pan") {
        state.cubeView.panX += dx * (window.devicePixelRatio || 1);
        state.cubeView.panY += dy * (window.devicePixelRatio || 1);
      } else {
        state.cubeView.yaw += dx * 0.008;
        state.cubeView.pitch = clamp(state.cubeView.pitch + dy * 0.006, -1.15, 0.75);
      }
    }
    updateCubeProbeFromPointer(event);
  });

  ["pointerup", "pointercancel", "pointerleave"].forEach((type) => {
    canvas.addEventListener(type, (event) => {
      state.cubeView.dragging = false;
      wrap.classList.remove("grabbing");
      try { canvas.releasePointerCapture(event.pointerId); } catch {}
    });
  });

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const nextZoom = state.cubeView.zoom * (event.deltaY > 0 ? 0.92 : 1.08);
    state.cubeView.zoom = clamp(nextZoom, 0.68, 1.85);
    updateCubeProbeFromPointer(event);
  }, { passive: false });

  updateCubeProbeFromControls();
}

function initImageAnalysis() {
  const input = $("analysis-file");
  if (!input) return;
  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (!file) return;
    $("analysis-file-name").textContent = file.name;
    const largeName = $("analysis-file-name-large");
    if (largeName) largeName.textContent = file.name;
    setPage("analysis");
    analyzeUploadedImage(file);
  });

  const bindCanvasPan = (canvas) => {
    if (!canvas) return;
    canvas.addEventListener("pointerdown", (event) => {
      state.analysisView.dragging = true;
      state.analysisView.lastX = event.clientX;
      state.analysisView.lastY = event.clientY;
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!state.analysisView.dragging) return;
      state.analysisView.panX += event.clientX - state.analysisView.lastX;
      state.analysisView.panY += event.clientY - state.analysisView.lastY;
      state.analysisView.lastX = event.clientX;
      state.analysisView.lastY = event.clientY;
      rerenderUploadedImage();
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach((type) => {
      canvas.addEventListener(type, (event) => {
        state.analysisView.dragging = false;
        try { canvas.releasePointerCapture(event.pointerId); } catch {}
      });
    });
  };

  bindCanvasPan($("analysis-preview"));
  bindCanvasPan($("analysis-preview-large"));
  drawEmptyAnalysis();
}

function bindClientErrorLogging() {
  window.addEventListener("error", (event) => {
    reportUiError(event.message || "Unhandled UI error", event.filename || "window");
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason && (event.reason.message || String(event.reason));
    reportUiError(reason || "Unhandled UI promise rejection", "promise");
  });
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  ws.onopen = () => {
    state.connected = true;
    $("overlay").style.display = "none";
    $("led-link").className = "led ok";
    $("link-label").textContent = "Connected";
    toast("Telemetry connected", "success");
    setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 25000);
  };

  ws.onclose = () => {
    state.connected = false;
    $("overlay").style.display = "flex";
    $("overlay-status").textContent = "Reconnecting telemetry...";
    $("led-link").className = "led off";
    $("link-label").textContent = "Offline";
    setTimeout(connectWebSocket, 1800);
  };

  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "telemetry") updateTelemetry(payload);
  };
}

async function setControlMode(mode) {
  try {
    const result = await postJson("/api/system/mode", { mode });
    state.mode = result.mode;
    state.processingActive = Boolean(result.processing_active);
    updateModeUi();
    if (state.processingActive) fetchSpectrum();
  } catch (error) {
    toast(error.message || "Mode change rejected", "error");
  }
}

async function setLiveProcessing(enabled) {
  try {
    const result = await postJson("/api/processing", { enabled });
    state.liveProcessingEnabled = Boolean(result.live_processing_enabled);
    state.processingActive = Boolean(result.processing_active);
    updateModeUi();
    if (state.processingActive) fetchSpectrum();
  } catch (error) {
    $("live-processing").checked = state.liveProcessingEnabled;
    toast(error.message || "Processing setting rejected", "error");
  }
}

function reportUiError(message, source = "ui") {
  fetch("/api/errors/client", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, source, severity: "ERROR" }),
  }).catch(() => {});
}

function updateModeUi() {
  document.body.dataset.mode = state.mode.toLowerCase();
  document.querySelectorAll(".mode-btn[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
  $("mode-label").textContent = `${state.mockMode ? "Simulation" : "Hardware"} | ${state.mode}`;
  $("live-processing").checked = state.liveProcessingEnabled;
  $("processing-state").textContent = state.processingActive ? "ON" : "OFF";
  $("processing-state").className = state.processingActive ? "ok" : "";
  document.querySelectorAll(".upload-analysis input, .upload-analysis button").forEach((el) => {
    el.disabled = false;
  });
}

async function refreshStatus() {
  try {
    const data = await fetchJson("/api/status");
    updateTelemetry({ hardware: data.hardware, scan: data.scan, system: data.system, config: data.config, events: [] });
  } catch {
    $("link-label").textContent = "Waiting";
  }
}

function updateTelemetry(data) {
  if (data.system) {
    state.mode = data.system.control_mode || state.mode;
    state.processingActive = Boolean(data.system.processing_active);
    state.liveProcessingEnabled = Boolean(data.system.live_processing_enabled);
    updateModeUi();
  }

  if (data.config && data.config.spectral_range) {
    updateSpectralRangeUi(data.config.spectral_range);
  }

  if (data.hardware) {
    const hw = data.hardware;
    const xPos = Number(hw.stage_x_mm ?? hw.stage_mm ?? 0);
    const stageMoving = Boolean(hw.stage_x_moving ?? hw.stage_moving);
    const stageStatus = hw.stage_status || (stageMoving ? "moving" : "idle");
    state.mockMode = Boolean(hw.mock_mode);
    $("stage-x-pos").textContent = `${xPos.toFixed(3)} mm`;
    $("stage-y-pos").textContent = stageStatus;
    $("camera-temp").textContent = `${Number(hw.camera_temp || 0).toFixed(1)} C`;
    $("temp-readout").textContent = `${Number(hw.camera_temp || 0).toFixed(1)} C`;
    const tempLarge = $("camera-temp-large");
    if (tempLarge) tempLarge.textContent = `${Number(hw.camera_temp || 0).toFixed(1)} C`;
    $("focus-readout").textContent = `${hw.lens_focus ?? "--"} ppm`;
    $("illumination-state").textContent = hw.illumination ? "On" : "Off";
    $("illumination-state").className = hw.illumination ? "ok" : "";
    updateCameraConnection(hw);
    updateStageConnection(hw);
    updateDiagnosticsStatus(hw);
    $("mode-label").textContent = `${state.mockMode ? "Simulation" : "Hardware"} | ${state.mode}`;
    $("led-mode").className = state.mockMode ? "led warn" : "led ok";
    state.tempHistory.push(Number(hw.camera_temp || 22.5));
    state.tempHistory.shift();
    drawTempSparkline();
  }

  if (data.scan) {
    const scan = data.scan;
    state.scan = {
      state: String(scan.state || "IDLE"),
      percent: Number(scan.percent || 0),
      nx: Number(scan.nx || 0),
      ny: Number(scan.ny || 0),
      session: scan.session_name || "",
      framesDone: Number(scan.frames_done || 0),
      totalFrames: Number(scan.total_frames || 0),
      eta: Number(scan.eta_seconds || 0),
    };
    if (["STOPPED", "ERROR"].includes(state.scan.state) && state.mode !== "ANALYSIS") {
      state.processingActive = false;
    }
    updateScanUi();
  }

  if (Array.isArray(data.events)) {
    data.events.forEach(handleEvent);
  }

}

function updateScanUi() {
  const s = state.scan;
  $("scan-state").textContent = s.state;
  $("scan-eta").textContent = `ETA ${s.eta || "--"}s`;
  $("scan-counter").textContent = `${s.framesDone || 0}/${s.totalFrames || 0}`;
  $("scan-progress").style.width = `${clamp(s.percent, 0, 100)}%`;
  $("cube-readout").textContent = s.nx ? `${s.nx} position scan | ${s.framesDone}/${s.totalFrames}` : "X/lambda volume";

  const idle = ["IDLE", "STOPPED", "ERROR", "ScanState.IDLE"].includes(s.state);
  const running = s.state === "RUNNING" || s.state === "ScanState.RUNNING";
  const paused = s.state === "PAUSED" || s.state === "ScanState.PAUSED";
  $("btn-start").disabled = !idle;
  $("btn-pause").disabled = !(running || paused);
  $("btn-stop").disabled = idle;
  $("btn-pause").textContent = paused ? "Resume" : "Pause";
  setStageControlsDisabled(state.stage.busy || running || paused);
}

function handleEvent(event) {
  if (event.type === "frame") {
    const nx = Number(event.nx || state.scan.nx || 1);
    const ny = Number(event.ny || state.scan.ny || 1);
    if (state.heatmap.length !== nx * ny) {
      state.heatmap = Array(nx * ny).fill(0);
    }
    const index = Number(event.yi) * nx + Number(event.xi);
    state.heatmap[index] = Number(event.intensity || 0);
    drawScanMap();
  }

  if (event.type === "log") {
    toast(event.message, event.message.includes("EMERGENCY") ? "error" : "info");
  }

  if (event.type === "error") {
    fetchErrors();
    toast(event.message || "System error recorded", "error");
  }
}

async function startScan() {
  const xStart = Number($("x-start").value);
  const xEnd = Number($("x-end").value);
  const xStep = Number($("x-step").value);
  const payload = {
    x_start: xStart,
    x_end: xEnd,
    x_step: xStep,
    number_of_images: Number($("image-count").value),
    auto_calculate_images: $("auto-count").value === "true",
    exposure_ms: Number($("exposure-ms").value),
    settling_s: Number($("settling-s").value),
    settling_time_s: Number($("settling-s").value),
    raster: $("scan-pattern").value,
    scan_pattern: $("scan-pattern").value,
    save_png: $("save-png").checked,
    save_tiff: $("save-tiff").checked,
    session_name: $("session-name").value,
    wavelength_min_nm: Number($("scan-wl-min").value),
    wavelength_max_nm: Number($("scan-wl-max").value),
  };

  try {
    const result = await postJson("/api/scan/start", payload);
    state.mode = "SCAN";
    state.processingActive = true;
    updateModeUi();
    state.heatmap = Array(result.nx * result.ny).fill(0);
    toast(`Scan started: ${result.session}`, "success");
    fetchDatasets();
  } catch (error) {
    toast(error.message || "Scan failed to start", "error");
  }
}

async function pauseOrResumeScan() {
  const paused = state.scan.state === "PAUSED" || state.scan.state === "ScanState.PAUSED";
  await postJson(`/api/scan/${paused ? "resume" : "pause"}`);
}

async function stopScan() {
  await postJson("/api/scan/stop");
  state.processingActive = false;
  updateModeUi();
  toast("Scan stop requested", "info");
}

async function emergencyStop() {
  await postJson("/api/scan/emergency");
  state.mode = "LIVE";
  state.processingActive = false;
  updateModeUi();
  toast("Emergency stop sent", "error");
}

async function homeStage() {
  if (state.stage.busy) return;
  state.stage.busy = true;
  setStageControlsDisabled(true);
  markStageMoving("x", -1, Math.max(1, state.stage.x));
  try {
    const result = await postJson("/api/stage/home");
    if (result.hardware) updateTelemetry({ hardware: result.hardware, events: [] });
    $("goto-x").value = "0.00";
    toast(result.message || "Stage homed to zero", result.physical_home ? "success" : "info");
  } catch (error) {
    reportUiError(error.message || "Home failed", "stage/home");
    toast(error.message || "Home failed", "error");
  } finally {
    state.stage.busy = false;
    clearStageMoving();
    setStageControlsDisabled(false);
    refreshStatus();
  }
}

async function jog(axis, direction) {
  if (state.stage.busy) return;
  state.stage.busy = true;
  setStageControlsDisabled(true);
  const step = Number($("jog-step").value);
  markStageMoving(axis, direction, step);
  try {
    const result = await postJson("/api/stage/jog", { axis, direction, step_mm: step });
    if (result.hardware) updateTelemetry({ hardware: result.hardware, events: [] });
  } catch {
    clearStageMoving();
    toast("Stage jog rejected", "error");
  } finally {
    state.stage.busy = false;
    setStageControlsDisabled(false);
    refreshStatus();
  }
}

async function gotoStage() {
  if (state.stage.busy) return;
  state.stage.busy = true;
  setStageControlsDisabled(true);
  const x = Number($("goto-x").value);
  markStageMoving("x", x >= state.stage.x ? 1 : -1, Math.abs(x - state.stage.x));
  try {
    const result = await postJson("/api/stage/goto", { x_mm: x });
    if (result.hardware) updateTelemetry({ hardware: result.hardware, events: [] });
    toast(`Moving stage to ${x.toFixed(3)} mm`, "info");
  } catch (error) {
    clearStageMoving();
    toast(error.message || "Stage move rejected", "error");
  } finally {
    state.stage.busy = false;
    setStageControlsDisabled(false);
    refreshStatus();
  }
}

function setStageControlsDisabled(disabled) {
  ["btn-home", "btn-goto", "goto-x", "jog-step"].forEach((id) => {
    const el = $(id);
    if (el) el.disabled = disabled;
  });
  document.querySelectorAll("[data-jog]").forEach((button) => {
    button.disabled = disabled;
  });
}

function markStageMoving(axis, direction, step) {
  const label = `${axis.toUpperCase()}${direction > 0 ? "+" : "-"}`;
  state.stage.movingUntil = Date.now() + Math.max(900, step * 420);
  state.stage.activeJog = label;
  updateJogButtonHighlight(label);
  $("stage-motion").textContent = `${state.mockMode ? "Sim moving" : "Moving"} ${label} | Step ${step.toFixed(2)} mm`;
  $("stage-motion").classList.add("moving");
  $("stage-label").textContent = `${state.mockMode ? "Stage Sim Moving" : "Stage Moving"} ${label}`;
  $("led-stage").className = "led warn";
}

function clearStageMoving() {
  state.stage.movingUntil = 0;
  state.stage.activeJog = "";
  updateJogButtonHighlight("");
  $("stage-motion").classList.remove("moving");
}

function updateCameraConnection(hw) {
  const cameraConnected = hw.camera_connected === true;
  const cameraStatus = String(hw.camera_status || (cameraConnected ? "connected" : "disconnected"));
  const streamAvailable = hw.camera_stream_available !== false;
  const fallback = Boolean(hw.camera_fallback_stream);

  const setCameraText = (label, led, feedText, feedClass) => {
    $("camera-label").textContent = label;
    $("led-camera").className = led;
    $("camera-feed-status").textContent = feedText;
    $("camera-feed-status").className = feedClass;
    const largeStatus = $("camera-large-status");
    if (largeStatus) {
      largeStatus.textContent = feedText;
      largeStatus.className = feedClass || "";
    }
    const pageState = $("camera-page-state");
    if (pageState) pageState.textContent = label;
    const statusLarge = $("camera-status-large");
    if (statusLarge) statusLarge.textContent = cameraStatus;
    const modeLarge = $("camera-mode-large");
    if (modeLarge) modeLarge.textContent = fallback ? "Fallback" : (state.mockMode ? "Simulation" : "Hardware");
    const streamLarge = $("camera-stream-health");
    if (streamLarge) streamLarge.textContent = streamAvailable ? "Active" : "Waiting";
  };

  if (cameraStatus === "simulation") {
    setCameraText("Camera Simulated", "led warn", "Simulation output", "warn");
    return;
  }

  if (cameraConnected) {
    setCameraText("Camera Connected", "led ok", "Live camera", "ok");
    return;
  }

  if (fallback || streamAvailable) {
    setCameraText("Camera Fallback", "led warn", "Fallback stream active", "warn");
    return;
  }

  setCameraText("Camera Disconnected", "led off", "No camera signal", "offline");
}

function updateJogButtonHighlight(label) {
  document.querySelectorAll("[data-jog]").forEach((button) => {
    const [axis, direction] = button.dataset.jog.split(":");
    const buttonLabel = `${axis.toUpperCase()}${Number(direction) > 0 ? "+" : "-"}`;
    button.classList.toggle("moving", buttonLabel === label);
  });
}

function updateStageConnection(hw) {
  const x = Number(hw.stage_x_mm ?? hw.stage_mm ?? 0);
  const y = 0;
  const stageConnected = hw.stage_connected === true || hw.stage_physical_connected === true;
  const stageAvailable = stageConnected || hw.stage_available === true || hw.stage_fallback === true || hw.stage_status === "simulation";
  const backendMoving = Boolean(hw.stage_x_moving ?? hw.stage_moving);
  const positionChanged = Math.abs(x - state.stage.x) > 0.0005;
  const moving = stageAvailable && (backendMoving || positionChanged || Date.now() < state.stage.movingUntil);
  state.stage.x = x;
  state.stage.y = y;

  if ((hw.stage_fallback || hw.stage_status === "simulation") && !moving) {
    $("stage-label").textContent = hw.stage_fallback ? "Stage Fallback" : "Stage Simulated";
    $("led-stage").className = "led warn";
    $("stage-motion").textContent = `${hw.stage_fallback ? "Fallback" : "Simulated"} stage | X ${x.toFixed(3)} mm`;
    $("stage-motion").classList.remove("moving");
    state.stage.activeJog = "";
    updateJogButtonHighlight("");
    return;
  }

  if (!stageAvailable) {
    $("stage-label").textContent = "Stage Disconnected";
    $("led-stage").className = "led off";
    $("stage-motion").textContent = "Stage disconnected";
    $("stage-motion").classList.remove("moving");
    updateJogButtonHighlight("");
    return;
  }

  if (moving) {
    const active = state.stage.activeJog ? ` ${state.stage.activeJog}` : "";
    $("stage-label").textContent = stageConnected ? `Stage Moving${active}` : `Stage Sim Moving${active}`;
    $("led-stage").className = "led warn";
    $("stage-motion").textContent = `${stageConnected ? "Moving" : "Sim moving"}${active} | X ${x.toFixed(3)} mm`;
    $("stage-motion").classList.add("moving");
  } else {
    $("stage-label").textContent = stageConnected ? "Stage Connected" : "Stage Fallback";
    $("led-stage").className = stageConnected ? "led ok" : "led warn";
    $("stage-motion").textContent = `${stageConnected ? "Stage idle" : "Fallback stage"} | X ${x.toFixed(3)} mm`;
    $("stage-motion").classList.remove("moving");
    state.stage.activeJog = "";
    updateJogButtonHighlight("");
  }
}

async function applyCameraSettings() {
  const exposure = Number($("exposure-ms").value);
  const gain = Number($("gain-db").value);
  await postJson("/api/camera/settings", { exposure_ms: exposure, gain_db: gain });
  $("camera-caption").textContent = `Exposure ${exposure} ms | Gain ${gain} dB`;
  const capLarge = $("camera-caption-large");
  if (capLarge) capLarge.textContent = `Exposure ${exposure} ms | Gain ${gain} dB`;
  const pageExposure = $("camera-page-exposure");
  const pageGain = $("camera-page-gain");
  if (pageExposure) pageExposure.value = exposure;
  if (pageGain) pageGain.value = gain;
  toast("Camera settings applied", "success");
}

async function applyCameraSettingsFromLarge() {
  const exposure = Number($("camera-page-exposure").value);
  const gain = Number($("camera-page-gain").value);
  $("exposure-ms").value = exposure;
  $("gain-db").value = gain;
  await applyCameraSettings();
}

async function detectHardware() {
  try {
    await postJson("/api/hardware/detect");
    await refreshStatus();
    toast("Hardware detection complete", "success");
  } catch {
    toast("Hardware detection failed", "error");
  }
}

async function fetchDatasets() {
  try {
    state.datasets = await fetchJson("/api/datasets");
    renderDatasets();
  } catch {
    state.datasets = [];
  }
}

function updateDiagnosticsStatus(hw = {}) {
  const stage = $("diag-stage");
  const camera = $("diag-camera");
  const processing = $("diag-processing");
  const mode = $("diag-mode");
  const errors = $("diag-errors");
  if (stage) {
    stage.textContent = `${hw.stage_status || "--"} | X ${Number(hw.stage_x_mm ?? hw.stage_mm ?? 0).toFixed(3)} mm`;
  }
  if (camera) {
    camera.textContent = `${hw.camera_status || "--"}${hw.camera_fallback_stream ? " | fallback" : ""}`;
  }
  if (processing) processing.textContent = state.processingActive ? "ON" : "OFF";
  if (mode) mode.textContent = `${state.mockMode ? "Simulation/Fallback" : "Hardware"} | ${state.mode}`;
  if (errors) errors.textContent = String(state.errors.length);
}

async function fetchErrors() {
  try {
    const result = await fetchJson("/api/errors");
    state.errors = Array.isArray(result.errors) ? result.errors.slice(-50).reverse() : [];
  } catch {
    state.errors = [];
  }
  const errorLabel = $("error-label");
  const ledErrors = $("led-errors");
  if (errorLabel) errorLabel.textContent = `Errors ${state.errors.length}`;
  if (ledErrors) ledErrors.className = state.errors.length ? "led warn" : "led ok";
  const diagErrors = $("diag-errors");
  if (diagErrors) diagErrors.textContent = String(state.errors.length);
  renderErrors();
  renderDiagnosticsErrors();
}

function renderErrors() {
  const list = $("queue-list");
  if (!list) return;

  list.innerHTML = "";

  if (!state.errors.length) {
    const empty = document.createElement("div");
    empty.className = "queue-row error-row empty";
    const label = document.createElement("span");
    const status = document.createElement("b");
    label.textContent = "No errors recorded";
    status.textContent = "OK";
    empty.append(label, status);
    list.appendChild(empty);
    return;
  }

  state.errors.forEach((entry) => {
    const row = document.createElement("div");
    const category = classifyError(entry);
    const critical = ["camera", "stage", "scan"].includes(category);
    row.className = `queue-row error-row ${category} ${critical ? "critical" : "warning"}`;
    const label = document.createElement("span");
    const status = document.createElement("b");
    label.textContent = `${formatErrorTime(entry.timestamp)} ${entry.message || entry.line || "Unknown error"}`;
    status.textContent = category.toUpperCase();
    row.append(label, status);
    list.appendChild(row);
  });
}

function renderDiagnosticsErrors() {
  const list = $("diagnostics-errors");
  if (!list) return;
  list.innerHTML = "";

  if (!state.errors.length) {
    const row = document.createElement("div");
    row.className = "queue-row error-row empty";
    const label = document.createElement("span");
    const status = document.createElement("b");
    label.textContent = "No saved errors";
    status.textContent = "OK";
    row.append(label, status);
    list.appendChild(row);
    return;
  }

  state.errors.forEach((entry) => {
    const row = document.createElement("div");
    const category = classifyError(entry);
    row.className = `queue-row error-row ${category} ${["camera", "stage", "scan"].includes(category) ? "critical" : "warning"}`;
    const label = document.createElement("span");
    const status = document.createElement("b");
    label.textContent = `${entry.timestamp || "--"} | ${entry.message || entry.line || "Unknown error"}`;
    status.textContent = (entry.severity || category).toUpperCase();
    row.append(label, status);
    list.appendChild(row);
  });
}

function classifyError(entry) {
  const text = `${entry.category || ""} ${entry.module || ""} ${entry.message || ""}`.toLowerCase();
  if (text.includes("camera")) return "camera";
  if (text.includes("stage")) return "stage";
  if (text.includes("scan")) return "scan";
  return "system";
}

function formatErrorTime(value) {
  if (!value) return "--:--:--";
  return String(value).split(" ").pop() || value;
}

function renderDatasets() {
  const query = $("dataset-search").value.toLowerCase();
  const tree = $("session-tree");
  const filtered = state.datasets.filter((d) => d.name.toLowerCase().includes(query));
  tree.innerHTML = `<li class="tree-group">Data</li>`;

  filtered.forEach((dataset) => {
    const item = document.createElement("li");
    item.className = `tree-item ${state.selectedDataset === dataset.name ? "active" : ""}`;
    item.textContent = `${dataset.name}`;
    item.addEventListener("click", () => selectDataset(dataset));
    tree.appendChild(item);
  });
}

function selectDataset(dataset) {
  state.selectedDataset = dataset.name;
  renderDatasets();
  const meta = dataset.metadata || {};
  $("meta-tbody").innerHTML = `
    <tr><td>Name</td><td>${dataset.name}</td></tr>
    <tr><td>Frames</td><td>${dataset.frame_count || 0}</td></tr>
    <tr><td>Grid</td><td>${meta.nx || meta.num_x || "-"} x ${meta.ny || meta.num_y || "-"}</td></tr>
    <tr><td>Wavelength</td><td>${meta.wavelength_min_nm || 400}-${meta.wavelength_max_nm || 1000} nm</td></tr>
    <tr><td>Pattern</td><td>${meta.raster || "-"}</td></tr>
    <tr><td>Storage</td><td>${$("save-folder").value || "scan_images"}</td></tr>
  `;
  loadDatasetMap(dataset.name);
  if (meta.analysis) {
    loadAnalysisDataset(dataset);
  }
}

async function loadDatasetMap(name) {
  try {
    const img = new Image();
    img.onload = () => {
      const canvas = $("scan-map");
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.src = `/api/datasets/${encodeURIComponent(name)}/map?ts=${Date.now()}`;
  } catch {
    drawScanMap();
  }
}

async function fetchSpectrum() {
  if (!state.processingActive) return;
  try {
    state.spectrum = await fetchJson("/api/analysis/spectrum/live");
    if (state.spectrum.processing_active === false) return;
    updateSpectralStats();
  } catch {
    const wavelengths = Array.from({ length: 120 }, (_, i) => 400 + i * 5);
    const intensity = wavelengths.map((w) => 50 + 300 * Math.exp(-((w - 690) ** 2) / 700));
    state.spectrum = { wavelengths_nm: wavelengths, intensity };
  }
}

function loadAnalysisDataset(dataset) {
  const meta = dataset.metadata || {};
  const source = meta.analysis || {};
  const profile = source.profile || [];
  const histogram = source.histogram || [];
  const analysis = {
    width: Number(source.width || meta.nx || 0),
    height: Number(source.height || meta.ny || 0),
    bands: Number(source.bands || meta.spectral_bands || 1),
    mean: Number(source.mean || 0),
    peak: Number(source.max || 0),
    contrast: Math.max(0, Number(source.max || 0) - Number(source.min || 0)),
    std: Number(source.std || 0),
    snr: Number(source.snr_estimate || 0),
    hist: histogram.length ? histogram : (profile.length ? profile : Array(64).fill(0)),
    profile,
    roi: null,
    bias: `${source.dtype || "TIFF"} | ${source.axes || "axes --"}`,
    previewMode: source.preview_mode || "preview",
    session: dataset.name,
    metadata: `${formatBytes(meta.bytes || 0)} | ${(source.shape || []).join(" x ") || "--"}`,
  };

  state.analysisCube = {
    shape: source.shape || [analysis.bands, analysis.height, analysis.width],
    bands: analysis.bands,
    profile,
    width: analysis.width,
    height: analysis.height,
    session: dataset.name,
  };
  state.spectrum = {
    processing_active: true,
    wavelengths_nm: wavelengthsForProfile(profile),
    intensity: profile,
  };
  updateAnalysisControls(analysis);
  updateAnalysisFields(analysis);
  updateSpectralStats();
  $("cube-readout").textContent = `Dataset cube | ${analysis.width} x ${analysis.height} x ${analysis.bands}`;

  const img = new Image();
  img.onload = () => {
    state.uploadedImage = { name: dataset.name, img, analysis };
    renderImageAnalysis(img, analysis);
    setPage("analysis");
  };
  img.onerror = () => {
    state.uploadedImage = null;
    renderAnalysisMetadata(analysis);
    setPage("analysis");
  };
  img.src = `/api/datasets/${encodeURIComponent(dataset.name)}/frame/0/0?ts=${Date.now()}`;
}

async function fetchSpectralRange() {
  try {
    updateSpectralRangeUi(await fetchJson("/api/spectral/range"));
  } catch {
    updateSpectralRangeUi({ min_wavelength_nm: 400, max_wavelength_nm: 1000, bands: 120 });
  }
}

function updateSpectralRangeUi(range) {
  $("spectral-range").textContent = `${range.min_wavelength_nm}-${range.max_wavelength_nm} nm`;
  $("spectral-bands").textContent = `${range.bands}`;
  $("wl-min").min = range.min_wavelength_nm;
  $("wl-min").max = range.max_wavelength_nm;
  $("wl-max").min = range.min_wavelength_nm;
  $("wl-max").max = range.max_wavelength_nm;
}

function updateImageCount() {
  if ($("auto-count").value !== "true") return;
  const start = Number($("x-start").value);
  const end = Number($("x-end").value);
  const step = Math.max(0.0001, Number($("x-step").value));
  $("image-count").value = Math.max(1, Math.round(Math.abs(end - start) / step) + 1);
}

function updateSpectralStats() {
  const data = state.spectrum.intensity || [];
  if (!data.length) return;
  const peak = Math.max(...data);
  const mean = data.reduce((a, b) => a + b, 0) / data.length;
  const noise = Math.sqrt(data.reduce((a, b) => a + (b - mean) ** 2, 0) / data.length) || 1;
  $("peak-value").textContent = peak.toFixed(1);
  $("mean-value").textContent = mean.toFixed(1);
  $("snr-value").textContent = (peak / noise).toFixed(1);
}

function updateWavelengthReadout() {
  let min = Number($("wl-min").value);
  let max = Number($("wl-max").value);
  if (min > max) [min, max] = [max, min];
  $("wl-readout").textContent = `${min} nm - ${max} nm`;
  $("scan-wl-min").value = min;
  $("scan-wl-max").value = max;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let text = await response.text();
    try { text = JSON.parse(text).detail || text; } catch {}
    throw new Error(text);
  }
  return response.json();
}

function drawLoop() {
  if (state.processingActive) {
    state.cubePhase += 0.01;
  }
  drawCube();
  drawSpectralChart();
  if (state.processingActive) {
    requestAnimationFrame(drawLoop);
  } else {
    setTimeout(() => requestAnimationFrame(drawLoop), 1000);
  }
}

function drawStaticCanvases() {
  drawScanMap();
  drawHistogram();
  drawTempSparkline();
  drawRoiCanvases();
  if (state.uploadedImage && state.uploadedImage.img) {
    renderImageAnalysis(state.uploadedImage.img, state.uploadedImage.analysis);
  } else {
    drawEmptyAnalysis();
  }
}

async function fetchStorageConfig() {
  try {
    const storage = await fetchJson("/api/storage");
    $("save-folder").value = storage.save_folder || "scan_images";
    const storageCell = document.querySelector("#meta-tbody tr:last-child td:last-child");
    if (storageCell) storageCell.textContent = storage.save_folder || "scan_images";
  } catch {
    $("save-folder").value = "scan_images";
  }
}

async function browseSaveFolder() {
  try {
    const result = await postJson("/api/storage/browse", { current_folder: $("save-folder").value });
    if (result.save_folder) {
      $("save-folder").value = result.save_folder;
      await fetchDatasets();
      toast("Save folder selected", "success");
    }
  } catch (error) {
    toast(error.message || "Folder browser could not open", "error");
  }
}

async function applySaveFolder() {
  const folder = $("save-folder").value.trim();
  if (!folder) {
    toast("Enter a save folder", "error");
    return;
  }
  try {
    const result = await postJson("/api/storage", { save_folder: folder });
    $("save-folder").value = result.save_folder;
    await fetchDatasets();
    toast("Save folder applied", "success");
  } catch (error) {
    toast(error.message || "Save folder rejected", "error");
  }
}

async function openSaveFolder() {
  try {
    await postJson("/api/storage/open", { save_folder: $("save-folder").value });
    toast("Opening save folder", "info");
  } catch (error) {
    toast(error.message || "Folder could not be opened", "error");
  }
}

function clearCanvas(canvas, color = "#050707") {
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  return ctx;
}

function drawCube() {
  const canvas = $("cube-canvas");
  const ctx = clearCanvas(canvas, "#030404");
  const metrics = cubeMetrics(canvas);
  const dpr = window.devicePixelRatio || 1;
  const faces = [
    { color: "#071b34", alpha: 0.76, pts: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]] },
    { color: "#0c3642", alpha: 0.72, pts: [[1, 0, 0], [1, 0, 1], [1, 1, 1], [1, 1, 0]] },
    { color: "#0c244f", alpha: 0.74, pts: [[0, 1, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1]] },
    { color: "#07152f", alpha: 0.66, pts: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]] },
    { color: "#0b2832", alpha: 0.62, pts: [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]] },
  ].map((face) => ({
    ...face,
    projected: face.pts.map((point) => projectCubePoint(point, metrics)),
    depth: face.pts.reduce((sum, point) => sum + rotateCubePoint(point, metrics).z, 0) / face.pts.length,
  })).sort((a, b) => a.depth - b.depth);

  faces.forEach((face) => drawFace(ctx, face.projected.map((p) => [p.x, p.y]), face.color, face.alpha));

  for (let z = 0; z <= 1.001; z += 0.075) {
    const heat = cubeIntensity(0.56, 0.52, z) / 620;
    const a = 0.12 + 0.22 * clamp(heat, 0, 1);
    const plane = [
      projectCubePoint([0, 0, z], metrics),
      projectCubePoint([1, 0, z], metrics),
      projectCubePoint([1, 1, z], metrics),
      projectCubePoint([0, 1, z], metrics),
    ];
    drawFace(ctx, plane.map((p) => [p.x, p.y]), heatColor(heat), a);
  }

  drawCubeGrid(ctx, metrics);
  drawCubeWire(ctx, metrics);
  drawCubeProbe(ctx, metrics);

  const axisX = projectCubePoint([1.16, 0, 0], metrics);
  const axisY = projectCubePoint([1, 1.14, 0], metrics);
  const axisL = projectCubePoint([0, 1, 1.15], metrics);
  ctx.globalAlpha = 1;
  ctx.fillStyle = "#c9d7d2";
  ctx.font = `${Math.max(11, canvas.width / 75)}px ${getComputedStyle(document.body).fontFamily}`;
  ctx.fillText("X [mm]", axisX.x, axisX.y);
  ctx.fillText("Y [mm]", axisY.x, axisY.y);
  ctx.fillText("Lambda [nm]", axisL.x - 24 * dpr, axisL.y - 4 * dpr);
}

function cubeMetrics(canvas) {
  const view = state.cubeView;
  return {
    cx: canvas.width * 0.5 + view.panX,
    cy: canvas.height * 0.54 + view.panY,
    scale: Math.min(canvas.width, canvas.height) * 0.58 * view.zoom,
    yaw: view.yaw,
    pitch: view.pitch,
  };
}

function rotateCubePoint(point, metrics) {
  const x = point[0] - 0.5;
  const y = point[1] - 0.5;
  const z = point[2] - 0.5;
  const cy = Math.cos(metrics.yaw);
  const sy = Math.sin(metrics.yaw);
  const cp = Math.cos(metrics.pitch);
  const sp = Math.sin(metrics.pitch);
  const rx = x * cy - z * sy;
  const rz = x * sy + z * cy;
  const ry = y * cp - rz * sp;
  const rz2 = y * sp + rz * cp;
  return { x: rx, y: ry, z: rz2 };
}

function projectCubePoint(point, metrics) {
  const rotated = rotateCubePoint(point, metrics);
  return {
    x: metrics.cx + rotated.x * metrics.scale,
    y: metrics.cy - rotated.y * metrics.scale,
    z: rotated.z,
  };
}

function drawCubeGrid(ctx, metrics) {
  ctx.globalAlpha = 0.52;
  ctx.lineWidth = Math.max(1, metrics.scale / 360);
  for (let i = 0; i <= 10; i += 1) {
    const t = i / 10;
    drawProjectedLine(ctx, [t, 0, 0], [t, 1, 0], metrics, "#335c70");
    drawProjectedLine(ctx, [0, t, 0], [1, t, 0], metrics, "#335c70");
    drawProjectedLine(ctx, [1, t, 0], [1, t, 1], metrics, "#2c6a73");
    drawProjectedLine(ctx, [t, 1, 0], [t, 1, 1], metrics, "#3b5792");
  }
  ctx.globalAlpha = 1;
}

function drawCubeWire(ctx, metrics) {
  const edges = [
    [[0, 0, 0], [1, 0, 0]], [[1, 0, 0], [1, 1, 0]], [[1, 1, 0], [0, 1, 0]], [[0, 1, 0], [0, 0, 0]],
    [[0, 0, 1], [1, 0, 1]], [[1, 0, 1], [1, 1, 1]], [[1, 1, 1], [0, 1, 1]], [[0, 1, 1], [0, 0, 1]],
    [[0, 0, 0], [0, 0, 1]], [[1, 0, 0], [1, 0, 1]], [[1, 1, 0], [1, 1, 1]], [[0, 1, 0], [0, 1, 1]],
  ];
  ctx.lineWidth = Math.max(1, metrics.scale / 260);
  edges.forEach(([a, b]) => drawProjectedLine(ctx, a, b, metrics, "#d7e4ff"));
}

function drawProjectedLine(ctx, a, b, metrics, color) {
  const p1 = projectCubePoint(a, metrics);
  const p2 = projectCubePoint(b, metrics);
  drawLine(ctx, [p1.x, p1.y], [p2.x, p2.y], color);
}

function drawCubeProbe(ctx, metrics) {
  const probe = state.cubeView.probe;
  const x = clamp(probe.x / 100, 0, 1);
  const y = clamp(probe.y / 100, 0, 1);
  const z = clamp((probe.l - 400) / 600, 0, 1);
  const p = projectCubePoint([x, y, z], metrics);
  const floor = projectCubePoint([x, y, 0], metrics);
  const ceiling = projectCubePoint([x, y, 1], metrics);
  const dpr = window.devicePixelRatio || 1;

  ctx.globalAlpha = 0.9;
  ctx.setLineDash([4 * dpr, 5 * dpr]);
  drawLine(ctx, [floor.x, floor.y], [ceiling.x, ceiling.y], "#f2b34b");
  ctx.setLineDash([]);

  ctx.fillStyle = "#f7e483";
  ctx.strokeStyle = "#171100";
  ctx.lineWidth = 2 * dpr;
  ctx.beginPath();
  ctx.arc(p.x, p.y, 5.2 * dpr, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = "#f6f9ed";
  ctx.font = `${11 * dpr}px ${getComputedStyle(document.body).fontFamily}`;
  ctx.fillText(`${Math.round(probe.l)} nm`, p.x + 8 * dpr, p.y - 8 * dpr);
  ctx.globalAlpha = 1;
}

function updateCubeProbeFromControls() {
  const x = Number($("slice-x").value);
  const y = Number($("slice-y").value);
  const l = Number($("slice-l").value);
  setCubeProbe(x, y, l);
}

function updateCubeProbeFromPointer(event) {
  const canvas = $("cube-canvas");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const px = (event.clientX - rect.left) * dpr;
  const py = (event.clientY - rect.top) * dpr;
  const metrics = cubeMetrics(canvas);
  const xNorm = clamp((px - metrics.cx) / (metrics.scale * 0.95) + 0.5, 0, 1);
  const yNorm = clamp(0.5 - (py - metrics.cy) / (metrics.scale * 0.9), 0, 1);
  const l = Number($("slice-l").value);
  $("slice-x").value = Math.round(xNorm * 100);
  $("slice-y").value = Math.round(yNorm * 100);
  setCubeProbe(xNorm * 100, yNorm * 100, l);
}

function setCubeProbe(x, y, l) {
  const z = clamp((l - 400) / 600, 0, 1);
  const intensity = cubeIntensity(x / 100, y / 100, z);
  state.cubeView.probe = { x, y, l, intensity };
  $("cube-x-detail").textContent = `${x.toFixed(1)} mm`;
  $("cube-y-detail").textContent = `${y.toFixed(1)} mm`;
  $("cube-l-detail").textContent = `${Math.round(l)} nm`;
  $("cube-i-detail").textContent = `${intensity.toFixed(1)} a.u.`;
}

function cubeIntensity(x, y, z) {
  const spatialA = Math.exp(-(((x - 0.58) ** 2) / 0.032 + ((y - 0.42) ** 2) / 0.044));
  const spatialB = 0.62 * Math.exp(-(((x - 0.28) ** 2) / 0.018 + ((y - 0.72) ** 2) / 0.025));
  const profile = state.analysisCube?.profile || [];
  const profileIndex = Math.min(profile.length - 1, Math.max(0, Math.round(z * Math.max(0, profile.length - 1))));
  const profileMax = profile.length ? Math.max(1, ...profile) : 1;
  const uploadedSpectral = profile.length ? Number(profile[profileIndex] || 0) / profileMax : 0;
  const spectralA = profile.length ? uploadedSpectral : Math.exp(-((z - 0.47) ** 2) / 0.012);
  const spectralB = profile.length ? uploadedSpectral * 0.4 : 0.5 * Math.exp(-((z - 0.78) ** 2) / 0.006);
  const ripple = 0.08 * (Math.sin((x + state.cubePhase) * 8) + Math.cos((y - state.cubePhase) * 7));
  return 34 + 520 * clamp((spatialA + spatialB) * (0.55 + spectralA + spectralB) / 2.15 + ripple, 0, 1);
}

function drawFace(ctx, points, color, alpha) {
  ctx.globalAlpha = alpha;
  ctx.fillStyle = color;
  ctx.beginPath();
  points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.closePath();
  ctx.fill();
}

function drawWire(ctx, points, color) {
  ctx.globalAlpha = 1;
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.beginPath();
  points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.closePath();
  ctx.stroke();
}

function drawLine(ctx, a, b, color) {
  ctx.strokeStyle = color;
  ctx.beginPath();
  ctx.moveTo(a[0], a[1]);
  ctx.lineTo(b[0], b[1]);
  ctx.stroke();
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function drawSpectralChart() {
  const canvas = $("spectral-chart");
  const ctx = clearCanvas(canvas, "#080a0a");
  const values = state.spectrum.intensity || [];
  const labels = state.spectrum.wavelengths_nm || state.spectrum.wavelengths || [];
  drawGrid(ctx, canvas.width, canvas.height, 7, 6);
  if (values.length < 2) return;

  const pad = 34;
  const min = Math.min(...values);
  const max = Math.max(...values);
  ctx.strokeStyle = "#f2f6f4";
  ctx.lineWidth = 1.5 * (window.devicePixelRatio || 1);
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = pad + (i / (values.length - 1)) * (canvas.width - pad * 1.35);
    const y = canvas.height - pad - ((v - min) / Math.max(1, max - min)) * (canvas.height - pad * 1.45);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#9ba7a2";
  ctx.font = `${11 * (window.devicePixelRatio || 1)}px sans-serif`;
  ctx.fillText(`${labels[0] || 400} nm`, pad, canvas.height - 9);
  ctx.fillText(`${labels[labels.length - 1] || 1000} nm`, canvas.width - pad * 2, canvas.height - 9);
  ctx.save();
  ctx.translate(12, canvas.height * 0.58);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Intensity [a.u.]", 0, 0);
  ctx.restore();
}

function drawGrid(ctx, w, h, cols, rows) {
  ctx.strokeStyle = "#273030";
  ctx.lineWidth = 1;
  for (let i = 1; i < cols; i += 1) {
    const x = (w / cols) * i;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let i = 1; i < rows; i += 1) {
    const y = (h / rows) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
}

function drawScanMap() {
  const canvas = $("scan-map");
  const ctx = clearCanvas(canvas, "#050707");
  const w = canvas.width;
  const h = canvas.height;
  drawGrid(ctx, w, h, 8, 6);

  const xStart = Number($("x-start").value);
  const xEnd = Number($("x-end").value);
  const xStep = Math.max(0.0001, Number($("x-step").value));
  const nx = state.scan.nx || Math.max(2, Math.round(Math.abs(xEnd - xStart) / xStep) + 1);
  const ny = state.scan.ny || 1;
  const values = state.heatmap.length === nx * ny ? state.heatmap : null;
  const max = values ? Math.max(1, ...values) : 1;
  const cellW = w / nx;
  const cellH = h / ny;

  for (let y = 0; y < ny; y += 1) {
    for (let x = 0; x < nx; x += 1) {
      const idx = y * nx + x;
      const t = values ? values[idx] / max : ((Math.sin(x * .4) + Math.cos(y * .7) + 2) / 4) * .45;
      ctx.fillStyle = heatColor(t);
      ctx.globalAlpha = values ? 0.95 : 0.28;
      ctx.fillRect(x * cellW, y * cellH, Math.max(1, cellW), Math.max(1, cellH));
    }
  }
  ctx.globalAlpha = 1;

  const pattern = $("scan-pattern").value;
  ctx.strokeStyle = "#dfeaff";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let y = 0; y < ny; y += 1) {
    const yPos = (y + .5) * cellH;
    const left = cellW * .5;
    const right = w - cellW * .5;
    if (pattern === "serpentine" && y % 2) {
      ctx.lineTo(right, yPos);
      ctx.lineTo(left, yPos);
    } else {
      ctx.lineTo(left, yPos);
      ctx.lineTo(right, yPos);
    }
  }
  ctx.stroke();
}

function drawHistogram() {
  const canvas = $("histogram");
  const ctx = clearCanvas(canvas, "#050707");
  const values = state.heatmap.length ? state.heatmap : Array.from({ length: 160 }, (_, i) => 42 + 80 * Math.exp(-((i - 70) ** 2) / 900));
  const bins = Array(22).fill(0);
  const maxVal = Math.max(1, ...values);
  values.forEach((v) => bins[Math.min(bins.length - 1, Math.floor((v / maxVal) * bins.length))] += 1);
  const maxBin = Math.max(1, ...bins);
  const barW = canvas.width / bins.length;
  bins.forEach((v, i) => {
    const barH = (v / maxBin) * canvas.height * .86;
    ctx.fillStyle = i > bins.length * .72 ? "#f2b34b" : "#59b7ff";
    ctx.fillRect(i * barW + 1, canvas.height - barH, Math.max(1, barW - 2), barH);
  });
}

function drawTempSparkline() {
  const canvas = $("temp-spark");
  const ctx = clearCanvas(canvas, "#050707");
  drawSeries(ctx, canvas, state.tempHistory, "#59b7ff", 18, 32);
}

function drawRoiCanvases() {
  const s1 = Array.from({ length: 44 }, (_, i) => 30 + 16 * Math.sin(i * .28) + 6 * Math.sin(i * .9));
  const s2 = Array.from({ length: 44 }, (_, i) => 22 + 12 * Math.cos(i * .22) + 9 * Math.sin(i * .48));
  drawSeries($("roi-spark-1").getContext("2d"), $("roi-spark-1"), s1, "#ff6a6a");
  drawSeries($("roi-spark-2").getContext("2d"), $("roi-spark-2"), s2, "#5de072");
  drawMiniMap($("roi-map-1"), 0.35);
  drawMiniMap($("roi-map-2"), 0.68);
}

function drawSeries(ctx, canvas, values, color, fixedMin = null, fixedMax = null) {
  ctx.fillStyle = "#050707";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const min = fixedMin ?? Math.min(...values);
  const max = fixedMax ?? Math.max(...values);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.4 * (window.devicePixelRatio || 1);
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / (values.length - 1)) * canvas.width;
    const y = canvas.height - ((v - min) / Math.max(1, max - min)) * canvas.height;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawMiniMap(canvas, center) {
  const ctx = clearCanvas(canvas, "#050707");
  const n = 16;
  const cw = canvas.width / n;
  const ch = canvas.height / n;
  for (let y = 0; y < n; y += 1) {
    for (let x = 0; x < n; x += 1) {
      const dx = x / n - center;
      const dy = y / n - .52;
      ctx.fillStyle = heatColor(Math.exp(-(dx * dx + dy * dy) / .022));
      ctx.fillRect(x * cw, y * ch, Math.ceil(cw), Math.ceil(ch));
    }
  }
}

function drawEmptyAnalysis() {
  ["analysis-preview", "analysis-preview-large"].forEach((id) => {
    const preview = $(id);
    if (!preview) return;
    const pctx = clearCanvas(preview, "#050707");
    pctx.fillStyle = "#65706c";
    pctx.font = `${11 * (window.devicePixelRatio || 1)}px ${getComputedStyle(document.body).fontFamily}`;
    pctx.fillText("No image loaded", 12 * (window.devicePixelRatio || 1), 24 * (window.devicePixelRatio || 1));
  });
  ["analysis-histogram", "analysis-histogram-large", "analysis-spectrum"].forEach((id) => {
    const canvas = $(id);
    if (canvas) clearCanvas(canvas, "#050707");
  });
  updateAnalysisFields(null);
}

function analyzeUploadedImage(file) {
  if (state.mode !== "ANALYSIS") {
    setControlMode("ANALYSIS");
  }

  if (/\.(tif|tiff)$/i.test(file.name)) {
    analyzeTiffFile(file);
    return;
  }

  const url = URL.createObjectURL(file);
  const img = new Image();
  img.onload = () => {
    URL.revokeObjectURL(url);
    const analysis = sampleImage(img);
    state.uploadedImage = { name: file.name, img, analysis };
    state.analysisCube = { shape: [analysis.height, analysis.width, analysis.bands], bands: analysis.bands, profile: analysis.profile, width: analysis.width, height: analysis.height, session: file.name };
    state.spectrum = { processing_active: true, wavelengths_nm: wavelengthsForProfile(analysis.profile), intensity: analysis.profile };
    $("cube-readout").textContent = `Loaded image | ${analysis.width} x ${analysis.height}`;
    updateAnalysisControls(analysis);
    updateAnalysisFields(analysis);
    renderImageAnalysis(img, analysis);
    toast("Image analysis ready", "success");
  };
  img.onerror = () => {
    URL.revokeObjectURL(url);
    toast("Image format could not be decoded in browser", "error");
  };
  img.src = url;
}

function analyzeTiffFile(file) {
  const form = new FormData();
  form.append("file", file);
  toast("TIFF upload started", "info");

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/analysis/tiff/upload");

  xhr.upload.onprogress = (event) => {
    if (!event.lengthComputable) return;
    const pct = Math.round((event.loaded / event.total) * 100);
    $("analysis-file-name").textContent = `${file.name} | ${pct}%`;
    const largeName = $("analysis-file-name-large");
    if (largeName) largeName.textContent = `${file.name} | ${pct}%`;
  };

  xhr.onload = () => {
    if (xhr.status < 200 || xhr.status >= 300) {
      reportUiError(xhr.responseText || "TIFF upload failed", "analysis/upload");
      toast(xhr.responseText || "TIFF upload failed", "error");
      fetchErrors();
      return;
    }

    let result = {};
    try {
      result = JSON.parse(xhr.responseText);
    } catch (error) {
      reportUiError(error.message || "Invalid TIFF upload response", "analysis/upload");
      toast("TIFF response could not be read", "error");
      return;
    }
    handleTiffResult(file.name, result);
    $("analysis-file-name").textContent = file.name;
    const largeName = $("analysis-file-name-large");
    if (largeName) largeName.textContent = file.name;
    toast("TIFF analysis ready", "success");
  };

  xhr.onerror = () => {
    reportUiError("TIFF upload network failure", "analysis/upload");
    toast("TIFF upload failed", "error");
    fetchErrors();
  };

  xhr.send(form);
}

function handleTiffResult(name, result) {
  const meta = result.metadata || {};
  const profile = result.profile || meta.profile || [];
  const histogram = result.histogram || meta.histogram || [];
  const shape = Array.isArray(meta.shape) ? meta.shape : [];
  const bands = Number(meta.bands || (shape.length > 2 ? shape[0] : 1));
  const analysis = {
    width: Number(meta.width || (shape.length > 1 ? shape[shape.length - 1] : 0)),
    height: Number(meta.height || (shape.length > 0 ? shape[shape.length - 2] : 0)),
    bands,
    mean: Number(meta.mean || 0),
    peak: Number(meta.max || 0),
    contrast: Math.max(0, Number(meta.max || 0) - Number(meta.min || 0)),
    std: Number(meta.std || 0),
    snr: Number(meta.snr_estimate || 0),
    hist: histogram.length ? histogram : (profile.length ? profile : Array(64).fill(0)),
    profile,
    roi: null,
    bias: `${meta.dtype || "TIFF"} | ${meta.axes || "axes --"}`,
    previewMode: meta.preview_mode || "preview",
    session: result.session || "",
    metadata: `${formatBytes(result.bytes || 0)} | ${shape.join(" x ") || "--"}`,
  };
  state.analysisCube = {
    shape,
    bands,
    profile,
    width: analysis.width,
    height: analysis.height,
    session: analysis.session || name,
  };
  state.spectrum = {
    processing_active: true,
    wavelengths_nm: wavelengthsForProfile(profile),
    intensity: profile,
  };
  state.processingActive = true;
  $("cube-readout").textContent = `Uploaded cube | ${analysis.width} x ${analysis.height} x ${bands}`;
  updateSpectralStats();
  updateAnalysisControls(analysis);
  updateAnalysisFields(analysis);
  setPage("analysis");
  fetchDatasets();

  if (result.png_base64) {
    const img = new Image();
    img.onload = () => {
      state.uploadedImage = { name, img, analysis };
      renderImageAnalysis(img, analysis);
    };
    img.src = `data:image/png;base64,${result.png_base64}`;
  } else {
    state.uploadedImage = null;
    drawEmptyAnalysis();
    renderAnalysisMetadata(analysis);
  }
}

function renderAnalysisMetadata(analysis) {
  $("analysis-size").textContent = analysis.width && analysis.height ? `${analysis.width} x ${analysis.height}` : "--";
  $("analysis-mean").textContent = `${analysis.mean.toFixed(1)} a.u.`;
  $("analysis-peak").textContent = `${analysis.peak.toFixed(1)} a.u.`;
  $("analysis-contrast").textContent = `${analysis.contrast.toFixed(1)}`;
  $("analysis-roi").textContent = "--";
  $("analysis-bias").textContent = analysis.bias;
  $("analysis-meta").textContent = analysis.metadata;
  drawAnalysisHistogram(analysis.hist);
  drawAnalysisSpectrum(analysis.profile || []);
  updateAnalysisFields(analysis);
}

function wavelengthsForProfile(profile = []) {
  const count = Math.max(1, profile.length || state.analysisCube?.bands || 1);
  const min = Number($("scan-wl-min")?.value || 400);
  const max = Number($("scan-wl-max")?.value || 1000);
  return Array.from({ length: count }, (_, i) => count === 1 ? min : min + (i / (count - 1)) * (max - min));
}

function updateAnalysisControls(analysis) {
  const bands = Math.max(1, Number(analysis?.bands || 1));
  const band = $("analysis-band");
  if (band) {
    band.max = String(bands);
    band.value = String(Math.min(Number(band.value || 1), bands));
  }
  const session = $("analysis-session-lg");
  if (session) session.textContent = analysis?.session || `${bands} band cube`;
}

function updateAnalysisFields(analysis) {
  const values = analysis ? {
    size: analysis.width && analysis.height ? `${analysis.width} x ${analysis.height}` : "--",
    bands: `${analysis.bands || 1}`,
    mean: `${Number(analysis.mean || 0).toFixed(2)} a.u.`,
    peak: `${Number(analysis.peak || 0).toFixed(2)} a.u.`,
    std: `${Number(analysis.std || 0).toFixed(2)}`,
    contrast: `${Number(analysis.contrast || 0).toFixed(2)}`,
    snr: analysis.snr ? `${Number(analysis.snr).toFixed(2)}` : "--",
    preview: analysis.previewMode || "--",
    metadata: analysis.metadata || "--",
  } : {
    size: "--",
    bands: "--",
    mean: "--",
    peak: "--",
    std: "--",
    contrast: "--",
    snr: "--",
    preview: "--",
    metadata: "--",
  };

  Object.entries(values).forEach(([key, value]) => {
    document.querySelectorAll(`[data-analysis-field="${key}"]`).forEach((node) => {
      node.textContent = value;
    });
  });
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit ? 1 : 0)} ${units[unit]}`;
}

function sampleImage(img) {
  const maxSide = 420;
  const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const w = Math.max(1, Math.round(img.naturalWidth * scale));
  const h = Math.max(1, Math.round(img.naturalHeight * scale));
  const sample = document.createElement("canvas");
  sample.width = w;
  sample.height = h;
  const ctx = sample.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, w, h);
  const data = ctx.getImageData(0, 0, w, h).data;
  const hist = Array(64).fill(0);
  let sum = 0;
  let sumSq = 0;
  let peak = 0;
  let rSum = 0;
  let gSum = 0;
  let bSum = 0;
  const lumas = [];

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    lumas.push(luma);
    sum += luma;
    sumSq += luma * luma;
    rSum += r;
    gSum += g;
    bSum += b;
    peak = Math.max(peak, luma);
    hist[Math.min(hist.length - 1, Math.floor((luma / 256) * hist.length))] += 1;
  }

  const count = Math.max(1, lumas.length);
  const mean = sum / count;
  const contrast = Math.sqrt(Math.max(0, sumSq / count - mean * mean));
  const threshold = percentile(lumas, 0.9);
  let bx = 0;
  let by = 0;
  let brightCount = 0;
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      const luma = lumas[y * w + x];
      if (luma >= threshold) {
        bx += x;
        by += y;
        brightCount += 1;
      }
    }
  }
  const colorMeans = [rSum / count, gSum / count, bSum / count];
  const channels = ["R", "G", "B"];
  const dominant = channels[colorMeans.indexOf(Math.max(...colorMeans))];
  const brightPct = (brightCount / count) * 100;

  return {
    width: img.naturalWidth,
    height: img.naturalHeight,
    bands: 3,
    sampleWidth: w,
    sampleHeight: h,
    mean,
    peak,
    contrast,
    std: contrast,
    snr: peak / Math.max(1, contrast),
    hist,
    profile: hist,
    roi: brightCount ? { x: (bx / brightCount) / w, y: (by / brightCount) / h, pct: brightPct } : null,
    bias: `${dominant} ${Math.max(...colorMeans).toFixed(0)}`,
    previewMode: "RGB image",
  };
}

function percentile(values, p) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * p))];
}

function renderImageAnalysis(img, analysis) {
  ["analysis-preview", "analysis-preview-large"].forEach((id) => {
    const canvas = $(id);
    if (canvas) renderAnalysisCanvas(canvas, img, analysis);
  });

  const sizeText = `${analysis.width} x ${analysis.height}`;
  $("analysis-size").textContent = sizeText;
  $("analysis-mean").textContent = `${analysis.mean.toFixed(1)} a.u.`;
  $("analysis-peak").textContent = `${analysis.peak.toFixed(1)} a.u.`;
  $("analysis-contrast").textContent = `${analysis.contrast.toFixed(1)}`;
  $("analysis-roi").textContent = analysis.roi ? `${analysis.roi.pct.toFixed(1)}% @ ${Math.round(analysis.roi.x * 100)},${Math.round(analysis.roi.y * 100)}` : "--";
  $("analysis-bias").textContent = analysis.bias;
  $("analysis-meta").textContent = analysis.metadata || "manual";
  drawAnalysisHistogram(analysis.hist);
  drawAnalysisSpectrum(analysis.profile || []);
  updateAnalysisFields(analysis);
}

function renderAnalysisCanvas(canvas, img, analysis) {
  const ctx = clearCanvas(canvas, "#050707");
  const scale = Math.min(canvas.width / img.naturalWidth, canvas.height / img.naturalHeight) * state.analysisView.zoom;
  const drawW = img.naturalWidth * scale;
  const drawH = img.naturalHeight * scale;
  const dpr = window.devicePixelRatio || 1;
  const dx = (canvas.width - drawW) / 2 + state.analysisView.panX * dpr;
  const dy = (canvas.height - drawH) / 2 + state.analysisView.panY * dpr;
  const settings = state.analysisSettings;
  ctx.save();
  ctx.globalAlpha = settings.opacity;
  ctx.filter = `brightness(${settings.brightness}) contrast(${settings.contrast})`;
  ctx.drawImage(img, dx, dy, drawW, drawH);
  ctx.restore();

  if (settings.gamma !== 1 && drawW > 0 && drawH > 0) {
    applyGammaToCanvas(ctx, canvas, settings.gamma);
  }

  if (analysis.roi) {
    const x = dx + analysis.roi.x * drawW;
    const y = dy + analysis.roi.y * drawH;
    ctx.strokeStyle = "#f2b34b";
    ctx.lineWidth = 2 * dpr;
    ctx.beginPath();
    ctx.arc(x, y, 10 * dpr, 0, Math.PI * 2);
    ctx.stroke();
    drawLine(ctx, [x - 14 * dpr, y], [x + 14 * dpr, y], "#f2b34b");
    drawLine(ctx, [x, y - 14 * dpr], [x, y + 14 * dpr], "#f2b34b");
  }

  const overlay = $("analysis-overlay-readout");
  if (overlay) {
    const band = Math.min(Number(settings.band || 1), Number(analysis.bands || 1));
    overlay.textContent = `${analysis.previewMode || "Preview"} | Band ${band}/${analysis.bands || 1}`;
  }
}

function applyGammaToCanvas(ctx, canvas, gamma) {
  try {
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const inv = 1 / Math.max(0.01, gamma);
    for (let i = 0; i < image.data.length; i += 4) {
      image.data[i] = 255 * ((image.data[i] / 255) ** inv);
      image.data[i + 1] = 255 * ((image.data[i + 1] / 255) ** inv);
      image.data[i + 2] = 255 * ((image.data[i + 2] / 255) ** inv);
    }
    ctx.putImageData(image, 0, 0);
  } catch {
    // Canvas filters can fail on unusual browser security settings; the preview still remains visible.
  }
}

function drawAnalysisHistogram(hist) {
  ["analysis-histogram", "analysis-histogram-large"].forEach((id) => {
    const canvas = $(id);
    if (!canvas) return;
    const ctx = clearCanvas(canvas, "#050707");
    const values = hist && hist.length ? hist : Array(64).fill(0);
    const max = Math.max(1, ...values);
    const barW = canvas.width / values.length;
    values.forEach((value, index) => {
      const t = index / Math.max(1, values.length - 1);
      const h = (value / max) * canvas.height * 0.88;
      ctx.fillStyle = paletteColor(t);
      ctx.fillRect(index * barW, canvas.height - h, Math.max(1, barW - 1), h);
    });
  });
}

function drawAnalysisSpectrum(profile) {
  const canvas = $("analysis-spectrum");
  if (!canvas) return;
  const ctx = clearCanvas(canvas, "#050707");
  const values = profile && profile.length ? profile : [];
  drawGrid(ctx, canvas.width, canvas.height, 6, 4);
  if (values.length < 2) return;
  const pad = 28 * (window.devicePixelRatio || 1);
  const min = Math.min(...values);
  const max = Math.max(...values);
  ctx.strokeStyle = "#ffcf6a";
  ctx.lineWidth = 1.7 * (window.devicePixelRatio || 1);
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = pad + (index / (values.length - 1)) * (canvas.width - pad * 1.4);
    const y = canvas.height - pad - ((value - min) / Math.max(1e-6, max - min)) * (canvas.height - pad * 1.55);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function paletteColor(t) {
  const v = clamp(t, 0, 1);
  const palette = state.analysisSettings.palette;
  if (palette === "gray") {
    const g = Math.round(v * 255);
    return `rgb(${g},${g},${g})`;
  }
  if (palette === "viridis") {
    return `rgb(${Math.round(68 + v * 185)},${Math.round(8 + v * 210)},${Math.round(85 + (1 - v) * 85)})`;
  }
  if (palette === "thermal") {
    return `rgb(${Math.round(40 + v * 215)},${Math.round(30 + v * 125)},${Math.round(110 - v * 90)})`;
  }
  return heatColor(v);
}

function heatColor(t) {
  const v = clamp(t, 0, 1);
  if (v < 0.2) return `rgb(${Math.round(8 + v * 80)},${Math.round(20 + v * 90)},${Math.round(120 + v * 360)})`;
  if (v < 0.45) return `rgb(${Math.round(20 + v * 60)},${Math.round(70 + v * 310)},${Math.round(210 - v * 230)})`;
  if (v < 0.7) return `rgb(${Math.round(10 + v * 260)},${Math.round(140 + v * 120)},${Math.round(50 - v * 40)})`;
  return `rgb(${Math.round(210 + v * 45)},${Math.round(210 - v * 95)},${Math.round(40 - v * 30)})`;
}

function toast(message, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  $("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}
