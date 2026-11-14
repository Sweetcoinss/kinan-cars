#!/usr/bin/env python3
"""
Rebrand: Bounechada Auto  ->  Kinan Cars
Removes every trace of the previous brand name from the site content.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGET_EXT = (".html", ".htm", ".css", ".js", ".svg", ".json", ".xml", ".txt")

# ordered, case-sensitive replacements (longest / most specific first)
PAIRS = [
    # logo with a coloured span:  BOUNECHADA <span>AUTO</span>  ->  KINAN <span>CARS</span>
    (re.compile(r"BOUNECHADA(\s*)<span([^>]*)>AUTO</span>"), r"KINAN\1<span\2>CARS</span>"),
    # svg logo tspans
    (re.compile(r'(<tspan class="black">)BOUNECHADA(</tspan>)'), r"\1KINAN\2"),
    (re.compile(r'(<tspan class="red"[^>]*>)AUTO(</tspan>)'), r"\1CARS\2"),
    # plain names
    (re.compile(r"BOUNECHADA AUTO"), "KINAN CARS"),
    (re.compile(r"BOUNECHADA"), "KINAN"),
    (re.compile(r"Bounechada Auto"), "Kinan Cars"),
    (re.compile(r"Bounechada"), "Kinan Cars"),
    # handles / emails / slugs
    (re.compile(r"bounechada_auto"), "kinan_cars"),
    (re.compile(r"bounechada-automobile"), "kinan-cars-automobile"),
    (re.compile(r"bounechada-auto"), "kinan-cars"),
    (re.compile(r"bounechadaauto"), "kinancars"),
    (re.compile(r"(?i)bounechada"), "kinancars"),
]

SKIP_DIRS = {"_tools", ".git"}
CHANGED = []


def rename(text):
    for rx, rep in PAIRS:
        text = rx.sub(rep, text)
    return text


def main():
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for fn in fns:
            if not fn.lower().endswith(TARGET_EXT):
                continue
            p = os.path.join(dp, fn)
            try:
                orig = open(p, encoding="utf-8").read()
            except Exception:
                continue
            new = rename(orig)
            if new != orig:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)
                CHANGED.append(os.path.relpath(p, ROOT))

    for c in CHANGED:
        print(f"  renamed  {c}")
    print(f"\n{len(CHANGED)} file(s) updated")

    # residual check
    left = []
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for fn in fns:
            if not fn.lower().endswith(TARGET_EXT):
                continue
            p = os.path.join(dp, fn)
            try:
                c = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if re.search(r"(?i)bounechada", c):
                left.append(os.path.relpath(p, ROOT))
    print(f"residual occurrences of the old name: {len(left)}")
    for l in left:
        print(f"  LEFTOVER {l}")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
