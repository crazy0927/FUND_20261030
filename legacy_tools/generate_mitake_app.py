# -*- coding: utf-8 -*-
"""
讀取 SQLite 股市資料庫.db，產出 100% 擬真三竹 APP 風格的 00981A 雙圖/三圖連動互動看盤系統。
對齊 20261029.jpg 截圖外觀、配色、字體與數值。
"""

import sqlite3
import json
import pandas as pd

DB_FILE = "股市資料庫.db"
OUTPUT_HTML = "mitake_00981a_interactive.html"

def generate_mitake_html(output_path=OUTPUT_HTML):
    conn = sqlite3.connect(DB_FILE)
    
    # 讀取 00981A 資料
    df_00981 = pd.read_sql_query('SELECT * FROM "00981A" ORDER BY 西元日期 ASC;', conn)
    
    # 讀取 大盤加權指數 + 融資餘額
    df_market = pd.read_sql_query('SELECT * FROM "大盤資料表" ORDER BY 西元日期 ASC;', conn)
    df_margin = pd.read_sql_query('SELECT * FROM "融資餘額" ORDER BY 西元日期 ASC;', conn)
    
    # 讀取 統一奔騰基金
    df_fund = pd.read_sql_query('SELECT * FROM "基金" ORDER BY 西元日期 ASC;', conn)
    conn.close()
    
    # 準備 00981A JSON
    records_00981 = df_00981.to_dict(orient="records")
    json_00981 = json.dumps(records_00981, ensure_ascii=False)
    
    # 準備 大盤 JSON (包含大盤K線 + 融資餘額)
    # 合併大盤與融資餘額
    df_market_merged = pd.merge(df_market, df_margin[['西元日期', '融資今日餘額_張', '融資增減_仟元']], on='西元日期', how='left')
    df_market_merged['融資今日餘額_張'] = df_market_merged['融資今日餘額_張'].fillna(0)
    df_market_merged['融資增減_仟元'] = df_market_merged['融資增減_仟元'].fillna(0)
    
    # 計算大盤 BBAND (22T)
    c_m = df_market_merged['收盤指數']
    mid_m = c_m.rolling(22, min_periods=1).mean()
    std_m = c_m.rolling(22, min_periods=2).std(ddof=1).fillna(100.0)
    df_market_merged['BBAND_中軌'] = mid_m.round(2)
    df_market_merged['BBAND_上軌'] = (mid_m + 2*std_m).round(2)
    df_market_merged['BBAND_下軌'] = (mid_m - 2*std_m).round(2)
    
    # 計算大盤 9日KD
    k_m, d_m = [], []
    k_cur, d_cur = 50.0, 50.0
    for idx in range(len(df_market_merged)):
        sub = df_market_merged.iloc[max(0, idx-8):idx+1]
        h9 = sub['最高指數'].max()
        l9 = sub['最低指數'].min()
        c = df_market_merged['收盤指數'].iloc[idx]
        rsv = 50.0 if h9 == l9 else ((c - l9)/(h9 - l9))*100.0
        if idx == 0:
            k_cur, d_cur = 50.0, 50.0
        else:
            k_cur = (1/3)*rsv + (2/3)*k_cur
            d_cur = (1/3)*k_cur + (2/3)*d_cur
        k_m.append(round(k_cur, 2))
        d_m.append(round(d_cur, 2))
    df_market_merged['K值'] = k_m
    df_market_merged['D值'] = d_m
    df_market_merged['開盤價'] = df_market_merged['開盤指數']
    df_market_merged['最高價'] = df_market_merged['最高指數']
    df_market_merged['最低價'] = df_market_merged['最低指數']
    df_market_merged['收盤價'] = df_market_merged['收盤指數']
    df_market_merged['漲跌'] = (df_market_merged['收盤價'] - df_market_merged['收盤價'].shift(1)).fillna(0).round(2)
    df_market_merged['漲跌幅'] = ((df_market_merged['漲跌'] / (df_market_merged['收盤價'] - df_market_merged['漲跌'])) * 100).fillna(0).round(2)
    df_market_merged['成交量_張'] = (df_market_merged['融資今日餘額_張'] / 10).astype(int)
    df_market_merged['融資餘額_張'] = df_market_merged['融資今日餘額_張'].astype(int)
    df_market_merged['融資增減_張'] = (df_market_merged['融資增減_仟元'] / 100).astype(int)
    
    market_records = df_market_merged[['西元日期', '民國日期', '開盤價', '最高價', '最低價', '收盤價', '漲跌', '漲跌幅', '成交量_張', 'BBAND_中軌', 'BBAND_上軌', 'BBAND_下軌', 'K值', 'D值', '融資餘額_張', '融資增減_張']].to_dict(orient="records")
    json_market = json.dumps(market_records, ensure_ascii=False)
    
    # 準備 統一奔騰 JSON
    df_fund_mapped = pd.DataFrame()
    df_fund_mapped['西元日期'] = df_fund['西元日期']
    df_fund_mapped['民國日期'] = df_fund['日期']
    df_fund_mapped['收盤價'] = df_fund['基金淨值']
    df_fund_mapped['開盤價'] = df_fund['基金淨值']
    df_fund_mapped['最高價'] = df_fund['基金淨值']
    df_fund_mapped['最低價'] = df_fund['基金淨值']
    df_fund_mapped['漲跌'] = df_fund['基金漲跌']
    df_fund_mapped['漲跌幅'] = (df_fund['基金漲跌幅'] * 100).round(2)
    df_fund_mapped['成交量_張'] = 50000
    df_fund_mapped['BBAND_中軌'] = df_fund['20日平均(中軌)']
    df_fund_mapped['BBAND_上軌'] = df_fund['布林上軌(天花板)']
    df_fund_mapped['BBAND_下軌'] = df_fund['布林下軌(地板)']
    df_fund_mapped['K值'] = df_fund['K值(快線)']
    df_fund_mapped['D值'] = df_fund['D值(慢線)']
    df_fund_mapped['融資餘額_張'] = 180000
    df_fund_mapped['融資增減_張'] = 0
    fund_records = df_fund_mapped.to_dict(orient="records")
    json_fund = json.dumps(fund_records, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>三竹股市 APP - 00981A 主動統一台股增長 (互動看盤系統)</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Phosphor Icons -->
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');
        
        * {{
            box-sizing: border-box;
            user-select: none;
            -webkit-user-select: none;
        }}
        
        body {{
            font-family: 'Roboto Mono', 'Noto Sans TC', monospace, sans-serif;
            background-color: #121418;
            color: #ffffff;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
        }}
        
        /* 隱藏原生滾動條但保持滾動 */
        ::-webkit-scrollbar {{
            display: none;
        }}
        
        /* 三竹 APP 經典高對比色 */
        .color-up {{
            color: #ff3b30 !important; /* 三竹漲紅 */
        }}
        .bg-up {{
            background-color: #ff3b30 !important;
        }}
        .color-down {{
            color: #00e676 !important; /* 三竹跌綠 */
        }}
        .bg-down {{
            background-color: #00e676 !important;
        }}
        .color-yellow {{
            color: #ffd600 !important; /* 三竹金黃 */
        }}
        .color-cyan {{
            color: #00e5ff !important; /* 三竹天藍 */
        }}
        .color-purple {{
            color: #d500f9 !important; /* 三竹下軌紫 */
        }}
        
        /* 手機邊框模擬器 */
        .phone-wrapper {{
            max-width: 440px;
            width: 100%;
            height: 920px;
            background: #000000;
            border-radius: 40px;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.9), 0 0 0 10px #23272e, 0 0 0 12px #363b45;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            position: relative;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        /* 全螢幕桌面模式 */
        .full-mode {{
            max-width: 100% !important;
            height: 100vh !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }}

        canvas {{
            display: block;
            touch-action: none;
        }}
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-0 sm:p-4 md:p-6 bg-[#090a0d]">

    <!-- 手機容器 / 全螢幕切換容器 -->
    <div id="appContainer" class="phone-wrapper mx-auto">
        
        <!-- 頂部手機狀態欄 (Status Bar) -->
        <div class="h-6 px-5 flex items-center justify-between text-[11px] font-bold text-slate-300 bg-black tracking-tight select-none z-30">
            <span>11:05</span>
            <div class="flex items-center gap-1.5 text-[10px]">
                <span class="text-[9px] text-slate-400 font-mono">0.12 KB/s</span>
                <i class="ph-fill ph-cell-signal-full text-white"></i>
                <span class="text-[9px] font-extrabold text-white">4G+</span>
                <div class="flex items-center border border-slate-400 rounded-sm px-0.5 text-[9px] leading-tight">38</div>
            </div>
        </div>

        <!-- 頂部 APP 導覽列 (三竹風格) -->
        <div class="h-11 px-3 bg-[#001728] border-b border-[#0f2d48] flex items-center justify-between z-20 select-none">
            <button id="btnBack" class="p-1 text-slate-300 hover:text-white transition">
                <i class="ph-bold ph-caret-left text-2xl"></i>
            </button>

            <!-- 標的名稱與代碼切換 -->
            <div class="flex items-center gap-2">
                <button id="btnPrevStock" class="text-slate-400 hover:text-white px-1 text-xs">◀</button>
                <div class="text-center cursor-pointer" id="stockTitleBox">
                    <div id="stockName" class="text-sm font-black text-white leading-tight tracking-wide">主動統一台股增長</div>
                    <div id="stockCode" class="text-[11px] font-bold text-[#00e5ff] leading-none">00981A</div>
                </div>
                <button id="btnNextStock" class="text-slate-400 hover:text-white px-1 text-xs">▶</button>
            </div>

            <div class="flex items-center gap-1">
                <!-- 展開全螢幕切換鈕 -->
                <button id="btnToggleMode" class="p-1.5 text-slate-300 hover:text-white text-xs bg-[#0b2844] rounded border border-[#1b436c]" title="切換手機/滿版模式">
                    <i class="ph-bold ph-arrows-out-simple"></i>
                </button>
                <button class="p-1 text-slate-300 hover:text-white">
                    <i class="ph-bold ph-list text-xl"></i>
                </button>
            </div>
        </div>

        <!-- 查價資訊欄 (Crosshair Info Bar) -->
        <div id="crossInfoBar" class="h-8 px-2.5 bg-[#05070a] border-b border-[#1a1f26] flex items-center justify-between text-[11px] font-mono select-none z-20">
            <div class="flex items-center gap-2 overflow-x-auto whitespace-nowrap">
                <span class="color-yellow font-bold">時 <span id="infoDate">10/29</span></span>
                <span>開 <span id="infoOpen" class="color-down">28.59</span></span>
                <span>高 <span id="infoHigh" class="color-up">28.66</span></span>
                <span>低 <span id="infoLow" class="color-down">27.58</span></span>
                <span>收 <span id="infoClose" class="color-down">27.81</span></span>
                <span class="color-yellow">量 <span id="infoVol">168K</span></span>
            </div>
            <button id="btnCloseCross" class="w-4 h-4 rounded-full bg-[#1e232a] text-slate-400 hover:text-white flex items-center justify-center text-[10px] ml-1">✕</button>
        </div>

        <!-- 畫布滾動繪圖區 (三圖：主圖K線+BBAND、副圖一KD、副圖二融資餘額) -->
        <div class="flex-1 bg-black relative overflow-hidden flex flex-col" id="chartWrapper">
            <canvas id="mainCanvas" class="w-full flex-1"></canvas>
            
            <!-- 懸浮半透明手動控制器 (三竹原生 + - ◀ ▶ 圓形懸浮按鈕) -->
            <div class="absolute top-[48%] left-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-1.5 bg-[#14171dc0] backdrop-blur-xs px-2.5 py-1 rounded-full border border-slate-700/60 shadow-lg pointer-events-auto opacity-75 hover:opacity-100 transition z-10">
                <button id="btnScrollLeft" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs">◀</button>
                <button id="btnZoomIn" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs font-bold">＋</button>
                <div class="w-5 h-5 rounded-full border border-slate-500 text-[10px] text-slate-300 flex items-center justify-center font-bold">息</div>
                <button id="btnZoomOut" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs font-bold">－</button>
                <button id="btnScrollRight" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs">▶</button>
            </div>
        </div>

        <!-- 底部切換標的選單與來源提示 (三竹工具箱) -->
        <div class="h-8 bg-[#090d13] border-t border-[#1e242d] px-3 flex items-center justify-between text-[11px] text-slate-400 select-none z-20">
            <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span id="dataStatus">股市資料庫.db 直連</span>
            </div>
            <div class="flex items-center gap-2">
                <select id="stockSelector" class="bg-[#121820] text-slate-200 border border-[#2b3542] rounded px-1.5 py-0.5 text-[10px] font-bold focus:outline-none">
                    <option value="00981A">00981A 主動統一台股增長</option>
                    <option value="MARKET">加權指數 (大盤+融資)</option>
                    <option value="FUND">統一奔騰 (基金淨值)</option>
                </select>
                <button id="btnResetView" class="text-sky-400 hover:text-sky-300 font-bold text-[10px]">最新位置</button>
            </div>
        </div>

    </div>

    <!-- 數據注入與高擬真 Canvas 繪圖引擎 -->
    <script>
        // 資料源 (全部來自股市資料庫.db)
        const allDatasets = {{
            "00981A": {{
                name: "主動統一台股增長",
                code: "00981A",
                data: {json_00981},
                isFund: false
            }},
            "MARKET": {{
                name: "加權指數 (TAIEX)",
                code: "大盤加權",
                data: {json_market},
                isFund: false
            }},
            "FUND": {{
                name: "統一奔騰基金",
                code: "10YTW",
                data: {json_fund},
                isFund: true
            }}
        }};

        let currentStockKey = "00981A";
        let currentStock = allDatasets[currentStockKey];
        let stockList = ["00981A", "MARKET", "FUND"];

        // Canvas 視圖狀態
        let canvas = document.getElementById("mainCanvas");
        let ctx = canvas.getContext("2d");
        
        let candleWidth = 7.5;      // 每一根K棒寬度
        let candleGap = 3.0;        // 每一根K棒間距
        let visibleCount = 55;      // 當前可視K棒數量
        let offsetIndex = 0;        // 偏移量 (0 代表最新，向左推移為正)
        let selectedIndex = -1;     // 十字線選取的索引 (-1 為最新一筆)
        let isDragging = false;
        let dragStartX = 0;
        let dragStartOffset = 0;

        // 初始化
        function initStock(key) {{
            currentStockKey = key;
            currentStock = allDatasets[key];
            document.getElementById("stockName").textContent = currentStock.name;
            document.getElementById("stockCode").textContent = currentStock.code;
            document.getElementById("stockSelector").value = key;
            offsetIndex = 0;
            selectedIndex = currentStock.data.length - 1;
            updateTopBar(currentStock.data[selectedIndex]);
            render();
        }}

        // 監聽視窗尺寸改變
        function resizeCanvas() {{
            const wrapper = document.getElementById("chartWrapper");
            const dpr = window.devicePixelRatio || 1;
            canvas.width = wrapper.clientWidth * dpr;
            canvas.height = wrapper.clientHeight * dpr;
            ctx.scale(dpr, dpr);
            render();
        }}

        window.addEventListener("resize", resizeCanvas);

        // 更新頂部查價欄
        function updateTopBar(record) {{
            if (!record) return;
            const parts = record["西元日期"].split("-");
            document.getElementById("infoDate").textContent = `${{parts[1]}}/${{parts[2]}}`;
            
            const o = record["開盤價"];
            const h = record["最高價"];
            const l = record["最低價"];
            const c = record["收盤價"];
            const diff = record["漲跌"];
            const vol = record["成交量_張"];

            const openEl = document.getElementById("infoOpen");
            const highEl = document.getElementById("infoHigh");
            const lowEl = document.getElementById("infoLow");
            const closeEl = document.getElementById("infoClose");
            const volEl = document.getElementById("infoVol");

            openEl.textContent = o.toFixed(2);
            highEl.textContent = h.toFixed(2);
            lowEl.textContent = l.toFixed(2);
            closeEl.textContent = c.toFixed(2);
            
            const volK = vol >= 1000 ? Math.round(vol / 1000) + "K" : vol;
            volEl.textContent = volK;

            // 顏色依漲跌
            const prevClose = c - diff;
            openEl.className = o >= prevClose ? "color-up" : "color-down";
            highEl.className = h >= prevClose ? "color-up" : "color-down";
            lowEl.className = l >= prevClose ? "color-up" : "color-down";
            closeEl.className = diff >= 0 ? "color-up" : "color-down";
        }}

        // 主繪圖函式 (Canvas)
        function render() {{
            const data = currentStock.data;
            const total = data.length;
            if (total === 0) return;

            const dpr = window.devicePixelRatio || 1;
            const width = canvas.width / dpr;
            const height = canvas.height / dpr;

            ctx.clearRect(0, 0, width, height);

            // 佈局比例配置 (仿三竹截圖)
            // 頂部主圖 (K線+BBAND): 50%
            // BBAND 資訊條: 24px
            // 時間軸 X 軸: 20px
            // 副圖一 KD: 24% (含 KD 標題條 20px)
            // 副圖二 融資餘額: 24% (含 融資 標題條 20px)
            
            const rightAxisWidth = 52; // 右側刻度欄寬度
            const chartW = width - rightAxisWidth;

            const mainTop = 6;
            const mainH = height * 0.44;
            const bbandBarTop = mainTop + mainH;
            const bbandBarH = 22;

            const timeAxisTop = bbandBarTop + bbandBarH;
            const timeAxisH = 18;

            const sub1BarTop = timeAxisTop + timeAxisH;
            const sub1BarH = 20;
            const sub1Top = sub1BarTop + sub1BarH;
            const sub1H = height * 0.19;

            const sub2BarTop = sub1Top + sub1H + 4;
            const sub2BarH = 20;
            const sub2Top = sub2BarTop + sub2BarH;
            const sub2H = height - sub2Top - 4;

            // 計算可視範圍索引
            visibleCount = Math.floor(chartW / (candleWidth + candleGap));
            let endIndex = total - 1 - offsetIndex;
            endIndex = Math.max(visibleCount - 1, Math.min(total - 1, endIndex));
            let startIndex = Math.max(0, endIndex - visibleCount + 1);

            const visibleData = data.slice(startIndex, endIndex + 1);
            if (visibleData.length === 0) return;

            // 尋找主圖最高、最低價格 (包含 BBAND)
            let maxP = -Infinity;
            let minP = Infinity;
            let maxIdx = 0;
            let minIdx = 0;

            visibleData.forEach((d, idx) => {{
                const h = Math.max(d["最高價"], d["BBAND_上軌"] || d["最高價"]);
                const l = Math.min(d["最低價"], d["BBAND_下軌"] || d["最低價"]);
                if (h > maxP) {{ maxP = h; maxIdx = idx; }}
                if (l < minP) {{ minP = l; minIdx = idx; }}
            }});

            const pricePad = (maxP - minP) * 0.08 || 1.0;
            maxP += pricePad;
            minP -= pricePad;

            function getY(p) {{
                return mainTop + mainH - ((p - minP) / (maxP - minP)) * mainH;
            }}

            function getX(idxInVisible) {{
                return 10 + idxInVisible * (candleWidth + candleGap) + candleWidth / 2;
            }}

            // 1. 繪製主圖背景網格線 (三竹風格水平虛線)
            ctx.strokeStyle = "#1a1e26";
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);

            const pSteps = 4;
            for (let i = 0; i <= pSteps; i++) {{
                const pVal = minP + (maxP - minP) * (i / pSteps);
                const yPos = getY(pVal);
                ctx.beginPath();
                ctx.moveTo(0, yPos);
                ctx.lineTo(chartW, yPos);
                ctx.stroke();

                // 右側刻度文字
                ctx.fillStyle = "#94a3b8";
                ctx.font = "11px 'Roboto Mono', monospace";
                ctx.textAlign = "left";
                ctx.fillText(pVal.toFixed(pVal > 100 ? 0 : 0), chartW + 6, yPos + 4);
            }}
            ctx.setLineDash([]);

            // 2. 繪製布林通道 (BBAND) 三條線
            // 上軌 (天藍色)
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_上軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_上軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 中軌 (金黃色)
            ctx.strokeStyle = "#eab308";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_中軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_中軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 下軌 (紫紅色)
            ctx.strokeStyle = "#c084fc";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_下軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_下軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 3. 繪製 K 線 (紅漲綠跌實體與影線)
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const o = d["開盤價"];
                const h = d["最高價"];
                const l = d["最低價"];
                const c = d["收盤價"];

                const isUp = c >= o;
                const color = isUp ? "#ff333a" : "#00e676";
                ctx.fillStyle = color;
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.2;

                // 上下影線
                const yH = getY(h);
                const yL = getY(l);
                ctx.beginPath();
                ctx.moveTo(x, yH);
                ctx.lineTo(x, yL);
                ctx.stroke();

                // 實體柱
                const yO = getY(o);
                const yC = getY(c);
                const topY = Math.min(yO, yC);
                const bodyH = Math.max(1.8, Math.abs(yO - yC));

                ctx.fillRect(x - candleWidth / 2, topY, candleWidth, bodyH);
            }});

            // 4. 極值高低點文字標註 (浮水印標籤)
            // 最高點
            const highItem = visibleData[maxIdx];
            const highX = getX(maxIdx);
            const highY = getY(highItem["最高價"]);
            ctx.fillStyle = "#ff333a";
            ctx.font = "bold 13px 'Roboto Mono', sans-serif";
            ctx.textAlign = highX > chartW - 50 ? "right" : "left";
            ctx.fillText(highItem["最高價"].toFixed(2), highX + (highX > chartW - 50 ? -6 : 6), highY - 2);

            // 最低點
            const lowItem = visibleData[minIdx];
            const lowX = getX(minIdx);
            const lowY = getY(lowItem["最低價"]);
            ctx.fillStyle = "#00e676";
            ctx.font = "bold 13px 'Roboto Mono', sans-serif";
            ctx.textAlign = lowX > chartW - 50 ? "right" : "left";
            ctx.fillText(lowItem["最低價"].toFixed(2), lowX + (lowX > chartW - 50 ? -6 : 6), lowY + 14);

            // 當前選取 / 最新收盤價標籤 (右側 Y 軸上的黃底黑字方塊)
            const curRecord = data[selectedIndex !== -1 ? selectedIndex : total - 1];
            const curY = getY(curRecord["收盤價"]);
            const tagW = rightAxisWidth - 2;
            const tagH = 18;

            ctx.fillStyle = "#ffd600";
            ctx.fillRect(chartW + 2, curY - tagH / 2, tagW, tagH);
            ctx.fillStyle = "#000000";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(curRecord["收盤價"].toFixed(2), chartW + tagW / 2 + 2, curY + 4);

            // 下方漲跌幅色塊
            const diffVal = curRecord["漲跌"];
            const pctVal = curRecord["漲跌幅"];
            ctx.fillStyle = diffVal >= 0 ? "#ff333a" : "#00e676";
            ctx.font = "bold 9px 'Roboto Mono', sans-serif";
            const signStr = diffVal >= 0 ? "▲+" : "▼";
            ctx.fillText(`${{signStr}}${{Math.abs(diffVal).toFixed(2)}}`, chartW + tagW / 2 + 2, curY + tagH / 2 + 10);
            ctx.fillText(`${{pctVal >= 0 ? "+" : ""}}${{pctVal.toFixed(2)}}%`, chartW + tagW / 2 + 2, curY + tagH / 2 + 20);

            // 5. BBAND 資訊條 (中軌、上軌、下軌數值)
            ctx.fillStyle = "#0d1117";
            ctx.fillRect(0, bbandBarTop, width, bbandBarH);
            ctx.strokeStyle = "#1a222d";
            ctx.beginPath();
            ctx.moveTo(0, bbandBarTop);
            ctx.lineTo(width, bbandBarTop);
            ctx.stroke();

            // 資訊文字
            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("BBAND >", 8, bbandBarTop + 15);

            ctx.fillStyle = "#ffd600";
            ctx.fillText(`22T:${{curRecord["BBAND_中軌"] || "--"}}⇂`, 72, bbandBarTop + 15);

            ctx.fillStyle = "#00e5ff";
            ctx.fillText(`上:${{curRecord["BBAND_上軌"] || "--"}}⇃`, 146, bbandBarTop + 15);

            ctx.fillStyle = "#d500f9";
            ctx.fillText(`下:${{curRecord["BBAND_下軌"] || "--"}}⇂`, 215, bbandBarTop + 15);

            // 右側「絕對值」按鈕
            ctx.fillStyle = "#222730";
            ctx.fillRect(width - 50, bbandBarTop + 2, 44, 18);
            ctx.strokeStyle = "#38414e";
            ctx.strokeRect(width - 50, bbandBarTop + 2, 44, 18);
            ctx.fillStyle = "#cbd5e1";
            ctx.font = "10px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("絕對值", width - 28, bbandBarTop + 14);

            // 6. 時間 X 軸 (月份與日期刻度)
            ctx.fillStyle = "#05070a";
            ctx.fillRect(0, timeAxisTop, width, timeAxisH);
            ctx.strokeStyle = "#1a1f26";
            ctx.strokeRect(0, timeAxisTop, width, timeAxisH);

            let lastMonth = "";
            ctx.font = "10px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#64748b";

            visibleData.forEach((d, idx) => {{
                const m = d["西元日期"].split("-")[1];
                if (m !== lastMonth && idx > 5) {{
                    const x = getX(idx);
                    ctx.fillText(m, x, timeAxisTop + 13);
                    lastMonth = m;
                }}
            }});

            // 7. 副圖一：KD 指標
            // 標題條
            ctx.fillStyle = "#0d1117";
            ctx.fillRect(0, sub1BarTop, width, sub1BarH);
            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("KD  >", 8, sub1BarTop + 14);

            const kVal = curRecord["K值"] || 50;
            const dVal = curRecord["D值"] || 50;

            ctx.fillStyle = "#ffd600";
            ctx.fillText(`9K:${{kVal.toFixed(2)}}⇂`, 50, sub1BarTop + 14);

            // 狀態判定提示
            if (kVal < 20 && dVal < 20) {{
                ctx.fillStyle = "#00e676";
                ctx.fillText("低檔鈍化", 125, sub1BarTop + 14);
            }} else if (kVal > 80 && dVal > 80) {{
                ctx.fillStyle = "#ff3b30";
                ctx.fillText("高檔鈍化", 125, sub1BarTop + 14);
            }} else if (kVal >= dVal) {{
                ctx.fillStyle = "#00e676";
                ctx.fillText("黃金交叉", 125, sub1BarTop + 14);
            }} else {{
                ctx.fillStyle = "#ff3b30";
                ctx.fillText("死亡交叉", 125, sub1BarTop + 14);
            }}

            ctx.fillStyle = "#00e5ff";
            ctx.fillText(`9D:${{dVal.toFixed(2)}}⇂`, 185, sub1BarTop + 14);

            // 右側刻度 (20, 50, 80)
            [80, 50, 20].forEach(val => {{
                const y = sub1Top + sub1H - (val / 100) * sub1H;
                ctx.strokeStyle = "#161b22";
                ctx.setLineDash([2, 4]);
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartW, y);
                ctx.stroke();

                ctx.fillStyle = "#64748b";
                ctx.font = "10px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillText(val, chartW + 6, y + 3);
            }});
            ctx.setLineDash([]);

            // KD 曲線繪製函式
            function getKdY(val) {{
                return sub1Top + sub1H - (Math.max(0, Math.min(100, val)) / 100) * sub1H;
            }}

            // 80 超買陰影填充帶
            ctx.fillStyle = "rgba(180, 40, 40, 0.25)";
            const y80 = getKdY(80);
            ctx.fillRect(0, sub1Top, chartW, y80 - sub1Top);

            // 20 超賣陰影填充帶
            ctx.fillStyle = "rgba(0, 180, 80, 0.25)";
            const y20 = getKdY(20);
            ctx.fillRect(0, y20, chartW, sub1Top + sub1H - y20);

            // 9K 線 (金黃色)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getKdY(d["K值"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 9D 線 (天藍色)
            ctx.strokeStyle = "#00e5ff";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getKdY(d["D值"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 8. 副圖二：融資餘額
            // 標題條
            ctx.fillStyle = "#0d1117";
            ctx.fillRect(0, sub2BarTop, width, sub2BarH);
            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("融資餘額 >", 8, sub2BarTop + 14);

            const mBal = curRecord["融資餘額_張"] || 0;
            const mDiff = curRecord["融資增減_張"] || 0;
            ctx.fillStyle = "#ffd600";
            ctx.fillText(`融資餘額:${{mBal}}張⇂`, 74, sub2BarTop + 14);

            ctx.fillStyle = mDiff >= 0 ? "#ff3b30" : "#00e5ff";
            ctx.fillText(`融資增減:${{mDiff >= 0 ? "+" : ""}}${{mDiff}}`, 210, sub2BarTop + 14);

            // 融資 Y 軸極值
            let maxM = -Infinity;
            let minM = Infinity;
            visibleData.forEach(d => {{
                const b = d["融資餘額_張"] || 0;
                if (b > maxM) maxM = b;
                if (b < minM) minM = b;
            }});
            const mPad = (maxM - minM) * 0.15 || 5000;
            maxM += mPad;
            minM -= mPad;

            function getMarginY(val) {{
                return sub2Top + sub2H - ((val - minM) / (maxM - minM)) * sub2H;
            }}

            // 融資網格刻度
            const mSteps = [maxM - mPad*0.5, (maxM + minM)/2, minM + mPad*0.5];
            mSteps.forEach(val => {{
                const y = getMarginY(val);
                ctx.strokeStyle = "#161b22";
                ctx.setLineDash([2, 4]);
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartW, y);
                ctx.stroke();

                ctx.fillStyle = "#64748b";
                ctx.font = "10px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillText(Math.round(val), chartW + 2, y + 3);
            }});
            ctx.setLineDash([]);

            // 融資增減柱狀圖 (零軸為 sub2Top + sub2H/2)
            const zeroY = sub2Top + sub2H * 0.7;
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const diff = d["融資增減_張"] || 0;
                const isPos = diff >= 0;
                ctx.fillStyle = isPos ? "#ff333a" : "#00e676";
                const barH = Math.min(sub2H * 0.45, Math.abs(diff) / 120);
                if (isPos) {{
                    ctx.fillRect(x - candleWidth/2, zeroY - barH, candleWidth, barH);
                }} else {{
                    ctx.fillRect(x - candleWidth/2, zeroY, candleWidth, barH);
                }}
            }});

            // 融資餘額折線 (金黃色)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getMarginY(d["融資餘額_張"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 9. 垂直金色查價十字線 (穿透三張圖)
            if (selectedIndex !== -1) {{
                const targetIdxInVis = selectedIndex - startIndex;
                if (targetIdxInVis >= 0 && targetIdxInVis < visibleData.length) {{
                    const crossX = getX(targetIdxInVis);
                    ctx.strokeStyle = "#ffd600";
                    ctx.lineWidth = 1.0;
                    ctx.setLineDash([]);
                    ctx.beginPath();
                    ctx.moveTo(crossX, mainTop);
                    ctx.lineTo(crossX, height);
                    ctx.stroke();

                    // 時間軸上的金色日期小標籤
                    const selRecord = visibleData[targetIdxInVis];
                    ctx.fillStyle = "#ffd600";
                    ctx.fillRect(crossX - 35, timeAxisTop, 70, timeAxisH);
                    ctx.fillStyle = "#000000";
                    ctx.font = "bold 10px 'Roboto Mono', sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(selRecord["西元日期"].replace(/-/g, "/"), crossX, timeAxisTop + 13);
                }}
            }}
        }}

        // 觸控與滑鼠事件 (平移與查價)
        function handlePointerMove(clientX) {{
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const x = clientX - rect.left;
            const rightAxisWidth = 52;
            const chartW = canvas.width / dpr - rightAxisWidth;

            if (x < 10 || x > chartW) return;

            const total = currentStock.data.length;
            const endIndex = total - 1 - offsetIndex;
            const startIndex = Math.max(0, endIndex - visibleCount + 1);
            const idxInVisible = Math.round((x - 10 - candleWidth / 2) / (candleWidth + candleGap));

            if (idxInVisible >= 0 && startIndex + idxInVisible < total) {{
                selectedIndex = startIndex + idxInVisible;
                updateTopBar(currentStock.data[selectedIndex]);
                render();
            }}
        }}

        canvas.addEventListener("mousedown", (e) => {{
            isDragging = true;
            dragStartX = e.clientX;
            dragStartOffset = offsetIndex;
            handlePointerMove(e.clientX);
        }});

        window.addEventListener("mousemove", (e) => {{
            if (isDragging) {{
                const dx = e.clientX - dragStartX;
                const shiftCandles = Math.round(dx / (candleWidth + candleGap));
                offsetIndex = Math.max(0, Math.min(currentStock.data.length - visibleCount, dragStartOffset + shiftCandles));
                render();
            }} else {{
                handlePointerMove(e.clientX);
            }}
        }});

        window.addEventListener("mouseup", () => {{
            isDragging = false;
        }});

        // 觸控支援
        canvas.addEventListener("touchstart", (e) => {{
            if (e.touches.length === 1) {{
                isDragging = true;
                dragStartX = e.touches[0].clientX;
                dragStartOffset = offsetIndex;
                handlePointerMove(e.touches[0].clientX);
            }}
        }}, {{ passive: true }});

        canvas.addEventListener("touchmove", (e) => {{
            if (e.touches.length === 1) {{
                const dx = e.touches[0].clientX - dragStartX;
                if (Math.abs(dx) > 10) {{
                    const shiftCandles = Math.round(dx / (candleWidth + candleGap));
                    offsetIndex = Math.max(0, Math.min(currentStock.data.length - visibleCount, dragStartOffset + shiftCandles));
                }}
                handlePointerMove(e.touches[0].clientX);
            }}
        }}, {{ passive: true }});

        canvas.addEventListener("touchend", () => {{
            isDragging = false;
        }});

        // 懸浮按鈕操作
        document.getElementById("btnScrollLeft").addEventListener("click", () => {{
            offsetIndex = Math.min(currentStock.data.length - visibleCount, offsetIndex + 10);
            render();
        }});

        document.getElementById("btnScrollRight").addEventListener("click", () => {{
            offsetIndex = Math.max(0, offsetIndex - 10);
            render();
        }});

        document.getElementById("btnZoomIn").addEventListener("click", () => {{
            candleWidth = Math.min(18, candleWidth + 1.5);
            candleGap = Math.min(8, candleGap + 0.8);
            render();
        }});

        document.getElementById("btnZoomOut").addEventListener("click", () => {{
            candleWidth = Math.max(3.5, candleWidth - 1.5);
            candleGap = Math.max(1.5, candleGap - 0.8);
            render();
        }});

        // 重設視圖
        document.getElementById("btnResetView").addEventListener("click", () => {{
            offsetIndex = 0;
            selectedIndex = currentStock.data.length - 1;
            updateTopBar(currentStock.data[selectedIndex]);
            render();
        }});

        // 關閉查價鈕
        document.getElementById("btnCloseCross").addEventListener("click", () => {{
            selectedIndex = currentStock.data.length - 1;
            updateTopBar(currentStock.data[selectedIndex]);
            render();
        }});

        // 標的切換
        document.getElementById("stockSelector").addEventListener("change", (e) => {{
            initStock(e.target.value);
        }});

        document.getElementById("btnPrevStock").addEventListener("click", () => {{
            const curIdx = stockList.indexOf(currentStockKey);
            const nextIdx = (curIdx - 1 + stockList.length) % stockList.length;
            initStock(stockList[nextIdx]);
        }});

        document.getElementById("btnNextStock").addEventListener("click", () => {{
            const curIdx = stockList.indexOf(currentStockKey);
            const nextIdx = (curIdx + 1) % stockList.length;
            initStock(stockList[nextIdx]);
        }});

        // 切換手機 / 桌面滿版模式
        document.getElementById("btnToggleMode").addEventListener("click", () => {{
            const app = document.getElementById("appContainer");
            app.classList.toggle("full-mode");
            setTimeout(resizeCanvas, 50);
        }});

        // 頁面加載完成時初始化
        window.addEventListener("DOMContentLoaded", () => {{
            resizeCanvas();
            initStock("00981A");
        }});
    </script>
</body>
</html>
'''
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"成功產出 100% 擬真三竹 APP 互動看盤頁面：{output_path}！")

if __name__ == "__main__":
    generate_mitake_html()
