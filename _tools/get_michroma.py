#!/usr/bin/env python3
"""Download the Michroma font (used by the logo SVG) so the logo works offline."""
import os
import re

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "_fonts")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

s = requests.Session()
s.headers.update({"User-Agent": UA})
os.makedirs(FONTS, exist_ok=True)

url = "https://fonts.googleapis.com/css2?family=Michroma&display=swap"
r = s.get(url, timeout=60)
r.raise_for_status()
css = r.text


def repl(m):
    raw = m.group(2).strip()
    if raw.startswith("data:"):
        return m.group(0)
    full = "https://fonts.googleapis.com" + raw if raw.startswith("/") else raw
    fn = os.path.basename(full.split("?")[0])
    dest = os.path.join(FONTS, fn)
    if not os.path.exists(dest):
        fr = s.get(full, timeout=60)
        fr.raise_for_status()
        open(dest, "wb").write(fr.content)
        print(f"[michroma] {fn}  {len(fr.content)//1024} KB")
    return f"url({fn})"


css = re.sub(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", repl, css)
with open(os.path.join(FONTS, "michroma.css"), "w", encoding="utf-8", newline="\n") as f:
    f.write(css)
print(f"[michroma] michroma.css  {len(css)} bytes")
