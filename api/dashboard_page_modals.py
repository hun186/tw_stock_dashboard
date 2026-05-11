from __future__ import annotations


def render_batch_watchlist_modal() -> str:
    return """    <div id='watchlistBatchModal' class='watchlist-batch-modal' role='dialog' aria-modal='true' aria-labelledby='watchlistBatchTitle'>
      <div class='watchlist-batch-dialog'>
        <div class='watchlist-batch-header'>
          <strong id='watchlistBatchTitle'>批次加入自選股</strong>
          <button type='button' onclick='closeBatchWatchlistDialog()' aria-label='關閉'>×</button>
        </div>
        <div class='watchlist-batch-body'>
          <div class='watchlist-batch-help'>先搜尋並勾選多檔股票，或在下方貼上多個代號（可用逗號、空白或換行分隔）；未按「批次加入」前，暫時關閉視窗也會保留已勾選內容。</div>
          <label for='watchKeyword'>關鍵字搜尋</label>
          <div class='watchlist-batch-row'>
            <input id='watchKeyword' placeholder='輸入名稱、代號、主題、次題材或摘要' style='flex:1;min-width:220px'>
            <button type='button' onclick='selectVisibleBatchStocks(true)'>全選搜尋結果</button>
            <button type='button' onclick='selectVisibleBatchStocks(false)'>清除搜尋勾選</button>
          </div>
          <div id='batchStockResults' class='watchlist-batch-list'></div>
          <label for='batchStockSymbols'>貼上代號</label>
          <textarea id='batchStockSymbols' class='watchlist-batch-paste' placeholder='例如：2330 2317
    2454, 2603'></textarea>
          <div id='batchWatchlistPreview' class='watchlist-batch-help'></div>
        </div>
        <div class='watchlist-batch-footer'>
          <button type='button' onclick='closeBatchWatchlistDialog()'>取消</button>
          <button type='button' onclick='addBatchWatchlistStocks()'>批次加入並更新</button>
        </div>
      </div>
    </div>"""


def render_stock_filter_modal() -> str:
    return """    <div id='stockFilterModal' class='watchlist-batch-modal' role='dialog' aria-modal='true' aria-labelledby='stockFilterTitle'>
      <div class='watchlist-batch-dialog'>
        <div class='watchlist-batch-header'>
          <strong id='stockFilterTitle'>股名／代號篩選</strong>
          <button type='button' onclick='closeStockFilterDialog()' aria-label='關閉'>×</button>
        </div>
        <div class='watchlist-batch-body'>
          <div class='watchlist-batch-help'>用和「批次加入自選」相同的搜尋勾選方式建立股名篩選；可勾選的來源僅限目前自選股清單。</div>
          <label for='stockFilterKeyword'>關鍵字搜尋</label>
          <div class='watchlist-batch-row'>
            <input id='stockFilterKeyword' placeholder='輸入名稱、代號、主題、次題材或摘要' style='flex:1;min-width:220px'>
            <button type='button' onclick='selectVisibleStockFilterStocks(true)'>全選搜尋結果</button>
            <button type='button' onclick='selectVisibleStockFilterStocks(false)'>清除搜尋勾選</button>
          </div>
          <div id='stockFilterResults' class='watchlist-batch-list'></div>
          <div id='stockFilterPreview' class='watchlist-batch-help'></div>
        </div>
        <div class='watchlist-batch-footer'>
          <button type='button' onclick='clearStockFilterSelection()'>清除股名篩選</button>
          <button type='button' onclick='closeStockFilterDialog()'>取消</button>
          <button type='button' onclick='applyStockFilterSelection()'>套用篩選並更新</button>
        </div>
      </div>
    </div>"""
