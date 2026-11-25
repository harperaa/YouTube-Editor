"""concept.py: the concept illustration (SKILL.md "Concept illustrations"): a schematic scene that SHOWS the idea working.

Full frame on the wash: a dark rounded panel (faint stripe texture, cyan-to-magenta rim) and one 1920x1080 SVG of line
art. Every element arrives on its own word: strokes draw on (pathLength 1, dashoffset 1 -> 0), wires draw and can run a
light along them, meters fill and change colour step by step, stamps land, checks and crosses draw, counters count and
terminals type from one proxy tween each (seek-safe: no tl.set per step). Colours: cyan = the protagonist and the safe
path, amber = money, value, time saved, magenta = the danger or the mistake, white = structure.

Storyboard beat:
  {"type": "concept", "id": "vslwave", "in": 516.7, "out": 525.9, "anchor": "the one video",
   "title": "THE VSL", "title_at": 517.0,                      # optional small caps title, top left of the panel
   "els": [ {"k": "box", "id": "oven", "x": 300, "y": 300, "w": 760, "h": 470, "at": 517.2, "label": "VSL", "lx": .., "ly": ..},
            {"k": "icon", "name": "user", "x": 560, "y": 420, "size": 180, "color": "cyan", "at": 519.0, "label": "YOUR ICP"},
            {"k": "meter", "x": 1300, "y": 260, "w": 90, "h": 560, "at": 520.0,
             "steps": [[0.25, 520.6, "cyan", "COLD"], [0.6, 521.6, "amber", "LUKEWARM"], [1.0, 523.0, "magenta", "HOT"]]},
            {"k": "glow", "x": .., "y": .., "w": .., "h": .., "steps": [[0.15, t, "cyan"], [0.5, t, "amber"], [0.9, t, "magenta"]]},
            {"k": "wire", "pts": [[x, y], ...], "at": t, "color": "cyan", "run": t2},
            {"k": "text", "x": .., "y": .., "text": "..", "size": 34, "color": "white", "at": t, "align": "middle|start|end", "mono": false},
            {"k": "stamp", "x": .., "y": .., "text": "HOT", "color": "magenta", "at": t, "size": 120, "rot": -8},
            {"k": "check" | "cross", "x": .., "y": .., "size": 70, "at": t, "color": ..},
            {"k": "count", "x": .., "y": .., "to": 10, "prefix": "", "suffix": " min", "at": t, "dur": 1.0, "size": 80},
            {"k": "term", "x": .., "y": .., "w": .., "h": .., "lines": [["$ npm install", t], ...]} ]}
            {"k": "scale", "x": 960, "y": 360, "len": 340, "left": "RISK", "right": "REWARD", "at": t, "tilts": [[-12, t1], [-20, t2]]}
Any element may carry "moves": [[dx, dy, t, dur]] (it travels) and "dim": t (it steps back to .32), and "anchor" (its
spoken phrase) for beat-check.
"""
import json

RGB = {"cyan": "10,240,240", "amber": "255,185,4", "magenta": "205,0,238", "white": "255,255,255", "dim": "255,255,255"}


def col(c, a=1.0):
    return "rgba(%s,%.2f)" % (RGB.get(c, RGB["white"]), (0.55 if c == "dim" else 1.0) * a)


def concept_css():
    return """
  .cn-panel { position:absolute; left:70px; top:60px; right:70px; bottom:60px; border-radius:34px;
    background: repeating-linear-gradient(90deg, rgba(255,255,255,.025) 0 2px, transparent 2px 9px), rgba(14,16,24,.94);
    box-shadow: 0 0 0 2px rgba(10,240,240,.35), 0 0 0 6px rgba(205,0,238,.12), 0 40px 120px rgba(0,0,0,.6); }
  .cn-svg { position:absolute; inset:0; width:1920px; height:1080px; overflow:visible; }
  .cn-svg .st { fill:none; stroke-width:3; stroke-linecap:round; stroke-linejoin:round; }
  .cn-svg text { font-family:'DM Sans', sans-serif; font-weight:700; letter-spacing:.04em; }
  .cn-svg text.mono { font-family:'SF Mono', Menlo, monospace; font-weight:500; letter-spacing:0; }
  .cn-title { position:absolute; left:130px; top:104px; font-weight:700; font-size:34px; letter-spacing:.14em; color:rgba(255,255,255,.72); opacity:0; }
"""


def concept_beat(b, bid, t_in, t_out, icons):
    """-> (inner_html, js_lines). icons: the composer's ICONS dict (64-unit line paths)."""
    svg, js = [], []
    J = js.append

    def draw(eid, at, dur=0.55):
        J("tl.fromTo('#%s', { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (eid, dur, at))

    def fade(eid, at, y=14):
        J("tl.fromTo('#%s', { opacity: 0, y: %d }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }, %.3f);" % (eid, y, at))

    def text(eid, x, y, s, size, c, anchor="middle", mono=False, op=1.0):
        return ('<text id="%s" x="%.0f" y="%.0f" font-size="%d" fill="%s" text-anchor="%s"%s style="opacity:0">%s</text>'
                % (eid, x, y, size, col(c, op), anchor, ' class="mono"' if mono else "", s))

    for i, e in enumerate(b.get("els", [])):
        k, eid = e["k"], "%s-%s" % (bid, e.get("id", "e%d" % i))
        n0 = len(svg)
        at = float(e.get("at", t_in + 0.3))
        c = e.get("color", "white")
        if k == "box":
            x, y, w, h, r = e["x"], e["y"], e["w"], e["h"], e.get("r", 18)
            d = "M%.0f %.0f h%.0f a%d %d 0 0 1 %d %d v%.0f a%d %d 0 0 1 -%d %d h-%.0f a%d %d 0 0 1 -%d -%d v-%.0f a%d %d 0 0 1 %d -%d z" % (
                x + r, y, w - 2 * r, r, r, r, r, h - 2 * r, r, r, r, r, w - 2 * r, r, r, r, r, h - 2 * r, r, r, r, r)
            if e.get("fill"):
                svg.append('<path id="%s-f" d="%s" fill="%s" style="opacity:0"/>' % (eid, d, col(e["fill"], 0.10)))
                J("tl.fromTo('#%s-f', { opacity: 0 }, { opacity: 1, duration: 0.5 }, %.3f);" % (eid, at + 0.3))
            svg.append('<path id="%s" class="st" pathLength="1" d="%s" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1"/>' % (eid, d, col(c)))
            draw(eid, at, e.get("dur", 0.7))
            if e.get("label"):
                lx, ly = e.get("lx", x + w / 2), e.get("ly", y - 22)
                svg.append(text(eid + "-l", lx, ly, e["label"], e.get("lsize", 34), e.get("lcolor", c), e.get("lanchor", "middle")))
                fade(eid + "-l", at + 0.35)
        elif k == "line":       # a straight structural stroke (a shelf, a door seam, a kernel bar)
            svg.append('<path id="%s" class="st" pathLength="1" d="M%.0f %.0f L%.0f %.0f" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1;stroke-width:%d"/>'
                       % (eid, e["x1"], e["y1"], e["x2"], e["y2"], col(c, e.get("op", 1.0)), e.get("sw", 3)))
            draw(eid, at, e.get("dur", 0.45))
        elif k == "icon":
            s = e.get("size", 120) / 64.0
            svg.append('<g transform="translate(%.0f %.0f) scale(%.3f)"><path id="%s" class="st" pathLength="1" d="%s" stroke="%s" '
                       'style="stroke-dasharray:1;stroke-dashoffset:1;stroke-width:%.2f"/></g>' % (e["x"], e["y"], s, eid, icons[e["name"]], col(c), 3.0 / s))
            draw(eid, at, e.get("dur", 0.6))
            if e.get("label"):
                svg.append(text(eid + "-l", e["x"] + e.get("size", 120) / 2, e["y"] + e.get("size", 120) + 44, e["label"], e.get("lsize", 30), c))
                fade(eid + "-l", at + 0.3)
        elif k == "wire":
            pts = e["pts"]; d = "M" + " L".join("%.0f %.0f" % (p[0], p[1]) for p in pts)
            svg.append('<path id="%s" class="st" pathLength="1" d="%s" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1"/>' % (eid, d, col(c, 0.85)))
            draw(eid, at, e.get("dur", 0.6))
            if e.get("run"):        # a light runs the wire: a short bright dash travels from start to end
                svg.append('<path id="%s-r" class="st" pathLength="1" d="%s" stroke="%s" style="stroke-width:7;stroke-dasharray:0.06 1;stroke-dashoffset:0.06;opacity:0"/>' % (eid, d, col(c)))
                tr = float(e["run"])
                J("tl.fromTo('#%s-r', { strokeDashoffset: 0.06, opacity: 1 }, { strokeDashoffset: -1, opacity: 1, duration: %.2f, ease: 'power1.inOut' }, %.3f);" % (eid, e.get("run_dur", 0.8), tr))
                J("tl.to('#%s-r', { opacity: 0, duration: 0.15 }, %.3f);" % (eid, tr + e.get("run_dur", 0.8)))
        elif k == "text":
            svg.append(text(eid, e["x"], e["y"], e["text"], e.get("size", 34), c, e.get("align", "middle"), e.get("mono", False), e.get("op", 1.0)))
            fade(eid, at, e.get("rise", 14))
        elif k == "meter":       # a vertical gauge: outline draws, then the fill climbs step by step and changes colour
            x, y, w, h = e["x"], e["y"], e["w"], e["h"]
            svg.append('<rect id="%s-o" class="st" pathLength="1" x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="14" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1"/>' % (eid, x, y, w, h, col("white", 0.8)))
            svg.append('<rect id="%s-f" x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="8" fill="%s"/>' % (eid, x + 10, y + 10, w - 20, h - 20, col(e["steps"][0][2])))
            draw(eid + "-o", at, 0.5)
            prev = 0.0
            for j, (lvl, ts, sc, lab) in enumerate(e["steps"]):
                ts = float(ts)
                if j == 0:
                    J("tl.fromTo('#%s-f', { scaleY: 0, fill: '%s', transformOrigin: '50%% 100%%' }, { scaleY: %.3f, fill: '%s', transformOrigin: '50%% 100%%', duration: 0.7, ease: 'power2.out' }, %.3f);" % (eid, col(sc), lvl, col(sc), ts))
                else:
                    J("tl.to('#%s-f', { scaleY: %.3f, fill: '%s', duration: 0.7, ease: 'power2.out' }, %.3f);" % (eid, lvl, col(sc), ts))
                ty = y + h - (h - 20) * lvl
                if not lab:
                    continue
                svg.append('<path id="%s-t%d" class="st" pathLength="1" d="M%.0f %.0f h40" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1"/>' % (eid, j, x + w + 14, ty, col(sc)))
                svg.append(text("%s-tl%d" % (eid, j), x + w + 70, ty + 12, lab, e.get("lsize", 36), sc, "start"))
                draw("%s-t%d" % (eid, j), ts + 0.2, 0.3)
                fade("%s-tl%d" % (eid, j), ts + 0.3, 0)
                prev = lvl
        elif k == "glow":        # a fill that warms step by step (an oven window, a lit room, a hot wire)
            x, y, w, h = e["x"], e["y"], e["w"], e["h"]
            svg.append('<rect id="%s" x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="%d" fill="%s" style="opacity:0"/>' % (eid, x, y, w, h, e.get("r", 12), col(e["steps"][0][2])))
            for j, (op, ts, sc) in enumerate(e["steps"]):
                if j == 0:
                    J("tl.fromTo('#%s', { opacity: 0, fill: '%s' }, { opacity: %.2f, fill: '%s', duration: 0.7 }, %.3f);" % (eid, col(sc), op, col(sc), float(ts)))
                else:
                    J("tl.to('#%s', { opacity: %.2f, fill: '%s', duration: 0.7 }, %.3f);" % (eid, op, col(sc), float(ts)))
        elif k == "stamp":
            size = e.get("size", 110); tw = len(e["text"]) * size * 0.66 + 70
            svg.append('<g id="%s" style="opacity:0;transform-box:fill-box;transform-origin:50%% 50%%"><g transform="rotate(%d %.0f %.0f)">'
                       '<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="18" fill="none" stroke="%s" stroke-width="7"/>'
                       '<text x="%.0f" y="%.0f" font-size="%d" fill="%s" text-anchor="middle">%s</text></g></g>'
                       % (eid, e.get("rot", -8), e["x"], e["y"], e["x"] - tw / 2, e["y"] - size * 0.82, tw, size * 1.12, col(c), e["x"], e["y"] + size * 0.12, size, col(c), e["text"]))
            J("tl.fromTo('#%s', { opacity: 0, scale: 1.7 }, { opacity: 1, scale: 1, duration: 0.26, ease: 'back.out(2.2)' }, %.3f);" % (eid, at))
        elif k in ("check", "cross"):
            s = e.get("size", 70); x, y = e["x"], e["y"]
            d = ("M%.0f %.0f l%.0f %.0f l%.0f %.0f" % (x, y + s * .5, s * .35, s * .35, s * .65, -s * .75)) if k == "check" else \
                ("M%.0f %.0f l%.0f %.0f M%.0f %.0f l%.0f %.0f" % (x, y, s, s, x + s, y, -s, s))
            svg.append('<path id="%s" class="st" pathLength="1" d="%s" stroke="%s" style="stroke-width:%d;stroke-dasharray:1;stroke-dashoffset:1"/>'
                       % (eid, d, col(e.get("color", "cyan" if k == "check" else "magenta")), e.get("sw", 9)))
            draw(eid, at, 0.3)
        elif k == "count":
            svg.append(text(eid, e["x"], e["y"], "%s0%s" % (e.get("prefix", ""), e.get("suffix", "")), e.get("size", 80), c, e.get("align", "middle")))
            fade(eid, at, 0)
            J("(function(){ var el = document.getElementById('%s'), p = { n: 0 }; tl.fromTo(p, { n: 0 }, { n: %s, duration: %.2f, ease: 'power1.out',"
              " onUpdate: function(){ el.textContent = %s + Math.round(p.n) + %s; } }, %.3f); })();"
              % (eid, e["to"], e.get("dur", 1.0), json.dumps(e.get("prefix", "")), json.dumps(e.get("suffix", "")), at + 0.1))
        elif k == "term":        # a terminal window; each line types from its own proxy tween
            x, y, w, h = e["x"], e["y"], e["w"], e["h"]
            svg.append('<rect id="%s-o" class="st" pathLength="1" x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="16" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1"/>' % (eid, x, y, w, h, col("white", 0.8)))
            draw(eid + "-o", at, 0.5)
            for j, (ln, ts) in enumerate(e["lines"]):
                lid = "%s-ln%d" % (eid, j)
                svg.append('<text id="%s" x="%.0f" y="%.0f" font-size="%d" fill="%s" class="mono" data-full="%s"></text>' % (lid, x + 34, y + 70 + j * 54, e.get("size", 34), col(e.get("color", "white")), ln.replace('"', "&quot;")))
                J("(function(){ var el = document.getElementById('%s'), s = el.getAttribute('data-full'), p = { n: 0 }; el.textContent = '';"
                  " tl.fromTo(p, { n: 0 }, { n: s.length, duration: %.2f, ease: 'none', onUpdate: function(){ el.textContent = s.slice(0, Math.floor(p.n)); } }, %.3f); })();"
                  % (lid, max(0.4, len(ln) * 0.045), float(ts)))
        elif k == "scale":       # a balance: post, a beam that tilts on its words, two pans that stay level and ride the beam ends
            cx, cy, L = e["x"], e["y"], e.get("len", 340)
            lc, rc = e.get("lc", "magenta"), e.get("rc", "cyan")
            svg.append('<path id="%s-post" class="st" pathLength="1" d="M%.0f %.0f V%.0f M%.0f %.0f H%.0f" stroke="%s" style="stroke-dasharray:1;stroke-dashoffset:1"/>'
                       % (eid, cx, cy, cy + 300, cx - 110, cy + 300, cx + 110, col("white", 0.8)))
            svg.append('<g id="%s-beam"><path class="st" d="M%.0f %.0f H%.0f" stroke="%s" style="stroke-width:5"/></g>' % (eid, cx - L, cy, cx + L, col("white")))
            for side, sx, sc, lab in (("lp", cx - L, lc, e.get("left", "")), ("rp", cx + L, rc, e.get("right", ""))):
                svg.append('<g id="%s-%s"><path class="st" d="M%.0f %.0f L%.0f %.0f M%.0f %.0f L%.0f %.0f" stroke="%s"/>'
                           '<path class="st" d="M%.0f %.0f h220 a110 40 0 0 1 -220 0z" stroke="%s" style="stroke-width:4"/>'
                           '<text x="%.0f" y="%.0f" font-size="%d" fill="%s" text-anchor="middle">%s</text></g>'
                           % (eid, side, sx, cy, sx - 100, cy + 150, sx, cy, sx + 100, cy + 150, col("white", 0.7), sx - 110, cy + 150, col(sc),
                              sx, cy + 250, e.get("lsize", 44), col(sc), lab))
            draw(eid + "-post", at, 0.5)
            J("tl.fromTo('#%s-beam, #%s-lp, #%s-rp', { opacity: 0 }, { opacity: 1, duration: 0.4, ease: 'power2.out' }, %.3f);" % (eid, eid, eid, at + 0.3))
            import math
            first = True
            for deg, ts in e.get("tilts", []):
                dy = L * math.sin(math.radians(deg))
                if first:
                    J("tl.fromTo('#%s-beam', { rotation: 0, svgOrigin: '%.0f %.0f' }, { rotation: %.2f, svgOrigin: '%.0f %.0f', duration: 0.8, ease: 'back.out(1.6)' }, %.3f);" % (eid, cx, cy, deg, cx, cy, float(ts)))
                    J("tl.fromTo('#%s-lp', { y: 0 }, { y: %.1f, duration: 0.8, ease: 'back.out(1.6)' }, %.3f);" % (eid, -dy, float(ts)))
                    J("tl.fromTo('#%s-rp', { y: 0 }, { y: %.1f, duration: 0.8, ease: 'back.out(1.6)' }, %.3f);" % (eid, dy, float(ts)))
                    first = False
                else:
                    J("tl.to('#%s-beam', { rotation: %.2f, svgOrigin: '%.0f %.0f', duration: 0.8, ease: 'back.out(1.6)' }, %.3f);" % (eid, deg, cx, cy, float(ts)))
                    J("tl.to('#%s-lp', { y: %.1f, duration: 0.8, ease: 'back.out(1.6)' }, %.3f);" % (eid, -dy, float(ts)))
                    J("tl.to('#%s-rp', { y: %.1f, duration: 0.8, ease: 'back.out(1.6)' }, %.3f);" % (eid, dy, float(ts)))
        else:
            raise SystemExit("concept element kind %r: box line icon wire text meter glow stamp check cross count term scale" % k)
        if e.get("moves") or e.get("dim"):   # any element can travel (moves: [[dx, dy, t, dur]]) or step back (dim: t)
            svg[n0:] = ['<g id="%s-mv">%s</g>' % (eid, "".join(svg[n0:]))]
            first = True
            for mv in e.get("moves", []):
                dx, dy, ts = mv[0], mv[1], float(mv[2]); du = mv[3] if len(mv) > 3 else 0.7
                if first:
                    J("tl.fromTo('#%s-mv', { x: 0, y: 0 }, { x: %.1f, y: %.1f, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (eid, dx, dy, du, ts)); first = False
                else:
                    J("tl.to('#%s-mv', { x: %.1f, y: %.1f, duration: %.2f, ease: 'power2.inOut' }, %.3f);" % (eid, dx, dy, du, ts))
            if e.get("dim"):
                J("tl.to('#%s-mv', { opacity: 0.32, duration: 0.4 }, %.3f);" % (eid, float(e["dim"])))

    title = ""
    if b.get("title"):
        title = '<div class="cn-title" id="%s-title">%s</div>' % (bid, b["title"])
        J("tl.fromTo('#%s-title', { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }, %.3f);" % (bid, float(b.get("title_at", t_in + 0.1))))
    J("tl.fromTo('#%s-panel', { opacity: 0, scale: 0.97 }, { opacity: 1, scale: 1, duration: 0.35, ease: 'power2.out' }, %.3f);" % (bid, t_in))
    inner = ('<div class="cut"><div class="gridbg"></div><div class="cn-panel" id="%s-panel"></div>%s<svg class="cn-svg" viewBox="0 0 1920 1080">%s</svg></div>'
             % (bid, title, "".join(svg)))
    return inner, js
