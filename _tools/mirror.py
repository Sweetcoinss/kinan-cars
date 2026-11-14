#!/usr/bin/env python3
"""
Recursive site mirror for https://www.bounechadaauto.com/
- Crawls same-origin HTML pages (BFS)
- Downloads every referenced asset (img, css, js, svg, font, video, ...)
- Preserves the original directory structure so relative links keep working
- Rewrites absolute same-origin URLs -> relative local paths
- Mirrors third-party assets (Google Fonts, GitHub release videos) into _external/
"""

import os
import re
import sys
import time
import json
import threading
from urllib.parse import urljoin, urlparse, unquote, urldefrag
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

ROOT = "https://www.bounechadaauto.com/"
BASE_HOSTS = {"www.bounechadaauto.com", "bounechadaauto.com"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
EXT_DIR = "_external"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "*/*",
}

session = requests.Session()
session.headers.update(HEADERS)

print_lock = threading.Lock()
seen = set()          # absolute URLs already queued
done = set()          # absolute URLs already downloaded
lock = threading.Lock()

TEXT_EXT = {".html", ".htm", ".xhtml"}
CSS_EXT = {".css"}
ASSET_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif",
    ".css", ".js", ".mjs", ".json", ".xml", ".txt",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".webm", ".ogv", ".mov", ".m4v", ".mp3", ".wav",
    ".pdf", ".zip", ".map",
}

SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "blob:", "#", "about:")


def log(msg):
    with print_lock:
        print(msg, flush=True)


def local_path_for(abs_url, base_url):
    """Map an absolute URL to a path inside the mirror, relative to base_url's folder."""
    p = urlparse(abs_url)
    host = p.netloc.lower()
    path = unquote(p.path)

    if host in BASE_HOSTS:
        rel = path.lstrip("/")
        if not rel or rel.endswith("/"):
            rel += "index.html"
        root = OUT
        if path == "/" or rel == "index.html":
            # keep index at root
            pass
    else:
        # third party asset -> _external/<host>/<path>
        rel = os.path.join(EXT_DIR, host, path.lstrip("/"))
        if not rel or rel.endswith(os.sep):
            rel += "index.html"
        root = OUT

    abspath = os.path.join(root, rel)
    try:
        relpath = os.path.relpath(abspath, os.path.dirname(os.path.join(root, local_path_for(base_url, base_url))))
    except Exception:
        relpath = rel
    return abspath, relpath


def rel_to_base(abs_local, base_abs_url):
    """Relative link from the page containing base_abs_url to abs_local (both on disk)."""
    base_dir = os.path.dirname(abs_local_for(base_abs_url))
    try:
        rel = os.path.relpath(abs_local, base_dir)
    except ValueError:
        rel = os.path.relpath(abs_local, OUT)
    return rel.replace(os.sep, "/")


def abs_local_for(abs_url):
    p = urlparse(abs_url)
    host = p.netloc.lower()
    path = unquote(p.path)
    if host in BASE_HOSTS:
        rel = path.lstrip("/")
        if not rel:
            rel = "index.html"
    else:
        rel = os.path.join(EXT_DIR, host, path.lstrip("/"))
        if not rel:
            rel = "index.html"
    return os.path.join(OUT, rel)


def fetch(url, referer=None):
    h = dict(HEADERS)
    if referer:
        h["Referer"] = referer
    r = session.get(url, headers=h, timeout=60, stream=True, allow_redirects=True)
    return r


def download(url, referer=None):
    """Download a single URL to its mirrored path. Returns (ok, local_path, content_type)."""
    if url in done:
        return True, abs_local_for(url), None
    with lock:
        if url in done:
            return True, abs_local_for(url), None
    try:
        r = fetch(url, referer)
        if r.status_code != 200:
            log(f"  !! {r.status_code} {url}")
            return False, None, None
        ctype = r.headers.get("Content-Type", "")
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext == "" and "text/html" in ctype:
            ext = ".html"
        # guess extension from content-type when missing
        if ext == "":
            guess = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                "image/svg+xml": ".svg", "image/gif": ".gif", "image/x-icon": ".ico",
                "text/css": ".css", "application/javascript": ".js",
                "application/json": ".json", "font/woff2": ".woff2", "font/woff": ".woff",
                "video/mp4": ".mp4", "application/xml": ".xml", "text/xml": ".xml",
            }.get(ctype.split(";")[0].strip(), ".bin")
            ext = guess
        p = urlparse(url)
        if p.hostname and p.hostname not in BASE_HOSTS and not unquote(p.path).lower().endswith(
                (".css", ".js", ".woff", ".woff2", ".ttf", ".otf", ".jpg", ".jpeg", ".png",
                 ".gif", ".webp", ".svg", ".ico", ".mp4", ".webm", ".json", ".xml", ".txt", ".mp3", ".wav")):
            # keep original extension for unknown ext
            pass
        local = abs_local_for(url)
        if ext and not local.lower().endswith(ext):
            local = os.path.splitext(local)[0] + ext
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as f:
            for chunk in r.iter_content(65536):
                if chunk:
                    f.write(chunk)
        with lock:
            done.add(url)
        return True, local, ctype
    except Exception as e:
        log(f"  !! ERR {url} :: {e}")
        return False, None, None


# ── URL extraction ────────────────────────────────────────────────────────────
CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)
ATTRS = ["src", "href", "poster", "data-src", "data-bg", "data-video", "content"]
SRCSET_ATTRS = ["srcset", "data-srcset"]


def iter_css_urls(text):
    for m in CSS_URL_RE.finditer(text):
        yield m.group(2).strip()


def extract_urls(html, page_url):
    soup = BeautifulSoup(html, "lxml")
    urls = []

    def add(u):
        if not u:
            return
        u = u.strip()
        if not u or u.lower().startswith(SKIP_SCHEMES):
            return
        urls.append(u)

    for tag in soup.find_all(True):
        for a in ATTRS:
            if tag.has_attr(a):
                v = tag.get(a)
                if a == "content" and tag.name not in ("meta",):
                    continue
                if isinstance(v, list):
                    v = " ".join(v)
                # meta content should only count for og:image / og:url style
                if a == "content":
                    if tag.get("property", "").startswith("og:") and "image" in tag.get("property", ""):
                        add(v)
                    continue
                add(v)
        for a in SRCSET_ATTRS:
            if tag.has_attr(a):
                for part in str(tag.get(a)).split(","):
                    part = part.strip()
                    if part:
                        add(part.split()[0])
        if tag.name == "style" and tag.string:
            for u in iter_css_urls(tag.string):
                add(u)

    # <style> blocks + inline style attributes
    for st in soup.find_all("style"):
        if st.string:
            for u in iter_css_urls(st.string):
                add(u)
    for tag in soup.find_all(style=True):
        for u in iter_css_urls(tag.get("style", "")):
            add(u)

    # raw source text (JS strings referencing assets)
    for m in re.finditer(r"""["']([^"'\s]+\.(?:mp4|webm|jpg|jpeg|png|gif|svg|webp|ico|css|js|woff2?))["']""",
                         html, re.I):
        add(m.group(1))

    resolved = []
    for u in urls:
        absolute = urljoin(page_url, u)
        absolute, _frag = urldefrag(absolute)
        resolved.append(absolute)
    return soup, list(dict.fromkeys(resolved))


def rewrite_css(css_text, css_url):
    """Download + rewrite url() references inside a stylesheet."""
    base_dir = os.path.dirname(css_url)
    new = css_text
    for raw in list(dict.fromkeys(iter_css_urls(css_text))):
        if raw.lower().startswith(SKIP_SCHEMES):
            continue
        absolute = urljoin(css_url, raw)
        absolute, _ = urldefrag(absolute)
        p = urlparse(absolute)
        if p.netloc and p.netloc.lower() not in BASE_HOSTS:
            # third-party -> download into _external
            ok, local, _ = download(absolute, referer=css_url)
            if ok and local:
                new = new.replace(raw, os.path.relpath(local, base_dir).replace(os.sep, "/"))
        else:
            rel_path = unquote(p.path).lstrip("/")
            if not rel_path:
                continue
            if rel_path.lower().endswith(".css"):
                continue
            ok, local, _ = download(absolute, referer=css_url)
            if ok and local:
                new = new.replace(raw, os.path.relpath(local, base_dir).replace(os.sep, "/"))
    return new


def process_page(abs_url, html):
    """Rewrite a page's HTML: download assets, point links at local files."""
    soup, urls = extract_urls(html, abs_url)
    page_local = abs_local_for(abs_url)

    for absolute in urls:
        p = urlparse(absolute)
        host = p.netloc.lower()
        path = unquote(p.path)

        # skip pure external navigational links (social, whatsapp, tel, maps embed)
        ext_no_frag = absolute
        if host and host not in BASE_HOSTS:
            is_asset = path.lower().endswith(tuple(ASSET_EXT)) or path == ""
            if is_asset and path.lower().endswith(tuple(ASSET_EXT)):
                ok, local, ctype = download(absolute, referer=abs_url)
                if not ok:
                    continue
                # rewrite in document
                rel = rel_to_base(local, abs_url)
                for tag in soup.find_all(True):
                    for a in ATTRS + SRCSET_ATTRS:
                        if not tag.has_attr(a):
                            continue
                        v = tag.get(a)
                        if not isinstance(v, str):
                            continue
                        if v.strip() == absolute:
                            tag[a] = rel
                    if tag.name == "style" and tag.string and absolute in tag.string:
                        tag.string = tag.string.replace(absolute, rel)
                for st in soup.find_all("style"):
                    if st.string and absolute in st.string:
                        st.string = st.string.replace(absolute, rel)
                # rewrite raw occurrences too (JS strings)
                html = html.replace(absolute, rel)
            else:
                # external page link -> keep as-is (absolute URL)
                continue
        else:
            # same origin
            if path.lower().endswith(tuple(TEXT_EXT)) or path.lower().endswith(".css"):
                continue  # handled separately (crawled / rewritten later)
            if path.lower().endswith(tuple(ASSET_EXT)):
                ok, local, ctype = download(absolute, referer=abs_url)
                if ok and local:
                    rel = rel_to_base(local, abs_url)
                    html = html.replace(absolute, rel)
                    html = html.replace(absolute.replace("https://", "http://"), rel)

    # absolute same-origin links to html pages -> relative local paths
    def repl_same_origin(m):
        raw = m.group(0)
        absolute, _frag = urldefrag(urljoin(abs_url, raw))
        p = urlparse(absolute)
        if p.netloc.lower() in BASE_HOSTS and p.path.lower().endswith(tuple(TEXT_EXT)):
            target = abs_local_for(absolute)
            if os.path.exists(target):
                return os.path.relpath(target, os.path.dirname(page_local)).replace(os.sep, "/")
        return raw

    html = re.sub(r"""(?:https?:)?//(?:www\.)?bounechadaauto\.com[^\s"'<>\\)]*""", repl_same_origin, html)

    # relative same-origin links -> local relative paths (verify existence)
    def repl_relative(m):
        raw = m.group(0)
        absolute, _frag = urldefrag(urljoin(abs_url, raw))
        p = urlparse(absolute)
        if p.netloc.lower() in BASE_HOSTS:
            target = abs_local_for(absolute)
            if os.path.exists(target):
                return os.path.relpath(target, os.path.dirname(page_local)).replace(os.sep, "/")
        return raw

    html = re.sub(
        r"""(?<![:\w/])(?:\./)?[A-Za-z0-9_\u00C0-\u024F%][^\s"'<>\\)]*?\.(?:html?|css|js|json|xml|txt)(?![A-Za-z0-9])""",
        repl_relative, html)

    return html


def crawl():
    queue = [ROOT]
    seen.add(ROOT)
    pages = []

    # seed
    ok, local, _ = download(ROOT)
    if not ok:
        log("FATAL: could not fetch root")
        return pages

    # process queue level by level
    while queue:
        nxt = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {}
            for u in queue:
                futs[ex.submit(fetch_html, u)] = u
            for fut in as_completed(futs):
                u = futs[fut]
                try:
                    html = fut.result()
                except Exception as e:
                    log(f"  !! page fail {u} {e}")
                    continue
                if html is None:
                    continue
                pages.append(u)
                out = process_page(u, html)
                local = abs_local_for(u)
                os.makedirs(os.path.dirname(local), exist_ok=True)
                with open(local, "w", encoding="utf-8", newline="\n") as f:
                    f.write(out)
                log(f"[page] {u}  ->  {os.path.relpath(local, OUT)}")

                # discover new same-origin html pages
                soup, urls = extract_urls(out, u)
                for absolute in urls:
                    p = urlparse(absolute)
                    if p.netloc.lower() in BASE_HOSTS and p.path.lower().endswith(tuple(TEXT_EXT)):
                        if absolute not in seen:
                            seen.add(absolute)
                            nxt.append(absolute)
        queue = nxt

    return pages


def fetch_html(url):
    try:
        r = fetch(url)
        if r.status_code != 200:
            log(f"  !! page {r.status_code} {url}")
            return None
        return r.text
    except Exception as e:
        log(f"  !! page ERR {url} {e}")
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    log(f"Mirroring {ROOT} -> {OUT}")
    pages = crawl()

    # ── stylesheets: rewrite url() and download referenced files ──
    css_files = []
    for root, _, files in os.walk(OUT):
        for fn in files:
            if fn.lower().endswith(".css"):
                css_files.append(os.path.join(root, fn))
    log(f"[css] {len(css_files)} stylesheet(s)")
    for cf in css_files:
        try:
            txt = open(cf, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        pseudo = "file:///" + cf.replace(os.sep, "/")
        new = rewrite_css(txt, pseudo)
        if new != txt:
            with open(cf, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)

    # ── second pass: now that all pages/assets exist, finalise link rewriting ──
    for page in pages:
        local = abs_local_for(page)
        if not os.path.exists(local):
            continue
        html = open(local, encoding="utf-8", errors="ignore").read()
        fixed = process_page(page, html)
        with open(local, "w", encoding="utf-8", newline="\n") as f:
            f.write(fixed)

    summary = {
        "root": ROOT,
        "output": os.path.abspath(OUT),
        "pages": len(pages),
        "page_list": pages,
        "files_downloaded": len(done),
    }
    with open(os.path.join(OUT, "_mirror_report.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    total = 0
    for r, _, fs in os.walk(OUT):
        for fn in fs:
            try:
                total += os.path.getsize(os.path.join(r, fn))
            except OSError:
                pass
    log("")
    log(f"DONE  pages={len(pages)}  files={len(done)}  size={total/1024/1024:.1f} MB")
    log(f"Output: {os.path.abspath(OUT)}")


if __name__ == "__main__":
    main()
