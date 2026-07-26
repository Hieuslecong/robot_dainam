import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../src/main.ts", import.meta.url), "utf8");
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("uses official Pipecat client and SmallWebRTC transport", () => {
  assert.match(source, /@pipecat-ai\/client-js/);
  assert.match(source, /@pipecat-ai\/small-webrtc-transport/);
  assert.match(source, /new PipecatClient/);
  assert.match(source, /new SmallWebRTCTransport/);
});

test("does not implement raw WebRTC signaling or heuristic protocol parsing", () => {
  assert.doesNotMatch(source, /new RTCPeerConnection/);
  assert.doesNotMatch(source, /createOffer\(/);
  assert.doesNotMatch(source, /type\.includes\(/);
});

test("labels local playback control as debug rather than barge-in", () => {
  assert.match(html, /Dừng loa cục bộ \(debug\)/);
  assert.match(source, /server pipeline was not interrupted/);
});


test("filters word-level bot output to avoid duplicate transcript rendering", () => {
  assert.match(source, /aggregated_by === ["']word["']/);
});

test("explicitly requests and exposes AEC/NS/AGC capture settings", () => {
  assert.match(source, /echoCancellation: true/);
  assert.match(source, /noiseSuppression: true/);
  assert.match(source, /autoGainControl: true/);
  assert.match(source, /applyConstraints/);
  assert.match(source, /getSettings\(\)/);
  assert.match(source, /client\.capture\.settings/);
});
