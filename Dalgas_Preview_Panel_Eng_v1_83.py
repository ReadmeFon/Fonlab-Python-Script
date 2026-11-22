#FLM: Dalgas: Preview Panel
"""
version_1.83
FontLab 8/9: A preview panel attached to the Glyph Window.
Works in Horizontal mode (bottom of the Glyph Window) and Vertical mode (right edge of the Glyph Window).

[Features]
- Ratio constant for the increment/decrement step of Size / Spacing / Leading: 	PP_SLIDER_ICON_STEP_RATIO = 0.02
- Name of the punctuation conversion rules in Vertical mode: 	v_punct_rules
- Contents of the punctuation conversion rules in Vertical mode: 	PP_V_PUNCT_RULES_DEFAULT =
----------------------------------------------------------------------
- Horizontal mode: overlay at the bottom of the Glyph Window. For the single active glyph, shows either 'Show All Master Glyphs'
  or 'Interpolation Preview' (the two functions are mutually exclusive).
  - Show All Master Glyphs: shows the active glyph of every master side by side.
  - Interpolation Preview: interpolates and shows only the instances the user registered in Font Info > Instances.
   While FontLab's native Preview panel always shows a fixed 7-step interpolation, this script
   shows exactly the interpolations the user registered in Font Info > Instances (the purpose of this script).
   If Font Info > Axes has several axes, it interpolates only along the Weight axis (axis tag wt). The other axes stay fixed
   at the position of the active master (both Horizontal and Vertical modes).
   In a font with several axes, if the VARIATIONS panel is open, the other axes follow the values chosen in the panel
   (choosing an instance or dragging a slider in the panel updates the preview. The panel's Weight value is not used).
   Ctrl(macOS Command)+click or Alt(macOS Option)+click on the Interpolation button shows all instances registered in
   Font Info > Instances (all axes such as Width, Italic, etc.), grouped by axis. A plain click on the button in this state
   returns to the regular Interpolation Preview (Weight steps) (both Horizontal and Vertical modes).
  - Glyph Import button (right of the Show All Masters button): a click reads the text of the active Glyph Window and shows it;
    Ctrl(macOS Command)+click or Alt(macOS Option)+click puts the preview text into the active Glyph Window
    (holding Ctrl/Alt changes the icon to the glyph export shape). Imported text is not written to the settings file.
  - Fit Height/Width button (up/down arrow left of the Horizontal mode button): each click toggles between fitting the glyph size
    to the window height and fitting all glyphs to the window width (Dock and Floating states are remembered separately).
  - The glyph size zoom (+/- buttons, Alt(macOS Option)+wheel) is saved to the settings file separately for the simple
    Interpolation, All Instances and All Masters views. Switching views restores the zoom last set for that view.
  - Ctrl+click or Alt+click inside the preview switches to text input mode, with Hangul composition input.
    While text is shown, a plain click also places an input caret. Pressing the Interpolation or All Masters button returns to the glyph view.

- Vertical mode: overlay at the right edge of the Glyph Window. Drag the left border to resize the width (default width 340px)
  - Typesets the text entered by the user from top to bottom. Pressing Enter starts a new column to the left.
  - Clicking inside the preview (when user-entered text is shown), or
     Ctrl+click / Alt+click / right-click (when Interpolation Preview / Show All Master Glyphs is shown) —
   any of these places an input caret, with Hangul composition input
  - Text exchange buttons (2, left of the grid icon): the inward arrow reads the text of the active Glyph Window and shows it,
    the outward arrow puts the preview text into the active Glyph Window. Imported text is not written to the settings file.
  - Saved Text button (between the text exchange buttons and the grid icon): a click loads the user text saved in the settings file,
    Alt(macOS Option)+click saves the current preview text to the settings file (holding Alt flips the icon upside down).
  - R button: shows characters other than Hangul, Han (CJK ideographs) and Kana rotated 90 degrees clockwise.
   (1) Ideographic commas / full stops / punctuation (quotes, etc.) are converted by the script's internal settings.
   (2) The conversion rules can be customized. Rules written in this script's settings file, Dalgas_Preview_Panel_Settings.json,
        take precedence. You can simply ask an AI to write the conversion rules for you.
   (3) Alt+click on the R button simply rotates everything to the vertical direction except Hangul / Han / Kana
       (no ideographic comma / full stop conversion). The R button is shown lying on its side.
   (4) Ctrl+click on the R button reads and applies the vertical-writing OpenType Features and Styles
       if the font defines them (e.g. Eulyoo 1945). The R button is shown with an underline below it.

  - Inside the preview, Alt(macOS Option)+wheel scroll increases/decreases the glyph size (Size) (the wheel without Alt scrolls).
  - Hold the Space bar and drag to pan. In the Interpolation / All Masters views it moves up and down; in user text it moves
    along the column direction (left/right). While entering text, Space is typed as a character, so no panning.
  - Pressing the Interpolation or All Masters button shows that function vertically for the single active glyph only.
    In this state no character is rotated, and clicks inside the window are ignored.
    Inside the preview, Ctrl+click, Alt(macOS Option)+click and right-click all switch to user text input mode.
  - Ruler guidelines: drag from FontLab's left or top Ruler and drop inside the preview to create an RGB 252, 66, 55 guideline.
    Guidelines are fixed to the typesetting coordinates, so they move with the glyphs when Size etc. changes.
     Ctrl(macOS Command)+click or Alt(macOS Option)+click on the right thick helper-line button
    deletes the guidelines. Guidelines are not saved to the settings file.
- This script's settings are saved to Dalgas_Preview_Panel_Settings.json in the FontLab Scripts folder and applied on the next run.
  It detects the running FontLab version (8, 9 ...) and uses that version's Scripts folder (e.g. on Windows Documents/FontLab/FontLab 9/Scripts,
  on macOS ~/Library/Application Support/FontLab/FontLab 9/Scripts).


[Guard] -------------------------------------------------------------------------------
[WebBrowser BG Bypass Guard applied]
1. Web browser re-entrancy is handled by the global "WebBrowser BG Bypass Guard".
2. Stabilization code 1 (_is_alive) is used independently of the web browser guard, so it was kept as is.
"""

import os
import re
import struct
import sys
import json
import time
import traceback
import fontlab as fl6
try:
    import FL as legacy         # detects font-switch transitions via the number of open fonts (legacy.fl.count).
except Exception:
    legacy = None
from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui
from typerig.proxy.fl.application.automat import Automat


# ── Widget liveness check helper for script stability (_is_alive) ──────────────
try:
    import sip as _sip

    def _is_alive(widget):
        try:
            return not _sip.isdeleted(widget)
        except Exception:
            return True
except ImportError:
    def _is_alive(widget):
        if widget is None:
            return False
        try:
            widget.isVisible()
            return True
        except Exception:
            return False


# ── WebBrowser BG Bypass Guard ──────────────
# Intercepts the webbrowser.open() call in update-install.py and delegates the actual
# open to a daemon thread. Because ShellExecuteW's nested pump no longer runs the main GUI
# thread's message queue, the browser can open normally while avoiding
# Qt/PythonQt re-entrancy crashes.
import threading as _threading
import webbrowser as _webbrowser

_BG_GUARD_ATTR = '_dalgas_webbrowser_bg_guard'

if not getattr(_webbrowser, _BG_GUARD_ATTR, False):
    _original_webbrowser_open = _webbrowser.open

    def _bg_thread_open(url, new=0, autoraise=True):
        _threading.Thread(
            target=_original_webbrowser_open,
            args=(url,),
            kwargs={'new': new, 'autoraise': autoraise},
            daemon=True,
        ).start()
        return True

    _webbrowser.open = _bg_thread_open
    _webbrowser.open_new = lambda url: _bg_thread_open(url, new=1)
    _webbrowser.open_new_tab = lambda url: _bg_thread_open(url, new=2)
    setattr(_webbrowser, _BG_GUARD_ATTR, True)
# ── WebBrowser BG Bypass Guard End ──────────


# ── app_name, app_version
app_name = 'Dalgas | Preview Panel'
app_version = 'v1.83'
PP_LOG = '[Preview Panel]'


# ============================================================
# Main settings
# ============================================================
PP_SETTINGS_FILE_NAME = 'Dalgas_Preview_Panel_Settings.json'
PP_CONTROLLER_ANCHOR = '_dalgas_preview_panel_controller_v1'
PP_RETIRED_SHELLS_ATTR = '_dalgas_preview_panel_retired_shells'
PP_OVERLAY_OBJECT_NAME = 'DalgasPreviewPanelOverlay'

PP_H_DEFAULT_HEIGHT = 300          # Horizontal mode default height (px)
PP_V_DEFAULT_WIDTH = 340           # Vertical mode default width (px)
PP_V_MIN_WIDTH = 50               # Vertical mode minimum width (px)
PP_H_MIN_HEIGHT = 110              # Horizontal mode minimum height
PP_CANVAS_MIN_VISIBLE = 120        # minimum glyph canvas size the panel leaves free (px)
PP_HANDLE = 7                      # border drag handle thickness (px)
PP_BAR_HEIGHT = 38                 # bottom icon row height (px)
PP_GUIDE_ROW_HEIGHT = 34           # Vertical mode helper-line button row height (px)
PP_SLIDER_ROW_HEIGHT = 30          # Vertical mode Size/Leading row height (px)
PP_ICON = 26                       # icon button size (px)
PP_ICON_GAP = 8                    # gap between icons (px)
PP_ICON_PEN = 1.8                  # icon stroke width
PP_SIDE_MARGIN = 10                # left/right margin of the icon row (px)

PP_H_FILL_RATIO = 0.94             # Horizontal mode default size: glyph frame height (Ascender+|Descender|) = 94% of the glyph area height
PP_H_ZOOM_MIN = 0.1                # +/- zoom range
PP_H_ZOOM_MAX = 8.0
PP_H_ZOOM_STEP = 0.05              # +/- 5% per step (Shift: 10%)
PP_H_ZOOM_STEP_SHIFT = 0.10
PP_H_ZOOM_KEYS = ('h_zoom', 'h_zoom_interp', 'h_zoom_all', 'h_zoom_masters')   # per-view zoom setting keys
PP_ALIGN_ICON = int(round(PP_ICON * 0.9))   # horizontal alignment icon size (90% of the default icon)
PP_H_TEXT_LINE_GAP = 0.15          # Horizontal mode text line gap (ratio of glyph frame height)
PP_H_GLYPH_IO_PEN = 2.0            # Horizontal mode Glyph Import icon stroke width (matches the Horizontal mode icon row)
PP_H_GLYPH_OUT_TIP_X = 0.5         # Horizontal mode export-shape arrow head tip x (px, 2.5)
PP_H_GLYPH_IO_LEFT_EXTEND = 3.0    # Horizontal mode Glyph Import/Export icon rectangle left side extension (px, import 1.0)
PP_SETTINGS_VERSION = 7   # 3 → 4 (v_punct_rules full stop / ellipsis entries extended)
                          # (v_punct_rules Japanese/Chinese punctuation 。、，． entries added)
                          # (v_punct_rules full-width ？！：； entries added)
                          # (v_punct_rules written one per line, rewritten in "rotate 90 group" format)
PP_SLIDER_ICON = 24                # Size/Spacing/Leading icon drawing reference size (px)
PP_SLIDER_ICON_SCALE = {'size': 0.80, 'spacing': 0.80, 'leading': 0.75}  
PP_SLIDER_ICON_STEP_RATIO = 0.005   # amount changed per icon click (ratio of the full slider range)
PP_GUIDE_HIT_RADIUS = 6.0          # screen distance for grabbing a preview guideline (px), (handle area)
PP_SLIDER_ICON_SHIFT_MULT = 10      # multiplier of the change when clicking/right-clicking with Shift held

PP_V_SIZE_MIN = 12                 # Size slider range (px) - minimum glyph size 12px, maximum 300px
PP_V_SIZE_MAX = 300
PP_V_SIZE_DEFAULT = 100
PP_V_LEADING_MIN = 0               # Leading slider range (%)
PP_V_LEADING_MAX = 100
PP_V_LEADING_DEFAULT = 30
PP_GRID_STEP = 20                  # grid step (px)
PP_GUIDE_BAND_RATIO = 0.35         # thick helper-line width = 35% of the widest glyph width

PP_TARGET_INTERVAL_MS = 350        # Glyph Window canvas tracking interval
PP_REFRESH_INTERVAL_MS = 300       # glyph change detection interval
PP_FONT_SETTLE_SEC = 1.0           # time (sec) to pause FontLab object access during a font-switch transition
PP_SAVE_DELAY_MS = 500             # settings save delay
PP_CARET_BLINK_MS = 530
PP_DUPLICATE_COMMIT_TIMEOUT_MS = 500

# Shared names for cooperating with other Dalgas overlays
PP_NAVIGATOR_OVERLAY_NAME = 'DalgasGlyphNavContent'
PP_SAM_QUICK_PREVIEW_NAME = 'DalgasShowAllMastersQuickPreviewOverlayV131'
PP_ERRSP_PANEL_NAME = 'DalgasElementReferencePanelV181'       # Replacer/Separator panel
PP_ZOOM_LENSE_NAME = 'DalgasMarqueeMasterOverlayV1'           # Zoom Lense overlay
PP_SSOGUI_OVERLAY_NAME = 'DalgasNodeCountGraphicOverlay_v5_13'  # Set Shape Order GUI overlay
PP_COLLAPSED_RIVAL_NAMES = (PP_ERRSP_PANEL_NAME, PP_SSOGUI_OVERLAY_NAME)  # panels that must not cover the collapsed bar
PP_ZORDER_CHANGE_EVENT = getattr(QtCore.QEvent, 'ZOrderChange', 126)   # z-order change event
PP_MODE_PROPERTY = 'dalgasPreviewPanelMode'                   # 'h' | 'v' | ''
PP_RULER_MAX_THICKNESS = 40
PP_LAUNCHER_REGISTRY_ATTR = '_dalgas_script_launcher_right_overlay_v1'
PP_LAUNCHER_WIDTH_PROPERTY = 'dalgasScriptLauncherRightReserve'
PP_LAUNCHER_EDGE_PROPERTY = 'dalgasScriptLauncherRightEdge'

# Selections panel Dock (shares the same occupancy marker as the View Glyph Large Size script so they don't overwrite each other)
PP_SELECTIONS_PANEL_OBJECT_NAME = 'SelectionsPanel'
PP_SELECTIONS_OWNER_PROPERTY = 'dalgasSelectionsHostOwner'
PP_SELECTIONS_HOST_MARKER_PROPERTY = 'dalgasSelectionsHostMarker'
PP_SELECTIONS_OWNER_ID = 'DalgasPreviewPanel'
PP_SELECTIONS_HOST_OBJECT_NAME = 'DalgasPreviewPanelSelectionsHost'
PP_DOCK_TRANSITION_GRACE_TICKS = 4
PP_DOCK_AUTO_FILL_DELAY_MS = 200          # wait before auto-fitting the height after Dock layout finishes (ms)
PP_DOCK_AUTO_FILL_MIN_GAP = 24            #  ignore empty space smaller than this (px)
PP_DOCK_AUTO_FILL_MAX_RETRY = 15          # maximum number of retries while dragging
PP_DOCK_AUTO_FILL_STEPS = 6               # number of handle move event steps
_PP_DOCK_AUTO_FILL_FAIL_REPORTED = [False]   # print the failure error only once

_PP_LOCATION_WT_RE = re.compile(r'\bwt\s*=\s*(-?\d+(?:\.\d+)?)')
# reads all 'axis tag=value' pairs from an axis location (flLocation) string (e.g. wt=470, wd=100, it=0).
_PP_LOCATION_ITEM_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)[\'"]?\s*[=:]\s*(-?\d+(?:\.\d+)?)')
PP_WEIGHT_AXIS_KEYS = ('wt', 'wght', 'weight')   # Weight axis tags (axis tags in Font Info > Axes, compared in lowercase)
# Italic/Slant axis tags (compared in lowercase). Used to put the Plain group first in the All Instances preview.
PP_ITALIC_AXIS_KEYS = ('it', 'ital', 'italic', 'sl', 'slnt', 'slant')
# VARIATIONS panel (FontLab internal widget names). If a build changes the names, the panel is not found and v1.65 behavior is used.
PP_VAR_PANEL_NAME = 'LocationPanel'       # VARIATIONS panel body
PP_VAR_AXIS_WIDGET_NAME = 'LocationWidget'   # row of one axis (axis name label, value field)
PP_VAR_RESCAN_SEC = 3.0                   # interval (sec) to search again when the panel is not found or hidden


# ============================================================
# PythonQt common helpers
# ============================================================
def _v(obj, name, default=None):
    """Reads a value, absorbing PythonQt property/method differences."""
    if obj is None:
        return default
    try:
        attr = getattr(obj, name)
    except Exception:
        return default
    try:
        return attr() if callable(attr) else attr
    except Exception:
        return default


def _int(obj, name, default=0):
    try:
        return int(_v(obj, name, default))
    except Exception:
        return default


def _object_name(widget):
    try:
        return str(_v(widget, 'objectName', '') or '')
    except Exception:
        return ''


def _class_name(widget):
    try:
        return type(widget).__name__
    except Exception:
        return ''


def _widget_alive(widget):
    if widget is None:
        return False
    try:
        widget.isVisible()
        return True
    except Exception:
        return False


def _same_widget(first, second):
    if first is second:
        return True
    if first is None or second is None:
        return False
    try:
        return str(first) == str(second)
    except Exception:
        return False


def _event_xy(event):
    for name in ('pos', 'localPos', 'posF'):
        point = _v(event, name, None)
        if point is not None:
            try:
                return float(_v(point, 'x', 0.0)), float(_v(point, 'y', 0.0))
            except Exception:
                continue
    return 0.0, 0.0


def _event_global_xy(event):
    for name in ('globalPos', 'globalPosition', 'screenPos'):
        point = _v(event, name, None)
        if point is not None:
            try:
                return int(_v(point, 'x', 0)), int(_v(point, 'y', 0))
            except Exception:
                continue
    try:
        point = QtGui.QCursor.pos()
        return int(_v(point, 'x', 0)), int(_v(point, 'y', 0))
    except Exception:
        return 0, 0


def _modifiers_int(event):
    try:
        return int(_v(event, 'modifiers', 0) or 0)
    except Exception:
        return 0


def _qstring_to_text(value):
    text = str(value) if value is not None else ''
    if text.startswith('QString (C++ Object ') or text.startswith('QString (C++ object '):
        return ''
    return text


def pp_push_handle_cursor(widget, shape):
    """Pushes the handle cursor onto the top of the override stack (once). Counters FontLab's Arrow override."""
    if getattr(widget, '_cursor_pushed', False):
        return
    try:
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(shape))
        widget._cursor_pushed = True
    except Exception:
        widget._cursor_pushed = False


def pp_pop_handle_cursor(widget):
    """Pops only the one override cursor pushed by the handle."""
    if not getattr(widget, '_cursor_pushed', False):
        return
    widget._cursor_pushed = False
    try:
        QtGui.QApplication.restoreOverrideCursor()
    except Exception:
        pass


def pp_cursor_inside(widget):
    try:
        return _v(widget, 'rect').contains(widget.mapFromGlobal(QtGui.QCursor.pos()))
    except Exception:
        return False


def pp_space_key_down():
    """Reads directly from the OS whether the Space key is held (works even if the panel has no keyboard focus)."""
    try:
        import ctypes
        if sys.platform.startswith('win'):
            return bool(ctypes.windll.user32.GetAsyncKeyState(0x20) & 0x8000)
        if sys.platform == 'darwin':
            lib = getattr(pp_space_key_down, '_quartz', None)
            if lib is None:
                lib = ctypes.cdll.LoadLibrary(
                    '/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
                lib.CGEventSourceKeyState.restype = ctypes.c_bool
                lib.CGEventSourceKeyState.argtypes = [ctypes.c_int32, ctypes.c_uint16]
                pp_space_key_down._quartz = lib
            return bool(lib.CGEventSourceKeyState(0, 49))  # 0: CombinedSessionState, 49: Space
    except Exception:
        pass
    return False


def pp_shift_down():
    try:
        mods = int(QtGui.QApplication.keyboardModifiers())
        return bool(mods & int(QtCore.Qt.ShiftModifier))
    except Exception:
        return False


def pp_alt_down():
    """Whether the Alt (macOS Option) key is held (reads the current state even without a mouse event)."""
    for reader in ('queryKeyboardModifiers', 'keyboardModifiers'):
        try:
            mods = int(getattr(QtGui.QApplication, reader)())
            return bool(mods & int(QtCore.Qt.AltModifier))
        except Exception:
            continue
    return False


def pp_ctrl_down():
    """Whether the Ctrl key (macOS Command — Qt's Control) is held (reads the current state without a mouse event)."""
    for reader in ('queryKeyboardModifiers', 'keyboardModifiers'):
        try:
            mods = int(getattr(QtGui.QApplication, reader)())
            return bool(mods & int(QtCore.Qt.ControlModifier))
        except Exception:
            continue
    return False


def pp_switch_click_modifier(event):
    """Whether this is a click with Ctrl (Mac Command is Qt's Control, Mac Control is Qt's Meta) or Alt (Mac Option)."""
    mods = _modifiers_int(event)
    mask = 0
    for name in ('ControlModifier', 'MetaModifier', 'AltModifier'):
        try:
            mask |= int(getattr(QtCore.Qt, name))
        except Exception:
            pass
    return bool(mods & mask)


def pp_retire(*objects):
    """Keeps a PythonQt widget as a terminated shell instead of deleting it immediately."""
    try:
        shells = getattr(sys, PP_RETIRED_SHELLS_ATTR, None)
        if shells is None:
            shells = []
            setattr(sys, PP_RETIRED_SHELLS_ATTR, shells)
        for obj in objects:
            if obj is not None and not any(item is obj for item in shells):
                shells.append(obj)
    except Exception:
        pass


# ============================================================
# Settings storage (FontLab Scripts folder / Dalgas_Preview_Panel_Settings.json)
# ============================================================
PP_DEFAULT_SETTINGS = {
    'mode': 'h',                       # 'h' Horizontal mode, 'v' Vertical mode
    'h_panel_height': PP_H_DEFAULT_HEIGHT,
    'v_panel_width': PP_V_DEFAULT_WIDTH,
    'h_zoom': 1.0,                     # Horizontal mode glyph size zoom (1.0 = fill height)
    'h_zoom_interp': 1.0,              # simple Interpolation view zoom
    'h_zoom_all': 1.0,                 # All Instances view zoom
    'h_zoom_masters': 1.0,             # All Masters view zoom
    'h_fit': 'height',                 # Floating Horizontal mode size fit: 'width' | 'height'
    'h_view': 'interp',                # Horizontal mode: 'interp' | 'masters' | None
    'h_align': 'center',               # alignment when exceeding the window in Horizontal mode: 'left' | 'center' | 'right'
    'settings_version': PP_SETTINGS_VERSION,
    'v_size': PP_V_SIZE_DEFAULT,
    'v_leading': PP_V_LEADING_DEFAULT,
    'v_spacing': 0,                    # Vertical mode spacing between glyphs (% of Size, -100~100)
    'dock_fit': 'width',               # Dock Horizontal mode size fit: 'width' | 'height'
    'guide_grid': False,
    'guide_edges': False,
    'guide_center': False,
    'guide_right': False,
    'rotate_latin': True,
    'rotate_plain': False,             # R Alt+click = rotate all characters except Hangul/Han/Kana 90° without rules
    'v_vert': False,                   # R Ctrl+click = apply OpenType vertical glyphs (vert) and vertical Advance
    'v_ltr': False,                    # Vertical mode column direction (True = left→right)
    'dark': False,
    'v_text': [],                      # Vertical mode text (one character, '\n', '/glyphname')
    'v_punct_rules': None,             # vertical writing punctuation rules (None means PP_V_PUNCT_RULES_DEFAULT)
}

# Korean vertical writing punctuation rules (applied to Vertical mode input text when R is selected)
#   "char": {"replace": replacement char, "rotate": 0 | 90 | 180, "move": "mozum", "align": "center",
#            "alternate": [opening char, closing char], "skip_after": ["latin", "digit"]}
#   skip_after: if the preceding character is Latin (latin) or a digit (digit), the rule is not used and the default R (Rotate) rule applies.
#   rotate 90 + align center: places the center of the rotated outline at the center of the glyph cell.
#   rotate: clockwise angle (around the glyph center). move "mozum": keeps the shape and moves the outline center to the
#   opposite side of the glyph center. alternate: for marks with no opening/closing distinction such as straight quotes,
#   odd occurrences use the opening char rule and even occurrences use the closing char rule.
PP_V_PUNCT_RULES_DEFAULT = {
    '.': {'replace': u'\u3002', 'rotate': 180,             # full stop → ideographic full stop 。
          'skip_after': ['latin', 'digit']},                # a full stop after Latin/digits behaves like Latin
    ',': {'replace': u'\u3001', 'move': 'mozum',          # comma → ideographic comma 、 (Mozum style conversion)
          'skip_after': ['latin', 'digit']},                # a comma after Latin/digits behaves like Latin
    u'\u3002': {'rotate': 180},                             # ideographic full stop 。 (direct Japanese/Chinese input)
    u'\u3001': {'move': 'mozum'},                           # ideographic comma 、 (including Chinese enumeration comma)
    u'\uFF0C': {'move': 'mozum'},                           # full-width comma ， (not replaced with 、, a comma for Chinese commas)
    u'\uFF0E': {'replace': u'\u3002', 'rotate': 180},       # full-width full stop ． → 。
    '?': {'rotate': 0, 'align': 'center'},                  # question mark
    '!': {'rotate': 0, 'align': 'center'},                  # exclamation mark
    u'\uFF1F': {'rotate': 0, 'align': 'center'},            # full-width question mark ？
    u'\uFF01': {'rotate': 0, 'align': 'center'},            # full-width exclamation mark ！
    u'\u201C': {'replace': u'\u300E', 'rotate': 90},       # “ → 『
    u'\u201D': {'replace': u'\u300F', 'rotate': 90},       # ” → 』
    u'\u2018': {'replace': u'\u300C', 'rotate': 90},       # ‘ → 「
    u'\u2019': {'replace': u'\u300D', 'rotate': 90},       # ’ → 」
    '"': {'alternate': [u'\u201C', u'\u201D']},           # straight double quote
    "'": {'alternate': [u'\u2018', u'\u2019']},           # straight single quote
    '(': {'rotate': 90}, ')': {'rotate': 90},
    '[': {'rotate': 90}, ']': {'rotate': 90},
    '{': {'rotate': 90}, '}': {'rotate': 90},
    u'\u300C': {'rotate': 90}, u'\u300D': {'rotate': 90},   # 「 」
    u'\u300E': {'rotate': 90}, u'\u300F': {'rotate': 90},   # 『 』
    u'\u3014': {'rotate': 90}, u'\u3015': {'rotate': 90},   # 〔 〕
    u'\u3008': {'rotate': 90}, u'\u3009': {'rotate': 90},   # 〈 〉
    u'\u300A': {'rotate': 90}, u'\u300B': {'rotate': 90},   # 《 》
    u'\u3010': {'rotate': 90}, u'\u3011': {'rotate': 90},   # 【 】
    u'\u3018': {'rotate': 90}, u'\u3019': {'rotate': 90},   # 〘 〙
    u'\u301A': {'rotate': 90}, u'\u301B': {'rotate': 90},   # 〚 〛
    u'\u3003': {'rotate': 90},   # 〃(Ditto Mark)

    u'\u2026': {'rotate': 90, 'align': 'center'},           # … (centered in the cell after rotation)
    u'\u00B7': {'rotate': 90},                              # ·
    ':': {'rotate': 90}, ';': {'rotate': 90},
    u'\uFF1A': {'rotate': 90}, u'\uFF1B': {'rotate': 90},   # full-width ： ；
    u'\u2015': {'rotate': 90}, u'\u2014': {'rotate': 90},   # ― —
    '-': {'rotate': 90},
    '~': {'rotate': 90},
    '/': {'rotate': 90},
}


def pp_default_punct_rules():
    return dict((key, dict(value)) for key, value in PP_V_PUNCT_RULES_DEFAULT.items())


PP_V_PUNCT_KEYS_ADDED_V5 = (u'\u3002', u'\u3001', u'\uFF0C', u'\uFF0E')   
PP_V_PUNCT_KEYS_ADDED_V6 = (u'\uFF1F', u'\uFF01', u'\uFF1A', u'\uFF1B')   


def pp_migrate_punct_rules(rules, old_version):
    """Fills new default entries into v_punct_rules of an older settings file (keeps the user's entries)."""
    if not isinstance(rules, dict):
        return rules
    defaults = pp_default_punct_rules()
    if old_version < 4:
        # extension: full stop skip_after, ellipsis align center
        period = rules.get('.')
        if isinstance(period, dict) and 'skip_after' not in period:
            period['skip_after'] = list(defaults['.']['skip_after'])
        ellipsis = rules.get(u'\u2026')
        if isinstance(ellipsis, dict) and 'align' not in ellipsis:
            ellipsis['align'] = 'center'
    if old_version < 5:
        for key in PP_V_PUNCT_KEYS_ADDED_V5:
            if key not in rules:
                rules[key] = dict(defaults[key])
    if old_version < 6:
        for key in PP_V_PUNCT_KEYS_ADDED_V6:   
            if key not in rules:
                rules[key] = dict(defaults[key])
    return rules


PP_V_PUNCT_ROTATE90_GROUP_KEY = 'rotate 90 group'   # group of characters simply rotated 90° clockwise (comma-separated string)


def pp_is_rotate90_group_key(key):
    """Checks whether the key is 'rotate 90 group' (ignores case, spaces, underscores and hyphens)."""
    if not isinstance(key, str):
        return False
    return re.sub(r'[\s_\-]', '', key).lower() == 'rotate90group'


def pp_parse_rotate90_group(value):
    """Converts a "(,),[,]" style (comma-separated string) or a character list into a character list. Items that are not 1 character are dropped."""
    if isinstance(value, str):
        items = value.split(',')
    elif isinstance(value, (list, tuple)):
        items = [item for item in value if isinstance(item, str)]
    else:
        return []
    chars = []
    for item in items:
        item = item.strip()
        if len(item) == 1 and item not in chars:
            chars.append(item)
    return chars


PP_V_PUNCT_NOTE_KEY = u'// Disable a rule'   # settings file note (key used in place of a JSON comment)
PP_V_PUNCT_NOTE_TEXT = (u'To disable a built-in script rule, enter it as char: {} as in the example below. '
                        u'That character will then not be rotated 90 degrees.')   # without double quotes (\")
PP_V_PUNCT_EXAMPLE_KEY = u'// Example'                     # rule-disable example (a comment key, so it is not applied)
PP_V_PUNCT_EXAMPLE_VALUE = {u'\u3010': {}}             # {"【": {}}


def pp_is_punct_comment_key(key):
    """Keys starting with "//" are comments (not used as rules)."""
    return isinstance(key, str) and key.startswith('//')


def pp_merge_default_punct_rules(rules):
    """Characters not in the settings file rules are filled from the script's default rules (settings file rules take precedence).
    Returns: (rules, whether any characters were filled)"""
    if not isinstance(rules, dict):
        return rules, False
    added = False
    for key, value in PP_V_PUNCT_RULES_DEFAULT.items():
        if key not in rules:
            rules[key] = dict(value)
            added = True
    return rules, added


def pp_clean_punct_rules(value):
    """Validates v_punct_rules in the settings file. None if unusable.
    The "rotate 90 group" string is expanded into per-character {"rotate": 90} rules (individual rules take precedence)."""
    if not isinstance(value, dict):
        return None
    rules = {}
    group_chars = []
    for key, rule in value.items():
        if pp_is_punct_comment_key(key):
            if rule is not None:
                rules[key] = rule   # (also keeps non-string JSON values): comments are only kept (not single-character keys, so they never match a rule lookup).
            continue
        if pp_is_rotate90_group_key(key):
            group_chars.extend(pp_parse_rotate90_group(rule))   
            continue
        if not isinstance(key, str) or len(key) != 1 or not isinstance(rule, dict):
            continue
        clean = {}
        replace = rule.get('replace')
        if isinstance(replace, str) and len(replace) == 1:
            clean['replace'] = replace
        rotate = rule.get('rotate')
        if isinstance(rotate, (int, float)) and not isinstance(rotate, bool) and int(rotate) in (0, 90, 180):
            clean['rotate'] = int(rotate)
        if rule.get('move') == 'mozum':
            clean['move'] = 'mozum'
        if rule.get('align') == 'center':
            clean['align'] = 'center'
        alternate = rule.get('alternate')
        if (isinstance(alternate, (list, tuple)) and len(alternate) == 2
                and all(isinstance(item, str) and len(item) == 1 for item in alternate)):
            clean['alternate'] = [alternate[0], alternate[1]]
        skip_after = rule.get('skip_after')
        if isinstance(skip_after, (list, tuple)):
            kinds = [item for item in skip_after if item in ('latin', 'digit')]
            if kinds:
                clean['skip_after'] = kinds
        rules[key] = clean
    for char in group_chars:   
        if char not in rules:
            rules[char] = {'rotate': 90}
    return rules


def pp_punct_rule_group(key, rule):
    """Classification for the settings file write order.
    0 full stop/comma (ideographic full stop/comma) / 1 replace, replace then rotate / 2 other individual rules / 3 alternate / 4 rotate 90 group"""
    if rule == {'rotate': 90}:
        return 4
    if rule.get('alternate'):
        return 3
    if (key in ('.', ',') or rule.get('move') == 'mozum' or rule.get('rotate') == 180
            or rule.get('replace') in (u'\u3002', u'\u3001')):
        return 0
    if rule.get('replace'):
        return 1
    return 2


def pp_punct_rules_json_text(rules, indent='  '):
    """Builds an easy-to-edit JSON string from v_punct_rules.
    Writes one rule per line, and joins simple 90° rotation characters with commas in "rotate 90 group" at the very end."""
    lines = ['%s%s%s: %s' % (indent, indent, json.dumps(PP_V_PUNCT_NOTE_KEY, ensure_ascii=False),
                             json.dumps(PP_V_PUNCT_NOTE_TEXT, ensure_ascii=False)),   
             '%s%s%s: %s' % (indent, indent, json.dumps(PP_V_PUNCT_EXAMPLE_KEY, ensure_ascii=False),
                             json.dumps(PP_V_PUNCT_EXAMPLE_VALUE, ensure_ascii=False))]   
    for key, rule in rules.items():   # comments added by the user
        if (pp_is_punct_comment_key(key) and key not in (PP_V_PUNCT_NOTE_KEY, PP_V_PUNCT_EXAMPLE_KEY)
                and rule is not None):
            lines.append('%s%s%s: %s' % (indent, indent, json.dumps(key, ensure_ascii=False),
                                         json.dumps(rule, ensure_ascii=False)))
    rules = dict((key, rule) for key, rule in rules.items()
                 if not pp_is_punct_comment_key(key) and isinstance(rule, dict))
    order = sorted(enumerate(rules.items()),
                   key=lambda item: (pp_punct_rule_group(item[1][0], item[1][1]), item[0]))
    group_chars = []
    for _index, (key, rule) in order:
        if pp_punct_rule_group(key, rule) == 4 and key != ',':
            group_chars.append(key)
            continue
        lines.append('%s%s%s: %s' % (indent, indent, json.dumps(key, ensure_ascii=False),
                                     json.dumps(rule, ensure_ascii=False)))
    if group_chars:
        lines.append('%s%s%s: %s' % (indent, indent,
                                     json.dumps(PP_V_PUNCT_ROTATE90_GROUP_KEY, ensure_ascii=False),
                                     json.dumps(','.join(group_chars), ensure_ascii=False)))
    return '{\n' + ',\n'.join(lines) + '\n' + indent + '}'


_PP_FONTLAB_MAJOR = [None]   # major version of the running FontLab (determined once)


def _pp_major_from_text(text):
    """Reads the major version number from text such as 'FontLab 9', 'FontLab9', 'FontLab 8.app'."""
    try:
        match = re.search(r'FontLab[ _-]?(\d{1,2})(?!\d)', str(text or ''), re.IGNORECASE)
    except Exception:
        return None
    if match:
        value = int(match.group(1))
        if 7 <= value <= 30:
            return value
    return None


def pp_fontlab_major():
    """Major version of the running FontLab (8, 9 ...). 8 if it cannot be determined."""
    if _PP_FONTLAB_MAJOR[0] is not None:
        return _PP_FONTLAB_MAJOR[0]
    major = None
    app = None
    try:
        app = QtGui.QApplication.instance()
    except Exception:
        app = None
    if app is not None:
        try:
            major = _pp_major_from_text(app.applicationName())
        except Exception:
            major = None
        if major is None:
            try:
                match = re.match(r'\s*(\d{1,2})\.', str(app.applicationVersion() or ''))
                if match and 7 <= int(match.group(1)) <= 30:
                    major = int(match.group(1))
            except Exception:
                major = None
    if major is None:
        texts = [getattr(sys, 'executable', '')]
        try:
            texts.append(sys.argv[0])
        except Exception:
            pass
        try:
            texts.append(os.path.abspath(__file__))
        except Exception:
            pass
        for text in texts:
            major = _pp_major_from_text(text)
            if major is not None:
                break
    if major is None:
        return 8   # an undetermined result is not stored (retried on the next call).
    _PP_FONTLAB_MAJOR[0] = major
    return major


def pp_scripts_dir():
    """Finds the FontLab Scripts folder on Windows and macOS.
    Uses the folder of the running FontLab version ('FontLab 8', 'FontLab 9' ...)."""
    home = os.path.expanduser('~')
    version_dir = 'FontLab %d' % pp_fontlab_major()   
    candidates = []
    if sys.platform.startswith('win'):
        bases = []
        for base in (os.environ.get('USERPROFILE'), home):
            if base and base not in bases:
                bases.append(base)
        for base in bases:
            candidates.append(os.path.join(base, 'Documents', 'FontLab', version_dir, 'Scripts'))
            candidates.append(os.path.join(base, 'OneDrive', 'Documents', 'FontLab', version_dir, 'Scripts'))
            candidates.append(os.path.join(base, 'OneDrive', u'\ubb38\uc11c', 'FontLab', version_dir, 'Scripts'))   # localized 'Documents' folder name of Korean Windows OneDrive
    elif sys.platform == 'darwin':
        candidates.append(os.path.join(home, 'Library', 'Application Support',
                                       'FontLab', version_dir, 'Scripts'))
    else:
        candidates.append(os.path.join(home, 'FontLab', version_dir, 'Scripts'))
    for path in candidates:
        if os.path.isdir(path):
            return path
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(here):
            return here
    except Exception:
        pass
    return home


def pp_settings_path():
    return os.path.join(pp_scripts_dir(), PP_SETTINGS_FILE_NAME)


def pp_load_settings():
    settings = dict(PP_DEFAULT_SETTINGS)
    settings['v_text'] = []
    path = pp_settings_path()
    rewrite_file = False   
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                old_version = int(data.get('settings_version', 1) or 1) if isinstance(
                    data.get('settings_version', 1), (int, float)) else 1
                if old_version < 2:
                    # Vertical mode helper lines now default to all off. Values saved by older versions are discarded once.
                    for guide_key in ('guide_grid', 'guide_edges', 'guide_center', 'guide_right'):
                        data.pop(guide_key, None)
                if old_version < 3:
                    # Vertical mode R (rotate) now defaults to selected. Values saved by older versions are discarded once.
                    data.pop('rotate_latin', None)
                data['settings_version'] = PP_SETTINGS_VERSION
                migrate_from = old_version      # used to extend v_punct_rules.
                rewrite_file = old_version < 7  # files from older versions are rewritten in the new v_punct_rules format.
                for key, default in PP_DEFAULT_SETTINGS.items():
                    if key not in data:
                        continue
                    value = data[key]
                    if key in ('h_view',):
                        if value in ('interp', 'masters', None):
                            settings[key] = value
                    elif key == 'mode':
                        if value in ('h', 'v'):
                            settings[key] = value
                    elif key in ('dock_fit', 'h_fit'):   
                        if value in ('width', 'height'):
                            settings[key] = value
                    elif key == 'h_align':
                        if value in ('left', 'center', 'right'):
                            settings[key] = value
                    elif key == 'v_punct_rules':
                        rules = pp_migrate_punct_rules(pp_clean_punct_rules(value),
                                                       migrate_from)   
                        rules, added = pp_merge_default_punct_rules(rules)   
                        if added:
                            rewrite_file = True   # also writes the filled default rules to the settings file.
                        if isinstance(value, dict) and (value.get(PP_V_PUNCT_NOTE_KEY) != PP_V_PUNCT_NOTE_TEXT
                                                        or PP_V_PUNCT_EXAMPLE_KEY not in value):
                            rewrite_file = True   # rewritten once to insert the note (including the example).
                        settings[key] = rules
                    elif key == 'v_text':
                        if isinstance(value, list):
                            settings[key] = [str(item) for item in value
                                             if isinstance(item, str) and item]
                    elif isinstance(default, bool):
                        settings[key] = bool(value)
                    elif isinstance(default, (int, float)):
                        try:
                            settings[key] = type(default)(value)
                        except Exception:
                            pass
    except Exception as error:
        print('%s Settings read error: %s' % (PP_LOG, error))
    settings['v_size'] = max(PP_V_SIZE_MIN, min(PP_V_SIZE_MAX, int(settings['v_size'])))
    settings['v_leading'] = max(PP_V_LEADING_MIN, min(PP_V_LEADING_MAX, int(settings['v_leading'])))
    settings['v_spacing'] = max(-100, min(100, int(settings['v_spacing'])))
    for zoom_key in PP_H_ZOOM_KEYS:   # per-view zoom
        settings[zoom_key] = max(PP_H_ZOOM_MIN, min(PP_H_ZOOM_MAX, float(settings[zoom_key])))
    if settings['guide_center'] and settings['guide_right']:
        settings['guide_right'] = False
    if settings.get('v_punct_rules') is None:
        settings['v_punct_rules'] = pp_default_punct_rules()   
    if rewrite_file:
        pp_save_settings(settings)   
    return settings


def pp_save_settings(settings):
    path = pp_settings_path()
    data = {}
    # writes v_punct_rules at the very top of the document (json.dump keeps the dict key order).
    keys = ['v_punct_rules'] + [key for key in PP_DEFAULT_SETTINGS if key != 'v_punct_rules']
    for key in keys:
        data[key] = settings.get(key, PP_DEFAULT_SETTINGS[key])
    try:
        # v_punct_rules is written one rule per line, and simple 90° rotation characters on one "rotate 90 group" line.
        rules = data.pop('v_punct_rules', None)
        if not isinstance(rules, dict):
            rules = pp_default_punct_rules()
        rest = json.dumps(data, ensure_ascii=False, indent=2)
        text = '{\n  "v_punct_rules": ' + pp_punct_rules_json_text(rules) + ',\n' + rest[2:] + '\n'
        json.loads(text)   # syntax check before writing (on failure goes to the except below)
        temp_path = path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        os.replace(temp_path, path)
    except Exception as error:
        print('%s Settings save error: %s' % (PP_LOG, error))


# ============================================================
# Color scheme (Light/Dark) — PP_ prefix exclusive to this script
# ============================================================
def PP_is_fontlab_dark():
    """Determines the FontLab UI mode (same order as ERR&S v3.32)."""
    try:
        preferences = fl6.flPreferences()
        dark_value = getattr(preferences, 'isDark', None)
        if callable(dark_value):
            dark_value = dark_value()
        if dark_value is not None:
            return bool(dark_value)
    except Exception:
        pass
    try:
        app = QtGui.QApplication.instance()
        if app is None:
            return False
        palette = getattr(app, 'palette', None)
        if callable(palette):
            palette = palette()
        window_color = palette.color(QtGui.QPalette.Window)
        lightness = getattr(window_color, 'lightness', 255)
        if callable(lightness):
            lightness = lightness()
        return int(lightness) < 128
    except Exception:
        return False


PP_FONTLAB_DARK = PP_is_fontlab_dark()
PP_THEME = {'dark': PP_FONTLAB_DARK}

PP_COLORS = {
    'light': {
        'background': '#ffffff',
        'ink': '#000000',
        'preedit': '#3D77F6',
        'missing': '#9aa1a9',
        'accent': '#3D77F6',
        'icon_off': '#8a8a8a',
        'icon_plain': '#777777',
        'icon_collapsed': '#505050',
        'icon_dark': '#505050',
        'selection': '#3D77F6',
        'icon_hover': '#eef1f5',
        'divider': '#cfd4da',
        'grid': '#ececec',
        'guide_edge': '#c4c8cd',
        'guide_band': '#dddddd',
        'ruler_guide': '#fc4237',      # preview guideline dragged from the Ruler (RGB 252, 66, 55)
        'label': '#222222',
        'slider_groove': '#d9d9d9',
        'slider_fill': '#666666',
        'slider_handle': '#ffffff',
        'slider_border': '#8a8a8a',
    },
    'dark': {
        'background': '#1f2124',
        'ink': '#ffffff',
        'preedit': '#7fb2ff',
        'missing': '#6b727b',
        'accent': '#5b9bff',
        'icon_off': '#8b929a',
        'icon_plain': '#9aa1a9',
        'icon_collapsed': '#505050',
        'icon_dark': '#a0a7af',
        'selection': '#5b9bff',
        'icon_hover': '#3a3f45',
        'divider': '#41464d',
        'grid': '#2c3035',
        'guide_edge': '#5a6068',
        'guide_band': '#3a3f45',
        'ruler_guide': '#fc4237',      # preview guideline dragged from the Ruler (RGB 252, 66, 55)
        'label': '#e6e8ea',
        'slider_groove': '#41464d',
        'slider_fill': '#a0a7af',
        'slider_handle': '#2c3035',
        'slider_border': '#8b929a',
    },
}


def PP_hex(role):
    return PP_COLORS['dark' if PP_THEME['dark'] else 'light'][role]


def PP_color(role):
    return QtGui.QColor(PP_hex(role))


def PP_slider_style():
    return (
        'QSlider { background:transparent; }'
        'QSlider::groove:horizontal { height:4px; background:%s; border-radius:2px; margin:0; }'
        'QSlider::sub-page:horizontal { height:4px; background:%s; border-radius:2px; }'
        'QSlider::add-page:horizontal { height:4px; background:%s; border-radius:2px; }'
        'QSlider::handle:horizontal { background:%s; border:1px solid %s; width:14px; '
        'height:14px; margin:-6px 0; border-radius:8px; }'
        % (PP_hex('slider_groove'), PP_hex('slider_fill'), PP_hex('slider_groove'),
           PP_hex('slider_handle'), PP_hex('slider_border')))


def PP_label_style():
    return ('QLabel { background:transparent; color:%s; font-size:12px; border:none; }'
            % PP_hex('label'))


# ============================================================
# Glyph Window Ruler / Script Launcher / Navigator avoidance (ERR&S v3.32 approach)
# ============================================================
def pp_ruler_insets(canvas):
    """Returns the canvas's (left Ruler width, top Ruler height). (0, 0) if there is no Ruler."""
    if canvas is None:
        return 0, 0
    try:
        canvas_w = _int(canvas, 'width')
        canvas_h = _int(canvas, 'height')
        children = list(canvas.children())
    except Exception:
        return 0, 0
    if canvas_w <= 0 or canvas_h <= 0:
        return 0, 0
    limit = PP_RULER_MAX_THICKNESS
    left = 0
    top = 0
    for child in children:
        try:
            if str(_v(child, 'objectName', '') or ''):
                continue
            if not hasattr(child, 'mapToGlobal'):
                continue
            if not bool(_v(child, 'isVisible', False)):
                continue
            x = _int(child, 'x')
            y = _int(child, 'y')
            w = _int(child, 'width')
            h = _int(child, 'height')
        except Exception:
            continue
        if w <= 0 or h <= 0:
            continue
        if (y == 0 and h <= limit and x <= limit
                and x + w >= canvas_w - 2 and w * 2 > canvas_w):
            top = max(top, h)
        elif (x == 0 and w <= limit and y <= limit
                and y + h >= canvas_h - 2 and h * 2 > canvas_h):
            left = max(left, w)
    return left, top


def pp_ruler_widgets(canvas):
    """Returns the canvas's Ruler widgets as {'left': widget, 'top': widget} (same test as pp_ruler_insets)."""
    result = {}
    if canvas is None:
        return result
    try:
        canvas_w = _int(canvas, 'width')
        canvas_h = _int(canvas, 'height')
        children = list(canvas.children())
    except Exception:
        return result
    if canvas_w <= 0 or canvas_h <= 0:
        return result
    limit = PP_RULER_MAX_THICKNESS
    for child in children:
        try:
            if str(_v(child, 'objectName', '') or ''):
                continue
            if not hasattr(child, 'mapToGlobal'):
                continue
            if not bool(_v(child, 'isVisible', False)):
                continue
            x = _int(child, 'x')
            y = _int(child, 'y')
            w = _int(child, 'width')
            h = _int(child, 'height')
        except Exception:
            continue
        if w <= 0 or h <= 0:
            continue
        if (y == 0 and h <= limit and x <= limit
                and x + w >= canvas_w - 2 and w * 2 > canvas_w):
            result['top'] = child
        elif (x == 0 and w <= limit and y <= limit
                and y + h >= canvas_h - 2 and h * 2 > canvas_h):
            result['left'] = child
    return result


def pp_launcher_right_edge(canvas):
    """Right edge of the Glyph canvas excluding the width occupied by the Script Launcher."""
    if canvas is None:
        return 0
    canvas_width = _int(canvas, 'width')
    try:
        reserve = int(canvas.property(PP_LAUNCHER_WIDTH_PROPERTY) or 0)
        edge = int(canvas.property(PP_LAUNCHER_EDGE_PROPERTY) or 0)
        if reserve > 0 and 0 < edge < canvas_width:
            return edge
    except Exception:
        pass
    return canvas_width


def pp_raise_script_launcher(canvas):
    """After raising the panel, restores the Script Launcher of the same canvas as the final foreground."""
    try:
        host = getattr(sys, PP_LAUNCHER_REGISTRY_ATTR, None)
        if host is None or not getattr(host, '_active', False):
            return
        host_canvas = getattr(host, '_canvas', None)
        if not _same_widget(host_canvas, canvas):
            return
        callback = getattr(host, '_ensure_on_top', None)
        if callable(callback):
            callback()
    except Exception:
        pass


# ── Native Zoom Tool (frameZoom) combined two-direction avoidance (shares the same sys list as ERR&S v3.32) ──
DZF_AVOIDERS_ATTR = '_dalgas_zoom_frame_avoiders_v1'
DZH_AVOIDERS_ATTR = '_dalgas_zoom_frame_horizontal_avoiders_v1'
DZF_FRAME_NAME = 'frameZoom'
DZF_GAP = 4
DZF_DEFAULT_EDGE_GAP = 6


def _dzf_list(attr):
    avoiders = getattr(sys, attr, None)
    if not isinstance(avoiders, list):
        avoiders = []
        try:
            setattr(sys, attr, avoiders)
        except Exception:
            pass
    return avoiders


def _dzf_global_xy(widget):
    point = widget.mapToGlobal(QtCore.QPoint(0, 0))
    return _int(point, 'x'), _int(point, 'y')


def _dzf_on_canvas(widget, canvas):
    current = widget
    for _depth in range(16):
        if _same_widget(current, canvas):
            return True
        current = _v(current, 'parentWidget', None)
        if current is None:
            break
    return False


def pp_zoom_avoid(widget, direction):
    """direction: 'bottom' (bottom overlay), 'right' (right overlay), None (unregister)."""
    if widget is None:
        return
    for attr in (DZF_AVOIDERS_ATTR, DZH_AVOIDERS_ATTR):
        avoiders = _dzf_list(attr)
        avoiders[:] = [item for item in avoiders if item is not widget]
    if direction == 'bottom':
        _dzf_list(DZF_AVOIDERS_ATTR).append(widget)
    elif direction == 'right':
        _dzf_list(DZH_AVOIDERS_ATTR).append(widget)


def _dzf_find_frame(canvas):
    stack = [(canvas, 0)]
    while stack:
        widget, depth = stack.pop()
        for child in list(_v(widget, 'children') or []):
            if _object_name(child) == DZF_FRAME_NAME:
                return child
            if depth < 2:
                stack.append((child, depth + 1))
    return None


def _dzf_prop(widget, name):
    try:
        result = widget.property(name)
        return None if result is None else int(result)
    except Exception:
        return None


def pp_zoom_sync(canvas):
    """Computes the vertical and horizontal avoiding GUIs together and moves frameZoom to its final position only once (ERR&S v3.32)."""
    if canvas is None:
        return
    try:
        frame = _dzf_find_frame(canvas)
        if frame is None:
            return
        cw = _int(canvas, 'width')
        ch = _int(canvas, 'height')
        fw = _int(frame, 'width')
        fh = _int(frame, 'height')
        if cw <= 0 or ch <= 0 or fw <= 0 or fh <= 0:
            return
        x = _int(frame, 'x')
        y = _int(frame, 'y')
        set_x = _dzf_prop(frame, 'dalgasZoomSetX')
        set_y = _dzf_prop(frame, 'dalgasZoomSetY')
        gap_r = _dzf_prop(frame, 'dalgasZoomGapR')
        gap_b = _dzf_prop(frame, 'dalgasZoomGapB')
        candidate_r = cw - x - fw
        if gap_r is None or set_x != x:
            if 0 <= candidate_r <= 80:
                gap_r = candidate_r
            elif gap_r is None:
                gap_r = DZF_DEFAULT_EDGE_GAP
        candidate_b = ch - y - fh
        if gap_b is None or set_y != y:
            if 0 <= candidate_b <= 80:
                gap_b = candidate_b
            elif gap_b is None:
                gap_b = DZF_DEFAULT_EDGE_GAP
        frame.setProperty('dalgasZoomGapR', gap_r)
        frame.setProperty('dalgasZoomGapB', gap_b)
        home_x = max(0, cw - gap_r - fw)
        home_y = max(0, ch - gap_b - fh)
        cgx, cgy = _dzf_global_xy(canvas)
        vertical_rects = []
        horizontal_rects = []
        for attr, rects in ((DZF_AVOIDERS_ATTR, vertical_rects),
                            (DZH_AVOIDERS_ATTR, horizontal_rects)):
            avoiders = _dzf_list(attr)
            alive = []
            for avoider in avoiders:
                try:
                    visible = bool(_v(avoider, 'isVisible', False))
                    alive.append(avoider)
                except Exception:
                    continue
                if not visible or not _dzf_on_canvas(avoider, canvas):
                    continue
                try:
                    ax, ay = _dzf_global_xy(avoider)
                except Exception:
                    continue
                aw = _int(avoider, 'width')
                ah = _int(avoider, 'height')
                if aw <= 0 or ah <= 0:
                    continue
                left = ax - cgx
                top = ay - cgy
                if left >= cw or left + aw <= 0 or top >= ch or top + ah <= 0:
                    continue
                rects.append((left, top, aw, ah))
            avoiders[:] = alive
        target_x = home_x
        target_y = home_y
        for _round in range(len(vertical_rects) + len(horizontal_rects) + 1):
            moved = False
            for left, top, aw, ah in vertical_rects:
                if (left >= target_x + fw or left + aw <= target_x
                        or top >= target_y + fh or top + ah <= target_y):
                    continue
                new_y = top - fh - DZF_GAP
                if new_y < target_y:
                    target_y = new_y
                    moved = True
            for left, top, aw, ah in horizontal_rects:
                if (left >= target_x + fw or left + aw <= target_x
                        or top >= target_y + fh or top + ah <= target_y):
                    continue
                new_x = left - fw - DZF_GAP
                if new_x < target_x:
                    target_x = new_x
                    moved = True
            if not moved:
                break
        target_x = max(0, target_x)
        target_y = max(0, target_y)
        if x != target_x or y != target_y:
            frame.move(target_x, target_y)
        frame.setProperty('dalgasZoomSetX', target_x)
        frame.setProperty('dalgasZoomSetY', target_y)
        frame.setProperty('dalgasSideZoomGapR', gap_r)
        frame.setProperty('dalgasSideZoomSetX', target_x)
    except Exception:
        pass


def pp_zoom_sync_later(canvas):
    if canvas is None:
        return
    try:
        QtCore.QTimer.singleShot(0, lambda: pp_zoom_sync(canvas))
    except Exception:
        pass


def pp_zoom_restore_if_running(canvas):
    try:
        if bool(_v(QtGui.QApplication, 'closingDown', False)):
            return
    except Exception:
        pass
    pp_zoom_sync(canvas)



# ============================================================
# Glyph outline Path (detached path approach of Set_Shape_Order_GUI v5.81)
# ============================================================
def pp_is_sticker(shape):
    try:
        return 'Sticker' in str(shape.shapeType)
    except Exception:
        return False


_PP_NONE_CONTOURS = [0]   # cumulative count of Contours read as None because they were not loaded


def _pp_direct_contours(shape):
    contours = []
    try:
        shape_data = _v(shape, 'shapeData')
        contours = list(_v(shape_data, 'contours') or [])
    except Exception:
        contours = []
    if not contours:
        try:
            contours = list(_v(shape, 'contours') or [])
        except Exception:
            contours = []
    # A None element is a Contour of a glyph FontLab has not loaded yet. Count it instead of skipping silently.
    missing = sum(1 for c in contours if c is None)
    if missing:
        _PP_NONE_CONTOURS[0] += missing
    return contours


def pp_warm_fg_glyph(font, glyph_name):
    """Reads the glyph's fg (fontgate) data once, down to the nodes, on all layers (read-only).
    After this, the flGlyph obtained has non-None Contours even for a glyph that was not loaded."""
    try:
        fg_glyph = font[glyph_name]
    except Exception:
        fg_glyph = None
    if fg_glyph is None:
        return
    try:
        layers = list(fg_glyph.layers)
    except Exception:
        return
    for fg_layer in layers:
        try:
            shapes = list(fg_layer.shapes)
        except Exception:
            continue
        for fg_shape in shapes:
            try:
                contours = fg_shape.contours
                count = len(contours)
            except Exception:
                continue
            for index in range(count):
                try:
                    contour = contours[index]
                except Exception:
                    continue
                if contour is None:
                    continue
                try:
                    nodes = contour.nodes() if callable(contour.nodes) else contour.nodes
                    if nodes is not None:
                        len(nodes)
                except Exception:
                    pass


def pp_component_glyph_names(fl_glyph):
    """Source glyph names of Components on all layers of the glyph (TypeRig pGlyph.components approach)."""
    names = []
    try:
        layers = list(fl_glyph.layers)
    except Exception:
        return names
    for layer in layers:
        try:
            shapes = list(layer.shapes)
        except Exception:
            continue
        for shape in shapes:
            try:
                shape_data = shape.shapeData
                if not shape_data.isComponent:
                    continue
                name = str(shape_data.componentGlyph or '')
            except Exception:
                continue
            if name and name not in names:
                names.append(name)
    return names


def _pp_new_path():
    path = QtGui.QPainterPath()
    path.setFillRule(QtCore.Qt.WindingFill)
    return path


def _pp_contours_path(contours):
    """Builds a detached flShape from a list of duplicated Contours and returns its closedPath."""
    detached = fl6.flShape()
    for contour in contours:
        detached.addContour(contour, True)
    detached.ensurePaths()
    return QtGui.QPainterPath(detached.closedPath)


def _pp_shape_has_delta_filter(shape):
    try:
        builder = _v(shape, 'shapeBuilder', None)
        if builder is None:
            return False
        return str(_v(builder, 'title', '') or '') == 'Delta'
    except Exception:
        return False


def pp_build_shape_path(shape):
    """Full Path of a Shape including Live Offset and recursively included Shapes."""
    try:
        shape.ensurePaths()
    except Exception:
        pass
    transform = shape.transform
    own = _pp_contours_path(
        [c.clone() for c in _pp_direct_contours(shape) if c is not None])
    path = _pp_new_path()
    path.addPath(transform.map(own))
    # The own outline of a Delta Shape is already the Delta result (adding the original would draw it twice).
    if _pp_shape_has_delta_filter(shape) and not path.isEmpty():
        return path
    for child in (c for c in (_v(shape, 'includesList') or []) if c is not None):
        path.addPath(transform.map(pp_build_shape_path(child)))
    return path


def pp_layer_advance(layer):
    for name in ('advanceWidth', 'advance'):
        value = _v(layer, name, None)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            pass
        try:
            return float(_v(value, 'x'))
        except Exception:
            continue
    return 0.0


def pp_layer_vadvance(layer):
    """Vertical Advance of the layer (OTF vmtx). (value, path read) — (None, None) if it cannot be read."""
    value = _v(layer, 'advanceHeight', None)
    if value is not None:
        try:
            number = float(value)
            if number > 0:
                return number, 'advanceHeight'
        except Exception:
            pass
    point = _v(layer, 'advance', None)
    if point is not None:
        try:
            number = float(_v(point, 'y'))
            if number > 0:
                return number, 'advance.y'
        except Exception:
            pass
    return None, None


# ============================================================
# Vertical metrics (vmtx/VORG) of the font's source file (OTF/TTF)
#   FontLab does not put vmtx into layers when opening an OTF (diagnosis: layer vertical Advance could not be read),
#   so the source file is read directly (parses the sfnt binary directly instead of fontTools). Read only once per file path and modification time.
# ============================================================
PP_VMETRIC_EXTS = ('.otf', '.ttf', '.otc', '.ttc')
_PP_FILE_VMETRICS = {}     # path → {'mtime', 'data' (None = unreadable), 'status'}


def pp_font_file_path(font):
    """Path of the font's source file (fgFont.path, or flPackage.path if missing)."""
    candidates = [lambda: _v(font, 'path')]
    try:
        package = fl6.flPackage(font)
        candidates.append(lambda: _v(package, 'path'))
    except Exception:
        pass
    for reader in candidates:
        try:
            value = _qstring_to_text(reader())
        except Exception:
            continue
        if value:
            return value
    return ''


def _pp_sfnt_tables(blob):
    """sfnt table locations {tag: (offset, length)}. For TTC/OTC reads the first font."""
    base = 0
    if blob[:4] == b'ttcf':
        base = struct.unpack('>I', blob[12:16])[0]
    count = struct.unpack('>H', blob[base + 4:base + 6])[0]
    tables = {}
    for index in range(count):
        record = base + 12 + index * 16
        tag = blob[record:record + 4].decode('latin-1')
        offset, length = struct.unpack('>II', blob[record + 8:record + 16])
        tables[tag] = (offset, length)
    return tables


def _pp_cff_index(blob, pos):
    """CFF INDEX → ([item bytes], next position)."""
    count = struct.unpack('>H', blob[pos:pos + 2])[0]
    if count == 0:
        return [], pos + 2
    off_size = blob[pos + 2]
    offsets = []
    start = pos + 3
    for index in range(count + 1):
        value = 0
        for byte in blob[start + index * off_size:start + (index + 1) * off_size]:
            value = (value << 8) | byte
        offsets.append(value)
    data = start + (count + 1) * off_size - 1
    items = [blob[data + offsets[i]:data + offsets[i + 1]] for i in range(count)]
    return items, data + offsets[-1]


def _pp_cff_dict(data):
    """CFF DICT → {operator: [operands]}. 12 x operators are 1200 + x."""
    result = {}
    operands = []
    pos = 0
    while pos < len(data):
        b0 = data[pos]
        if b0 <= 21:
            if b0 == 12:
                pos += 1
                op = 1200 + data[pos]
            else:
                op = b0
            result[op] = operands
            operands = []
            pos += 1
        elif b0 == 28:
            operands.append(struct.unpack('>h', data[pos + 1:pos + 3])[0])
            pos += 3
        elif b0 == 29:
            operands.append(struct.unpack('>i', data[pos + 1:pos + 5])[0])
            pos += 5
        elif b0 == 30:
            pos += 1
            while pos < len(data):
                byte = data[pos]
                pos += 1
                if (byte & 0x0F) == 0x0F or (byte >> 4) == 0x0F:
                    break
            operands.append(0)
        elif 32 <= b0 <= 246:
            operands.append(b0 - 139)
            pos += 1
        elif 247 <= b0 <= 250:
            operands.append((b0 - 247) * 256 + data[pos + 1] + 108)
            pos += 2
        elif 251 <= b0 <= 254:
            operands.append(-(b0 - 251) * 256 - data[pos + 1] - 108)
            pos += 2
        else:
            pos += 1
    return result


def _pp_cff_names(blob, offset, num_glyphs):
    """CFF glyph names {name: GID}. CID fonts use the cid00000 form; name-keyed fonts read only custom strings (SID ≥ 391)
    (standard string names are found via cmap Unicode)."""
    header_size = blob[offset + 2]
    pos = offset + header_size
    _names, pos = _pp_cff_index(blob, pos)
    top_dicts, pos = _pp_cff_index(blob, pos)
    strings, pos = _pp_cff_index(blob, pos)
    if not top_dicts:
        return {}
    top = _pp_cff_dict(top_dicts[0])
    is_cid = 1230 in top
    charset_offset = (top.get(15) or [0])[0]
    if charset_offset in (0, 1, 2):
        return {}
    ids = [0]
    pos = offset + charset_offset
    fmt = blob[pos]
    pos += 1
    if fmt == 0:
        for _index in range(num_glyphs - 1):
            ids.append(struct.unpack('>H', blob[pos:pos + 2])[0])
            pos += 2
    else:
        while len(ids) < num_glyphs:
            first = struct.unpack('>H', blob[pos:pos + 2])[0]
            if fmt == 1:
                left = blob[pos + 2]
                pos += 3
            else:
                left = struct.unpack('>H', blob[pos + 2:pos + 4])[0]
                pos += 4
            ids.extend(range(first, first + left + 1))
    names = {}
    for gid, value in enumerate(ids[:num_glyphs]):
        if is_cid:
            names['cid%05d' % value] = gid
        elif value >= 391 and value - 391 < len(strings):
            names[strings[value - 391].decode('latin-1')] = gid
    return names


def _pp_post_names(blob, offset, num_glyphs):
    """TrueType post 2.0 glyph names {name: GID} (custom names only; standard Mac names are found via cmap)."""
    if struct.unpack('>I', blob[offset:offset + 4])[0] != 0x00020000:
        return {}
    count = struct.unpack('>H', blob[offset + 32:offset + 34])[0]
    pos = offset + 34
    indexes = struct.unpack('>%dH' % count, blob[pos:pos + 2 * count])
    pos += 2 * count
    custom = []
    while len(custom) < max([0] + [i - 257 for i in indexes]):
        length = blob[pos]
        custom.append(blob[pos + 1:pos + 1 + length].decode('latin-1'))
        pos += 1 + length
    names = {}
    for gid, index in enumerate(indexes[:num_glyphs]):
        if index >= 258 and index - 258 < len(custom):
            names[custom[index - 258]] = gid
    return names


def _pp_cmap_unicodes(blob, offset):
    """cmap → {Unicode: GID}. Reads (3,10)/(0,4~6) format 12 first, otherwise (3,1)/(0,x) format 4."""
    count = struct.unpack('>H', blob[offset + 2:offset + 4])[0]
    subtables = []
    for index in range(count):
        record = offset + 4 + index * 8
        platform, encoding, sub_offset = struct.unpack('>HHI', blob[record:record + 8])
        fmt = struct.unpack('>H', blob[offset + sub_offset:offset + sub_offset + 2])[0]
        subtables.append((platform, encoding, fmt, offset + sub_offset))
    chosen = None
    for want in (12, 4):
        for platform, encoding, fmt, pos in subtables:
            if fmt == want and (platform == 0 or (platform == 3 and encoding in (1, 10))):
                chosen = (fmt, pos)
                break
        if chosen:
            break
    result = {}
    if chosen is None:
        return result
    fmt, pos = chosen
    if fmt == 12:
        groups = struct.unpack('>I', blob[pos + 12:pos + 16])[0]
        for index in range(groups):
            start, end, gid = struct.unpack('>III', blob[pos + 16 + index * 12:pos + 28 + index * 12])
            for code in range(start, end + 1):
                result[code] = gid + code - start
        return result
    seg_count = struct.unpack('>H', blob[pos + 6:pos + 8])[0] // 2
    ends = struct.unpack('>%dH' % seg_count, blob[pos + 14:pos + 14 + 2 * seg_count])
    starts_pos = pos + 16 + 2 * seg_count
    starts = struct.unpack('>%dH' % seg_count, blob[starts_pos:starts_pos + 2 * seg_count])
    deltas_pos = starts_pos + 2 * seg_count
    deltas = struct.unpack('>%dh' % seg_count, blob[deltas_pos:deltas_pos + 2 * seg_count])
    ranges_pos = deltas_pos + 2 * seg_count
    ranges = struct.unpack('>%dH' % seg_count, blob[ranges_pos:ranges_pos + 2 * seg_count])
    for seg in range(seg_count):
        for code in range(starts[seg], ends[seg] + 1):
            if code == 0xFFFF:
                continue
            if ranges[seg] == 0:
                gid = (code + deltas[seg]) & 0xFFFF
            else:
                at = ranges_pos + seg * 2 + ranges[seg] + (code - starts[seg]) * 2
                gid = struct.unpack('>H', blob[at:at + 2])[0]
                if gid:
                    gid = (gid + deltas[seg]) & 0xFFFF
            if gid:
                result[code] = gid
    return result


def _pp_load_file_vmetrics(path):
    """(data, status). FontLab has no fontTools, so the sfnt binary is read directly.
    data = {'path', 'gid_vmtx': [(advance, tsb)], 'names': {name: GID}, 'unicodes': {Unicode: GID},
    'vorg': {GID: y}|None, 'vorg_default'}."""
    try:
        with open(path, 'rb') as handle:
            blob = handle.read()
    except Exception as error:
        return None, 'Could not open file: %s' % error
    try:
        tables = _pp_sfnt_tables(blob)
        if 'vmtx' not in tables or 'vhea' not in tables or 'maxp' not in tables:
            return None, 'No vmtx/vhea in file'
        num_glyphs = struct.unpack('>H', blob[tables['maxp'][0] + 4:tables['maxp'][0] + 6])[0]
        vhea = tables['vhea'][0]
        long_count = struct.unpack('>H', blob[vhea + 34:vhea + 36])[0]
        pos = tables['vmtx'][0]
        gid_vmtx = []
        advance = 0
        for gid in range(num_glyphs):
            if gid < long_count:
                advance, tsb = struct.unpack('>Hh', blob[pos:pos + 4])
                pos += 4
            else:
                tsb = struct.unpack('>h', blob[pos:pos + 2])[0]
                pos += 2
            gid_vmtx.append((advance, tsb))
        vorg = None
        vorg_default = None
        if 'VORG' in tables:
            at = tables['VORG'][0]
            vorg_default, records = struct.unpack('>hH', blob[at + 4:at + 8])
            vorg = {}
            for index in range(records):
                gid, value = struct.unpack('>Hh', blob[at + 8 + index * 4:at + 12 + index * 4])
                vorg[gid] = value
        names = {}
        name_source = 'cmap'
        try:
            if 'CFF ' in tables:
                names = _pp_cff_names(blob, tables['CFF '][0], num_glyphs)
                name_source = 'CFF charset + cmap'
            elif 'post' in tables:
                names = _pp_post_names(blob, tables['post'][0], num_glyphs)
                name_source = 'post + cmap'
        except Exception as error:
            print('%s Source file glyph name read error: %s' % (PP_LOG, error))
            names = {}
        unicodes = {}
        if 'cmap' in tables:
            try:
                unicodes = _pp_cmap_unicodes(blob, tables['cmap'][0])
            except Exception as error:
                print('%s Source file cmap read error: %s' % (PP_LOG, error))
        return ({'path': path, 'gid_vmtx': gid_vmtx, 'names': names, 'unicodes': unicodes,
                 'vorg': vorg, 'vorg_default': vorg_default},
                'vmtx %d%s, glyph names %d (%s)' % (len(gid_vmtx), ', VORG' if vorg is not None else '',
                                                 len(names), name_source))
    except Exception as error:
        return None, 'vmtx/VORG read error: %s' % error


def _pp_file_vmetrics_entry(font):
    path = pp_font_file_path(font)
    if not path:
        return None, 'No font file path'
    if not path.lower().endswith(PP_VMETRIC_EXTS):
        return None, 'Source is not an OTF/TTF file: %s' % os.path.basename(path)
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        return None, 'File not found: %s' % path
    entry = _PP_FILE_VMETRICS.get(path)
    if entry is None or entry['mtime'] != mtime:
        data, status = _pp_load_file_vmetrics(path)
        entry = {'mtime': mtime, 'data': data, 'status': status}
        _PP_FILE_VMETRICS[path] = entry
        print('%s Source file vertical metrics read: %s — %s' % (PP_LOG, os.path.basename(path), status))
    return entry, entry['status']


def pp_font_file_vmetrics(font):
    """Vertical metrics of the source file (None if missing or unreadable)."""
    try:
        entry, _status = _pp_file_vmetrics_entry(font)
    except Exception:
        return None
    return entry['data'] if entry is not None else None


def pp_font_file_vmetrics_status(font):
    try:
        return _pp_file_vmetrics_entry(font)[1]
    except Exception as error:
        return 'Error: %s' % error


# ============================================================
# Reading OpenType vertical writing (vert/vrt2) feature code
#   The panel draws outlines directly without a shaping engine, so single substitutions in the FEA code are applied directly.
# ============================================================
_PP_FEA_COMMENT = re.compile(r'#[^\n]*')
_PP_FEA_LOOKUP_DEF = re.compile(
    r'\blookup\s+([A-Za-z_][\w.\-]*)\s*(?:useExtension\s*)?\{(.*?)\}\s*\1\s*;', re.S)
_PP_FEA_LOOKUP_REF = re.compile(r'\blookup\s+([A-Za-z_][\w.\-]*)\s*;')
_PP_FEA_CLASS_DEF = re.compile(r'(@[\w.\-]+)\s*=\s*\[([^\]]*)\]\s*;')
_PP_FEA_SUB = re.compile(r'\bsub(?:stitute)?\s+([^;]*?)\s+by\s+([^;]*?)\s*;', re.S)
_PP_FEA_ITEM = re.compile(r'^(@[\w.\-]+|\[[^\]]*\]|\\?[\w.\-]+)$')
_PP_FEA_RANGE = re.compile(r'^([A-Za-z_.]*?)(\d+)-\1(\d+)$')
_PP_FEA_CID_RANGE = re.compile(r'^\\(\d+)-\\(\d+)$')


def _pp_fea_name(token):
    """FEA glyph name token → glyph name. CID numbers (\\1086) become the cid01086 form."""
    token = token.strip()
    if token.startswith('\\'):
        token = token[1:]
    if token.isdigit():
        return 'cid%05d' % int(token)
    return token


def _pp_fea_class_items(body, classes):
    """Expands the contents inside brackets into a list of glyph names (including class references and ranges)."""
    tokens = body.split()
    names = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == '-':
            token = token + '-' + tokens[index + 2]
            index += 2
        index += 1
        if token.startswith('@'):
            names.extend(classes.get(token, []))
            continue
        match = _PP_FEA_CID_RANGE.match(token)
        if match:
            low, high = int(match.group(1)), int(match.group(2))
            if 0 <= high - low <= 70000:
                names.extend('cid%05d' % n for n in range(low, high + 1))
            continue
        match = _PP_FEA_RANGE.match(token.lstrip('\\'))
        if match and len(match.group(2)) == len(match.group(3)):
            prefix, width = match.group(1), len(match.group(2))
            low, high = int(match.group(2)), int(match.group(3))
            if 0 <= high - low <= 70000:
                names.extend('%s%0*d' % (prefix, width, n) for n in range(low, high + 1))
                continue
        names.append(_pp_fea_name(token))
    return names


def _pp_fea_item(text, classes):
    """One side of a sub statement (one glyph / @class / [...]) → list of glyph names. None if several items (ligatures etc.)."""
    text = text.strip()
    if not _PP_FEA_ITEM.match(text):
        return None
    if text.startswith('@'):
        return list(classes.get(text, []))
    if text.startswith('['):
        return _pp_fea_class_items(text[1:-1], classes)
    return [_pp_fea_name(text)]


def _pp_fea_subs(body, classes, mapping):
    """Puts the body's single substitutions into mapping (glyphs already present are not changed). Returns the number of pairs added."""
    added = 0
    for match in _PP_FEA_SUB.finditer(body):
        left, right = match.group(1), match.group(2)
        if "'" in left or "'" in right or right.strip() == 'NULL':
            continue
        sources = _pp_fea_item(left, classes)
        targets = _pp_fea_item(right, classes)
        if not sources or not targets:
            continue
        if len(targets) == 1:
            targets = targets * len(sources)
        elif len(targets) != len(sources):
            continue
        for source, target in zip(sources, targets):
            if source and target and source not in mapping:
                mapping[source] = target
                added += 1
    return added


def pp_feature_sources(font):
    """FEA code of the Features panel. (prefix, {tag: code}) — same path as TypeRig pFont.getFeature."""
    prefix = ''
    codes = {}
    try:
        features = font.features
    except Exception:
        features = None
    if features is None:
        return prefix, codes
    for reader in (lambda: features.get_prefix(), lambda: _v(features, 'prefix')):
        try:
            value = _qstring_to_text(reader())
            if value:
                prefix = value
                break
        except Exception:
            continue
    tags = []
    for reader in (lambda: features.keys(), lambda: features.tags()):
        try:
            tags = [str(tag) for tag in list(reader() or [])]
            break
        except Exception:
            continue
    for tag in tags:
        for reader in (lambda t=tag: features.get_feature(t), lambda t=tag: features[t]):
            try:
                value = reader()
            except Exception:
                continue
            if value is not None:
                codes[tag] = _qstring_to_text(value)
                break
    return prefix, codes


_PP_FEA_NAMES_BLOCK = re.compile(r'\bfeatureNames\s*\{(.*?)\}\s*;', re.S)
_PP_FEA_NAME_STR = re.compile(r'\bname\s+[^";]*?"([^"]*)"')


def pp_build_vert_map(font):
    """{horizontal glyph name: vertical glyph name} and a summary for output. vert first, missing glyphs filled from vrt2.
    Applies the first stylistic set (ss01~ss20) whose name (featureNames) contains 'Vertical' after vert
    (GSUB order: stylistic set substitution applied on top of the vert result glyphs).
    Returns (vert substitution, stylistic set substitution, summary). PPFontCache chains the two substitutions."""
    prefix, codes = pp_feature_sources(font)
    texts = [prefix] + [codes[tag] for tag in codes]
    full = _PP_FEA_COMMENT.sub('', u'\n'.join(text for text in texts if text))
    classes = {}
    for match in _PP_FEA_CLASS_DEF.finditer(full):
        classes[match.group(1)] = _pp_fea_class_items(match.group(2), classes)
    lookups = {}
    for match in _PP_FEA_LOOKUP_DEF.finditer(full):
        lookups.setdefault(match.group(1), match.group(2))

    def feature_body(tag):
        code = _PP_FEA_COMMENT.sub('', codes.get(tag) or '')
        block = re.compile(r'\bfeature\s+%s\s*\{(.*?)\}\s*%s\s*;' % (tag, tag), re.S)
        found = block.search(code) if code else None
        if found is None:
            found = block.search(full)
        if found is not None:
            return found.group(1)
        return code if code.strip() else None

    def feature_subs(body, mapping):
        names_free = _PP_FEA_NAMES_BLOCK.sub('', body)
        added = _pp_fea_subs(names_free, classes, mapping)
        for name in _PP_FEA_LOOKUP_REF.findall(names_free):
            if name in lookups:
                added += _pp_fea_subs(lookups[name], classes, mapping)
        return added

    mapping = {}
    counts = []
    for tag in ('vert', 'vrt2'):
        body = feature_body(tag)
        if body is None:
            continue
        counts.append('%s %d' % (tag, feature_subs(body, mapping)))
    if not counts:
        counts.append('no vert/vrt2 (Features tags: %s)' % (', '.join(sorted(codes.keys())) or 'unreadable'))
    # vertical writing stylistic set (Vertical in the name) — the one set with the lowest number
    ss_seen = []
    ss_tag = None
    ss_map = {}
    for number in range(1, 21):
        tag = 'ss%02d' % number
        body = feature_body(tag)
        if body is None:
            continue
        label = ''
        names = _PP_FEA_NAMES_BLOCK.search(body)
        if names is not None:
            strings = _PP_FEA_NAME_STR.findall(names.group(1))
            label = strings[0] if strings else ''
        ss_seen.append('%s "%s"' % (tag, label) if label else tag)
        if ss_tag is None and 'vertical' in label.lower():
            ss_tag = tag
            feature_subs(body, ss_map)
    if ss_tag is not None:
        counts.append('%s %d (Vertical stylistic set)' % (ss_tag, len(ss_map)))
    else:
        counts.append('no Vertical stylistic set (stylistic sets: %s)' % (', '.join(ss_seen) or 'none'))
    # vert and stylistic set substitutions are returned separately, not merged (rotated characters get only the stylistic set, without vert).
    return mapping, ss_map, ', '.join(counts)


def pp_layer_shapes(layer, with_contours_only=False):
    result = []
    try:
        for shape in list(layer.shapes):
            if pp_is_sticker(shape):
                continue
            if with_contours_only:
                try:
                    if len(shape.contours) <= 0:
                        continue
                except Exception:
                    continue
            result.append(shape)
    except Exception:
        pass
    return result


def pp_get_layer(fl_glyph, name):
    """Reads a layer by master name (same getLayerByName path as TypeRig pGlyph.layer())."""
    if fl_glyph is None or not name:
        return None
    try:
        layer = fl_glyph.getLayerByName(name)
        if layer is not None:
            return layer
    except Exception:
        pass
    try:
        for layer in list(fl_glyph.layers):
            if str(_v(layer, 'name', '') or '') == name:
                return layer
    except Exception:
        pass
    return None


def pp_layer_paths(layer):
    paths = []
    for shape in pp_layer_shapes(layer):
        try:
            paths.append(pp_build_shape_path(shape))
        except Exception as error:
            print('%s Path creation error: %s' % (PP_LOG, error))
    return paths


# ============================================================
# Interpolation (interpolation code of Set_Shape_Order_GUI v5.81)
# ============================================================
def _pp_interp_transform(trans_a, trans_b, t):
    values = []
    for name in ('m11', 'm12', 'm21', 'm22', 'dx', 'dy'):
        va = float(_v(trans_a, name, 0.0))
        vb = float(_v(trans_b, name, 0.0))
        values.append(va + (vb - va) * t)
    return QtGui.QTransform(*values)


try:
    from typerig.proxy.fl.objects.node import pNode as _PP_pNode
except Exception:
    _PP_pNode = None


def _pp_set_node_xy(node, x, y):
    if _PP_pNode is not None:
        try:
            _PP_pNode(node).reloc(x, y)
            return
        except Exception:
            pass
    node.x = x
    node.y = y


def _pp_node_is_on(node):
    value = _v(node, 'isOn', None)
    if isinstance(value, bool):
        return value
    return _v(node, 'type', None) == 'on'


def _pp_contour_segments(contour):
    """Splits a closed Contour into a list of segments (start point, [handles...], end point)."""
    points = []
    for node in list(_v(contour, 'nodes', []) or []):
        points.append((float(_v(node, 'x', 0.0)),
                       float(_v(node, 'y', 0.0)),
                       _pp_node_is_on(node)))
    first = next((i for i, p in enumerate(points) if p[2]), None)
    if first is None:
        return None
    points = points[first:] + points[:first]
    segments = []
    start = points[0][:2]
    handles = []
    for point in points[1:] + [points[0]]:
        if point[2]:
            segments.append((start, handles, point[:2]))
            start = point[:2]
            handles = []
        else:
            handles.append(point[:2])
    return segments


def _pp_segment_as_cubic(segment):
    p0, handles, p3 = segment
    if len(handles) >= 2:
        return p0, handles[0], handles[-1], p3, True
    if len(handles) == 1:
        q = handles[0]
        c1 = (p0[0] + (q[0] - p0[0]) * 2.0 / 3.0, p0[1] + (q[1] - p0[1]) * 2.0 / 3.0)
        c2 = (p3[0] + (q[0] - p3[0]) * 2.0 / 3.0, p3[1] + (q[1] - p3[1]) * 2.0 / 3.0)
        return p0, c1, c2, p3, True
    c1 = (p0[0] + (p3[0] - p0[0]) / 3.0, p0[1] + (p3[1] - p0[1]) / 3.0)
    c2 = (p0[0] + (p3[0] - p0[0]) * 2.0 / 3.0, p0[1] + (p3[1] - p0[1]) * 2.0 / 3.0)
    return p0, c1, c2, p3, False


def _pp_lerp_point(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _pp_segment_interp_path(contours_a, contours_b, t):
    path = _pp_new_path()
    for contour_a, contour_b in zip(contours_a, contours_b):
        segments_a = _pp_contour_segments(contour_a)
        segments_b = _pp_contour_segments(contour_b)
        if not segments_a or not segments_b or len(segments_a) != len(segments_b):
            return None
        start = _pp_lerp_point(segments_a[0][0], segments_b[0][0], t)
        path.moveTo(start[0], start[1])
        for seg_a, seg_b in zip(segments_a, segments_b):
            a0, a1, a2, a3, curve_a = _pp_segment_as_cubic(seg_a)
            b0, b1, b2, b3, curve_b = _pp_segment_as_cubic(seg_b)
            end = _pp_lerp_point(a3, b3, t)
            if not curve_a and not curve_b:
                path.lineTo(end[0], end[1])
            else:
                c1 = _pp_lerp_point(a1, b1, t)
                c2 = _pp_lerp_point(a2, b2, t)
                path.cubicTo(c1[0], c1[1], c2[0], c2[1], end[0], end[1])
        path.closeSubpath()
    return path


def pp_interp_shape_path(shape_a, shape_b, t):
    """Path linearly interpolating the node coordinates and transforms of two master Shapes. None if incompatible."""
    for shape in (shape_a, shape_b):
        try:
            shape.ensurePaths()
        except Exception:
            pass
    contours_a = [c for c in _pp_direct_contours(shape_a) if c is not None]
    contours_b = [c for c in _pp_direct_contours(shape_b) if c is not None]
    if not contours_a or len(contours_a) != len(contours_b):
        return None
    same_structure = True
    for contour_a, contour_b in zip(contours_a, contours_b):
        nodes_a = list(_v(contour_a, 'nodes', []) or [])
        nodes_b = list(_v(contour_b, 'nodes', []) or [])
        if not nodes_a or len(nodes_a) != len(nodes_b):
            same_structure = False
            break
    if same_structure:
        clones = []
        for contour_a, contour_b in zip(contours_a, contours_b):
            clone = contour_a.clone()
            nodes_c = list(_v(clone, 'nodes', []) or [])
            nodes_b = list(_v(contour_b, 'nodes', []) or [])
            for node_c, node_b in zip(nodes_c, nodes_b):
                xa = float(_v(node_c, 'x', 0.0))
                ya = float(_v(node_c, 'y', 0.0))
                xb = float(_v(node_b, 'x', 0.0))
                yb = float(_v(node_b, 'y', 0.0))
                _pp_set_node_xy(node_c, xa + (xb - xa) * t, ya + (yb - ya) * t)
            clones.append(clone)
        own_path = _pp_contours_path(clones)
    else:
        own_path = _pp_segment_interp_path(contours_a, contours_b, t)
        if own_path is None:
            return None
    transform = _pp_interp_transform(shape_a.transform, shape_b.transform, t)
    path = _pp_new_path()
    path.addPath(transform.map(own_path))
    if ((_pp_shape_has_delta_filter(shape_a) or _pp_shape_has_delta_filter(shape_b))
            and not path.isEmpty()):
        return path
    includes_a = [c for c in (_v(shape_a, 'includesList') or []) if c is not None]
    includes_b = [c for c in (_v(shape_b, 'includesList') or []) if c is not None]
    if len(includes_a) != len(includes_b):
        return None
    for child_a, child_b in zip(includes_a, includes_b):
        child_path = pp_interp_shape_path(child_a, child_b, t)
        if child_path is None:
            return None
        path.addPath(transform.map(child_path))
    return path


def pp_instance_axis_weight(instance):
    """Reads the Weight axis position of an instance (Location 'wt=' in Font Info > Instances)."""
    try:
        location = instance.location
        if callable(location):
            location = location()
    except Exception:
        location = None
    if location is not None:
        for key in ('wt', 'wght', 'weight', 'Weight'):
            try:
                return float(location[key])
            except Exception:
                continue
        try:
            match = _PP_LOCATION_WT_RE.search(repr(location))
            if match:
                return float(match.group(1))
        except Exception:
            pass
    try:
        value = getattr(instance, 'weightValue')
        value = value() if callable(value) else value
        return float(value)
    except Exception:
        return None


def pp_location_dict(location):
    """Reads an axis location (flLocation) as {axis tag (lowercase): value}. Empty dict if unreadable."""
    if location is None:
        return {}
    try:
        if callable(location):
            location = location()
    except Exception:
        return {}
    result = {}
    try:
        for key in list(location.keys()):
            try:
                result[str(key).lower()] = float(location[key])
            except Exception:
                continue
    except Exception:
        result = {}
    if result:
        return result
    for reader in (repr, str):
        try:
            text = reader(location)
        except Exception:
            continue
        for match in _PP_LOCATION_ITEM_RE.finditer(text or ''):
            try:
                result[match.group(1).lower()] = float(match.group(2))
            except Exception:
                continue
        if result:
            break
    return result


def pp_location_weight_key(location_dict):
    """Finds the Weight axis tag in an axis location dict (None if absent)."""
    for key in PP_WEIGHT_AXIS_KEYS:
        if key in location_dict:
            return key
    return None


def pp_location_others(location_dict, weight_key):
    """Axis location excluding the Weight axis (tuple for comparison)."""
    return tuple(sorted((key, round(float(value), 4))
                        for key, value in location_dict.items() if key != weight_key))


def pp_instance_raw_specs(font):
    """Reads Font Info > Instances in registration order as is (excludes only '#' temporary instances, keeps duplicates)."""
    try:
        package = fl6.flPackage(font)
        instances = list(package.instances)
    except Exception:
        return []
    specs = []
    for instance in instances:
        label = str(getattr(instance, 'tsn', '') or getattr(instance, 'name', '') or '')
        if label.strip().startswith('#'):
            continue
        weight = pp_instance_axis_weight(instance)
        try:
            location = instance.location
            if callable(location):
                location = location()
        except Exception:
            location = None
        try:
            location_repr = repr(location) if location is not None else ''
        except Exception:
            location_repr = ''
        specs.append({'label': label, 'weight': weight, 'location_repr': location_repr,
                      'loc': pp_location_dict(location),
                      'loc_obj': location})   # the instance's own axis location (used as is in FontLab 9)
    return specs


def pp_instance_specs(font, group=None):
    """Reads Font Info > Instances in registration order as is (excludes '#' temporary instances and duplicates at the same location).
    If group (result of PPFontCache.weight_group) is given, selects only instances whose non-Weight axis values match
    that group. If there is no such instance, all instances are used."""
    raw = pp_instance_raw_specs(font)
    if group is not None:
        weight_key, others = group[0], group[1]
        matched = [spec for spec in raw
                   if spec['loc'] and pp_location_others(spec['loc'], weight_key) == others]
        if matched:
            raw = matched
    specs = []
    seen = set()
    for spec in raw:
        weight = spec['weight']
        if weight is not None:
            key = round(weight, 4)
            if key in seen:
                continue
            seen.add(key)
        specs.append(spec)
    return specs


def pp_instance_specs_at(font, weight_key, others):
    """Weight steps for the VARIATIONS panel location. Returns instances whose other axis values equal others, in registration order
    (one per wt). If there is no such instance, returns the wt values of all instances in ascending order."""
    raw = [spec for spec in pp_instance_raw_specs(font) if spec['weight'] is not None]
    matched = [spec for spec in raw
               if spec['loc'] and pp_location_others(spec['loc'], weight_key) == others]
    if matched:
        raw = matched
    else:
        raw = sorted(raw, key=lambda spec: spec['weight'])
    specs = []
    seen = set()
    for spec in raw:
        key = round(spec['weight'], 4)
        if key in seen:
            continue
        seen.add(key)
        specs.append(spec)
    return specs


def pp_instance_all_specs(font, axes=None):
    """For the All Instances preview. From the instances in Font Info > Instances (excluding '#' temporary instances),
    keeps only one of duplicate instances with the same axis location (all axes).
    Sorted in per-axis groups. Instances whose axis values, excluding Weight, from axes (list of axis tags in Font Info > Axes order)
    are equal are grouped; groups with smaller axis values come first, and within a group smaller Weight values come first.
    axes also accepts a list of (axis name, axis tag). The Italic (Slant) axis is used as the outermost group so that
    Plain (axis value 0) always comes first, followed by Italic."""
    specs = []
    seen = set()
    for spec in pp_instance_raw_specs(font):
        if spec['loc']:
            key = tuple(sorted((axis, round(float(value), 4)) for axis, value in spec['loc'].items()))
        elif spec['weight'] is not None:
            key = (('#weight', round(float(spec['weight']), 4)),)
        else:
            key = ('#label', spec['label'])
        if key in seen:
            continue
        seen.add(key)
        spec = dict(spec)
        spec['key'] = key
        specs.append(spec)
    # per-axis group sort (Python's sort is stable, so equal values keep registration order).
    order = []
    italic_axes = []   # Italic/Slant axis tags (lowercase)
    for axis in (axes or []):
        if isinstance(axis, (tuple, list)):
            name, short = str(axis[0] or ''), str(axis[1] or '')
        else:
            name, short = '', str(axis)
        short = short.lower()
        if not short:
            continue
        order.append(short)
        lowered = name.lower()
        if (short in PP_ITALIC_AXIS_KEYS
                or any(word in lowered for word in ('italic', 'slant', 'oblique'))):
            italic_axes.append(short)
    for spec in specs:
        for axis in spec['loc']:
            if axis not in order:
                order.append(axis)
                if axis in PP_ITALIC_AXIS_KEYS:
                    italic_axes.append(axis)
    others = [axis for axis in order if axis not in PP_WEIGHT_AXIS_KEYS and axis not in italic_axes]

    def italic_key(spec):
        """Plain = (0, ...) first, Italic after."""
        loc = spec['loc']
        if italic_axes:
            values = tuple(abs(float(loc.get(axis, 0.0))) for axis in italic_axes)
            return (0 if all(value < 0.0001 for value in values) else 1, values)
        label = (spec.get('label') or '').lower()
        return (1 if ('italic' in label or 'oblique' in label) else 0, ())

    def group_key(spec):
        loc = spec['loc']
        if not loc:
            return (1, italic_key(spec), (), 0.0)   # instances whose axis location could not be read go last (registration order kept)
        weight_key = pp_location_weight_key(loc)
        weight = loc.get(weight_key) if weight_key else spec['weight']
        if weight is None:
            weight = spec['weight'] if spec['weight'] is not None else 0.0
        return (0, italic_key(spec), tuple(float(loc.get(axis, 0.0)) for axis in others), float(weight))

    specs.sort(key=group_key)
    return specs


_PP_LOCATION_FAIL_REPORTED = [False]   # the axis location creation failure error is printed only once.


def _pp_location_matches(location, values):
    """Whether the created axis location matches values ({axis tag: value}). Treated as matching if unreadable."""
    read = pp_location_dict(location)
    if not read:
        return True
    for short, value in values.items():
        got = read.get(str(short).lower())
        if got is None or abs(float(got) - float(value)) > 0.001:
            return False
    return True


def pp_build_location(package, base_master, values, fallback=None):
    """Creates an flLocation with values ({axis tag: value}) put into base_master's axis location. None if it cannot be created.
    (1) FontLab 8 approach (set directly on a copy) (2) fallback (e.g. the instance's own location, used as is)
    (3) build from an axis value dict (4) value setter functions. FontLab 9's flLocation does not support (1)."""
    errors = []
    base = None
    try:
        base = package.location(base_master)
    except Exception as error:
        errors.append('location(%s): %s' % (base_master, error))
    # (1) FontLab 8: sets the axis values directly on a copy (the original master location is not changed).
    if base is not None:
        try:
            location = fl6.flLocation(base)
            for short, value in values.items():
                location[short] = float(value)
            return location
        except Exception as error:
            errors.append('item assignment: %s' % error)
    # (2) A location whose values need no change, such as the instance's own location
    if fallback is not None:
        return fallback
    # (3) Built from an axis value dict (all axes of the master location + values).
    full = {}
    if base is not None:
        try:
            for key in list(base.keys()):
                try:
                    full[str(key)] = float(base[key])
                except Exception:
                    continue
        except Exception:
            pass
        if not full:
            for key, value in pp_location_dict(base).items():
                full[key] = float(value)
    lowered = dict((str(key).lower(), key) for key in full)
    for short, value in values.items():
        key = lowered.get(str(short).lower(), short)
        full[key] = float(value)
    try:
        location = fl6.flLocation(full)
        if _pp_location_matches(location, values):
            return location
        errors.append('flLocation(dict): value mismatch')
    except Exception as error:
        errors.append('flLocation(dict): %s' % error)
    # (4) Value setter functions of the copy
    if base is not None:
        for method_name in ('set', 'setValue', 'setAxisValue', 'setAxis', 'insert', 'update'):
            try:
                location = fl6.flLocation(base)
                method = getattr(location, method_name, None)
                if not callable(method):
                    continue
                if method_name == 'update':
                    method(dict((str(k), float(v)) for k, v in values.items()))
                else:
                    for short, value in values.items():
                        method(short, float(value))
                if _pp_location_matches(location, values):
                    return location
                errors.append('%s(): value mismatch' % method_name)
            except Exception as error:
                errors.append('%s(): %s' % (method_name, error))
    if not _PP_LOCATION_FAIL_REPORTED[0]:
        _PP_LOCATION_FAIL_REPORTED[0] = True
        try:
            names = sorted(name for name in dir(fl6.flLocation) if not name.startswith('_'))
        except Exception:
            names = []
        print('%s Axis location (flLocation) creation error: %s | flLocation functions: %s'
              % (PP_LOG, '; '.join(errors), ', '.join(names)))
    return None


def _pp_type_name(obj):
    try:
        return type(obj).__name__
    except Exception:
        return ''


def _pp_child_widgets(widget):
    result = []
    try:
        for child in (_v(widget, 'children') or []):
            if _v(child, 'isWidgetType', False):
                result.append(child)
    except Exception:
        pass
    return result


def _pp_widget_text(widget):
    try:
        value = widget.property('text')
    except Exception:
        return None
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None


class PPVariationsPanel(object):
    """Reads the current axis values of the VARIATIONS panel (LocationPanel) (read-only, does not change the panel)."""

    def __init__(self):
        self._panel = None
        self._last_scan = 0.0

    def _find_panel(self):
        """Returns the visible panel. None if not found (scans all widgets only once every PP_VAR_RESCAN_SEC)."""
        panel = self._panel
        if panel is not None:
            try:
                if _v(panel, 'isVisible', False):
                    return panel
            except Exception:
                self._panel = None
        now = time.time()
        if now - self._last_scan < PP_VAR_RESCAN_SEC:
            return None
        self._last_scan = now
        self._panel = None
        try:
            app = QtGui.QApplication.instance()
            widgets = list(_v(app, 'allWidgets') or [])
        except Exception:
            widgets = []
        found_hidden = False
        for widget in widgets:
            try:
                if _pp_type_name(widget) != PP_VAR_PANEL_NAME:
                    continue
                if _v(widget, 'isVisible', False):
                    self._panel = widget
                    return widget
                found_hidden = True
            except Exception:
                continue
        if found_hidden:
            return None
        # Search once more by objectName only if not found by class name.
        for widget in widgets:
            try:
                if str(_v(widget, 'objectName', '') or '') != PP_VAR_PANEL_NAME:
                    continue
                if _v(widget, 'isVisible', False):
                    self._panel = widget
                    return widget
            except Exception:
                continue
        return None

    def _axis_rows(self, panel):
        """Reads the axis rows in the panel in screen order as [(axis name text, value text)]."""
        rows = []
        stack = [panel]
        visited = 0
        while stack and visited < 800:
            widget = stack.pop()
            visited += 1
            children = _pp_child_widgets(widget)
            if (_pp_type_name(widget) == PP_VAR_AXIS_WIDGET_NAME
                    or str(_v(widget, 'objectName', '') or '') == PP_VAR_AXIS_WIDGET_NAME):
                label = None
                value = None
                for child in children:
                    name = str(_v(child, 'objectName', '') or '')
                    if name == 'label' and label is None:
                        label = _pp_widget_text(child)
                    elif name == 'value' and value is None:
                        value = _pp_widget_text(child)
                rows.append((label, value))
                continue
            # Children are pushed in reverse to keep screen order (earlier children pop first from the stack).
            stack.extend(reversed(children))
        return rows

    def location(self, axes):
        """axes: [(axis name, axis tag)]. Returns the panel's current location {axis tag: value}.
        None if the panel is missing or hidden, or if the panel's axes do not match this font's axes."""
        if not axes or len(axes) < 2:
            return None
        try:
            panel = self._find_panel()
            if panel is None:
                return None
            rows = self._axis_rows(panel)
        except Exception:
            self._panel = None
            return None
        if len(rows) != len(axes):
            return None
        by_name = {}
        for label, value in rows:
            if label is not None:
                by_name[label.strip().lower()] = value
        result = {}
        for index, (name, short) in enumerate(axes):
            text = by_name.get(str(name).strip().lower())
            if text is None:
                # If the axis name text does not match, use the row at the same index (axis count was confirmed equal above).
                text = rows[index][1]
            try:
                result[short] = float(str(text).replace(',', '.').strip())
            except Exception:
                return None
        return result


_PP_VAR_PANEL = PPVariationsPanel()


def pp_glyph_has_instance_layer(fl_glyph):
    """FontLab creates the '#instance' layer only when masters are compatible (per SSO v5.31)."""
    try:
        for layer in list(fl_glyph.layers):
            name = str(_v(layer, 'name', '') or '')
            if name.strip().lower().startswith('#instance'):
                return True
    except Exception:
        return False
    return False


# ============================================================
# Font info cache (masters, Weight, metrics, Unicode lookup, Path)
# ============================================================
def pp_font_id(font):
    if font is None:
        return None
    for reader in (lambda: font.path, lambda: font.name):
        try:
            value = reader()
            if callable(value):
                value = value()
            if value:
                return str(value)
        except Exception:
            continue
    return str(id(font))


def pp_master_names(font):
    try:
        from typerig.proxy.fl.objects.font import pFont
        names = [n for n in pFont(font).pMasters.names if not str(n).startswith('#')]
        if names:
            return [str(n) for n in names]
    except Exception:
        pass
    try:
        names = [str(m.name) for m in font.masters if not str(m.name).startswith('#')]
        if names:
            return names
    except Exception:
        pass
    return []


def pp_is_hangul(code):
    return (0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F
            or 0xA960 <= code <= 0xA97F or 0xD7B0 <= code <= 0xD7FF)


def pp_is_hanja(code):
    return (0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF
            or 0xF900 <= code <= 0xFAFF or 0x20000 <= code <= 0x3FFFF)


def pp_is_kana(code):
    """Japanese Kana (Hiragana, Katakana, Katakana Phonetic Extensions, half-width Katakana)."""
    return (0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF
            or 0x31F0 <= code <= 0x31FF or 0xFF65 <= code <= 0xFF9F)


def pp_is_cjk_punct(code):
    """Japanese (CJK) punctuation and symbols: CJK Symbols and Punctuation, Halfwidth and Fullwidth Forms, Vertical Forms, CJK Compatibility Forms."""
    return (0x3000 <= code <= 0x303F or 0xFF00 <= code <= 0xFFEF
            or 0xFE10 <= code <= 0xFE1F or 0xFE30 <= code <= 0xFE4F)


def pp_is_cjk_letter(code):
    return pp_is_hangul(code) or pp_is_hanja(code) or pp_is_kana(code)


def pp_is_latin_or_digit(char, kinds=('latin', 'digit')):
    """Whether it is a Latin letter or a digit. Choose 'latin'/'digit' with kinds."""
    if not char or len(char) != 1:
        return False
    try:
        code = ord(char)
    except Exception:
        return False
    if 'digit' in kinds and char.isdigit() and code < 0x0250:
        return True
    if 'latin' in kinds and char.isalpha() and (code < 0x0250 or 0x1E00 <= code <= 0x1EFF):
        return True
    return False


def pp_keep_upright(code, plain=False):
    """Characters not rotated in vertical writing even when R (rotate) is selected.
    With plain (simple rotation R), only Hangul/Han/Kana stay upright and CJK punctuation is rotated too."""
    if plain:
        return pp_is_cjk_letter(code)
    return pp_is_cjk_letter(code) or pp_is_cjk_punct(code)


# Summary table of the Unicode vertical orientation property (UAX #50 Vertical_Orientation).
#   U (upright), Tu (upright, the vertical glyph if any), Tr (the vertical glyph if any, otherwise rotated), R (rotated).
#   Used only for characters not changed into vertical glyphs under underlined R (show the font's settings as is).
PP_VO_UPRIGHT_RANGES = (
    (0x00A7, 0x00A7), (0x00A9, 0x00A9), (0x00AE, 0x00AE), (0x00B1, 0x00B1),
    (0x00BC, 0x00BE), (0x00D7, 0x00D7), (0x00F7, 0x00F7), (0x02EA, 0x02EB),
    (0x1100, 0x11FF), (0x1401, 0x167F), (0x18B0, 0x18FF),
    (0x2016, 0x2016), (0x2020, 0x2021), (0x2030, 0x2031), (0x203B, 0x203C),
    (0x2042, 0x2042), (0x2047, 0x2049), (0x2051, 0x2051), (0x2065, 0x2065),
    (0x20DD, 0x20E0), (0x20E2, 0x20E4), (0x2100, 0x2101), (0x2103, 0x2109),
    (0x210F, 0x210F), (0x2113, 0x2114), (0x2116, 0x2117), (0x211E, 0x2123),
    (0x2125, 0x2125), (0x2127, 0x2127), (0x2129, 0x2129), (0x212E, 0x212E),
    (0x2135, 0x213F), (0x2145, 0x214A), (0x214C, 0x214D), (0x214F, 0x2189),
    (0x218C, 0x218F), (0x221E, 0x221E), (0x2234, 0x2235), (0x2300, 0x2307),
    (0x230C, 0x231F), (0x2322, 0x2328), (0x232B, 0x232B), (0x237D, 0x239A),
    (0x23BE, 0x23CD), (0x23CF, 0x23CF), (0x23D1, 0x23DB), (0x23E2, 0x2422),
    (0x2424, 0x24FF), (0x25A0, 0x2619), (0x2620, 0x2767), (0x2776, 0x2793),
    (0x2B12, 0x2B2F), (0x2B50, 0x2B59), (0x2BB8, 0x2BFF), (0x2E50, 0x2E51),
    (0x2E80, 0x2FFF), (0x3000, 0x3007), (0x3012, 0x3013),
    (0x3020, 0x302F), (0x3031, 0x303F), (0x3040, 0x309F), (0x30A1, 0x30FB),
    (0x30FD, 0x30FF), (0x3100, 0x31FF), (0x3200, 0x33FF), (0x3400, 0x4DBF),
    (0x4DC0, 0x4DFF), (0x4E00, 0x9FFF), (0xA000, 0xA4CF), (0xA960, 0xA97F),
    (0xAC00, 0xD7FF), (0xE000, 0xFAFF), (0xFE10, 0xFE1F), (0xFE30, 0xFE48),
    (0xFE50, 0xFE57), (0xFE5F, 0xFE62), (0xFE67, 0xFE6F),
    (0xFF01, 0xFF07), (0xFF0A, 0xFF0C), (0xFF0E, 0xFF19), (0xFF1F, 0xFF3A),
    (0xFF3C, 0xFF3C), (0xFF3E, 0xFF3E), (0xFF40, 0xFF5A), (0xFFE0, 0xFFE2),
    (0xFFE4, 0xFFE7), (0xFFF0, 0xFFF8), (0xFFFC, 0xFFFD),
    (0x1F000, 0x1FAFF), (0x20000, 0x3FFFD),
)
# Tr: rotated if there is no vertical writing glyph (brackets, wave dash, prolonged sound mark, etc.).
PP_VO_TR_CODES = frozenset(
    list(range(0x3008, 0x3012)) + list(range(0x3014, 0x3020)) +
    [0x3030, 0x30A0, 0x30FC, 0xFE59, 0xFE5A, 0xFE5B, 0xFE5C, 0xFE5D, 0xFE5E,
     0xFF08, 0xFF09, 0xFF0D, 0xFF1A, 0xFF1B, 0xFF1C, 0xFF1D, 0xFF1E,
     0xFF3B, 0xFF3D, 0xFF3F, 0xFF5B, 0xFF5C, 0xFF5D, 0xFF5E, 0xFF5F, 0xFF60, 0xFFE3])


def pp_uax50_class(code):
    """Summary UAX #50 vertical orientation class. 'Tr' (upright if a vertical glyph exists, otherwise rotated), 'U' (U/Tu upright), 'R' (rotated)."""
    if code in PP_VO_TR_CODES:
        return 'Tr'
    for low, high in PP_VO_UPRIGHT_RANGES:
        if code < low:
            return 'R'
        if code <= high:
            return 'U'
    return 'R'


def pp_uax50_rotate(code):
    """Whether a character without a vertical writing glyph is rotated 90° according to UAX #50 (R/Tr = rotated, U/Tu = upright)."""
    return pp_uax50_class(code) != 'U'


class PPFontCache(object):
    """Holds computed results for one active font. Everything is cleared when the font changes."""

    def __init__(self):
        self.reset(None)

    def reset(self, font_id):
        self.font_id = font_id
        self.masters = []
        self.weight_map = None
        self.master_locs = None      # {master: {axis tag: value}}, None = not read yet
        self.axes = None             # [(axis name, axis tag)], None = not read yet
        self.metrics = None
        self.char_names = {}
        self.unicode_index = None
        self.items = {}
        self.reported = set()
        self.warmed = set()          # names of glyphs whose fg pre-read is done
        self.none_reported = set()   # names of glyphs for which the None Contour error was printed
        self.vert_map = None         # {horizontal glyph: vertical writing glyph} (Features vert/vrt2), None = not read yet
        self.ss_map = {}             # Vertical stylistic set substitution (kept separately from vert)
        self.vert_alt = {}           # glyph name → vertical writing glyph name (None if none) lookup results
        self.vert_reported = False   # the read result is printed once per font.
        self.vadv_reported = False
        self._sync_count = 0

    def sync(self, font):
        font_id = pp_font_id(font)
        if font_id != self.font_id:
            self.reset(font_id)
        self._sync_count += 1
        # The master list is re-read only on font switch and about every 3 seconds (10 ticks).
        if self.masters and self._sync_count % 10 != 1:
            return
        self.forget_vert()   # re-read about every 3 seconds so Features code edits are reflected.
        masters = pp_master_names(font)
        if masters != self.masters:
            self.masters = masters
            self.weight_map = None
            self.master_locs = None   
            self.axes = None          
            self.items = {}

    def get_metrics(self, font):
        if self.metrics is None:
            upm = 1000.0
            asc = None
            desc = None
            try:
                package = fl6.flPackage(font)
            except Exception:
                package = None
            for reader in (lambda: package.upm, lambda: font.upm):
                try:
                    value = float(reader())
                    if value > 0:
                        upm = value
                        break
                except Exception:
                    continue
            try:
                asc = float(package.ascender_value)
            except Exception:
                asc = None
            try:
                desc = float(package.descender_value)
            except Exception:
                desc = None
            if asc is None or desc is None or asc - desc <= 0:
                asc = upm * 0.8
                desc = -upm * 0.2
            self.metrics = (upm, asc, desc)
        return self.metrics

    def get_weight_map(self, font):
        """Weight value per master (SSO v5.81 _build_weight_map approach, once per font)."""
        if self.weight_map is not None:
            return self.weight_map
        weight_map = {}
        try:
            package = fl6.flPackage(font)
            try:
                current_master = package.master
            except Exception:
                current_master = None
            for name in self.masters:
                try:
                    package.setMaster(name)
                    weight_map[name] = float(package.weight_value)
                except Exception:
                    weight_map[name] = 400.0
            if current_master:
                try:
                    package.setMaster(current_master)
                except Exception:
                    pass
        except Exception as error:
            print('%s weight_map creation error: %s' % (PP_LOG, error))
        self.weight_map = weight_map
        return weight_map

    def get_master_locations(self, font):
        """Axis location per master {master: {axis tag: value}} (Location in Font Info > Masters, once per font)."""
        if self.master_locs is not None:
            return self.master_locs
        locations = {}
        try:
            package = fl6.flPackage(font)
        except Exception:
            package = None
        if package is not None:
            for name in self.masters:
                try:
                    location = pp_location_dict(package.location(name))
                except Exception:
                    location = {}
                if location:
                    locations[name] = location
        self.master_locs = locations
        return locations

    def get_axes(self, font):
        """The font's axis list [(axis name, axis tag)] (Font Info > Axes order, once per font)."""
        if self.axes is not None:
            return self.axes
        axes = []
        try:
            package = fl6.flPackage(font)
            for axis in list(_v(package, 'axes') or []):
                short = str(_v(axis, 'shortName', '') or '')
                if short:
                    axes.append((str(_v(axis, 'name', '') or ''), short))
        except Exception:
            axes = []
        self.axes = axes
        return axes

    def variation_place(self, font):
        """Current location of the VARIATIONS panel. Returns (Weight axis tag, tuple of other axis location, {axis tag: value}).
        None if there is only one axis or the panel cannot be read."""
        axes = self.get_axes(font)
        if len(axes) < 2:
            return None
        location = _PP_VAR_PANEL.location(axes)
        if not location:
            return None
        weight_key = None
        for short in location:
            if short.lower() in PP_WEIGHT_AXIS_KEYS:
                weight_key = short
                break
        if weight_key is None:
            return None
        others = tuple(sorted((short.lower(), round(float(value), 4))
                              for short, value in location.items() if short != weight_key))
        return (weight_key, others, location)

    def variation_item(self, font, glyph_name, weight, place):
        """(paths, advance) — glyph obtained by FontLab's own interpolation (flGlyph.interpolateInstance) at the VARIATIONS panel
        location (place) with only Weight replaced by weight. None if it cannot be computed."""
        if weight is None or place is None:
            return None
        key = ('v', glyph_name, round(float(weight), 4), place[1])
        if key in self.items:
            return self.items[key]
        missing_before = _PP_NONE_CONTOURS[0]
        item = None
        try:
            item = self._compute_variation(font, glyph_name, float(weight), place)
        except Exception as error:
            self._report(glyph_name, 'VARIATIONS', 'wt=%s' % weight, 'interpolateInstance error: %s' % error)
            item = None
        if _PP_NONE_CONTOURS[0] != missing_before:
            self._report_none(glyph_name)
            return item
        self.items[key] = item
        return item

    def _compute_variation(self, font, glyph_name, weight, place):
        fl_glyph = self.fl_glyph(font, glyph_name)
        if fl_glyph is None or not self.masters:
            return None
        weight_key, _others, values = place
        package = fl6.flPackage(font)
        # Copies the master location and fills in axis values (the original master location is not changed).
        # built with pp_build_location to also support FontLab 9.
        wanted = dict(values)
        wanted[weight_key] = float(weight)
        location = pp_build_location(package, self.masters[0], wanted)
        if location is None:
            return None
        layer = fl_glyph.interpolateInstance(location, True)
        if layer is None:
            return None
        return (pp_layer_paths(layer), pp_layer_advance(layer))

    def all_instance_item(self, font, glyph_name, spec):
        """(paths, advance) — glyph interpolated at the Location (all axes) of one instance. None if it cannot be computed.
        With several axes uses FontLab's own interpolation (flGlyph.interpolateInstance); with one axis uses the existing Weight interpolation."""
        key = ('a', glyph_name, spec.get('key'))
        if key in self.items:
            return self.items[key]
        missing_before = _PP_NONE_CONTOURS[0]
        item = None
        try:
            if len(self.get_axes(font)) >= 2 and spec.get('loc'):
                item = self._compute_all_instance(font, glyph_name, spec['loc'], spec.get('loc_obj'))
            elif spec.get('weight') is not None:
                item = self._compute_interp(font, glyph_name, float(spec['weight']), None)
        except Exception as error:
            self._report(glyph_name, 'Instance', spec.get('label') or '', 'interpolateInstance error: %s' % error)
            item = None
        if _PP_NONE_CONTOURS[0] != missing_before:
            self._report_none(glyph_name)
            return item
        self.items[key] = item
        return item

    def _compute_all_instance(self, font, glyph_name, loc, loc_obj=None):
        fl_glyph = self.fl_glyph(font, glyph_name)
        if fl_glyph is None or not self.masters:
            return None
        package = fl6.flPackage(font)
        # Axis tag case follows Font Info > Axes (keys of spec['loc'] are lowercase).
        shorts = {}
        for _name, short in self.get_axes(font):
            shorts[short.lower()] = short
        # Copies the master location and fills in axis values (the original master location is not changed).
        # FontLab 9 does not support setting directly, so the instance's own location (loc_obj) is used as is.
        wanted = dict((shorts.get(axis, axis), float(value)) for axis, value in loc.items())
        location = pp_build_location(package, self.masters[0], wanted, fallback=loc_obj)
        if location is None:
            return None
        layer = fl_glyph.interpolateInstance(location, True)
        if layer is None:
            return None
        return (pp_layer_paths(layer), pp_layer_advance(layer))

    def forget_variation_items(self):
        """Discards interpolation results of the previous location when the panel location changes (so they don't pile up while dragging a slider)."""
        for key in list(self.items.keys()):
            if key[0] == 'v':
                del self.items[key]

    def weight_group(self, font, master):
        """Master group used for Weight interpolation in a font with several axes.
        Returns (Weight axis tag, other axis location, {master: wt value}). Contains only masters whose other axis values equal master (the active master).
        None if there is only one axis or the axis locations cannot be read (interpolates the old way)."""
        locations = self.get_master_locations(font)
        if not locations:
            return None
        base = locations.get(master)
        if base is None:
            for name in self.masters:
                if name in locations:
                    base = locations[name]
                    break
        if base is None or len(base) < 2:
            return None
        weight_key = pp_location_weight_key(base)
        if weight_key is None:
            return None
        others = pp_location_others(base, weight_key)
        weights = {}
        for name in self.masters:
            location = locations.get(name)
            if location is None or weight_key not in location:
                continue
            if pp_location_others(location, weight_key) == others:
                weights[name] = float(location[weight_key])
        if not weights:
            return None
        return (weight_key, others, weights)

    def glyph_name_for_char(self, font, char):
        """Finds the actual glyph name for one character (ERR&S v3.32 approach, including Han)."""
        if char in self.char_names:
            return self.char_names[char]
        name = None
        try:
            code = ord(char)
        except Exception:
            code = None
        if code is not None:
            try:
                fg = fl6.fgSymbol(int(code)).glyph(font, False)
            except Exception:
                fg = None
            if fg is not None:
                try:
                    if code in list(_v(fg, 'unicodes') or []):
                        name = str(_v(fg, 'name'))
                except Exception:
                    pass
            if name is None:
                standard = (('uni%04X' % code,) if code <= 0xFFFF
                            else ('u%05X' % code, 'u%06X' % code))
                for candidate in standard:
                    try:
                        fg = font[candidate]
                    except Exception:
                        fg = None
                    if fg is None:
                        continue
                    try:
                        if code in list(_v(fg, 'unicodes') or []):
                            name = str(_v(fg, 'name'))
                            break
                    except Exception:
                        continue
            if name is None:
                if self.unicode_index is None:
                    index = {}
                    try:
                        for fg in font.glyphs:
                            for value in (_v(fg, 'unicodes') or []):
                                index.setdefault(value, str(_v(fg, 'name')))
                    except Exception:
                        pass
                    self.unicode_index = index
                name = self.unicode_index.get(code)
        self.char_names[char] = name
        return name

    def _warm(self, font, glyph_name):
        """Reads fg data first, once per glyph per font. True if newly read."""
        if not glyph_name or glyph_name in self.warmed:
            return False
        self.warmed.add(glyph_name)
        pp_warm_fg_glyph(font, glyph_name)
        return True

    def fl_glyph(self, font, glyph_name):
        try:
            fg = font[glyph_name]
        except Exception:
            fg = None
        if fg is None:
            return None
        # fg must be read before getting the flGlyph so Contours of unloaded glyphs are not None.
        self._warm(font, glyph_name)
        try:
            fl_glyph = fl6.flGlyph(fg, font)
        except Exception:
            return None
        # Also pre-reads Component source glyphs (and their Components) and gets the flGlyph again.
        pending = pp_component_glyph_names(fl_glyph)
        newly = False
        depth = 0
        while pending and depth < 8:
            depth += 1
            next_pending = []
            for name in pending:
                if self._warm(font, name):
                    newly = True
                    try:
                        source = fl6.flGlyph(font[name], font)
                    except Exception:
                        source = None
                    if source is not None:
                        next_pending.extend(pp_component_glyph_names(source))
            pending = next_pending
        if newly:
            try:
                fl_glyph = fl6.flGlyph(fg, font)
            except Exception:
                pass
        return fl_glyph

    def _report_none(self, glyph_name):
        if glyph_name in self.none_reported:
            return
        self.none_reported.add(glyph_name)
        print('%s Outline read error: %s — some outlines are missing because of unloaded Contours (None).'
              % (PP_LOG, glyph_name))

    def master_item(self, font, glyph_name, master):
        """(paths, advance) — the glyph as is on the master layer."""
        key = ('m', glyph_name, master)
        if key in self.items:
            return self.items[key]
        item = None
        missing_before = _PP_NONE_CONTOURS[0]
        fl_glyph = self.fl_glyph(font, glyph_name)
        if fl_glyph is not None:
            layer = pp_get_layer(fl_glyph, master)
            if layer is not None:
                item = (pp_layer_paths(layer), pp_layer_advance(layer))
        if _PP_NONE_CONTOURS[0] != missing_before:
            # Incomplete results are not cached and are read again on the next refresh.
            self._report_none(glyph_name)
            return item
        if item is not None:
            self.items[key] = item
        return item

    def interp_item(self, font, glyph_name, weight, group=None):
        """(paths, advance) — glyph interpolated at the target Weight. None if it cannot be computed.
        If group (weight_group result) is given, interpolates only along the Weight axis within that master group."""
        key = ('i', glyph_name, round(float(weight), 4) if weight is not None else None,
               group[1] if group is not None else None)
        if key in self.items:
            return self.items[key]
        missing_before = _PP_NONE_CONTOURS[0]
        item = self._compute_interp(font, glyph_name, weight, group)
        if _PP_NONE_CONTOURS[0] != missing_before:
            self._report_none(glyph_name)
            return item
        self.items[key] = item
        return item

    def _compute_interp(self, font, glyph_name, target_weight, group=None):
        fl_glyph = self.fl_glyph(font, glyph_name)
        if fl_glyph is None or target_weight is None:
            return None
        if group is not None:
            # With several axes, interpolates by the wt value of the axis location using only masters whose other axis values equal the active master.
            weight_map = group[2]
        else:
            weight_map = self.get_weight_map(font)
        masters = []
        for name in self.masters:
            if name not in weight_map:
                continue
            layer = pp_get_layer(fl_glyph, name)
            if layer is not None:
                masters.append((float(weight_map[name]), name, layer))
        masters.sort(key=lambda item: item[0])
        if not masters:
            return None
        if len(masters) == 1:
            layer = masters[0][2]
            return (pp_layer_paths(layer), pp_layer_advance(layer))
        for weight, name, layer in masters:
            if abs(target_weight - weight) < 0.0001:
                return (pp_layer_paths(layer), pp_layer_advance(layer))
        if target_weight < masters[0][0]:
            left, right = masters[0], masters[1]
        elif target_weight > masters[-1][0]:
            left, right = masters[-2], masters[-1]
        else:
            left, right = masters[0], masters[-1]
            for index in range(len(masters) - 1):
                low = masters[index]
                high = masters[index + 1]
                if low[0] <= target_weight <= high[0]:
                    left, right = low, high
                    break
        span = right[0] - left[0]
        if span == 0:
            return (pp_layer_paths(left[2]), pp_layer_advance(left[2]))
        blend = float(target_weight - left[0]) / float(span)
        left_shapes = pp_layer_shapes(left[2], with_contours_only=True)
        right_shapes = pp_layer_shapes(right[2], with_contours_only=True)
        if not left_shapes or len(left_shapes) != len(right_shapes):
            self._report(glyph_name, left[1], right[1],
                         'Shape count %d ↔ %d' % (len(left_shapes), len(right_shapes)))
            return None
        paths = []
        for index, (shape_a, shape_b) in enumerate(zip(left_shapes, right_shapes)):
            try:
                path = pp_interp_shape_path(shape_a, shape_b, blend)
            except Exception as error:
                print('%s Interpolation Path error: %s' % (PP_LOG, error))
                path = None
            if path is None:
                self._report(glyph_name, left[1], right[1], 'Shape #%d incompatible' % index)
                return None
            paths.append(path)
        adv_a = pp_layer_advance(left[2])
        adv_b = pp_layer_advance(right[2])
        return (paths, adv_a + (adv_b - adv_a) * blend)

    def _report(self, glyph_name, left_name, right_name, reason):
        key = (glyph_name, left_name, right_name, reason)
        if key in self.reported:
            return
        self.reported.add(key)
        print('%s Interpolation error: %s — masters %s ↔ %s, %s'
              % (PP_LOG, glyph_name, left_name, right_name, reason))

    def forget_glyph(self, glyph_name):
        for key in list(self.items.keys()):
            if key[1] == glyph_name:
                del self.items[key]

    # ── OpenType vertical writing glyphs (vert) / vertical Advance ─────────
    def forget_vert(self):
        self.vert_map = None
        self.ss_map = {}
        self.vert_alt = {}

    def _glyph_exists(self, font, glyph_name):
        try:
            return font[glyph_name] is not None
        except Exception:
            return False

    def _ensure_vert_maps(self, font):
        if self.vert_map is not None:
            return
        try:
            self.vert_map, self.ss_map, summary = pp_build_vert_map(font)
        except Exception as error:
            self.vert_map, self.ss_map, summary = {}, {}, 'read error: %s' % error
        if not self.vert_reported:
            self.vert_reported = True
            print('%s Vertical writing glyphs (vert) Features read: %s' % (PP_LOG, summary))

    def _existing(self, font, glyph_name):
        return glyph_name if (glyph_name and self._glyph_exists(font, glyph_name)) else None

    def vert_glyph_name(self, font, glyph_name, rotated=False):
        """Vertical writing glyph name (None if unchanged).
        Upright characters: vert/vrt2 code → glyphs with '.vert'/'.vrt2' suffix → Vertical stylistic set on that result.
        Rotated characters (rotated): typeset like horizontal writing, so only the Vertical stylistic set is applied, without vert."""
        if not glyph_name:
            return None
        key = (glyph_name, bool(rotated))
        if key in self.vert_alt:
            return self.vert_alt[key]
        self._ensure_vert_maps(font)
        base = glyph_name
        if not rotated:
            alt = self._existing(font, self.vert_map.get(glyph_name))
            if not alt:
                for suffix in ('.vert', '.vrt2'):
                    if self._glyph_exists(font, glyph_name + suffix):
                        alt = glyph_name + suffix
                        break
            if alt:
                base = alt
        styled = self._existing(font, self.ss_map.get(base))
        if styled:
            base = styled
        result = base if base != glyph_name else None
        self.vert_alt[key] = result
        return result

    def has_vert_glyph(self, font, glyph_name):
        """Whether there is a vertical writing glyph changed by vert/vrt2 (or the '.vert'/'.vrt2' suffix)."""
        if not glyph_name:
            return False
        self._ensure_vert_maps(font)
        if self._existing(font, self.vert_map.get(glyph_name)):
            return True
        return any(self._glyph_exists(font, glyph_name + suffix) for suffix in ('.vert', '.vrt2'))

    def vertical_metrics(self, font, glyph_name, master):
        """(vertical Advance, vertical origin Y, Top Side Bearing). Unreadable values are None.
        Read in this order: 1) vmtx/VORG of the font's source file (OTF/TTF) 2) the layer's vertical Advance (path)."""
        key = ('vh', glyph_name, master)
        if key in self.items:
            return self.items[key]
        value = origin = tsb = None
        source = None
        data = pp_font_file_vmetrics(font)
        if data is not None:
            # glyph name (CID/custom name) → GID, otherwise the FontLab glyph's Unicode → cmap GID
            gid = data['names'].get(glyph_name)
            if gid is None:
                try:
                    for code in (_v(font[glyph_name], 'unicodes') or []):
                        gid = data['unicodes'].get(int(code))
                        if gid is not None:
                            break
                except Exception:
                    gid = None
            record = data['gid_vmtx'][gid] if (gid is not None and gid < len(data['gid_vmtx'])) else None
            if record is not None:
                value, tsb = float(record[0]), float(record[1])
                if data['vorg'] is not None:
                    origin = float(data['vorg'].get(gid, data['vorg_default']))
                source = '%s vmtx%s' % (os.path.basename(data['path']),
                                        '·VORG' if data['vorg'] is not None else '')
        if value is None:
            fl_glyph = self.fl_glyph(font, glyph_name)
            if fl_glyph is not None:
                layer = pp_get_layer(fl_glyph, master)
                if layer is not None:
                    value, source = pp_layer_vadvance(layer)
                    tsb = None
        upm = self.get_metrics(font)[0]
        if value is not None and (value <= 0 or value > upm * 4.0):
            value = origin = tsb = None
        if not self.vadv_reported:
            self.vadv_reported = True
            if value is not None:
                text = '%g (%s)' % (value, source)
                if origin is not None:
                    text += ', vertical origin Y %g' % origin
                elif tsb is not None:
                    text += ', Top Side Bearing %g' % tsb
            else:
                text = 'unreadable — using the glyph frame height (em) (%s)' % pp_font_file_vmetrics_status(font)
            print('%s Vertical Advance read: %s = %s' % (PP_LOG, glyph_name, text))
        result = (value, origin, tsb)
        self.items[key] = result
        return result


# ============================================================
# Finds the font and glyph directly from the Glyph Window canvas the panel is attached to.
#   After switching fonts, CurrentFont() returns the previous font until the canvas is clicked.
# ============================================================
_PP_VIEWPORT = [None]               # Glyph Window canvas the panel follows (QWidget)
_PP_PACKAGE_FONT = [None, None]     # [package id, AllFonts index] — fgFont wrappers are not kept.
_PP_FONT_STATE = {'count': None, 'until': 0.0}   # font-switch transition state


def _pp_open_font_count():
    """Number of open fonts. Uses legacy.fl.count, which does not create fgFont wrappers. None if unreadable."""
    if legacy is None:
        return None
    try:
        return int(legacy.fl.count)
    except Exception:
        return None


def pp_fonts_settling():
    """True during the transition of loading or closing a font. FontLab objects are not accessed during this time.
    If the number of open fonts changed, a modal window is open, or a font is open but CurrentFont() is None,
    it is treated as a transition for PP_FONT_SETTLE_SEC from then on."""
    now = time.time()
    count = _pp_open_font_count()
    state = _PP_FONT_STATE
    if count != state['count']:
        first = state['count'] is None and state['until'] == 0.0
        state['count'] = count
        _PP_PACKAGE_FONT[0] = None
        _PP_PACKAGE_FONT[1] = None
        if not first:
            state['until'] = now + PP_FONT_SETTLE_SEC
            return True
    try:
        modal = QtGui.QApplication.activeModalWidget()
    except Exception:
        modal = None
    if modal is not None:
        state['until'] = now + PP_FONT_SETTLE_SEC
        return True
    if now < state['until']:
        return True
    if count:
        try:
            no_current = fl6.CurrentFont() is None
        except Exception:
            no_current = True
        if no_current:
            state['until'] = now + PP_FONT_SETTLE_SEC
            return True
    return False


def pp_set_viewport(widget):
    _PP_VIEWPORT[0] = widget


def _pp_valid_fl(obj):
    return obj is not None and not bool(_v(obj, 'isNull', False))


def _pp_related_widgets(viewport):
    """viewport itself → children (2 levels) → parents (4 levels)."""
    result = [viewport]
    level = [viewport]
    for _depth in range(2):
        nxt = []
        for widget in level:
            try:
                for child in list(widget.children() or []):
                    if isinstance(child, QtGui.QWidget):
                        nxt.append(child)
            except Exception:
                continue
        result.extend(nxt)
        level = nxt
    parent = viewport
    for _depth in range(4):
        try:
            parent = parent.parentWidget()
        except Exception:
            parent = None
        if parent is None:
            break
        result.append(parent)
    return result


def pp_viewport_fl_canvas(viewport=None):
    if viewport is None:
        viewport = _PP_VIEWPORT[0]
    if viewport is None or not _widget_alive(viewport):
        return None
    try:
        workspace = fl6.flWorkspace.instance()
    except Exception:
        workspace = None
    if workspace is None:
        return None
    related = _pp_related_widgets(viewport)
    for widget in related:
        try:
            fl_canvas = workspace.getCanvasForViewport(widget)
        except Exception:
            fl_canvas = None
        if _pp_valid_fl(fl_canvas):
            return fl_canvas
    # finds the canvas in the canvases() list whose viewPort() is a related widget.
    try:
        canvases = list(_v(workspace, 'canvases', None) or [])
    except Exception:
        canvases = []
    for fl_canvas in canvases:
        if not _pp_valid_fl(fl_canvas):
            continue
        port = _v(fl_canvas, 'viewPort', None)
        if port is None:
            continue
        for widget in related:
            if _same_widget(port, widget):
                return fl_canvas
    return None


def pp_activate_viewport_canvas(viewport):
    """Makes the canvas FontLab's active canvas (same state as clicking it). True if changed."""
    fl_canvas = pp_viewport_fl_canvas(viewport)
    if fl_canvas is None:
        return False
    try:
        workspace = fl6.flWorkspace.instance()
        if workspace is None:
            return False
        try:
            if workspace.isActiveCanvas(fl_canvas):
                return False
        except Exception:
            pass
        workspace.setActiveCanvas(fl_canvas)
        return True
    except Exception:
        return False


def _pp_canvas_fl_glyph(fl_canvas):
    """Active glyph (flGlyph) of the canvas Text Block. The first glyph if there is no active glyph."""
    try:
        blocks = list(fl_canvas.textBlocks() or [])
    except Exception:
        return None
    fallback = None
    for block in blocks:
        try:
            info = block.getActiveGlyph()
        except Exception:
            info = None
        if info is None:
            continue
        glyph = _v(info, 'glyph', None)
        if glyph is None:
            continue
        if bool(_v(info, 'isActive', False)):
            return glyph
        if fallback is None:
            fallback = glyph
    return fallback


def _pp_package_id(package):
    try:
        value = _v(package, 'id', None)
        return None if value is None else str(value)
    except Exception:
        return None


def _pp_font_label(font):
    """Font name for diagnostics: file name → font name."""
    if font is None:
        return '-'
    for reader in (lambda: _v(font, 'path', ''), lambda: _v(font, 'name', ''),
                   lambda: _v(font, 'fullName', ''), lambda: _v(font, 'familyName', '')):
        try:
            value = str(reader() or '')
        except Exception:
            value = ''
        if value:
            return os.path.basename(value) or value
    return '?'


def _pp_names_of(obj):
    names = set()
    for attr in ('name', 'fullName', 'fontName', 'familyName'):
        try:
            value = str(_v(obj, attr, '') or '')
        except Exception:
            value = ''
        if value:
            names.add(value)
    try:
        info = _v(obj, 'info', None)
        for attr in ('postscriptFullName', 'postscriptFontName', 'openTypeNameCompatibleFullName'):
            value = str(_v(info, attr, '') or '')
            if value:
                names.add(value)
    except Exception:
        pass
    return names


def _pp_font_for_package(package):
    """Finds the open fgFont matching the flPackage (id → isEqual → path → name)."""
    if not _pp_valid_fl(package):
        return None
    pid = _pp_package_id(package)
    try:
        packages = fl6.AllFonts()
                # Avoid out-of-range index lookups that would otherwise be used to end fgPackages iteration.
        fonts = [packages[index] for index in range(len(packages))] if packages is not None else []
    except Exception:
        fonts = []
    # takes the font at the remembered index again and checks the package id is the same (fgFont wrappers are not kept).
    if pid is not None and _PP_PACKAGE_FONT[0] == pid and _PP_PACKAGE_FONT[1] is not None:
        index = _PP_PACKAGE_FONT[1]
        if 0 <= index < len(fonts):
            try:
                if _pp_package_id(fl6.flPackage(fonts[index])) == pid:
                    return fonts[index]
            except Exception:
                pass
        _PP_PACKAGE_FONT[0] = None
        _PP_PACKAGE_FONT[1] = None
    path = str(_v(package, 'path', '') or '')
    packages = []
    for font in fonts:
        try:
            packages.append((font, fl6.flPackage(font)))
        except Exception:
            continue
    found = None
    if pid is not None:
        for font, other in packages:
            if _pp_package_id(other) == pid:
                found = font
                break
    if found is None:
        for font, other in packages:
            try:
                if package.isEqual(other):
                    found = font
                    break
            except Exception:
                continue
    if found is None and path:
        norm = os.path.normcase(os.path.normpath(path))
        for font, other in packages:
            for candidate in (_v(font, 'path', ''), _v(other, 'path', '')):
                try:
                    if candidate and os.path.normcase(os.path.normpath(str(candidate))) == norm:
                        found = font
                        break
                except Exception:
                    continue
            if found is not None:
                break
    if found is None:
        names = _pp_names_of(package)
        if names:
            matches = [font for font, other in packages
                       if names & (_pp_names_of(other) | _pp_names_of(font))]
            if len(matches) == 1:
                found = matches[0]
    if found is not None and pid is not None:
        for index, font in enumerate(fonts):
            if font is found:
                _PP_PACKAGE_FONT[0] = pid
                _PP_PACKAGE_FONT[1] = index
                break
    return found


def _pp_workspace_package_font():
    """The fgFont pointed to by flWorkspace.currentPackage."""
    try:
        workspace = fl6.flWorkspace.instance()
        package = _v(workspace, 'currentPackage', None) if workspace is not None else None
    except Exception:
        package = None
    return _pp_font_for_package(package) if _pp_valid_fl(package) else None


def _pp_glyph_in_font(font, name):
    if font is None or not name:
        return None
    try:
        fg = font[name]
    except Exception:
        fg = None
    if fg is None:
        return None
    pp_warm_fg_glyph(font, name)   # makes sure Contours of unloaded glyphs do not become None.
    try:
        return fl6.flGlyph(fg, font)
    except Exception:
        return None


def _pp_canvas_font_glyph(fl_canvas):
    if fl_canvas is None:
        return None, None
    glyph = _pp_canvas_fl_glyph(fl_canvas)
    if glyph is None:
        return None, None
    package = _v(glyph, 'package', None)
    if not _pp_valid_fl(package):
        return None, glyph
    return _pp_font_for_package(package), glyph


def pp_viewport_font_glyph():
    """(fgFont, flGlyph) — font and active glyph of the canvas the panel is attached to.
    If not found on the canvas, the glyph with the same name in the font of flWorkspace.currentPackage."""
    font, glyph = _pp_canvas_font_glyph(pp_viewport_fl_canvas())
    if font is not None and glyph is not None:
        return font, glyph
    name = None
    if glyph is not None:
        name = str(_v(glyph, 'name', '') or '') or None
    if name is None:
        try:
            current = fl6.CurrentGlyph()
            name = str(_v(current, 'name', '') or '') or None
        except Exception:
            name = None
    font = _pp_workspace_package_font()
    if font is None:
        return None, None
    return font, _pp_glyph_in_font(font, name)


def pp_same_font(first, second):
    if first is None or second is None:
        return first is second
    try:
        a = _pp_package_id(fl6.flPackage(first))
        b = _pp_package_id(fl6.flPackage(second))
        if a is not None and b is not None:
            return a == b
    except Exception:
        pass
    return pp_font_id(first) == pp_font_id(second)


def pp_current_font():
    """Font of the canvas the panel is attached to. fl6.CurrentFont() if not found."""
    try:
        view_font, _glyph = pp_viewport_font_glyph()
    except Exception:
        view_font = None
    if view_font is not None:
        return view_font
    try:
        return fl6.CurrentFont()
    except Exception:
        return None


_PP_LAST_GLYPH_NAME = [None]        # name of the active glyph shown last


def _pp_canvas_any_glyph(fl_canvas):
    """First glyph (flGlyph) of the canvas Text Block glyph list when there is no active glyph."""
    if not _pp_valid_fl(fl_canvas):
        return None
    glyph = _pp_canvas_fl_glyph(fl_canvas)
    if glyph is not None:
        return glyph
    try:
        blocks = list(fl_canvas.textBlocks() or [])
    except Exception:
        return None
    for block in blocks:
        try:
            infos = list(block.getAllGlyphs() or [])
        except Exception:
            infos = []
        for info in infos:
            glyph = _v(info, 'glyph', None)
            if glyph is not None and str(_v(glyph, 'name', '') or ''):
                return glyph
    return None


def pp_fallback_glyph_name():
    """Glyph name to use when CurrentGlyph() is None (canvas glyph → last glyph)."""
    canvas = pp_viewport_fl_canvas()
    if canvas is None:
        try:
            workspace = fl6.flWorkspace.instance()
            canvas = workspace.getActiveCanvas() if workspace is not None else None
        except Exception:
            canvas = None
    glyph = _pp_canvas_any_glyph(canvas)
    if glyph is not None:
        name = str(_v(glyph, 'name', '') or '')
        if name:
            return name
    return _PP_LAST_GLYPH_NAME[0]


def pp_active_glyph_info(font_cache):
    """Returns (font, glyph_name, fl_glyph, active_master). Nones if unavailable."""
    try:
        font = fl6.CurrentFont()
        fg = fl6.CurrentGlyph()
    except Exception:
        return None, None, None, None
    # if the canvas the panel is attached to shows a different font (right after a font switch), use the canvas's font and glyph.
    view_font, view_glyph = None, None
    try:
        view_font, view_glyph = pp_viewport_font_glyph()
    except Exception:
        view_font, view_glyph = None, None
    if view_font is not None and view_glyph is not None and not pp_same_font(view_font, font):
        font = view_font
        font_cache.sync(font)
        try:
            name = str(_v(view_glyph, 'name'))
        except Exception:
            name = None
        fl_glyph = view_glyph
        fg = None
    else:
        if font is None:
            return None, None, None, None
        font_cache.sync(font)
        if fg is not None:
            try:
                name = str(_v(fg, 'name'))
            except Exception:
                name = None
            try:
                fl_glyph = fl6.flGlyph(fg, font)
            except Exception:
                fl_glyph = None
        else:
            # right after switching fonts in the Fonts panel, CurrentGlyph() is None.
            #   Uses the same glyph of the new font by the canvas glyph name (or the last glyph name if none).
            name = pp_fallback_glyph_name()
            fl_glyph = _pp_glyph_in_font(font, name)
            if fl_glyph is None:
                name = None
    if name:
        _PP_LAST_GLYPH_NAME[0] = name
    master = None
    try:
        master = str(fl_glyph.activeLayer.name)
    except Exception:
        master = None
    if master not in font_cache.masters:
        try:
            master = str(fl6.flPackage(font).master)
        except Exception:
            master = None
    if master not in font_cache.masters:
        master = font_cache.masters[0] if font_cache.masters else None
    return font, name, fl_glyph, master


# ============================================================
# Glyph Window text exchange
#   Read: symbolList() of the active Text Block (including line breaks). On failure, the glyph list of getAllGlyphs().
#   Write: flItems.requestContent(fgSymbolList, caret index) — the path used in Twin Mode
# ============================================================
def pp_current_text_block():
    """Text Block of the active Glyph Window (active block → block containing the active glyph → first block)."""
    try:
        workspace = fl6.flWorkspace.instance()
    except Exception:
        return None
    if workspace is None:
        return None
    # if the canvas the panel is attached to is not the active canvas (right after a font switch), activate it first.
    pp_activate_viewport_canvas(_PP_VIEWPORT[0])
    try:
        block = workspace.getActiveTextBlock()
    except Exception:
        block = None
    if block is not None and not bool(_v(block, 'isNull', False)):
        return block
    try:
        fl_canvas = workspace.getActiveCanvas()
    except Exception:
        fl_canvas = None
    blocks = []
    if fl_canvas is not None:
        try:
            blocks = list(fl_canvas.textBlocks() or [])
        except Exception:
            blocks = []
    for candidate in blocks:
        try:
            info = candidate.getActiveGlyph()
        except Exception:
            info = None
        if info is not None and bool(_v(info, 'isActive', False)):
            return candidate
    return blocks[0] if blocks else None


def _pp_glyph_token(font, font_cache, name, char):
    """Builds a panel text token from a glyph name and a character. Uses the character only if it points to the same glyph."""
    if char:
        try:
            mapped = font_cache.glyph_name_for_char(font, char)
        except Exception:
            mapped = None
        if not name or mapped == name:
            return char
    if name:
        return '/' + name
    return None


def _pp_symbol_token(font, font_cache, sym):
    if sym is None:
        return None
    if bool(_v(sym, 'cr', False)):
        return '\n'
    code = 0
    if _v(sym, 'hasUnicode', None) is not False:
        try:
            code = int(_v(sym, 'unicode', 0) or 0)
        except Exception:
            code = 0
    name = ''
    if _v(sym, 'hasName', None) is not False:
        name = _qstring_to_text(_v(sym, 'name', '')) or ''
    if code in (10, 13, 0x2028, 0x2029):
        return '\n'
    char = None
    if 32 <= code <= 0x10FFFF and not (0xD800 <= code <= 0xDFFF):
        try:
            char = chr(code)
        except Exception:
            char = None
    if not char and not name:
        # If there is neither a character nor a name, gets the name from the glyph the symbol points to.
        try:
            fg = sym.glyph(font, False)
        except Exception:
            fg = None
        if fg is None:
            return None
        name = str(_v(fg, 'name', '') or '')
        codes = list(_v(fg, 'unicodes') or [])
        if codes:
            try:
                char = chr(int(codes[0]))
            except Exception:
                char = None
    return _pp_glyph_token(font, font_cache, name, char)


def pp_read_glyph_window_tokens(font, font_cache):
    """Reads the active Glyph Window text as a list of panel text tokens (one character, '\\n', '/glyphname').
    None if it cannot be read."""
    block = pp_current_text_block()
    if block is None:
        return None
    try:
        symbols = fl6.fgSymbolList(block.symbolList())
        count = int(symbols.size())
        tokens = []
        for index in range(count):
            token = _pp_symbol_token(font, font_cache, symbols.at(index))
            if token:
                tokens.append(token)
        return tokens
    except Exception as error:
        print('%s Failed to read the Glyph Window symbol list (reading again via the glyph list): %s' % (PP_LOG, error))
    try:
        tokens = []
        for info in list(block.getAllGlyphs() or []):
            fg = _v(info, 'glyph')
            if fg is None:
                continue
            name = str(_v(fg, 'name', '') or '')
            codes = list(_v(fg, 'unicodes') or [])
            char = None
            if codes:
                try:
                    char = chr(int(codes[0]))
                except Exception:
                    char = None
            token = _pp_glyph_token(font, font_cache, name, char)
            if token:
                tokens.append(token)
        return tokens
    except Exception as error:
        print('%s Failed to read the Glyph Window text: %s' % (PP_LOG, error))
        return None


def _pp_fl_items():
    for factory in (lambda: fl6.flItems.instance(), lambda: fl6.flItems()):
        try:
            items = factory()
            if items is not None:
                return items
        except Exception:
            continue
    return None


def _pp_symbols_by_segments(tokens):
    """Builds an fgSymbolList from a string for characters and line breaks (TypeRig outputString approach),
    and appends '/glyphname' as fgSymbol(name)."""
    result = fl6.fgSymbolList()
    run = []

    def flush():
        if run:
            result.append(fl6.fgSymbolList(u''.join(run), False))
            del run[:]

    for token in tokens:
        if token.startswith('/') and len(token) > 1:
            flush()
            result.append(fl6.fgSymbol(token[1:]))
        else:
            run.append(token)
    flush()
    return result


def _pp_line_break_symbol():
    try:
        probe = fl6.fgSymbolList(u'\n', False)
        if int(probe.size()) == 1 and bool(_v(probe.at(0), 'cr', False)):
            return fl6.fgSymbol(probe.at(0))
    except Exception:
        pass
    for builder in (lambda: fl6.fgSymbol(10), lambda: fl6.fgSymbol()):
        try:
            sym = builder()
            sym.cr = True
            if bool(_v(sym, 'cr', False)):
                return sym
        except Exception:
            continue
    return None


def _pp_symbols_one_by_one(tokens):
    """Fallback path: builds an fgSymbol for each token."""
    symbols = []
    for token in tokens:
        if token == '\n':
            sym = _pp_line_break_symbol()
            if sym is None:
                continue
        elif token.startswith('/') and len(token) > 1:
            sym = fl6.fgSymbol(token[1:])
        else:
            sym = fl6.fgSymbol(int(ord(token)))
        symbols.append(sym)
    return fl6.fgSymbolList(symbols)


def pp_write_glyph_window_tokens(tokens):
    """Puts the list of panel text tokens into the active Glyph Window as text. True on success."""
    items = _pp_fl_items()
    if items is None:
        print('%s flItems is not available, so the text could not be put into the Glyph Window.' % PP_LOG)
        return False
    symbols = None
    try:
        symbols = _pp_symbols_by_segments(tokens)
        if int(symbols.size()) <= 0:
            symbols = None
    except Exception as error:
        print('%s Failed to build the symbol list (building again per character): %s' % (PP_LOG, error))
        symbols = None
    if symbols is None:
        try:
            symbols = _pp_symbols_one_by_one(tokens)
        except Exception as error:
            print('%s Failed to build the symbol list: %s' % (PP_LOG, error))
            return False
    try:
        items.requestContent(symbols, 0)
    except Exception as error:
        print('%s Failed to put the text into the Glyph Window: %s' % (PP_LOG, error))
        return False
    return True


def pp_glyph_geometry_signature(fl_glyph, masters):
    """Structure and coordinate signature of the active glyph (SSO v5.81 _graphic_signature approach)."""
    result = []
    try:
        for master in masters:
            layer = pp_get_layer(fl_glyph, master)
            if layer is None:
                result.append((master, None))
                continue
            shape_sig = []
            for shape in pp_layer_shapes(layer):
                contour_sig = []
                for contour in _pp_direct_contours(shape):
                    nodes = _v(contour, 'nodes', []) or []
                    contour_sig.append(tuple(
                        (round(float(_v(n, 'x', 0.0)), 2), round(float(_v(n, 'y', 0.0)), 2))
                        for n in nodes))
                try:
                    tr = shape.transform
                    contour_sig.append(tuple(round(float(_v(tr, k, 0.0)), 3)
                                             for k in ('m11', 'm12', 'm21', 'm22', 'dx', 'dy')))
                except Exception:
                    pass
                shape_sig.append(tuple(contour_sig))
            result.append((master, tuple(shape_sig), round(pp_layer_advance(layer), 2)))
        return tuple(result)
    except Exception:
        return None


# ============================================================
# Text Tool detection (tool QAction tracking approach of Hangeul_Input_Tool_OnOff)
# ============================================================
PP_TEXT_TOOL_ACTION = 'actionText'
PP_GLYPH_TOOL_ACTIONS = (
    'actionBucket', 'actionDemo', 'actionDrawPen', 'actionDraw', 'actionEdit',
    'actionEllipse', 'actionEmpty_Tool', 'actionGuideline', 'actionKerning',
    'actionKnife', 'actionMetrics', 'actionNodes_tool', 'actionOptimizer',
    'actionPaint', 'actionParametrization', 'actionPen', 'actionPrepolate',
    'actionRectangle', 'actionRotate', 'actionScale', 'actionSlant',
    'actionStapler', 'actionStrokeTool', 'actionTTH', 'actionText', 'actionZoom',
)
PP_GLYPH_TOOL_TOOLTIPS = (
    ('fill', 'actionBucket'), ('demo tool', 'actionDemo'), ('pen', 'actionDrawPen'),
    ('pencil', 'actionDraw'), ('element', 'actionEdit'), ('ellipse', 'actionEllipse'),
    ('empty tool', 'actionEmpty_Tool'), ('guide', 'actionGuideline'),
    ('kerning', 'actionKerning'), ('knife', 'actionKnife'), ('metrics', 'actionMetrics'),
    ('contour', 'actionNodes_tool'), ('eraser', 'actionOptimizer'), ('brush', 'actionPaint'),
    ('magnet', 'actionParametrization'), ('rapid', 'actionPen'),
    ('matchmaker', 'actionPrepolate'), ('rectangle', 'actionRectangle'),
    ('rotate', 'actionRotate'), ('scale', 'actionScale'), ('slant', 'actionSlant'),
    ('scissors', 'actionStapler'), ('thickness', 'actionStrokeTool'),
    ('truetype hinting', 'actionTTH'), ('text', 'actionText'), ('zoom', 'actionZoom'),
)


def _pp_is_qaction(obj):
    try:
        if obj.inherits('QAction'):
            return True
    except Exception:
        pass
    return _class_name(obj) in ('QAction', 'QWidgetAction')


def _pp_checked(obj):
    try:
        if obj.isCheckable():
            return bool(obj.isChecked())
    except Exception:
        try:
            return bool(obj.isChecked())
        except Exception:
            pass
    return None


class PPTextToolTracker(QtGui.QWidget):
    """Remembers the Text Tool selection state via the triggered signal of FontLab's Glyph tool QActions."""

    def __init__(self, change_callback=None):
        QtGui.QWidget.__init__(self, None)
        self.hide()
        self._change_callback = change_callback
        self._app = QtGui.QApplication.instance()
        self._actions = {}
        self._text_action = None
        self._mode = None
        self._connections = []
        self._shutdown = False
        self.rescan()

    def rescan(self):
        if self._shutdown:
            return
        self._disconnect()
        self._find_actions()
        for name, action in list(self._actions.items()):
            slot = (lambda checked=False, n=name: self._on_tool(n))
            try:
                action.triggered.connect(slot)
                self._connections.append((action, 'triggered', slot))
            except Exception:
                pass
            try:
                for owner in list(action.associatedWidgets()):
                    self._connect_button(owner, action, name)
            except Exception:
                pass
        self._connect_tooltip_buttons()
        inferred = self._infer()
        if inferred is not None:
            self._mode = bool(inferred)

    def _connect_button(self, owner, action, name):
        candidates = [owner]
        try:
            getter = getattr(owner, 'widgetForAction', None)
            button = getter(action) if callable(getter) else None
            if button is not None:
                candidates.append(button)
        except Exception:
            pass
        for button in candidates:
            clicked = getattr(button, 'clicked', None)
            if clicked is None or not hasattr(clicked, 'connect'):
                continue
            if any(_same_widget(item, button) for item, _kind, _slot in self._connections):
                continue
            slot = (lambda checked=False, n=name: self._on_tool(n))
            try:
                clicked.connect(slot)
                self._connections.append((button, 'clicked', slot))
            except Exception:
                pass

    def _connect_tooltip_buttons(self):
        if self._app is None:
            return
        try:
            widgets = list(self._app.allWidgets())
        except Exception:
            widgets = []
        for widget in widgets:
            try:
                tooltip = _qstring_to_text(_v(widget, 'toolTip', '')).strip().lower()
            except Exception:
                tooltip = ''
            if not tooltip:
                continue
            head = tooltip.split(':', 1)[0].strip()
            name = ''
            for label, action_name in PP_GLYPH_TOOL_TOOLTIPS:
                if head == label or head.startswith(label + ' ('):
                    name = action_name
                    break
            if not name:
                continue
            clicked = getattr(widget, 'clicked', None)
            if clicked is None or not hasattr(clicked, 'connect'):
                continue
            if any(_same_widget(item, widget) for item, _kind, _slot in self._connections):
                continue
            slot = (lambda checked=False, n=name: self._on_tool(n))
            try:
                clicked.connect(slot)
                self._connections.append((widget, 'clicked', slot))
            except Exception:
                pass

    def _find_actions(self):
        self._actions = {}
        self._text_action = None
        if self._app is None:
            return
        missing = set(PP_GLYPH_TOOL_ACTIONS)
        try:
            stack = list(self._app.topLevelWidgets())
        except Exception:
            stack = []
        visited = set()
        inspected = 0
        while stack and missing and inspected < 20000:
            obj = stack.pop()
            marker = id(obj)
            if marker in visited:
                continue
            visited.add(marker)
            inspected += 1
            name = _object_name(obj)
            if name in missing and _pp_is_qaction(obj):
                self._actions[name] = obj
                missing.discard(name)
            try:
                children = _v(obj, 'children', None)
                if children:
                    stack.extend(list(children))
            except Exception:
                pass
        self._text_action = self._actions.get(PP_TEXT_TOOL_ACTION)
        if self._text_action is not None:
            try:
                group = self._text_action.actionGroup()
                for sibling in list(group.actions()):
                    sibling_name = _object_name(sibling)
                    if sibling_name and _pp_is_qaction(sibling):
                        self._actions[sibling_name] = sibling
            except Exception:
                pass

    def _infer(self):
        action = self._text_action
        if action is None:
            return None
        try:
            group = action.actionGroup()
            checked_action = group.checkedAction() if group is not None else None
            if checked_action is not None:
                return _same_widget(checked_action, action)
        except Exception:
            pass
        checked = [name for name, item in self._actions.items() if _pp_checked(item)]
        if checked:
            return PP_TEXT_TOOL_ACTION in checked
        return None

    def _on_tool(self, name):
        if self._shutdown:
            return
        active = (name == PP_TEXT_TOOL_ACTION)
        changed = (self._mode != active)
        self._mode = active
        if changed and callable(self._change_callback):
            try:
                self._change_callback(active)
            except Exception:
                traceback.print_exc()

    def is_text_tool_active(self):
        if self._mode is not None:
            return bool(self._mode)
        inferred = self._infer()
        if inferred is not None:
            self._mode = bool(inferred)
            return self._mode
        # In builds where the Text Tool action itself is not found, input is not blocked.
        return self._text_action is None

    def _disconnect(self):
        for obj, kind, slot in list(self._connections):
            try:
                getattr(obj, kind).disconnect(slot)
            except Exception:
                pass
        self._connections = []

    def shutdown(self):
        self._shutdown = True
        self._disconnect()
        self._change_callback = None



# ============================================================
# Icon buttons (blue line icons drawn directly, no background)
# ============================================================
def _pp_text_width(metrics, text):
    for name in ('horizontalAdvance', 'width'):
        try:
            return float(getattr(metrics, name)(text))
        except Exception:
            continue
    return 10.0


def _pp_fill_text(painter, text, pixel_size, weight, color, center_x, center_y):
    """Turns text into a Path and fills it at the given center (icons only)."""
    font = QtGui.QFont()
    font.setPixelSize(int(pixel_size))
    try:
        font.setWeight(int(weight))
    except Exception:
        font.setBold(weight >= 63)
    path = QtGui.QPainterPath()
    path.addText(QtCore.QPointF(0.0, 0.0), font, text)
    rect = path.boundingRect()
    dx = center_x - (float(_v(rect, 'x', 0.0)) + float(_v(rect, 'width', 0.0)) / 2.0)
    dy = center_y - (float(_v(rect, 'y', 0.0)) + float(_v(rect, 'height', 0.0)) / 2.0)
    path.translate(dx, dy)
    painter.fillPath(path, QtGui.QBrush(color))
    return path


class PPIcon(QtGui.QWidget):
    """Panel icon button. The state (on/off/plain/collapsed/disabled) is queried from the panel."""

    def __init__(self, kind, panel, click_callback, icon_size=PP_ICON):
        QtGui.QWidget.__init__(self, panel)
        self._kind = kind
        self._panel = panel
        self._click_callback = click_callback
        self._size = int(icon_size)
        self.setFixedSize(self._size, self._size)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, True)
        self.setStyleSheet('background:transparent; border:none;')

    def _state(self):
        try:
            return self._panel.icon_state(self._kind)
        except Exception:
            return 'off'

    def _interactive(self, state=None):
        """Whether it can be clicked (in the collapsed state only the eye icon can be clicked)."""
        if state is None:
            state = self._state()
        if state == 'disabled':
            return False
        if state == 'collapsed' and self._kind != 'eye':
            return False
        return True

    def refresh_cursor(self):
        """Icons that cannot be clicked show the default arrow cursor instead of the pointing-hand cursor."""
        try:
            shape = (QtCore.Qt.PointingHandCursor if self._interactive()
                     else QtCore.Qt.ArrowCursor)
            if getattr(self, '_cursor_shape', None) != shape:
                self._cursor_shape = shape
                self.setCursor(shape)
        except Exception:
            pass

    def enterEvent(self, event):
        self.refresh_cursor()
        self._start_alt_watch()
        self.update()

    def leaveEvent(self, event):
        self._stop_alt_watch()
        self.update()

    # ── Alt hover vertical flip of the Saved Text icon ─────────────
    def _watch_modifier_down(self):
        """Whether the modifier key that changes the icon shape is held.
        Saved Text icon: Alt; Horizontal mode Glyph Import icon: Ctrl (Mac Command) or Alt (Mac Option)."""
        if self._kind == 'h_glyph_io':
            return pp_ctrl_down() or pp_alt_down()
        return pp_alt_down()

    def _start_alt_watch(self):
        if self._kind not in ('user_text', 'h_glyph_io'):   # Horizontal mode Glyph Import icon added
            return
        timer = getattr(self, '_alt_timer', None)
        if timer is None:
            timer = QtCore.QTimer(self)
            timer.setInterval(80)
            timer.timeout.connect(self._alt_tick)
            self._alt_timer = timer
        self._alt_shown = self._watch_modifier_down()
        timer.start()

    def _stop_alt_watch(self):
        timer = getattr(self, '_alt_timer', None)
        if timer is not None:
            timer.stop()
        self._alt_shown = False

    def _alt_tick(self):
        if not bool(_v(self, 'underMouse', False)):
            self._stop_alt_watch()
            self.update()
            return
        alt = self._watch_modifier_down()
        if alt != getattr(self, '_alt_shown', False):
            self._alt_shown = alt
            self.update()

    def mousePressEvent(self, event):
        event.accept()
        if _v(event, 'button') != QtCore.Qt.LeftButton:
            return
        if not self._interactive():
            return
        # Changes the panel after the click event finishes.
        QtCore.QTimer.singleShot(0, self._click_callback)
        if self._kind in ('minus', 'plus'):
            # While held, repeats the same action every 70ms starting after 400ms.
            timer = getattr(self, '_repeat_timer', None)
            if timer is None:
                timer = QtCore.QTimer(self)
                timer.timeout.connect(self._repeat_tick)
                self._repeat_timer = timer
            timer.setInterval(400)
            timer.start()

    def _repeat_tick(self):
        timer = getattr(self, '_repeat_timer', None)
        if timer is None:
            return
        try:
            if not (QtGui.QApplication.mouseButtons() & QtCore.Qt.LeftButton):
                timer.stop()
                return
        except Exception:
            pass
        timer.setInterval(70)
        try:
            self._click_callback()
        except Exception:
            timer.stop()

    def _stop_repeat(self):
        timer = getattr(self, '_repeat_timer', None)
        if timer is not None:
            timer.stop()

    def mouseReleaseEvent(self, event):
        event.accept()
        self._stop_repeat()

    def hideEvent(self, event):
        self._stop_repeat()
        self._stop_alt_watch()

    def paintEvent(self, event):
        state = self._state()
        if state == 'on':
            color = PP_color('accent')
        elif state == 'plain':
            color = PP_color('icon_plain')
        elif state == 'dark':
            color = PP_color('icon_dark')
        elif state == 'collapsed':
            # in the hidden state only the eye icon turns blue on hover.
            if self._kind == 'eye' and bool(_v(self, 'underMouse', False)):
                color = PP_color('accent')
            else:
                color = PP_color('icon_collapsed')
        elif state == 'disabled':
            color = PP_color('icon_off')
            color.setAlpha(90)
        else:
            color = PP_color('icon_off')
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            size = float(self._size)
            if self._interactive(state) and bool(_v(self, 'underMouse', False)):
                painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                painter.setBrush(QtGui.QBrush(PP_color('icon_hover')))
                painter.drawRoundedRect(QtCore.QRectF(0.5, 0.5, size - 1.0, size - 1.0), 4, 4)
            pen = QtGui.QPen(color)
            pen.setWidthF(PP_ICON_PEN)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
            drawer = getattr(self, '_draw_' + self._kind, None)
            if drawer is not None:
                drawer(painter, pen, color, size)
        finally:
            painter.end()

    # ── Shapes of each icon ─────────────────────────────────────────
    def _draw_dock(self, painter, pen, color, size):
        """Thick circle (same shape as the SSO v5.33 Gallery Dock button)."""
        ring = QtGui.QPen(color)
        ring.setWidthF(3.0)
        painter.setPen(ring)
        center = size / 2.0
        radius = 7.0
        painter.drawEllipse(QtCore.QRectF(center - radius, center - radius,
                                          radius * 2.0, radius * 2.0))

    def _draw_eye(self, painter, pen, color, size):
        """Eye icon of ERR&S v3.32."""
        center = size / 2.0
        outline = QtGui.QPainterPath()
        outline.moveTo(3.5, center)
        outline.quadTo(center, 0.0, size - 3.5, center)
        outline.quadTo(center, size, 3.5, center)
        painter.drawPath(outline)
        painter.drawEllipse(QtCore.QRectF(center - 4.2, center - 4.2, 8.4, 8.4))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawEllipse(QtCore.QRectF(center - 1.9, center - 1.9, 3.8, 3.8))

    def _draw_invert(self, painter, pen, color, size):
        """Color scheme inversion icon of ERR&S v3.32 (bottom-right half circle filled)."""
        center = size / 2.0
        radius = 8.0
        rect = QtCore.QRectF(center - radius, center - radius, radius * 2.0, radius * 2.0)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawPie(rect, int(-135 * 16), int(180 * 16))
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.drawEllipse(rect)

    def _draw_interp(self, painter, pen, color, size):
        """A very thin A and a very bold A side by side (A by weight)."""
        _pp_fill_text(painter, 'A', 17, 0, color, size / 2.0 - 5.6, size / 2.0)
        bold = _pp_fill_text(painter, 'A', 17, 99, color, size / 2.0 + 5.2, size / 2.0)
        # Adds an outline in the same color so it surely looks bold even if the system font's Black weight is insufficient.
        outline = QtGui.QPen(color)
        outline.setWidthF(1.5)
        outline.setJoinStyle(QtCore.Qt.MiterJoin)
        painter.setPen(outline)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.drawPath(bold)
        show_all = False
        try:
            ctrl = self._panel._ctrl
            mode = ctrl.st['mode']
            show_all = (self._state() == 'on' and bool(ctrl.interp_all.get(mode)))
        except Exception:
            show_all = False
        if show_all:
            painter.resetTransform()
            bar = QtGui.QPen(PP_color('accent'))
            bar.setWidthF(2.0)
            bar.setCapStyle(QtCore.Qt.FlatCap)
            painter.setPen(bar)
            painter.drawLine(QtCore.QPointF(0.0, size - 2.5),
                             QtCore.QPointF(size, size - 2.5))

    def _draw_fitv(self, painter, pen, color, size):
        """Up/down arrow."""
        line = QtGui.QPen(color)
        line.setWidthF(2.0)
        line.setCapStyle(QtCore.Qt.RoundCap)
        line.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(line)
        center = size / 2.0
        painter.drawLine(QtCore.QPointF(center, 5.0), QtCore.QPointF(center, size - 5.0))
        for tip, direction in ((5.0, 1.0), (size - 5.0, -1.0)):
            painter.drawLine(QtCore.QPointF(center, tip),
                             QtCore.QPointF(center - 4.5, tip + 4.5 * direction))
            painter.drawLine(QtCore.QPointF(center, tip),
                             QtCore.QPointF(center + 4.5, tip + 4.5 * direction))

    def _draw_masters(self, painter, pen, color, size):
        """Three dots and three horizontal lines."""
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        for y in (7.5, 13.0, 18.5):
            painter.drawEllipse(QtCore.QRectF(4.6, y - 1.9, 3.8, 3.8))
        line = QtGui.QPen(color)
        line.setWidthF(2.4)
        line.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(line)
        for y in (7.5, 13.0, 18.5):
            painter.drawLine(QtCore.QPointF(11.0, y), QtCore.QPointF(21.5, y))

    def _draw_halign(self, painter, pen, color, size):
        """Horizontal mode indicator: four center-aligned horizontal lines (same shape in Vertical mode)."""
        line = QtGui.QPen(color)
        line.setWidthF(2.4)
        line.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(line)
        center = size / 2.0
        for y, length in ((6.5, 16.0), (11.0, 9.0), (15.5, 9.0), (20.0, 16.0)):
            painter.drawLine(QtCore.QPointF(center - length / 2.0, y),
                             QtCore.QPointF(center + length / 2.0, y))

    def _draw_vmode(self, painter, pen, color, size):
        """Vertical mode: four top-aligned vertical lines. Mirrored horizontally for left→right column direction."""
        mirror = False
        try:
            st = self._panel._ctrl.st
            mirror = st['mode'] == 'v' and bool(st.get('v_ltr', False))
        except Exception:
            mirror = False
        if mirror:
            painter.translate(size, 0.0)
            painter.scale(-1.0, 1.0)
        line = QtGui.QPen(color)
        line.setWidthF(2.4)
        line.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(line)
        for x, length in ((6.0, 15.0), (10.5, 15.0), (15.0, 9.0), (19.5, 15.0)):
            painter.drawLine(QtCore.QPointF(x, 5.5), QtCore.QPointF(x, 5.5 + length))

    def _draw_minus(self, painter, pen, color, size):
        line = QtGui.QPen(color)
        line.setWidthF(1.6)
        painter.setPen(line)
        painter.drawLine(QtCore.QPointF(6.0, 13.0), QtCore.QPointF(20.0, 13.0))

    def _draw_plus(self, painter, pen, color, size):
        line = QtGui.QPen(color)
        line.setWidthF(1.6)
        painter.setPen(line)
        painter.drawLine(QtCore.QPointF(6.0, 13.0), QtCore.QPointF(20.0, 13.0))
        painter.drawLine(QtCore.QPointF(13.0, 6.0), QtCore.QPointF(13.0, 20.0))

    def _draw_close(self, painter, pen, color, size):
        """Two thick diagonal lines with round ends (SSO v5.24 X button shape)."""
        line = QtGui.QPen(color)
        line.setWidthF(2.6)
        line.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(line)
        painter.drawLine(QtCore.QPointF(8.0, 8.0), QtCore.QPointF(18.0, 18.0))
        painter.drawLine(QtCore.QPointF(18.0, 8.0), QtCore.QPointF(8.0, 18.0))

    def _draw_rotate(self, painter, pen, color, size):
        """A very bold R. drawn rotated 90° clockwise when simple rotation R is on."""
        plain = False
        try:
            st = self._panel._ctrl.st
            plain = bool(st['rotate_latin']) and bool(st.get('rotate_plain'))
        except Exception:
            plain = False
        if plain:
            painter.translate(size / 2.0, size / 2.0)
            painter.rotate(90.0)
            painter.translate(-size / 2.0, -size / 2.0)
        path = _pp_fill_text(painter, 'R', 18, 99, color, size / 2.0, size / 2.0)
        outline = QtGui.QPen(color)
        outline.setWidthF(1.4)
        outline.setJoinStyle(QtCore.Qt.MiterJoin)
        painter.setPen(outline)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.drawPath(path)
        # when vertical writing glyphs (vert) are on, draws a short blue underline below the R.
        vert = False
        try:
            vert = bool(self._panel._ctrl.st.get('v_vert'))
        except Exception:
            vert = False
        if vert:
            painter.resetTransform()
            bar = QtGui.QPen(PP_color('accent'))
            bar.setWidthF(2.0)
            bar.setCapStyle(QtCore.Qt.RoundCap)
            painter.setPen(bar)
            painter.drawLine(QtCore.QPointF(size / 2.0 - 5.0, size - 2.5),
                             QtCore.QPointF(size / 2.0 + 5.0, size - 2.5))

    def _align_lines(self, painter, color, size, anchor):
        line = QtGui.QPen(color)
        line.setWidthF(2.2)
        line.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(line)
        unit = size / 26.0
        for y, length in ((6.5, 15.0), (11.0, 9.0), (15.5, 15.0), (20.0, 9.0)):
            y *= unit
            length *= unit
            if anchor == 'left':
                x0 = 5.0 * unit
            elif anchor == 'right':
                x0 = size - 5.0 * unit - length
            else:
                x0 = (size - length) / 2.0
            painter.drawLine(QtCore.QPointF(x0, y), QtCore.QPointF(x0 + length, y))

    def _draw_align_left(self, painter, pen, color, size):
        self._align_lines(painter, color, size, 'left')

    def _draw_align_center(self, painter, pen, color, size):
        self._align_lines(painter, color, size, 'center')

    def _draw_align_right(self, painter, pen, color, size):
        self._align_lines(painter, color, size, 'right')

    def _guide_frame(self, painter, color):
        frame = QtGui.QPen(PP_color('icon_off'))
        frame.setWidthF(1.0)
        painter.setPen(frame)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        rect = QtCore.QRectF(4.5, 6.5, 17.0, 13.0)
        painter.drawRect(rect)
        return rect

    def _draw_grid(self, painter, pen, color, size):
        line = QtGui.QPen(color)
        line.setWidthF(1.0)
        painter.setPen(line)
        left, top, w, h = 4.5, 6.5, 17.0, 13.0
        painter.drawRect(QtCore.QRectF(left, top, w, h))
        for i in range(1, 4):
            x = left + w * i / 4.0
            painter.drawLine(QtCore.QPointF(x, top), QtCore.QPointF(x, top + h))
        for i in range(1, 3):
            y = top + h * i / 3.0
            painter.drawLine(QtCore.QPointF(left, y), QtCore.QPointF(left + w, y))

    def _draw_edges(self, painter, pen, color, size):
        rect = QtCore.QRectF(4.5, 6.5, 17.0, 13.0)
        dotted = QtGui.QPen(PP_color('icon_off'))
        dotted.setWidthF(1.0)
        dotted.setStyle(QtCore.Qt.DotLine)
        painter.setPen(dotted)
        painter.drawLine(QtCore.QPointF(4.5, 6.5), QtCore.QPointF(21.5, 6.5))
        painter.drawLine(QtCore.QPointF(4.5, 19.5), QtCore.QPointF(21.5, 19.5))
        side = QtGui.QPen(color)
        side.setWidthF(1.4)
        painter.setPen(side)
        painter.drawLine(QtCore.QPointF(rect.left(), 6.5), QtCore.QPointF(rect.left(), 19.5))
        painter.drawLine(QtCore.QPointF(rect.right(), 6.5), QtCore.QPointF(rect.right(), 19.5))

    def _draw_center(self, painter, pen, color, size):
        self._guide_frame(painter, color)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(QtCore.QRectF(11.5, 3.5, 3.0, 19.0))

    def _draw_right(self, painter, pen, color, size):
        self._guide_frame(painter, color)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(QtCore.QRectF(20.0, 3.5, 3.0, 19.0))

    def _glyph_io_frame(self, painter, color, left_extend=0.0, pen_width=1.4):
        """Rectangle open in the middle of its left side (the arrow passes through this gap).
        moves the left side left by left_extend to widen the box (stroke width unchanged).
        pen_width sets the stroke width (Vertical mode icons keep the existing 1.4)."""
        line = QtGui.QPen(color)
        line.setWidthF(float(pen_width))
        line.setCapStyle(QtCore.Qt.RoundCap)
        line.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(line)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        left, top, right, bottom = 9.5, 6.5, 21.5, 19.5
        left -= float(left_extend)
        path = QtGui.QPainterPath()
        path.moveTo(QtCore.QPointF(left, 10.0))
        path.lineTo(QtCore.QPointF(left, top))
        path.lineTo(QtCore.QPointF(right, top))
        path.lineTo(QtCore.QPointF(right, bottom))
        path.lineTo(QtCore.QPointF(left, bottom))
        path.lineTo(QtCore.QPointF(left, 16.0))
        painter.drawPath(path)
        return line

    def _glyph_io_arrow(self, painter, line, head_left, x_out=3.5, head=3.2):
        """Accepts x_out (outer end) and head (arrowhead length). Vertical mode icons keep the existing values."""
        y = 13.0
        x_in = 16.0
        painter.setPen(line)
        painter.drawLine(QtCore.QPointF(x_out, y), QtCore.QPointF(x_in, y))
        tip = x_out if head_left else x_in
        back = head if head_left else -head
        painter.drawLine(QtCore.QPointF(tip, y), QtCore.QPointF(tip + back, y - 3.2))
        painter.drawLine(QtCore.QPointF(tip, y), QtCore.QPointF(tip + back, y + 3.2))

    def _draw_glyph_out(self, painter, pen, color, size):
        """Outward (left) arrow — puts the preview text into the Glyph Window."""
        line = self._glyph_io_frame(painter, color)
        self._glyph_io_arrow(painter, line, True)

    def _draw_glyph_in(self, painter, pen, color, size):
        """Inward (right) arrow — reads the Glyph Window text."""
        line = self._glyph_io_frame(painter, color, 1.0)   # widens the box 1px to the left.
        self._glyph_io_arrow(painter, line, False)

    def _draw_h_glyph_io(self, painter, pen, color, size):
        """Horizontal mode Glyph Import icon (inward arrow). Hovering with Ctrl/Alt held changes it to
        the glyph export shape (outward arrow). The stroke width matches the Horizontal mode icon row."""
        export = getattr(self, '_alt_shown', False) and bool(_v(self, 'underMouse', False))
        # for both import and export, moves the rectangle's left side 2px further left than import to enlarge the box.
        line = self._glyph_io_frame(painter, color, PP_H_GLYPH_IO_LEFT_EXTEND, PP_H_GLYPH_IO_PEN)
        if export:
            # So the arrowhead does not touch the widened box's left side, the arrow end moves 1px left and the arrowhead is drawn a little shorter.
            # the arrowhead looked overlapped with the box's left side, so the arrow head was moved 2px further left (x 2.5 → 0.5).
            self._glyph_io_arrow(painter, line, True, x_out=PP_H_GLYPH_OUT_TIP_X, head=3.0)
        else:
            self._glyph_io_arrow(painter, line, False)

    def _draw_user_text(self, painter, pen, color, size):
        """Arrow pointing up above a base — load saved text.
        Hovering with Alt held draws it flipped vertically (can save)."""
        if getattr(self, '_alt_shown', False) and bool(_v(self, 'underMouse', False)):
            painter.translate(0.0, size)
            painter.scale(1.0, -1.0)
            color = PP_color('accent')   # the flipped (save) state is blue
        line = QtGui.QPen(color)
        line.setWidthF(1.4)
        line.setCapStyle(QtCore.Qt.RoundCap)
        line.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(line)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        tray = QtGui.QPainterPath()
        tray.moveTo(QtCore.QPointF(6.5, 14.5))
        tray.lineTo(QtCore.QPointF(6.5, 20.5))
        tray.lineTo(QtCore.QPointF(19.5, 20.5))
        tray.lineTo(QtCore.QPointF(19.5, 14.5))
        painter.drawPath(tray)
        x = 13.0
        top, bottom = 5.5, 17.0
        painter.drawLine(QtCore.QPointF(x, bottom), QtCore.QPointF(x, top))
        painter.drawLine(QtCore.QPointF(x, top), QtCore.QPointF(x - 3.2, top + 3.2))
        painter.drawLine(QtCore.QPointF(x, top), QtCore.QPointF(x + 3.2, top + 3.2))


# ============================================================
# Border drag handle (Horizontal mode: top border, Vertical mode: left border)
# ============================================================
class PPSliderIcon(QtGui.QWidget):
    """Picture icon in front of the Size/Spacing/Leading sliders.
    A click increases the slider value; a click with Alt held decreases it.
    A right-click also decreases the value like Alt+click.
    While held, keeps changing the value in the same direction every 70ms starting after 400ms (click increases, right-click/Alt+click decreases).
    Click/right-click with Shift held (including holding) changes by 10x."""

    def __init__(self, kind, parent):
        QtGui.QWidget.__init__(self, parent)
        self._kind = kind
        self._slider = None
        self._repeat_timer = None   # repeat timer while held (owned by the widget)
        self._repeat_sign = 0       # repeat direction (+1 increase, -1 decrease)
        self._repeat_mult = 1       # repeat multiplier (10 when pressed with Shift held)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, True)
        self._scale = float(PP_SLIDER_ICON_SCALE.get(kind, 1.0))
        side = int(round(PP_SLIDER_ICON * self._scale))
        self.setFixedSize(side, side)
        self.setStyleSheet('background:transparent; border:none;')

    def set_slider(self, slider):
        self._slider = slider

    def mousePressEvent(self, event):
        event.accept()
        slider = self._slider
        button = _v(event, 'button')
        if slider is None or button not in (QtCore.Qt.LeftButton, QtCore.Qt.RightButton):
            return
        # a right-click (including macOS Control+click) also decreases the value like Alt+click.
        sign = 1
        try:
            if (button == QtCore.Qt.RightButton
                    or _modifiers_int(event) & int(QtCore.Qt.AltModifier)):
                sign = -1
        except Exception:
            pass
        # pressing with Shift held changes by 10x (also used for hold-to-repeat).
        mult = 1
        try:
            if _modifiers_int(event) & int(QtCore.Qt.ShiftModifier):
                mult = PP_SLIDER_ICON_SHIFT_MULT
        except Exception:
            pass
        if not self._step_value(sign, mult):
            self._stop_repeat()
            return
        # while held, repeats in the same direction every 70ms starting after 400ms.
        #        The direction decided at press time is kept (releasing or pressing Alt during the repeat does not change it).
        self._repeat_sign = sign
        self._repeat_mult = mult   
        timer = self._repeat_timer
        if timer is None:
            timer = QtCore.QTimer(self)
            timer.timeout.connect(self._repeat_tick)
            self._repeat_timer = timer
        timer.setInterval(400)
        timer.start()

    def _step_value(self, sign, mult=1):
        """Changes the slider value by one step. False if it cannot change further at the end of the range.
        Changes by mult times (Shift is 10x). Stops at the end of the range if it would go beyond."""
        slider = self._slider
        if slider is None:
            return False
        try:
            low = int(_v(slider, 'minimum', 0))
            high = int(_v(slider, 'maximum', 100))
            current = int(_v(slider, 'value', 0))
            step = max(1, int(round((high - low) * PP_SLIDER_ICON_STEP_RATIO)))
            value = max(low, min(high, current + step * sign * int(mult)))
            if value == current:
                return False
            slider.setValue(value)
            return True
        except Exception as error:
            print('%s Slider icon error: %s' % (PP_LOG, error))
            return False

    def _repeat_tick(self):
        """Keeps changing the value while held. Stops when the button is released or at the end of the range."""
        timer = self._repeat_timer
        if timer is None:
            return
        try:
            buttons = QtGui.QApplication.mouseButtons()
            if not ((buttons & QtCore.Qt.LeftButton) or (buttons & QtCore.Qt.RightButton)):
                timer.stop()
                return
        except Exception:
            pass
        timer.setInterval(70)
        if not self._step_value(self._repeat_sign, self._repeat_mult):
            timer.stop()

    def _stop_repeat(self):
        timer = self._repeat_timer
        if timer is not None:
            timer.stop()

    def mouseReleaseEvent(self, event):
        event.accept()
        self._stop_repeat()   

    def hideEvent(self, event):
        self._stop_repeat()   # stops the repeat when hidden.

    def mouseDoubleClickEvent(self, event):
        # Even on a fast double click, the second click is applied once more.
        self.mousePressEvent(event)

    def contextMenuEvent(self, event):
        # right-click is used to decrease the value, so it is not passed to the parent widget's context menu.
        event.accept()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.scale(self._scale, self._scale)   # draws the 24px reference drawing scaled down by the factor.
            color = PP_color('label')
            size = float(PP_SLIDER_ICON)
            if self._kind == 'size':
                # A large T and a small T (baseline aligned)
                big = QtGui.QFont()
                big.setPixelSize(19)
                big.setBold(True)
                small = QtGui.QFont()
                small.setPixelSize(11)
                small.setBold(True)
                path = QtGui.QPainterPath()
                path.addText(QtCore.QPointF(1.0, 19.5), big, 'T')
                path.addText(QtCore.QPointF(13.5, 19.5), small, 'T')
                painter.fillPath(path, QtGui.QBrush(color))
            elif self._kind == 'spacing':
                # A T on top and a left/right arrow below
                path = _pp_fill_text(painter, 'T', 15, 87, color, size / 2.0, 7.5)
                line = QtGui.QPen(color)
                line.setWidthF(1.8)
                line.setCapStyle(QtCore.Qt.RoundCap)
                painter.setPen(line)
                y = 19.5
                painter.drawLine(QtCore.QPointF(3.0, y), QtCore.QPointF(size - 3.0, y))
                for tip, direction in ((3.0, 1.0), (size - 3.0, -1.0)):
                    painter.drawLine(QtCore.QPointF(tip, y),
                                     QtCore.QPointF(tip + 3.5 * direction, y - 3.0))
                    painter.drawLine(QtCore.QPointF(tip, y),
                                     QtCore.QPointF(tip + 3.5 * direction, y + 3.0))
            else:
                # Up/down arrow and three horizontal lines
                line = QtGui.QPen(color)
                line.setWidthF(1.8)
                line.setCapStyle(QtCore.Qt.RoundCap)
                painter.setPen(line)
                x = 5.0
                painter.drawLine(QtCore.QPointF(x, 3.0), QtCore.QPointF(x, size - 3.0))
                for tip, direction in ((3.0, 1.0), (size - 3.0, -1.0)):
                    painter.drawLine(QtCore.QPointF(x, tip),
                                     QtCore.QPointF(x - 3.0, tip + 3.5 * direction))
                    painter.drawLine(QtCore.QPointF(x, tip),
                                     QtCore.QPointF(x + 3.0, tip + 3.5 * direction))
                painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                painter.setBrush(QtGui.QBrush(color))
                for y in (5.0, 10.5, 16.0):
                    painter.drawRect(QtCore.QRectF(10.0, y, size - 12.0, 3.0))
        finally:
            painter.end()


class PPSlider(QtGui.QSlider):
    """Horizontal slider that returns to the default value when the handle is double-clicked."""

    def __init__(self, parent, default_value):
        QtGui.QSlider.__init__(self, QtCore.Qt.Horizontal, parent)
        self._default_value = int(default_value)

    def mouseDoubleClickEvent(self, event):
        try:
            x, _y = _event_xy(event)
            low = int(_v(self, 'minimum', 0))
            high = int(_v(self, 'maximum', 100))
            current = int(_v(self, 'value', 0))
            width = float(_int(self, 'width'))
            handle = 16.0   # QSS handle 14px + border 1px×2
            ratio = 0.0 if high == low else float(current - low) / float(high - low)
            handle_center = handle / 2.0 + ratio * max(0.0, width - handle)
            if abs(x - handle_center) <= handle / 2.0 + 3.0:
                self.setValue(self._default_value)
                event.accept()
                return
        except Exception:
            pass
        QtGui.QSlider.mouseDoubleClickEvent(self, event)


class PPResizeHandle(QtGui.QWidget):

    def __init__(self, panel, drag_callback):
        QtGui.QWidget.__init__(self, panel)
        self._panel = panel
        self._drag_callback = drag_callback
        self._orientation = 'h'
        self._press = None
        self._press_size = None
        self._cursor_pushed = False
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, True)
        self.setStyleSheet('background:transparent; border:none;')
        self.set_orientation('h')

    def _cursor_shape(self):
        return QtCore.Qt.SizeVerCursor if self._orientation == 'h' else QtCore.Qt.SizeHorCursor

    def enterEvent(self, event):
        pp_push_handle_cursor(self, self._cursor_shape())

    def leaveEvent(self, event):
        if self._press is None:  # while dragging, kept even outside the handle.
            pp_pop_handle_cursor(self)

    def set_orientation(self, orientation):
        if orientation != self._orientation and getattr(self, '_cursor_pushed', False):
            pp_pop_handle_cursor(self)
        self._orientation = orientation
        self.setCursor(QtCore.Qt.SizeVerCursor if orientation == 'h'
                       else QtCore.Qt.SizeHorCursor)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            # The drag area is left transparent and only the border line with the Glyph Window is shown.
            if self._orientation == 'h':
                painter.fillRect(0, 0, _int(self, 'width'), 1, PP_color('divider'))
            else:
                painter.fillRect(0, 0, 1, _int(self, 'height'), PP_color('divider'))
        finally:
            painter.end()

    def mousePressEvent(self, event):
        event.accept()
        if _v(event, 'button') != QtCore.Qt.LeftButton:
            return
        gx, gy = _event_global_xy(event)
        self._press = gy if self._orientation == 'h' else gx
        if self._orientation == 'h':
            self._press_size = _int(self._panel, 'height')
        else:
            self._press_size = _int(self._panel, 'width')
        try:
            self.grabMouse()
        except Exception:
            pass

    def mouseMoveEvent(self, event):
        event.accept()
        if self._press is None:
            return
        gx, gy = _event_global_xy(event)
        current = gy if self._orientation == 'h' else gx
        self._drag_callback(self._press_size - (current - self._press))

    def mouseReleaseEvent(self, event):
        event.accept()
        self._press = None
        self._press_size = None
        try:
            self.releaseMouse()
        except Exception:
            pass
        if not pp_cursor_inside(self):
            pp_pop_handle_cursor(self)

    def hideEvent(self, event):
        self._press = None
        self._press_size = None
        pp_pop_handle_cursor(self)


# ============================================================
# Preview canvas (Horizontal/Vertical drawing, Vertical mode text input)
# ============================================================
class PPCanvasEventFilter(QtGui.QWidget):
    """Hidden filter receiving the canvas's key/IME/focus events (same local filter as Hangeul Input Tool)."""

    def __init__(self, canvas):
        QtGui.QWidget.__init__(self, canvas)
        self.hide()
        self._canvas = canvas

    def eventFilter(self, watched, event):
        canvas = self._canvas
        if canvas is None:
            return False
        try:
            return bool(canvas.filter_event(event))
        except Exception as error:
            print('%s Input handling error: %s' % (PP_LOG, error))
            return False


class PPAppKeyFilter(QtGui.QWidget):
    """Key filter installed on QApplication only while typing. Intercepts only key/IME events going to the canvas."""

    def __init__(self, canvas):
        QtGui.QWidget.__init__(self, canvas)
        self.hide()
        self._canvas = canvas
        self._types = (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease,
                       QtCore.QEvent.ShortcutOverride, QtCore.QEvent.InputMethod)

    def eventFilter(self, watched, event):
        canvas = self._canvas
        if canvas is None:
            return False
        try:
            event_type = event.type()
            if event_type not in self._types:
                return False
            if watched is not canvas and not _same_widget(watched, canvas):
                return False
            if not canvas.is_editing():
                return False
            if event_type == QtCore.QEvent.KeyRelease:
                # Releases of keys being typed are not passed to FontLab's app filter either (except command shortcuts).
                return not bool(canvas._command_modifiers(event))
            return bool(canvas.filter_event(event, source='app'))
        except Exception as error:
            print('%s Input handling error: %s' % (PP_LOG, error))
            return False


class PPPreviewCanvas(QtGui.QWidget):

    def __init__(self, panel):
        QtGui.QWidget.__init__(self, panel)
        self._panel = panel
        self._ctrl = panel._ctrl
        self._st = panel._ctrl.st
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._cells = []
        self._pre_cells = []
        self._cell_kind = 'glyph'
        self._metrics = (1000.0, 800.0, -200.0)
        self._scroll_v = 0.0
        self._scroll_y = 0.0            # vertical scroll of the Vertical mode Interpolation / All Masters views
        self._pan_x = 0.0               # Horizontal mode panning (Space+drag, wheel)
        self._pan_y = 0.0
        self._h_overflow = (False, False)
        self._overflow_reported = None
        self._panning = None
        self._v_panning = None          # Vertical mode Space+drag panning (start global position, start scroll value)
        self._cursor_pushed = False
        self._anchor = None             # block selection start point (None means no block)
        self._selecting = False
        self._app_filter_on = False
        self._vl = None
        self._hl = None                 # Horizontal mode text layout
        self._cursor = len(self._tokens())
        self._editing = False
        self._preedit = ''
        self._caret_on = True
        self._pending_commit = ''
        self._pending_native = ''
        self._ignored_commit = ''
        self._pending_deadline = 0.0
        self._reported = set()
        self._drag_guide = None         # guideline being dragged from the Ruler (kind, x, y)
        self._guide_hold = None         # preview guideline grabbed and being dragged
        self._guide_hover_axis = None   # direction of the guideline showing the handle cursor ('x'/'y')
        self.setMouseTracking(True)     # handle cursor over guidelines
        self._caret_timer = QtCore.QTimer(self)
        self._caret_timer.setInterval(PP_CARET_BLINK_MS)
        self._caret_timer.timeout.connect(self._blink)
        self._filter = PPCanvasEventFilter(self)
        self.installEventFilter(self._filter)
        self._app_filter = PPAppKeyFilter(self)

    # ── Data ───────────────────────────────────────────────
    def _mode(self):
        return self._st['mode']

    def _tokens(self):
        """List of text tokens to edit/show. Horizontal mode uses the horizontal text (not written to the settings file),
        Vertical mode uses the Vertical mode text."""
        if self._mode() == 'h':
            return self._ctrl.h_text
        return self._st['v_text']

    def _h_text_on(self):
        """Whether Horizontal mode is showing text (text read from the Glyph Window or typed directly)."""
        return self._mode() == 'h' and bool(getattr(self._ctrl, 'h_text_on', False))

    def rebuild(self):
        cache = self._ctrl.font_cache
        # during a font-switch transition, FontLab objects are not accessed and the current screen is kept.
        #   The signature is cleared so the refresh timer rebuilds it after the transition.
        if pp_fonts_settling():
            self._ctrl._last_sig = None
            return
        try:
            font, glyph_name, fl_glyph, master = pp_active_glyph_info(cache)
        except Exception:
            font, glyph_name, fl_glyph, master = None, None, None, None
        if font is None:
            self._cells = []
            self._pre_cells = []
            self.update()
            return
        try:
            self._metrics = cache.get_metrics(font)
        except Exception:
            self._metrics = (1000.0, 800.0, -200.0)
        view = self._st['h_view'] if self._mode() == 'h' else self._ctrl.v_view
        if getattr(self, '_last_scroll_view', None) != (self._mode(), view):
            self._last_scroll_view = (self._mode(), view)
            self._scroll_y = 0.0        # resets the vertical scroll when the view changes.
        try:
            # when Horizontal mode is showing text, builds text cells like the Vertical mode user text.
            if (self._mode() == 'h' and not self._h_text_on()) or (self._mode() == 'v' and view):
                self._cell_kind = 'glyph'
                self._cells = self._glyph_view_cells(font, glyph_name, fl_glyph, master, view)
                self._pre_cells = []
            else:
                self._cell_kind = 'text'
                self._cells = self._text_cells(font, master)
                self._pre_cells = self._char_cells(font, master, self._preedit)
        except Exception:
            traceback.print_exc()
            self._cells = []
        self.update()

    def _glyph_char(self, font, glyph_name):
        try:
            fg = font[glyph_name]
            codes = list(_v(fg, 'unicodes') or [])
            if codes:
                return chr(int(codes[0]))
        except Exception:
            pass
        return None

    def _rotate_for(self, char):
        if self._mode() == 'v' and bool(self._st.get('v_vert')) and char:
            # underlined R (show the font's settings as is) decides rotation by UAX #50 regardless of the R state.
            #   Characters changed into vertical writing glyphs are set upright again in _make_cell.
            try:
                return len(char) == 1 and pp_uax50_rotate(ord(char))
            except Exception:
                return False
        if self._mode() != 'v' or not self._st['rotate_latin'] or not char:
            return False
        try:
            code = ord(char)
        except Exception:
            return False
        return not pp_keep_upright(code, bool(self._st.get('rotate_plain')))

    def _make_cell(self, item, char, ti=None, pre=False, vert=False, vadv=None, rot=None):
        upm = self._metrics[0]
        if item is None:
            return {'paths': [], 'adv': upm * 0.6, 'rot': False, 'char': char,
                    'missing': True, 'ti': ti, 'pre': pre}
        paths, adv = item
        if adv <= 0:
            adv = upm * 0.6
        cell = {'paths': paths, 'adv': adv, 'rot': self._rotate_for(char), 'char': char,
                'missing': False, 'ti': ti, 'pre': pre}
        if vert:
            # vertical writing glyphs are already designed for vertical writing, so they are not rotated.
            cell['vert'] = True
            cell['rot'] = False
        if rot is not None:
            # underlined R follows the rotation decided by _token_item (stylistic set glyphs are rotated too if the character is an R character).
            cell['rot'] = bool(rot)
        # vadv = (vertical Advance, vertical origin Y, Top Side Bearing)
        advance, origin, tsb = vadv if isinstance(vadv, tuple) else (vadv, None, None)
        if advance is not None and advance > 0:
            cell['vadv'] = float(advance)   # cell height of an upright character (vertical Advance)
            if origin is None and tsb is not None:
                # in fonts without VORG (TTF etc.), the vertical origin is the top of the glyph outline + Top Side Bearing.
                top_y = None
                for path in paths or []:
                    try:
                        rect = path.boundingRect()
                        if float(_v(rect, 'width', 0.0)) <= 0 and float(_v(rect, 'height', 0.0)) <= 0:
                            continue
                        value = float(_v(rect, 'y', 0.0)) + float(_v(rect, 'height', 0.0))
                    except Exception:
                        continue
                    top_y = value if top_y is None else max(top_y, value)
                if top_y is not None:
                    origin = top_y + float(tsb)
            if origin is not None:
                cell['vorg'] = float(origin)   # glyph Y (vertical origin) placed at the top edge of the cell
        return cell

    def _vert_on(self):
        """Whether Vertical mode applies OpenType vertical writing glyphs (vert) and vertical Advance."""
        return self._mode() == 'v' and bool(self._st.get('v_vert'))

    def _glyph_view_cells(self, font, glyph_name, fl_glyph, master, view):
        cache = self._ctrl.font_cache
        if not glyph_name:
            return []
        char = self._glyph_char(font, glyph_name)
        cells = []
        if view == 'masters':
            for name in cache.masters:
                cells.append(self._make_cell(cache.master_item(font, glyph_name, name), char))
        elif view == 'interp':
            # if there is no #instance layer (incompatible masters) or no instance info in Font Info so
            #   interpolation is impossible, shows the single active glyph (active master) instead of an empty screen.
            # if Font Info > Axes has several axes, interpolates only along the Weight (wt) axis (other axes at the active master location).
            specs = []
            has_instance = fl_glyph is not None and pp_glyph_has_instance_layer(fl_glyph)
            interpolated = False
            # All Instances preview (Interpolation button Ctrl/Alt+click). If there are no results at all, falls through to the method below.
            if has_instance and self._ctrl.interp_all.get(self._mode()):
                axis_codes = list(cache.get_axes(font))   # for per-axis group sorting, (axis name, axis tag)
                for spec in pp_instance_all_specs(font, axis_codes):
                    item = cache.all_instance_item(font, glyph_name, spec)
                    cell = self._make_cell(item, char)
                    if item is None:
                        cell['missing'] = False  # failed interpolation slots are left empty.
                    else:
                        interpolated = True
                    cells.append(cell)
                if not interpolated:
                    cells = []
            # with several axes and the VARIATIONS panel open, other axes follow the panel values and
            #   Weight steps are drawn with FontLab's own interpolation. If there are no results at all, falls through to the v1.65 method below.
            place = cache.variation_place(font) if (has_instance and not interpolated) else None
            if place is not None:
                for spec in pp_instance_specs_at(font, place[0].lower(), place[1]):
                    item = cache.variation_item(font, glyph_name, spec['weight'], place)
                    cell = self._make_cell(item, char)
                    if item is None:
                        cell['missing'] = False  # failed interpolation slots are left empty.
                    else:
                        interpolated = True
                    cells.append(cell)
                if not interpolated:
                    cells = []
            if not interpolated:
                group = cache.weight_group(font, master)
                if has_instance:
                    specs = pp_instance_specs(font, group)
                for spec in specs:
                    item = cache.interp_item(font, glyph_name, spec['weight'], group)
                    cell = self._make_cell(item, char)
                    if item is None:
                        cell['missing'] = False  # failed interpolation slots are left empty.
                    else:
                        interpolated = True
                    cells.append(cell)
            if not interpolated:
                cells = []
                if master:
                    cells.append(self._make_cell(cache.master_item(font, glyph_name, master), char))
        else:
            if master:
                cells.append(self._make_cell(cache.master_item(font, glyph_name, master), char))
        if self._mode() == 'v':
            # the Vertical mode Interpolation / All Masters views keep all characters upright regardless of R selection.
            for cell in cells:
                cell['rot'] = False
        return cells

    def _token_item(self, font, master, token):
        """(item, char, vert, vadv, rot). vert = whether changed into a vertical writing glyph, vadv = vertical Advance.
        rot = rotation decided under underlined R (None means the existing rules). Like InDesign / CSS mixed,
          UAX #50 R (Latin, digits, half-width punctuation) is typeset like horizontal writing (only the stylistic set, without vert) then rotated 90°,
          U gets vert (+stylistic set) and stays upright, Tr stays upright if a vert glyph exists and is rotated otherwise."""
        cache = self._ctrl.font_cache
        vert_on = self._vert_on()
        vert = False
        rot = None
        if token.startswith('/') and len(token) > 1:
            name = token[1:]
            char = self._glyph_char(font, name)
        else:
            name = cache.glyph_name_for_char(font, token)
            char = token
            if vert_on and name and master and len(token) == 1:
                # glyphs specified directly with '/glyphname' are not changed.
                kind = pp_uax50_class(ord(token))
                if kind == 'R':
                    rot = True
                elif kind == 'Tr':
                    rot = not cache.has_vert_glyph(font, name)
                else:
                    rot = False
                alt = cache.vert_glyph_name(font, name, rotated=rot)
                if alt:
                    alt_item = cache.master_item(font, alt, master)
                    if alt_item is not None:
                        name = alt
                        vert = True
        item = cache.master_item(font, name, master) if (name and master) else None
        vadv = None
        if vert_on and item is not None and not rot:
            vadv = cache.vertical_metrics(font, name, master)   # (Advance, origin Y, TSB)
        return item, char, vert, vadv, rot

    def _text_cells(self, font, master):
        cells = []
        # attaching full stops/commas to the right/left of the column was replaced by the vertical writing punctuation rules.
        use_rules = (self._mode() == 'v' and bool(self._st['rotate_latin'])
                     and not bool(self._st.get('rotate_plain')))   # simple rotation R does not apply the rules
        if self._vert_on():
            use_rules = False   # underlined R does not apply punctuation rules the font itself does not apply.
        rules = self._st.get('v_punct_rules') or {}
        alt_counts = {}   # occurrence count per straight quote kind (odd = opening, even = closing)
        previous = None   # the immediately preceding character (none after a line break)
        for ti, token in enumerate(self._tokens()):
            if token == '\n':
                cells.append({'nl': True, 'ti': ti})
                previous = None
                continue
            item, char, vert, vadv, rot = self._token_item(font, master, token)
            if item is None and token.startswith('/'):
                char = token[1:]
            cell = self._make_cell(item, char, ti=ti, vert=vert, vadv=vadv, rot=rot)
            # punctuation rules are not applied to characters changed into vertical writing glyphs.
            if use_rules and not cell.get('missing') and not vert and len(token) == 1:
                self._apply_punct_rule(cell, font, master, token, rules, alt_counts, previous)
            cells.append(cell)
            previous = char if (char and len(char) == 1) else None
        return cells

    def _apply_punct_rule(self, cell, font, master, token, rules, alt_counts, previous=None):
        """Applies the vertical writing punctuation rules only to the display form (cell). The source text is left as is."""
        rule = rules.get(token)
        if not rule:
            return
        skip_after = rule.get('skip_after')
        if skip_after and previous and pp_is_latin_or_digit(previous, skip_after):
            return   # after Latin/digits the rule is not used, and it is shown by the default R rule (like Latin).
        alternate = rule.get('alternate')
        if alternate:
            count = alt_counts.get(token, 0) + 1
            alt_counts[token] = count
            rule = rules.get(alternate[0] if count % 2 == 1 else alternate[1])
            if not rule:
                return
        replace = rule.get('replace')
        if replace:
            cache = self._ctrl.font_cache
            name = cache.glyph_name_for_char(font, replace)
            item = cache.master_item(font, name, master) if (name and master) else None
            if item is not None:
                paths, adv = item
                if adv <= 0:
                    adv = self._metrics[0] * 0.6
                cell['paths'] = paths
                cell['adv'] = adv
            # If there is no replacement glyph, shows the original mark (rotation and Mozum still apply).
        rotate = rule.get('rotate')
        if rule.get('move') == 'mozum':
            cell['rot'] = False
            cell['vform'] = 'mozum'
        elif rotate == 90:
            cell['rot'] = True
            if rule.get('align') == 'center':
                cell['rot_center'] = True   # rotated outline center at the cell center
        elif rotate == 180:
            cell['rot'] = False
            cell['vform'] = 'r180'
        elif rotate == 0 or rule.get('align') == 'center':
            cell['rot'] = False
            if rule.get('align') == 'center':
                cell['vform'] = 'center'

    def _char_cells(self, font, master, text):
        cells = []
        for char in text or '':
            item, _char, vert, vadv, rot = self._token_item(font, master, char)
            cells.append(self._make_cell(item, char, pre=True, vert=vert, vadv=vadv, rot=rot))
        return cells

    # ── Drawing ───────────────────────────────────────────────
    def _ink(self, cell):
        return PP_color('preedit') if cell.get('pre') else PP_color('ink')

    def _fill_cell(self, painter, cell, transform):
        brush = QtGui.QBrush(self._ink(cell))
        for path in cell.get('paths') or []:
            try:
                painter.fillPath(transform.map(path), brush)
            except Exception:
                continue

    def _draw_missing(self, painter, cell, rect, em):
        text = cell.get('char') or ''
        if not text:
            return
        font = QtGui.QFont()
        font.setPixelSize(max(6, int(em * 0.6)))
        painter.setFont(font)
        painter.setPen(QtGui.QPen(PP_color('preedit') if cell.get('pre') else PP_color('missing')))
        painter.drawText(rect, int(QtCore.Qt.AlignCenter), text)

    def _draw_punct(self, painter, cell, center, col_w, top, cell_h, scale, em, asc, desc):
        """Draws full stops/commas attached to the right or left end of the column based on the glyph outline."""
        box = None
        for path in cell.get('paths') or []:
            try:
                rect = path.boundingRect()
                x0 = float(_v(rect, 'x', 0.0))
                y0 = float(_v(rect, 'y', 0.0))
                w = float(_v(rect, 'width', 0.0))
                h = float(_v(rect, 'height', 0.0))
            except Exception:
                continue
            if w <= 0 and h <= 0:
                continue
            item = (x0, y0, x0 + w, y0 + h)
            box = item if box is None else (min(box[0], item[0]), min(box[1], item[1]),
                                            max(box[2], item[2]), max(box[3], item[3]))
        if box is None:
            return
        if cell['punct'] == 'right':
            left = center + col_w / 2.0 - box[2] * scale
        else:
            left = center - col_w / 2.0 - box[0] * scale
        if cell.get('punct_short'):
            baseline = top + cell_h / 2.0 + (box[1] + box[3]) / 2.0 * scale
        else:
            baseline = top + em * (asc / (asc - desc))
        self._fill_cell(painter, cell, QtGui.QTransform(scale, 0.0, 0.0, -scale, left, baseline))

    @staticmethod
    def _cell_ink_box(cell):
        box = None
        for path in cell.get('paths') or []:
            try:
                rect = path.boundingRect()
                x0 = float(_v(rect, 'x', 0.0))
                y0 = float(_v(rect, 'y', 0.0))
                w = float(_v(rect, 'width', 0.0))
                h = float(_v(rect, 'height', 0.0))
            except Exception:
                continue
            if w <= 0 and h <= 0:
                continue
            item = (x0, y0, x0 + w, y0 + h)
            box = item if box is None else (min(box[0], item[0]), min(box[1], item[1]),
                                            max(box[2], item[2]), max(box[3], item[3]))
        return box

    def _draw_vform(self, painter, cell, center, top, cell_h, scale, em, asc, desc):
        """Display form of the vertical writing punctuation rules (180° rotation, Mozum, glyph frame center).
        Glyph center = (Advance Width / 2, (Ascender + Descender) / 2)."""
        adv = float(cell['adv'])
        mid = (asc + desc) / 2.0
        baseline = top + em * (asc / (asc - desc))
        left = center - adv * scale / 2.0
        form = cell.get('vform')
        if form == 'r180':
            # (x, y) → (adv - x, 2·mid - y), then set upright
            transform = QtGui.QTransform(-scale, 0.0, 0.0, scale,
                                         left + adv * scale, baseline - 2.0 * mid * scale)
        else:
            box = self._cell_ink_box(cell)
            if box is None:
                return
            ax = (box[0] + box[2]) / 2.0
            ay = (box[1] + box[3]) / 2.0
            if form == 'mozum':
                # Moves the outline center to the opposite side of the glyph center (shape unchanged).
                dx = 2.0 * (adv / 2.0 - ax)
                dy = 2.0 * (mid - ay)
            else:
                # Glyph frame center: aligns the outline center with the glyph center.
                dx = adv / 2.0 - ax
                dy = mid - ay
            transform = QtGui.QTransform(scale, 0.0, 0.0, -scale,
                                         left + dx * scale, baseline - dy * scale)
        self._fill_cell(painter, cell, transform)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            width = float(_int(self, 'width'))
            height = float(_int(self, 'height'))
            painter.fillRect(QtCore.QRectF(0.0, 0.0, width, height), PP_color('background'))
            if self._mode() == 'h':
                self._paint_h(painter, width, height)
            else:
                self._paint_v(painter, width, height)
        except Exception:
            traceback.print_exc()
        finally:
            painter.end()

    def _fit_mode(self):
        """Horizontal mode size fit ('width' | 'height'). dock_fit in the Dock state, h_fit in the Floating state."""
        if self._panel.is_docked():
            return self._st.get('dock_fit', 'width')
        return self._st.get('h_fit', 'height')

    def _paint_h(self, painter, width, height):
        if self._cell_kind == 'text' and self._h_text_on():
            self._paint_h_text(painter, width, height)   
            return
        cells = self._cells
        if not cells:
            return
        upm, asc, desc = self._metrics
        side = float(PP_SIDE_MARGIN)
        available = max(1.0, width - 2.0 * side)
        # the default size is the zoom at which the glyph frame height (Ascender + |Descender|) fills the glyph area height.
        #        It is independent of glyph outlines and Advance Width, so the displayed size does not vary per glyph.
        frame_h = float(asc - desc)
        fit = height * PP_H_FILL_RATIO / frame_h
        center_y = (asc + desc) / 2.0
        # the width limit is also computed as number of glyphs × glyph frame height instead of the actual sum of Advance Widths.
        total_units = frame_h * len(cells)
        # if the actual sum of Advance Widths is larger than the estimate (wide glyphs), fits to the actual sum so it does not exceed the window.
        real_units = 0.0
        for cell in cells:
            try:
                real_units += float(cell.get('adv', 0) or 0)
            except Exception:
                pass
        all_instances = (self._st.get('h_view') == 'interp' and bool(self._ctrl.interp_all.get('h')))
        if all_instances and real_units > 0:
            total_units = real_units
        else:
            total_units = max(total_units, real_units)
        dock_fit = self._fit_mode()   # follows the Fit Height/Width button in the Floating state too.
        if dock_fit == 'width' and total_units > 0:
            fit = min(fit, available / total_units)
        elif dock_fit == 'height':
            pass                                   # maximum for the window height (width may overflow)
        elif total_units > 0 and total_units * fit > available:
            fit = available / total_units
        scale = fit * float(self._st[self._ctrl.h_zoom_key()])   # per-view zoom
        widths = [cell['adv'] * scale for cell in cells]
        total = sum(widths)
        content_h = frame_h * scale         # based on the glyph frame height
        overflow_x = total > available + 0.5
        overflow_y = content_h > height + 0.5
        self._h_overflow = (overflow_x, overflow_y)
        self._notify_overflow(overflow_x)
        if not overflow_x:
            self._pan_x = 0.0
            x = (width - total) / 2.0
        else:
            align = self._st.get('h_align', 'center')
            if align == 'left':
                base_x = side
            elif align == 'right':
                base_x = width - side - total
            else:
                base_x = (width - total) / 2.0
            x = max(width - side - total, min(side, base_x + self._pan_x))
            self._pan_x = x - base_x
        if not overflow_y:
            self._pan_y = 0.0
        else:
            limit_y = (content_h - height) / 2.0 + 8.0
            self._pan_y = max(-limit_y, min(limit_y, self._pan_y))
        baseline = height / 2.0 + center_y * scale + self._pan_y
        for cell, cell_width in zip(cells, widths):
            if cell.get('missing'):
                em = upm * scale
                self._draw_missing(painter, cell,
                                   QtCore.QRectF(x, baseline - asc * scale, cell_width, em), em)
            else:
                self._fill_cell(painter, cell, QtGui.QTransform(scale, 0.0, 0.0, -scale, x, baseline))
            x += cell_width

    # ── Horizontal mode text (text read from the Glyph Window or typed directly) ─────
    def _layout_h_text(self, width, height):
        """Horizontal mode text layout. Pressing Enter starts a new line below.
        The size follows the same rule as the Horizontal mode glyph view (glyph frame height fills the window height, fits the width if it overflows)."""
        upm, asc, desc = self._metrics
        frame_h = float(asc - desc)
        if frame_h <= 0:
            frame_h = float(upm)
        side = float(PP_SIDE_MARGIN)
        available = max(1.0, width - 2.0 * side)
        gap_units = frame_h * PP_H_TEXT_LINE_GAP
        lines = [[]]            # per line [(cell, x units, width units)]
        line_w = [0.0]
        carets_u = {}           # token index → (line, x units)
        cur_x = 0.0
        for cell in self._sequence_v():
            ti = cell.get('ti')
            if ti is not None:
                carets_u[ti] = (len(lines) - 1, cur_x)
            if cell.get('nl'):
                lines.append([])
                line_w.append(0.0)
                cur_x = 0.0
                continue
            adv = float(cell.get('adv', 0) or 0)
            lines[-1].append((cell, cur_x, adv))
            cur_x += adv
            line_w[-1] = cur_x
        carets_u[len(self._tokens())] = (len(lines) - 1, cur_x)
        n_lines = len(lines)
        block_units_h = n_lines * frame_h + (n_lines - 1) * gap_units
        max_w = max(line_w) if line_w else 0.0
        fit = height * PP_H_FILL_RATIO / block_units_h
        dock_fit = self._fit_mode()   # follows the Fit Height/Width button in the Floating state too.
        if dock_fit == 'width' and max_w > 0:
            fit = min(fit, available / max_w)
        elif dock_fit == 'height':
            pass                                   # maximum for the window height (width may overflow)
        elif max_w > 0 and max_w * fit > available:
            fit = available / max_w
        scale = fit * float(self._st[self._ctrl.h_zoom_key()])   # per-view zoom
        block_w = max_w * scale
        block_h = block_units_h * scale
        overflow_x = block_w > available + 0.5
        overflow_y = block_h > height + 0.5
        self._h_overflow = (overflow_x, overflow_y)
        self._notify_overflow(overflow_x)
        align = 'center'
        if not overflow_x:
            self._pan_x = 0.0
            block_x = (width - block_w) / 2.0
        else:
            align = self._st.get('h_align', 'center')
            if align == 'left':
                base_x = side
            elif align == 'right':
                base_x = width - side - block_w
            else:
                base_x = (width - block_w) / 2.0
            block_x = max(width - side - block_w, min(side, base_x + self._pan_x))
            self._pan_x = block_x - base_x
        if not overflow_y:
            self._pan_y = 0.0
        else:
            limit_y = (block_h - height) / 2.0 + 8.0
            self._pan_y = max(-limit_y, min(limit_y, self._pan_y))
        top = (height - block_h) / 2.0 + self._pan_y
        line_h = frame_h * scale
        pitch = (frame_h + gap_units) * scale
        line_x = []
        line_top = []
        placed = []
        for index, items in enumerate(lines):
            width_px = line_w[index] * scale
            if align == 'left':
                x0 = block_x
            elif align == 'right':
                x0 = block_x + block_w - width_px
            else:
                x0 = block_x + (block_w - width_px) / 2.0
            y0 = top + index * pitch
            line_x.append(x0)
            line_top.append(y0)
            for cell, x_units, adv in items:
                placed.append((cell, x0 + x_units * scale, y0, adv * scale))
        carets = {}
        for ti, (line, x_units) in carets_u.items():
            carets[ti] = (line, line_x[line] + x_units * scale)
        layout = {
            'placed': placed, 'carets': carets, 'line_count': n_lines, 'line_top': line_top,
            'line_h': line_h, 'pitch': pitch, 'scale': scale, 'asc': asc, 'upm': upm,
        }
        self._hl = layout
        return layout

    def _paint_h_text(self, painter, width, height):
        layout = self._layout_h_text(width, height)
        scale = layout['scale']
        asc = layout['asc']
        upm = layout['upm']
        line_h = layout['line_h']
        selection = self._selection_range()
        if selection is not None:
            sel_color = PP_color('selection')
            sel_color.setAlpha(70)
            for cell, x, y0, cell_w in layout['placed']:
                ti = cell.get('ti')
                if ti is not None and selection[0] <= ti < selection[1]:
                    painter.fillRect(QtCore.QRectF(x, y0, cell_w, line_h), sel_color)
        for cell, x, y0, cell_w in layout['placed']:
            if x > width or x + cell_w < 0 or y0 > height or y0 + line_h < 0:
                continue
            baseline = y0 + asc * scale
            if cell.get('missing'):
                em = upm * scale
                self._draw_missing(painter, cell, QtCore.QRectF(x, baseline - asc * scale, cell_w, em), em)
            else:
                self._fill_cell(painter, cell, QtGui.QTransform(scale, 0.0, 0.0, -scale, x, baseline))
        if self._editing and self._caret_on:
            caret = layout['carets'].get(self._cursor)
            if caret is not None:
                line, x = caret
                painter.fillRect(QtCore.QRectF(x - 1.0, layout['line_top'][line], 2.0, line_h),
                                 PP_color('accent'))

    def _hit_caret_h(self, x, y):
        layout = getattr(self, '_hl', None)
        n = len(self._tokens())
        if not layout:
            return n
        pitch = layout['pitch'] or 1.0
        line = int((y - layout['line_top'][0]) // pitch) if layout['line_top'] else 0
        line = max(0, min(layout['line_count'] - 1, line))
        return self._caret_in_line(line, x, n)

    def _caret_in_line(self, line, x, fallback):
        layout = getattr(self, '_hl', None)
        best = None
        for index, (ln, cx) in (layout['carets'].items() if layout else []):
            if ln != line:
                continue
            distance = abs(cx - x)
            if best is None or distance < best[0]:
                best = (distance, index)
        return best[1] if best is not None else fallback

    def _move_line(self, step):
        layout = getattr(self, '_hl', None)
        if not layout:
            return
        caret = layout['carets'].get(self._cursor)
        if caret is None:
            return
        line, x = caret
        target = line + step
        if target < 0:
            self._cursor = 0
            return
        if target > layout['line_count'] - 1:
            self._cursor = len(self._tokens())
            return
        self._cursor = self._caret_in_line(target, x, self._cursor)

    def _move_line_edge(self, start):
        layout = getattr(self, '_hl', None)
        if not layout:
            return
        caret = layout['carets'].get(self._cursor)
        if caret is None:
            return
        line = caret[0]
        indices = sorted(index for index, (ln, _x) in layout['carets'].items() if ln == line)
        if indices:
            self._cursor = indices[0] if start else indices[-1]

    def _notify_overflow(self, overflow_x):
        """When the visibility of the horizontal alignment icons changes, re-lays out the panel after drawing finishes."""
        if self._overflow_reported == overflow_x:
            return
        self._overflow_reported = overflow_x
        panel = self._panel
        try:
            QtCore.QTimer.singleShot(0, panel.relayout)
        except Exception:
            pass

    def h_overflow_x(self):
        return bool(self._overflow_reported) and self._mode() == 'h' and bool(self._cells)

    def reset_pan(self):
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()

    @staticmethod
    def _is_space_cell(cell):
        char = cell.get('char')
        return bool(char) and len(char) == 1 and char.isspace()

    def _sequence_v(self):
        """Cell list in vertical layout order (inserts the composing character at the caret position)."""
        if self._cell_kind != 'text' or not self._pre_cells:
            return list(self._cells)
        result = []
        inserted = False
        for cell in self._cells:
            if not inserted and cell.get('ti') == self._cursor:
                result.extend(self._pre_cells)
                inserted = True
            result.append(cell)
        if not inserted:
            result.extend(self._pre_cells)
        return result

    def _layout_v(self, width, height):
        upm, asc, desc = self._metrics
        top_margin = 16.0
        bottom_margin = 16.0
        side = float(PP_SIDE_MARGIN)
        limit = max(top_margin + 1.0, height - bottom_margin)
        sequence = self._sequence_v()
        # the Interpolation / All Masters views fill the window width regardless of the Size value.
        fit = self._cell_kind != 'text'
        if fit:
            available_w = max(1.0, float(width) - 2.0 * side)
            # instead of the widest Advance Width, sets the size at which the glyph frame height (Ascender + |Descender|)
            #        fills the window width. It looks the same size even when the glyph or master changes.
            em = available_w * float(upm) / float(asc - desc)
            # if the whole column exceeds the window height at the width-based size, shrinks to the size that fills the height.
            #        The column height is proportional to the glyph size (em): em × (sum of glyph height ratios + gap ratio × (count-1)).
            available_h = max(1.0, float(height) - top_margin - bottom_margin)
            ratio_sum = 0.0
            count = 0
            for cell in sequence:
                if cell.get('nl'):
                    continue
                if cell.get('rot') or self._is_space_cell(cell) or cell.get('punct_short'):
                    ratio_sum += float(cell.get('adv', 0)) / float(upm)
                elif cell.get('vadv'):
                    ratio_sum += float(cell['vadv']) / float(upm)   # vertical Advance
                else:
                    ratio_sum += 1.0
                count += 1
            factor = ratio_sum + float(self._st.get('v_spacing', 0)) / 100.0 * max(0, count - 1)
            if factor > 0 and em * factor > available_h:
                em = available_h / factor
            # if the Size slider was moved, uses that size. The handle is placed at the currently displayed size.
            view_size = getattr(self._ctrl, 'v_view_size', None)
            if view_size:
                em = float(view_size)
            self._sync_size_slider(em)
        else:
            em = float(self._st['v_size'])
            self._sync_size_slider(em)
        scale = em / upm
        upright = [cell['adv'] * scale for cell in sequence
                   if not cell.get('nl') and not cell.get('rot') and not cell.get('missing')
                   and not self._is_space_cell(cell) and cell.get('adv', 0) > 0]
        if any(cell.get('rot') and not cell.get('nl') and not self._is_space_cell(cell)
               for cell in sequence):
            upright.append(em)
        col_w = max(upright) if upright else em
        gap = em * float(self._st['v_leading']) / 100.0
        spacing = em * float(self._st.get('v_spacing', 0)) / 100.0
        placed = []
        carets = {}
        col = 0
        y = top_margin
        col_end = top_margin
        col_used = False
        for cell in sequence:
            ti = cell.get('ti')
            if ti is not None:
                carets[ti] = (col, col_end if cell.get('nl') else y)
            if cell.get('nl'):
                col += 1
                y = top_margin
                col_end = top_margin
                col_used = False
                continue
            # Spaces keep the same size (Advance Width) as in the rotated (R) state.
            cell_h = (cell['adv'] * scale
                      if (cell.get('rot') or self._is_space_cell(cell) or cell.get('punct_short'))
                      else em)
            if (cell.get('vadv') and not cell.get('missing') and not cell.get('rot')
                    and not self._is_space_cell(cell) and not cell.get('punct_short')):
                # upright characters use the layer's vertical Advance (vmtx) as the cell height.
                cell_h = float(cell['vadv']) * scale
            if col_used and y + cell_h > limit and not fit:
                col += 1
                y = top_margin
                col_used = False
                if ti is not None:
                    carets[ti] = (col, y)
            placed.append((cell, col, y, cell_h))
            col_end = y + cell_h
            y = col_end + spacing          # Spacing: gap between glyphs (negative values make them overlap)
            col_used = True
        if self._cell_kind == 'text':
            carets[len(self._tokens())] = (col, col_end)
        else:
            # The Interpolation / All Masters views center each column vertically.
            spans = {}
            for _cell, c, top, cell_h in placed:
                low, high = spans.get(c, (top, top + cell_h))
                spans[c] = (min(low, top), max(high, top + cell_h))
            # if it exceeds the window height, aligns to the top and scrolls vertically with the wheel.
            overflow_y = 0.0
            for low, high in spans.values():
                overflow_y = max(overflow_y, (high - low) - (height - top_margin - bottom_margin))
            self._scroll_y = max(0.0, min(overflow_y, self._scroll_y))
            shifted = []
            for cell, c, top, cell_h in placed:
                low, high = spans[c]
                offset = max(0.0, (height - (high - low)) / 2.0 - low)
                shifted.append((cell, c, top + offset - self._scroll_y, cell_h))
            placed = shifted
        col_count = col + 1
        block = col_count * col_w + (col_count - 1) * gap
        available = max(1.0, width - 2.0 * side)
        ltr = bool(self._st.get('v_ltr', False))
        if block <= available:
            self._scroll_v = 0.0
            right_edge = (width + block) / 2.0
            left_edge = (width - block) / 2.0
        else:
            self._scroll_v = max(0.0, min(block - available, self._scroll_v))
            right_edge = width - side + self._scroll_v
            left_edge = side - self._scroll_v      # for left→right the first column is at the left edge
        layout = {
            'placed': placed, 'carets': carets, 'col_count': col_count, 'col_w': col_w,
            'gap': gap, 'right_edge': right_edge, 'left_edge': left_edge, 'ltr': ltr,
            'em': em, 'scale': scale,
            'top': top_margin, 'asc': asc, 'desc': desc,
        }
        self._vl = layout
        return layout

    def _sync_size_slider(self, em):
        """Moves the Size slider handle to the current on-screen glyph size (no signal is emitted)."""
        slider = getattr(self._panel, 'size_slider', None)
        if slider is None:
            return
        try:
            value = int(round(float(em)))
            value = max(PP_V_SIZE_MIN, min(PP_V_SIZE_MAX, value))
            if int(_v(slider, 'value', value)) == value:
                return
            slider.blockSignals(True)
            try:
                slider.setValue(value)
            finally:
                slider.blockSignals(False)
        except Exception:
            pass

    # ── Preview guidelines dragged from the Ruler ─────────────
    def set_drag_guide(self, kind, point):
        """Draws the guideline being dragged at the cursor position. Clears it if point is None."""
        value = None if (kind is None or point is None) else (kind, float(point[0]), float(point[1]))
        if value == self._drag_guide:
            return
        self._drag_guide = value
        self.update()

    def _current_layout_v(self):
        layout = self._vl
        if layout is None:
            layout = self._layout_v(float(_int(self, 'width')), float(_int(self, 'height')))
        return layout

    def _guide_origin_y(self, layout):
        """Reference y of a horizontal guideline: the top start point of the glyph layout (in view states, with centering and scroll applied)."""
        if self._cell_kind != 'text' and layout.get('placed'):
            return min(top for _cell, _col, top, _h in layout['placed'])
        return float(layout.get('top', 0.0))

    def add_ruler_guide(self, kind, point):
        """Converts the drop position (preview coordinates) into typesetting coordinates (font units) and remembers it as a guideline.
        'left' Ruler → vertical line (distance from the nearest column center), 'top' Ruler → horizontal line (distance from the top start point)."""
        if self._mode() != 'v':
            return
        layout = self._current_layout_v()
        scale = float(layout.get('scale') or 0.0)
        if scale <= 0.0:
            return
        x, y = float(point[0]), float(point[1])
        if kind == 'left':
            count = max(1, int(layout.get('col_count') or 1))
            best = None
            for col in range(count):
                center = self._column_center(layout, col)
                distance = abs(x - center)
                if best is None or distance < best[0]:
                    best = (distance, col, center)
            guide = {'axis': 'x', 'col': best[1], 'u': (x - best[2]) / scale}
        else:
            guide = {'axis': 'y', 'u': (y - self._guide_origin_y(layout)) / scale}
        self._ctrl.v_guides.append(guide)
        self.update()

    def _paint_ruler_guides(self, painter, layout, width, height):
        guides = list(getattr(self._ctrl, 'v_guides', None) or [])
        drag = self._drag_guide
        if not guides and drag is None:
            return
        scale = float(layout.get('scale') or 0.0)
        color = PP_color('ruler_guide')
        pen = QtGui.QPen(color)
        pen.setWidthF(1.0)
        pen.setCosmetic(True)
        painter.save()
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
            painter.setPen(pen)
            if scale > 0.0:
                origin_y = self._guide_origin_y(layout)
                for guide in guides:
                    if guide.get('hidden'):
                        continue    # a guideline being dragged out of the window is hidden.
                    try:
                        if guide.get('axis') == 'x':
                            x = self._column_center(layout, int(guide.get('col', 0))) + float(guide['u']) * scale
                            painter.drawLine(QtCore.QPointF(x, 0.0), QtCore.QPointF(x, height))
                        else:
                            y = origin_y + float(guide['u']) * scale
                            painter.drawLine(QtCore.QPointF(0.0, y), QtCore.QPointF(width, y))
                    except Exception:
                        continue
            if drag is not None:
                drag_color = PP_color('ruler_guide')
                drag_color.setAlpha(170)
                drag_pen = QtGui.QPen(drag_color)
                drag_pen.setWidthF(1.0)
                drag_pen.setCosmetic(True)
                painter.setPen(drag_pen)
                kind, x, y = drag
                if kind == 'left':
                    painter.drawLine(QtCore.QPointF(x, 0.0), QtCore.QPointF(x, height))
                else:
                    painter.drawLine(QtCore.QPointF(0.0, y), QtCore.QPointF(width, y))
        finally:
            painter.restore()

    # ── Grabbing and moving preview guidelines / throwing them out of the window to delete ─────────────
    def _guide_screen_pos(self, guide, layout):
        """Screen position of the guideline (x for vertical lines, y for horizontal lines). None if it cannot be computed."""
        scale = float(layout.get('scale') or 0.0)
        if scale <= 0.0:
            return None
        try:
            if guide.get('axis') == 'x':
                return self._column_center(layout, int(guide.get('col', 0))) + float(guide['u']) * scale
            return self._guide_origin_y(layout) + float(guide['u']) * scale
        except Exception:
            return None

    def _hit_ruler_guide(self, x, y):
        """Index of the preview guideline at the pressed position (within 4px on screen). None if none."""
        guides = list(getattr(self._ctrl, 'v_guides', None) or [])
        if not guides or self._mode() != 'v':
            return None
        layout = self._current_layout_v()
        best = None
        best_distance = PP_GUIDE_HIT_RADIUS
        for index, guide in enumerate(guides):
            pos = self._guide_screen_pos(guide, layout)
            if pos is None:
                continue
            distance = abs((x if guide.get('axis') == 'x' else y) - pos)
            if distance <= best_distance:
                best = index
                best_distance = distance
        return best

    def _inside_canvas(self, x, y):
        return (0.0 <= x < float(_int(self, 'width'))
                and 0.0 <= y < float(_int(self, 'height')))

    def _move_held_guide(self, x, y):
        hold = self._guide_hold
        guides = getattr(self._ctrl, 'v_guides', None) or []
        if hold is None or not 0 <= hold['index'] < len(guides):
            return
        guide = guides[hold['index']]
        if not self._inside_canvas(x, y):
            hold['outside'] = True
            guide['hidden'] = True
            self.update()
            return
        hold['outside'] = False
        guide.pop('hidden', None)
        layout = self._current_layout_v()
        scale = float(layout.get('scale') or 0.0)
        if scale <= 0.0:
            return
        if guide.get('axis') == 'x':
            count = max(1, int(layout.get('col_count') or 1))
            best = None
            for col in range(count):
                center = self._column_center(layout, col)
                distance = abs(x - center)
                if best is None or distance < best[0]:
                    best = (distance, col, center)
            guide['col'] = best[1]
            guide['u'] = (x - best[2]) / scale
        else:
            guide['u'] = (y - self._guide_origin_y(layout)) / scale
        self.update()

    def _update_guide_hover(self, x, y):
        """If the cursor with no button pressed is over a guideline, shows the handle cursor; removes it when it leaves."""
        axis = None
        if self._inside_canvas(x, y):
            index = self._hit_ruler_guide(x, y)
            guides = getattr(self._ctrl, 'v_guides', None) or []
            if index is not None and 0 <= index < len(guides):
                axis = 'x' if guides[index].get('axis') == 'x' else 'y'
        if axis == self._guide_hover_axis:
            return
        if self._guide_hover_axis is not None:
            pp_pop_handle_cursor(self)
        self._guide_hover_axis = axis
        if axis is not None:
            pp_push_handle_cursor(self, QtCore.Qt.SplitHCursor if axis == 'x'
                                  else QtCore.Qt.SplitVCursor)

    def _clear_guide_hover(self):
        if self._guide_hover_axis is None:
            return
        self._guide_hover_axis = None
        if self._guide_hold is None:
            pp_pop_handle_cursor(self)

    def _finish_held_guide(self, cancel=False):
        hold = self._guide_hold
        self._guide_hold = None
        self._guide_hover_axis = None   # the handle cursor used for grabbing is removed too.
        pp_pop_handle_cursor(self)
        if hold is None:
            return
        guides = getattr(self._ctrl, 'v_guides', None)
        if guides is None or not 0 <= hold['index'] < len(guides):
            return
        if cancel:
            guides[hold['index']] = hold['original']
        elif hold.get('outside'):
            del guides[hold['index']]
        else:
            guides[hold['index']].pop('hidden', None)
        self.update()

    def _column_center(self, layout, col):
        if layout.get('ltr'):
            return layout['left_edge'] + layout['col_w'] / 2.0 + col * (layout['col_w'] + layout['gap'])
        return layout['right_edge'] - layout['col_w'] / 2.0 - col * (layout['col_w'] + layout['gap'])

    def _paint_v(self, painter, width, height):
        st = self._st
        if st['guide_grid']:
            pen = QtGui.QPen(PP_color('grid'))
            pen.setWidthF(1.0)
            painter.setPen(pen)
            step = float(PP_GRID_STEP)
            x = 0.5
            while x < width:
                painter.drawLine(QtCore.QPointF(x, 0.0), QtCore.QPointF(x, height))
                x += step
            y = 0.5
            while y < height:
                painter.drawLine(QtCore.QPointF(0.0, y), QtCore.QPointF(width, y))
                y += step
        layout = self._layout_v(width, height)
        col_w = layout['col_w']
        band = max(2.0, col_w * PP_GUIDE_BAND_RATIO)
        show_cols = layout['col_count'] if (self._cells or self._editing or self._pre_cells) else 0
        if st['guide_center'] or st['guide_right']:
            for col in range(show_cols):
                center = self._column_center(layout, col)
                if st['guide_center']:
                    left_x = center - band / 2.0
                else:
                    # right end of the right thick helper line = right line of the both-end helper lines
                    left_x = center + col_w / 2.0 - band
                painter.fillRect(QtCore.QRectF(left_x, 0.0, band, height),
                                 PP_color('guide_band'))
        if st['guide_edges']:
            pen = QtGui.QPen(PP_color('guide_edge'))
            pen.setWidthF(1.0)
            painter.setPen(pen)
            for col in range(show_cols):
                center = self._column_center(layout, col)
                for x in (center - col_w / 2.0, center + col_w / 2.0):
                    painter.drawLine(QtCore.QPointF(x, 0.0), QtCore.QPointF(x, height))
        scale = layout['scale']
        em = layout['em']
        asc = layout['asc']
        desc = layout['desc']
        mid = (asc + desc) / 2.0
        selection = self._selection_range() if self._cell_kind == 'text' else None
        if selection is not None:
            sel_color = PP_color('selection')
            sel_color.setAlpha(70)
            for cell, col, top, cell_h in layout['placed']:
                ti = cell.get('ti')
                if ti is not None and selection[0] <= ti < selection[1]:
                    center = self._column_center(layout, col)
                    painter.fillRect(QtCore.QRectF(center - col_w / 2.0, top, col_w, cell_h),
                                     sel_color)
        for cell, col, top, cell_h in layout['placed']:
            center = self._column_center(layout, col)
            if top > height or top + cell_h < 0:
                continue
            if cell.get('missing'):
                self._draw_missing(painter, cell,
                                   QtCore.QRectF(center - em / 2.0, top, em, cell_h), em)
            elif cell.get('vform'):
                self._draw_vform(painter, cell, center, top, cell_h, scale, em, asc, desc)
            elif cell.get('punct'):
                self._draw_punct(painter, cell, center, col_w, top, cell_h, scale, em, asc, desc)
            elif cell.get('rot') and cell.get('rot_center') and self._cell_ink_box(cell) is not None:
                # places the center of the rotated outline at the cell center (column center, middle of the cell height).
                box = self._cell_ink_box(cell)
                ax = (box[0] + box[2]) / 2.0
                ay = (box[1] + box[3]) / 2.0
                self._fill_cell(painter, cell,
                                QtGui.QTransform(0.0, scale, scale, 0.0,
                                                 center - ay * scale, top + cell_h / 2.0 - ax * scale))
            elif cell.get('rot'):
                self._fill_cell(painter, cell,
                                QtGui.QTransform(0.0, scale, scale, 0.0, center - mid * scale, top))
            else:
                if cell.get('vorg') is not None:
                    # places the vertical origin (VORG or outline top + TSB) at the top edge of the cell (OpenType vertical typesetting).
                    baseline = top + float(cell['vorg']) * scale
                else:
                    baseline = top + em * (asc / (asc - desc))
                left = center - cell['adv'] * scale / 2.0
                self._fill_cell(painter, cell,
                                QtGui.QTransform(scale, 0.0, 0.0, -scale, left, baseline))
        if self._editing and self._caret_on and self._cell_kind == 'text':
            caret = layout['carets'].get(self._cursor)
            if caret is not None:
                col, y = caret
                center = self._column_center(layout, col)
                painter.fillRect(QtCore.QRectF(center - col_w / 2.0, y - 1.0, col_w, 2.0),
                                 PP_color('accent'))
        # preview guidelines dragged from the Ruler are drawn above the glyphs.
        self._paint_ruler_guides(painter, layout, width, height)

    # ── Mouse ───────────────────────────────────────────────
    def mousePressEvent(self, event):
        event.accept()
        button = _v(event, 'button')
        # in the Vertical mode Interpolation / All Masters views, right-click is also taken as switching to user text input.
        # in the Horizontal mode glyph view (when not showing text), right-click is also taken as switching to text input.
        right_switch = (button == QtCore.Qt.RightButton
                        and ((self._mode() == 'v' and bool(self._ctrl.v_view))
                             or (self._mode() == 'h' and not self._h_text_on())))
        if button != QtCore.Qt.LeftButton and not right_switch:
            return
        if self._mode() == 'h':
            # When glyphs exceed the window, dragging with Space held pans.
            # while typing, Space is entered as a character, so no panning.
            # panning uses the left button only (right-click switches to text input).
            if (button == QtCore.Qt.LeftButton and any(self._h_overflow)
                    and pp_space_key_down() and not self._editing):
                gx, gy = _event_global_xy(event)
                self._panning = (gx, gy, self._pan_x, self._pan_y)
                pp_push_handle_cursor(self, QtCore.Qt.ClosedHandCursor)
                return
            # in the glyph views (active glyph, Interpolation, All Masters), a plain click keeps the view, and
            #   only Ctrl (Mac Command/Control)+click or Alt (Mac Option)+click switches to text input mode.
            #   While showing text, a plain click also creates an input caret (same as Vertical mode).
            #   right-click also switches to text input mode like Ctrl+click / Alt+click.
            if not self._h_text_on():
                if not (right_switch or pp_switch_click_modifier(event)):
                    return
                self._ctrl.set_h_text_mode(True)
            if self._cell_kind != 'text':
                self.rebuild()
            self.begin_edit()
            x, y = _event_xy(event)
            self._layout_h_text(float(_int(self, 'width')), float(_int(self, 'height')))
            previous = self._cursor
            self._cursor = self._hit_caret_h(x, y)
            if _modifiers_int(event) & int(QtCore.Qt.ShiftModifier):
                if self._anchor is None:
                    self._anchor = previous
            else:
                self._anchor = self._cursor
            self._selecting = True
            self._caret_on = True
            self.update()
            return
        # Vertical mode Space+drag panning (when not typing, left button only).
        if button == QtCore.Qt.LeftButton and pp_space_key_down() and not self._editing:
            gx, gy = _event_global_xy(event)
            self._v_panning = (gx, gy, self._scroll_v, self._scroll_y)
            pp_push_handle_cursor(self, QtCore.Qt.ClosedHandCursor)
            return
        # pressing on a preview guideline grabs it (dropping it outside the window deletes it).
        if button == QtCore.Qt.LeftButton:
            x, y = _event_xy(event)
            index = self._hit_ruler_guide(x, y)
            if index is not None:
                guide = self._ctrl.v_guides[index]
                self._guide_hold = {'index': index, 'outside': False, 'original': dict(guide)}
                pp_push_handle_cursor(self, QtCore.Qt.SplitHCursor if guide.get('axis') == 'x'
                                      else QtCore.Qt.SplitVCursor)
                return
        if self._ctrl.v_view:
            # in the Interpolation / All Masters views, a plain click does nothing and keeps the view.
            #   Only Ctrl (Mac Control/Command)+click or Alt (Mac Option)+click switches to user text input mode.
            if not (right_switch or pp_switch_click_modifier(event)):
                return
            self._ctrl.set_v_view(None)
        if self._cell_kind != 'text':
            self.rebuild()
        # a click creates an input caret regardless of whether the Text Tool is selected (own Hangul composition input).
        # clicking keeps the contents of the preview area (including text read from the Glyph Window) as is.
        self.begin_edit()
        x, y = _event_xy(event)
        self._layout_v(float(_int(self, 'width')), float(_int(self, 'height')))
        previous = self._cursor
        self._cursor = self._hit_caret(x, y)
        if _modifiers_int(event) & int(QtCore.Qt.ShiftModifier):
            if self._anchor is None:
                self._anchor = previous
        else:
            self._anchor = self._cursor
        self._selecting = True
        self._caret_on = True
        self.update()

    def mouseMoveEvent(self, event):
        event.accept()
        if self._guide_hold is not None:     
            x, y = _event_xy(event)
            self._move_held_guide(x, y)
            return
        if self._v_panning is not None:     # Vertical mode Space+drag panning
            gx, gy = _event_global_xy(event)
            start_x, start_y, scroll_v, scroll_y = self._v_panning
            if self._cell_kind == 'text':
                dx = gx - start_x
                # For right→left columns, a larger _scroll_v moves glyphs to the right; for left→right columns, to the left.
                if bool(self._st.get('v_ltr', False)):
                    self._scroll_v = scroll_v - dx
                else:
                    self._scroll_v = scroll_v + dx
            else:
                self._scroll_y = scroll_y - (gy - start_y)
            self.update()
            return
        if not self._selecting and self._panning is None:     # handle cursor
            try:
                held = int(_v(event, 'buttons', 0) or 0)
            except Exception:
                held = 0
            if not held:
                x, y = _event_xy(event)
                self._update_guide_hover(x, y)
                return
        if self._selecting and self._editing and self._cell_kind == 'text':   # Horizontal mode text too
            x, y = _event_xy(event)
            self._cursor = (self._hit_caret_h(x, y) if self._mode() == 'h'
                            else self._hit_caret(x, y))
            self._caret_on = True
            self.update()
            return
        if self._panning is None:
            return
        gx, gy = _event_global_xy(event)
        start_x, start_y, pan_x, pan_y = self._panning
        self._pan_x = pan_x + (gx - start_x)
        self._pan_y = pan_y + (gy - start_y)
        self.update()

    def mouseReleaseEvent(self, event):
        event.accept()
        self._selecting = False
        if self._guide_hold is not None:     # dropping outside the window deletes the guideline.
            x, y = _event_xy(event)
            self._move_held_guide(x, y)
            self._finish_held_guide()
            return
        if self._panning is not None:
            self._panning = None
            pp_pop_handle_cursor(self)
        if self._v_panning is not None:     
            self._v_panning = None
            pp_pop_handle_cursor(self)

    def hideEvent(self, event):
        self._panning = None
        self._v_panning = None   
        if self._guide_hold is not None:     # if hidden while dragging, returns it to its original position.
            self._finish_held_guide(cancel=True)
        self._guide_hover_axis = None        
        pp_pop_handle_cursor(self)

    def leaveEvent(self, event):
        # when leaving the window, removes the guideline handle cursor (kept while dragging).
        if self._guide_hold is None:
            self._clear_guide_hover()
        QtGui.QWidget.leaveEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def wheelEvent(self, event):
        event.accept()
        delta = 0
        try:
            angle = _v(event, 'angleDelta')
            delta = int(_v(angle, 'y', 0)) or int(_v(angle, 'x', 0))
        except Exception:
            try:
                delta = int(_v(event, 'delta', 0))
            except Exception:
                delta = 0
        if not delta:
            return
        step = -float(delta) / 120.0 * 40.0
        if self._mode() == 'h' and pp_alt_down():
            # Alt (macOS Option)+wheel zooms the glyph size in/out instead of panning (same as the FontLab Glyph Window).
            self._ctrl.zoom(1 if delta > 0 else -1)
            return
        if self._mode() == 'v' and pp_alt_down():
            # in Vertical mode too, Alt (macOS Option)+wheel zooms the glyph size (Size) in/out.
            self._ctrl.zoom_v(1 if delta > 0 else -1)
            return
        if self._mode() == 'h':
            self._pan_x -= step
        elif self._cell_kind != 'text':
            self._scroll_y += step       # the single-column view scrolls up and down.
        else:
            self._scroll_v += step
        self.update()

    def _hit_caret(self, x, y):
        layout = self._vl
        n = len(self._tokens())
        if not layout:
            return n
        pitch = layout['col_w'] + layout['gap']
        if layout.get('ltr'):
            col = int(round((x - layout['left_edge'] - layout['col_w'] / 2.0) / pitch))
        else:
            col = int(round((layout['right_edge'] - layout['col_w'] / 2.0 - x) / pitch))
        if col < 0:
            col = 0
        if col > layout['col_count'] - 1:
            return n
        return self._caret_in_column(col, y, n)

    def _caret_in_column(self, col, y, fallback):
        layout = self._vl
        best = None
        for index, (c, cy) in (layout['carets'].items() if layout else []):
            if c != col:
                continue
            distance = abs(cy - y)
            if best is None or distance < best[0]:
                best = (distance, index)
        return best[1] if best is not None else fallback

    # ── Start/end editing ─────────────────────────────────────────
    def begin_edit(self):
        if self._editing:
            return
        self._editing = True
        self._clear_pending()
        self._ignored_commit = ''
        # first commits, in place, Hangul being composed in another widget (e.g. the Glyph canvas Text Tool).
        try:
            app = QtGui.QApplication.instance()
            method = _v(app, 'inputMethod', None)
            if method is None:
                method = _v(QtGui.QApplication, 'inputMethod', None)
            commit = getattr(method, 'commit', None)
            if callable(commit):
                commit()
        except Exception as error:
            print('%s IME commit failed: %s' % (PP_LOG, error))
        self.setAttribute(QtCore.Qt.WA_InputMethodEnabled, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        try:
            self.setFocus(QtCore.Qt.MouseFocusReason)
        except Exception:
            self.setFocus()
        self._caret_on = True
        self._caret_timer.start()
        self._set_app_filter(True)

    def end_edit(self, clear_focus=True):
        if not self._editing:
            return
        if self._preedit:
            self._commit_preedit_and_reset()
        self._editing = False
        self._selecting = False
        self._set_app_filter(False)
        try:
            self._caret_timer.stop()
        except Exception:
            pass
        self.setAttribute(QtCore.Qt.WA_InputMethodEnabled, False)
        if clear_focus:
            try:
                if bool(_v(self, 'hasFocus', False)):
                    self.clearFocus()
            except Exception:
                pass
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.update()

    def is_editing(self):
        return self._editing

    def _selection_range(self):
        if self._anchor is None or self._anchor == self._cursor:
            return None
        n = len(self._tokens())
        low = max(0, min(self._anchor, self._cursor))
        high = min(n, max(self._anchor, self._cursor))
        return (low, high) if high > low else None

    def _delete_selection(self):
        selection = self._selection_range()
        self._anchor = None
        if selection is None:
            return False
        del self._tokens()[selection[0]:selection[1]]
        self._cursor = selection[0]
        return True

    def _selected_text(self):
        selection = self._selection_range()
        if selection is None:
            return ''
        return ''.join(self._tokens()[selection[0]:selection[1]])

    def _set_app_filter(self, on):
        """Keeps a QApplication event filter only while typing. Filters installed later run first, so
        key events are received before FontLab's app shortcut handling (. , / ? glyph navigation etc.)."""
        app = QtGui.QApplication.instance()
        if app is None or bool(on) == self._app_filter_on:
            return
        try:
            if on:
                app.installEventFilter(self._app_filter)
            else:
                app.removeEventFilter(self._app_filter)
            self._app_filter_on = bool(on)
        except Exception as error:
            print('%s Input filter setup error: %s' % (PP_LOG, error))

    def _blink(self):
        self._caret_on = not self._caret_on
        self.update()

    # ── Input events (state machine ported from Hangeul Input Tool) ──────────
    def _clear_pending(self):
        self._pending_commit = ''
        self._pending_native = ''
        self._pending_deadline = 0.0

    def _expire_pending(self):
        if self._pending_deadline and time.time() >= self._pending_deadline:
            self._pending_commit = ''
            self._pending_native = ''
            self._ignored_commit = ''
            self._pending_deadline = 0.0

    def _arm_pending_commit(self, text):
        self._pending_native = ''
        self._pending_commit = text
        self._pending_deadline = time.time() + PP_DUPLICATE_COMMIT_TIMEOUT_MS / 1000.0

    def _arm_pending_native(self, text):
        self._pending_commit = ''
        self._pending_native = text
        self._pending_deadline = time.time() + PP_DUPLICATE_COMMIT_TIMEOUT_MS / 1000.0

    def _reset_input_method(self):
        try:
            app = QtGui.QApplication.instance()
            method = _v(app, 'inputMethod', None)
            if method is None:
                method = _v(QtGui.QApplication, 'inputMethod', None)
            reset = getattr(method, 'reset', None)
            if callable(reset):
                reset()
        except Exception as error:
            print('%s IME reset failed: %s' % (PP_LOG, error))

    def _commit_preedit_and_reset(self):
        """Leaves the composing character as committed input and cancels the IME composition."""
        text = self._preedit
        if not text:
            return
        self._preedit = ''
        self._pre_cells = []
        self._insert_text(text)
        self._arm_pending_commit(text)
        self._ignored_commit = text
        self._reset_input_method()

    @staticmethod
    def _is_interrupt_key(key, text):
        if text:
            return False
        modifier_keys = tuple(value for value in (
            getattr(QtCore.Qt, 'Key_Control', None),
            getattr(QtCore.Qt, 'Key_Alt', None),
            getattr(QtCore.Qt, 'Key_Meta', None)) if value is not None)
        if key in modifier_keys:
            return True
        try:
            return int(QtCore.Qt.Key_F1) <= key <= int(QtCore.Qt.Key_F35)
        except Exception:
            return False

    def _command_modifiers(self, event):
        mods = _modifiers_int(event)
        mask = 0
        for name in ('ControlModifier', 'AltModifier', 'MetaModifier'):
            try:
                mask |= int(getattr(QtCore.Qt, name))
            except Exception:
                pass
        return mods & mask

    def _edit_shortcut(self, event):
        """Returns the key name if it is Ctrl (Mac Cmd)+A/C/X/V."""
        try:
            mods = _modifiers_int(event)
            if not (mods & int(QtCore.Qt.ControlModifier)):
                return ''
            if mods & (int(QtCore.Qt.AltModifier) | int(QtCore.Qt.MetaModifier)):
                return ''
            key = int(_v(event, 'key', 0))
            for name in ('A', 'C', 'X', 'V'):
                if key == int(getattr(QtCore.Qt, 'Key_' + name)):
                    return name
        except Exception:
            pass
        return ''

    def _is_paste(self, event):
        return self._edit_shortcut(event) == 'V'

    def filter_event(self, event, source='object'):
        event_type = _v(event, 'type')
        if event_type == QtCore.QEvent.FocusOut:
            if self._editing:
                self.end_edit(clear_focus=False)
            return False
        if source == 'object' and self._app_filter_on and event_type in (
                QtCore.QEvent.ShortcutOverride, QtCore.QEvent.InputMethod,
                QtCore.QEvent.KeyPress):
            return False  # already handled by the app filter.
        if event_type == QtCore.QEvent.ShortcutOverride:
            if not self._editing:
                return False
            if self._command_modifiers(event) and not self._edit_shortcut(event):
                return False  # Ctrl/Alt/Meta shortcuts are passed to FontLab.
            event.accept()
            return True
        if event_type == QtCore.QEvent.InputMethod:
            if not self._editing:
                event.accept()
                return True
            return self._on_input_method(event)
        if event_type == QtCore.QEvent.KeyPress:
            if not self._editing:
                return False
            return self._on_key_press(event)
        return False

    def _set_preedit(self, text):
        self._preedit = text or ''
        cache = self._ctrl.font_cache
        # fgFont is not kept in self._font but obtained each time. During a transition the composing character is not drawn.
        font = None
        master = None
        if self._preedit and not pp_fonts_settling():
            try:
                font, _name, _flg, master = pp_active_glyph_info(cache)
            except Exception:
                font, master = None, None
        if font is not None and self._preedit:
            self._pre_cells = self._char_cells(font, master, self._preedit)
        else:
            self._pre_cells = []
        self._caret_on = True
        self.update()

    def _on_input_method(self, event):
        preedit = _qstring_to_text(_v(event, 'preeditString', ''))
        commit = _qstring_to_text(_v(event, 'commitString', ''))
        self._expire_pending()
        # If a composing character already committed by the reset just before a shortcut is committed again, it is discarded once.
        if commit and self._ignored_commit and commit == self._ignored_commit:
            self._ignored_commit = ''
            self._arm_pending_commit(commit)
            self._set_preedit(preedit)
            event.accept()
            return True
        if preedit and not commit:
            self._clear_pending()
        if (preedit or commit) and self._selection_range() is not None:
            self._delete_selection()
            self._text_changed()
        if commit:
            if self._pending_native and commit == self._pending_native:
                self._clear_pending()
            else:
                self._clear_pending()
                self._preedit = ''
                self._insert_text(commit)
                self._arm_pending_commit(commit)
        self._set_preedit(preedit)
        event.accept()
        return True

    def _on_key_press(self, event):
        # removed the check that ended input when not in the Text Tool.
        try:
            key = int(_v(event, 'key', 0))
        except Exception:
            key = 0
        text = _qstring_to_text(_v(event, 'text', ''))
        self._expire_pending()
        if self._preedit and self._is_interrupt_key(key, text):
            self._commit_preedit_and_reset()
        # Filters out cases where FontLab sends the IME-committed character once more as a key=0 KeyPress.
        if key == 0 and text:
            if self._pending_commit and text == self._pending_commit:
                self._clear_pending()
                event.accept()
                return True
            if self._pending_commit:
                self._clear_pending()
            if self._preedit:
                self._preedit = ''
                self._pre_cells = []
            self._insert_text(text)
            self._arm_pending_native(text)
            event.accept()
            return True
        K = QtCore.Qt
        n = len(self._tokens())
        command = self._command_modifiers(event)
        handled = True
        shortcut = self._edit_shortcut(event)
        shift = bool(_modifiers_int(event) & int(K.ShiftModifier))
        navigation = (int(K.Key_Up), int(K.Key_Down), int(K.Key_Left), int(K.Key_Right),
                      int(K.Key_Home), int(K.Key_End))
        if key in navigation:
            # Shift+arrow keys extend the block, plain arrow keys clear it.
            if shift:
                if self._anchor is None:
                    self._anchor = self._cursor
            else:
                self._anchor = None
        if shortcut == 'A':
            self._anchor = 0
            self._cursor = n
        elif shortcut in ('C', 'X'):
            text_now = self._selected_text()
            if text_now:
                try:
                    QtGui.QApplication.clipboard().setText(text_now)
                except Exception:
                    pass
                if shortcut == 'X':
                    self._delete_selection()
                    self._text_changed()
        elif shortcut == 'V':
            try:
                clip = _qstring_to_text(QtGui.QApplication.clipboard().text())
            except Exception:
                clip = ''
            if clip:
                self._insert_text(clip)
        elif command:
            handled = False
        elif key == int(K.Key_Backspace):
            if self._delete_selection():
                self._text_changed()
            elif self._cursor > 0:
                del self._tokens()[self._cursor - 1]
                self._cursor -= 1
                self._text_changed()
        elif key == int(K.Key_Delete):
            if self._delete_selection():
                self._text_changed()
            elif self._cursor < n:
                del self._tokens()[self._cursor]
                self._text_changed()
        elif key in (int(K.Key_Return), int(K.Key_Enter)):
            self._insert_text('\n')
        elif self._mode() == 'h' and key in (int(K.Key_Up), int(K.Key_Down)):
            self._move_line(-1 if key == int(K.Key_Up) else 1)     # Horizontal mode moves to the previous/next line
        elif self._mode() == 'h' and key in (int(K.Key_Left), int(K.Key_Right)):
            if key == int(K.Key_Left):                             # Horizontal mode moves to the previous/next character
                self._cursor = max(0, self._cursor - 1)
            else:
                self._cursor = min(n, self._cursor + 1)
        elif self._mode() == 'h' and key in (int(K.Key_Home), int(K.Key_End)):
            self._move_line_edge(key == int(K.Key_Home))          # Horizontal mode moves to the start/end of the line
        elif key == int(K.Key_Up):
            self._cursor = max(0, self._cursor - 1)
        elif key == int(K.Key_Down):
            self._cursor = min(n, self._cursor + 1)
        elif key in (int(K.Key_Left), int(K.Key_Right)):
            forward = int(K.Key_Right) if self._st.get('v_ltr', False) else int(K.Key_Left)
            self._move_column(1 if key == forward else -1)
        elif key in (int(K.Key_Home), int(K.Key_End)):
            self._move_column_edge(key == int(K.Key_Home))
        elif key == int(K.Key_Escape):
            self.end_edit()
            event.accept()
            return True
        elif key == int(K.Key_Tab):
            pass
        elif text and not command and all(ord(ch) >= 32 for ch in text):
            self._insert_text(text)
        else:
            handled = False
        if handled:
            self._caret_on = True
            self.update()
            event.accept()
        return handled

    def _move_column(self, step):
        layout = self._vl
        if not layout:
            return
        caret = layout['carets'].get(self._cursor)
        if caret is None:
            return
        col, y = caret
        target = col + step
        if target < 0:
            self._cursor = 0
            return
        if target > layout['col_count'] - 1:
            self._cursor = len(self._tokens())
            return
        self._cursor = self._caret_in_column(target, y, self._cursor)

    def _move_column_edge(self, start):
        layout = self._vl
        if not layout:
            return
        caret = layout['carets'].get(self._cursor)
        if caret is None:
            return
        col = caret[0]
        indices = sorted(index for index, (c, _y) in layout['carets'].items() if c == col)
        if indices:
            self._cursor = indices[0] if start else indices[-1]

    def _insert_text(self, text):
        tokens = self._tokens()
        changed = self._delete_selection()
        for char in text:
            if char in ('\r', '\n', ' '):
                char = '\n'
            elif ord(char) < 32:
                continue
            tokens.insert(self._cursor, char)
            self._cursor += 1
            changed = True
        if changed:
            self._text_changed()

    def _text_changed(self):
        self._cursor = max(0, min(len(self._tokens()), self._cursor))
        # typed/pasted text is not saved automatically (written only when Save is used).
        self.rebuild()

    def set_text_tokens(self, tokens):
        self._tokens()[:] = list(tokens)
        self._cursor = len(self._tokens())
        self._anchor = None
        self._preedit = ''
        self._pre_cells = []

    def inputMethodQuery(self, query):
        """Reports the caret rectangle for positioning the IME candidate window."""
        try:
            cursor_query = getattr(QtCore.Qt, 'ImCursorRectangle',
                                   getattr(QtCore.Qt, 'ImMicroFocus', None))
            if (cursor_query is not None and int(query) == int(cursor_query)
                    and self._editing and self._mode() == 'h' and self._hl):
                caret = self._hl['carets'].get(self._cursor)    # Horizontal mode text
                if caret is not None:
                    line, x = caret
                    return QtCore.QRect(int(x), int(self._hl['line_top'][line]),
                                        2, int(self._hl['line_h']))
            if (cursor_query is not None and int(query) == int(cursor_query)
                    and self._editing and self._mode() == 'v' and self._vl):
                caret = self._vl['carets'].get(self._cursor)
                if caret is not None:
                    col, y = caret
                    center = self._column_center(self._vl, col)
                    return QtCore.QRect(int(center - self._vl['col_w'] / 2.0), int(y),
                                        int(self._vl['col_w']), 2)
        except Exception:
            pass
        return QtGui.QWidget.inputMethodQuery(self, query)

    def shutdown(self):
        self._set_app_filter(False)
        if self._app_filter is not None:
            self._app_filter._canvas = None
        try:
            self._caret_timer.stop()
        except Exception:
            pass
        try:
            self.removeEventFilter(self._filter)
        except Exception:
            pass
        if self._filter is not None:
            self._filter._canvas = None



# ============================================================
# Panel body (Horizontal/Vertical mode layout, icons, sliders)
# ============================================================
PP_LEFT_ICON_KINDS = ('dock', 'eye', 'invert', 'interp', 'masters')
PP_H_RIGHT_ICON_KINDS = ('halign', 'vmode', 'minus', 'plus', 'close')   # left → right
PP_V_RIGHT_ICON_KINDS = ('halign', 'vmode', 'close')          # R was moved to the left group.
PP_ALIGN_KINDS = ('align_left', 'align_center', 'align_right')
PP_GUIDE_KINDS = ('grid', 'edges', 'center', 'right')
PP_GLYPH_IO_KINDS = ('glyph_out', 'glyph_in', 'user_text')   # left of the grid icon (outward/inward arrows)
                                                              # load/save saved text (user_text)
PP_H_LEFT_EXTRA_KINDS = ('h_glyph_io',)   # right of the Horizontal mode All Masters icon (Glyph Import)
PP_USER_TEXT_ICON_NAME = 'DalgasPreviewPanelUserTextIcon'   # for the tooltip style selector
PP_H_GLYPH_IO_ICON_NAME = 'DalgasPreviewPanelHGlyphIoIcon'   # for the Glyph Import icon tooltip style selector
PP_INTERP_ICON_NAME = 'DalgasPreviewPanelInterpIcon'
PP_ROTATE_ICON_NAME = 'DalgasPreviewPanelRotateIcon'         # for the R icon tooltip style selector
PP_GLYPH_IO_GAP = 14               # gap between the text exchange icons and the grid icon (px)


class PPPanel(QtGui.QWidget):
    """Body placed in the overlay on the Glyph Window canvas (or in the Selections panel host)."""

    def __init__(self, controller):
        QtGui.QWidget.__init__(self, None)
        self._ctrl = controller
        self._collapsed = False
        self._docked = False
        self._released = False
        self.setObjectName(PP_OVERLAY_OBJECT_NAME)
        self.setAttribute(QtCore.Qt.WA_NoMousePropagation, True)
        self.setAutoFillBackground(False)
        self.setMinimumSize(0, 0)

        self.canvas = PPPreviewCanvas(self)
        self.handle = PPResizeHandle(self, controller.resize_panel)
        callbacks = {
            'dock': controller.toggle_dock,
            'eye': controller.toggle_collapsed,
            'invert': controller.toggle_theme,
            'interp': lambda: controller.toggle_view('interp'),
            'masters': lambda: controller.toggle_view('masters'),
            'halign': lambda: controller.set_mode('h'),
            'vmode': controller.click_vmode,
            'minus': lambda: controller.zoom(-1),
            'plus': lambda: controller.zoom(1),
            'close': controller.close_script,
            'rotate': controller.toggle_rotate,
            'grid': lambda: controller.toggle_guide('grid'),
            'edges': lambda: controller.toggle_guide('edges'),
            'center': lambda: controller.toggle_guide('center'),
            'right': controller.click_right_guide,     # Ctrl+click deletes the preview guidelines
            'glyph_out': controller.send_text_to_glyph_window,
            'glyph_in': controller.load_text_from_glyph_window,
            'user_text': controller.click_user_text,
            'h_glyph_io': controller.click_h_glyph_io,  # Horizontal mode Glyph Import (Ctrl/Alt+click exports)
        }
        self.icons = {}
        for kind, callback in callbacks.items():
            self.icons[kind] = PPIcon(kind, self, callback)
        self.icons['user_text'].setToolTip('Alt+click: Save')   
        self.icons['h_glyph_io'].setToolTip('Alt+click: Export to Glyph Window')   
        self.icons['interp'].setToolTip('Ctrl+Click: Show All Instances')
        try:
            self.icons['rotate'].setToolTip('Alt+click: Simple rotation R\nCtrl+click: Vertical writing glyphs (vert)')   
        except Exception:
            pass
        # separated by selectors so the tooltip does not inherit the icon's transparent background style, and uses a light yellow tooltip.
        # the same style is applied to the R icon tooltip (it was missed in v1.40 and the tooltip background looked black).
        for kind, object_name in (('user_text', PP_USER_TEXT_ICON_NAME),
                                  ('rotate', PP_ROTATE_ICON_NAME),
                                  ('interp', PP_INTERP_ICON_NAME),
                                  ('h_glyph_io', PP_H_GLYPH_IO_ICON_NAME)):   
            self.icons[kind].setObjectName(object_name)
            self.icons[kind].setStyleSheet(
                '#%s { background:transparent; border:none; } '
                'QToolTip { color:#000000; background-color:#ffffe1; border:1px solid #767676; '
                'padding:2px; }' % object_name)
        for kind in PP_ALIGN_KINDS:
            self.icons[kind] = PPIcon(kind, self, (lambda k=kind: controller.set_h_align(k[6:])),
                                      icon_size=PP_ALIGN_ICON)

        self.icons['fitv'] = PPIcon('fitv', self, controller.toggle_dock_fit)
        self.size_label = PPSliderIcon('size', self)
        self.spacing_label = PPSliderIcon('spacing', self)
        self.leading_label = PPSliderIcon('leading', self)
        self.size_slider = PPSlider(self, PP_V_SIZE_DEFAULT)
        self.spacing_slider = PPSlider(self, 0)
        self.leading_slider = PPSlider(self, PP_V_LEADING_DEFAULT)
        self.size_label.set_slider(self.size_slider)
        self.spacing_label.set_slider(self.spacing_slider)
        self.leading_label.set_slider(self.leading_slider)
        st = controller.st
        for slider, low, high, value_now in (
                (self.size_slider, PP_V_SIZE_MIN, PP_V_SIZE_MAX, st['v_size']),
                (self.spacing_slider, -100, 100, st['v_spacing']),
                (self.leading_slider, PP_V_LEADING_MIN, PP_V_LEADING_MAX, st['v_leading'])):
            slider.setFocusPolicy(QtCore.Qt.NoFocus)
            slider.setRange(low, high)
            slider.setValue(int(value_now))
            slider.setAttribute(QtCore.Qt.WA_NoMousePropagation, True)
        self.size_slider.valueChanged.connect(lambda value: controller.set_v_size(value))
        self.leading_slider.valueChanged.connect(lambda value: controller.set_v_leading(value))
        self.spacing_slider.valueChanged.connect(lambda value: controller.set_v_spacing(value))
        self.apply_theme()
        self.relayout()

    # ── State queries ────────────────────────────────────────────
    def mode(self):
        return self._ctrl.st['mode']

    def icon_state(self, kind):
        ctrl = self._ctrl
        st = ctrl.st
        if self._collapsed:
            return 'collapsed'
        if kind == 'dock':
            return 'on'
        if kind == 'eye':
            return 'disabled' if self._docked else 'on'
        if kind == 'invert':
            return 'off' if bool(PP_THEME['dark']) != bool(PP_FONTLAB_DARK) else 'on'
        if kind in ('interp', 'masters'):
            if st['mode'] == 'h' and bool(getattr(ctrl, 'h_text_on', False)):
                return 'off'   # Horizontal mode showing text
            view = st['h_view'] if st['mode'] == 'h' else ctrl.v_view
            return 'on' if view == kind else 'off'
        if kind == 'halign':
            return 'on' if st['mode'] == 'h' else 'off'
        if kind == 'vmode':
            return 'on' if st['mode'] == 'v' else 'off'
        if kind in ('minus', 'plus'):
            return 'plain'
        if kind == 'close':
            return 'on'
        if kind == 'rotate':
            return 'on' if st['rotate_latin'] else 'off'
        if kind in PP_GUIDE_KINDS:
            return 'on' if st['guide_' + kind] else 'off'
        if kind in PP_ALIGN_KINDS:
            return 'on' if st.get('h_align', 'center') == kind[6:] else 'off'
        if kind == 'fitv':
            # dock_fit in the Dock state, h_fit in the Floating state
            if self._docked:
                return 'on' if st.get('dock_fit', 'width') == 'height' else 'dark'
            return 'on' if st.get('h_fit', 'height') == 'height' else 'dark'
        return 'off'

    def collapsed_size(self):
        count = len(PP_LEFT_ICON_KINDS)
        return (count * PP_ICON + (count - 1) * PP_ICON_GAP, PP_ICON)

    def is_collapsed(self):
        return self._collapsed

    def is_docked(self):
        return self._docked

    # ── Layout ────────────────────────────────────────────────
    def set_collapsed(self, collapsed):
        self._collapsed = bool(collapsed)
        if self._collapsed:
            self.canvas.end_edit()
        self.relayout()
        self.update_icons()
        self.update()

    def set_docked(self, docked):
        self._docked = bool(docked)
        self.relayout()
        self.update_icons()

    def _place_row(self, kinds, x, y, gaps):
        """Lays out kinds from x to the right. gaps[i] is the gap before the i-th icon."""
        for index, kind in enumerate(kinds):
            if index > 0:
                x += gaps[index]
            icon = self.icons[kind]
            icon.move(x, y)
            icon.show()
            x += int(_v(icon, 'width', PP_ICON))
        return x

    @staticmethod
    def _row_width(kinds, gaps):
        return len(kinds) * PP_ICON + sum(gaps[1:len(kinds)])

    def relayout(self):
        if self._released:
            return
        width = _int(self, 'width')
        height = _int(self, 'height')
        mode = self._ctrl.st['mode']
        all_kinds = set(self.icons.keys())
        sliders = (self.size_label, self.spacing_label, self.leading_label,
                   self.size_slider, self.spacing_slider, self.leading_slider)
        if self._collapsed:
            for widget in (self.canvas, self.handle) + sliders:
                widget.hide()
            for kind in all_kinds - set(PP_LEFT_ICON_KINDS):
                self.icons[kind].hide()
            for index, kind in enumerate(PP_LEFT_ICON_KINDS):
                icon = self.icons[kind]
                icon.move(index * (PP_ICON + PP_ICON_GAP), 0)
                icon.show()
                icon.raise_()
            return

        shown = set()
        if mode == 'h':
            top = 0 if self._docked else PP_HANDLE
            self.handle.set_orientation('h')
            self.handle.setGeometry(0, 0, max(1, width), PP_HANDLE)
            self.handle.setVisible(not self._docked)
            self.canvas.setGeometry(0, top, max(1, width), max(1, height - top - PP_BAR_HEIGHT))
            for widget in sliders:
                widget.hide()
            bar_y = height - PP_BAR_HEIGHT + (PP_BAR_HEIGHT - PP_ICON) // 2
            # In the Dock state, an up/down arrow (fit window height/width) is placed left of the Horizontal mode icon.
            # always placed in the Floating state too.
            right_kinds = ('fitv',) + PP_H_RIGHT_ICON_KINDS
            # the Glyph Import icon is placed right of the Show All Master Glyphs icon.
            left_kinds = PP_LEFT_ICON_KINDS + PP_H_LEFT_EXTRA_KINDS
            gaps = [PP_ICON_GAP] * 8
            needed = (2 * PP_SIDE_MARGIN + PP_ICON_GAP + self._row_width(left_kinds, gaps)
                      + self._row_width(right_kinds, gaps))
            if width < needed:
                gaps = [0] * 8   # in a narrow window (e.g. Selections panel Dock) the gaps are removed.
            left_end = self._place_row(left_kinds, PP_SIDE_MARGIN, bar_y, gaps)
            shown.update(left_kinds)
            right_w = self._row_width(right_kinds, gaps)
            right_start = width - PP_SIDE_MARGIN - right_w
            self._place_row(right_kinds, right_start, bar_y, gaps)
            shown.update(right_kinds)
            # Three alignment icons (90% size) at the exact center of the bottom row, only when glyphs exceed the window.
            # Not shown if it is narrow enough to overlap the icon groups on both sides.
            align_gap = 4
            align_w = 3 * PP_ALIGN_ICON + 2 * align_gap
            align_x = (width - align_w) // 2
            align_fits = (align_x >= left_end + 4 and align_x + align_w <= right_start - 4)
            if self.canvas.h_overflow_x() and align_fits:
                align_y = height - PP_BAR_HEIGHT + (PP_BAR_HEIGHT - PP_ALIGN_ICON) // 2
                x = align_x
                for kind in PP_ALIGN_KINDS:
                    icon = self.icons[kind]
                    icon.move(x, align_y)
                    icon.show()
                    shown.add(kind)
                    x += PP_ALIGN_ICON + align_gap
        else:
            left = 0 if self._docked else PP_HANDLE
            self.handle.set_orientation('v')
            self.handle.setGeometry(0, 0, PP_HANDLE, max(1, height))
            self.handle.setVisible(not self._docked)
            # Vertical mode icon gaps are reduced by 8px (only the gap before R is reduced by 4px).
            left_kinds = PP_LEFT_ICON_KINDS + ('rotate',)
            left_gaps = [0] * len(PP_LEFT_ICON_KINDS) + [0]   # the gap before R is also 0px
            right_gaps = [0] * len(PP_V_RIGHT_ICON_KINDS)
            guide_gaps = [0] * len(PP_GUIDE_KINDS)
            bar_needed = (left + 2 * PP_SIDE_MARGIN + PP_ICON_GAP
                          + self._row_width(left_kinds, left_gaps)
                          + self._row_width(PP_V_RIGHT_ICON_KINDS, right_gaps))
            show_icons = width >= bar_needed
            inner_left = left + PP_SIDE_MARGIN
            inner_w = width - inner_left - PP_SIDE_MARGIN
            size_label_w = _int(self.size_label, 'width') + 4
            spacing_label_w = _int(self.spacing_label, 'width') + 4
            leading_label_w = _int(self.leading_label, 'width') + 4
            slider_gap = 10
            slider_min = 16
            slider_w = (inner_w - size_label_w - spacing_label_w - leading_label_w
                        - 2 * slider_gap) // 3
            show_sliders = slider_w >= slider_min
            # if the sliders cannot fit, only the three icons remain; if even the icons cannot fit, the whole row is hidden.
            icons_only_w = (_int(self.size_label, 'width') + _int(self.spacing_label, 'width')
                            + _int(self.leading_label, 'width') + 2 * slider_gap)
            show_slider_icons = show_sliders or inner_w >= icons_only_w
            controls = 0
            if show_icons:
                controls += PP_BAR_HEIGHT + PP_GUIDE_ROW_HEIGHT
            if show_slider_icons:
                controls += PP_SLIDER_ROW_HEIGHT
            canvas_h = max(1, height - controls)
            self.canvas.setGeometry(left, 0, max(1, width - left), canvas_h)
            row_y = canvas_h
            if show_icons:
                # Four helper-line buttons (right-aligned)
                guide_y = row_y + (PP_GUIDE_ROW_HEIGHT - PP_ICON) // 2
                guide_w = self._row_width(PP_GUIDE_KINDS, guide_gaps)
                guide_x = width - PP_SIDE_MARGIN - guide_w
                self._place_row(PP_GUIDE_KINDS, guide_x, guide_y, guide_gaps)
                shown.update(PP_GUIDE_KINDS)
                # two text exchange icons left of the grid icon
                io_gaps = [0] * len(PP_GLYPH_IO_KINDS)
                io_w = self._row_width(PP_GLYPH_IO_KINDS, io_gaps)
                self._place_row(PP_GLYPH_IO_KINDS, guide_x - PP_GLYPH_IO_GAP - io_w, guide_y, io_gaps)
                shown.update(PP_GLYPH_IO_KINDS)
                row_y += PP_GUIDE_ROW_HEIGHT
            if show_sliders:
                # Size/Spacing/Leading slider row (sliders shrink to fit the width)
                label_h = PP_SLIDER_ROW_HEIGHT
                x = inner_left
                for label, label_w, slider in (
                        (self.size_label, size_label_w, self.size_slider),
                        (self.spacing_label, spacing_label_w, self.spacing_slider),
                        (self.leading_label, leading_label_w, self.leading_slider)):
                    label.move(x, row_y + (label_h - _int(label, 'height')) // 2)
                    slider.setGeometry(x + label_w, row_y, slider_w, label_h)
                    x += label_w + slider_w + slider_gap
                for widget in sliders:
                    widget.show()
                row_y += PP_SLIDER_ROW_HEIGHT
            elif show_slider_icons:
                # Shows only the three icons (values can be adjusted with click / Alt+click).
                label_h = PP_SLIDER_ROW_HEIGHT
                x = inner_left
                for label, slider in ((self.size_label, self.size_slider),
                                      (self.spacing_label, self.spacing_slider),
                                      (self.leading_label, self.leading_slider)):
                    label.move(x, row_y + (label_h - _int(label, 'height')) // 2)
                    label.show()
                    slider.hide()
                    x += _int(label, 'width') + slider_gap
                row_y += PP_SLIDER_ROW_HEIGHT
            else:
                for widget in sliders:
                    widget.hide()
            if show_icons:
                bar_y = row_y + (PP_BAR_HEIGHT - PP_ICON) // 2
                self._place_row(left_kinds, inner_left, bar_y, left_gaps)
                shown.update(left_kinds)
                right_w = self._row_width(PP_V_RIGHT_ICON_KINDS, right_gaps)
                self._place_row(PP_V_RIGHT_ICON_KINDS, width - PP_SIDE_MARGIN - right_w,
                                bar_y, right_gaps)
                shown.update(PP_V_RIGHT_ICON_KINDS)
        for kind in all_kinds - shown:
            self.icons[kind].hide()
        self.canvas.show()
        self.handle.raise_()

    def resizeEvent(self, event):
        self.relayout()

    def paintEvent(self, event):
        if self._collapsed:
            return
        painter = QtGui.QPainter(self)
        try:
            painter.fillRect(0, 0, _int(self, 'width'), _int(self, 'height'),
                             PP_color('background'))
        finally:
            painter.end()

    def mousePressEvent(self, event):
        event.accept()
        # In the Vertical mode Interpolation / All Masters views, clicking outside the icons returns to the user input text.
        # a plain click keeps the view; only Ctrl+click / Alt+click returns to the user input text.
        # right-click also returns to the user input text.
        button = _v(event, 'button')
        if (not self._collapsed and self._ctrl.st['mode'] == 'v' and self._ctrl.v_view
                and (button == QtCore.Qt.RightButton
                     or (button == QtCore.Qt.LeftButton and pp_switch_click_modifier(event)))):
            self._ctrl.set_v_view(None)

    def mouseReleaseEvent(self, event):
        event.accept()

    def wheelEvent(self, event):
        event.accept()

    def apply_theme(self):
        for slider in (self.size_slider, self.spacing_slider, self.leading_slider):
            slider.setStyleSheet(PP_slider_style())
        for label in (self.size_label, self.spacing_label, self.leading_label):
            label.update()
        self.update_icons()
        self.handle.update()
        self.canvas.update()
        self.update()

    def update_icons(self):
        for icon in self.icons.values():
            refresh = getattr(icon, 'refresh_cursor', None)
            if refresh is not None:
                refresh()
            icon.update()

    def sync_sliders(self):
        st = self._ctrl.st
        for slider, key in ((self.size_slider, 'v_size'), (self.spacing_slider, 'v_spacing'),
                            (self.leading_slider, 'v_leading')):
            try:
                slider.blockSignals(True)
                slider.setValue(int(st[key]))
            finally:
                slider.blockSignals(False)

    def release_resources(self):
        if self._released:
            return
        self._released = True
        for label in (self.size_label, self.spacing_label, self.leading_label):
            try:
                label._stop_repeat()   # stops the icon repeat timer.
            except Exception:
                pass
        try:
            self.canvas.end_edit()
        except Exception:
            pass
        try:
            self.canvas.shutdown()
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass


# ============================================================
# Selections panel Dock (SelectionsPanelHost approach of Large Size v4.56)
# ============================================================
def pp_find_panel_page(object_name, visible_only=False):
    app = QtGui.QApplication.instance()
    if app is None:
        return None
    try:
        widgets = app.allWidgets()
    except Exception:
        return None
    fallback = None
    for widget in widgets:
        try:
            if _object_name(widget) != object_name:
                continue
            visible = bool(_v(widget, 'isVisible', False))
            attached = widget.parent() is not None
            if visible and attached:
                return widget
            if not visible_only and fallback is None:
                fallback = widget
        except Exception:
            continue
    return None if visible_only else fallback


def pp_open_and_find_selections_panel():
    panel = pp_find_panel_page(PP_SELECTIONS_PANEL_OBJECT_NAME, visible_only=True)
    if panel is not None:
        return panel
    try:
        Automat().run(PP_SELECTIONS_PANEL_OBJECT_NAME)
        QtGui.QApplication.processEvents()
    except Exception as error:
        print('%s Selections panel open error: %s' % (PP_LOG, error))
        return None
    return pp_find_panel_page(PP_SELECTIONS_PANEL_OBJECT_NAME, visible_only=True)


def pp_close_native_panel(panel_widget):
    """Closes the native panel via the actual tab close signal (tabCloseRequested) path."""
    if panel_widget is None or not _widget_alive(panel_widget):
        return False
    try:
        if _object_name(panel_widget) == 'MainWindow' or _class_name(panel_widget) == 'MainWindow':
            return False
        stacked = panel_widget.parent()
        if stacked is None:
            return False
        tab_widget = stacked.parent()
        if tab_widget is None:
            return False
        tabbar = None
        for child in tab_widget.children():
            if _class_name(child) == 'YTabBar':
                tabbar = child
                break
        if tabbar is None or not hasattr(tabbar, 'tabCloseRequested'):
            return False
        index = stacked.indexOf(panel_widget)
        tab_count = _int(tabbar, 'count')
        if index is None or index < 0 or index >= tab_count:
            return False
        signal_object = tabbar.tabCloseRequested
        if hasattr(signal_object, 'emit'):
            signal_object.emit(index)
        else:
            tabbar.tabCloseRequested(index)
        return True
    except Exception as error:
        print('%s Selections panel close error: %s' % (PP_LOG, error))
        return False


def _pp_property_text(obj, name):
    try:
        value = obj.property(name)
        return '' if value is None else str(value).strip()
    except Exception:
        return ''


def _pp_registered_hosts(panel):
    result = []
    try:
        children = panel.children()
    except Exception:
        children = []
    for child in children:
        try:
            owner = _pp_property_text(child, PP_SELECTIONS_HOST_MARKER_PROPERTY)
            if owner and _widget_alive(child):
                result.append((child, owner))
        except Exception:
            continue
    return result


def pp_claim_selections_panel(panel):
    """Acquires occupancy of the Selections panel without overwriting another host (e.g. Large Size)."""
    owner = _pp_property_text(panel, PP_SELECTIONS_OWNER_PROPERTY)
    hosts = _pp_registered_hosts(panel)
    if owner:
        if [host for host, host_owner in hosts if host_owner == owner]:
            return False, owner
        try:
            panel.setProperty(PP_SELECTIONS_OWNER_PROPERTY, '')
        except Exception:
            return False, owner
    if hosts:
        try:
            panel.setProperty(PP_SELECTIONS_OWNER_PROPERTY, hosts[0][1])
        except Exception:
            pass
        return False, hosts[0][1]
    try:
        panel.setProperty(PP_SELECTIONS_OWNER_PROPERTY, PP_SELECTIONS_OWNER_ID)
        if _pp_property_text(panel, PP_SELECTIONS_OWNER_PROPERTY) == PP_SELECTIONS_OWNER_ID:
            return True, ''
    except Exception:
        pass
    return False, 'Failed to write the occupancy property'


def pp_release_selections_panel(panel):
    if panel is None or not _widget_alive(panel):
        return
    try:
        if _pp_property_text(panel, PP_SELECTIONS_OWNER_PROPERTY) == PP_SELECTIONS_OWNER_ID:
            panel.setProperty(PP_SELECTIONS_OWNER_PROPERTY, '')
    except Exception:
        pass


class PPSelectionsHost(QtGui.QWidget):
    """Temporary host covering the SelectionsPanel without touching its original contents."""

    def __init__(self, panel, content):
        QtGui.QWidget.__init__(self, panel)
        self.setObjectName(PP_SELECTIONS_HOST_OBJECT_NAME)
        self.setProperty(PP_SELECTIONS_HOST_MARKER_PROPERTY, PP_SELECTIONS_OWNER_ID)
        self._panel = panel
        self._content = None
        # state that makes the Selections panel take the full height of the Dock column (SSO GUI v5.36/v5.37/v5.47 approach)
        self._original_content_size_policy = None
        self._native_fill_widgets = []
        self._native_fill_policies = []
        self._native_fill_sizes = []
        self._native_fill_layout_stretches = []
        self._native_fill_token = ()
        self._native_fill_updating = False
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self._host_layout = QtGui.QVBoxLayout()
        self._host_layout.setContentsMargins(0, 0, 0, 0)
        self._host_layout.setSpacing(0)
        self.setLayout(self._host_layout)
        # instance timer for auto-fitting the Dock column height (owned by the host as parent)
        self._auto_fill_retry = 0
        self._auto_fill_timer = QtCore.QTimer(self)
        self._auto_fill_timer.setSingleShot(True)
        self._auto_fill_timer.timeout.connect(self._run_dock_auto_fill)
        panel.installEventFilter(self)
        self._refresh_native_fill_chain()
        self.attach_content(content)
        self.sync_geometry()
        self.show()
        self.raise_()

    def content(self):
        return self._content

    def attach_content(self, content):
        if content is None:
            return
        self._content = content
        try:
            self._original_content_size_policy = _v(content, 'sizePolicy')
        except Exception:
            self._original_content_size_policy = None
        # the body receives all the remaining horizontal/vertical space of the Selections box.
        try:
            content.setMinimumSize(0, 0)
            content.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        except Exception:
            pass
        content.setParent(self)
        self._host_layout.addWidget(content, 1)
        try:
            self._host_layout.setStretch(0, 1)
        except Exception:
            pass
        content.show()

    def release_content(self):
        content = self._content
        if content is not None:
            try:
                self._host_layout.removeWidget(content)
                content.hide()
            except Exception:
                pass
            try:
                if self._original_content_size_policy is not None:
                    content.setSizePolicy(self._original_content_size_policy)
                    content.updateGeometry()
            except Exception:
                pass
        self._original_content_size_policy = None
        self._content = None
        return content

    # ── Fill the full Dock column height (GalleryPanelHost approach of SSO GUI v5.36/v5.37/v5.47) ──
    def _collect_native_fill_chain(self):
        """Returns the QWidget parent chain from the SelectionsPanel up to the current YDock."""
        result = []
        current = self._panel
        seen = set()
        for _ in range(10):
            if current is None:
                break
            marker = id(current)
            if marker in seen:
                break
            seen.add(marker)
            class_name = _class_name(current)
            if class_name == 'MainWindow' or _object_name(current) == 'MainWindow':
                break
            result.append(current)
            if class_name == 'YDock':
                break
            parent = _v(current, 'parentWidget', None)
            if parent is None:
                parent = _v(current, 'parent', None)
            if parent is current:
                break
            current = parent
        return result

    def _restore_native_fill_chain(self):
        """Restores the size constraints, stretch and event filters of the native parent chain."""
        self._native_fill_updating = True
        try:
            for widget in list(self._native_fill_widgets[1:]):
                try:
                    if _widget_alive(widget):
                        widget.removeEventFilter(self)
                except Exception:
                    pass
            for layout, item_index, stretch in reversed(list(self._native_fill_layout_stretches)):
                try:
                    layout.setStretch(item_index, stretch)
                    layout.invalidate()
                    layout.activate()
                except Exception:
                    pass
            for widget, minimum_size, maximum_size in reversed(list(self._native_fill_sizes)):
                try:
                    if _widget_alive(widget):
                        widget.setMinimumSize(minimum_size)
                        widget.setMaximumSize(maximum_size)
                except Exception:
                    pass
            for widget, policy in reversed(list(self._native_fill_policies)):
                try:
                    if _widget_alive(widget) and policy is not None:
                        widget.setSizePolicy(policy)
                        widget.updateGeometry()
                except Exception:
                    pass
            self._native_fill_widgets = []
            self._native_fill_policies = []
            self._native_fill_sizes = []
            self._native_fill_layout_stretches = []
            self._native_fill_token = ()
        finally:
            self._native_fill_updating = False

    def _reassert_native_fill_chain(self):
        """Makes the Selections parent path receive the remaining space even after Dock layout updates."""
        if self._native_fill_updating:
            return
        self._native_fill_updating = True
        try:
            chain_changed = False
            for widget in list(self._native_fill_widgets):
                try:
                    if not _widget_alive(widget):
                        continue
                    changed = False
                    minimum_size = _v(widget, 'minimumSize')
                    if (int(_v(minimum_size, 'width', 0) or 0) != 0
                            or int(_v(minimum_size, 'height', 0) or 0) != 0):
                        widget.setMinimumSize(0, 0)
                        changed = True
                    maximum_size = _v(widget, 'maximumSize')
                    if (int(_v(maximum_size, 'width', 16777215)) != 16777215
                            or int(_v(maximum_size, 'height', 16777215)) != 16777215):
                        widget.setMaximumSize(16777215, 16777215)
                        changed = True
                    policy = _v(widget, 'sizePolicy')
                    if (_v(policy, 'horizontalPolicy') != QtGui.QSizePolicy.Expanding
                            or _v(policy, 'verticalPolicy') != QtGui.QSizePolicy.Expanding):
                        widget.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
                        changed = True
                    if changed:
                        widget.updateGeometry()
                        chain_changed = True
                except Exception:
                    pass
            for layout, item_index, _stretch in list(self._native_fill_layout_stretches):
                try:
                    if int(layout.stretch(item_index)) != 1:
                        layout.setStretch(item_index, 1)
                        chain_changed = True
                    if chain_changed:
                        layout.invalidate()
                        layout.activate()
                except Exception:
                    pass
        finally:
            self._native_fill_updating = False

    def _refresh_native_fill_chain(self):
        """Releases the size limits of the Selections parent chain and applies layout expansion (only when the chain changed)."""
        if self._native_fill_updating:
            return
        chain = self._collect_native_fill_chain()
        try:
            token_parts = []
            for widget in chain:
                token_parts.append(str(widget))
                token_parts.append(str(_v(widget, 'layout', None)))
            token = tuple(token_parts)
        except Exception:
            token = tuple(id(widget) for widget in chain)
        if token and token == self._native_fill_token:
            return
        self._restore_native_fill_chain()
        self._native_fill_updating = True
        try:
            self._native_fill_widgets = list(chain)
            self._native_fill_token = token
            for index, widget in enumerate(chain):
                try:
                    policy = _v(widget, 'sizePolicy')
                except Exception:
                    policy = None
                self._native_fill_policies.append((widget, policy))
                minimum_size = _v(widget, 'minimumSize')
                maximum_size = _v(widget, 'maximumSize')
                try:
                    minimum_size = QtCore.QSize(int(_v(minimum_size, 'width', 0) or 0),
                                                int(_v(minimum_size, 'height', 0) or 0))
                except Exception:
                    minimum_size = QtCore.QSize(0, 0)
                try:
                    maximum_size = QtCore.QSize(int(_v(maximum_size, 'width', 16777215)),
                                                int(_v(maximum_size, 'height', 16777215)))
                except Exception:
                    maximum_size = QtCore.QSize(16777215, 16777215)
                self._native_fill_sizes.append((widget, minimum_size, maximum_size))
                try:
                    widget.setMinimumSize(0, 0)
                    widget.setMaximumSize(16777215, 16777215)
                    widget.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
                    widget.updateGeometry()
                except Exception:
                    pass
                if index > 0:
                    try:
                        widget.installEventFilter(self)
                    except Exception:
                        pass
                if index + 1 < len(chain):
                    try:
                        parent_layout = _v(chain[index + 1], 'layout')
                        item_index = int(parent_layout.indexOf(widget))
                        if item_index >= 0 and hasattr(parent_layout, 'setStretch'):
                            original_stretch = int(parent_layout.stretch(item_index))
                            self._native_fill_layout_stretches.append(
                                (parent_layout, item_index, original_stretch))
                            parent_layout.setStretch(item_index, 1)
                            parent_layout.invalidate()
                            parent_layout.activate()
                    except Exception:
                        pass
        finally:
            self._native_fill_updating = False
        # If moved to a new Dock position, fits the Dock column height after layout finishes.
        self._schedule_dock_auto_fill()

    def _schedule_dock_auto_fill(self):
        """Schedules the Selections height auto-fit to run once a moment later."""
        timer = getattr(self, '_auto_fill_timer', None)
        if timer is None:
            return
        try:
            self._auto_fill_retry = 0
            timer.start(PP_DOCK_AUTO_FILL_DELAY_MS)
        except Exception:
            pass

    def _find_dock_column(self):
        """Finds the YPanel containing the SelectionsPanel and the YDock docked in the MainWindow."""
        current = _v(self._panel, 'parentWidget', None)
        ypanel = None
        for _ in range(8):
            if current is None:
                return None, None
            if _class_name(current) == 'YPanel':
                ypanel = current
                break
            current = _v(current, 'parentWidget', None)
        if ypanel is None:
            return None, None
        ydock = _v(ypanel, 'parentWidget', None)
        if ydock is None or _class_name(ydock) != 'YDock':
            return None, None
        # A Floating YDock is an independent window. Only the case docked inside the MainWindow is handled.
        if bool(_v(ydock, 'isWindow', True)):
            return None, None
        return ypanel, ydock

    @staticmethod
    def _rect_tuple(widget):
        geometry = _v(widget, 'geometry', None)
        return (int(_v(geometry, 'x', 0)), int(_v(geometry, 'y', 0)),
                int(_v(geometry, 'width', 0)), int(_v(geometry, 'height', 0)))

    def _run_dock_auto_fill(self):
        """If the Selections panel is alone in the Dock column, drags the bottom border handle down to the end of the column."""
        panel = self._panel
        if panel is None or not _widget_alive(panel):
            return
        if not bool(_v(panel, 'isVisible', False)):
            return
        try:
            dragging = bool(QtGui.QApplication.mouseButtons() & QtCore.Qt.LeftButton)
        except Exception:
            dragging = False
        if dragging:
            # If the user is moving the Dock or dragging a border, retries after it finishes.
            if self._auto_fill_retry < PP_DOCK_AUTO_FILL_MAX_RETRY:
                self._auto_fill_retry += 1
                try:
                    self._auto_fill_timer.start(PP_DOCK_AUTO_FILL_DELAY_MS)
                except Exception:
                    pass
            return
        ypanel, ydock = self._find_dock_column()
        if ypanel is None:
            return
        try:
            px, py, pw, ph = self._rect_tuple(ypanel)
            dock_height = int(_v(ydock, 'height', 0) or 0)
            panel_bottom = py + ph
            if pw <= 0 or ph <= 0 or dock_height <= 0:
                return
            splitter = None
            for child in ydock.children():
                try:
                    if not hasattr(child, 'isWindow'):
                        continue
                    if _same_widget(child, ypanel):
                        continue
                    if not bool(_v(child, 'isVisible', False)):
                        continue
                    cx, cy, cw, ch = self._rect_tuple(child)
                    overlap = min(px + pw, cx + cw) - max(px, cx)
                    if overlap <= 8:
                        continue
                    class_name = _class_name(child)
                    if class_name == 'YPanel':
                        # If there are other panels in the same column, they are not pushed away.
                        return
                    if (class_name == 'YSplitter' and cw > ch
                            and overlap >= pw // 2
                            and panel_bottom - 14 <= cy <= panel_bottom + 6):
                        splitter = child
                except Exception:
                    continue
            if splitter is None:
                return
            sx, sy, sw, sh = self._rect_tuple(splitter)
            delta = (dock_height - sh) - sy
            if delta < PP_DOCK_AUTO_FILL_MIN_GAP:
                return
            self._drag_splitter(splitter, delta)
            new_height = self._rect_tuple(ypanel)[3]
            if new_height <= ph + 4:
                if not _PP_DOCK_AUTO_FILL_FAIL_REPORTED[0]:
                    _PP_DOCK_AUTO_FILL_FAIL_REPORTED[0] = True
                    print('%s Error: could not automatically fit the Selections panel height to the end of the Dock column. '
                          'Please drag the bottom border of the Selections panel down manually.' % PP_LOG)
                return
            self.sync_geometry()
        except Exception as error:
            print('%s Selections height auto-fit error: %s' % (PP_LOG, error))

    @staticmethod
    def _send_splitter_mouse(widget, event_type, global_x, global_y, button, buttons):
        """Sends a synthetic mouse event in the handle's coordinates."""
        origin = widget.mapToGlobal(QtCore.QPoint(0, 0))
        local = QtCore.QPointF(float(global_x - int(_v(origin, 'x', 0))),
                               float(global_y - int(_v(origin, 'y', 0))))
        screen = QtCore.QPointF(float(global_x), float(global_y))
        event = QtGui.QMouseEvent(event_type, local, screen, button, buttons, QtCore.Qt.NoModifier)
        QtGui.QApplication.sendEvent(widget, event)

    def _drag_splitter(self, splitter, delta):
        """Presses the handle, moves it down by delta (px), then releases."""
        width = int(_v(splitter, 'width', 0) or 0)
        height = int(_v(splitter, 'height', 0) or 0)
        start = splitter.mapToGlobal(QtCore.QPoint(width // 2, height // 2))
        start_x = int(_v(start, 'x', 0))
        start_y = int(_v(start, 'y', 0))
        left = QtCore.Qt.LeftButton
        pressed = False
        try:
            self._send_splitter_mouse(splitter, QtCore.QEvent.MouseButtonPress,
                                      start_x, start_y, left, left)
            pressed = True
            steps = max(1, PP_DOCK_AUTO_FILL_STEPS)
            for step in range(1, steps + 1):
                y = start_y + int(round(delta * float(step) / steps))
                self._send_splitter_mouse(splitter, QtCore.QEvent.MouseMove,
                                          start_x, y, QtCore.Qt.NoButton, left)
        finally:
            if pressed:
                self._send_splitter_mouse(splitter, QtCore.QEvent.MouseButtonRelease,
                                          start_x, start_y + int(delta), left, QtCore.Qt.NoButton)

    def sync_geometry(self):
        try:
            if self._panel is None or not _widget_alive(self._panel):
                return
            self._refresh_native_fill_chain()     
            self._reassert_native_fill_chain()    
            self.setGeometry(_v(self._panel, 'rect'))
            host_rect = _v(self, 'rect')
            try:
                self._host_layout.setGeometry(host_rect)
                self._host_layout.activate()
            except Exception:
                pass
            if self._content is not None:
                self._content.setGeometry(host_rect)
            self.raise_()
        except Exception as error:
            print('%s Selections host size sync error: %s' % (PP_LOG, error))

    def eventFilter(self, watched, event):
        if self._native_fill_updating:
            return False
        try:
            event_type = event.type()
            if event_type in (QtCore.QEvent.Resize, QtCore.QEvent.Move,
                              QtCore.QEvent.Show, QtCore.QEvent.LayoutRequest,
                              QtCore.QEvent.ParentChange):
                if event_type == QtCore.QEvent.ParentChange:
                    self._refresh_native_fill_chain()   # re-captures the chain when the Dock position changes.
                self.sync_geometry()
                self.show()
                self.raise_()
            elif event_type in (QtCore.QEvent.Hide, QtCore.QEvent.Close):
                self.hide()
        except Exception:
            pass
        return False

    def dispose(self):
        # stops the scheduled height auto-fit and restores the size constraints of the parent chain.
        try:
            self._auto_fill_timer.stop()
        except Exception:
            pass
        panel = self._panel
        try:
            if panel is not None and _widget_alive(panel):
                panel.removeEventFilter(self)
        except Exception:
            pass
        try:
            self._restore_native_fill_chain()
        except Exception:
            pass
        self.release_content()
        self.hide()
        try:
            self.setProperty(PP_SELECTIONS_HOST_MARKER_PROPERTY, '')
        except Exception:
            pass
        pp_release_selections_panel(panel)
        self._panel = None
        try:
            self.setObjectName('')
            self.setParent(None)
        except Exception:
            pass
        pp_retire(self)



# ============================================================
# Shows guidelines dragged from the native Ruler in the Vertical mode preview
#   Installs a local event filter only on the Ruler widgets to detect presses, and briefly checks the cursor/button state while dragging.
#   When dropped in the preview area, deletes the one real guideline FontLab created on the active glyph and creates a preview guideline.
# ============================================================
PP_RULER_DRAG_POLL_MS = 25          # cursor check interval while dragging
PP_RULER_DRAG_TIMEOUT_SEC = 120.0   # safety timeout when the button release can never be read
PP_NATIVE_GUIDE_RETRY_MS = (0, 120, 400)   # delete retries in case FontLab creates the guideline late


PP_NATIVE_GUIDE_UNDO_TITLE = 'Preview Panel Ruler Guide'   # Undo/History name for deleting the real guideline


def _pp_guide_id(guide):
    """flGuideLine object id (first criterion for comparing guidelines). None if unreadable."""
    try:
        value = _v(guide, 'id')
        return None if value is None else int(value)
    except Exception:
        return None


def _pp_guide_sig(guide):
    """Signature for comparing guidelines (segment, name). Empty tuple if unreadable.
    FontLab 8's flGuideLine.vector is an flNode, so linef (QLineF) / centerPoint are read."""
    parts = []
    try:
        line = _v(guide, 'linef')
        for point in (line.p1(), line.p2()):
            parts.append(round(float(_v(point, 'x', 0.0)), 3))
            parts.append(round(float(_v(point, 'y', 0.0)), 3))
    except Exception:
        try:
            point = _v(guide, 'centerPoint')
            parts.append(round(float(_v(point, 'x', 0.0)), 3))
            parts.append(round(float(_v(point, 'y', 0.0)), 3))
            parts.append(round(float(_v(guide, 'angle', 0.0)), 3))
        except Exception:
            pass
    try:
        parts.append(str(_v(guide, 'name', '') or ''))
    except Exception:
        pass
    return tuple(parts)


def _pp_guide_list(host):
    try:
        return list(_v(host, 'guidelines') or [])
    except Exception:
        return []


def _pp_guide_hosts():
    """Returns the guideline stores of the active glyph's active layer and of the font as [(kind, store, glyph, id, layer name)].
    The layer is read via the same path as Dalgas A_ContextMenu_Create_Guide_OnOff v4.25
    (fgGlyph.activeLayer name → flGlyph.getLayerByName)."""
    hosts = []
    font = None
    fl_glyph = None
    glyph_name = ''
    layer_name = ''
    try:
        font = fl6.CurrentFont()
        fg = fl6.CurrentGlyph()
        if font is not None and fg is not None:
            glyph_name = str(_v(fg, 'name', '') or '')
            layer_name = str(_v(fg.activeLayer, 'name', '') or '')
            fl_glyph = fl6.flGlyph(fg, font)
    except Exception:
        fl_glyph = None
    if fl_glyph is not None and layer_name:
        try:
            layer = fl_glyph.getLayerByName(layer_name)
            if layer is not None:
                key = ('layer', glyph_name, layer_name)
                hosts.append(('layer', layer, fl_glyph, key, layer_name))
        except Exception:
            pass
    if font is not None:
        try:
            host = fl6.flPackage(font).guidelinesHost
            if host is not None:
                hosts.append(('font', host, None, ('font', pp_font_id(font)), ''))
        except Exception:
            pass
    return hosts


def pp_snapshot_native_guides():
    """Guideline state at the time the Ruler is pressed. {kind: (store id, count, signature list, id list)}"""
    snap = {}
    for kind, host, _glyph, key, _layer_name in _pp_guide_hosts():
        guides = _pp_guide_list(host)
        snap[kind] = (key, len(guides), [_pp_guide_sig(g) for g in guides],
                      [_pp_guide_id(g) for g in guides])
    return snap


def _pp_find_new_guide(guides, before):
    """Finds the one guideline that did not exist at press time (id → signature → last item)."""
    old_ids = [value for value in before[3] if value is not None]
    if len(old_ids) == len(before[3]):
        for guide in guides:
            guide_id = _pp_guide_id(guide)
            if guide_id is not None and guide_id not in old_ids:
                return guide
    remaining = list(before[2])
    target = None
    for guide in guides:
        sig = _pp_guide_sig(guide)
        if sig and sig in remaining:
            remaining.remove(sig)
        else:
            target = guide
    return target if target is not None else guides[-1]


def _pp_fresh_layer_guides(layer_name):
    """Creates FontLab objects anew and re-reads the real guideline list of the active glyph layer."""
    try:
        fl_glyph = fl6.flGlyph(fl6.CurrentGlyph(), fl6.CurrentFont())
        layer = fl_glyph.getLayerByName(layer_name)
        return list(layer.guidelines)
    except Exception:
        return None


def _pp_notify_glyph_guides(fl_glyph):
    """Notifies Undo/History, glyph update and Glyph Window update
    (same path as _rg_notify_changes of Dalgas A_ContextMenu_Create_Guide_OnOff v4.25)."""
    try:
        fl6.flItems.notifyChangesApplied(PP_NATIVE_GUIDE_UNDO_TITLE, fl_glyph, True)
    except Exception:
        pass
    try:
        package_id = int(fl_glyph.fgPackage.id)
        glyph_id = int(fl_glyph.fgGlyphId)
        try:
            fl6.flItems.notifyGlyphUpdated(package_id, glyph_id)
        except Exception:
            fl6.flItems.instance().notifyGlyphUpdated(package_id, glyph_id)
    except Exception:
        pass
    try:
        workspace = fl6.flWorkspace.instance()
        workspace.update()
        workspace.updateActiveViewport()
    except Exception:
        pass


def _pp_copy_guide(guide):
    """Copy of an flGuideLine (copy constructor → clone()). None on failure."""
    for maker in (lambda: fl6.flGuideLine(guide), lambda: guide.clone()):
        try:
            copy = maker()
            if copy is not None:
                return copy
        except Exception:
            continue
    return None


def _pp_remove_layer_guide(target, guides, before, layer_name):
    """Deletes only one guideline of the glyph layer. flLayer has no API for deleting one (removeGuideline).
    Uses only verified APIs.
      - flLayer.removeGuides(True, True): the Remove Guide path of Dalgas A_ContextMenu_Create_Guide_OnOff v4.25
      - flLayer.appendGuidelines([...]): the path of TypeRig addGuideline / layer_copy_guides (v4.25 Create Guide)
    1) Before deleting, copies all guidelines to keep (excluding the new guideline). If even one cannot be copied, nothing is deleted.
    2) Deletes horizontal/vertical guidelines with removeGuides(True, True).
    3) Re-reads, excludes guidelines that remained undeleted (diagonals etc.), and restores only the copies of deleted existing guidelines with appendGuidelines.
    4) Re-reads and checks that the count equals the count at press time and that the new guideline is gone (signature comparison).
    Returns: (success, list of error descriptions)"""
    tried = []
    before_count = before[1]
    before_sigs = list(before[2])
    target_id = _pp_guide_id(target)
    target_sig = _pp_guide_sig(target)
    kept = [g for g in guides if g is not target]
    copies = []
    for guide in kept:
        copy = _pp_copy_guide(guide)
        if copy is None:
            tried.append('failed to copy existing guidelines - nothing deleted')
            return False, tried
        copies.append((_pp_guide_id(guide), _pp_guide_sig(guide), copy))
    try:
        layer = fl6.flGlyph(fl6.CurrentGlyph(), fl6.CurrentFont()).getLayerByName(layer_name)
        layer.removeGuides(True, True)
    except Exception as error:
        tried.append('flLayer.removeGuides(%s)' % error)
        return False, tried
    survivors = _pp_guide_list(layer)
    survivor_ids = set(i for i in (_pp_guide_id(g) for g in survivors) if i is not None)
    survivor_sigs = [_pp_guide_sig(g) for g in survivors]
    restore = []
    for guide_id, sig, copy in copies:
        if guide_id is not None and guide_id in survivor_ids:
            continue
        if guide_id is None and sig and sig in survivor_sigs:
            survivor_sigs.remove(sig)
            continue
        restore.append(copy)
    if restore:
        try:
            layer.appendGuidelines(restore)
        except Exception as error:
            tried.append('flLayer.appendGuidelines(%s) - %d existing guidelines may have been deleted (undo with Ctrl+Z)'
                         % (error, len(restore)))
            return False, tried
    fresh = _pp_fresh_layer_guides(layer_name)
    if fresh is None:
        tried.append('failed to re-read the result')
        return False, tried
    if len(fresh) != before_count:
        tried.append('guideline count %d (%d at press time)' % (len(fresh), before_count))
        return False, tried
    if target_id is not None and any(_pp_guide_id(g) == target_id for g in fresh):
        tried.append('the new guideline remains')
        return False, tried
    fresh_sigs = [_pp_guide_sig(g) for g in fresh]
    if all(before_sigs) and all(fresh_sigs) and sorted(fresh_sigs) != sorted(before_sigs):
        tried.append('restored guideline positions differ from press time')
        return False, tried
    if target_sig and target_sig not in before_sigs and target_sig in fresh_sigs:
        tried.append('the new guideline remains')
        return False, tried
    return True, tried


def pp_remove_new_native_guide(snap):
    """Deletes the one guideline added since press time.
    Returns: True (done: deleted or cannot be deleted), False (no new guideline yet - retry)."""
    if not snap:
        return True
    for kind, host, fl_glyph, key, layer_name in _pp_guide_hosts():
        before = snap.get(kind)
        if before is None or before[0] != key:
            continue
        guides = _pp_guide_list(host)
        if len(guides) != before[1] + 1:
            continue
        target = _pp_find_new_guide(guides, before)
        if kind == 'layer':
            done, tried = _pp_remove_layer_guide(target, guides, before, layer_name)
            if done:
                _pp_notify_glyph_guides(fl_glyph)
            else:
                print('%s Failed to delete the Ruler guideline: %s' % (PP_LOG, ', '.join(tried) or 'none'))
            return True
        # Font guideline: same path as TypeRig pFont.delGuideline
        try:
            host.removeGuideline(target)
        except Exception:
            try:
                target.remove()
            except Exception as error:
                print('%s Failed to delete the Ruler font guideline: %s' % (PP_LOG, error))
                return True
        try:
            host.guidelinesChanged()
        except Exception:
            pass
        return True
    return False


class PPRulerGuideWatcher(QtGui.QWidget):
    """Detects Ruler presses to track the drag, and creates a preview guideline when dropped in the preview area."""

    def __init__(self, controller):
        QtGui.QWidget.__init__(self, controller)
        self.hide()
        self._ctrl = controller
        self._rulers = []           # [(kind, widget)] - 'left' vertical line, 'top' horizontal line
        self._drag_kind = None
        self._drag_started = 0.0
        self._last_local = None
        self._snapshot = None
        self._remove_left = []
        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.setInterval(PP_RULER_DRAG_POLL_MS)
        self._poll_timer.timeout.connect(self._poll)
        self._remove_timer = QtCore.QTimer(self)
        self._remove_timer.setSingleShot(True)
        self._remove_timer.timeout.connect(self._remove_tick)

    # ── Ruler widget connection ──────────────────────────────────────
    def sync(self, canvas):
        """Installs the filter on the canvas's Ruler widgets. Turning off the Ruler removes the widgets, so they are searched anew each time."""
        found = pp_ruler_widgets(canvas) if canvas is not None else {}
        wanted = [(kind, widget) for kind, widget in found.items()]
        same = len(wanted) == len(self._rulers)
        if same:
            for kind, widget in wanted:
                if not any(k == kind and _same_widget(w, widget) for k, w in self._rulers):
                    same = False
                    break
        if same:
            return
        self._unwatch()
        for kind, widget in wanted:
            try:
                widget.installEventFilter(self)
                self._rulers.append((kind, widget))
            except Exception:
                continue

    def _unwatch(self):
        for _kind, widget in self._rulers:
            try:
                if _widget_alive(widget):
                    widget.removeEventFilter(self)
            except Exception:
                pass
        self._rulers = []

    def eventFilter(self, watched, event):
        try:
            if _v(event, 'type') != QtCore.QEvent.MouseButtonPress:
                return False
            if _v(event, 'button') != QtCore.Qt.LeftButton:
                return False
            for kind, widget in self._rulers:
                if watched is widget or _same_widget(watched, widget):
                    self._start(kind)
                    break
        except Exception as error:
            print('%s Ruler detection error: %s' % (PP_LOG, error))
        return False

    # ── Drag tracking ────────────────────────────────────────────
    def _accepting(self):
        ctrl = self._ctrl
        if ctrl is None or ctrl._shutdown_done or ctrl._collapsed:
            return False
        return ctrl.st['mode'] == 'v' and ctrl._overlay_usable()

    def _start(self, kind):
        if not self._accepting():
            return
        try:
            self._remove_timer.stop()
        except Exception:
            pass
        self._remove_left = []
        self._drag_kind = kind
        self._drag_started = time.time()
        self._last_local = None
        try:
            self._snapshot = pp_snapshot_native_guides()
        except Exception:
            self._snapshot = None
        self._poll_timer.start()

    def _preview_point(self):
        """Preview canvas coordinates (x, y) if the cursor is inside the preview area, otherwise None."""
        canvas = self._ctrl._canvas()
        if canvas is None or not bool(_v(canvas, 'isVisible', False)):
            return None
        try:
            local = canvas.mapFromGlobal(QtGui.QCursor.pos())
            x = float(_v(local, 'x', 0))
            y = float(_v(local, 'y', 0))
        except Exception:
            return None
        if 0.0 <= x < float(_int(canvas, 'width')) and 0.0 <= y < float(_int(canvas, 'height')):
            return x, y
        return None

    def _poll(self):
        kind = self._drag_kind
        if kind is None or not self._accepting():
            self._stop()
            return
        try:
            held = bool(QtGui.QApplication.mouseButtons() & QtCore.Qt.LeftButton)
        except Exception:
            held = False
        point = self._preview_point()
        canvas = self._ctrl._canvas()
        if held and time.time() - self._drag_started < PP_RULER_DRAG_TIMEOUT_SEC:
            self._last_local = point
            if canvas is not None:
                canvas.set_drag_guide(kind, point)
            return
        # The button was released: if the drop position is the preview area, creates a guideline.
        drop = point if point is not None else self._last_local
        snapshot = self._snapshot
        self._stop()
        if drop is None or canvas is None:
            return
        try:
            canvas.add_ruler_guide(kind, drop)
        except Exception as error:
            print('%s Ruler guideline creation error: %s' % (PP_LOG, error))
            return
        if snapshot:
            self._snapshot = snapshot
            self._remove_left = list(PP_NATIVE_GUIDE_RETRY_MS)
            self._remove_tick()

    def _remove_tick(self):
        """Deletes the real guideline FontLab created. If it has not appeared yet, checks again a little later."""
        snapshot = self._snapshot
        if self._ctrl is None or self._ctrl._shutdown_done:
            self._snapshot = None
            self._remove_left = []
            return
        if not snapshot or not self._remove_left:
            self._snapshot = None
            return
        delay = self._remove_left.pop(0)
        if delay > 0:
            self._remove_left.insert(0, 0)
            self._remove_timer.start(delay)
            return
        try:
            done = pp_remove_new_native_guide(snapshot)
        except Exception as error:
            print('%s Ruler guideline deletion error: %s' % (PP_LOG, error))
            done = True
        if done or not self._remove_left:
            self._snapshot = None
            self._remove_left = []
            canvas_widget = getattr(self._ctrl, '_canvas_widget', None)
            if canvas_widget is not None and _widget_alive(canvas_widget):
                try:
                    canvas_widget.update()
                except Exception:
                    pass
            return
        self._remove_tick()

    def _stop(self):
        try:
            self._poll_timer.stop()
        except Exception:
            pass
        self._drag_kind = None
        self._last_local = None
        canvas = self._ctrl._canvas() if self._ctrl is not None else None
        if canvas is not None:
            try:
                canvas.set_drag_guide(None, None)
            except Exception:
                pass

    def shutdown(self):
        try:
            self._remove_timer.stop()
        except Exception:
            pass
        self._snapshot = None
        self._remove_left = []
        self._stop()
        self._unwatch()
        self._ctrl = None


# ============================================================
# Controller (canvas tracking, layout, Dock, settings, shutdown)
# ============================================================
class PPController(QtGui.QWidget):
    """Manages Glyph Window canvas discovery, overlay layout, Dock, refresh and shutdown."""

    def __init__(self):
        QtGui.QWidget.__init__(self, None)
        self.setObjectName('DalgasPreviewPanelController')
        self.hide()
        self._shutdown_done = False
        self._changing_canvas = False
        self._canvas_widget = None
        self._watched = []
        self._sync_pending = False
        self._collapsed = False
        self._raising_collapsed = False   # raising the collapsed bar again (re-entrancy guard)
        self._host = None
        self._host_miss = 0
        self._selections_opened_by_us = False
        self._last_sig = None
        self._last_geom = (None, None)
        self._last_inst = None
        self._last_var = None        # other axis values of the VARIATIONS panel (excluding Weight)
        self._tick = 0
        self._docked_viewport_widget = None     # Glyph Window canvas followed in the Dock state
        self.st = pp_load_settings()
        # every time the script runs, R starts as the blue R (rules-applied R).
        #   Underlined R (v_vert) and simple rotation R (rotate_plain) are turned off regardless of saved values.
        self.st['rotate_latin'] = True
        self.st['rotate_plain'] = False
        self.st['v_vert'] = False
        # Vertical mode text written in the settings file (from the last Save). This value is written on auto-save.
        self._saved_v_text = list(self.st.get('v_text') or [])
        # Starts in dark mode if FontLab is in dark mode. Otherwise uses the saved color scheme.
        if PP_FONTLAB_DARK:
            self.st['dark'] = True
        PP_THEME['dark'] = bool(self.st['dark'])
        self.v_view = None          # Vertical mode starts with Interpolation / All Masters OFF.
        # All Instances preview (Interpolation button Ctrl/Alt+click) state. Per mode, not written to the settings file.
        self.interp_all = {'h': False, 'v': False}
        if self.st.get('dock_fit', 'width') == 'width' or self.st.get('h_fit', 'height') == 'width':
            for zoom_key in ('h_zoom_interp', 'h_zoom_all', 'h_zoom_masters'):
                self.st[zoom_key] = 1.0
        # glyph size (px) of the Vertical mode Interpolation / All Masters views. None means the size that fills the window.
        self.v_view_size = None
        # user input text kept while the Glyph Window text is shown (None means the user text is being shown)
        self.v_user_text_stash = None
        # preview guidelines dragged from the Ruler (typesetting coordinates). Not saved to the settings file.
        self.v_guides = []
        # Horizontal mode text (text read from the Glyph Window or typed directly). Not written to the settings file.
        self.h_text = []
        self.h_text_on = False      # whether Horizontal mode is showing text (starts in the glyph view on every run)
        self.font_cache = PPFontCache()
        self.tracker = PPTextToolTracker(self._on_text_tool_changed)
        self.overlay = PPPanel(self)
        self.overlay.hide()

        self._save_timer = QtCore.QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(PP_SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._save_now)
        self._target_timer = QtCore.QTimer(self)
        self._target_timer.setInterval(PP_TARGET_INTERVAL_MS)
        self._target_timer.timeout.connect(self._sync_target)
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setInterval(PP_REFRESH_INTERVAL_MS)
        self._refresh_timer.timeout.connect(self._refresh_tick)
        self.ruler_watcher = PPRulerGuideWatcher(self)     
        try:
            QtGui.QApplication.instance().aboutToQuit.connect(self.shutdown)
        except Exception:
            pass
        self._target_timer.start()
        self._refresh_timer.start()
        self._sync_target()
        self.overlay.canvas.rebuild()

    # ── Shared queries ────────────────────────────────────────────
    def text_tool_active(self):
        try:
            return self.tracker.is_text_tool_active()
        except Exception:
            return True

    def _on_text_tool_changed(self, active):
        # changing the FontLab tool does not end panel input (input is independent of the Text Tool).
        return

    def schedule_save(self):
        if self._shutdown_done:
            return
        try:
            self._save_timer.start()
        except Exception:
            self._save_now()

    def _save_now(self):
        # v_text stores the text from the last Save, not the current on-screen text.
        data = dict(self.st)
        data['v_text'] = list(getattr(self, '_saved_v_text', None) or [])
        pp_save_settings(data)

    def _overlay_usable(self):
        overlay = self.overlay
        if overlay is None:
            return False
        try:
            _v(overlay, 'isVisible')
            return True
        except Exception:
            return False

    def _canvas(self):
        return self.overlay.canvas if self._overlay_usable() else None

    # ── Icon actions ──────────────────────────────────────────
    def set_mode(self, mode):
        if self._shutdown_done or mode == self.st['mode'] or self._collapsed:
            return
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()
        if mode == 'v':
            # entering Vertical mode always shows the user input text (the text saved in the settings file).
            self.v_view = None
            self.restore_user_text()    
            if canvas is not None:
                canvas._cursor = len(self.st['v_text'])
                canvas._anchor = None
        elif canvas is not None:
            canvas._cursor = len(self.h_text)    # Horizontal mode text caret
            canvas._anchor = None
        self.st['mode'] = mode
        self._after_mode_change()
        self.schedule_save()

    def _after_mode_change(self):
        if not self._overlay_usable():
            return
        self.overlay.relayout()
        self.overlay.sync_sliders()
        self._sync_geometry()
        self.overlay.relayout()
        self.overlay.canvas.rebuild()
        self.overlay.update_icons()

    def toggle_view(self, kind):
        if self._collapsed:
            return
        # Ctrl (Mac Command)+click / Alt (Mac Option)+click on the Interpolation button turns on the All Instances preview.
        #   A plain click in the All Instances state does not turn it off but returns to the regular Interpolation Preview.
        mode = self.st['mode']
        if kind == 'interp':
            all_click = pp_ctrl_down() or pp_alt_down()
            current = self.st['h_view'] if mode == 'h' else self.v_view
            text_on = mode == 'h' and self.h_text_on
            if all_click or (self.interp_all.get(mode) and current == 'interp' and not text_on):
                self.interp_all[mode] = bool(all_click)
                if mode == 'h':
                    if text_on:
                        self.set_h_text_mode(False)
                    self.st['h_view'] = 'interp'
                    self._reset_h_fit_zoom()
                    self.schedule_save()
                    self._refresh_view()
                elif current == 'interp':
                    self._refresh_view()
                else:
                    self.set_v_view('interp')
                return
        self.interp_all[mode] = False
        if self.st['mode'] == 'h':
            if self.h_text_on:
                # pressed while Horizontal mode is showing text, ends the text display and turns on that view.
                self.set_h_text_mode(False)
                self.st['h_view'] = kind
            else:
                self.st['h_view'] = None if self.st['h_view'] == kind else kind
            self._reset_h_fit_zoom()
            self.schedule_save()
        else:
            self.set_v_view(None if self.v_view == kind else kind)
            return
        self._refresh_view()

    def _h_fit_mode(self):
        docked = False
        try:
            docked = bool(self.overlay is not None and self.overlay.is_docked())
        except Exception:
            docked = False
        if docked:
            return self.st.get('dock_fit', 'width')
        return self.st.get('h_fit', 'height')

    def _reset_h_fit_zoom(self):
        if self.st.get('h_view') and self._h_fit_mode() == 'width':
            self.st[self.h_zoom_key()] = 1.0

    def set_v_view(self, view):
        canvas = self._canvas()
        if view and canvas is not None:
            canvas.end_edit()
        self.v_view = view
        self.v_view_size = None     # every time a view is turned on, starts at the size that fills the window.
        self._refresh_view()

    def _refresh_view(self):
        if not self._overlay_usable():
            return
        self.overlay.canvas.rebuild()
        self.overlay.update_icons()

    def h_zoom_key(self):
        """Zoom setting key of the current Horizontal mode view. h_zoom when showing text or with the view off."""
        if self.st.get('mode') == 'h' and not self.h_text_on:
            view = self.st.get('h_view')
            if view == 'interp':
                return 'h_zoom_all' if self.interp_all.get('h') else 'h_zoom_interp'
            if view == 'masters':
                return 'h_zoom_masters'
        return 'h_zoom'

    def zoom(self, direction):
        step = PP_H_ZOOM_STEP_SHIFT if pp_shift_down() else PP_H_ZOOM_STEP
        key = self.h_zoom_key()   # per-view zoom
        zoom = float(self.st[key]) + (step if direction > 0 else -step)
        self.st[key] = round(max(PP_H_ZOOM_MIN, min(PP_H_ZOOM_MAX, zoom)), 4)
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.update()

    def set_h_align(self, align):
        if align not in ('left', 'center', 'right'):
            return
        self.st['h_align'] = align
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.reset_pan()
            self.overlay.update_icons()

    def click_vmode(self):
        """In Horizontal mode switches to Vertical mode; in Vertical mode toggles the column direction (L→R / R→L)."""
        if self._shutdown_done or self._collapsed:
            return
        if self.st['mode'] != 'v':
            self.set_mode('v')
            return
        self.st['v_ltr'] = not bool(self.st.get('v_ltr', False))
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.update()
            self.overlay.update_icons()

    def toggle_rotate(self):
        # Alt+click is simple rotation R (rotates all characters except Hangul/Han/Kana 90° without rules),
        #   a regular click is rules-applied R. If the same method is on, it turns off; if the other method is on, it switches.
        # Ctrl+click (macOS Command+click) toggles OpenType vertical writing glyphs (vert) / vertical Advance.
        #   Independent of R's rotation state.
        if pp_ctrl_down():
            self.st['v_vert'] = not bool(self.st.get('v_vert'))
            try:
                self.font_cache.forget_vert()
                self.font_cache.vert_reported = False
                self.font_cache.vadv_reported = False
            except Exception:
                pass
            print('%s Vertical writing glyphs (vert): %s' % (PP_LOG, 'on' if self.st['v_vert'] else 'off'))
            self.schedule_save()
            self._refresh_view()
            return
        plain = pp_alt_down()
        if self.st.get('v_vert'):
            # clicking R in the underlined R state turns off underlined R and turns on R (regular click: rules-applied R, Alt+click:
            #   simple rotation R). R is not turned off from underlined R.
            self.st['v_vert'] = False
            self.st['rotate_latin'] = True
            self.st['rotate_plain'] = plain
            print('%s Vertical writing glyphs (vert): off' % PP_LOG)
            self.schedule_save()
            self._refresh_view()
            return
        if self.st['rotate_latin'] and bool(self.st.get('rotate_plain')) == plain:
            self.st['rotate_latin'] = False
        else:
            self.st['rotate_latin'] = True
            self.st['rotate_plain'] = plain
        self.schedule_save()
        self._refresh_view()

    def click_right_guide(self):
        """Right thick helper-line button. Ctrl (macOS Command)+click deletes all preview guidelines.
        Alt (macOS Option)+click does the same."""
        if pp_ctrl_down() or pp_alt_down():
            self.clear_v_guides()
            return
        self.toggle_guide('right')

    def clear_v_guides(self):
        """Deletes all preview guidelines dragged from the Ruler."""
        if not self.v_guides:
            return
        self.v_guides = []
        if self._overlay_usable():
            self.overlay.canvas.update()

    def toggle_guide(self, name):
        key = 'guide_' + name
        self.st[key] = not self.st[key]
        if self.st[key] and name == 'center':
            self.st['guide_right'] = False
        elif self.st[key] and name == 'right':
            self.st['guide_center'] = False
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.update_icons()
            self.overlay.canvas.update()

    # ── Glyph Window text exchange ─────────────────────
    def restore_user_text(self):
        """If the Glyph Window text was being shown, returns to the kept user input text. True if returned."""
        stash = self.v_user_text_stash
        if stash is None:
            return False
        self.v_user_text_stash = None
        self.st['v_text'][:] = list(stash)
        canvas = self._canvas()
        if canvas is not None:
            canvas._cursor = len(self.st['v_text'])
            canvas._anchor = None
        return True

    def _current_font(self):
        font = pp_current_font()    # prefers the font of the canvas the panel is attached to.
        if font is not None:
            try:
                self.font_cache.sync(font)
            except Exception:
                pass
        return font

    def load_text_from_glyph_window(self):
        """Inward arrow: reads the active Glyph Window text and shows it in the Vertical mode preview (not written to the settings file)."""
        if self._shutdown_done or self._collapsed or self.st['mode'] != 'v':
            return
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()   # the composing character is committed to the user input text first.
        font = self._current_font()
        if font is None:
            return
        tokens = pp_read_glyph_window_tokens(font, self.font_cache)
        if tokens is None:
            print('%s Could not read the text of the active Glyph Window.' % PP_LOG)
            return
        if self.v_user_text_stash is None:
            self.v_user_text_stash = list(self.st['v_text'])
        self.st['v_text'][:] = tokens
        self.v_view = None
        if canvas is not None:
            canvas._cursor = len(self.st['v_text'])
            canvas._anchor = None
            canvas._preedit = ''
            canvas._pre_cells = []
            canvas._scroll_v = 0.0
        self._refresh_view()

    def click_user_text(self):
        """Saved Text icon. A click loads the user text from the settings file, Alt+click saves the current contents."""
        if self._shutdown_done or self._collapsed or self.st['mode'] != 'v':
            return
        if pp_alt_down():
            self.save_user_text()
        else:
            self.load_user_text()

    def save_user_text(self):
        """Writes the current contents of the preview area to Dalgas_Preview_Panel_Settings.json."""
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()
        # The saved contents become the user text, so the kept text is discarded.
        self.v_user_text_stash = None
        self._saved_v_text = list(self.st['v_text'])   # text is written only when Save is used.
        try:
            self._save_timer.stop()
        except Exception:
            pass
        self._save_now()
        if self._overlay_usable():
            self.overlay.update_icons()

    def load_user_text(self):
        """Loads the user text written in Dalgas_Preview_Panel_Settings.json into the preview area."""
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()
        # removed the behavior of first writing unsaved input. Loads the saved text of the settings file as is.
        try:
            tokens = list(pp_load_settings().get('v_text') or [])
        except Exception as error:
            print('%s Could not read the user text from the settings file: %s' % (PP_LOG, error))
            return
        self._saved_v_text = list(tokens)
        self.v_user_text_stash = None
        self.st['v_text'][:] = tokens
        self.v_view = None
        if canvas is not None:
            canvas._cursor = len(self.st['v_text'])
            canvas._anchor = None
            canvas._preedit = ''
            canvas._pre_cells = []
            canvas._scroll_v = 0.0
        self._refresh_view()

    # ── Horizontal mode Glyph Import/Export, text input mode ─────────────
    def set_h_text_mode(self, on):
        """Turns Horizontal mode text display on and off (not written to the settings file)."""
        on = bool(on)
        canvas = self._canvas()
        if not on and canvas is not None:
            canvas.end_edit()
        if on == self.h_text_on:
            return
        self.h_text_on = on
        if canvas is not None:
            canvas._cursor = len(self.h_text)
            canvas._anchor = None
            canvas._pan_x = 0.0
            canvas._pan_y = 0.0
        self._refresh_view()

    def click_h_glyph_io(self):
        """Horizontal mode Glyph Import icon. A click imports the Glyph Window text;
        Ctrl (Mac Command)+click / Alt (Mac Option)+click exports the preview text to the Glyph Window."""
        if self._shutdown_done or self._collapsed or self.st['mode'] != 'h':
            return
        if pp_ctrl_down() or pp_alt_down():
            self.send_h_text_to_glyph_window()
        else:
            self.load_h_text_from_glyph_window()

    def load_h_text_from_glyph_window(self):
        """Reads the active Glyph Window text and shows it in the Horizontal mode preview (not written to the settings file)."""
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()
        font = self._current_font()
        if font is None:
            return
        tokens = pp_read_glyph_window_tokens(font, self.font_cache)
        if tokens is None:
            print('%s Could not read the text of the active Glyph Window.' % PP_LOG)
            return
        self.h_text[:] = tokens
        self.h_text_on = True
        if canvas is not None:
            canvas._cursor = len(self.h_text)
            canvas._anchor = None
            canvas._preedit = ''
            canvas._pre_cells = []
            canvas._pan_x = 0.0
            canvas._pan_y = 0.0
        self._refresh_view()

    def send_h_text_to_glyph_window(self):
        """Puts the Horizontal mode preview text into the active Glyph Window (only while showing text)."""
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()
        if not self.h_text_on:
            return
        tokens = list(self.h_text)
        if not any(token != '\n' for token in tokens):
            return
        if self._current_font() is None:
            return
        if pp_write_glyph_window_tokens(tokens):
            self._refresh_view()

    def send_text_to_glyph_window(self):
        """Outward arrow: puts the Vertical mode preview text into the active Glyph Window."""
        if self._shutdown_done or self._collapsed or self.st['mode'] != 'v':
            return
        canvas = self._canvas()
        if canvas is not None:
            canvas.end_edit()
        tokens = list(self.st['v_text'])
        if not any(token != '\n' for token in tokens):
            return
        if self._current_font() is None:
            return
        if pp_write_glyph_window_tokens(tokens):
            self._refresh_view()

    def zoom_v(self, direction):
        """Vertical mode Alt+wheel. Increases or decreases by 5% (Shift: 10%) of the current display size (Size slider value)."""
        if self.st.get('mode') != 'v' or not self._overlay_usable():
            return
        try:
            current = int(_v(self.overlay.size_slider, 'value', self.st['v_size']))
        except Exception:
            current = int(self.st['v_size'])
        ratio = PP_H_ZOOM_STEP_SHIFT if pp_shift_down() else PP_H_ZOOM_STEP
        change = max(1, int(round(current * ratio)))
        self.set_v_size(current + (change if direction > 0 else -change))

    def set_v_size(self, value):
        try:
            value = int(value)
        except Exception:
            return
        value = max(PP_V_SIZE_MIN, min(PP_V_SIZE_MAX, value))
        if self.st['mode'] == 'v' and self.v_view:
            # in the Interpolation / All Masters views, changes the view-only size (v_size and the settings file stay unchanged).
            self.v_view_size = value
            if self._overlay_usable():
                self.overlay.canvas.update()
            return
        self.st['v_size'] = value
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.update()

    def set_v_leading(self, value):
        try:
            value = int(value)
        except Exception:
            return
        self.st['v_leading'] = max(PP_V_LEADING_MIN, min(PP_V_LEADING_MAX, value))
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.update()

    def set_v_spacing(self, value):
        try:
            value = int(value)
        except Exception:
            return
        self.st['v_spacing'] = max(-100, min(100, value))
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.update()

    def toggle_dock_fit(self):
        # also used in the Floating state (dock_fit in the Dock state, h_fit in the Floating state). Resets only the current view's zoom.
        docked = False
        try:
            docked = bool(self.overlay is not None and self.overlay.is_docked())
        except Exception:
            docked = False
        if docked:
            self.st['dock_fit'] = 'width' if self.st.get('dock_fit') == 'height' else 'height'
        else:
            self.st['h_fit'] = 'width' if self.st.get('h_fit', 'height') == 'height' else 'height'
        self.st[self.h_zoom_key()] = 1.0
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.canvas.reset_pan()
            self.overlay.update_icons()

    def toggle_theme(self):
        PP_THEME['dark'] = not PP_THEME['dark']
        self.st['dark'] = bool(PP_THEME['dark'])
        self.schedule_save()
        if self._overlay_usable():
            self.overlay.apply_theme()

    def toggle_collapsed(self):
        if self._shutdown_done or self._host is not None or not self._overlay_usable():
            return
        self._collapsed = not self._collapsed
        self.overlay.set_collapsed(self._collapsed)
        self._sync_geometry()
        if not self._collapsed:
            self.overlay.relayout()
            self.overlay.canvas.rebuild()

    def close_script(self):
        self.shutdown()

    # ── Resizing ────────────────────────────────────────────
    def _height_limits(self, canvas):
        canvas_height = max(1, _int(canvas, 'height') - self._navigator_reserve(canvas))
        canvas_height = max(1, canvas_height - pp_ruler_insets(canvas)[1])
        maximum = max(1, canvas_height - PP_CANVAS_MIN_VISIBLE)
        minimum = min(PP_H_MIN_HEIGHT, maximum)
        return minimum, maximum

    def _width_limits(self, available_width):
        maximum = max(1, available_width - PP_CANVAS_MIN_VISIBLE)
        minimum = min(PP_V_MIN_WIDTH, maximum)
        return minimum, maximum

    def resize_panel(self, requested):
        canvas = self._canvas_widget
        if canvas is None or self._collapsed or self._host is not None:
            return
        try:
            if self.st['mode'] == 'h':
                minimum, maximum = self._height_limits(canvas)
                self.st['h_panel_height'] = int(max(minimum, min(maximum, int(requested))))
            else:
                ruler_left = pp_ruler_insets(canvas)[0]
                right = max(ruler_left + 1, min(_int(canvas, 'width'), pp_launcher_right_edge(canvas)))
                minimum, maximum = self._width_limits(right - ruler_left)
                self.st['v_panel_width'] = int(max(minimum, min(maximum, int(requested))))
            self.schedule_save()
            self._sync_geometry()
        except Exception as error:
            if self._destroyed_widget_error(error):
                self._recover_destroyed_widgets()
                return
            raise

    # ── Canvas discovery and layout (ERR&S v3.32 approach) ─────────────────
    @staticmethod
    def _destroyed_widget_error(error):
        return isinstance(error, ValueError) and 'destroyed QWidget object' in str(error)

    def _drop_overlay_reference(self):
        old = self.overlay
        self.overlay = None
        pp_zoom_avoid(old, None)
        pp_retire(old)

    def _ensure_overlay(self):
        if self._overlay_usable():
            return self.overlay
        self._drop_overlay_reference()
        if self._shutdown_done:
            return None
        overlay = PPPanel(self)
        overlay.hide()
        overlay.set_collapsed(self._collapsed)
        self.overlay = overlay
        overlay.canvas.rebuild()
        return overlay

    def _detach_overlay(self):
        if not self._overlay_usable():
            self._drop_overlay_reference()
            return
        if self._host is not None:
            return
        try:
            self.overlay.canvas.end_edit()
        except Exception:
            pass
        try:
            self.overlay.hide()
            self.overlay.setParent(self)
        except Exception as error:
            if self._destroyed_widget_error(error):
                self._drop_overlay_reference()
            else:
                raise

    def _recover_destroyed_widgets(self):
        canvas = self._canvas_widget
        self._canvas_widget = None
        if canvas is not None:
            try:
                canvas.removeEventFilter(self)
            except Exception:
                pass
        try:
            self._detach_overlay()
        except Exception:
            self._drop_overlay_reference()

    def _walk(self, root, max_depth=32):
        result = []
        stack = [(root, 0)]
        seen = set()
        while stack:
            widget, depth = stack.pop()
            if widget is None or depth > max_depth:
                continue
            marker = id(widget)
            if marker in seen:
                continue
            seen.add(marker)
            result.append(widget)
            for child in list(_v(widget, 'children') or []):
                stack.append((child, depth + 1))
        return result

    def _glyph_window_ancestor(self, widget):
        current = widget
        for _ in range(40):
            if current is None:
                return None
            if _object_name(current) == 'GlyphWindow':
                return current
            current = _v(current, 'parentWidget', None)
        return None

    def _canvas_from_window(self, glyph_window):
        candidates = []
        for widget in self._walk(glyph_window):
            if widget is self.overlay or _object_name(widget) != 'widget':
                continue
            try:
                width = _int(widget, 'width')
                height = _int(widget, 'height')
                if _v(widget, 'isVisible') and width >= 200 and height >= 200:
                    candidates.append((width * height, widget))
            except Exception:
                continue
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _find_canvas_widget(self):
        app = QtGui.QApplication.instance()
        if app is None:
            return None
        focus = _v(app, 'focusWidget', None)
        glyph_window = self._glyph_window_ancestor(focus)
        if glyph_window is not None:
            canvas = self._canvas_from_window(glyph_window)
            if canvas is not None:
                return canvas
        current = self._canvas_widget
        if current is not None and _widget_alive(current):
            try:
                if _v(current, 'isVisible') and self._glyph_window_ancestor(current) is not None:
                    return current
            except Exception:
                pass
        try:
            widgets = list(_v(app, 'allWidgets') or [])
        except Exception:
            widgets = []
        candidates = []
        for widget in widgets:
            if _object_name(widget) != 'GlyphWindow':
                continue
            if not _v(widget, 'isVisible', False):
                continue
            canvas = self._canvas_from_window(widget)
            if canvas is not None:
                candidates.append((_int(canvas, 'width') * _int(canvas, 'height'), canvas))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _set_canvas_widget(self, canvas):
        previous = self._canvas_widget
        try:
            self._set_canvas_widget_core(canvas)
        finally:
            if previous is not None and previous is not self._canvas_widget:
                pp_zoom_sync(previous)

    def _set_canvas_widget_core(self, canvas):
        if canvas is self._canvas_widget and (canvas is None or self._overlay_usable()):
            return
        if self._changing_canvas:
            return
        self._changing_canvas = True
        try:
            previous = self._canvas_widget
            self._canvas_widget = None
            if previous is not None:
                try:
                    previous.removeEventFilter(self)
                except Exception:
                    pass
            if canvas is None:
                self._detach_overlay()
                return
            overlay = self._ensure_overlay()
            if overlay is None:
                return
            canvas.installEventFilter(self)
            self._canvas_widget = canvas
            pp_set_viewport(canvas)     
            self._schedule_activate_canvas(canvas)
            overlay.hide()
            overlay.setParent(canvas)
            self._sync_geometry()
            if self._canvas_widget is not canvas or not self._overlay_usable():
                return
            if self._sam_preview_visible(canvas):
                return
            overlay.show()
            overlay.raise_()
            pp_raise_script_launcher(canvas)
            # A newly opened Glyph Window may create new tool buttons, so they are connected once more.
            QtCore.QTimer.singleShot(0, self._rescan_tools)
        except Exception as error:
            try:
                canvas.removeEventFilter(self)
            except Exception:
                pass
            self._canvas_widget = None
            try:
                self._detach_overlay()
            except Exception:
                self._drop_overlay_reference()
            if not self._destroyed_widget_error(error):
                print('%s Canvas connection error: %s' % (PP_LOG, error))
        finally:
            self._changing_canvas = False

    # ── Immediate response to font switching ─────────────────────────────
    def _schedule_activate_canvas(self, canvas):
        """Makes the new canvas the active canvas in the next event loop (same state as clicking it)."""
        def _run():
            if self._shutdown_done or not _widget_alive(canvas):
                return
            if canvas is not self._canvas_widget and canvas is not self._docked_viewport_widget:
                return
            if pp_activate_viewport_canvas(canvas):
                self._last_sig = None
                if self._overlay_usable():
                    self._refresh_tick()
        try:
            QtCore.QTimer.singleShot(0, _run)
        except Exception:
            pass

    def _docked_viewport(self):
        """Glyph Window canvas to follow in the Dock state: canvas with focus → previous canvas → visible canvas."""
        current = self._docked_viewport_widget
        app = QtGui.QApplication.instance()
        focus = _v(app, 'focusWidget', None) if app is not None else None
        glyph_window = self._glyph_window_ancestor(focus) if focus is not None else None
        canvas = self._canvas_from_window(glyph_window) if glyph_window is not None else None
        if canvas is None and current is not None and _widget_alive(current):
            try:
                if _v(current, 'isVisible', False):
                    canvas = current
            except Exception:
                canvas = None
        if canvas is None and self._tick % 5 == 0:
            try:
                canvas = self._find_canvas_widget()
            except Exception:
                canvas = None
        if canvas is not None and canvas is not current:
            self._docked_viewport_widget = canvas
            self._schedule_activate_canvas(canvas)
        return canvas if canvas is not None else current

    def _update_viewport(self):
        if self._host is not None:
            viewport = self._docked_viewport()
        else:
            viewport = self._canvas_widget
        pp_set_viewport(viewport)

    def _rescan_tools(self):
        if self._shutdown_done:
            return
        try:
            self.tracker.rescan()
        except Exception:
            pass

    def _watch(self, widget):
        for watched in self._watched:
            if watched is widget:
                return
        try:
            widget.installEventFilter(self)
            self._watched.append(widget)
        except Exception:
            pass

    def _unwatch_all(self):
        for widget in self._watched:
            try:
                widget.removeEventFilter(self)
            except Exception:
                pass
        self._watched = []

    def _errsp_panel(self, canvas):
        """Visible Replacer/Separator panel on the same canvas (None if none)."""
        if canvas is None:
            return None
        for child in list(_v(canvas, 'children') or []):
            if _object_name(child) != PP_ERRSP_PANEL_NAME:
                continue
            self._watch(child)
            if _v(child, 'isVisible', False):
                return child
        return None

    @staticmethod
    def _x_in_canvas(widget, canvas):
        """Canvas x coordinate of widget's left border (None on failure)."""
        try:
            origin = QtCore.QPoint(0, 0)
            return int(widget.mapToGlobal(origin).x()) - int(canvas.mapToGlobal(origin).x())
        except Exception:
            return None

    def _collapsed_x_beside_errsp(self, canvas, x, bar_w, available_right):
        """x of the collapsed bar in Horizontal mode. The middle of the empty space between the three Replacer/Separator icons
        on the right and the Apply button on the left. Returns x as is if there is no Replacer/Separator."""
        panel = self._errsp_panel(canvas)
        if panel is None:
            return x
        try:
            icon_bar = getattr(panel, 'icon_bar', None)
        except Exception:
            icon_bar = None
        icon_left = None
        icon_w = 0
        if icon_bar is not None and _v(icon_bar, 'isVisible', False):
            icon_left = self._x_in_canvas(icon_bar, canvas)
            icon_w = _int(icon_bar, 'width')
        if icon_left is None:
            # If the icon bar cannot be read directly, assumes three icons (26px, 8px gap) at the exact horizontal center of the panel.
            icon_w = 3 * 26 + 2 * 8
            icon_left = _int(panel, 'x') + (_int(panel, 'width') - icon_w) // 2
        icon_right = icon_left + icon_w
        right_bound = available_right
        if not bool(getattr(panel, '_collapsed', False)):
            try:
                tab = panel.tabs.currentWidget()
                button = getattr(tab, 'apply_button', None)
            except Exception:
                button = None
            if button is not None and _v(button, 'isVisible', False):
                apply_left = self._x_in_canvas(button, canvas)
                if apply_left is not None and icon_right < apply_left <= available_right:
                    right_bound = apply_left
        gap = right_bound - icon_right
        if gap >= bar_w + 24:
            return icon_right + (gap - bar_w) // 2
        return min(icon_right + 12, max(0, available_right - bar_w - 8))

    def _watch_collapsed_rivals(self, canvas):
        """Attaches a z-order watch filter to the GUI and Replacer/Separator panels on the same canvas as the collapsed bar."""
        if canvas is None:
            return
        for child in list(_v(canvas, 'children') or []):
            if _object_name(child) in PP_COLLAPSED_RIVAL_NAMES:
                self._watch(child)

    def _keep_collapsed_on_top(self, rival):
        """If a rival panel came up above the collapsed bar, raises the bar above it again (leaves it if already on top)."""
        if (self._raising_collapsed or self._shutdown_done or self._changing_canvas
                or self._host is not None or not self._collapsed or not self._overlay_usable()):
            return
        overlay = self.overlay
        canvas = self._canvas_widget
        if canvas is None or not _v(overlay, 'isVisible', False):
            return
        if not _same_widget(_v(overlay, 'parentWidget', None), canvas):
            return
        if not _same_widget(_v(rival, 'parentWidget', None), canvas):
            return
        overlay_index = None
        rival_index = None
        for index, child in enumerate(list(_v(canvas, 'children') or [])):
            if overlay_index is None and _same_widget(child, overlay):
                overlay_index = index
            elif rival_index is None and _same_widget(child, rival):
                rival_index = index
        if overlay_index is None or rival_index is None or overlay_index > rival_index:
            return
        self._raising_collapsed = True
        try:
            overlay.raise_()
            pp_raise_script_launcher(canvas)
        finally:
            self._raising_collapsed = False

    def _navigator_reserve(self, canvas, include_errsp=False):
        """If the View Glyph Navigator is shown as an Overlay at the bottom of the canvas, leaves space for its height.
        With include_errsp, the Replacer/Separator panel (avoided in Vertical mode) is also left free the same way."""
        if canvas is None:
            return 0
        canvas_height = _int(canvas, 'height')
        bands = []
        names = (PP_NAVIGATOR_OVERLAY_NAME, PP_ERRSP_PANEL_NAME) if include_errsp else (
            PP_NAVIGATOR_OVERLAY_NAME,)
        for child in list(_v(canvas, 'children') or []):
            name = _object_name(child)
            if name == PP_ERRSP_PANEL_NAME and not include_errsp:
                self._watch(child)
            if name not in names:
                continue
            self._watch(child)
            try:
                if not _v(child, 'isVisible'):
                    continue
                top = _int(child, 'y')
                bottom = top + _int(child, 'height')
            except Exception:
                continue
            if top <= 0:
                continue
            bands.append((top, bottom))
        # treats the panel attached to the canvas bottom and the panels stacked directly on top of it, in order, as the bottom
        # (e.g. the Replacer/Separator panel above the Navigator).
        floor = canvas_height
        changed = True
        while changed:
            changed = False
            for top, bottom in bands:
                if top < floor and bottom >= floor - 2:
                    floor = top
                    changed = True
        return max(0, canvas_height - floor)

    def _zoom_lense_span(self, canvas, band_top, band_bottom, left, right):
        """(left, right) excluding the width of the Zoom Lense overlapping the Horizontal mode band (band_top~band_bottom)."""
        if canvas is None:
            return left, right
        canvas_width = _int(canvas, 'width')
        for child in list(_v(canvas, 'children') or []):
            if _object_name(child) != PP_ZOOM_LENSE_NAME:
                continue
            self._watch(child)
            try:
                if not _v(child, 'isVisible'):
                    continue
                x = _int(child, 'x')
                y = _int(child, 'y')
                w = _int(child, 'width')
                h = _int(child, 'height')
            except Exception:
                continue
            if w <= 0 or h <= 0 or y >= band_bottom or y + h <= band_top:
                continue  # does not overlap the Horizontal mode band vertically (collapsed Zoom Lense icon etc.).
            if x + w / 2.0 < canvas_width / 2.0:
                left = max(left, x + w)
            else:
                right = min(right, x)
        if right - left < 40:
            return left, max(left + 40, right)
        return left, right

    def _set_mode_property(self, overlay, mode):
        """Horizontal/Vertical mode marker read by other scripts. Written only when it changes."""
        try:
            current = str(overlay.property(PP_MODE_PROPERTY) or '')
            if current != mode:
                overlay.setProperty(PP_MODE_PROPERTY, mode)
        except Exception:
            pass

    def _sam_preview_visible(self, canvas):
        """True if the Show All Masters Quick Preview screen is visible on the same canvas."""
        if canvas is None:
            return False
        visible = False
        for child in list(_v(canvas, 'children') or []):
            if _object_name(child) != PP_SAM_QUICK_PREVIEW_NAME:
                continue
            self._watch(child)
            if _v(child, 'isVisible', False):
                visible = True
        return visible

    def _sync_later(self):
        if self._sync_pending:
            return
        self._sync_pending = True

        def _run():
            self._sync_pending = False
            if self._shutdown_done or self._changing_canvas or self._canvas_widget is None:
                return
            try:
                self._sync_geometry()
            except Exception as error:
                if self._destroyed_widget_error(error):
                    self._recover_destroyed_widgets()

        try:
            QtCore.QTimer.singleShot(0, _run)
        except Exception:
            self._sync_pending = False

    def _sync_geometry(self):
        self._sync_geometry_core()
        canvas = self._canvas_widget
        if canvas is not None and self._overlay_usable() and self._host is None:
            direction = 'bottom' if (self.st['mode'] == 'h' or self._collapsed) else 'right'
            pp_zoom_avoid(self.overlay, direction)
            pp_zoom_sync(canvas)

    def _sync_geometry_core(self):
        if self._host is not None:
            return
        canvas = self._canvas_widget
        if canvas is None:
            try:
                self._detach_overlay()
            except Exception:
                self._drop_overlay_reference()
            return
        overlay = self.overlay if self._overlay_usable() else None
        if overlay is None:
            self._recover_destroyed_widgets()
            return
        try:
            if self._sam_preview_visible(canvas):
                if _v(overlay, 'isVisible'):
                    overlay.hide()
                return
        except Exception as error:
            if self._destroyed_widget_error(error):
                self._recover_destroyed_widgets()
                return
        try:
            parent = _v(overlay, 'parentWidget', None)
            if not _same_widget(parent, canvas):
                overlay.hide()
                overlay.setParent(canvas)
            width = max(1, _int(canvas, 'width'))
            height = max(1, _int(canvas, 'height') - self._navigator_reserve(canvas))
            ruler_left, ruler_top = pp_ruler_insets(canvas)
            ruler_left = min(ruler_left, width - 1)
            available_right = max(ruler_left + 1, min(width, pp_launcher_right_edge(canvas)))
            available_width = max(1, available_right - ruler_left)
            self._set_mode_property(overlay, '' if self._collapsed else self.st['mode'])
            if self._collapsed:
                self._watch_collapsed_rivals(canvas)   
                bar_w, bar_h = overlay.collapsed_size()
                bar_w = min(bar_w, available_width)
                if self.st['mode'] == 'h':
                    x = ruler_left + (available_width - bar_w) // 2
                    # placed in the middle of the empty space between the Apply buttons, avoiding the three Replacer/Separator icons.
                    x = self._collapsed_x_beside_errsp(canvas, x, bar_w, available_right)
                else:
                    x = available_right - bar_w - 8
                    # Vertical mode is placed in the remaining area excluding the Replacer/Separator panel area.
                    height = max(1, _int(canvas, 'height')
                                 - self._navigator_reserve(canvas, include_errsp=True))
                overlay.setGeometry(max(ruler_left, x), max(0, height - bar_h - 8), bar_w, bar_h)
            elif self.st['mode'] == 'h':
                minimum, maximum = self._height_limits(canvas)
                panel_h = int(max(minimum, min(maximum, int(self.st['h_panel_height']))))
                # uses the full horizontal width without avoiding the Zoom Lense (the Zoom Lense uses only the area above this panel).
                overlay.setGeometry(ruler_left, height - panel_h, available_width, panel_h)
            else:
                # Vertical mode uses the area only down to the top of the Replacer/Separator panel.
                height = max(1, _int(canvas, 'height')
                             - self._navigator_reserve(canvas, include_errsp=True))
                minimum, maximum = self._width_limits(available_width)
                panel_w = int(max(minimum, min(maximum, int(self.st['v_panel_width']))))
                top = min(ruler_top, max(0, height - 1))
                overlay.setGeometry(available_right - panel_w, top, panel_w, max(1, height - top))
            if _v(canvas, 'isVisible'):
                if not _v(overlay, 'isVisible'):
                    overlay.show()
                overlay.raise_()
                pp_raise_script_launcher(canvas)
            else:
                self._set_canvas_widget(None)
        except Exception as error:
            if self._destroyed_widget_error(error):
                self._recover_destroyed_widgets()
                return
            raise

    def _sync_target(self):
        if self._shutdown_done or self._changing_canvas:
            return
        self._sync_ruler_watcher()      
        if self._host is not None:
            self._sync_docked()
            return
        try:
            canvas = self._find_canvas_widget()
            if canvas is not self._canvas_widget or (canvas is not None and not self._overlay_usable()):
                self._set_canvas_widget(canvas)
            elif canvas is not None:
                self._sync_geometry()
            elif self._canvas_widget is not None:
                self._set_canvas_widget(None)
        except Exception as error:
            if self._destroyed_widget_error(error):
                self._recover_destroyed_widgets()
                return
            traceback.print_exc()

    def _sync_ruler_watcher(self):
        """Fits the detection filter to the Ruler widgets of the Glyph Window canvas currently followed."""
        watcher = getattr(self, 'ruler_watcher', None)
        if watcher is None:
            return
        canvas = self._canvas_widget
        if self._host is not None:
            canvas = self._docked_viewport_widget
        if canvas is not None and not _widget_alive(canvas):
            canvas = None
        try:
            watcher.sync(canvas)
        except Exception as error:
            if self._destroyed_widget_error(error):
                try:
                    watcher.sync(None)
                except Exception:
                    pass
            else:
                print('%s Ruler connection error: %s' % (PP_LOG, error))

    def eventFilter(self, watched, event):
        # in the collapsed state, if the GUI or Replacer/Separator panel comes to the front, raises the bar again before drawing.
        try:
            if (self._collapsed and _v(event, 'type') == PP_ZORDER_CHANGE_EVENT
                    and _object_name(watched) in PP_COLLAPSED_RIVAL_NAMES):
                self._keep_collapsed_on_top(watched)
                return False
        except Exception:
            pass
        try:
            if (_object_name(watched) in (PP_NAVIGATOR_OVERLAY_NAME, PP_SAM_QUICK_PREVIEW_NAME,
                                          PP_ERRSP_PANEL_NAME, PP_ZOOM_LENSE_NAME)  
                    and _v(event, 'type') in (QtCore.QEvent.Resize, QtCore.QEvent.Move,
                                              QtCore.QEvent.Show, QtCore.QEvent.Hide,
                                              QtCore.QEvent.ParentChange)):
                self._sync_later()
                return False
        except Exception:
            pass
        if watched is self._canvas_widget:
            try:
                event_type = _v(event, 'type')
                if event_type in (QtCore.QEvent.Resize, QtCore.QEvent.Show,
                                  QtCore.QEvent.WindowActivate,
                                  QtCore.QEvent.DynamicPropertyChange):
                    self._sync_geometry()
                    if event_type == QtCore.QEvent.Resize:
                        pp_zoom_sync_later(self._canvas_widget)
                elif event_type in (QtCore.QEvent.ChildAdded, QtCore.QEvent.ChildRemoved):
                    self._sync_later()
                elif event_type in (QtCore.QEvent.Hide, QtCore.QEvent.Close):
                    # If left as a child of the canvas, it is destroyed together when the file is closed.
                    self._set_canvas_widget(None)
            except Exception as error:
                if self._destroyed_widget_error(error):
                    self._recover_destroyed_widgets()
                else:
                    traceback.print_exc()
        return False

    # ── Glyph change detection ────────────────────────────────────────
    def _refresh_tick(self):
        if self._shutdown_done or not self._overlay_usable() or self._collapsed:
            return
        overlay = self.overlay
        if not _v(overlay, 'isVisible', False):
            return
        try:
            if QtGui.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
                return
        except Exception:
            pass
        # FontLab objects are not accessed during the transition of loading or closing a font.
        if pp_fonts_settling():
            self._last_sig = None
            return
        try:
            self._update_viewport()     
        except Exception:
            pass
        try:
            font, glyph_name, fl_glyph, master = pp_active_glyph_info(self.font_cache)
        except Exception:
            return
        geometry = None
        if fl_glyph is not None:
            geometry = pp_glyph_geometry_signature(fl_glyph, self.font_cache.masters)
        view = self.st['h_view'] if self.st['mode'] == 'h' else self.v_view
        self._tick += 1
        if view == 'interp' and font is not None and (self._last_inst is None or self._tick % 3 == 0):
            try:
                instances = tuple((spec['label'], spec['weight'], spec['location_repr'])
                                  for spec in pp_instance_raw_specs(font))   # all, before removing duplicates
            except Exception:
                instances = None
            if instances != self._last_inst:
                if self._last_inst is not None:
                    for key in list(self.font_cache.items.keys()):
                        if key[0] in ('i', 'v', 'a'):   # also discards panel location interpolation results ('v').
                            # also discards All Instances interpolation results ('a').
                            del self.font_cache.items[key]
                self._last_inst = instances
        # redraws when the other axis values of the VARIATIONS panel (excluding Weight) change.
        var_sig = None
        if view == 'interp' and font is not None:
            try:
                place = self.font_cache.variation_place(font)
            except Exception:
                place = None
            var_sig = place[1] if place is not None else None
            if var_sig != self._last_var:
                self.font_cache.forget_variation_items()
                self._last_var = var_sig
        last_name, last_geometry = self._last_geom
        if glyph_name and last_name == glyph_name and last_geometry != geometry:
            self.font_cache.forget_glyph(glyph_name)
        self._last_geom = (glyph_name, geometry)
        sig = (self.font_cache.font_id, glyph_name, master, tuple(self.font_cache.masters),
               geometry, self._last_inst if view == 'interp' else None, var_sig,
               self.st['mode'], self.st['h_view'], self.v_view, self.h_text_on,   # h_text_on
               tuple(sorted(self.interp_all.items())))   # All Instances preview state
        if sig != self._last_sig:
            self._last_sig = sig
            overlay.canvas.rebuild()

    # ── Selections panel Dock ─────────────────────────────────
    def toggle_dock(self):
        if self._shutdown_done:
            return
        if self._host is not None:
            self.undock()
        else:
            self.dock()

    def dock(self):
        if self._host is not None:
            return
        if self._collapsed:
            # When docking in the collapsed state, shows the script screen again first.
            self._collapsed = False
            if self._overlay_usable():
                self.overlay.set_collapsed(False)
        was_open = pp_find_panel_page(PP_SELECTIONS_PANEL_OBJECT_NAME, visible_only=True) is not None
        panel = pp_open_and_find_selections_panel()
        if panel is None:
            print('%s Error: could not find a visible SelectionsPanel, so Dock was not possible.' % PP_LOG)
            return
        claimed, owner = pp_claim_selections_panel(panel)
        if not claimed:
            owner_label = 'Large Size' if owner == 'DalgasViewGlyphLargeSize' else owner
            message = ('The Selections panel is in use by another host, so Dock was cancelled.\n\n'
                       'Current owner: %s' % (owner_label or 'unknown'))
            try:
                QtGui.QMessageBox.warning(self.overlay, 'Selections panel in use', message)
            except Exception:
                print('%s %s' % (PP_LOG, message.replace('\n', ' ')))
            return
        host = None
        try:
            overlay = self._ensure_overlay()
            overlay.canvas.end_edit()
            overlay.hide()
            canvas = self._canvas_widget
            if canvas is not None:
                try:
                    canvas.removeEventFilter(self)
                except Exception:
                    pass
            self._canvas_widget = None
            pp_zoom_avoid(overlay, None)
            pp_zoom_restore_if_running(canvas)
            host = PPSelectionsHost(panel, overlay)
            self._host = host
            self._host_miss = 0
            self._selections_opened_by_us = not was_open
            overlay.set_docked(True)
            host.sync_geometry()
            host.show()
            host.raise_()
            overlay.show()
            overlay.relayout()
            overlay.canvas.rebuild()
        except Exception as error:
            print('%s Selections host creation error: %s' % (PP_LOG, error))
            try:
                if host is not None:
                    host.dispose()
                else:
                    pp_release_selections_panel(panel)
            except Exception:
                pass
            self._host = None
            if self._overlay_usable():
                self.overlay.set_docked(False)
                self.overlay.setParent(self)
            self._sync_target()

    def _remove_host(self):
        host = self._host
        if host is None:
            return None
        panel = getattr(host, '_panel', None)
        try:
            content = host.release_content()
        except Exception:
            content = self.overlay
        try:
            host.dispose()
        except Exception:
            pp_release_selections_panel(panel)
        self._host = None
        self._host_miss = 0
        if content is not None and _widget_alive(content):
            self.overlay = content
        if self._overlay_usable():
            self.overlay.canvas.end_edit()
            self.overlay.set_docked(False)
            self.overlay.hide()
            self.overlay.setParent(self)
        return panel

    def undock(self):
        """Leaves the Selections panel and returns to the Glyph Window overlay."""
        if self._host is None:
            return
        opened_by_us = self._selections_opened_by_us
        panel = self._remove_host()
        self._selections_opened_by_us = False
        if opened_by_us and panel is not None and not pp_close_native_panel(panel):
            print('%s Error: could not close the Selections panel after detaching.' % PP_LOG)
        self._sync_target()
        if self._overlay_usable():
            self.overlay.relayout()
            self.overlay.canvas.rebuild()

    def _sync_docked(self):
        host = self._host
        panel = getattr(host, '_panel', None)
        try:
            panel_visible = bool(_v(panel, 'isVisible', False))
            panel_attached = panel is not None and panel.parent() is not None
        except Exception:
            panel_visible = False
            panel_attached = False
        if panel_visible and panel_attached:
            self._host_miss = 0
            try:
                if host.content() is None and self._overlay_usable():
                    host.attach_content(self.overlay)
                host.sync_geometry()
                host.show()
                host.raise_()
                if self._overlay_usable() and not _v(self.overlay, 'isVisible', False):
                    self.overlay.show()
            except Exception:
                pass
            return
        try:
            if QtGui.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
                self._host_miss = 0
                return  # a temporary hide during a Dock move drag is not treated as closing.
        except Exception:
            pass
        replacement = pp_find_panel_page(PP_SELECTIONS_PANEL_OBJECT_NAME, visible_only=True)
        if replacement is not None and not _same_widget(replacement, panel):
            if self._migrate_host(replacement):
                return
        self._host_miss += 1
        if self._host_miss < PP_DOCK_TRANSITION_GRACE_TICKS:
            return
        # If the user closed the Selections panel, the script ends (same as the SSO v5.39 Gallery rule).
        self._remove_host()
        self._selections_opened_by_us = False
        self.shutdown()

    def _migrate_host(self, new_panel):
        """Reattaches the body to the SelectionsPanel replaced by a font switch."""
        claimed, _owner = pp_claim_selections_panel(new_panel)
        if not claimed:
            return False
        old_host = self._host
        try:
            content = old_host.release_content()
        except Exception:
            content = self.overlay
        try:
            old_host.dispose()
        except Exception:
            pass
        try:
            if content is not None and _widget_alive(content):
                self.overlay = content
            overlay = self._ensure_overlay()
            overlay.hide()
            self._host = PPSelectionsHost(new_panel, overlay)
            self._host_miss = 0
            overlay.set_docked(True)
            self._host.sync_geometry()
            overlay.show()
            overlay.canvas.rebuild()
            return True
        except Exception as error:
            print('%s Selections host migration error: %s' % (PP_LOG, error))
            pp_release_selections_panel(new_panel)
            self._host = None
            if self._overlay_usable():
                self.overlay.set_docked(False)
                self.overlay.setParent(self)
            return False

    # ── Shutdown ────────────────────────────────────────────────
    def shutdown(self):
        if self._shutdown_done:
            return
        self._shutdown_done = True
        for timer in (self._target_timer, self._refresh_timer, self._save_timer):
            try:
                timer.stop()
            except Exception:
                pass
        try:
            self.ruler_watcher.shutdown()     
        except Exception:
            pass
        try:
            QtGui.QApplication.instance().aboutToQuit.disconnect(self.shutdown)
        except Exception:
            pass
        if self._overlay_usable():
            try:
                self.overlay.canvas.end_edit()
            except Exception:
                pass
        self._save_now()
        try:
            self.tracker.shutdown()
        except Exception:
            pass
        selections_panel = None
        if self._host is not None:
            opened_by_us = self._selections_opened_by_us
            try:
                panel = self._remove_host()
                if opened_by_us:
                    selections_panel = panel
            except Exception as error:
                print('%s Selections host cleanup error: %s' % (PP_LOG, error))
                self._host = None
        if selections_panel is not None:
            pp_close_native_panel(selections_panel)
        zoom_canvas = self._canvas_widget
        self._unwatch_all()
        if self._canvas_widget is not None:
            try:
                self._canvas_widget.removeEventFilter(self)
            except Exception:
                pass
        self._canvas_widget = None
        self._docked_viewport_widget = None
        pp_set_viewport(None)       
        old_overlay = self.overlay
        if self._overlay_usable():
            try:
                old_overlay.hide()
                old_overlay.setParent(self)
                old_overlay.release_resources()
            except Exception:
                pass
        self.overlay = None
        pp_zoom_avoid(old_overlay, None)
        pp_zoom_restore_if_running(zoom_canvas)
        try:
            if getattr(sys, PP_CONTROLLER_ANCHOR, None) is self:
                setattr(sys, PP_CONTROLLER_ANCHOR, None)
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass
        pp_retire(self, old_overlay, self.tracker, getattr(self, 'ruler_watcher', None))


def run():
    previous = getattr(sys, PP_CONTROLLER_ANCHOR, None)
    if previous is not None:
        try:
            previous.shutdown()
        except Exception as error:
            if not (isinstance(error, ValueError) and 'destroyed QWidget object' in str(error)):
                traceback.print_exc()
    try:
        controller = PPController()
        setattr(sys, PP_CONTROLLER_ANCHOR, controller)
        return controller
    except Exception as error:
        traceback.print_exc()
        print('%s Start error: %s' % (PP_LOG, error))
        return None


run()
