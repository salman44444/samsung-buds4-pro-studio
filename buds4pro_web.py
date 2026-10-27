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
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Galaxy Buds4 Pro — Samsung One UI Studio</title>
<style>
  /* ==========================================================================
     Samsung One UI 6 / 7 (Galaxy Wearable) Design System Tokens
     ========================================================================== */
  :root, [data-theme="dark"] {
    --oui-bg: #000000;
    --oui-bg-elevated: #0b0b0d;
    --oui-card: #17171a;
    --oui-card-hover: #1f1f24;
    --oui-card-active: #27272d;
    --oui-surface-2: #222227;
    --oui-surface-3: #2c2c33;
    --oui-divider: rgba(255, 255, 255, 0.08);
    --oui-border: rgba(255, 255, 255, 0.06);
    --oui-text: #fafaff;
    --oui-text-secondary: #9999a3;
    --oui-text-muted: #6e6e77;
    --oui-blue: #387aff;
    --oui-blue-bright: #4d8dff;
    --oui-blue-soft: rgba(56, 122, 255, 0.16);
    --oui-cyan: #00c4b4;
    --oui-green: #2ad181;
    --oui-amber: #ffab1a;
    --oui-red: #ff4d4d;
    --oui-switch-off: #44444c;
    --oui-appbar-bg: rgba(0, 0, 0, 0.78);
    --oui-shadow: 0 10px 30px rgba(0, 0, 0, 0.55);
    --oui-radius-card: 26px;
    --oui-radius-inner: 18px;
    --oui-radius-pill: 999px;
  }

  [data-theme="light"] {
    --oui-bg: #f2f2f7;
    --oui-bg-elevated: #e9e9f0;
    --oui-card: #fcfcff;
    --oui-card-hover: #f3f3f8;
    --oui-card-active: #e8e8f0;
    --oui-surface-2: #ededf4;
    --oui-surface-3: #e0e0ea;
    --oui-divider: rgba(0, 0, 0, 0.07);
    --oui-border: rgba(0, 0, 0, 0.05);
    --oui-text: #121216;
    --oui-text-secondary: #63636e;
    --oui-text-muted: #8e8e99;
    --oui-blue: #0381fe;
    --oui-blue-bright: #006ae6;
    --oui-blue-soft: rgba(3, 129, 254, 0.12);
    --oui-cyan: #00a599;
    --oui-green: #16a35e;
    --oui-amber: #e08b00;
    --oui-red: #e53935;
    --oui-switch-off: #c6c6d0;
    --oui-appbar-bg: rgba(242, 242, 247, 0.85);
    --oui-shadow: 0 6px 22px rgba(0, 0, 0, 0.05);
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-tap-highlight-color: transparent;
  }

  body {
    font-family: 'SamsungOne', 'One UI Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: var(--oui-bg);
    color: var(--oui-text);
    line-height: 1.42;
    min-height: 100vh;
    padding-bottom: 72px;
    transition: background-color 0.25s ease, color 0.25s ease;
  }

  .oui-shell {
    max-width: 640px;
    margin: 0 auto;
    padding: 0 14px;
  }

  /* ==========================================================================
     1. One UI Sticky App Bar & Top Viewing Area (Reachability Principle)
     ========================================================================== */
  .oui-appbar {
    position: sticky;
    top: 0;
    z-index: 50;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    background: var(--oui-appbar-bg);
    padding: 12px 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    transition: border-color 0.2s ease;
  }

  .oui-appbar-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .oui-wearable-badge {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--oui-blue-bright);
    background: var(--oui-blue-soft);
    padding: 4px 10px;
    border-radius: var(--oui-radius-pill);
  }

  .oui-appbar-title {
    font-size: 16.5px;
    font-weight: 700;
    letter-spacing: -0.2px;
    opacity: 0;
    transform: translateY(4px);
    transition: opacity 0.22s ease, transform 0.22s ease;
  }

  .oui-appbar.scrolled .oui-appbar-title {
    opacity: 1;
    transform: translateY(0);
  }

  .oui-appbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .oui-icon-btn {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--oui-text);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.16s ease, transform 0.12s ease;
  }

  .oui-icon-btn:hover {
    background: var(--oui-surface-2);
  }

  .oui-icon-btn:active {
    transform: scale(0.93);
  }

  .oui-pill-btn {
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    color: var(--oui-text);
    background: var(--oui-surface-2);
    border: none;
    padding: 8px 16px;
    border-radius: var(--oui-radius-pill);
    cursor: pointer;
    transition: background 0.16s ease, transform 0.12s ease, color 0.16s ease;
  }

  .oui-pill-btn:hover {
    background: var(--oui-surface-3);
  }

  .oui-pill-btn:active {
    transform: scale(0.96);
  }

  .oui-pill-btn.primary {
    background: var(--oui-blue);
    color: #ffffff;
  }

  .oui-pill-btn.primary:hover {
    background: var(--oui-blue-bright);
  }

  /* One UI Viewing Area (Upper Hero Section) */
  .oui-viewing-area {
    text-align: center;
    padding: 20px 12px 26px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .oui-device-title {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.6px;
    margin-bottom: 6px;
  }

  .oui-conn-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 13px;
    font-weight: 600;
    color: var(--oui-text-secondary);
    background: var(--oui-card);
    padding: 5px 14px;
    border-radius: var(--oui-radius-pill);
    margin-bottom: 22px;
  }

  .oui-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--oui-text-muted);
    transition: background 0.25s ease, box-shadow 0.25s ease;
  }

  .oui-status-dot.connected {
    background: var(--oui-green);
    box-shadow: 0 0 8px rgba(42, 209, 129, 0.7);
  }

  /* Buds4 Pro Vector Illustration Stage */
  .oui-buds-stage {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 26px;
    margin-bottom: 22px;
    width: 100%;
  }

  .oui-bud-graphic {
    width: 78px;
    height: 92px;
    filter: drop-shadow(0 10px 18px rgba(0, 0, 0, 0.35));
    transition: transform 0.3s ease;
  }

  .oui-bud-graphic:hover {
    transform: translateY(-3px);
  }

  .blade-led {
    stroke: var(--oui-blue-bright);
    filter: drop-shadow(0 0 5px var(--oui-blue));
    transition: opacity 0.3s ease;
  }

  /* Galaxy Wearable Battery Strip (L / R / Case) */
  .oui-battery-strip {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    width: 100%;
  }

  @media (max-width: 500px) {
    .oui-battery-strip {
      grid-template-columns: 1fr;
    }
  }

  .oui-bat-pill-card {
    background: var(--oui-card);
    border-radius: 22px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
  }

  .oui-bat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .oui-lr-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 700;
    color: var(--oui-text-secondary);
  }

  .oui-lr-circle {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--oui-surface-3);
    color: var(--oui-text);
    font-size: 11px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .oui-lr-circle.active {
    background: var(--oui-blue);
    color: #fff;
  }

  .oui-bat-value-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 6px;
  }

  .oui-bat-pct {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }

  .oui-bat-state {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--oui-text-secondary);
  }

  .oui-bat-state.in-ear {
    color: var(--oui-blue-bright);
  }

  .oui-bat-bar-track {
    height: 6px;
    background: var(--oui-surface-2);
    border-radius: var(--oui-radius-pill);
    overflow: hidden;
  }

  .oui-bat-bar-fill {
    height: 100%;
    width: 0%;
    background: var(--oui-green);
    border-radius: var(--oui-radius-pill);
    transition: width 0.35s cubic-bezier(0.22, 1, 0.36, 1), background-color 0.25s ease;
  }

  .oui-bat-bar-fill.low {
    background: var(--oui-red);
  }

  /* ==========================================================================
     2. One UI Section Headers & Focus Blocks (Interaction Area)
     ========================================================================== */
  .oui-section-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--oui-text-secondary);
    padding: 18px 18px 8px;
    letter-spacing: 0.1px;
  }

  .oui-block {
    background: var(--oui-card);
    border-radius: var(--oui-radius-card);
    padding: 6px 20px;
    margin-bottom: 12px;
    overflow: hidden;
  }

  .oui-block-padded {
    background: var(--oui-card);
    border-radius: var(--oui-radius-card);
    padding: 20px;
    margin-bottom: 12px;
  }

  /* ==========================================================================
     3. Galaxy Wearable 4-Way Noise Control Selector
     ========================================================================== */
  .oui-nc-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 16px;
  }

  .oui-nc-title {
    font-size: 16px;
    font-weight: 700;
  }

  .oui-nc-active-text {
    font-size: 13px;
    font-weight: 600;
    color: var(--oui-blue-bright);
  }

  .oui-nc-track {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    background: var(--oui-surface-2);
    padding: 8px;
    border-radius: 22px;
  }

  .oui-nc-option {
    border: none;
    background: transparent;
    color: var(--oui-text-secondary);
    padding: 10px 4px;
    border-radius: 16px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    font-family: inherit;
    transition: all 0.2s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .oui-nc-option:hover {
    color: var(--oui-text);
  }

  .oui-nc-icon-circle {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: var(--oui-card);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.22s ease;
    color: var(--oui-text-secondary);
  }

  .oui-nc-label {
    font-size: 12px;
    font-weight: 600;
    line-height: 1.2;
  }

  .oui-nc-option.active {
    color: var(--oui-text);
  }

  .oui-nc-option.active .oui-nc-icon-circle {
    background: var(--oui-blue);
    color: #ffffff;
    box-shadow: 0 4px 14px rgba(56, 122, 255, 0.45);
    transform: scale(1.05);
  }

  .oui-nc-option.active .oui-nc-label {
    color: var(--oui-blue-bright);
    font-weight: 700;
  }

  /* Contextual Level Box inside Noise Control Card */
  .oui-nc-subbox {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid var(--oui-divider);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .oui-slider-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .oui-slider-title {
    font-size: 14px;
    font-weight: 600;
  }

  .oui-slider-val {
    font-size: 13px;
    font-weight: 700;
    color: var(--oui-blue-bright);
  }

  /* One UI Range Slider */
  input[type="range"].oui-range {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 8px;
    background: var(--oui-surface-3);
    border-radius: var(--oui-radius-pill);
    outline: none;
    cursor: pointer;
  }

  input[type="range"].oui-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #ffffff;
    border: 3px solid var(--oui-blue);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    cursor: pointer;
    transition: transform 0.14s ease;
  }

  input[type="range"].oui-range::-webkit-slider-thumb:hover {
    transform: scale(1.12);
  }

  input[type="range"].oui-range::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #ffffff;
    border: 3px solid var(--oui-blue);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    cursor: pointer;
  }

  .oui-scale-labels {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--oui-text-muted);
    font-weight: 600;
    padding: 0 2px;
  }

  /* ==========================================================================
     4. One UI List Rows, Blue Value Subtitles, Switches & Selects
     ========================================================================== */
  .oui-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 15px 0;
    border-top: 1px solid var(--oui-divider);
  }

  .oui-row.first {
    border-top: none;
  }

  .oui-row-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
    flex: 1;
  }

  .oui-row-title {
    font-size: 15.5px;
    font-weight: 600;
    color: var(--oui-text);
  }

  .oui-row-sub {
    font-size: 13px;
    color: var(--oui-text-secondary);
  }

  /* Authentic One UI Blue Value Subtitle */
  .oui-row-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--oui-blue-bright);
  }

  .oui-row-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  /* One UI Vertical Divider before Switch */
  .oui-v-divider {
    width: 1px;
    height: 22px;
    background: var(--oui-divider);
  }

  /* Samsung One UI Pill Switch */
  .oui-switch {
    position: relative;
    display: inline-block;
    width: 46px;
    height: 26px;
    flex-shrink: 0;
  }

  .oui-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .oui-switch-track {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background-color: var(--oui-switch-off);
    border-radius: var(--oui-radius-pill);
    transition: background-color 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .oui-switch-track::before {
    content: "";
    position: absolute;
    height: 20px;
    width: 20px;
    left: 3px;
    bottom: 3px;
    background-color: #ffffff;
    border-radius: 50%;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
    transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .oui-switch input:checked + .oui-switch-track {
    background-color: var(--oui-blue);
  }

  .oui-switch input:checked + .oui-switch-track::before {
    transform: translateX(20px);
  }

  /* One UI Select & Text Inputs */
  select.oui-select,
  input[type="text"].oui-input {
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--oui-blue-bright);
    background: var(--oui-surface-2);
    border: 1px solid transparent;
    padding: 8px 14px;
    border-radius: 14px;
    outline: none;
    cursor: pointer;
    transition: border-color 0.16s ease, background 0.16s ease;
  }

  input[type="text"].oui-input {
    color: var(--oui-text);
    cursor: text;
  }

  select.oui-select:focus,
  input[type="text"].oui-input:focus {
    border-color: var(--oui-blue);
  }

  /* ==========================================================================
     5. One UI Equalizer Preset Pills & 9-Band Custom EQ Drawer
     ========================================================================== */
  .oui-eq-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 6px 0 10px;
  }

  .oui-eq-chip {
    font-family: inherit;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: var(--oui-radius-pill);
    border: none;
    background: var(--oui-surface-2);
    color: var(--oui-text-secondary);
    cursor: pointer;
    transition: all 0.18s ease;
  }

  .oui-eq-chip:hover {
    color: var(--oui-text);
    background: var(--oui-surface-3);
  }

  .oui-eq-chip.active {
    background: var(--oui-blue);
    color: #ffffff;
    box-shadow: 0 3px 12px rgba(56, 122, 255, 0.35);
  }

  .oui-eq-drawer {
    background: var(--oui-surface-2);
    border-radius: 20px;
    padding: 16px 14px;
    margin: 8px 0 10px;
  }

  .oui-eq-bands {
    display: grid;
    grid-template-columns: repeat(9, 1fr);
    gap: 4px;
    padding: 14px 4px 6px;
    text-align: center;
  }

  .oui-eq-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .oui-eq-col input[type="range"] {
    writing-mode: vertical-lr;
    direction: rtl;
    width: 22px;
    height: 116px;
    accent-color: var(--oui-blue);
    cursor: pointer;
  }

  .oui-eq-gain {
    font-size: 11px;
    font-weight: 700;
    color: var(--oui-blue-bright);
  }

  .oui-eq-freq {
    font-size: 10.5px;
    font-weight: 600;
    color: var(--oui-text-secondary);
  }

  /* ==========================================================================
     6. One UI Expandable Category Cards (Galaxy Wearable Menu Items)
     ========================================================================== */
  details.oui-expander {
    background: var(--oui-card);
    border-radius: var(--oui-radius-card);
    margin-bottom: 12px;
    overflow: hidden;
    transition: background-color 0.2s ease;
  }

  details.oui-expander > summary {
    list-style: none;
    cursor: pointer;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    user-select: none;
    transition: background-color 0.15s ease;
  }

  details.oui-expander > summary::-webkit-details-marker {
    display: none;
  }

  details.oui-expander > summary:hover {
    background: var(--oui-card-hover);
  }

  .oui-exp-lead {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
    flex: 1;
  }

  /* One UI Squircle Category Icon Badge */
  .oui-cat-icon {
    width: 40px;
    height: 40px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: #ffffff;
  }

  .oui-cat-icon.teal   { background: linear-gradient(135deg, #00c4b4, #0097a7); }
  .oui-cat-icon.blue   { background: linear-gradient(135deg, #387aff, #1b56d0); }
  .oui-cat-icon.amber  { background: linear-gradient(135deg, #ffab1a, #f57c00); }
  .oui-cat-icon.green  { background: linear-gradient(135deg, #2ad181, #129c58); }
  .oui-cat-icon.purple { background: linear-gradient(135deg, #7c5cff, #5333ed); }
  .oui-cat-icon.slate  { background: linear-gradient(135deg, #5c6bc0, #3949ab); }

  .oui-exp-titles {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .oui-exp-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--oui-text);
  }

  .oui-exp-sub {
    font-size: 13px;
    font-weight: 500;
    color: var(--oui-blue-bright);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .oui-chev {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--oui-text-secondary);
    transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1), background 0.16s ease;
    flex-shrink: 0;
  }

  details.oui-expander[open] > summary .oui-chev {
    transform: rotate(180deg);
    background: var(--oui-surface-2);
    color: var(--oui-text);
  }

  .oui-exp-body {
    padding: 0 20px 10px;
    border-top: 1px solid var(--oui-divider);
  }

  /* Checkboxes styled as One UI Filter Chips */
  .oui-check-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--oui-surface-2);
    padding: 6px 12px;
    border-radius: var(--oui-radius-pill);
    font-size: 12.5px;
    font-weight: 600;
    color: var(--oui-text-secondary);
    cursor: pointer;
    user-select: none;
  }

  .oui-check-chip input {
    accent-color: var(--oui-blue);
  }

  /* Developer SPP Log Box */
  .oui-log-box {
    background: var(--oui-bg-elevated);
    border: 1px solid var(--oui-divider);
    border-radius: 16px;
    height: 185px;
    overflow-y: auto;
    padding: 12px;
    font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
    font-size: 11.5px;
    margin: 10px 0 8px;
  }

  .log-tx { color: var(--oui-blue-bright); }
  .log-rx { color: var(--oui-green); }
</style>
</head>
<body>

<div class="oui-shell">
  <!-- ========================================================================
       One UI Sticky App Bar
       ======================================================================== -->
  <nav class="oui-appbar" id="oui-appbar">
    <div class="oui-appbar-left">
      <span class="oui-wearable-badge">Galaxy Wearable</span>
      <span class="oui-appbar-title" id="appbar-title">Salman's Buds4 Pro</span>
    </div>
    <div class="oui-appbar-actions">
      <button class="oui-pill-btn primary" id="btn-connect" onclick="api('connect')">Connect</button>
      <button class="oui-pill-btn" id="btn-disconnect" onclick="api('disconnect')">Disconnect</button>
      <button class="oui-icon-btn" onclick="api('refresh')" title="Sync telemetry">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
      </button>
      <button class="oui-icon-btn" onclick="toggleTheme()" id="btn-theme" title="Switch One UI Dark / Light Mode">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
      </button>
    </div>
  </nav>

  <!-- ========================================================================
       One UI Viewing Area (Upper Hero Section: Device Graphic & L/R/Case Status)
       ======================================================================== -->
  <section class="oui-viewing-area">
    <h1 class="oui-device-title" id="hdr-title">Salman's Buds4 Pro</h1>
    <div class="oui-conn-pill">
      <span class="oui-status-dot" id="conn-dot"></span>
      <span id="conn-text">Connecting...</span>
    </div>

    <!-- Custom Vector Illustration of Galaxy Buds4 Pro Blade Design -->
    <div class="oui-buds-stage" aria-hidden="true">
      <!-- Left Earbud SVG -->
      <svg class="oui-bud-graphic" viewBox="0 0 80 96" fill="none">
        <ellipse cx="46" cy="30" rx="22" ry="18" fill="#2b2c34" stroke="#454754" stroke-width="2"/>
        <ellipse cx="56" cy="30" rx="11" ry="13" fill="#17181d"/>
        <path d="M26 24 L18 78 L30 82 L38 34 Z" fill="url(#bladeGradL)" stroke="#555869" stroke-width="1.5" stroke-linejoin="round"/>
        <line x1="25" y1="34" x2="20" y2="70" class="blade-led" stroke-width="2.5" stroke-linecap="round"/>
        <defs>
          <linearGradient id="bladeGradL" x1="18" y1="24" x2="38" y2="82" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#4b4e5d"/>
            <stop offset="100%" stop-color="#23252d"/>
          </linearGradient>
        </defs>
      </svg>

      <!-- Right Earbud SVG -->
      <svg class="oui-bud-graphic" viewBox="0 0 80 96" fill="none">
        <ellipse cx="34" cy="30" rx="22" ry="18" fill="#2b2c34" stroke="#454754" stroke-width="2"/>
        <ellipse cx="24" cy="30" rx="11" ry="13" fill="#17181d"/>
        <path d="M54 24 L62 78 L50 82 L42 34 Z" fill="url(#bladeGradR)" stroke="#555869" stroke-width="1.5" stroke-linejoin="round"/>
        <line x1="55" y1="34" x2="60" y2="70" class="blade-led" stroke-width="2.5" stroke-linecap="round"/>
        <defs>
          <linearGradient id="bladeGradR" x1="62" y1="24" x2="42" y2="82" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#4b4e5d"/>
            <stop offset="100%" stop-color="#23252d"/>
          </linearGradient>
        </defs>
      </svg>
    </div>

    <!-- Galaxy Wearable Battery Pills -->
    <div class="oui-battery-strip">
      <div class="oui-bat-pill-card">
        <div class="oui-bat-header">
          <span class="oui-lr-badge"><span class="oui-lr-circle" id="badge-l">L</span> Left</span>
          <span class="oui-bat-state" id="place-l">Disconnected</span>
        </div>
        <div class="oui-bat-value-row">
          <span class="oui-bat-pct" id="bat-l">--%</span>
        </div>
        <div class="oui-bat-bar-track"><div class="oui-bat-bar-fill" id="bar-l"></div></div>
      </div>

      <div class="oui-bat-pill-card">
        <div class="oui-bat-header">
          <span class="oui-lr-badge"><span class="oui-lr-circle" id="badge-r">R</span> Right</span>
          <span class="oui-bat-state" id="place-r">Disconnected</span>
        </div>
        <div class="oui-bat-value-row">
          <span class="oui-bat-pct" id="bat-r">--%</span>
        </div>
        <div class="oui-bat-bar-track"><div class="oui-bat-bar-fill" id="bar-r"></div></div>
      </div>

      <div class="oui-bat-pill-card">
        <div class="oui-bat-header">
          <span class="oui-lr-badge"><span class="oui-lr-circle" id="badge-c">C</span> Case</span>
          <span class="oui-bat-state" id="place-c">Standby</span>
        </div>
        <div class="oui-bat-value-row">
          <span class="oui-bat-pct" id="bat-c">--</span>
        </div>
        <div class="oui-bat-bar-track"><div class="oui-bat-bar-fill" id="bar-c"></div></div>
      </div>
    </div>
  </section>

  <!-- ========================================================================
       One UI Interaction Area — Primary Block 1: Noise Controls
       ======================================================================== -->
  <div class="oui-section-label">Noise controls</div>
  <div class="oui-block-padded">
    <div class="oui-nc-header">
      <span class="oui-nc-title">Mode</span>
      <span class="oui-nc-active-text" id="nc-current-label">Active noise canceling</span>
    </div>

    <!-- Galaxy Wearable 4-Way Circular Icon Pill Selector -->
    <div class="oui-nc-track">
      <button class="oui-nc-option" id="nc-btn-0" onclick="api('set_noise_control', {mode: 0})">
        <span class="oui-nc-icon-circle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="8"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </span>
        <span class="oui-nc-label">Off</span>
      </button>

      <button class="oui-nc-option" id="nc-btn-1" onclick="api('set_noise_control', {mode: 1})">
        <span class="oui-nc-icon-circle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M2 12h3m14 0h3M7 7v10m10-10v10M12 4v16"/></svg>
        </span>
        <span class="oui-nc-label">ANC</span>
      </button>

      <button class="oui-nc-option" id="nc-btn-2" onclick="api('set_noise_control', {mode: 2})">
        <span class="oui-nc-icon-circle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="M5 8a9.5 9.5 0 0 0 0 8m14-8a9.5 9.5 0 0 1 0 8"/></svg>
        </span>
        <span class="oui-nc-label">Ambient</span>
      </button>

      <button class="oui-nc-option" id="nc-btn-3" onclick="api('set_noise_control', {mode: 3})">
        <span class="oui-nc-icon-circle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="m12 3 2.4 5.6L20 11l-5.6 2.4L12 19l-2.4-5.6L4 11l5.6-2.4L12 3Z"/></svg>
        </span>
        <span class="oui-nc-label">Adaptive</span>
      </button>
    </div>

    <!-- Contextual ANC Level Slider (Shown when ANC is selected) -->
    <div class="oui-nc-subbox" id="row-anc-level">
      <div class="oui-slider-header">
        <span class="oui-slider-title">Active noise canceling level</span>
        <span class="oui-slider-val" id="anc-level-val">Level 5 of 5</span>
      </div>
      <input type="range" class="oui-range" min="0" max="4" id="anc-level" onchange="api('set_anc_level', {level: +this.value})">
      <div class="oui-scale-labels"><span>Low</span><span>•••••</span><span>Max</span></div>
    </div>

    <!-- Contextual Ambient Volume Slider (Shown when Ambient/Adaptive is selected) -->
    <div class="oui-nc-subbox" id="row-amb-vol" style="display: none;">
      <div class="oui-slider-header">
        <span class="oui-slider-title">Ambient sound volume</span>
        <span class="oui-slider-val" id="amb-vol-val">Level 5 of 5</span>
      </div>
      <input type="range" class="oui-range" min="0" max="4" id="amb-vol" onchange="api('set_ambient_volume', {volume: +this.value})">
      <div class="oui-scale-labels"><span>Low</span><span>•••••</span><span>High</span></div>
    </div>

    <!-- Voice Detect Row (One UI Switch with Divider) -->
    <div class="oui-row" style="margin-top: 14px; padding-bottom: 2px;">
      <div class="oui-row-text">
        <span class="oui-row-title">Voice detect</span>
        <span class="oui-row-sub">Switch to Ambient sound and lower media volume when you start speaking</span>
      </div>
      <div class="oui-row-right">
        <span class="oui-v-divider"></span>
        <label class="oui-switch">
          <input type="checkbox" id="conv-det" onchange="api('set_conversation_detect', {enabled: this.checked})">
          <span class="oui-switch-track"></span>
        </label>
      </div>
    </div>
  </div>

  <!-- ========================================================================
       One UI Primary Block 2: Sound Quality and Effects
       ======================================================================== -->
  <div class="oui-section-label">Sound quality and effects</div>
  <div class="oui-block">
    <!-- Equalizer Presets + Expandable 9-Band Custom EQ -->
    <div class="oui-row first" style="flex-direction: column; align-items: stretch; gap: 10px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="oui-row-text">
          <span class="oui-row-title">Equalizer</span>
          <span class="oui-row-value" id="eq-name-label">Balanced</span>
        </div>
        <button class="oui-pill-btn" onclick="toggleEqDrawer()" id="btn-eq-drawer">9-Band EQ ▾</button>
      </div>

      <div class="oui-eq-pills">
        <button class="oui-eq-chip" id="eq-btn-0" onclick="api('set_equalizer_preset', {mode: 0})">Balanced</button>
        <button class="oui-eq-chip" id="eq-btn-1" onclick="api('set_equalizer_preset', {mode: 1})">Bass boost</button>
        <button class="oui-eq-chip" id="eq-btn-2" onclick="api('set_equalizer_preset', {mode: 2})">Soft</button>
        <button class="oui-eq-chip" id="eq-btn-3" onclick="api('set_equalizer_preset', {mode: 3})">Dynamic</button>
        <button class="oui-eq-chip" id="eq-btn-4" onclick="api('set_equalizer_preset', {mode: 4})">Clear</button>
        <button class="oui-eq-chip" id="eq-btn-5" onclick="api('set_equalizer_preset', {mode: 5})">Treble boost</button>
        <button class="oui-eq-chip" id="eq-btn-7" onclick="openAndSendCustomEq()">Custom</button>
      </div>

      <!-- Expandable 9-Band Custom Equalizer Studio -->
      <div id="eq-drawer" class="oui-eq-drawer" style="display: none;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 12.5px; font-weight: 600; color: var(--oui-text-secondary);">Custom 9-Band Equalizer (-10 dB to +10 dB)</span>
          <button class="oui-pill-btn" onclick="resetCustomEq()" style="padding: 5px 12px; font-size: 12px;">Reset flat</button>
        </div>
        <div class="oui-eq-bands" id="eq-sliders"></div>
        <div class="oui-row" style="padding-bottom: 4px; margin-top: 6px;">
          <div class="oui-row-text">
            <span class="oui-row-title" style="font-size: 14px;">Left / Right sound balance</span>
            <span class="oui-row-value" id="stereo-bal-val">Center</span>
          </div>
          <input type="range" class="oui-range" style="width: 170px;" min="0" max="32" id="stereo-bal" onchange="api('set_stereo_balance', {value: +this.value})">
        </div>
      </div>
    </div>

    <!-- 360 Audio -->
    <div class="oui-row">
      <div class="oui-row-text">
        <span class="oui-row-title">360 audio</span>
        <span class="oui-row-sub">Hear vivid, immersive sound coming from all directions</span>
      </div>
      <div class="oui-row-right">
        <label class="oui-check-chip" title="Head tracking">
          <input type="checkbox" id="spatial-ht" onchange="sendSpatial()"> Head tracking
        </label>
        <span class="oui-v-divider"></span>
        <label class="oui-switch">
          <input type="checkbox" id="spatial-on" onchange="sendSpatial()">
          <span class="oui-switch-track"></span>
        </label>
      </div>
    </div>

    <!-- Labs: Gaming Mode -->
    <div class="oui-row">
      <div class="oui-row-text">
        <span class="oui-row-title">Gaming mode</span>
        <span class="oui-row-sub">Minimize audio delay for synchronized gaming sound</span>
      </div>
      <div class="oui-row-right">
        <label class="oui-switch">
          <input type="checkbox" id="game-mode" onchange="api('set_gaming_mode', {enabled: this.checked})">
          <span class="oui-switch-track"></span>
        </label>
      </div>
    </div>
  </div>

  <!-- ========================================================================
       One UI Expandable Category Blocks (Progressive Disclosure)
       ======================================================================== -->
  <div class="oui-section-label">Earbud settings</div>

  <!-- Category A: Smart Environment & Custom Ambient -->
  <details class="oui-expander">
    <summary>
      <div class="oui-exp-lead">
        <div class="oui-cat-icon teal">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M2 10v3m4-7v11m4-14v18m4-13v7m4-10v13m4-8v3"/></svg>
        </div>
        <div class="oui-exp-titles">
          <span class="oui-exp-title">Hearing enhancements & ambient</span>
          <span class="oui-exp-sub" id="sum-env">Adaptive volume • Siren detect • Custom ambient</span>
        </div>
      </div>
      <span class="oui-chev">▾</span>
    </summary>
    <div class="oui-exp-body">
      <div class="oui-row first">
        <div class="oui-row-text">
          <span class="oui-row-title">Voice detect duration</span>
          <span class="oui-row-sub">Keep Ambient sound on after you stop speaking</span>
        </div>
        <select class="oui-select" id="conv-dur" onchange="api('set_conversation_detect_duration', {duration: +this.value})">
          <option value="0">5 seconds</option>
          <option value="1">10 seconds</option>
          <option value="2">15 seconds</option>
        </select>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Adapt sound to surroundings</span>
          <span class="oui-row-sub">Automatically adjust volume based on noise around you</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="adapt-vol" onchange="api('set_adaptive_volume', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Siren detect</span>
          <span class="oui-row-sub">Switch to Ambient sound when emergency sirens are detected</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="siren-det" onchange="api('set_siren_detect', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Noise controls with one earbud</span>
          <span class="oui-row-sub">Use ANC or Ambient sound even while wearing only one earbud</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="nc-one" onchange="api('set_noise_controls_one_earbud', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Amplify ambient sound</span>
          <span class="oui-row-sub">Customize per-ear ambient volume and tone</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="amb-cust-on" onchange="sendCustomAmbient()"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Left / Right ambient volume</span>
          <span class="oui-row-sub">Independent per-ear amplification</span>
        </div>
        <div style="display: flex; gap: 10px; width: 200px;">
          <input type="range" class="oui-range" min="0" max="4" id="amb-cust-l" onchange="sendCustomAmbient()" title="Left Ear">
          <input type="range" class="oui-range" min="0" max="4" id="amb-cust-r" onchange="sendCustomAmbient()" title="Right Ear">
        </div>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Ambient sound tone</span>
          <span class="oui-row-sub">Soft to Clear</span>
        </div>
        <input type="range" class="oui-range" style="width: 180px;" min="0" max="4" id="amb-cust-tone" onchange="sendCustomAmbient()">
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Extra high ambient volume</span>
          <span class="oui-row-sub">Boost ambient pass-through above standard maximum</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="amb-extra" onchange="api('set_extra_high_ambient', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>
    </div>
  </details>

  <!-- Category B: Earbud Controls (Pinch & Swipe Gestures) -->
  <details class="oui-expander">
    <summary>
      <div class="oui-exp-lead">
        <div class="oui-cat-icon purple">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 11V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2v0M14 10V4a2 2 0 0 0-2-2 2 2 0 0 0-2 2v6M10 10.5V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/></svg>
        </div>
        <div class="oui-exp-titles">
          <span class="oui-exp-title">Earbud controls</span>
          <span class="oui-exp-sub" id="sum-touch">Pinch & hold: Switch noise controls</span>
        </div>
      </div>
      <span class="oui-chev">▾</span>
    </summary>
    <div class="oui-exp-body">
      <div class="oui-row first">
        <div class="oui-row-text">
          <span class="oui-row-title">Block touches (Lock all)</span>
          <span class="oui-row-sub">Prevent unintended pinch and swipe actions</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="tc-lock-all" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Single pinch</span>
          <span class="oui-row-value">Play or pause track</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="tc-single" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Double pinch</span>
          <span class="oui-row-value">Play next track</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="tc-double" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Triple pinch</span>
          <span class="oui-row-value">Play previous track</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="tc-triple" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Pinch and hold</span>
          <span class="oui-row-sub">Enable custom left and right hold actions</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="tc-hold" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Answer / end calls & decline calls</span>
          <span class="oui-row-sub">Double pinch to answer/end • Pinch & hold to decline</span>
        </div>
        <div style="display: flex; gap: 10px;">
          <label class="oui-switch"><input type="checkbox" id="tc-call-dbl" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
          <label class="oui-switch"><input type="checkbox" id="tc-call-hold" onchange="sendTouchLocks()"><span class="oui-switch-track"></span></label>
        </div>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Left / Right pinch and hold action</span>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <select class="oui-select" id="tc-opt-l" onchange="sendTouchOptions()">
            <option value="2">Left: Switch noise controls</option>
            <option value="1">Left: Bixby / Voice assistant</option>
            <option value="3">Left: Volume down</option>
            <option value="4">Left: Spotify Spot On</option>
          </select>
          <select class="oui-select" id="tc-opt-r" onchange="sendTouchOptions()">
            <option value="2">Right: Switch noise controls</option>
            <option value="1">Right: Bixby / Voice assistant</option>
            <option value="3">Right: Volume up</option>
            <option value="4">Right: Spotify Spot On</option>
          </select>
        </div>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Left noise control cycle</span>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          <label class="oui-check-chip"><input type="checkbox" id="cyc-l-anc" onchange="sendNcCycle()"> ANC</label>
          <label class="oui-check-chip"><input type="checkbox" id="cyc-l-amb" onchange="sendNcCycle()"> Ambient</label>
          <label class="oui-check-chip"><input type="checkbox" id="cyc-l-adp" onchange="sendNcCycle()"> Adaptive</label>
          <label class="oui-check-chip"><input type="checkbox" id="cyc-l-off" onchange="sendNcCycle()"> Off</label>
        </div>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Right noise control cycle</span>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          <label class="oui-check-chip"><input type="checkbox" id="cyc-r-anc" onchange="sendNcCycle()"> ANC</label>
          <label class="oui-check-chip"><input type="checkbox" id="cyc-r-amb" onchange="sendNcCycle()"> Ambient</label>
          <label class="oui-check-chip"><input type="checkbox" id="cyc-r-adp" onchange="sendNcCycle()"> Adaptive</label>
          <label class="oui-check-chip"><input type="checkbox" id="cyc-r-off" onchange="sendNcCycle()"> Off</label>
        </div>
      </div>
    </div>
  </details>

  <!-- Category C: Blade Lights & Voice Controls -->
  <details class="oui-expander">
    <summary>
      <div class="oui-exp-lead">
        <div class="oui-cat-icon amber">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83"/></svg>
        </div>
        <div class="oui-exp-titles">
          <span class="oui-exp-title">Blade lights & voice controls</span>
          <span class="oui-exp-sub" id="sum-lights">Blade lights: Blink • Voice controls</span>
        </div>
      </div>
      <span class="oui-chev">▾</span>
    </summary>
    <div class="oui-exp-body">
      <div class="oui-row first">
        <div class="oui-row-text">
          <span class="oui-row-title">Blade lighting style</span>
          <span class="oui-row-sub">Lighting effect when earbuds are out of the case</span>
        </div>
        <select class="oui-select" id="light-mode" onchange="api('set_lighting_mode', {mode: +this.value})">
          <option value="0">Blink</option>
          <option value="1">Fade in and out</option>
          <option value="2">Steady</option>
        </select>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Voice controls</span>
          <span class="oui-row-sub">Say "Next song", "Volume up", or "Answer call" without a wake word</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="hotcmd-on" onchange="api('set_hot_command', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Bixby voice wake-up</span>
          <span class="oui-row-sub">Say "Hi, Bixby" while wearing your earbuds</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="bixby-on" onchange="api('set_bixby_wakeup', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Speak seamlessly</span>
          <span class="oui-row-sub">Say the command right away without waiting for sound feedback</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="speak-seam" onchange="api('set_speak_seamlessly', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>
    </div>
  </details>

  <!-- Category D: Calls, Seamless Connection & Find My Earbuds -->
  <details class="oui-expander">
    <summary>
      <div class="oui-exp-lead">
        <div class="oui-cat-icon green">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
        </div>
        <div class="oui-exp-titles">
          <span class="oui-exp-title">Call features, connection & Find My Earbuds</span>
          <span class="oui-exp-sub" id="sum-calls">Sidetone • Seamless connection • Earbud fit test</span>
        </div>
      </div>
      <span class="oui-chev">▾</span>
    </summary>
    <div class="oui-exp-body">
      <div class="oui-row first">
        <div class="oui-row-text">
          <span class="oui-row-title">Use Ambient sound during calls</span>
          <span class="oui-row-sub">Hear your own voice clearly while on phone calls (Sidetone)</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="sidetone" onchange="api('set_sidetone', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Extra clear call sound</span>
          <span class="oui-row-sub">Boost voice clarity on calls in noisy environments</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="clear-call" onchange="api('set_extra_clear_call', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Seamless earbud connection</span>
          <span class="oui-row-sub">Quickly switch your earbuds to other nearby devices</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="seamless-conn" onchange="api('set_seamless_connection', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">In-ear detection (Auto pause)</span>
          <span class="oui-row-sub">Pause media playback when earbuds are removed</span>
        </div>
        <label class="oui-switch"><input type="checkbox" id="auto-pause" onchange="api('set_auto_pause_resume', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Play calls on earbuds & neck stretch reminders</span>
          <span class="oui-row-sub">Call path control and posture alert after 10 min slouching</span>
        </div>
        <div style="display: flex; gap: 10px;">
          <label class="oui-switch" title="Call Path Control"><input type="checkbox" id="call-path" onchange="api('set_call_path_control', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
          <label class="oui-switch" title="Neck Stretch Reminders"><input type="checkbox" id="neck-posture" onchange="api('set_neck_posture_reminder', {enabled: this.checked})"><span class="oui-switch-track"></span></label>
        </div>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Find My Earbuds</span>
          <span class="oui-row-sub">Make your earbuds beep so you can locate them</span>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          <button class="oui-pill-btn primary" onclick="api('find_my_buds', {active: true, wearing: true})">Ring</button>
          <button class="oui-pill-btn" onclick="api('find_my_buds', {active: false})">Stop</button>
          <button class="oui-pill-btn" onclick="api('mute_buds', {left: true, right: false})">Mute L</button>
          <button class="oui-pill-btn" onclick="api('mute_buds', {left: false, right: true})">Mute R</button>
        </div>
      </div>

      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Earbud fit test & diagnostics</span>
          <span class="oui-row-value" id="diag-status">Fit: Not run • Self-test: Not run</span>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          <button class="oui-pill-btn" onclick="api('fit_test', {start: true})">Fit test</button>
          <button class="oui-pill-btn" onclick="api('self_test')">Self-test</button>
          <button class="oui-pill-btn" onclick="api('sync_time')">Sync time</button>
          <button class="oui-pill-btn" onclick="api('pairing_mode')">Pairing</button>
        </div>
      </div>
    </div>
  </details>

  <!-- Category E: About Earbuds, Battery Telemetry & Developer SPP Console -->
  <div class="oui-section-label">About earbuds & developer tools</div>
  <details class="oui-expander">
    <summary>
      <div class="oui-exp-lead">
        <div class="oui-cat-icon slate">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        </div>
        <div class="oui-exp-titles">
          <span class="oui-exp-title">Software information & SPP packet console</span>
          <span class="oui-exp-sub" id="sum-hw">FW: -- • Temps & cell voltage • Raw SPP inspector</span>
        </div>
      </div>
      <span class="oui-chev">▾</span>
    </summary>
    <div class="oui-exp-body">
      <div class="oui-row first">
        <div class="oui-row-text">
          <span class="oui-row-title">Software & hardware version</span>
          <span class="oui-row-value" id="hw-fw-info" style="font-family: monospace;">--</span>
        </div>
      </div>
      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Thermistors, cell voltage & charge cycles</span>
          <span class="oui-row-value" id="thermal-info" style="font-family: monospace;">--</span>
        </div>
      </div>
      <div class="oui-row">
        <div class="oui-row-text">
          <span class="oui-row-title">Model SKU & serial numbers</span>
          <span class="oui-row-sub" id="serial-info" style="font-family: monospace;">--</span>
        </div>
      </div>

      <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">
        <input type="text" class="oui-input" id="raw-id" placeholder="MsgId (e.g. 0x78)" style="width: 155px;">
        <input type="text" class="oui-input" id="raw-hex" placeholder="Payload Hex (e.g. 01)" style="flex: 1;">
        <button class="oui-pill-btn primary" onclick="sendRawCmd()">Send SPP</button>
      </div>
      <div class="oui-log-box" id="pkt-log"></div>
    </div>
  </details>
</div>

<script>
const FREQS = ["63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"];
const LIGHT_LABELS = {0: "Blink", 1: "Fade in and out", 2: "Steady"};
let currentBands = [0,0,0,0,0,0,0,0,0];

// One UI Collapsing Header Scroll Listener
window.addEventListener("scroll", () => {
  const bar = document.getElementById("oui-appbar");
  if (window.scrollY > 75) {
    bar.classList.add("scrolled");
  } else {
    bar.classList.remove("scrolled");
  }
});

function toggleTheme() {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
  root.setAttribute("data-theme", next);
}

function initEqSliders() {
  const wrap = document.getElementById("eq-sliders");
  wrap.innerHTML = "";
  FREQS.forEach((f, idx) => {
    const col = document.createElement("div");
    col.className = "oui-eq-col";
    col.innerHTML = `
      <span class="oui-eq-gain" id="eq-gain-${idx}">0dB</span>
      <input type="range" min="-10" max="10" value="0" id="eq-band-${idx}" oninput="updateBandLabel(${idx}, this.value)" onchange="sendCustomEq()">
      <span class="oui-eq-freq">${f}</span>
    `;
    wrap.appendChild(col);
  });
}

function toggleEqDrawer(forceOpen = false) {
  const d = document.getElementById("eq-drawer");
  const isHidden = d.style.display === "none";
  const show = forceOpen ? true : isHidden;
  d.style.display = show ? "block" : "none";
  document.getElementById("btn-eq-drawer").textContent = show ? "Hide 9-Band EQ ▴" : "9-Band EQ ▾";
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
  document.getElementById("appbar-title").textContent = s.device_name;

  const dot = document.getElementById("conn-dot");
  dot.className = s.connected ? "oui-status-dot connected" : "oui-status-dot";
  document.getElementById("conn-text").textContent = s.connected
    ? `Connected • ${s.noise_control_mode_name}`
    : `Disconnected (${s.device_mac})`;
  document.getElementById("btn-connect").textContent = s.connected ? "Reconnect" : "Connect";
  document.getElementById("btn-connect").className = s.connected ? "oui-pill-btn" : "oui-pill-btn primary";

  // Left Earbud Battery Pill
  document.getElementById("bat-l").textContent = `${s.battery_left}%`;
  const barL = document.getElementById("bar-l");
  barL.style.width = `${Math.min(100, Math.max(0, s.battery_left))}%`;
  barL.className = s.battery_left <= 15 ? "oui-bat-bar-fill low" : "oui-bat-bar-fill";
  const plL = document.getElementById("place-l");
  plL.textContent = s.placement_left_name + (s.charging_left ? " ⚡" : "");
  plL.className = s.placement_left === 1 ? "oui-bat-state in-ear" : "oui-bat-state";
  document.getElementById("badge-l").className = s.placement_left === 1 ? "oui-lr-circle active" : "oui-lr-circle";

  // Right Earbud Battery Pill
  document.getElementById("bat-r").textContent = `${s.battery_right}%`;
  const barR = document.getElementById("bar-r");
  barR.style.width = `${Math.min(100, Math.max(0, s.battery_right))}%`;
  barR.className = s.battery_right <= 15 ? "oui-bat-bar-fill low" : "oui-bat-bar-fill";
  const plR = document.getElementById("place-r");
  plR.textContent = s.placement_right_name + (s.charging_right ? " ⚡" : "");
  plR.className = s.placement_right === 1 ? "oui-bat-state in-ear" : "oui-bat-state";
  document.getElementById("badge-r").className = s.placement_right === 1 ? "oui-lr-circle active" : "oui-lr-circle";

  // Charging Case Battery Pill
  const hasCase = s.battery_case > 0 && s.battery_case <= 100;
  document.getElementById("bat-c").textContent = hasCase ? `${s.battery_case}%` : "Closed";
  const barC = document.getElementById("bar-c");
  barC.style.width = hasCase ? `${s.battery_case}%` : "0%";
  barC.className = (hasCase && s.battery_case <= 15) ? "oui-bat-bar-fill low" : "oui-bat-bar-fill";
  const plC = document.getElementById("place-c");
  plC.textContent = hasCase ? (s.charging_case ? "Charging ⚡" : "Case open") : "Standby";
  plC.className = hasCase ? "oui-bat-state in-ear" : "oui-bat-state";
  document.getElementById("badge-c").className = hasCase ? "oui-lr-circle active" : "oui-lr-circle";

  // Noise Control 4-Way Track + Contextual Sliders
  document.getElementById("nc-current-label").textContent = s.noise_control_mode_name;
  [0,1,2,3].forEach(m => {
    document.getElementById(`nc-btn-${m}`).className = s.noise_control_mode === m ? "oui-nc-option active" : "oui-nc-option";
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
    if (el) el.className = s.equalizer_mode === m ? "oui-eq-chip active" : "oui-eq-chip";
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

  // Expandable Section Blue Value Subtitles & Inputs
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
    `Adapt sound: ${s.adaptive_volume ? 'On' : 'Off'} • Siren: ${s.siren_detect ? 'On' : 'Off'} • Amplify ambient: ${s.ambient_custom_enabled ? 'On' : 'Off'}`;

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
  document.getElementById("sum-touch").textContent = s.touchpad_lock_all
    ? "Block touches: On"
    : "Touches unlocked • Pinch & hold active";

  document.getElementById("light-mode").value = s.lighting_control;
  document.getElementById("bixby-on").checked = s.bixby_wakeup;
  document.getElementById("hotcmd-on").checked = s.hot_command_enabled;
  document.getElementById("speak-seam").checked = s.speak_seamlessly;
  document.getElementById("sum-lights").textContent =
    `Blade lights: ${LIGHT_LABELS[s.lighting_control] || 'Blink'} • Voice controls: ${s.hot_command_enabled ? 'On' : 'Off'}`;

  document.getElementById("sidetone").checked = s.sidetone_enabled;
  document.getElementById("clear-call").checked = s.extra_clear_call;
  document.getElementById("seamless-conn").checked = s.seamless_connection;
  document.getElementById("auto-pause").checked = s.auto_pause_resume;
  document.getElementById("call-path").checked = s.call_path_control;
  document.getElementById("neck-posture").checked = s.neck_stretch_calibration;
  document.getElementById("sum-calls").textContent =
    `Sidetone: ${s.sidetone_enabled ? 'On' : 'Off'} • Clear call: ${s.extra_clear_call ? 'On' : 'Off'} • Seamless: ${s.seamless_connection ? 'On' : 'Off'}`;
  document.getElementById("diag-status").textContent =
    `Fit: L=${s.fit_test_left}, R=${s.fit_test_right} • Self-test: ${s.self_test_passed === null ? "Not run" : (s.self_test_passed ? "Passed" : "Failed")}`;

  document.getElementById("sum-hw").textContent =
    `FW: ${s.fw_version_left || 'R640XXU0AZD2'} • ${s.temp_left_c}°C / ${s.temp_right_c}°C • ${s.vcell_mv} mV`;
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
