#!/usr/bin/env python3
"""Final touch-ups: route every page's font stylesheet to the local copy."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUBPAGE_FONTS = ("https://fonts.googleapis.com/css2?family=Bebas+Neue"
                  "&family=Barlow+Condensed:wght@300;400;500;600;700"
                  "&family=Outfit:wght@300;400;500;600;700&display=swap")

n = 0
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ("_tools", "_fonts", "_media")]
    for fn in fns:
        if not fn.lower().endswith((".html", ".htm", ".css")):
            continue
        p = os.path.join(dp, fn)
        t = open(p, encoding="utf-8", errors="ignore").read()
        o = t
        t = t.replace(SUBPAGE_FONTS, "_fonts/fonts.css")
        # fonts now served locally -> drop the preconnect hints
        t = re.sub(r"""\s*<link rel="preconnect" href="https://fonts\.(?:googleapis|gstatic)\.com"[^>]*>""",
                   "", t)
        # ar.css lives at root and must import the local cairo sheet
        if fn.lower() == "ar.css":
            t = t.replace("url('cairo.css')", "url('_fonts/cairo.css')")
            t = t.replace('url("cairo.css")', 'url("_fonts/cairo.css")')
        if t != o:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(t)
            n += 1
            print(f"[fix] {os.path.relpath(p, ROOT)}")
print(f"[fix] {n} files updated")
