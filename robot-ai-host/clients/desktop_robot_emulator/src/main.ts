import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import "./style.css";

type BootstrapResponse = {
  session_id: string;
  webrtcUrl: string;
};

type DeviceResponse = {
  access_token: string;
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
const wakeButton = el<HTMLButtonElement>("wake");
const sleepButton = el<HTMLButtonElement>("sleep");
const statusNode = el<HTMLParagraphElement>("status");
const robot = el<HTMLDivElement>("robot");
const head = el<HTMLDivElement>("head");
const mouth = el<HTMLDivElement>("mouth");
const stateLabel = el<HTMLParagraphElement>("stateLabel");
const behaviorLabel = el<HTMLParagraphElement>("behaviorLabel");
const lastText = el<HTMLParagraphElement>("lastText");
const botAudio = el<HTMLAudioElement>("botAudio");

serverUrl.value = window.location.origin;

let client: PipecatClient | undefined;
let token = "";
let sessionId = "";
let heartbeatTimer: number | undefined;

// ---------- Face controller ----------

type RobotState = "offline" | "idle" | "listening" | "thinking" | "speaking" | "sleeping";

const STATE_LABELS: Record<RobotState, string> = {
  offline: "Chưa kết nối",
  idle: "Đang chờ",
  listening: "Đang nghe…",
  thinking: "Đang nghĩ…",
  speaking: "Đang nói",
  sleeping: "Đang ngủ (chạm Đánh thức)",
};

// Behavior IDs from the host behavior map (spec 15.4) + "greet" on connect.
const KNOWN_BEHAVIORS = new Set([
  "greet",
  "attentive_idle",
  "gentle_nod",
  "happy_tilt",
  "slow_nod",
  "soft_nod",
  "positive_nod",
  "attentive_still",
]);

// emotion → face accent (eyes/mouth shape handled in CSS via data-emotion).
const EMOTIONS = new Set([
  "neutral", "friendly", "cheerful", "calm", "empathetic", "encouraging", "serious",
  "sad", "angry", "surprised", "love", "shy", "confused", "sleepy",
  "laughing", "excited",
]);

// Voice commands: user asks the robot to make a face → change it directly,
// no server round-trip needed. Order matters (first match wins).
const FACE_COMMANDS: Array<[RegExp, string]> = [
  [/mặt buồn|buồn đi|khóc|mặt khóc/i, "sad"],
  [/mặt giận|giận dữ|tức giận|mặt cáu/i, "angry"],
  [/ngạc nhiên|bất ngờ|kinh ngạc/i, "surprised"],
  [/thả tim|mặt yêu|đáng yêu|dễ thương/i, "love"],
  [/nháy mắt/i, "wink"],
  [/cười to|cười lớn|haha|ha ha/i, "laughing"],
  [/phấn khích|quẩy lên|tuyệt vời|hào hứng/i, "excited"],
  [/mắc cỡ|xấu hổ|thẹn|ngại quá/i, "shy"],
  [/bối rối|hoang mang|khó hiểu/i, "confused"],
  [/buồn ngủ|mệt mỏi|uể oải/i, "sleepy"],
  [/mặt vui|cười lên|vui lên|mặt cười|hạnh phúc/i, "cheerful"],
  [/nghiêm túc|mặt ngầu|lạnh lùng/i, "serious"],
  [/bình thường|mặt thường|hết buồn|thôi buồn/i, "neutral"],
];

// Floating particles for expressive bursts (hearts, sparkles).
const particles = el<HTMLDivElement>("particles");

function spawnParticles(glyphs: string[], count = 7): void {
  for (let i = 0; i < count; i++) {
    const p = document.createElement("span");
    p.className = "particle";
    p.textContent = glyphs[i % glyphs.length];
    p.style.left = `${12 + Math.random() * 76}%`;
    p.style.animationDelay = `${Math.random() * 0.9}s`;
    p.style.fontSize = `${16 + Math.random() * 14}px`;
    particles.appendChild(p);
    window.setTimeout(() => p.remove(), 3000);
  }
}

let emotionHoldTimer: number | undefined;

function holdEmotion(emotion: string, holdMs = 10_000): void {
  if (emotion === "wink") {
    robot.classList.add("wink");
    window.setTimeout(() => robot.classList.remove("wink"), 900);
    return;
  }
  setEmotion(emotion);
  behaviorLabel.textContent = `emotion: ${emotion}`;
  if (emotion === "love") spawnParticles(["💖", "💕", "✨"]);
  else if (emotion === "cheerful" || emotion === "laughing") spawnParticles(["✨", "🌟"], 5);
  else if (emotion === "excited") spawnParticles(["🎉", "⭐", "✨"], 8);
  window.clearTimeout(emotionHoldTimer);
  if (emotion !== "neutral") {
    emotionHoldTimer = window.setTimeout(() => setEmotion("neutral"), holdMs);
  }
}

function matchFaceCommand(text: string): string | undefined {
  for (const [pattern, emotion] of FACE_COMMANDS) {
    if (pattern.test(text)) return emotion;
  }
  return undefined;
}

function setState(state: RobotState): void {
  robot.dataset.state = state;
  stateLabel.textContent = STATE_LABELS[state];
  if (state === "idle") head.classList.add("b-attentive_idle");
  else head.classList.remove("b-attentive_idle");
}

function setEmotion(emotion: string): void {
  robot.dataset.emotion = EMOTIONS.has(emotion) ? emotion : "neutral";
}

let behaviorResetTimer: number | undefined;

function playBehavior(name: string, emotion: string, durationMs: number): void {
  if (!KNOWN_BEHAVIORS.has(name)) return;
  setEmotion(emotion);
  behaviorLabel.textContent = `behavior: ${name} (${emotion})`;
  // Restart the CSS animation even if the same behavior repeats.
  head.classList.remove(...Array.from(head.classList).filter((c) => c.startsWith("b-") && c !== "b-attentive_idle"));
  void head.offsetWidth; // reflow → animation restarts
  if (name !== "attentive_idle") head.classList.add(`b-${name}`);
  window.clearTimeout(behaviorResetTimer);
  behaviorResetTimer = window.setTimeout(() => {
    head.classList.remove(`b-${name}`);
    behaviorLabel.textContent = "—";
  }, Math.max(durationMs, 1400));
}

// ---------- Mouth driven by bot audio (WebAudio analyser) ----------

let audioCtx: AudioContext | undefined;
let analyser: AnalyserNode | undefined;
let mouthRaf: number | undefined;

function attachMouthAnalyser(stream: MediaStream): void {
  audioCtx?.close().catch(() => undefined);
  audioCtx = new AudioContext();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  audioCtx.createMediaStreamSource(stream).connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);
  const loop = () => {
    if (!analyser) return;
    analyser.getByteFrequencyData(data);
    let sum = 0;
    for (const v of data) sum += v;
    const level = sum / data.length / 255; // 0..1
    if (robot.dataset.state === "speaking") {
      mouth.classList.add("talking");
      const h = 9 + Math.min(34, level * 170);
      mouth.style.height = `${h}px`;
      mouth.style.borderRadius = h > 18 ? "16px" : "8px";
      mouth.classList.toggle("open", h > 20); // tongue peeks on wide-open
    } else {
      mouth.classList.remove("talking", "open");
      mouth.style.height = "";
      mouth.style.borderRadius = "";
    }
    mouthRaf = requestAnimationFrame(loop);
  };
  cancelAnimationFrame(mouthRaf ?? 0);
  mouthRaf = requestAnimationFrame(loop);
}

// ---------- Pipecat client ----------

function log(message: string): void {
  statusNode.textContent = message;
}

async function sendClientMessage(type: string, data: Record<string, unknown>): Promise<void> {
  try { client?.sendClientMessage(type, data); } catch { /* not connected */ }
}

function configureClient(): PipecatClient {
  return new PipecatClient({
    transport: new SmallWebRTCTransport(),
    enableMic: true,
    enableCam: false,
    callbacks: {
      onDisconnected: () => {
        setState("offline");
        stopHeartbeat();
        updateControls(false);
      },
      onBotReady: () => {
        setState("idle");
        log("Robot sẵn sàng — nói vào micro.");
      },
      onTrackStarted: (track: MediaStreamTrack, participant: { local?: boolean }) => {
        if (track.kind !== "audio" || participant?.local) return;
        const stream = new MediaStream([track]);
        botAudio.srcObject = stream;
        botAudio.play().catch(() => log("Trình duyệt chặn autoplay — bấm vào trang."));
        attachMouthAnalyser(stream);
      },
      onUserStartedSpeaking: () => setState("listening"),
      onUserStoppedSpeaking: () => {
        if (robot.dataset.state === "listening") setState("thinking");
      },
      onBotStartedSpeaking: () => setState("speaking"),
      onBotStoppedSpeaking: () => setState("idle"),
      onUserTranscript: (data: { text?: string; final?: boolean }) => {
        if (!data.final || !data.text) return;
        lastText.textContent = `Bạn: ${data.text}`;
        const emotion = matchFaceCommand(data.text);
        if (emotion) holdEmotion(emotion);
      },
      onBotOutput: (data: { text?: string; aggregated_by?: string }) => {
        if (data.aggregated_by === "word") return;
        if (!data.text) return;
        lastText.textContent = `Robot: ${data.text}`;
        // Mirror the bot's own non-verbal cues on the face.
        if (/\[cười\]|\[chuckle\]/i.test(data.text)) holdEmotion("laughing", 6000);
        else if (/\[thở dài\]|\[sigh\]/i.test(data.text)) holdEmotion("empathetic", 6000);
      },
      onServerMessage: (message: { type?: string; data?: Record<string, unknown> }) => {
        if (message?.type !== "robot.behavior") return;
        const b = message.data ?? {};
        playBehavior(
          String(b.name ?? b.behavior ?? ""),
          String(b.emotion ?? "neutral"),
          Number(b.duration_ms ?? 0),
        );
        sendClientMessage("robot.behavior.ack", {
          behavior_id: String(b.behavior_id ?? ""),
          status: "completed",
          duration_ms: Number(b.duration_ms ?? 0),
        });
      },
      onError: () => log("Lỗi pipeline — xem log server."),
    },
  });
}

async function registerDevice(): Promise<DeviceResponse> {
  const response = await fetch(`${server()}/v1/devices/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      device_id: deviceId.value.trim(),
      device_type: "desktop_robot_emulator",
      firmware_version: "0.1.0",
      provisioning_secret: provisioningSecret.value,
      capabilities: { audio_input: true, audio_output: true, motion: true, display: true },
    }),
  });
  if (!response.ok) throw new Error(`Đăng ký thiết bị lỗi ${response.status}: ${await response.text()}`);
  return response.json();
}

async function connect(): Promise<void> {
  updateControls(false, true);
  try {
    if (!client) client = configureClient();
    if (client.state === "disconnected") await client.initDevices();
    const device = await registerDevice();
    token = device.access_token;
    const bootstrap = (await client.startBot({
      endpoint: `${server()}/v1/sessions`,
      headers: new Headers({ Authorization: `Bearer ${token}` }),
      requestData: {
        device_id: deviceId.value.trim(),
        profile: profile.value,
        language: "vi-VN",
        transport: "webrtc",
        metadata: { client_version: "robot-emulator-0.1.0" },
      },
      timeout: 20_000,
    })) as BootstrapResponse;
    if (!bootstrap?.webrtcUrl || !bootstrap?.session_id) throw new Error("Bootstrap thiếu webrtcUrl/session_id");
    sessionId = bootstrap.session_id;
    await client.connect(bootstrap);
    startHeartbeat(device.heartbeat_interval_seconds || 15);
    updateControls(true);
    log(`Đã kết nối (session ${sessionId.slice(0, 8)}…)`);
  } catch (error) {
    log(`Kết nối thất bại: ${String(error)}`);
    setState("offline");
    await disconnect(true);
  }
}

async function disconnect(silent = false): Promise<void> {
  stopHeartbeat();
  try { await client?.disconnect(); } catch { /* already down */ }
  if (token && sessionId) {
    fetch(`${server()}/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => undefined);
  }
  sessionId = "";
  token = "";
  botAudio.srcObject = null;
  setState("offline");
  updateControls(false);
  if (!silent) log("Đã ngắt kết nối.");
}

function startHeartbeat(intervalSeconds: number): void {
  stopHeartbeat();
  heartbeatTimer = window.setInterval(() => {
    if (!sessionId || !token) return;
    fetch(`${server()}/v1/sessions/${encodeURIComponent(sessionId)}/heartbeat`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => undefined);
  }, Math.max(5, intervalSeconds) * 1000);
}

function stopHeartbeat(): void {
  if (heartbeatTimer !== undefined) window.clearInterval(heartbeatTimer);
  heartbeatTimer = undefined;
}

function server(): string {
  return serverUrl.value.trim().replace(/\/$/, "");
}

const controlsPanel = el<HTMLElement>("controls");
const gearToggle = el<HTMLButtonElement>("gearToggle");

function updateControls(connected: boolean, connecting = false): void {
  connectButton.disabled = connected || connecting;
  disconnectButton.disabled = !connected && !connecting;
  wakeButton.disabled = !connected;
  sleepButton.disabled = !connected;
  connectButton.textContent = connecting ? "Đang kết nối…" : "Kết nối";
  // Once connected, settings tuck away behind the gear; reappear on disconnect.
  gearToggle.hidden = !connected;
  controlsPanel.classList.toggle("collapsed", connected);
}

gearToggle.addEventListener("click", () => controlsPanel.classList.toggle("collapsed"));
connectButton.addEventListener("click", () => void connect());
disconnectButton.addEventListener("click", () => void disconnect());
wakeButton.addEventListener("click", () => {
  void sendClientMessage("robot.wake", {});
  setState("idle");
});
sleepButton.addEventListener("click", () => {
  void sendClientMessage("robot.sleep", {});
  setState("sleeping");
});
window.addEventListener("beforeunload", () => {
  stopHeartbeat();
  client?.disconnect();
});

setState("offline");
