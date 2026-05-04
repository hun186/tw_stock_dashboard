"""Vercel Python entrypoint.

Vercel's Python runtime is request/response based and does not run Streamlit's
long-lived server process. This endpoint returns a helpful HTML page and can
optionally redirect users to a hosted Streamlit URL via STREAMLIT_PUBLIC_URL.
"""

from __future__ import annotations

import html
import os


STREAMLIT_PUBLIC_URL = os.getenv("STREAMLIT_PUBLIC_URL", "").strip()


def _render_html() -> str:
    safe_url = html.escape(STREAMLIT_PUBLIC_URL, quote=True)

    if STREAMLIT_PUBLIC_URL:
        return f"""<!doctype html>
<html lang=\"zh-Hant\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <meta http-equiv=\"refresh\" content=\"2;url={safe_url}\" />
  <title>tw_stock_dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; line-height: 1.6; }}
    .card {{ max-width: 720px; padding: 1.25rem 1.5rem; border: 1px solid #ddd; border-radius: 12px; }}
    a.btn {{ display: inline-block; margin-top: 0.8rem; padding: 0.55rem 0.9rem; background: #111; color: #fff; border-radius: 8px; text-decoration: none; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>tw_stock_dashboard</h1>
    <p>正在導向到 Streamlit 儀表板…</p>
    <p>若未自動跳轉，請點下面按鈕：</p>
    <a class=\"btn\" href=\"{safe_url}\">開啟 Dashboard</a>
  </div>
</body>
</html>"""

    return """<!doctype html>
<html lang=\"zh-Hant\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>tw_stock_dashboard</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; line-height: 1.7; }
    .card { max-width: 760px; padding: 1.25rem 1.5rem; border: 1px solid #ddd; border-radius: 12px; }
    code { background: #f5f5f5; padding: 0.1rem 0.35rem; border-radius: 4px; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>tw_stock_dashboard</h1>
    <p>這個專案是 <strong>Streamlit</strong> 應用，Vercel Python Runtime 無法直接執行長時間常駐的 Streamlit 服務。</p>
    <p>你可以：</p>
    <ol>
      <li>本機執行：<code>streamlit run app.py</code></li>
      <li>部署到支援長時間行程的容器平台（Railway / Render / Fly.io）</li>
      <li>若你已有外部 Streamlit 網址，請在 Vercel 設定環境變數 <code>STREAMLIT_PUBLIC_URL</code>，此頁會自動導向。</li>
    </ol>
  </div>
</body>
</html>"""


def app(environ, start_response):
    body = _render_html().encode("utf-8")

    status = "200 OK"
    headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    start_response(status, headers)
    return [body]
