#!/usr/bin/env python3
"""Pick the next short from the bank, render it to an mp4 in shorts/, and write _meta.json.
The workflow then pushes the mp4 (public raw URL) and shorts_post.py posts it as a Reel."""
import json, subprocess, datetime, pathlib

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent
BANK = json.loads((HERE / "short_data.json").read_text(encoding="utf-8"))
STATE = HERE / "shorts_state.json"

state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"cursor": 0, "posted": []}
shorts = BANK["shorts"]
idx = state.get("cursor", 0) % len(shorts)
short = shorts[idx]
key = short["key"]
date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")

cur = HERE / "_current.json"
cur.write_text(json.dumps({"cta": BANK["cta"], "beats": short["beats"]}), encoding="utf-8")
frames = HERE / "frames"

subprocess.run(["node", str(HERE / "render_short_ci.mjs"), str(cur), str(frames)], check=True)

out_rel = f"shorts/{key}_{date}.mp4"
out = REPO / out_rel
out.parent.mkdir(exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", str(frames / "%04d.jpg"),
                "-i", str(HERE / "audio_bed.m4a"), "-shortest", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k", str(out)], check=True)

raw = f"https://raw.githubusercontent.com/1765Sanctum/apparel-social-assets/main/{out_rel}"
(HERE / "_meta.json").write_text(json.dumps({
    "key": key, "idx": idx, "ig_caption": short["ig_caption"],
    "fb_message": short["fb_message"], "mp4": out_rel, "raw_url": raw,
}, indent=2), encoding="utf-8")
print(f"RENDERED {out_rel}  ->  {raw}")
