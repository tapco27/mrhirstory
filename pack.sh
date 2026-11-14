#!/usr/bin/env bash
# Packs this repository as mr-history.skill, the file Claude installs with its "Save skill" button.
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import os, zipfile
skip_dirs = {'node_modules', 'build', 'out', 'hd', '__pycache__'}
skip_files = {'depth_small.onnx', 'timeline.js', 'wall.png', 'leaf_l.jpg', 'leaf_r.jpg', 'door.js'}
with zipfile.ZipFile('mr-history.skill', 'w', zipfile.ZIP_DEFLATED) as z:
    z.write('SKILL.md', 'mr-history/SKILL.md')
    for top in ('references', 'template'):
        for root, dirs, files in os.walk(top):
            dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
            for f in sorted(files):
                if f not in skip_files:
                    z.write(os.path.join(root, f), 'mr-history/' + os.path.join(root, f))
print('mr-history.skill written')
PY
