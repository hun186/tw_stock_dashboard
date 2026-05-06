# 台股 LLM 批次分類資料源（Excel 輸出版）

這個資料源產生器會從公開資訊觀測站抓取上市 / 上櫃公司基本資料，並輸出 Excel：

```text
tw_stock_llm_source.xlsx
```

欄位：

```text
symbol | name | market | industry | llm_input
```

你可以直接把 `llm_input` 欄位送進 LLM 平行化分析框架跑分類。

## 安裝

```bash
pip install pandas requests openpyxl
```

## 執行

```bash
python build_tw_stock_llm_source_excel.py
```

## 輸出

- `tw_stock_llm_source.xlsx`
- `tw_stock_llm_source.csv`（備用）
