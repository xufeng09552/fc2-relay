#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC2 抓取中转（HuggingFace Space / Koyeb 版）

背景：家里的 NAS 和电脑在大陆网络访问不了 FC2 商品页（DNS 污染 + SNI 阻断），
     但能访问境外的云服务。所以把这段 30 行的中转部署在境外免费云上，
     由它代取网页原文，NAS 再从它这里拿。图片 CDN 家里能直连，不用中转。

接口：
  GET /health                             → {"ok": true, ...}
  GET /fetch?url=<目标URL>&key=<令牌>      → 目标页原始字节 + 原 Content-Type
  GET /                                   → 浏览器打开时显示的说明页

安全（否则就是一个公开代理，会被人拿去乱用）：
  - 只放行 fc2.com 及其子域
  - 必须带 key

环境变量：
  PORT         监听端口，默认 7860（HF Space 要求 7860；Koyeb 会自动注入）
  RELAY_TOKEN  覆盖下面的默认令牌（可选）
"""

from __future__ import annotations

import json
import os
import ssl
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, parse, request

ALLOW_HOSTS = ("fc2.com",)
PORT = int(os.environ.get("PORT", "7860"))
DEFAULT_TOKEN = "fc2r_tpi9dhdxjsiiupqm0uufe6d4t8k2"
TOKEN = (os.environ.get("RELAY_TOKEN") or DEFAULT_TOKEN).strip()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()

INDEX_HTML = """<!doctype html><html lang="zh"><meta charset="utf-8">
<title>FC2 relay</title>
<style>
 body{font:15px/1.7 -apple-system,Segoe UI,sans-serif;max-width:640px;margin:60px auto;padding:0 20px;color:#2c2c2a}
 code{background:#f1efe8;padding:2px 6px;border-radius:4px;font-size:13px}
 .ok{color:#0f6e56;font-weight:500}
</style>
<h2>FC2 抓取中转 · 运行中</h2>
<p class="ok">服务正常。</p>
<p>这是一个只放行 <code>fc2.com</code> 的单用途抓取中转，仅供内网 NAS 使用，不是公开代理。</p>
<p>健康检查：<a href="/health">/health</a></p>
</html>"""


def host_allowed(host: str) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOW_HOSTS)


class Handler(BaseHTTPRequestHandler):
    server_version = "fc2-relay/1.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):  # noqa: N802
        parsed = parse.urlparse(self.path)
        qs = parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            self._json(200, {"ok": True, "service": "fc2-relay",
                             "allow": list(ALLOW_HOSTS)})
            return

        if parsed.path == "/" and not qs.get("url"):
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        if parsed.path not in ("/fetch", "/"):
            self._json(404, {"error": "not found"})
            return

        if (qs.get("key") or [""])[0] != TOKEN:
            self._json(403, {"error": "bad key"})
            return

        target = (qs.get("url") or [""])[0]
        if not target:
            self._json(400, {"error": "missing url"})
            return
        if parse.urlparse(target).scheme not in ("http", "https"):
            self._json(400, {"error": "bad scheme"})
            return
        host = parse.urlparse(target).hostname or ""
        if not host_allowed(host):
            self._json(403, {"error": "host not allowed: %s" % host})
            return

        try:
            req = request.Request(target, headers={"User-Agent": UA,
                                                   "Accept-Language": "ja,en;q=0.8"})
            with request.urlopen(req, timeout=40, context=CTX) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "text/html; charset=utf-8")
            self._send(200, data, ctype)
        except error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()[:4096]
            except Exception:
                pass
            self._send(exc.code, body,
                       exc.headers.get("Content-Type", "text/plain"))
        except Exception as exc:
            self._json(502, {"error": "%s: %s" % (type(exc).__name__, exc)})

    do_HEAD = do_GET


def main() -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("fc2-relay listening on :%d  allow=%s" % (PORT, ALLOW_HOSTS), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
