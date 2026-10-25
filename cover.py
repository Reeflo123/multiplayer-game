import sys, numpy as np
from PIL import Image, ImageFont
import engine as E
from scripts import VIDEOS
vid = sys.argv[1]; spec = VIDEOS[vid]; c = spec["cover"]; theme = spec["theme"]
rng = np.random.default_rng(11)
bg = E.BGS[theme](40.0, rng); t = c.get("bg_time", 25.0)
if hasattr(bg, "prev_t"): bg.prev_t = t - 1 / 30; bg.zpos = 0.3 * t
f = bg.frame(t, 0.3)
im = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).resize((E.W, E.H), Image.BICUBIC)
y = np.linspace(0, 1, E.H)[:, None, None]
im = Image.fromarray(np.clip(np.asarray(im, np.float32) * (1 - 0.45 * np.exp(-((y - 0.47) / 0.2) ** 2)), 0, 255).astype(np.uint8)).convert("RGBA")
accent = E.THEMES[theme]["accent"]; big = ImageFont.truetype(E.ANTON, 250)
blk = E.text_block([(l, big, accent if i in c["accent_lines"] else (255, 255, 255), 6) for i, l in enumerate(c["lines"])])
E.overlay(im, blk, E.W / 2, E.H * 0.46)
sb = E.text_block([(c["sub"], ImageFont.truetype(E.PLAY_I, 58), (240, 240, 240), 0)])
E.overlay(im, sb, E.W / 2, E.H * 0.46 + blk.height / 2 + 40)
im.convert("RGB").save(f"out/{vid}_cover.jpg", quality=92)
