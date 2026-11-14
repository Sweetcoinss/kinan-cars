#!/usr/bin/env python3
"""Verify all local references in the mirrored site resolve to real files."""
import os
import re
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ATTR_RE = re.compile(
    r"""(?:src|href|poster|data-src|data-bg|data-video)\s*=\s*(["'])(.*?)\1""", re.I | re.S)
CSSURL_RE = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.I)
# plain quoted asset paths inside inline JS (skip template literals)
JS_RE = re.compile(r"""(?<![$\w])["']([^"'\s]+\.(?:mp4|webm|jpe?g|png|gif|svg|webp|ico|css|js|woff2?))["']""",
                    re.I)

# template-literal / dynamic fragments we must not treat as paths
DYNAMIC = re.compile(r"[$}{`\\]")


def norm(r):
    r = r.strip()
    if not r or DYNAMIC.search(r):
        return None
    if r.lower().startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "#")):
        return None
    if r.startswith("//"):
        return None
    r = r.split("#")[0].split("?")[0]
    if not r:
        return None
    return r


missing = []
checked = 0
external = set()
pages = 0

for dirpath, _, files in os.walk(ROOT):
    dn = [d for d in os.listdir(dirpath)]
    if "_tools" in dirpath or "_fonts" in dirpath or "_media" in dirpath:
        continue
    for fn in files:
        if not fn.lower().endswith((".html", ".htm", ".css", ".js")):
            continue
        pages += 1
        fp = os.path.join(dirpath, fn)
        txt = open(fp, encoding="utf-8", errors="ignore").read()
        refs = set()

        for m in ATTR_RE.finditer(txt):
            v = m.group(2)
            if "srcset" in v.lower():
                continue
            # plain attribute -> whole value is the path (may contain spaces)
            refs.add(v.strip())
        for m in re.finditer(r"""srcset\s*=\s*(["'])(.*?)\1""", txt, re.I | re.S):
            for part in m.group(2).split(","):
                part = part.strip()
                if part:
                    refs.add(part.split()[0])
        refs.update(CSSURL_RE.findall(txt))
        refs.update(JS_RE.findall(txt))

        for r in refs:
            if r.lower().startswith(("http://", "https://", "//")):
                external.add(r.split("?")[0])
                continue
            r = norm(r)
            if r is None:
                continue
            target = os.path.normpath(os.path.join(dirpath, unquote(r)))
            checked += 1
            if not os.path.exists(target):
                missing.append((os.path.relpath(fp, ROOT), r))

print(f"scanned {pages} html/css/js files")
print(f"checked {checked} local references")
print(f"MISSING: {len(missing)}")
for page, ref in missing[:60]:
    print(f"  {page}  ->  {ref}")
print(f"\nexternal refs still pointing out ({len(external)}):")
for u in sorted(external):
    print(f"  {u}")
