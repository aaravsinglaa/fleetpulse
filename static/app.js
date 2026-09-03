const $ = (selector) => document.querySelector(selector);
let selectedVehicleId = 1;
let selectedVehicleDetail = null;
let updateInProgress = false;

const sourceLabels = {
  simulator: "Simulator",
  csv_replay: "CSV replay",
  external_api: "External API",
  sensor_gateway: "Gateway",
};

function readingAge(timestamp) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 3) return "Now";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function exactTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function renderSummary(vehicles, incidents) {
  const healthy = vehicles.filter((vehicle) => vehicle.status === "healthy").length;
  const averageBattery = vehicles.reduce((sum, vehicle) => sum + vehicle.battery_pct, 0) / vehicles.length;
  $("#vehicle-count").textContent = vehicles.length;
  $("#unit-count").textContent = `${vehicles.length} units`;
  $("#healthy-count").textContent = healthy;
  $("#health-rate").textContent = `${Math.round(healthy / vehicles.length * 100)}% of fleet`;
  $("#avg-battery").textContent = `${Math.round(averageBattery)}%`;
  $("#incident-count").textContent = incidents.length;
  $("#incident-badge").textContent = incidents.length;
}

function renderVehicles(vehicles) {
  $("#vehicle-rows").innerHTML = vehicles.map((vehicle) => {
    const battery = Math.round(vehicle.battery_pct);
    const isHot = vehicle.temperature_c > 50;
    const isStale = vehicle.incidents.includes("stale_telemetry");
    const selected = vehicle.id === selectedVehicleId;
    return `<tr class="${selected ? "selected" : ""}">
      <td class="unit-cell"><button type="button" class="unit-button" data-vehicle-id="${vehicle.id}" aria-label="View ${vehicle.name} history"><strong>${String(vehicle.id).padStart(3, "0")} · ${vehicle.name}</strong><small>${vehicle.model}</small></button></td>
      <td><span class="state ${vehicle.status}">${vehicle.status === "healthy" ? "Normal" : "Attention"}</span></td>
      <td><div class="charge"><span>${battery}%</span><span class="charge-meter"><i class="${battery < 35 ? "low" : ""}" style="width:${battery}%"></i></span></div></td>
      <td class="temperature ${isHot ? "hot" : ""}">${vehicle.temperature_c.toFixed(1)}°C</td>
      <td>${Math.round(vehicle.speed_kph)} km/h</td>
      <td><span class="source">${sourceLabels[vehicle.source] || vehicle.source}</span></td>
      <td><time class="report-time ${isStale ? "stale" : ""}" datetime="${vehicle.timestamp}">${readingAge(vehicle.timestamp)}<small>${exactTime(vehicle.timestamp)}</small></time></td>
    </tr>`;
  }).join("");
}

function renderIncidents(incidents) {
  if (!incidents.length) {
    $("#incidents").innerHTML = '<div class="empty"><strong>No active incidents</strong>All diagnostic rules are within limits.</div>';
    return;
  }
  $("#incidents").innerHTML = incidents.map((incident) => {
    const rule = incident.type === "high_temperature" ? `Temperature > ${incident.threshold.toFixed(1)}°C` : `Signal age > ${incident.threshold.toFixed(0)}s`;
    return `<article class="incident">
      <div class="incident-top"><span class="severity ${incident.severity}">${incident.severity}</span><time datetime="${incident.detected_at}">${readingAge(incident.detected_at)}</time></div>
      <h3>${String(incident.vehicle_id).padStart(3, "0")} · ${incident.vehicle_name}</h3>
      <p>${incident.message}</p>
      <dl><dt>Rule</dt><dd>${rule}</dd><dt>Last sample</dt><dd>${exactTime(incident.detected_at)}</dd></dl>
    </article>`;
  }).join("");
}

function drawTemperatureHistory(detail) {
  const canvas = $("#temperature-chart");
  const rect = canvas.getBoundingClientRect();
  if (!rect.width || !detail?.telemetry?.length) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(rect.width * ratio);
  canvas.height = Math.floor(rect.height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);

  const samples = [...detail.telemetry].reverse();
  const width = rect.width;
  const height = rect.height;
  const pad = { top: 14, right: 18, bottom: 28, left: 42 };
  const chartWidth = width - pad.left - pad.right;
  const chartHeight = height - pad.top - pad.bottom;
  const observedMinimum = Math.min(...samples.map((sample) => sample.temperature_c));
  const minimum = Math.min(20, Math.floor(observedMinimum / 10) * 10);
  const maximum = 60;
  const yPosition = (value) => pad.top + chartHeight - ((value - minimum) / (maximum - minimum)) * chartHeight;

  ctx.font = "10px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  ctx.lineWidth = 1;
  [minimum, 30, 40, 50, 60].filter((value, index, list) => value >= minimum && list.indexOf(value) === index).forEach((value) => {
    const y = yPosition(value);
    ctx.strokeStyle = value === 50 ? "#d7aaa5" : "#e2e5e9";
    ctx.setLineDash(value === 50 ? [4, 4] : []);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
    ctx.fillStyle = value === 50 ? "#9f3329" : "#7c848e";
    ctx.textAlign = "right";
    ctx.fillText(`${value}°`, pad.left - 8, y + 3);
  });
  ctx.setLineDash([]);

  const points = samples.map((sample, index) => ({
    x: pad.left + (samples.length === 1 ? chartWidth / 2 : index / (samples.length - 1) * chartWidth),
    y: yPosition(sample.temperature_c),
  }));
  ctx.strokeStyle = "#2457a6";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach(({ x, y }, index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.stroke();
  points.forEach(({ x, y }, index) => {
    ctx.fillStyle = samples[index].temperature_c > 50 ? "#b42318" : "#2457a6";
    ctx.beginPath(); ctx.arc(x, y, 2.4, 0, Math.PI * 2); ctx.fill();
  });

  const labelIndexes = [...new Set([0, Math.floor((samples.length - 1) / 2), samples.length - 1])];
  ctx.fillStyle = "#7c848e";
  ctx.textAlign = "center";
  labelIndexes.forEach((index) => ctx.fillText(exactTime(samples[index].timestamp), points[index].x, height - 6));
}

async function updateSelectedVehicle() {
  const response = await fetch(`/vehicles/${selectedVehicleId}?history=60`);
  if (!response.ok) throw new Error("Vehicle history unavailable");
  selectedVehicleDetail = await response.json();
  const latest = selectedVehicleDetail.telemetry[0];
  $("#selected-vehicle").textContent = `${String(selectedVehicleDetail.id).padStart(3, "0")} · ${selectedVehicleDetail.name} · ${selectedVehicleDetail.model}`;
  $("#selected-temp").textContent = latest ? `${latest.temperature_c.toFixed(1)}°C` : "—";
  $("#sample-count").textContent = selectedVehicleDetail.telemetry.length;
  drawTemperatureHistory(selectedVehicleDetail);
}

async function updateDashboard() {
  if (updateInProgress) return;
  updateInProgress = true;
  try {
    const [vehiclesResponse, incidentsResponse] = await Promise.all([fetch("/vehicles"), fetch("/incidents")]);
    if (!vehiclesResponse.ok || !incidentsResponse.ok) throw new Error("Telemetry unavailable");
    const [vehicles, incidents] = await Promise.all([vehiclesResponse.json(), incidentsResponse.json()]);
    if (!vehicles.some((vehicle) => vehicle.id === selectedVehicleId)) selectedVehicleId = vehicles[0]?.id;
    renderSummary(vehicles, incidents);
    renderVehicles(vehicles);
    renderIncidents(incidents);
    await updateSelectedVehicle();
    $("#last-sync").textContent = `Updated ${exactTime(new Date().toISOString())}`;
    $("#connection-label").textContent = "Connected";
    $(".connection").classList.remove("offline");
  } catch (error) {
    $("#connection-label").textContent = "Unavailable";
    $(".connection").classList.add("offline");
    $("#last-sync").textContent = "Update failed";
  } finally {
    updateInProgress = false;
  }
}

$("#vehicle-rows").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-vehicle-id]");
  if (!button) return;
  selectedVehicleId = Number(button.dataset.vehicleId);
  $("#vehicle-rows tr.selected")?.classList.remove("selected");
  button.closest("tr").classList.add("selected");
  await updateSelectedVehicle();
});
$("#refresh").addEventListener("click", updateDashboard);
window.addEventListener("resize", () => drawTemperatureHistory(selectedVehicleDetail));
updateDashboard();
setInterval(updateDashboard, 2000);
