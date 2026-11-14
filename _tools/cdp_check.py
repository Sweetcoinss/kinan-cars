#!/usr/bin/env python3
"""
Drive headless Chrome over the DevTools protocol:
  - capture full-page screenshots of every mirrored page
  - record console errors and failed network requests (404s etc.)
Usage: python cdp_check.py <base_url> <out_dir>
"""
import base64
import json
import os
import sys
import threading
import time
import urllib.request

import websocket

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_shots")

PORT = 9222
PAGES = [
    ("index", "/"),
    ("bmw-m3", "/bmw-m3.html"),
    ("mercedes-gle", "/mercedes-gle.html"),
    ("yamaha-tmax", "/yamaha-tmax.html"),
]

os.makedirs(OUT, exist_ok=True)


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.id = 0
        self.events = []
        self.lock = threading.Lock()

    def send(self, method, **params):
        with self.lock:
            self.id += 1
            mid = self.id
            self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            else:
                with self.lock:
                    self.events.append(msg)

    def drain(self):
        with self.lock:
            ev = self.events[:]
            self.events = []
        return ev


def main():
    # wait for chrome
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2).read()
            break
        except Exception:
            time.sleep(0.5)
    else:
        print("chrome not up")
        return 1

    tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list").read())
    page = next(t for t in tabs if t["type"] == "page")
    cdp = CDP(page["webSocketDebuggerUrl"])

    cdp.send("Page.enable")
    cdp.send("Runtime.enable")
    cdp.send("Log.enable")
    cdp.send("Network.enable")

    all_fail = []

    for name, path in PAGES:
        url = BASE.rstrip("/") + path
        cdp.send("Page.navigate", url=url)
        time.sleep(4.0)
        # let reveal animations settle: scroll through the page in steps so every
        # IntersectionObserver target actually fires
        cdp.send("Runtime.evaluate", expression="""(async()=>{
            const step = 600;
            const h = document.body.scrollHeight;
            for (let y = 0; y < h; y += step) {
                window.scrollTo(0, y);
                await new Promise(r=>setTimeout(r,120));
            }
            window.scrollTo(0, h);
            await new Promise(r=>setTimeout(r,900));
            window.scrollTo(0,0);
            await new Promise(r=>setTimeout(r,700));
            return document.body.scrollHeight;
        })()""", awaitPromise=True)
        time.sleep(2.0)

        evs = cdp.drain()
        fails = []
        console = []
        for e in evs:
            m = e.get("method")
            p = e.get("params", {})
            if m == "Network.loadingFailed":
                fails.append(("failed", p.get("type"), p.get("errorText"), p.get("requestId")))
            elif m == "Network.responseReceived":
                r = p.get("response", {})
                if r.get("status", 200) >= 400:
                    fails.append((r.get("status"), r.get("url"), ""))
            elif m == "Log.entryAdded":
                en = p.get("entry", {})
                if en.get("level") in ("error", "warning"):
                    console.append(f"{en.get('level')}: {en.get('text')} {en.get('url','')}")
            elif m == "Runtime.exceptionThrown":
                console.append("exception: " + json.dumps(p.get("exceptionDetails", {}))[:300])

        # full page screenshot
        metrics = cdp.send("Page.getLayoutMetrics")
        h = int(metrics.get("contentSize", {}).get("height", 0))
        w = int(metrics.get("contentSize", {}).get("width", 1440))
        h = min(h, 30000)
        shot = cdp.send("Page.captureScreenshot", format="png",
                        clip={"x": 0, "y": 0, "width": w, "height": h, "scale": 1},
                        captureBeyondViewport=True)
        fp = os.path.join(OUT, f"{name}.png")
        open(fp, "wb").write(base64.b64decode(shot["data"]))

        status = "OK" if not fails else f"{len(fails)} ISSUE(S)"
        print(f"[{status}] {name}  {w}x{h}  -> {os.path.basename(fp)}")
        for f in fails:
            print(f"    NET {f}")
        for c in console[:10]:
            print(f"    CON {c}")
        all_fail.extend((name, f) for f in fails)

    print()
    print(f"TOTAL network issues: {len(all_fail)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
