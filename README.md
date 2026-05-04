# 多台股監控 Dashboard

這是一套用 Streamlit 製作的台股多檔監控儀表板，適合用來觀察多檔股票是否回檔、是否靠近均線、RSI 是否過熱或轉弱。

## 功能

- 一頁顯示多檔台股趨勢
- 支援自訂 watchlist.csv
- K 線 + MA5 / MA20 / MA60
- RSI 14
- 成交量
- 自動標示：
  - 回檔靠近 MA20
  - 跌破 MA20
  - 強勢在 MA20 上
  - 過熱 RSI
- 可切換期間與 K 線週期
- 支援 `.TW`、`.TWO` Yahoo Finance 股票代號

## 安裝

```bash
cd tw_stock_dashboard
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

macOS / Linux：

```bash
source .venv/bin/activate
```

安裝套件：

```bash
pip install -r requirements.txt
```

## 啟動

```bash
streamlit run app.py
```

瀏覽器會開啟 dashboard。

## 修改股票清單

編輯 `watchlist.csv`：

```csv
symbol,name,group
2330.TW,台積電,權值參考
4977.TW,眾達-KY,AI光通訊
4971.TWO,IET-KY,AI光通訊
```

上市股票通常用 `.TW`，上櫃股票通常用 `.TWO`。

## 回檔判斷邏輯

預設邏輯：

- 價格在 MA20 上方 0%～5%：接近 MA20，可能是回檔觀察區
- 價格跌破 MA20：轉弱 / 需要小心
- 價格高於 MA20 超過 10% 且 RSI > 70：偏熱，不適合追
- 價格仍在 MA20 上且 RSI 未過熱：強勢整理

這不是投資建議，只是幫你快速篩出該看的標的。


## Vercel 線上部署

本專案已加入 Vercel 部署設定（`Dockerfile` + `vercel.json`），可直接部署為線上服務。

### 1) 本機先確認可執行

```bash
streamlit run app.py
```

### 2) 安裝並登入 Vercel CLI

```bash
npm i -g vercel
vercel login
```

### 3) 部署

在專案根目錄執行：

```bash
vercel
```

首次部署時建議選擇：

- Framework Preset: `Other`
- Root Directory: `./`

正式版部署：

```bash
vercel --prod
```

### 4) 重要設定

- Vercel 不會直接用 `Dockerfile` 跑 Streamlit；其 Python Runtime 需要可辨識的入口點。
- 本專案提供 `api/main.py`（WSGI）作為 Vercel 入口，避免 build 階段出現「No python entrypoint found」。
- 若要完整執行互動式 Streamlit 介面，建議改用可長時間執行行程的容器平台（例如 Railway、Render、Fly.io）。
