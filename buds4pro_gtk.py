#!/usr/bin/env python3
"""
Samsung Galaxy Buds4 Pro Studio — Native GTK4 + Libadwaita Desktop Application.

Designed with progressive disclosure:
  - Most-used controls (Battery Hero Cards, 4-Way Noise Control Mode, Contextual
    ANC/Ambient Slider, Voice Detect, Equalizer Preset, and 360 Spatial Audio)
    are front-and-center.
  - Detailed/advanced settings (9-Band Custom EQ, Custom Ambient, Pinch & Touch
    Gestures, Blade Lights, Call & Connection, Diagnostics, and Hardware/SPP
    Protocol Inspector) are tucked into expandable rows (Adw.ExpanderRow) that
    open only when clicked.
"""

from __future__ import annotations

import sys
import webbrowser
from typing import Dict, List, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from buds4pro_protocol import Buds4ProController, Buds4ProState, EQ_PRESET_NAMES, SppPacket
from buds4pro_web import Buds4ProHttpServer

EQ_FREQS = ["63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"]
LIGHT_NAMES = {0: "Blink", 1: "Fade In/Out", 2: "Steady"}

CUSTOM_CSS = """
.hero-card {
    background: alpha(@card_bg_color, 0.95);
    border: 1px solid alpha(@borders, 0.7);
    border-radius: 16px;
    padding: 16px 18px;
}
.earbud-tag {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    opacity: 0.65;
}
.battery-huge {
    font-size: 30px;
    font-weight: 800;
    margin-top: 2px;
    margin-bottom: 2px;
}
.status-pill {
    background: alpha(@accent_bg_color, 0.16);
    color: @accent_color;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 600;
}
.status-pill-muted {
    background: alpha(@window_fg_color, 0.08);
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 600;
    opacity: 0.75;
}
.mode-pill-box {
    background: alpha(@window_fg_color, 0.06);
    border-radius: 14px;
    padding: 5px;
}
.mode-pill-btn {
    border-radius: 10px;
    padding: 10px 14px;
    font-weight: 700;
    border: none;
    background: transparent;
}
.mode-pill-btn:checked {
    background: @accent_bg_color;
    color: @accent_fg_color;
    box-shadow: 0 2px 10px alpha(@accent_bg_color, 0.4);
}
.preset-chip {
    border-radius: 999px;
    padding: 5px 12px;
    font-size: 12.5px;
    font-weight: 600;
}
.preset-chip:checked {
    background: @accent_bg_color;
    color: @accent_fg_color;
}
.sniffer-view {
    font-family: monospace;
    font-size: 12px;
    padding: 10px;
    border-radius: 10px;
}
"""


class Buds4ProWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, controller: Buds4ProController):
        super().__init__(application=app, title="Samsung Buds4 Pro")
        self.set_default_size(680, 820)
        self.controller = controller
        self._syncing = False

        self._load_css()

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Clean HeaderBar
        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(
            title="Samsung Galaxy Buds4 Pro",
            subtitle="Connecting...",
        )
        header.set_title_widget(self.title_widget)

        self.conn_btn = Gtk.Button(label="Connect", tooltip_text="Connect to Galaxy Buds4 Pro")
        self.conn_btn.add_css_class("suggested-action")
        self.conn_btn.connect("clicked", lambda _: self.controller.connect())
        header.pack_start(self.conn_btn)

        self.disconn_btn = Gtk.Button(label="Disconnect", tooltip_text="Disconnect Galaxy Buds4 Pro from Laptop")
        self.disconn_btn.add_css_class("destructive-action")
        self.disconn_btn.connect("clicked", lambda _: self.controller.disconnect(bluetooth=True))
        header.pack_start(self.disconn_btn)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh Status")
        refresh_btn.connect("clicked", lambda _: self.controller.request_telemetry_refresh())
        header.pack_start(refresh_btn)

        web_btn = Gtk.Button(icon_name="applications-internet-symbolic", tooltip_text="Open Web Studio (http://127.0.0.1:8765)")
        web_btn.connect("clicked", lambda _: webbrowser.open("http://127.0.0.1:8765"))
        header.pack_end(web_btn)

        toolbar_view.add_top_bar(header)

        # Single-page clean scrollable view with progressive disclosure
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        clamp = Adw.Clamp(maximum_size=640, tightening_threshold=560)
        clamp.set_margin_top(14)
        clamp.set_margin_bottom(28)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(root_box)
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)

        # 1. Hero Battery & Wearing Status Cards
        root_box.append(self._build_hero_cards())

        # 2. Primary Noise Control Card (Always Visible)
        root_box.append(self._build_primary_noise_section())

        # 3. Essential Sound & Equalizer Section (Presets visible; 9-band sliders expand on click)
        root_box.append(self._build_sound_section())

        # 4. Expandable Secondary Settings (Hidden until clicked)
        root_box.append(self._build_expandable_settings_section())

        self.controller.add_listener(self._on_controller_update)
        self._render_state(self.controller.state, None)

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CUSTOM_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # =========================================================================
    # 1. Hero Battery & Placement Cards
    # =========================================================================
    def _build_hero_cards(self) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)

        # Left Earbud Card
        card_l, self.lbl_bat_l, self.lbl_place_l, self.bar_bat_l = self._create_bat_card("LEFT EARBUD")
        grid.attach(card_l, 0, 0, 1, 1)

        # Right Earbud Card
        card_r, self.lbl_bat_r, self.lbl_place_r, self.bar_bat_r = self._create_bat_card("RIGHT EARBUD")
        grid.attach(card_r, 1, 0, 1, 1)

        # Charging Case Card
        card_c, self.lbl_bat_c, self.lbl_place_c, self.bar_bat_c = self._create_bat_card("CHARGING CASE")
        grid.attach(card_c, 2, 0, 1, 1)

        return grid

    def _create_bat_card(self, title: str):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("hero-card")

        tag = Gtk.Label(label=title, xalign=0)
        tag.add_css_class("earbud-tag")

        val = Gtk.Label(label="--%", xalign=0)
        val.add_css_class("battery-huge")

        bar = Gtk.LevelBar()
        bar.set_min_value(0)
        bar.set_max_value(100)
        bar.set_value(0)
        bar.set_size_request(-1, 6)

        pill = Gtk.Label(label="Disconnected", xalign=0.5)
        pill.add_css_class("status-pill-muted")
        pill.set_halign(Gtk.Align.START)
        pill.set_margin_top(4)

        card.append(tag)
        card.append(val)
        card.append(bar)
        card.append(pill)
        return card, val, pill, bar

    # =========================================================================
    # 2. Primary Noise Control Section (Most Used — Front & Center)
    # =========================================================================
    def _build_primary_noise_section(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title="Noise Controls")

        # 4-Way Mode Selector Row
        mode_row = Adw.PreferencesRow()
        mode_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        mode_outer.set_margin_top(12)
        mode_outer.set_margin_bottom(12)
        mode_outer.set_margin_start(12)
        mode_outer.set_margin_end(12)

        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True)
        pill_box.add_css_class("mode-pill-box")

        self.nc_mode_buttons: Dict[int, Gtk.ToggleButton] = {}
        for mode_id, label in [
            (0, "Off"),
            (1, "ANC"),
            (2, "Ambient"),
            (3, "Adaptive"),
        ]:
            btn = Gtk.ToggleButton(label=label)
            btn.add_css_class("mode-pill-btn")
            btn.connect("toggled", self._on_nc_mode_toggled, mode_id)
            pill_box.append(btn)
            self.nc_mode_buttons[mode_id] = btn

        mode_outer.append(pill_box)
        mode_row.set_child(mode_outer)
        group.add(mode_row)

        # Contextual ANC Level Row (Visible when ANC is active)
        self.row_anc_level = Adw.ActionRow(
            title="ANC Strength",
            subtitle="Level 5 (Maximum noise reduction)",
        )
        self.anc_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 5, 1)
        self.anc_scale.set_draw_value(True)
        self.anc_scale.set_digits(0)
        self.anc_scale.set_size_request(190, -1)
        self.anc_scale.connect("value-changed", self._on_anc_scale_changed)
        self.row_anc_level.add_suffix(self.anc_scale)
        group.add(self.row_anc_level)

        # Contextual Ambient Volume Row (Visible when Ambient is active)
        self.row_amb_vol = Adw.ActionRow(
            title="Ambient Sound Level",
            subtitle="Level 5",
        )
        self.amb_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 5, 1)
        self.amb_scale.set_draw_value(True)
        self.amb_scale.set_digits(0)
        self.amb_scale.set_size_request(190, -1)
        self.amb_scale.connect("value-changed", self._on_amb_scale_changed)
        self.row_amb_vol.add_suffix(self.amb_scale)
        group.add(self.row_amb_vol)

        # Voice Detect ExpanderRow (Switch always visible; timeout & environment detection expand on click)
        self.exp_voice_detect = Adw.ExpanderRow(
            title="Voice Detect + Smart Environment",
            subtitle="Lower volume and switch to Ambient when you speak",
        )
        self.sw_conv_det = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.sw_conv_det.connect(
            "notify::active",
            lambda w, _: None if self._syncing else self.controller.set_conversation_detect(w.get_active()),
        )
        self.exp_voice_detect.add_suffix(self.sw_conv_det)

        dur_row = Adw.ActionRow(
            title="Conversation Timeout",
            subtitle="Resume noise canceling after you stop speaking",
        )
        self.dd_conv_dur = Gtk.DropDown.new_from_strings(["5 seconds", "10 seconds", "15 seconds"])
        self.dd_conv_dur.set_valign(Gtk.Align.CENTER)
        self.dd_conv_dur.connect("notify::selected", self._on_conv_dur_changed)
        dur_row.add_suffix(self.dd_conv_dur)
        self.exp_voice_detect.add_row(dur_row)

        self.sw_adapt_vol = self._add_expander_switch(
            self.exp_voice_detect,
            "Adaptive Volume",
            "Automatically adjust playback volume to surrounding noise",
            lambda val: self.controller.set_adaptive_volume(val),
        )
        self.sw_siren = self._add_expander_switch(
            self.exp_voice_detect,
            "Siren Detect",
            "Switch to Ambient Sound when emergency sirens are detected",
            lambda val: self.controller.set_siren_detect(val),
        )
        self.sw_nc_one = self._add_expander_switch(
            self.exp_voice_detect,
            "Noise Controls with One Earbud",
            "Allow ANC and Ambient Sound when wearing a single earbud",
            lambda val: self.controller.set_noise_controls_one_earbud(val),
        )
        group.add(self.exp_voice_detect)

        # Customize Ambient Sound ExpanderRow (Hidden until clicked)
        self.exp_cust_amb = Adw.ExpanderRow(
            title="Customize Ambient Sound",
            subtitle="Per-ear ambient amplification, tone, and extra-high boost",
        )
        self.sw_amb_cust = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.sw_amb_cust.connect("notify::active", lambda *_: self._push_custom_ambient())
        self.exp_cust_amb.add_suffix(self.sw_amb_cust)

        self.scale_amb_l = self._add_expander_scale(
            self.exp_cust_amb, "Left Ear Ambient Level", 0, 4, 1, lambda _: self._push_custom_ambient()
        )
        self.scale_amb_r = self._add_expander_scale(
            self.exp_cust_amb, "Right Ear Ambient Level", 0, 4, 1, lambda _: self._push_custom_ambient()
        )
        self.scale_amb_tone = self._add_expander_scale(
            self.exp_cust_amb, "Ambient Tone (Soft to Clear)", 0, 4, 1, lambda _: self._push_custom_ambient()
        )
        self.sw_amb_extra = self._add_expander_switch(
            self.exp_cust_amb,
            "Extra High Ambient Volume",
            "Boost ambient pass-through above standard maximum",
            lambda val: self.controller.set_extra_high_ambient(val),
        )
        group.add(self.exp_cust_amb)

        return group

    # =========================================================================
    # 3. Sound & Equalizer Section (Presets visible; 9-band EQ expands on click)
    # =========================================================================
    def _build_sound_section(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title="Sound + Equalizer")

        # Equalizer ExpanderRow: Preset chips visible in first child row, 9-band sliders inside expander
        self.exp_eq = Adw.ExpanderRow(
            title="Equalizer",
            subtitle="Balanced (Off) — Click to customize presets or 9-band EQ",
        )

        preset_row = Adw.PreferencesRow()
        preset_wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preset_wrap.set_margin_top(10)
        preset_wrap.set_margin_bottom(10)
        preset_wrap.set_margin_start(12)
        preset_wrap.set_margin_end(12)

        self.eq_buttons: Dict[int, Gtk.ToggleButton] = {}
        for mode_id, title in [
            (0, "Balanced"),
            (1, "Bass"),
            (2, "Soft"),
            (3, "Dynamic"),
            (4, "Clear"),
            (5, "Treble"),
            (7, "Custom"),
        ]:
            b = Gtk.ToggleButton(label=title)
            b.add_css_class("preset-chip")
            b.connect("toggled", self._on_eq_preset_toggled, mode_id)
            preset_wrap.append(b)
            self.eq_buttons[mode_id] = b

        preset_row.set_child(preset_wrap)
        group.add(preset_row)

        # 9-Band Custom EQ inside self.exp_eq (Hidden until clicked or when Custom is selected)
        reset_row = Adw.ActionRow(
            title="Reset 9-Band Custom Equalizer",
            subtitle="Flatten all frequency bands to 0 dB",
        )
        reset_btn = Gtk.Button(label="Reset 0 dB", valign=Gtk.Align.CENTER)
        reset_btn.connect("clicked", self._on_reset_eq_clicked)
        reset_row.add_suffix(reset_btn)
        self.exp_eq.add_row(reset_row)

        self.eq_band_scales: List[Gtk.Scale] = []
        for idx, freq in enumerate(EQ_FREQS):
            sc = self._add_expander_scale(
                self.exp_eq,
                f"{freq}",
                -10,
                10,
                1,
                lambda _: self._push_custom_eq(),
            )
            self.eq_band_scales.append(sc)
        group.add(self.exp_eq)

        # 360 Spatial Audio ExpanderRow (Toggle visible; Head Tracking, Gaming Mode, Balance inside)
        self.exp_spatial = Adw.ExpanderRow(
            title="360 Spatial Audio + Gaming Mode",
            subtitle="Immersive spatial sound, head tracking, and low-latency sync",
        )
        self.sw_spatial = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.sw_spatial.connect("notify::active", lambda *_: self._push_spatial())
        self.exp_spatial.add_suffix(self.sw_spatial)

        self.sw_head_track = self._add_expander_switch(
            self.exp_spatial,
            "360 Head Tracking",
            "Track head movement using earbud motion sensors",
            lambda _: self._push_spatial(),
        )
        self.sw_gaming = self._add_expander_switch(
            self.exp_spatial,
            "Gaming Mode (Low Latency)",
            "Minimize Bluetooth audio delay for gaming and video",
            lambda val: self.controller.set_gaming_mode(val),
        )
        self.scale_balance = self._add_expander_scale(
            self.exp_spatial,
            "Left / Right Balance (16 = Center)",
            0,
            32,
            1,
            lambda val: self.controller.set_stereo_balance(int(val)),
        )
        group.add(self.exp_spatial)

        return group

    # =========================================================================
    # 4. Expandable Secondary Settings (Pinch, Blade Lights, Calls, Diagnostics, SPP)
    # =========================================================================
    def _build_expandable_settings_section(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(title="Controls + Device Settings")

        # 4A. Pinch & Touch Controls ExpanderRow
        self.exp_touch = Adw.ExpanderRow(
            title="Pinch + Touch Controls",
            subtitle="Enabled — Click to customize gestures and Pinch + Hold actions",
        )
        self.sw_touch_enabled = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.sw_touch_enabled.connect("notify::active", lambda *_: self._push_touch_locks())
        self.exp_touch.add_suffix(self.sw_touch_enabled)

        self.sw_pinch_1 = self._add_expander_switch(
            self.exp_touch, "Single Pinch", "Play / Pause track", lambda _: self._push_touch_locks()
        )
        self.sw_pinch_2 = self._add_expander_switch(
            self.exp_touch, "Double Pinch", "Next track", lambda _: self._push_touch_locks()
        )
        self.sw_pinch_3 = self._add_expander_switch(
            self.exp_touch, "Triple Pinch", "Previous track", lambda _: self._push_touch_locks()
        )
        self.sw_pinch_hold = self._add_expander_switch(
            self.exp_touch, "Pinch + Hold", "Trigger assigned shortcut", lambda _: self._push_touch_locks()
        )
        self.sw_call_dbl = self._add_expander_switch(
            self.exp_touch, "Answer / End Calls (Double Pinch)", "Double pinch during calls", lambda _: self._push_touch_locks()
        )
        self.sw_call_hold = self._add_expander_switch(
            self.exp_touch, "Decline Calls (Pinch + Hold)", "Hold pinch on incoming call", lambda _: self._push_touch_locks()
        )

        self.touch_opt_codes = [2, 1, 3, 4]
        opt_labels = ["Switch Noise Controls", "Voice Assistant", "Volume Control", "Spotify Spot On"]

        row_opt_l = Adw.ActionRow(title="Left Pinch + Hold Action")
        self.dd_opt_l = Gtk.DropDown.new_from_strings(opt_labels)
        self.dd_opt_l.set_valign(Gtk.Align.CENTER)
        self.dd_opt_l.connect("notify::selected", lambda *_: self._push_touch_options())
        row_opt_l.add_suffix(self.dd_opt_l)
        self.exp_touch.add_row(row_opt_l)

        row_opt_r = Adw.ActionRow(title="Right Pinch + Hold Action")
        self.dd_opt_r = Gtk.DropDown.new_from_strings(opt_labels)
        self.dd_opt_r.set_valign(Gtk.Align.CENTER)
        self.dd_opt_r.connect("notify::selected", lambda *_: self._push_touch_options())
        row_opt_r.add_suffix(self.dd_opt_r)
        self.exp_touch.add_row(row_opt_r)

        row_cyc_l = Adw.ActionRow(title="Left Noise Cycle Modes")
        box_l = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        self.chk_l_anc = Gtk.CheckButton(label="ANC")
        self.chk_l_amb = Gtk.CheckButton(label="Amb")
        self.chk_l_adp = Gtk.CheckButton(label="Adp")
        self.chk_l_off = Gtk.CheckButton(label="Off")
        for chk in (self.chk_l_anc, self.chk_l_amb, self.chk_l_adp, self.chk_l_off):
            chk.connect("toggled", lambda *_: self._push_nc_cycle())
            box_l.append(chk)
        row_cyc_l.add_suffix(box_l)
        self.exp_touch.add_row(row_cyc_l)

        row_cyc_r = Adw.ActionRow(title="Right Noise Cycle Modes")
        box_r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        self.chk_r_anc = Gtk.CheckButton(label="ANC")
        self.chk_r_amb = Gtk.CheckButton(label="Amb")
        self.chk_r_adp = Gtk.CheckButton(label="Adp")
        self.chk_r_off = Gtk.CheckButton(label="Off")
        for chk in (self.chk_r_anc, self.chk_r_amb, self.chk_r_adp, self.chk_r_off):
            chk.connect("toggled", lambda *_: self._push_nc_cycle())
            box_r.append(chk)
        row_cyc_r.add_suffix(box_r)
        self.exp_touch.add_row(row_cyc_r)
        group.add(self.exp_touch)

        # 4B. Blade Lights & Voice Control ExpanderRow
        self.exp_lights = Adw.ExpanderRow(
            title="Blade Lights + Voice Assistant",
            subtitle="Lighting: Blink | Bixby + Voice Commands",
        )
        light_row = Adw.ActionRow(title="Blade Lighting Style", subtitle="LED pattern when earbuds are out of case")
        self.dd_lighting = Gtk.DropDown.new_from_strings(["Blink", "Fade In / Out", "Steady"])
        self.dd_lighting.set_valign(Gtk.Align.CENTER)
        self.dd_lighting.connect("notify::selected", self._on_lighting_changed)
        light_row.add_suffix(self.dd_lighting)
        self.exp_lights.add_row(light_row)

        self.sw_hotcmd = self._add_expander_switch(
            self.exp_lights,
            "Voice Controls (Hot Commands)",
            "Say 'Next song', 'Volume up', or 'Answer call' without wake word",
            lambda val: self.controller.set_hot_command(val),
        )
        self.sw_bixby = self._add_expander_switch(
            self.exp_lights,
            "Bixby Voice Wake-up",
            "Wake voice assistant hands-free",
            lambda val: self.controller.set_bixby_wakeup(val),
        )
        self.sw_speak_seam = self._add_expander_switch(
            self.exp_lights,
            "Speak Seamlessly",
            "Say commands immediately after waking Bixby",
            lambda val: self.controller.set_speak_seamlessly(val),
        )
        group.add(self.exp_lights)

        # 4C. Calls & Connection Settings ExpanderRow
        self.exp_calls = Adw.ExpanderRow(
            title="Call + Connection Settings",
            subtitle="Call clarity, Sidetone, Seamless Connection, and Auto-Pause",
        )
        self.sw_sidetone = self._add_expander_switch(
            self.exp_calls,
            "Use Ambient Sound During Calls (Sidetone)",
            "Hear your own voice clearly during phone calls",
            lambda val: self.controller.set_sidetone(val),
        )
        self.sw_clear_call = self._add_expander_switch(
            self.exp_calls,
            "Extra Clear Call Sound",
            "Enhance voice clarity on calls",
            lambda val: self.controller.set_extra_clear_call(val),
        )
        self.sw_seamless = self._add_expander_switch(
            self.exp_calls,
            "Seamless Earbud Connection",
            "Switch Bluetooth connection between devices without disconnecting",
            lambda val: self.controller.set_seamless_connection(val),
        )
        self.sw_auto_pause = self._add_expander_switch(
            self.exp_calls,
            "Auto Pause / Resume When Removed",
            "Pause media automatically when earbuds are removed",
            lambda val: self.controller.set_auto_pause_resume(val),
        )
        self.sw_call_path = self._add_expander_switch(
            self.exp_calls,
            "Automatic Call Path Control",
            "Route audio to earbuds automatically when worn",
            lambda val: self.controller.set_call_path_control(val),
        )
        self.sw_neck = self._add_expander_switch(
            self.exp_calls,
            "Neck Stretch Posture Reminders",
            "Notify when head posture is tilted downward for too long",
            lambda val: self.controller.set_neck_posture_reminder(val),
        )
        group.add(self.exp_calls)

        # 4D. Find My Earbuds, Fit Test & System Actions ExpanderRow
        self.exp_diag = Adw.ExpanderRow(
            title="Find My Earbuds + Fit Test",
            subtitle="Ring lost earbuds, check eartip seal, or run hardware self-test",
        )
        fmg_row = Adw.ActionRow(title="Find My Earbuds", subtitle="Play locator chime on Left / Right earbuds")
        fmg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        btn_ring = Gtk.Button(label="Ring")
        btn_ring.connect("clicked", lambda _: self.controller.set_find_my_buds(True, True))
        btn_stop = Gtk.Button(label="Stop")
        btn_stop.connect("clicked", lambda _: self.controller.set_find_my_buds(False))
        btn_mute_l = Gtk.Button(label="Mute L")
        btn_mute_l.connect("clicked", lambda _: self.controller.set_find_my_buds_mute(True, False))
        btn_mute_r = Gtk.Button(label="Mute R")
        btn_mute_r.connect("clicked", lambda _: self.controller.set_find_my_buds_mute(False, True))
        for b in (btn_ring, btn_stop, btn_mute_l, btn_mute_r):
            fmg_box.append(b)
        fmg_row.add_suffix(fmg_box)
        self.exp_diag.add_row(fmg_row)

        self.row_diag = Adw.ActionRow(title="Earbud Fit + Self-Test", subtitle="Fit: Not Run | Self-Test: Not Run")
        diag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        btn_fit = Gtk.Button(label="Fit Test")
        btn_fit.connect("clicked", lambda _: self.controller.run_fit_test(True))
        btn_selftest = Gtk.Button(label="Self-Test")
        btn_selftest.connect("clicked", lambda _: self.controller.run_self_test())
        diag_box.append(btn_fit)
        diag_box.append(btn_selftest)
        self.row_diag.add_suffix(diag_box)
        self.exp_diag.add_row(self.row_diag)

        sys_row = Adw.ActionRow(title="System Utilities", subtitle="Sync clock, enter Bluetooth pairing mode, or reboot")
        sys_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        btn_time = Gtk.Button(label="Sync Clock")
        btn_time.connect("clicked", lambda _: self.controller.sync_time())
        btn_pair = Gtk.Button(label="Pairing Mode")
        btn_pair.connect("clicked", lambda _: self.controller.start_pairing_mode())
        btn_reboot = Gtk.Button(label="Reboot")
        btn_reboot.add_css_class("destructive-action")
        btn_reboot.connect("clicked", lambda _: self.controller.reboot_buds())
        for b in (btn_time, btn_pair, btn_reboot):
            sys_box.append(b)
        sys_row.add_suffix(sys_box)
        self.exp_diag.add_row(sys_row)
        group.add(self.exp_diag)

        # 4E. Hardware Telemetry & Live SPP Protocol Inspector ExpanderRow
        self.exp_dev = Adw.ExpanderRow(
            title="Hardware Details + Developer SPP Console",
            subtitle="Firmware, serial numbers, thermistors, and raw Bluetooth frame sniffer",
        )
        self.row_thermal = Adw.ActionRow(title="Sensors + Battery Health", subtitle="--")
        self.row_hw_fw = Adw.ActionRow(title="Firmware + Hardware Versions", subtitle="--")
        self.row_sku_serial = Adw.ActionRow(title="SKU + Serial Numbers", subtitle="--")
        self.exp_dev.add_row(self.row_thermal)
        self.exp_dev.add_row(self.row_hw_fw)
        self.exp_dev.add_row(self.row_sku_serial)

        raw_row = Adw.PreferencesRow()
        raw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        raw_box.set_margin_top(10)
        raw_box.set_margin_bottom(10)
        raw_box.set_margin_start(12)
        raw_box.set_margin_end(12)

        cmd_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_msg_id = Gtk.Entry(placeholder_text="MsgId (e.g. 120 or 0x78)")
        self.entry_payload = Gtk.Entry(placeholder_text="Payload Hex (e.g. 01)", hexpand=True)
        send_btn = Gtk.Button(label="Send SPP Frame")
        send_btn.add_css_class("suggested-action")
        send_btn.connect("clicked", self._on_send_raw_clicked)
        cmd_bar.append(self.entry_msg_id)
        cmd_bar.append(self.entry_payload)
        cmd_bar.append(send_btn)
        raw_box.append(cmd_bar)

        sniffer_scroll = Gtk.ScrolledWindow(min_content_height=150, max_content_height=200)
        self.log_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.NONE)
        self.log_view.add_css_class("sniffer-view")
        sniffer_scroll.set_child(self.log_view)
        raw_box.append(sniffer_scroll)

        raw_row.set_child(raw_box)
        self.exp_dev.add_row(raw_row)
        group.add(self.exp_dev)

        return group

    # =========================================================================
    # UI Helper Builders & Callbacks
    # =========================================================================
    def _add_expander_switch(self, expander: Adw.ExpanderRow, title: str, subtitle: str, cb) -> Gtk.Switch:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        sw = Gtk.Switch(valign=Gtk.Align.CENTER)
        sw.connect("notify::active", lambda w, _: None if self._syncing else cb(w.get_active()))
        row.add_suffix(sw)
        row.set_activatable_widget(sw)
        expander.add_row(row)
        return sw

    def _add_expander_scale(self, expander: Adw.ExpanderRow, title: str, min_v: int, max_v: int, step: int, cb) -> Gtk.Scale:
        row = Adw.ActionRow(title=title)
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_v, max_v, step)
        sc.set_draw_value(True)
        sc.set_digits(0)
        sc.set_size_request(190, -1)
        sc.connect("value-changed", lambda w: None if self._syncing else cb(w.get_value()))
        row.add_suffix(sc)
        expander.add_row(row)
        return sc

    def _on_nc_mode_toggled(self, btn: Gtk.ToggleButton, mode_id: int):
        if self._syncing or not btn.get_active():
            return
        self._syncing = True
        for mid, other in self.nc_mode_buttons.items():
            if mid != mode_id:
                other.set_active(False)
        self._syncing = False
        self._update_contextual_noise_rows(mode_id)
        self.controller.set_noise_control(mode_id)

    def _update_contextual_noise_rows(self, mode_id: int):
        # Show ANC level slider only when ANC (1) is selected; show Ambient volume when Ambient (2) or Adaptive (3) is selected
        self.row_anc_level.set_visible(mode_id == 1)
        self.row_amb_vol.set_visible(mode_id in (2, 3))

    def _on_anc_scale_changed(self, scale: Gtk.Scale):
        lvl = int(scale.get_value()) - 1
        self.row_anc_level.set_subtitle(f"Level {lvl + 1} of 5")
        if not self._syncing:
            self.controller.set_anc_level(lvl)

    def _on_amb_scale_changed(self, scale: Gtk.Scale):
        vol = int(scale.get_value()) - 1
        self.row_amb_vol.set_subtitle(f"Level {vol + 1} of 5")
        if not self._syncing:
            self.controller.set_ambient_volume(vol)

    def _on_conv_dur_changed(self, dd: Gtk.DropDown, _):
        if not self._syncing:
            self.controller.set_conversation_detect_duration(int(dd.get_selected()))

    def _push_custom_ambient(self):
        if self._syncing:
            return
        self.controller.set_customize_ambient(
            self.sw_amb_cust.get_active(),
            int(self.scale_amb_l.get_value()),
            int(self.scale_amb_r.get_value()),
            int(self.scale_amb_tone.get_value()),
        )

    def _on_eq_preset_toggled(self, btn: Gtk.ToggleButton, mode_id: int):
        if self._syncing or not btn.get_active():
            return
        self._syncing = True
        for mid, other in self.eq_buttons.items():
            if mid != mode_id:
                other.set_active(False)
        self._syncing = False
        if mode_id == 7:
            self.exp_eq.set_expanded(True)
        self.controller.set_equalizer_preset(mode_id)

    def _on_reset_eq_clicked(self, _):
        self._syncing = True
        for sc in self.eq_band_scales:
            sc.set_value(0)
        self._syncing = False
        self._push_custom_eq()

    def _push_custom_eq(self):
        if self._syncing:
            return
        bands = [int(sc.get_value()) for sc in self.eq_band_scales]
        self.controller.set_custom_equalizer(bands)

    def _push_spatial(self):
        if self._syncing:
            return
        self.controller.set_spatial_audio(self.sw_spatial.get_active(), self.sw_head_track.get_active())

    def _push_touch_locks(self):
        if self._syncing:
            return
        lock_all = not self.sw_touch_enabled.get_active()
        self.controller.set_touchpad_gestures(
            lock_all,
            self.sw_pinch_1.get_active(),
            self.sw_pinch_2.get_active(),
            self.sw_pinch_3.get_active(),
            self.sw_pinch_hold.get_active(),
            self.sw_call_dbl.get_active(),
            self.sw_call_hold.get_active(),
        )

    def _push_touch_options(self):
        if self._syncing:
            return
        l_code = self.touch_opt_codes[min(self.dd_opt_l.get_selected(), 3)]
        r_code = self.touch_opt_codes[min(self.dd_opt_r.get_selected(), 3)]
        self.controller.set_touchpad_options(l_code, r_code)

    def _push_nc_cycle(self):
        if self._syncing:
            return
        self.controller.set_pinch_hold_nc_cycle(
            self.chk_l_anc.get_active(),
            self.chk_l_amb.get_active(),
            self.chk_l_adp.get_active(),
            self.chk_l_off.get_active(),
            self.chk_r_anc.get_active(),
            self.chk_r_amb.get_active(),
            self.chk_r_adp.get_active(),
            self.chk_r_off.get_active(),
        )

    def _on_lighting_changed(self, dd: Gtk.DropDown, _):
        if not self._syncing:
            self.controller.set_lighting_mode(int(dd.get_selected()))

    def _on_send_raw_clicked(self, _):
        id_str = self.entry_msg_id.get_text().strip()
        hex_str = self.entry_payload.get_text().strip()
        try:
            mid = int(id_str, 16) if id_str.startswith("0x") else int(id_str, 10)
            payload = bytes.fromhex(hex_str) if hex_str else b""
            self.controller.send_message(mid, payload)
        except Exception as e:
            print(f"Raw send error: {e}")

    def _on_controller_update(self, state: Buds4ProState, pkt: Optional[SppPacket]):
        GLib.idle_add(self._render_state, state, pkt)

    def _render_state(self, s: Buds4ProState, pkt: Optional[SppPacket]):
        self._syncing = True
        try:
            if s.connected:
                self.title_widget.set_title(s.device_name)
                self.title_widget.set_subtitle(f"Connected ({s.device_mac})  •  {s.noise_control_mode_name}")
                self.conn_btn.set_label("Reconnect")
                self.conn_btn.remove_css_class("suggested-action")
                self.disconn_btn.add_css_class("destructive-action")
            else:
                self.title_widget.set_title(s.device_name)
                self.title_widget.set_subtitle(f"Disconnected ({s.device_mac})")
                self.conn_btn.set_label("Connect")
                self.conn_btn.add_css_class("suggested-action")
                self.disconn_btn.remove_css_class("destructive-action")

            # Hero Cards
            self.lbl_bat_l.set_label(f"{s.battery_left}%")
            self.bar_bat_l.set_value(max(0, min(100, s.battery_left)))
            self.lbl_place_l.set_label(s.placement_left_name + (" ⚡" if s.charging_left else ""))
            self.lbl_place_l.set_css_classes(["status-pill" if s.placement_left == 1 else "status-pill-muted"])

            self.lbl_bat_r.set_label(f"{s.battery_right}%")
            self.bar_bat_r.set_value(max(0, min(100, s.battery_right)))
            self.lbl_place_r.set_label(s.placement_right_name + (" ⚡" if s.charging_right else ""))
            self.lbl_place_r.set_css_classes(["status-pill" if s.placement_right == 1 else "status-pill-muted"])

            if 0 < s.battery_case <= 100:
                self.lbl_bat_c.set_label(f"{s.battery_case}%")
                self.bar_bat_c.set_value(s.battery_case)
                self.lbl_place_c.set_label("Charging ⚡" if s.charging_case else "Case Open")
                self.lbl_place_c.set_css_classes(["status-pill"])
            else:
                self.lbl_bat_c.set_label("Closed")
                self.bar_bat_c.set_value(0)
                self.lbl_place_c.set_label("Standby")
                self.lbl_place_c.set_css_classes(["status-pill-muted"])

            # Noise Control
            for mid, btn in self.nc_mode_buttons.items():
                btn.set_active(s.noise_control_mode == mid)
            self._update_contextual_noise_rows(s.noise_control_mode)

            self.anc_scale.set_value(s.anc_level + 1)
            self.row_anc_level.set_subtitle(f"Level {s.anc_level + 1} of 5")
            self.amb_scale.set_value(s.ambient_volume + 1)
            self.row_amb_vol.set_subtitle(f"Level {s.ambient_volume + 1} of 5")

            self.sw_conv_det.set_active(s.detect_conversations)
            dur_lbl = {0: "5s", 1: "10s", 2: "15s"}.get(s.detect_conversations_duration, "5s")
            self.exp_voice_detect.set_subtitle(
                f"Voice Detect: {'On (' + dur_lbl + ')' if s.detect_conversations else 'Off'}  •  Adaptive Vol: {'On' if s.adaptive_volume else 'Off'}  •  Siren: {'On' if s.siren_detect else 'Off'}"
            )
            self.dd_conv_dur.set_selected(min(2, max(0, s.detect_conversations_duration)))
            self.sw_siren.set_active(s.siren_detect)
            self.sw_adapt_vol.set_active(s.adaptive_volume)
            self.sw_nc_one.set_active(s.noise_controls_with_one_earbud)

            self.sw_amb_cust.set_active(s.ambient_custom_enabled)
            self.scale_amb_l.set_value(s.ambient_custom_left)
            self.scale_amb_r.set_value(s.ambient_custom_right)
            self.scale_amb_tone.set_value(s.ambient_custom_tone)
            self.sw_amb_extra.set_active(s.extra_high_ambient)

            # Equalizer & Sound
            for mid, btn in self.eq_buttons.items():
                btn.set_active(s.equalizer_mode == mid)
            self.exp_eq.set_subtitle(f"Active: {EQ_PRESET_NAMES.get(s.equalizer_mode, 'Balanced')} — Click for 9-Band Custom EQ")
            for idx, sc in enumerate(self.eq_band_scales):
                if idx < len(s.custom_eq_bands):
                    sc.set_value(s.custom_eq_bands[idx])

            self.sw_spatial.set_active(s.spatial_audio)
            self.sw_head_track.set_active(s.spatial_head_tracking)
            self.scale_balance.set_value(s.stereo_balance)
            self.sw_gaming.set_active(s.gaming_mode or s.adjust_sound_sync)
            self.exp_spatial.set_subtitle(
                f"360 Audio: {'On' if s.spatial_audio else 'Off'}  •  Head Tracking: {'On' if s.spatial_head_tracking else 'Off'}  •  Gaming: {'On' if (s.gaming_mode or s.adjust_sound_sync) else 'Off'}"
            )

            # Touch Controls
            self.sw_touch_enabled.set_active(not s.touchpad_lock_all)
            self.exp_touch.set_subtitle(
                "Unlocked — Click to configure Pinch + Hold and gesture options"
                if not s.touchpad_lock_all
                else "Locked (All earbud touch gestures disabled)"
            )
            self.sw_pinch_1.set_active(s.single_pinch_on)
            self.sw_pinch_2.set_active(s.double_pinch_on)
            self.sw_pinch_3.set_active(s.triple_pinch_on)
            self.sw_pinch_hold.set_active(s.pinch_hold_on)
            self.sw_call_dbl.set_active(s.double_pinch_call_on)
            self.sw_call_hold.set_active(s.pinch_hold_call_on)

            if s.touch_option_left in self.touch_opt_codes:
                self.dd_opt_l.set_selected(self.touch_opt_codes.index(s.touch_option_left))
            if s.touch_option_right in self.touch_opt_codes:
                self.dd_opt_r.set_selected(self.touch_opt_codes.index(s.touch_option_right))

            self.chk_l_anc.set_active(s.nc_cycle_left_anc)
            self.chk_l_amb.set_active(s.nc_cycle_left_ambient)
            self.chk_l_adp.set_active(s.nc_cycle_left_adaptive)
            self.chk_l_off.set_active(s.nc_cycle_left_off)
            self.chk_r_anc.set_active(s.nc_cycle_right_anc)
            self.chk_r_amb.set_active(s.nc_cycle_right_ambient)
            self.chk_r_adp.set_active(s.nc_cycle_right_adaptive)
            self.chk_r_off.set_active(s.nc_cycle_right_off)

            # Blade Lights & Voice
            self.dd_lighting.set_selected(min(2, max(0, s.lighting_control)))
            self.sw_bixby.set_active(s.bixby_wakeup)
            self.sw_hotcmd.set_active(s.hot_command_enabled)
            self.sw_speak_seam.set_active(s.speak_seamlessly)
            self.exp_lights.set_subtitle(
                f"Blade Lights: {LIGHT_NAMES.get(s.lighting_control, 'Blink')}  •  Voice Cmds: {'On' if s.hot_command_enabled else 'Off'}  •  Bixby: {'On' if s.bixby_wakeup else 'Off'}"
            )

            # Calls & Connection
            self.sw_sidetone.set_active(s.sidetone_enabled)
            self.sw_clear_call.set_active(s.extra_clear_call)
            self.sw_seamless.set_active(s.seamless_connection)
            self.sw_auto_pause.set_active(s.auto_pause_resume)
            self.sw_call_path.set_active(s.call_path_control)
            self.sw_neck.set_active(s.neck_stretch_calibration)
            self.exp_calls.set_subtitle(
                f"Sidetone: {'On' if s.sidetone_enabled else 'Off'}  •  Clear Call: {'On' if s.extra_clear_call else 'Off'}  •  Seamless Conn: {'On' if s.seamless_connection else 'Off'}"
            )

            # Diagnostics & Hardware
            st_str = "Not Run" if s.self_test_passed is None else ("PASSED" if s.self_test_passed else "FAILED")
            self.row_diag.set_subtitle(f"Fit: L={s.fit_test_left}, R={s.fit_test_right}  •  Self-Test: {st_str}")
            self.exp_dev.set_subtitle(
                f"FW: {s.fw_version_left or 'R640XXU0AZD2'}  •  Temps: {s.temp_left_c}°C / {s.temp_right_c}°C  •  Cell: {s.vcell_mv} mV"
            )
            self.row_thermal.set_subtitle(
                f"Left: {s.temp_left_c}°C ({s.cycles_left} cycles)  •  Right: {s.temp_right_c}°C ({s.cycles_right} cycles)  •  Voltage: {s.vcell_mv} mV"
            )
            self.row_hw_fw.set_subtitle(
                f"Buds FW: {s.fw_version_left or '--'}  •  Case FW: {s.fw_version_cradle or '--'}  •  HW: {s.hw_version or '--'}  •  Touch FW: {s.touch_fw_version or '--'}"
            )
            self.row_sku_serial.set_subtitle(
                f"SKU: {s.sku_left}  •  Serials: L={s.serial_left or '--'}, R={s.serial_right or '--'}, Case={s.serial_cradle or '--'}"
            )

            if pkt is not None:
                buf = self.log_view.get_buffer()
                line = f"[{pkt.timestamp}] {pkt.direction} id={pkt.msg_id:3d} (0x{pkt.msg_id:02X}) {pkt.name:<30} len={len(pkt.payload):3d} | {pkt.payload.hex(' ')}\n"
                buf.insert(buf.get_end_iter(), line)
        finally:
            self._syncing = False
        return False


class Buds4ProApp(Adw.Application):
    def __init__(self, controller: Buds4ProController):
        super().__init__(application_id="io.github.salman.SamsungBuds4ProStudio", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.controller = controller
        self.win: Optional[Buds4ProWindow] = None

    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        if not self.win:
            self.win = Buds4ProWindow(self, self.controller)
        self.win.present()
        GLib.timeout_add(150, lambda: (self.controller.connect(), False)[1])


def main():
    ctrl = Buds4ProController()
    http_srv = Buds4ProHttpServer(ctrl, "127.0.0.1", 8765)
    http_srv.start()
    print("Samsung Galaxy Buds4 Pro Studio — Web API listening on http://127.0.0.1:8765")
    app = Buds4ProApp(ctrl)
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
