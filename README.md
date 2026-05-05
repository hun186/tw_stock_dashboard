# 多台股監控 Dashboard（Vercel 版）

這個專案已全面改為 **Vercel 部署版本**，統一使用 `api/main.py` 的 WSGI Dashboard。

> 已移除 Streamlit 版本，避免雙軌維護造成重構與維運混亂。

## 功能

- 一頁顯示多檔台股趨勢
- 支援 `watchlist.csv`
- 支援 `group_map.csv`（可覆蓋自動分類，做主題族群）
- K 線 + MA20
- RSI 14
- 狀態判斷與篩選（資料不足 / 可關注 / 回檔 / 偏熱 / 強勢）
- 可切換期間、K 線週期、股池來源（自選 / 分類）
- 支援族群 / 子族群篩選
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
symbol,name,group,subgroup
2330.TW,台積電,AI晶片,先進製程
4977.TW,眾達-KY,AI光通訊,光通訊模組
3163.TWO,波若威,AI光通訊,光纖元件
```

上市股票通常用 `.TW`，上櫃股票通常用 `.TWO`。

## 自動分類與族群覆蓋

- `分類股池` 來源是證交所上市公司資料（`產業別`），系統會自動轉成 `上市-代碼 - 產業名`（例如 `上市-24 - 半導體業`）。
- 若要改成自己的主題族群（例如 `AI光通訊` / `機器人`），可新增 `group_map.csv`：

```csv
symbol,group
4977.TW,AI光通訊
2454.TW,AI伺服器
```

- 若不想手動維護本機檔，可設定環境變數 `GROUP_MAP_URL` 指向公開 CSV（欄位同樣是 `symbol,group`，例如 GitHub Raw / Google Sheet CSV 匯出連結），系統會自動抓取並套用。
- 覆蓋優先權：`GROUP_MAP_URL`（遠端） > `group_map.csv`（本機） > 系統自動產業分類。

## 免責聲明

這不是投資建議，僅用於觀察與資料整理。
