#FLM: Cluade: 95_C_Change Linked Element Color
"""
version_1.22
FontLab 8: Changes the Fill Color of the selected shape and of every shape linked to it by Element Reference.
Created as a standalone window with parent=None (FontLab exit detection is handled in closeEvent)

How it works:
1. Select a shape in the current glyph
2. Pick a color in the script window and click the Apply button
3. The script finds the shapeData ID of the selected shape
4. Every shape in the font with the same shapeData ID gets the new color
"""

import fontlab as fl6
import FL as legacy
import sys
from typerig.proxy.fl.objects.glyph import pGlyph
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui import QtGui
from PythonQt import QtCore, QtGui as _C15_THEME_QT_GUI


# ── Widget liveness helper for script stability (_is_alive) ──────────
try:
    import sip as _sip
    def _is_alive(widget):
        try:
            return not _sip.isdeleted(widget)
        except Exception:
            return True
except ImportError:
    def _is_alive(widget):
        return True


# ── WebBrowser BG Bypass Guard ──────────
# Intercepts webbrowser.open() calls made when opening external links (e.g. help/forum
# links in a right-click menu) and hands the actual open to a daemon thread. Because the
# nested ShellExecuteW pump no longer runs the main GUI thread's message queue, Qt/PythonQt
# reentrancy crashes are avoided while the browser still opens normally. This is an
# idempotent, process-wide patch; closing this one file does not revert it (it resets
# when FontLab restarts). 
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


# ── C15-specific app name and version
_C15_APP_NAME = 'Change El Color'
_C15_APP_VERSION = 'v1.22'

_C15_THEME_LIGHT = 'light'
_C15_THEME_DARK = 'dark'
_C15_THEME_API_VERSION = 1


def _c15_theme_qt_value(obj, name, default=None):
    """Safely reads a value that PythonQt exposes either as a method or as a property."""
    if obj is None:
        return default
    try:
        value = getattr(obj, name)
        return value() if callable(value) else value
    except Exception:
        return default


def _c15_theme_detect_fontlab_mode():
    """Detects the UI mode from the global QApplication palette, not from the glyph canvas."""
    try:
        app = _C15_THEME_QT_GUI.QApplication.instance()
        palette = _c15_theme_qt_value(app, 'palette')
        if palette is None:
            return _C15_THEME_LIGHT
        window_color = palette.color(_C15_THEME_QT_GUI.QPalette.Window)
        lightness = _c15_theme_qt_value(window_color, 'lightness')
        if lightness is not None and int(lightness) < 128:
            return _C15_THEME_DARK
    except Exception:
        pass
    return _C15_THEME_LIGHT


def _c15_theme_checkbox_qss(theme_mode):
    """Returns the per-mode text color for the Delta Filter option."""
    if theme_mode == _C15_THEME_DARK:
        return "font-size: 11px; padding-left: 10px; color: #E6EDF3;"
    return "font-size: 11px; padding-left: 10px;"


def _c15_theme_apply_button_qss(theme_mode):
    """Returns the per-mode style of the Apply button."""
    if theme_mode == _C15_THEME_DARK:
        return """
            QPushButton {
                font-size: 14px;
                padding: 5px;
                font-weight: bold;
                background-color: #353A40;
                color: #F2F4F6;
                border: 1px solid #69727D;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #454C54;
                border: 1px solid #87919C;
            }
            QPushButton:pressed {
                background-color: #22272D;
                border: 1px solid #9AA5B1;
            }
        """
    return """
            QPushButton {
                font-size: 14px;
                padding: 5px;
                font-weight: bold;
            }
        """


def _c15_theme_swatch_border(theme_mode):
    """Keeps the swatch RGB and returns only a border color suited to the mode."""
    if theme_mode == _C15_THEME_DARK:
        return '#B8C2CC'
    return '#AAA'

# Intentional shared flag that stops the three color scripts from re-entering a
# color-apply function on the same UI thread. No controller or window object is shared.
_DALGAS_LINKED_COLOR_BUSY_ATTR = '_dalgas_linked_color_operation_busy'


# Color palette definition
_C15_COLORS = {
    'Black': QtGui.QColor(0, 0, 0, 255),
    'Red': QtGui.QColor(255, 0, 0, 255),
    'Blue': QtGui.QColor(0, 0, 255, 255),
    'Pink': QtGui.QColor(255, 0, 255, 255),  # Magenta
    'Orange': QtGui.QColor(255, 165, 0, 255),
    'Green': QtGui.QColor(0, 94, 32, 255),
    'Dark Green': QtGui.QColor(0, 49, 42, 255),
    'Brown': QtGui.QColor(125, 73, 0, 255),
    'Dark Brown': QtGui.QColor(121, 0, 0, 255),
    'Violet': QtGui.QColor(146, 39, 143, 255),
    'Dark Violet': QtGui.QColor(75, 0, 73, 255),
    'Hanul': QtGui.QColor(0, 175, 233, 255),
    'Dark Hanul': QtGui.QColor(0, 118, 163, 255),
    'Blue2': QtGui.QColor(55, 55, 170, 255),
    'Dark Blue': QtGui.QColor(27, 20, 100, 255)
}


def _color15_has_delta_filter(shape):
    """Checks whether a Delta Filter is applied to the shape.

    Determined by shape.shapeBuilder.title == 'Delta'.
    """
    try:
        if not hasattr(shape, 'shapeBuilder'):
            return False
        builder = shape.shapeBuilder
        if builder is None:
            return False
        if hasattr(builder, 'title'):
            return builder.title == 'Delta'
    except Exception:
        pass
    return False


def _color15_get_shape_data_id(shape):
    """Returns the shapeData ID of a shape.

    When a Delta Filter is applied to a shape, FontLab issues a new shapeData
    dedicated to that shape at the moment the filter is applied. So own.shapeData
    is always a valid value, but it differs from the shared ID of the source Element Reference.
    (Measured: the shapeData.id of a plain Link shape == the
    includesList[0].shapeData.id of a Delta Filter shape; the two belong to the same group)

    Therefore, for a shape with a Delta Filter, own.shapeData is ignored and the
    shapeData ID of the source shape shown in the Element panel (shape.includesList[0])
    is always used, so that it matches the same ID as the other Linked Shapes
    sharing the same Element Reference.
    """
    if _color15_has_delta_filter(shape):
        try:
            if hasattr(shape, 'includesList') and shape.includesList:
                source_shape = shape.includesList[0]
                if hasattr(source_shape, 'shapeData') and source_shape.shapeData:
                    return source_shape.shapeData.id
        except Exception:
            pass
        return None

    try:
        if hasattr(shape, 'shapeData') and shape.shapeData:
            return shape.shapeData.id
    except:
        pass

    return None


def _color15_find_all_linked_shapes(font, shape_data_id, layer_name):
    """
    Finds every shape in the whole font that has the same shapeData ID.
    
    Args:
        font: pFont object
        shape_data_id: shapeData ID to look for
        layer_name: layer name
    
    Returns:
        list of (glyph_name, shape) tuples
    """
    linked_shapes = []
    
    # Iterate over all glyphs
    for glyph in font.pGlyphs():
        try:
            # Get the shapes of this layer
            shapes = glyph.shapes(layer_name)
            
            # Skip if shapes is None (empty glyph or control character)
            if shapes is None:
                continue
            
            for shape in shapes:
                # Compare shapeData IDs
                if _color15_get_shape_data_id(shape) == shape_data_id:
                    linked_shapes.append((glyph.name, shape))
        except:
            continue
    
    return linked_shapes


def _color15_change_linked_shapes_color(color_name, include_delta=False):
    """Prevents nested entry into C15 color application and runs the actual work."""
    if getattr(sys, _DALGAS_LINKED_COLOR_BUSY_ATTR, False):
        print("Another Linked Element Color operation is in progress.")
        return

    setattr(sys, _DALGAS_LINKED_COLOR_BUSY_ATTR, True)
    try:
        return _color15_change_linked_shapes_color_unlocked(
            color_name, include_delta=include_delta
        )
    finally:
        setattr(sys, _DALGAS_LINKED_COLOR_BUSY_ATTR, False)


def _color15_change_linked_shapes_color_unlocked(color_name, include_delta=False):
    """
    Changes the color of the selected shape and of every shape linked to it by Element Reference.

    Args:
        color_name: color name defined in _C15_COLORS
        include_delta: if True, also changes the color of shapes with a Delta Filter applied.
                        (default False: shapes with a Delta Filter are skipped)
    """
    # Current glyph
    glyph = pGlyph()
    # An fgGlyph object returns False in a bool() context even when valid,
    # so always compare with is not None.
    if glyph is None:
        print("ERROR: No glyph active!")
        return
    
    # Current font
    font = pFont()
    if font is None:
        print("ERROR: No font active!")
        return
    
    # Get the color
    color = _C15_COLORS.get(color_name)
    if not color:
        print(f"ERROR: Unknown color: {color_name}")
        return
    
    # Get the layer name first
    layer_name = glyph.layer().name
    
    # Get the selected shapes
    # Method 1: selectedShapes() - when nodes are selected with the Contour Tool
    selected_shapes = glyph.selectedShapes()
    
    # Method 2: check the active/selected attributes - when whole shapes are selected with the Element Tool
    if not selected_shapes:
        all_shapes = glyph.shapes(layer_name)
        selected_shapes = [s for s in all_shapes if (hasattr(s, 'active') and s.active) or (hasattr(s, 'selected') and s.selected)]
    
    if not selected_shapes:
        print("No shapes selected! Please select shapes with Element tool (Q) or Contour tool (V).")
        return
    
    # Process each selected shape
    total_changed = 0
    processed_ids = set()  # Avoid processing the same ID twice
    
    for selected_shape in selected_shapes:
        # Get the shapeData ID
        shape_data_id = _color15_get_shape_data_id(selected_shape)
        
        if shape_data_id is None:
            # Skip a standalone shape with a Delta Filter, depending on the option
            if not include_delta and _color15_has_delta_filter(selected_shape):
                continue
            # For a standalone shape, just change its color
            selected_shape.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
            # Also change the Delta Filter source shape (the source shown in the Element panel)
            if include_delta and _color15_has_delta_filter(selected_shape):
                try:
                    if selected_shape.includesList:
                        selected_shape.includesList[0].brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                except Exception:
                    pass
            total_changed += 1
            continue
        
        # Skip IDs that have already been processed
        if shape_data_id in processed_ids:
            continue
        
        processed_ids.add(shape_data_id)
        
        # Find all shapes with the same shapeData ID
        linked_shapes = _color15_find_all_linked_shapes(font, shape_data_id, layer_name)
        
        # Change the color of all linked shapes
        for glyph_name, shape in linked_shapes:
            # Skip shapes with a Delta Filter, depending on the option
            if not include_delta and _color15_has_delta_filter(shape):
                continue
            try:
                shape.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                # Also change the Delta Filter source shape (the source shown in the Element panel)
                if include_delta and _color15_has_delta_filter(shape):
                    try:
                        if shape.includesList:
                            shape.includesList[0].brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                    except Exception:
                        pass
                total_changed += 1
            except Exception as e:
                print(f"ERROR: Failed to apply color to '{glyph_name}': {e}")
        
        # Update each glyph
        updated_glyphs = set([glyph_name for glyph_name, _ in linked_shapes])
        for glyph_name in updated_glyphs:
            try:
                g = font.glyph(glyph_name)
                if g:
                    g.update()
                    # Force the glyph's changed flag
                    g.setChanged()
            except:
                pass
    
    # Update the current glyph
    glyph.update()
    
    # Force an update with TypeRig's updateObject
    try:
        font.updateObject(glyph.fl, 'Color changed', verbose=False)
    except:
        pass
    
    # Toggle the selection state to force a canvas refresh
    try:
        # Store the currently selected shapes
        temp_selected = []
        for shape in selected_shapes:
            if hasattr(shape, 'selected'):
                temp_selected.append(shape)
                shape.selected = False  # Deselect
        
        # Update the glyph
        glyph.update()
        
        # Reselect
        for shape in temp_selected:
            shape.selected = True
        
        glyph.update()
    except Exception as e:
        print(f"Selection toggle warning: {e}")
    
    # Force a canvas update
    try:
        canvas = fl6.CurrentCanvas()
        if canvas:
            canvas.update()
            canvas.repaint()
    except:
        pass


class C15LinkedColorDialog(QtGui.QDialog):
    """Color selection dialog"""
    
    def __init__(self):
        # parent=None: create as a standalone window.
        # Setting main_win as the parent makes Qt's parent-child ownership conflict
        # with Python's reference, causing a SIGSEGV when FontLab quits.
        # Also, when the local variable dialog in _color15_show_color_menu() is garbage-collected
        # after the function returns, it double-conflicts with Qt parent ownership, so parent must be None.
        super(C15LinkedColorDialog, self).__init__(None)
        self._c15_theme_mode = _c15_theme_detect_fontlab_mode()
        self._c15_theme_api_version = _C15_THEME_API_VERSION
        self.setWindowTitle('%s %s' % (_C15_APP_NAME, _C15_APP_VERSION))
        self.setObjectName('dalgas_c15_linked_color_dialog')
        self.setFixedWidth(260)
        
        # Since parent=None, WindowStaysOnTopHint keeps the window above FontLab.
        # WA_DeleteOnClose=False: prevents Qt from deleting the widget first
        # while a Python global variable still references it.
        self.setWindowFlags(
            (self.windowFlags()
             | QtCore.Qt.WindowStaysOnTopHint
             | QtCore.Qt.CustomizeWindowHint)
            & ~QtCore.Qt.WindowContextHelpButtonHint
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        
        self.selected_color = None  # Currently selected color
        
        # Main layout
        main_layout = QtGui.QVBoxLayout()
        # v1.15: Margins/spacing are set explicitly instead of relying on OS defaults.
        # (The default margins/spacing of macOS QMacStyle differ from Windows QWindowsStyle,
        # which misaligned the three-column color buttons and removed the margin below
        # the Apply button.)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)
        
        # Delta Filter option
        label_layout = QtGui.QHBoxLayout()

        self.chk_include_delta = QtGui.QCheckBox("Include shapes with Delta Filter")
        # Unchecked by default (shapes with a Delta Filter are excluded)
        self.chk_include_delta.setChecked(False)
        self.chk_include_delta.setStyleSheet(
            _c15_theme_checkbox_qss(self._c15_theme_mode)
        )
        label_layout.addWidget(self.chk_include_delta)

        label_layout.addStretch()
        main_layout.addLayout(label_layout)
        
        # All colors (3 per row)
        self.color_buttons = {}

        all_color_names = [
            'Red', 'Pink', 'Orange',
            'Hanul', 'Dark Hanul', 'Black',
            'Blue', 'Blue2', 'Dark Blue',
            'Green', 'Dark Green', 'Violet',
            'Brown', 'Dark Brown', 'Dark Violet'
        ]

        COLORS_PER_ROW = 3
        for i in range(0, len(all_color_names), COLORS_PER_ROW):
            row_layout = QtGui.QHBoxLayout()
            # v1.15: Button spacing is fixed explicitly for each row so it renders the same
            # on macOS and Windows (prevents the jagged "teeth" misalignment of the 3 columns).
            row_layout.setSpacing(6)
            # v1.16: Per the Qt docs, a sub-layout's (row_layout) margins follow the style (QStyle)
            # defaults and may differ by OS. They are fixed to 0 so the rows match the width of the
            # Apply button, which is added directly to main_layout with addWidget.
            row_layout.setContentsMargins(0, 0, 0, 0)
            for color_name in all_color_names[i:i + COLORS_PER_ROW]:
                btn = self.create_color_button(color_name)
                self.color_buttons[color_name] = btn
                # stretch=1: buttons expand evenly in proportion to the window width.
                row_layout.addWidget(btn, 1)
            main_layout.addLayout(row_layout)

        # Apply button (spans the full width; height reduced to about 50% of the original)
        apply_btn = QtGui.QPushButton("Apply")
        apply_btn.setStyleSheet(
            _c15_theme_apply_button_qss(self._c15_theme_mode)
        )
        apply_btn.clicked.connect(self.on_apply)
        main_layout.addWidget(apply_btn)
        
        self.setLayout(main_layout)

        # Fixed window start position (based on a QHD monitor)
        # Aligned to the same x position as the right-hand panel column (View Shape Coordinates, Dalgas Paste, etc.)
        self.move(1972, 571)

        # ── FontLab exit detection: connect the aboutToQuit signal ──────────
        # Fires on Qt's normal shutdown path. It may not fire when FontLab quits with
        # several fonts open, so _exit_timer is used for detection as well.
        self._runtime_active = False

        # Timer dedicated to exit detection (low-frequency 2000 ms to minimize UI load)
        self._exit_timer = QtCore.QTimer(self)
        self._activate_runtime()

    def _activate_runtime(self):
        """Restores the exit-monitoring connections when an existing hidden window is shown again."""
        if self._runtime_active:
            return
        try:
            app = QtGui.QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self.close)
        except Exception:
            pass
        try:
            self._exit_timer.timeout.connect(self._check_fontlab_alive)
        except Exception:
            pass
        self._exit_timer.start(2000)
        self._runtime_active = True

    # - Timer callback dedicated to FontLab exit detection --------------------------------
    def _check_fontlab_alive(self):
        """Timer callback dedicated to FontLab exit detection"""
        # [Safeguard 1] Stop immediately while the window/widget is being destroyed
        if not _is_alive(self):
            try:
                self._exit_timer.stop()
            except Exception:
                pass
            return
        try:
            _font_check = fl6.CurrentFont()
        except Exception:
            _font_check = None
        if _font_check is None:
            try:
                _font_count = legacy.fl.count
            except Exception:
                _font_count = 0
            if _font_count > 0:
                return  # In transition -> wait
            self._exit_timer.stop()
            try:
                p = self.parent()
                if p is not None:
                    p.close()
                else:
                    self.close()
            except Exception:
                pass

    def create_color_button(self, color_name):
        """Create a color button"""
        btn = QtGui.QPushButton("")  # No text label on the button (colors alone identify it)
        btn.setToolTip(color_name)  # Show the color name on mouse hover
        btn.setCheckable(True)  # Make it toggleable
        btn.clicked.connect(lambda checked, name=color_name: self.on_color_selected(name, btn)) # Pass the button object as an argument
        
        # Set the SizePolicy so the button expands horizontally in proportion to the window width
        # (fixed min-width removed and replaced with Expanding -> evenly split to the window width in the 3-column layout)
        btn.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        # v1.15: Pushes the built-in minimum width of the macOS native QPushButton's sizeHint()
        # down to 0 so the Expanding policy splits the row into exact thirds
        # (the cause of uneven button widths and jagged "teeth" between rows
        # that occurred only on macOS).
        btn.setMinimumWidth(0)
        # v1.15: Gives the Fixed policy an actual fixed height so the height is not driven
        # by the OS default sizeHint and renders the same on both OSes.
        btn.setFixedHeight(32)
        
        # Button color preview and base style
        color = _C15_COLORS[color_name]
        text_color = "white" if (color.red() + color.green() + color.blue()) < 384 else "black"
        
        # Store the base style (used when deselected) - thin 1px border, slightly rounded corners (border-radius)
        # Vertical padding reduced from 10px to 6px to bring the height down to about 80% of the original
        base_border_style = (
            'border: 1px solid %s;'
            % _c15_theme_swatch_border(self._c15_theme_mode)
        )
        btn.setProperty('base_border_style', base_border_style)
        btn.setProperty(
            'base_style',
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"color: {text_color}; font-weight: bold; padding: 6px 4px; "
            f"{base_border_style} border-radius: 6px;"
        )
        
        btn.setStyleSheet(btn.property('base_style')) # Initial apply
        
        return btn
    
    def closeEvent(self, event):
        # Disconnect the aboutToQuit signal to prevent duplicate calls.
        try:
            QtGui.QApplication.instance().aboutToQuit.disconnect(self.close)
        except Exception:
            pass
        try:
            self._exit_timer.stop()
            self._exit_timer.timeout.disconnect()
        except Exception:
            pass
        self._runtime_active = False
        event.accept()

    def __del__(self):
        # Guards against Qt destroying the widget directly without calling closeEvent.
        try:
            self._exit_timer.stop()
        except Exception:
            pass

    def close_dialog(self):
        """Close the dialog"""
        self.close()
    
    def on_color_selected(self, color_name, clicked_btn):
        """Called when a color is selected"""
        
        # 1. Reset the borders of all buttons (deselect)
        for name, btn in self.color_buttons.items():
            # Clear the existing check
            btn.setChecked(False)
            
            # Restore the base style (thin border)
            btn.setStyleSheet(btn.property('base_style'))

        # 2. Always set the clicked button to the selected state
        clicked_btn.setChecked(True)
        
        # Add a very thick border (5px) to the base style of the selected button
        base_style = clicked_btn.property('base_style')
        
        # Orange border by default, black border for bright colors
        if color_name in ['Orange', 'Red', 'Pink']:
            border_color = "#000"  # Black
        else:
            border_color = "#FFA500"  # Orange
        
        # Apply a thick border instead of the existing border: 1px solid #AAA;
        base_border_style = clicked_btn.property('base_border_style')
        selected_style = base_style.replace(
            base_border_style,
            f"border: 5px solid {border_color};"
        ).replace("padding: 6px 4px;", "padding: 2px 0px;")
        
        clicked_btn.setStyleSheet(selected_style)
        
        self.selected_color = color_name
    
    def on_apply(self):
        """Called when the Apply button is clicked"""
        if self.selected_color:
            include_delta = self.chk_include_delta.isChecked()
            _color15_change_linked_shapes_color(self.selected_color, include_delta=include_delta)
        else:
            print("Please select a color first!")


_C15_DIALOG_ANCHOR_ATTR = '_dalgas_c15_linked_color_dialog_controller'
_c15_dialog = None

def _color15_show_color_menu():
    """Show the color selection menu"""
    global _c15_dialog
    existing = getattr(sys, _C15_DIALOG_ANCHOR_ATTR, None)
    if existing is None:
        existing = _c15_dialog

    # Windows from before v1.19 have no theme API marker. Even when a new file is run in the
    # same FontLab session, only the old C15 window is closed normally so the old UI is not reused.
    if (existing is not None
            and getattr(existing, '_c15_theme_api_version', None)
            != _C15_THEME_API_VERSION):
        try:
            existing.close()
        except Exception:
            pass
        existing = None
        try:
            setattr(sys, _C15_DIALOG_ANCHOR_ATTR, None)
        except Exception:
            pass

    # Reactivate a live existing instance regardless of whether it is hidden.
    # The replacement pattern of creating a new window right after deleteLater() is not used.
    try:
        if existing is not None and _is_alive(existing):
            existing._activate_runtime()
            existing.show()
            existing.raise_()
            existing.activateWindow()
            _c15_dialog = existing
            setattr(sys, _C15_DIALOG_ANCHOR_ATTR, existing)
            return
    except Exception:
        pass

    _c15_dialog = C15LinkedColorDialog()
    setattr(sys, _C15_DIALOG_ANCHOR_ATTR, _c15_dialog)
    _c15_dialog.show()


# Main execution
if __name__ == '__main__':
    _color15_show_color_menu()
