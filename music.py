import sys, json, numpy as np, soundfile as sf
from scripts import VIDEOS
THEME_STYLE = {"gold": "money", "dawn": "life", "steel": "year"}
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.ndimage import uniform_filter1d

SR = 44100
def hz(m): return 440 * 2 ** ((m - 69) / 12)

STYLE = {
    "money": dict(bpm=96, chords=[[48, 51, 55, 60], [44, 48, 51, 56], [51, 55, 58, 63], [46, 50, 53, 58]], roots=[36, 32, 39, 34], kit="trap", drums_line=2),
    "life":  dict(bpm=76, chords=[[48, 52, 55, 60], [43, 50, 55, 59], [45, 48, 52, 57], [41, 45, 48, 53]], roots=[36, 31, 33, 29], kit="soft", drums_line=6),
    "year":  dict(bpm=110, chords=[[50, 53, 57, 62], [46, 50, 53, 58], [41, 45, 48, 53], [48, 52, 55, 60]], roots=[38, 34, 29, 36], kit="drive", drums_line=1),
}

def build(vid):
    st = STYLE[THEME_STYLE[VIDEOS[vid]["theme"]]]; rng = np.random.default_rng(sum(map(ord, vid)) % 1000)
    d = json.load(open(f"out/{vid}.json")); tl = d["timeline"]
    end_start = d["speech_end"] + 0.25; DUR = end_start + 4.6
    N = int(DUR * SR); t = np.arange(N) / SR
    beat = 60 / st["bpm"]; bar = beat * 4
    hits = [L["start"] for L in tl if L["hit"]]
    drums_on = tl[st["drums_line"]]["start"]
    L = np.zeros(N); R = np.zeros(N)

    def add(sig, start, gain=1.0, pan=0.0):
        a = int(start * SR)
        if a >= N or a + len(sig) <= 0: return
        if a < 0: sig = sig[-a:]; a = 0
        b = min(N, a + len(sig)); s = sig[:b - a] * gain
        L[a:b] += s * (1 - max(0, pan)); R[a:b] += s * (1 + min(0, pan))

    # --- pad (chord per bar, saw-ish additive, filtered)
    for bi in range(int(DUR / bar) + 1):
        c = st["chords"][bi % 4]; s0 = bi * bar
        n = int((bar + 1.5) * SR); x = np.arange(n) / SR
        env = np.clip(x / 0.6, 0, 1) * np.clip((bar + 1.5 - x) / 1.5, 0, 1)
        sig = np.zeros(n)
        for m in c:
            for k in range(1, 7):
                for dt in (-.003, .003):
                    sig += np.sin(2 * np.pi * hz(m) * k * (1 + dt) * x + rng.uniform(0, 6)) / k ** 1.4
        add(sig * env, s0, 0.018)
        # bass
        r = st["roots"][bi % 4]
        if st["kit"] in ("trap", "drive"):
            step = beat / 2
            for k in range(8):
                ts = s0 + k * step
                if ts < 0.3: continue
                nn = int(step * SR); xx = np.arange(nn) / SR
                sg = (np.sin(2 * np.pi * hz(r) * xx) + .4 * np.sin(2 * np.pi * hz(r) * 2 * xx)) * np.exp(-xx * 7)
                add(sg, ts, 0.16 if ts > drums_on else 0.08)
        else:
            nn = int(bar * SR); xx = np.arange(nn) / SR
            add(np.sin(2 * np.pi * hz(r - 12) * xx) * np.clip(xx / .3, 0, 1) * np.clip((bar - xx) / .5, 0, 1), s0, 0.22 if s0 > drums_on else 0.1)
        # piano / pluck arps
        notes = [c[0] + 12, c[2] + 12, c[1] + 24, c[3] + 12] * 2
        stepp = beat / 2
        for k, m in enumerate(notes):
            ts = s0 + k * stepp
            nn = int(1.6 * SR); xx = np.arange(nn) / SR; f = hz(m)
            sg = (np.sin(2 * np.pi * f * xx) + .35 * np.sin(4 * np.pi * f * xx) * np.exp(-xx * 5)) * np.exp(-xx * 3.2) * np.clip(xx / .003, 0, 1)
            add(sg, ts, 0.06 if st["kit"] == "soft" else 0.035, pan=(-.3 if k % 2 else .3))

    # --- drums
    def kick():
        n = int(.45 * SR); x = np.arange(n) / SR
        f = 48 + 110 * np.exp(-x * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * (5 if st["kit"] == "trap" else 9))
    def snare():
        n = int(.3 * SR); x = np.arange(n) / SR
        nz = sosfilt(butter(2, [900, 7000], "band", fs=SR, output="sos"), rng.standard_normal(n))
        return (nz * .8 + np.sin(2 * np.pi * 190 * x) * .5) * np.exp(-x * 16)
    def hat():
        n = int(.06 * SR)
        return sosfilt(butter(2, 7000, "high", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-np.arange(n) / SR * 70)
    K, S, Hh = kick(), snare(), hat()
    tb = drums_on
    while tb < end_start - 0.2:
        for b in range(4):
            tt = tb + b * beat
            if tt >= end_start - 0.2: break
            if st["kit"] == "trap":
                if b in (0,) or (b == 2 and int(tb / bar) % 2): add(K, tt, .55)
                if b == 2: add(S, tt, .32)
                for h in range(4): add(Hh, tt + h * beat / 4, .07 if h % 2 else .1, pan=.25)
            elif st["kit"] == "drive":
                add(K, tt, .5)
                if b in (1, 3): add(S, tt, .3)
                for h in range(2): add(Hh, tt + h * beat / 2, .09 if h else .05, pan=-.2)
            else:
                if b in (0, 2): add(K, tt, .35)
                if b == 3: add(S, tt, .12)
        tb += bar

    # --- impacts + whooshes
    def boom(big=False):
        n = int((3 if big else 2) * SR); x = np.arange(n) / SR
        f = 38 + 60 * np.exp(-x * 9)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * (1.2 if big else 2))
        nz = sosfilt(butter(2, 2500, "low", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-x * 7) * .5
        return b + nz
    def whoosh(dur):
        n = int(dur * SR); x = np.arange(n) / SR
        nz = rng.standard_normal(n); out = np.zeros(n)
        for i, lo in enumerate(np.linspace(300, 5000, 8)):
            seg = slice(i * n // 8, (i + 1) * n // 8)
            out[seg] = sosfilt(butter(2, [lo, lo * 2], "band", fs=SR, output="sos"), nz)[seg]
        return out * (x / dur) ** 2
    for h in hits:
        if h > 0.5: add(whoosh(0.7), h - 0.7, .25)
        add(boom(), h, .5)
    add(whoosh(2.2), end_start - 2.2, .35)
    add(boom(True), end_start, .75)
    # final sustained chord
    c = st["chords"][0]; n = int(4.6 * SR); x = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * hz(m + 12) * x) + .3 * np.sin(2 * np.pi * hz(m) * x) for m in c)
    add(sig * np.clip(x / .05, 0, 1) * np.exp(-x * .6), end_start, .05)

    # reverb send
    irn = int(2.4 * SR); irt = np.arange(irn) / SR
    for ch, seed in ((L, 1), (R, 2)):
        ir = np.random.default_rng(seed).standard_normal(irn) * np.exp(-irt * 2.8) * .015
        ch += fftconvolve(ch, ir)[:N] * .8
    mus = np.stack([L, R], 1)
    fade = np.clip(t / .05, 0, 1) * np.clip((DUR - t) / .6, 0, 1)
    mus *= fade[:, None]

    # voice
    vo = np.zeros(N)
    for s0, f in d["voice"]:
        a, _ = sf.read(f); s = int(s0 * SR); vo[s:s + len(a)] += a[:N - s]
    vo *= 0.6 / np.abs(vo).max()
    act = uniform_filter1d((np.abs(vo) > .01).astype(float), int(.2 * SR))
    act = uniform_filter1d(np.clip(act * 4, 0, 1), int(.3 * SR))
    mus *= 0.5 / np.sqrt(np.mean(mus ** 2)) * 0.25
    gain = 1 - act * (1 - 10 ** (-8 / 20))
    mix = mus * gain[:, None] + vo[:, None]
    mix *= 0.9 / np.abs(mix).max()
    sf.write(f"out/{vid}_mix.wav", mix, SR, subtype="PCM_16")
    print(vid, round(DUR, 2))

for v in sys.argv[1:]: build(v)
