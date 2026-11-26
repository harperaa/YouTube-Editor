"""stage.py: the stage scene (SKILL.md "Stage scenes"), the house explainer look learned from Christian Peverelli's
videos: a full-frame dark stage (near-black, a teal glow pooled at the bottom, a faint violet top) where glass UI
builds piece by piece on the words, real software rebuilt as it looks (Claude Code, the terminal, a chat, an X post, a
docs page), skeleton placeholders that fill in as each item is said, a highlighter that sweeps the spoken words, and
one sound for every thing that happens on screen.

Storyboard beat:
  {"type": "stage", "id": "cm", "in": 12.0, "out": 21.5, "anchor": "a hidden switch",
   "src": "Anthropic's announcement, Nov 17", "domain": "x.com",      # optional source pills, top left
   "cam": [[1.12, -80, 40, 15.0, 3.0]],                               # optional push: scale, x, y, at, dur
   "sfx": true,                                                       # false = silent scene
   "els": [ {"k": "window", "id": "w", "app": "claude-code", "x": 560, "y": 180, "w": 800, "h": 560, "at": 12.2}, ... ]}

Element kinds (x, y, w, h in the 1920x1080 frame; "at" = when it lands, on its word):
  window   app chrome: app = claude-code | claude | terminal | browser | plain; title; url (browser); badge {text, at}
  rows     a list that starts as skeleton bars and fills as each item is said:
           items [{text, at, sub, value, icon, logo, num}], skel (rows shown before), rowh, gap, show (skeleton time),
           numbered, active (the newest glows, the rest step back)
  cards    a row of tall glass cards: items [{title, sub, icon, at}], show; the newest glows
  toggle   a settings row: label, sub, at (appears), on (the switch flips), glow
  checks   a row of boxes ticked in turn: n, size, gap, ticks [t, ...] (or from + every + count)
  grid     tiles of documents: cols, rows, cw, ch, gap, label ("Script {n}"), at, scan [t, dur], pick [[index, t], ...],
           values {index: "$1,250"}
  count    a number that counts: from, to, prefix, suffix, of ("of 40"), at, dur, size, decimals
  big      a hero number or word: text, sub, sub_em [word indexes], at, size
  keys     keycaps pressed in turn: keys ["Ctrl", "O"], at, gap
  timeline a date line: w, at, nodes [{pos 0-1, label, at, pill}], end ("Today")
  vs       two cards and a "vs": left {title, sub, icon}, right {...}, at, right_at
  type     a typed terminal or prompt line: text, at, cps, size, prompt ("❯"), hl (time it gets a glow box)
  text     words that rise in one by one: text, em [indexes], size, at, align, color, every (seconds per word)
  pill     a small rounded label: text, at, dot, glow
  tweet    an X post rebuilt: name, handle, text, at, verified, marks [[phrase, t0, t1], ...]
  page     a web or docs page rebuilt in type: theme light | dark, kicker, title, byline, paras [..], marks [[phrase, t0, t1]],
           serif, scroll [[px, t, dur]]
  bars     a bar chart: data [[label, value, sub], ...], at, every, hl [[index, t], ...], unit, title
  logo     a brand logo on a white tile: src (img/...), label, size, at
  icon     a line icon on a glass tile: name (an ICONS name, or "claude"), size, color, at, label
  wire     a connector: pts [[x, y], ...], at, run (a light travels it), color
  chat     chat messages: msgs [{who: user | ai, text, at}]
  progress a bar that fills: steps [[fraction, t], ...], label

Any element: "out" (fades away), "dim" (steps back to .35), "glow" (lights teal), "moves" [[dx, dy, t, dur]],
"anchor" (its spoken phrase, checked by beat-check), "sfx" (a sound name from sfx/ui-*.wav, or false).
"""
import html as _html

CY = "10,240,240"
CLAUDE = "#D97757"
SFX_VOL = {"whoosh": .20, "pop": .34, "tick": .26, "click": .30, "toggle": .30, "select": .20, "key": .24, "scan": .12,
           "success": .20, "thock": .30, "swoosh-out": .14, "count": .14}
DEFAULT_SFX = {"window": "pop", "rows": "tick", "cards": "pop", "toggle": "toggle", "checks": "tick", "grid": "pop",
               "count": "thock", "big": "thock", "keys": "key", "timeline": "pop", "vs": "pop", "type": "typing",
               "text": None, "pill": None, "tweet": "pop", "page": "pop", "bars": "pop", "logo": "pop", "icon": "pop",
               "wire": None, "chat": "pop", "progress": None}

SPARK = ('<svg viewBox="-50 -50 100 100" class="spark">%s</svg>' % "".join(
    '<rect x="-4.5" y="-46" width="9" height="40" rx="4.5" transform="rotate(%d)" fill="%s"/>' % (a, CLAUDE) for a in range(0, 360, 30)))


def esc(s):
    return _html.escape(str(s), quote=True)


def stage_css():
    return """
  .stg { position:absolute; inset:0; overflow:hidden; font-family:'DM Sans',sans-serif; color:#fff;
    background: radial-gradient(1200px 520px at 50%% 112%%, rgba(%(cy)s,.20), transparent 70%%),
                radial-gradient(1400px 600px at 50%% -20%%, rgba(120,70,210,.16), transparent 70%%), #06080c; }
  .stg-cam { position:absolute; inset:0; transform-origin:50%% 50%%; }
  .stg .el { position:absolute; opacity:0; }
  .stg .glass { background: linear-gradient(180deg, rgba(255,255,255,.075), rgba(255,255,255,.03)); border:1.5px solid rgba(255,255,255,.11);
    border-radius:20px; box-shadow: 0 30px 80px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.06); }
  .stg .lit { border-color: rgba(%(cy)s,.85) !important; box-shadow: 0 0 0 1px rgba(%(cy)s,.45), 0 0 34px rgba(%(cy)s,.38), inset 0 0 24px rgba(%(cy)s,.10) !important; }
  .stg .glowbox { position:absolute; inset:-1.5px; border-radius:inherit; border:2px solid rgba(%(cy)s,.9); opacity:0; pointer-events:none;
    box-shadow: 0 0 34px rgba(%(cy)s,.45), inset 0 0 22px rgba(%(cy)s,.12); }
  .stg .cy { color: rgb(%(cy)s); }
  .stg .sk { display:inline-block; width:24px; height:17px; border-radius:5px; background:rgba(255,255,255,.17); margin-right:5px; vertical-align:middle; }
  .stg .pill { display:inline-flex; align-items:center; gap:8px; padding:7px 16px; border-radius:999px; font-size:28px; font-weight:500;
    background:rgba(30,34,42,.92); border:1px solid rgba(255,255,255,.12); color:rgba(255,255,255,.9); white-space:nowrap; }
  .stg .pill .dot { width:8px; height:8px; border-radius:50%%; background:rgb(%(cy)s); box-shadow:0 0 10px rgba(%(cy)s,.8); }
  .stg .win { overflow:hidden; }
  .stg .win .bar { height:50px; display:flex; align-items:center; padding:0 20px; border-bottom:1px solid rgba(255,255,255,.07); font-size:20px; font-weight:500; color:rgba(255,255,255,.85); }
  .stg .win .dots { display:flex; gap:9px; } .stg .win .dots i { width:13px; height:13px; border-radius:50%%; background:rgba(255,255,255,.22); display:block; }
  .stg .win .ttl { position:absolute; left:0; right:0; top:0; height:50px; display:flex; align-items:center; justify-content:center; gap:10px; }
  .stg .win .url { margin-left:24px; flex:1; height:30px; border-radius:9px; background:rgba(255,255,255,.07); font-size:16px; display:flex; align-items:center; padding-left:14px; color:rgba(255,255,255,.6); }
  .stg .spark { width:26px; height:26px; }
  .stg .badge { position:absolute; right:22px; top:62px; }
  .stg .row { position:absolute; left:0; right:0; display:flex; align-items:center; padding:0 22px; gap:16px; border-radius:14px; }
  .stg .row .lay { position:absolute; left:84px; right:22px; top:0; bottom:0; display:flex; align-items:center; justify-content:space-between; }
  .stg .row .num { width:44px; height:44px; border-radius:11px; background:rgba(255,255,255,.09); display:flex; align-items:center; justify-content:center; font-size:21px; font-weight:700; flex:none; }
  .stg .row .ico { width:44px; height:44px; border-radius:50%%; background:rgba(255,255,255,.12); display:flex; align-items:center; justify-content:center; flex:none; overflow:hidden; }
  .stg .row .ico img { width:30px; height:30px; object-fit:contain; }
  .stg .row .t1 { font-size:30px; font-weight:500; } .stg .row .t2 { font-size:28px; color:rgba(255,255,255,.55); }
  .stg .row .val { font-size:30px; font-weight:700; } .stg .row .val .cy { color:rgb(%(cy)s); }
  .stg .card { position:absolute; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px; text-align:center; }
  .stg .card .tile { width:70px; height:70px; border-radius:18px; background:rgba(%(cy)s,.16); border:1px solid rgba(%(cy)s,.4); display:flex; align-items:center; justify-content:center; }
  .stg .card .tile svg { width:40px; height:40px; } .stg .card .t1 { font-size:34px; font-weight:700; } .stg .card .t2 { font-size:28px; color:rgba(255,255,255,.6); }
  .stg .card .skl { position:absolute; left:0; right:0; bottom:58px; text-align:center; }
  .stg svg .ic { fill:none; stroke:rgb(%(cy)s); stroke-width:3.4; stroke-linecap:round; stroke-linejoin:round; }
  .stg .tgl { width:76px; height:42px; border-radius:21px; background:rgba(255,255,255,.16); position:relative; flex:none; }
  .stg .tgl .on { position:absolute; inset:0; border-radius:21px; background:rgb(%(cy)s); opacity:0; }
  .stg .tgl .knob { position:absolute; left:5px; top:5px; width:32px; height:32px; border-radius:50%%; background:#fff; }
  .stg .cb { position:absolute; border-radius:12px; border:2px solid rgba(255,255,255,.16); background:rgba(255,255,255,.04); }
  .stg .cb .fill { position:absolute; inset:-2px; border-radius:12px; border:2px solid rgba(%(cy)s,.95); background:rgba(%(cy)s,.18); box-shadow:0 0 16px rgba(%(cy)s,.4); opacity:0; }
  .stg .cb svg { position:absolute; inset:18%%; width:64%%; height:64%%; }
  .stg .cb path { fill:none; stroke:rgb(%(cy)s); stroke-width:9; stroke-linecap:round; stroke-linejoin:round; }
  .stg .tile-doc { position:absolute; border-radius:12px; padding:12px; overflow:hidden; }
  .stg .tile-doc .lab { font-size:15px; color:rgba(255,255,255,.75); margin-bottom:8px; } .stg .tile-doc .ln { height:6px; border-radius:3px; background:rgba(255,255,255,.55); margin:7px 0; }
  .stg .tile-doc .val { position:absolute; left:12px; bottom:10px; font-size:28px; font-weight:700; }
  .stg .scan { position:absolute; top:-10px; bottom:-10px; width:4px; background:rgb(%(cy)s); box-shadow:0 0 24px 6px rgba(%(cy)s,.55); opacity:0; }
  .stg .num-big { font-weight:700; letter-spacing:-.02em; line-height:1; text-align:center; }
  .stg .sub { font-weight:500; text-align:center; }
  .stg .key { display:inline-flex; align-items:center; justify-content:center; min-width:150px; height:150px; padding:0 34px; border-radius:26px;
    background:linear-gradient(180deg,#2b313a,#1c2027); border:1.5px solid rgba(255,255,255,.12); box-shadow:0 10px 0 #11141a, 0 24px 60px rgba(0,0,0,.6); font-size:76px; font-weight:500; }
  .stg .plus { font-size:60px; color:rgba(255,255,255,.55); margin:0 34px; }
  .stg .tl-line { position:absolute; height:3px; background:rgba(255,255,255,.18); transform-origin:0 50%%; }
  .stg .tl-fill { position:absolute; height:3px; background:rgb(%(cy)s); box-shadow:0 0 12px rgba(%(cy)s,.7); transform-origin:0 50%%; }
  .stg .tl-node { position:absolute; width:18px; height:18px; margin:-7.5px 0 0 -9px; border-radius:50%%; background:#fff; border:3px solid #06080c; box-shadow:0 0 0 2px rgba(255,255,255,.4); }
  .stg .tl-lab { position:absolute; font-size:28px; color:rgba(255,255,255,.65); transform:translateX(-50%%); white-space:nowrap; }
  .stg .vsdot { position:absolute; width:64px; height:64px; border-radius:50%%; background:#11151c; border:1.5px solid rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:700; }
  .stg .term { font-family:'SF Mono',Menlo,monospace; white-space:pre; }
  .stg .caret { display:inline-block; width:.55em; height:1.05em; background:#fff; vertical-align:-.15em; margin-left:2px; }
  .stg .hlbox { position:absolute; inset:-10px -14px; border-radius:10px; border:2px solid rgba(%(cy)s,.9); box-shadow:0 0 24px rgba(%(cy)s,.4); opacity:0; }
  .stg .wd { display:inline-block; opacity:0; } .stg .wd.em { color:rgb(%(cy)s); }
  .stg .tw { padding:30px 36px; } .stg .tw .hd { display:flex; align-items:center; gap:14px; margin-bottom:18px; }
  .stg .tw .av { width:54px; height:54px; border-radius:50%%; background:#2a2f38; display:flex; align-items:center; justify-content:center; overflow:hidden; }
  .stg .tw .nm { font-size:30px; font-weight:700; } .stg .tw .hn { font-size:19px; color:rgba(255,255,255,.5); } .stg .tw .fl { color:#1d9bf0; font-weight:700; }
  .stg .tw .vf { display:inline-block; width:20px; height:20px; border-radius:50%%; background:#1d9bf0; vertical-align:-3px; margin-left:4px; }
  .stg .tw .xl { position:absolute; right:34px; top:30px; font-size:34px; font-weight:700; }
  .stg .doc-body, .stg .tw .bd { --ink: rgba(255,255,255,.94); color: var(--ink); }
  .stg .pg { padding:44px 56px; overflow:hidden; }
  .stg .pg.light { background:#f6f5f1; border:none; color:#1d1d1f; } .stg .pg.light .doc-body { --ink: #2b2b2e; }
  .stg .pg .kick { font-size:17px; letter-spacing:.08em; text-transform:uppercase; color:rgba(0,0,0,.5); margin-bottom:10px; }
  .stg .pg.dark .kick { color:rgba(255,255,255,.5); }
  .stg .pg h1 { margin:0 0 14px; font-size:44px; line-height:1.15; font-weight:700; } .stg .pg.serif h1, .stg .pg.serif p { font-family: Georgia, 'Times New Roman', serif; font-weight:400; }
  .stg .pg .by { font-size:17px; color:rgba(0,0,0,.45); margin-bottom:26px; } .stg .pg.dark .by { color:rgba(255,255,255,.45); }
  .stg .pg p { font-size:30px; line-height:1.55; margin:0 0 22px; }
  .stg .mk { background-image: linear-gradient(rgba(%(cy)s,.55), rgba(%(cy)s,.55)); background-repeat:no-repeat; background-size:0%% 100%%; border-radius:3px; color: inherit; }
  .stg .pg.light .mk { background-image: linear-gradient(rgba(%(cy)s,.75), rgba(%(cy)s,.75)); }
  .stg .mk.on { color: #fff; } .stg .pg.light .mk.on { color:#0b0d10; }
  .stg .bar-col { position:absolute; bottom:0; border-radius:10px 10px 0 0; background:linear-gradient(180deg,#9aa0aa,#5f656f); transform-origin:50%% 100%%; }
  .stg .bar-col.hl { background:linear-gradient(180deg, rgb(%(cy)s), rgba(%(cy)s,.55)); box-shadow:0 0 30px rgba(%(cy)s,.5); }
  .stg .bar-v { position:absolute; font-size:30px; font-weight:700; text-align:center; transform:translateX(-50%%); }
  .stg .bar-l { position:absolute; font-size:28px; color:rgba(255,255,255,.7); text-align:center; transform:translateX(-50%%); white-space:nowrap; }
  .stg .logo-tile { border-radius:22px; background:#fff; display:flex; align-items:center; justify-content:center; box-shadow:0 20px 50px rgba(0,0,0,.5); }
  .stg .logo-tile img { width:66%%; height:66%%; object-fit:contain; }
  .stg .ico-tile { border-radius:50%%; display:flex; align-items:center; justify-content:center; }
  .stg .wire { fill:none; stroke:rgba(255,255,255,.35); stroke-width:3; stroke-linecap:round; }
  .stg .wire-run { fill:none; stroke:rgb(%(cy)s); stroke-width:4; stroke-linecap:round; filter:drop-shadow(0 0 8px rgba(%(cy)s,.9)); }
  .stg .msg { position:absolute; max-width:74%%; font-size:30px; line-height:1.4; padding:12px 20px; border-radius:18px; }
  .stg .msg.user { right:24px; background:rgb(%(cy)s); color:#04191b; font-weight:500; }
  .stg .msg.ai { left:24px; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.1); }
  .stg .prog { position:absolute; height:12px; border-radius:6px; background:rgba(255,255,255,.12); overflow:hidden; }
  .stg .prog i { position:absolute; left:0; top:0; bottom:0; width:100%%; background:rgb(%(cy)s); box-shadow:0 0 14px rgba(%(cy)s,.7); transform-origin:0 50%%; transform:scaleX(0); }
""" % {"cy": CY}


def stage_beat(b, bid, t_in, t_out, icons, attr_anchor):
    """-> (inner_html, js_lines, cues). cues: [(sound name, time, volume)], one per on-screen event."""
    H, JS, cues = [], [], []
    J = JS.append
    sfx_on = b.get("sfx", True)

    def cue(name, t, el=None):
        if not sfx_on or not name or (el is not None and el.get("sfx") is False):
            return
        if el is not None and isinstance(el.get("sfx"), str):
            name = el["sfx"]
        cues.append((name, round(float(t), 3), SFX_VOL.get(name, .25)))

    def anc(e, at):
        a = e.get("anchor")
        return (' data-at="%.3f"%s' % (at, attr_anchor(a))) if a else ""

    def ico(name, size=40, color=None):
        if name == "claude":
            return SPARK.replace('class="spark"', 'class="spark" style="width:%dpx;height:%dpx"' % (size, size))
        st = ' style="width:%dpx;height:%dpx"' % (size, size)
        stroke = ' style="stroke:%s"' % color if color else ""
        return '<svg viewBox="0 0 64 64"%s><path class="ic"%s d="%s"/></svg>' % (st, stroke, icons.get(name, icons["doc"]))

    def rise(sel, at, y=18, dur=0.45, scale=None):
        frm = "opacity: 0, y: %d" % y + (", scale: %.2f" % scale if scale else "")
        to = "opacity: 1, y: 0" + (", scale: 1" if scale else "")
        J("tl.fromTo('%s', { %s }, { %s, duration: %.2f, ease: 'power3.out', immediateRender: false }, %.3f);" % (sel, frm, to, dur, at))
        J("tl.set('%s', { opacity: 0 }, %.3f);" % (sel, t_in))

    def generic(e, eid):
        if e.get("dim") is not None:
            J("tl.to('#%s', { opacity: 0.35, duration: 0.35 }, %.3f);" % (eid, float(e["dim"])))
        if e.get("glow") is not None:
            J("tl.to('#%s-gl', { opacity: 1, duration: 0.3 }, %.3f);" % (eid, float(e["glow"])))
            cue("select", e["glow"], e)
        for mv in e.get("moves", []):
            J("tl.to('#%s', { x: %.0f, y: %.0f, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (eid, mv[0], mv[1], mv[3] if len(mv) > 3 else 0.6, mv[2]))
        if e.get("out") is not None:
            J("tl.to('#%s', { opacity: 0, duration: 0.3 }, %.3f);" % (eid, float(e["out"])))

    def box(eid, e, inner, cls="", extra_style=""):
        x, y = e.get("x", 0), e.get("y", 0)
        wh = "".join("%s:%spx;" % (k2, e[k]) for k, k2 in (("w", "width"), ("h", "height")) if e.get(k) is not None)
        gl = '<div class="glowbox" id="%s-gl"></div>' % eid if e.get("glow") is not None else ""
        return '<div class="el %s" id="%s" style="left:%spx;top:%spx;%s%s"%s>%s%s</div>' % (
            cls, eid, x, y, wh, extra_style, anc(e, float(e.get("at", t_in))), inner, gl)

    # source pills
    if b.get("src") or b.get("domain"):
        pills = ""
        if b.get("src"):
            pills += '<span class="pill" style="font-size:17px;padding:6px 14px">%s</span>' % esc(b["src"])
        if b.get("domain"):
            pills += '<span class="pill" style="font-size:17px;padding:6px 14px;margin-left:%dpx"><span class="dot" style="width:6px;height:6px"></span>%s</span>' % (
                b.get("domain_gap", 120), esc(b["domain"]))
        H.append('<div class="el" id="%s-src" style="left:34px;top:24px" data-layout-ignore>%s</div>' % (bid, pills))
        rise("#%s-src" % bid, t_in + 0.12, y=-10, dur=0.35)

    for i, e in enumerate(b.get("els", [])):
        k = e["k"]
        eid = "%s-%s" % (bid, e.get("id", "e%d" % i))
        at = float(e.get("at", t_in + 0.25))
        snd = DEFAULT_SFX.get(k)
        x, y = e.get("x", 0), e.get("y", 0)

        if k == "window":
            app = e.get("app", "plain")
            title = e.get("title", {"claude-code": "Claude Code", "claude": "Claude", "terminal": "Terminal"}.get(app, ""))
            mark = SPARK if app in ("claude-code", "claude") else ""
            bar = '<div class="bar"><div class="dots"><i></i><i></i><i></i></div>%s</div>' % (
                '<div class="url" data-layout-ignore>%s</div>' % esc(e.get("url", "")) if app == "browser" else "")
            ttl = '<div class="ttl" data-layout-ignore>%s<span>%s</span></div>' % (mark, esc(title)) if app != "browser" else ""
            badge = ""
            if e.get("badge"):
                badge = '<div class="badge" id="%s-bd"><span class="pill" style="border-color:rgba(%s,.7)"><span class="dot"></span>%s</span></div>' % (eid, CY, esc(e["badge"]["text"]))
            H.append(box(eid, e, bar + ttl + badge, "glass win"))
            rise("#" + eid, at, y=30, dur=0.55, scale=0.97)
            cue(snd, at, e)
            if e.get("badge"):
                ba = float(e["badge"]["at"])
                J("tl.fromTo('#%s-bd', { opacity: 0, scale: 0.85 }, { opacity: 1, scale: 1, duration: 0.35, ease: 'back.out(2)', immediateRender: false }, %.3f);" % (eid, ba))
                J("tl.set('#%s-bd', { opacity: 0 }, %.3f);" % (eid, t_in))
                cue("select", ba, None)

        elif k == "rows":
            items = e["items"]
            n = max(e.get("skel", len(items)), len(items))
            rh, gap, w = e.get("rowh", 74), e.get("gap", 14), e.get("w", 760)
            show = float(e.get("show", at))
            rows = []
            for j in range(n):
                it = items[j] if j < len(items) else None
                ry = j * (rh + gap)
                lead = ('<div class="num">%s</div>' % (j + 1)) if e.get("numbered") else (
                    '<div class="ico">%s</div>' % ('<img src="%s">' % esc(it["logo"]) if it and it.get("logo") else (ico(it["icon"], 26) if it and it.get("icon") else "")))
                skel = '<div class="lay" id="%s-r%d-s"><span>%s</span><span>%s</span></div>' % (
                    eid, j, '<i class="sk"></i>' * (3 + j % 2), '<i class="sk"></i>' * 3 if (it and it.get("value")) or e.get("values") else "")
                full = ""
                if it:
                    val = it.get("value", "")
                    full = '<div class="lay" id="%s-r%d-f" style="opacity:0"><span><div class="t1">%s</div>%s</span><span class="val">%s</span></div>' % (
                        eid, j, esc(it["text"]), '<div class="t2">%s</div>' % esc(it["sub"]) if it.get("sub") else "", val)
                rows.append('<div class="row glass" id="%s-r%d" style="top:%dpx;height:%dpx"%s>%s%s%s<div class="glowbox" id="%s-r%d-gl"></div></div>' % (
                    eid, j, ry, rh, anc(it, float(it["at"])) if it else "", lead, skel, full, eid, j))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%spx;height:%spx">%s</div>' % (eid, x, y, w, n * (rh + gap), "".join(rows)))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, show))
            J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            for j in range(n):
                J("tl.fromTo('#%s-r%d', { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out', immediateRender: false }, %.3f);" % (eid, j, show + 0.06 * j))
            cue("pop", show, e)
            prev = None
            for j, it in enumerate(items):
                ta = float(it["at"])
                J("tl.to('#%s-r%d-s', { opacity: 0, duration: 0.18 }, %.3f);" % (eid, j, ta))
                J("tl.fromTo('#%s-r%d-f', { opacity: 0, x: -10 }, { opacity: 1, x: 0, duration: 0.3, ease: 'power2.out', immediateRender: false }, %.3f);" % (eid, j, ta + 0.05))
                if e.get("active", True):
                    J("tl.to('#%s-r%d-gl', { opacity: 1, duration: 0.25 }, %.3f);" % (eid, j, ta))
                    if prev is not None:
                        J("tl.to('#%s-r%d-gl', { opacity: 0, duration: 0.25 }, %.3f);" % (eid, prev, ta))
                prev = j
                cue(snd, ta, e)

        elif k == "cards":
            items = e["items"]
            n = len(items)
            w, h, gap = e.get("w", 1400), e.get("h", 300), e.get("gap", 24)
            cw = (w - gap * (n - 1)) / n
            show = float(e.get("show", at))
            cs = []
            for j, it in enumerate(items):
                cs.append('<div class="card glass" id="%s-c%d" style="left:%.0fpx;top:0;width:%.0fpx;height:%spx"%s>'
                          '<div class="tile">%s</div><div id="%s-c%d-s" class="skl"><i class="sk"></i><i class="sk"></i><i class="sk"></i><i class="sk"></i></div>'
                          '<div id="%s-c%d-f" style="opacity:0"><div class="t1">%s</div><div class="t2">%s</div></div><div class="glowbox" id="%s-c%d-gl"></div></div>' % (
                              eid, j, j * (cw + gap), cw, h, anc(it, float(it["at"])), ico(it.get("icon", "doc")), eid, j, eid, j,
                              esc(it.get("title", "")), esc(it.get("sub", "")), eid, j))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%spx;height:%spx">%s</div>' % (eid, x, y, w, h, "".join(cs)))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, show)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            for j in range(n):
                J("tl.fromTo('#%s-c%d', { opacity: 0, y: 30 }, { opacity: 0.55, y: 0, duration: 0.4, ease: 'power3.out', immediateRender: false }, %.3f);" % (eid, j, show + 0.07 * j))
            cue("pop", show, e)
            for j, it in enumerate(items):
                ta = float(it["at"])
                J("tl.to('#%s-c%d', { opacity: 1, duration: 0.25 }, %.3f);" % (eid, j, ta))
                J("tl.to('#%s-c%d-s', { opacity: 0, duration: 0.15 }, %.3f);" % (eid, j, ta))
                J("tl.fromTo('#%s-c%d-f', { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.3, immediateRender: false }, %.3f);" % (eid, j, ta + 0.05))
                J("tl.to('#%s-c%d-gl', { opacity: 1, duration: 0.25 }, %.3f);" % (eid, j, ta))
                if j:
                    J("tl.to('#%s-c%d-gl', { opacity: 0, duration: 0.25 }, %.3f);" % (eid, j - 1, ta))
                    J("tl.to('#%s-c%d', { opacity: 0.6, duration: 0.25 }, %.3f);" % (eid, j - 1, ta))
                cue("select", ta, e)

        elif k == "toggle":
            w = e.get("w", 820)
            inner = ('<div class="row" style="position:relative;height:%dpx;padding:0 30px;justify-content:space-between">'
                     '<span><div class="t1" id="%s-lb" style="font-size:40px;font-weight:700">%s</div>%s</span>'
                     '<div class="tgl"><div class="on" id="%s-on"></div><div class="knob" id="%s-kn"></div></div></div>') % (
                e.get("h", 110), eid, esc(e.get("label", "")), '<div class="t2" id="%s-sb" style="font-size:28px;opacity:0">%s</div>' % (eid, esc(e["sub"])) if e.get("sub") else "", eid, eid)
            H.append(box(eid, dict(e, w=w), inner, "glass"))
            rise("#" + eid, at, scale=0.98); cue("pop", at, e)
            if e.get("sub_at") is not None and e.get("sub"):
                J("tl.fromTo('#%s-sb', { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: false }, %.3f);" % (eid, float(e["sub_at"])))
            if e.get("hl") is not None:
                J("tl.fromTo('#%s-lb', { color: '#ffffff' }, { color: 'rgb(%s)', duration: 0.3, immediateRender: false }, %.3f);" % (eid, CY, float(e["hl"])))
            if e.get("on") is not None:
                to = float(e["on"])
                J("tl.fromTo('#%s-kn', { x: 0 }, { x: 34, duration: 0.22, ease: 'power2.out', immediateRender: false }, %.3f);" % (eid, to))
                J("tl.fromTo('#%s-on', { opacity: 0 }, { opacity: 1, duration: 0.22, immediateRender: false }, %.3f);" % (eid, to))
                cue(snd, to, e)

        elif k == "checks":
            n, sz, gap = e.get("n", 10), e.get("size", 64), e.get("gap", 18)
            ticks = e.get("ticks") or [float(e["from"]) + j * float(e["every"]) for j in range(int(e.get("count", n)))]
            bx = "".join('<div class="cb" style="left:%dpx;top:0;width:%dpx;height:%dpx"><div class="fill" id="%s-f%d"></div>'
                         '<svg viewBox="0 0 64 64"><path id="%s-k%d" d="M14 33 L27 46 L50 19" pathLength="1" style="stroke-dasharray:1;stroke-dashoffset:1"/></svg></div>' % (
                             j * (sz + gap), sz, sz, eid, j, eid, j) for j in range(n))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:%dpx"%s>%s</div>' % (eid, x, y, n * (sz + gap), sz, anc(e, at), bx))
            rise("#" + eid, at, y=12, dur=0.35)
            last_t = -9.0
            for j, tk in enumerate(ticks[:n]):
                J("tl.fromTo('#%s-f%d', { opacity: 0 }, { opacity: 1, duration: 0.15, immediateRender: false }, %.3f);" % (eid, j, tk))
                J("tl.fromTo('#%s-k%d', { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.22, ease: 'power2.out', immediateRender: false }, %.3f);" % (eid, j, tk))
                if tk - last_t >= 0.14:
                    cue(snd, tk, e); last_t = tk

        elif k == "grid":
            cols, rws = e.get("cols", 7), e.get("rows", 2)
            cw, ch, gap = e.get("cw", 120), e.get("ch", 150), e.get("gap", 14)
            vals = {int(kk): v for kk, v in (e.get("values") or {}).items()}
            tiles = []
            for j in range(cols * rws):
                lab = e.get("label", "").replace("{n}", "%02d" % (j + 1)) if e.get("label") else ""
                lines = "".join('<div class="ln" style="width:%d%%"></div>' % (90 - (q * 17 + j * 7) % 45) for q in range(4))
                v = '<div class="val" id="%s-v%d">%s</div>' % (eid, j, esc(vals[j])) if j in vals else ""
                tiles.append('<div class="tile-doc glass" id="%s-t%d" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><div class="lab" data-layout-ignore>%s</div>%s%s<div class="glowbox" id="%s-t%d-gl"></div></div>' % (
                    eid, j, (j % cols) * (cw + gap), (j // cols) * (ch + gap), cw, ch, esc(lab), lines, v, eid, j))
            gw, gh = cols * (cw + gap) - gap, rws * (ch + gap) - gap
            scan = '<div class="scan" id="%s-sc" style="left:0"></div>' % eid if e.get("scan") else ""
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:%dpx"%s>%s%s</div>' % (eid, x, y, gw, gh, anc(e, at), "".join(tiles), scan))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            J("tl.fromTo('#%s .tile-doc', { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 0.3, stagger: { each: %.3f, grid: [%d, %d], from: 'start' }, ease: 'power2.out', immediateRender: false }, %.3f);" % (
                eid, min(0.035, 0.8 / (cols * rws)), rws, cols, at))
            cue(snd, at, e)
            if e.get("scan"):
                s0, sd = float(e["scan"][0]), float(e["scan"][1])
                J("tl.fromTo('#%s-sc', { opacity: 1, x: 0 }, { opacity: 1, x: %d, duration: %.2f, ease: 'none', immediateRender: false }, %.3f);" % (eid, gw, sd, s0))
                J("tl.to('#%s-sc', { opacity: 0, duration: 0.2 }, %.3f);" % (eid, s0 + sd))
                cue("scan", s0, e)
            picks = e.get("pick", [])
            if picks:
                p0 = min(float(p[1]) for p in picks)
                pick_set = {int(p[0]) for p in picks}
                J("tl.to([%s], { opacity: 0.35, duration: 0.3 }, %.3f);" % (",".join("'#%s-t%d'" % (eid, j) for j in range(cols * rws) if j not in pick_set), p0))
                for p in picks:
                    J("tl.to('#%s-t%d-gl', { opacity: 1, duration: 0.25 }, %.3f);" % (eid, int(p[0]), float(p[1])))
                for tp in sorted({round(float(p[1]), 2) for p in picks}):
                    cue("select", tp, e)

        elif k in ("count", "big"):
            size = e.get("size", 200 if k == "big" else 120)
            align = e.get("align", "center")
            if k == "count":
                dec = e.get("decimals", 0)
                fmt0 = ("{:,.%df}" % dec).format(float(e.get("from", 0)))
                num = '<span id="%s-n">%s%s%s</span>' % (eid, esc(e.get("prefix", "")), fmt0, esc(e.get("suffix", "")))
                if e.get("of"):
                    num += '<span style="font-size:.45em;color:rgba(255,255,255,.7)"> %s</span>' % esc(e["of"])
            else:
                num = esc(e["text"])
            sub = ""
            if e.get("sub"):
                em = set(e.get("sub_em", []))
                sub = '<div class="sub" style="font-size:%dpx;margin-top:18px">%s</div>' % (
                    e.get("sub_size", 44), " ".join('<span class="cy">%s</span>' % esc(w2) if q in em else esc(w2) for q, w2 in enumerate(e["sub"].split(" "))))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%spx;text-align:%s"%s><div class="num-big" style="font-size:%dpx">%s</div>%s</div>' % (
                eid, x, y, e.get("w", 900), align, anc(e, at), size, num, sub))
            rise("#" + eid, at, y=26, dur=0.5, scale=0.92)
            if k == "count":
                dur = float(e.get("dur", 1.0))
                J("(function(){ var el = document.getElementById('%s-n'); var p = { n: %s }; tl.fromTo(p, { n: %s }, { n: %s, duration: %.2f, ease: 'power2.out', immediateRender: false, "
                  "onUpdate: function(){ el.textContent = %s + p.n.toLocaleString('en-US', { minimumFractionDigits: %d, maximumFractionDigits: %d }) + %s; } }, %.3f); })();" % (
                      eid, float(e.get("from", 0)), float(e.get("from", 0)), float(e["to"]), dur, repr(e.get("prefix", "")), dec, dec, repr(e.get("suffix", "")), at))
                cue("count", at, e); cue(snd, at + dur - 0.05, e)
            else:
                cue(snd, at, e)

        elif k == "keys":
            ks = e["keys"]
            gap = float(e.get("gap", 0.35))
            parts = []
            for j, kk in enumerate(ks):
                if j:
                    parts.append('<span class="plus" id="%s-p%d" style="opacity:0">+</span>' % (eid, j))
                parts.append('<span class="key" id="%s-k%d" style="opacity:0">%s</span>' % (eid, j, esc(kk)))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%spx;display:flex;align-items:center;justify-content:center"%s>%s</div>' % (
                eid, x, y, e.get("w", 900), anc(e, at), "".join(parts)))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            for j in range(len(ks)):
                tk = at + j * gap
                if j:
                    J("tl.fromTo('#%s-p%d', { opacity: 0 }, { opacity: 1, duration: 0.2, immediateRender: false }, %.3f);" % (eid, j, tk - 0.1))
                J("tl.fromTo('#%s-k%d', { opacity: 0, y: -40 }, { opacity: 1, y: 0, duration: 0.28, ease: 'back.out(1.8)', immediateRender: false }, %.3f);" % (eid, j, tk))
                J("tl.to('#%s-k%d', { y: 8, duration: 0.08, yoyo: true, repeat: 1 }, %.3f);" % (eid, j, tk + 0.3 + (len(ks) - 1 - j) * 0.0))
                cue(snd, tk + 0.3, e)

        elif k == "timeline":
            w = e.get("w", 1400)
            parts = ['<div class="tl-line" id="%s-ln" style="left:0;top:0;width:%dpx"></div>' % (eid, w),
                     '<div class="tl-fill" id="%s-fl" style="left:0;top:0;width:%dpx;transform:scaleX(0)"></div>' % (eid, w)]
            if e.get("end"):
                parts.append('<div class="tl-lab" style="left:%dpx;top:22px">%s</div>' % (w - 30, esc(e["end"])))
            for j, nd in enumerate(e.get("nodes", [])):
                nx = nd["pos"] * w
                parts.append('<div class="tl-node" id="%s-n%d" style="left:%.0fpx;top:0;opacity:0"></div>' % (eid, j, nx))
                if nd.get("label"):
                    parts.append('<div class="tl-lab" id="%s-l%d" style="left:%.0fpx;top:22px;opacity:0">%s</div>' % (eid, j, nx, esc(nd["label"])))
                if nd.get("pill"):
                    parts.append('<div id="%s-q%d" style="position:absolute;left:%.0fpx;top:%dpx;opacity:0;transform:translateX(-12px)"><span class="pill" style="font-size:24px;padding:9px 20px">%s</span></div>' % (
                        eid, j, nx - 12, -70 - 58 * nd.get("stack", 0), esc(nd["pill"])))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:4px"%s>%s</div>' % (eid, x, y, w, anc(e, at), "".join(parts)))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            J("tl.fromTo('#%s-ln', { scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: 'power2.inOut', immediateRender: false }, %.3f);" % (eid, at))
            last = 0.0
            for j, nd in enumerate(e.get("nodes", [])):
                ta = float(nd["at"])
                J("tl.fromTo('#%s-fl', { scaleX: %.4f }, { scaleX: %.4f, duration: 0.5, ease: 'power2.inOut', immediateRender: false }, %.3f);" % (eid, last, nd["pos"], ta - 0.2))
                last = nd["pos"]
                J("tl.fromTo('#%s-n%d', { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(2)', immediateRender: false }, %.3f);" % (eid, j, ta))
                if nd.get("label"):
                    J("tl.fromTo('#%s-l%d', { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: false }, %.3f);" % (eid, j, ta))
                if nd.get("pill"):
                    J("tl.fromTo('#%s-q%d', { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out', immediateRender: false }, %.3f);" % (eid, j, ta + 0.05))
                cue(snd, ta, e)

        elif k == "vs":
            w, h = e.get("w", 1100), e.get("h", 300)
            cw = (w - 40) / 2

            def side(s, sid):
                return ('<div class="card glass" id="%s" style="left:%.0fpx;top:0;width:%.0fpx;height:%dpx"><div class="tile">%s</div>'
                        '<div class="t1" style="font-size:38px">%s</div><div class="t2">%s</div><div class="glowbox" id="%s-gl"></div></div>') % (
                    sid, 0 if sid.endswith("-a") else cw + 40, cw, h, ico(s.get("icon", "doc")), esc(s["title"]), esc(s.get("sub", "")), sid)
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:%dpx"%s>%s%s<div class="vsdot" data-layout-ignore style="left:%.0fpx;top:%.0fpx">vs</div></div>' % (
                eid, x, y, w, h, anc(e, at), side(e["left"], eid + "-a"), side(e["right"], eid + "-b"), w / 2 - 32, h / 2 - 32))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            ra = float(e.get("right_at", at + 0.5))
            J("tl.fromTo('#%s-a', { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.45, ease: 'power3.out', immediateRender: false }, %.3f);" % (eid, at))
            J("tl.fromTo('#%s-b', { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: 0.45, ease: 'power3.out', immediateRender: false }, %.3f);" % (eid, ra))
            J("tl.to('#%s-b-gl', { opacity: 1, duration: 0.3 }, %.3f);" % (eid, ra + 0.3))
            cue(snd, at, e); cue("select", ra, e)

        elif k == "type":
            size, cps = e.get("size", 38), float(e.get("cps", 28))
            prompt = e.get("prompt", "❯")
            s = e["text"]
            hl = '<div class="hlbox" id="%s-hl"></div>' % eid if e.get("hl") is not None else ""
            H.append('<div class="el term" id="%s" style="left:%spx;top:%spx;font-size:%dpx"%s><span style="position:relative">%s'
                     '<span style="color:rgba(255,255,255,.55)">%s </span><span id="%s-tx"></span><span class="caret" id="%s-cr"></span></span></div>' % (
                         eid, x, y, size, anc(e, at), hl, esc(prompt), eid, eid))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at - 0.15)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            dur = len(s) / cps
            J("(function(){ var el = document.getElementById('%s-tx'); var s = %s; var p = { n: 0 }; tl.fromTo(p, { n: 0 }, { n: s.length, duration: %.3f, ease: 'none', immediateRender: false, "
              "onUpdate: function(){ el.textContent = s.slice(0, Math.floor(p.n)); } }, %.3f); el.textContent = ''; })();" % (eid, repr(s), dur, at))
            J("tl.set('#%s-cr', { opacity: 0 }, %.3f);" % (eid, at + dur + 0.4))
            if e.get("hl") is not None:
                J("tl.fromTo('#%s-hl', { opacity: 0 }, { opacity: 1, duration: 0.25, immediateRender: false }, %.3f);" % (eid, float(e["hl"])))
                cue("select", e["hl"], e)
            if sfx_on and e.get("sfx") is not False:
                cues.append(("typing", round(at, 3), 0.16, round(dur, 2)))

        elif k == "text":
            size, every = e.get("size", 64), float(e.get("every", 0.09))
            em = set(e.get("em", []))
            ws = e["text"].split(" ")
            spans = " ".join('<span class="wd%s" id="%s-w%d">%s</span>' % (" em" if q in em else "", eid, q, esc(w2)) for q, w2 in enumerate(ws))
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%spx;font-size:%dpx;font-weight:%d;text-align:%s;line-height:1.2;color:%s"%s>%s</div>' % (
                eid, x, y, e.get("w", 1600), size, e.get("weight", 700), e.get("align", "center"), e.get("color", "#fff"), anc(e, at), spans))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            wt = e.get("word_at") or [at + q * every for q in range(len(ws))]
            for q in range(len(ws)):
                J("tl.fromTo('#%s-w%d', { opacity: 0, y: %d, filter: 'blur(6px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.35, ease: 'power3.out', immediateRender: false }, %.3f);" % (
                    eid, q, int(size * 0.35), float(wt[q])))

        elif k == "pill":
            H.append(box(eid, e, '<span class="pill"%s>%s%s</span>' % (
                ' style="border-color:rgba(%s,.8);box-shadow:0 0 18px rgba(%s,.35)"' % (CY, CY) if e.get("lit") else "",
                '<span class="dot"></span>' if e.get("dot", True) else "", esc(e["text"]))))
            rise("#" + eid, at, y=10, dur=0.3)

        elif k in ("tweet", "page"):
            marks = e.get("marks", [])
            body_cls = "bd" if k == "tweet" else "doc-body"
            paras = [e["text"]] if k == "tweet" else e.get("paras", [])
            out_paras, mjs = [], []
            mi = 0
            for para in paras:
                seg = esc(para)
                for mk in marks:
                    ph = esc(mk[0])
                    if ph in seg and ('data-mk' not in seg.split(ph)[0][-60:]):
                        t0, t1 = float(mk[1]), float(mk[2])
                        words = ph.split(" ")
                        total = sum(len(w2) + 1 for w2 in words)
                        acc, spans = 0.0, []
                        for q, w2 in enumerate(words):
                            ws0 = t0 + (t1 - t0) * acc / total
                            acc += len(w2) + 1
                            ws1 = t0 + (t1 - t0) * acc / total
                            sid = "%s-m%d-%d" % (eid, mi, q)
                            spans.append('<span class="mk" id="%s" data-mk="1">%s%s</span>' % (sid, w2, " " if q < len(words) - 1 else ""))
                            mjs.append("tl.fromTo('#%s', { backgroundSize: '0%% 100%%' }, { backgroundSize: '100%% 100%%', duration: %.3f, ease: 'none', immediateRender: false }, %.3f);" % (sid, max(0.06, ws1 - ws0), ws0))
                            mjs.append("tl.set('#%s', { attr: { class: 'mk on' } }, %.3f);" % (sid, ws0))
                            mjs.append("tl.set('#%s', { attr: { class: 'mk' } }, %.3f);" % (sid, t_in))
                        seg = seg.replace(ph, "".join(spans), 1)
                        mi += 1
                out_paras.append(seg)
            if k == "tweet":
                head = ('<div class="hd"><div class="av">%s</div><div><div class="nm">%s%s</div><div class="hn" data-layout-ignore>%s · <span class="fl">Follow</span></div></div></div><div class="xl">𝕏</div>') % (
                    ('<img src="%s" style="width:100%%;height:100%%;object-fit:cover">' % esc(e["avatar"])) if e.get("avatar") else ico(e.get("icon", "claude"), 34),
                    esc(e["name"]), '<span class="vf"></span>' if e.get("verified", True) else "", esc(e.get("handle", "")))
                inner = head + '<div class="bd" id="%s-bd" style="font-size:%dpx;line-height:1.45">%s</div>' % (eid, e.get("size", 30), "<br><br>".join(out_paras))
                H.append(box(eid, dict(e, w=e.get("w", 1100)), inner, "glass tw"))
            else:
                theme = e.get("theme", "light")
                head = ""
                if e.get("kicker"):
                    head += '<div class="kick" data-layout-ignore>%s</div>' % esc(e["kicker"])
                if e.get("title"):
                    head += '<h1>%s</h1>' % esc(e["title"])
                if e.get("byline"):
                    head += '<div class="by" data-layout-ignore>%s</div>' % esc(e["byline"])
                inner = '<div id="%s-sc">%s<div class="doc-body" id="%s-bd">%s</div></div>' % (eid, head, eid, "".join("<p>%s</p>" % p for p in out_paras))
                H.append(box(eid, dict(e, w=e.get("w", 1300), h=e.get("h", 760)), inner, "glass pg %s%s" % (theme, " serif" if e.get("serif") else "")))
            rise("#" + eid, at, y=40, dur=0.55, scale=0.97)
            cue(snd, at, e)
            if marks:
                first = min(float(m[1]) for m in marks)
                dim = "rgba(43,43,46,.42)" if (k == "page" and e.get("theme", "light") == "light") else "rgba(255,255,255,.42)"
                ink = "#2b2b2e" if (k == "page" and e.get("theme", "light") == "light") else "rgba(255,255,255,.94)"
                J("tl.fromTo('#%s-bd', { '--ink': '%s' }, { '--ink': '%s', duration: 0.4, immediateRender: false }, %.3f);" % (eid, ink, dim, first - 0.1))
                JS.extend(mjs)
            for sc in e.get("scroll", []):
                J("tl.to('#%s-sc', { y: %d, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (eid, -int(sc[0]), sc[2] if len(sc) > 2 else 0.8, float(sc[1])))

        elif k == "bars":
            data = e["data"]
            w, h = e.get("w", 1300), e.get("h", 520)
            n = len(data)
            vmax = max(float(d[1]) for d in data)
            slot = w / n
            bw = slot * 0.62
            every = float(e.get("every", 0.08))
            parts = []
            hls = {int(hh[0]): float(hh[1]) for hh in e.get("hl", [])}
            for j, d in enumerate(data):
                bh = max(6, h * float(d[1]) / vmax)
                cx = slot * j + slot / 2
                parts.append('<div class="bar-col%s" id="%s-b%d" style="left:%.0fpx;width:%.0fpx;height:%.0fpx;bottom:60px"></div>' % (
                    " hl" if j in hls and e.get("hl_static") else "", eid, j, cx - bw / 2, bw, bh))
                parts.append('<div class="bar-v" id="%s-v%d" style="left:%.0fpx;bottom:%.0fpx;opacity:0">%s%s</div>' % (eid, j, cx, 60 + bh + 10, esc(str(d[1])), esc(e.get("unit", ""))))
                parts.append('<div class="bar-l" style="left:%.0fpx;bottom:22px">%s</div>' % (cx, esc(d[0])))
                if len(d) > 2:
                    parts.append('<div class="bar-l" style="left:%.0fpx;bottom:-34px;font-size:28px;color:rgba(255,255,255,.45)">%s</div>' % (cx, esc(d[2])))
            ttl = '<div style="position:absolute;left:0;right:0;top:-80px;text-align:center;font-size:44px;font-weight:700">%s</div>' % e["title"] if e.get("title") else ""
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:%dpx"%s>%s%s</div>' % (eid, x, y, w, h + 60, anc(e, at), ttl, "".join(parts)))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            for j in range(n):
                J("tl.fromTo('#%s-b%d', { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: 'power3.out', immediateRender: false }, %.3f);" % (eid, j, at + j * every))
                J("tl.fromTo('#%s-v%d', { opacity: 0 }, { opacity: 1, duration: 0.25, immediateRender: false }, %.3f);" % (eid, j, at + j * every + 0.35))
            cue(snd, at, e)
            for j, th in hls.items():
                J("tl.set('#%s-b%d', { attr: { class: 'bar-col hl' } }, %.3f);" % (eid, j, th))
                J("tl.set('#%s-b%d', { attr: { class: 'bar-col' } }, %.3f);" % (eid, j, t_in))
                cue("select", th, e)

        elif k == "logo":
            sz = e.get("size", 130)
            lab = '<div style="position:absolute;left:%dpx;top:%dpx;font-size:%dpx;font-weight:700;white-space:nowrap">%s</div>' % (
                sz + 24, sz / 2 - e.get("lsize", 36) * 0.62, e.get("lsize", 36), esc(e["label"])) if e.get("label") else ""
            H.append(box(eid, e, '<div class="logo-tile" style="width:%dpx;height:%dpx"><img src="%s"></div>%s' % (sz, sz, esc(e["src"]), lab)))
            rise("#" + eid, at, y=0, dur=0.4, scale=0.6)
            cue(snd, at, e)

        elif k == "icon":
            sz = e.get("size", 120)
            c = {"cyan": "rgb(%s)" % CY, "amber": "#FFB904", "magenta": "#CD00EE", "white": "#fff"}.get(e.get("color", "cyan"))
            bg = "rgba(255,255,255,.06)" if e.get("name") != "claude" else "rgba(217,119,87,.10)"
            lab = '<div style="position:absolute;left:50%%;top:%dpx;transform:translateX(-50%%);font-size:%dpx;font-weight:500;white-space:nowrap">%s</div>' % (
                sz + 16, e.get("lsize", 26), esc(e["label"])) if e.get("label") else ""
            H.append(box(eid, dict(e, w=sz, h=sz), '<div class="ico-tile glass" style="width:%dpx;height:%dpx;background:%s;border-radius:50%%">%s</div>%s' % (
                sz, sz, bg, ico(e["name"], int(sz * 0.52), c), lab)))
            rise("#" + eid, at, y=0, dur=0.4, scale=0.7)
            cue(snd, at, e)

        elif k == "wire":
            pts = e["pts"]
            d = "M" + " L".join("%s %s" % (p[0], p[1]) for p in pts)
            run = ""
            if e.get("run") is not None:
                run = '<path class="wire-run" id="%s-r" d="%s" pathLength="1" style="stroke-dasharray:0.12 1;stroke-dashoffset:0.12;opacity:0"/>' % (eid, d)
            H.append('<svg class="el" id="%s" style="left:0;top:0;width:1920px;height:1080px;overflow:visible" viewBox="0 0 1920 1080"><path class="wire" id="%s-p" d="%s" pathLength="1" style="stroke-dasharray:1;stroke-dashoffset:1"/>%s</svg>' % (eid, eid, d, run))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, at)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            J("tl.fromTo('#%s-p', { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: %.2f, ease: 'power2.inOut', immediateRender: false }, %.3f);" % (eid, e.get("dur", 0.5), at))
            if e.get("run") is not None:
                tr = float(e["run"])
                J("tl.fromTo('#%s-r', { opacity: 1, strokeDashoffset: 0.12 }, { opacity: 1, strokeDashoffset: -1, duration: %.2f, ease: 'power1.inOut', immediateRender: false }, %.3f);" % (eid, e.get("run_dur", 0.9), tr))
                J("tl.set('#%s-r', { opacity: 0 }, %.3f);" % (eid, tr + e.get("run_dur", 0.9)))
                cue("swoosh-out" if e.get("run_sfx") else None, tr, e)

        elif k == "chat":
            w = e.get("w", 760)
            ys, parts = 0, []
            for j, m in enumerate(e["msgs"]):
                parts.append('<div class="msg %s" id="%s-m%d" style="top:%dpx;opacity:0">%s%s</div>' % (
                    m.get("who", "user"), eid, j, ys, (SPARK.replace('class="spark"', 'class="spark" style="width:20px;height:20px;vertical-align:-4px;margin-right:8px"') if m.get("who") == "ai" else ""), esc(m["text"])))
                ys += m.get("h", 74)
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:%dpx">%s</div>' % (eid, x, y, w, ys, "".join(parts)))
            J("tl.set('#%s', { opacity: 1 }, %.3f);" % (eid, float(e["msgs"][0]["at"]) - 0.05)); J("tl.set('#%s', { opacity: 0 }, %.3f);" % (eid, t_in))
            for j, m in enumerate(e["msgs"]):
                ta = float(m["at"])
                J("tl.fromTo('#%s-m%d', { opacity: 0, y: 14, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: 'back.out(1.6)', immediateRender: false }, %.3f);" % (eid, j, ta))
                cue(snd, ta, e)

        elif k == "progress":
            w = e.get("w", 600)
            lab = '<div style="position:absolute;left:0;top:-44px;font-size:28px;color:rgba(255,255,255,.7)">%s</div>' % esc(e["label"]) if e.get("label") else ""
            H.append('<div class="el" id="%s" style="left:%spx;top:%spx;width:%dpx;height:12px">%s<div class="prog" style="left:0;top:0;width:%dpx"><i id="%s-f"></i></div></div>' % (eid, x, y, w, lab, w, eid))
            rise("#" + eid, at, y=8, dur=0.3)
            last = 0.0
            for st in e.get("steps", []):
                J("tl.fromTo('#%s-f', { scaleX: %.3f }, { scaleX: %.3f, duration: %.2f, ease: 'power2.inOut', immediateRender: false }, %.3f);" % (eid, last, float(st[0]), st[2] if len(st) > 2 else 0.5, float(st[1])))
                last = float(st[0])

        else:
            raise SystemExit("stage element kind %r: window rows cards toggle checks grid count big keys timeline vs type text pill tweet page bars logo icon wire chat progress" % k)

        if k not in ("rows", "cards"):
            generic(e, eid)
        else:
            for kk in ("dim", "out", "moves"):
                if e.get(kk) is not None:
                    generic({kk: e[kk]}, eid)

    # the scene: cut in on a whoosh, every cue at least 0.12 s from the one before, leave on a blur
    J("tl.fromTo('#%s-cam', { opacity: 0, scale: 1.04, filter: 'blur(10px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.32, ease: 'power2.out', immediateRender: false }, %.3f);" % (bid, t_in))
    J("tl.to('#%s-cam', { opacity: 0, scale: 0.98, filter: 'blur(10px)', duration: 0.28, ease: 'power2.in' }, %.3f);" % (bid, t_out - 0.28))
    for c in b.get("cam", []):
        J("tl.to('#%s-cam', { scale: %.3f, x: %.0f, y: %.0f, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (bid, c[0], c[1], c[2], c[4], c[3]))
    if sfx_on and b.get("enter_sfx", True):
        cues.insert(0, ("whoosh", round(t_in, 3), SFX_VOL["whoosh"]))
    kept, last = [], -9.0
    for c in sorted(cues, key=lambda c: c[1]):
        if c[1] - last >= 0.12 or c[0] == "typing":
            kept.append(c)
            if c[0] != "typing":
                last = c[1]
    inner = '<div class="stg" id="%s-stg"><div class="stg-cam" id="%s-cam" style="opacity:0" data-layout-allow-overflow>%s</div></div>' % (bid, bid, "".join(H))
    return inner, JS, kept
