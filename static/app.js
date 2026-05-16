const state = {
  connected: false,
  mockMode: true,
  scan: { state: "IDLE", percent: 0, nx: 0, ny: 0, session: "" },
  heatmap: [],
  tempHistory: Array(80).fill(22.5),
  spectrum: { wavelengths: [], intensity: [] },
  datasets: [],
  selectedDataset: null,
  cubePhase: 0,
};

const $ = (id) => document.getElementById(id);
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

document.addEventListener("DOMContentLoaded", () => {
  initClock();
  initCanvasSizing();
  bindControls();
  connectWebSocket();
  refreshStatus();
  fetchDatasets();
  fetchSpectrum();
  setInterval(refreshStatus, 2500);
  setInterval(fetchDatasets, 9000);
  setInterval(fetchSpectrum, 1400);
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
  $("btn-refresh").addEventListener("click", fetchDatasets);
  $("dataset-search").addEventListener("input", renderDatasets);
  $("btn-start").addEventListener("click", startScan);
  $("btn-pause").addEventListener("click", pauseOrResumeScan);
  $("btn-stop").addEventListener("click", () => postJson("/api/scan/stop"));
  $("btn-emergency").addEventListener("click", emergencyStop);
  $("btn-home").addEventListener("click", () => postJson("/api/stage/home").then(() => toast("Homing stage", "info")));
  $("btn-detect").addEventListener("click", detectHardware);
  $("btn-capture").addEventListener("click", () => toast("Live frame held in acquisition buffer", "info"));
  $("btn-apply-camera").addEventListener("click", applyCameraSettings);

  document.querySelectorAll("[data-jog]").forEach((button) => {
    button.addEventListener("click", () => {
      const [axis, direction] = button.dataset.jog.split(":");
      jog(axis, Number(direction));
    });
  });

  ["wl-min", "wl-max", "scan-wl-min", "scan-wl-max"].forEach((id) => {
    $(id).addEventListener("input", updateWavelengthReadout);
  });

  ["x-range", "y-range", "x-step", "y-step", "scan-pattern"].forEach((id) => {
    $(id).addEventListener("input", drawScanMap);
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

async function refreshStatus() {
  try {
    const data = await fetchJson("/api/status");
    updateTelemetry({ hardware: data.hardware, scan: data.scan, events: [] });
  } catch {
    $("link-label").textContent = "Waiting";
  }
}

function updateTelemetry(data) {
  if (data.hardware) {
    const hw = data.hardware;
    state.mockMode = Boolean(hw.mock_mode);
    $("stage-x-pos").textContent = `${Number(hw.stage_x_mm || 0).toFixed(3)} mm`;
    $("stage-y-pos").textContent = `${Number(hw.stage_y_mm || 0).toFixed(3)} mm`;
    $("camera-temp").textContent = `${Number(hw.camera_temp || 0).toFixed(1)} C`;
    $("temp-readout").textContent = `${Number(hw.camera_temp || 0).toFixed(1)} C`;
    $("focus-readout").textContent = `${hw.lens_focus ?? "--"} ppm`;
    $("illumination-state").textContent = hw.illumination ? "On" : "Off";
    $("illumination-state").className = hw.illumination ? "ok" : "";
    $("mode-label").textContent = state.mockMode ? "Simulation" : "Hardware";
    $("led-mode").className = state.mockMode ? "led warn" : "led ok";
    state.tempHistory.push(Number(hw.camera_temp || 22.5));
    state.tempHistory.shift();
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
    updateScanUi();
  }

  if (Array.isArray(data.events)) {
    data.events.forEach(handleEvent);
  }

  drawStaticCanvases();
}

function updateScanUi() {
  const s = state.scan;
  $("scan-state").textContent = s.state;
  $("scan-eta").textContent = `ETA ${s.eta || "--"}s`;
  $("scan-progress").style.width = `${clamp(s.percent, 0, 100)}%`;
  $("cube-readout").textContent = s.nx && s.ny ? `${s.nx} x ${s.ny} scan | ${s.framesDone}/${s.totalFrames}` : "X/Y/lambda volume";

  const idle = s.state === "IDLE" || s.state === "ScanState.IDLE";
  const running = s.state === "RUNNING" || s.state === "ScanState.RUNNING";
  const paused = s.state === "PAUSED" || s.state === "ScanState.PAUSED";
  $("btn-start").disabled = !idle;
  $("btn-pause").disabled = !(running || paused);
  $("btn-stop").disabled = idle;
  $("btn-pause").textContent = paused ? "Resume" : "Pause";
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
  }

  if (event.type === "log") {
    toast(event.message, event.message.includes("EMERGENCY") ? "error" : "info");
  }
}

async function startScan() {
  const xRange = Number($("x-range").value);
  const yRange = Number($("y-range").value);
  const xStep = Number($("x-step").value);
  const yStep = Number($("y-step").value);
  const payload = {
    x_start: 80,
    x_end: 80 + xRange,
    x_step: xStep,
    y_start: 80,
    y_end: 80 + yRange,
    y_step: yStep,
    exposure_ms: Number($("exposure-ms").value),
    settling_s: 0.1,
    raster: $("scan-pattern").value,
    session_name: $("session-name").value,
    wavelength_min_nm: Number($("scan-wl-min").value),
    wavelength_max_nm: Number($("scan-wl-max").value),
  };

  try {
    const result = await postJson("/api/scan/start", payload);
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

async function emergencyStop() {
  await postJson("/api/scan/emergency");
  toast("Emergency stop sent", "error");
}

async function jog(axis, direction) {
  const step = Number($("jog-step").value);
  try {
    await postJson("/api/stage/jog", { axis, direction, step_mm: step });
  } catch {
    toast("Stage jog rejected", "error");
  }
}

async function applyCameraSettings() {
  const exposure = Number($("exposure-ms").value);
  const gain = Number($("gain-db").value);
  await postJson("/api/camera/settings", { exposure_ms: exposure, gain_db: gain });
  $("camera-caption").textContent = `Exposure ${exposure} ms | Gain ${gain} dB`;
  toast("Camera settings applied", "success");
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
  `;
  loadDatasetMap(dataset.name);
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
  try {
    state.spectrum = await fetchJson("/api/analysis/spectrum/live");
    updateSpectralStats();
  } catch {
    const wavelengths = Array.from({ length: 120 }, (_, i) => 400 + i * 5);
    const intensity = wavelengths.map((w) => 50 + 300 * Math.exp(-((w - 690) ** 2) / 700));
    state.spectrum = { wavelengths_nm: wavelengths, intensity };
  }
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
  state.cubePhase += 0.01;
  drawCube();
  drawSpectralChart();
  requestAnimationFrame(drawLoop);
}

function drawStaticCanvases() {
  drawScanMap();
  drawHistogram();
  drawTempSparkline();
  drawRoiCanvases();
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
  const w = canvas.width;
  const h = canvas.height;
  const cx = w * 0.46;
  const cy = h * 0.48;
  const size = Math.min(w, h) * 0.48;
  const depth = size * 0.34;
  const phase = state.cubePhase;

  const front = [
    [cx - size * 0.56, cy - size * 0.38],
    [cx + size * 0.54, cy - size * 0.22],
    [cx + size * 0.42, cy + size * 0.54],
    [cx - size * 0.62, cy + size * 0.42],
  ];
  const back = front.map(([x, y]) => [x + depth, y - depth * 0.62]);

  drawFace(ctx, [back[0], back[1], front[1], front[0]], "#10315d", 0.74);
  drawFace(ctx, [front[1], back[1], back[2], front[2]], "#0c4b5d", 0.7);
  drawFace(ctx, front, "#082d73", 0.78);

  for (let i = 0; i < 34; i += 1) {
    const t = i / 33;
    const band = Math.sin(t * Math.PI * 4 + phase * 2) * 0.5 + 0.5;
    const heat = Math.exp(-((t - 0.48) ** 2) / 0.028) + 0.5 * Math.exp(-((t - 0.76) ** 2) / 0.012);
    const color = heatColor(clamp((band * 0.25 + heat * 0.75), 0, 1));
    const x1 = lerp(front[0][0], front[1][0], t);
    const y1 = lerp(front[0][1], front[1][1], t);
    const x2 = lerp(front[3][0], front[2][0], t);
    const y2 = lerp(front[3][1], front[2][1], t);
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.45;
    ctx.lineWidth = Math.max(1, w / 540);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  ctx.globalAlpha = 1;
  drawWire(ctx, [front[0], front[1], front[2], front[3]], "#d7e4ff");
  drawWire(ctx, [back[0], back[1], back[2], back[3]], "#9fc6ff");
  [0, 1, 2, 3].forEach((i) => drawLine(ctx, front[i], back[i], "#9fc6ff"));

  ctx.fillStyle = "#c9d7d2";
  ctx.font = `${Math.max(11, w / 70)}px ${getComputedStyle(document.body).fontFamily}`;
  ctx.fillText("X [mm]", front[3][0] + size * 0.34, front[3][1] + 30);
  ctx.fillText("Y [mm]", front[2][0] + 20, front[2][1] - size * 0.25);
  ctx.fillText("lambda [nm]", back[0][0] - 46, back[0][1] - 8);
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

  const nx = state.scan.nx || Math.max(2, Math.round(Number($("x-range").value) / Number($("x-step").value)) + 1);
  const ny = state.scan.ny || Math.max(2, Math.round(Number($("y-range").value) / Number($("y-step").value)) + 1);
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
