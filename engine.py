import sys, json, math, subprocess, time, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scripts import VIDEOS

W, H, FPS = 1080, 1920, 30
HW, HH = W // 2, H // 2
FD = "fonts/"
ANTON = FD + "anton/files/anton-latin-400-normal.woff"
PLAY_I = FD + "playfair-display/files/playfair-display-latin-600-italic.woff"
PLAY_IB = FD + "playfair-display/files/playfair-display-latin-800-italic.woff"

THEMES = {
    "gold":  dict(accent=(242, 193, 78), accent2=(255, 226, 150)),
    "dawn":  dict(accent=(255, 179, 107), accent2=(255, 214, 170)),
    "steel": dict(accent=(255, 62, 62), accent2=(255, 140, 140)),
}

def ease(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def eout(x):
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3

def radial(cx, cy, r, w, h, p=2.0):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.clip(1 - np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r, 0, 1) ** p

# ------------------------------------------------------------------ backgrounds (half res)
class GoldBG:
    """Black & gold: anamorphic light streaks, pulsing glow, spinning falling coins."""
    def __init__(s, dur, rng):
        s.rng = rng
        yy = np.linspace(0, 1, HH, dtype=np.float32)[:, None, None]
        s.base = (np.array([6, 5, 4], np.float32) * (1 - yy) + np.array([18, 13, 6], np.float32) * yy) * np.ones((1, HW, 1), np.float32)
        s.glow = radial(HW * .5, HH * .55, HW * 1.1, HW, HH, 2.4)[..., None] * np.array([150, 105, 35], np.float32)
        s.top = radial(HW * .5, -60, HW * .9, HW, HH, 2)[..., None] * np.array([90, 70, 30], np.float32)
        n = 46
        s.cx = rng.uniform(-30, HW + 30, n); s.cy = rng.uniform(-HH, HH, n)
        s.z = rng.uniform(0.25, 1.0, n); s.ph = rng.uniform(0, 6.28, n); s.spin = rng.uniform(1.5, 4.5, n)
        s.sway = rng.uniform(0, 6.28, n)
    def frame(s, t, energy):
        f = s.base + s.glow * (0.55 + 0.25 * math.sin(t * 1.3) + 0.6 * energy) + s.top
        # anamorphic streaks
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        lay = Image.new("RGB", (HW, HH)); d = ImageDraw.Draw(lay)
        for i in range(3):
            y = HH * (0.25 + 0.27 * i) + 40 * math.sin(t * 0.3 + i * 2)
            a = 0.35 + 0.25 * math.sin(t * 0.7 + i)
            d.rectangle((0, y - 2, HW, y + 2), fill=tuple(int(c * a) for c in (255, 200, 110)))
        # coins
        order = np.argsort(s.z)
        for i in order:
            z = s.z[i]
            spd = 60 + 140 * z
            y = (s.cy[i] + t * spd) % (HH + 120) - 60
            x = s.cx[i] + 18 * math.sin(t * 0.8 + s.sway[i])
            r = 6 + 22 * z
            w = abs(math.cos(t * s.spin[i] + s.ph[i]))
            rx = max(1.5, r * w)
            b = 0.35 + 0.65 * z
            edge = tuple(int(c * b) for c in (150, 105, 30))
            face = tuple(int(c * b * (0.75 + 0.25 * w)) for c in (240, 190, 80))
            d.ellipse((x - rx, y - r, x + rx, y + r), fill=edge)
            d.ellipse((x - rx * 0.8, y - r * 0.82, x + rx * 0.8, y + r * 0.82), fill=face)
            if w > 0.85:  # glint
                g = tuple(int(c * b) for c in (255, 245, 210))
                d.ellipse((x - rx * .3 - 2, y - r * .55, x - rx * .3 + 2, y - r * .2), fill=g)
        blur = lay.filter(ImageFilter.GaussianBlur(5))
        arr = np.asarray(img, np.float32) + np.asarray(lay, np.float32) * 0.6 + np.asarray(blur, np.float32) * 0.75
        return arr

class DawnBG:
    """Night -> sunrise over the length of the video, sun rising with god rays, stars fading."""
    def __init__(s, dur, rng):
        s.dur = dur
        y, x = np.mgrid[0:HH, 0:HW].astype(np.float32)
        s.x, s.y = x, y
        s.yn = (y / HH)[..., None]
        n = 220
        s.sx = rng.integers(0, HW, n); s.sy = rng.integers(0, int(HH * .7), n); s.sb = rng.uniform(.3, 1, n); s.sp = rng.uniform(0, 6.28, n)
        s.mist = np.asarray(Image.fromarray((rng.random((HH // 8, HW // 4)) * 255).astype(np.uint8)).resize((HW * 2, HH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30)), np.float32) / 255
    def frame(s, t, energy):
        p = ease(t / (s.dur * 0.92))
        top = np.array([6, 10, 28]) * (1 - p) + np.array([40, 60, 120]) * p
        mid = np.array([14, 18, 48]) * (1 - p) + np.array([210, 120, 110]) * p
        bot = np.array([20, 18, 40]) * (1 - p) + np.array([255, 170, 90]) * p
        yn = s.yn
        f = np.where(yn < .55, top * (1 - yn / .55) + mid * (yn / .55), mid * (1 - (yn - .55) / .45) + bot * ((yn - .55) / .45)).astype(np.float32)
        # sun
        sy = HH * (1.12 - 0.42 * p); sx = HW * .5
        dx, dy = s.x - sx, s.y - sy
        dist = np.sqrt(dx * dx + dy * dy) + 1e-3
        sun = np.clip(1 - dist / (HW * (0.18 + .02 * energy)), 0, 1) ** 0.6
        halo = np.clip(1 - dist / (HW * 1.3), 0, 1) ** 2.5
        ang = np.arctan2(dy, dx)
        rays = (0.5 + 0.5 * np.sin(ang * 14 + t * 0.25)) ** 6 * (0.5 + 0.5 * np.sin(ang * 5 - t * 0.17)) * np.clip(1 - dist / (HH * .95), 0, 1) ** 1.5
        sunc = np.array([255, 220, 160], np.float32)
        f += (sun[..., None] * 255 + halo[..., None] * sunc * (0.25 + 0.5 * p) + rays[..., None] * sunc * (0.15 + 0.45 * p) * (1 + energy)) * (0.3 + 0.7 * p)
        # stars
        sa = (1 - p) ** 1.5
        if sa > 0.02:
            tw = s.sb * (0.6 + 0.4 * np.sin(t * 2 + s.sp)) * sa * 230
            f[s.sy, s.sx] += tw[:, None]
        # mist
        off = int((t * 12) % HW)
        m = s.mist[:, off:off + HW]
        f += (m ** 2)[..., None] * np.array([120, 110, 130], np.float32) * (0.25 + .2 * p) * (s.yn ** 1.5)
        return f

class SteelBG:
    """Monochrome hyperspace tunnel accelerating, red accent glow, horizontal light sweeps."""
    def __init__(s, dur, rng):
        s.dur = dur; s.rng = rng
        n = 420
        s.px = rng.uniform(-1, 1, n); s.py = rng.uniform(-1, 1, n); s.pz = rng.uniform(0.05, 1, n)
        s.base = np.full((HH, HW, 3), (8, 8, 10), np.float32)
        s.red = radial(HW * .5, HH * .5, HW * .9, HW, HH, 2.2)[..., None] * np.array([110, 14, 14], np.float32)
        s.prev_t = 0; s.zpos = 0.0
    def frame(s, t, energy):
        speed = 0.12 + 0.55 * ease(t / s.dur) + 0.6 * energy
        dt = t - s.prev_t; s.prev_t = t; s.zpos += speed * dt
        f = s.base + s.red * (0.35 + 0.2 * math.sin(t * 1.1) + 0.9 * energy)
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
        cx, cy = HW / 2, HH * .47
        for x, y, z0 in zip(s.px, s.py, s.pz):
            z = (z0 - s.zpos) % 1.0 + 0.02
            z2 = z + 0.012 + speed * 0.05
            X1, Y1 = cx + x / z * 60, cy + y / z * 60
            X2, Y2 = cx + x / z2 * 60, cy + y / z2 * 60
            b = int(min(255, 40 + 215 * (1 - z)))
            d.line((X2, Y2, X1, Y1), fill=(b, b, b + 6), width=1 if z > .4 else 2)
        for i in range(2):
            y = (t * 90 + i * HH / 2) % (HH + 200) - 100
            d.rectangle((0, y, HW, y + 1), fill=(60, 60, 64))
        return np.asarray(img, np.float32)

BGS = {"gold": GoldBG, "dawn": DawnBG, "steel": SteelBG}

# ------------------------------------------------------------------ captions
class Captions:
    def __init__(s, tl, accent):
        s.accent = accent
        s.f = ImageFont.truetype(ANTON, 118); s.fe = ImageFont.truetype(ANTON, 150)
        s.chunks = []
        for L in tl:
            words = L["words"]; cur = []
            for w in words:
                cur.append(w)
                raw = w[0]
                brk = len(cur) >= 3 or re.search(r"[.,!?]$", raw.replace("*", "")) or raw.startswith("*")
                if brk and not (raw.startswith("*") and len(cur) == 1 and False):
                    s.chunks.append(cur); cur = []
            if cur: s.chunks.append(cur)
        # chunk display spans
        s.spans = []
        for i, c in enumerate(s.chunks):
            st = c[0][1]
            en = c[-1][2] + 0.25
            if i + 1 < len(s.chunks): en = min(en, s.chunks[i + 1][0][1])
            s.spans.append((st, en))
        s.cache = {}
    def render(s, ci, active):
        key = (ci, active)
        if key in s.cache: return s.cache[key]
        words = s.chunks[ci]
        toks = []
        for j, (w, _, _) in enumerate(words):
            emph = "*" in w
            txt = w.replace("*", "").upper()
            f = s.fe if emph else s.f
            col = s.accent if (emph or j == active) else (255, 255, 255)
            toks.append((txt, f, col))
        space = 28
        widths = [t[1].getlength(t[0]) for t in toks]
        # wrap into lines that fit
        lines, cur, cw = [], [], 0
        for tk, wd in zip(toks, widths):
            if cur and cw + space + wd > W - 120:
                lines.append(cur); cur, cw = [], 0
            cur.append((tk, wd)); cw += wd + (space if len(cur) > 1 else 0)
        lines.append(cur)
        lh = 168
        img = Image.new("RGBA", (W, lh * len(lines) + 60), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d, ds = ImageDraw.Draw(img), ImageDraw.Draw(sh)
        for li, ln in enumerate(lines):
            tw = sum(wd for _, wd in ln) + space * (len(ln) - 1)
            x = (W - tw) / 2
            for (txt, f, col), wd in ln:
                base_y = 30 + li * lh + (150 - (f.size)) * 0.75
                ds.text((x, base_y + 6), txt, font=f, fill=(0, 0, 0, 200), stroke_width=10, stroke_fill=(0, 0, 0, 200))
                d.text((x, base_y), txt, font=f, fill=col + (255,), stroke_width=4, stroke_fill=(0, 0, 0, 255))
                x += wd + space
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        out = Image.alpha_composite(sh, img)
        s.cache[key] = out
        return out
    def at(s, t):
        for ci, (st, en) in enumerate(s.spans):
            if st - 0.04 <= t < en:
                words = s.chunks[ci]; active = 0
                for j, (_, ws, we) in enumerate(words):
                    if t >= ws - 0.03: active = j
                return ci, active, t - st
        return None

def overlay(frame_img, ov, x, y, scale=1.0, alpha=1.0):
    if scale != 1.0:
        ov = ov.resize((max(1, int(ov.width * scale)), max(1, int(ov.height * scale))), Image.BILINEAR)
    if alpha < 1.0:
        a = ov.getchannel("A").point(lambda v: int(v * alpha)); ov = ov.copy(); ov.putalpha(a)
    frame_img.alpha_composite(ov, (int(x - ov.width / 2), int(y - ov.height / 2)))

def text_block(lines, w=W):
    """lines: list of (text, font, color, letterspacing) -> RGBA"""
    imgs = []
    for txt, f, col, sp in lines:
        adv = [f.getlength(c) for c in txt]; tw = sum(adv) + sp * (len(txt) - 1)
        if tw > w - 110:
            f = f.font_variant(size=int(f.size * (w - 110) / tw)); sp = sp * (w - 110) / tw
            adv = [f.getlength(c) for c in txt]; tw = sum(adv) + sp * (len(txt) - 1)
        asc, desc = f.getmetrics()
        im = Image.new("RGBA", (w, asc + desc + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        x = (w - tw) / 2
        for c, a in zip(txt, adv):
            d.text((x, 10), c, font=f, fill=col + (255,), stroke_width=3, stroke_fill=(0, 0, 0, 255)); x += a + sp
        imgs.append(im)
    hgt = sum(i.height for i in imgs)
    out = Image.new("RGBA", (w, hgt + 40), (0, 0, 0, 0)); y = 20
    for i in imgs: out.alpha_composite(i, (0, y)); y += i.height - 8
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); sh.putalpha(out.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .8)))
    return Image.alpha_composite(sh, out)

# ------------------------------------------------------------------ main render
def main(vid):
    spec = VIDEOS[vid]; th = THEMES[spec["theme"]]
    data = json.load(open(f"out/{vid}.json"))
    tl = data["timeline"]
    end_start = data["speech_end"] + 0.25
    DUR = end_start + 4.6
    json.dump({"dur": DUR, "end_start": end_start}, open(f"out/{vid}_meta.json", "w"))
    rng = np.random.default_rng(11)
    bg = BGS[spec["theme"]](DUR, rng)
    cap = Captions(tl, th["accent"])
    hits = [L["start"] for L in tl if L["hit"]] + [end_start]
    emph_t = [ws for L in tl for (w, ws, we) in L["words"] if "*" in w]
    # hook
    fa = ImageFont.truetype(ANTON, 104); fp = ImageFont.truetype(PLAY_I, 62)
    hook = text_block([(spec["hook"][0], fa, (255, 255, 255), 6), (spec["hook"][1], fp, th["accent"], 0)])
    fe1 = ImageFont.truetype(ANTON, 150); fe3 = ImageFont.truetype(PLAY_I, 50)
    endA = text_block([(spec["end"][0], fe1, (255, 255, 255), 8)])
    endB = text_block([(spec["end"][1], fe1, th["accent"], 8)])
    endC = text_block([(spec["end"][2], fe3, (235, 235, 235), 0)])
    # grain, vignette
    grains = [(rng.standard_normal((H // 2, W // 2)).astype(np.float32)) for _ in range(6)]
    grains = [np.asarray(Image.fromarray(np.clip(g * 40 + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.NEAREST), np.float32)[..., None] - 128 for g in grains]
    vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = np.clip(1.12 - (((vx - W / 2) / (W * .72)) ** 2 + ((vy - H / 2) / (H * .6)) ** 2) * .55, .35, 1)[..., None]

    stills = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    p = None if stills else subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
                          "-pix_fmt", "yuv420p", f"out/{vid}_silent.mp4"], stdin=subprocess.PIPE)
    n = int(DUR * FPS); st = time.time()
    idxs = [int(x * FPS) for x in stills] if stills else range(n)
    for i in idxs:
        t = i / FPS
        if stills: bg.prev_t = max(0, t - 1 / FPS) if hasattr(bg, "prev_t") else 0
        # energy from hits / emphasis
        e_hit = max([math.exp(-(t - h) * 4) for h in hits if t >= h] + [0])
        e_emp = max([math.exp(-(t - h) * 6) for h in emph_t if t >= h] + [0])
        energy = min(1.0, e_hit * .8 + e_emp * .35)
        f = bg.frame(t, energy)
        # punch zoom + shake
        z = 1 + 0.07 * e_hit + 0.035 * e_emp + 0.04 * (t / DUR)
        sx = (math.sin(t * 47) * 6 + math.sin(t * 31) * 4) * e_hit
        sy = (math.cos(t * 41) * 6) * e_hit
        im = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        cw, ch = HW / z, HH / z
        x0 = (HW - cw) / 2 + sx / 2; y0 = (HH - ch) / 2 + sy / 2
        im = im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")
        # hook (first ~3.6s)
        if t < 3.8:
            a = ease(t / 0.15) * ease((3.8 - t) / 0.5)
            overlay(im, hook, W / 2, H * 0.2 - 30 * (1 - eout(t / 0.4)), 1 + 0.08 * (1 - eout(t / 0.35)), a)
        # captions
        if t < end_start:
            c = cap.at(t)
            if c:
                ci, act, lt = c
                ov = cap.render(ci, act)
                sc = 1 + 0.18 * (1 - eout(lt / 0.13))
                overlay(im, ov, W / 2, H * 0.53, sc, ease(lt / 0.06))
        else:
            lt = t - end_start
            out = ease((DUR - t) / 0.6)
            overlay(im, endA, W / 2, H * .42, 1 + .25 * (1 - eout(lt / .25)), ease(lt / .1) * out)
            overlay(im, endB, W / 2, H * .42 + 165, 1 + .25 * (1 - eout((lt - .35) / .25)), ease((lt - .35) / .1) * out)
            overlay(im, endC, W / 2, H * .42 + 330, 1.0, ease((lt - 1.1) / .5) * out)
        if spec["theme"] == "steel":  # day counter
            day = 1 + int(364 * ease(min(1, t / (end_start - 0.3))))
            if not hasattr(main, "_fc"): main._fc = ImageFont.truetype(ANTON, 54)
            ctr = text_block([(f"DAY {day}", main._fc, th["accent"] if day == 365 else (220, 220, 225), 4)])
            overlay(im, ctr, W / 2, H * .085, 1.0, ease((t - 3.6) / .5))
            if t > 3.6:
                bar = Image.new("RGBA", (int(600 * day / 365) + 1, 6), th["accent"] + (int(230 * ease((t - 3.6) / .5)),))
                im.alpha_composite(bar, (W // 2 - 300, int(H * .085) + 52))
        arr = np.asarray(im.convert("RGB"), np.float32)
        # flash on hits
        fl = max([math.exp(-(t - h) * 14) for h in hits if t >= h] + [0]) * 0.45
        arr = arr * vign  # no film grain (looked noisy after platform compression)
        arr = arr + (255 - arr) * fl
        arr *= ease(t / 0.12) * ease((DUR - t) / 0.35)
        if stills:
            Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(f"out/{vid}_s{t:05.1f}.png"); continue
        p.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
        if i % 300 == 0: print(vid, i, n, round(time.time() - st), flush=True)
    if stills: return
    p.stdin.close(); p.wait(); print(vid, "done", round(time.time() - st), flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
