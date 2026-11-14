# Generates the narration with ElevenLabs and keeps the word times that come back with it, so the reel can be
# timed to the voice without transcribing it.
# Usage: voice.py voices [part of a name]     the voices of the account: id, name, kind
#        voice.py models                      the models that can speak
#        voice.py say <episode.json> [out.mp3]   speak every narrated line (default out: assets/voice/narration.mp3)
# The episode's "voice" block chooses the voice: {"id": "...", "model": "...", "stability": 0.5, "similarity": 0.75,
# "speed": 1.0}. A beat may carry "tts": the text to speak when it should differ from the caption (numbers
# spelled out, diacritics for a word that is read wrong).
# The key: saved on the cloud environment for api.elevenlabs.io (the network proxy adds it), or ELEVENLABS_API_KEY.
import base64, json, os, subprocess, sys

API = 'https://api.elevenlabs.io'
KEY = os.environ.get('ELEVENLABS_API_KEY', 'set-by-proxy')


def call(method, path, body=None):
    cmd = ['curl', '-sS', '-m', '300', '-X', method, '-H', f'xi-api-key: {KEY}', '-H', 'Content-Type: application/json', '-w', '\n%{http_code}', API + path]
    if body is not None:
        cmd += ['--data-binary', json.dumps(body, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    text, _, code = out.rpartition('\n')
    if code != '200':
        hint = ' (no key is reaching ElevenLabs: save one for api.elevenlabs.io or set ELEVENLABS_API_KEY)' if code in ('401', '403') else ''
        raise SystemExit(f'ElevenLabs answered {code}{hint}: {text[:400]}')
    return json.loads(text)


if sys.argv[1] == 'voices':
    want = sys.argv[2].lower() if len(sys.argv) > 2 else ''
    for v in call('GET', '/v1/voices')['voices']:
        if want in v['name'].lower():
            print(v['voice_id'], '|', v['name'], '|', v.get('category'), '|', ', '.join(f'{k}: {x}' for k, x in (v.get('labels') or {}).items()))
elif sys.argv[1] == 'models':
    for m in call('GET', '/v1/models'):
        if m.get('can_do_text_to_speech'):
            print(m['model_id'], '|', m['name'], '|', ', '.join(l['language_id'] for l in m.get('languages', []))[:80])
elif sys.argv[1] == 'say':
    ep = json.load(open(sys.argv[2], encoding='utf-8')); out = sys.argv[3] if len(sys.argv) > 3 else 'assets/voice/narration.mp3'
    v = ep.get('voice') or {}
    if not v.get('id'):
        raise SystemExit('episode.json has no "voice": {"id": ...}. List the voices with: voice.py voices')
    # One request for the whole narration, so the voice keeps one tone from the first line to the last
    lines = [b.get('tts') or b['say'] for b in ep['beats'] if 'say' in b and 'clip' not in b]
    body = {'text': '\n\n'.join(lines), 'voice_settings': {'stability': v.get('stability', .5), 'similarity_boost': v.get('similarity', .75), 'speed': v.get('speed', 1.0)}}
    if v.get('model'):
        body['model_id'] = v['model']
    got = call('POST', f"/v1/text-to-speech/{v['id']}/with-timestamps?output_format=mp3_44100_128", body)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(base64.b64decode(got['audio_base64']))
    # Characters with times -> words with times, saved beside the audio for tools/align.py
    al = got.get('alignment') or got['normalized_alignment']; words = []; cur = None
    for ch, a, b in zip(al['characters'], al['character_start_times_seconds'], al['character_end_times_seconds']):
        if ch.isspace():
            cur = None; continue
        if cur is None:
            cur = {'w': '', 'a': round(a, 3), 'b': round(b, 3)}; words.append(cur)
        cur['w'] += ch; cur['b'] = round(b, 3)
    json.dump(words, open(os.path.splitext(out)[0] + '.words.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{out}: {len(lines)} lines, {len(words)} words, {words[-1]["b"]:.1f}s, {len(body["text"])} characters spoken')
else:
    raise SystemExit(__doc__ or 'usage: voice.py voices|models|say')
