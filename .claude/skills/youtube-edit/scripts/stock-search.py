#!/usr/bin/env python3
"""stock-search.py: search Pexels and/or Pixabay for one B-roll slot, write the shortlist, fetch the pick.

Keys: PEXELS_API_KEY and PIXABAY_API_KEY from the environment, else from the first .env.local found walking up from the
current folder (KEY=value lines). Provider "auto" uses every provider that has a key. Requests go through curl: the
Pixabay API answered Python's default client with 403 while curl worked (no faked user agent, ever).

Search (no download):
  python3 stock-search.py --slot ceo --q "business executives meeting" --out-dir W/broll [--provider auto|pexels|pixabay]
      -> W/broll/shortlist-ceo.json + .md (id, provider, page, author, licence, duration, 4K or not, tags) and
         W/broll/shortlist-ceo.jpg (thumbnails, numbered in shortlist order)
Download the pick:
  python3 stock-search.py --slot ceo --pick pixabay:318026 --out-dir W/broll   -> W/broll/raw/ceo-318026.mp4 (+ clips.json)
Offline (tests, cached results): --from-json FILE --provider pixabay|pexels parses a saved API response instead.

Pixabay: GET https://pixabay.com/api/videos/?key=..&q=..&video_type=film&safesearch=true&per_page=..; hits[].videos has
large (3840 wide when present; empty url and size 0 when not), medium (1920), small, tiny. Cache results 24 h, 100
requests a minute, no mass downloads: one query per slot, download only what you use, never hotlink.
Pexels: GET https://api.pexels.com/videos/search?query=..&orientation=landscape&per_page=.. with the key in the
Authorization header; take the 3840-wide entry of video_files.
"""
import argparse, json, os, subprocess, sys, urllib.parse


def load_keys():
    keys = {k: os.environ.get(k) for k in ("PEXELS_API_KEY", "PIXABAY_API_KEY")}
    d = os.getcwd()
    while True:
        p = os.path.join(d, ".env.local")
        if os.path.exists(p):
            for line in open(p):
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k in keys and not keys[k]: keys[k] = v.strip().strip('"')
            break
        if os.path.dirname(d) == d: break
        d = os.path.dirname(d)
    return keys


def curl_json(url, headers=()):
    cmd = ["curl", "-sf", url]
    for h in headers: cmd += ["-H", h]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: sys.exit("request failed (%d): %s" % (r.returncode, url.split("key=")[0]))
    return json.loads(r.stdout)


def norm_pixabay(d):
    out = []
    for h in d.get("hits", []):
        v = h["videos"]; big = v["large"] if v.get("large", {}).get("url") else v["medium"]
        out.append({"provider": "pixabay", "id": h["id"], "page": h.get("pageURL"), "author": h.get("user"),
                    "licence": "Pixabay Content License", "duration": h.get("duration"), "tags": h.get("tags", ""),
                    "width": big["width"], "height": big["height"], "is4k": bool(v.get("large", {}).get("url")),
                    "url": big["url"], "thumb": v.get("small", big).get("thumbnail") or big.get("thumbnail")})
    return out


def norm_pexels(d):
    out = []
    for h in d.get("videos", []):
        files = sorted([f for f in h.get("video_files", []) if f.get("width")], key=lambda f: -f["width"])
        if not files: continue
        big = next((f for f in files if f["width"] == 3840), files[0])
        out.append({"provider": "pexels", "id": h["id"], "page": h.get("url"), "author": h.get("user", {}).get("name"),
                    "licence": "Pexels License", "duration": h.get("duration"), "tags": "",
                    "width": big["width"], "height": big["height"], "is4k": big["width"] >= 3840,
                    "url": big["link"], "thumb": h.get("image")})
    return out


ap = argparse.ArgumentParser()
ap.add_argument("--slot", required=True); ap.add_argument("--q"); ap.add_argument("--out-dir", required=True)
ap.add_argument("--provider", default="auto", choices=["auto", "pexels", "pixabay"]); ap.add_argument("--per", type=int, default=10)
ap.add_argument("--pick"); ap.add_argument("--from-json")
a = ap.parse_args()
os.makedirs(a.out_dir, exist_ok=True)
short = os.path.join(a.out_dir, "shortlist-%s.json" % a.slot)

if a.pick:
    prov, pid = a.pick.split(":")
    hit = next((h for h in json.load(open(short)) if h["provider"] == prov and str(h["id"]) == pid), None)
    if not hit: sys.exit("%s is not in %s" % (a.pick, short))
    os.makedirs(os.path.join(a.out_dir, "raw"), exist_ok=True)
    dst = os.path.join(a.out_dir, "raw", "%s-%s.mp4" % (a.slot, pid))
    subprocess.run(["curl", "-sfL", "-o", dst, hit["url"]], check=True)
    rec_p = os.path.join(a.out_dir, "clips.json")
    rec = json.load(open(rec_p)) if os.path.exists(rec_p) else []
    rec = [r for r in rec if r["slot"] != a.slot] + [{"slot": a.slot, "file": dst, **{k: hit[k] for k in
           ("provider", "id", "page", "author", "licence", "duration", "width", "height")}}]
    json.dump(rec, open(rec_p, "w"), indent=1)
    print("downloaded %s (%dx%d, %s) -> %s" % (a.pick, hit["width"], hit["height"], hit["licence"], dst))
    sys.exit(0)

hits = []
if a.from_json:
    d = json.load(open(a.from_json))
    hits = norm_pixabay(d) if a.provider == "pixabay" else norm_pexels(d)
else:
    if not a.q: sys.exit("--q is required for a search")
    keys = load_keys()
    provs = [a.provider] if a.provider != "auto" else [p for p, k in (("pexels", "PEXELS_API_KEY"), ("pixabay", "PIXABAY_API_KEY")) if keys[k]]
    if not provs: sys.exit("no PEXELS_API_KEY or PIXABAY_API_KEY in the environment or .env.local: use the page's download button")
    for p in provs:
        if p == "pixabay":
            url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": keys["PIXABAY_API_KEY"], "q": a.q[:100],
                  "video_type": "film", "safesearch": "true", "per_page": max(3, a.per)})
            hits += norm_pixabay(curl_json(url))
        else:
            url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": a.q, "orientation": "landscape", "per_page": a.per})
            hits += norm_pexels(curl_json(url, ["Authorization: " + keys["PEXELS_API_KEY"]]))
hits.sort(key=lambda h: (not h["is4k"],))
json.dump(hits, open(short, "w"), indent=1)
md = ["# B-roll shortlist: %s%s" % (a.slot, (" (\"%s\")" % a.q) if a.q else ""), "",
      "| # | pick with | 4K | s | author | page | tags |", "|---|---|---|---|---|---|---|"]
for i, h in enumerate(hits):
    md.append("| %d | `%s:%s` | %s | %s | %s | %s | %s |" % (i, h["provider"], h["id"], "yes" if h["is4k"] else "%dp" % h["height"],
              h["duration"], h["author"], h["page"], h["tags"][:50]))
open(short.replace(".json", ".md"), "w").write("\n".join(md) + "\n")
thumbs = []
for i, h in enumerate(hits[:12]):
    if not h.get("thumb"): continue
    p = os.path.join(a.out_dir, ".thumbs", "%s-%02d.jpg" % (a.slot, i)); os.makedirs(os.path.dirname(p), exist_ok=True)
    if subprocess.run(["curl", "-sfL", "-o", p, h["thumb"]]).returncode == 0: thumbs.append(p)
if thumbs:
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in thumbs: cmd += ["-i", p]
    n = len(thumbs)
    cmd += ["-filter_complex", "".join("[%d]scale=320:180[s%d];" % (i, i) for i in range(n)) + "".join("[s%d]" % i for i in range(n))
            + "xstack=inputs=%d:layout=%s" % (n, "|".join("%d_%d" % ((i % 4) * 320, (i // 4) * 180) for i in range(n))) if n > 1 else "[0]scale=320:180",
            short.replace(".json", ".jpg")]
    subprocess.run(cmd, check=True)
print("%d candidates -> %s (+ .md, .jpg); pick one with --pick provider:id" % (len(hits), short))
