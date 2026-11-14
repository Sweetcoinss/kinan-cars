#!/usr/bin/env python3
"""Render favicon.svg to a real favicon.ico so /favicon.ico no longer 404s."""
import base64
import io
import json
import os
import sys
import time
import urllib.request

import websocket
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 9222

tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list").read())
page = next(t for t in tabs if t["type"] == "page")
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60)
mid = [0]


def send(method, **params):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": method, "params": params}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid[0]:
            return m.get("result", {})


send("Page.enable")
svg = os.path.join(ROOT, "favicon.svg").replace(os.sep, "/")
send("Page.navigate", url="file:///" + svg)
time.sleep(2.5)

html = """<!doctype html><html><head><style>
html,body{margin:0;padding:0;background:transparent}
img{width:256px;height:256px;display:block}
</style></head><body><img src="file:///%s"></body></html>""" % svg
tmp = os.path.join(ROOT, "_tools", "_favicon_tmp.html")
open(tmp, "w", encoding="utf-8").write(html)
send("Page.navigate", url="file:///" + tmp.replace(os.sep, "/"))
time.sleep(2.0)

shot = send("Page.captureScreenshot", format="png",
            clip={"x": 0, "y": 0, "width": 256, "height": 256, "scale": 1})
img = Image.open(io.BytesIO(base64.b64decode(shot["data"]))).convert("RGBA")
ico = os.path.join(ROOT, "favicon.ico")
img.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
os.remove(tmp)
print(f"[favicon] wrote {ico}  ({os.path.getsize(ico)} bytes)")
