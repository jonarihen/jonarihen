"""Generate the aaris.tech-styled SVG panels for the GitHub profile README.

Usage: tools/fonts.sh && python3 tools/build.py tools/fonts .
"""
import base64
import io
import random
import sys
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FONTS_DIR = Path(sys.argv[1])
OUT = Path(sys.argv[2])
(OUT / "assets").mkdir(parents=True, exist_ok=True)

# ── Tokens (from aaris.tech src/styles.css) ──────────────────────────────────
BG, RAISE = "#0e1014", "#12151a"
INK, MUT, DIM = "#e9ecef", "#8b939e", "#4d545e"
LINE, SOFT = "#232830", "#1a1e25"
ACC, OK, AMBER = "#ff5a1f", "#3fd97f", "#ffb224"
W = 1000
PAD = 36

FONT_FILES = {
    "disp": "ArchivoDisplay.ttf",
    "sans": "ArchivoRegular.ttf",
    "sans6": "ArchivoSemi.ttf",
    "sans7": "ArchivoBold.ttf",
    "mono": "MonoMedium.ttf",
    "mono6": "MonoSemiBold.ttf",
}
_fonts = {k: TTFont(FONTS_DIR / v) for k, v in FONT_FILES.items()}
_metrics = {}
for k, f in _fonts.items():
    _metrics[k] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)


def tw(text, font, size, ls=0.0):
    """Advance width of text in px; ls is letter-spacing in em."""
    cmap, hmtx, upm = _metrics[font]
    adv = sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in text) / upm * size
    return adv + ls * size * len(text)


def wrap(text, font, size, width, ls=0.0):
    lines, cur = [], ""
    for word in text.split(" "):
        cand = f"{cur} {word}".strip()
        if cur and tw(cand, font, size, ls) > width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


class Svg:
    def __init__(self, h, label):
        self.h = h
        self.label = label
        self.parts = []
        self.used = {}

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, font, size, fill, ls=0.0, anchor="start", extra="", anim=""):
        self.used.setdefault(font, set()).update(s)
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" class="{font}" font-size="{size}" '
            f'fill="{fill}" letter-spacing="{ls * size:.2f}" text-anchor="{anchor}"{extra}>'
            f"{anim}{escape(s)}</text>"
        )
        return tw(s, font, size, ls)

    def spans(self, x, y, runs, font, size, ls=0.0):
        """Inline runs of (text, fill) on one baseline; returns end x."""
        for s, fill in runs:
            x += self.text(x, y, s, font, size, fill, ls)
        return x

    def rect(self, x, y, w, h, fill="none", stroke=None, extra=""):
        st = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{st}{extra}/>')

    def hline(self, x1, x2, y, color=LINE):
        self.add(f'<path d="M{x1} {y + 0.5}H{x2}" stroke="{color}"/>')

    def vline(self, x, y1, y2, color=LINE):
        self.add(f'<path d="M{x + 0.5} {y1}V{y2}" stroke="{color}"/>')

    def led(self, x, y, kind="ok", delay=0.0):
        color = {"ok": OK, "act": AMBER, "off": LINE}[kind]
        cls = {"ok": "led-ok", "act": "led-act", "off": ""}[kind]
        self.add(
            f'<rect x="{x}" y="{y}" width="8" height="8" fill="{color}" class="{cls}" '
            f'style="animation-delay:{delay:.2f}s"/>'
        )

    def screw(self, x, y):
        self.add(f'<rect x="{x + 0.5}" y="{y + 0.5}" width="7" height="7" fill="{LINE}" stroke="{DIM}"/>')

    def render(self, name, grid=True, frame=True):
        faces = []
        for font, chars in sorted(self.used.items()):
            opts = subset.Options()
            opts.flavor = "woff"
            opts.layout_features = ["kern", "liga"]
            opts.name_IDs = []
            opts.notdef_outline = True
            sub = subset.Subsetter(opts)
            f = TTFont(FONTS_DIR / FONT_FILES[font])
            sub.populate(text="".join(chars) + " ")
            sub.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff"
            f.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            faces.append(
                f"@font-face{{font-family:at-{font};src:url(data:font/woff;base64,{b64}) format('woff')}}"
                f".{font}{{font-family:at-{font},{'ui-monospace,monospace' if 'mono' in font else 'system-ui,sans-serif'}}}"
            )
        css = "".join(faces) + (
            ".led-ok{animation:steady 2.6s steps(1) infinite}"
            ".led-act{animation:act .7s steps(1) infinite}"
            "@keyframes steady{0%,92%,100%{opacity:1}94%{opacity:.2}}"
            "@keyframes act{0%,28%{opacity:1}34%,52%{opacity:.15}58%,100%{opacity:1}}"
            ".pulse{stroke-dasharray:90 1400;animation:pulse 3.2s linear infinite}"
            "@keyframes pulse{from{stroke-dashoffset:90}to{stroke-dashoffset:-1310}}"
            ".tick{animation:tick 40s linear infinite}"
            "@keyframes tick{from{transform:translateX(0)}to{transform:translateX(var(--d))}}"
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        )
        bg = [f'<rect width="{W}" height="{self.h}" fill="{BG}"/>']
        if grid:
            bg.append(f'<rect width="{W}" height="{self.h}" fill="url(#grid)" opacity=".55"/>')
        if frame:
            bg.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{self.h - 1}" fill="none" stroke="{LINE}"/>')
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" viewBox="0 0 {W} {self.h}" width="{W}" height="{self.h}" '
            f'role="img" aria-label="{escape(self.label)}">'
            f"<title>{escape(self.label)}</title>"
            f"<defs><style>{css}</style>"
            f'<pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">'
            f'<path d="M48 .5H0M.5 0V48" fill="none" stroke="{SOFT}"/></pattern>'
            f'<pattern id="hatch" width="15" height="15" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
            f'<path d="M14.5 0V15" stroke="{SOFT}"/></pattern></defs>'
            + "".join(bg)
            + "".join(self.parts)
            + "</svg>"
        )
        (OUT / "assets" / f"{name}.svg").write_text(svg)
        print(f"{name}.svg  {len(svg) // 1024} KB")


def sec_head(s, y, no, title, meta):
    """Section header: 'no' in accent mono, display title, meta right-aligned."""
    s.text(PAD, y, no, "mono6", 13, ACC, 0.1)
    s.text(PAD + 38, y, title.upper(), "disp", 34, INK, -0.005)
    s.text(W - PAD, y, meta, "mono", 11, MUT, 0.08, anchor="end")
    s.hline(PAD, W - PAD, y + 22)


# ── 01 Header ────────────────────────────────────────────────────────────────
def header():
    s = Svg(0, "Jonathan Aaris Henningsen. IT consultant, datacenter and infrastructure, at Perspektiva IT.")
    # Status bar
    s.add(f'<rect x="1" y="1" width="{W - 2}" height="52" fill="{BG}" fill-opacity=".9"/>')
    s.hline(0, W, 53)
    x = s.text(PAD, 33, "AARIS", "disp", 15, INK, 0.04)
    x += s.text(PAD + x, 33, ".", "disp", 15, ACC, 0.04)
    s.text(PAD + x, 33, "TECH", "disp", 15, INK, 0.04)
    nx = 300
    for no, label in [("01", "OPERATOR"), ("02", "RACK-01"), ("03", "CERTS"), ("04", "UPLINK")]:
        nx = s.spans(nx, 32, [(no + " ", ACC), (label, MUT)], "mono6", 10.5, 0.14) + 26
    right = "GITHUB / JONARIHEN"
    rw = tw(right, "mono", 11, 0.08)
    s.led(W - PAD - rw - 18, 24, "ok")
    s.text(W - PAD, 32, right, "mono", 11, MUT, 0.08, anchor="end")

    y = 112
    s.spans(PAD, y, [("01 / OPERATOR", ACC), (" — TECHNICAL DOSSIER · HUMAN, MOSTLY SELF-HOSTING", DIM)], "mono", 11.5, 0.22)

    # Split-flap name: each glyph cycles through random characters, then locks
    # left-to-right. Uses SMIL <set> so the final glyph still shows without it.
    pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ0123456789#%/&*+="
    rng = random.Random(5560)
    size, lh = 100, 96
    y += 30
    for row, (word, color, delay) in enumerate([("JONATHAN", INK, 0), ("AARIS", ACC, 0.35), ("HENNINGSEN", INK, 0.65)]):
        y += lh
        x = PAD
        for i, ch in enumerate(word):
            adv = tw(ch, "disp", size, -0.01)
            cx = x + (adv - size * 0.01) / 2
            lock = delay + 0.2 + i * 0.055 + rng.random() * 0.14
            t = 0.0
            while t < lock:
                g = rng.choice(pool)
                s.text(cx, y, g, "disp", size, color, anchor="middle", extra=' opacity="0"',
                       anim=f'<set attributeName="opacity" to="1" begin="{t:.3f}s" dur="0.048s"/>')
                t += 0.048
            s.text(cx, y, ch, "disp", size, color, anchor="middle",
                   anim=f'<set attributeName="opacity" to="0" begin="0s" dur="{lock:.3f}s"/>')
            x += adv

    # Intro + nameplate
    y += 52
    top = y
    intro = (
        "IT consultant at Perspektiva IT, where I look after the datacenter and backup — "
        "Nutanix hosting, HYCU, Fortinet networks, and a lot of Linux. I'd rather automate "
        "and improve than just keep the lights on. Evenings belong to a homelab that's "
        "honestly gotten a bit out of hand: Proxmox, TrueNAS, Docker, FortiGate."
    )
    ly = top + 18
    for line in wrap(intro, "sans", 16.5, 440):
        s.text(PAD, ly, line, "sans", 16.5, MUT)
        ly += 30

    px, pw = 530, W - PAD - 530
    rows = [
        ("ROLE", "IT CONSULTANT — DATACENTER & INFRASTRUCTURE", INK),
        ("LOC", "REGION SJÆLLAND, DK", INK),
        ("UPTIME", "CONTINUOUS · SINCE FEB 2020", OK),
        ("STACK", "NUTANIX / FORTINET / ALMALINUX / HYCU / PROXMOX", INK),
        ("DUTY", "DATACENTER & BACKUP OPS @ PERSPEKTIVA IT", INK),
        ("S/N", "JAH-DK-5560 · REV 2026.10", INK),
    ]
    body = []
    for k, v, c in rows:
        body.append((k, wrap(v, "mono", 12, pw - 32 - 92, 0.02), c))
    ph = 40 + sum(22 + 18.6 * len(ls) for _, ls, _ in body) + 52
    s.rect(px + 0.5, top + 0.5, pw - 1, ph - 1, RAISE, LINE)
    s.text(px + 16, top + 25, "ASSET TAG // OPERATOR", "mono6", 10.5, MUT, 0.16)
    s.text(px + pw - 16, top + 25, "OPERATIONAL", "mono6", 10.5, OK, 0.16, anchor="end")
    s.led(px + pw - 16 - tw("OPERATIONAL", "mono6", 10.5, 0.16) - 16, top + 17, "ok")
    s.hline(px, px + pw, top + 40)
    ry = top + 40
    for i, (k, ls, c) in enumerate(body):
        h = 22 + 18.6 * len(ls)
        s.text(px + 16, ry + 25, k, "mono", 12, DIM, 0.08)
        for j, line in enumerate(ls):
            s.text(px + 16 + 106, ry + 25 + j * 18.6, line, "mono", 12, c, 0.02)
        ry += h
        if i < len(body) - 1:
            s.hline(px, px + pw, ry, SOFT)
    # Barcode
    bx, bars = px + 16, []
    pattern = [(0, 1), (4, 3), (9, 1), (14, 1)]
    while bx < px + pw - 34:
        for off, w in pattern:
            if bx + off + w <= px + pw - 16:
                bars.append(f'<rect x="{bx + off}" y="{ry + 12}" width="{w}" height="26"/>')
        bx += 17
    s.add(f'<g fill="{MUT}" opacity=".7">{"".join(bars)}</g>')

    # Trace line under the nameplate
    ty = top + ph + 22
    d = f"M{px} {ty + 46}H{px + 80}V{ty + 10}H{px + 190}V{ty + 46}H{px + 310}V{ty + 10}H{px + pw}"
    s.add(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.5"/>')
    s.add(f'<path d="{d}" fill="none" stroke="{ACC}" stroke-width="1.5" class="pulse"/>')
    for vx, vy in [(80, 46), (80, 10), (190, 10), (190, 46), (310, 46), (310, 10)]:
        s.add(f'<rect x="{px + vx - 3}" y="{ty + vy - 3}" width="6" height="6" fill="{BG}" stroke="{DIM}"/>')

    s.h = int(max(ly, ty + 60) + 34)
    s.render("header")


# ── Ticker ───────────────────────────────────────────────────────────────────
def ticker():
    items = ["NUTANIX AHV", "FORTIGATE", "FORTIMANAGER", "ALMALINUX", "DEBIAN", "PROXMOX VE",
             "PROXMOX BACKUP SERVER", "HYCU R-CLOUD", "DATTO SIRIS", "TRUENAS SCALE", "ZFS", "DOCKER",
             "PFSENSE", "WIREGUARD", "IPSEC", "CADDY", "NGINX", "GRAYLOG", "ACTIVE DIRECTORY"]
    s = Svg(44, "Stack: " + ", ".join(items))
    x, g = 0.0, []
    for copy in range(2):
        for it in items:
            sub = Svg(0, "")
            x0 = x
            x += sub.text(x, 26.5, "///", "mono", 11, ACC)
            x += 22
            x += sub.text(x, 26.5, it, "mono", 11, MUT, 0.18) + 22
            g += sub.parts
            for f, c in sub.used.items():
                s.used.setdefault(f, set()).update(c)
        if copy == 0:
            half = x
    s.add(f'<g class="tick" style="--d:-{half:.1f}px">{"".join(g)}</g>')
    s.hline(0, W, 0)
    s.hline(0, W, 43)
    s.render("ticker", grid=False, frame=False)


# ── Capability matrix ────────────────────────────────────────────────────────
def capability():
    skills = [
        ("VIRTUALIZATION & HOSTING", ["Nutanix AHV / Prism", "Proxmox VE", "VMware ESXi"]),
        ("BACKUP & RESTORE", ["HYCU R-Cloud", "Proxmox Backup Server", "Datto Siris", "Offsite S3 backup"]),
        ("NETWORK & SECURITY", ["Fortinet FortiGate & FortiManager", "pfSense", "Zyxel", "VLAN / VPN", "Certificate management"]),
        ("OS & OPERATIONS", ["AlmaLinux", "Debian", "Windows Server", "Active Directory"]),
        ("AUTOMATION & TOOLING", ["Docker", "Scripting", "Reverse proxy — Caddy & Nginx", "Centralized logging — Graylog"]),
    ]
    s = Svg(0, "Capability matrix. " + " ".join(f"{k}: {', '.join(v)}." for k, v in skills))
    s.text(PAD + 12, 44, "CAPABILITY MATRIX", "mono6", 11, MUT, 0.18)
    s.hline(PAD, W - PAD, 58)
    y = 59
    col = PAD + 240
    for key, items in skills:
        # lay items out with " / " separators, wrapping at the right edge
        lines, cur, cx = [[]], 0, col
        for i, it in enumerate(items):
            iw = tw(it, "mono", 13)
            sep = 30 if i < len(items) - 1 else 0
            if cx + iw > W - PAD - 12 and lines[-1]:
                lines.append([])
                cx = col
            lines[-1].append((cx, it, i < len(items) - 1))
            cx += iw + sep
        h = 32 + 23 * len(lines)
        s.text(PAD + 12, y + 31, key, "mono6", 11, ACC, 0.14)
        for li, line in enumerate(lines):
            for cx, it, more in line:
                s.text(cx, y + 31 + li * 23, it, "mono", 13, INK)
                if more:
                    s.text(cx + tw(it, "mono", 13) + 10, y + 31 + li * 23, "/", "mono", 13, DIM)
        y += h
        s.hline(PAD, W - PAD, y - 1, SOFT)
    s.h = int(y + 28)
    s.render("capability")


# ── 02 Rack-01 ───────────────────────────────────────────────────────────────
PROJECTS = [
    ("homelabrrr", "Homelabrrr", 2,
     "Self-service portal for a Proxmox homelab with FortiGate-backed networking. Users get assigned VMs "
     "and LXCs with browser VNC, SSH and SFTP; admins manage hosts, VLANs, firewall policies, port forwards "
     "and audit history from one place.",
     ["REACT", "NODE.JS", "POSTGRESQL", "PROXMOX", "FORTIGATE", "PASSKEYS"]),
    ("caddy-forticertsync", "caddy-forticertsync", 1,
     "Caddy v2 plugin that pushes renewed TLS certificates straight into FortiGate via the FortiOS REST API, "
     "rebinds SSL-VPN, admin HTTPS and VIPs to the new cert and cleans up the old one. No cron, no polling.",
     ["GO", "CADDY", "FORTIOS API", "TLS"]),
    ("tools-platform", "tools.aaris.tech — Web Toolbox", 1,
     "Modular, self-hosted web toolbox with auto-discovery. Custom tools include a Danish traffic fine "
     "simulator, an EPUB-to-PDF converter and a unit converter. No sign-up, no tracking.",
     ["DOCKER", "FLASK", "PYTHON", "NGINX"]),
]


def rack_head():
    s = Svg(150, "02 Rack-01: public builds on GitHub")
    sec_head(s, 52, "02", "Rack-01 — Builds", "ELEVATION · FRONT VIEW")
    s.text(PAD, 104, "Public repos. Everything here runs in production at home first.", "sans", 15.5, MUT)
    # rack head bar
    s.rect(PAD + 0.5, 124.5, W - 2 * PAD - 1, 40, RAISE, LINE)
    s.text(PAD + 18, 149, "RACK-01 · GITHUB.COM/JONARIHEN", "mono6", 11, INK, 0.14)
    total = sum(p[2] for p in PROJECTS) + 1
    x = W - PAD - 18
    x -= s.text(x, 149, f"{total}U", "mono6", 11, MUT, 0.14, anchor="end") + 22
    x -= s.text(x, 149, "ACT", "mono6", 11, MUT, 0.14, anchor="end") + 15
    s.led(x - 8, 141, "act")
    x -= 30
    x -= s.text(x, 149, "PWR", "mono6", 11, MUT, 0.14, anchor="end") + 15
    s.led(x - 8, 141, "ok")
    s.h = 165
    s.render("rack-head", frame=False)


def rack_units():
    u = sum(p[2] for p in PROJECTS) + 1
    for idx, (slug, title, units, desc, tags) in enumerate(PROJECTS):
        lines = wrap(desc, "sans", 14.5, W - 2 * PAD - 58 - 44 - 50)
        h = int(26 + 30 + 25 * len(lines) + 16 + 24 + 24)
        s = Svg(h, f"{title}: {desc}")
        x0, x1 = PAD, W - PAD
        s.rect(x0 + 0.5, 0.5, x1 - x0 - 1, h - 1, BG, LINE)
        # U scale
        s.vline(x0 + 58, 0, h)
        top_u, bot_u = u, u - units + 1
        rng_label = [f"U{top_u:02d}"] if units == 1 else [f"U{top_u:02d}", "—", f"U{bot_u:02d}"]
        for i, lab in enumerate(rng_label):
            s.text(x0 + 29, h / 2 + 4 + (i - (len(rng_label) - 1) / 2) * 15, lab, "mono", 10, DIM, 0.06, anchor="middle")
        u -= units
        # ears
        for ex in (x0 + 59, x1 - 22):
            s.screw(ex + 7, 12)
            s.screw(ex + 7, h - 20)
        s.vline(x0 + 59 + 22, 0, h, SOFT)
        s.vline(x1 - 23, 0, h, SOFT)
        cx = x0 + 59 + 22 + 22
        y = 26 + 20
        s.text(cx, y, title, "sans7", 18.5, INK)
        rx = x1 - 23 - 22
        rx -= s.text(rx, y - 1, "REPO ↗", "mono6", 11, ACC, 0.14, anchor="end") + 18
        for j, kind in enumerate(["off", "act", "ok"]):
            s.led(rx - 8 - j * 13, y - 13, kind, delay=(idx * 0.7) % 2.6 if kind == "ok" else (idx * 0.31) % 0.7)
        y += 30
        for line in lines:
            s.text(cx, y, line, "sans", 14.5, MUT)
            y += 25
        y += 4
        tx = cx
        for t in tags:
            tw_ = tw(t, "mono", 10.5, 0.1) + 20
            s.rect(tx + 0.5, y + 0.5, tw_ - 1, 24 - 1, "none", LINE)
            s.text(tx + 10, y + 16, t, "mono", 10.5, MUT, 0.1)
            tx += tw_ + 7
        s.render(f"unit-{slug}", grid=False, frame=False)
    s = Svg(58, "Empty slot: reserved for future bad decisions")
    s.rect(PAD + 0.5, 0.5, W - 2 * PAD - 1, 57, "url(#hatch)", LINE)
    s.add(f'<rect x="{PAD + 1}" y="1" width="57" height="56" fill="{BG}"/>')
    s.vline(PAD + 58, 0, 58)
    s.text(PAD + 29, 33, "U01", "mono", 10, DIM, 0.06, anchor="middle")
    s.text((PAD + 58 + W - PAD) / 2, 33, "EMPTY — RESERVED FOR FUTURE BAD DECISIONS", "mono", 11, DIM, 0.14, anchor="middle")
    s.render("rack-foot", grid=False, frame=False)


# ── 03 Certifications ────────────────────────────────────────────────────────
def certs():
    data = [
        ("NOV 2025", "Nutanix Certified Professional — Multicloud Infrastructure 6", "NUTANIX"),
        ("OCT 2025", "Fortinet Certified Professional — Secure Networking", "FORTINET"),
        ("OCT 2025", "FortiManager 7.4 Administrator", "FORTINET"),
        ("FEB 2025", "HYCU R-Cloud Hybrid Cloud Edition Admin", "HYCU, INC."),
        ("JAN 2025", "FortiGate 7.4 Administrator", "FORTINET"),
        ("APR 2022", "Microsoft Certified: Security, Compliance, and Identity Fundamentals", "MICROSOFT"),
        ("JUN 2020", "Microsoft 365 Certified: Fundamentals", "MICROSOFT"),
    ]
    s = Svg(0, "03 Certifications. " + " ".join(f"{n} ({i}, {d})." for d, n, i in data))
    sec_head(s, 52, "03", "Compliance & Certification", f"{len(data)} RECORDS · ALL CURRENT")
    y = 96
    s.text(PAD + 12, y, "ISSUED", "mono6", 10, DIM, 0.16)
    s.text(PAD + 128, y, "RECORD", "mono6", 10, DIM, 0.16)
    s.text(W - PAD - 12, y, "STATUS", "mono6", 10, DIM, 0.16, anchor="end")
    y += 14
    s.hline(PAD, W - PAD, y)
    for i, (d, name, issuer) in enumerate(data):
        lines = wrap(name, "sans6", 15.5, W - 2 * PAD - 128 - 120)
        h = 24 + 21 * len(lines) + 20
        s.text(PAD + 12, y + 30, d, "mono", 12, MUT, 0.06)
        for j, line in enumerate(lines):
            s.text(PAD + 128, y + 30 + j * 21, line, "sans6", 15.5, INK)
        s.text(PAD + 128, y + 30 + len(lines) * 21, issuer, "mono", 10.5, DIM, 0.14)
        s.led(W - PAD - 12 - tw("VALID", "mono6", 10.5, 0.14) - 16, y + 22, "ok", delay=i * 0.37)
        s.text(W - PAD - 12, y + 30, "VALID", "mono6", 10.5, OK, 0.14, anchor="end")
        y += h
        s.hline(PAD, W - PAD, y, SOFT if i < len(data) - 1 else LINE)
    s.h = int(y + 30)
    s.render("certs")


# ── 04 Uplink ────────────────────────────────────────────────────────────────
def uplink():
    s = Svg(0, "04 Uplink: open a connection")
    sec_head(s, 52, "04", "Uplink", "PACKET LOSS 0% · TTL 64")
    x = s.text(PAD, 136, "OPEN A CONNECTION", "disp", 50, INK, -0.01)
    s.text(PAD + x, 136, ".", "disp", 50, ACC)
    s.text(PAD, 178, "Professional opportunity, collaboration, or just talking tech — all packets accepted below.",
           "sans", 15.5, MUT)
    s.h = 206
    s.render("uplink", frame=False)

    for slug, proto, addr in [("site", "HTTPS / 443", "aaris.tech"),
                              ("linkedin", "HTTPS / 443", "linkedin.com/in/jonathan-aaris-henningsen")]:
        s = Svg(76, f"{addr}")
        s.hline(PAD, W - PAD, 0)
        s.hline(PAD, W - PAD, 75)
        s.text(PAD + 14, 43, proto, "mono6", 11, DIM, 0.16)
        s.text(PAD + 14 + 170, 44, addr, "mono", 19, INK)
        s.text(W - PAD - 14, 45, "↗", "mono", 20, ACC, anchor="end")
        s.render(f"link-{slug}", grid=False, frame=False)

    s = Svg(64, "Footer")
    s.hline(0, W, 0)
    s.text(PAD, 38, "DOC NO. JAH-GH · REV 1.0", "mono", 10.5, DIM, 0.12)
    s.text(W / 2, 38, "NO COOKIES, NO TRACKING, NO TELEMETRY", "mono", 10.5, DIM, 0.12, anchor="middle")
    s.text(W - PAD, 38, "© JONATHAN AARIS HENNINGSEN", "mono", 10.5, DIM, 0.12, anchor="end")
    s.render("footer", grid=False, frame=False)


header()
ticker()
capability()
rack_head()
rack_units()
certs()
uplink()
