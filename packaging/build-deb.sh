#!/usr/bin/env bash
# Builds dist/Folio_<version>_amd64.deb — a self-contained package (Python, Qt and
# PyMuPDF are bundled), so it installs on Zorin OS 18 / Ubuntu 24.04 without pip.
#
# Needs: python3 (3.10+), python3-venv, dpkg-deb
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' folio.py)
ARCH=amd64
BUILD="$ROOT/build"
PKG="$BUILD/pkg"
echo "Building Folio $VERSION"

rm -rf "$BUILD" "$ROOT/dist"
mkdir -p "$BUILD" "$ROOT/dist"

# 1. Bundle the app with PyInstaller in a clean virtual environment
python3 -m venv "$BUILD/venv"
"$BUILD/venv/bin/pip" install -q --upgrade pip
"$BUILD/venv/bin/pip" install -q -r requirements.txt pyinstaller
"$BUILD/venv/bin/pyinstaller" --noconfirm --clean --windowed --name folio \
    --distpath "$BUILD/app" --workpath "$BUILD/work" --specpath "$BUILD" \
    --exclude-module tkinter \
    --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtQml \
    --exclude-module PySide6.QtQuick --exclude-module PySide6.QtWebEngineCore \
    --exclude-module PySide6.QtMultimedia --exclude-module PySide6.Qt3DCore \
    folio.py

# 2. Lay out the package
mkdir -p "$PKG/DEBIAN" "$PKG/opt" "$PKG/usr/bin" "$PKG/usr/share/applications" \
         "$PKG/usr/share/icons/hicolor/scalable/apps" "$PKG/usr/share/icons/hicolor/256x256/apps" \
         "$PKG/usr/share/doc/folio"
cp -a "$BUILD/app/folio" "$PKG/opt/folio"
ln -s /opt/folio/folio "$PKG/usr/bin/folio"
install -m 644 packaging/folio.desktop "$PKG/usr/share/applications/folio.desktop"
install -m 644 branding/folio-icon.svg "$PKG/usr/share/icons/hicolor/scalable/apps/folio.svg"
install -m 644 branding/folio-icon-256.png "$PKG/usr/share/icons/hicolor/256x256/apps/folio.png"
install -m 644 LICENSE "$PKG/usr/share/doc/folio/copyright"

SIZE=$(du -sk "$PKG" | cut -f1)
cat > "$PKG/DEBIAN/control" <<EOF
Package: folio
Version: $VERSION
Architecture: $ARCH
Maintainer: Solomon A. <solomwn@users.noreply.github.com>
Installed-Size: $SIZE
Depends: libc6 (>= 2.39), libegl1, libgl1, libfontconfig1, libfreetype6, libdbus-1-3, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-render-util0, libxcb-image0, libxcb-randr0, libxcb-xinerama0, libxcb-xkb1, libx11-xcb1, libwayland-client0, libwayland-cursor0, libwayland-egl1
Recommends: fonts-dejavu-core
Section: graphics
Priority: optional
Homepage: https://github.com/solomwn/folio
Description: Modern PDF editor for Linux
 Folio opens, edits, annotates, signs, merges, splits and reorganises
 PDF documents, with a clean dark/light interface built for Zorin OS.
EOF

cat > "$PKG/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
exit 0
EOF
cp "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"
chmod 755 "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"

OUT="$ROOT/dist/Folio_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group --build -Zxz "$PKG" "$OUT"
echo "Built $OUT ($(du -h "$OUT" | cut -f1))"
