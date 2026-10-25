# Daily motivation shorts — runbook

Account: Metricool brand "Regulile Comunității 🔔" → YouTube, TikTok, Facebook, Instagram. Language: English.
Post time: 19:00 Europe/Lisbon, every day.

## Spec format (specs/YYYY-MM-DD.json)
- theme: "gold" (money), "dawn" (life / hope / perseverance), "steel" (discipline / self-improvement)
- hook: [BIG TOP LINE in caps, small italic subline] — shown for the first 3.6 s; must stop the scroll
- lines: 9-14 short spoken lines, ~30-45 s of speech total. `*word*` = accent colour + zoom (1-2 per line max, usually the last key word).
  Prefix `#` = impact hit + flash (put on 3-5 turning-point lines, incl. the first line).
- end: [line 1 white, line 2 accent, small CTA] — CTA drives saves/shares/comments
- cover: {lines: 2-3 short caps lines, accent_lines: [index], sub: short italic line, bg_time: 15-30}
- post: {title (YouTube, < 70 chars), caption (1-2 lines + emoji), hashtags (5), first_comment (question to drive comments)}

## Writing rules
Original lines only (no quotes from famous people, no lyrics, no real names). Punchy, second-person, one idea per video.
Money videos: habits and mindset only — no promises of returns, no specific investment/crypto/stock tips, no get-rich-quick.
No medical claims, nothing political, nothing shaming or hateful. Each topic must differ from every topic in history.json.

## Build
`./build.sh YYYY-MM-DD` → out/<id>_final.mp4 (≈30-40 MB) and out/<id>_cover.jpg

## Hosting
Branch `media` (orphan, force-pushed) holds only the last 3 days of files. Public URL:
https://raw.githubusercontent.com/Reeflo123/multiplayer-game/media/<file>
Branch `automation` holds this code, specs/ and history.json.
