# Daily motivation shorts — runbook

Account: Metricool brand "Regulile Comunității 🔔" → YouTube, TikTok, Facebook, Instagram. Language: English.
Post times: 07:00 and 19:00 Europe/Lisbon, every day (see settings.json). Spec ids: YYYY-MM-DD-am (07:00) and YYYY-MM-DD-pm (19:00).
Morning (am) videos: energising — discipline, starting the day, ambition. Evening (pm) videos: money mindset or reflective life lessons.
AI-content labels per network are set in settings.json (ai_labels).

## Spec format (specs/YYYY-MM-DD.json)
- theme: "gold" (money), "dawn" (life / hope / perseverance), "steel" (discipline / self-improvement)
- hook: [BIG TOP LINE in caps, small italic subline] — shown for the first 3.6 s; must stop the scroll
- lines: 20-24 spoken lines, ~57-63 s of speech total, so the FINAL video is 61-70 s (TikTok Creator Rewards only pays for videos over 1 minute). `*word*` = accent colour + zoom (1-2 per line max, usually the last key word).
  Prefix `#` = impact hit + flash (put on 3-5 turning-point lines, incl. the first line).
- end: [line 1 white, line 2 accent, small CTA] — CTA drives saves/shares/comments
- cover: {lines: 2-3 short caps lines, accent_lines: [index], sub: short italic line, bg_time: 15-30}
- day_counter: optional true — shows a DAY 1→365 counter at the top; only for videos about a year/365-day journey.
- post: {title (YouTube, < 70 chars), caption (1-2 lines + emoji), hashtags (5), first_comment (question to drive comments)}

## Writing rules
Goal: views and platform payouts (no products, no links in bio). Retention is everything: hook in the first second, a new idea or turn every 3-4 lines, build to a strong final line.
Original lines only (no quotes from famous people, no lyrics, no real names). Punchy, second-person, one idea per video.
Money videos: habits and mindset only — no promises of returns, no specific investment/crypto/stock tips, no get-rich-quick.
No medical claims, nothing political, nothing shaming or hateful. Each topic must differ from every topic in history.json.

## Build
First measure: `python3 vo.py <id>` prints 'speech ends X'. X must be 57-65 (final video = X + ~4.9 s). Too short: add lines; too long: cut. Only then run build.sh.
`./build.sh YYYY-MM-DD` → out/<id>_final.mp4 (≈30-40 MB) and out/<id>_cover.jpg

## Hosting
Branch `media` (orphan, force-pushed) holds only the last 3 days of files. Public URL:
https://raw.githubusercontent.com/Reeflo123/multiplayer-game/media/<file>
Branch `automation` holds this code, specs/ and history.json.
