# 每日題材分析報告說明

每日題材分析報告是把股池中的個股技術訊號、題材分類、Gemini / LLM 摘要與來源連結整理成 Markdown 快報的離線批次功能。它的定位是「收盤後的宏觀題材觀察」，不是在 Vercel runtime 內即時大量爬價產生的互動報告。

## 報告適合回答什麼問題？

報告會聚合全股池資料，協助快速檢查：

- 當期最強題材 Top N。
- 每個題材內的強勢股與風險股。
- 新突破股、過熱股、跌破 MA20 股。
- 題材 / 個股是否缺價格、缺 Gemini summary、缺 reference_url。
- 個股對應的題材、次題材、短摘要與來源 URL。

報告內容適合用於盤後整理與隔日觀察清單，不應被解讀成投資建議。

## 核心設計：CI 預建，Vercel 只讀

Vercel 的 Serverless runtime 不適合在使用者點擊時大量下載 2,000 多檔股票價格，也不適合把產出的報告寫回檔案系統。因此本專案採用以下流程：

1. GitHub Actions 在台股收盤後重建 `prebuilt_cache/`。
2. 同一個 workflow 使用更新後的快取產生 `reports/daily_theme_report.md`。
3. workflow 將快取與報告 commit 回 repository。
4. Vercel 重新部署後，只提供報告狀態檢測與 Markdown 下載，不在 runtime 寫檔。

相關 workflow：`.github/workflows/rebuild-prebuilt-cache.yml`。

## 本機產生報告

### 使用預設輸出路徑

```bash
python scripts/generate_theme_daily_report.py
```

預設會輸出到：

```text
reports/daily_theme_report.md
```

### 指定輸出檔案

```bash
python scripts/generate_theme_daily_report.py --output rep.md
```

### 指定報告標題日期

```bash
python scripts/generate_theme_daily_report.py --output rep.md --as-of 2026-05-12
```

`--as-of` 只會指定報告標題與報告日期文字，例如 `# 台股每日題材快報（2026-05-12）`。它目前不是價格資料的截止日過濾器，也不會強制資料切到指定交易日。

如果要產出「某一天收盤版」報告，請確認 `prebuilt_cache/` 是該交易日收盤後更新的快取，再搭配 `--as-of` 標示報告日。

### 限制分析股票數（快速試跑）

```bash
python scripts/generate_theme_daily_report.py --output rep.md --stock-limit 50
```

此參數只取股池前 N 檔，適合確認格式或 debug，不適合當正式全市場報告。

### 允許即時抓價

```bash
python scripts/generate_theme_daily_report.py --output rep.md --allow-live-fetch
```

`--allow-live-fetch` 會在缺少快取或快取過舊時嘗試線上抓價。完整股池可能超過 2,000 檔，盤中還可能額外抓即時 / 分鐘資料，因此可能跑很久，也可能受到資料源限流影響。正式報告建議優先依賴收盤後 GitHub Actions 預建快取。

## 建議操作情境

| 情境 | 建議指令 / 流程 | 注意事項 |
| --- | --- | --- |
| 收盤後正式報告 | GitHub Actions 自動產生 | 使用更新後的 `prebuilt_cache/`，Vercel 只提供下載 |
| 本機重建正式報告 | `python scripts/prebuild_price_cache.py` 後再跑 `python scripts/generate_theme_daily_report.py --as-of YYYY-MM-DD` | `--as-of` 只是標題日期，資料完整性取決於快取 |
| 快速測格式 | `python scripts/generate_theme_daily_report.py --stock-limit 50 --output rep.md` | 只分析前 50 檔，不代表全市場 |
| 盤中臨時觀察 | `python scripts/generate_theme_daily_report.py --allow-live-fetch --output rep.md` | 盤中資料未收盤，突破 / 過熱 / 跌破訊號可能收盤後改變 |

## 儀表板上的檢測與下載

Dashboard 標題列右側提供：

- **檢測報告**：呼叫 `/api/theme-report/status`，確認部署中是否有 `reports/daily_theme_report.md`。
- **下載報告**：呼叫 `/api/theme-report/download`，直接下載預建 Markdown。

若尚未找到報告，代表目前部署沒有包含 `reports/daily_theme_report.md`。請等待 GitHub Actions 收盤後產生並由 Vercel 部署，或在本機產生後確認檔案有被 commit。

## 報告資料來源與欄位

報告股池由以下來源合併：

1. Gemini agent 題材 Excel。
2. 舊版 LLM 分類 Excel。
3. `watchlist.csv`。

每檔股票會嘗試讀取：

- `symbol` / `name`。
- `group` / `subgroup` 題材分類。
- `summary` Gemini 摘要。
- `reference_url` 來源網址。
- 價格快取資料，用於計算收盤價、漲跌幅、突破 / 過熱 / MA20 訊號。

若缺少價格、summary 或 reference_url，報告會在資料品質提示與個股條目中標示缺資料。

## 常見疑問

### 早上 10 點跑，會是今天的完整日報嗎？

不會。若早上 10 點使用 `--as-of` 或預設今天日期，標題可能是今天，但今天尚未收盤。若加上 `--allow-live-fetch`，資料更接近盤中快照，不是收盤資料。正式「每日」報告建議收盤後產生。

### 為什麼不在 Vercel 點按鈕直接產生報告？

完整股池 live fetch 負載很大，可能造成 Serverless timeout，也無法可靠寫入 Vercel 檔案系統。按鈕設計成「檢測 / 下載預建報告」，把大量資料更新交給 GitHub Actions。

### `--as-of` 可以指定歷史交易日嗎？

目前只能指定報告日期文字，不能保證價格資料截止在該交易日。若未來要嚴格支援歷史交易日，建議新增 `--data-date` 或 `--price-date`，在分析前過濾價格資料到指定日期。

## Troubleshooting

- **全部股票都缺價格資料**：先執行 `python scripts/prebuild_price_cache.py`，或小量測試時加 `--allow-live-fetch --stock-limit 50`。
- **`--allow-live-fetch` 跑很久**：完整股池很大，請改用 `--stock-limit` 測試，正式報告交給 GitHub Actions。
- **儀表板顯示找不到報告**：確認 `reports/daily_theme_report.md` 是否存在、是否已 commit、Vercel 是否已部署到包含該檔案的 commit。
- **報告日期與資料日期不一致**：目前報告日期由 `--as-of` 或執行當天決定；資料日期由快取內容決定。
