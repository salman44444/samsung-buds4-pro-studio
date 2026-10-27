#!/usr/bin/env python3
"""
Local HTTP REST API & Interactive Web Control Studio for Samsung Galaxy Buds4 Pro.
Designed with progressive disclosure: essential settings are front-and-center,
while advanced/detailed settings expand smoothly when clicked.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from gi.repository import GLib

from buds4pro_protocol import Buds4ProController


WEB_UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Samsung Galaxy Buds4 Pro Studio (SM-R640)</title>
<style>
  :root {
    --bg: #090b10;
    --card: #121620;
    --card-hover: #171c29;
    --surface: #191f2e;
    --border: rgba(255, 255, 255, 0.08);
    --text: #f3f6fc;
    --muted: #8b98b1;
    --accent: #3b82f6;
    --accent-soft: rgba(59, 130, 246, 0.16);
    --green: #10b981;
    --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: radial-gradient(circle at top, #131a2c 0%, var(--bg) 55%);
    color: var(--text);
    line-height: 1.5;
    padding: 28px 16px 60px;
    min-height: 100vh;
  }
  .shell { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
  header {
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
    background: var(--card); border: 1px solid var(--border);
    border-radius: 20px; padding: 16px 20px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.35);
  }
  .brand { display: flex; align-items: center; gap: 14px; }
  .logo {
    width: 44px; height: 44px; border-radius: 13px;
    background: linear-gradient(135deg, #3b82f6, #6366f1);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 16px;
    box-shadow: 0 4px 16px rgba(59,130,246,0.35);
  }
  .brand h1 { font-size: 18px; font-weight: 700; letter-spacing: -0.2px; }
  .brand p { font-size: 12.5px; color: var(--muted); display: flex; align-items: center; gap: 7px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red); display: inline-block; }
  .dot.on { background: var(--green); box-shadow: 0 0 8px var(--green); }
  .hdr-actions { display: flex; gap: 8px; }
  button, select, input[type="text"] {
    font-family: inherit; font-size: 13px; color: var(--text);
    background: var(--surface); border: 1px solid var(--border);
    padding: 8px 14px; border-radius: 11px; cursor: pointer;
    transition: all 0.16s ease;
  }
  button:hover { border-color: var(--accent); background: #21293d; }
  button.primary { background: var(--accent); border-color: var(--accent); font-weight: 600; }
  button.ghost { background: transparent; }

  /* Hero Battery Cards */
  .hero-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  @media (max-width: 560px) { .hero-grid { grid-template-columns: 1fr; } }
  .bat-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 18px; padding: 16px 18px;
    display: flex; flex-direction: column; gap: 6px;
  }
  .bat-tag { font-size: 11px; font-weight: 700; letter-spacing: 0.7px; color: var(--muted); }
  .bat-num { font-size: 30px; font-weight: 800; letter-spacing: -0.8px; }
  .bat-bar-bg { height: 5px; background: rgba(255,255,255,0.08); border-radius: 99px; overflow: hidden; }
  .bat-bar-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); width: 0%; transition: width 0.3s ease; }
  .pill {
    align-self: flex-start; margin-top: 4px;
    font-size: 11.5px; font-weight: 600; padding: 3px 10px; border-radius: 999px;
    background: rgba(255,255,255,0.06); color: var(--muted);
  }
  .pill.active { background: var(--accent-soft); color: #60a5fa; }

  /* Primary Cards */
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 20px; padding: 20px;
  }
  .sec-head {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 14px;
  }
  .sec-title { font-size: 14px; font-weight: 700; color: var(--text); }
  .sec-sub { font-size: 12px; color: var(--muted); }

  /* Segmented 4-way Noise Control Selector */
  .seg-group {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
    background: #0b0e15; padding: 5px; border-radius: 14px; border: 1px solid var(--border);
  }
  .seg-btn {
    border: none; background: transparent; padding: 11px 8px;
    border-radius: 10px; font-weight: 700; font-size: 13px; color: var(--muted);
  }
  .seg-btn:hover { background: rgba(255,255,255,0.04); color: var(--text); }
  .seg-btn.active {
    background: var(--accent); color: #fff;
    box-shadow: 0 3px 14px rgba(59, 130, 246, 0.4);
  }

  /* Preset Chips */
  .chips { display: flex; flex-wrap: wrap; gap: 7px; }
  .chip {
    border-radius: 999px; padding: 6px 14px; font-size: 12.5px; font-weight: 600;
    background: var(--surface); border: 1px solid var(--border); color: var(--muted);
  }
  .chip.active {
    background: var(--accent); border-color: var(--accent); color: #fff;
  }

  .row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 0; border-top: 1px solid var(--border); gap: 14px;
  }
  .row.first { border-top: none; padding-top: 4px; }
  .row-title { font-size: 13.5px; font-weight: 600; }
  .row-desc { font-size: 12px; color: var(--muted); }

  /* Toggle Switch */
  .switch { position: relative; display: inline-block; width: 44px; height: 24px; flex-shrink: 0; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .toggle {
    position: absolute; cursor: pointer; inset: 0;
    background: #273147; transition: .2s; border-radius: 24px;
  }
  .toggle:before {
    position: absolute; content: ""; height: 18px; width: 18px;
    left: 3px; bottom: 3px; background: white; transition: .2s; border-radius: 50%;
  }
  input:checked + .toggle { background: var(--accent); }
  input:checked + .toggle:before { transform: translateX(20px); }
  input[type="range"] { accent-color: var(--accent); width: 180px; cursor: pointer; }

  /* Collapsible Details / Expandable Drawers */
  details.expander {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 18px; overflow: hidden; transition: background 0.15s ease;
  }
  details.expander > summary {
    list-style: none; cursor: pointer; padding: 16px 20px;
    display: flex; justify-content: space-between; align-items: center;
    user-select: none;
  }
  details.expander > summary::-webkit-details-marker { display: none; }
  details.expander > summary:hover { background: var(--card-hover); }
  .exp-left { display: flex; flex-direction: column; gap: 2px; }
  .exp-title { font-size: 14px; font-weight: 700; }
  .exp-summary { font-size: 12px; color: var(--muted); }
  .exp-right { display: flex; align-items: center; gap: 12px; }
  .chev {
    font-size: 12px; color: var(--muted); transition: transform 0.2s ease;
    width: 24px; height: 24px; border-radius: 50%; background: var(--surface);
    display: flex; align-items: center; justify-content: center;
  }
  details.expander[open] .chev { transform: rotate(180deg); color: var(--text); }
  .exp-body {
    padding: 4px 20px 18px; border-top: 1px solid var(--border);
    background: rgba(0, 0, 0, 0.16);
  }

  /* 9-Band Equalizer Drawer */
  .eq-bands {
    display: grid; grid-template-columns: repeat(9, 1fr); gap: 6px;
    background: #0c0f17; padding: 14px 8px; border-radius: 14px; border: 1px solid var(--border);
    text-align: center; margin-top: 10px;
  }
  .eq-col { display: flex; flex-direction: column; align-items: center; gap: 6px; }
  .eq-col input[type="range"] { writing-mode: vertical-lr; direction: rtl; width: 20px; height: 110px; }
  .eq-freq { font-size: 10.5px; color: var(--muted); font-weight: 600; }
  .eq-gain { font-size: 11.5px; font-weight: 700; color: #60a5fa; }

  .log-box {
    background: #07090e; border: 1px solid var(--border); border-radius: 12px;
    height: 180px; overflow-y: auto; padding: 10px; font-family: monospace; font-size: 11.5px;
    margin-top: 10px;
  }
  .log-tx { color: #60a5fa; }
  .log-rx { color: #34d399; }
</style>
</head>
<body>
<div class="shell">
  <!-- Header -->
  <header>
    <div class="brand">
      <div class="logo">B4P</div>
      <div>
        <h1 id="hdr-title">Salman's Buds4 Pro</h1>
        <p><span class="dot" id="conn-dot"></span><span id="conn-text">Connecting...</span></p>
      </div>
    </div>
    <div class="hdr-actions">
      <button class="primary" id="btn-connect" onclick="api('connect')">Connect</button>
      <button class="danger" id="btn-disconnect" onclick="api('disconnect')">Disconnect</button>
      <button class="ghost" onclick="api('refresh')" title="Refresh Telemetry">↻</button>
    </div>
  </header>

  <!-- 1. Hero Battery Cards (Always Visible) -->
  <div class="hero-grid">
    <div class="bat-card">
      <div class="bat-tag">LEFT EARBUD</div>
      <div class="bat-num" id="bat-l">--%</div>
      <div class="bat-bar-bg"><div class="bat-bar-fill" id="bar-l"></div></div>
      <span class="pill" id="place-l">Disconnected</span>
    </div>
    <div class="bat-card">
      <div class="bat-tag">RIGHT EARBUD</div>
      <div class="bat-num" id="bat-r">--%</div>
      <div class="bat-bar-bg"><div class="bat-bar-fill" id="bar-r"></div></div>
      <span class="pill" id="place-r">Disconnected</span>
    </div>
    <div class="bat-card">
      <div class="bat-tag">CHARGING CASE</div>
      <div class="bat-num" id="bat-c">--</div>
      <div class="bat-bar-bg"><div class="bat-bar-fill" id="bar-c"></div></div>
      <span class="pill" id="place-c">Standby</span>
    </div>
  </div>

  <!-- 2. Primary Noise Control Card (Most Used — Always Visible) -->
  <div class="card">
    <div class="sec-head">
      <div>
        <div class="sec-title">Noise Controls</div>
        <div class="sec-sub" id="nc-current-label">Active Noise Canceling</div>
      </div>
    </div>
    <div class="seg-group">
      <button class="seg-btn" id="nc-btn-0" onclick="api('set_noise_control', {mode: 0})">Off</button>
      <button class="seg-btn" id="nc-btn-1" onclick="api('set_noise_control', {mode: 1})">ANC</button>
      <button class="seg-btn" id="nc-btn-2" onclick="api('set_noise_control', {mode: 2})">Ambient</button>
      <button class="seg-btn" id="nc-btn-3" onclick="api('set_noise_control', {mode: 3})">Adaptive</button>
    </div>

    <!-- Contextual ANC Level Slider (Shown only when ANC is active) -->
    <div class="row" id="row-anc-level" style="margin-top: 10px;">
      <div>
        <div class="row-title">ANC Strength</div>
        <div class="row-desc" id="anc-level-val">Level 5 of 5</div>
      </div>
      <input type="range" min="0" max="4" id="anc-level" onchange="api('set_anc_level', {level: +this.value})">
    </div>

    <!-- Contextual Ambient Volume Slider (Shown only when Ambient/Adaptive is active) -->
    <div class="row" id="row-amb-vol" style="margin-top: 10px; display: none;">
      <div>
        <div class="row-title">Ambient Sound Volume</div>
        <div class="row-desc" id="amb-vol-val">Level 5 of 5</div>
      </div>
      <input type="range" min="0" max="4" id="amb-vol" onchange="api('set_ambient_volume', {volume: +this.value})">
    </div>

    <!-- Quick Voice Detect Toggle -->
    <div class="row">
      <div>
        <div class="row-title">Voice Detect</div>
        <div class="row-desc">Switch to Ambient Sound & lower media when you speak</div>
      </div>
      <label class="switch"><input type="checkbox" id="conv-det" onchange="api('set_conversation_detect', {enabled: this.checked})"><span class="toggle"></span></label>
    </div>
  </div>

  <!-- 3. Primary Sound & Equalizer Card (Presets & 360 Audio visible; 9-Band Custom EQ expands on click) -->
  <div class="card">
    <div class="sec-head">
      <div>
        <div class="sec-title">Equalizer & 360 Audio</div>
        <div class="sec-sub" id="eq-name-label">Balanced (Off)</div>
      </div>
      <button class="ghost" onclick="toggleEqDrawer()" id="btn-eq-drawer">Fine-Tune 9-Band EQ ▾</button>
    </div>
    <div class="chips">
      <button class="chip" id="eq-btn-0" onclick="api('set_equalizer_preset', {mode: 0})">Balanced</button>
      <button class="chip" id="eq-btn-1" onclick="api('set_equalizer_preset', {mode: 1})">Bass Boost</button>
      <button class="chip" id="eq-btn-2" onclick="api('set_equalizer_preset', {mode: 2})">Soft</button>
      <button class="chip" id="eq-btn-3" onclick="api('set_equalizer_preset', {mode: 3})">Dynamic</button>
      <button class="chip" id="eq-btn-4" onclick="api('set_equalizer_preset', {mode: 4})">Clear</button>
      <button class="chip" id="eq-btn-5" onclick="api('set_equalizer_preset', {mode: 5})">Treble Boost</button>
      <button class="chip" id="eq-btn-7" onclick="openAndSendCustomEq()">Custom</button>
    </div>

    <!-- Hidden 9-Band EQ Drawer (Revealed when Custom or Fine-Tune is clicked) -->
    <div id="eq-drawer" style="display: none; margin-top: 12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:12px;color:var(--muted);">9-Band Custom Equalizer (-10 dB to +10 dB)</span>
        <button onclick="resetCustomEq()" style="padding:4px 10px;font-size:11.5px;">Reset Flat 0 dB</button>
      </div>
      <div class="eq-bands" id="eq-sliders"></div>
      <div class="row">
        <div>
          <div class="row-title">Left / Right Sound Balance</div>
          <div class="row-desc" id="stereo-bal-val">Center</div>
        </div>
        <input type="range" min="0" max="32" id="stereo-bal" onchange="api('set_stereo_balance', {value: +this.value})">
      </div>
    </div>

    <!-- Quick 360 Spatial Audio & Gaming Toggles -->
    <div class="row" style="margin-top: 10px;">
      <div>
        <div class="row-title">360 Spatial Audio</div>
        <div class="row-desc">Immersive multi-dimensional spatial sound</div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;">
        <label style="font-size:12px;color:var(--muted);display:flex;align-items:center;gap:5px;cursor:pointer;">
          <input type="checkbox" id="spatial-ht" onchange="sendSpatial()"> Head Track
        </label>
        <label class="switch"><input type="checkbox" id="spatial-on" onchange="sendSpatial()"><span class="toggle"></span></label>
      </div>
    </div>
    <div class="row">
      <div>
        <div class="row-title">Gaming Mode</div>
        <div class="row-desc">Low-latency wireless audio synchronization</div>
      </div>
      <label class="switch"><input type="checkbox" id="game-mode" onchange="api('set_gaming_mode', {enabled: this.checked})"><span class="toggle"></span></label>
    </div>
  </div>

  <!-- 4. Expandable Secondary Settings (Hidden until clicked) -->

  <!-- 4A. Smart Environment & Custom Ambient -->
  <details class="expander">
    <summary>
      <div class="exp-left">
        <span class="exp-title">Smart Environment & Custom Ambient</span>
        <span class="exp-summary" id="sum-env">Adaptive Vol • Siren Detect • Per-Ear Ambient</span>
      </div>
      <div class="exp-right"><span class="chev">▾</span></div>
    </summary>
    <div class="exp-body">
      <div class="row first">
        <div>
          <div class="row-title">Voice Detect Timeout</div>
          <div class="row-desc">Delay before returning to ANC after speaking stops</div>
        </div>
        <select id="conv-dur" onchange="api('set_conversation_detect_duration', {duration: +this.value})">
          <option value="0">5 seconds</option>
          <option value="1">10 seconds</option>
          <option value="2">15 seconds</option>
        </select>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Adaptive Volume</div>
          <div class="row-desc">Automatically adjust playback volume to surrounding noise</div>
        </div>
        <label class="switch"><input type="checkbox" id="adapt-vol" onchange="api('set_adaptive_volume', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Siren Detect</div>
          <div class="row-desc">Allow ambient pass-through when sirens are detected</div>
        </div>
        <label class="switch"><input type="checkbox" id="siren-det" onchange="api('set_siren_detect', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Noise Controls with One Earbud</div>
          <div class="row-desc">Allow ANC & Ambient Sound when wearing a single earbud</div>
        </div>
        <label class="switch"><input type="checkbox" id="nc-one" onchange="api('set_noise_controls_one_earbud', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Custom Ambient Sound</div>
          <div class="row-desc">Independent Left/Right ambient amplification & tone</div>
        </div>
        <label class="switch"><input type="checkbox" id="amb-cust-on" onchange="sendCustomAmbient()"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div class="row-title">Left / Right Ambient Balance</div>
        <div style="display:flex;gap:8px;">
          <input type="range" min="0" max="4" id="amb-cust-l" style="width:95px;" onchange="sendCustomAmbient()" title="Left Ear">
          <input type="range" min="0" max="4" id="amb-cust-r" style="width:95px;" onchange="sendCustomAmbient()" title="Right Ear">
        </div>
      </div>
      <div class="row">
        <div class="row-title">Ambient Sound Tone (Soft → Clear)</div>
        <input type="range" min="0" max="4" id="amb-cust-tone" onchange="sendCustomAmbient()">
      </div>
      <div class="row">
        <div>
          <div class="row-title">Extra High Ambient Volume</div>
          <div class="row-desc">Boost ambient pass-through above standard maximum</div>
        </div>
        <label class="switch"><input type="checkbox" id="amb-extra" onchange="api('set_extra_high_ambient', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
    </div>
  </details>

  <!-- 4B. Pinch & Touch Controls -->
  <details class="expander">
    <summary>
      <div class="exp-left">
        <span class="exp-title">Pinch & Touch Controls</span>
        <span class="exp-summary" id="sum-touch">Touch Gestures Unlocked</span>
      </div>
      <div class="exp-right"><span class="chev">▾</span></div>
    </summary>
    <div class="exp-body">
      <div class="row first">
        <div>
          <div class="row-title">Lock All Touch / Pinch Gestures</div>
          <div class="row-desc">Disable all accidental pinch and swipe inputs</div>
        </div>
        <label class="switch"><input type="checkbox" id="tc-lock-all" onchange="sendTouchLocks()"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div class="row-title">Single Pinch (Play / Pause)</div>
        <label class="switch"><input type="checkbox" id="tc-single" onchange="sendTouchLocks()"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div class="row-title">Double Pinch (Next Track)</div>
        <label class="switch"><input type="checkbox" id="tc-double" onchange="sendTouchLocks()"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div class="row-title">Triple Pinch (Previous Track)</div>
        <label class="switch"><input type="checkbox" id="tc-triple" onchange="sendTouchLocks()"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div class="row-title">Pinch & Hold</div>
        <label class="switch"><input type="checkbox" id="tc-hold" onchange="sendTouchLocks()"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div class="row-title">Call Gestures (Double Pinch Answer / Hold Decline)</div>
        <div style="display:flex;gap:10px;">
          <label class="switch"><input type="checkbox" id="tc-call-dbl" onchange="sendTouchLocks()"><span class="toggle"></span></label>
          <label class="switch"><input type="checkbox" id="tc-call-hold" onchange="sendTouchLocks()"><span class="toggle"></span></label>
        </div>
      </div>
      <div class="row">
        <div class="row-title">Left / Right Pinch & Hold Action</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <select id="tc-opt-l" onchange="sendTouchOptions()">
            <option value="2">L: Switch Noise Controls</option>
            <option value="1">L: Voice Assistant</option>
            <option value="3">L: Volume Down</option>
            <option value="4">L: Spotify Spot On</option>
          </select>
          <select id="tc-opt-r" onchange="sendTouchOptions()">
            <option value="2">R: Switch Noise Controls</option>
            <option value="1">R: Voice Assistant</option>
            <option value="3">R: Volume Up</option>
            <option value="4">R: Spotify Spot On</option>
          </select>
        </div>
      </div>
      <div class="row">
        <div class="row-title">Left Pinch & Hold Noise Cycle</div>
        <div style="display:flex;gap:10px;font-size:12.5px;">
          <label><input type="checkbox" id="cyc-l-anc" onchange="sendNcCycle()"> ANC</label>
          <label><input type="checkbox" id="cyc-l-amb" onchange="sendNcCycle()"> Ambient</label>
          <label><input type="checkbox" id="cyc-l-adp" onchange="sendNcCycle()"> Adaptive</label>
          <label><input type="checkbox" id="cyc-l-off" onchange="sendNcCycle()"> Off</label>
        </div>
      </div>
      <div class="row">
        <div class="row-title">Right Pinch & Hold Noise Cycle</div>
        <div style="display:flex;gap:10px;font-size:12.5px;">
          <label><input type="checkbox" id="cyc-r-anc" onchange="sendNcCycle()"> ANC</label>
          <label><input type="checkbox" id="cyc-r-amb" onchange="sendNcCycle()"> Ambient</label>
          <label><input type="checkbox" id="cyc-r-adp" onchange="sendNcCycle()"> Adaptive</label>
          <label><input type="checkbox" id="cyc-r-off" onchange="sendNcCycle()"> Off</label>
        </div>
      </div>
    </div>
  </details>

  <!-- 4C. Blade Lights & Voice Assistant -->
  <details class="expander">
    <summary>
      <div class="exp-left">
        <span class="exp-title">Blade Lights & Voice Assistant</span>
        <span class="exp-summary" id="sum-lights">Blade Lights: Blink • Voice Commands</span>
      </div>
      <div class="exp-right"><span class="chev">▾</span></div>
    </summary>
    <div class="exp-body">
      <div class="row first">
        <div>
          <div class="row-title">Blade Lighting Style</div>
          <div class="row-desc">LED lighting mode when earbuds are worn/outside case</div>
        </div>
        <select id="light-mode" onchange="api('set_lighting_mode', {mode: +this.value})">
          <option value="0">Blink</option>
          <option value="1">Fade In / Out</option>
          <option value="2">Steady</option>
        </select>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Voice Controls (Hot Commands)</div>
          <div class="row-desc">Control music, volume & calls by voice without wake word</div>
        </div>
        <label class="switch"><input type="checkbox" id="hotcmd-on" onchange="api('set_hot_command', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Bixby Voice Wake-up</div>
          <div class="row-desc">Wake Bixby hands-free while wearing earbuds</div>
        </div>
        <label class="switch"><input type="checkbox" id="bixby-on" onchange="api('set_bixby_wakeup', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Speak Seamlessly</div>
          <div class="row-desc">Speak commands right after waking Bixby without waiting</div>
        </div>
        <label class="switch"><input type="checkbox" id="speak-seam" onchange="api('set_speak_seamlessly', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
    </div>
  </details>

  <!-- 4D. Calls, Connection & Find My Earbuds -->
  <details class="expander">
    <summary>
      <div class="exp-left">
        <span class="exp-title">Calls, Connection & Find My Earbuds</span>
        <span class="exp-summary" id="sum-calls">Sidetone • Seamless Connection • Ring & Fit Test</span>
      </div>
      <div class="exp-right"><span class="chev">▾</span></div>
    </summary>
    <div class="exp-body">
      <div class="row first">
        <div>
          <div class="row-title">Use Ambient Sound During Calls (Sidetone)</div>
          <div class="row-desc">Hear your own voice naturally while on phone calls</div>
        </div>
        <label class="switch"><input type="checkbox" id="sidetone" onchange="api('set_sidetone', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Extra Clear Call Sound</div>
          <div class="row-desc">Enhance speech clarity during calls</div>
        </div>
        <label class="switch"><input type="checkbox" id="clear-call" onchange="api('set_extra_clear_call', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Seamless Earbud Connection</div>
          <div class="row-desc">Allow switching Bluetooth connection between paired devices</div>
        </div>
        <label class="switch"><input type="checkbox" id="seamless-conn" onchange="api('set_seamless_connection', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Auto Pause / Resume When Removed</div>
          <div class="row-desc">Pause playback when removing earbuds</div>
        </div>
        <label class="switch"><input type="checkbox" id="auto-pause" onchange="api('set_auto_pause_resume', {enabled: this.checked})"><span class="toggle"></span></label>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Automatic Call Path & Neck Stretch Reminders</div>
        </div>
        <div style="display:flex;gap:10px;">
          <label class="switch" title="Call Path Control"><input type="checkbox" id="call-path" onchange="api('set_call_path_control', {enabled: this.checked})"><span class="toggle"></span></label>
          <label class="switch" title="Neck Posture Reminder"><input type="checkbox" id="neck-posture" onchange="api('set_neck_posture_reminder', {enabled: this.checked})"><span class="toggle"></span></label>
        </div>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Find My Earbuds</div>
          <div class="row-desc">Play locator chime on Left / Right earbuds</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <button onclick="api('find_my_buds', {active: true, wearing: true})">Ring</button>
          <button onclick="api('find_my_buds', {active: false})">Stop</button>
          <button onclick="api('mute_buds', {left: true, right: false})">Mute L</button>
          <button onclick="api('mute_buds', {left: false, right: true})">Mute R</button>
        </div>
      </div>
      <div class="row">
        <div>
          <div class="row-title">Earbud Fit Test & Hardware Self-Test</div>
          <div class="row-desc" id="diag-status">Fit: Not Run • Self-Test: Not Run</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <button onclick="api('fit_test', {start: true})">Fit Test</button>
          <button onclick="api('self_test')">Self-Test</button>
          <button onclick="api('sync_time')">Sync Clock</button>
          <button onclick="api('pairing_mode')">Pairing Mode</button>
        </div>
      </div>
    </div>
  </details>

  <!-- 4E. Hardware Telemetry & Developer SPP Packet Sniffer -->
  <details class="expander">
    <summary>
      <div class="exp-left">
        <span class="exp-title">Hardware Details & Developer SPP Console</span>
        <span class="exp-summary" id="sum-hw">FW: -- • Temps & Voltage • Raw Packet Sniffer</span>
      </div>
      <div class="exp-right"><span class="chev">▾</span></div>
    </summary>
    <div class="exp-body">
      <div class="row first">
        <div class="row-title">Firmware & Hardware</div>
        <div class="row-desc" id="hw-fw-info" style="font-family:monospace;">--</div>
      </div>
      <div class="row">
        <div class="row-title">Thermistors, Voltage & Cycles</div>
        <div class="row-desc" id="thermal-info" style="font-family:monospace;">--</div>
      </div>
      <div class="row">
        <div class="row-title">SKU & Serial Numbers</div>
        <div class="row-desc" id="serial-info" style="font-family:monospace;">--</div>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px;">
        <input type="text" id="raw-id" placeholder="MsgId (e.g. 120 or 0x78)" style="width:170px;">
        <input type="text" id="raw-hex" placeholder="Payload Hex (e.g. 01)" style="flex:1;">
        <button class="primary" onclick="sendRawCmd()">Send SPP</button>
      </div>
      <div class="log-box" id="pkt-log"></div>
    </div>
  </details>
</div>

<script>
const FREQS = ["63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"];
const LIGHT_LABELS = {0: "Blink", 1: "Fade In/Out", 2: "Steady"};
let currentBands = [0,0,0,0,0,0,0,0,0];

function initEqSliders() {
  const wrap = document.getElementById("eq-sliders");
  wrap.innerHTML = "";
  FREQS.forEach((f, idx) => {
    const col = document.createElement("div");
    col.className = "eq-col";
    col.innerHTML = `
      <span class="eq-gain" id="eq-gain-${idx}">0dB</span>
      <input type="range" min="-10" max="10" value="0" id="eq-band-${idx}" oninput="updateBandLabel(${idx}, this.value)" onchange="sendCustomEq()">
      <span class="eq-freq">${f}</span>
    `;
    wrap.appendChild(col);
  });
}

function toggleEqDrawer(forceOpen = false) {
  const d = document.getElementById("eq-drawer");
  const isHidden = d.style.display === "none";
  const show = forceOpen ? true : isHidden;
  d.style.display = show ? "block" : "none";
  document.getElementById("btn-eq-drawer").textContent = show ? "Hide 9-Band EQ ▴" : "Fine-Tune 9-Band EQ ▾";
}

function openAndSendCustomEq() {
  toggleEqDrawer(true);
  sendCustomEq();
}

function updateBandLabel(idx, val) {
  currentBands[idx] = parseInt(val, 10);
  const sign = val > 0 ? "+" : "";
  document.getElementById(`eq-gain-${idx}`).textContent = `${sign}${val}dB`;
}

async function api(action, body = {}) {
  const res = await fetch(`/api/${action}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (data.state) renderState(data.state, data.packets || []);
}

function sendCustomEq() {
  for (let i = 0; i < 9; i++) {
    currentBands[i] = parseInt(document.getElementById(`eq-band-${i}`).value, 10);
  }
  api("set_custom_equalizer", {bands: currentBands});
}

function resetCustomEq() {
  for (let i = 0; i < 9; i++) {
    document.getElementById(`eq-band-${i}`).value = 0;
    updateBandLabel(i, 0);
  }
  sendCustomEq();
}

function sendSpatial() {
  api("set_spatial_audio", {
    enabled: document.getElementById("spatial-on").checked,
    head_tracking: document.getElementById("spatial-ht").checked
  });
}

function sendCustomAmbient() {
  api("set_customize_ambient", {
    enabled: document.getElementById("amb-cust-on").checked,
    left_vol: +document.getElementById("amb-cust-l").value,
    right_vol: +document.getElementById("amb-cust-r").value,
    tone: +document.getElementById("amb-cust-tone").value
  });
}

function sendTouchLocks() {
  api("set_touchpad_gestures", {
    lock_all: document.getElementById("tc-lock-all").checked,
    single_pinch: document.getElementById("tc-single").checked,
    double_pinch: document.getElementById("tc-double").checked,
    triple_pinch: document.getElementById("tc-triple").checked,
    pinch_hold: document.getElementById("tc-hold").checked,
    double_pinch_call: document.getElementById("tc-call-dbl").checked,
    pinch_hold_call: document.getElementById("tc-call-hold").checked
  });
}

function sendTouchOptions() {
  api("set_touchpad_options", {
    left: +document.getElementById("tc-opt-l").value,
    right: +document.getElementById("tc-opt-r").value
  });
}

function sendNcCycle() {
  api("set_pinch_hold_nc_cycle", {
    left_anc: document.getElementById("cyc-l-anc").checked,
    left_ambient: document.getElementById("cyc-l-amb").checked,
    left_adaptive: document.getElementById("cyc-l-adp").checked,
    left_off: document.getElementById("cyc-l-off").checked,
    right_anc: document.getElementById("cyc-r-anc").checked,
    right_ambient: document.getElementById("cyc-r-amb").checked,
    right_adaptive: document.getElementById("cyc-r-adp").checked,
    right_off: document.getElementById("cyc-r-off").checked
  });
}

function sendRawCmd() {
  const idRaw = document.getElementById("raw-id").value.trim();
  const hexRaw = document.getElementById("raw-hex").value.trim();
  const msg_id = idRaw.startsWith("0x") ? parseInt(idRaw, 16) : parseInt(idRaw, 10);
  if (isNaN(msg_id)) return;
  api("send_raw", {msg_id, payload_hex: hexRaw});
}

function renderState(s, packets) {
  document.getElementById("hdr-title").textContent = s.device_name;
  const dot = document.getElementById("conn-dot");
  dot.className = s.connected ? "dot on" : "dot";
  document.getElementById("conn-text").textContent = s.connected
    ? `Connected (${s.device_mac}) • ${s.noise_control_mode_name}`
    : `Disconnected (${s.device_mac})`;
  document.getElementById("btn-connect").textContent = s.connected ? "Reconnect" : "Connect";
  document.getElementById("btn-connect").className = s.connected ? "ghost" : "primary";

  // Hero Cards
  document.getElementById("bat-l").textContent = `${s.battery_left}%`;
  document.getElementById("bar-l").style.width = `${Math.min(100, Math.max(0, s.battery_left))}%`;
  const plL = document.getElementById("place-l");
  plL.textContent = s.placement_left_name + (s.charging_left ? " ⚡" : "");
  plL.className = s.placement_left === 1 ? "pill active" : "pill";

  document.getElementById("bat-r").textContent = `${s.battery_right}%`;
  document.getElementById("bar-r").style.width = `${Math.min(100, Math.max(0, s.battery_right))}%`;
  const plR = document.getElementById("place-r");
  plR.textContent = s.placement_right_name + (s.charging_right ? " ⚡" : "");
  plR.className = s.placement_right === 1 ? "pill active" : "pill";

  const hasCase = s.battery_case > 0 && s.battery_case <= 100;
  document.getElementById("bat-c").textContent = hasCase ? `${s.battery_case}%` : "Closed";
  document.getElementById("bar-c").style.width = hasCase ? `${s.battery_case}%` : "0%";
  const plC = document.getElementById("place-c");
  plC.textContent = hasCase ? (s.charging_case ? "Charging ⚡" : "Case Open") : "Standby";
  plC.className = hasCase ? "pill active" : "pill";

  // Noise Control + Contextual Sliders
  document.getElementById("nc-current-label").textContent = s.noise_control_mode_name;
  [0,1,2,3].forEach(m => {
    document.getElementById(`nc-btn-${m}`).className = s.noise_control_mode === m ? "seg-btn active" : "seg-btn";
  });
  document.getElementById("row-anc-level").style.display = s.noise_control_mode === 1 ? "flex" : "none";
  document.getElementById("row-amb-vol").style.display = (s.noise_control_mode === 2 || s.noise_control_mode === 3) ? "flex" : "none";

  document.getElementById("anc-level").value = s.anc_level;
  document.getElementById("anc-level-val").textContent = `Level ${s.anc_level + 1} of 5`;
  document.getElementById("amb-vol").value = s.ambient_volume;
  document.getElementById("amb-vol-val").textContent = `Level ${s.ambient_volume + 1} of 5`;
  document.getElementById("conv-det").checked = s.detect_conversations;

  // Equalizer & 360 Audio
  document.getElementById("eq-name-label").textContent = s.equalizer_name;
  [0,1,2,3,4,5,7].forEach(m => {
    const el = document.getElementById(`eq-btn-${m}`);
    if (el) el.className = s.equalizer_mode === m ? "chip active" : "chip";
  });
  if (Array.isArray(s.custom_eq_bands) && s.custom_eq_bands.length === 9) {
    s.custom_eq_bands.forEach((v, idx) => {
      const sl = document.getElementById(`eq-band-${idx}`);
      if (sl && document.activeElement !== sl) {
        sl.value = v;
        updateBandLabel(idx, v);
      }
    });
  }
  document.getElementById("spatial-on").checked = s.spatial_audio;
  document.getElementById("spatial-ht").checked = s.spatial_head_tracking;
  document.getElementById("stereo-bal").value = s.stereo_balance;
  document.getElementById("stereo-bal-val").textContent = s.stereo_balance === 16 ? "Center" : (s.stereo_balance < 16 ? `Left +${16-s.stereo_balance}` : `Right +${s.stereo_balance-16}`);
  document.getElementById("game-mode").checked = s.gaming_mode || s.adjust_sound_sync;

  // Expandable Section Summaries & Inputs
  document.getElementById("conv-dur").value = s.detect_conversations_duration;
  document.getElementById("siren-det").checked = s.siren_detect;
  document.getElementById("adapt-vol").checked = s.adaptive_volume;
  document.getElementById("nc-one").checked = s.noise_controls_with_one_earbud;
  document.getElementById("amb-cust-on").checked = s.ambient_custom_enabled;
  document.getElementById("amb-cust-l").value = s.ambient_custom_left;
  document.getElementById("amb-cust-r").value = s.ambient_custom_right;
  document.getElementById("amb-cust-tone").value = s.ambient_custom_tone;
  document.getElementById("amb-extra").checked = s.extra_high_ambient;
  document.getElementById("sum-env").textContent =
    `Adaptive Vol: ${s.adaptive_volume ? 'On' : 'Off'} • Siren: ${s.siren_detect ? 'On' : 'Off'} • Custom Ambient: ${s.ambient_custom_enabled ? 'On' : 'Off'}`;

  document.getElementById("tc-lock-all").checked = s.touchpad_lock_all;
  document.getElementById("tc-single").checked = s.single_pinch_on;
  document.getElementById("tc-double").checked = s.double_pinch_on;
  document.getElementById("tc-triple").checked = s.triple_pinch_on;
  document.getElementById("tc-hold").checked = s.pinch_hold_on;
  document.getElementById("tc-call-dbl").checked = s.double_pinch_call_on;
  document.getElementById("tc-call-hold").checked = s.pinch_hold_call_on;
  document.getElementById("tc-opt-l").value = s.touch_option_left;
  document.getElementById("tc-opt-r").value = s.touch_option_right;
  document.getElementById("cyc-l-anc").checked = s.nc_cycle_left_anc;
  document.getElementById("cyc-l-amb").checked = s.nc_cycle_left_ambient;
  document.getElementById("cyc-l-adp").checked = s.nc_cycle_left_adaptive;
  document.getElementById("cyc-l-off").checked = s.nc_cycle_left_off;
  document.getElementById("cyc-r-anc").checked = s.nc_cycle_right_anc;
  document.getElementById("cyc-r-amb").checked = s.nc_cycle_right_ambient;
  document.getElementById("cyc-r-adp").checked = s.nc_cycle_right_adaptive;
  document.getElementById("cyc-r-off").checked = s.nc_cycle_right_off;
  document.getElementById("sum-touch").textContent = s.touchpad_lock_all ? "Locked (All gestures disabled)" : "Unlocked • Pinch & Hold active";

  document.getElementById("light-mode").value = s.lighting_control;
  document.getElementById("bixby-on").checked = s.bixby_wakeup;
  document.getElementById("hotcmd-on").checked = s.hot_command_enabled;
  document.getElementById("speak-seam").checked = s.speak_seamlessly;
  document.getElementById("sum-lights").textContent =
    `Blade Lights: ${LIGHT_LABELS[s.lighting_control] || 'Blink'} • Voice Cmds: ${s.hot_command_enabled ? 'On' : 'Off'} • Bixby: ${s.bixby_wakeup ? 'On' : 'Off'}`;

  document.getElementById("sidetone").checked = s.sidetone_enabled;
  document.getElementById("clear-call").checked = s.extra_clear_call;
  document.getElementById("seamless-conn").checked = s.seamless_connection;
  document.getElementById("auto-pause").checked = s.auto_pause_resume;
  document.getElementById("call-path").checked = s.call_path_control;
  document.getElementById("neck-posture").checked = s.neck_stretch_calibration;
  document.getElementById("sum-calls").textContent =
    `Sidetone: ${s.sidetone_enabled ? 'On' : 'Off'} • Clear Call: ${s.extra_clear_call ? 'On' : 'Off'} • Seamless Conn: ${s.seamless_connection ? 'On' : 'Off'}`;
  document.getElementById("diag-status").textContent =
    `Fit: L=${s.fit_test_left}, R=${s.fit_test_right} • Self-Test: ${s.self_test_passed === null ? "Not Run" : (s.self_test_passed ? "PASSED" : "FAILED")}`;

  document.getElementById("sum-hw").textContent =
    `FW: ${s.fw_version_left || 'R640XXU0AZD2'} • Temps: ${s.temp_left_c}°C / ${s.temp_right_c}°C • Cell: ${s.vcell_mv} mV`;
  document.getElementById("hw-fw-info").textContent =
    `Buds: ${s.fw_version_left || '--'} | Case: ${s.fw_version_cradle || '--'} | HW: ${s.hw_version || '--'} | Touch: ${s.touch_fw_version || '--'}`;
  document.getElementById("thermal-info").textContent =
    `L: ${s.temp_left_c}°C (${s.cycles_left} cyc) | R: ${s.temp_right_c}°C (${s.cycles_right} cyc) | Cell: ${s.vcell_mv} mV`;
  document.getElementById("serial-info").textContent =
    `${s.sku_left} | L:${s.serial_left || '--'} R:${s.serial_right || '--'} C:${s.serial_cradle || '--'}`;

  if (packets && packets.length) {
    const logEl = document.getElementById("pkt-log");
    logEl.innerHTML = packets.slice(-50).reverse().map(p =>
      `<div class="${p.direction === 'TX' ? 'log-tx' : 'log-rx'}">[${p.timestamp}] ${p.direction} id=${p.msg_id} (${p.msg_hex}) ${p.name.padEnd(28, ' ')} len=${String(p.length).padStart(3, ' ')} | ${p.payload_hex}</div>`
    ).join("");
  }
}

async function pollState() {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    if (data.state) renderState(data.state, data.packets || []);
  } catch (e) {}
}

initEqSliders();
pollState();
setInterval(pollState, 1200);
</script>
</body>
</html>
"""


class Buds4ProHttpServer:
    """Thread-safe HTTP server that dispatches commands onto the GLib main loop."""

    def __init__(self, controller: Buds4ProController, host: str = "127.0.0.1", port: int = 8765):
        self.controller = controller
        self.host = host
        self.port = port
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def _run_on_glib(self, fn):
        done = threading.Event()
        result: Dict[str, Any] = {"ok": False}

        def wrapper():
            try:
                result["ok"] = fn()
            except Exception as e:
                result["error"] = str(e)
            finally:
                done.set()
            return False

        GLib.idle_add(wrapper)
        done.wait(timeout=3.0)
        return result

    def handle_action(self, action: str, body: Dict[str, Any]) -> Dict[str, Any]:
        c = self.controller
        if action == "connect":
            self._run_on_glib(lambda: (c.connect(), True)[1])
        elif action == "disconnect":
            self._run_on_glib(lambda: (c.disconnect(), True)[1])
        elif action == "refresh":
            self._run_on_glib(lambda: (c.request_telemetry_refresh(), True)[1])
        elif action == "set_noise_control":
            self._run_on_glib(lambda: c.set_noise_control(int(body.get("mode", 1))))
        elif action == "set_anc_level":
            self._run_on_glib(lambda: c.set_anc_level(int(body.get("level", 4))))
        elif action == "set_ambient_volume":
            self._run_on_glib(lambda: c.set_ambient_volume(int(body.get("volume", 4))))
        elif action == "set_extra_high_ambient":
            self._run_on_glib(lambda: c.set_extra_high_ambient(bool(body.get("enabled", False))))
        elif action == "set_customize_ambient":
            self._run_on_glib(
                lambda: c.set_customize_ambient(
                    bool(body.get("enabled", False)),
                    int(body.get("left_vol", 2)),
                    int(body.get("right_vol", 2)),
                    int(body.get("tone", 2)),
                )
            )
        elif action == "set_conversation_detect":
            self._run_on_glib(lambda: c.set_conversation_detect(bool(body.get("enabled", False))))
        elif action == "set_conversation_detect_duration":
            self._run_on_glib(lambda: c.set_conversation_detect_duration(int(body.get("duration", 0))))
        elif action == "set_siren_detect":
            self._run_on_glib(lambda: c.set_siren_detect(bool(body.get("enabled", False))))
        elif action == "set_adaptive_volume":
            self._run_on_glib(lambda: c.set_adaptive_volume(bool(body.get("enabled", False))))
        elif action == "set_noise_controls_one_earbud":
            self._run_on_glib(lambda: c.set_noise_controls_one_earbud(bool(body.get("enabled", False))))
        elif action == "set_equalizer_preset":
            self._run_on_glib(lambda: c.set_equalizer_preset(int(body.get("mode", 0))))
        elif action == "set_custom_equalizer":
            bands = [int(x) for x in body.get("bands", [0] * 9)]
            self._run_on_glib(lambda: c.set_custom_equalizer(bands))
        elif action == "set_stereo_balance":
            self._run_on_glib(lambda: c.set_stereo_balance(int(body.get("value", 16))))
        elif action == "set_spatial_audio":
            self._run_on_glib(
                lambda: c.set_spatial_audio(
                    bool(body.get("enabled", True)),
                    bool(body.get("head_tracking", False)),
                )
            )
        elif action == "set_gaming_mode":
            self._run_on_glib(lambda: c.set_gaming_mode(bool(body.get("enabled", False))))
        elif action == "set_touchpad_gestures":
            self._run_on_glib(
                lambda: c.set_touchpad_gestures(
                    bool(body.get("lock_all", False)),
                    bool(body.get("single_pinch", True)),
                    bool(body.get("double_pinch", True)),
                    bool(body.get("triple_pinch", True)),
                    bool(body.get("pinch_hold", True)),
                    bool(body.get("double_pinch_call", True)),
                    bool(body.get("pinch_hold_call", True)),
                )
            )
        elif action == "set_touchpad_options":
            self._run_on_glib(
                lambda: c.set_touchpad_options(
                    int(body.get("left", 2)),
                    int(body.get("right", 2)),
                )
            )
        elif action == "set_pinch_hold_nc_cycle":
            self._run_on_glib(
                lambda: c.set_pinch_hold_nc_cycle(
                    bool(body.get("left_anc", True)),
                    bool(body.get("left_ambient", True)),
                    bool(body.get("left_adaptive", False)),
                    bool(body.get("left_off", False)),
                    bool(body.get("right_anc", True)),
                    bool(body.get("right_ambient", True)),
                    bool(body.get("right_adaptive", False)),
                    bool(body.get("right_off", False)),
                )
            )
        elif action == "set_lighting_mode":
            self._run_on_glib(lambda: c.set_lighting_mode(int(body.get("mode", 0))))
        elif action == "set_bixby_wakeup":
            self._run_on_glib(lambda: c.set_bixby_wakeup(bool(body.get("enabled", False))))
        elif action == "set_bixby_language":
            self._run_on_glib(lambda: c.set_bixby_language(int(body.get("lang_id", 3))))
        elif action == "set_speak_seamlessly":
            self._run_on_glib(lambda: c.set_speak_seamlessly(bool(body.get("enabled", False))))
        elif action == "set_hot_command":
            self._run_on_glib(lambda: c.set_hot_command(bool(body.get("enabled", False))))
        elif action == "set_sidetone":
            self._run_on_glib(lambda: c.set_sidetone(bool(body.get("enabled", False))))
        elif action == "set_extra_clear_call":
            self._run_on_glib(lambda: c.set_extra_clear_call(bool(body.get("enabled", False))))
        elif action == "set_auto_pause_resume":
            self._run_on_glib(lambda: c.set_auto_pause_resume(bool(body.get("enabled", False))))
        elif action == "set_seamless_connection":
            self._run_on_glib(lambda: c.set_seamless_connection(bool(body.get("enabled", True))))
        elif action == "set_call_path_control":
            self._run_on_glib(lambda: c.set_call_path_control(bool(body.get("enabled", True))))
        elif action == "set_neck_posture_reminder":
            self._run_on_glib(lambda: c.set_neck_posture_reminder(bool(body.get("enabled", False))))
        elif action == "find_my_buds":
            self._run_on_glib(
                lambda: c.set_find_my_buds(
                    bool(body.get("active", False)),
                    bool(body.get("wearing", True)),
                )
            )
        elif action == "mute_buds":
            self._run_on_glib(
                lambda: c.set_find_my_buds_mute(
                    bool(body.get("left", False)),
                    bool(body.get("right", False)),
                )
            )
        elif action == "fit_test":
            self._run_on_glib(lambda: c.run_fit_test(bool(body.get("start", True))))
        elif action == "self_test":
            self._run_on_glib(lambda: c.run_self_test())
        elif action == "pairing_mode":
            self._run_on_glib(lambda: c.start_pairing_mode())
        elif action == "sync_time":
            self._run_on_glib(lambda: c.sync_time())
        elif action == "send_raw":
            mid = int(body.get("msg_id", 0))
            hex_str = str(body.get("payload_hex", "")).strip()
            payload = bytes.fromhex(hex_str) if hex_str else b""
            self._run_on_glib(lambda: c.send_message(mid, payload))

        return {
            "ok": True,
            "state": c.to_dict(),
            "packets": c.packet_log[-60:],
        }

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _send_json(self, obj: dict, status: int = 200):
                raw = json.dumps(obj).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path in ("/", "/index.html"):
                    raw = WEB_UI_HTML.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                elif parsed.path == "/api/state":
                    self._send_json(
                        {
                            "ok": True,
                            "state": parent.controller.to_dict(),
                            "packets": parent.controller.packet_log[-60:],
                        }
                    )
                else:
                    self._send_json({"ok": False, "error": "Not found"}, 404)

            def do_POST(self):
                parsed = urlparse(self.path)
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8") or "{}")
                except Exception:
                    body = {}
                if parsed.path.startswith("/api/"):
                    action = parsed.path[len("/api/") :]
                    resp = parent.handle_action(action, body)
                    self._send_json(resp)
                else:
                    self._send_json({"ok": False, "error": "Unknown endpoint"}, 404)

        ThreadingHTTPServer.allow_reuse_address = True
        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()


if __name__ == "__main__":
    ctrl = Buds4ProController()
    srv = Buds4ProHttpServer(ctrl, "127.0.0.1", 8765)
    srv.start()
    print("Connecting to Samsung Galaxy Buds4 Pro...")
    ctrl.connect(lambda ok, msg: print(f"[Connect] ok={ok}: {msg}"))
    print("Web Studio live at http://127.0.0.1:8765")
    GLib.MainLoop().run()
