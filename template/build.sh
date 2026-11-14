#!/usr/bin/env bash
# Builds the reel from episode.json. Usage: [VOICE=voice-over.mp3] ./build.sh [output.mp4]
#   The host's clips in assets/clips carry their own sound. The narration is VOICE, or assets/voice/narration.mp3
#   when it exists; without one the narrated lines are timed by an estimate and stay silent (a draft to review).
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-out/reel.mp4}"
VOICE="${VOICE:-}"; [ -z "$VOICE" ] && [ -f assets/voice/narration.mp3 ] && VOICE=assets/voice/narration.mp3
mkdir -p out build

# The gate (drawn once), word times from the clips and the narration, then the timeline
[ -f assets/door/wall.png ] || python3 tools/portal.py assets/door/wood.jpg assets/door
python3 tools/align.py episode.json assets/clips build/words.json $VOICE
python3 tools/plan.py episode.json src/timeline.js build/words.json
# Pictures with a camera move get upscaled and a depth map; then every moving shot is cut into 9:16 frames
python3 tools/enhance.py models assets/hd assets/raw src/timeline.js
python3 tools/plates.py src/timeline.js assets/raw assets/clips assets/hd build/plates

# Score (the episode's own track from assets/music, or the synthesized one) and effects, speech on top,
# then master to -14 LUFS with a peak limiter
python3 tools/music.py src/timeline.js build/music.wav build/sfx.wav assets/sfx
python3 tools/mix.py src/timeline.js assets/clips assets/music build/music.wav build/sfx.wav build/mix.wav $VOICE
I=$(ffmpeg -hide_banner -nostats -i build/mix.wav -af ebur128 -f null - 2>&1 | awk '/I:/{v=$2} END{print v}')
G=$(python3 -c "print(round(-14-($I),2))")
ffmpeg -hide_banner -loglevel error -y -i build/mix.wav -af "volume=${G}dB,alimiter=limit=0.84:attack=4:release=80:level=false" build/master.wav
echo "master gain ${G} dB"

# Frames (4 parallel workers), then encode
rm -rf build/frames
for w in 0 1 2 3; do node src/render.mjs reel.html build/frames "$w" 4 & done
wait
FPS=$(python3 -c "import json,re;print(json.loads(re.sub(r'^[^{]*','',open('src/timeline.js',encoding='utf-8').read()).strip().rstrip(';'))['fps'])")
ffmpeg -hide_banner -loglevel error -y -framerate "$FPS" -i build/frames/f_%05d.jpg -i build/master.wav \
  -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
