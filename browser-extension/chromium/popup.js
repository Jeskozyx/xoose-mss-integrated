/**
 * Popup Minimalis & Transparan untuk Google Chrome / Microsoft Edge.
 * Menyediakan indikator status aktif, domain cocok, kontrol lokal Start/Pause/Stop,
 * serta tombol persetujuan transparan untuk izin opsional `<all_urls>`.
 */

import { createBrowserApi } from "./shared/browser-api.js";

const api = createBrowserApi();

const statusPill = document.getElementById("statusPill");
const statusText = document.getElementById("statusText");
const domainValue = document.getElementById("domainValue");
const modeValue = document.getElementById("modeValue");
const hostValue = document.getElementById("hostValue");
const statsValue = document.getElementById("statsValue");
const toggleBtn = document.getElementById("toggleBtn");
const stopBtn = document.getElementById("stopBtn");
const permBtn = document.getElementById("permBtn");
const reconnectBtn = document.getElementById("reconnectBtn");
const errorBox = document.getElementById("errorBox");

let currentStatus = null;

function formatStateLabel(state) {
  switch (state) {
    case "capturing":
      return { text: "Aktif", cls: "capturing" };
    case "paused_local":
      return { text: "Dijeda", cls: "paused" };
    case "paused_unfocused":
      return { text: "Jeda (Fokus)", cls: "paused" };
    case "paused_origin_changed":
      return { text: "Jeda (Origin)", cls: "paused" };
    case "error_host_disconnected":
      return { text: "Host Putus", cls: "error" };
    case "stopped_permission_revoked":
      return { text: "Izin Dicabut", cls: "error" };
    case "stopped_local":
      return { text: "Berhenti", cls: "" };
    case "idle_mismatch":
      return { text: "Bukan Target", cls: "" };
    case "idle_internal_url":
      return { text: "Tab Internal", cls: "" };
    default:
      return { text: "Siaga", cls: "" };
  }
}

function render(status) {
  currentStatus = status;
  const badge = formatStateLabel(status.capture_state);
  statusPill.className = `pill ${badge.cls}`.trim();
  statusText.textContent = badge.text;

  domainValue.textContent = status.matched_domain || "-";
  modeValue.textContent = status.permission_mode === "automatic_domain" ? "Otomatis" : "Local-Start";
  hostValue.textContent = status.extension_connected ? "Terhubung" : "Terputus";
  statsValue.textContent = `v${status.config_version || 0} · ${status.captures_sent || 0}x`;

  const isRunning = status.local_session_state === "running";
  toggleBtn.textContent = isRunning ? "Jeda" : (status.local_session_state === "paused" ? "Lanjut" : "Mulai");
  stopBtn.disabled = status.local_session_state === "stopped";

  permBtn.textContent = status.has_host_permission ? "Cabut Izin Otomatis" : "Izinkan Mode Otomatis";

  if (status.last_error) {
    errorBox.textContent = status.last_error;
    errorBox.style.display = "block";
  } else {
    errorBox.style.display = "none";
  }
}

async function fetchStatus() {
  try {
    const res = await api.runtime.sendMessage({ type: "GET_STATUS" });
    if (res?.ok && res.status) {
      render(res.status);
    }
  } catch (err) {
    errorBox.textContent = err?.message || "Gagal memuat status extension.";
    errorBox.style.display = "block";
  }
}

toggleBtn.addEventListener("click", async () => {
  const action = currentStatus?.local_session_state === "running" ? "pause" : "start";
  const res = await api.runtime.sendMessage({ type: "LOCAL_CONTROL", action });
  if (res?.ok && res.status) {
    render(res.status);
  }
});

stopBtn.addEventListener("click", async () => {
  const res = await api.runtime.sendMessage({ type: "LOCAL_CONTROL", action: "stop" });
  if (res?.ok && res.status) {
    render(res.status);
  }
});

permBtn.addEventListener("click", async () => {
  try {
    if (currentStatus?.has_host_permission) {
      await api.permissions.remove({ origins: ["<all_urls>"] });
    } else {
      await api.permissions.request({ origins: ["<all_urls>"] });
    }
    const res = await api.runtime.sendMessage({ type: "REFRESH_PERMISSIONS" });
    if (res?.ok && res.status) {
      render(res.status);
    }
  } catch (err) {
    errorBox.textContent = err?.message || "Gagal mengubah izin browser.";
    errorBox.style.display = "block";
  }
});

reconnectBtn.addEventListener("click", async () => {
  const res = await api.runtime.sendMessage({ type: "RECONNECT_HOST" });
  if (res?.ok && res.status) {
    render(res.status);
  }
});

void fetchStatus();
