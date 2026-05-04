# 多台股監控 Dashboard（Vercel 版）

這個專案已全面改為 **Vercel 部署版本**，統一使用 `api/main.py` 的 WSGI Dashboard。

> 已移除 Streamlit 版本，避免雙軌維護造成重構與維運混亂。

## 功能

- 一頁顯示多檔台股趨勢
- 支援 `watchlist.csv`
- K 線 + MA20
- RSI 14
- 狀態判斷與篩選（資料不足 / 可關注 / 回檔 / 偏熱 / 強勢）
- 可切換期間、K 線週期、股池來源（自選 / 分類）
- 支援設定儲存到瀏覽器、匯入 / 匯出 JSON 設定

## 本機開發

```bash
cd tw_stock_dashboard
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Vercel 部署

```bash
vercel
vercel --prod
```

Vercel 會直接執行 `api/main.py`。

## URL 參數

可透過 QueryString 調整頁面狀態：

- `tab`: `watchlist` / `category`
- `industry`: 產業代碼（例如 `24`）
- `period`: `3mo` / `6mo` / `1y`
- `interval`: `1d` / `1wk`
- `limit`: 顯示檔數
- `status_filter`: `all` / `watch` / `buy` / `pullback` / `overheat` / `strong`

## 自選股清單

編輯 `watchlist.csv`：

```csv
symbol,name,group
2330.TW,台積電,權值參考
4977.TW,眾達-KY,AI光通訊
4971.TWO,IET-KY,AI光通訊
```

上市股票通常用 `.TW`，上櫃股票通常用 `.TWO`。

## 免責聲明

這不是投資建議，僅用於觀察與資料整理。
