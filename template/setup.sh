#!/usr/bin/env bash
# Prepares a fresh copy of the template: fonts, Python packages, and a check of the tools the build needs.
set -euo pipefail
cd "$(dirname "$0")"
npm install --silent --no-audit --no-fund
python3 -c "import numpy, scipy, PIL, cv2, onnxruntime" 2>/dev/null || pip install -q numpy scipy pillow opencv-python-headless onnxruntime
# Transcription is only needed for a recorded voice-over or a host clip (a generated voice brings its own word times)
python3 -c "import faster_whisper" 2>/dev/null || pip install -q faster-whisper || echo "faster-whisper not installed: word timing of recordings will not work"
command -v ffmpeg >/dev/null || { echo "ffmpeg is missing"; exit 1; }
node -e "require('playwright')" 2>/dev/null || { echo "Playwright is missing: npm i -g playwright && npx playwright install chromium"; exit 1; }
echo "ready"
