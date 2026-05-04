# 多台股監控 Dashboard（Vercel / WSGI 單一版本）

這是一套以 **WSGI 單頁 Dashboard** 實作的台股監控工具，部署目標為 Vercel（入口：`api/main.py`）。

> 本專案已移除 Streamlit 版本，避免雙版本維護造成功能落差與重構混亂。

## 功能

- 自選股監控 / 分類股池切換
- K 線圖 + MA20
- RSI14 與狀態分類（資料不足 / 回檔 / 跌破 / 過熱 / 強勢）
- 自訂代號清單（`symbols`）
- 自選管理（頁面上加入/刪除代號）
- 每列顯示檔數設定（`cols`）
- 設定存到瀏覽器、下載/匯入設定檔

## 安裝

```bash
cd tw_stock_dashboard
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 本機啟動（WSGI）

可用 gunicorn 啟動：

```bash
gunicorn api.main:app --bind 0.0.0.0:8000
```

然後開啟 `http://127.0.0.1:8000`。

## Vercel 部署

```bash
vercel
vercel --prod
```

## Query 參數

- `tab`: `watchlist` / `category`
- `industry`: 產業代碼（分類池用）
- `period`: `3mo` / `6mo` / `1y`
- `interval`: `1d` / `1wk`
- `limit`: 顯示檔數上限
- `cols`: 每列幾檔（1~4）
- `status_filter`: `all` / `watch` / `buy` / `pullback` / `overheat` / `strong`
- `symbols`: 自訂代號清單（逗號或換行，例如 `2330.TW,2317.TW`）

## 注意

這不是投資建議。資料來自 Yahoo Finance 與公開 API，可能延遲或缺漏。
