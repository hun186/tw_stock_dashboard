# Codex 多階段精進指引：Gemini 題材資料應用

這份文件把 Gemini agent 產出的「題材 / 次題材 Excel」與「個股 summary / reference_url」整理成後續可交給 Codex 分階段實作的產品藍圖。目標是讓台股 Dashboard 從技術線圖監控，逐步升級為「題材研究 + 技術訊號 + 個人筆記 + 自動快報」的研究工作台。

## 現況與核心資產

- Gemini agent 分析結果預期放在 `data/tw_stock_llm_datasource_excel/tw_stock_analysis_result_Gemini_agent.xlsx`，目前 Dashboard 已支援讀取 `symbol`、`name`、`group`、`subgroup` 等分類欄位。
- Gemini Excel 若包含 `summary` 與 `reference_url`，這兩欄可作為題材脈絡、資料來源與個股研究卡的核心內容。
- Dashboard 已有技術指標與訊號：MA、RSI、量能、20 日高低點、突破、過熱、跌破 MA20、縮量盤整等。
- Dashboard 已有股池來源、產業、主題、次題材、個人標籤與備註等互動框架，適合逐步加上 LLM 題材資料應用。

## 多階段精進路線圖

### Phase 1：資料完整接入與摘要顯示

**目標**：先把 Gemini Excel 裡還沒充分利用的 `summary`、`reference_url` 帶進 Dashboard，讓使用者在看線圖與表格時能直接理解個股題材來源。

**建議實作**：

1. 擴充資料載入層，讓 Gemini / LLM 分類結果可保留 `summary`、`reference_url`。
2. 維持既有 `symbol`、`name`、`group`、`subgroup` 欄位相容性，避免破壞 watchlist 與舊版 Excel。
3. 在股票總表新增「題材摘要」與「來源」欄位，或以可展開區塊 / tooltip 顯示。
4. 在股票卡片加入個股摘要短文與來源連結。
5. 讓批次加入自選與股名篩選的搜尋可匹配 summary 關鍵字。

**驗收標準**：

- Excel 有 `summary`、`reference_url` 時，Dashboard 能正常顯示。
- Excel 沒有這兩欄時，Dashboard 不會錯誤，並以空字串或 `-` 呈現。
- 既有測試通過，且 watchlist / category 兩種頁籤都能正常顯示。

### Phase 2：題材輪動雷達

**目標**：把個股技術訊號聚合成題材層級的熱度與風險，讓使用者先看題材，再鑽進個股。

**建議實作**：

1. 依 `group` 與 `subgroup` 聚合目前候選股或分析後股票。
2. 統計每個題材的股票數、強勢 / 觀察 / 風險 / 轉弱 / 中性檔數。
3. 計算題材平均漲跌幅、平均成交量、平均訊號分數。
4. 建立「題材熱度分數」，例如：強勢檔數、訊號分數、量能擴張與風險檔數加權。
5. 在 Dashboard 新增「題材熱度榜」區塊，支援點擊題材後自動套用篩選。

**驗收標準**：

- 使用者可看到主題 / 次題材排行榜。
- 每個題材列出偏多、觀察、警示、轉弱檔數。
- 點擊題材能切換至對應 `group_filter` / `subgroup_filter`。

### Phase 3：題材型選股器

**目標**：把「題材分類、summary 關鍵字、技術訊號、量能條件」組合成多條件選股器。

**建議實作**：

1. 新增 summary 關鍵字搜尋，例如搜尋「儲能」、「虛擬電廠」、「CPO」、「海外」、「併購」。
2. 新增技術訊號篩選，例如突破、放量上漲、回測 MA20、過熱、跌破 MA20。
3. 新增量能條件，例如成交量大於 20 日均量 1.5x、2x、4x。
4. 新增「同題材強勢股」、「同題材低基期」、「同題材風險股」快捷篩選。
5. 將篩選結果支援匯出 JSON 或 CSV，方便保存研究清單。

**驗收標準**：

- 使用者可用 summary 關鍵字搭配主題 / 次題材與技術訊號篩選。
- 篩選狀態可透過 URL 參數保存或分享。
- 不影響既有自選股與個人標籤功能。

### Phase 4：個股研究卡與投資筆記

**目標**：讓每檔股票變成可長期追蹤的研究卡，結合 LLM 摘要、來源、技術狀態與個人筆記。

**建議實作**：

1. 在股票卡片或表格列加入「展開研究卡」功能。
2. 研究卡內容包含：公司名稱、代號、主題、次題材、summary、reference_url、形勢判斷、收盤價、目標價、目標價 / 現價。
3. 整合既有個人欄位：操作方法、個股特性、行情階段、風險與觀察、備註。
4. 增加「研究卡匯出」功能，支援 Markdown 複製或 JSON 匯出。
5. 若後續接入 LLM，可根據研究卡產生「觀察重點」與「需驗證問題」。

**驗收標準**：

- 使用者能從任一股票打開完整研究卡。
- 研究卡可複製成 Markdown。
- 個人標籤與備註仍保存在瀏覽器備份機制中。

### Phase 5：每日題材快報與告警

**目標**：將 Dashboard 分析結果整理成每日收盤後可閱讀的題材快報。

**建議實作**：

1. 新增產生日報的 script 或 API route。
2. 日報包含：最強題材 Top N、題材內強勢股、題材內風險股、新突破股、過熱股、跌破 MA20 股。
3. 每檔重點股票附上 Gemini summary 的短摘與來源 URL。
4. 支援輸出 Markdown、HTML 或 JSON。
5. 後續可接 GitHub Actions、Email、LINE Notify 替代方案或其他推播服務。

**驗收標準**：

- 可在本機執行指令產生一份 Markdown 日報。
- 日報內容不依賴瀏覽器互動。
- 無法取得價格或摘要時，輸出清楚的缺資料提示。

### Phase 6：題材關聯圖、相似股與持股曝險

**目標**：把 Gemini 題材資料升級為研究知識圖譜與投資組合檢查工具。

**建議實作**：

1. 題材關聯圖：建立 `group -> subgroup -> stock` 的節點與邊。
2. 相似股推薦：以 summary、group、subgroup 做文字相似度或 embedding，比對同題材股票。
3. 持股題材曝險：若 watchlist 或未來持股資料包含權重 / 市值，統計各題材曝險比例。
4. 題材版本控管：記錄每次 Gemini agent 輸出的日期、變動股票、分類變化與 summary 更新。
5. 資料品質檢查：找出缺 summary、缺 reference_url、分類過粗、來源失效的股票。

**驗收標準**：

- 可輸出題材關聯資料 JSON。
- 可列出任一股票的同題材 / 相似摘要候選股。
- 可產生資料品質報告。

## 共通開發原則

- 保持向後相容：舊 Excel、watchlist 與官方產業 fallback 不應因新增欄位失效。
- 欄位缺失要優雅降級：`summary`、`reference_url`、目標價或價格資料缺失時不可讓頁面壞掉。
- 優先用純函式整理資料，讓單元測試容易覆蓋。
- 外部網路資料應盡量快取或預先產生，避免 Vercel Serverless 逾時。
- 新增 UI 功能時，注意表格不要過寬；摘要適合用展開、tooltip 或研究卡呈現。
- 若新增可分享狀態，優先使用 URL 參數，並確保本機設定匯入 / 匯出仍可保存。

## Codex 提詞模板

### 總提詞：要求 Codex 先讀本指引

```text
請先閱讀 `docs/codex_llm_theme_enhancement_guide.md`，再依照其中 Phase 1 到 Phase 6 的順序協助精進這個台股 Dashboard。每次只實作一個明確階段或子任務，保持向後相容，新增或更新測試，完成後提交 commit 並建立 PR 說明。
```

### Phase 1 提詞：接入 summary 與 reference_url

```text
請依照 `docs/codex_llm_theme_enhancement_guide.md` 的 Phase 1，讓 Gemini agent Excel 的 `summary` 與 `reference_url` 欄位被資料載入層保留並顯示在 Dashboard。需求：
1. 支援欄位別名，例如 `summary` / `摘要` / `題材摘要`，以及 `reference_url` / `url` / `來源` / `資料來源`。
2. 舊 Excel 沒有這兩欄時不可壞掉。
3. 股票總表或股票卡片要能看到摘要與來源連結。
4. 搜尋股票時可以匹配 summary 關鍵字。
5. 補上或更新測試，最後 commit 並建立 PR。
```

### Phase 2 提詞：題材輪動雷達

```text
請依照 `docs/codex_llm_theme_enhancement_guide.md` 的 Phase 2，新增題材輪動雷達。需求：
1. 依 `group` 與 `subgroup` 聚合已分析股票的訊號結果。
2. 顯示每個題材的股票數、偏多、觀察、警示、轉弱、中性檔數。
3. 計算題材平均漲跌幅、平均訊號分數與題材熱度分數。
4. 在 Dashboard 新增題材熱度榜，點擊後可套用主題 / 次題材篩選。
5. 補上測試，確保空資料與缺欄位時也能安全運作。
```

### Phase 3 提詞：題材型選股器

```text
請依照 `docs/codex_llm_theme_enhancement_guide.md` 的 Phase 3，新增題材型選股器。需求：
1. 支援 summary 關鍵字篩選。
2. 支援技術訊號 code / bucket 篩選。
3. 支援量能倍數條件篩選。
4. 篩選狀態可透過 URL 參數保存。
5. 不破壞現有自選股、分類股池與個人標籤篩選。
```

### Phase 4 提詞：個股研究卡

```text
請依照 `docs/codex_llm_theme_enhancement_guide.md` 的 Phase 4，新增個股研究卡。需求：
1. 使用者能從表格或股票卡片打開研究卡。
2. 研究卡顯示公司名稱、代號、主題、次題材、summary、reference_url、形勢判斷、收盤價、目標價與個人標籤欄位。
3. 提供一鍵複製 Markdown 功能。
4. 研究卡在缺少 summary、reference_url 或目標價時要優雅降級。
5. 補上測試或至少補上關鍵 HTML 產出測試。
```

### Phase 5 提詞：每日題材快報

```text
請依照 `docs/codex_llm_theme_enhancement_guide.md` 的 Phase 5，新增每日題材快報功能。需求：
1. 新增可在本機執行的 script，輸出 Markdown 日報。
2. 日報包含最強題材、題材內強勢股、風險股、新突破股、過熱股與跌破 MA20 股。
3. 每檔重點股票附上 Gemini summary 短摘與 reference_url。
4. 價格資料或 summary 缺失時要輸出清楚提示。
5. 補上測試，避免外部網路不穩造成測試失敗。
```

### Phase 6 提詞：關聯圖、相似股與曝險分析

```text
請依照 `docs/codex_llm_theme_enhancement_guide.md` 的 Phase 6，先實作題材關聯資料輸出與資料品質報告。需求：
1. 輸出 `group -> subgroup -> stock` 的 JSON 結構。
2. 產生缺 summary、缺 reference_url、分類過粗的資料品質報告。
3. 提供任一股票的同題材候選股列表。
4. 先使用本機資料與簡單文字比對，不要強制依賴外部 embedding API。
5. 補上測試與 README 說明。
```

## 推薦執行順序

1. 先做 Phase 1，因為資料已經存在，效果最快。
2. 再做 Phase 2，讓題材分類真正變成「題材輪動」觀察工具。
3. 接著做 Phase 4，強化單檔研究體驗。
4. Phase 3 可依使用者篩選需求穿插進行。
5. Phase 5 適合在資料與訊號穩定後導入自動化。
6. Phase 6 屬於研究平台化，可最後逐步加深。
