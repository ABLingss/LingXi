#!/bin/bash
# build.sh — PyInstaller build script for Stock JSON Clipper V1.0
#
# Produces single-file executables for the current platform.
#
# Usage:
#   bash build.sh              # Build for current OS
#   bash build.sh clean        # Clean build artifacts
#
# Output per platform:
#   Windows: dist/StockJSONClipper.exe
#   Linux:   dist/StockJSONClipper
#   macOS:   dist/StockJSONClipper

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
NAME="StockJSONClipper"
ENTRY="main.py"

echo "============================================"
echo " Building Stock JSON Clipper V1.0"
echo " Platform: $(uname -s)"
echo "============================================"
echo ""

cd "$PROJECT_DIR"

if [ "${1:-}" = "clean" ]; then
    echo "Cleaning build artifacts..."
    rm -rf build dist *.spec
    echo "Done."
    exit 0
fi

# Clean previous builds
rm -rf build dist *.spec

echo "[1/3] Checking Python..."
PYTHON=$(which python3.9 2>/dev/null || which python3 2>/dev/null)
echo "  Using: $PYTHON"
$PYTHON --version

echo ""
echo "[2/3] Running PyInstaller..."
echo "  This produces a single-file executable (~10-15MB)."
echo ""

# Platform-specific settings
HIDDEN_IMPORTS="--hidden-import pystray._win32 --hidden-import pystray._xorg --hidden-import pystray._darwin"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import PIL.Image --hidden-import PIL.ImageDraw"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import webview.platforms.cef"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import webview.platforms.gtk"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import webview.platforms.cocoa"
HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import webview.platforms.winforms"

EXCLUDE="--exclude-module numpy --exclude-module pandas --exclude-module matplotlib --exclude-module scipy --exclude-module tkinter"

if [ "$(uname -s)" = "Linux" ]; then
    echo "  Target: Linux"
    CONSOLE_FLAG="--noconsole"  # Linux ignores this, but include for consistency
elif [ "$(uname -s)" = "Darwin" ]; then
    echo "  Target: macOS"
    CONSOLE_FLAG="--windowed"
    # macOS bundles need special handling for pystray
    HIDDEN_IMPORTS="$HIDDEN_IMPORTS --hidden-import Foundation --hidden-import AppKit --hidden-import objc"
else
    # Windows (MINGW/Cygwin) or native Windows
    echo "  Target: Windows"
    CONSOLE_FLAG="--noconsole"
fi

$PYTHON -m PyInstaller \
    --onefile \
    $CONSOLE_FLAG \
    --name "$NAME" \
    --clean \
    $HIDDEN_IMPORTS \
    $EXCLUDE \
    "$ENTRY"

echo ""
echo "[3/3] Checking output..."
echo ""

if [ -f "dist/${NAME}" ]; then
    SIZE=$(du -h "dist/${NAME}" | cut -f1)
    echo "✅ Linux executable: dist/${NAME} (${SIZE})"
elif [ -f "dist/${NAME}.exe" ]; then
    SIZE=$(du -h "dist/${NAME}.exe" | cut -f1)
    echo "✅ Windows executable: dist/${NAME}.exe (${SIZE})"
elif [ -d "dist/${NAME}.app" ]; then
    SIZE=$(du -sh "dist/${NAME}.app" | cut -f1)
    echo "✅ macOS bundle: dist/${NAME}.app (${SIZE})"
else
    echo "❌ Build failed: no executable found in dist/"
    echo "Contents of dist/:"
    ls -la dist/ 2>/dev/null || echo "  (empty)"
    exit 1
fi

echo ""
echo "============================================"
echo " Build complete!"
echo ""
echo " Release checklist:"
echo "  [ ] Test on target platform"
echo "  [ ] Verify clipboard monitoring works"
echo "  [ ] Verify #save mode creates files"
echo "  [ ] Verify panel opens from tray"
echo "============================================"
