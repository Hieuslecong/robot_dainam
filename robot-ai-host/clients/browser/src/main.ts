import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import "./style.css";

type BootstrapResponse = {
  session_id: string;
  status: string;
  expires_in: number;
  webrtcUrl: string;
  webrtc?: { url?: string; ice_servers?: unknown[] };
};

type DeviceResponse = {
  device_id: string;
  access_token: string;
  expires_in: number;
  heartbeat_interval_seconds: number;
};

const el = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing element #${id}`);
  return node as T;
};

const serverUrl = el<HTMLInputElement>("serverUrl");
const deviceId = el<HTMLInputElement>("deviceId");
const provisioningSecret = el<HTMLInputElement>("provisioningSecret");
const profile = el<HTMLSelectElement>("profile");
const connectButton = el<HTMLButtonElement>("connect");
const disconnectButton = el<HTMLButtonElement>("disconnect");
const initDevicesButton = el<HTMLButtonElement>("initDevices");
const toggleMicButton = el<HTMLButtonElement>("toggleMic");
const stopLocalPlaybackButton = el<HTMLButtonElement>("stopLocalPlayback");
const micSelect = el<HTMLSelectElement>("micSelect");
const micLevel = el<HTMLSpanElement>("micLevel");
const micStatus = el<HTMLParagraphElement>("micStatus");
const connectionBadge = el<HTMLDivElement>("connectionBadge");
const sessionIdNode = el<HTMLElement>("sessionId");
const transportStateNode = el<HTMLElement>("transportState");
const botStateNode = el<HTMLElement>("botState");
const userStateNode = el<HTMLElement>("userState");
const audioStateNode = el<HTMLElement>("audioState");
const transcriptNode = el<HTMLDivElement>("transcript");
const behaviorNode = el<HTMLDivElement>("behavior");
const metricsNode = el<HTMLElement>("metrics");
const logNode = el<HTMLElement>("log");
const botAudio = el<HTMLAudioElement>("botAudio");

serverUrl.value = window.location.origin;

// Auto-increment device_id for browser test client sessions
if (!deviceId.value || deviceId.value === "browser-test-001" || deviceId.value === "robot-face-001") {
  let counter = parseInt(localStorage.getItem("browser_device_counter") || "0", 10) + 1;
  localStorage.setItem("browser_device_counter", counter.toString());
  deviceId.value = `browser-client-${String(counter).padStart(3, "0")}`;
}


let client: PipecatClient | undefined;
let token = "";
let sessionId = "";
let heartbeatTimer: number | undefined;
let botSpeaking = false;
let bargeInStartedAt: number | undefined;
let lastUserStoppedAt: number | undefined;
let partialUserMessage: HTMLDivElement | undefined;
let remoteStream: MediaStream | undefined;
let connectStartedAt: number | undefined;

function log(message: string, data?: unknown): void {
  const stamp = new Date().toISOString();
  const suffix = data === undefined ? "" : ` ${safeStringify(data)}`;
  logNode.textContent += `[${stamp}] ${message}${suffix}\n`;
  logNode.scrollTop = logNode.scrollHeight;
}

function safeStringify(value: unknown): string {
  try { return JSON.stringify(value, null, 2); }
  catch { return String(value); }
}

function setTransportState(state: string): void {
  transportStateNode.textContent = state;
  connectionBadge.textContent = state;
  connectionBadge.dataset.state = state;
}

function appendTranscript(role: "user" | "bot", text: string, partial = false): void {
  if (!text.trim()) return;
  if (role === "user" && partial) {
    if (!partialUserMessage) {
      partialUserMessage = document.createElement("div");
      partialUserMessage.className = "message user partial";
      transcriptNode.appendChild(partialUserMessage);
    }
    partialUserMessage.textContent = text;
  } else {
    if (role === "user" && partialUserMessage) {
      partialUserMessage.remove();
      partialUserMessage = undefined;
    }
    const node = document.createElement("div");
    node.className = `message ${role}`;
    node.textContent = text;
    transcriptNode.appendChild(node);
  }
  transcriptNode.scrollTop = transcriptNode.scrollHeight;
}

function appendBehavior(data: unknown): void {
  const node = document.createElement("div");
  node.className = "event";
  node.textContent = `${new Date().toLocaleTimeString()} ${safeStringify(data)}`;
  behaviorNode.prepend(node);
}

async function postClientMessage(type: string, data: Record<string, unknown>): Promise<void> {
  if (!client) return;
  try { client.sendClientMessage(type, data); }
  catch (error) { log(`Không gửi được ${type}`, error); }
}

// Spec 8.5/4.6: browser AEC/NS/AGC must be explicitly requested, verified from
// the live track and exposed (UI + server evidence) before any server-side AEC
// work is considered.
const CAPTURE_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

async function reportCaptureSettings(track: MediaStreamTrack): Promise<void> {
  try {
    await track.applyConstraints(CAPTURE_CONSTRAINTS);
  } catch (error) {
    log("applyConstraints failed", error);
  }
  const s = track.getSettings();
  const summary = {
    echoCancellation: s.echoCancellation ?? null,
    noiseSuppression: s.noiseSuppression ?? null,
    autoGainControl: s.autoGainControl ?? null,
    sampleRate: s.sampleRate ?? null,
    deviceId: s.deviceId ?? null,
  };
  micStatus.textContent = `AEC=${String(summary.echoCancellation)} NS=${String(summary.noiseSuppression)} AGC=${String(summary.autoGainControl)}`;
  log("Local capture settings", summary);
  await postClientMessage("client.capture.settings", summary);
}

function configureClient(): PipecatClient {
  return new PipecatClient({
    transport: new SmallWebRTCTransport(),
    enableMic: true,
    enableCam: false,
    callbacks: {
      onConnected: () => log("Transport connected"),
      onDisconnected: () => {
        log("Transport disconnected");
        setTransportState("disconnected");
        stopHeartbeat();
        updateControls(false);
      },
      onTransportStateChanged: (state: string) => {
        setTransportState(state);
        log("Transport state", state);
      },
      onBotStarted: (response: unknown) => log("Session bootstrap succeeded", response),
      onBotReady: (data: unknown) => {
        botStateNode.textContent = "ready";
        log("RTVI bot ready", data);
        if (connectStartedAt !== undefined) {
          postClientMessage("client.webrtc.connected", { elapsed_ms: performance.now() - connectStartedAt });
          connectStartedAt = undefined;
        }
      },
      onTrackStarted: (track: MediaStreamTrack, participant: { local?: boolean }) => {
        if (track.kind === "audio" && participant?.local) {
          void reportCaptureSettings(track);
          return;
        }
        if (track.kind !== "audio" || participant?.local) return;
        remoteStream = new MediaStream([track]);
        botAudio.srcObject = remoteStream;
        botAudio.play().catch((error) => log("Audio autoplay blocked", error));
        audioStateNode.textContent = "track-active";
        log("Remote audio track started", { id: track.id });
      },
      onTrackStopped: (track: MediaStreamTrack, participant: { local?: boolean }) => {
        if (track.kind !== "audio" || participant?.local) return;
        audioStateNode.textContent = "inactive";
        log("Remote audio track stopped", { id: track.id });
      },
      onUserStartedSpeaking: () => {
        userStateNode.textContent = "speaking";
        if (botSpeaking) bargeInStartedAt = performance.now();
      },
      onUserStoppedSpeaking: () => {
        userStateNode.textContent = "idle";
        lastUserStoppedAt = performance.now();
      },
      onBotStartedSpeaking: () => {
        botSpeaking = true;
        botStateNode.textContent = "speaking";
      },
      onBotStoppedSpeaking: () => {
        botSpeaking = false;
        botStateNode.textContent = "ready";
        if (bargeInStartedAt !== undefined) {
          const elapsed = performance.now() - bargeInStartedAt;
          postClientMessage("client.barge_in.stopped", { elapsed_ms: elapsed });
          bargeInStartedAt = undefined;
        }
      },
      onUserTranscript: (data: { text?: string; final?: boolean }) => {
        appendTranscript("user", data.text ?? "", !data.final);
      },
      onBotOutput: (data: { text?: string; aggregated_by?: string }) => {
        // RTVI can emit both sentence-level output and word-level TTS text.
        // Render only logical blocks to avoid duplicating the same response.
        if (data.aggregated_by === "word") return;
        appendTranscript("bot", data.text ?? "");
      },
      onMetrics: (data: unknown) => {
        metricsNode.textContent = safeStringify(data);
      },
      onServerMessage: (message: { type?: string; data?: Record<string, unknown> }) => {
        log("Server message", message);
        if (message?.type !== "robot.behavior") return;
        const behavior = message.data ?? {};
        appendBehavior(behavior);
        const behaviorId = String(behavior.behavior_id ?? "");
        postClientMessage("robot.behavior.ack", {
          behavior_id: behaviorId,
          status: "completed",
          duration_ms: Number(behavior.duration_ms ?? 0),
        });
      },
      onError: (message: unknown) => {
        connectionBadge.dataset.state = "error";
        log("Pipecat error", message);
      },
      onMessageError: (message: unknown) => log("RTVI message error", message),
      onDeviceError: (error: unknown) => {
        micStatus.textContent = `Lỗi microphone: ${safeStringify(error)}`;
        log("Device error", error);
      },
      onAvailableMicsUpdated: (mics: MediaDeviceInfo[]) => updateMicOptions(mics),
      onMicUpdated: (mic: MediaDeviceInfo) => {
        micStatus.textContent = `Đang dùng: ${mic.label || mic.deviceId}`;
        micSelect.value = mic.deviceId;
      },
      onLocalAudioLevel: (level: number) => {
        micLevel.style.width = `${Math.min(100, Math.max(0, level * 100))}%`;
      },
    },
  });
}

function updateMicOptions(mics: MediaDeviceInfo[]): void {
  micSelect.innerHTML = "";
  for (const [index, mic] of mics.entries()) {
    const option = document.createElement("option");
    option.value = mic.deviceId;
    option.textContent = mic.label || `Microphone ${index + 1}`;
    micSelect.appendChild(option);
  }
  micStatus.textContent = mics.length ? `${mics.length} microphone khả dụng.` : "Không tìm thấy microphone.";
}

async function initializeDevices(): Promise<void> {
  if (!client) client = configureClient();
  initDevicesButton.disabled = true;
  try {
    await client.initDevices();
    const mics = await client.getAllMics();
    updateMicOptions(mics);
    log("Media devices initialized", { microphones: mics.length });
  } catch (error) {
    micStatus.textContent = `Không khởi tạo được microphone: ${String(error)}`;
    log("initDevices failed", error);
  } finally {
    initDevicesButton.disabled = false;
  }
}

async function registerDevice(): Promise<DeviceResponse> {
  const response = await fetch(`${normalizedServer()}/v1/devices/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      device_id: deviceId.value.trim(),
      device_type: "desktop_browser_emulator",
      firmware_version: "0.2.0",
      provisioning_secret: provisioningSecret.value,
      capabilities: { audio_input: true, audio_output: true, motion: true, display: true },
    }),
  });
  if (!response.ok) throw new Error(`Device registration ${response.status}: ${await response.text()}`);
  return response.json();
}

async function connect(): Promise<void> {
  if (!deviceId.value.trim()) throw new Error("Device ID không được để trống");
  updateControls(false, true);
  try {
    if (!client) client = configureClient();
    if (client.state === "disconnected") await client.initDevices();
    const device = await registerDevice();
    token = device.access_token;
    const bootstrap = await client.startBot({
      endpoint: `${normalizedServer()}/v1/sessions`,
      headers: new Headers({ Authorization: `Bearer ${token}` }),
      requestData: {
        device_id: deviceId.value.trim(),
        profile: profile.value,
        language: "vi-VN",
        transport: "webrtc",
        metadata: { client_version: "browser-0.2.0" },
      },
      timeout: 20_000,
    }) as BootstrapResponse;
    if (!bootstrap?.webrtcUrl || !bootstrap?.session_id) throw new Error("Bootstrap response thiếu webrtcUrl/session_id");
    sessionId = bootstrap.session_id;
    sessionIdNode.textContent = sessionId;
    connectStartedAt = performance.now();
    await client.connect(bootstrap);
    startHeartbeat(device.heartbeat_interval_seconds || 15);
    updateControls(true);
    log("Session ready", { session_id: sessionId, profile: profile.value });
  } catch (error) {
    log("Connection failed", error);
    connectionBadge.dataset.state = "error";
    connectionBadge.textContent = "error";
    await disconnect(true);
    throw error;
  }
}

async function disconnect(closeServerSession = true): Promise<void> {
  stopHeartbeat();
  try { await client?.disconnect(); }
  catch (error) { log("Client disconnect error", error); }
  if (closeServerSession && token && sessionId) {
    try {
      await fetch(`${normalizedServer()}/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (error) { log("Server session cleanup failed", error); }
  }
  sessionId = "";
  token = "";
  sessionIdNode.textContent = "—";
  botAudio.srcObject = null;
  remoteStream = undefined;
  botSpeaking = false;
  audioStateNode.textContent = "inactive";
  updateControls(false);
}

function startHeartbeat(intervalSeconds: number): void {
  stopHeartbeat();
  heartbeatTimer = window.setInterval(async () => {
    if (!sessionId || !token) return;
    try {
      const response = await fetch(`${normalizedServer()}/v1/sessions/${encodeURIComponent(sessionId)}/heartbeat`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await response.text());
    } catch (error) { log("Heartbeat failed", error); }
  }, Math.max(5, intervalSeconds) * 1000);
}

function stopHeartbeat(): void {
  if (heartbeatTimer !== undefined) window.clearInterval(heartbeatTimer);
  heartbeatTimer = undefined;
}

function normalizedServer(): string { return serverUrl.value.trim().replace(/\/$/, ""); }

function updateControls(connected: boolean, connecting = false): void {
  connectButton.disabled = connected || connecting;
  disconnectButton.disabled = !connected && !connecting;
  toggleMicButton.disabled = !connected;
  stopLocalPlaybackButton.disabled = !connected;
  deviceId.disabled = connected || connecting;
  provisioningSecret.disabled = connected || connecting;
  profile.disabled = connected || connecting;
  connectButton.textContent = connecting ? "Đang kết nối…" : "Kết nối";
}

initDevicesButton.addEventListener("click", () => initializeDevices());
connectButton.addEventListener("click", () => connect().catch((error) => alert(String(error))));
disconnectButton.addEventListener("click", () => disconnect());
toggleMicButton.addEventListener("click", () => {
  if (!client) return;
  const enable = !client.isMicEnabled;
  client.enableMic(enable);
  toggleMicButton.textContent = enable ? "Tắt microphone" : "Bật microphone";
  micStatus.textContent = enable ? "Microphone đang bật." : "Microphone đang tắt.";
  postClientMessage(enable ? "robot.unmute" : "robot.mute", {});
});
micSelect.addEventListener("change", () => client?.updateMic(micSelect.value));
stopLocalPlaybackButton.addEventListener("click", () => {
  botAudio.pause();
  audioStateNode.textContent = "locally-paused-debug";
  log("Local playback stopped for debugging only; server pipeline was not interrupted");
});
el<HTMLButtonElement>("clearTranscript").addEventListener("click", () => { transcriptNode.innerHTML = ""; partialUserMessage = undefined; });
el<HTMLButtonElement>("clearLog").addEventListener("click", () => { logNode.textContent = ""; });

botAudio.addEventListener("playing", () => {
  audioStateNode.textContent = "audible";
  const elapsed = lastUserStoppedAt === undefined ? undefined : performance.now() - lastUserStoppedAt;
  postClientMessage("client.playback.started", { elapsed_ms: elapsed ?? null });
});
botAudio.addEventListener("pause", () => { if (!botAudio.ended) audioStateNode.textContent = "paused"; });
botAudio.addEventListener("error", () => log("Bot audio element error", botAudio.error));
window.addEventListener("beforeunload", () => { stopHeartbeat(); client?.disconnect(); });

updateControls(false);
