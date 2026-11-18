# Changelog

## 1.1.0 – tabs
- **Tabs**: every PDF opens in its own tab in the same window. Drag tabs to reorder, × or Ctrl+W to close,
  Ctrl+Tab / Ctrl+Shift+Tab (or Ctrl+PgDn / Ctrl+PgUp) to switch, **+** to open another PDF.
- Opening a PDF while Folio is already running (double-click in Files, *Open With*, or `folio file.pdf`)
  now adds a tab to the open window instead of starting a second window. `folio --new-window` still opens a separate one.
- Each tab remembers its own zoom, page and undo history; a file that is already open just switches to its tab.
- Opening several files at once opens them as tabs. Dropping several files offers *Open in new tabs*,
  *Merge into one PDF* or *Insert pages*.
- When closing the window, Folio asks about every tab with unsaved changes.

## 1.0.0 – first release
- Open PDFs (and images, XPS, EPUB, which are converted to PDF), page thumbnails, zoom, fit width/page, search.
- **Edit text**: rewrite existing text in place, matching size, colour and font style.
- Annotate: add text, highlight, freehand drawing, rectangles, images; delete annotations with right-click.
- Signature: draw once, saved for next time, placed with one click.
- Erase an area permanently.
- Pages: drag to reorder, rotate, delete, duplicate, insert blank pages or pages from other files.
- Merge, split, extract pages, compress, password-protect (AES-256), print.
- Dark and light themes, undo/redo, drag & drop, recent files.
- `.deb` package for Zorin OS 18 / Ubuntu 24.04.
