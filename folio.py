#!/usr/bin/env python3
"""
Folio — a modern PDF editor for Linux.

Open, view, edit text, annotate, sign, merge, split, reorder, rotate,
compress and password-protect PDF documents.

Requires: PySide6, PyMuPDF
"""
import os
import sys
import shutil
import statistics
import subprocess
from contextlib import contextmanager
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

from PySide6.QtCore import (Qt, QSize, QRectF, QPointF, QRect, QTimer, Signal,
                            QObject, QByteArray, QSettings)
from PySide6.QtGui import (QIcon, QPixmap, QImage, QPainter, QColor, QPen,
                           QKeySequence, QPainterPath, QFont, QShortcut,
                           QPalette, QGuiApplication)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QToolButton, QPushButton, QButtonGroup, QScrollArea, QListWidget,
    QListWidgetItem, QAbstractItemView, QStyledItemDelegate, QStyle,
    QFileDialog, QMessageBox, QInputDialog, QDialog, QPlainTextEdit, QSpinBox,
    QLineEdit, QMenu, QStackedWidget, QFrame, QRadioButton, QAbstractButton,
    QColorDialog)

APP = "Folio"
VERSION = "1.0.0"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "folio"
SIG_PATH = CONFIG_DIR / "signature.png"
OPENABLE = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif",
            ".xps", ".epub", ".svg", ".cbz", ".fb2"}
OPEN_FILTER = ("Documents (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif *.xps *.epub *.svg);;"
               "PDF files (*.pdf);;All files (*)")
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)"

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------
THEMES = {
    "dark": dict(bg="#0e1015", surface="#15181f", surface2="#1c2029", hover="#242935",
                 border="#262b36", text="#e8eaf0", muted="#8b92a5", icon="#c4c9d6",
                 accent="#7d8bff", accent_hover="#98a3ff", accent_text="#0e1015",
                 canvas="#0a0c10", scroll="#2c3240", toast="#e8eaf0", toast_text="#0e1015",
                 danger="#ff6b7a"),
    "light": dict(bg="#f4f5f8", surface="#ffffff", surface2="#f1f3f7", hover="#e8ebf2",
                  border="#e2e5ec", text="#171a21", muted="#6b7282", icon="#3d4352",
                  accent="#4f5bd5", accent_hover="#3f4bc2", accent_text="#ffffff",
                  canvas="#e7e9ef", scroll="#cfd3dc", toast="#171a21", toast_text="#ffffff",
                  danger="#d93a4a"),
}

QSS = """
* { font-size: 13px; }
QWidget { color: %(text)s; }
QMainWindow, QDialog, #Home, #Central { background: %(bg)s; }
#TopBar, #OptionsBar, #BottomBar, #Sidebar { background: %(surface)s; }
#TopBar { border-bottom: 1px solid %(border)s; }
#OptionsBar { border-bottom: 1px solid %(border)s; }
#BottomBar { border-top: 1px solid %(border)s; }
#Sidebar { border-right: 1px solid %(border)s; }
#Canvas, QScrollArea#Viewer { background: %(canvas)s; border: none; }
QLabel { background: transparent; }
#Brand { font-size: 15px; font-weight: 700; }
#DocChip { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 8px;
           padding: 4px 10px; color: %(muted)s; }
#Muted { color: %(muted)s; }
#SectionTitle { color: %(muted)s; font-size: 11px; font-weight: 700; }
#DialogTitle { font-size: 17px; font-weight: 700; }
#HeroTitle { font-size: 27px; font-weight: 700; }
#HeroSub { color: %(muted)s; font-size: 14px; }
#Card { background: %(surface)s; border: 1px solid %(border)s; border-radius: 18px; }
#DropZone { border: 2px dashed %(border)s; border-radius: 14px; background: %(surface2)s;
            color: %(muted)s; }
#Divider { background: %(border)s; }
#ToolGroup { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 11px; }
QToolButton { background: transparent; border: none; border-radius: 8px; padding: 6px; }
QToolButton:hover { background: %(hover)s; }
QToolButton:checked { background: %(accent_soft)s; }
QToolButton::menu-indicator { image: none; width: 0; }
QPushButton { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 9px;
              padding: 7px 14px; font-weight: 500; }
QPushButton:hover { background: %(hover)s; }
QPushButton:disabled { color: %(muted)s; }
QPushButton#Primary { background: %(accent)s; color: %(accent_text)s; border: 1px solid %(accent)s;
                      font-weight: 600; }
QPushButton#Primary:hover { background: %(accent_hover)s; border-color: %(accent_hover)s; }
QPushButton#Primary:disabled { background: %(surface2)s; color: %(muted)s; border-color: %(border)s; }
QPushButton#Ghost { background: transparent; border: none; padding: 5px 10px; }
QPushButton#Ghost:hover { background: %(hover)s; }
QPushButton#Recent { text-align: left; background: transparent; border: none; border-radius: 10px;
                     padding: 9px 12px; }
QPushButton#Recent:hover { background: %(hover)s; }
QLineEdit, QSpinBox, QPlainTextEdit { background: %(surface2)s; border: 1px solid %(border)s;
    border-radius: 9px; padding: 6px 9px; selection-background-color: %(accent)s;
    selection-color: %(accent_text)s; }
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus { border: 1px solid %(accent)s; }
QLineEdit#PageBox { padding: 3px 4px; border-radius: 7px; }
QSpinBox { padding-right: 9px; }
QSpinBox::up-button, QSpinBox::down-button { width: 0; border: none; }
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar::handle:vertical { background: %(scroll)s; border-radius: 4px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: %(muted)s; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(scroll)s; border-radius: 4px; min-width: 36px; }
QScrollBar::handle:horizontal:hover { background: %(muted)s; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget#FileList { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 10px;
                       padding: 4px; }
QListWidget#FileList::item { padding: 9px 10px; border-radius: 7px; }
QListWidget#FileList::item:selected { background: %(accent_soft)s; color: %(text)s; }
QMenu { background: %(surface)s; border: 1px solid %(border)s; border-radius: 12px; padding: 6px; }
QMenu::item { padding: 7px 26px 7px 10px; border-radius: 7px; }
QMenu::item:selected { background: %(hover)s; }
QMenu::item:disabled { color: %(muted)s; }
QMenu::separator { height: 1px; background: %(border)s; margin: 5px 6px; }
QMenu::icon { padding-left: 8px; }
QToolTip { background: %(surface2)s; color: %(text)s; border: 1px solid %(border)s;
           border-radius: 6px; padding: 5px 8px; }
#Toast { background: %(toast)s; color: %(toast_text)s; border-radius: 10px; padding: 10px 18px;
         font-weight: 500; }
QRadioButton { spacing: 8px; background: transparent; }
"""

ICONS = {
    "open": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "save": '<path d="M5 3h11l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M7 3v5h8V3"/><path d="M7 21v-7h10v7"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
    "redo": '<path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/>',
    "cursor": '<path d="M5 3.5l13.5 6.8-5.8 1.9-1.9 5.8z"/><path d="m13 13 5 5"/>',
    "text": '<path d="M5 7V5h14v2"/><path d="M12 5v14"/><path d="M9 19h6"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "highlight": '<path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/>',
    "draw": '<path d="M3 17c3-6 5.5-6 7.5-2s4 4 6.5-1.5S21 9 21 9"/>',
    "rect": '<rect x="4" y="5" width="16" height="14" rx="2"/>',
    "whiteout": '<path d="m7 21-4.3-4.3a1 1 0 0 1 0-1.4l10-10a1 1 0 0 1 1.4 0l5.6 5.6a1 1 0 0 1 0 1.4L12 21"/><path d="M22 21H7"/><path d="m5 11 9 9"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
    "signature": '<path d="M3 17c2.5 0 3.5-9 5.5-9s-.5 9 2 9 2-4 4-4 1 3 3 3 2-1 3.5-1"/><path d="M3 21h18"/>',
    "merge": '<path d="M6 3v6a6 6 0 0 0 6 6h0a6 6 0 0 1 6 6"/><path d="M18 3v6a6 6 0 0 1-6 6"/><path d="M12 15v6"/>',
    "split": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9"/><path d="M14.5 14.5 20 20"/><path d="M8.1 8.1 12 12"/>',
    "rotl": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    "rotr": '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    "trash": '<path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "compress": '<path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="m14 10 7-7"/><path d="m3 21 7-7"/>',
    "extract": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M12 18v-6M9 15l3 3 3-3"/>',
    "fit": '<path d="M3 12h18"/><path d="m7 8-4 4 4 4"/><path d="m17 8 4 4-4 4"/>',
    "more": '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>',
    "print": '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 14h12v7H6z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    "close": '<path d="M18 6 6 18M6 6l12 12"/>',
    "left": '<path d="m15 18-6-6 6-6"/>',
    "right": '<path d="m9 18 6-6-6-6"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    "page": '<rect x="5" y="3" width="14" height="18" rx="2"/>',
    "upload": '<path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/>',
}

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#8f9cff"/><stop offset="1" stop-color="#5a47e6"/></linearGradient></defs>
<rect x="2" y="2" width="60" height="60" rx="16" fill="url(#g)"/>
<path d="M23 14h13l11 11v21a4 4 0 0 1-4 4H23a4 4 0 0 1-4-4V18a4 4 0 0 1 4-4z" fill="#ffffff"/>
<path d="M36 14v8a3 3 0 0 0 3 3h8z" fill="#d9ddff"/>
<path d="M25 33h15M25 39h10" stroke="#5a47e6" stroke-width="3" stroke-linecap="round"/>
</svg>"""


def _render_svg(svg, w, h, dpr=2.0):
    r = QSvgRenderer(QByteArray(svg.encode()))
    pm = QPixmap(int(w * dpr), int(h * dpr))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    r.render(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def svg_pixmap(name, color, size=20, opacity=1.0):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-opacity="{opacity}" stroke-width="1.8" stroke-linecap="round" '
           f'stroke-linejoin="round">{ICONS[name]}</svg>')
    return _render_svg(svg, size, size)


def logo_pixmap(size):
    return _render_svg(LOGO_SVG, size, size)


def rgba(hexc, a):
    c = QColor(hexc)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


class Theme(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.name = "dark"
        self._registered = []

    def __getitem__(self, key):
        return THEMES[self.name][key]

    def icon(self, name):
        ic = QIcon()
        ic.addPixmap(svg_pixmap(name, self["icon"]), QIcon.Normal, QIcon.Off)
        ic.addPixmap(svg_pixmap(name, self["accent"]), QIcon.Normal, QIcon.On)
        ic.addPixmap(svg_pixmap(name, self["muted"], opacity=0.55), QIcon.Disabled, QIcon.Off)
        return ic

    def register(self, obj, name):
        self._registered.append((obj, name))
        obj.setIcon(self.icon(name))

    def apply(self, app):
        vals = dict(THEMES[self.name])
        vals["accent_soft"] = rgba(vals["accent"], 0.18)
        app.setStyleSheet(QSS % vals)
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(vals["bg"]))
        pal.setColor(QPalette.WindowText, QColor(vals["text"]))
        pal.setColor(QPalette.Base, QColor(vals["surface2"]))
        pal.setColor(QPalette.AlternateBase, QColor(vals["surface"]))
        pal.setColor(QPalette.Text, QColor(vals["text"]))
        pal.setColor(QPalette.Button, QColor(vals["surface2"]))
        pal.setColor(QPalette.ButtonText, QColor(vals["text"]))
        pal.setColor(QPalette.Highlight, QColor(vals["accent"]))
        pal.setColor(QPalette.HighlightedText, QColor(vals["accent_text"]))
        pal.setColor(QPalette.ToolTipBase, QColor(vals["surface2"]))
        pal.setColor(QPalette.ToolTipText, QColor(vals["text"]))
        pal.setColor(QPalette.PlaceholderText, QColor(vals["muted"]))
        app.setPalette(pal)
        alive = []
        for obj, name in self._registered:
            try:
                obj.setIcon(self.icon(name))
                alive.append((obj, name))
            except RuntimeError:
                pass
        self._registered = alive
        self.changed.emit()


T = Theme()


def tbtn(icon, tip, checkable=False, size=20):
    b = QToolButton()
    b.setToolTip(tip)
    b.setCheckable(checkable)
    b.setIconSize(QSize(size, size))
    b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.NoFocus)
    T.register(b, icon)
    return b


def divider(vertical=True):
    d = QFrame()
    d.setObjectName("Divider")
    if vertical:
        d.setFixedSize(1, 22)
    else:
        d.setFixedHeight(1)
    return d


def hex_to_rgb(hexc):
    c = QColor(hexc)
    return (c.redF(), c.greenF(), c.blueF())


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


# ----------------------------------------------------------------------------
# Fonts (for text that Helvetica can't encode, e.g. Greek, Cyrillic)
# ----------------------------------------------------------------------------
_font_cache = {}


def system_font(serif=False, mono=False, bold=False, italic=False):
    key = (serif, mono, bold, italic)
    if key in _font_cache:
        return _font_cache[key]
    family = "DejaVu Sans Mono" if mono else ("DejaVu Serif" if serif else "DejaVu Sans")
    style = ":bold" if bold else ""
    style += ":italic" if italic else ""
    path = None
    if shutil.which("fc-match"):
        try:
            out = subprocess.run(["fc-match", "-f", "%{file}", family + style],
                                 capture_output=True, text=True, timeout=3).stdout.strip()
            if out and Path(out).exists() and out.lower().endswith((".ttf", ".otf")):
                path = out
        except Exception:
            path = None
    _font_cache[key] = path
    return path


def pick_font(text, serif=False, mono=False, bold=False, italic=False):
    """Return (fontname, fontfile). Uses PDF base-14 fonts when possible."""
    try:
        text.encode("latin-1")
        latin = True
    except UnicodeEncodeError:
        latin = False
    if latin:
        if mono:
            base = "co"
        elif serif:
            base = "ti"
        else:
            base = "he"
        if serif and not mono:
            suffix = {(False, False): "ro", (True, False): "bo", (False, True): "it", (True, True): "bi"}
        else:
            suffix = {(False, False): "lv" if base == "he" else "ur", (True, False): "bo",
                      (False, True): "it", (True, True): "bi"}
        return base + suffix[(bold, italic)], None
    f = system_font(serif, mono, bold, italic) or system_font()
    if f:
        name = "F" + "".join("1" if x else "0" for x in (serif, mono, bold, italic))
        return name, f
    return "helv", None


# ----------------------------------------------------------------------------
# Document model with undo/redo
# ----------------------------------------------------------------------------
class Document(QObject):
    structure_changed = Signal()
    pages_changed = Signal(list)
    state_changed = Signal()

    MAX_UNDO = 40

    def __init__(self, fdoc, path=None, title=None, password=None, dirty=False):
        super().__init__()
        self.doc = fdoc
        self.path = path
        self.title = title or (Path(path).name if path else "Untitled.pdf")
        self.password = password
        self.dirty = dirty
        self.undo_stack = []
        self.redo_stack = []

    def _reopen(self, data):
        try:
            self.doc.close()
        except Exception:
            pass
        self.doc = fitz.open(stream=data, filetype="pdf")
        if self.doc.needs_pass and self.password:
            self.doc.authenticate(self.password)

    @contextmanager
    def change(self, pages=None):
        """Wrap a modification. pages=None means page structure changed."""
        snap = self.doc.tobytes()
        try:
            yield self.doc
        except Exception:
            self._reopen(snap)
            self.structure_changed.emit()
            raise
        self.undo_stack.append(snap)
        del self.undo_stack[:-self.MAX_UNDO]
        self.redo_stack.clear()
        self.dirty = True
        if pages is None:
            self.structure_changed.emit()
        else:
            self.pages_changed.emit(list(pages))
        self.state_changed.emit()

    def undo(self):
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.doc.tobytes())
        self._reopen(self.undo_stack.pop())
        self.dirty = True
        self.structure_changed.emit()
        self.state_changed.emit()
        return True

    def redo(self):
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.doc.tobytes())
        self._reopen(self.redo_stack.pop())
        self.dirty = True
        self.structure_changed.emit()
        self.state_changed.emit()
        return True

    def save(self, path):
        tmp = str(path) + ".folio-tmp"
        try:
            self.doc.save(tmp, garbage=3, deflate=True)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self.path = str(path)
        self.title = Path(path).name
        self.dirty = False
        self.state_changed.emit()


class Cancelled(Exception):
    pass


def load_document(path, parent):
    """Open a PDF (asking for its password if needed) or convert another format.
    Returns (fitz.Document, password, is_pdf)."""
    p = Path(path)
    if p.suffix.lower() != ".pdf":
        src = fitz.open(str(p))
        if src.is_pdf:
            data = src.tobytes()
        else:
            data = src.convert_to_pdf()
        src.close()
        return fitz.open(stream=data, filetype="pdf"), None, False
    doc = fitz.open(stream=p.read_bytes(), filetype="pdf")
    pw = None
    if doc.needs_pass:
        prompt = f"“{p.name}” is password protected.\nEnter its password:"
        while True:
            pw, ok = QInputDialog.getText(parent, "Password required", prompt, QLineEdit.Password)
            if not ok:
                raise Cancelled()
            if doc.authenticate(pw):
                break
            prompt = "That password didn't work. Try again:"
    return doc, pw, True


def apply_redactions(page, keep_images=True, keep_graphics=True):
    kw = {}
    if keep_images:
        kw["images"] = getattr(fitz, "PDF_REDACT_IMAGE_NONE", 0)
    kw["graphics"] = (getattr(fitz, "PDF_REDACT_LINE_ART_NONE", 0) if keep_graphics
                      else getattr(fitz, "PDF_REDACT_LINE_ART_REMOVE_IF_COVERED", 1))
    try:
        page.apply_redactions(**kw)
    except TypeError:
        kw.pop("graphics", None)
        page.apply_redactions(**kw)


# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------
TOOLS = [
    ("select", "Select", "cursor", "V", "Drag over text to copy it. Right-click a page for page options."),
    ("edit", "Edit text", "edit", "E", "Drag a box over existing text to rewrite it."),
    ("text", "Add text", "text", "T", "Click anywhere on a page to add text."),
    ("highlight", "Highlight", "highlight", "H", "Drag across text to highlight it."),
    ("draw", "Draw", "draw", "D", "Draw freehand with your mouse, touchpad or pen."),
    ("rect", "Shape", "rect", "R", "Drag to draw a rectangle."),
    ("erase", "Erase", "whiteout", "X", "Drag over an area to permanently remove what's there."),
    ("image", "Image", "image", "I", "Drag a box (or just click) where the image should go."),
    ("sign", "Sign", "signature", "S", "Click or drag a box where your signature should go."),
]
TOOL_META = {t[0]: t for t in TOOLS}
DRAG_TOOLS = {"select", "edit", "highlight", "rect", "erase", "image", "sign"}


# ----------------------------------------------------------------------------
# Small widgets
# ----------------------------------------------------------------------------
class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()
        self.timer = QTimer(self, singleShot=True, timeout=self.hide)

    def show_msg(self, text, ms=2600):
        self.setText(text)
        self.adjustSize()
        par = self.parentWidget()
        self.move((par.width() - self.width()) // 2, par.height() - self.height() - 64)
        self.raise_()
        self.show()
        self.timer.start(ms)


class Swatch(QAbstractButton):
    def __init__(self, color):
        super().__init__()
        self.color = color
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip(color)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.isChecked():
            p.setPen(QPen(QColor(T["accent"]), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(1.5, 1.5, 21, 21))
        elif self.underMouse():
            p.setPen(QPen(QColor(T["border"]), 2))
            p.drawEllipse(QRectF(1.5, 1.5, 21, 21))
        ring = QColor(T["muted"])
        ring.setAlpha(110)
        p.setPen(QPen(ring, 1))
        p.setBrush(QColor(self.color))
        p.drawEllipse(QRectF(5, 5, 14, 14))

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()


class Dialog(QDialog):
    def __init__(self, parent, title, subtitle=None, width=460):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(width)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(24, 22, 24, 20)
        self.v.setSpacing(12)
        t = QLabel(title)
        t.setObjectName("DialogTitle")
        self.v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("Muted")
            s.setWordWrap(True)
            self.v.addWidget(s)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self.v.addSpacing(4)
        self.v.addLayout(self.body)
        self.v.addSpacing(6)
        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(8)
        self.v.addLayout(self.buttons)

    def add_buttons(self, ok_text="OK", cancel=True):
        self.buttons.addStretch(1)
        if cancel:
            c = QPushButton("Cancel")
            c.clicked.connect(self.reject)
            self.buttons.addWidget(c)
        ok = QPushButton(ok_text)
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        self.buttons.addWidget(ok)
        return ok


class TextDialog(Dialog):
    def __init__(self, parent, title, subtitle, text="", size=14, ok="Add"):
        super().__init__(parent, title, subtitle, 480)
        self.edit = QPlainTextEdit(text)
        self.edit.setMinimumHeight(130)
        self.body.addWidget(self.edit)
        row = QHBoxLayout()
        lbl = QLabel("Font size")
        lbl.setObjectName("Muted")
        self.size = QSpinBox()
        self.size.setRange(4, 144)
        self.size.setValue(int(round(size)))
        self.size.setSuffix(" pt")
        self.size.setFixedWidth(80)
        row.addWidget(lbl)
        row.addWidget(self.size)
        row.addStretch(1)
        hint = QLabel("Ctrl+Enter to apply")
        hint.setObjectName("Muted")
        row.addWidget(hint)
        self.body.addLayout(row)
        self.add_buttons(ok)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.accept)
        self.edit.setFocus()
        self.edit.selectAll()

    def values(self):
        return self.edit.toPlainText(), self.size.value()


class SignaturePad(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(520, 210)
        self.setCursor(Qt.CrossCursor)
        self.strokes = []
        self.ink = QColor("#111827")

    def clear(self):
        self.strokes = []
        self.update()

    def _path(self, pts):
        path = QPainterPath(pts[0])
        if len(pts) < 3:
            for q in pts[1:]:
                path.lineTo(q)
            return path
        for a, b in zip(pts[1:-1], pts[2:]):
            mid = (a + b) / 2
            path.quadTo(a, mid)
        path.lineTo(pts[-1])
        return path

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        p.setPen(QPen(QColor("#d6d9e0"), 1, Qt.DashLine))
        y = self.height() - 50
        p.drawLine(30, y, self.width() - 30, y)
        if not self.strokes:
            p.setPen(QColor("#9aa0ad"))
            p.drawText(self.rect().adjusted(0, 0, 0, -70), Qt.AlignCenter, "Sign here")
        p.setPen(QPen(self.ink, 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        for s in self.strokes:
            if len(s) > 1:
                p.drawPath(self._path(s))
            elif s:
                p.drawPoint(s[0])

    def mousePressEvent(self, e):
        self.strokes.append([e.position()])
        self.update()

    def mouseMoveEvent(self, e):
        if self.strokes:
            self.strokes[-1].append(e.position())
            self.update()

    def to_image(self):
        pts = [q for s in self.strokes for q in s]
        if not pts:
            return None
        xs = [q.x() for q in pts]
        ys = [q.y() for q in pts]
        pad = 6
        x0, y0 = min(xs) - pad, min(ys) - pad
        w, h = max(xs) - x0 + pad, max(ys) - y0 + pad
        scale = 4
        img = QImage(int(w * scale), int(h * scale), QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(scale, scale)
        p.translate(-x0, -y0)
        p.setPen(QPen(self.ink, 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for s in self.strokes:
            if len(s) > 1:
                p.drawPath(self._path(s))
        p.end()
        return img


class SignatureDialog(Dialog):
    def __init__(self, parent):
        super().__init__(parent, "Create your signature",
                         "Draw your signature below. It's saved on this computer for next time.", 580)
        self.pad = SignaturePad()
        self.body.addWidget(self.pad)
        row = QHBoxLayout()
        row.setSpacing(6)
        lbl = QLabel("Ink")
        lbl.setObjectName("Muted")
        row.addWidget(lbl)
        grp = QButtonGroup(self)
        for i, c in enumerate(("#111827", "#1d4ed8", "#0f766e")):
            s = Swatch(c)
            grp.addButton(s)
            s.setChecked(i == 0)
            s.clicked.connect(lambda _=False, c=c: self._ink(c))
            row.addWidget(s)
        row.addStretch(1)
        clear = QPushButton("Clear")
        clear.setObjectName("Ghost")
        clear.clicked.connect(self.pad.clear)
        row.addWidget(clear)
        from_file = QPushButton("Use an image file…")
        from_file.setObjectName("Ghost")
        from_file.clicked.connect(self._from_file)
        row.addWidget(from_file)
        self.body.addLayout(row)
        self.add_buttons("Save signature")
        self.image_file = None

    def _ink(self, c):
        self.pad.ink = QColor(c)
        self.pad.update()

    def _from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose signature image", str(Path.home()), IMAGE_FILTER)
        if path:
            self.image_file = path
            self.accept()

    def accept(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if self.image_file:
            QImage(self.image_file).save(str(SIG_PATH), "PNG")
            return super().accept()
        img = self.pad.to_image()
        if img is None:
            return
        img.save(str(SIG_PATH), "PNG")
        super().accept()


class MergeDialog(Dialog):
    def __init__(self, parent, paths=()):
        super().__init__(parent, "Merge PDFs",
                         "Add files and drag them into the order you want. Images work too.", 520)
        self.list = QListWidget()
        self.list.setObjectName("FileList")
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setMinimumHeight(260)
        self.list.setIconSize(QSize(18, 18))
        self.body.addWidget(self.list)
        row = QHBoxLayout()
        add = QPushButton("Add files…")
        add.clicked.connect(self.add_files)
        rem = QPushButton("Remove")
        rem.clicked.connect(self.remove)
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        self.count = QLabel()
        self.count.setObjectName("Muted")
        row.addWidget(self.count)
        self.body.addLayout(row)
        self.ok = self.add_buttons("Merge")
        for p in paths:
            self._add(p)
        self._update()

    def _add(self, path):
        it = QListWidgetItem(T.icon("file"), Path(path).name)
        it.setToolTip(str(path))
        it.setData(Qt.UserRole, str(path))
        self.list.addItem(it)

    def _update(self):
        n = self.list.count()
        self.count.setText(f"{n} file{'s' if n != 1 else ''}")
        self.ok.setEnabled(n >= 2)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add files", str(Path.home()), OPEN_FILTER)
        for p in paths:
            self._add(p)
        self._update()

    def remove(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        self._update()

    def paths(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]


def parse_ranges(text, n):
    """'1-3, 5, 7-' -> [[0,1,2],[4],[6..n-1]]"""
    groups = []
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a.strip() else 1
            b = int(b) if b.strip() else n
        else:
            a = b = int(part)
        a, b = max(1, a), min(n, b)
        if a > b:
            raise ValueError(part)
        groups.append(list(range(a - 1, b)))
    if not groups:
        raise ValueError("empty")
    return groups


class SplitDialog(Dialog):
    def __init__(self, parent, n):
        super().__init__(parent, "Split document", f"This document has {n} pages. How should it be split?", 460)
        self.n = n
        self.r_each = QRadioButton("Every page as its own file")
        self.r_every = QRadioButton("Every")
        self.r_ranges = QRadioButton("Custom ranges")
        self.r_each.setChecked(True)
        self.every = QSpinBox()
        self.every.setRange(1, max(1, n))
        self.every.setValue(min(2, n))
        self.every.setSuffix(" pages")
        self.every.setFixedWidth(100)
        self.ranges = QLineEdit()
        self.ranges.setPlaceholderText("e.g. 1-3, 4, 5-")
        self.body.addWidget(self.r_each)
        row = QHBoxLayout()
        row.addWidget(self.r_every)
        row.addWidget(self.every)
        row.addStretch(1)
        self.body.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(self.r_ranges)
        row2.addWidget(self.ranges, 1)
        self.body.addLayout(row2)
        self.every.valueChanged.connect(lambda: self.r_every.setChecked(True))
        self.ranges.textEdited.connect(lambda: self.r_ranges.setChecked(True))
        self.add_buttons("Choose folder & split")

    def groups(self):
        if self.r_each.isChecked():
            return [[i] for i in range(self.n)]
        if self.r_every.isChecked():
            k = self.every.value()
            return [list(range(i, min(i + k, self.n))) for i in range(0, self.n, k)]
        return parse_ranges(self.ranges.text(), self.n)


class PasswordDialog(Dialog):
    def __init__(self, parent):
        super().__init__(parent, "Protect with password",
                         "Saves an encrypted copy (AES-256). Anyone opening it will need this password.")
        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.Password)
        self.pw1.setPlaceholderText("Password")
        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.Password)
        self.pw2.setPlaceholderText("Confirm password")
        self.err = QLabel("")
        self.err.setStyleSheet(f"color: {T['danger']};")
        self.body.addWidget(self.pw1)
        self.body.addWidget(self.pw2)
        self.body.addWidget(self.err)
        self.add_buttons("Save protected copy…")

    def accept(self):
        if len(self.pw1.text()) < 1:
            self.err.setText("Please enter a password.")
            return
        if self.pw1.text() != self.pw2.text():
            self.err.setText("The passwords don't match.")
            return
        super().accept()


# ----------------------------------------------------------------------------
# Page viewer
# ----------------------------------------------------------------------------
class PageWidget(QWidget):
    def __init__(self, viewer, index):
        super().__init__()
        self.v = viewer
        self.index = index
        self.start = None
        self.cur = None
        self.ink = []

    def _clamp(self, pt):
        return QPointF(min(max(pt.x(), 0), self.width()), min(max(pt.y(), 0), self.height()))

    def paintEvent(self, e):
        if not self.v.d or self.index >= len(self.v.d.doc) or self not in self.v.pages:
            return
        p = QPainter(self)
        p.drawPixmap(0, 0, self.v.pixmap(self.index))
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(0, 0, 0, 45), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1))
        hits = self.v.search_hits.get(self.index)
        if hits:
            for k, r in enumerate(hits):
                qr = self.v.pdf_rect_to_widget(self.index, r)
                active = (self.index, k) == self.v.active_hit
                p.fillRect(qr, QColor(255, 186, 0, 150 if active else 70))
        main = self.v.main
        tool = main.tool
        accent = QColor(T["accent"])
        if self.start is not None and self.cur is not None:
            r = QRectF(self.start, self.cur).normalized()
            if tool == "highlight":
                c = QColor(main.opts["highlight"]["color"])
                c.setAlpha(100)
                p.fillRect(r, c)
            elif tool == "erase":
                p.fillRect(r, QColor(255, 255, 255, 230))
                p.setPen(QPen(QColor(T["danger"]), 1.5, Qt.DashLine))
                p.drawRect(r)
            elif tool == "rect":
                o = main.opts["rect"]
                p.setPen(QPen(QColor(o["color"]), max(1.0, o["size"] * self.v.zoom)))
                p.drawRect(r)
            else:
                fill = QColor(accent)
                fill.setAlpha(35)
                p.fillRect(r, fill)
                p.setPen(QPen(accent, 1.5, Qt.DashLine))
                p.drawRect(r)
        if len(self.ink) > 1:
            o = main.opts["draw"]
            p.setPen(QPen(QColor(o["color"]), max(1.0, o["size"] * self.v.zoom),
                          Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath(self.ink[0])
            for q in self.ink[1:]:
                path.lineTo(q)
            p.drawPath(path)

    def mousePressEvent(self, e):
        self.v.setFocus()
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        tool = self.v.main.tool
        pos = self._clamp(e.position())
        if tool == "text":
            self.v.main.page_click(self.index, pos)
        elif tool == "draw":
            self.ink = [pos]
        elif tool in DRAG_TOOLS:
            self.start = self.cur = pos

    def mouseMoveEvent(self, e):
        pos = self._clamp(e.position())
        if self.ink:
            self.ink.append(pos)
            self.update()
        elif self.start is not None:
            self.cur = pos
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.ink:
            pts, self.ink = self.ink, []
            self.update()
            if len(pts) > 1:
                self.v.main.page_ink(self.index, pts)
            return
        if self.start is not None:
            r = QRectF(self.start, self.cur).normalized()
            self.start = self.cur = None
            self.update()
            self.v.main.page_rect(self.index, r)

    def contextMenuEvent(self, e):
        self.v.main.page_context(self.index, QPointF(e.pos()), e.globalPos())


class Viewer(QScrollArea):
    current_changed = Signal(int)
    zoom_changed = Signal(float)
    CACHE_PIXELS = 120_000_000

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName("Viewer")
        self.setWidgetResizable(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.container = QWidget()
        self.container.setObjectName("Canvas")
        self.lay = QVBoxLayout(self.container)
        self.lay.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.lay.setSpacing(18)
        self.lay.setContentsMargins(28, 28, 28, 48)
        self.setWidget(self.container)
        self.d = None
        self.zoom = 1.0
        self.pages = []
        self.cache = {}
        self.current = 0
        self.search_hits = {}
        self.active_hit = None
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    # -- document ---------------------------------------------------------
    def set_document(self, d):
        self.d = d
        self.rebuild()

    def rebuild(self, keep_page=None):
        for w in self.pages:
            self.lay.removeWidget(w)
            w.hide()
            w.deleteLater()
        self.pages = []
        self.cache.clear()
        if not self.d:
            return
        for i in range(len(self.d.doc)):
            w = PageWidget(self, i)
            w.setFixedSize(self.page_size(i))
            self.lay.addWidget(w, 0, Qt.AlignHCenter)
            self.pages.append(w)
        self.set_tool_cursor(self.main.tool)
        self.lay.activate()
        target = min(keep_page if keep_page is not None else 0, len(self.pages) - 1)
        self.current = -1
        QTimer.singleShot(0, lambda: self.scroll_to(max(target, 0), animate=False))

    def refresh(self, pages):
        for i in pages:
            self.cache.pop(i, None)
            if 0 <= i < len(self.pages):
                self.pages[i].setFixedSize(self.page_size(i))
                self.pages[i].update()

    def page_size(self, i):
        r = self.d.doc[i].rect
        return QSize(max(1, round(r.width * self.zoom)), max(1, round(r.height * self.zoom)))

    def pixmap(self, i):
        pm = self.cache.get(i)
        if pm is not None:
            return pm
        dpr = self.devicePixelRatioF()
        z = self.zoom * dpr
        pix = self.d.doc[i].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)
        self.cache[i] = pm
        total = sum(p.width() * p.height() for p in self.cache.values())
        while total > self.CACHE_PIXELS and len(self.cache) > 2:
            k = next(iter(self.cache))
            if k == i:
                break
            old = self.cache.pop(k)
            total -= old.width() * old.height()
        return pm

    # -- coordinates --------------------------------------------------------
    def widget_to_pdf(self, i, qp):
        page = self.d.doc[i]
        return fitz.Point(qp.x() / self.zoom, qp.y() / self.zoom) * page.derotation_matrix

    def widget_rect_to_pdf(self, i, qr):
        a = self.widget_to_pdf(i, qr.topLeft())
        b = self.widget_to_pdf(i, qr.bottomRight())
        return fitz.Rect(a, b).normalize()

    def pdf_rect_to_widget(self, i, r):
        page = self.d.doc[i]
        rr = fitz.Rect(r) * page.rotation_matrix
        z = self.zoom
        return QRectF(rr.x0 * z, rr.y0 * z, rr.width * z, rr.height * z)

    # -- navigation ---------------------------------------------------------
    def scroll_to(self, i, animate=True, y_offset=None):
        if not (0 <= i < len(self.pages)):
            return
        w = self.pages[i]
        y = w.y() - 16 if y_offset is None else w.y() + y_offset - self.viewport().height() // 3
        self.verticalScrollBar().setValue(max(0, int(y)))
        self._set_current(i)

    def scroll_to_rect(self, i, rect):
        qr = self.pdf_rect_to_widget(i, rect)
        self.scroll_to(i, y_offset=qr.y())
        w = self.pages[i]
        self.ensureVisible(int(w.x() + qr.center().x()), int(w.y() + qr.center().y()), 80, 80)

    def _set_current(self, i):
        if i != self.current:
            self.current = i
            self.current_changed.emit(i)

    def _on_scroll(self, value):
        if not self.pages:
            return
        mid = value + self.viewport().height() / 3
        lo, hi = 0, len(self.pages) - 1
        while lo < hi:
            m = (lo + hi + 1) // 2
            if self.pages[m].y() <= mid:
                lo = m
            else:
                hi = m - 1
        self._set_current(lo)

    # -- zoom ---------------------------------------------------------------
    def set_zoom(self, z):
        z = max(0.2, min(5.0, z))
        if not self.d or abs(z - self.zoom) < 1e-3:
            self.zoom = z
            self.zoom_changed.emit(z)
            return
        i = max(self.current, 0)
        frac = 0.0
        if self.pages:
            w = self.pages[i]
            frac = (self.verticalScrollBar().value() - w.y()) / max(1, w.height())
        self.zoom = z
        self.cache.clear()
        for k, w in enumerate(self.pages):
            w.setFixedSize(self.page_size(k))
        self.lay.activate()
        self.container.adjustSize()
        if self.pages:
            w = self.pages[i]
            self.verticalScrollBar().setValue(int(w.y() + frac * w.height()))
        self.zoom_changed.emit(z)

    def _avail(self):
        m = self.lay.contentsMargins()
        sb = self.verticalScrollBar().sizeHint().width()
        return (self.viewport().width() - m.left() - m.right() - sb,
                self.viewport().height() - m.top() - 16)

    def fit_width(self):
        if not self.d:
            return
        w = max(self.d.doc[i].rect.width for i in range(min(len(self.d.doc), 50)))
        self.set_zoom(self._avail()[0] / w)

    def fit_page(self):
        if not self.d:
            return
        r = self.d.doc[max(self.current, 0)].rect
        aw, ah = self._avail()
        self.set_zoom(min(aw / r.width, ah / r.height))

    def initial_zoom(self):
        if not self.d:
            return
        w = max(self.d.doc[i].rect.width for i in range(min(len(self.d.doc), 50)))
        self.set_zoom(max(0.5, min(1.5, self._avail()[0] / w)))

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            steps = e.angleDelta().y() / 120
            self.set_zoom(self.zoom * (1.1 ** steps))
            e.accept()
        else:
            super().wheelEvent(e)

    def set_tool_cursor(self, tool):
        cur = {"select": Qt.IBeamCursor, "text": Qt.IBeamCursor, "draw": Qt.CrossCursor}.get(
            tool, Qt.CrossCursor)
        for w in self.pages:
            w.setCursor(cur)

    def update_pages(self, pages=None):
        for i in (pages if pages is not None else range(len(self.pages))):
            if 0 <= i < len(self.pages):
                self.pages[i].update()


# ----------------------------------------------------------------------------
# Thumbnail sidebar
# ----------------------------------------------------------------------------
class ThumbList(QListWidget):
    reordered = Signal()

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def dropEvent(self, e):
        super().dropEvent(e)
        QTimer.singleShot(0, self.reordered.emit)


class ThumbDelegate(QStyledItemDelegate):
    W = 128

    def __init__(self, sidebar):
        super().__init__(sidebar)
        self.sb = sidebar

    def sizeHint(self, opt, idx):
        ar = idx.data(Qt.UserRole + 1) or 1.414
        w = self.W if ar >= 1 else int(self.W / ar * 0.8) if ar < 0.8 else self.W
        w = min(w, self.W + 20)
        return QSize(self.sb.list.viewport().width() - 2, int(w * ar) + 42)

    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = opt.rect
        sel = bool(opt.state & QStyle.State_Selected)
        hov = bool(opt.state & QStyle.State_MouseOver)
        ar = idx.data(Qt.UserRole + 1) or 1.414
        h = r.height() - 42
        w = int(h / ar)
        x = r.x() + (r.width() - w) // 2
        y = r.y() + 8
        card = QRectF(r).adjusted(8, 2, -8, -2)
        if sel:
            p.setPen(Qt.NoPen)
            c = QColor(T["accent"])
            c.setAlpha(42)
            p.setBrush(c)
            p.drawRoundedRect(card, 10, 10)
        elif hov:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T["hover"]))
            p.drawRoundedRect(card, 10, 10)
        target = QRect(x, y, w, h)
        p.drawPixmap(target, self.sb.thumb(idx.row(), w))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(T["accent"]) if sel else QColor(0, 0, 0, 50), 2 if sel else 1))
        p.drawRoundedRect(QRectF(target).adjusted(-0.5, -0.5, 0.5, 0.5), 2, 2)
        f = QFont(opt.font)
        f.setPointSizeF(max(8.0, f.pointSizeF() - 1))
        f.setBold(sel)
        p.setFont(f)
        p.setPen(QColor(T["accent"] if sel else T["muted"]))
        p.drawText(QRect(r.x(), y + h + 4, r.width(), 24), Qt.AlignCenter, str(idx.row() + 1))
        p.restore()


class Sidebar(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(200)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setContentsMargins(16, 0, 10, 0)
        t = QLabel("PAGES")
        t.setObjectName("SectionTitle")
        self.count = QLabel("")
        self.count.setObjectName("Muted")
        head.addWidget(t)
        head.addWidget(self.count)
        head.addStretch(1)
        v.addLayout(head)
        acts = QHBoxLayout()
        acts.setContentsMargins(10, 0, 10, 4)
        acts.setSpacing(2)
        self.b_rotl = tbtn("rotl", "Rotate left", size=18)
        self.b_rotr = tbtn("rotr", "Rotate right", size=18)
        self.b_add = tbtn("plus", "Insert pages", size=18)
        self.b_ext = tbtn("extract", "Extract selected pages", size=18)
        self.b_del = tbtn("trash", "Delete selected pages (Del)", size=18)
        self.b_rotl.clicked.connect(lambda: main.rotate_pages(-90))
        self.b_rotr.clicked.connect(lambda: main.rotate_pages(90))
        self.b_ext.clicked.connect(main.extract_pages)
        self.b_del.clicked.connect(main.delete_pages)
        add_menu = QMenu(self)
        a1 = add_menu.addAction("Insert pages from file…")
        a1.triggered.connect(main.insert_from_file)
        a2 = add_menu.addAction("Insert blank page")
        a2.triggered.connect(main.insert_blank)
        a3 = add_menu.addAction("Duplicate page")
        a3.triggered.connect(main.duplicate_page)
        self.b_add.setMenu(add_menu)
        self.b_add.setPopupMode(QToolButton.InstantPopup)
        for b in (self.b_rotl, self.b_rotr, self.b_add, self.b_ext, self.b_del):
            acts.addWidget(b)
        acts.addStretch(1)
        v.addLayout(acts)
        self.list = ThumbList()
        self.list.setItemDelegate(ThumbDelegate(self))
        self.list.reordered.connect(self._reordered)
        self.list.itemClicked.connect(lambda it: main.viewer.scroll_to(self.list.row(it)))
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context)
        v.addWidget(self.list, 1)
        self.thumbs = {}
        QShortcut(QKeySequence.Delete, self.list, activated=main.delete_pages,
                  context=Qt.WidgetWithChildrenShortcut)

    def rebuild(self):
        self.thumbs.clear()
        self.list.blockSignals(True)
        self.list.clear()
        d = self.main.d
        if d:
            for i in range(len(d.doc)):
                it = QListWidgetItem()
                it.setData(Qt.UserRole, i)
                r = d.doc[i].rect
                it.setData(Qt.UserRole + 1, r.height / max(1, r.width))
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
                self.list.addItem(it)
            n = len(d.doc)
            self.count.setText(f"· {n}")
        else:
            self.count.setText("")
        self.list.blockSignals(False)

    def refresh(self, pages):
        d = self.main.d
        for i in pages:
            self.thumbs.pop(i, None)
            it = self.list.item(i)
            if it:
                r = d.doc[i].rect
                it.setData(Qt.UserRole + 1, r.height / max(1, r.width))
        self.list.doItemsLayout()
        self.list.viewport().update()

    def thumb(self, row, w):
        pm = self.thumbs.get(row)
        if pm is not None and pm.width() / pm.devicePixelRatio() >= w - 1:
            return pm
        dpr = self.devicePixelRatioF()
        page = self.main.d.doc[row]
        z = w * dpr / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(dpr)
        self.thumbs[row] = pm
        return pm

    def select_row(self, i):
        self.list.blockSignals(True)
        it = self.list.item(i)
        if it and not it.isSelected() or len(self.list.selectedItems()) <= 1:
            self.list.setCurrentRow(i)
            self.list.scrollToItem(self.list.item(i)) if self.list.item(i) else None
        self.list.blockSignals(False)

    def selected_rows(self):
        return sorted(self.list.row(it) for it in self.list.selectedItems())

    def _reordered(self):
        order = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if order == sorted(order):
            return
        with self.main.d.change() as doc:
            doc.select(order)
        self.main.toast.show_msg("Pages reordered")

    def _context(self, pos):
        it = self.list.itemAt(pos)
        if not it:
            return
        m = QMenu(self)
        n = len(self.selected_rows())
        lbl = f"{n} pages" if n > 1 else "page"
        m.addAction(T.icon("rotr"), "Rotate right", lambda: self.main.rotate_pages(90))
        m.addAction(T.icon("rotl"), "Rotate left", lambda: self.main.rotate_pages(-90))
        m.addSeparator()
        m.addAction(T.icon("copy"), "Duplicate page", self.main.duplicate_page)
        m.addAction(T.icon("page"), "Insert blank page after", self.main.insert_blank)
        m.addAction(T.icon("extract"), f"Extract {lbl}…", self.main.extract_pages)
        m.addSeparator()
        m.addAction(T.icon("trash"), f"Delete {lbl}", self.main.delete_pages)
        m.exec(self.list.viewport().mapToGlobal(pos))


# ----------------------------------------------------------------------------
# Options bar (per-tool settings)
# ----------------------------------------------------------------------------
class OptionsBar(QWidget):
    COLORS = ["#111827", "#2563eb", "#dc2626", "#16a34a", "#facc15", "#f97316", "#7c3aed", "#ec4899"]

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName("OptionsBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(46)
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(10)
        self.icon = QLabel()
        self.title = QLabel()
        self.title.setStyleSheet("font-weight: 600;")
        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        h.addWidget(self.icon)
        h.addWidget(self.title)
        h.addWidget(self.hint)
        h.addStretch(1)

        self.color_box = QWidget()
        cb = QHBoxLayout(self.color_box)
        cb.setContentsMargins(0, 0, 0, 0)
        cb.setSpacing(2)
        lbl = QLabel("Color")
        lbl.setObjectName("Muted")
        cb.addWidget(lbl)
        cb.addSpacing(4)
        self.swatches = QButtonGroup(self)
        for c in self.COLORS:
            s = Swatch(c)
            self.swatches.addButton(s)
            s.clicked.connect(lambda _=False, c=c: self._set_color(c))
            cb.addWidget(s)
        self.custom = tbtn("plus", "Custom color…", size=16)
        self.custom.clicked.connect(self._custom_color)
        cb.addWidget(self.custom)
        h.addWidget(self.color_box)

        self.size_box = QWidget()
        sb = QHBoxLayout(self.size_box)
        sb.setContentsMargins(10, 0, 0, 0)
        sb.setSpacing(6)
        self.size_lbl = QLabel("Size")
        self.size_lbl.setObjectName("Muted")
        self.size = QSpinBox()
        self.size.setFixedWidth(76)
        self.size.valueChanged.connect(self._set_size)
        sb.addWidget(self.size_lbl)
        sb.addWidget(self.size)
        h.addWidget(self.size_box)

        self.sig_btn = QPushButton("New signature…")
        self.sig_btn.clicked.connect(main.new_signature)
        h.addWidget(self.sig_btn)
        self._tool = None

    def set_tool(self, tool, enabled=True):
        self._tool = tool
        key, name, icon, sc, hint = TOOL_META[tool]
        self.icon.setPixmap(svg_pixmap(icon, T["accent"], 18))
        if not enabled:
            self.title.setText("Welcome")
            self.hint.setText("Open a PDF to start editing.")
            self.icon.setPixmap(svg_pixmap("info", T["accent"], 18))
        else:
            self.title.setText(name)
            self.hint.setText(hint)
        o = self.main.opts.get(tool) if enabled else None
        self.color_box.setVisible(bool(o and "color" in o))
        self.size_box.setVisible(bool(o and o.get("size")))
        self.sig_btn.setVisible(enabled and tool == "sign")
        if o:
            self.swatches.setExclusive(False)
            for b in self.swatches.buttons():
                b.setChecked(b.color.lower() == o.get("color", "").lower())
            self.swatches.setExclusive(True)
            if o.get("size"):
                self.size.blockSignals(True)
                if tool == "text":
                    self.size_lbl.setText("Font size")
                    self.size.setRange(4, 144)
                    self.size.setSuffix(" pt")
                else:
                    self.size_lbl.setText("Thickness")
                    self.size.setRange(1, 30)
                    self.size.setSuffix(" px")
                self.size.setValue(int(o["size"]))
                self.size.blockSignals(False)

    def _set_color(self, c):
        o = self.main.opts.get(self._tool)
        if o is not None:
            o["color"] = c

    def _custom_color(self):
        o = self.main.opts.get(self._tool)
        if o is None:
            return
        c = QColorDialog.getColor(QColor(o["color"]), self, "Pick a color")
        if c.isValid():
            o["color"] = c.name()
            self.set_tool(self._tool)

    def _set_size(self, v):
        o = self.main.opts.get(self._tool)
        if o is not None and "size" in o:
            o["size"] = v

    def refresh_theme(self):
        if self._tool:
            self.set_tool(self._tool, self.main.d is not None)


# ----------------------------------------------------------------------------
# Home screen
# ----------------------------------------------------------------------------
class DropZone(QLabel):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName("DropZone")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(120)
        self.setCursor(Qt.PointingHandCursor)
        self.setText("Drop PDFs here, or click to browse\nDrop several files to merge them")

    def mousePressEvent(self, e):
        self.main.open_dialog()


class HomeView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setObjectName("Home")
        self.setAttribute(Qt.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(580)
        v = QVBoxLayout(card)
        v.setContentsMargins(44, 40, 44, 32)
        v.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(64))
        logo.setAlignment(Qt.AlignCenter)
        v.addWidget(logo)
        v.addSpacing(6)
        title = QLabel("Your PDFs, beautifully simple.")
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)
        sub = QLabel("Open, edit, sign, merge and organize PDF documents.")
        sub.setObjectName("HeroSub")
        sub.setAlignment(Qt.AlignCenter)
        v.addWidget(sub)
        v.addSpacing(14)
        v.addWidget(DropZone(main))
        v.addSpacing(6)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        b_open = QPushButton("  Open PDF")
        b_open.setObjectName("Primary")
        b_open.setMinimumHeight(40)
        T.register(b_open, "open")
        b_open.clicked.connect(main.open_dialog)
        b_merge = QPushButton("  Merge PDFs")
        b_merge.setMinimumHeight(40)
        T.register(b_merge, "merge")
        b_merge.clicked.connect(main.merge_dialog)
        for b in (b_open, b_merge):
            b.setCursor(Qt.PointingHandCursor)
            btns.addWidget(b, 1)
        v.addLayout(btns)
        v.addSpacing(10)
        self.recent_title = QLabel("RECENT")
        self.recent_title.setObjectName("SectionTitle")
        v.addWidget(self.recent_title)
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(0)
        v.addLayout(self.recent_box)
        row.addWidget(card)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)
        T.changed.connect(self.refresh_recent)

    def refresh_recent(self):
        while self.recent_box.count():
            it = self.recent_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        recent = [p for p in self.main.recent() if Path(p).exists()][:5]
        self.recent_title.setVisible(bool(recent))
        for p in recent:
            b = QPushButton(f"  {Path(p).name}")
            b.setObjectName("Recent")
            b.setIcon(T.icon("file"))
            b.setToolTip(p)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, p=p: self.main.open_path(p))
            self.recent_box.addWidget(b)


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.d = None
        self.tool = "select"
        self.settings = QSettings("Folio", "Folio")
        self.opts = {
            "text": {"color": "#111827", "size": 14},
            "highlight": {"color": "#facc15"},
            "draw": {"color": "#2563eb", "size": 2},
            "rect": {"color": "#dc2626", "size": 2},
        }
        self.search_term = ""
        self.hits = []
        self.hit_pos = -1
        self.doc_actions = []
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon(logo_pixmap(256)))
        self.resize(1380, 900)
        self.setMinimumSize(980, 620)
        self.setAcceptDrops(True)

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())
        self.options = OptionsBar(self)
        root.addWidget(self.options)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.home = HomeView(self)
        self.stack.addWidget(self.home)
        editor = QWidget()
        eh = QHBoxLayout(editor)
        eh.setContentsMargins(0, 0, 0, 0)
        eh.setSpacing(0)
        self.sidebar = Sidebar(self)
        self.viewer = Viewer(self)
        eh.addWidget(self.sidebar)
        eh.addWidget(self.viewer, 1)
        self.stack.addWidget(editor)
        root.addWidget(self._build_bottombar())
        self.toast = Toast(central)

        self.viewer.current_changed.connect(self._on_current)
        self.viewer.zoom_changed.connect(lambda z: self.zoom_btn.setText(f"{round(z * 100)}%"))
        self._shortcuts()
        T.changed.connect(self._on_theme)
        self.home.refresh_recent()
        self.set_tool("select")
        self.update_state()

    # -- building -----------------------------------------------------------
    def _build_topbar(self):
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setAttribute(Qt.WA_StyledBackground, True)
        bar.setFixedHeight(60)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 14, 0)
        h.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(28))
        h.addWidget(logo)
        brand = QLabel(APP)
        brand.setObjectName("Brand")
        h.addWidget(brand)
        h.addSpacing(12)
        self.doc_chip = QLabel("")
        self.doc_chip.setObjectName("DocChip")
        self.doc_chip.setMaximumWidth(260)
        h.addWidget(self.doc_chip)
        h.addStretch(1)

        self.tool_group = QWidget()
        self.tool_group.setObjectName("ToolGroup")
        self.tool_group.setAttribute(Qt.WA_StyledBackground, True)
        tg = QHBoxLayout(self.tool_group)
        tg.setContentsMargins(4, 4, 4, 4)
        tg.setSpacing(2)
        self.tool_btns = {}
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for key, name, icon, sc, _hint in TOOLS:
            b = tbtn(icon, f"{name}   {sc}", checkable=True)
            grp.addButton(b)
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            tg.addWidget(b)
            self.tool_btns[key] = b
            if key in ("edit", "highlight", "erase"):
                tg.addSpacing(3)
                tg.addWidget(divider())
                tg.addSpacing(3)
        h.addWidget(self.tool_group)
        h.addStretch(1)

        self.undo_btn = tbtn("undo", "Undo   Ctrl+Z")
        self.undo_btn.clicked.connect(self.undo)
        self.redo_btn = tbtn("redo", "Redo   Ctrl+Shift+Z")
        self.redo_btn.clicked.connect(self.redo)
        h.addWidget(self.undo_btn)
        h.addWidget(self.redo_btn)
        h.addSpacing(6)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search")
        self.search.setFixedWidth(190)
        self.search.setClearButtonEnabled(True)
        self.search_action = self.search.addAction(T.icon("search"), QLineEdit.LeadingPosition)
        self.search.returnPressed.connect(self.find_next)
        self.search.textChanged.connect(lambda t: self.search_reset() if not t else None)
        h.addWidget(self.search)
        self.search_count = QLabel("")
        self.search_count.setObjectName("Muted")
        h.addWidget(self.search_count)
        h.addSpacing(4)

        self.theme_btn = tbtn("sun", "Switch theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        h.addWidget(self.theme_btn)
        self.more_btn = tbtn("more", "More")
        self.more_btn.setMenu(self._build_menu())
        self.more_btn.setPopupMode(QToolButton.InstantPopup)
        h.addWidget(self.more_btn)
        h.addSpacing(6)
        self.open_btn = QPushButton("Open")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(self.open_dialog)
        h.addWidget(self.open_btn)
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("Primary")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save)
        h.addWidget(self.save_btn)
        return bar

    def _build_menu(self):
        m = QMenu(self)

        def add(text, icon, fn, shortcut=None, needs_doc=True):
            a = m.addAction(text)
            T.register(a, icon)
            a.triggered.connect(fn)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
                self.addAction(a)
            if needs_doc:
                self.doc_actions.append(a)
            return a

        add("Open…", "open", self.open_dialog, "Ctrl+O", False)
        add("Merge PDFs…", "merge", self.merge_dialog, None, False)
        m.addSeparator()
        add("Save as…", "save", self.save_as, "Ctrl+Shift+S")
        add("Insert pages from file…", "plus", self.insert_from_file)
        add("Extract selected pages…", "extract", self.extract_pages)
        add("Split document…", "split", self.split_dialog)
        m.addSeparator()
        add("Compress…", "compress", self.compress)
        add("Protect with password…", "lock", self.protect)
        add("Print…", "print", self.print_doc, "Ctrl+P")
        m.addSeparator()
        add("Close document", "close", self.close_document, "Ctrl+W")
        add(f"About {APP}", "info", self.about, None, False)
        return m

    def _build_bottombar(self):
        bar = QWidget()
        bar.setObjectName("BottomBar")
        bar.setAttribute(Qt.WA_StyledBackground, True)
        bar.setFixedHeight(40)
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 0, 14, 0)
        h.setSpacing(4)
        self.prev_btn = tbtn("left", "Previous page", size=16)
        self.prev_btn.clicked.connect(lambda: self.viewer.scroll_to(self.viewer.current - 1))
        self.page_box = QLineEdit()
        self.page_box.setObjectName("PageBox")
        self.page_box.setFixedWidth(46)
        self.page_box.setAlignment(Qt.AlignCenter)
        self.page_box.returnPressed.connect(self._goto_page)
        self.page_total = QLabel("")
        self.page_total.setObjectName("Muted")
        self.next_btn = tbtn("right", "Next page", size=16)
        self.next_btn.clicked.connect(lambda: self.viewer.scroll_to(self.viewer.current + 1))
        for w in (self.prev_btn, self.page_box, self.page_total, self.next_btn):
            h.addWidget(w)
        h.addSpacing(10)
        self.status = QLabel("")
        self.status.setObjectName("Muted")
        h.addWidget(self.status)
        h.addStretch(1)
        self.zoom_out_btn = tbtn("minus", "Zoom out   Ctrl+-", size=16)
        self.zoom_out_btn.clicked.connect(lambda: self.viewer.set_zoom(self.viewer.zoom / 1.15))
        self.zoom_btn = QPushButton("100%")
        self.zoom_btn.setObjectName("Ghost")
        self.zoom_btn.setFixedWidth(64)
        self.zoom_btn.setCursor(Qt.PointingHandCursor)
        zm = QMenu(self)
        for pct in (50, 75, 100, 125, 150, 200, 300):
            zm.addAction(f"{pct}%", lambda p=pct: self.viewer.set_zoom(p / 100))
        zm.addSeparator()
        zm.addAction("Fit width", self.viewer_fit_width)
        zm.addAction("Fit page", lambda: self.viewer.fit_page())
        self.zoom_btn.setMenu(zm)
        self.zoom_in_btn = tbtn("plus", "Zoom in   Ctrl++", size=16)
        self.zoom_in_btn.clicked.connect(lambda: self.viewer.set_zoom(self.viewer.zoom * 1.15))
        self.fit_btn = tbtn("fit", "Fit width   Ctrl+0", size=16)
        self.fit_btn.clicked.connect(self.viewer_fit_width)
        for w in (self.zoom_out_btn, self.zoom_btn, self.zoom_in_btn, self.fit_btn):
            h.addWidget(w)
        return bar

    def viewer_fit_width(self):
        self.viewer.fit_width()

    def _shortcuts(self):
        def sc(key, fn, parent=None, ctx=Qt.WindowShortcut):
            s = QShortcut(QKeySequence(key), parent or self)
            s.setContext(ctx)
            s.activated.connect(fn)

        sc("Ctrl+S", self.save)
        sc("Ctrl+Z", self.undo)
        sc("Ctrl+Shift+Z", self.redo)
        sc("Ctrl+Y", self.redo)
        sc("Ctrl+F", lambda: (self.search.setFocus(), self.search.selectAll()))
        sc("F3", self.find_next)
        sc("Shift+F3", lambda: self.find_next(backwards=True))
        sc("Ctrl+=", lambda: self.viewer.set_zoom(self.viewer.zoom * 1.15))
        sc("Ctrl++", lambda: self.viewer.set_zoom(self.viewer.zoom * 1.15))
        sc("Ctrl+-", lambda: self.viewer.set_zoom(self.viewer.zoom / 1.15))
        sc("Ctrl+0", self.viewer_fit_width)
        for key, _n, _i, letter, _h in TOOLS:
            sc(letter, lambda k=key: self.set_tool(k), self.viewer, Qt.WidgetWithChildrenShortcut)
        sc("Escape", lambda: self.set_tool("select"), self.viewer, Qt.WidgetWithChildrenShortcut)
        sc("Escape", self._search_escape, self.search, Qt.WidgetShortcut)

    def _search_escape(self):
        self.search.clear()
        self.viewer.setFocus()

    # -- state --------------------------------------------------------------
    def recent(self):
        r = self.settings.value("recent", [])
        if isinstance(r, str):
            r = [r]
        return list(r or [])

    def add_recent(self, path):
        path = str(Path(path).resolve())
        r = [p for p in self.recent() if p != path]
        r.insert(0, path)
        self.settings.setValue("recent", r[:10])
        self.home.refresh_recent()

    def update_state(self):
        has = self.d is not None
        for w in (self.save_btn, self.search):
            w.setEnabled(has)
        for w in (self.tool_group, self.undo_btn, self.redo_btn, self.search, self.prev_btn,
                  self.next_btn, self.page_box, self.page_total, self.zoom_in_btn, self.zoom_out_btn,
                  self.zoom_btn, self.fit_btn, self.status):
            w.setVisible(has)
        self.search_count.setVisible(has)
        for a in self.doc_actions:
            a.setEnabled(has)
        self.undo_btn.setEnabled(has and bool(self.d.undo_stack))
        self.redo_btn.setEnabled(has and bool(self.d.redo_stack))
        if has:
            dot = "  ●" if self.d.dirty else ""
            self.doc_chip.setText(f"{self.d.title}{dot}")
            self.doc_chip.setToolTip(self.d.path or "Not saved yet")
            self.doc_chip.show()
            self.setWindowTitle(f"{'• ' if self.d.dirty else ''}{self.d.title} — {APP}")
            self.page_total.setText(f"/ {len(self.d.doc)}")
            self._on_current(self.viewer.current)
        else:
            self.doc_chip.hide()
            self.setWindowTitle(APP)
            self.page_box.setText("")
            self.page_total.setText("")
            self.status.setText("")
        self.options.set_tool(self.tool, has)

    def _on_current(self, i):
        if not self.d:
            return
        i = max(i, 0)
        self.page_box.setText(str(i + 1))
        r = self.d.doc[i].rect
        self.status.setText(f"{r.width / 72 * 25.4:.0f} × {r.height / 72 * 25.4:.0f} mm")
        if self.sidebar.list.currentRow() != i and len(self.sidebar.selected_rows()) <= 1:
            self.sidebar.select_row(i)

    def _goto_page(self):
        try:
            self.viewer.scroll_to(int(self.page_box.text()) - 1)
        except ValueError:
            pass
        self.viewer.setFocus()

    def set_tool(self, tool):
        self.tool = tool
        self.tool_btns[tool].setChecked(True)
        self.viewer.set_tool_cursor(tool)
        self.options.set_tool(tool, self.d is not None)

    def toggle_theme(self):
        T.name = "light" if T.name == "dark" else "dark"
        self.settings.setValue("theme", T.name)
        T.apply(QApplication.instance())

    def _on_theme(self):
        self.theme_btn.setIcon(T.icon("sun" if T.name == "dark" else "moon"))
        self.search_action.setIcon(T.icon("search"))
        self.options.refresh_theme()
        self.sidebar.list.viewport().update()

    def opt_color(self, tool):
        return hex_to_rgb(self.opts[tool]["color"])

    # -- document lifecycle -------------------------------------------------
    def set_document(self, d):
        old = self.d
        self.d = d
        self.search_reset(update=False)
        if d:
            d.structure_changed.connect(self.on_structure)
            d.pages_changed.connect(self.on_pages)
            d.state_changed.connect(self.update_state)
            self.stack.setCurrentIndex(1)
            self.sidebar.rebuild()
            self.viewer.set_document(d)
            QTimer.singleShot(0, self.viewer.initial_zoom)
            self.viewer.setFocus()
        else:
            self.viewer.set_document(None)
            self.sidebar.rebuild()
            self.stack.setCurrentIndex(0)
            self.home.refresh_recent()
        if old is not None:
            try:
                old.doc.close()
            except Exception:
                pass
            old.deleteLater()
        self.update_state()

    def on_structure(self):
        cur = self.viewer.current
        self.search_reset(update=False)
        self.sidebar.rebuild()
        self.viewer.rebuild(keep_page=cur)
        self.update_state()

    def on_pages(self, pages):
        self.sidebar.refresh(pages)
        self.viewer.refresh(pages)
        if self.search_term:
            self.search_reset()

    def maybe_save(self):
        if not self.d or not self.d.dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"Save changes to “{self.d.title}”?")
        box.setInformativeText("Your changes will be lost if you don't save them.")
        save = box.addButton("Save", QMessageBox.AcceptRole)
        box.addButton("Don't save", QMessageBox.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        if clicked == save:
            return self.save()
        return clicked != cancel

    def open_dialog(self):
        start = str(Path(self.d.path).parent) if self.d and self.d.path else str(Path.home())
        paths, _ = QFileDialog.getOpenFileNames(self, "Open", start, OPEN_FILTER)
        if len(paths) == 1:
            self.open_path(paths[0])
        elif len(paths) > 1:
            self.merge_dialog(paths)

    def open_path(self, path):
        if not self.maybe_save():
            return
        try:
            doc, pw, is_pdf = load_document(path, self)
        except Cancelled:
            return
        except Exception as ex:
            return self.error(f"Couldn't open “{Path(path).name}”", str(ex))
        title = Path(path).name if is_pdf else Path(path).stem + ".pdf"
        self.set_document(Document(doc, str(path) if is_pdf else None, title, pw, dirty=not is_pdf))
        self.add_recent(path)

    def close_document(self):
        if self.maybe_save():
            self.set_document(None)

    def save(self):
        if not self.d:
            return False
        if not self.d.path:
            return self.save_as()
        try:
            self.d.save(self.d.path)
        except Exception as ex:
            self.error("Couldn't save the file", str(ex))
            return False
        self.toast.show_msg("Saved")
        return True

    def _ask_save_path(self, title, suggested):
        start = str(Path(self.d.path).parent) if self.d and self.d.path else str(Path.home())
        path, _ = QFileDialog.getSaveFileName(self, title, str(Path(start) / suggested), "PDF files (*.pdf)")
        if path and not path.lower().endswith(".pdf"):
            path += ".pdf"
        return path

    def save_as(self):
        if not self.d:
            return False
        path = self._ask_save_path("Save as", self.d.title)
        if not path:
            return False
        try:
            self.d.save(path)
        except Exception as ex:
            self.error("Couldn't save the file", str(ex))
            return False
        self.add_recent(path)
        self.toast.show_msg(f"Saved as {Path(path).name}")
        return True

    def undo(self):
        if self.d and self.d.undo():
            self.toast.show_msg("Undone", 1200)

    def redo(self):
        if self.d and self.d.redo():
            self.toast.show_msg("Redone", 1200)

    def error(self, title, detail=""):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(title)
        box.setText(title)
        if detail:
            box.setInformativeText(detail)
        box.exec()

    def about(self):
        QMessageBox.about(self, f"About {APP}",
                          f"<b>{APP} {VERSION}</b><br>A modern PDF editor for Linux.<br><br>"
                          f"Built with Qt (PySide6) and PyMuPDF {fitz.VersionBind}.")

    # -- drag & drop --------------------------------------------------------
    def _drop_paths(self, e):
        out = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p and Path(p).suffix.lower() in OPENABLE:
                out.append(p)
        return out

    def dragEnterEvent(self, e):
        if self._drop_paths(e):
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = self._drop_paths(e)
        if len(paths) == 1:
            if self.d:
                m = QMenu(self)
                a_open = m.addAction(T.icon("open"), "Open this file")
                a_ins = m.addAction(T.icon("plus"), "Insert its pages after the current page")
                chosen = m.exec(self.mapToGlobal(e.position().toPoint()))
                if chosen == a_ins:
                    return self.insert_from_file([paths[0]])
                if chosen != a_open:
                    return
            self.open_path(paths[0])
        elif paths:
            self.merge_dialog(paths)

    def closeEvent(self, e):
        if self.maybe_save():
            e.accept()
        else:
            e.ignore()

    # -- page tools ---------------------------------------------------------
    def page_click(self, i, pos):
        o = self.opts["text"]
        dlg = TextDialog(self, "Add text", None, "", o["size"])
        if not dlg.exec():
            return
        text, size = dlg.values()
        if not text.strip():
            return
        o["size"] = size
        self.options.set_tool(self.tool)
        pt = self.viewer.widget_to_pdf(i, pos)
        fontname, fontfile = pick_font(text)
        with self.d.change([i]) as doc:
            page = doc[i]
            page.insert_text(fitz.Point(pt.x, pt.y + size * 0.85), text, fontsize=size,
                             fontname=fontname, fontfile=fontfile, color=self.opt_color("text"),
                             rotate=page.rotation)

    def page_ink(self, i, pts):
        o = self.opts["draw"]
        pdf = [tuple(self.viewer.widget_to_pdf(i, q)) for q in pts]
        with self.d.change([i]) as doc:
            a = doc[i].add_ink_annot([pdf])
            a.set_border(width=o["size"])
            a.set_colors(stroke=self.opt_color("draw"))
            a.update()

    def page_rect(self, i, qr):
        tiny = qr.width() < 5 and qr.height() < 5
        rect = self.viewer.widget_rect_to_pdf(i, qr)
        t = self.tool
        if t == "select":
            if tiny:
                return
            text = self.d.doc[i].get_textbox(rect).strip()
            if text:
                QGuiApplication.clipboard().setText(text)
                self.toast.show_msg(f"Copied {len(text)} characters")
            else:
                self.toast.show_msg("No text in that area")
        elif t == "edit":
            if tiny:
                return self.toast.show_msg("Drag a box over the text you want to change")
            self.edit_text(i, rect)
        elif t == "highlight":
            self.highlight(i, rect, tiny)
        elif t == "rect":
            if tiny:
                return
            o = self.opts["rect"]
            with self.d.change([i]) as doc:
                a = doc[i].add_rect_annot(rect)
                a.set_border(width=o["size"])
                a.set_colors(stroke=self.opt_color("rect"))
                a.update()
        elif t == "erase":
            if tiny:
                return
            with self.d.change([i]) as doc:
                page = doc[i]
                page.add_redact_annot(rect, fill=(1, 1, 1))
                apply_redactions(page, keep_images=False, keep_graphics=False)
        elif t == "image":
            path, _ = QFileDialog.getOpenFileName(self, "Choose an image", str(Path.home()), IMAGE_FILTER)
            if path:
                self.place_image(i, rect, tiny, path, 220)
        elif t == "sign":
            if not SIG_PATH.exists() and not self.new_signature():
                return
            self.place_image(i, rect, tiny, str(SIG_PATH), 170)

    def place_image(self, i, rect, tiny, path, default_w):
        img = QImage(path)
        if img.isNull():
            return self.error("Couldn't read that image")
        if tiny or rect.width < 8 or rect.height < 8:
            ar = img.height() / max(1, img.width())
            rect = fitz.Rect(rect.x0, rect.y0, rect.x0 + default_w, rect.y0 + default_w * ar)
        with self.d.change([i]) as doc:
            doc[i].insert_image(rect, filename=path, keep_proportion=True)

    def new_signature(self):
        dlg = SignatureDialog(self)
        ok = bool(dlg.exec())
        if ok:
            self.toast.show_msg("Signature saved — click on a page to place it")
        return ok

    def highlight(self, i, rect, tiny):
        page = self.d.doc[i]
        words = page.get_text("words") if not tiny else []
        lines = {}
        for w in words:
            wr = fitz.Rect(w[:4])
            cx, cy = (wr.x0 + wr.x1) / 2, (wr.y0 + wr.y1) / 2
            if not (rect.x0 <= cx <= rect.x1 and rect.y0 <= cy <= rect.y1):
                continue
            key = (w[5], w[6])
            r = fitz.Rect(w[:4])
            lines[key] = lines[key] | r if key in lines else r
        if not lines and tiny:
            return
        with self.d.change([i]) as doc:
            page = doc[i]
            if lines:
                a = page.add_highlight_annot(quads=[r.quad for r in lines.values()])
            else:
                a = page.add_highlight_annot(rect)
            a.set_colors(stroke=self.opt_color("highlight"))
            a.update()

    def edit_text(self, i, rect):
        page = self.d.doc[i]
        info = page.get_text("dict", clip=rect)
        lines = []
        for b in info["blocks"]:
            if b.get("type") != 0:
                continue
            for ln in b["lines"]:
                spans = [s for s in ln["spans"] if s["text"].strip()]
                if spans:
                    lines.append(spans)
        if not lines:
            return self.toast.show_msg("No editable text found there")
        lines.sort(key=lambda sp: (round(sp[0]["origin"][1], 1), sp[0]["origin"][0]))
        spans = [s for sp in lines for s in sp]
        ref = max(spans, key=lambda s: len(s["text"]))
        size = statistics.median(s["size"] for s in spans)
        c = ref["color"]
        color = (((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255)
        fname = ref["font"].lower()
        flags = ref["flags"]
        bold = bool(flags & 16) or any(k in fname for k in ("bold", "black", "heavy", "semibold"))
        italic = bool(flags & 2) or "italic" in fname or "oblique" in fname
        mono = bool(flags & 8) or "mono" in fname or "courier" in fname
        serif = (bool(flags & 4) or any(k in fname for k in ("times", "serif", "georgia", "garamond", "roman"))) \
            and "sans" not in fname
        old = "\n".join("".join(s["text"] for s in sp).strip() for sp in lines)

        dlg = TextDialog(self, "Edit text",
                         "Change the text below. Folio matches the original font style as closely as it can.",
                         old, size, ok="Apply")
        if not dlg.exec():
            return
        new, size = dlg.values()
        if new == old and abs(size - round(statistics.median(s["size"] for s in spans))) < 0.5:
            return
        origins = [fitz.Point(sp[0]["origin"]) for sp in lines]
        lh = (origins[-1].y - origins[0].y) / (len(origins) - 1) if len(origins) > 1 else size * 1.25
        if lh <= 0:
            lh = size * 1.25
        fontname, fontfile = pick_font(new, serif, mono, bold, italic)
        with self.d.change([i]) as doc:
            page = doc[i]
            for sp in lines:
                lr = fitz.Rect(sp[0]["bbox"])
                for s in sp[1:]:
                    lr |= fitz.Rect(s["bbox"])
                lr &= rect
                band = lr.height * 0.25
                page.add_redact_annot(fitz.Rect(lr.x0 + 0.3, lr.y0 + band, lr.x1 - 0.3, lr.y1 - band), fill=False)
            apply_redactions(page)
            for k, txt in enumerate(new.split("\n")):
                if not txt:
                    continue
                if k < len(origins):
                    pt = origins[k]
                else:
                    pt = fitz.Point(origins[0].x, origins[-1].y + (k - len(origins) + 1) * lh)
                page.insert_text(pt, txt, fontsize=size, fontname=fontname, fontfile=fontfile,
                                 color=color, rotate=page.rotation)
        self.toast.show_msg("Text updated")

    def page_context(self, i, pos, gpos):
        page = self.d.doc[i]
        pt = self.viewer.widget_to_pdf(i, pos)
        hit = None
        for a in page.annots() or []:
            if (a.rect + (-3, -3, 3, 3)).contains(pt):
                hit = a.xref
        m = QMenu(self)
        if hit:
            m.addAction(T.icon("trash"), "Delete this annotation", lambda: self._delete_annot(i, hit))
            m.addSeparator()
        m.addAction(T.icon("copy"), "Copy page text", lambda: self._copy_page_text(i))
        m.addSeparator()
        m.addAction(T.icon("rotr"), "Rotate page right", lambda: self.rotate_pages(90, [i]))
        m.addAction(T.icon("rotl"), "Rotate page left", lambda: self.rotate_pages(-90, [i]))
        m.addAction(T.icon("copy"), "Duplicate page", lambda: self.duplicate_page([i]))
        m.addAction(T.icon("trash"), "Delete page", lambda: self.delete_pages([i]))
        m.exec(gpos)

    def _delete_annot(self, i, xref):
        with self.d.change([i]) as doc:
            page = doc[i]
            page.delete_annot(page.load_annot(xref))
        self.toast.show_msg("Annotation deleted")

    def _copy_page_text(self, i):
        QGuiApplication.clipboard().setText(self.d.doc[i].get_text())
        self.toast.show_msg(f"Copied text of page {i + 1}")

    # -- page operations ----------------------------------------------------
    def _targets(self, pages=None):
        if pages:
            return sorted(pages)
        rows = self.sidebar.selected_rows()
        return rows or [max(self.viewer.current, 0)]

    def rotate_pages(self, deg, pages=None):
        if not self.d:
            return
        pages = self._targets(pages)
        with self.d.change(pages) as doc:
            for p in pages:
                pg = doc[p]
                pg.set_rotation((pg.rotation + deg) % 360)

    def delete_pages(self, pages=None):
        if not self.d:
            return
        pages = set(self._targets(pages))
        n = len(self.d.doc)
        if len(pages) >= n:
            return self.error("Can't delete every page", "A PDF needs at least one page.")
        with self.d.change() as doc:
            doc.select([k for k in range(n) if k not in pages])
        self.toast.show_msg(f"Deleted {len(pages)} page{'s' if len(pages) > 1 else ''} — Ctrl+Z to undo")

    def duplicate_page(self, pages=None):
        if not self.d:
            return
        pages = self._targets(pages)
        with self.d.change() as doc:
            src = fitz.open(stream=doc.tobytes(), filetype="pdf")
            if src.needs_pass and self.d.password:
                src.authenticate(self.d.password)
            for k, p in enumerate(pages):
                at = p + k + 1
                doc.insert_pdf(src, from_page=p, to_page=p, start_at=at)

    def insert_blank(self):
        if not self.d:
            return
        cur = max(self.viewer.current, 0)
        r = self.d.doc[cur].rect
        with self.d.change() as doc:
            doc.new_page(pno=cur + 1, width=r.width, height=r.height)
        QTimer.singleShot(50, lambda: self.viewer.scroll_to(cur + 1))

    def insert_from_file(self, paths=None):
        if not self.d:
            return
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(self, "Insert pages from", str(Path.home()), OPEN_FILTER)
        srcs = []
        for p in paths or []:
            try:
                srcs.append(load_document(p, self)[0])
            except Cancelled:
                pass
            except Exception as ex:
                self.error(f"Couldn't open “{Path(p).name}”", str(ex))
        if not srcs:
            return
        at = max(self.viewer.current, 0) + 1
        total = 0
        with self.d.change() as doc:
            for s in srcs:
                doc.insert_pdf(s, start_at=at + total)
                total += len(s)
        self.toast.show_msg(f"Inserted {total} page{'s' if total != 1 else ''}")
        QTimer.singleShot(50, lambda: self.viewer.scroll_to(at))

    def extract_pages(self):
        if not self.d:
            return
        pages = self._targets()
        stem = Path(self.d.title).stem
        label = f"page{pages[0] + 1}" if len(pages) == 1 else f"pages{pages[0] + 1}-{pages[-1] + 1}"
        path = self._ask_save_path("Extract pages", f"{stem}-{label}.pdf")
        if not path:
            return
        out = fitz.open()
        for p in pages:
            out.insert_pdf(self.d.doc, from_page=p, to_page=p)
        out.save(path, garbage=3, deflate=True)
        out.close()
        self.toast.show_msg(f"Saved {len(pages)} page{'s' if len(pages) > 1 else ''} to {Path(path).name}")

    def split_dialog(self):
        if not self.d:
            return
        dlg = SplitDialog(self, len(self.d.doc))
        if not dlg.exec():
            return
        try:
            groups = dlg.groups()
        except ValueError:
            return self.error("Those page ranges don't look right", "Use something like: 1-3, 4, 7-")
        start = str(Path(self.d.path).parent) if self.d.path else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Save the parts to…", start)
        if not folder:
            return
        stem = Path(self.d.title).stem
        width = len(str(len(groups)))
        for k, g in enumerate(groups, 1):
            out = fitz.open()
            for p in g:
                out.insert_pdf(self.d.doc, from_page=p, to_page=p)
            out.save(str(Path(folder) / f"{stem}-part{k:0{width}d}.pdf"), garbage=3, deflate=True)
            out.close()
        self.toast.show_msg(f"Split into {len(groups)} files")

    def merge_dialog(self, paths=()):
        dlg = MergeDialog(self, paths)
        if not dlg.exec():
            return
        files = dlg.paths()
        if not self.maybe_save():
            return
        out = fitz.open()
        for p in files:
            try:
                src = load_document(p, self)[0]
            except Cancelled:
                continue
            except Exception as ex:
                self.error(f"Skipped “{Path(p).name}”", str(ex))
                continue
            out.insert_pdf(src)
            src.close()
        if len(out) == 0:
            return
        data = out.tobytes(garbage=3, deflate=True)
        out.close()
        doc = fitz.open(stream=data, filetype="pdf")
        self.set_document(Document(doc, None, "Merged.pdf", dirty=True))
        self.toast.show_msg(f"Merged {len(files)} files — press Save to keep it")

    def compress(self):
        if not self.d:
            return
        path = self._ask_save_path("Save compressed copy", f"{Path(self.d.title).stem}-compressed.pdf")
        if not path:
            return
        before = len(self.d.doc.tobytes())
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            tmp = fitz.open(stream=self.d.doc.tobytes(), filetype="pdf")
            if tmp.needs_pass and self.d.password:
                tmp.authenticate(self.d.password)
            if hasattr(tmp, "rewrite_images"):
                try:
                    tmp.rewrite_images(dpi_threshold=180, dpi_target=150, quality=70)
                except Exception:
                    pass
            tmp.save(path, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)
            tmp.close()
        except Exception as ex:
            QApplication.restoreOverrideCursor()
            return self.error("Compression failed", str(ex))
        QApplication.restoreOverrideCursor()
        after = os.path.getsize(path)
        pct = max(0, 100 - after * 100 / max(1, before))
        self.toast.show_msg(f"{human_size(before)} → {human_size(after)}  ({pct:.0f}% smaller)", 4000)

    def protect(self):
        if not self.d:
            return
        dlg = PasswordDialog(self)
        if not dlg.exec():
            return
        path = self._ask_save_path("Save protected copy", f"{Path(self.d.title).stem}-protected.pdf")
        if not path:
            return
        pw = dlg.pw1.text()
        try:
            self.d.doc.save(path, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_AES_256,
                            owner_pw=pw, user_pw=pw)
        except Exception as ex:
            return self.error("Couldn't save the protected copy", str(ex))
        self.toast.show_msg(f"Protected copy saved: {Path(path).name}")

    def print_doc(self):
        if not self.d:
            return
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(self.d.title)
        dlg = QPrintDialog(printer, self)
        dlg.setMinMax(1, len(self.d.doc))
        if dlg.exec() != QDialog.Accepted:
            return
        first, last = printer.fromPage(), printer.toPage()
        if first == 0:
            first, last = 1, len(self.d.doc)
        painter = QPainter(printer)
        dpi = min(printer.resolution(), 300)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for k, i in enumerate(range(first - 1, last)):
                if k:
                    printer.newPage()
                z = dpi / 72
                pix = self.d.doc[i].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
                area = painter.viewport()
                s = min(area.width() / img.width(), area.height() / img.height())
                w, h = img.width() * s, img.height() * s
                painter.drawImage(QRectF((area.width() - w) / 2, (area.height() - h) / 2, w, h), img)
        finally:
            painter.end()
            QApplication.restoreOverrideCursor()
        self.toast.show_msg("Sent to printer")

    # -- search -------------------------------------------------------------
    def search_reset(self, update=True):
        self.search_term = ""
        self.hits = []
        self.hit_pos = -1
        self.viewer.search_hits = {}
        self.viewer.active_hit = None
        self.search_count.setText("")
        if update:
            self.viewer.update_pages()

    def find_next(self, backwards=False):
        if not self.d:
            return
        term = self.search.text().strip()
        if not term:
            return
        if term != self.search_term:
            self.search_reset(update=False)
            self.search_term = term
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for i, page in enumerate(self.d.doc):
                rs = page.search_for(term)
                if rs:
                    self.viewer.search_hits[i] = rs
                    self.hits += [(i, k) for k in range(len(rs))]
            QApplication.restoreOverrideCursor()
            if not self.hits:
                self.search_count.setText("0")
                self.toast.show_msg(f"No results for “{term}”")
                return
            cur = max(self.viewer.current, 0)
            self.hit_pos = next((k for k, (p, _) in enumerate(self.hits) if p >= cur), 0)
        else:
            if not self.hits:
                return
            self.hit_pos = (self.hit_pos + (-1 if backwards else 1)) % len(self.hits)
        i, k = self.hits[self.hit_pos]
        self.viewer.active_hit = (i, k)
        self.viewer.update_pages()
        self.viewer.scroll_to_rect(i, self.viewer.search_hits[i][k])
        self.search_count.setText(f"{self.hit_pos + 1}/{len(self.hits)}")


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setOrganizationName(APP)
    app.setDesktopFileName("folio")
    app.setStyle("Fusion")
    font = QFont()
    font.setFamilies(["Inter", "Cantarell", "Ubuntu", "Noto Sans", "DejaVu Sans"])
    font.setPointSizeF(10)
    app.setFont(font)
    settings = QSettings("Folio", "Folio")
    T.name = settings.value("theme", "dark") if settings.value("theme", "dark") in THEMES else "dark"
    T.apply(app)
    win = MainWindow()
    win._on_theme()
    win.show()
    files = [a for a in sys.argv[1:] if Path(a).exists()]
    if len(files) == 1:
        QTimer.singleShot(0, lambda: win.open_path(files[0]))
    elif len(files) > 1:
        QTimer.singleShot(0, lambda: win.merge_dialog(files))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
