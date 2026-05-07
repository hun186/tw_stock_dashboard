# 多台股監控 Dashboard（Vercel 版）

這個專案已全面改為 **Vercel 部署版本**，統一使用 `api/main.py` 的 WSGI Dashboard。

線上展示網址：[https://tw-stock-dashboard-six.vercel.app/](https://tw-stock-dashboard-six.vercel.app/)

> 已移除 Streamlit 版本，避免雙軌維護造成重構與維運混亂。

## 功能

- 一頁顯示多檔台股趨勢
- 支援 `watchlist.csv`
- K 線 + MA20
- RSI 14
- 形勢判斷與篩選（資料不足 / 偏多 / 觀察 / 風險 / 轉弱 / 中性）
- 可切換期間、K 線週期、股池來源（自選 / 分類）
- 支援設定儲存到瀏覽器、匯入 / 匯出 JSON 設定


## 示意圖

### Dashboard 總覽

![多台股監控 Dashboard 總覽](docs/screenshots/dashboard-overview.svg)

### 總表個人標籤

![總表個人標籤與觀察備註](docs/screenshots/stock-meta-table.svg)

## 功能截圖

### 篩選與排序選項

![篩選與排序選項](docs/screenshots/filter_option.png)

### 設定匯入 / 匯出

![設定匯入與匯出](docs/screenshots/config_io.png)

### 股票總表與個人標籤

![股票總表與個人標籤](docs/screenshots/stock_tables.png)

### Dashboard 曲線圖

![Dashboard 曲線圖](docs/screenshots/dashboard_curves.png)

### Dashboard 文字摘要

![Dashboard 文字摘要](docs/screenshots/dashboard_text.png)

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
- `status_filter`: `all` / `watch` / `bull` / `observe` / `warn` / `bear` / `neutral`
- `card_sort`: `signal_score`（預設）/ `symbol` / `close` / `volume` / `change_pct` / `target_ratio`
- `show_target_price`: `0` / `1`（預設 `0`；開啟會逐檔查 Yahoo 目標價，速度較慢）
- `compact_progress`: `1` / `0`（預設 `1`；開啟後將處理進度縮成單列精簡顯示）

## 自選股清單

編輯 `watchlist.csv`：

```csv
symbol,name,group
2330.TW,台積電,權值參考
4977.TW,眾達-KY,AI光通訊
4971.TWO,IET-KY,AI光通訊
```

上市股票通常用 `.TW`，上櫃股票通常用 `.TWO`。

## LLM 主題分類匯入（可選）

若有外部批次分析輸出，可將檔案放在 `data/tw_stock_llm_source_with_group.xlsx`，
並使用工作表 `LLM_result_stock_group_json_fla`。程式會讀取欄位：

- `symbol`
- `name`
- `group`
- `subgroup`（可選）

合併規則：

- 先載入 LLM 分類
- 再疊上 `watchlist.csv`
- 若同一 `symbol` 重複，以 `watchlist.csv` 為優先（可手動覆寫 LLM 分類）


## 效能瓶頸與加速策略

切換頁籤或刷新頁面時，後端會重新組合股池、抓取每頁股票價格、計算技術指標並產生 Plotly 圖表。最容易造成等待的環節有三個：

1. **價格資料**：日線 / 週線會優先讀取 `prebuilt_cache/`，避免每次頁面操作都打 Yahoo Finance。預建快取現在允許保留 7 天；分鐘線仍維持短 TTL，以免盤中資料過舊。
2. **靜態股池資料**：自選清單、LLM 分類 Excel、上市 / 上櫃產業清單會在同一個 Python process 內快取，減少重複讀檔與重複呼叫交易所 OpenAPI。
3. **目標價**：Yahoo `Ticker.get_info()` 是逐檔外部查詢，容易拖慢整頁渲染；因此預設關閉，需要時可從頁面上的「目標價」選單或 `show_target_price=1` 開啟。

若要維持最快刷新速度，建議：

- 使用日線 / 週線並定期執行 `python scripts/prebuild_price_cache.py` 更新 `prebuilt_cache/`。
- 每頁檔數不要一次拉太大；頁面仍需為每檔股票產生 Plotly HTML。
- 非必要時保持「目標價」關閉。

## 免責聲明

這不是投資建議，僅用於觀察與資料整理。

## 預先產生快取（適合 Vercel 唯讀檔案系統）

Vercel 執行環境是唯讀，不適合在使用者操作時動態落盤快取。
本專案改為支援「**先在本機或 CI 預產生快取檔，再跟程式一起 deploy**」。

### 1) 產生快取檔

```bash
python scripts/prebuild_price_cache.py
```

會將自選股的歷史資料輸出到 `prebuilt_cache/`。

### 2) 提交到 GitHub

```bash
git add prebuilt_cache scripts/prebuild_price_cache.py
git commit -m "chore: refresh prebuilt price cache"
git push
```

### 3) Vercel 自動部署

push 後由 Vercel 自動部署，`api/main.py` 會優先讀取 `prebuilt_cache/` 的資料，降低使用者操作時等待。

## GitHub Actions 自動重建快取

已提供排程檔：`.github/workflows/rebuild-prebuilt-cache.yml`。

- 觸發方式：
  - 每週一到五 UTC `06:10`（約台北時間 `14:10`，收盤後）
  - 或手動 `workflow_dispatch`
- 流程：安裝依賴 → 執行 `python scripts/prebuild_price_cache.py` → 若 `prebuilt_cache/` 有變更就自動 commit + push。

> 第一次使用前，請確認 repository 的 Actions 權限允許 `contents: write`。
