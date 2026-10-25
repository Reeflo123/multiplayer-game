import sys, re, json, subprocess, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
from scripts import VIDEOS
k = Kokoro('kokoro.onnx', 'voices.bin')
SR = 44100

def clean(line): return line.lstrip('#').replace('*', '')

def phrase_split(text):
    parts = re.split(r'(?<=[.,!?…])\s+', text.strip())
    return [p for p in parts if p]

def chunks_by_silence(a, sr):
    env = np.convolve(np.abs(a), np.ones(int(sr*0.02))/int(sr*0.02), 'same')
    voiced = env > 0.012
    segs, inside, start, last_v = [], False, 0, 0
    gap = int(sr*0.13)
    for i in np.where(np.diff(voiced.astype(int)) != 0)[0]:
        pass
    idx = np.where(voiced)[0]
    if len(idx) == 0: return [(0, len(a)/sr)]
    s = idx[0]; prev = idx[0]
    for j in idx[1:]:
        if j - prev > gap:
            segs.append((s/sr, prev/sr)); s = j
        prev = j
    segs.append((s/sr, prev/sr))
    return segs

def word_times(line, a, sr):
    words_raw = line.lstrip('#').split()
    phrases = phrase_split(clean(line))
    segs = chunks_by_silence(a, sr)
    # merge segments down to number of phrases (merge smallest gaps first)
    while len(segs) > len(phrases):
        gaps = [segs[i+1][0]-segs[i][1] for i in range(len(segs)-1)]
        g = int(np.argmin(gaps)); segs[g:g+2] = [(segs[g][0], segs[g+1][1])]
    if len(segs) < len(phrases):  # fall back to one span
        segs = [(segs[0][0], segs[-1][1])]; phrases = [clean(line)]
    out, wi = [], 0
    for (s0, s1), ph in zip(segs, phrases):
        n = len(ph.split()); ws = words_raw[wi:wi+n]; wi += n
        wts = [len(re.sub(r'[^A-Za-z0-9]', '', w)) + 2 for w in ws]
        t = s0; tot = sum(wts)
        for w, wt in zip(ws, wts):
            d = (s1 - s0) * wt / tot
            out.append((w, t, t + d)); t += d
    return out

ONLY = sys.argv[1:]
for vid, spec in VIDEOS.items():
    if ONLY and vid not in ONLY: continue
    SPD = 0.9 if spec['theme'] == 'dawn' else 0.97; GAP = 0.5 if spec['theme'] == 'dawn' else 0.32
    t = 0.35; timeline = []; voice = []
    for i, line in enumerate(spec['lines']):
        if i and line.startswith('#'): t += 0.55
        a, sr = k.create(clean(line), voice='am_onyx', speed=SPD, lang='en-us')
        nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0]-300): nz[-1]+1200]
        sf.write('tmp.wav', a, sr)
        r = 2 ** (-1.2/12)
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i','tmp.wav','-af',
            f'asetrate={int(sr*r)},aresample={SR},atempo={1/r:.5f},bass=g=5:f=100,'
            'equalizer=f=2800:t=q:w=1:g=3,highpass=f=45,acompressor=threshold=0.1:ratio=4:attack=4:release=100',
            '-ar', str(SR), '-ac', '1', f'out/{vid}_{i:02d}.wav'], check=True)
        b, _ = sf.read(f'out/{vid}_{i:02d}.wav')
        words = word_times(line, b, SR)
        timeline.append({'line': line, 'start': t, 'dur': len(b)/SR, 'hit': line.startswith('#'),
                         'words': [(w, t+s, t+e) for w, s, e in words]})
        voice.append((t, f'out/{vid}_{i:02d}.wav'))
        t += len(b)/SR + GAP
    json.dump({'timeline': timeline, 'voice': voice, 'speech_end': t}, open(f'out/{vid}.json', 'w'), indent=1)
    print(vid, 'speech ends', round(t, 1))
