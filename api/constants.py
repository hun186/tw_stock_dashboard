from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = APP_DIR / "watchlist.csv"
LLM_GROUP_FILE = APP_DIR / "data" / "tw_stock_llm_source_with_group.xlsx"
LLM_GROUP_SHEET = "LLM_result_stock_group_json_fla"
TWSE_LISTED_INFO_API = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
STATIC_CACHE_DIR = APP_DIR / "prebuilt_cache"

UP_COLOR = "#d60000"
DOWN_COLOR = "#008a00"
MA5_COLOR = "#ffd400"
MA20_COLOR = "#8a2be2"
MA60_COLOR = "#6ec6ff"

INDUSTRY_CODE_NAME = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維", "05": "電機機械",
    "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙工業", "10": "鋼鐵工業", "11": "橡膠工業",
    "12": "汽車工業", "14": "建材營造", "15": "航運業", "16": "觀光餐旅", "17": "金融保險",
    "18": "貿易百貨", "20": "其他", "21": "化學工業", "22": "生技醫療", "23": "油電燃氣",
    "24": "半導體業", "25": "電腦及週邊", "26": "光電業", "27": "通信網路", "28": "電子零組件",
    "29": "電子通路", "30": "資訊服務", "31": "其他電子", "32": "文化創意", "33": "農業科技",
    "34": "電子商務", "35": "綠能環保", "36": "數位雲端", "37": "運動休閒", "38": "居家生活",
    "80": "管理股票",
}

STATUS_FILTERS = {
    "all": "全部",
    "watch": "⚪ 資料不足",
    "bull": "🔴 偏多",
    "observe": "🟡 觀察",
    "warn": "🟠 風險",
    "bear": "🟢 轉弱",
    "neutral": "⚪ 中性",
}
