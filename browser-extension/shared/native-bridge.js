/**
 * NativeBridge: Klien `runtime.connectNative()` untuk berkomunikasi dengan
 * `com.xoose.loveyou.host` menggunakan chunked transfer base64 + SHA-256
 * dan auto-reconnect dengan exponential backoff.
 */

export const NATIVE_HOST_NAME = "com.xoose.loveyou.host";
export const MAX_CHUNK_PAYLOAD_CHARS = 240 * 1024; // ~240 KB base64 (< batas aman Native Messaging)
export const MAX_CHUNKS = 64;

/**
 * Menghitung SHA-256 hex dari Uint8Array menggunakan Web Crypto API.
 * @param {Uint8Array} bytes
 * @returns {Promise<string>}
 */
export async function computeSha256Hex(bytes) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error("Web Crypto subtle API tidak tersedia untuk perhitungan SHA-256.");
  }
  const digest = await subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Mengubah data URL (`data:image/png;base64,...`) menjadi `{ mimeType, base64, bytes }`.
 * @param {string} dataUrl
 * @returns {{ mimeType: string, base64: string, bytes: Uint8Array }}
 */
export function decodeImageDataUrl(dataUrl) {
  if (typeof dataUrl !== "string" || !dataUrl.startsWith("data:")) {
    throw new Error("Data URL gambar tidak valid.");
  }
  const commaIdx = dataUrl.indexOf(",");
  if (commaIdx < 0) {
    throw new Error("Data URL gambar tidak memiliki pemisah payload.");
  }
  const header = dataUrl.slice(5, commaIdx);
  const base64 = dataUrl.slice(commaIdx + 1).trim();
  const [mimeRaw] = header.split(";");
  const mimeType = (mimeRaw || "image/png").toLowerCase();
  if (!header.includes(";base64")) {
    throw new Error("Data URL gambar wajib berformat base64.");
  }

  let bytes;
  if (typeof Buffer !== "undefined") {
    bytes = new Uint8Array(Buffer.from(base64, "base64"));
  } else {
    const binary = atob(base64);
    bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
  }
  return { mimeType, base64, bytes };
}

/**
 * Memecah string base64 menjadi pesan-pesan `capture_chunk` tervalidasi.
 * @param {object} params
 * @param {string} params.captureId
 * @param {string} params.base64
 * @param {string} params.mimeType
 * @param {string} params.targetFormat
 * @param {string} params.checksum
 * @param {object} params.meta
 * @param {number} [params.maxChunkChars]
 * @returns {Array<object>}
 */
export function buildCaptureChunks({
  captureId,
  base64,
  mimeType,
  targetFormat = "webp",
  checksum,
  meta = {},
  maxChunkChars = MAX_CHUNK_PAYLOAD_CHARS,
}) {
  if (!captureId || !base64 || !checksum) {
    throw new Error("captureId, base64, dan checksum wajib diisi untuk chunk transfer.");
  }
  const chunkSize = Math.max(1024, Math.min(MAX_CHUNK_PAYLOAD_CHARS, Number(maxChunkChars) || MAX_CHUNK_PAYLOAD_CHARS));
  const slices = [];
  for (let offset = 0; offset < base64.length; offset += chunkSize) {
    slices.push(base64.slice(offset, offset + chunkSize));
  }
  if (slices.length > MAX_CHUNKS) {
    throw new Error(`Jumlah chunk (${slices.length}) melebihi batas maksimum (${MAX_CHUNKS}).`);
  }

  return slices.map((payload, idx) => ({
    type: "capture_chunk",
    capture_id: captureId,
    chunk_index: idx,
    chunk_count: slices.length,
    mime_type: mimeType,
    target_format: targetFormat,
    payload,
    checksum,
    meta: idx === 0 ? meta : undefined,
  }));
}

export function generateUuid() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  // Fallback RFC4122 v4
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export class NativeBridge {
  /**
   * @param {object} opts
   * @param {object} opts.api - adapter dari createBrowserApi()
   * @param {string} [opts.hostName]
   * @param {function} [opts.onConfigUpdate]
   * @param {function} [opts.onControlAction]
   * @param {function} [opts.onCaptureAck]
   * @param {function} [opts.onCaptureError]
   * @param {function} [opts.onConnectionChange]
   */
  constructor({
    api,
    hostName = NATIVE_HOST_NAME,
    onConfigUpdate = null,
    onControlAction = null,
    onCaptureAck = null,
    onCaptureError = null,
    onConnectionChange = null,
  }) {
    this.api = api;
    this.hostName = hostName;
    this.onConfigUpdate = onConfigUpdate;
    this.onControlAction = onControlAction;
    this.onCaptureAck = onCaptureAck;
    this.onCaptureError = onCaptureError;
    this.onConnectionChange = onConnectionChange;

    this.port = null;
    this.connected = false;
    this.lastError = null;
    this._reconnectAttempts = 0;
    this._reconnectTimer = null;
    this._stopped = false;
  }

  connect() {
    if (this.connected && this.port) {
      return true;
    }
    this._stopped = false;
    this._clearReconnectTimer();

    try {
      const port = this.api.runtime.connectNative(this.hostName);
      this.port = port;
      this.connected = true;
      this.lastError = null;
      this._reconnectAttempts = 0;

      port.onMessage.addListener((msg) => this._handleMessage(msg));
      port.onDisconnect.addListener(() => this._handleDisconnect());

      const manifest = this.api.runtime.getManifest();
      this.postMessage({
        type: "hello",
        protocol_version: 1,
        browser: this.api.browserName,
        extension_id: this.api.runtime.id || "",
        extension_version: manifest?.version || "1.0.0",
      });
      this.postMessage({ type: "get_config", current_config_version: 0 });

      this.onConnectionChange?.(true, null);
      return true;
    } catch (err) {
      this.connected = false;
      this.port = null;
      this.lastError = err?.message || String(err);
      this.onConnectionChange?.(false, this.lastError);
      this._scheduleReconnect();
      return false;
    }
  }

  disconnect() {
    this._stopped = true;
    this._clearReconnectTimer();
    if (this.port) {
      try {
        this.port.disconnect();
      } catch {
        // abaikan error saat disconnect
      }
      this.port = null;
    }
    const wasConnected = this.connected;
    this.connected = false;
    if (wasConnected) {
      this.onConnectionChange?.(false, null);
    }
  }

  postMessage(message) {
    if (!this.connected || !this.port) {
      return false;
    }
    try {
      this.port.postMessage(message);
      return true;
    } catch (err) {
      this.lastError = err?.message || String(err);
      this._handleDisconnect();
      return false;
    }
  }

  requestConfig(currentConfigVersion = 0) {
    return this.postMessage({
      type: "get_config",
      current_config_version: Number(currentConfigVersion) || 0,
    });
  }

  sendStatusReport(statusPayload) {
    return this.postMessage({
      type: "status_report",
      ...statusPayload,
    });
  }

  sendCaptureAbort(captureId, reason = "aborted") {
    return this.postMessage({
      type: "capture_abort",
      capture_id: captureId,
      reason,
    });
  }

  /**
   * Memecah dan mengirim satu gambar hasil `captureVisibleTab()` ke Native Host.
   * @param {object} params
   * @returns {Promise<{ ok: boolean, captureId?: string, chunkCount?: number, checksum?: string, error?: string }>}
   */
  async sendCapturedImage({ dataUrl, targetFormat = "webp", meta = {}, maxChunkChars = MAX_CHUNK_PAYLOAD_CHARS }) {
    if (!this.connected || !this.port) {
      return { ok: false, error: "Native host tidak terhubung." };
    }

    const captureId = generateUuid();
    try {
      const { mimeType, base64, bytes } = decodeImageDataUrl(dataUrl);
      const checksum = await computeSha256Hex(bytes);
      const chunks = buildCaptureChunks({
        captureId,
        base64,
        mimeType,
        targetFormat,
        checksum,
        meta,
        maxChunkChars,
      });

      for (const chunkMsg of chunks) {
        const sent = this.postMessage(chunkMsg);
        if (!sent) {
          return { ok: false, captureId, error: "Koneksi Native host terputus saat mengirim chunk." };
        }
      }

      return {
        ok: true,
        captureId,
        chunkCount: chunks.length,
        checksum,
      };
    } catch (err) {
      this.sendCaptureAbort(captureId, "encode_error");
      return { ok: false, captureId, error: err?.message || String(err) };
    }
  }

  _handleMessage(msg) {
    if (!msg || typeof msg !== "object") {
      return;
    }
    switch (msg.type) {
      case "config_update":
        this.onConfigUpdate?.(msg);
        break;
      case "control_action":
        this.onControlAction?.(msg);
        break;
      case "capture_ack":
        this.onCaptureAck?.(msg);
        break;
      case "capture_error":
        this.lastError = msg.message || msg.code || "Native host capture error";
        this.onCaptureError?.(msg);
        break;
      default:
        break;
    }
  }

  _handleDisconnect() {
    const runtimeErr = this.api.raw?.runtime?.lastError?.message;
    this.port = null;
    this.connected = false;
    this.lastError = runtimeErr || this.lastError || "Native host terputus.";
    this.onConnectionChange?.(false, this.lastError);
    if (!this._stopped) {
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (this._stopped || this._reconnectTimer) {
      return;
    }
    this._reconnectAttempts += 1;
    const delayMs = Math.min(30000, 1500 * Math.pow(2, Math.min(this._reconnectAttempts - 1, 4)));
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      if (!this._stopped && !this.connected) {
        this.connect();
      }
    }, delayMs);
  }

  _clearReconnectTimer() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }
}
