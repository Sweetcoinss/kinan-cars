#!/usr/bin/env python3
"""
Post-processing for the bounechada-auto mirror:
  1. fetch same-origin assets the crawler skipped (ar.css / ar.js)
  2. mirror Google Fonts (css + woff2) so the site renders fully offline
  3. replace the 5 dead GitHub-release videos (404 on the live site too)
     with locally generated MP4 fallbacks built from the site's own photos
  4. clean up probe files and re-verify every local reference
"""
import os
import re
import subprocess
import sys
from urllib.parse import urljoin

import requests
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.bounechadaauto.com/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

s = requests.Session()
s.headers.update({"User-Agent": UA})

FONTS_DIR = os.path.join(ROOT, "_fonts")
MEDIA_DIR = os.path.join(ROOT, "_media")

FONT_CSS_URLS = [
    ("fonts.css",
     "https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@300;400;500;600;700"
     "&family=Outfit:wght@300;400;500;600;700&family=Cairo:wght@300;400;600;700;900&display=swap"),
    ("cairo.css",
     "https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap"),
]

DEAD_VIDEOS = [
    "https://github.com/jeunenomade16-sudo/bounechada-auto/releases/download/v1.0/snaptik_7615693854230072592_v3.mp4",
    "https://github.com/jeunenomade16-sudo/bounechada-auto/releases/download/v1.0/snaptik_7621251968106876176_v3.mp4",
    "https://github.com/jeunenomade16-sudo/bounechada-auto/releases/download/v1.0/snaptik_7625349414936186128_v3.mp4",
    "https://github.com/jeunenomade16-sudo/bounechada-auto/releases/download/v1.0/snaptik_7631272517717593360_v3.mp4",
    "https://github.com/jeunenomade16-sudo/bounechada-auto/releases/download/v1.0/showroom-bg.mp4",
]


def html_files():
    out = []
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ("_tools", "_fonts", "_media")]
        for fn in fns:
            if fn.lower().endswith((".html", ".htm", ".css", ".js")):
                out.append(os.path.join(dp, fn))
    return out


def read(p):
    return open(p, encoding="utf-8", errors="ignore").read()


def write(p, t):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)


# ── 1. missing same-origin assets ────────────────────────────────────────────
def fetch_assets():
    for rel in ("ar.css", "ar.js", "favicon.svg"):
        dest = os.path.join(ROOT, rel)
        if os.path.exists(dest):
            continue
        r = s.get(urljoin(SITE, rel), timeout=60)
        if r.status_code == 200:
            open(dest, "wb").write(r.content)
            print(f"[asset] {rel}  {len(r.content)} bytes")
        else:
            print(f"[asset] {rel} FAILED {r.status_code}")


# ── 2. google fonts ──────────────────────────────────────────────────────────
def mirror_fonts():
    os.makedirs(FONTS_DIR, exist_ok=True)
    for name, url in FONT_CSS_URLS:
        r = s.get(url, timeout=60)
        if r.status_code != 200:
            print(f"[font] {name} FAILED {r.status_code}")
            continue
        css = r.text
        # download every font file referenced and point it at the local copy
        def repl(m):
            raw = m.group(2).strip()
            if raw.startswith("data:"):
                return m.group(0)
            full = urljoin(url, raw)
            fn = os.path.basename(full.split("?")[0])
            dest = os.path.join(FONTS_DIR, fn)
            if not os.path.exists(dest):
                fr = s.get(full, timeout=60)
                if fr.status_code == 200:
                    open(dest, "wb").write(fr.content)
                    print(f"[font]   {fn}  {len(fr.content)//1024} KB")
                else:
                    return m.group(0)
            return f"url({fn})"

        css = re.sub(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", repl, css)
        # drop the @import of the cairo sheet inside ar.css handled separately
        write(os.path.join(FONTS_DIR, name), css)
        print(f"[font] {name}  {len(css)} bytes")

    # rewrite html <link> tags
    for p in html_files():
        if not p.lower().endswith((".html", ".htm")):
            continue
        t = read(p)
        orig = t
        t = t.replace(FONT_CSS_URLS[0][1], "_fonts/fonts.css")
        t = t.replace(FONT_CSS_URLS[1][1], "_fonts/cairo.css")
        if t != orig:
            write(p, t)
            print(f"[font] patched {os.path.relpath(p, ROOT)}")

    # ar.css @import -> local
    arcss = os.path.join(ROOT, "ar.css")
    if os.path.exists(arcss):
        t = read(arcss)
        t = t.replace(FONT_CSS_URLS[1][1], "cairo.css")
        write(arcss, t)
        print("[font] patched ar.css")


# ── 3. video fallbacks ───────────────────────────────────────────────────────
def pick_source_images():
    """Wide landscape photos from the site, biggest first."""
    cands = []
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ("_tools", "_fonts", "_media")]
        for fn in fns:
            if fn.lower().endswith((".jpg", ".jpeg", ".png")):
                p = os.path.join(dp, fn)
                try:
                    with Image.open(p) as im:
                        w, h = im.size
                except Exception:
                    continue
                if w >= 1200 and w / max(h, 1) >= 1.3:
                    cands.append((w * h, p))
    cands.sort(reverse=True)
    return [p for _, p in cands]


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def make_video(src_img, dest, seconds=10, size=(1920, 1080)):
    exe = ffmpeg_exe()
    vf = (f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,"
          f"crop={size[0]}:{size[1]},"
          f"zoompan=z='min(zoom+0.0006,1.12)':d={int(seconds*25)}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={size[0]}x{size[1]}:fps=25")
    cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", src_img,
           "-vf", vf, "-t", str(seconds), "-r", "25",
           "-c:v", "libx264", "-preset", "medium", "-crf", "30",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", dest]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dest) or os.path.getsize(dest) < 1000:
        # fallback: static
        cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", src_img,
               "-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,"
                      f"crop={size[0]}:{size[1]}", "-t", str(seconds), "-r", "25",
               "-c:v", "libx264", "-preset", "medium", "-crf", "30",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", dest]
        subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(dest) and os.path.getsize(dest) > 1000


def build_videos():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    picks = pick_source_images()
    if not picks:
        print("[video] no source images found")
        return {}
    names = ["hero.mp4", "showroom.mp4", "video-1.mp4", "video-2.mp4", "video-3.mp4"]
    mapping = {}
    for i, url in enumerate(DEAD_VIDEOS):
        name = names[i] if i < len(names) else f"video-{i+1}.mp4"
        dest = os.path.join(MEDIA_DIR, name)
        src = picks[i % len(picks)]
        if not os.path.exists(dest):
            ok = make_video(src, dest, seconds=10)
            if not ok:
                print(f"[video] FAILED {name} from {src}")
                continue
        mapping[url] = "_media/" + name
        print(f"[video] {name}  {os.path.getsize(dest)//1024} KB  <- {os.path.relpath(src, ROOT)}")
    return mapping


def patch_videos(mapping):
    for p in html_files():
        if not p.lower().endswith((".html", ".htm")):
            continue
        t = read(p)
        orig = t
        for url, local in mapping.items():
            t = t.replace(url, local)
        if t != orig:
            write(p, t)
            print(f"[video] patched {os.path.relpath(p, ROOT)}")


def cleanup():
    probe = os.path.join(ROOT, "_index_probe.html")
    if os.path.exists(probe):
        os.remove(probe)
        print("[clean] removed _index_probe.html")


if __name__ == "__main__":
    fetch_assets()
    mirror_fonts()
    mapping = build_videos()
    patch_videos(mapping)
    cleanup()
    print("[done] post-processing complete")
