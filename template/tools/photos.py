# Finds and fetches pictures that are free to use commercially without credit (CC0 or Public Domain Mark),
# through Openverse, and keeps the record of where each one came from.
# Usage: photos.py search "<words>" [count]    candidates: id, size, licence, source, title
#        photos.py get <id>=<name> [...]       download to assets/raw/<name>.jpg and record its source
#        photos.py sheet [name prefix]         contact sheet of assets/raw -> build/look/photos.jpg
#        photos.py sources                     write SOURCES.md for the pictures episode.json uses
import csv, glob, json, os, subprocess, sys, time

RAW, CACHE, LEDGER = 'assets/raw', 'build/ov', 'assets/raw/photo_sources.tsv'
AGENT = 'reel-template/1.0 (asset fetch)'


def curl(url, out, extra=()):
    return subprocess.run(['curl', '-sS', '-m', '90', '-f', '-L', '-A', AGENT, '-o', out, *extra, url], capture_output=True).returncode == 0


if sys.argv[1] == 'search':
    q = sys.argv[2]; n = sys.argv[3] if len(sys.argv) > 3 else '20'
    os.makedirs(CACHE, exist_ok=True); path = os.path.join(CACHE, q.replace(' ', '_') + '.json')
    for attempt in range(4):                               # the public API often answers 504 on the first try
        if curl('https://api.openverse.org/v1/images/', path, ['-G', '--data-urlencode', f'q={q}', '--data-urlencode', 'license=cc0,pdm', '--data-urlencode', f'page_size={n}']):
            break
        time.sleep(8)
    else:
        raise SystemExit('Openverse did not answer; try again in a minute')
    index = json.load(open(CACHE + '/index.json')) if os.path.exists(CACHE + '/index.json') else {}
    for r in json.load(open(path)).get('results', []):
        index[r['id'][:8]] = {k: r.get(k) for k in ('url', 'license', 'creator', 'foreign_landing_url', 'title', 'width', 'height', 'source')}
        print(r['id'][:8], f"{r.get('width')}x{r.get('height')}", r.get('license'), r.get('source'), '|', (r.get('title') or '')[:80])
    json.dump(index, open(CACHE + '/index.json', 'w'), ensure_ascii=False)
elif sys.argv[1] == 'get':
    index = json.load(open(CACHE + '/index.json')); os.makedirs(RAW, exist_ok=True)
    rows = open(LEDGER, encoding='utf-8').read().splitlines() if os.path.exists(LEDGER) else []
    for pair in sys.argv[2:]:
        key, name = pair.split('='); r = index[key]; url = r['url']; wiki = 'upload.wikimedia.org' in url and '/commons/' in url
        if wiki:                                           # ask Wikimedia for a 1920 px rendering instead of the huge original
            head, tail = url.split('/commons/'); url = f"{head}/commons/thumb/{tail}/{1920 if (r.get('width') or 1920) >= 1920 else 960}px-{tail.split('/')[-1]}"
        ok = curl(url, f'{RAW}/{name}.jpg') or (wiki and (time.sleep(6) or curl(url, f'{RAW}/{name}.jpg')))
        print(name, 'ok' if ok else 'FAILED', r.get('source'), r.get('license'))
        if ok:
            rows = [x for x in rows if not x.startswith(name + '.jpg\t')] + [f"{name}.jpg\t{r['license']}\t{r.get('creator')}\t{r.get('foreign_landing_url')}\t{r.get('title')}"]
        time.sleep(3 if wiki else .5)                      # Wikimedia refuses bursts
    open(LEDGER, 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
elif sys.argv[1] == 'sheet':
    from PIL import Image, ImageDraw
    tiles = []
    for f in sorted(glob.glob(f"{RAW}/{sys.argv[2] if len(sys.argv) > 2 else ''}*.jpg")):
        im = Image.open(f).convert('RGB'); label = f'{os.path.basename(f)[:-4]} {im.size[0]}x{im.size[1]}'
        im.thumbnail((330, 330)); t = Image.new('RGB', (340, 360), '#222'); t.paste(im, (5, 5)); ImageDraw.Draw(t).text((6, 342), label, fill='#0f0'); tiles.append(t)
    cols = 7; sheet = Image.new('RGB', (cols * 340, ((len(tiles) + cols - 1) // cols) * 360), '#222')
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * 340, (k // cols) * 360))
    os.makedirs('build/look', exist_ok=True); sheet.save('build/look/photos.jpg', quality=85); print(len(tiles), 'pictures -> build/look/photos.jpg')
elif sys.argv[1] == 'sources':
    ep = json.load(open('episode.json', encoding='utf-8'))
    used = sorted({s['photo'] for b in ep['beats'] for s in b.get('shots', []) if 'photo' in s})
    rows = {r[0][:-4]: r for r in csv.reader(open(LEDGER, encoding='utf-8'), delimiter='\t') if r} if os.path.exists(LEDGER) else {}
    out = ['# Sources', '', 'Pictures found through Openverse are CC0 or Public Domain Mark: free for commercial use, no credit required.', '', '## Pictures', '']
    out += [f"- `{u}.jpg` — {rows[u][1].upper()} — {rows[u][2]} — {rows[u][3]}" if u in rows else f"- `{u}.jpg` — supplied by the account owner or generated for this episode" for u in used]
    door = [r for r in csv.reader(open('assets/door/sources.tsv', encoding='utf-8'), delimiter='\t') if r] if os.path.exists('assets/door/sources.tsv') else []
    out += ['', '## The gate', '', 'Drawn by `tools/portal.py`.'] + [f"Its door leaves use `assets/door/{r[0]}` — {r[1].upper()} — {r[2]} — {r[3]}" for r in door]
    out += ['', '## Sound', '', f"- Score: {'`assets/music/' + ep['music'] + '` (supplied by the account owner)' if ep.get('music') else 'synthesized by `tools/music.py`'}.",
            '- Effects: CC0 recordings in `assets/sfx` (see its `ledger.json`) and sounds synthesized by `tools/music.py`.', '']
    open('SOURCES.md', 'w', encoding='utf-8').write('\n'.join(out)); print(len(used), 'pictures listed;', len([u for u in used if u not in rows]), 'without a recorded source')
else:
    raise SystemExit('usage: photos.py search|get|sheet|sources')
