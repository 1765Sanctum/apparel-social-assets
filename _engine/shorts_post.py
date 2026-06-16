#!/usr/bin/env python3
"""Post the rendered short (from _meta.json) as an IG Reel + FB video, then advance state.
Waits for the just-pushed raw URL to be live before posting (Meta fetches it server-side).
Transient Meta 5xx are retried. Born 2026-06-13."""
import json, os, sys, time, urllib.request, urllib.parse, pathlib

HERE = pathlib.Path(__file__).parent
GRAPH = "https://graph.facebook.com/v21.0"
meta = json.loads((HERE / "_meta.json").read_text(encoding="utf-8"))
PAGE_ID = os.environ["META_PAGE_ID"]
IG_ID = os.environ["META_IG_USER_ID"]


def _open(req, timeout=60):
    last = None
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace") if e.fp else ""
            if e.code < 500:
                raise SystemExit(f"Meta error {e.code}: {body[:300]}")
            last = body
        except Exception as e:
            last = str(e)
        time.sleep(5)
    raise SystemExit(f"Meta request failed after retries: {last}")


def post(path, data):
    return _open(urllib.request.Request(f"{GRAPH}/{path}", data=urllib.parse.urlencode(data).encode(), method="POST"))


def get(path, params):
    return _open(urllib.request.Request(f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)))


def page_token():
    direct = os.environ.get("APPAREL_META_PAGE_TOKEN", "").strip()
    if direct:
        return direct
    sysu = os.environ["APPAREL_META_SYSTEM_USER_TOKEN"]
    return get(PAGE_ID, {"fields": "access_token", "access_token": sysu})["access_token"]


raw = meta["raw_url"]
# Wait for the pushed mp4 to be live on the CDN before handing the URL to Meta.
for _ in range(20):
    try:
        if urllib.request.urlopen(urllib.request.Request(raw, method="HEAD"), timeout=20).status == 200:
            break
    except Exception:
        pass
    time.sleep(6)
else:
    raise SystemExit(f"raw URL never went live: {raw}")

tok = page_token()

# IG Reel (async container -> poll FINISHED -> publish). cover_url = the design's mockup
# (JPEG, 1080x1920, center-crop) so the grid shows the shirt, not a black opening frame.
reel = {"media_type": "REELS", "video_url": raw, "caption": meta["ig_caption"],
        "share_to_feed": "true", "access_token": tok}
if meta.get("cover_url"):
    reel["cover_url"] = meta["cover_url"]
cid = post(f"{IG_ID}/media", reel)["id"]
deadline = time.time() + 480
while time.time() < deadline:
    st = get(cid, {"fields": "status_code", "access_token": tok}).get("status_code")
    if st == "FINISHED":
        break
    if st == "ERROR":
        raise SystemExit(f"IG reel container {cid} -> ERROR")
    time.sleep(12)
else:
    raise SystemExit(f"IG reel container {cid} not FINISHED after 8 min")
ig_id = post(f"{IG_ID}/media_publish", {"creation_id": cid, "access_token": tok})["id"]

# FB video
fb_id = post(f"{PAGE_ID}/videos", {"file_url": raw, "description": meta["fb_message"], "access_token": tok})["id"]
print(f"POSTED  IG reel {ig_id}  |  FB video {fb_id}")

STATE = HERE / "shorts_state.json"
state = json.loads(STATE.read_text(encoding="utf-8"))
state["cursor"] = meta["idx"] + 1
state.setdefault("posted", []).append({"key": meta["key"], "ig": ig_id, "fb": fb_id, "raw": raw,
                                       "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
